"""CLI for three residual listed-consideration reference values."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_terminal_evidence as service,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-terminal-evidence", required=True, type=Path)
    parser.add_argument(
        "--prior-terminal-evidence-custody-root", required=True, type=Path
    )
    parser.add_argument("--residual-identity", required=True, type=Path)
    parser.add_argument("--residual-identity-custody-root", required=True, type=Path)
    parser.add_argument("--consideration", required=True, type=Path)
    parser.add_argument("--consideration-custody-root", required=True, type=Path)
    parser.add_argument("--cessation", required=True, type=Path)
    parser.add_argument("--cessation-custody-root", required=True, type=Path)
    parser.add_argument("--payoff-terms", required=True, type=Path)
    parser.add_argument("--payoff-terms-custody-root", required=True, type=Path)
    parser.add_argument("--canonical-eod-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        builder = (
            service.build_strong_leader_pullback_listed_consideration_residual_terminal_evidence
        )
        result = builder(
            prior_terminal_evidence_root=args.prior_terminal_evidence,
            prior_terminal_evidence_custody_root=(
                args.prior_terminal_evidence_custody_root
            ),
            residual_identity_root=args.residual_identity,
            residual_identity_custody_root=(
                args.residual_identity_custody_root
            ),
            consideration_root=args.consideration,
            consideration_custody_root=args.consideration_custody_root,
            cessation_root=args.cessation,
            cessation_custody_root=args.cessation_custody_root,
            payoff_terms_root=args.payoff_terms,
            payoff_terms_custody_root=args.payoff_terms_custody_root,
            canonical_eod_root=args.canonical_eod_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=_clean_revision(),
            evaluated_at=args.evaluated_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": service.CONTRACT_VERSION,
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "network_request_count": 0,
                    "terminal_reference_value_count": 0,
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
                "residual_case_count": report.residual_case_count,
                "prior_terminal_reference_value_count": (
                    report.prior_terminal_reference_value_count
                ),
                "residual_terminal_reference_value_count": (
                    report.residual_terminal_reference_value_count
                ),
                "cumulative_terminal_reference_value_count": (
                    report.cumulative_terminal_reference_value_count
                ),
                "valuation_session_count": report.valuation_session_count,
                "decision_state_counts": report.decision_state_counts,
                "price_quality_status_counts": (
                    report.price_quality_status_counts
                ),
                "price_quality_flag_counts": report.price_quality_flag_counts,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "canonical_terminal_outcome_count": 0,
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
        error = (
            service.StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError
        )
        raise error("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
