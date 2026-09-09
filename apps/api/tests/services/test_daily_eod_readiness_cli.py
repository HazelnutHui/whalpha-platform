from __future__ import annotations

import json
import socket
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_readiness_cli as cli


def _argv() -> list[str]:
    return [
        "--checked-at", "2026-08-27T20:30:00+00:00",
        "--target-session", "2026-08-27",
        "--latest-canonical-session", "2026-08-26",
        "--acquisition-action", "prepare_identity_catchup",
    ]


def test_cli_prints_machine_readiness_plan(monkeypatch, capsys) -> None:
    captured = {}

    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "plan_daily_eod_readiness",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(
            alert_required=False,
            as_dict=lambda: {"status": "ready_for_fetch_review"},
        ),
    )
    assert cli.main(_argv()) == 0
    assert captured["target_session"].isoformat() == "2026-08-27"
    assert json.loads(capsys.readouterr().out)["status"] == "ready_for_fetch_review"


def test_cli_parses_ordered_attempt_evidence(monkeypatch, capsys) -> None:
    captured = {}

    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "plan_daily_eod_readiness",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(alert_required=False, as_dict=lambda: {"status": "waiting"}),
    )
    assert cli.main([
        *_argv(),
        "--attempt", "1|2026-08-27T20:31:00+00:00|rate_limited|1800",
    ]) == 0
    assert captured["attempts"][0].retry_after_seconds == 1800
    capsys.readouterr()


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "plan_daily_eod_readiness",
        lambda **kwargs: (_ for _ in ()).throw(
            cli.DailyEodReadinessError("private operational detail")
        ),
    )
    assert cli.main(_argv()) == 1
    output = capsys.readouterr().out
    assert "private" not in output
    assert json.loads(output)["external_request_count"] == 0


def test_cli_alert_plan_exits_nonzero(monkeypatch, capsys) -> None:
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "plan_daily_eod_readiness",
        lambda **kwargs: SimpleNamespace(
            alert_required=True,
            as_dict=lambda: {"status": "blocked", "alert_required": True},
        ),
    )
    assert cli.main(_argv()) == 1
    capsys.readouterr()


def test_cli_operator_review_gate_exits_nonzero(capsys) -> None:
    argv = _argv()
    argv[-1] = "prepare_eod_catchup"

    assert cli.main(argv) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "awaiting_operator_review"
    assert payload["operator_review_required"] is True
    assert payload["external_request_count"] == 0


def test_cli_delayed_profile_removes_only_the_basic_release_review(capsys) -> None:
    argv = _argv()
    argv[-1] = "prepare_eod_catchup"

    assert cli.main([
        *argv,
        "--provider-recency-profile",
        "massive_stocks_delayed_15_minutes",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready_for_fetch_review"
    assert payload["operator_review_required"] is False
    assert payload["provider_recency_profile"] == (
        "massive_stocks_delayed_15_minutes"
    )
    assert payload["provider_completeness_asserted"] is False


def test_readiness_socket_guard_blocks_and_restores() -> None:
    original = socket.socket
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("localhost", 80)
        guarded = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
    assert socket.socket is original
