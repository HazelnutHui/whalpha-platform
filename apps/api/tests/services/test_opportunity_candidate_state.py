from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, Inexact, ROUND_DOWN, Rounded, localcontext
from uuid import UUID

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateBreakoutAvailability,
    CandidateBreakoutFactV1,
    CandidateComponentV1,
    CandidateConfidenceV1,
    CandidateDataQualityStatus,
    CandidateMetricAvailability,
    CandidateOpportunityStage,
    CandidateStateObservationV1,
    OpportunityCandidateScoreV1,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_PARAMETER_FINGERPRINT,
    CANDIDATE_STATE_PARAMETER_FINGERPRINT,
    COMPONENT_PARAMETERS,
    candidate_state_parameter_payload,
)
from tip_api.services.opportunity_candidate_state import (
    OpportunityCandidateStateError,
    append_opportunity_candidate_state_history,
    candidate_prior_state_source_from_history,
    opportunity_candidate_state_history_fingerprint,
    replay_opportunity_candidate_state_history,
)


INSTRUMENT_ID = UUID("b3c193ec-99ef-5455-a69d-2e17789dc41b")
UNIVERSE_ID = "provider_classified_common_shares_v1"
TICKER = "TEST"
START = date(2026, 8, 3)


def _component(component_id: str, weight: int, score: Decimal | None) -> CandidateComponentV1:
    return CandidateComponentV1(
        component_id=component_id,
        configured_weight=f"{weight}.0000",
        effective_weight=("0.0000" if score is None else f"{weight}.0000"),
        score=None if score is None else f"{score:.4f}",
        contribution=None if score is None else f"{score * Decimal(weight) / Decimal(100):.4f}",
        availability=(CandidateMetricAvailability.UNAVAILABLE if score is None else CandidateMetricAvailability.AVAILABLE),
        cap_applied=None,
        metrics=(),
        reason_codes=(("required_submetric_missing",) if score is None else ("fixture_component",)),
    )


def _candidate(
    session: date,
    score: str | None,
    *,
    ticker: str = TICKER,
    trend: str | None = None,
    relative_strength: str | None = None,
    market_alignment: str | None = None,
    price: str = "20",
    liquidity: str | None = "50000000",
    quarantined: bool = False,
) -> OpportunityCandidateScoreV1:
    base = None if score is None else Decimal(score)
    overrides = {
        "trend_quality": trend,
        "stock_relative_strength": relative_strength,
        "market_alignment": market_alignment,
    }
    components = tuple(
        _component(
            parameter.component_id,
            parameter.configured_weight,
            None
            if base is None
            else Decimal(overrides[parameter.component_id])
            if overrides.get(parameter.component_id) is not None
            else base,
        )
        for parameter in COMPONENT_PARAMETERS
    )
    calculated_base = None if base is None else sum(Decimal(item.contribution) for item in components if item.contribution)
    return OpportunityCandidateScoreV1(
        parameter_fingerprint=CANDIDATE_PARAMETER_FINGERPRINT,
        as_of_session=session,
        universe_id=UNIVERSE_ID,
        instrument_id=INSTRUMENT_ID,
        ticker=ticker,
        security_type="CS",
        latest_data_session=session,
        base_score=None if calculated_base is None else f"{calculated_base:.4f}",
        adjusted_score=None if calculated_base is None else f"{calculated_base:.4f}",
        configured_weight_available="0.0000" if base is None else "100.0000",
        missingness_penalty="100.0000" if base is None else "0.0000",
        components=components,
        confidence=CandidateConfidenceV1(
            source_completeness="1.0000",
            history_completeness="1.0000",
            relationship_support="0.4000",
            state_confirmation_support="0.0000",
            confirmation_session_count=0,
            prior_state_record_fingerprint=None,
            confidence="0.7300",
        ),
        latest_price=price,
        median_dollar_volume_20=liquidity,
        annualized_volatility_10="0.3000000000",
        maximum_absolute_open_gap_5="0.0400000000",
        current_volume_ratio="1.3000000000",
        primary_driver_instrument_id=UUID("cfe87a18-41ec-50a3-a95e-5c76e868ecf5"),
        primary_driver_ticker="SPY",
        driver_correlation_20="0.5000000000",
        relationship_kind="price_derived_exposure_proxy",
        corporate_action_review_required=quarantined,
        data_quality_status=(CandidateDataQualityStatus.QUARANTINED if quarantined else CandidateDataQualityStatus.PASSED),
        supporting_evidence=(),
        counterevidence=(),
        invalidation_conditions=("base_score_below_45",),
        reason_codes=("fixture",),
        warnings=(),
        logical_fingerprint=f"{session.toordinal():064x}"[-64:],
    )


def _observation(
    index: int,
    score: str | None,
    *,
    regime: RegimeState | None = RegimeState.BALANCED,
    breakout: bool = False,
    breakout_available: bool = True,
    **candidate_kwargs,
) -> CandidateStateObservationV1:
    session = START + timedelta(days=index)
    if breakout_available:
        fact = CandidateBreakoutFactV1(
            as_of_session=session,
            instrument_id=INSTRUMENT_ID,
            availability=CandidateBreakoutAvailability.AVAILABLE,
            close="101" if breakout else "99",
            prior_five_session_close_high="100",
            current_volume_ratio="1.20" if breakout else "1.19",
            prior_five_sessions=tuple(session - timedelta(days=offset) for offset in range(5, 0, -1)),
            triggered=breakout,
            missing_reason=None,
            reason_codes=("typed_breakout_fact",),
        )
    else:
        fact = CandidateBreakoutFactV1(
            as_of_session=session,
            instrument_id=INSTRUMENT_ID,
            availability=CandidateBreakoutAvailability.UNAVAILABLE,
            close=None,
            prior_five_session_close_high=None,
            current_volume_ratio=None,
            prior_five_sessions=(),
            triggered=None,
            missing_reason="insufficient_prior_five_session_history",
            reason_codes=("insufficient_prior_five_session_history",),
        )
    return CandidateStateObservationV1(
        candidate=_candidate(session, score, **candidate_kwargs),
        regime_state=regime,
        breakout_fact=fact,
    )


def _run(observations):
    _, records = _bind_observations(tuple(observations))
    return records


def _with_confirmation_count(
    observation: CandidateStateObservationV1,
    count: int,
    prior_fingerprint: str | None,
) -> CandidateStateObservationV1:
    state_support = ("0.0000", "0.3333", "0.6667", "1.0000")[count]
    confidence = ("0.7300", "0.7800", "0.8300", "0.8800")[count]
    confidence_record = observation.candidate.confidence.model_copy(
        update={
            "state_confirmation_support": state_support,
            "confirmation_session_count": count,
            "prior_state_record_fingerprint": prior_fingerprint if count else None,
            "confidence": confidence,
        }
    )
    candidate = observation.candidate.model_copy(update={"confidence": confidence_record})
    return observation.model_copy(update={"candidate": candidate})


def _bind_observations(
    observations: tuple[CandidateStateObservationV1, ...],
) -> tuple[tuple[CandidateStateObservationV1, ...], tuple]:
    history = ()
    bound: list[CandidateStateObservationV1] = []
    for observation in observations:
        count = history[-1].stage_confirmation_count_after if history else 0
        prior_fingerprint = history[-1].logical_fingerprint if history and count else None
        current = _with_confirmation_count(observation, count, prior_fingerprint)
        records = append_opportunity_candidate_state_history(
            existing_history=history,
            observations=(current,),
            expected_sessions=(current.candidate.as_of_session,),
            universe_id=UNIVERSE_ID,
            instrument_id=INSTRUMENT_ID,
            ticker=TICKER,
            security_type="CS",
        )
        history = (*history, *records)
        bound.append(current)
    return tuple(bound), history


def test_parameter_contract_and_breakout_fact_are_fixed_and_typed() -> None:
    assert len(CANDIDATE_STATE_PARAMETER_FINGERPRINT) == 64
    assert candidate_state_parameter_payload()["confirmation_count_source"] == "prior_candidate_state_history"
    with pytest.raises(ValueError, match="reconcile"):
        _observation(0, "60", breakout=True).breakout_fact.model_copy(update={"triggered": False}).model_validate(
            _observation(0, "60", breakout=True).breakout_fact.model_dump() | {"triggered": False}
        )


def test_watch_prepare_and_enter_use_fixed_confirmation_counts() -> None:
    records = _run(
        (
            _observation(0, "60"),
            _observation(1, "70", trend="60", relative_strength="60"),
            _observation(2, "70", trend="60", relative_strength="60"),
            _observation(3, "80"),
            _observation(4, "80"),
        )
    )
    assert records[0].final_stage is CandidateOpportunityStage.WATCH
    assert records[1].pending_target_stage is CandidateOpportunityStage.PREPARE
    assert records[1].confirmation_count_after == 1
    assert records[2].final_stage is CandidateOpportunityStage.PREPARE
    assert records[3].pending_target_stage is CandidateOpportunityStage.ENTER
    assert records[4].final_stage is CandidateOpportunityStage.ENTER
    assert all(item.confirmation_count_source == "prior_candidate_state_history" for item in records)
    assert tuple(item.stage_confirmation_count_before for item in records) == (0, 1, 2, 1, 2)
    assert tuple(item.stage_confirmation_count_after for item in records) == (1, 2, 1, 2, 1)


def test_prepare_breakout_trigger_enters_in_one_session() -> None:
    records = _run(
        (
            _observation(0, "60"),
            _observation(1, "70", trend="60", relative_strength="60"),
            _observation(2, "70", trend="60", relative_strength="60"),
            _observation(3, "70", breakout=True),
        )
    )
    assert records[-1].final_stage is CandidateOpportunityStage.ENTER
    assert records[-1].transition_rule_id == "prepare_to_enter_breakout"
    assert records[-1].breakout_triggered is True
    assert "breakout_participation_trigger" in records[-1].reason_codes


def test_active_candidate_is_invalidated_not_exited_or_sold_and_reentry_needs_three() -> None:
    observations = [
        _observation(0, "60"),
        _observation(1, "40"),
        _observation(2, "60"),
        _observation(3, "60"),
        _observation(4, "60"),
    ]
    records = _run(observations)
    assert records[1].final_stage is CandidateOpportunityStage.INVALIDATED
    assert records[1].transition_status == "invalidated"
    assert "not a sell instruction" in records[1].human_explanation
    assert records[3].pending_target_stage is CandidateOpportunityStage.WATCH
    assert records[4].final_stage is CandidateOpportunityStage.WATCH


def test_missing_fact_pauses_once_then_nulls_state_for_manual_review() -> None:
    records = _run((_observation(0, "60"), _observation(1, None), _observation(2, None)))
    assert records[1].final_stage is CandidateOpportunityStage.WATCH
    assert records[1].stale_state
    assert records[1].transition_status == "unavailable_stale"
    assert records[2].final_stage is None
    assert not records[2].stale_state
    assert records[2].manual_review_required
    assert records[2].transition_status == "unavailable_null"


def test_replay_is_input_order_decimal_context_and_restart_stable() -> None:
    observations = tuple(
        _observation(index, score, trend="60", relative_strength="60")
        for index, score in enumerate(("60", "70", "70", "80", "80"))
    )
    sessions = tuple(item.candidate.as_of_session for item in observations)
    bound_observations, expected = _bind_observations(observations)
    shuffled = replay_opportunity_candidate_state_history(
        observations=tuple(reversed(bound_observations)),
        expected_sessions=sessions,
        universe_id=UNIVERSE_ID,
        instrument_id=INSTRUMENT_ID,
        ticker=TICKER,
        security_type="CS",
    )
    assert opportunity_candidate_state_history_fingerprint(shuffled) == opportunity_candidate_state_history_fingerprint(expected)
    suffix = append_opportunity_candidate_state_history(
        existing_history=expected[:3],
        observations=bound_observations[3:],
        expected_sessions=sessions[3:],
        universe_id=UNIVERSE_ID,
        instrument_id=INSTRUMENT_ID,
        ticker=TICKER,
        security_type="CS",
    )
    assert tuple(item.logical_fingerprint for item in expected[3:]) == tuple(item.logical_fingerprint for item in suffix)
    with localcontext() as context:
        context.prec = 9
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        trapped = _run(observations)
    assert opportunity_candidate_state_history_fingerprint(trapped) == opportunity_candidate_state_history_fingerprint(expected)


def test_ticker_is_daily_display_metadata_while_stable_id_mismatch_fails_closed() -> None:
    old_ticker = _observation(0, "60", ticker="OLDA")
    new_ticker = _observation(1, "60", ticker="NEWB")
    bound_observations, _ = _bind_observations((old_ticker, new_ticker))
    sessions = (START, START + timedelta(days=1), START + timedelta(days=2))
    replayed = replay_opportunity_candidate_state_history(
        observations=bound_observations,
        expected_sessions=sessions,
        universe_id=UNIVERSE_ID,
        instrument_id=INSTRUMENT_ID,
        ticker="NEWB",
        security_type="CS",
    )
    assert tuple(item.ticker for item in replayed) == ("OLDA", "NEWB", "NEWB")
    appended = append_opportunity_candidate_state_history(
        existing_history=replayed[:1],
        observations=(bound_observations[1],),
        expected_sessions=(START + timedelta(days=1),),
        universe_id=UNIVERSE_ID,
        instrument_id=INSTRUMENT_ID,
        ticker="NEWB",
        security_type="CS",
    )
    assert appended[0].ticker == "NEWB"

    observation = _observation(0, "60")
    with pytest.raises(OpportunityCandidateStateError, match="duplicate"):
        replay_opportunity_candidate_state_history(
            observations=(observation, observation),
            expected_sessions=(START,),
            universe_id=UNIVERSE_ID,
            instrument_id=INSTRUMENT_ID,
            ticker=TICKER,
            security_type="CS",
        )
    with pytest.raises(OpportunityCandidateStateError, match="identity"):
        replay_opportunity_candidate_state_history(
            observations=(observation,),
            expected_sessions=(START,),
            universe_id=UNIVERSE_ID,
            instrument_id=UUID("56b156a3-f31e-5dad-86f0-111707323aae"),
            ticker=TICKER,
            security_type="CS",
        )


def test_prior_state_source_is_derived_from_capped_stage_history_and_mismatch_fails() -> None:
    first = _run((_observation(0, "60"),))
    source = candidate_prior_state_source_from_history(
        history=first,
        as_of_session=START + timedelta(days=1),
        universe_id=UNIVERSE_ID,
        instrument_ids=(INSTRUMENT_ID,),
    )
    assert not source.bootstrap
    assert source.source_state_session == START
    assert source.supports[0].stage_confirmation_session_count == 1
    assert source.supports[0].source_state_record_fingerprint == first[0].logical_fingerprint

    mismatched = _observation(1, "60")
    with pytest.raises(OpportunityCandidateStateError, match="must equal"):
        append_opportunity_candidate_state_history(
            existing_history=first,
            observations=(mismatched,),
            expected_sessions=(START + timedelta(days=1),),
            universe_id=UNIVERSE_ID,
            instrument_id=INSTRUMENT_ID,
            ticker=TICKER,
            security_type="CS",
        )
