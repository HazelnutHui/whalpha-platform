"""CLI for the final outcome-blind pre-research data gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_pre_research_admission_review as service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "development-census",
        "prior-admission",
        "blocker-census",
        "blocker-census-custody-root",
        "terminal-census",
        "terminal-census-custody-root",
        "data-root",
        "canonical-action-publication",
        "adjustment-publication",
        "eod-evidence",
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
        result = service.build_strong_leader_pullback_pre_research_admission_review(
            development_census_root=args.development_census,
            prior_admission_root=args.prior_admission,
            blocker_census_root=args.blocker_census,
            blocker_census_custody_root=args.blocker_census_custody_root,
            terminal_census_root=args.terminal_census,
            terminal_census_custody_root=args.terminal_census_custody_root,
            data_root=args.data_root,
            canonical_action_publication_root=args.canonical_action_publication,
            adjustment_publication_root=args.adjustment_publication,
            eod_evidence_path=args.eod_evidence,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=_clean_revision(),
            evaluated_at=args.evaluated_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({
            "contract_version": service.CONTRACT_VERSION,
            "status": "stopped",
            "error_type": type(exc).__name__,
            "canonical_data_write_count": 0,
            "strategy_research_started": False,
            "network_request_count": 0,
        }, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 1
    report = result.report
    print(json.dumps({
        "contract_version": report.contract_version,
        "status": result.status,
        "decision_status": report.decision_status,
        "complete_cross_section_session_count": report.complete_cross_section_session_count,
        "terminal_reference_documented_instrument_count": report.terminal_reference_documented_instrument_count,
        "terminal_reference_gap_instrument_count": report.terminal_reference_gap_instrument_count,
        "blocker_codes": report.blocker_codes,
        "next_action": report.next_action,
        "report_sha256": result.report_sha256,
        "logical_fingerprint": report.logical_fingerprint,
        "historical_coverage_manifest_published": False,
        "development_authorized": False,
        "strategy_research_started": False,
        "canonical_data_write_count": 0,
        "network_request_count": 0,
    }, sort_keys=True, separators=(",", ":")))
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
        ["git", "status", "--porcelain"], check=True,
        capture_output=True, text=True,
    ).stdout
    if status:
        raise service.StrongLeaderPullbackPreResearchAdmissionReviewError(
            "repository must be clean"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
