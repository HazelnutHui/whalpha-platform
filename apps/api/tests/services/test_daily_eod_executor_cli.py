from __future__ import annotations

import json
import socket
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_executor_cli as cli


def _argv(tmp_path: Path) -> list[str]:
    return [
        "--as-of-session", "2026-08-27",
        "--data-root", str(tmp_path / "data"),
        "--run-root", str(tmp_path / "runs"),
        "--phase1a-audit", "/tmp/executor-phase1a",
        "--prior-phase1b-audit", "/tmp/executor-prior-phase1b",
        "--phase1b-audit", "/tmp/executor-phase1b",
        "--prior-candidate-audit", "/tmp/executor-prior-candidate",
        "--candidate-audit", "/tmp/executor-candidate",
        "--entry-geometry-audit", "/tmp/executor-entry",
    ]


def test_cli_requires_plan_fingerprint_for_execution(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cli,
        "execute_daily_eod_action",
        lambda **kwargs: pytest.fail("executor must not run"),
    )
    with pytest.raises(SystemExit):
        cli.main([*_argv(tmp_path), "--execute-action", "calculate_phase1a"])


def test_cli_executes_exact_action_and_prints_machine_result(monkeypatch, tmp_path, capsys) -> None:
    captured = {}

    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "execute_daily_eod_action",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(
            outcome="succeeded",
            as_dict=lambda: {"outcome": "succeeded", "action": "calculate_phase1a"},
        ),
    )
    assert cli.main([
        *_argv(tmp_path),
        "--execute-action", "calculate_phase1a",
        "--expected-plan-fingerprint", "a" * 64,
    ]) == 0
    assert captured["expected_plan_fingerprint"] == "a" * 64
    assert captured["expected_action"].value == "calculate_phase1a"
    assert json.loads(capsys.readouterr().out)["outcome"] == "succeeded"


def test_cli_recovery_never_accepts_execution_fingerprint(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cli,
        "recover_daily_eod_action",
        lambda **kwargs: pytest.fail("recovery must not run"),
    )
    with pytest.raises(SystemExit):
        cli.main([
            *_argv(tmp_path),
            "--recover-incomplete",
            "--expected-plan-fingerprint", "a" * 64,
        ])


@pytest.mark.parametrize(
    "error",
    [
        cli.DailyEodExecutorError("private path detail"),
        cli.DailyEodAutomationError("private planner detail"),
        OSError("private filesystem detail"),
    ],
)
def test_cli_returns_sanitized_rejection(monkeypatch, tmp_path, capsys, error) -> None:
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "recover_daily_eod_action",
        lambda **kwargs: (_ for _ in ()).throw(error),
    )
    assert cli.main([*_argv(tmp_path), "--recover-incomplete"]) == 1
    output = capsys.readouterr().out
    assert "private" not in output
    assert json.loads(output)["reason_code"] == "daily_eod_execution_rejected"


def test_executor_socket_guard_blocks_network_and_restores() -> None:
    original = socket.socket
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("127.0.0.1", 9))
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("localhost", 80)
        guarded = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
    assert socket.socket is original
