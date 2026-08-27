"""Network-prohibited CLI for daily EOD provider-attempt custody."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from tip_api.providers.massive.same_day_catchup import SameDayCatchupError
from tip_api.services.daily_eod_acquisition_custody import (
    DailyEodAcquisitionConfig,
    DailyEodAcquisitionCustodyError,
    record_acquisition_outcome,
    recover_acquisition_attempt,
    reserve_acquisition_attempt,
)
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import ACQUISITION_ACTIONS, AttemptOutcome
from tip_api.services.daily_eod_run_journal import DailyEodRunJournalError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reserve, record, or recover one provider fetch without executing it."
    )
    parser.add_argument("--target-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--latest-canonical-session", required=True, type=date.fromisoformat
    )
    parser.add_argument(
        "--acquisition-action",
        required=True,
        choices=tuple(sorted(item.value for item in ACQUISITION_ACTIONS)),
    )
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reserve", action="store_true")
    mode.add_argument(
        "--record-outcome",
        choices=tuple(item.value for item in AttemptOutcome),
    )
    mode.add_argument("--recover-incomplete", action="store_true")
    parser.add_argument("--checked-at", type=datetime.fromisoformat)
    parser.add_argument("--expected-readiness-fingerprint")
    parser.add_argument("--retry-after-seconds", type=int)
    args = parser.parse_args(argv)
    if not args.package.is_absolute() or not args.run_root.is_absolute():
        parser.error("--package and --run-root must be absolute")
    if args.reserve:
        if args.checked_at is None or not _is_fingerprint(
            args.expected_readiness_fingerprint
        ):
            parser.error(
                "--reserve requires --checked-at and --expected-readiness-fingerprint"
            )
        if args.retry_after_seconds is not None:
            parser.error("--retry-after-seconds is invalid with --reserve")
    elif args.record_outcome is not None:
        if args.checked_at is not None or args.expected_readiness_fingerprint is not None:
            parser.error("readiness arguments are valid only with --reserve")
    elif any(
        value is not None
        for value in (
            args.checked_at,
            args.expected_readiness_fingerprint,
            args.retry_after_seconds,
        )
    ):
        parser.error("recovery accepts no readiness or retry arguments")
    config = DailyEodAcquisitionConfig(
        target_session=args.target_session,
        latest_canonical_session=args.latest_canonical_session,
        acquisition_action=NextAction(args.acquisition_action),
        package_path=args.package,
        run_root=args.run_root,
    )
    try:
        with _offline_socket_guard():
            if args.reserve:
                result = reserve_acquisition_attempt(
                    config=config,
                    checked_at=args.checked_at,
                    expected_readiness_fingerprint=args.expected_readiness_fingerprint,
                )
            elif args.record_outcome is not None:
                result = record_acquisition_outcome(
                    config=config,
                    outcome=AttemptOutcome(args.record_outcome),
                    retry_after_seconds=args.retry_after_seconds,
                )
            else:
                result = recover_acquisition_attempt(config=config)
    except (
        DailyEodAcquisitionCustodyError,
        DailyEodRunJournalError,
        SameDayCatchupError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_acquisition_custody_rejected",
                    "error_type": type(exc).__name__,
                    "provider_request_executed_by_custody": False,
                    "credential_access_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 1 if result.outcome in {
        "permanent_failure",
        "quality_failure",
        "recovery_blocked",
    } else 0


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during acquisition custody")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during acquisition custody")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during acquisition custody")

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
