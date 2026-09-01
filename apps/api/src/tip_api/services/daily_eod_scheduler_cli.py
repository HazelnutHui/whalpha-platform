"""Credential-free CLI for reviewing one default-off scheduler wake."""

from __future__ import annotations

import argparse
import json
import os
import pwd
import socket
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from tip_api.persistence.eod_read import EodDatasetUnavailableError
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.daily_eod_scheduler import (
    DailyEodSchedulerError,
    plan_daily_eod_scheduler_wake,
)
from tip_api.services.daily_eod_scheduler_runtime_plan import (
    APPROVED_RUNTIME_PARENT,
)
from tip_api.services.market_calendar import MarketCalendarError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review one network-free, default-off daily scheduler wake."
    )
    parser.add_argument("--checked-at", type=datetime.fromisoformat)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--review-enabled-candidate", action="store_true")
    parser.add_argument("--verify-dell-runtime", action="store_true")
    parser.add_argument("--expected-revision")
    parser.add_argument("--expected-python-executable", type=Path)
    parser.add_argument(
        "--expected-checkout-mode",
        choices=("main", "detached"),
    )
    args = parser.parse_args(argv)
    if not args.data_root.is_absolute():
        parser.error("--data-root must be absolute")
    runtime_arguments_valid = (
        not args.verify_dell_runtime
        and args.expected_revision is None
        and args.expected_python_executable is None
        and args.expected_checkout_mode is None
    ) or (
        args.verify_dell_runtime
        and args.expected_revision is not None
        and args.expected_python_executable is not None
    )
    if not runtime_arguments_valid:
        parser.error(
            "runtime verification, revision, and Python executable are required together"
        )
    if args.expected_revision is not None and not _is_revision(args.expected_revision):
        parser.error("--expected-revision must be an exact Git revision")
    if args.expected_python_executable is not None and (
        not args.expected_python_executable.is_absolute()
    ):
        parser.error("--expected-python-executable must be absolute")
    checked_at = args.checked_at or _utc_now()
    try:
        with _offline_socket_guard():
            if args.verify_dell_runtime:
                _verify_dell_runtime(
                    expected_revision=args.expected_revision,
                    expected_python_executable=args.expected_python_executable,
                    expected_checkout_mode=args.expected_checkout_mode or "main",
                )
            repository = CanonicalEodReadRepository(args.data_root)
            sessions = repository.list_session_index()
            if sessions:
                latest_integrity = repository.inspect_session(sessions[-1])
                if latest_integrity.session_date != sessions[-1]:
                    raise DailyEodSchedulerError(
                        "latest canonical EOD does not match its completion index"
                    )
            plan = plan_daily_eod_scheduler_wake(
                checked_at=checked_at,
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
                    "runtime_verified": False,
                    "scheduler_candidate_enabled": False,
                    "scheduler_installation_performed": False,
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
    payload = plan.as_dict()
    payload["runtime_verified"] = args.verify_dell_runtime
    payload["checked_at_source"] = (
        "explicit_argument" if args.checked_at is not None else "system_utc_clock"
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def _verify_dell_runtime(
    *,
    expected_revision: str,
    expected_python_executable: Path,
    expected_checkout_mode: str = "main",
    command_runner: CommandRunner = subprocess.run,
) -> None:
    """Fail closed unless Dell runs the exact clean planned checkout."""

    root = _source_repository_root()
    if (
        socket.gethostname().split(".", 1)[0].strip().lower() != "dell5820"
        or pwd.getpwuid(os.geteuid()).pw_name != "hui"
        or root.is_symlink()
        or root.resolve() != root
        or not root.is_dir()
        or not expected_python_executable.is_absolute()
        or not expected_python_executable.is_file()
        or Path(sys.executable).resolve() != expected_python_executable.resolve()
    ):
        raise DailyEodSchedulerError("scheduler runtime host identity mismatch")
    if expected_checkout_mode not in {"main", "detached"}:
        raise DailyEodSchedulerError("scheduler checkout mode is invalid")
    if expected_checkout_mode == "detached" and root != (
        APPROVED_RUNTIME_PARENT / f"revision={expected_revision}"
    ):
        raise DailyEodSchedulerError("scheduler detached runtime path mismatch")
    commands = (
        ["/usr/bin/git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD"],
        [
            "/usr/bin/git",
            "--no-optional-locks",
            "-C",
            str(root),
            "branch",
            "--show-current",
        ],
        [
            "/usr/bin/git",
            "--no-optional-locks",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "--untracked-files=normal",
        ],
    )
    try:
        revision, branch, status = (
            command_runner(
                command,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            for command in commands
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DailyEodSchedulerError(
            "scheduler runtime repository identity is unavailable"
        ) from exc
    expected_branch = "main" if expected_checkout_mode == "main" else ""
    if revision != expected_revision or branch != expected_branch or status:
        raise DailyEodSchedulerError(
            f"scheduler runtime requires clean pinned {expected_checkout_mode} revision"
        )


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodSchedulerError("scheduler source repository root is unavailable")


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _is_revision(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )


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
