from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import historical_corporate_action_repeat_diff_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--kind",
        "split",
        "--start-date",
        "2025-06-23",
        "--end-date",
        "2026-09-04",
        "--baseline-package",
        str(tmp_path / "baseline"),
        "--repeat-package",
        str(tmp_path / "repeat"),
        "--output-root",
        str(tmp_path / "diff"),
        "--compared-at",
        "2026-09-08T10:00:00Z",
        "--execute",
    ]


def test_cli_failure_is_safe(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)

    def fail(**kwargs):
        del kwargs
        raise cli.HistoricalCorporateActionRepeatDiffError("private row")

    monkeypatch.setattr(cli, "build_historical_corporate_action_repeat_diff", fail)

    assert cli.main(_args(tmp_path)) == 1
    captured = capsys.readouterr()
    assert "private row" not in captured.err
    payload = json.loads(captured.err)
    assert payload["external_request_count"] == 0
    assert payload["canonical_data_write_count"] == 0


def test_cli_reports_only_safe_aggregates(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    manifest = SimpleNamespace(
        action_kind=SimpleNamespace(value="split"),
        start_date=SimpleNamespace(isoformat=lambda: "2025-06-23"),
        end_date=SimpleNamespace(isoformat=lambda: "2026-09-04"),
        baseline_record_count=10,
        repeat_record_count=11,
        unchanged_record_count=8,
        changed_record_count=1,
        added_record_count=2,
        removed_record_count=1,
        changed_field_counts=(("ticker", 1),),
        effective_date_changed_record_count=0,
        provider_ticker_changed_record_count=1,
        pagination_shape_changed=True,
        logical_fingerprint="b" * 64,
        point_in_time_eligibility="outcome_reconciliation_only",
    )
    monkeypatch.setattr(
        cli,
        "build_historical_corporate_action_repeat_diff",
        lambda **kwargs: SimpleNamespace(
            manifest=manifest,
            status="published",
            manifest_sha256="c" * 64,
        ),
    )

    assert cli.main(_args(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_record_count"] == 1
    assert payload["added_record_count"] == 2
    assert payload["publication_count"] == 0
