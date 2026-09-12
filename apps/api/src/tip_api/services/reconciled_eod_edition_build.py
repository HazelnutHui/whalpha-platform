"""Resumable complete-interval construction for Reconciled EOD Edition."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from tip_api.contracts.market_data.v1.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageV1,
)
from tip_api.persistence.parquet.reconciled_eod_edition import (
    ParquetReconciledEodEditionCandidateRepository,
)
from tip_api.services.reconciled_eod_edition_batch import (
    MAXIMUM_SESSIONS_PER_BATCH,
    MAXIMUM_WORKERS,
    ReconciledEodEditionBatchResultV1,
    run_reconciled_eod_edition_batch,
)
from tip_api.services.reconciled_eod_source_coverage import (
    resolve_reconciled_eod_batch_sources,
)


CONTRACT_VERSION = "reconciled-eod-price-bar-edition-build-result/1.1"
MAXIMUM_INTERVAL_SESSIONS = 1_500
ProgressCallback = Callable[["ReconciledEodEditionBuildCheckpointV1"], None]


class ReconciledEodEditionBuildError(RuntimeError):
    """Fail-closed error for complete-interval candidate construction."""


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionBuildCheckpointV1:
    batch_number: int
    first_session: str
    last_session: str
    requested_session_count: int
    published_session_count: int
    reused_session_count: int
    failed_session_count: int
    record_count: int
    added_record_count: int
    absent_record_count: int
    status: str


class ReconciledEodEditionBuildStoppedError(ReconciledEodEditionBuildError):
    """Construction stopped after retaining all successful session partitions."""

    def __init__(
        self,
        *,
        checkpoint: ReconciledEodEditionBuildCheckpointV1,
        failed_sessions: tuple[tuple[str, str], ...],
        completed_checkpoints: tuple[ReconciledEodEditionBuildCheckpointV1, ...],
    ) -> None:
        self.checkpoint = checkpoint
        self.failed_sessions = failed_sessions
        self.completed_checkpoints = completed_checkpoints
        super().__init__(
            "Reconciled EOD edition construction stopped with session failures"
        )


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionBuildResultV1:
    contract_version: str
    status: Literal["complete"]
    edition_id: str
    implementation_revision: str
    evaluation_first_session: str
    evaluation_last_session: str
    warmup_first_session: str | None
    warmup_last_session: str | None
    target_session_count: int
    batch_count: int
    batch_size: int
    worker_count: int
    published_session_count: int
    reused_session_count: int
    record_count: int
    added_record_count: int
    absent_record_count: int
    retained_original_session_count: int
    later_reacquisition_session_count: int
    interval_manifest_fingerprint: str
    checkpoints: tuple[ReconciledEodEditionBuildCheckpointV1, ...]
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    candidate_session_write_count: int = 0
    interval_manifest_write_count: Literal[1] = 1
    candidate_authority: Literal[False] = False
    production_authority: Literal[False] = False
    research_performance_authorized: Literal[False] = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_reconciled_eod_edition_build(
    *,
    coverage: ReconciledEodSourceCoverageV1,
    data_root: Path,
    candidate_root: Path,
    edition_id: str,
    implementation_revision: str,
    created_at: datetime,
    workers: int = MAXIMUM_WORKERS,
    batch_size: int = MAXIMUM_SESSIONS_PER_BATCH,
    progress: ProgressCallback | None = None,
) -> ReconciledEodEditionBuildResultV1:
    """Build and seal one full edition from exact selected coverage sources."""

    _validate_inputs(
        coverage=coverage,
        implementation_revision=implementation_revision,
        created_at=created_at,
        workers=workers,
        batch_size=batch_size,
    )
    sessions = tuple(item.session_date for item in coverage.sessions)
    repository = ParquetReconciledEodEditionCandidateRepository(
        root=candidate_root,
        edition_id=edition_id,
        implementation_revision=implementation_revision,
        created_at=created_at,
    )
    repository.prepare()

    checkpoints: list[ReconciledEodEditionBuildCheckpointV1] = []
    published = 0
    reused = 0
    records = 0
    additions = 0
    absences = 0
    for offset in range(0, len(sessions), batch_size):
        batch_number = len(checkpoints) + 1
        batch_sessions = sessions[offset : offset + batch_size]
        sources = resolve_reconciled_eod_batch_sources(
            coverage=coverage,
            data_root=data_root,
            session_dates=batch_sessions,
        )
        result = run_reconciled_eod_edition_batch(
            data_root=data_root,
            candidate_root=candidate_root,
            edition_id=edition_id,
            implementation_revision=implementation_revision,
            sources=sources,
            workers=workers,
            created_at=created_at,
        )
        checkpoint = _checkpoint(batch_number=batch_number, result=result)
        checkpoints.append(checkpoint)
        if progress is not None:
            progress(checkpoint)
        if result.failed_session_count:
            failed_sessions = tuple(
                (item.session_date, item.failure_code)
                for item in result.sessions
                if item.status == "failed"
            )
            raise ReconciledEodEditionBuildStoppedError(
                checkpoint=checkpoint,
                failed_sessions=failed_sessions,
                completed_checkpoints=tuple(checkpoints),
            )
        published += result.published_session_count
        reused += result.reused_session_count
        records += result.record_count
        additions += result.added_record_count
        absences += result.absent_record_count

    completed = repository.publish_interval_manifest(
        session_dates=sessions,
        evaluation_first_session=coverage.evaluation_first_session,
        evaluation_last_session=coverage.evaluation_last_session,
        warmup_first_session=coverage.warmup_first_session,
        warmup_last_session=coverage.warmup_last_session,
    )
    manifest = completed.manifest
    if (
        manifest.implementation_revision != implementation_revision
        or manifest.warmup_first_session != coverage.warmup_first_session
        or manifest.warmup_last_session != coverage.warmup_last_session
        or len(manifest.sessions) != coverage.target_session_count
        or manifest.retained_original_session_count
        != coverage.retained_original_session_count
        or manifest.later_reacquisition_session_count
        != coverage.later_reacquisition_session_count
        or manifest.added_record_count != additions
        or manifest.absent_record_count != absences
    ):
        raise ReconciledEodEditionBuildError(
            "completed Reconciled EOD interval differs from construction evidence"
        )
    return ReconciledEodEditionBuildResultV1(
        contract_version=CONTRACT_VERSION,
        status="complete",
        edition_id=edition_id,
        implementation_revision=implementation_revision,
        evaluation_first_session=coverage.evaluation_first_session.isoformat(),
        evaluation_last_session=coverage.evaluation_last_session.isoformat(),
        warmup_first_session=(
            coverage.warmup_first_session.isoformat()
            if coverage.warmup_first_session is not None
            else None
        ),
        warmup_last_session=(
            coverage.warmup_last_session.isoformat()
            if coverage.warmup_last_session is not None
            else None
        ),
        target_session_count=coverage.target_session_count,
        batch_count=len(checkpoints),
        batch_size=batch_size,
        worker_count=workers,
        published_session_count=published,
        reused_session_count=reused,
        record_count=records,
        added_record_count=additions,
        absent_record_count=absences,
        retained_original_session_count=manifest.retained_original_session_count,
        later_reacquisition_session_count=(
            manifest.later_reacquisition_session_count
        ),
        interval_manifest_fingerprint=manifest.logical_fingerprint,
        checkpoints=tuple(checkpoints),
        candidate_session_write_count=published,
    )


def _validate_inputs(
    *,
    coverage: ReconciledEodSourceCoverageV1,
    implementation_revision: str,
    created_at: datetime,
    workers: int,
    batch_size: int,
) -> None:
    if coverage.status != "ready_for_candidate_build":
        raise ReconciledEodEditionBuildError(
            "incomplete source coverage cannot feed full-edition construction"
        )
    if not 1 <= coverage.target_session_count <= MAXIMUM_INTERVAL_SESSIONS:
        raise ReconciledEodEditionBuildError(
            "full-edition session count exceeds the bounded interval"
        )
    if (
        len(implementation_revision) != 40
        or any(character not in "0123456789abcdef" for character in implementation_revision)
    ):
        raise ReconciledEodEditionBuildError(
            "implementation revision must be a full lowercase Git SHA"
        )
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ReconciledEodEditionBuildError(
            "full-edition creation time must be timezone-aware"
        )
    if not 1 <= workers <= MAXIMUM_WORKERS:
        raise ReconciledEodEditionBuildError(
            "full-edition worker count must be between one and four"
        )
    if not 1 <= batch_size <= MAXIMUM_SESSIONS_PER_BATCH:
        raise ReconciledEodEditionBuildError(
            "full-edition batch size must be between one and forty"
        )


def _checkpoint(
    *,
    batch_number: int,
    result: ReconciledEodEditionBatchResultV1,
) -> ReconciledEodEditionBuildCheckpointV1:
    return ReconciledEodEditionBuildCheckpointV1(
        batch_number=batch_number,
        first_session=result.sessions[0].session_date,
        last_session=result.sessions[-1].session_date,
        requested_session_count=result.requested_session_count,
        published_session_count=result.published_session_count,
        reused_session_count=result.reused_session_count,
        failed_session_count=result.failed_session_count,
        record_count=result.record_count,
        added_record_count=result.added_record_count,
        absent_record_count=result.absent_record_count,
        status=result.status,
    )
