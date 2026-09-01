from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from tip_api.services import daily_eod_scheduler_runtime_plan_cli as cli


REVISION = "b" * 40


def test_cli_emits_write_free_plan_under_network_guard(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_verify_host_and_source", lambda: None)
    monkeypatch.setattr(cli, "_repository_state", lambda: (REVISION, "main", ""))
    monkeypatch.setattr(
        cli,
        "_resolve_python_executable",
        lambda: Path("/usr/bin/python3.12"),
    )

    original_builder = cli.build_daily_eod_scheduler_runtime_plan

    def guarded_builder(**kwargs):
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return original_builder(**kwargs)

    monkeypatch.setattr(cli, "build_daily_eod_scheduler_runtime_plan", guarded_builder)

    assert cli.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["implementation_revision"] == REVISION
    assert payload["creation_performed"] is False
    assert payload["installation_performed"] is False


def test_cli_rejects_dirty_or_non_main_source(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_verify_host_and_source", lambda: None)
    monkeypatch.setattr(cli, "_repository_state", lambda: (REVISION, "topic", " M x"))

    assert cli.main([]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["filesystem_write_count"] == 0


def test_cli_rejects_arguments() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--create"])
