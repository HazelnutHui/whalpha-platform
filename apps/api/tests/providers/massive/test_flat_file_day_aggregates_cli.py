from __future__ import annotations

from datetime import date
from pathlib import Path

from tip_api.providers.massive import flat_file_day_aggregates_cli as cli


def test_review_is_bound_without_loading_credentials(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    revision = "a" * 40
    package = tmp_path / "acquisition-package"
    monkeypatch.setattr(cli, "_clean_revision", lambda: revision)
    monkeypatch.setattr(
        cli,
        "load_massive_flat_file_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )

    result = cli.main(
        [
            "--session-date",
            "2022-01-03",
            "--package-path",
            str(package),
            "--review",
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "maximum_request_count=1" in output
    assert "2022/01/2022-01-03.csv.gz" in output
    assert cli.required_acknowledgement(
        session_date=date(2022, 1, 3),
        package_path=package,
        revision=revision,
    ) in output


def test_wrong_acknowledgement_stops_before_credential_access(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "load_massive_flat_file_config_from_file",
        lambda: (_ for _ in ()).throw(AssertionError("credential loaded")),
    )

    result = cli.main(
        [
            "--session-date",
            "2022-01-03",
            "--package-path",
            str(tmp_path / "acquisition-package"),
            "--acknowledgement",
            "wrong",
        ]
    )

    assert result == 2
    assert "authorization-mismatch" in capsys.readouterr().err
