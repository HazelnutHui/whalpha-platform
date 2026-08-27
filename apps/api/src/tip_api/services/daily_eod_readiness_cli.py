"""Network-free administrator CLI for one daily EOD readiness decision."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date, datetime

from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    ACQUISITION_ACTIONS,
    AcquisitionAttempt,
    AttemptOutcome,
    DailyEodReadinessError,
    ReadinessNextAction,
    plan_daily_eod_readiness,
)
from tip_api.services.market_calendar import MarketCalendarError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan one network-free daily EOD acquisition-readiness decision."
    )
    parser.add_argument("--checked-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--target-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--latest-canonical-session", required=True, type=date.fromisoformat
    )
    parser.add_argument(
        "--acquisition-action",
        required=True,
        choices=tuple(sorted(item.value for item in ACQUISITION_ACTIONS)),
    )
    parser.add_argument(
        "--attempt",
        action="append",
        default=[],
        metavar="SEQUENCE|OBSERVED_AT|OUTCOME[|RETRY_AFTER_SECONDS]",
    )
    args = parser.parse_args(argv)
    try:
        attempts = tuple(_parse_attempt(value) for value in args.attempt)
        with _offline_socket_guard():
            plan = plan_daily_eod_readiness(
                checked_at=args.checked_at,
                target_session=args.target_session,
                latest_canonical_session=args.latest_canonical_session,
                acquisition_action=NextAction(args.acquisition_action),
                attempts=attempts,
            )
    except (DailyEodReadinessError, MarketCalendarError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_readiness_rejected",
                    "error_type": type(exc).__name__,
                    "scheduler_enabled": False,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(plan.as_dict(), sort_keys=True, separators=(",", ":")))
    return (
        1
        if plan.alert_required
        or getattr(plan, "next_action", None)
        is ReadinessNextAction.OPERATOR_DIAGNOSIS
        else 0
    )


def _parse_attempt(value: str) -> AcquisitionAttempt:
    parts = value.split("|")
    if len(parts) not in {3, 4}:
        raise DailyEodReadinessError("attempt argument is malformed")
    try:
        retry_after = None if len(parts) == 3 else int(parts[3])
        return AcquisitionAttempt(
            sequence=int(parts[0]),
            observed_at=datetime.fromisoformat(parts[1]),
            outcome=AttemptOutcome(parts[2]),
            retry_after_seconds=retry_after,
        )
    except (TypeError, ValueError) as exc:
        raise DailyEodReadinessError("attempt argument is malformed") from exc


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during daily EOD readiness planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during daily EOD readiness planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during daily EOD readiness planning")

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
