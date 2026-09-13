"""CLI for the immutable SEC Company Facts semantic census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tip_api.providers.sec.companyfacts_semantic_census import (
    MAXIMUM_PROCESSES,
    SecCompanyfactsSemanticCensusError,
    build_sec_companyfacts_semantic_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized-package", required=True, type=Path)
    parser.add_argument("--link-package", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-package", required=True, type=Path)
    parser.add_argument("--processes", type=int, default=min(8, MAXIMUM_PROCESSES))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_sec_companyfacts_semantic_census(
            normalized_package_path=args.normalized_package,
            link_package_path=args.link_package,
            data_root=args.data_root,
            output_package_path=args.output_package,
            process_count=args.processes,
            implementation_revision=revision,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
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
    census = result.census
    print(
        json.dumps(
            {
                "status": "completed",
                "implementation_revision": revision,
                "package_path": str(result.package_path),
                "occurrence_count": census.occurrence_count,
                "distinct_filer_count": census.distinct_filer_count,
                "semantic_key_count": census.semantic_key_count,
                "within_accession_conflict_group_count": (
                    census.within_accession_conflict_group_count
                ),
                "later_revision_value_change_count": (
                    census.later_revision_value_change_count
                ),
                "logical_fingerprint": census.logical_fingerprint,
                "external_request_count": 0,
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
        raise SecCompanyfactsSemanticCensusError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
