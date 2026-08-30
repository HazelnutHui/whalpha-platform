from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tip_api.contracts.analytics.v1 import (
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageManifestV1,
    HistoricalDatasetCoverageReferenceV1,
    HistoricalReadinessStatus,
    RESEARCH_REQUIRED_DATASET_FAMILIES,
)
from tip_api.read_models.eod import EodSessionDescriptor
from tip_api.services.strategy_research_readiness import (
    ResearchRequirementState,
    StrategyResearchReadinessError,
    StrategyResearchReadinessNextAction,
    StrategyResearchReadinessStatus,
    assess_strategy_research_readiness,
    canonical_eod_identity_evidence,
)


def _sessions(count: int) -> tuple[date, ...]:
    start = date(2025, 1, 2)
    return tuple(start + timedelta(days=index) for index in range(count))


def _descriptors(count: int) -> tuple[EodSessionDescriptor, ...]:
    return tuple(
        EodSessionDescriptor(
            schema_version="1.0",
            session_date=session,
            record_count=10_000,
            completion_status="completed",
            identity_as_of_date=session,
            available_at=datetime.combine(session, datetime.min.time(), tzinfo=UTC),
            quality_warning_count=0,
        )
        for session in _sessions(count)
    )


def _coverage(count: int = 252) -> HistoricalCoverageManifestV1:
    sessions = _sessions(count)
    datasets = tuple(
        HistoricalDatasetCoverageReferenceV1(
            family=family,
            dataset_path=f"historical/{family.value}",
            record_count=1_000,
            first_session=sessions[0],
            last_session=sessions[-1],
            logical_fingerprint=f"{index:x}" * 64,
            physical_sha256=f"{index + 6:x}" * 64,
            completed=True,
            quarantined_record_count=0,
        )
        for index, family in enumerate(
            sorted(RESEARCH_REQUIRED_DATASET_FAMILIES, key=lambda item: item.value),
            start=1,
        )
    )
    return HistoricalCoverageManifestV1(
        coverage_id="a" * 64,
        sessions=sessions,
        feature_warmup_sessions=20,
        maximum_outcome_horizon_sessions=5,
        matured_signal_session_count=count - 25,
        datasets=datasets,
        readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
        reason_codes=(),
        created_at=datetime(2026, 8, 30, tzinfo=UTC),
        logical_fingerprint="f" * 64,
    )


def test_current_short_history_without_coverage_manifest_is_data_blocked() -> None:
    canonical = canonical_eod_identity_evidence(_descriptors(31))
    assessment = assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical,
    )
    observations = {item.requirement_id: item for item in assessment.observations}

    assert assessment.status is StrategyResearchReadinessStatus.DATA_BLOCKED
    assert (
        assessment.next_action
        is StrategyResearchReadinessNextAction.COMPLETE_HISTORICAL_FOUNDATION
    )
    assert (
        observations["canonical_history_depth"].state
        is ResearchRequirementState.MECHANICS_ONLY
    )
    assert observations["canonical_history_depth"].observed_session_count == 31
    assert (
        observations["daily_point_in_time_membership"].state
        is ResearchRequirementState.BLOCKED
    )
    assert (
        observations["experiment_preregistration"].state
        is ResearchRequirementState.SATISFIED
    )
    assert assessment.development_authorized is False
    assert assessment.performance_claims_authorized is False
    assert assessment.external_request_count == 0
    assert assessment.production_write_count == 0


def test_research_ready_manifest_reaches_separate_development_review_only() -> None:
    canonical = canonical_eod_identity_evidence(_descriptors(252))
    assessment = assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical,
        coverage_manifest=_coverage(),
    )

    assert (
        assessment.status
        is StrategyResearchReadinessStatus.READY_FOR_DEVELOPMENT_REVIEW
    )
    assert (
        assessment.next_action
        is StrategyResearchReadinessNextAction.REVIEW_DEVELOPMENT_ACTIVATION
    )
    assert assessment.reason_codes == (
        "separate_development_activation_review_required",
    )
    assert all(
        item.state is ResearchRequirementState.SATISFIED
        for item in assessment.observations
        if item.required_for_development
    )
    assert assessment.development_authorized is False
    assert assessment.performance_claims_authorized is False


def test_coverage_manifest_cannot_reference_noncanonical_sessions() -> None:
    canonical = canonical_eod_identity_evidence(_descriptors(251))
    with pytest.raises(StrategyResearchReadinessError, match="absent from canonical"):
        assess_strategy_research_readiness(
            experiment=strong_stock_pullback_research_experiment_v1(),
            canonical_evidence=canonical,
            coverage_manifest=_coverage(),
        )


def test_coverage_warmup_and_horizon_must_cover_registered_experiment() -> None:
    canonical = canonical_eod_identity_evidence(_descriptors(252))
    short_warmup = _coverage().model_copy(update={"feature_warmup_sessions": 19})
    with pytest.raises(StrategyResearchReadinessError, match="warmup"):
        assess_strategy_research_readiness(
            experiment=strong_stock_pullback_research_experiment_v1(),
            canonical_evidence=canonical,
            coverage_manifest=short_warmup,
        )

    short_horizon = _coverage().model_copy(
        update={"maximum_outcome_horizon_sessions": 3}
    )
    with pytest.raises(StrategyResearchReadinessError, match="horizon"):
        assess_strategy_research_readiness(
            experiment=strong_stock_pullback_research_experiment_v1(),
            canonical_evidence=canonical,
            coverage_manifest=short_horizon,
        )


def test_assessment_is_deterministic() -> None:
    canonical = canonical_eod_identity_evidence(_descriptors(31))
    first = assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical,
    )
    second = assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical,
    )

    assert first.logical_content_fingerprint == second.logical_content_fingerprint
    assert first.as_dict() == second.as_dict()


def test_canonical_identity_must_bind_every_session_without_future_reference() -> None:
    descriptors = list(_descriptors(2))
    descriptors[1] = replace(
        descriptors[1],
        identity_as_of_date=descriptors[1].session_date + timedelta(days=1),
    )
    with pytest.raises(StrategyResearchReadinessError, match="future Identity"):
        canonical_eod_identity_evidence(tuple(descriptors))


def test_canonical_evidence_rejects_incomplete_or_empty_sessions() -> None:
    descriptor = _descriptors(1)[0]
    with pytest.raises(StrategyResearchReadinessError, match="not completed"):
        canonical_eod_identity_evidence(
            (replace(descriptor, completion_status="partial"),)
        )
    with pytest.raises(StrategyResearchReadinessError, match="no records"):
        canonical_eod_identity_evidence((replace(descriptor, record_count=0),))
