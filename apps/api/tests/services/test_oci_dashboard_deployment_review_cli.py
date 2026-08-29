from __future__ import annotations

import json
import socket
from types import SimpleNamespace

import pytest

from tip_api.services import oci_dashboard_deployment_review_cli as cli


def test_cli_is_network_prohibited_and_only_emits_review(monkeypatch, capsys, tmp_path):
    captured = []

    def selected(**kwargs):
        captured.append(kwargs)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return SimpleNamespace(
            as_dict=lambda: {
                "contract_version": "oci-dashboard-deployment-runtime-review/1.0",
                "status": "review_ready",
                "installation_performed": False,
                "deployment_authorized": False,
            }
        )

    monkeypatch.setattr(cli, "_source_repository_root", lambda: tmp_path)
    monkeypatch.setattr(cli, "review_deployment_runtime_candidate", selected)

    assert cli.main(
        [
            "--config-id",
            "oci-deployment-review-cli-1",
            "--run-root",
            "/var/lib/trading-intelligence-platform/daily-eod",
            "--review-enabled-candidate",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["installation_performed"] is False
    assert payload["deployment_authorized"] is False
    assert captured[0]["capability_enabled"] is True


def test_cli_rejects_relative_run_root_without_review(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "review_deployment_runtime_candidate",
        lambda **_kwargs: pytest.fail("review must not run"),
    )
    with pytest.raises(SystemExit):
        cli.main(
            [
                "--config-id",
                "oci-deployment-review-cli-2",
                "--run-root",
                "relative",
            ]
        )
