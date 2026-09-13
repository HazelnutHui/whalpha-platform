"""CLI for the first-strategy cross-venue source acceptance sample."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    CONTRACT_VERSION,
    StrongLeaderPullbackSourceAcceptanceSampleError,
    build_strong_leader_pullback_source_acceptance_sample,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocker-census", required=True, type=Path)
    parser.add_argument("--blocker-census-custody-root", required=True, type=Path)
    parser.add_argument("--lifecycle-shadow", required=True, type=Path)
    parser.add_argument("--lifecycle-shadow-custody-root", required=True, type=Path)
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
        result = build_strong_leader_pullback_source_acceptance_sample(
            blocker_census_root=args.blocker_census,
            blocker_census_custody_root=args.blocker_census_custody_root,
            lifecycle_shadow_root=args.lifecycle_shadow,
            lifecycle_shadow_custody_root=args.lifecycle_shadow_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=revision,
            evaluated_at=args.evaluated_at,
        )
    except (
        StrongLeaderPullbackSourceAcceptanceSampleError,
        OSError,
        RuntimeError,
        ValueError,
    ):
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "source_acceptance_sample_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "provider_request_count": 0,
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
                "record_type": "source_acceptance_sample_completion",
                "status": result.status,
                "implementation_revision": revision,
                "action_case_count": report.action_case_count,
                "lifecycle_case_count": report.lifecycle_case_count,
                "combined_instrument_count": report.combined_instrument_count,
                "lifecycle_source_occurrence_count": (
                    report.lifecycle_source_occurrence_count
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "provider_request_count": 0,
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
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
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
