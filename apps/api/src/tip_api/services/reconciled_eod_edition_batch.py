"""Bounded, resumable construction of Reconciled EOD Edition sessions."""

from __future__ import annotations

import multiprocessing
import os
import socket
import stat
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Literal

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
)
from tip_api.persistence.parquet.reconciled_eod_edition import (
    ParquetReconciledEodEditionCandidateRepository,
    ReconciledEodEditionPersistenceError,
    read_reconciled_eod_session,
)
from tip_api.providers.massive.same_day_catchup import (
    SameDayCatchupError,
    read_grouped_daily_package,
)
from tip_api.services.reconciled_eod_edition import (
    ReconciledEodEditionError,
    build_reconciled_eod_session_candidate,
)


CONTRACT_VERSION = "reconciled-eod-price-bar-edition-batch-result/1.1"
MAXIMUM_SESSIONS_PER_BATCH = 40
MAXIMUM_WORKERS = 4
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")


class ReconciledEodEditionBatchError(RuntimeError):
    """Fail-closed error for a bounded edition-construction batch."""


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionSourceV1:
    session_date: date
    package_path: Path
    source_provenance: ReconciledEodSourceProvenance


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionBatchSessionResultV1:
    session_date: str
    status: Literal["published", "already_present", "failed"]
    source_provenance: str
    record_count: int
    added_record_count: int
    absent_record_count: int
    manifest_fingerprint: str | None
    failure_code: Literal[
        "none",
        "source_package_invalid",
        "candidate_validation_failed",
        "candidate_persistence_failed",
        "unexpected_failure",
    ]


@dataclass(frozen=True, slots=True)
class ReconciledEodEditionBatchResultV1:
    contract_version: str
    edition_id: str
    implementation_revision: str
    requested_session_count: int
    worker_count: int
    sessions: tuple[ReconciledEodEditionBatchSessionResultV1, ...]
    status: Literal["batch_complete", "stopped_with_failures"]
    published_session_count: int
    reused_session_count: int
    failed_session_count: int
    record_count: int
    added_record_count: int
    absent_record_count: int
    external_request_count: int
    canonical_data_write_count: int
    candidate_session_write_count: int
    interval_manifest_write_count: int
    candidate_authority: bool
    production_authority: bool
    research_performance_authorized: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _BuildJob:
    data_root: Path
    candidate_root: Path
    edition_id: str
    implementation_revision: str
    created_at: datetime | None
    source: ReconciledEodEditionSourceV1


def run_reconciled_eod_edition_batch(
    *,
    data_root: Path,
    candidate_root: Path,
    edition_id: str,
    implementation_revision: str,
    sources: tuple[ReconciledEodEditionSourceV1, ...],
    workers: int = 1,
    created_at: datetime | None = None,
) -> ReconciledEodEditionBatchResultV1:
    """Build at most forty exact sessions without writing canonical data."""

    _validate_inputs(
        data_root=data_root,
        sources=sources,
        workers=workers,
    )
    repository = ParquetReconciledEodEditionCandidateRepository(
        root=candidate_root,
        edition_id=edition_id,
        implementation_revision=implementation_revision,
        created_at=created_at,
    )
    edition_path = repository.prepare()
    results: list[ReconciledEodEditionBatchSessionResultV1] = []
    pending: list[_BuildJob] = []
    for source in sources:
        reused = _reuse_existing_session(
            repository=repository,
            edition_path=edition_path,
            source=source,
        )
        if reused is not None:
            results.append(reused)
        else:
            pending.append(
                _BuildJob(
                    data_root=data_root,
                    candidate_root=candidate_root,
                    edition_id=edition_id,
                    implementation_revision=implementation_revision,
                    created_at=created_at,
                    source=source,
                )
            )

    if workers == 1:
        with _network_prohibited():
            results.extend(_build_and_publish(job) for job in pending)
    elif pending:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_disable_network_in_worker,
        ) as executor:
            results.extend(executor.map(_build_and_publish, pending))

    ordered = tuple(sorted(results, key=lambda item: item.session_date))
    expected_sessions = tuple(item.session_date.isoformat() for item in sources)
    actual_sessions = tuple(item.session_date for item in ordered)
    actual_provenance = tuple(item.source_provenance for item in ordered)
    expected_provenance = tuple(item.source_provenance.value for item in sources)
    if (
        actual_sessions != expected_sessions
        or actual_provenance != expected_provenance
    ):
        raise ReconciledEodEditionBatchError(
            "reconciled EOD batch result bindings differ"
        )
    failed = sum(item.status == "failed" for item in ordered)
    published = sum(item.status == "published" for item in ordered)
    reused = sum(item.status == "already_present" for item in ordered)
    if published + reused + failed != len(ordered):
        raise ReconciledEodEditionBatchError(
            "reconciled EOD batch result coverage differs"
        )
    return ReconciledEodEditionBatchResultV1(
        contract_version=CONTRACT_VERSION,
        edition_id=edition_id,
        implementation_revision=implementation_revision,
        requested_session_count=len(sources),
        worker_count=workers,
        sessions=ordered,
        status="stopped_with_failures" if failed else "batch_complete",
        published_session_count=published,
        reused_session_count=reused,
        failed_session_count=failed,
        record_count=sum(item.record_count for item in ordered),
        added_record_count=sum(item.added_record_count for item in ordered),
        absent_record_count=sum(item.absent_record_count for item in ordered),
        external_request_count=0,
        canonical_data_write_count=0,
        candidate_session_write_count=published,
        interval_manifest_write_count=0,
        candidate_authority=False,
        production_authority=False,
        research_performance_authorized=False,
    )


def _validate_inputs(
    *,
    data_root: Path,
    sources: tuple[ReconciledEodEditionSourceV1, ...],
    workers: int,
) -> None:
    if (
        not data_root.is_absolute()
        or data_root.is_symlink()
        or not data_root.is_dir()
    ):
        raise ReconciledEodEditionBatchError(
            "reconciled EOD canonical data root is unavailable"
        )
    try:
        resolved_data_root = data_root.resolve(strict=True)
        approved_data_root = APPROVED_DATA_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ReconciledEodEditionBatchError(
            "reconciled EOD canonical data root is unavailable"
        ) from exc
    if resolved_data_root != data_root or resolved_data_root != approved_data_root:
        raise ReconciledEodEditionBatchError(
            "reconciled EOD canonical data root is not the approved Dell root"
        )
    if not 1 <= workers <= MAXIMUM_WORKERS:
        raise ReconciledEodEditionBatchError(
            "reconciled EOD batch workers must be between one and four"
        )
    if not 1 <= len(sources) <= MAXIMUM_SESSIONS_PER_BATCH:
        raise ReconciledEodEditionBatchError(
            "reconciled EOD batch must contain between one and forty sessions"
        )
    sessions = tuple(item.session_date for item in sources)
    if sessions != tuple(sorted(set(sessions))):
        raise ReconciledEodEditionBatchError(
            "reconciled EOD batch sessions must be unique and ordered"
        )
    for source in sources:
        path = source.package_path
        if not path.is_absolute() or path.is_symlink() or not path.is_dir():
            raise ReconciledEodEditionBatchError(
                "reconciled EOD source package is unavailable"
            )
        metadata = path.stat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise ReconciledEodEditionBatchError(
                "reconciled EOD source package custody differs"
            )


def _reuse_existing_session(
    *,
    repository: ParquetReconciledEodEditionCandidateRepository,
    edition_path: Path,
    source: ReconciledEodEditionSourceV1,
) -> ReconciledEodEditionBatchSessionResultV1 | None:
    partition = edition_path / f"session_date={source.session_date.isoformat()}"
    if not os.path.lexists(partition):
        return None
    completed = read_reconciled_eod_session(
        root=repository.root,
        edition_id=repository.edition_id,
        session_date=source.session_date,
    )
    package = read_grouped_daily_package(
        package_path=source.package_path,
        expected_session=source.session_date,
    )
    manifest = completed.manifest
    if (
        manifest.implementation_revision != repository.implementation_revision
        or (
            repository.created_at is not None
            and manifest.created_at != repository.created_at
        )
        or manifest.source_provenance != source.source_provenance
        or manifest.source_observed_at != package.manifest.fetched_at
        or manifest.source_package_manifest_sha256
        != package.package_manifest_sha256
        or manifest.source_package_content_sha256
        != package.manifest.package_content_sha256
    ):
        raise ReconciledEodEditionBatchError(
            "existing reconciled EOD session differs from selected source"
        )
    return ReconciledEodEditionBatchSessionResultV1(
        session_date=source.session_date.isoformat(),
        status="already_present",
        source_provenance=source.source_provenance.value,
        record_count=manifest.diff.rebuilt_record_count,
        added_record_count=manifest.diff.added_record_count,
        absent_record_count=manifest.diff.absent_record_count,
        manifest_fingerprint=manifest.logical_fingerprint,
        failure_code="none",
    )


def _build_and_publish(
    job: _BuildJob,
) -> ReconciledEodEditionBatchSessionResultV1:
    source = job.source
    try:
        with TemporaryDirectory(prefix="tip-reconciled-eod-") as temporary:
            candidate = build_reconciled_eod_session_candidate(
                data_root=job.data_root,
                package_path=source.package_path,
                working_root=Path(temporary),
                session_date=source.session_date,
                source_provenance=source.source_provenance,
            )
            result = ParquetReconciledEodEditionCandidateRepository(
                root=job.candidate_root,
                edition_id=job.edition_id,
                implementation_revision=job.implementation_revision,
                created_at=job.created_at,
            ).publish_session(candidate)
        return ReconciledEodEditionBatchSessionResultV1(
            session_date=source.session_date.isoformat(),
            status=result.status,
            source_provenance=source.source_provenance.value,
            record_count=result.record_count,
            added_record_count=candidate.diff.added_record_count,
            absent_record_count=candidate.diff.absent_record_count,
            manifest_fingerprint=result.manifest_fingerprint,
            failure_code="none",
        )
    except SameDayCatchupError:
        return _failed_result(source, "source_package_invalid")
    except ReconciledEodEditionError:
        return _failed_result(source, "candidate_validation_failed")
    except ReconciledEodEditionPersistenceError:
        return _failed_result(source, "candidate_persistence_failed")
    except Exception:
        return _failed_result(source, "unexpected_failure")


def _failed_result(
    source: ReconciledEodEditionSourceV1,
    failure_code: Literal[
        "source_package_invalid",
        "candidate_validation_failed",
        "candidate_persistence_failed",
        "unexpected_failure",
    ],
) -> ReconciledEodEditionBatchSessionResultV1:
    return ReconciledEodEditionBatchSessionResultV1(
        session_date=source.session_date.isoformat(),
        status="failed",
        source_provenance=source.source_provenance.value,
        record_count=0,
        added_record_count=0,
        absent_record_count=0,
        manifest_fingerprint=None,
        failure_code=failure_code,
    )


def _disable_network_in_worker() -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise ReconciledEodEditionBatchError(
            "network is disabled in reconciled EOD batch workers"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo
    _disable_network_in_worker()
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
