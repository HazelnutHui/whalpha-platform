from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from tip_api.services import reconciled_eod_edition_build as module
from tip_api.services.reconciled_eod_edition_batch import (
    ReconciledEodEditionBatchResultV1,
    ReconciledEodEditionBatchSessionResultV1,
)
from tip_api.services.reconciled_eod_edition_build import (
    ReconciledEodEditionBuildError,
    ReconciledEodEditionBuildStoppedError,
    run_reconciled_eod_edition_build,
)


NOW = datetime(2026, 9, 11, 3, tzinfo=UTC)
REVISION = "a" * 40
SESSIONS = (date(2026, 9, 4), date(2026, 9, 8), date(2026, 9, 9))


def _coverage(*, status: str = "ready_for_candidate_build") -> object:
    return SimpleNamespace(
        status=status,
        sessions=tuple(SimpleNamespace(session_date=item) for item in SESSIONS),
        target_session_count=3,
        evaluation_first_session=SESSIONS[1],
        evaluation_last_session=SESSIONS[-1],
        warmup_first_session=SESSIONS[0],
        warmup_last_session=SESSIONS[0],
        retained_original_session_count=3,
        later_reacquisition_session_count=0,
    )


def _batch_result(
    sessions: tuple[date, ...],
    *,
    failure: date | None = None,
) -> ReconciledEodEditionBatchResultV1:
    items = tuple(
        ReconciledEodEditionBatchSessionResultV1(
            session_date=session.isoformat(),
            status="failed" if session == failure else "published",
            source_provenance="retained_original",
            record_count=0 if session == failure else 10,
            added_record_count=0 if session == failure else 1,
            absent_record_count=0,
            manifest_fingerprint=None if session == failure else "b" * 64,
            failure_code="unexpected_failure" if session == failure else "none",
        )
        for session in sessions
    )
    failed = sum(item.status == "failed" for item in items)
    return ReconciledEodEditionBatchResultV1(
        contract_version="fixture",
        edition_id="edition-v1",
        implementation_revision=REVISION,
        requested_session_count=len(items),
        worker_count=2,
        sessions=items,
        status="stopped_with_failures" if failed else "batch_complete",
        published_session_count=len(items) - failed,
        reused_session_count=0,
        failed_session_count=failed,
        record_count=sum(item.record_count for item in items),
        added_record_count=sum(item.added_record_count for item in items),
        absent_record_count=sum(item.absent_record_count for item in items),
        external_request_count=0,
        canonical_data_write_count=0,
        candidate_session_write_count=len(items) - failed,
        interval_manifest_write_count=0,
        candidate_authority=False,
        production_authority=False,
        research_performance_authorized=False,
    )


class _FakeRepository:
    published = False

    def __init__(self, **values) -> None:
        self.values = values

    def prepare(self) -> None:
        return None

    def publish_interval_manifest(self, **values) -> object:
        type(self).published = True
        assert values["session_dates"] == SESSIONS
        return SimpleNamespace(
            manifest=SimpleNamespace(
                implementation_revision=REVISION,
                warmup_first_session=values["warmup_first_session"],
                warmup_last_session=values["warmup_last_session"],
                sessions=tuple(range(3)),
                retained_original_session_count=3,
                later_reacquisition_session_count=0,
                added_record_count=3,
                absent_record_count=0,
                logical_fingerprint="c" * 64,
            )
        )


def test_builds_all_batches_then_publishes_the_only_completion_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _FakeRepository.published = False
    monkeypatch.setattr(
        module,
        "ParquetReconciledEodEditionCandidateRepository",
        _FakeRepository,
    )
    resolved: list[tuple[date, ...]] = []
    monkeypatch.setattr(
        module,
        "resolve_reconciled_eod_batch_sources",
        lambda **values: resolved.append(values["session_dates"])
        or values["session_dates"],
    )
    monkeypatch.setattr(
        module,
        "run_reconciled_eod_edition_batch",
        lambda **values: _batch_result(tuple(values["sources"])),
    )
    checkpoints = []

    result = run_reconciled_eod_edition_build(
        coverage=_coverage(),  # type: ignore[arg-type]
        data_root=tmp_path / "data",
        candidate_root=tmp_path / "candidate",
        edition_id="edition-v1",
        implementation_revision=REVISION,
        created_at=NOW,
        workers=2,
        batch_size=2,
        progress=checkpoints.append,
    )

    assert resolved == [SESSIONS[:2], SESSIONS[2:]]
    assert [item.batch_number for item in checkpoints] == [1, 2]
    assert _FakeRepository.published is True
    assert result.status == "complete"
    assert result.batch_count == 2
    assert result.published_session_count == 3
    assert result.reused_session_count == 0
    assert result.record_count == 30
    assert result.added_record_count == 3
    assert result.interval_manifest_fingerprint == "c" * 64
    assert result.interval_manifest_write_count == 1
    assert result.external_request_count == 0
    assert result.canonical_data_write_count == 0
    assert result.production_authority is False


def test_failure_stops_before_interval_marker_and_preserves_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _FakeRepository.published = False
    monkeypatch.setattr(
        module,
        "ParquetReconciledEodEditionCandidateRepository",
        _FakeRepository,
    )
    monkeypatch.setattr(
        module,
        "resolve_reconciled_eod_batch_sources",
        lambda **values: values["session_dates"],
    )
    monkeypatch.setattr(
        module,
        "run_reconciled_eod_edition_batch",
        lambda **values: _batch_result(
            tuple(values["sources"]),
            failure=SESSIONS[1],
        ),
    )

    with pytest.raises(ReconciledEodEditionBuildStoppedError) as captured:
        run_reconciled_eod_edition_build(
            coverage=_coverage(),  # type: ignore[arg-type]
            data_root=tmp_path / "data",
            candidate_root=tmp_path / "candidate",
            edition_id="edition-v1",
            implementation_revision=REVISION,
            created_at=NOW,
            workers=2,
            batch_size=2,
        )

    assert captured.value.failed_sessions == (
        (SESSIONS[1].isoformat(), "unexpected_failure"),
    )
    assert captured.value.checkpoint.failed_session_count == 1
    assert _FakeRepository.published is False


@pytest.mark.parametrize(
    ("coverage", "revision", "created_at", "workers", "batch_size", "match"),
    (
        (_coverage(status="incomplete"), REVISION, NOW, 4, 40, "incomplete"),
        (_coverage(), "short", NOW, 4, 40, "Git SHA"),
        (_coverage(), REVISION, NOW.replace(tzinfo=None), 4, 40, "timezone"),
        (_coverage(), REVISION, NOW, 0, 40, "one and four"),
        (_coverage(), REVISION, NOW, 4, 41, "one and forty"),
    ),
)
def test_rejects_unready_or_unbounded_build_inputs(
    coverage,
    revision,
    created_at,
    workers,
    batch_size,
    match,
) -> None:
    with pytest.raises(ReconciledEodEditionBuildError, match=match):
        module._validate_inputs(
            coverage=coverage,
            implementation_revision=revision,
            created_at=created_at,
            workers=workers,
            batch_size=batch_size,
        )


def test_reuse_rejects_different_frozen_creation_time(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
        ReconciledEodSourceProvenance,
    )
    from tip_api.services import reconciled_eod_edition_batch as batch_module
    from tip_api.services.reconciled_eod_edition_batch import (
        ReconciledEodEditionBatchError,
        ReconciledEodEditionSourceV1,
    )

    source = ReconciledEodEditionSourceV1(
        session_date=SESSIONS[0],
        package_path=tmp_path / "package",
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
    )
    manifest = SimpleNamespace(
        implementation_revision=REVISION,
        created_at=NOW + timedelta(seconds=1),
        source_provenance=source.source_provenance,
        source_observed_at=NOW,
        source_package_manifest_sha256="d" * 64,
        source_package_content_sha256="e" * 64,
    )
    monkeypatch.setattr(
        batch_module,
        "read_reconciled_eod_session",
        lambda **_values: SimpleNamespace(manifest=manifest),
    )
    monkeypatch.setattr(
        batch_module,
        "read_grouped_daily_package",
        lambda **_values: SimpleNamespace(
            manifest=SimpleNamespace(
                fetched_at=NOW,
                package_content_sha256="e" * 64,
            ),
            package_manifest_sha256="d" * 64,
        ),
    )
    partition = tmp_path / f"session_date={SESSIONS[0].isoformat()}"
    partition.mkdir()
    repository = SimpleNamespace(
        root=tmp_path,
        edition_id="edition-v1",
        implementation_revision=REVISION,
        created_at=NOW,
    )

    with pytest.raises(ReconciledEodEditionBatchError, match="differs"):
        batch_module._reuse_existing_session(
            repository=repository,
            edition_path=tmp_path,
            source=source,
        )
