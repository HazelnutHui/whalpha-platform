"""CLI for the three-case listed-consideration residual source plan."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source_plan as plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-plan", required=True, type=Path)
    parser.add_argument("--original-plan-custody-root", required=True, type=Path)
    parser.add_argument("--identity-adjudication", required=True, type=Path)
    parser.add_argument(
        "--identity-adjudication-custody-root", required=True, type=Path
    )
    parser.add_argument("--consideration", required=True, type=Path)
    parser.add_argument("--consideration-custody-root", required=True, type=Path)
    parser.add_argument("--submissions-package", required=True, type=Path)
    parser.add_argument("--submissions-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        builder = (
            plan.build_strong_leader_pullback_listed_consideration_residual_source_plan
        )
        result = builder(
            original_plan_root=args.original_plan,
            original_plan_custody_root=args.original_plan_custody_root,
            identity_adjudication_root=args.identity_adjudication,
            identity_adjudication_custody_root=(
                args.identity_adjudication_custody_root
            ),
            consideration_root=args.consideration,
            consideration_custody_root=args.consideration_custody_root,
            submissions_package_root=args.submissions_package,
            submissions_custody_root=args.submissions_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=_clean_revision(),
            evaluated_at=args.evaluated_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "network_request_count": 0,
                    "planned_source_document_count": 0,
                    "identity_assignment_count": 0,
                    "terminal_value_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
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
                "status": result.status,
                "completion_status": report.completion_status,
                "implementation_revision": report.implementation_revision,
                "evaluated_at": report.evaluated_at.isoformat(),
                "residual_case_count": report.residual_case_count,
                "local_composite_evidence_ready_count": (
                    report.local_composite_evidence_ready_count
                ),
                "replacement_registration_required_count": (
                    report.replacement_registration_required_count
                ),
                "planned_source_document_count": (
                    report.planned_source_document_count
                ),
                "resolution_path_counts": report.resolution_path_counts,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "identity_assignment_count": 0,
                "terminal_value_count": 0,
                "canonical_data_write_count": 0,
                "research_admission_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _datetime(value: str) -> datetime:
    try:
        return normalize_utc_datetime(datetime.fromisoformat(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "timestamp must be an ISO-8601 UTC value"
        ) from exc


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise plan.StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
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
