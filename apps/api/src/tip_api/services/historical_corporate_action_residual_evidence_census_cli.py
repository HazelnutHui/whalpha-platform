"""CLI for the assignment-free corporate-action residual evidence census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_corporate_action_residual_evidence_census import (
    APPROVED_DATA_ROOT,
    CONTRACT_VERSION,
    HistoricalCorporateActionResidualEvidenceCensusError,
    build_historical_corporate_action_residual_evidence_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-shadow", required=True, type=Path)
    parser.add_argument("--resolution-shadow-custody-root", required=True, type=Path)
    parser.add_argument("--unresolved-census", required=True, type=Path)
    parser.add_argument("--unresolved-census-custody-root", required=True, type=Path)
    parser.add_argument("--lifecycle-shadow", required=True, type=Path)
    parser.add_argument("--lifecycle-shadow-custody-root", required=True, type=Path)
    parser.add_argument(
        "--lifecycle-anchor",
        required=True,
        action="append",
        type=date.fromisoformat,
    )
    parser.add_argument("--finra-custody-root", required=True, type=Path)
    parser.add_argument("--finra-range-start", required=True, type=date.fromisoformat)
    parser.add_argument("--finra-range-end", required=True, type=date.fromisoformat)
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
        result = build_historical_corporate_action_residual_evidence_census(
            data_root=APPROVED_DATA_ROOT,
            resolution_shadow_output_root=args.resolution_shadow,
            resolution_shadow_custody_root=args.resolution_shadow_custody_root,
            unresolved_census_output_root=args.unresolved_census,
            unresolved_census_custody_root=args.unresolved_census_custody_root,
            lifecycle_shadow_root=args.lifecycle_shadow,
            lifecycle_shadow_custody_root=args.lifecycle_shadow_custody_root,
            lifecycle_anchor_dates=tuple(args.lifecycle_anchor),
            finra_custody_root=args.finra_custody_root,
            finra_range_start=args.finra_range_start,
            finra_range_end=args.finra_range_end,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=revision,
            evaluated_at=args.evaluated_at,
        )
    except (
        HistoricalCorporateActionResidualEvidenceCensusError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        del exc
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "historical_corporate_action_residual_evidence_census_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "stable_identity_assignment_count": 0,
                    "canonical_data_write_count": 0,
                    "historical_coverage_write_count": 0,
                    "analytics_execution_count": 0,
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
                "record_type": "historical_corporate_action_residual_evidence_census_completion",
                "status": result.status,
                "implementation_revision": revision,
                "residual_record_count": manifest.residual_record_count,
                "residual_record_candidate_relation_counts": (
                    manifest.residual_record_candidate_relation_counts
                ),
                "inactive_source_state_counts": manifest.inactive_source_state_counts,
                "finra_exact_date_symbol_record_count": (
                    manifest.finra_exact_date_symbol_record_count
                ),
                "finra_exact_numeric_record_count": (
                    manifest.finra_exact_numeric_record_count
                ),
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "stable_identity_assignment_count": 0,
                "canonical_data_write_count": 0,
                "historical_coverage_write_count": 0,
                "analytics_execution_count": 0,
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
        raise HistoricalCorporateActionResidualEvidenceCensusError(
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
