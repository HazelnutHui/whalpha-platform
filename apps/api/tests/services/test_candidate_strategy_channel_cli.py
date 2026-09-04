from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import tip_api.services.candidate_strategy_channel_cli as cli


def test_strategy_cli_consumes_only_current_candidate_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = date(2026, 9, 3)
    universe_ids = ("primary", "secondary")
    candidate_batches = tuple(
        SimpleNamespace(universe_id=universe_id) for universe_id in universe_ids
    )
    evidence = SimpleNamespace(
        manifest={
            "as_of_session": session.isoformat(),
            "universe_ids": list(universe_ids),
        },
        candidate_batches=candidate_batches,
    )
    calls: dict[str, object] = {}

    def read_current(path: Path, *, as_of_session: date):
        calls["candidate_path"] = path
        calls["candidate_session"] = as_of_session
        return evidence

    monkeypatch.setattr(cli, "validate_strategy_channel_tmp_output_dir", lambda path: path)
    monkeypatch.setattr(cli, "read_opportunity_candidate_current_batches", read_current)
    monkeypatch.setattr(cli, "read_candidate_entry_geometry_audit", lambda path: {"ok": True})
    monkeypatch.setattr(
        cli,
        "_read_records",
        lambda path: [
            {"as_of_session": session.isoformat(), "universe_id": universe_id}
            for universe_id in universe_ids
        ],
    )
    monkeypatch.setattr(
        cli,
        "CandidateEntryGeometryBatchV1",
        SimpleNamespace(
            model_validate=lambda row: SimpleNamespace(
                universe_id=row["universe_id"]
            )
        ),
    )
    monkeypatch.setattr(
        cli,
        "calculate_candidate_strategy_channels",
        lambda **kwargs: SimpleNamespace(universe_id=kwargs["candidate_batch"].universe_id),
    )
    monkeypatch.setattr(
        cli,
        "build_candidate_strategy_channel_consumer",
        lambda result: result,
    )
    monkeypatch.setattr(
        cli,
        "compare_with_independent_strategy_channel_oracle",
        lambda **kwargs: SimpleNamespace(
            mismatch_count=0,
            input_permutation_match=True,
        ),
    )

    def write_audit(**kwargs):
        calls["candidate_manifest"] = kwargs["candidate_audit_manifest"]
        return {
            "as_of_session": session.isoformat(),
            "universe_ids": list(universe_ids),
            "logical_content_fingerprint": "a" * 64,
            "oracle_mismatch_count": 0,
            "input_permutation_match": True,
            "shadow_only": True,
            "external_request_count": 0,
            "production_write_count": 0,
        }

    monkeypatch.setattr(cli, "write_candidate_strategy_channel_audit", write_audit)

    candidate_path = tmp_path / "candidate"
    output_path = tmp_path / "output"
    assert (
        cli.main(
            [
                "--as-of-session",
                session.isoformat(),
                "--candidate-audit",
                str(candidate_path),
                "--entry-geometry-audit",
                str(tmp_path / "entry"),
                "--output-dir",
                str(output_path),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert calls == {
        "candidate_path": candidate_path,
        "candidate_session": session,
        "candidate_manifest": evidence.manifest,
    }
    assert summary["status"] == "completed"
    assert summary["timings"]["candidate_current_projection_seconds"] >= 0
    assert summary["peak_memory_kib"] > 0
