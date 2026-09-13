from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import strong_leader_pullback_source_acceptance_sample_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--blocker-census", str(tmp_path),
        "--blocker-census-custody-root", str(tmp_path),
        "--lifecycle-shadow", str(tmp_path),
        "--lifecycle-shadow-custody-root", str(tmp_path),
        "--output-root", str(tmp_path / "build=fixture"),
        "--output-custody-root", str(tmp_path),
        "--evaluated-at", "2026-09-13T14:00:00Z",
        "--execute",
    ]


def test_stop_output_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "build_strong_leader_pullback_source_acceptance_sample",
        lambda **_: (_ for _ in ()).throw(
            cli.StrongLeaderPullbackSourceAcceptanceSampleError("private case")
        ),
    )
    assert cli.main(_args(tmp_path)) == 1
    payload = json.loads(capsys.readouterr().err)
    assert "private case" not in json.dumps(payload)
    assert payload["provider_request_count"] == 0
    assert payload["canonical_data_write_count"] == 0
    assert payload["research_admission_count"] == 0


def test_completion_output_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    report = SimpleNamespace(
        contract_version=cli.CONTRACT_VERSION,
        action_case_count=20,
        lifecycle_case_count=64,
        combined_instrument_count=68,
        lifecycle_source_occurrence_count=122,
        logical_fingerprint="b" * 64,
    )
    monkeypatch.setattr(
        cli,
        "build_strong_leader_pullback_source_acceptance_sample",
        lambda **_: SimpleNamespace(
            status="published", report=report, report_sha256="c" * 64
        ),
    )
    assert cli.main(_args(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action_case_count"] == 20
    assert payload["lifecycle_case_count"] == 64
    assert "action_cases" not in payload
    assert "lifecycle_cases" not in payload
    assert payload["provider_request_count"] == 0
    assert payload["deployment_count"] == 0
