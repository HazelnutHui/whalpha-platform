"""Tests for the exact-authorization six-page lifecycle census."""

from tip_api.providers.massive import historical_lifecycle_census_cli as cli


def test_review_does_not_load_credentials(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "load_massive_provider_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )
    assert cli.main(["--anchor-date", "2026-07-16", "--review"]) == 0
    output = capsys.readouterr().out
    assert "maximum_request_count=6" in output
    assert "I_AUTHORIZE_MASSIVE_LIFECYCLE_CENSUS_" in output


def test_wrong_ack_stops_before_credentials(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "load_massive_provider_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )
    result = cli.main(
        ["--anchor-date", "2026-07-16", "--acknowledgement", "wrong"]
    )
    assert result == 2
    assert "authorization-mismatch" in capsys.readouterr().err
