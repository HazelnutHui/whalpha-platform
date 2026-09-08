from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import historical_corporate_action_source_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--kind",
        "split",
        "--start-date",
        "2025-06-23",
        "--end-date",
        "2026-09-04",
        "--package",
        str(tmp_path / "split=2025-06-23_2026-09-04"),
        "--execute",
    ]


def test_cli_failure_never_emits_exception_text(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(cli, "load_massive_provider_config_from_file", object)
    monkeypatch.setattr(cli, "MassiveUrllibTransport", object)

    def fail(**kwargs):
        del kwargs
        raise cli.MassiveTransportUnavailableError("fixture-secret response")

    monkeypatch.setattr(
        cli, "fetch_historical_corporate_action_source_package", fail
    )
    result = cli.main(_args(tmp_path))

    captured = capsys.readouterr()
    assert result == 1
    assert "fixture-secret" not in captured.err
    payload = json.loads(captured.err)
    assert payload["automatic_retry"] is False
    assert payload["action_kind"] == "split"
    assert payload["adjustment_ledger_write_count"] == 0


def test_cli_reports_only_reviewable_completion_metadata(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(cli, "load_massive_provider_config_from_file", object)
    monkeypatch.setattr(cli, "MassiveUrllibTransport", object)
    manifest = SimpleNamespace(
        action_kind=SimpleNamespace(value="split"),
        start_date=SimpleNamespace(isoformat=lambda: "2025-06-23"),
        end_date=SimpleNamespace(isoformat=lambda: "2026-09-04"),
        request_count=1,
        record_count=5,
        package_bytes=1234,
        invalid_effective_date_count=0,
        duplicate_source_action_id_count=0,
        unexpected_field_counts=(),
        logical_fingerprint="b" * 64,
        pagination_complete=True,
        research_eligibility="source_observation_only",
    )
    monkeypatch.setattr(
        cli,
        "fetch_historical_corporate_action_source_package",
        lambda **kwargs: SimpleNamespace(
            manifest=manifest,
            status="published",
            manifest_sha256="c" * 64,
        ),
    )

    result = cli.main(_args(tmp_path))

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["record_count"] == 5
    assert payload["canonical_data_write_count"] == 0
    assert payload["publication_count"] == 0
