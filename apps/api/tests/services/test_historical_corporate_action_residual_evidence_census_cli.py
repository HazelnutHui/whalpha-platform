from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import historical_corporate_action_residual_evidence_census_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--resolution-shadow", str(tmp_path),
        "--resolution-shadow-custody-root", str(tmp_path),
        "--unresolved-census", str(tmp_path),
        "--unresolved-census-custody-root", str(tmp_path),
        "--lifecycle-shadow", str(tmp_path),
        "--lifecycle-shadow-custody-root", str(tmp_path),
        "--lifecycle-anchor", "2026-09-03",
        "--finra-custody-root", str(tmp_path),
        "--finra-range-start", "2021-09-13",
        "--finra-range-end", "2026-09-09",
        "--output-root", str(tmp_path / "build=fixture"),
        "--output-custody-root", str(tmp_path),
        "--evaluated-at", "2026-09-13T00:00:00Z",
        "--execute",
    ]


def test_cli_stop_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "build_historical_corporate_action_residual_evidence_census",
        lambda **_: (_ for _ in ()).throw(
            cli.HistoricalCorporateActionResidualEvidenceCensusError("private")
        ),
    )
    assert cli.main(_args(tmp_path)) == 1
    payload = json.loads(capsys.readouterr().err)
    assert "private" not in json.dumps(payload)
    assert payload["stable_identity_assignment_count"] == 0


def test_cli_completion_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    manifest = SimpleNamespace(
        contract_version=cli.CONTRACT_VERSION,
        residual_record_count=10,
        residual_record_candidate_relation_counts=(("no_lifecycle_evidence", 3),),
        inactive_source_state_counts=(("no_ticker_match", 10),),
        finra_exact_date_symbol_record_count=2,
        finra_exact_numeric_record_count=1,
        logical_fingerprint="b" * 64,
    )
    monkeypatch.setattr(
        cli,
        "build_historical_corporate_action_residual_evidence_census",
        lambda **_: SimpleNamespace(
            status="published", manifest=manifest, manifest_sha256="c" * 64
        ),
    )
    assert cli.main(_args(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["residual_record_count"] == 10
    assert "records" not in payload
    assert payload["stable_identity_assignment_count"] == 0
