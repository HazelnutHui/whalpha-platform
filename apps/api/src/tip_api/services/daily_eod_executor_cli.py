"""Administrator CLI for one exact offline daily EOD action or recovery."""

from __future__ import annotations

import argparse
import json
import socket
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationError,
    DailyEodAutomationPaths,
    NextAction,
)
from tip_api.services.daily_eod_executor import (
    OFFLINE_ACTIONS,
    DailyEodExecutionConfig,
    DailyEodExecutorError,
    execute_daily_eod_action,
    recover_daily_eod_action,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunJournalError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute one exact offline daily EOD action under Dell run custody."
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument("--prior-phase1b-audit", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--prior-candidate-audit", required=True, type=Path)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--entry-geometry-audit", required=True, type=Path)
    parser.add_argument("--phase2-audit", required=True, type=Path)
    parser.add_argument("--preview-bundle", required=True, type=Path)
    parser.add_argument("--strategy-channel-audit", required=True, type=Path)
    parser.add_argument("--panel-cache-root", type=Path)
    parser.add_argument("--candidate-work-dir", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--execute-action",
        choices=tuple(item.value for item in OFFLINE_ACTIONS),
    )
    mode.add_argument("--recover-incomplete", action="store_true")
    parser.add_argument("--expected-plan-fingerprint")
    args = parser.parse_args(argv)
    for name in (
        "data_root",
        "run_root",
        "phase1a_audit",
        "prior_phase1b_audit",
        "phase1b_audit",
        "prior_candidate_audit",
        "candidate_audit",
        "entry_geometry_audit",
        "phase2_audit",
        "preview_bundle",
        "strategy_channel_audit",
        "panel_cache_root",
        "candidate_work_dir",
    ):
        value = getattr(args, name)
        if value is not None and not value.is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.execute_action is not None:
        if not _is_fingerprint(args.expected_plan_fingerprint):
            parser.error("--execute-action requires --expected-plan-fingerprint SHA-256")
    elif args.expected_plan_fingerprint is not None:
        parser.error("--expected-plan-fingerprint is only valid with --execute-action")
    config = DailyEodExecutionConfig(
        target_session=args.as_of_session,
        paths=DailyEodAutomationPaths(
            data_root=args.data_root,
            phase1a_audit=args.phase1a_audit,
            prior_phase1b_audit=args.prior_phase1b_audit,
            phase1b_audit=args.phase1b_audit,
            prior_candidate_audit=args.prior_candidate_audit,
            candidate_audit=args.candidate_audit,
            entry_geometry_audit=args.entry_geometry_audit,
            phase2_audit=args.phase2_audit,
            preview_bundle=args.preview_bundle,
            strategy_channel_audit=args.strategy_channel_audit,
        ),
        run_root=args.run_root,
        panel_cache_root=args.panel_cache_root,
        candidate_work_dir=args.candidate_work_dir,
    )
    try:
        with _offline_socket_guard():
            if args.recover_incomplete:
                result = recover_daily_eod_action(config=config)
            else:
                result = execute_daily_eod_action(
                    config=config,
                    expected_plan_fingerprint=args.expected_plan_fingerprint,
                    expected_action=NextAction(args.execute_action),
                )
    except (
        DailyEodAutomationError,
        DailyEodExecutorError,
        DailyEodRunJournalError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_execution_rejected",
                    "error_type": type(exc).__name__,
                    "external_request_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.outcome in {"succeeded", "recovered_succeeded", "recovered_not_completed"} else 1


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
            raise RuntimeError("network is prohibited during daily EOD offline execution")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during daily EOD offline execution")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during daily EOD offline execution")

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
