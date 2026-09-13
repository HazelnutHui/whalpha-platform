"""CLI for owner-only SEC filer-to-security link candidate construction."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.services.sec_filer_security_link_decision import (
    MAXIMUM_WORKERS,
    build_sec_filer_security_link_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-package", required=True, type=Path)
    parser.add_argument("--range-start", required=True, type=date.fromisoformat)
    parser.add_argument("--range-end", required=True, type=date.fromisoformat)
    parser.add_argument("--provider", default="massive_stocks_basic")
    parser.add_argument("--workers", type=int, default=min(4, MAXIMUM_WORKERS))
    parser.add_argument(
        "--allow-missing-source-session",
        action="append",
        default=[],
        type=date.fromisoformat,
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_sec_filer_security_link_package(
            data_root=args.data_root,
            output_package_path=args.output_package,
            range_start=args.range_start,
            range_end=args.range_end,
            provider=args.provider,
            worker_count=args.workers,
            allowed_missing_source_sessions=tuple(
                sorted(set(args.allow_missing_source_session))
            ),
            implementation_revision=revision,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "canonical_data_write_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    manifest = result.manifest
    print(
        json.dumps(
            {
                "status": "completed",
                "implementation_revision": revision,
                "package_path": str(result.package_path),
                "session_count": manifest.session_count,
                "row_count": manifest.row_count,
                "decision_status_counts": manifest.decision_status_counts,
                "missing_source_session_count": (
                    manifest.missing_source_session_count
                ),
                "multi_security_cik_session_count": (
                    manifest.multi_security_cik_session_count
                ),
                "logical_fingerprint": manifest.logical_fingerprint,
                "canonical_data_write_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
