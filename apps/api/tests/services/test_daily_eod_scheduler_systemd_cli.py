from __future__ import annotations

import json
import socket
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_scheduler_systemd_cli as cli


def test_cli_is_network_and_write_free(monkeypatch, capsys, tmp_path) -> None:
    captured = []

    def review(**kwargs):
        captured.append(kwargs)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return SimpleNamespace(
            as_dict=lambda: {
                "contract_version": "daily-eod-scheduler-systemd-review/1.1",
                "status": "review_ready_prerequisite_missing",
                "installation_performed": False,
            }
        )

    monkeypatch.setattr(cli, "_source_repository_root", lambda: tmp_path)
    monkeypatch.setattr(cli, "review_scheduler_systemd_candidate", review)

    assert cli.main(
        [
            "--config-id",
            "dell-systemd-cli-review-1",
            "--review-enabled-candidate",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["installation_performed"] is False
    assert "scheduler_installed" not in payload
    assert captured[0]["activation_candidate_enabled"] is True


def test_cli_rejects_unexpected_arguments() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--config-id", "dell-systemd-cli-review-2", "--install"])
