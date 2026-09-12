from __future__ import annotations

import json
import socket
from types import SimpleNamespace

import pytest

from tip_api.services import reconciled_eod_historical_mechanics_evidence_cli as cli


def test_cli_requires_and_forwards_exact_edition_identity(monkeypatch, capsys) -> None:
    observed = {}

    def assess(**values):
        observed.update(values)
        return SimpleNamespace(
            as_dict=lambda: {
                "status": "price_identity_mechanics_only",
                "evidence_publication_performed": False,
                "production_write_count": 0,
            }
        )

    monkeypatch.setattr(
        cli,
        "assess_reconciled_eod_historical_mechanics_evidence",
        assess,
    )

    assert cli.main(
        [
            "--data-root",
            "/data/example",
            "--edition-id",
            "edition-one",
            "--expected-interval-fingerprint",
            "a" * 64,
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "price_identity_mechanics_only"
    assert observed["data_root"].as_posix() == "/data/example"
    assert observed["edition_id"] == "edition-one"
    assert observed["expected_interval_manifest_fingerprint"] == "a" * 64
    assert observed["max_workers"] == cli.DEFAULT_VALIDATION_WORKERS


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    def rejected(**values):
        raise cli.ReconciledEodHistoricalMechanicsEvidenceError(
            "private path detail"
        )

    monkeypatch.setattr(
        cli,
        "assess_reconciled_eod_historical_mechanics_evidence",
        rejected,
    )

    assert cli.main(
        [
            "--data-root",
            "/data/example",
            "--edition-id",
            "edition-one",
            "--expected-interval-fingerprint",
            "a" * 64,
        ]
    ) == 1
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
