"""CLI for the immutable conservative SEC filing-clock ledger."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.providers.sec.filing_clock_ledger import (
    MAXIMUM_WORKERS,
    SecFilingClockLedgerError,
    build_sec_filing_clock_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submissions-package", required=True, type=Path)
    parser.add_argument("--submissions-custody-root", required=True, type=Path)
    parser.add_argument("--submissions-census-root", required=True, type=Path)
    parser.add_argument("--companyfacts-package", required=True, type=Path)
    parser.add_argument("--companyfacts-custody-root", required=True, type=Path)
    parser.add_argument("--companyfacts-census-root", required=True, type=Path)
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
        result = build_sec_filing_clock_package(
            submissions_package_path=args.submissions_package,
            submissions_custody_root=args.submissions_custody_root,
            submissions_census_root=args.submissions_census_root,
            companyfacts_package_path=args.companyfacts_package,
            companyfacts_custody_root=args.companyfacts_custody_root,
            companyfacts_census_root=args.companyfacts_census_root,
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
                "record_count": manifest.record_count,
                "admitted_accession_count": manifest.admitted_accession_count,
                "quarantined_accession_count": (
                    manifest.quarantined_accession_count
                ),
                "conflicting_acceptance_accession_count": (
                    manifest.conflicting_acceptance_accession_count
                ),
                "filing_date_disagreement_count": (
                    manifest.filing_date_disagreement_count
                ),
                "selected_midnight_acceptance_count": (
                    manifest.selected_midnight_acceptance_count
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
        raise SecFilingClockLedgerError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
