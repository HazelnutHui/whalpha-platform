"""Offline point-in-time eligibility gate for Universe Membership evidence."""

from __future__ import annotations

import hashlib
import os
import stat
from datetime import datetime
from pathlib import Path

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    IdentitySourceCustodyManifest,
    UniverseMembershipKnowledgeTimeAssessmentV1,
    UniverseMembershipPartitionManifestV1,
    build_universe_membership_knowledge_time_assessment,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    ParquetHistoricalResearchRepository,
)
from tip_api.services.historical_identity_source_custody import (
    read_historical_identity_source_custody,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


class UniverseMembershipKnowledgeTimeError(RuntimeError):
    """Raised when timing evidence is incomplete, unsafe, or inconsistent."""


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")


def assess_universe_membership_knowledge_time(
    *,
    data_root: Path,
    membership_root: Path,
    membership_partition_path: Path,
    provider: str,
    assessed_at: datetime,
    calendar: MarketSessionCalendar | None = None,
) -> UniverseMembershipKnowledgeTimeAssessmentV1:
    """Formally reread one partition and classify next-open signal usability."""

    assessed_at = normalize_utc_datetime(assessed_at)
    root = _validated_membership_root(membership_root)
    partition = membership_partition_path.resolve(strict=True)
    if root != membership_root or root not in partition.parents:
        raise UniverseMembershipKnowledgeTimeError(
            "membership partition escaped its declared root"
        )
    records = ParquetHistoricalResearchRepository(root).read_universe_membership(
        partition
    )
    if not records:
        raise UniverseMembershipKnowledgeTimeError("membership partition is empty")

    manifest_path = partition / MANIFEST_FILE_NAME
    parquet_path = partition / PARQUET_FILE_NAME
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
            manifest_bytes
        )
    except Exception as exc:
        raise UniverseMembershipKnowledgeTimeError(
            "membership completion manifest is invalid"
        ) from exc
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()

    source = read_historical_identity_source_custody(
        data_root=data_root,
        provider=provider,
        session_date=manifest.session_date,
    ).manifest
    _validate_source_binding(manifest, source)

    session_calendar = calendar or ExchangeCalendar()
    if session_calendar.calendar_id != "XNYS":
        raise UniverseMembershipKnowledgeTimeError(
            "membership timing policy requires XNYS"
        )
    next_session = session_calendar.next_session(manifest.session_date)
    information_cutoff = session_calendar.session_close(manifest.session_date)
    next_open = session_calendar.session_open(next_session)
    if manifest.source_data_cutoff < information_cutoff:
        raise UniverseMembershipKnowledgeTimeError(
            "membership source cutoff precedes the represented market close"
        )

    source_is_contemporaneous = (
        source.point_in_time_eligibility == "eligible_at_source_observed_at"
    )
    completed_before_open = manifest.evaluated_at < next_open
    if source_is_contemporaneous and completed_before_open:
        eligibility = PointInTimeEligibility.SIGNAL_ELIGIBLE
        reasons = ("source_and_evaluation_completed_before_next_session_open",)
    else:
        eligibility = PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY
        reason_set = set()
        if not source_is_contemporaneous:
            reason_set.add("identity_source_outcome_reconciliation_only")
        if not completed_before_open:
            reason_set.add("membership_evaluation_not_before_next_session_open")
        reasons = tuple(sorted(reason_set))

    return build_universe_membership_knowledge_time_assessment(
        membership_logical_fingerprint=manifest.logical_fingerprint,
        membership_manifest_sha256=manifest_sha,
        membership_parquet_sha256=_file_sha256(parquet_path),
        identity_source_logical_fingerprint=source.logical_fingerprint,
        identity_source_contract_version=source.contract_version,
        identity_source_point_in_time_eligibility=(
            source.point_in_time_eligibility
        ),
        methodology_version=manifest.methodology_version,
        session_date=manifest.session_date,
        market_information_cutoff_at=information_cutoff,
        source_data_cutoff=manifest.source_data_cutoff,
        evaluated_at=manifest.evaluated_at,
        entry_session_date=next_session,
        next_session_open_at=next_open,
        assessed_at=assessed_at,
        calendar_id=session_calendar.calendar_id,
        calendar_version=session_calendar.calendar_version,
        point_in_time_eligibility=eligibility,
        reason_codes=reasons,
    )


def _validate_source_binding(
    membership: UniverseMembershipPartitionManifestV1,
    source: IdentitySourceCustodyManifest,
) -> None:
    if source.as_of_date != membership.session_date:
        raise UniverseMembershipKnowledgeTimeError(
            "Identity source session differs from Membership"
        )
    if source.logical_fingerprint not in membership.source_fingerprints:
        raise UniverseMembershipKnowledgeTimeError(
            "Membership does not bind the Identity source custody fingerprint"
        )
    if source.source_package_fetched_at > membership.source_data_cutoff:
        raise UniverseMembershipKnowledgeTimeError(
            "Membership cutoff precedes its Identity source observation"
        )


def _validated_membership_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise UniverseMembershipKnowledgeTimeError(
            "membership root is unavailable or unsafe"
        )
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise UniverseMembershipKnowledgeTimeError(
            "membership root must be an exact absolute path"
        )
    if resolved == APPROVED_DATA_ROOT:
        return resolved
    try:
        validate_offline_artifact_location(
            resolved,
            persistent_names={"universe-membership-candidate"},
            allow_tmp_descendants=True,
        )
    except OfflineArtifactCustodyError as exc:
        raise UniverseMembershipKnowledgeTimeError(
            "membership root is outside approved boundaries"
        ) from exc
    root_stat = resolved.stat()
    if root_stat.st_uid != os.getuid() or stat.S_IMODE(root_stat.st_mode) != 0o700:
        raise UniverseMembershipKnowledgeTimeError(
            "temporary membership root must be owner-only"
        )
    return resolved


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
