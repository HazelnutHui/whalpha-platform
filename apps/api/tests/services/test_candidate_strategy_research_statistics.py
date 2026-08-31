from __future__ import annotations

import hashlib
from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    ResearchGateStatus,
    ResearchInferenceStatus,
    ResearchStatisticsStage,
    StrategyEvaluationSplit,
    StrategyMembershipMode,
    StrategyOutcomeStatus,
    StrongLeaderPullbackCohortOutcomeV1,
    StrongLeaderPullbackCohortRole,
    research_statistics_fingerprint,
)
from tip_api.services.candidate_strategy_research_execution import (
    build_candidate_strategy_chronological_plan,
    build_strong_leader_pullback_mechanics,
    build_strong_leader_pullback_observation,
)
from tip_api.services.candidate_strategy_research_statistics import (
    CandidateStrategyResearchStatisticsError,
    build_fixture_cohort_outcome,
    evaluate_development_statistics_fixture,
    evaluate_holdout_statistics_fixture,
    evaluate_validation_statistics_fixture,
)
from tip_api.services.market_calendar import ExchangeCalendar


@pytest.fixture(scope="module")
def research_fixture():
    calendar = ExchangeCalendar()
    sessions = [date(2024, 1, 2)]
    while len(sessions) < 252:
        sessions.append(calendar.next_session(sessions[-1]))
    plan = build_candidate_strategy_chronological_plan(
        ordered_sessions=tuple(sessions)
    )
    observations = []
    instrument_number = 1
    for session_assignment in plan.assignments:
        if not session_assignment.usable_for_signal_evaluation:
            continue
        for role_index in range(4):
            signal_fixture = role_index < 2
            source = hashlib.sha256(
                f"{session_assignment.session}:{role_index}".encode("utf-8")
            ).hexdigest()
            observations.append(
                build_strong_leader_pullback_observation(
                    as_of_session=session_assignment.session,
                    universe_id="primary",
                    instrument_id=UUID(int=instrument_number),
                    ticker=f"T{instrument_number}",
                    membership_mode=StrategyMembershipMode.POINT_IN_TIME,
                    membership_session=session_assignment.session,
                    membership_included=True,
                    relative_strength_20s_percentile="0.9500",
                    trend_quality_score="80.0000",
                    pullback_depth_atr="1.2500",
                    close_above_prior_close=True,
                    close_above_prior_high=True,
                    pullback_volume_ratio=(
                        "0.7000" if signal_fixture else "1.5000"
                    ),
                    market_regime="Balanced",
                    source_max_session=session_assignment.session,
                    source_fingerprint=source,
                )
            )
            instrument_number += 1
    observations = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.as_of_session,
                item.universe_id,
                str(item.instrument_id),
            ),
        )
    )
    mechanics = build_strong_leader_pullback_mechanics(
        plan=plan,
        observations=observations,
    )
    return plan, observations, mechanics


def _outcomes(mechanics, *, split, selected=None, signal_return="0.0300000000"):
    result = []
    for assignment in mechanics.assignments:
        if (
            assignment.evaluation_split is not split
            or assignment.universe_id != "primary"
            or assignment.cohort_role
            not in {
                StrongLeaderPullbackCohortRole.SIGNAL,
                StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL,
            }
            or (
                selected is not None
                and assignment.parameter_combination_id != selected
            )
        ):
            continue
        is_signal = assignment.cohort_role is StrongLeaderPullbackCohortRole.SIGNAL
        stock_return = signal_return if is_signal else "0.0000000000"
        result.append(
            build_fixture_cohort_outcome(
                assignment=assignment,
                horizon_sessions=3,
                status=StrategyOutcomeStatus.AVAILABLE,
                underlying_price_return=stock_return,
                benchmark_price_return="0.0000000000",
                relative_to_benchmark_return=stock_return,
                maximum_favorable_excursion=(
                    "0.0400000000" if is_signal else "0.0100000000"
                ),
                maximum_adverse_excursion="-0.0100000000",
                source_eod_fingerprint=hashlib.sha256(
                    assignment.logical_fingerprint.encode("ascii")
                ).hexdigest(),
            )
        )
    return tuple(result)


@pytest.fixture(scope="module")
def completed_fixture(research_fixture):
    _, observations, mechanics = research_fixture
    development = evaluate_development_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=_outcomes(
            mechanics,
            split=StrategyEvaluationSplit.DEVELOPMENT,
        ),
    )
    validation = evaluate_validation_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=_outcomes(
            mechanics,
            split=StrategyEvaluationSplit.VALIDATION,
        ),
        development_report=development,
    )
    holdout = evaluate_holdout_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=_outcomes(
            mechanics,
            split=StrategyEvaluationSplit.HOLDOUT,
            selected=development.selected_parameter_combination_id,
        ),
        validation_report=validation,
    )
    return development, validation, holdout


def test_development_uses_registered_scope_and_locks_one_parameter(
    completed_fixture,
) -> None:
    development, _, _ = completed_fixture
    primary = [
        item for item in development.summaries if item.horizon_sessions == 3
    ]

    assert development.stage is ResearchStatisticsStage.DEVELOPMENT
    assert len(development.summaries) == 72
    assert len(primary) == 24
    assert all(item.inference_status is ResearchInferenceStatus.AVAILABLE for item in primary)
    assert all(item.session_balanced_mean_contrast == "0.0300000000" for item in primary)
    assert all(item.contrast_lower_90pct == "0.0300000000" for item in primary)
    assert development.selected_parameter_combination_id == min(
        item.parameter_combination_id for item in primary
    )
    assert development.parameter_lock is not None
    assert development.parameter_lock.selected_before_validation is True
    assert development.stage_transition_authorized is False
    assert development.performance_claim_authorized is False
    one_session = next(
        item
        for item in development.summaries
        if item.parameter_combination_id
        == development.selected_parameter_combination_id
        and item.horizon_sessions == 1
    )
    assert one_session.signal_coverage_ratio == "0.0000"
    assert (
        one_session.signal_unavailable_or_pending_count
        == one_session.signal_assigned_count
    )


def test_validation_applies_all_24_holm_family_and_registered_gates(
    completed_fixture,
) -> None:
    development, validation, _ = completed_fixture
    selected = next(
        item
        for item in validation.summaries
        if item.parameter_combination_id
        == development.selected_parameter_combination_id
        and item.horizon_sessions == 3
    )

    assert validation.stage is ResearchStatisticsStage.VALIDATION
    assert validation.parameter_lock == development.parameter_lock
    assert selected.one_sided_raw_p_value == "0.000500"
    assert selected.holm_adjusted_p_value == "0.012000"
    assert next(
        item.signal_median_spy_relative_return_net
        for item in selected.cost_scenarios
        if item.basis_points_per_side == 25
    ) == "0.0250000000"
    assert selected.signal_market_regime_counts == {
        "Balanced": 106,
        "Defensive": 0,
        "Risk-on": 0,
    }
    assert {item.status for item in validation.gate_evaluations} == {
        ResearchGateStatus.PASS
    }
    assert validation.all_required_gates_passed is True


def test_holdout_exposes_only_locked_parameter_and_remains_non_authoritative(
    completed_fixture,
) -> None:
    development, validation, holdout = completed_fixture

    assert holdout.stage is ResearchStatisticsStage.HOLDOUT
    assert len(holdout.summaries) == 3
    assert {
        item.parameter_combination_id for item in holdout.summaries
    } == {development.selected_parameter_combination_id}
    assert holdout.prior_stage_report_fingerprint == validation.logical_fingerprint
    assert holdout.holdout_consumed is True
    assert holdout.all_required_gates_passed is True
    assert holdout.fixture_only is True
    assert holdout.stage_transition_authorized is False
    assert holdout.performance_claim_authorized is False
    assert holdout.single_use_holdout_custody_implemented is False


def test_failed_validation_gate_prevents_holdout_consumption(
    research_fixture,
    completed_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    development, _, _ = completed_fixture
    validation = evaluate_validation_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=_outcomes(
            mechanics,
            split=StrategyEvaluationSplit.VALIDATION,
            signal_return="0.0010000000",
        ),
        development_report=development,
    )

    assert validation.all_required_gates_passed is False
    assert next(
        item.status
        for item in validation.gate_evaluations
        if item.gate_id == "net_primary_median_positive"
    ) is ResearchGateStatus.FAIL
    with pytest.raises(CandidateStrategyResearchStatisticsError, match="every"):
        evaluate_holdout_statistics_fixture(
            mechanics=mechanics,
            observations=observations,
            outcomes=(),
            validation_report=validation,
        )


def test_empty_development_is_inconclusive_and_cannot_open_validation(
    research_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    development = evaluate_development_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=(),
    )

    assert development.parameter_lock is None
    assert development.selected_parameter_combination_id is None
    assert all(
        item.inference_status is ResearchInferenceStatus.INCONCLUSIVE
        for item in development.summaries
    )
    with pytest.raises(
        CandidateStrategyResearchStatisticsError,
        match="conclusive development",
    ):
        evaluate_validation_statistics_fixture(
            mechanics=mechanics,
            observations=observations,
            outcomes=(),
            development_report=development,
        )


def test_stage_input_rejects_cross_split_and_unlocked_holdout(
    research_fixture,
    completed_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    development, validation, _ = completed_fixture
    validation_outcome = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.VALIDATION,
    )[0]
    with pytest.raises(CandidateStrategyResearchStatisticsError, match="another"):
        evaluate_development_statistics_fixture(
            mechanics=mechanics,
            observations=observations,
            outcomes=(validation_outcome,),
        )

    unlocked = next(
        item.combination_id
        for item in mechanics.parameter_combinations
        if item.combination_id != development.selected_parameter_combination_id
    )
    wrong_holdout = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.HOLDOUT,
        selected=unlocked,
    )[0]
    with pytest.raises(CandidateStrategyResearchStatisticsError, match="unlocked"):
        evaluate_holdout_statistics_fixture(
            mechanics=mechanics,
            observations=observations,
            outcomes=(wrong_holdout,),
            validation_report=validation,
        )


def test_fixture_label_fingerprint_detects_business_value_tampering(
    research_fixture,
) -> None:
    _, _, mechanics = research_fixture
    outcome = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.DEVELOPMENT,
    )[0]
    payload = outcome.model_dump(mode="python")
    payload["underlying_price_return"] = "0.0400000000"
    payload["relative_to_benchmark_return"] = "0.0400000000"
    provisional = StrongLeaderPullbackCohortOutcomeV1.model_construct(**payload)
    payload["logical_fingerprint"] = research_statistics_fingerprint(provisional)

    with pytest.raises(ValidationError, match="label fingerprint"):
        StrongLeaderPullbackCohortOutcomeV1.model_validate(payload)
