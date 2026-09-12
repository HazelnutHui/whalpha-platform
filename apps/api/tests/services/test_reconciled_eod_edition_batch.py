from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import pytest

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
)
from tip_api.providers.massive.same_day_catchup import SameDayCatchupError
from tip_api.services import reconciled_eod_edition_batch as module
from tip_api.services.reconciled_eod_edition_batch import (
    ReconciledEodEditionBatchError,
    ReconciledEodEditionBatchSessionResultV1,
    ReconciledEodEditionSourceV1,
    run_reconciled_eod_edition_batch,
)


REVISION = "a" * 40


def source(tmp_path: Path, session: date) -> ReconciledEodEditionSourceV1:
    package = tmp_path / f"package-{session.isoformat()}"
    package.mkdir()
    return ReconciledEodEditionSourceV1(
        session_date=session,
        package_path=package,
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )


def result(
    session: date,
    *,
    status: Literal["published", "already_present", "failed"],
) -> ReconciledEodEditionBatchSessionResultV1:
    return ReconciledEodEditionBatchSessionResultV1(
        session_date=session.isoformat(),
        status=status,
        source_provenance="retained_original",
        record_count=10 if status != "failed" else 0,
        added_record_count=1 if status != "failed" else 0,
        absent_record_count=0,
        manifest_fingerprint="1" * 64 if status != "failed" else None,
        failure_code="unexpected_failure" if status == "failed" else "none",
    )


def run_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    sources: tuple[ReconciledEodEditionSourceV1, ...],
    workers: int = 1,
):
    data_root = tmp_path / "data"
    data_root.mkdir(exist_ok=True)
    data_root = data_root.resolve()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root)
    return run_reconciled_eod_edition_batch(
        data_root=data_root,
        candidate_root=tmp_path / "candidate",
        edition_id="massive-exact-symbol-v1",
        implementation_revision=REVISION,
        sources=sources,
        workers=workers,
    )


def test_batch_reuses_completed_session_and_builds_only_pending(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sessions = (date(2026, 9, 8), date(2026, 9, 9))
    sources = tuple(source(tmp_path, item) for item in sessions)
    built: list[date] = []

    def reuse(**kwargs):
        selected = kwargs["source"]
        if selected.session_date == sessions[0]:
            return result(selected.session_date, status="already_present")
        return None

    def build(job):
        built.append(job.source.session_date)
        return result(job.source.session_date, status="published")

    monkeypatch.setattr(module, "_reuse_existing_session", reuse)
    monkeypatch.setattr(module, "_build_and_publish", build)

    completed = run_batch(monkeypatch, tmp_path, sources=sources)

    assert built == [sessions[1]]
    assert completed.status == "batch_complete"
    assert completed.published_session_count == 1
    assert completed.reused_session_count == 1
    assert completed.failed_session_count == 0
    assert completed.record_count == 20
    assert completed.added_record_count == 2
    assert completed.absent_record_count == 0
    assert completed.external_request_count == 0
    assert completed.canonical_data_write_count == 0
    assert completed.candidate_session_write_count == 1
    assert completed.interval_manifest_write_count == 0
    assert completed.candidate_authority is False
    assert completed.production_authority is False
    assert completed.research_performance_authorized is False


def test_batch_retains_partition_results_when_one_session_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sessions = (date(2026, 9, 8), date(2026, 9, 9))
    sources = tuple(source(tmp_path, item) for item in sessions)
    monkeypatch.setattr(module, "_reuse_existing_session", lambda **_kwargs: None)

    def build(job):
        status = "failed" if job.source.session_date == sessions[1] else "published"
        return result(job.source.session_date, status=status)

    monkeypatch.setattr(module, "_build_and_publish", build)

    completed = run_batch(monkeypatch, tmp_path, sources=sources)

    assert completed.status == "stopped_with_failures"
    assert completed.published_session_count == 1
    assert completed.failed_session_count == 1
    assert [item.status for item in completed.sessions] == ["published", "failed"]
    assert completed.interval_manifest_write_count == 0


def test_batch_rejects_result_with_wrong_session_binding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected = (source(tmp_path, date(2026, 9, 9)),)
    monkeypatch.setattr(module, "_reuse_existing_session", lambda **_kwargs: None)
    monkeypatch.setattr(
        module,
        "_build_and_publish",
        lambda _job: result(date(2026, 9, 8), status="published"),
    )

    with pytest.raises(ReconciledEodEditionBatchError, match="bindings differ"):
        run_batch(monkeypatch, tmp_path, sources=selected)


def test_worker_classifies_invalid_source_package_without_leaking_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected = source(tmp_path, date(2026, 9, 9))

    def fail(**_kwargs):
        raise SameDayCatchupError("sensitive source detail")

    monkeypatch.setattr(module, "build_reconciled_eod_session_candidate", fail)
    failed = module._build_and_publish(
        module._BuildJob(
            data_root=tmp_path,
            candidate_root=tmp_path / "candidate",
            edition_id="massive-exact-symbol-v1",
            implementation_revision=REVISION,
            created_at=None,
            source=selected,
        )
    )

    assert failed.status == "failed"
    assert failed.failure_code == "source_package_invalid"
    assert "sensitive" not in str(failed)


@pytest.mark.parametrize("workers", [0, 5])
def test_batch_rejects_worker_counts_outside_bounded_range(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    workers: int,
) -> None:
    selected = (source(tmp_path, date(2026, 9, 9)),)

    with pytest.raises(ReconciledEodEditionBatchError, match="one and four"):
        run_batch(
            monkeypatch,
            tmp_path,
            sources=selected,
            workers=workers,
        )


@pytest.mark.parametrize("mode", ["duplicate", "unordered"])
def test_batch_rejects_duplicate_or_unordered_sessions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
) -> None:
    first = source(tmp_path, date(2026, 9, 8))
    second = source(tmp_path, date(2026, 9, 9))
    selected = (first, first) if mode == "duplicate" else (second, first)

    with pytest.raises(ReconciledEodEditionBatchError, match="unique and ordered"):
        run_batch(monkeypatch, tmp_path, sources=selected)


def test_batch_rejects_nonapproved_canonical_data_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", approved.resolve())
    selected = (source(tmp_path, date(2026, 9, 9)),)

    with pytest.raises(ReconciledEodEditionBatchError, match="approved Dell root"):
        run_reconciled_eod_edition_batch(
            data_root=other.resolve(),
            candidate_root=tmp_path / "candidate",
            edition_id="massive-exact-symbol-v1",
            implementation_revision=REVISION,
            sources=selected,
        )


@pytest.mark.parametrize("session_count", [0, 41])
def test_batch_rejects_session_counts_outside_bounded_range(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_count: int,
) -> None:
    selected = tuple(
        source(tmp_path, date(2026, 1, day))
        for day in range(1, min(session_count, 31) + 1)
    )
    if session_count == 41:
        selected += tuple(
            source(tmp_path, date(2026, 2, day)) for day in range(1, 11)
        )

    with pytest.raises(ReconciledEodEditionBatchError, match="one and forty"):
        run_batch(monkeypatch, tmp_path, sources=selected)
