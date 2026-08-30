"""Network-prohibited CLI for the current blocked historical-pilot baseline."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tip_api.services.current_historical_pilot_baseline import (
    CurrentHistoricalPilotBaselineError,
    assess_current_historical_pilot_baseline,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an exact current historical-pilot review without requesting "
            "data or granting authority."
        )
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument(
        "--reviewed-at",
        required=True,
        type=_datetime,
        help="Exact timezone-aware ISO-8601 review time.",
    )
    args = parser.parse_args(argv)
    try:
        with _offline_socket_guard():
            report = assess_current_historical_pilot_baseline(
                data_root=args.data_root,
                repository_root=args.repository_root,
                reviewed_at=args.reviewed_at,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "current_historical_pilot_baseline_rejected",
                    "error_type": type(exc).__name__,
                    "required_user_acknowledgement": None,
                    "acquisition_authorized": False,
                    "apply_authorized": False,
                    "publication_authorized": False,
                    "deployment_authorized": False,
                    "scheduler_authorized": False,
                    "external_request_count": 0,
                    "data_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(report.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


def _datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("reviewed-at must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("reviewed-at must include a timezone")
    return parsed


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during pilot baseline review")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during pilot baseline review")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during pilot baseline review")

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
