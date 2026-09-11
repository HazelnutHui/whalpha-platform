"""Operator CLI for exact Reconciled EOD Edition planning and Apply."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from tip_api.services.reconciled_eod_edition_apply import (
    apply_approved_reconciled_eod_edition_plan,
)
from tip_api.services.reconciled_eod_edition_apply_plan import (
    build_reconciled_eod_edition_apply_plan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or Apply one complete Reconciled EOD Edition",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("--data-root", type=Path, required=True)
    plan.add_argument("--candidate-root", type=Path, required=True)
    plan.add_argument("--plan-path", type=Path, required=True)
    plan.add_argument("--edition-id", required=True)
    plan.add_argument("--planner-revision", required=True)
    plan.add_argument("--created-at", type=datetime.fromisoformat, required=True)

    apply = subparsers.add_parser("apply")
    apply.add_argument("--data-root", type=Path, required=True)
    apply.add_argument("--plan-path", type=Path, required=True)
    apply.add_argument("--approved-plan-sha256", required=True)
    apply.add_argument("--expected-plan-logical-fingerprint", required=True)
    apply.add_argument("--expected-current-state-fingerprint", required=True)
    apply.add_argument("--verify-then-complete", action="store_true")
    apply.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "plan":
        evidence = build_reconciled_eod_edition_apply_plan(
            data_root=args.data_root,
            candidate_root=args.candidate_root,
            plan_path=args.plan_path,
            edition_id=args.edition_id,
            planner_revision=args.planner_revision,
            created_at=args.created_at,
        )
        output = {
            "status": evidence.plan.status,
            "plan_path": str(evidence.plan_path),
            "plan_sha256": evidence.plan_sha256,
            "plan_logical_fingerprint": evidence.plan.logical_fingerprint,
            "expected_current_state_fingerprint": (
                evidence.plan.expected_current_state_fingerprint
            ),
            "edition_id": evidence.plan.edition_id,
            "candidate_session_count": evidence.plan.candidate_session_count,
            "candidate_record_count": evidence.plan.candidate_record_count,
            "inventory_change_file_count": (
                evidence.plan.inventory_change_file_count
            ),
            "inventory_change_bytes": evidence.plan.inventory_change_bytes,
            "apply_authorized": evidence.plan.apply_authorized,
            "production_authority": evidence.plan.production_authority,
            "research_performance_authorized": (
                evidence.plan.research_performance_authorized
            ),
        }
    else:
        if not args.execute:
            parser.error("Apply requires --execute")
        result = apply_approved_reconciled_eod_edition_plan(
            plan_path=args.plan_path,
            approved_plan_sha256=args.approved_plan_sha256,
            expected_plan_logical_fingerprint=(
                args.expected_plan_logical_fingerprint
            ),
            expected_current_state_fingerprint=(
                args.expected_current_state_fingerprint
            ),
            data_root=args.data_root,
            verify_then_complete=args.verify_then_complete,
        )
        output = {
            "status": result.status,
            "plan_sha256": result.plan_sha256,
            "plan_logical_fingerprint": result.plan_logical_fingerprint,
            "edition_id": result.edition_id,
            "interval_manifest_fingerprint": (
                result.interval_manifest_fingerprint
            ),
            "edition_published": result.edition_published,
            "edition_reused": result.edition_reused,
            "published_file_count": result.published_file_count,
            "published_bytes": result.published_bytes,
            "formal_reread_session_count": result.formal_reread_session_count,
            "formal_reread_record_count": result.formal_reread_record_count,
            "external_request_count": result.external_request_count,
            "production_authority": result.production_authority,
            "research_performance_authorized": (
                result.research_performance_authorized
            ),
        }
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
