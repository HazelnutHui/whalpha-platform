from __future__ import annotations

import json
import socket
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_automation_cli as cli
from tip_api.services.daily_eod_automation import PlanStatus


def _argv(tmp_path: Path) -> list[str]:
    return [
        "--as-of-session", "2026-08-26",
        "--data-root", str(tmp_path),
        "--phase1a-audit", "/tmp/phase1a-test",
        "--prior-phase1b-audit", "/tmp/prior-phase1b-test",
        "--phase1b-audit", "/tmp/phase1b-test",
        "--prior-candidate-audit", "/tmp/prior-candidate-test",
        "--candidate-audit", "/tmp/candidate-test",
        "--entry-geometry-audit", "/tmp/entry-test",
        "--phase2-audit", "/tmp/phase2-test",
        "--preview-bundle", "/tmp/preview-test",
        "--strategy-channel-audit", "/tmp/strategy-test",
        "--market-intelligence-output-root", "/tmp/mi-output-test",
        "--market-intelligence-approval-plan", "/tmp/mi-plan-test.json",
    ]


def test_cli_prints_machine_plan_and_uses_blocked_exit(monkeypatch, tmp_path, capsys) -> None:
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "plan_daily_eod_automation",
        lambda **kwargs: SimpleNamespace(
            status=PlanStatus.BLOCKED,
            as_dict=lambda: {"status": "blocked", "next_action": "operator_diagnosis"},
        ),
    )
    assert cli.main(_argv(tmp_path)) == 1
    assert json.loads(capsys.readouterr().out) == {
        "next_action": "operator_diagnosis",
        "status": "blocked",
    }


def test_cli_rejects_relative_path_before_planning(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cli,
        "plan_daily_eod_automation",
        lambda **kwargs: pytest.fail("planner must not run"),
    )
    argv = _argv(tmp_path)
    argv[argv.index("--phase1a-audit") + 1] = "relative"
    with pytest.raises(SystemExit):
        cli.main(argv)


def test_offline_guard_blocks_network_and_restores() -> None:
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
