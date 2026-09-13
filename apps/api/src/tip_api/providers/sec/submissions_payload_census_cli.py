"""CLI for the network-free SEC filing-time coverage census."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.providers.sec.submissions_payload_census import (
    CONTRACT_VERSION,
    MAXIMUM_WORKERS,
    SecSubmissionsPayloadCensusError,
    census_sec_submissions_payloads,
    seal_sec_submissions_payload_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submissions-package", required=True, type=Path)
    parser.add_argument("--submissions-custody-root", required=True, type=Path)
    parser.add_argument("--companyfacts-package", required=True, type=Path)
    parser.add_argument("--companyfacts-custody-root", required=True, type=Path)
    parser.add_argument("--companyfacts-census-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
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
        census = census_sec_submissions_payloads(
            submissions_package_path=args.submissions_package,
            submissions_custody_root=args.submissions_custody_root,
            companyfacts_package_path=args.companyfacts_package,
            companyfacts_custody_root=args.companyfacts_custody_root,
            companyfacts_census_root=args.companyfacts_census_root,
            range_start=args.range_start,
            range_end=args.range_end,
            worker_count=args.workers,
        )
        target = seal_sec_submissions_payload_census(
            output_root=args.output_root, census=census
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
    print(
        json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "record_type": "sec_submissions_payload_census_completion",
                "status": "sealed",
                "implementation_revision": revision,
                "source_member_count": census.source_member_count,
                "quarantined_member_count": census.quarantined_member_count,
                "filing_row_count": census.filing_row_count,
                "companyfacts_target_accession_count": (
                    census.companyfacts_target_accession_count
                ),
                "target_accession_matched_count": (
                    census.target_accession_matched_count
                ),
                "target_accession_missing_count": (
                    census.target_accession_missing_count
                ),
                "target_with_valid_acceptance_count": (
                    census.target_with_valid_acceptance_count
                ),
                "target_conflicting_acceptance_count": (
                    census.target_conflicting_acceptance_count
                ),
                "logical_fingerprint": census.logical_fingerprint,
                "output_sha256": _sha256_file(target),
                "output_path": str(target),
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
        raise SecSubmissionsPayloadCensusError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
