from __future__ import annotations

import json
import socket
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_acquisition_custody_cli as cli


def _base(tmp_path: Path) -> list[str]:
    return [
        "--target-session", "2026-08-27",
        "--latest-canonical-session", "2026-08-26",
        "--acquisition-action", "prepare_identity_catchup",
        "--package", "/tmp/custody-cli-package",
        "--run-root", str(tmp_path / "runs"),
    ]


def test_reserve_requires_exact_readiness_evidence(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cli,
        "reserve_acquisition_attempt",
        lambda **kwargs: pytest.fail("reservation must not run"),
    )
    with pytest.raises(SystemExit):
        cli.main([*_base(tmp_path), "--reserve"])


def test_cli_reserves_without_fetching(monkeypatch, tmp_path, capsys) -> None:
    captured = {}

    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "reserve_acquisition_attempt",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(
            outcome="reserved",
            as_dict=lambda: {
                "outcome": "reserved",
                "provider_request_executed_by_custody": False,
            },
        ),
    )
    assert cli.main([
        *_base(tmp_path),
        "--reserve",
        "--checked-at", "2026-08-27T20:30:00+00:00",
        "--expected-readiness-fingerprint", "a" * 64,
    ]) == 0
    assert captured["expected_readiness_fingerprint"] == "a" * 64
    assert json.loads(capsys.readouterr().out)[
        "provider_request_executed_by_custody"
    ] is False


def test_cli_records_rate_limit_and_parses_retry_after(monkeypatch, tmp_path, capsys) -> None:
    captured = {}

    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "record_acquisition_outcome",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(outcome="rate_limited", as_dict=lambda: {"outcome": "rate_limited"}),
    )
    assert cli.main([
        *_base(tmp_path),
        "--record-outcome", "rate_limited",
        "--retry-after-seconds", "1800",
    ]) == 0
    assert captured["retry_after_seconds"] == 1800
    capsys.readouterr()


def test_recovery_rejects_reservation_arguments(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cli,
        "recover_acquisition_attempt",
        lambda **kwargs: pytest.fail("recovery must not run"),
    )
    with pytest.raises(SystemExit):
        cli.main([
            *_base(tmp_path),
            "--recover-incomplete",
            "--checked-at", "2026-08-27T20:30:00+00:00",
        ])


def test_cli_sanitizes_custody_failure(monkeypatch, tmp_path, capsys) -> None:
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "recover_acquisition_attempt",
        lambda **kwargs: (_ for _ in ()).throw(
            cli.DailyEodAcquisitionCustodyError("private package detail")
        ),
    )
    assert cli.main([*_base(tmp_path), "--recover-incomplete"]) == 1
    output = capsys.readouterr().out
    assert "private" not in output
    assert json.loads(output)["credential_access_count"] == 0


def test_custody_socket_guard_blocks_and_restores() -> None:
    original = socket.socket
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("localhost", 80)
        guarded = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
    assert socket.socket is original
