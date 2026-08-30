from __future__ import annotations

import json
import socket
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from tip_api.read_models.eod import EodSessionDescriptor
from tip_api.services import strategy_research_readiness_cli as cli


def _descriptor() -> EodSessionDescriptor:
    return EodSessionDescriptor(
        schema_version="1.0",
        session_date=date(2026, 8, 28),
        record_count=9_945,
        completion_status="completed",
        identity_as_of_date=date(2026, 8, 28),
        available_at=datetime(2026, 8, 29, tzinfo=UTC),
        quality_warning_count=0,
    )


def test_cli_reports_valid_data_blocked_assessment(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "CanonicalEodReadRepository",
        lambda root: SimpleNamespace(list_sessions=lambda: (_descriptor(),)),
    )

    assert cli.main(["--data-root", "/data/example"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "data_blocked"
    assert payload["development_authorized"] is False
    assert payload["external_request_count"] == 0


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "CanonicalEodReadRepository",
        lambda root: SimpleNamespace(
            list_sessions=lambda: (_ for _ in ()).throw(
                cli.StrategyResearchReadinessError("private path detail")
            )
        ),
    )

    assert cli.main(["--data-root", "/data/example"]) == 1
    output = capsys.readouterr().out
    assert "private" not in output
    payload = json.loads(output)
    assert payload["status"] == "rejected"
    assert payload["production_write_count"] == 0


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
