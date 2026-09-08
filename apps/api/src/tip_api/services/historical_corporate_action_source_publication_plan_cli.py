"""Network-disabled CLI for a bounded corporate-action publication plan."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.services.historical_corporate_action_source_publication_plan import (
    build_corporate_action_source_publication_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a no-write bounded corporate-action source plan."
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--resolution-shadow-root", required=True, type=Path)
    parser.add_argument("--split-repeat-diff-root", required=True, type=Path)
    parser.add_argument("--dividend-repeat-diff-root", required=True, type=Path)
    parser.add_argument("--created-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--plan-path", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            source_revision = _clean_revision()
            evidence = build_corporate_action_source_publication_plan(
                data_root=args.data_root,
                resolution_shadow_root=args.resolution_shadow_root,
                split_repeat_diff_root=args.split_repeat_diff_root,
                dividend_repeat_diff_root=args.dividend_repeat_diff_root,
                source_revision=source_revision,
                created_at=args.created_at,
                plan_path=args.plan_path,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "corporate_action_source_plan_rejected",
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
                "source_revision": plan.publication.source_revision,
                "expected_current_state_fingerprint": (
                    plan.expected_current_state_fingerprint
                ),
                "start_date": plan.publication.start_date.isoformat(),
                "end_date": plan.publication.end_date.isoformat(),
                "source_record_count": plan.publication.source_record_count,
                "resolved_record_count": plan.publication.resolved_record_count,
                "quarantined_record_count": (
                    plan.publication.quarantined_record_count
                ),
                "target_partition_paths": plan.target_partition_paths,
                "target_publication_partition": (
                    plan.target_publication_partition
                ),
                "inventory_change_file_count": plan.inventory_change_file_count,
                "inventory_change_bytes": plan.inventory_change_bytes,
                "apply_authorized": plan.apply_authorized,
                "canonical_corporate_action_authorized": (
                    plan.canonical_corporate_action_authorized
                ),
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


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during corporate-action planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during corporate-action planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during corporate-action planning")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


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
