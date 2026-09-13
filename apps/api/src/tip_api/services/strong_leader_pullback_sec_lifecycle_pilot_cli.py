"""CLI for the bounded first-strategy SEC lifecycle metadata pilot."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.strong_leader_pullback_sec_lifecycle_pilot import (
    CONTRACT_VERSION,
    StrongLeaderPullbackSecLifecyclePilotError,
    build_strong_leader_pullback_sec_lifecycle_pilot,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True, type=Path)
    parser.add_argument("--sample-custody-root", required=True, type=Path)
    parser.add_argument("--submissions-package", required=True, type=Path)
    parser.add_argument("--submissions-custody-root", required=True, type=Path)
    parser.add_argument("--submissions-census-root", required=True, type=Path)
    parser.add_argument("--source-snapshot-date", required=True, type=date.fromisoformat)
    parser.add_argument("--range-start", required=True, type=date.fromisoformat)
    parser.add_argument("--range-end", required=True, type=date.fromisoformat)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument(
        "--evaluated-at",
        required=True,
        type=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")),
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_strong_leader_pullback_sec_lifecycle_pilot(
            sample_root=args.sample,
            sample_custody_root=args.sample_custody_root,
            submissions_package_path=args.submissions_package,
            submissions_custody_root=args.submissions_custody_root,
            submissions_census_root=args.submissions_census_root,
            source_snapshot_date=args.source_snapshot_date,
            range_start=args.range_start,
            range_end=args.range_end,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=revision,
            evaluated_at=args.evaluated_at,
        )
    except (
        OSError,
        RuntimeError,
        StrongLeaderPullbackSecLifecyclePilotError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "sec_lifecycle_pilot_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "document_request_count": 0,
                    "credential_read_count": 0,
                    "canonical_data_write_count": 0,
                    "historical_coverage_write_count": 0,
                    "research_admission_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    report = result.report
    print(
        json.dumps(
            {
                "contract_version": report.contract_version,
                "record_type": "sec_lifecycle_pilot_completion",
                "status": result.status,
                "implementation_revision": revision,
                "lifecycle_case_count": report.lifecycle_case_count,
                "candidate_filing_count": report.candidate_filing_count,
                "on_or_after_last_observation_candidate_count": (
                    report.on_or_after_last_observation_candidate_count
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "document_request_count": 0,
                "credential_read_count": 0,
                "canonical_data_write_count": 0,
                "historical_coverage_write_count": 0,
                "research_admission_count": 0,
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
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "repository must be clean"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
