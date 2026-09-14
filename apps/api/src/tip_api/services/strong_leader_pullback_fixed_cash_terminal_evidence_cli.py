"""CLI for first-strategy fixed-cash terminal evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_fixed_cash_terminal_evidence import (
    StrongLeaderPullbackFixedCashTerminalEvidenceError,
    build_strong_leader_pullback_fixed_cash_terminal_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consideration", required=True, type=Path)
    parser.add_argument("--consideration-custody-root", required=True, type=Path)
    parser.add_argument("--cessation", required=True, type=Path)
    parser.add_argument("--cessation-custody-root", required=True, type=Path)
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
        result = build_strong_leader_pullback_fixed_cash_terminal_evidence(
            consideration_root=args.consideration,
            consideration_custody_root=args.consideration_custody_root,
            cessation_root=args.cessation,
            cessation_custody_root=args.cessation_custody_root,
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
                    "terminal_cash_evidence_count": 0,
                    "canonical_lifecycle_fact_count": 0,
                    "canonical_terminal_outcome_count": 0,
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
                "source_candidate_count": report.source_candidate_count,
                "terminal_cash_evidence_count": (
                    report.terminal_cash_evidence_count
                ),
                "excluded_case_count": report.excluded_case_count,
                "evidenced_timing_profile_counts": (
                    report.evidenced_timing_profile_counts
                ),
                "completion_equals_stop_boundary_count": (
                    report.completion_equals_stop_boundary_count
                ),
                "completion_before_stop_boundary_count": (
                    report.completion_before_stop_boundary_count
                ),
                "completion_after_stop_boundary_count": (
                    report.completion_after_stop_boundary_count
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "canonical_lifecycle_fact_count": 0,
                "canonical_terminal_outcome_count": 0,
                "strategy_outcome_label_count": 0,
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
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
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
