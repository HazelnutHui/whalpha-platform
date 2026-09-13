"""CLI for a bounded, network-free SEC Company Facts payload census."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tip_api.providers.sec.companyfacts_payload_census import (
    CONTRACT_VERSION,
    MAXIMUM_WORKERS,
    SecCompanyfactsPayloadCensusError,
    census_sec_companyfacts_payloads,
    seal_sec_companyfacts_payload_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-package", required=True, type=Path)
    parser.add_argument("--source-custody-root", required=True, type=Path)
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
        census = census_sec_companyfacts_payloads(
            source_package_path=args.source_package,
            source_custody_root=args.source_custody_root,
            range_start=args.range_start,
            range_end=args.range_end,
            worker_count=args.workers,
        )
        target = seal_sec_companyfacts_payload_census(
            output_root=args.output_root,
            census=census,
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
                "record_type": "sec_companyfacts_payload_census_completion",
                "status": "sealed",
                "implementation_revision": revision,
                "source_snapshot_date": census.source_snapshot_date.isoformat(),
                "source_member_count": census.source_member_count,
                "populated_member_count": census.populated_member_count,
                "empty_object_member_count": census.empty_object_member_count,
                "empty_facts_member_count": census.empty_facts_member_count,
                "quarantined_member_count": census.quarantined_member_count,
                "fact_count": census.fact_count,
                "fact_filed_in_range_count": census.fact_filed_in_range_count,
                "in_range_unique_accession_count": census.in_range_unique_accession_count,
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
        raise SecCompanyfactsPayloadCensusError("repository must be clean")
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
