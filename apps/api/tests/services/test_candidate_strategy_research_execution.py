from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateStrategySignalV1,
    ResearchSessionExclusionCode,
    StrategyChannel,
    StrategyChannelStatus,
    StrategyCorporateActionStatus,
    StrategyEvaluationSplit,
    StrategyMembershipMode,
    StrategyOutcomeStatus,
    StrongLeaderPullbackCohortRole,
    candidate_strategy_signal_id,
    strategy_channel_logical_fingerprint,
)
from tip_api.services.candidate_strategy_research_execution import (
    CandidateStrategyResearchExecutionError,
    ResearchOutcomeBarV1,
    build_candidate_strategy_chronological_plan,
    build_strong_leader_pullback_mechanics,
    build_strong_leader_pullback_observation,
    enumerate_strong_leader_pullback_parameters,
    mature_strategy_outcome,
    schedule_pending_strategy_outcomes,
)
from tip_api.services.market_calendar import ExchangeCalendar


INSTRUMENT_IDS = tuple(
    UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(1, 5)
)


@pytest.fixture(scope="module")
def ordered_sessions() -> tuple[date, ...]:
    calendar = ExchangeCalendar()
    sessions = [date(2024, 1, 2)]
    while len(sessions) < 252:
        sessions.append(calendar.next_session(sessions[-1]))
    return tuple(sessions)


def _observation(
    *,
    session: date,
    instrument_index: int,
    membership_mode: StrategyMembershipMode = StrategyMembershipMode.POINT_IN_TIME,
    membership_included: bool = True,
    relative_strength: str = "0.9500",
    trend_quality: str = "80.0000",
    pullback_depth: str = "1.0000",
    close_above_prior_close: bool = True,
    close_above_prior_high: bool = True,
    volume_ratio: str = "0.7000",
):
    return build_strong_leader_pullback_observation(
        as_of_session=session,
        universe_id="primary",
        instrument_id=INSTRUMENT_IDS[instrument_index],
        ticker=f"T{instrument_index + 1}",
        membership_mode=membership_mode,
        membership_session=(
            session
            if membership_mode is StrategyMembershipMode.POINT_IN_TIME
            else date(2026, 8, 28)
        ),
        membership_included=membership_included,
        relative_strength_20s_percentile=relative_strength,
        trend_quality_score=trend_quality,
        pullback_depth_atr=pullback_depth,
        close_above_prior_close=close_above_prior_close,
        close_above_prior_high=close_above_prior_high,
        pullback_volume_ratio=volume_ratio,
        market_regime="Balanced",
        source_max_session=session,
        source_fingerprint=str(instrument_index + 1) * 64,
    )


def _signal(*, session: date, split: str) -> CandidateStrategySignalV1:
    assessment_fingerprint = "a" * 64
    payload: dict[str, object] = {
        "signal_id": candidate_strategy_signal_id(
            as_of_session=session,
            universe_id="primary",
            instrument_id=INSTRUMENT_IDS[0],
            channel=StrategyChannel.STRONG_STOCK_PULLBACK,
            assessment_logical_fingerprint=assessment_fingerprint,
        ),
        "as_of_session": session,
        "universe_id": "primary",
        "instrument_id": INSTRUMENT_IDS[0],
        "ticker": "T1",
        "security_type": "CS",
        "channel": StrategyChannel.STRONG_STOCK_PULLBACK,
        "channel_status": StrategyChannelStatus.ADVANCE_TO_RESEARCH,
        "channel_score": "82.0000",
        "within_channel_rank": 1,
        "assessment_logical_fingerprint": assessment_fingerprint,
        "assessment_parameter_fingerprint": "b" * 64,
        "source_candidate_fingerprint": "c" * 64,
        "source_entry_geometry_fingerprint": "d" * 64,
        "source_market_regime_fingerprint": "e" * 64,
        "source_sessions": (session,),
        "membership_mode": StrategyMembershipMode.POINT_IN_TIME,
        "membership_session": session,
        "membership_fingerprint": "f" * 64,
        "membership_methodology_version": "synthetic-point-in-time-v1",
        "evaluation_eligible": True,
        "evaluation_split": StrategyEvaluationSplit(split),
        "limitation_codes": (),
        "sealed_without_outcomes": True,
    }
    provisional = CandidateStrategySignalV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    normalized = provisional.model_dump(mode="python")
    normalized["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        provisional,
        exclude={"logical_fingerprint"},
    )
    return CandidateStrategySignalV1.model_validate(normalized)


def _oracle_role(observation, combination) -> StrongLeaderPullbackCohortRole:
    if observation.membership_mode is not StrategyMembershipMode.POINT_IN_TIME:
        return StrongLeaderPullbackCohortRole.EXCLUDED_MEMBERSHIP
    leadership = {
        "rs20_percentile_gte_0.80_and_trend_quality_gte_70": (
            Decimal("0.80"),
            Decimal("70"),
        ),
        "rs20_percentile_gte_0.90_and_trend_quality_gte_75": (
            Decimal("0.90"),
            Decimal("75"),
        ),
    }
    minimum_rs, minimum_trend = leadership[combination.leadership_gate]
    if (
        Decimal(observation.relative_strength_20s_percentile) < minimum_rs
        or Decimal(observation.trend_quality_score) < minimum_trend
    ):
        return StrongLeaderPullbackCohortRole.EXCLUDED_NOT_LEADER
    bands = {
        "0.50_to_1.50": (Decimal("0.50"), Decimal("1.50")),
        "0.75_to_2.00": (Decimal("0.75"), Decimal("2.00")),
        "1.00_to_2.50": (Decimal("1.00"), Decimal("2.50")),
    }
    minimum_depth, maximum_depth = bands[combination.pullback_depth_atr_band]
    recovery = (
        observation.close_above_prior_close
        if combination.recovery_trigger == "close_above_prior_close"
        else observation.close_above_prior_high
    )
    triggered = (
        minimum_depth
        <= Decimal(observation.pullback_depth_atr)
        <= maximum_depth
        and recovery
        and Decimal(observation.pullback_volume_ratio)
        <= Decimal(combination.volume_contraction_ratio_max)
    )
    return (
        StrongLeaderPullbackCohortRole.SIGNAL
        if triggered
        else StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL
    )


def test_chronological_plan_has_fixed_splits_purge_embargo_and_maturity(
    ordered_sessions: tuple[date, ...],
) -> None:
    first = build_candidate_strategy_chronological_plan(
        ordered_sessions=ordered_sessions
    )
    second = build_candidate_strategy_chronological_plan(
        ordered_sessions=ordered_sessions
    )

    assert first == second
    assert first.raw_split_session_counts == {
        "development": 126,
        "validation": 63,
        "holdout": 63,
    }
    assert first.usable_signal_session_counts == {
        "development": 101,
        "validation": 53,
        "holdout": 53,
    }
    assert first.assignments[0].exclusion_codes == (
        ResearchSessionExclusionCode.FEATURE_WARMUP,
    )
    assert first.assignments[121].exclusion_codes == (
        ResearchSessionExclusionCode.BOUNDARY_PURGE,
    )
    assert first.assignments[126].exclusion_codes == (
        ResearchSessionExclusionCode.BOUNDARY_EMBARGO,
    )
    assert first.assignments[-1].exclusion_codes == (
        ResearchSessionExclusionCode.OUTCOME_NOT_MATURE,
    )
    assert first.random_split_prohibited is True


def test_chronological_plan_rejects_short_or_noncontiguous_history(
    ordered_sessions: tuple[date, ...],
) -> None:
    with pytest.raises(CandidateStrategyResearchExecutionError, match="252"):
        build_candidate_strategy_chronological_plan(
            ordered_sessions=ordered_sessions[:-1]
        )
    calendar = ExchangeCalendar()
    broken = (
        ordered_sessions[:120]
        + ordered_sessions[121:]
        + (calendar.next_session(ordered_sessions[-1]),)
    )
    with pytest.raises(CandidateStrategyResearchExecutionError, match="contiguous"):
        build_candidate_strategy_chronological_plan(ordered_sessions=broken)


def test_all_24_preregistered_parameter_combinations_are_deterministic() -> None:
    first = enumerate_strong_leader_pullback_parameters()
    second = enumerate_strong_leader_pullback_parameters()

    assert first == second
    assert len(first) == 24
    assert len({item.combination_id for item in first}) == 24


def test_mechanics_match_independent_oracle_and_never_contain_outcomes(
    ordered_sessions: tuple[date, ...],
) -> None:
    plan = build_candidate_strategy_chronological_plan(
        ordered_sessions=ordered_sessions
    )
    session = ordered_sessions[40]
    observations = tuple(
        sorted(
            (
                _observation(session=session, instrument_index=0),
                _observation(
                    session=session,
                    instrument_index=1,
                    pullback_depth="3.0000",
                    close_above_prior_high=False,
                    volume_ratio="1.1000",
                ),
                _observation(
                    session=session,
                    instrument_index=2,
                    relative_strength="0.5000",
                    trend_quality="60.0000",
                ),
                _observation(
                    session=session,
                    instrument_index=3,
                    membership_mode=(
                        StrategyMembershipMode.CURRENT_AS_OF_CONSTITUENT_REPLAY
                    ),
                ),
            ),
            key=lambda item: (
                item.as_of_session,
                item.universe_id,
                str(item.instrument_id),
            ),
        )
    )
    batch = build_strong_leader_pullback_mechanics(
        plan=plan,
        observations=observations,
    )
    observation_by_id = {item.instrument_id: item for item in observations}
    combination_by_id = {
        item.combination_id: item for item in batch.parameter_combinations
    }

    for assignment in batch.assignments:
        assert assignment.cohort_role is _oracle_role(
            observation_by_id[assignment.instrument_id],
            combination_by_id[assignment.parameter_combination_id],
        )
        assert assignment.sealed_without_outcomes is True
    assert len(batch.assignments) == 96
    assert batch.contains_forward_outcomes is False
    assert batch.performance_claim_authorized is False


def test_boundary_observation_is_excluded_before_setup_evaluation(
    ordered_sessions: tuple[date, ...],
) -> None:
    plan = build_candidate_strategy_chronological_plan(
        ordered_sessions=ordered_sessions
    )
    observation = _observation(
        session=ordered_sessions[121],
        instrument_index=0,
    )

    batch = build_strong_leader_pullback_mechanics(
        plan=plan,
        observations=(observation,),
    )

    assert {
        item.cohort_role for item in batch.assignments
    } == {StrongLeaderPullbackCohortRole.EXCLUDED_CHRONOLOGICAL_BOUNDARY}


def test_outcomes_begin_pending_and_mature_only_from_exact_future_path(
    ordered_sessions: tuple[date, ...],
) -> None:
    plan = build_candidate_strategy_chronological_plan(
        ordered_sessions=ordered_sessions
    )
    signal_session = ordered_sessions[40]
    signal = _signal(session=signal_session, split="development")
    pending = schedule_pending_strategy_outcomes(signal=signal, plan=plan)

    assert tuple(item.horizon_sessions for item in pending) == (1, 3, 5)
    assert all(item.status is StrategyOutcomeStatus.PENDING for item in pending)
    assert all(item.label_source_max_session is None for item in pending)
    wrong_channel = signal.model_copy(
        update={"channel": StrategyChannel.MOMENTUM_BREAKOUT}
    )
    with pytest.raises(CandidateStrategyResearchExecutionError, match="only"):
        schedule_pending_strategy_outcomes(signal=wrong_channel, plan=plan)
    three_session = pending[1]
    assert mature_strategy_outcome(
        signal=signal,
        pending=three_session,
        known_through_session=three_session.expected_path_sessions[1],
    ) == three_session
    with pytest.raises(CandidateStrategyResearchExecutionError, match="immature"):
        mature_strategy_outcome(
            signal=signal,
            pending=three_session,
            known_through_session=three_session.expected_path_sessions[1],
            source_eod_fingerprint="9" * 64,
        )

    instrument_bars = (
        ResearchOutcomeBarV1(
            session=three_session.expected_path_sessions[0],
            open=Decimal("100"),
            high=Decimal("103"),
            low=Decimal("98"),
            close=Decimal("102"),
        ),
        ResearchOutcomeBarV1(
            session=three_session.expected_path_sessions[1],
            open=Decimal("102"),
            high=Decimal("106"),
            low=Decimal("101"),
            close=Decimal("105"),
        ),
        ResearchOutcomeBarV1(
            session=three_session.expected_path_sessions[2],
            open=Decimal("105"),
            high=Decimal("108"),
            low=Decimal("104"),
            close=Decimal("107"),
        ),
    )
    benchmark_bars = (
        ResearchOutcomeBarV1(
            session=three_session.expected_path_sessions[0],
            open=Decimal("500"),
            high=Decimal("505"),
            low=Decimal("498"),
            close=Decimal("503"),
        ),
        ResearchOutcomeBarV1(
            session=three_session.expected_path_sessions[1],
            open=Decimal("503"),
            high=Decimal("507"),
            low=Decimal("501"),
            close=Decimal("505"),
        ),
        ResearchOutcomeBarV1(
            session=three_session.expected_path_sessions[2],
            open=Decimal("505"),
            high=Decimal("511"),
            low=Decimal("504"),
            close=Decimal("510"),
        ),
    )
    available = mature_strategy_outcome(
        signal=signal,
        pending=three_session,
        known_through_session=three_session.expected_exit_session,
        instrument_bars=instrument_bars,
        benchmark_bars=benchmark_bars,
        source_eod_fingerprint="9" * 64,
    )

    assert available.status is StrategyOutcomeStatus.AVAILABLE
    assert available.underlying_price_return == "0.0700000000"
    assert available.benchmark_price_return == "0.0200000000"
    assert available.relative_to_benchmark_return == "0.0500000000"
    assert available.maximum_favorable_excursion == "0.0800000000"
    assert available.maximum_adverse_excursion == "-0.0200000000"
    assert available.underlying_stock_result_not_option_return is True

    wrong_path = instrument_bars[:-1]
    with pytest.raises(CandidateStrategyResearchExecutionError, match="exact expected"):
        mature_strategy_outcome(
            signal=signal,
            pending=three_session,
            known_through_session=three_session.expected_exit_session,
            instrument_bars=wrong_path,
            benchmark_bars=benchmark_bars,
            source_eod_fingerprint="9" * 64,
        )


def test_corporate_action_review_quarantines_without_numeric_claims(
    ordered_sessions: tuple[date, ...],
) -> None:
    plan = build_candidate_strategy_chronological_plan(
        ordered_sessions=ordered_sessions
    )
    signal = _signal(session=ordered_sessions[40], split="development")
    pending = schedule_pending_strategy_outcomes(signal=signal, plan=plan)[0]

    quarantined = mature_strategy_outcome(
        signal=signal,
        pending=pending,
        known_through_session=pending.expected_exit_session,
        corporate_action_status=StrategyCorporateActionStatus.REVIEW_REQUIRED,
        source_eod_fingerprint="9" * 64,
        quarantine_reason_codes=("split_adjustment_requires_review",),
    )

    assert quarantined.status is StrategyOutcomeStatus.QUARANTINED
    assert quarantined.underlying_price_return is None
    assert quarantined.reason_codes == ("split_adjustment_requires_review",)
