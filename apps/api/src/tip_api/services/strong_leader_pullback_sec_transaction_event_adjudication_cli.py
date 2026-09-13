"""CLI for typed first-strategy SEC transaction-event evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_transaction_event_adjudication import (
    StrongLeaderPullbackSecTransactionEventAdjudicationError,
    build_strong_leader_pullback_sec_transaction_event_adjudication,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-custody-root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-custody-root", required=True, type=Path)
    parser.add_argument("--transaction", required=True, type=Path)
    parser.add_argument("--transaction-custody-root", required=True, type=Path)
    parser.add_argument("--cover-adjudication", required=True, type=Path)
    parser.add_argument("--cover-adjudication-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = build_strong_leader_pullback_sec_transaction_event_adjudication(
            plan_root=args.plan,
            plan_custody_root=args.plan_custody_root,
            source_root=args.source,
            source_custody_root=args.source_custody_root,
            transaction_root=args.transaction,
            transaction_custody_root=args.transaction_custody_root,
            cover_adjudication_root=args.cover_adjudication,
            cover_adjudication_custody_root=(
                args.cover_adjudication_custody_root
            ),
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
                "transaction_document_count": report.transaction_document_count,
                "matched_event_count": report.matched_event_count,
                "ambiguous_event_count": report.ambiguous_event_count,
                "unsupported_event_count": report.unsupported_event_count,
                "decision_rule_counts": report.decision_rule_counts,
                "scope_profile_counts": report.scope_profile_counts,
                "report_date_relation_counts": report.report_date_relation_counts,
                "report_date_difference_count": report.report_date_difference_count,
                "earliest_event_date": (
                    report.earliest_event_date.isoformat()
                    if report.earliest_event_date is not None
                    else None
                ),
                "latest_event_date": (
                    report.latest_event_date.isoformat()
                    if report.latest_event_date is not None
                    else None
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "termination_reason_adjudication_count": 0,
                "consideration_adjudication_count": 0,
                "party_relation_adjudication_count": 0,
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
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
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
