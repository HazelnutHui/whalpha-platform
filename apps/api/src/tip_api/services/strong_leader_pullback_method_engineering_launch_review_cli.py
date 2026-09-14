"""CLI for the first-strategy outcome-blind method-engineering boundary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_method_engineering_launch_review as service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "pre-research-review",
        "pre-research-review-custody-root",
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
        result = (
            service.build_strong_leader_pullback_method_engineering_launch_review(
                pre_research_review_root=args.pre_research_review,
                pre_research_review_custody_root=(
                    args.pre_research_review_custody_root
                ),
                output_root=args.output_root,
                output_custody_root=args.output_custody_root,
                implementation_revision=_clean_revision(),
                reviewed_at=args.reviewed_at,
            )
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({
            "contract_version": service.CONTRACT_VERSION,
            "status": "stopped",
            "error_type": type(exc).__name__,
            "method_engineering_authorized": False,
            "true_return_labels_authorized": False,
            "canonical_data_write_count": 0,
            "network_request_count": 0,
        }, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 1
    report = result.report
    print(json.dumps({
        "contract_version": report.contract_version,
        "status": result.status,
        "decision_status": report.decision_status,
        "formal_data_gate_status": report.formal_data_gate_status,
        "signal_session_count": report.signal_session_count,
        "included_path_count": report.included_path_count,
        "unresolved_formal_blocker_codes": report.unresolved_formal_blocker_codes,
        "next_action": report.next_action,
        "method_engineering_authorized": True,
        "true_return_labels_authorized": False,
        "performance_claims_authorized": False,
        "report_sha256": result.report_sha256,
        "logical_fingerprint": report.logical_fingerprint,
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
        raise service.StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "repository must be clean"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
