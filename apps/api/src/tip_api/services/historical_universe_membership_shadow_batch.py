"""Bounded, resumable batch execution for historical membership shadows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Mapping

from tip_api.persistence.instrument_master import (
    InstrumentMasterSnapshotCorruptionError,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.persistence.parquet.security_evidence import (
    read_completed_security_evidence_snapshot,
)
from tip_api.persistence.security_evidence import SecurityEvidenceCorruptionError
from tip_api.providers.massive.same_day_catchup import SameDayCatchupError
from tip_api.services.historical_universe_membership_shadow import (
    MAXIMUM_SHARED_PANEL_ANALYSIS_SESSIONS,
    HistoricalUniverseMembershipShadowError,
    HistoricalUniverseMembershipIdentityMismatchError,
    build_historical_universe_membership_shadow,
    prepare_historical_universe_membership_eod_panel,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar

BatchSessionStatus = Literal[
    "published",
    "already_present",
    "source_validation_failed",
]


class HistoricalUniverseMembershipShadowBatchError(RuntimeError):
    """Fail-closed error at the shared batch/output boundary."""


@dataclass(frozen=True, slots=True)
class HistoricalUniverseMembershipShadowBatchSession:
    session_date: str
    status: BatchSessionStatus
    failure_code: str | None
    evaluated_base_count: int | None
    record_count: int | None
    included_counts: tuple[tuple[str, int], ...]
    excluded_counts: tuple[tuple[str, int], ...]
    quarantined_counts: tuple[tuple[str, int], ...]
    logical_fingerprint: str | None
    physical_sha256: str | None


@dataclass(frozen=True, slots=True)
class HistoricalUniverseMembershipShadowBatchResult:
    requested_session_count: int
    completed_session_count: int
    failed_session_count: int
    shared_eod_partition_read_count: int
    status: Literal["completed", "completed_with_source_failures"]
    sessions: tuple[HistoricalUniverseMembershipShadowBatchSession, ...]
    external_request_count: int = 0
    canonical_data_write_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_historical_universe_membership_shadow_batch(
    *,
    data_root: Path,
    package_paths: Mapping[date, Path],
    catalog_as_of_date: date,
    evaluated_at: datetime,
    output_root: Path,
    calendar: MarketSessionCalendar | None = None,
) -> HistoricalUniverseMembershipShadowBatchResult:
    """Build one to five adjacent shadows with one shared formal EOD panel."""

    session_calendar = calendar or ExchangeCalendar()
    source_root, target_root, resolved_packages = _validate_batch_paths(
        data_root=data_root,
        output_root=output_root,
        package_paths=package_paths,
    )
    sessions = tuple(sorted(resolved_packages))
    panel = prepare_historical_universe_membership_eod_panel(
        data_root=source_root,
        analysis_sessions=sessions,
        calendar=session_calendar,
    )
    security_snapshot = read_completed_security_evidence_snapshot(
        source_root,
        as_of_date=catalog_as_of_date,
    )
    repository = ParquetHistoricalResearchRepository(
        target_root,
        created_at=evaluated_at,
    )

    results = []
    for session in sessions:
        try:
            shadow = build_historical_universe_membership_shadow(
                data_root=source_root,
                package_path=resolved_packages[session],
                session_date=session,
                catalog_as_of_date=catalog_as_of_date,
                evaluated_at=evaluated_at,
                calendar=session_calendar,
                eod_panel=panel,
                security_snapshot=security_snapshot,
            )
        except (
            HistoricalUniverseMembershipShadowError,
            InstrumentMasterSnapshotCorruptionError,
            SameDayCatchupError,
            SecurityEvidenceCorruptionError,
        ) as exc:
            results.append(
                HistoricalUniverseMembershipShadowBatchSession(
                    session_date=session.isoformat(),
                    status="source_validation_failed",
                    failure_code=_source_failure_code(exc),
                    evaluated_base_count=None,
                    record_count=None,
                    included_counts=(),
                    excluded_counts=(),
                    quarantined_counts=(),
                    logical_fingerprint=None,
                    physical_sha256=None,
                )
            )
            continue

        reconstruction = shadow.reconstruction
        published = repository.publish_universe_membership(
            reconstruction.records,
            methodology_version=reconstruction.methodology_version,
            session_date=session,
        )
        reread = repository.read_universe_membership(published.partition_path)
        if reread != reconstruction.records:
            raise HistoricalUniverseMembershipShadowBatchError(
                "formal membership reread differs from the batch shadow"
            )
        results.append(
            HistoricalUniverseMembershipShadowBatchSession(
                session_date=session.isoformat(),
                status=published.status,
                failure_code=None,
                evaluated_base_count=reconstruction.evaluated_base_count,
                record_count=published.record_count,
                included_counts=reconstruction.included_counts,
                excluded_counts=reconstruction.excluded_counts,
                quarantined_counts=reconstruction.quarantined_counts,
                logical_fingerprint=published.logical_fingerprint,
                physical_sha256=published.physical_sha256,
            )
        )

    output = tuple(results)
    failed_count = sum(
        item.status == "source_validation_failed" for item in output
    )
    return HistoricalUniverseMembershipShadowBatchResult(
        requested_session_count=len(sessions),
        completed_session_count=len(sessions) - failed_count,
        failed_session_count=failed_count,
        shared_eod_partition_read_count=len(panel.session_reads),
        status=(
            "completed_with_source_failures" if failed_count else "completed"
        ),
        sessions=output,
    )


def _validate_batch_paths(
    *,
    data_root: Path,
    output_root: Path,
    package_paths: Mapping[date, Path],
) -> tuple[Path, Path, dict[date, Path]]:
    if not 1 <= len(package_paths) <= MAXIMUM_SHARED_PANEL_ANALYSIS_SESSIONS:
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch requires one to five explicit session packages"
        )
    source_root = data_root.resolve(strict=True)
    target_root = output_root.resolve(strict=False)
    temporary_root = Path("/tmp").resolve(strict=True)
    if temporary_root not in target_root.parents:
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch output root must be a child of /tmp"
        )
    resolved_packages = {
        session: path.resolve(strict=True)
        for session, path in package_paths.items()
    }
    sources = (source_root, *resolved_packages.values())
    if any(_paths_overlap(target_root, item) for item in sources):
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch source and output paths must be disjoint"
        )
    return source_root, target_root, resolved_packages


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _source_failure_code(exc: Exception) -> str:
    if isinstance(exc, HistoricalUniverseMembershipIdentityMismatchError):
        return "identity_snapshot_mismatch"
    if isinstance(exc, SameDayCatchupError):
        return "package_custody_failed"
    if isinstance(exc, InstrumentMasterSnapshotCorruptionError):
        return "canonical_identity_unavailable"
    if isinstance(exc, SecurityEvidenceCorruptionError):
        return "security_catalog_unavailable"
    return "membership_source_validation_failed"
