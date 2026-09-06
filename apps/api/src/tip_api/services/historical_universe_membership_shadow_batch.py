"""Bounded, resumable batch execution for historical membership shadows."""

from __future__ import annotations

import hashlib
import json
import os
import stat
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
from tip_api.persistence.security_evidence import (
    CompletedSecurityEvidenceSnapshot,
    SecurityEvidenceCorruptionError,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import SameDayCatchupError
from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    identity_source_binding_fingerprint,
)
from tip_api.services.historical_identity_source_custody import (
    HistoricalIdentitySourceCustodyError,
    read_historical_identity_source_custody,
)
from tip_api.services.historical_identity_rebuild_profile_map import (
    HistoricalIdentityRebuildProfile,
    HistoricalIdentityRebuildProfileMapV1,
    profile_binding_for_session,
)
from tip_api.services.historical_universe_membership_shadow import (
    MAXIMUM_SHARED_PANEL_ANALYSIS_SESSIONS,
    HistoricalUniverseMembershipEvidenceQualityError,
    HistoricalUniverseMembershipShadowError,
    HistoricalUniverseMembershipIdentityMismatchError,
    build_historical_universe_membership_shadow,
    build_historical_universe_membership_shadow_from_canonical_source,
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
    identity_rebuild_profile: HistoricalIdentityRebuildProfile | None
    identity_profile_binding_fingerprint: str | None
    status: BatchSessionStatus
    failure_code: str | None
    evaluated_base_count: int | None
    record_count: int | None
    included_counts: tuple[tuple[str, int], ...]
    excluded_counts: tuple[tuple[str, int], ...]
    quarantined_counts: tuple[tuple[str, int], ...]
    logical_fingerprint: str | None
    physical_sha256: str | None
    identity_source_mode: Literal[
        "retained_package", "canonical_source_custody"
    ] | None = None
    identity_source_custody_fingerprint: str | None = None
    methodology_version: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalUniverseMembershipShadowBatchResult:
    identity_profile_map_fingerprint: str
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


@dataclass(frozen=True, slots=True)
class HistoricalUniverseMembershipCanonicalSourceBatchResult:
    identity_source_result_fingerprint: str
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
    identity_profile_map: HistoricalIdentityRebuildProfileMapV1,
    calendar: MarketSessionCalendar | None = None,
) -> HistoricalUniverseMembershipShadowBatchResult:
    """Build one to five adjacent shadows with one shared formal EOD panel."""

    if not isinstance(identity_profile_map, HistoricalIdentityRebuildProfileMapV1):
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch requires a formally validated Identity profile map"
        )
    session_calendar = calendar or ExchangeCalendar()
    source_root, target_root, resolved_packages = _validate_batch_paths(
        data_root=data_root,
        output_root=output_root,
        package_paths=package_paths,
    )
    sessions = tuple(sorted(resolved_packages))
    identity_profile_bindings = {
        session: profile_binding_for_session(identity_profile_map, session)
        for session in sessions
    }
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
                identity_profile_binding=identity_profile_bindings[session],
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
                    identity_rebuild_profile=(
                        identity_profile_bindings[session].rebuild_profile
                    ),
                    identity_profile_binding_fingerprint=(
                        identity_profile_bindings[session].logical_fingerprint
                    ),
                    status="source_validation_failed",
                    failure_code=_source_failure_code(exc),
                    evaluated_base_count=None,
                    record_count=None,
                    included_counts=(),
                    excluded_counts=(),
                    quarantined_counts=(),
                    logical_fingerprint=None,
                    physical_sha256=None,
                    identity_source_mode="retained_package",
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
                identity_rebuild_profile=shadow.identity_rebuild_profile,
                identity_profile_binding_fingerprint=(
                    shadow.identity_profile_binding_fingerprint
                ),
                status=published.status,
                failure_code=None,
                evaluated_base_count=reconstruction.evaluated_base_count,
                record_count=published.record_count,
                included_counts=reconstruction.included_counts,
                excluded_counts=reconstruction.excluded_counts,
                quarantined_counts=reconstruction.quarantined_counts,
                logical_fingerprint=published.logical_fingerprint,
                physical_sha256=published.physical_sha256,
                identity_source_mode="retained_package",
                methodology_version=reconstruction.methodology_version,
            )
        )

    output = tuple(results)
    failed_count = sum(
        item.status == "source_validation_failed" for item in output
    )
    return HistoricalUniverseMembershipShadowBatchResult(
        identity_profile_map_fingerprint=identity_profile_map.logical_fingerprint,
        requested_session_count=len(sessions),
        completed_session_count=len(sessions) - failed_count,
        failed_session_count=failed_count,
        shared_eod_partition_read_count=len(panel.session_reads),
        status=(
            "completed_with_source_failures" if failed_count else "completed"
        ),
        sessions=output,
    )


def run_historical_universe_membership_canonical_source_batch(
    *,
    data_root: Path,
    sessions: tuple[date, ...],
    catalog_as_of_date: date,
    evaluated_at: datetime,
    output_root: Path,
    calendar: MarketSessionCalendar | None = None,
    security_snapshot: CompletedSecurityEvidenceSnapshot | None = None,
) -> HistoricalUniverseMembershipCanonicalSourceBatchResult:
    """Build one to five adjacent shadows from canonical normalized sources."""

    session_calendar = calendar or ExchangeCalendar()
    source_root, target_root, ordered_sessions = _validate_canonical_batch_paths(
        data_root=data_root,
        output_root=output_root,
        sessions=sessions,
    )
    panel = prepare_historical_universe_membership_eod_panel(
        data_root=source_root,
        analysis_sessions=ordered_sessions,
        calendar=session_calendar,
    )
    if security_snapshot is None:
        security_snapshot = read_completed_security_evidence_snapshot(
            source_root,
            as_of_date=catalog_as_of_date,
        )
    elif security_snapshot.manifest.as_of_date != catalog_as_of_date:
        raise HistoricalUniverseMembershipShadowBatchError(
            "shared security catalog as-of date mismatch"
        )
    repository = ParquetHistoricalResearchRepository(
        target_root,
        created_at=evaluated_at,
    )

    results = []
    for session in ordered_sessions:
        try:
            shadow = build_historical_universe_membership_shadow_from_canonical_source(
                data_root=source_root,
                session_date=session,
                catalog_as_of_date=catalog_as_of_date,
                evaluated_at=evaluated_at,
                calendar=session_calendar,
                eod_panel=panel,
                security_snapshot=security_snapshot,
            )
        except (
            HistoricalIdentitySourceCustodyError,
            HistoricalUniverseMembershipShadowError,
            InstrumentMasterSnapshotCorruptionError,
            SecurityEvidenceCorruptionError,
        ) as exc:
            source_profile: HistoricalIdentityRebuildProfile | None = None
            source_binding_fingerprint: str | None = None
            source_custody_fingerprint: str | None = None
            if isinstance(exc, HistoricalUniverseMembershipEvidenceQualityError):
                custody = read_historical_identity_source_custody(
                    data_root=source_root,
                    provider=MASSIVE_PROVIDER_ID,
                    session_date=session,
                )
                source_profile = custody.manifest.identity_rebuild_profile
                source_binding_fingerprint = identity_source_binding_fingerprint(
                    custody.manifest
                )
                source_custody_fingerprint = custody.manifest.logical_fingerprint
            results.append(
                HistoricalUniverseMembershipShadowBatchSession(
                    session_date=session.isoformat(),
                    identity_rebuild_profile=source_profile,
                    identity_profile_binding_fingerprint=(
                        source_binding_fingerprint
                    ),
                    status="source_validation_failed",
                    failure_code=_source_failure_code(exc),
                    evaluated_base_count=None,
                    record_count=None,
                    included_counts=(),
                    excluded_counts=(),
                    quarantined_counts=(),
                    logical_fingerprint=None,
                    physical_sha256=None,
                    identity_source_mode="canonical_source_custody",
                    identity_source_custody_fingerprint=(
                        source_custody_fingerprint
                    ),
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
                "formal membership reread differs from the canonical-source shadow"
            )
        results.append(
            HistoricalUniverseMembershipShadowBatchSession(
                session_date=session.isoformat(),
                identity_rebuild_profile=shadow.identity_rebuild_profile,
                identity_profile_binding_fingerprint=(
                    shadow.identity_profile_binding_fingerprint
                ),
                status=published.status,
                failure_code=None,
                evaluated_base_count=reconstruction.evaluated_base_count,
                record_count=published.record_count,
                included_counts=reconstruction.included_counts,
                excluded_counts=reconstruction.excluded_counts,
                quarantined_counts=reconstruction.quarantined_counts,
                logical_fingerprint=published.logical_fingerprint,
                physical_sha256=published.physical_sha256,
                identity_source_mode=shadow.identity_source_mode,
                identity_source_custody_fingerprint=(
                    shadow.identity_source_custody_fingerprint
                ),
                methodology_version=reconstruction.methodology_version,
            )
        )

    output = tuple(results)
    failed_count = sum(
        item.status == "source_validation_failed" for item in output
    )
    return HistoricalUniverseMembershipCanonicalSourceBatchResult(
        identity_source_result_fingerprint=_batch_source_result_fingerprint(output),
        requested_session_count=len(ordered_sessions),
        completed_session_count=len(ordered_sessions) - failed_count,
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
    target_root = _prepare_owner_only_output_root(output_root)
    return source_root, target_root, resolved_packages


def _validate_canonical_batch_paths(
    *,
    data_root: Path,
    output_root: Path,
    sessions: tuple[date, ...],
) -> tuple[Path, Path, tuple[date, ...]]:
    if (
        not 1 <= len(sessions) <= MAXIMUM_SHARED_PANEL_ANALYSIS_SESSIONS
        or len(set(sessions)) != len(sessions)
    ):
        raise HistoricalUniverseMembershipShadowBatchError(
            "canonical-source batch requires one to five unique sessions"
        )
    source_root = data_root.resolve(strict=True)
    target_root = output_root.resolve(strict=False)
    temporary_root = Path("/tmp").resolve(strict=True)
    if temporary_root not in target_root.parents:
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch output root must be a child of /tmp"
        )
    if _paths_overlap(target_root, source_root):
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch source and output paths must be disjoint"
        )
    target_root = _prepare_owner_only_output_root(output_root)
    return source_root, target_root, tuple(sorted(sessions))


def _prepare_owner_only_output_root(output_root: Path) -> Path:
    temporary_root = Path("/tmp").resolve(strict=True)
    if not output_root.is_absolute():
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch output root must be absolute"
        )
    current = output_root
    while current != temporary_root:
        if current.exists() and current.is_symlink():
            raise HistoricalUniverseMembershipShadowBatchError(
                "batch output path contains a symlink"
            )
        if temporary_root not in current.parents:
            raise HistoricalUniverseMembershipShadowBatchError(
                "batch output root must be a child of /tmp"
            )
        current = current.parent
    if output_root.exists():
        if output_root.is_symlink() or not output_root.is_dir():
            raise HistoricalUniverseMembershipShadowBatchError(
                "batch output root is not a directory"
            )
    else:
        if output_root.parent.is_symlink() or not output_root.parent.is_dir():
            raise HistoricalUniverseMembershipShadowBatchError(
                "batch output parent is unavailable"
            )
        output_root.mkdir(mode=0o700)
    resolved = output_root.resolve(strict=True)
    if (
        resolved != output_root
        or stat.S_IMODE(resolved.stat().st_mode) != 0o700
        or resolved.stat().st_uid != os.geteuid()
    ):
        raise HistoricalUniverseMembershipShadowBatchError(
            "batch output root must be owner-only"
        )
    return resolved


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _source_failure_code(exc: Exception) -> str:
    if isinstance(exc, HistoricalUniverseMembershipIdentityMismatchError):
        return "identity_snapshot_mismatch"
    if isinstance(exc, HistoricalUniverseMembershipEvidenceQualityError):
        return ",".join(exc.failure_codes)
    if isinstance(exc, SameDayCatchupError):
        return "package_custody_failed"
    if isinstance(exc, HistoricalIdentitySourceCustodyError):
        return "canonical_identity_source_unavailable"
    if isinstance(exc, InstrumentMasterSnapshotCorruptionError):
        return "canonical_identity_unavailable"
    if isinstance(exc, SecurityEvidenceCorruptionError):
        return "security_catalog_unavailable"
    return "membership_source_validation_failed"


def _batch_source_result_fingerprint(
    sessions: tuple[HistoricalUniverseMembershipShadowBatchSession, ...],
) -> str:
    values = [
        {
            "session_date": item.session_date,
            "source_status": (
                "source_validation_failed"
                if item.failure_code is not None
                else "validated"
            ),
            "failure_code": item.failure_code,
            "identity_profile_binding_fingerprint": (
                item.identity_profile_binding_fingerprint
            ),
            "identity_source_custody_fingerprint": (
                item.identity_source_custody_fingerprint
            ),
            "methodology_version": item.methodology_version,
        }
        for item in sessions
    ]
    return hashlib.sha256(
        json.dumps(
            values,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
