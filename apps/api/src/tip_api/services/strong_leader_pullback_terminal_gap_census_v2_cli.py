"""CLI for the EOD-corrected Strong-Leader Pullback terminal-gap census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_terminal_gap_census_v2 as service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "boundary-census",
        "boundary-census-custody-root",
        "prior-gap-census",
        "prior-gap-census-custody-root",
        "source-sample",
        "source-sample-custody-root",
        "lifecycle-shadow",
        "lifecycle-shadow-custody-root",
        "payoff-terms",
        "payoff-terms-custody-root",
        "fixed-cash",
        "fixed-cash-custody-root",
        "listed-terminal",
        "listed-terminal-custody-root",
        "residual-terminal",
        "residual-terminal-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument(
        "--lifecycle-anchor", required=True, action="append", type=date.fromisoformat
    )
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = service.build_strong_leader_pullback_terminal_gap_census_v2(
            boundary_census_root=args.boundary_census,
            boundary_census_custody_root=args.boundary_census_custody_root,
            prior_gap_census_root=args.prior_gap_census,
            prior_gap_census_custody_root=args.prior_gap_census_custody_root,
            source_sample_root=args.source_sample,
            source_sample_custody_root=args.source_sample_custody_root,
            lifecycle_shadow_root=args.lifecycle_shadow,
            lifecycle_shadow_custody_root=args.lifecycle_shadow_custody_root,
            lifecycle_anchor_dates=tuple(args.lifecycle_anchor),
            payoff_terms_root=args.payoff_terms,
            payoff_terms_custody_root=args.payoff_terms_custody_root,
            fixed_cash_root=args.fixed_cash,
            fixed_cash_custody_root=args.fixed_cash_custody_root,
            listed_terminal_root=args.listed_terminal,
            listed_terminal_custody_root=args.listed_terminal_custody_root,
            residual_terminal_root=args.residual_terminal,
            residual_terminal_custody_root=args.residual_terminal_custody_root,
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
                    "terminal_outcome_count": 0,
                    "research_admission_count": 0,
                    "canonical_data_write_count": 0,
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
                "population_instrument_count": report.population_instrument_count,
                "newly_in_scope_instrument_count": report.newly_in_scope_instrument_count,
                "reference_documented_instrument_count": (
                    report.reference_documented_instrument_count
                ),
                "remaining_gap_instrument_count": report.remaining_gap_instrument_count,
                "documented_horizon_5_crossing_path_count": (
                    report.documented_horizon_5_crossing_path_count
                ),
                "remaining_horizon_5_crossing_path_count": (
                    report.remaining_horizon_5_crossing_path_count
                ),
                "state_impacts": [
                    item.model_dump(mode="json") for item in report.state_impacts
                ],
                "priority_order": report.priority_order,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "terminal_outcome_count": 0,
                "research_admission_count": 0,
                "canonical_data_write_count": 0,
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
        raise service.StrongLeaderPullbackTerminalGapCensusV2Error(
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
