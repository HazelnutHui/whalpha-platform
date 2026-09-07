"""Prepare one prospective daily Membership candidate without canonical writes."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    UniverseMembershipDecisionV1,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.historical_universe_membership_shadow import (
    CANONICAL_SOURCE_HISTORICAL_METHODOLOGY_VERSION,
)
from tip_api.services.historical_universe_membership_shadow_batch import (
    run_historical_universe_membership_canonical_source_batch,
)
from tip_api.services.universe_membership_canonical import (
    PUBLICATION_DIRECTORY,
    PUBLICATION_POLICY_ID,
    read_canonical_universe_membership,
)
from tip_api.services.universe_membership_knowledge_time import (
    assess_universe_membership_knowledge_time,
)


CONTRACT_VERSION = "daily-universe-membership-continuation/1.0"
METHODOLOGY_VERSION = CANONICAL_SOURCE_HISTORICAL_METHODOLOGY_VERSION


class DailyUniverseMembershipContinuationError(RuntimeError):
    """Raised when prospective daily Membership cannot remain evidence-safe."""


@dataclass(frozen=True, slots=True)
class DailyUniverseMembershipContinuationResult:
    status: Literal[
        "candidate_ready_for_publication_plan",
        "outcome_only_candidate",
        "canonical_already_complete",
    ]
    session_date: str
    methodology_version: str
    candidate_partition_path: str | None
    candidate_status: str | None
    record_count: int
    membership_logical_fingerprint: str
    point_in_time_eligibility: str
    knowledge_time_assessment_fingerprint: str
    canonical_publication_fingerprint: str | None
    external_request_count: int = 0
    canonical_data_write_count: int = 0
    publication_authorized: bool = False
    historical_coverage_authorized: bool = False
    research_performance_authorized: bool = False
    scheduler_enabled: bool = False
    website_pipeline_blocked: bool = False
    contract_version: str = CONTRACT_VERSION

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def prepare_daily_universe_membership_candidate(
    *,
    data_root: Path,
    session_date: date,
    catalog_as_of_date: date,
    evaluated_at: datetime,
    assessed_at: datetime,
    candidate_root: Path,
    provider: str = MASSIVE_PROVIDER_ID,
) -> DailyUniverseMembershipContinuationResult:
    """Build or reuse one daily candidate and prove its next-open eligibility."""

    if provider != MASSIVE_PROVIDER_ID:
        raise DailyUniverseMembershipContinuationError(
            "daily Membership requires the canonical provider"
        )
    evaluated_at = normalize_utc_datetime(evaluated_at)
    assessed_at = normalize_utc_datetime(assessed_at)
    if assessed_at < evaluated_at:
        raise DailyUniverseMembershipContinuationError(
            "Membership assessment cannot precede evaluation"
        )

    canonical_membership, canonical_publication = _canonical_targets(
        data_root=data_root,
        session_date=session_date,
    )
    membership_exists = os.path.lexists(canonical_membership)
    publication_exists = os.path.lexists(canonical_publication)
    if membership_exists or publication_exists:
        if not membership_exists or not publication_exists:
            raise DailyUniverseMembershipContinuationError(
                "canonical Membership is incomplete; use exact-plan recovery"
            )
        canonical = read_canonical_universe_membership(
            data_root=data_root,
            methodology_version=METHODOLOGY_VERSION,
            session_date=session_date,
            provider=provider,
        )
        assessment = canonical.publication.knowledge_time_assessment
        return DailyUniverseMembershipContinuationResult(
            status="canonical_already_complete",
            session_date=session_date.isoformat(),
            methodology_version=METHODOLOGY_VERSION,
            candidate_partition_path=None,
            candidate_status=None,
            record_count=len(canonical.records),
            membership_logical_fingerprint=(
                canonical.membership_manifest.logical_fingerprint
            ),
            point_in_time_eligibility=(
                canonical.publication.point_in_time_eligibility.value
            ),
            knowledge_time_assessment_fingerprint=(
                assessment.logical_fingerprint
            ),
            canonical_publication_fingerprint=(
                canonical.publication.logical_fingerprint
            ),
        )

    candidate_partition = _candidate_partition(
        candidate_root=candidate_root,
        session_date=session_date,
    )
    if os.path.lexists(candidate_partition):
        records, manifest = _read_candidate(
            candidate_root=candidate_root,
            candidate_partition=candidate_partition,
            session_date=session_date,
        )
        candidate_status = "already_present"
    else:
        batch = run_historical_universe_membership_canonical_source_batch(
            data_root=data_root,
            sessions=(session_date,),
            catalog_as_of_date=catalog_as_of_date,
            evaluated_at=evaluated_at,
            output_root=candidate_root,
        )
        if (
            batch.status != "completed"
            or batch.completed_session_count != 1
            or batch.failed_session_count != 0
            or len(batch.sessions) != 1
            or batch.sessions[0].logical_fingerprint is None
        ):
            failure = (
                batch.sessions[0].failure_code
                if batch.sessions
                else "membership_candidate_not_completed"
            )
            raise DailyUniverseMembershipContinuationError(
                f"daily Membership candidate failed: {failure}"
            )
        candidate_status = batch.sessions[0].status
        records, manifest = _read_candidate(
            candidate_root=candidate_root,
            candidate_partition=candidate_partition,
            session_date=session_date,
        )

    assessment = assess_universe_membership_knowledge_time(
        data_root=data_root,
        membership_root=candidate_root,
        membership_partition_path=candidate_partition,
        provider=provider,
        assessed_at=assessed_at,
    )
    signal_eligible = (
        assessment.point_in_time_eligibility
        is PointInTimeEligibility.SIGNAL_ELIGIBLE
    )
    return DailyUniverseMembershipContinuationResult(
        status=(
            "candidate_ready_for_publication_plan"
            if signal_eligible
            else "outcome_only_candidate"
        ),
        session_date=session_date.isoformat(),
        methodology_version=METHODOLOGY_VERSION,
        candidate_partition_path=str(candidate_partition),
        candidate_status=candidate_status,
        record_count=len(records),
        membership_logical_fingerprint=manifest.logical_fingerprint,
        point_in_time_eligibility=assessment.point_in_time_eligibility.value,
        knowledge_time_assessment_fingerprint=assessment.logical_fingerprint,
        canonical_publication_fingerprint=None,
    )


def _candidate_partition(*, candidate_root: Path, session_date: date) -> Path:
    return (
        candidate_root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={session_date.isoformat()}"
    )


def _canonical_targets(*, data_root: Path, session_date: date) -> tuple[Path, Path]:
    membership = (
        data_root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={session_date.isoformat()}"
    )
    publication = (
        data_root
        / "market-data"
        / PUBLICATION_DIRECTORY
        / "schema_version=1"
        / f"policy_id={PUBLICATION_POLICY_ID}"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={session_date.isoformat()}"
    )
    return membership, publication


def _read_candidate(
    *,
    candidate_root: Path,
    candidate_partition: Path,
    session_date: date,
) -> tuple[
    tuple[UniverseMembershipDecisionV1, ...],
    UniverseMembershipPartitionManifestV1,
]:
    try:
        records = ParquetHistoricalResearchRepository(
            candidate_root
        ).read_universe_membership(candidate_partition)
        manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
            (candidate_partition / MANIFEST_FILE_NAME).read_bytes()
        )
    except Exception as exc:
        raise DailyUniverseMembershipContinuationError(
            "daily Membership candidate is incomplete or corrupt"
        ) from exc
    if (
        not records
        or manifest.session_date != session_date
        or manifest.methodology_version != METHODOLOGY_VERSION
        or manifest.record_count != len(records)
    ):
        raise DailyUniverseMembershipContinuationError(
            "daily Membership candidate boundary differs"
        )
    return records, manifest
