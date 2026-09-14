"""CLI for listed-consideration registration-document adjudication."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_listed_consideration_adjudication import (
    StrongLeaderPullbackListedConsiderationAdjudicationError,
    build_strong_leader_pullback_listed_consideration_adjudication,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-custody-root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-custody-root", required=True, type=Path)
    parser.add_argument("--payoff-terms", required=True, type=Path)
    parser.add_argument("--payoff-terms-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = build_strong_leader_pullback_listed_consideration_adjudication(
            plan_root=args.plan,
            plan_custody_root=args.plan_custody_root,
            source_root=args.source,
            source_custody_root=args.source_custody_root,
            payoff_terms_root=args.payoff_terms,
            payoff_terms_custody_root=args.payoff_terms_custody_root,
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
                "case_count": report.case_count,
                "matched_identity_count": report.matched_identity_count,
                "final_ratio_absent_count": report.final_ratio_absent_count,
                "transaction_scope_absent_count": (
                    report.transaction_scope_absent_count
                ),
                "required_evidence_not_matched_count": (
                    report.required_evidence_not_matched_count
                ),
                "resolution_state_counts": report.resolution_state_counts,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "identity_assignment_count": (
                    report.consideration_security_identity_assignment_count
                ),
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
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
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
