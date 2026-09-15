"""CLI for the source-driven Strong-Leader Pullback V2 admission review."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_research_admission_v2_review as service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "development-census-root",
        "diagnostics-root",
        "diagnostics-custody-root",
        "corporate-action-source-root",
        "prior-split-source-root",
        "split-resolution-shadow-root",
        "split-resolution-shadow-custody-root",
        "canonical-data-root",
        "canonical-split-action-root",
        "canonical-split-adjustment-root",
        "final-terminal-root",
        "final-terminal-custody-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--reviewed-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = service.publish_strong_leader_pullback_research_admission_v2_review(
            development_census_root=args.development_census_root,
            diagnostics_root=args.diagnostics_root,
            diagnostics_custody_root=args.diagnostics_custody_root,
            corporate_action_source_root=args.corporate_action_source_root,
            prior_split_source_root=args.prior_split_source_root,
            split_resolution_shadow_root=args.split_resolution_shadow_root,
            split_resolution_shadow_custody_root=(
                args.split_resolution_shadow_custody_root
            ),
            canonical_data_root=args.canonical_data_root,
            canonical_split_action_root=args.canonical_split_action_root,
            canonical_split_adjustment_root=args.canonical_split_adjustment_root,
            final_terminal_root=args.final_terminal_root,
            final_terminal_custody_root=args.final_terminal_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            reviewed_at=args.reviewed_at,
            implementation_revision=_clean_revision(),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "contains_forward_outcomes": False,
                    "contains_performance_metrics": False,
                    "parameter_selection_count": 0,
                    "network_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    report = result.report
    print(
        json.dumps(
            {
                "status": result.status,
                "decision_status": report.decision.status,
                "complete_feature_session_count": (
                    report.feature_evidence.complete_cross_section_session_count
                ),
                "warmup_session_count": (
                    report.feature_evidence.feature_window_warmup_session_count
                ),
                "excluded_feature_session_count": (
                    report.feature_evidence.excluded_session_count
                ),
                "terminal_exact_path_count": (
                    report.terminal_evidence.exact_terminal_reference_path_count
                ),
                "terminal_interval_path_count": (
                    report.terminal_evidence.interval_terminal_reference_path_count
                ),
                "terminal_unbounded_path_count": (
                    report.terminal_evidence.unbounded_terminal_reference_path_count
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "development_label_construction_authorized": (
                    report.decision.development_label_construction_authorized
                ),
                "validation_authorized": False,
                "holdout_access_authorized": False,
                "performance_claim_authorized": False,
                "candidate_activation_authorized": False,
                "network_request_count": 0,
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
        result = normalize_utc_datetime(datetime.fromisoformat(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "timestamp must be an ISO-8601 UTC value"
        ) from exc
    return result


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise service.StrongLeaderPullbackResearchAdmissionV2ReviewError(
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
