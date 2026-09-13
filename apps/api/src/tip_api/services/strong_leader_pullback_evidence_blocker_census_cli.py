"""CLI for the outcome-blind first-strategy evidence blocker census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.strong_leader_pullback_evidence_blocker_census import (
    APPROVED_DATA_ROOT,
    CONTRACT_VERSION,
    StrongLeaderPullbackEvidenceBlockerCensusError,
    build_strong_leader_pullback_evidence_blocker_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-census", required=True, type=Path)
    parser.add_argument("--admission-decision", required=True, type=Path)
    parser.add_argument("--resolution-shadow", required=True, type=Path)
    parser.add_argument("--resolution-shadow-custody-root", required=True, type=Path)
    parser.add_argument("--unresolved-census", required=True, type=Path)
    parser.add_argument("--unresolved-census-custody-root", required=True, type=Path)
    parser.add_argument("--residual-census", required=True, type=Path)
    parser.add_argument("--residual-census-custody-root", required=True, type=Path)
    parser.add_argument("--lifecycle-shadow", required=True, type=Path)
    parser.add_argument("--lifecycle-shadow-custody-root", required=True, type=Path)
    parser.add_argument(
        "--lifecycle-anchor", required=True, action="append", type=date.fromisoformat
    )
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
        result = build_strong_leader_pullback_evidence_blocker_census(
            data_root=APPROVED_DATA_ROOT,
            development_census_root=args.development_census,
            admission_decision_root=args.admission_decision,
            resolution_shadow_output_root=args.resolution_shadow,
            resolution_shadow_custody_root=args.resolution_shadow_custody_root,
            unresolved_census_output_root=args.unresolved_census,
            unresolved_census_custody_root=args.unresolved_census_custody_root,
            residual_census_output_root=args.residual_census,
            residual_census_custody_root=args.residual_census_custody_root,
            lifecycle_shadow_root=args.lifecycle_shadow,
            lifecycle_shadow_custody_root=args.lifecycle_shadow_custody_root,
            lifecycle_anchor_dates=tuple(args.lifecycle_anchor),
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=revision,
            evaluated_at=args.evaluated_at,
        )
    except (
        StrongLeaderPullbackEvidenceBlockerCensusError,
        OSError,
        RuntimeError,
        ValueError,
    ):
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "strong_leader_pullback_evidence_blocker_census_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "strategy_trigger_count": 0,
                    "forward_outcome_count": 0,
                    "performance_metric_count": 0,
                    "stable_identity_assignment_count": 0,
                    "canonical_data_write_count": 0,
                    "historical_coverage_write_count": 0,
                    "research_admission_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                    "external_request_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    manifest = result.manifest
    print(
        json.dumps(
            {
                "contract_version": manifest.contract_version,
                "record_type": "strong_leader_pullback_evidence_blocker_census_completion",
                "status": result.status,
                "implementation_revision": revision,
                "included_path_count": manifest.included_path_count,
                "action_exposure_record_count": manifest.action_exposure_record_count,
                "resolved_action_exposure_record_count": (
                    manifest.resolved_action_exposure_record_count
                ),
                "unassigned_action_candidate_exposure_record_count": (
                    manifest.unassigned_action_candidate_exposure_record_count
                ),
                "feature_action_unique_path_count": (
                    manifest.feature_action_unique_path_count
                ),
                "horizon_5_action_unique_path_count": (
                    manifest.horizon_5_action_unique_path_count
                ),
                "lifecycle_instrument_count": manifest.lifecycle_instrument_count,
                "horizon_5_lifecycle_crossing_path_count": (
                    manifest.horizon_5_lifecycle_crossing_path_count
                ),
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "strategy_trigger_count": 0,
                "forward_outcome_count": 0,
                "performance_metric_count": 0,
                "stable_identity_assignment_count": 0,
                "canonical_data_write_count": 0,
                "historical_coverage_write_count": 0,
                "research_admission_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
                "external_request_count": 0,
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
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
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
