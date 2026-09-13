from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import strong_leader_pullback_evidence_blocker_census_cli as cli


def _args(tmp_path) -> list[str]:
    return [
        "--development-census", str(tmp_path),
        "--admission-decision", str(tmp_path),
        "--resolution-shadow", str(tmp_path),
        "--resolution-shadow-custody-root", str(tmp_path),
        "--unresolved-census", str(tmp_path),
        "--unresolved-census-custody-root", str(tmp_path),
        "--residual-census", str(tmp_path),
        "--residual-census-custody-root", str(tmp_path),
        "--lifecycle-shadow", str(tmp_path),
        "--lifecycle-shadow-custody-root", str(tmp_path),
        "--lifecycle-anchor", "2026-09-03",
        "--output-root", str(tmp_path / "build=fixture"),
        "--output-custody-root", str(tmp_path),
        "--evaluated-at", "2026-09-13T00:00:00Z",
        "--execute",
    ]


def test_stop_output_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    monkeypatch.setattr(
        cli,
        "build_strong_leader_pullback_evidence_blocker_census",
        lambda **_: (_ for _ in ()).throw(
            cli.StrongLeaderPullbackEvidenceBlockerCensusError("private")
        ),
    )
    assert cli.main(_args(tmp_path)) == 1
    payload = json.loads(capsys.readouterr().err)
    assert "private" not in json.dumps(payload)
    assert payload["stable_identity_assignment_count"] == 0
    assert payload["forward_outcome_count"] == 0


def test_completion_output_is_aggregate_only(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "a" * 40)
    manifest = SimpleNamespace(
        contract_version=cli.CONTRACT_VERSION,
        included_path_count=100,
        action_exposure_record_count=5,
        resolved_action_exposure_record_count=4,
        unassigned_action_candidate_exposure_record_count=1,
        feature_action_unique_path_count=20,
        horizon_5_action_unique_path_count=10,
        lifecycle_instrument_count=3,
        horizon_5_lifecycle_crossing_path_count=2,
        logical_fingerprint="b" * 64,
    )
    monkeypatch.setattr(
        cli,
        "build_strong_leader_pullback_evidence_blocker_census",
        lambda **_: SimpleNamespace(
            status="published", manifest=manifest, manifest_sha256="c" * 64
        ),
    )
    assert cli.main(_args(tmp_path)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action_exposure_record_count"] == 5
    assert "records" not in payload
    assert payload["forward_outcome_count"] == 0
