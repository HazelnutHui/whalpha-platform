"""CLI for Strong-Leader Pullback SEC transaction candidates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_transaction_candidates import (
    StrongLeaderPullbackSecTransactionCandidatesError,
    build_strong_leader_pullback_sec_transaction_candidates,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-custody-root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-custody-root", required=True, type=Path)
    parser.add_argument("--content-census", required=True, type=Path)
    parser.add_argument("--content-census-custody-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output-custody-root", required=True, type=Path)
    parser.add_argument("--evaluated-at", required=True, type=_datetime)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("--execute is required")
    try:
        result = build_strong_leader_pullback_sec_transaction_candidates(
            plan_root=args.plan,
            plan_custody_root=args.plan_custody_root,
            source_root=args.source,
            source_custody_root=args.source_custody_root,
            content_census_root=args.content_census,
            content_census_custody_root=args.content_census_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
            implementation_revision=_clean_revision(),
            evaluated_at=args.evaluated_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "network_request_count": 0,
                    "transaction_completion_fact_count": 0,
                    "lifecycle_fact_count": 0,
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
                "completion_status": report.completion_status,
                "implementation_revision": report.implementation_revision,
                "evaluated_at": report.evaluated_at.isoformat(),
                "transaction_document_count": report.transaction_document_count,
                "instrument_count": report.instrument_count,
                "form_counts": report.form_counts,
                "structure_state_counts": report.structure_state_counts,
                "field_candidate_document_counts": (
                    report.field_candidate_document_counts
                ),
                "field_candidate_occurrence_counts": (
                    report.field_candidate_occurrence_counts
                ),
                "document_with_field_candidate_count": (
                    report.document_with_field_candidate_count
                ),
                "referenced_completion_exhibit_count": (
                    report.referenced_completion_exhibit_count
                ),
                "report_sha256": result.report_sha256,
                "logical_fingerprint": report.logical_fingerprint,
                "network_request_count": 0,
                "transaction_completion_fact_count": 0,
                "lifecycle_fact_count": 0,
                "terminal_outcome_count": 0,
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
        raise argparse.ArgumentTypeError("timestamp must be an ISO-8601 UTC value") from exc


def _clean_revision() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
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
