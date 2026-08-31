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
from tip_api.services.strategy_research_development_activation import (
    DevelopmentActivationNextAction,
    DevelopmentActivationReviewStatus,
    StrategyResearchDevelopmentActivationError,
    build_research_development_control_evidence,
    review_strategy_research_development_activation,
)
from tip_api.services.strategy_research_readiness import (
    StrategyResearchReadinessError,
    assess_strategy_research_readiness,
    canonical_eod_identity_evidence,
    validate_strategy_research_readiness_assessment,
)


NOW = datetime(2026, 8, 31, 12, tzinfo=UTC)
REVISION = "1" * 40
ORACLE_AUDIT = "a" * 64
HOLDOUT_AUDIT = "b" * 64


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


def _coverage() -> HistoricalCoverageManifestV1:
    sessions = _sessions(252)
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
        coverage_id="c" * 64,
        sessions=sessions,
        feature_warmup_sessions=20,
        maximum_outcome_horizon_sessions=5,
        matured_signal_session_count=227,
        datasets=datasets,
        readiness_status=HistoricalReadinessStatus.RESEARCH_READY,
        reason_codes=(),
        created_at=NOW,
        logical_fingerprint="d" * 64,
    )


def _readiness(count: int, *, ready: bool):
    return assess_strategy_research_readiness(
        experiment=strong_stock_pullback_research_experiment_v1(),
        canonical_evidence=canonical_eod_identity_evidence(_descriptors(count)),
        coverage_manifest=_coverage() if ready else None,
    )


def _controls(readiness, **counts):
    return build_research_development_control_evidence(
        implementation_revision=REVISION,
        experiment_fingerprint=(
            strong_stock_pullback_research_experiment_v1().logical_fingerprint
        ),
        readiness_assessment_fingerprint=readiness.logical_content_fingerprint,
        inference_oracle_audit_fingerprint=ORACLE_AUDIT,
        holdout_custody_audit_fingerprint=HOLDOUT_AUDIT,
        **counts,
    )


def test_current_data_blocked_state_cannot_create_an_authorization() -> None:
    readiness = _readiness(31, ready=False)
    review = review_strategy_research_development_activation(
        experiment=strong_stock_pullback_research_experiment_v1(),
        readiness=readiness,
        controls=_controls(readiness),
        reviewed_at=NOW,
    )

    assert review.review_status is DevelopmentActivationReviewStatus.BLOCKED
    assert review.next_action is (
        DevelopmentActivationNextAction.COMPLETE_RESEARCH_READINESS
    )
    assert review.unresolved_gate_ids == ("formal_research_readiness",)
    assert review.authorization_binding_fingerprint is None
    assert review.required_user_acknowledgement is None
    assert review.development_activation_authorized is False
    assert review.real_evaluation_executed is False
    assert review.parameter_selection_executed is False
    assert review.holdout_accessed is False
    assert review.performance_claims_authorized is False
    assert review.external_request_count == 0
    assert review.production_write_count == 0


def test_complete_fixture_readiness_only_generates_exact_authorization_review() -> None:
    readiness = _readiness(252, ready=True)
    review = review_strategy_research_development_activation(
        experiment=strong_stock_pullback_research_experiment_v1(),
        readiness=readiness,
        controls=_controls(readiness),
        reviewed_at=NOW,
    )

    assert review.review_status is (
        DevelopmentActivationReviewStatus.READY_FOR_EXACT_USER_AUTHORIZATION
    )
    assert review.next_action is (
        DevelopmentActivationNextAction.REQUEST_EXACT_USER_AUTHORIZATION
    )
    assert review.unresolved_gate_ids == ()
    assert review.required_user_acknowledgement == (
        "I_AUTHORIZE_STRATEGY_DEVELOPMENT_"
        f"{review.authorization_binding_fingerprint}"
    )
    assert review.development_activation_authorized is False
    assert review.real_evaluation_executed is False
    assert review.holdout_accessed is False


@pytest.mark.parametrize(
    ("field", "gate"),
    [
        ("existing_real_result_count", "no_existing_real_result"),
        (
            "existing_development_activation_count",
            "no_existing_development_activation",
        ),
        ("existing_holdout_consumption_count", "sealed_holdout_unconsumed"),
    ],
)
def test_existing_research_state_blocks_a_second_activation(field: str, gate: str) -> None:
    readiness = _readiness(252, ready=True)
    review = review_strategy_research_development_activation(
        experiment=strong_stock_pullback_research_experiment_v1(),
        readiness=readiness,
        controls=_controls(readiness, **{field: 1}),
        reviewed_at=NOW,
    )

    assert review.review_status is DevelopmentActivationReviewStatus.BLOCKED
    assert review.unresolved_gate_ids == (gate,)
    assert review.required_user_acknowledgement is None


def test_review_rejects_readiness_control_and_experiment_drift() -> None:
    readiness = _readiness(252, ready=True)
    with pytest.raises(
        StrategyResearchDevelopmentActivationError,
        match="readiness binding",
    ):
        review_strategy_research_development_activation(
            experiment=strong_stock_pullback_research_experiment_v1(),
            readiness=readiness,
            controls=build_research_development_control_evidence(
                implementation_revision=REVISION,
                experiment_fingerprint=(
                    strong_stock_pullback_research_experiment_v1().logical_fingerprint
                ),
                readiness_assessment_fingerprint="e" * 64,
                inference_oracle_audit_fingerprint=ORACLE_AUDIT,
                holdout_custody_audit_fingerprint=HOLDOUT_AUDIT,
            ),
            reviewed_at=NOW,
        )

    with pytest.raises(
        StrategyResearchDevelopmentActivationError,
        match="experiment binding",
    ):
        review_strategy_research_development_activation(
            experiment=strong_stock_pullback_research_experiment_v1(),
            readiness=readiness,
            controls=build_research_development_control_evidence(
                implementation_revision=REVISION,
                experiment_fingerprint="f" * 64,
                readiness_assessment_fingerprint=(
                    readiness.logical_content_fingerprint
                ),
                inference_oracle_audit_fingerprint=ORACLE_AUDIT,
                holdout_custody_audit_fingerprint=HOLDOUT_AUDIT,
            ),
            reviewed_at=NOW,
        )


def test_readiness_formal_reread_rejects_tampering() -> None:
    readiness = _readiness(31, ready=False)
    validate_strategy_research_readiness_assessment(readiness)
    with pytest.raises(StrategyResearchReadinessError, match="formally reconcile"):
        validate_strategy_research_readiness_assessment(
            replace(readiness, development_authorized=True)
        )


def test_control_evidence_rejects_tampering_and_negative_counts() -> None:
    readiness = _readiness(252, ready=True)
    with pytest.raises(
        StrategyResearchDevelopmentActivationError,
        match="control evidence",
    ):
        review_strategy_research_development_activation(
            experiment=strong_stock_pullback_research_experiment_v1(),
            readiness=readiness,
            controls=replace(_controls(readiness), implementation_revision="2" * 40),
            reviewed_at=NOW,
        )
    with pytest.raises(
        StrategyResearchDevelopmentActivationError,
        match="control evidence",
    ):
        build_research_development_control_evidence(
            implementation_revision=REVISION,
            experiment_fingerprint=(
                strong_stock_pullback_research_experiment_v1().logical_fingerprint
            ),
            readiness_assessment_fingerprint=readiness.logical_content_fingerprint,
            inference_oracle_audit_fingerprint=ORACLE_AUDIT,
            holdout_custody_audit_fingerprint=HOLDOUT_AUDIT,
            existing_real_result_count=-1,
        )


def test_review_is_deterministic_and_rejects_naive_time() -> None:
    readiness = _readiness(252, ready=True)
    controls = _controls(readiness)
    first = review_strategy_research_development_activation(
        experiment=strong_stock_pullback_research_experiment_v1(),
        readiness=readiness,
        controls=controls,
        reviewed_at=NOW,
    )
    second = review_strategy_research_development_activation(
        experiment=strong_stock_pullback_research_experiment_v1(),
        readiness=readiness,
        controls=controls,
        reviewed_at=NOW,
    )
    assert first == second

    with pytest.raises(
        StrategyResearchDevelopmentActivationError,
        match="timezone-aware",
    ):
        review_strategy_research_development_activation(
            experiment=strong_stock_pullback_research_experiment_v1(),
            readiness=readiness,
            controls=controls,
            reviewed_at=datetime(2026, 8, 31, 12),
        )
