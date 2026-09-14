"""CLI for the corrected terminal-population listed reference."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import (
    strong_leader_pullback_terminal_population_listed_reference as service,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "payoff-policy",
        "payoff-policy-custody-root",
        "core-adjudication",
        "core-adjudication-custody-root",
        "cessation",
        "cessation-custody-root",
        "submissions-package",
        "submissions-custody-root",
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
        result = service.build_strong_leader_pullback_terminal_population_listed_reference(
            payoff_policy_root=args.payoff_policy,
            payoff_policy_custody_root=args.payoff_policy_custody_root,
            core_adjudication_root=args.core_adjudication,
            core_adjudication_custody_root=args.core_adjudication_custody_root,
            cessation_root=args.cessation,
            cessation_custody_root=args.cessation_custody_root,
            submissions_package_root=args.submissions_package,
            submissions_custody_root=args.submissions_custody_root,
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
                    "contract_version": service.CONTRACT_VERSION,
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "network_request_count": 0,
                    "terminal_reference_case_count": 0,
                    "canonical_terminal_outcome_count": 0,
                    "canonical_data_write_count": 0,
                    "research_admission_count": 0,
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
                "implementation_revision": report.implementation_revision,
                "identity_resolution_state": report.identity.resolution_state,
                "consideration_instrument_id": str(
                    report.identity.assigned_consideration_instrument_id
                ),
                "consideration_close_usd": report.consideration_close_usd,
                "primary_reference_alternative": report.primary_reference_alternative,
                "primary_gross_reference_value_usd": (
                    report.primary_gross_reference_value_usd
                ),
                "sensitivity_min_gross_reference_value_usd": (
                    report.sensitivity_min_gross_reference_value_usd
                ),
                "sensitivity_max_gross_reference_value_usd": (
                    report.sensitivity_max_gross_reference_value_usd
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "canonical_terminal_outcome_count": 0,
                "canonical_data_write_count": 0,
                "research_admission_count": 0,
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
        raise service.StrongLeaderPullbackTerminalPopulationListedReferenceError(
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
