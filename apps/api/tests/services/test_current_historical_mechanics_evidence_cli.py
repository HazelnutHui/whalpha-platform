from __future__ import annotations

import json
import socket
from types import SimpleNamespace

import pytest

from tip_api.services import current_historical_mechanics_evidence_cli as cli


def test_cli_prints_compact_read_only_report(monkeypatch, capsys) -> None:
    observed = {}

    def assess(root):
        observed["root"] = root
        return SimpleNamespace(
            as_dict=lambda: {
                "status": "mechanics_only",
                "evidence_publication_performed": False,
                "production_write_count": 0,
            }
        )

    monkeypatch.setattr(cli, "assess_current_historical_mechanics_evidence", assess)

    assert cli.main(["--data-root", "/data/example"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "mechanics_only"
    assert output["evidence_publication_performed"] is False
    assert observed["root"].as_posix() == "/data/example"


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    def rejected(root):
        raise cli.CurrentHistoricalMechanicsEvidenceError("private path detail")

    monkeypatch.setattr(cli, "assess_current_historical_mechanics_evidence", rejected)

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
