from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
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
    _block_bootstrap,
    build_fixture_cohort_outcome,
    evaluate_development_statistics_fixture,
    evaluate_holdout_statistics_fixture,
    evaluate_validation_statistics_fixture,
)
from tip_api.services.candidate_strategy_research_statistics_oracle import (
    calculate_block_bootstrap_inference_oracle,
    calculate_holm_adjustment_oracle,
    calculate_research_statistics_oracle,
)
from tip_api.services.candidate_strategy_holdout_custody import (
    CandidateStrategyHoldoutCustodyError,
    HoldoutCustodyConfig,
    HoldoutEvaluationEvidence,
    consume_locked_holdout_once,
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


def _holdout_config(tmp_path: Path) -> HoldoutCustodyConfig:
    root = tmp_path / "holdout-custody"
    root.mkdir(mode=0o700, parents=True)
    return HoldoutCustodyConfig(
        holdout_root=root,
        repository_root=Path(__file__).parents[3],
        data_root=Path("/data/trading-intelligence-platform"),
    )


def test_external_holdout_custody_consumes_exact_lock_once(
    tmp_path: Path,
    completed_fixture,
) -> None:
    _, validation, holdout = completed_fixture
    calls = []

    def capability(context):
        calls.append(context)
        return HoldoutEvaluationEvidence(
            **asdict(context),
            result_report_fingerprint=holdout.logical_fingerprint,
            outcome="completed",
            reason_code="fixture_holdout_completed",
        )

    times = iter(
        (
            datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
            datetime(2026, 8, 31, 9, 1, tzinfo=UTC),
        )
    )
    config = _holdout_config(tmp_path)
    first = consume_locked_holdout_once(
        config=config,
        validation_report=validation,
        capability=capability,
        clock=lambda: next(times),
    )
    second = consume_locked_holdout_once(
        config=config,
        validation_report=validation,
        capability=lambda _context: pytest.fail("holdout evaluated twice"),
    )

    assert len(calls) == 1
    assert first.outcome == "completed"
    assert first.holdout_evaluated_by_invocation is True
    assert first.custody_event_write_count == 2
    assert first.production_write_count == 0
    assert first.external_request_count == 0
    assert first.stage_transition_authorized is False
    assert first.performance_claim_authorized is False
    assert second.outcome == "already_consumed"
    assert second.holdout_evaluated_by_invocation is False
    assert second.custody_event_write_count == 0
    assert second.result_report_fingerprint == holdout.logical_fingerprint


def test_holdout_interruption_and_invalid_evidence_permanently_block_replay(
    tmp_path: Path,
    completed_fixture,
) -> None:
    _, validation, holdout = completed_fixture
    interrupted = _holdout_config(tmp_path / "interrupted")
    with pytest.raises(RuntimeError, match="evaluation crashed"):
        consume_locked_holdout_once(
            config=interrupted,
            validation_report=validation,
            capability=lambda _context: (_ for _ in ()).throw(
                RuntimeError("evaluation crashed")
            ),
            clock=lambda: datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
        )
    with pytest.raises(CandidateStrategyHoldoutCustodyError, match="unknown"):
        consume_locked_holdout_once(
            config=interrupted,
            validation_report=validation,
            capability=lambda _context: pytest.fail("ambiguous holdout replayed"),
        )

    invalid = _holdout_config(tmp_path / "invalid")
    with pytest.raises(CandidateStrategyHoldoutCustodyError, match="binding differs"):
        consume_locked_holdout_once(
            config=invalid,
            validation_report=validation,
            capability=lambda context: HoldoutEvaluationEvidence(
                **{
                    **asdict(context),
                    "parameter_combination_id": "f" * 64,
                },
                result_report_fingerprint=holdout.logical_fingerprint,
                outcome="completed",
                reason_code="fixture_holdout_completed",
            ),
            clock=lambda: datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
        )
    with pytest.raises(CandidateStrategyHoldoutCustodyError, match="unknown"):
        consume_locked_holdout_once(
            config=invalid,
            validation_report=validation,
            capability=lambda _context: pytest.fail("invalid evidence retried"),
        )

    failed = _holdout_config(tmp_path / "failed")
    failed_times = iter(
        (
            datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
            datetime(2026, 8, 31, 9, 1, tzinfo=UTC),
        )
    )
    failure = consume_locked_holdout_once(
        config=failed,
        validation_report=validation,
        capability=lambda context: HoldoutEvaluationEvidence(
            **asdict(context),
            result_report_fingerprint=None,
            outcome="failed",
            reason_code="fixture_evaluation_failed",
        ),
        clock=lambda: next(failed_times),
    )
    assert failure.outcome == "failed"
    with pytest.raises(CandidateStrategyHoldoutCustodyError, match="prior.*failed"):
        consume_locked_holdout_once(
            config=failed,
            validation_report=validation,
            capability=lambda _context: pytest.fail("failed holdout replayed"),
        )


def test_holdout_custody_rejects_nonvalidation_and_tampered_journal(
    tmp_path: Path,
    completed_fixture,
) -> None:
    development, validation, holdout = completed_fixture
    config = _holdout_config(tmp_path)
    with pytest.raises(CandidateStrategyHoldoutCustodyError, match="validation"):
        consume_locked_holdout_once(
            config=config,
            validation_report=development,
            capability=lambda _context: pytest.fail("development opened holdout"),
        )

    times = iter(
        (
            datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
            datetime(2026, 8, 31, 9, 1, tzinfo=UTC),
        )
    )
    result = consume_locked_holdout_once(
        config=config,
        validation_report=validation,
        capability=lambda context: HoldoutEvaluationEvidence(
            **asdict(context),
            result_report_fingerprint=holdout.logical_fingerprint,
            outcome="completed",
            reason_code="fixture_holdout_completed",
        ),
        clock=lambda: next(times),
    )
    event = config.holdout_root / f"holdout={result.custody_id}" / "event-000002.json"
    event.chmod(0o644)
    with pytest.raises(CandidateStrategyHoldoutCustodyError, match="custody"):
        consume_locked_holdout_once(
            config=config,
            validation_report=validation,
            capability=lambda _context: pytest.fail("tampered custody reused"),
        )


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


def test_independent_oracle_reproduces_every_descriptive_development_value(
    research_fixture,
    completed_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    development, _, _ = completed_fixture
    outcomes = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.DEVELOPMENT,
    )
    oracle = calculate_research_statistics_oracle(
        mechanics=mechanics,
        observations=observations,
        outcomes=outcomes,
        split=StrategyEvaluationSplit.DEVELOPMENT,
    )
    actual_by_key = {
        (item.parameter_combination_id, item.horizon_sessions): item
        for item in development.summaries
    }

    for expected in oracle:
        actual = actual_by_key[
            (expected.parameter_combination_id, expected.horizon_sessions)
        ]
        assert actual.signal_assigned_count == expected.signal_assigned_count
        assert actual.control_assigned_count == expected.control_assigned_count
        assert actual.signal_available_count == expected.signal_available_count
        assert actual.control_available_count == expected.control_available_count
        assert actual.signal_quarantined_count == expected.signal_quarantined_count
        assert actual.control_quarantined_count == expected.control_quarantined_count
        assert (
            actual.signal_unavailable_or_pending_count
            == expected.signal_other_count
        )
        assert (
            actual.control_unavailable_or_pending_count
            == expected.control_other_count
        )
        assert actual.signal_coverage_ratio == expected.signal_coverage_ratio
        assert actual.control_coverage_ratio == expected.control_coverage_ratio
        assert actual.paired_session_count == expected.paired_session_count
        assert (
            actual.signal_market_regime_counts
            == expected.signal_market_regime_counts
        )
        assert (
            actual.inference_status is ResearchInferenceStatus.AVAILABLE
        ) == expected.evidence_floor_met
        assert (
            actual.signal_mean_underlying_return
            == expected.signal_mean_underlying_return
        )
        assert (
            actual.signal_median_underlying_return
            == expected.signal_median_underlying_return
        )
        assert (
            actual.signal_median_spy_relative_return
            == expected.signal_median_spy_relative_return
        )
        assert actual.signal_hit_rate == expected.signal_hit_rate
        assert (
            actual.signal_mean_maximum_favorable_excursion
            == expected.signal_mean_maximum_favorable_excursion
        )
        assert (
            actual.signal_mean_maximum_adverse_excursion
            == expected.signal_mean_maximum_adverse_excursion
        )
        assert (
            actual.session_balanced_mean_contrast
            == expected.session_balanced_mean_contrast
        )
        assert actual.contrast_lower_90pct == expected.contrast_lower_90pct
        assert actual.contrast_upper_90pct == expected.contrast_upper_90pct
        assert actual.one_sided_raw_p_value == expected.one_sided_raw_p_value
        assert actual.bootstrap_replicates == expected.bootstrap_replicates


@pytest.mark.parametrize("count", [1, 2, 5, 20, 37, 53])
def test_independent_inference_oracle_matches_arbitrary_nonconstant_series(
    count: int,
) -> None:
    values = tuple(
        (
            Decimal(((index * 17) % 29) - 14) / Decimal("1000")
            + Decimal(index % 3) / Decimal("10000")
        )
        for index in range(count)
    )
    seed_material = f"validation:arbitrary-series-{count}:3"

    expected = calculate_block_bootstrap_inference_oracle(
        values,
        seed_material=seed_material,
    )
    actual_lower, actual_upper, actual_probability = _block_bootstrap(
        values,
        seed_material=seed_material,
    )

    assert expected.lower_90pct == actual_lower
    assert expected.upper_90pct == actual_upper
    assert expected.one_sided_p_value == actual_probability
    assert expected.replicate_count == 2_000


def test_independent_holm_oracle_matches_full_validation_family(
    completed_fixture,
) -> None:
    _, validation, _ = completed_fixture
    primary = {
        item.parameter_combination_id: Decimal(item.one_sided_raw_p_value)
        for item in validation.summaries
        if item.horizon_sessions == 3 and item.one_sided_raw_p_value is not None
    }
    expected = calculate_holm_adjustment_oracle(primary)

    assert len(expected) == 24
    for item in validation.summaries:
        if item.horizon_sessions == 3:
            assert item.holm_adjusted_p_value is not None
            assert Decimal(item.holm_adjusted_p_value) == expected[
                item.parameter_combination_id
            ].quantize(Decimal("0.000001"))


@pytest.mark.parametrize("validation_return", ["0.0000000000", "-0.0200000000"])
def test_null_or_reversing_validation_cannot_reach_holdout(
    validation_return,
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
            signal_return=validation_return,
        ),
        development_report=development,
    )

    assert validation.all_required_gates_passed is False
    assert any(
        item.status is ResearchGateStatus.FAIL
        for item in validation.gate_evaluations
    )
    with pytest.raises(CandidateStrategyResearchStatisticsError, match="every"):
        evaluate_holdout_statistics_fixture(
            mechanics=mechanics,
            observations=observations,
            outcomes=(),
            validation_report=validation,
        )


def test_single_session_crowding_is_inconclusive_despite_many_assignments(
    research_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    all_outcomes = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.DEVELOPMENT,
    )
    assignment_by_fingerprint = {
        item.logical_fingerprint: item for item in mechanics.assignments
    }
    first_session = min(
        assignment_by_fingerprint[item.assignment_fingerprint].as_of_session
        for item in all_outcomes
    )
    crowded = tuple(
        item
        for item in all_outcomes
        if assignment_by_fingerprint[item.assignment_fingerprint].as_of_session
        == first_session
    )
    report = evaluate_development_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=crowded,
    )

    assert report.parameter_lock is None
    assert all(
        item.inference_status is ResearchInferenceStatus.INCONCLUSIVE
        for item in report.summaries
    )
    assert max(item.paired_session_count for item in report.summaries) == 1


def test_one_extreme_session_does_not_rescue_validation(
    research_fixture,
    completed_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    development, _, _ = completed_fixture
    eligible = [
        item
        for item in mechanics.assignments
        if item.evaluation_split is StrategyEvaluationSplit.VALIDATION
        and item.universe_id == "primary"
        and item.cohort_role
        in {
            StrongLeaderPullbackCohortRole.SIGNAL,
            StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL,
        }
    ]
    extreme_session = min(item.as_of_session for item in eligible)
    outcomes = []
    for assignment in eligible:
        extreme_signal = (
            assignment.cohort_role is StrongLeaderPullbackCohortRole.SIGNAL
            and assignment.as_of_session == extreme_session
        )
        stock_return = "1.0000000000" if extreme_signal else "0.0000000000"
        outcomes.append(
            build_fixture_cohort_outcome(
                assignment=assignment,
                horizon_sessions=3,
                status=StrategyOutcomeStatus.AVAILABLE,
                underlying_price_return=stock_return,
                benchmark_price_return="0.0000000000",
                relative_to_benchmark_return=stock_return,
                maximum_favorable_excursion=(
                    "1.0000000000" if extreme_signal else "0.0100000000"
                ),
                maximum_adverse_excursion="-0.0100000000",
                source_eod_fingerprint=hashlib.sha256(
                    assignment.logical_fingerprint.encode("ascii")
                ).hexdigest(),
            )
        )
    validation = evaluate_validation_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=tuple(outcomes),
        development_report=development,
    )
    selected = next(
        item
        for item in validation.summaries
        if item.parameter_combination_id
        == validation.selected_parameter_combination_id
        and item.horizon_sessions == 3
    )

    assert Decimal(selected.session_balanced_mean_contrast or "0") > 0
    assert selected.signal_median_spy_relative_return == "0.0000000000"
    assert validation.all_required_gates_passed is False
    assert next(
        item.status
        for item in validation.gate_evaluations
        if item.gate_id == "net_primary_median_positive"
    ) is ResearchGateStatus.FAIL


def test_differential_missingness_is_visible_and_never_authoritative(
    research_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    assignment_by_fingerprint = {
        item.logical_fingerprint: item for item in mechanics.assignments
    }
    complete = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.DEVELOPMENT,
    )
    signal_seen = 0
    retained = []
    for outcome in complete:
        assignment = assignment_by_fingerprint[outcome.assignment_fingerprint]
        if assignment.cohort_role is StrongLeaderPullbackCohortRole.SIGNAL:
            signal_seen += 1
            if signal_seen % 10 == 0:
                continue
        retained.append(outcome)
    report = evaluate_development_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=tuple(retained),
    )
    selected = next(
        item
        for item in report.summaries
        if item.parameter_combination_id
        == report.selected_parameter_combination_id
        and item.horizon_sessions == 3
    )

    assert Decimal(selected.signal_coverage_ratio) < 1
    assert "signal_outcome_coverage_incomplete" in selected.reason_codes
    assert report.stage_transition_authorized is False
    assert report.performance_claim_authorized is False


def test_incomplete_validation_coverage_fails_independent_quality_gate(
    research_fixture,
    completed_fixture,
) -> None:
    _, observations, mechanics = research_fixture
    development, _, _ = completed_fixture
    assignment_by_fingerprint = {
        item.logical_fingerprint: item for item in mechanics.assignments
    }
    complete = _outcomes(
        mechanics,
        split=StrategyEvaluationSplit.VALIDATION,
    )
    signal_seen = 0
    retained = []
    for outcome in complete:
        assignment = assignment_by_fingerprint[outcome.assignment_fingerprint]
        if assignment.cohort_role is StrongLeaderPullbackCohortRole.SIGNAL:
            signal_seen += 1
            if signal_seen % 10 == 0:
                continue
        retained.append(outcome)
    validation = evaluate_validation_statistics_fixture(
        mechanics=mechanics,
        observations=observations,
        outcomes=tuple(retained),
        development_report=development,
    )
    coverage_gate = next(
        item
        for item in validation.gate_evaluations
        if item.gate_id == "complete_validation_family_evidence"
    )

    assert coverage_gate.status is ResearchGateStatus.FAIL
    assert Decimal(coverage_gate.observed_value or "1") < 1
    assert validation.all_required_gates_passed is False
