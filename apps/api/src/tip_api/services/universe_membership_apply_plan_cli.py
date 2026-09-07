"""Network-disabled CLI for a no-write Membership Apply plan."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.universe_membership_apply_plan import (
    build_universe_membership_apply_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a no-write signal-eligible Membership Apply plan."
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--candidate-membership-partition", required=True, type=Path)
    parser.add_argument("--provider", default=MASSIVE_PROVIDER_ID)
    parser.add_argument("--assessed-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--created-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--plan-path", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            evidence = build_universe_membership_apply_plan(
                data_root=args.data_root,
                candidate_root=args.candidate_root,
                candidate_membership_partition=(
                    args.candidate_membership_partition
                ),
                provider=args.provider,
                assessed_at=args.assessed_at,
                created_at=args.created_at,
                plan_path=args.plan_path,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "universe_membership_apply_plan_rejected",
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
                "expected_current_state_fingerprint": (
                    plan.expected_current_state_fingerprint
                ),
                "session_date": plan.publication.session_date.isoformat(),
                "membership_logical_fingerprint": (
                    plan.publication.membership_logical_fingerprint
                ),
                "knowledge_time_assessment_fingerprint": (
                    plan.publication.knowledge_time_assessment.logical_fingerprint
                ),
                "point_in_time_eligibility": (
                    plan.publication.point_in_time_eligibility.value
                ),
                "inventory_change_file_count": plan.inventory_change_file_count,
                "inventory_change_bytes": plan.inventory_change_bytes,
                "target_membership_partition": plan.target_membership_partition,
                "target_publication_partition": plan.target_publication_partition,
                "apply_authorized": plan.apply_authorized,
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


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during Membership planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during Membership planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during Membership planning")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
