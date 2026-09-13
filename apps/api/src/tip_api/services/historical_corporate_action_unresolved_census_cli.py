"""CLI for the assignment-free unresolved corporate-action census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.services.historical_corporate_action_unresolved_census import (
    APPROVED_DATA_ROOT,
    CONTRACT_VERSION,
    DEFAULT_HISTORY_WORKERS,
    HistoricalCorporateActionUnresolvedCensusError,
    build_historical_corporate_action_unresolved_census,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-shadow", required=True, type=Path)
    parser.add_argument("--resolution-shadow-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument(
        "--evaluated-at",
        required=True,
        type=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")),
    )
    parser.add_argument(
        "--process-count", type=int, default=DEFAULT_HISTORY_WORKERS
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    revision: str | None = None
    try:
        revision = _clean_revision()
        result = build_historical_corporate_action_unresolved_census(
            data_root=APPROVED_DATA_ROOT,
            resolution_shadow_output_root=args.resolution_shadow,
            resolution_shadow_custody_root=args.resolution_shadow_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=revision,
            evaluated_at=args.evaluated_at,
            max_workers=args.process_count,
        )
    except (
        HistoricalCorporateActionUnresolvedCensusError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "historical_corporate_action_unresolved_census_stop",
                    "status": "stopped",
                    "implementation_revision": revision,
                    "error_type": type(exc).__name__,
                    "stable_identity_assignment_count": 0,
                    "canonical_data_write_count": 0,
                    "adjustment_ledger_write_count": 0,
                    "historical_coverage_write_count": 0,
                    "analytics_execution_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
                    "scheduler_change_count": 0,
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
                "record_type": "historical_corporate_action_unresolved_census_completion",
                "status": result.status,
                "implementation_revision": revision,
                "unresolved_typed_record_count": manifest.unresolved_typed_record_count,
                "unrepresentable_source_record_count": (
                    manifest.unrepresentable_source_record_count
                ),
                "unresolved_unique_ticker_count": (
                    manifest.unresolved_unique_ticker_count
                ),
                "ticker_classification_counts": manifest.ticker_classification_counts,
                "source_record_classification_counts": (
                    manifest.source_record_classification_counts
                ),
                "candidate_relation_count": manifest.candidate_relation_count,
                "distinct_candidate_instrument_count": (
                    manifest.distinct_candidate_instrument_count
                ),
                "identity_session_count": manifest.identity_session_count,
                "process_count": manifest.process_count,
                "manifest_sha256": result.manifest_sha256,
                "logical_fingerprint": manifest.logical_fingerprint,
                "stable_identity_assignment_count": 0,
                "canonical_data_write_count": 0,
                "adjustment_ledger_write_count": 0,
                "historical_coverage_write_count": 0,
                "analytics_execution_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
                "scheduler_change_count": 0,
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
        raise HistoricalCorporateActionUnresolvedCensusError(
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
