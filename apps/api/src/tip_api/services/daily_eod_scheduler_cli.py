"""Credential-free CLI for reviewing one default-off scheduler wake."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.persistence.eod_read import EodDatasetUnavailableError
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.daily_eod_scheduler import (
    DailyEodSchedulerError,
    plan_daily_eod_scheduler_wake,
)
from tip_api.services.market_calendar import MarketCalendarError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review one network-free, default-off daily scheduler wake."
    )
    parser.add_argument("--checked-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--review-enabled-candidate", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root.is_absolute():
        parser.error("--data-root must be absolute")
    try:
        with _offline_socket_guard():
            repository = CanonicalEodReadRepository(args.data_root)
            sessions = repository.list_session_index()
            if sessions:
                latest_integrity = repository.inspect_session(sessions[-1])
                if latest_integrity.session_date != sessions[-1]:
                    raise DailyEodSchedulerError(
                        "latest canonical EOD does not match its completion index"
                    )
            plan = plan_daily_eod_scheduler_wake(
                checked_at=args.checked_at,
                completed_sessions=sessions,
                review_enabled_candidate=args.review_enabled_candidate,
            )
    except (
        DailyEodSchedulerError,
        EodDatasetUnavailableError,
        MarketCalendarError,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_scheduler_wake_rejected",
                    "error_type": type(exc).__name__,
                    "scheduler_candidate_enabled": False,
                    "scheduler_installed": False,
                    "coordinator_invocation_count": 0,
                    "credential_access_count": 0,
                    "external_request_count": 0,
                    "filesystem_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(plan.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during scheduler planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during scheduler planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during scheduler planning")

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
