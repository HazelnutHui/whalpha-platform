"""Tests for the exact-authorization entitlement probe CLI."""

from tip_api.providers.massive import historical_entitlement_probe_cli as cli
from tip_api.providers.massive.historical_entitlement_probe import (
    required_probe_acknowledgement,
)


def test_review_prints_bound_acknowledgement_without_loading_credentials(
    monkeypatch, capsys
) -> None:
    revision = "a" * 40
    monkeypatch.setattr(cli, "_clean_revision", lambda: revision)
    monkeypatch.setattr(
        cli,
        "load_massive_provider_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )

    assert cli.main(["--session-date", "2026-07-16", "--review"]) == 0
    output = capsys.readouterr().out
    assert "maximum_request_count=4" in output
    assert required_probe_acknowledgement(
        session_date=cli.date(2026, 7, 16), revision=revision
    ) in output


def test_wrong_acknowledgement_stops_before_credential_access(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "load_massive_provider_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )

    assert (
        cli.main(
            [
                "--session-date",
                "2026-07-16",
                "--acknowledgement",
                "wrong",
            ]
        )
        == 2
    )
    assert "authorization-mismatch" in capsys.readouterr().err
