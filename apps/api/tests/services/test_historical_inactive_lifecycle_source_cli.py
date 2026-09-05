from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

from tip_api.services import historical_inactive_lifecycle_source_cli as cli


def test_cli_failure_never_emits_exception_text(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(cli, "load_massive_provider_config_from_file", object)
    monkeypatch.setattr(cli, "MassiveUrllibTransport", object)

    def fail(**kwargs):
        del kwargs
        raise cli.MassiveTransportUnavailableError("fixture-secret response")

    monkeypatch.setattr(
        cli, "fetch_historical_inactive_lifecycle_source_package", fail
    )
    result = cli.main(
        [
            "--anchor-date",
            "2026-07-16",
            "--package",
            str(tmp_path / "package"),
            "--execute",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "fixture-secret" not in captured.err
    payload = json.loads(captured.err)
    assert payload["automatic_retry"] is False
    assert payload["canonical_data_write_count"] == 0


def test_cli_emits_bounded_progress_and_completion(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(cli, "load_massive_provider_config_from_file", object)
    monkeypatch.setattr(cli, "MassiveUrllibTransport", object)

    def complete(**kwargs):
        kwargs["progress"](
            SimpleNamespace(sequence=1, row_count=1, physical_sha256="b" * 64),
            1,
            100,
        )
        manifest = SimpleNamespace(
            anchor_date=date(2026, 7, 16),
            request_count=1,
            record_count=1,
            package_bytes=100,
            duplicate_ticker_count=0,
            field_presence_counts=(("delisted_utc", 1),),
            logical_fingerprint="c" * 64,
            pagination_complete=True,
            point_in_time_eligibility="outcome_reconciliation_only",
        )
        return SimpleNamespace(
            manifest=manifest,
            manifest_sha256="d" * 64,
            status="published",
        )

    monkeypatch.setattr(
        cli, "fetch_historical_inactive_lifecycle_source_package", complete
    )
    assert (
        cli.main(
            [
                "--anchor-date",
                "2026-07-16",
                "--package",
                str(tmp_path / "package"),
                "--execute",
            ]
        )
        == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert json.loads(lines[0])["record_type"] == (
        "inactive_lifecycle_source_checkpoint"
    )
    final = json.loads(lines[1])
    assert final["record_type"] == "inactive_lifecycle_source_completion"
    assert final["point_in_time_eligibility"] == "outcome_reconciliation_only"
    assert final["canonical_data_write_count"] == 0
