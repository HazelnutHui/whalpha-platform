"""CLI for immutable SEC Company Facts occurrence normalization."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.providers.sec.companyfacts_normalized_source import (
    MAXIMUM_WORKERS,
    SecCompanyfactsNormalizedSourceError,
    build_sec_companyfacts_normalized_source,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--companyfacts-package", required=True, type=Path)
    parser.add_argument("--companyfacts-custody-root", required=True, type=Path)
    parser.add_argument("--companyfacts-census-root", required=True, type=Path)
    parser.add_argument("--filing-clock-package", required=True, type=Path)
    parser.add_argument("--output-package", required=True, type=Path)
    parser.add_argument("--range-start", required=True, type=date.fromisoformat)
    parser.add_argument("--range-end", required=True, type=date.fromisoformat)
    parser.add_argument("--workers", type=int, default=min(8, MAXIMUM_WORKERS))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_sec_companyfacts_normalized_source(
            companyfacts_package_path=args.companyfacts_package,
            companyfacts_custody_root=args.companyfacts_custody_root,
            companyfacts_census_root=args.companyfacts_census_root,
            filing_clock_package_path=args.filing_clock_package,
            output_package_path=args.output_package,
            range_start=args.range_start,
            range_end=args.range_end,
            worker_count=args.workers,
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
                "entity_count": manifest.entity_count,
                "concept_count": manifest.concept_count,
                "occurrence_count": manifest.occurrence_count,
                "clock_admitted_occurrence_count": (
                    manifest.clock_admitted_occurrence_count
                ),
                "clock_quarantined_occurrence_count": (
                    manifest.clock_quarantined_occurrence_count
                ),
                "normalization_quarantined_occurrence_count": (
                    manifest.normalization_quarantined_occurrence_count
                ),
                "content_fingerprint": manifest.content_fingerprint,
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
        raise SecCompanyfactsNormalizedSourceError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
