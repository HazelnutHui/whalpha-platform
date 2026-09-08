from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

from tip_api.services import historical_corporate_action_resolution_shadow_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--start-date",
        "2026-08-20",
        "--end-date",
        "2026-08-22",
        "--split-source-package",
        str(tmp_path / "split"),
        "--dividend-source-package",
        str(tmp_path / "dividend"),
        "--identity-evidence",
        str(tmp_path / "identity.json"),
        "--output-root",
        str(tmp_path / "shadow"),
        "--materialized-at",
        "2026-09-02T00:00:00Z",
        "--execute",
    ]


def test_cli_failure_is_safe(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)

    def fail(**kwargs):
        del kwargs
        raise cli.HistoricalCorporateActionResolutionShadowError("secret row")

    monkeypatch.setattr(
        cli, "build_historical_corporate_action_resolution_shadow", fail
    )
    assert cli.main(_args(tmp_path)) == 1
    captured = capsys.readouterr()
    assert "secret row" not in captured.err
    payload = json.loads(captured.err)
    assert payload["external_request_count"] == 0
    assert payload["canonical_data_write_count"] == 0


def test_cli_completion_reports_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    manifest = SimpleNamespace(
        start_date=date(2026, 8, 20),
        end_date=date(2026, 8, 22),
        source_record_count=4,
        mapped_record_count=4,
        identity_session_available_record_count=3,
        identity_session_unavailable_record_count=1,
        resolution_status_counts=(("resolved", 2), ("unresolved", 2)),
        record_status_counts=(("active", 2), ("quarantined", 2)),
        action_type_counts=(("cash_dividend", 2), ("stock_split", 2)),
        quality_flag_counts=(("source_available_time_unavailable", 4),),
        artifacts=(object(),),
        logical_fingerprint="b" * 64,
        point_in_time_eligibility="outcome_reconciliation_only",
    )
    monkeypatch.setattr(
        cli,
        "build_historical_corporate_action_resolution_shadow",
        lambda **kwargs: SimpleNamespace(
            status="published",
            manifest=manifest,
            manifest_sha256="c" * 64,
        ),
    )

    assert cli.main(_args(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_record_count"] == 4
    assert payload["artifact_count"] == 1
    assert payload["adjustment_ledger_write_count"] == 0
