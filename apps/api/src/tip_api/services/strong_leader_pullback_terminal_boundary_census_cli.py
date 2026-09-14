"""CLI for the Strong-Leader Pullback terminal-boundary census."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_terminal_boundary_census as service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "data-root",
        "development-census",
        "blocker-census",
        "blocker-census-custody-root",
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
        result = service.build_strong_leader_pullback_terminal_boundary_census(
            data_root=args.data_root,
            development_census_root=args.development_census,
            blocker_census_root=args.blocker_census,
            blocker_census_custody_root=args.blocker_census_custody_root,
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
                "lifecycle_instrument_count": report.lifecycle_instrument_count,
                "changed_instrument_count": report.changed_instrument_count,
                "newly_horizon_5_in_scope_instrument_count": (
                    report.newly_horizon_5_in_scope_instrument_count
                ),
                "legacy_horizon_5_crossing_instrument_count": (
                    report.legacy_horizon_5_crossing_instrument_count
                ),
                "corrected_horizon_5_crossing_instrument_count": (
                    report.corrected_horizon_5_crossing_instrument_count
                ),
                "legacy_horizon_5_crossing_path_count": (
                    report.legacy_horizon_5_crossing_path_count
                ),
                "corrected_horizon_5_crossing_path_count": (
                    report.corrected_horizon_5_crossing_path_count
                ),
                "boundary_relation_counts": report.boundary_relation_counts,
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
        raise service.StrongLeaderPullbackTerminalBoundaryCensusError(
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
