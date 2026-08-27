"""Offline CLI for one explicit immutable acquisition operator review."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from tip_api.services.daily_eod_acquisition_custody import (
    DailyEodAcquisitionConfig,
)
from tip_api.services.daily_eod_acquisition_operator_review import (
    DailyEodAcquisitionOperatorReviewError,
    record_acquisition_operator_review,
)
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    ACQUISITION_ACTIONS,
    DailyEodReadinessError,
    OperatorReviewDisposition,
    OperatorReviewEvidenceCode,
    OperatorReviewPurpose,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunJournalError


ACKNOWLEDGEMENT = "I_UNDERSTAND_REVIEW_DOES_NOT_EXECUTE_OR_AUTHORIZE_FETCH"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.acknowledgement != ACKNOWLEDGEMENT:
        parser.error("the exact review-only acknowledgement is required")
    try:
        with _offline_socket_guard():
            result = record_acquisition_operator_review(
                config=DailyEodAcquisitionConfig(
                    target_session=args.target_session,
                    latest_canonical_session=args.latest_canonical_session,
                    acquisition_action=NextAction(args.acquisition_action),
                    package_path=args.package,
                    run_root=args.run_root,
                ),
                purpose=OperatorReviewPurpose(args.purpose),
                disposition=OperatorReviewDisposition(args.disposition),
                evidence_code=OperatorReviewEvidenceCode(args.evidence_code),
                not_before=args.not_before,
                expected_terminal_event_fingerprint=(
                    args.expected_terminal_event_fingerprint
                ),
            )
    except (
        DailyEodAcquisitionOperatorReviewError,
        DailyEodReadinessError,
        DailyEodRunJournalError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_operator_review_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "production_write_count": 0,
                    "fetch_authorized_by_review": False,
                    "scheduler_enabled": False,
                    "publication_authorized": False,
                    "deployment_authorized": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Record one offline operator review without executing or authorizing a fetch."
        )
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
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument(
        "--purpose",
        required=True,
        choices=tuple(item.value for item in OperatorReviewPurpose),
    )
    parser.add_argument(
        "--disposition",
        required=True,
        choices=tuple(item.value for item in OperatorReviewDisposition),
    )
    parser.add_argument(
        "--evidence-code",
        required=True,
        choices=tuple(item.value for item in OperatorReviewEvidenceCode),
    )
    parser.add_argument("--not-before", required=True, type=datetime.fromisoformat)
    parser.add_argument("--expected-terminal-event-fingerprint")
    parser.add_argument("--acknowledgement", required=True)
    return parser


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during operator review")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during operator review")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during operator review")

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
