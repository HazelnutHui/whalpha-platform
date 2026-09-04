"""Network-disabled CLI for historical Identity source Apply planning."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tip_api.services.historical_identity_rebuild_profile_map import (
    read_historical_identity_rebuild_profile_map,
)
from tip_api.services.historical_identity_source_apply_plan import (
    build_historical_identity_source_apply_plan,
)
from tip_api.services.historical_universe_membership_shadow_cli import (
    _network_disabled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create one complete, inventory-bound and no-write historical "
            "Identity source Apply plan."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--profile-map", type=Path, required=True)
    parser.add_argument("--created-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--plan-path", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--session", type=date.fromisoformat, action="append")
    args = parser.parse_args(argv)

    with _network_disabled():
        profile_map = read_historical_identity_rebuild_profile_map(args.profile_map)
        evidence = build_historical_identity_source_apply_plan(
            data_root=args.data_root,
            candidate_root=args.candidate_root,
            profile_map=profile_map,
            created_at=args.created_at,
            plan_path=args.plan_path,
            workers=args.workers,
            sessions=None if args.session is None else tuple(args.session),
        )
    plan = evidence.plan
    print(
        json.dumps(
            {
                "plan_path": str(evidence.plan_path),
                "plan_sha256": evidence.plan_sha256,
                "logical_fingerprint": plan.logical_fingerprint,
                "status": plan.status,
                "session_count": plan.session_count,
                "first_session": plan.first_session.isoformat(),
                "last_session": plan.last_session.isoformat(),
                "current_profile_session_count": (
                    plan.current_profile_session_count
                ),
                "legacy_profile_session_count": (
                    plan.legacy_profile_session_count
                ),
                "record_count": plan.record_count,
                "source_request_count": plan.source_request_count,
                "source_response_bytes": plan.source_response_bytes,
                "normalized_parquet_bytes": plan.normalized_parquet_bytes,
                "manifest_bytes": plan.manifest_bytes,
                "inventory_change_file_count": (
                    plan.inventory_change_file_count
                ),
                "inventory_change_bytes": plan.inventory_change_bytes,
                "expected_current_state_fingerprint": (
                    plan.expected_current_state_fingerprint
                ),
                "candidate_inventory_fingerprint": (
                    plan.candidate_inventory_fingerprint
                ),
                "external_request_count": plan.external_request_count,
                "canonical_data_write_count": plan.canonical_data_write_count,
                "apply_authorized": plan.apply_authorized,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
