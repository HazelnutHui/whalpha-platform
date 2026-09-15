"""CLI for the disconnected split-adjustment candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_split_adjustment_candidate import (
    APPROVED_DATA_ROOT,
    CONTRACT_VERSION,
    HistoricalSplitAdjustmentCandidateError,
    build_historical_split_adjustment_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-shadow", required=True, type=Path)
    parser.add_argument("--resolution-shadow-custody-root", type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--basis-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--calculated-at",
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
        result = build_historical_split_adjustment_candidate(
            data_root=APPROVED_DATA_ROOT,
            resolution_shadow_output_root=args.resolution_shadow,
            resolution_shadow_custody_root=args.resolution_shadow_custody_root,
            output_root=args.output_root,
            basis_session=args.basis_session,
            calculated_at=args.calculated_at,
        )
    except (
        HistoricalSplitAdjustmentCandidateError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "record_type": "historical_split_adjustment_candidate_stop",
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
    candidate = result.candidate
    print(
        json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "record_type": "historical_split_adjustment_candidate_completion",
                "status": result.status,
                "implementation_revision": revision,
                "basis_session": candidate.basis_session.isoformat(),
                "split_source_record_count": candidate.split_source_record_count,
                "resolved_split_source_record_count": (
                    candidate.resolved_split_source_record_count
                ),
                "unresolved_split_source_record_count": (
                    candidate.unresolved_split_source_record_count
                ),
                "resolved_event_group_count": candidate.resolved_event_group_count,
                "multiple_same_date_event_group_count": (
                    candidate.multiple_same_date_event_group_count
                ),
                "possible_impact_instrument_count": (
                    candidate.possible_impact_instrument_count
                ),
                "file_sha256": result.file_sha256,
                "logical_fingerprint": candidate.logical_fingerprint,
                "total_return_adjustment_status": (
                    candidate.total_return_adjustment_status
                ),
                "ledger_projection_status": candidate.ledger_projection_status,
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
        raise HistoricalSplitAdjustmentCandidateError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
