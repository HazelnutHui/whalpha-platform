from __future__ import annotations

import json
import socket
from types import SimpleNamespace

import pytest

from tip_api.services import current_historical_pilot_baseline_cli as cli


def test_cli_emits_blocked_non_authorizing_report(monkeypatch, capsys) -> None:
    observed = {}

    def assess(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            as_dict=lambda: {
                "status": "blocked",
                "required_user_acknowledgement": None,
                "external_request_count": 0,
                "data_write_count": 0,
            }
        )

    monkeypatch.setattr(cli, "assess_current_historical_pilot_baseline", assess)
    assert cli.main(
        [
            "--data-root",
            "/data/example",
            "--repository-root",
            "/repo/example",
            "--reviewed-at",
            "2026-08-30T20:00:00+00:00",
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["required_user_acknowledgement"] is None
    assert observed["reviewed_at"].tzinfo is not None


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    def rejected(**kwargs):
        raise cli.CurrentHistoricalPilotBaselineError("private path detail")

    monkeypatch.setattr(cli, "assess_current_historical_pilot_baseline", rejected)
    assert cli.main(
        [
            "--data-root",
            "/data/example",
            "--repository-root",
            "/repo/example",
            "--reviewed-at",
            "2026-08-30T20:00:00+00:00",
        ]
    ) == 1
    output = capsys.readouterr().out
    assert "private" not in output
    payload = json.loads(output)
    assert payload["status"] == "rejected"
    assert payload["external_request_count"] == 0


def test_cli_socket_guard_blocks_and_restores() -> None:
    original = socket.socket
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("localhost", 80)
        guarded = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
    assert socket.socket is original
