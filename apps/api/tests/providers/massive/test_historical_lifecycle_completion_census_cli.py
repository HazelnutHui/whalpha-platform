"""Tests for the bounded lifecycle completion census CLI."""

import json
from types import SimpleNamespace

from tip_api.providers.massive import historical_lifecycle_completion_census_cli as cli


def test_execute_requires_clean_revision_before_credentials(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "_clean_revision",
        lambda: (_ for _ in ()).throw(RuntimeError("dirty")),
    )
    monkeypatch.setattr(
        cli,
        "load_massive_provider_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )

    assert cli.main(["--anchor-date", "2026-07-16", "--execute"]) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "stopped"
    assert payload["error_type"] == "RuntimeError"
    assert payload["data_write_count"] == 0


def test_completion_output_contains_only_bounded_aggregate_evidence(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(cli, "load_massive_provider_config_from_file", object)
    monkeypatch.setattr(cli, "MassiveUrllibTransport", object)
    monkeypatch.setattr(
        cli,
        "census_complete_massive_historical_lifecycle_pagination",
        lambda **kwargs: SimpleNamespace(
            as_dict=lambda: {
                "contract_version": (
                    "massive-historical-lifecycle-completion-census/1.0"
                ),
                "status": "completed",
                "result_count": 7000,
                "response_body_retained": False,
                "data_write_count": 0,
            }
        ),
    )

    assert cli.main(["--anchor-date", "2026-07-16", "--execute"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["implementation_revision"] == "a" * 40
    assert payload["maximum_request_count"] == 20
    assert payload["maximum_result_count"] == 25000
    assert payload["response_body_retained"] is False
    assert payload["data_write_count"] == 0
