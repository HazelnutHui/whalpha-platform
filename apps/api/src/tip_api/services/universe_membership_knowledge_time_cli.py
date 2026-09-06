"""Network-disabled CLI for one Membership knowledge-time assessment."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.universe_membership_knowledge_time import (
    assess_universe_membership_knowledge_time,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify one Membership partition for next-open signal use."
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--membership-root", required=True, type=Path)
    parser.add_argument("--membership-partition", required=True, type=Path)
    parser.add_argument("--provider", default=MASSIVE_PROVIDER_ID)
    parser.add_argument("--assessed-at", required=True, type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            report = assess_universe_membership_knowledge_time(
                data_root=args.data_root,
                membership_root=args.membership_root,
                membership_partition_path=args.membership_partition,
                provider=args.provider,
                assessed_at=args.assessed_at,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "membership_knowledge_time_assessment_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "assessed",
                **report.model_dump(mode="json"),
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
            raise RuntimeError("network is prohibited during timing assessment")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during timing assessment")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during timing assessment")

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
