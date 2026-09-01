"""Dell-only, network- and write-free immutable scheduler runtime planner."""

from __future__ import annotations

import json
import os
import pwd
import socket
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from tip_api.services.daily_eod_scheduler_runtime_plan import (
    APPROVED_PYTHON_LAUNCHER,
    APPROVED_SOURCE_REPOSITORY,
    CONTRACT_VERSION,
    DailyEodSchedulerRuntimePlanError,
    build_daily_eod_scheduler_runtime_plan,
)


def main(argv: list[str] | None = None) -> int:
    if argv:
        raise SystemExit("this command accepts no arguments")
    try:
        with _offline_socket_guard():
            _verify_host_and_source()
            revision, branch, status = _repository_state()
            if branch != "main" or status:
                raise DailyEodSchedulerRuntimePlanError(
                    "runtime planning requires clean canonical main"
                )
            python_executable = _resolve_python_executable()
            plan = build_daily_eod_scheduler_runtime_plan(
                implementation_revision=revision,
                expected_python_executable=python_executable,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "status": "rejected",
                    "reason_code": "daily_scheduler_runtime_plan_rejected",
                    "error_type": type(exc).__name__,
                    "creation_performed": False,
                    "installation_performed": False,
                    "network_request_count": 0,
                    "credential_access_count": 0,
                    "data_read_count": 0,
                    "filesystem_write_count": 0,
                    "production_write_count": 0,
                    "systemd_change_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(plan.model_dump_json())
    return 0


def _verify_host_and_source() -> None:
    if (
        socket.gethostname().split(".", 1)[0].strip().lower() != "dell5820"
        or pwd.getpwuid(os.geteuid()).pw_name != "hui"
        or _source_repository_root() != APPROVED_SOURCE_REPOSITORY
        or APPROVED_SOURCE_REPOSITORY.is_symlink()
        or not APPROVED_SOURCE_REPOSITORY.is_dir()
    ):
        raise DailyEodSchedulerRuntimePlanError(
            "runtime planning requires the canonical Dell hui repository"
        )


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodSchedulerRuntimePlanError("source repository root is unavailable")


def _repository_state() -> tuple[str, str, str]:
    def run(*arguments: str) -> str:
        result = subprocess.run(
            ["/usr/bin/git", "-C", str(APPROVED_SOURCE_REPOSITORY), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    return (
        run("rev-parse", "HEAD"),
        run("branch", "--show-current"),
        run("status", "--porcelain"),
    )


def _resolve_python_executable() -> Path:
    python_executable = APPROVED_PYTHON_LAUNCHER.resolve(strict=True)
    if not python_executable.is_file() or not os.access(python_executable, os.X_OK):
        raise DailyEodSchedulerRuntimePlanError(
            "canonical Python launcher custody is invalid"
        )
    return python_executable


@contextmanager
def _offline_socket_guard():
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during runtime planning")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited during runtime planning")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited during runtime planning")

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
    raise SystemExit(main(sys.argv[1:]))
