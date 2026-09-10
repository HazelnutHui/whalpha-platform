"""Outcome-blind Strong-Leader Pullback development-admission decision."""

from __future__ import annotations

from datetime import datetime

from tip_api.contracts.analytics.v1.candidate_strategy_development_admission import (
    STRONG_LEADER_PULLBACK_DEVELOPMENT_MINIMUM_SESSIONS,
    DevelopmentAdmissionDecisionStatus,
    StrongLeaderPullbackDevelopmentAdmissionDecisionV1,
    development_admission_fingerprint,
)
from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    DevelopmentCoverageEvidenceStatus,
    StrongLeaderPullbackDevelopmentCoverageCensusV1,
)
from tip_api.contracts.common import normalize_utc_datetime


class StrongLeaderPullbackDevelopmentAdmissionError(RuntimeError):
    """Raised when the census cannot support the bounded rejection decision."""


def decide_strong_leader_pullback_development_admission(
    *,
    census: StrongLeaderPullbackDevelopmentCoverageCensusV1,
    census_physical_sha256: str,
    decision_revision: str,
    decided_at: datetime,
) -> StrongLeaderPullbackDevelopmentAdmissionDecisionV1:
    """Freeze a missingness-only rejection without opening strategy outcomes."""

    census = StrongLeaderPullbackDevelopmentCoverageCensusV1.model_validate(
        census.model_dump(mode="json")
    )
    decided_at = normalize_utc_datetime(decided_at)
    if decided_at < census.calculated_at:
        raise StrongLeaderPullbackDevelopmentAdmissionError(
            "development admission cannot predate its census"
        )
    candidate_sessions = tuple(
        item for item in census.sessions if item.primary_included_count > 0
    )
    complete_sessions = tuple(
        item
        for item in candidate_sessions
        if item.all_required_evidence_complete_count
        == item.primary_included_count
        and item.split_quarantined_path_count == 0
    )
    if (
        len(complete_sessions)
        >= STRONG_LEADER_PULLBACK_DEVELOPMENT_MINIMUM_SESSIONS
    ):
        raise StrongLeaderPullbackDevelopmentAdmissionError(
            "current rejection contract cannot admit a development cohort"
        )

    statuses = {item.family: item.status for item in census.dataset_evidence}
    blockers = {
        "minimum_complete_session_count_not_met",
    }
    if census.all_required_evidence_complete_count == 0:
        blockers.add("all_required_evidence_complete_path_count_zero")
    if census.absent_row_neutrality_unproven_path_count > 0:
        blockers.add("absent_row_neutrality_unproven")
    if census.lifecycle_unavailable_path_count > 0:
        blockers.add("instrument_lifecycle_unavailable")
    if census.split_quarantined_path_count > 0:
        blockers.add("split_path_quarantine_present")
    incomplete_families = tuple(
        family
        for family in (
            "adjustment_ledger",
            "corporate_action",
            "instrument_lifecycle",
        )
        if (
            statuses[family]
            is not DevelopmentCoverageEvidenceStatus.COMPLETE_RECONSTRUCTION_INPUT
        )
    )
    blockers.update(
        f"{family}_not_complete_reconstruction_input"
        for family in incomplete_families
    )

    payload = {
        "decision_revision": decision_revision,
        "decided_at": decided_at,
        "census_source_revision": census.source_revision,
        "census_calculated_at": census.calculated_at,
        "census_logical_fingerprint": census.logical_fingerprint,
        "census_physical_sha256": census_physical_sha256,
        "first_session": census.first_session,
        "last_session": census.last_session,
        "observed_session_count": census.session_count,
        "raw_candidate_session_count": len(candidate_sessions),
        "zero_included_session_count": (
            census.session_count - len(candidate_sessions)
        ),
        "complete_cross_section_session_count": len(complete_sessions),
        "incomplete_cross_section_session_count": (
            len(candidate_sessions) - len(complete_sessions)
        ),
        "raw_feature_path_count": census.raw_feature_path_complete_count,
        "all_required_evidence_complete_path_count": (
            census.all_required_evidence_complete_count
        ),
        "absent_row_neutrality_unproven_path_count": (
            census.absent_row_neutrality_unproven_path_count
        ),
        "lifecycle_unavailable_path_count": (
            census.lifecycle_unavailable_path_count
        ),
        "split_quarantined_path_count": census.split_quarantined_path_count,
        "incomplete_required_dataset_families": incomplete_families,
        "decision_status": (
            DevelopmentAdmissionDecisionStatus.REJECTED_CURRENT_EVIDENCE
        ),
        "blocker_codes": tuple(sorted(blockers)),
    }
    provisional = StrongLeaderPullbackDevelopmentAdmissionDecisionV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackDevelopmentAdmissionDecisionV1(
        **payload,
        logical_fingerprint=development_admission_fingerprint(provisional),
    )
