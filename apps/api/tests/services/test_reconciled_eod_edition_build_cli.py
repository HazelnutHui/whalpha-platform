from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import reconciled_eod_edition_build_cli as module
from tip_api.services.reconciled_eod_edition_build import (
    CONTRACT_VERSION,
    ReconciledEodEditionBuildCheckpointV1,
    ReconciledEodEditionBuildStoppedError,
)


def _arguments(tmp_path) -> list[str]:
    return [
        "--data-root",
        str(tmp_path / "data"),
        "--coverage-path",
        str(tmp_path / "coverage.json"),
        "--coverage-file-sha256",
        "a" * 64,
        "--candidate-root",
        str(tmp_path / "candidate"),
        "--edition-id",
        "edition-v1",
        "--created-at",
        "2026-09-11T03:00:00+00:00",
        "--workers",
        "2",
        "--batch-size",
        "20",
        "--execute",
    ]


def _checkpoint(*, failed: int = 0) -> ReconciledEodEditionBuildCheckpointV1:
    return ReconciledEodEditionBuildCheckpointV1(
        batch_number=1,
        first_session="2026-09-08",
        last_session="2026-09-09",
        requested_session_count=2,
        published_session_count=2 - failed,
        reused_session_count=0,
        failed_session_count=failed,
        record_count=20 - failed * 10,
        added_record_count=2 - failed,
        absent_record_count=0,
        status="stopped_with_failures" if failed else "batch_complete",
    )


def test_cli_binds_clean_revision_and_emits_progress_then_completion(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "read_reconciled_eod_source_coverage",
        lambda **_kwargs: SimpleNamespace(coverage="sealed"),
    )
    observed: dict[str, object] = {}

    def run(**kwargs):
        observed.update(kwargs)
        kwargs["progress"](_checkpoint())
        return SimpleNamespace(
            as_dict=lambda: {
                "contract_version": CONTRACT_VERSION,
                "status": "complete",
                "canonical_data_write_count": 0,
                "production_authority": False,
            }
        )

    monkeypatch.setattr(module, "run_reconciled_eod_edition_build", run)

    assert module.main(_arguments(tmp_path)) == 0

    lines = capsys.readouterr().out.splitlines()
    progress = json.loads(lines[0])
    completion = json.loads(lines[1])
    assert observed["coverage"] == "sealed"
    assert observed["implementation_revision"] == "c" * 40
    assert observed["workers"] == 2
    assert observed["batch_size"] == 20
    assert progress["record_type"] == "edition_build_checkpoint"
    assert completion["status"] == "complete"
    assert completion["canonical_data_write_count"] == 0


def test_cli_failure_output_is_bounded_and_resumable(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "read_reconciled_eod_source_coverage",
        lambda **_kwargs: SimpleNamespace(coverage="sealed"),
    )

    def stopped(**_kwargs):
        checkpoint = _checkpoint(failed=1)
        error = ReconciledEodEditionBuildStoppedError(
            checkpoint=checkpoint,
            failed_sessions=(("2026-09-09", "unexpected_failure"),),
            completed_checkpoints=(checkpoint,),
        )
        error.__cause__ = RuntimeError("sensitive source response")
        raise error

    monkeypatch.setattr(module, "run_reconciled_eod_edition_build", stopped)

    assert module.main(_arguments(tmp_path)) == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert captured.out == ""
    assert payload["status"] == "stopped_with_failures"
    assert payload["safe_resume_from_completed_sessions"] is True
    assert payload["interval_manifest_write_count"] == 0
    assert "sensitive" not in captured.err
    assert "source response" not in captured.err
