from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import historical_corporate_action_unresolved_census_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--resolution-shadow",
        str(tmp_path / "shadow" / "build=fixture"),
        "--resolution-shadow-custody-root",
        str(tmp_path / "shadow"),
        "--output-root",
        str(tmp_path / "output" / "build=fixture"),
        "--output-custody-root",
        str(tmp_path / "output"),
        "--evaluated-at",
        "2026-09-13T00:00:00Z",
        "--process-count",
        "2",
        "--execute",
    ]


def test_cli_stop_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)

    def fail(**kwargs):
        del kwargs
        raise cli.HistoricalCorporateActionUnresolvedCensusError("private ticker")

    monkeypatch.setattr(
        cli, "build_historical_corporate_action_unresolved_census", fail
    )
    assert cli.main(_args(tmp_path)) == 1
    captured = capsys.readouterr()
    assert "private ticker" not in captured.err
    payload = json.loads(captured.err)
    assert payload["stable_identity_assignment_count"] == 0
    assert payload["external_request_count"] == 0


def test_cli_completion_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    manifest = SimpleNamespace(
        contract_version=cli.CONTRACT_VERSION,
        unresolved_typed_record_count=10,
        unrepresentable_source_record_count=1,
        unresolved_unique_ticker_count=3,
        ticker_classification_counts=(
            ("multiple_historical_candidates", 1),
            ("one_historical_candidate", 1),
            ("zero_historical_candidates", 1),
        ),
        source_record_classification_counts=(
            ("multiple_historical_candidates", 2),
            ("one_historical_candidate", 3),
            ("zero_historical_candidates", 5),
        ),
        candidate_relation_count=3,
        distinct_candidate_instrument_count=3,
        identity_session_count=2,
        process_count=2,
        logical_fingerprint="b" * 64,
    )
    monkeypatch.setattr(
        cli,
        "build_historical_corporate_action_unresolved_census",
        lambda **kwargs: SimpleNamespace(
            status="published",
            manifest=manifest,
            manifest_sha256="c" * 64,
        ),
    )
    assert cli.main(_args(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["unresolved_typed_record_count"] == 10
    assert payload["stable_identity_assignment_count"] == 0
    assert "records" not in payload
