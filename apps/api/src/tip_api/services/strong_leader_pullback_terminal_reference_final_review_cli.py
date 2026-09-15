"""CLI for the final Strong-Leader Pullback terminal-reference review."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_terminal_reference_final_review as service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "gap-v3",
        "gap-v3-custody-root",
        "gap-v4",
        "gap-v4-custody-root",
        "payoff-terms",
        "payoff-terms-custody-root",
        "consideration",
        "consideration-custody-root",
        "legacy-sec-source",
        "legacy-sec-source-custody-root",
        "terminal-sec-plan",
        "terminal-sec-plan-custody-root",
        "terminal-sec-source",
        "terminal-sec-source-custody-root",
        "supplement-plan",
        "supplement-plan-custody-root",
        "supplement-source",
        "supplement-source-custody-root",
        "canonical-eod-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = service.publish_strong_leader_pullback_terminal_reference_final_review(
            gap_v3_root=args.gap_v3,
            gap_v3_custody_root=args.gap_v3_custody_root,
            gap_v4_root=args.gap_v4,
            gap_v4_custody_root=args.gap_v4_custody_root,
            payoff_terms_root=args.payoff_terms,
            payoff_terms_custody_root=args.payoff_terms_custody_root,
            consideration_root=args.consideration,
            consideration_custody_root=args.consideration_custody_root,
            legacy_sec_source_root=args.legacy_sec_source,
            legacy_sec_source_custody_root=args.legacy_sec_source_custody_root,
            terminal_sec_plan_root=args.terminal_sec_plan,
            terminal_sec_plan_custody_root=args.terminal_sec_plan_custody_root,
            terminal_sec_source_root=args.terminal_sec_source,
            terminal_sec_source_custody_root=args.terminal_sec_source_custody_root,
            supplement_plan_root=args.supplement_plan,
            supplement_plan_custody_root=args.supplement_plan_custody_root,
            supplement_source_root=args.supplement_source,
            supplement_source_custody_root=args.supplement_source_custody_root,
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
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "network_request_count": 0,
                    "forward_outcome_count": 0,
                    "performance_metric_count": 0,
                    "parameter_selection_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
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
                "status": result.status,
                "completion_status": report.completion_status,
                "residual_case_count": report.residual_case_count,
                "residual_path_count": report.residual_path_count,
                "total_exact_reference_path_count": report.total_exact_reference_path_count,
                "finite_interval_reference_path_count": report.finite_interval_reference_path_count,
                "unbounded_reference_path_count": report.unbounded_reference_path_count,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "forward_outcome_count": 0,
                "performance_metric_count": 0,
                "parameter_selection_count": 0,
                "canonical_data_write_count": 0,
                "production_write_count": 0,
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
        raise service.StrongLeaderPullbackTerminalReferenceFinalReviewError(
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
