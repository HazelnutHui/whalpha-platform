"""Pure deterministic Phase 5B candidate-context state replay."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Sequence
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateBreakoutAvailability,
    CandidateConfirmationCountSource,
    CandidateDataQualityStatus,
    CandidateOpportunityStage,
    CandidatePriorStateSourceV1,
    CandidatePriorStateSupportV1,
    CandidateStateAvailability,
    CandidateStateGateResultV1,
    CandidateStateObservationV1,
    CandidateStateTransitionStatus,
    OpportunityCandidateStateRecordV1,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    BASE_LIQUIDITY_FLOOR,
    BASE_PRICE_FLOOR,
    BASE_WATCH_CONFIDENCE,
    BASE_WATCH_SCORE,
    BREAKOUT_ENTER_SCORE,
    BREAKOUT_VOLUME_RATIO,
    CANDIDATE_STATE_PARAMETER_FINGERPRINT,
    CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
    ENTER_SCORE,
    ENTER_TO_PREPARE_SCORE,
    ENTER_TO_PREPARE_TREND_SCORE,
    INVALIDATION_SCORE,
    MISSING_STATE_HOLD_SESSIONS,
    PREPARE_RELATIVE_STRENGTH_SCORE,
    PREPARE_SCORE,
    PREPARE_TO_WATCH_MARKET_ALIGNMENT_SCORE,
    PREPARE_TO_WATCH_SCORE,
    PREPARE_TREND_SCORE,
    REENTRY_WATCH_SCORE,
    STATE_CONFIRMATION_SUPPORT_SESSION_CAP,
)


class OpportunityCandidateStateError(RuntimeError):
    """Raised when candidate state history cannot be replayed deterministically."""


@dataclass(slots=True)
class _RuntimeState:
    stage: CandidateOpportunityStage | None = None
    pending_target: CandidateOpportunityStage | None = None
    pending_rule_id: str | None = None
    pending_count: int = 0
    consecutive_missing_sessions: int = 0
    stage_confirmation_count: int = 0


@dataclass(frozen=True, slots=True)
class _Transition:
    rule_id: str
    target: CandidateOpportunityStage
    confirmation_sessions: int
    reason_code: str


def replay_opportunity_candidate_state_history(
    *,
    observations: Sequence[CandidateStateObservationV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    instrument_id: UUID,
    ticker: str,
    security_type: str,
) -> tuple[OpportunityCandidateStateRecordV1, ...]:
    """Replay candidate state from an empty ledger over explicit completed sessions."""

    runtime = _RuntimeState()
    return _replay(
        observations=observations,
        expected_sessions=expected_sessions,
        universe_id=universe_id,
        instrument_id=instrument_id,
        ticker=ticker,
        security_type=security_type,
        runtime=runtime,
    )


def append_opportunity_candidate_state_history(
    *,
    existing_history: Sequence[OpportunityCandidateStateRecordV1],
    observations: Sequence[CandidateStateObservationV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    instrument_id: UUID,
    ticker: str,
    security_type: str,
) -> tuple[OpportunityCandidateStateRecordV1, ...]:
    """Continue from an explicit ledger prefix without consulting external state."""

    if not existing_history:
        return replay_opportunity_candidate_state_history(
            observations=observations,
            expected_sessions=expected_sessions,
            universe_id=universe_id,
            instrument_id=instrument_id,
            ticker=ticker,
            security_type=security_type,
        )
    _validate_existing_history(
        existing_history,
        universe_id=universe_id,
        instrument_id=instrument_id,
        security_type=security_type,
    )
    sessions = tuple(expected_sessions)
    if sessions and sessions[0] <= existing_history[-1].as_of_session:
        raise OpportunityCandidateStateError("append sessions must be later than the persisted prefix")
    last = existing_history[-1]
    runtime = _RuntimeState(
        stage=last.final_stage,
        pending_target=last.pending_target_stage,
        pending_rule_id=last.transition_rule_id if last.pending_target_stage is not None else None,
        pending_count=last.confirmation_count_after if last.pending_target_stage is not None else 0,
        consecutive_missing_sessions=last.consecutive_missing_sessions,
        stage_confirmation_count=last.stage_confirmation_count_after,
    )
    return _replay(
        observations=observations,
        expected_sessions=sessions,
        universe_id=universe_id,
        instrument_id=instrument_id,
        ticker=ticker,
        security_type=security_type,
        runtime=runtime,
    )


def opportunity_candidate_state_history_fingerprint(
    records: Sequence[OpportunityCandidateStateRecordV1],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in records])


def candidate_prior_state_source_from_history(
    *,
    history: Sequence[OpportunityCandidateStateRecordV1],
    as_of_session: date,
    universe_id: str,
    instrument_ids: Sequence[UUID],
) -> CandidatePriorStateSourceV1:
    """Build the only scorer input allowed from an explicit compatible state-history prefix."""

    ordered_ids = tuple(sorted(instrument_ids, key=str))
    if len(ordered_ids) != len(set(ordered_ids)):
        raise OpportunityCandidateStateError("candidate prior-state source IDs must be unique")
    if not history:
        return CandidatePriorStateSourceV1(
            universe_id=universe_id,
            as_of_session=as_of_session,
            bootstrap=True,
            source_state_session=None,
            state_history_fingerprint=CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
            supports=(),
        )
    ordered_history = tuple(sorted(history, key=lambda item: (item.as_of_session, str(item.instrument_id))))
    if any(item.universe_id != universe_id or item.as_of_session >= as_of_session for item in ordered_history):
        raise OpportunityCandidateStateError("candidate prior-state history is incompatible with the requested batch")
    source_session = max(item.as_of_session for item in ordered_history)
    latest_by_id = {
        item.instrument_id: item
        for item in ordered_history
        if item.as_of_session == source_session
    }
    supports = tuple(
        CandidatePriorStateSupportV1(
            instrument_id=instrument_id,
            prior_stage=(latest_by_id[instrument_id].final_stage if instrument_id in latest_by_id else None),
            stage_confirmation_session_count=(
                latest_by_id[instrument_id].stage_confirmation_count_after if instrument_id in latest_by_id else 0
            ),
            source_state_record_fingerprint=(
                latest_by_id[instrument_id].logical_fingerprint if instrument_id in latest_by_id else None
            ),
        )
        for instrument_id in ordered_ids
    )
    return CandidatePriorStateSourceV1(
        universe_id=universe_id,
        as_of_session=as_of_session,
        bootstrap=False,
        source_state_session=source_session,
        state_history_fingerprint=_fingerprint(
            [item.model_dump(mode="json") for item in ordered_history]
        ),
        supports=supports,
    )


def _replay(
    *,
    observations: Sequence[CandidateStateObservationV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    instrument_id: UUID,
    ticker: str,
    security_type: str,
    runtime: _RuntimeState,
) -> tuple[OpportunityCandidateStateRecordV1, ...]:
    sessions = tuple(expected_sessions)
    _validate_sessions(sessions)
    if security_type not in {"CS", "ADRC"}:
        raise OpportunityCandidateStateError("candidate state permits only CS or ADRC security form")
    by_session: dict[date, CandidateStateObservationV1] = {}
    for observation in observations:
        candidate = observation.candidate
        if candidate.as_of_session not in sessions:
            raise OpportunityCandidateStateError("candidate observation is outside the explicit replay range")
        if candidate.as_of_session in by_session:
            raise OpportunityCandidateStateError("duplicate candidate state observation session")
        if (
            candidate.universe_id != universe_id
            or candidate.instrument_id != instrument_id
            or candidate.security_type != security_type
        ):
            raise OpportunityCandidateStateError("candidate state observation identity does not match replay key")
        if observation.confirmation_count_source is not CandidateConfirmationCountSource.PRIOR_CANDIDATE_STATE_HISTORY:
            raise OpportunityCandidateStateError("candidate confidence confirmation count must cite prior state history")
        by_session[candidate.as_of_session] = observation

    return tuple(
        _record_for_session(
            session=session,
            observation=by_session.get(session),
            universe_id=universe_id,
            instrument_id=instrument_id,
            ticker=ticker,
            security_type=security_type,
            runtime=runtime,
        )
        for session in sessions
    )


def _record_for_session(
    *,
    session: date,
    observation: CandidateStateObservationV1 | None,
    universe_id: str,
    instrument_id: UUID,
    ticker: str,
    security_type: str,
    runtime: _RuntimeState,
) -> OpportunityCandidateStateRecordV1:
    if (
        observation is not None
        and observation.candidate.confidence.confirmation_session_count
        != runtime.stage_confirmation_count
    ):
        raise OpportunityCandidateStateError(
            "candidate confidence confirmation count must equal the prior state-ledger stage count"
        )
    if observation is None or _required_state_fact_missing(observation):
        return _unavailable_record(
            session=session,
            observation=observation,
            universe_id=universe_id,
            instrument_id=instrument_id,
            ticker=ticker,
            security_type=security_type,
            runtime=runtime,
        )
    return _available_record(observation, runtime)


def _available_record(
    observation: CandidateStateObservationV1,
    runtime: _RuntimeState,
) -> OpportunityCandidateStateRecordV1:
    candidate = observation.candidate
    prior_stage = runtime.stage
    stage_confirmation_count_before = runtime.stage_confirmation_count
    runtime.consecutive_missing_sessions = 0
    gates = _gate_results(observation)
    gate_map = {item.gate_id: item.passed for item in gates}
    transition = _qualifying_transition(observation, prior_stage, gate_map)
    count_before = 0
    count_after = 0
    proposed = transition.target if transition is not None else prior_stage
    reasons = ["candidate_state_input_available"]

    if transition is None:
        reversed_pending = runtime.pending_target is not None
        runtime.pending_target = None
        runtime.pending_rule_id = None
        runtime.pending_count = 0
        status = (
            CandidateStateTransitionStatus.PENDING_REVERSED
            if reversed_pending
            else CandidateStateTransitionStatus.NOT_LISTED
            if prior_stage is None
            else CandidateStateTransitionStatus.HELD
        )
        rule_id = "pending_reversed" if reversed_pending else "not_listed_hold" if prior_stage is None else "stage_hold"
        reasons.append("pending_confirmation_reversed" if reversed_pending else "candidate_not_listed" if prior_stage is None else "candidate_stage_held")
    else:
        if runtime.pending_target is transition.target and runtime.pending_rule_id == transition.rule_id:
            count_before = runtime.pending_count
        runtime.pending_target = transition.target
        runtime.pending_rule_id = transition.rule_id
        runtime.pending_count = count_before + 1
        count_after = runtime.pending_count
        rule_id = transition.rule_id
        reasons.append(transition.reason_code)
        if runtime.pending_count >= transition.confirmation_sessions:
            runtime.stage = transition.target
            runtime.pending_target = None
            runtime.pending_rule_id = None
            runtime.pending_count = 0
            if transition.rule_id == "not_listed_to_watch":
                status = CandidateStateTransitionStatus.LISTED
            elif transition.target is CandidateOpportunityStage.INVALIDATED:
                status = CandidateStateTransitionStatus.INVALIDATED
                reasons.extend(("candidate_invalidated", "candidate_context_not_sale_action"))
            else:
                status = CandidateStateTransitionStatus.SWITCHED
            reasons.append(f"candidate_stage_switched_to_{transition.target.value}")
        else:
            status = CandidateStateTransitionStatus.PENDING
            reasons.append("candidate_transition_confirmation_pending")

    required = transition.confirmation_sessions if transition is not None else 0
    if runtime.stage is None:
        stage_confirmation_count_after = 0
    elif runtime.stage is prior_stage:
        stage_confirmation_count_after = min(
            stage_confirmation_count_before + 1,
            STATE_CONFIRMATION_SUPPORT_SESSION_CAP,
        )
    else:
        stage_confirmation_count_after = 1
    runtime.stage_confirmation_count = stage_confirmation_count_after
    breakout_triggered = (
        observation.breakout_fact.triggered
        if observation.breakout_fact.availability is CandidateBreakoutAvailability.AVAILABLE
        else None
    )
    provisional = OpportunityCandidateStateRecordV1(
        parameter_fingerprint=CANDIDATE_STATE_PARAMETER_FINGERPRINT,
        as_of_session=candidate.as_of_session,
        universe_id=candidate.universe_id,
        instrument_id=candidate.instrument_id,
        ticker=candidate.ticker,
        security_type=candidate.security_type,
        prior_stage=prior_stage,
        proposed_stage=proposed,
        final_stage=runtime.stage,
        transition_status=status,
        transition_rule_id=rule_id,
        pending_target_stage=runtime.pending_target,
        confirmation_count_before=count_before,
        confirmation_count_after=count_after,
        required_confirmation_sessions=required,
        confirmation_count_source=CandidateConfirmationCountSource.PRIOR_CANDIDATE_STATE_HISTORY,
        input_confidence_confirmation_session_count=candidate.confidence.confirmation_session_count,
        stage_confirmation_count_before=stage_confirmation_count_before,
        stage_confirmation_count_after=stage_confirmation_count_after,
        regime_state=observation.regime_state,
        base_score=candidate.base_score,
        confidence=candidate.confidence.confidence,
        breakout_triggered=breakout_triggered,
        state_availability=CandidateStateAvailability.AVAILABLE,
        stale_state=False,
        consecutive_missing_sessions=0,
        manual_review_required=runtime.stage is CandidateOpportunityStage.INVALIDATED,
        anomaly_or_quarantine=_anomaly_or_quarantine(observation),
        gate_results=gates,
        reason_codes=tuple(reasons),
        human_explanation=_explanation(status, runtime.stage),
        source_candidate_fingerprint=candidate.logical_fingerprint,
        logical_fingerprint="0" * 64,
    )
    return _with_fingerprint(provisional)


def _unavailable_record(
    *,
    session: date,
    observation: CandidateStateObservationV1 | None,
    universe_id: str,
    instrument_id: UUID,
    ticker: str,
    security_type: str,
    runtime: _RuntimeState,
) -> OpportunityCandidateStateRecordV1:
    prior_stage = runtime.stage
    stage_confirmation_count_before = runtime.stage_confirmation_count
    runtime.consecutive_missing_sessions += 1
    count_before = runtime.pending_count
    if runtime.consecutive_missing_sessions <= MISSING_STATE_HOLD_SESSIONS:
        status = CandidateStateTransitionStatus.UNAVAILABLE_STALE
        final_stage = runtime.stage
        stale = final_stage is not None
        manual_review = False
        count_after = runtime.pending_count
        stage_confirmation_count_after = runtime.stage_confirmation_count
        required = _pending_confirmation_requirement(runtime)
        pending_target = runtime.pending_target
        rule_id = runtime.pending_rule_id or "missing_required_observation_hold"
        reasons = ("missing_required_history", "confirmation_count_paused", "prior_candidate_stage_held_one_session")
    else:
        status = CandidateStateTransitionStatus.UNAVAILABLE_NULL
        runtime.stage = None
        runtime.pending_target = None
        runtime.pending_rule_id = None
        runtime.pending_count = 0
        runtime.stage_confirmation_count = 0
        final_stage = None
        stale = False
        manual_review = True
        count_after = 0
        stage_confirmation_count_after = 0
        required = 0
        pending_target = None
        rule_id = "missing_required_observation_expired"
        reasons = ("missing_required_history", "stale_state_hold_expired", "candidate_stage_null_manual_review_required")
    input_count = stage_confirmation_count_before
    provisional = OpportunityCandidateStateRecordV1(
        parameter_fingerprint=CANDIDATE_STATE_PARAMETER_FINGERPRINT,
        as_of_session=session,
        universe_id=universe_id,
        instrument_id=instrument_id,
        ticker=ticker,
        security_type=security_type,
        prior_stage=prior_stage,
        proposed_stage=None,
        final_stage=final_stage,
        transition_status=status,
        transition_rule_id=rule_id,
        pending_target_stage=pending_target,
        confirmation_count_before=count_before,
        confirmation_count_after=count_after,
        required_confirmation_sessions=required,
        confirmation_count_source=CandidateConfirmationCountSource.PRIOR_CANDIDATE_STATE_HISTORY,
        input_confidence_confirmation_session_count=input_count,
        stage_confirmation_count_before=stage_confirmation_count_before,
        stage_confirmation_count_after=stage_confirmation_count_after,
        regime_state=None,
        base_score=None,
        confidence=None,
        breakout_triggered=None,
        state_availability=CandidateStateAvailability.UNAVAILABLE,
        stale_state=stale,
        consecutive_missing_sessions=runtime.consecutive_missing_sessions,
        manual_review_required=manual_review,
        anomaly_or_quarantine=False,
        gate_results=(),
        reason_codes=reasons,
        human_explanation=(
            "Required candidate facts are missing; the prior candidate stage is held stale for this session and confirmation is paused."
            if final_stage is not None
            else "Required candidate facts remain missing; the candidate stage is null and requires manual review."
        ),
        source_candidate_fingerprint=None,
        logical_fingerprint="0" * 64,
    )
    return _with_fingerprint(provisional)


def _qualifying_transition(
    observation: CandidateStateObservationV1,
    stage: CandidateOpportunityStage | None,
    gates: dict[str, bool | None],
) -> _Transition | None:
    if stage in {CandidateOpportunityStage.WATCH, CandidateOpportunityStage.PREPARE, CandidateOpportunityStage.ENTER}:
        if gates["invalidation"]:
            return _Transition("active_to_invalidated", CandidateOpportunityStage.INVALIDATED, 1, "candidate_invalidation_condition_fired")
    if stage is None:
        if all(gates[item] for item in ("watch_score", "watch_confidence", "price_floor", "liquidity_floor", "quarantine_clear")):
            return _Transition("not_listed_to_watch", CandidateOpportunityStage.WATCH, 1, "watch_entry_gate_passed")
        return None
    if stage is CandidateOpportunityStage.WATCH:
        if all(gates[item] for item in ("prepare_score", "regime_not_stress", "relative_strength_prepare", "trend_prepare", "quarantine_clear")):
            return _Transition("watch_to_prepare", CandidateOpportunityStage.PREPARE, 2, "score_prepare_confirmed")
        return None
    if stage is CandidateOpportunityStage.PREPARE:
        if all(gates[item] for item in ("breakout_fact", "breakout_score", "regime_not_stress", "quarantine_clear")):
            return _Transition("prepare_to_enter_breakout", CandidateOpportunityStage.ENTER, 1, "breakout_participation_trigger")
        if all(gates[item] for item in ("enter_score", "price_floor", "liquidity_floor", "quarantine_clear")):
            return _Transition("prepare_to_enter", CandidateOpportunityStage.ENTER, 2, "score_enter_confirmed")
        if gates["prepare_to_watch"]:
            return _Transition("prepare_to_watch", CandidateOpportunityStage.WATCH, 2, "prepare_evidence_deteriorated")
        return None
    if stage is CandidateOpportunityStage.ENTER:
        if gates["enter_to_prepare"]:
            return _Transition("enter_to_prepare", CandidateOpportunityStage.PREPARE, 2, "trend_deterioration")
        return None
    if stage is CandidateOpportunityStage.INVALIDATED:
        if all(gates[item] for item in ("reentry_score", "price_floor", "liquidity_floor", "quarantine_clear")):
            return _Transition("invalidated_to_watch", CandidateOpportunityStage.WATCH, 3, "candidate_reentry_confirmation")
    return None


def _gate_results(observation: CandidateStateObservationV1) -> tuple[CandidateStateGateResultV1, ...]:
    candidate = observation.candidate
    score = _decimal(candidate.base_score, "base score")
    confidence = _decimal(candidate.confidence.confidence, "confidence")
    price = _decimal(candidate.latest_price, "latest price")
    liquidity = _decimal(candidate.median_dollar_volume_20, "median dollar volume")
    relative_strength = _component_score(observation, "stock_relative_strength")
    trend = _component_score(observation, "trend_quality")
    market_alignment = _component_score(observation, "market_alignment")
    anomaly = _anomaly_or_quarantine(observation)
    breakout = (
        observation.breakout_fact.triggered
        if observation.breakout_fact.availability is CandidateBreakoutAvailability.AVAILABLE
        else None
    )
    invalidation = (
        score < Decimal(INVALIDATION_SCORE)
        or price < Decimal(BASE_PRICE_FLOOR)
        or liquidity < Decimal(BASE_LIQUIDITY_FLOOR)
        or anomaly
        or observation.declared_invalidation_fired
    )
    return (
        _gate("watch_score", score >= Decimal(BASE_WATCH_SCORE), score, BASE_WATCH_SCORE, ">="),
        _gate("watch_confidence", confidence >= Decimal(BASE_WATCH_CONFIDENCE), confidence, BASE_WATCH_CONFIDENCE, ">="),
        _gate("price_floor", price >= Decimal(BASE_PRICE_FLOOR), price, BASE_PRICE_FLOOR, ">="),
        _gate("liquidity_floor", liquidity >= Decimal(BASE_LIQUIDITY_FLOOR), liquidity, BASE_LIQUIDITY_FLOOR, ">="),
        _gate("prepare_score", score >= Decimal(PREPARE_SCORE), score, PREPARE_SCORE, ">="),
        _gate("regime_not_stress", observation.regime_state is not None and observation.regime_state is not RegimeState.STRESS, None if observation.regime_state is None else observation.regime_state.value, "stress", "is_not"),
        _gate("relative_strength_prepare", relative_strength is not None and relative_strength >= Decimal(PREPARE_RELATIVE_STRENGTH_SCORE), relative_strength, PREPARE_RELATIVE_STRENGTH_SCORE, ">="),
        _gate("trend_prepare", trend is not None and trend >= Decimal(PREPARE_TREND_SCORE), trend, PREPARE_TREND_SCORE, ">="),
        _gate("enter_score", score >= Decimal(ENTER_SCORE), score, ENTER_SCORE, ">="),
        _gate("breakout_fact", breakout, observation.breakout_fact.current_volume_ratio, BREAKOUT_VOLUME_RATIO, ">="),
        _gate("breakout_score", score >= Decimal(BREAKOUT_ENTER_SCORE), score, BREAKOUT_ENTER_SCORE, ">="),
        _gate("enter_to_prepare", score < Decimal(ENTER_TO_PREPARE_SCORE) or (trend is not None and trend < Decimal(ENTER_TO_PREPARE_TREND_SCORE)), score, ENTER_TO_PREPARE_SCORE, "<"),
        _gate("prepare_to_watch", score < Decimal(PREPARE_TO_WATCH_SCORE) or (market_alignment is not None and market_alignment < Decimal(PREPARE_TO_WATCH_MARKET_ALIGNMENT_SCORE)), score, PREPARE_TO_WATCH_SCORE, "<"),
        _gate("invalidation", invalidation, score, INVALIDATION_SCORE, "<"),
        _gate("reentry_score", score >= Decimal(REENTRY_WATCH_SCORE), score, REENTRY_WATCH_SCORE, ">="),
        _gate("quarantine_clear", not anomaly, str(anomaly).lower(), "false", "is"),
    )


def _gate(
    gate_id: str,
    passed: bool | None,
    actual: Decimal | str | None,
    threshold: str | None,
    operator: str | None,
) -> CandidateStateGateResultV1:
    return CandidateStateGateResultV1(
        gate_id=gate_id,
        passed=passed,
        actual_value=None if actual is None else str(actual),
        threshold=threshold,
        boundary_operator=operator,
        reason_codes=(f"{gate_id}_{'unavailable' if passed is None else 'passed' if passed else 'failed'}",),
    )


def _required_state_fact_missing(observation: CandidateStateObservationV1) -> bool:
    candidate = observation.candidate
    return candidate.base_score is None or candidate.median_dollar_volume_20 is None


def _component_score(observation: CandidateStateObservationV1, component_id: str) -> Decimal | None:
    component = next((item for item in observation.candidate.components if item.component_id == component_id), None)
    return None if component is None or component.score is None else _decimal(component.score, component_id)


def _anomaly_or_quarantine(observation: CandidateStateObservationV1) -> bool:
    candidate = observation.candidate
    return (
        candidate.corporate_action_review_required
        or candidate.data_quality_status in {CandidateDataQualityStatus.QUARANTINED, CandidateDataQualityStatus.FAILED}
        or observation.declared_invalidation_fired
    )


def _pending_confirmation_requirement(runtime: _RuntimeState) -> int:
    if runtime.pending_rule_id in {"watch_to_prepare", "prepare_to_enter", "enter_to_prepare", "prepare_to_watch"}:
        return 2
    if runtime.pending_rule_id == "invalidated_to_watch":
        return 3
    if runtime.pending_rule_id is not None:
        return 1
    return 0


def _explanation(
    status: CandidateStateTransitionStatus,
    stage: CandidateOpportunityStage | None,
) -> str:
    if status is CandidateStateTransitionStatus.INVALIDATED:
        return "The research candidate is invalidated for review; this is not a sell instruction or an order."
    if stage is CandidateOpportunityStage.ENTER:
        return "EOD conditions meet the Enter research-candidate gate; this is not an order instruction."
    if stage is CandidateOpportunityStage.PREPARE:
        return "Several candidate conditions are improving, but an execution trigger is not implied."
    if stage is CandidateOpportunityStage.WATCH:
        return "The instrument remains a research candidate with evidence still requiring confirmation."
    return "The instrument is not currently assigned an actionable candidate stage."


def _validate_sessions(sessions: tuple[date, ...]) -> None:
    if not sessions:
        raise OpportunityCandidateStateError("candidate state replay requires explicit completed sessions")
    if tuple(sorted(sessions)) != sessions or len(set(sessions)) != len(sessions):
        raise OpportunityCandidateStateError("candidate state sessions must be unique and ascending")


def _validate_existing_history(
    records: Sequence[OpportunityCandidateStateRecordV1],
    *,
    universe_id: str,
    instrument_id: UUID,
    security_type: str,
) -> None:
    sessions = tuple(item.as_of_session for item in records)
    _validate_sessions(sessions)
    for item in records:
        if (
            item.universe_id != universe_id
            or item.instrument_id != instrument_id
            or item.security_type != security_type
        ):
            raise OpportunityCandidateStateError("persisted candidate state history does not match replay key")
        if item.parameter_fingerprint != CANDIDATE_STATE_PARAMETER_FINGERPRINT:
            raise OpportunityCandidateStateError("persisted candidate state parameter fingerprint mismatch")


def _decimal(value: str | None, label: str) -> Decimal:
    if value is None:
        raise OpportunityCandidateStateError(f"{label} is unavailable")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise OpportunityCandidateStateError(f"{label} is malformed") from exc
    if not parsed.is_finite():
        raise OpportunityCandidateStateError(f"{label} must be finite")
    return parsed


def _with_fingerprint(record: OpportunityCandidateStateRecordV1) -> OpportunityCandidateStateRecordV1:
    return record.model_copy(
        update={"logical_fingerprint": _fingerprint(record.model_dump(mode="json", exclude={"logical_fingerprint"}))}
    )


def _fingerprint(value: object) -> str:
    normalized = _normalize(value)
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _normalize(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {_normalize(str(key)): _normalize(item) for key, item in value.items()}
    return value
