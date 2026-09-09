"""Default-review CLI for one finite daily EOD offline run."""

from __future__ import annotations

import argparse
import json
import os
import socket
import stat
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from tip_api.services.daily_eod_automation import DailyEodAutomationError
from tip_api.services.daily_eod_bounded_offline_runner import (
    DEFAULT_MAXIMUM_ACTIONS,
    DEFAULT_MAXIMUM_ELAPSED_SECONDS,
    BoundedOfflineRunStatus,
    DailyEodBoundedOfflineRunnerError,
    run_bounded_daily_eod_offline,
)
from tip_api.services.daily_eod_executor import (
    DailyEodExecutionConfig,
    DailyEodExecutorError,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunJournalError
from tip_api.services.daily_eod_workspace import (
    DailyEodWorkspaceError,
    derive_daily_eod_workspace_layout,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketCalendarError


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_arguments(parser, args)
    started_at = args.started_at or datetime.now(UTC)
    try:
        repository_root = _source_repository_root()
        prior_session = ExchangeCalendar().previous_session(args.as_of_session)
        layout = derive_daily_eod_workspace_layout(
            workspace_root=args.workspace_root,
            data_root=args.data_root,
            repository_root=repository_root,
            target_session=args.as_of_session,
            prior_session=prior_session,
        )
        if args.execute:
            _validate_existing_workspace(layout)
        config = DailyEodExecutionConfig(
            target_session=args.as_of_session,
            paths=layout.as_automation_paths(),
            run_root=layout.run_root,
            panel_cache_root=layout.panel_cache_root,
            candidate_work_dir=layout.candidate_work_dir,
            publication_expected_current_state_fingerprint=(
                args.publication_expected_current_state_fingerprint
            ),
        )
        with _offline_socket_guard():
            result = run_bounded_daily_eod_offline(
                config=config,
                started_at=started_at,
                execute=args.execute,
                maximum_actions=args.maximum_actions,
                maximum_elapsed_seconds=args.maximum_elapsed_seconds,
            )
    except (
        DailyEodAutomationError,
        DailyEodBoundedOfflineRunnerError,
        DailyEodExecutorError,
        DailyEodRunJournalError,
        DailyEodWorkspaceError,
        MarketCalendarError,
        OSError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_bounded_offline_run_rejected",
                    "error_type": type(exc).__name__,
                    "execution_enabled": args.execute,
                    "automatic_retry_enabled": False,
                    "automatic_recovery_enabled": False,
                    "external_request_count": 0,
                    "production_write_count": 0,
                    "publication_authorized": False,
                    "deployment_authorized": False,
                    "scheduler_installation_performed": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    payload = result.as_dict()
    payload["started_at_source"] = (
        "explicit_argument" if args.started_at is not None else "system_utc_clock"
    )
    payload["workspace_layout_fingerprint"] = layout.logical_content_fingerprint
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if result.status in {
        BoundedOfflineRunStatus.BLOCKED,
        BoundedOfflineRunStatus.ACTION_FAILED,
    }:
        return 1
    if result.status is BoundedOfflineRunStatus.BUDGET_EXHAUSTED:
        return 2
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review or execute a finite sequence of governed Dell-local daily "
            "EOD offline actions."
        )
    )
    parser.add_argument("--as-of-session", required=True, type=date.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--started-at", type=datetime.fromisoformat)
    parser.add_argument("--maximum-actions", type=int, default=DEFAULT_MAXIMUM_ACTIONS)
    parser.add_argument(
        "--maximum-elapsed-seconds",
        type=int,
        default=DEFAULT_MAXIMUM_ELAPSED_SECONDS,
    )
    parser.add_argument("--publication-expected-current-state-fingerprint")
    parser.add_argument("--execute", action="store_true")
    return parser


def _validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    for name in ("data_root", "workspace_root"):
        if not getattr(args, name).is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.workspace_root.name != "daily-eod":
        parser.error("--workspace-root basename must be daily-eod")
    if args.started_at is not None and (
        args.started_at.tzinfo is None or args.started_at.utcoffset() is None
    ):
        parser.error("--started-at must be timezone aware")
    fingerprint = args.publication_expected_current_state_fingerprint
    if fingerprint is not None and not _is_fingerprint(fingerprint):
        parser.error(
            "--publication-expected-current-state-fingerprint must be SHA-256"
        )


def _validate_existing_workspace(layout) -> None:  # type: ignore[no-untyped-def]
    required = (
        layout.workspace_root,
        layout.workspace_root / "sessions",
        layout.session_root,
        layout.prior_session_root,
        layout.run_root,
        layout.panel_cache_root,
    )
    for directory in required:
        if directory.is_symlink() or not directory.is_dir():
            raise DailyEodWorkspaceError(
                "bounded offline execution requires the pre-provisioned workspace"
            )
        metadata = directory.stat()
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise DailyEodWorkspaceError(
                "bounded offline workspace custody differs"
            )


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodWorkspaceError("executing source repository root is unavailable")


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during bounded offline execution")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during bounded offline execution")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during bounded offline execution")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
