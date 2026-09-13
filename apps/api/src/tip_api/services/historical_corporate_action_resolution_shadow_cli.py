"""CLI for the disconnected corporate-action resolution shadow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_corporate_action_resolution_shadow import (
    APPROVED_DATA_ROOT,
    CONTRACT_VERSION,
    HistoricalCorporateActionResolutionShadowError,
    build_historical_corporate_action_resolution_shadow,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--split-source-package", required=True, type=Path)
    parser.add_argument("--dividend-source-package", required=True, type=Path)
    parser.add_argument(
        "--identity-evidence", required=True, type=Path, action="append"
    )
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--source-custody-root", type=Path)
    parser.add_argument("--output-custody-root", type=Path)
    parser.add_argument(
        "--materialized-at",
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
        result = build_historical_corporate_action_resolution_shadow(
            data_root=APPROVED_DATA_ROOT,
            split_source_package_path=args.split_source_package,
            dividend_source_package_path=args.dividend_source_package,
            identity_evidence_path=(
                args.identity_evidence[0]
                if len(args.identity_evidence) == 1
                and args.output_custody_root is None
                else None
            ),
            identity_evidence_paths=(
                tuple(args.identity_evidence)
                if len(args.identity_evidence) > 1
                or args.output_custody_root is not None
                else ()
            ),
            output_root=args.output_root,
            start_date=args.start_date,
            end_date=args.end_date,
            materialized_at=args.materialized_at,
            source_custody_root=args.source_custody_root,
            output_custody_root=args.output_custody_root,
        )
    except (
        HistoricalCorporateActionResolutionShadowError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "corporate_action_resolution_shadow_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "adjustment_ledger_write_count": 0,
                    "analytics_execution_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
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
                "contract_version": getattr(
                    manifest, "contract_version", CONTRACT_VERSION
                ),
                "record_type": "corporate_action_resolution_shadow_completion",
                "status": result.status,
                "implementation_revision": revision,
                "start_date": manifest.start_date.isoformat(),
                "end_date": manifest.end_date.isoformat(),
                "source_record_count": manifest.source_record_count,
                "mapped_record_count": manifest.mapped_record_count,
                "unrepresentable_source_record_count": (
                    manifest.unrepresentable_source_record_count
                ),
                "unrepresentable_reason_counts": (
                    manifest.unrepresentable_reason_counts
                ),
                "source_mapping_one_to_one": manifest.source_mapping_one_to_one,
                "source_accounting_one_to_one": (
                    manifest.source_accounting_one_to_one
                ),
                "identity_session_available_record_count": (
                    manifest.identity_session_available_record_count
                ),
                "identity_session_unavailable_record_count": (
                    manifest.identity_session_unavailable_record_count
                ),
                "resolution_status_counts": manifest.resolution_status_counts,
                "record_status_counts": manifest.record_status_counts,
                "action_type_counts": manifest.action_type_counts,
                "quality_flag_counts": manifest.quality_flag_counts,
                "artifact_count": len(manifest.artifacts),
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "point_in_time_eligibility": manifest.point_in_time_eligibility,
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "adjustment_ledger_write_count": 0,
                "analytics_execution_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
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
        raise HistoricalCorporateActionResolutionShadowError(
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
