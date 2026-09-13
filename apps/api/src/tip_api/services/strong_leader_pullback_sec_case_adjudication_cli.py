"""CLI for the first-strategy SEC case adjudication."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_case_adjudication import (
    StrongLeaderPullbackSecCaseAdjudicationError,
    build_strong_leader_pullback_sec_case_adjudication,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sample", required=True, type=Path)
    parser.add_argument("--source-sample-custody-root", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-custody-root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-custody-root", required=True, type=Path)
    parser.add_argument("--transaction", required=True, type=Path)
    parser.add_argument("--transaction-custody-root", required=True, type=Path)
    parser.add_argument("--coverage", required=True, type=Path)
    parser.add_argument("--coverage-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = build_strong_leader_pullback_sec_case_adjudication(
            source_sample_root=args.source_sample,
            source_sample_custody_root=args.source_sample_custody_root,
            plan_root=args.plan,
            plan_custody_root=args.plan_custody_root,
            source_root=args.source,
            source_custody_root=args.source_custody_root,
            transaction_root=args.transaction,
            transaction_custody_root=args.transaction_custody_root,
            coverage_root=args.coverage,
            coverage_custody_root=args.coverage_custody_root,
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
                    "lifecycle_fact_count": 0,
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
                "lifecycle_case_count": report.lifecycle_case_count,
                "cover_8k_document_count": report.cover_8k_document_count,
                "cover_security_row_count": report.cover_security_row_count,
                "incomplete_security_context_count": (
                    report.incomplete_security_context_count
                ),
                "matched_cover_document_count": report.matched_cover_document_count,
                "outside_lifecycle_window_document_count": (
                    report.outside_lifecycle_window_document_count
                ),
                "matched_identity_case_count": report.matched_identity_case_count,
                "result_state_counts": report.result_state_counts,
                "field_result_counts": report.field_result_counts,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "lifecycle_fact_count": 0,
                "terminal_outcome_count": 0,
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
        raise StrongLeaderPullbackSecCaseAdjudicationError(
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
