"""CLI for the corrected terminal-population SEC source plan."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as service,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "terminal-gap-v2",
        "terminal-gap-v2-custody-root",
        "lifecycle-shadow",
        "lifecycle-shadow-custody-root",
        "submissions-package",
        "submissions-custody-root",
        "submissions-census-root",
        "output-root",
        "output-custody-root",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument(
        "--lifecycle-anchor", required=True, action="append", type=date.fromisoformat
    )
    parser.add_argument("--source-snapshot-date", required=True, type=date.fromisoformat)
    parser.add_argument("--range-start", required=True, type=date.fromisoformat)
    parser.add_argument("--range-end", required=True, type=date.fromisoformat)
    parser.add_argument("--planned-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = service.build_strong_leader_pullback_terminal_population_sec_source_plan(
            terminal_gap_v2_root=args.terminal_gap_v2,
            terminal_gap_v2_custody_root=args.terminal_gap_v2_custody_root,
            lifecycle_shadow_root=args.lifecycle_shadow,
            lifecycle_shadow_custody_root=args.lifecycle_shadow_custody_root,
            lifecycle_anchor_dates=tuple(args.lifecycle_anchor),
            submissions_package_path=args.submissions_package,
            submissions_custody_root=args.submissions_custody_root,
            submissions_census_root=args.submissions_census_root,
            source_snapshot_date=args.source_snapshot_date,
            range_start=args.range_start,
            range_end=args.range_end,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=_clean_revision(),
            planned_at=args.planned_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": service.CONTRACT_VERSION,
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "credential_read_count": 0,
                    "document_write_count": 0,
                    "terminal_outcome_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
                    "publication_count": 0,
                    "deployment_count": 0,
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
                "planned_at": report.planned_at.isoformat(),
                "newly_in_scope_case_count": report.newly_in_scope_case_count,
                "planned_request_count": report.planned_request_count,
                "form_counts": report.form_counts,
                "relation_counts": report.relation_counts,
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "external_request_count": 0,
                "credential_read_count": 0,
                "document_write_count": 0,
                "terminal_outcome_count": 0,
                "canonical_data_write_count": 0,
                "research_admission_count": 0,
                "publication_count": 0,
                "deployment_count": 0,
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
        raise service.StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
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
