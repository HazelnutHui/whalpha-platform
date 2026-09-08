"""Network-disabled CLI for canonical split-action publication planning."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from tip_api.services.canonical_split_action_publication_plan import (
    build_canonical_split_action_publication_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a no-write canonical split-action publication plan."
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--split-candidate-root", required=True, type=Path)
    parser.add_argument("--publication-candidate-root", required=True, type=Path)
    parser.add_argument("--plan-path", required=True, type=Path)
    parser.add_argument("--created-at", required=True, type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    try:
        evidence = build_canonical_split_action_publication_plan(
            data_root=args.data_root,
            split_candidate_root=args.split_candidate_root,
            publication_candidate_root=args.publication_candidate_root,
            plan_path=args.plan_path,
            source_revision=_clean_revision(),
            created_at=args.created_at,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "canonical_split_action_plan_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    plan = evidence.plan
    print(
        json.dumps(
            {
                "status": plan.status,
                "plan_path": str(evidence.plan_path),
                "plan_sha256": evidence.plan_sha256,
                "plan_logical_fingerprint": plan.logical_fingerprint,
                "source_revision": plan.source_revision,
                "expected_current_state_fingerprint": (
                    plan.expected_current_state_fingerprint
                ),
                "target_publication_root": plan.target_publication_root,
                "action_record_count": plan.publication.action_record_count,
                "active_action_record_count": (
                    plan.publication.active_action_record_count
                ),
                "quarantined_action_record_count": (
                    plan.publication.quarantined_action_record_count
                ),
                "possible_impact_instrument_count": (
                    plan.publication.possible_impact_instrument_count
                ),
                "inventory_change_file_count": plan.inventory_change_file_count,
                "inventory_change_bytes": plan.inventory_change_bytes,
                "apply_authorized": plan.apply_authorized,
                "adjustment_ledger_authorized": (
                    plan.adjustment_ledger_authorized
                ),
                "historical_coverage_authorized": (
                    plan.historical_coverage_authorized
                ),
                "research_performance_authorized": (
                    plan.research_performance_authorized
                ),
                "external_request_count": 0,
                "canonical_data_write_count": 0,
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
        raise RuntimeError("repository must be clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
