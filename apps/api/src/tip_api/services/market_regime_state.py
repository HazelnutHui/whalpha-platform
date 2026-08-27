"""Pure deterministic Phase 1b Market Regime state machine and chronological replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from typing import Iterable, Sequence

from tip_api.contracts.analytics.v1 import (
    MarketRegimeCompositeV1,
    MarketRegimeStateExplanationV1,
    MarketRegimeStateRecordV1,
    RegimeInitializationStatus,
    RegimeState,
    RegimeStateAvailability,
    RegimeTransitionStatus,
    StateThresholdDistanceV1,
)
from tip_api.parameters.market_regime.state_v1_0_1 import (
    BOOTSTRAP_CONFIRMATION_SESSIONS,
    CANDIDATE_BANDS,
    DEFENSIVE_RANK,
    PHASE1A_PARAMETER_FINGERPRINT,
    STATE_PARAMETER_FINGERPRINT,
    TRANSITION_RULES,
    TransitionRule,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


ZERO = Decimal("0")
HUNDRED = Decimal("100")
SCORE_QUANTUM = Decimal("0.0001")
STATE_DISCLAIMERS = (
    "Market regime is a research-environment label, not a buy recommendation.",
    "A high Composite does not mean an instrument should be purchased.",
    "Liquidity / participation uses participation proxies, not fund-flow data.",
    "A high Leadership / Dispersion score does not imply that current leaders must continue rising.",
    "The state is statistical decision support and does not establish causality.",
)


class MarketRegimeStateError(RuntimeError):
    """Raised when state replay cannot preserve a deterministic XNYS boundary."""


@dataclass(slots=True)
class _RuntimeState:
    confirmed: RegimeState | None = None
    provisional: bool = False
    pending: RegimeState | None = None
    pending_count: int = 0


def instantaneous_regime_candidate(score: Decimal | str) -> RegimeState:
    """Classify one available Composite under the fixed unhysterized bands."""

    value = _score(score)
    if value >= Decimal("70.0000"):
        return RegimeState.RISK_ON
    if value >= Decimal("50.0000"):
        return RegimeState.BALANCED
    if value >= Decimal("30.0000"):
        return RegimeState.DEFENSIVE
    return RegimeState.STRESS


def replay_regime_state_history(
    *,
    composites: Sequence[MarketRegimeCompositeV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    calendar: MarketSessionCalendar | None = None,
) -> tuple[tuple[MarketRegimeStateRecordV1, ...], tuple[MarketRegimeStateExplanationV1, ...]]:
    """Replay a complete deterministic history from an empty state."""

    return _replay(
        composites=composites,
        expected_sessions=expected_sessions,
        universe_id=universe_id,
        runtime=_RuntimeState(),
        calendar=calendar or ExchangeCalendar(),
    )


def append_regime_state_history(
    *,
    existing_history: Sequence[MarketRegimeStateRecordV1],
    composites: Sequence[MarketRegimeCompositeV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    calendar: MarketSessionCalendar | None = None,
) -> tuple[tuple[MarketRegimeStateRecordV1, ...], tuple[MarketRegimeStateExplanationV1, ...]]:
    """Resume from an explicit persisted row; result must equal full replay."""

    market_calendar = calendar or ExchangeCalendar()
    if not existing_history:
        return replay_regime_state_history(
            composites=composites,
            expected_sessions=expected_sessions,
            universe_id=universe_id,
            calendar=market_calendar,
        )
    _validate_existing_history(existing_history, universe_id)
    if not expected_sessions:
        return (), ()
    if market_calendar.previous_session(expected_sessions[0]) != existing_history[-1].as_of_session:
        raise MarketRegimeStateError("append session must immediately follow persisted XNYS history")
    last = existing_history[-1]
    runtime = _RuntimeState(
        confirmed=last.confirmed_state,
        provisional=last.state_is_provisional,
        pending=last.pending_target_state,
        pending_count=(last.consecutive_confirmation_sessions if last.pending_target_state is not None else 0),
    )
    return _replay(
        composites=composites,
        expected_sessions=expected_sessions,
        universe_id=universe_id,
        runtime=runtime,
        calendar=market_calendar,
    )


def state_history_fingerprint(records: Sequence[MarketRegimeStateRecordV1]) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in records])


def _replay(
    *,
    composites: Sequence[MarketRegimeCompositeV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    runtime: _RuntimeState,
    calendar: MarketSessionCalendar,
) -> tuple[tuple[MarketRegimeStateRecordV1, ...], tuple[MarketRegimeStateExplanationV1, ...]]:
    sessions = tuple(expected_sessions)
    _validate_expected_sessions(sessions, calendar)
    by_session: dict[date, MarketRegimeCompositeV1] = {}
    for composite in composites:
        if composite.universe_id != universe_id:
            raise MarketRegimeStateError("state replay cannot mix Universes")
        if composite.as_of_session not in sessions:
            raise MarketRegimeStateError("composite is outside the explicit replay session range")
        if composite.as_of_session in by_session:
            raise MarketRegimeStateError("duplicate state composite session")
        by_session[composite.as_of_session] = composite

    records: list[MarketRegimeStateRecordV1] = []
    explanations: list[MarketRegimeStateExplanationV1] = []
    for session in sessions:
        composite = by_session.get(session)
        if composite is None or composite.regime_score is None:
            record = _unavailable_record(session, universe_id, runtime)
        else:
            record = _available_record(composite, runtime)
        records.append(record)
        explanations.append(_explanation(record, composite))
    return tuple(records), tuple(explanations)


def _available_record(
    composite: MarketRegimeCompositeV1,
    runtime: _RuntimeState,
) -> MarketRegimeStateRecordV1:
    score = _score(composite.regime_score)
    candidate = instantaneous_regime_candidate(score)
    previous = runtime.confirmed
    rule: TransitionRule | None = None
    achieved_count = 0
    required = 0
    reasons = ["state_input_available", f"candidate_band_{candidate.value}"]

    if runtime.confirmed is None:
        required = BOOTSTRAP_CONFIRMATION_SESSIONS
        if runtime.pending is None:
            runtime.pending = candidate
            runtime.pending_count = 1
            achieved_count = 1
            status = RegimeTransitionStatus.INITIALIZATION_PENDING
            rule_id = "bootstrap_first_candidate"
            reasons.extend(("bootstrap_started", "first_candidate_not_auto_confirmed"))
        elif runtime.pending is candidate:
            runtime.confirmed = candidate
            runtime.provisional = False
            achieved_count = BOOTSTRAP_CONFIRMATION_SESSIONS
            runtime.pending = None
            runtime.pending_count = 0
            status = RegimeTransitionStatus.INITIALIZED_CONFIRMED
            rule_id = "bootstrap_two_bands_agree"
            reasons.append("bootstrap_two_consecutive_candidates_confirmed")
        else:
            runtime.confirmed = _more_defensive(runtime.pending, candidate)
            runtime.provisional = True
            achieved_count = BOOTSTRAP_CONFIRMATION_SESSIONS
            runtime.pending = None
            runtime.pending_count = 0
            status = RegimeTransitionStatus.INITIALIZED_PROVISIONAL
            rule_id = "bootstrap_disagreement_more_defensive"
            reasons.extend(("bootstrap_candidates_disagreed", "more_defensive_bootstrap_state_selected"))
    else:
        if runtime.provisional and candidate is runtime.confirmed:
            runtime.provisional = False
            runtime.pending = None
            runtime.pending_count = 0
            status = RegimeTransitionStatus.PROVISIONAL_CLEARED
            rule_id = "bootstrap_provisional_match_clear"
            reasons.append("provisional_state_matched_and_cleared")
        else:
            rule = _qualifying_rule(runtime.confirmed, score)
            if rule is None:
                reversed_pending = runtime.pending is not None
                runtime.pending = None
                runtime.pending_count = 0
                in_band = candidate is not runtime.confirmed
                status = (
                    RegimeTransitionStatus.PENDING_REVERSED
                    if reversed_pending
                    else RegimeTransitionStatus.HYSTERESIS_HELD
                    if in_band
                    else RegimeTransitionStatus.HELD
                )
                rule_id = "pending_reversed" if reversed_pending else "hysteresis_hold" if in_band else "state_hold"
                reasons.append(
                    "pending_transition_reversed"
                    if reversed_pending
                    else "candidate_inside_hysteresis_band"
                    if in_band
                    else "confirmed_state_held"
                )
            elif rule.immediate:
                runtime.confirmed = RegimeState.STRESS
                runtime.provisional = False
                runtime.pending = None
                runtime.pending_count = 0
                achieved_count = 1
                required = 1
                status = RegimeTransitionStatus.IMMEDIATE_STRESS_OVERRIDE
                rule_id = rule.rule_id
                reasons.extend(("immediate_stress_override", "adjacent_transition_exception_applied"))
            else:
                required = rule.confirmation_sessions
                if runtime.pending is RegimeState(rule.target_state):
                    runtime.pending_count += 1
                else:
                    runtime.pending = RegimeState(rule.target_state)
                    runtime.pending_count = 1
                achieved_count = runtime.pending_count
                if runtime.pending_count >= required:
                    runtime.confirmed = RegimeState(rule.target_state)
                    runtime.provisional = False
                    runtime.pending = None
                    runtime.pending_count = 0
                    status = RegimeTransitionStatus.SWITCHED
                    rule_id = rule.rule_id
                    reasons.extend(("transition_confirmation_satisfied", f"state_switched_to_{runtime.confirmed.value}"))
                else:
                    status = RegimeTransitionStatus.PENDING
                    rule_id = rule.rule_id
                    reasons.extend(("transition_confirmation_pending", f"pending_{rule.target_state}"))

    initialization = _initialization_status(runtime)
    active_rule = rule or _nearest_rule(runtime.confirmed or previous, score)
    entry, exit_, operator = _threshold_metadata(active_rule, candidate, runtime.confirmed is None)
    in_hysteresis = (
        previous is not None
        and candidate is not previous
        and rule is None
        and status in {RegimeTransitionStatus.HYSTERESIS_HELD, RegimeTransitionStatus.PENDING_REVERSED}
    )
    if runtime.pending is not None:
        required = _required_for_pending(runtime.confirmed, runtime.pending)
        achieved_count = runtime.pending_count
    remaining = max(0, required - achieved_count)
    supporting, conflicting = _dimension_evidence(composite, score)
    provisional = MarketRegimeStateRecordV1(
        state_parameter_fingerprint=STATE_PARAMETER_FINGERPRINT,
        phase1a_parameter_fingerprint=PHASE1A_PARAMETER_FINGERPRINT,
        as_of_session=composite.as_of_session,
        universe_id=composite.universe_id,
        composite=_score_string(score),
        instantaneous_candidate_state=candidate,
        confirmed_state=runtime.confirmed,
        previous_confirmed_state=previous,
        state_is_provisional=runtime.provisional,
        transition_status=status,
        transition_rule_id=rule_id,
        pending_target_state=runtime.pending,
        consecutive_confirmation_sessions=achieved_count,
        required_confirmation_sessions=required,
        entry_threshold=entry,
        exit_threshold=exit_,
        boundary_operator=operator,
        initialization_status=initialization,
        state_availability=RegimeStateAvailability.AVAILABLE,
        stale_state=False,
        in_hysteresis_band=in_hysteresis,
        confirmation_sessions_remaining=remaining,
        threshold_distances=_threshold_distances(score, previous or runtime.confirmed),
        supporting_dimension_ids=supporting,
        conflicting_dimension_ids=conflicting,
        reason_codes=tuple(reasons),
        source_composite_fingerprint=composite.logical_fingerprint,
        logical_fingerprint="0" * 64,
    )
    return _with_fingerprint(provisional)


def _unavailable_record(
    session: date,
    universe_id: str,
    runtime: _RuntimeState,
) -> MarketRegimeStateRecordV1:
    previous = runtime.confirmed
    required = _required_for_pending(runtime.confirmed, runtime.pending) if runtime.pending is not None else 0
    status = (
        RegimeTransitionStatus.UNAVAILABLE_STALE
        if runtime.confirmed is not None
        else RegimeTransitionStatus.UNAVAILABLE_UNINITIALIZED
    )
    reasons = (
        "composite_unavailable",
        "confirmation_counter_paused",
        "prior_confirmed_state_stale" if runtime.confirmed is not None else "state_not_initialized",
    )
    provisional = MarketRegimeStateRecordV1(
        state_parameter_fingerprint=STATE_PARAMETER_FINGERPRINT,
        phase1a_parameter_fingerprint=PHASE1A_PARAMETER_FINGERPRINT,
        as_of_session=session,
        universe_id=universe_id,
        composite=None,
        instantaneous_candidate_state=None,
        confirmed_state=runtime.confirmed,
        previous_confirmed_state=previous,
        state_is_provisional=runtime.provisional,
        transition_status=status,
        transition_rule_id="missing_composite_pause",
        pending_target_state=runtime.pending,
        consecutive_confirmation_sessions=runtime.pending_count,
        required_confirmation_sessions=required,
        entry_threshold=None,
        exit_threshold=None,
        boundary_operator=None,
        initialization_status=_initialization_status(runtime),
        state_availability=RegimeStateAvailability.UNAVAILABLE,
        stale_state=True,
        in_hysteresis_band=False,
        confirmation_sessions_remaining=max(0, required - runtime.pending_count),
        threshold_distances=(),
        supporting_dimension_ids=(),
        conflicting_dimension_ids=(),
        reason_codes=reasons,
        source_composite_fingerprint=None,
        logical_fingerprint="0" * 64,
    )
    return _with_fingerprint(provisional)


def _qualifying_rule(current: RegimeState, score: Decimal) -> TransitionRule | None:
    candidates = [
        item
        for item in TRANSITION_RULES
        if (item.current_state == current.value or (item.current_state == "any_non_stress" and current is not RegimeState.STRESS))
        and _matches(score, item.operator, Decimal(item.threshold))
    ]
    return min(candidates, key=lambda item: item.priority) if candidates else None


def _nearest_rule(current: RegimeState | None, score: Decimal) -> TransitionRule | None:
    if current is None:
        return None
    candidates = [
        item
        for item in TRANSITION_RULES
        if item.current_state == current.value or (item.current_state == "any_non_stress" and current is not RegimeState.STRESS)
    ]
    return min(candidates, key=lambda item: (abs(score - Decimal(item.threshold)), item.priority)) if candidates else None


def _threshold_metadata(
    rule: TransitionRule | None,
    candidate: RegimeState,
    bootstrap: bool,
) -> tuple[str | None, str | None, str | None]:
    if bootstrap or rule is None:
        band = next(item for item in CANDIDATE_BANDS if item.state == candidate.value)
        if band.lower is not None:
            return band.lower, None, band.lower_operator
        return band.upper, None, band.upper_operator
    reciprocal = next(
        (
            item
            for item in TRANSITION_RULES
            if item.current_state == rule.target_state and item.target_state == rule.current_state
        ),
        None,
    )
    if rule.current_state == "any_non_stress":
        reciprocal = next(item for item in TRANSITION_RULES if item.rule_id == "stress_to_defensive")
    return rule.threshold, reciprocal.threshold if reciprocal is not None else None, rule.operator


def _threshold_distances(score: Decimal, state: RegimeState | None) -> tuple[StateThresholdDistanceV1, ...]:
    values = [
        StateThresholdDistanceV1(
            threshold_id="candidate_risk_on_lower",
            threshold="70.0000",
            signed_distance=_score_string(score - Decimal("70.0000")),
            boundary_operator=">=",
            threshold_kind="candidate_boundary",
        ),
        StateThresholdDistanceV1(
            threshold_id="candidate_balanced_lower",
            threshold="50.0000",
            signed_distance=_score_string(score - Decimal("50.0000")),
            boundary_operator=">=",
            threshold_kind="candidate_boundary",
        ),
        StateThresholdDistanceV1(
            threshold_id="candidate_defensive_lower",
            threshold="30.0000",
            signed_distance=_score_string(score - Decimal("30.0000")),
            boundary_operator=">=",
            threshold_kind="candidate_boundary",
        ),
    ]
    if state is not None:
        rules = sorted(
            (
                item
                for item in TRANSITION_RULES
                if item.current_state == state.value or (item.current_state == "any_non_stress" and state is not RegimeState.STRESS)
            ),
            key=lambda item: item.priority,
        )
        values.extend(
            StateThresholdDistanceV1(
                threshold_id=item.rule_id,
                threshold=item.threshold,
                signed_distance=_score_string(score - Decimal(item.threshold)),
                boundary_operator=item.operator,
                threshold_kind="transition_boundary",
            )
            for item in rules
        )
    return tuple(values)


def _dimension_evidence(
    composite: MarketRegimeCompositeV1,
    score: Decimal,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    conflict_values: list[tuple[Decimal, str]] = []
    for dimension in composite.dimensions:
        if dimension.score is None:
            continue
        value = Decimal(dimension.score)
        opposite = (score >= Decimal("50") and value < Decimal("50")) or (
            score < Decimal("50") and value >= Decimal("50")
        )
        if score - value >= Decimal("20") or opposite:
            conflict_values.append((abs(score - value), dimension.dimension_id))
    conflicting = tuple(item[1] for item in sorted(conflict_values, key=lambda item: (-item[0], item[1])))
    conflict_set = set(conflicting)
    support_values = [
        (Decimal(dimension.score_contribution or "0"), dimension.dimension_id)
        for dimension in composite.dimensions
        if dimension.score is not None
        and Decimal(dimension.score) >= Decimal("60")
        and dimension.dimension_id not in conflict_set
    ]
    supporting = tuple(item[1] for item in sorted(support_values, key=lambda item: (-item[0], item[1])))
    return supporting, conflicting


def _explanation(
    record: MarketRegimeStateRecordV1,
    composite: MarketRegimeCompositeV1 | None,
) -> MarketRegimeStateExplanationV1:
    if record.composite is None:
        candidate_text = "Composite is unavailable; no instantaneous candidate state is formed."
    else:
        candidate_text = (
            f"Composite {record.composite} maps to {record.instantaneous_candidate_state.value} "
            "under the fixed inclusive/exclusive V1 candidate bands."
        )
    transition_text = _transition_text(record)
    references = (
        (f"phase1a_composite:{record.source_composite_fingerprint}",)
        if record.source_composite_fingerprint is not None
        else ()
    )
    return MarketRegimeStateExplanationV1(
        state_parameter_fingerprint=STATE_PARAMETER_FINGERPRINT,
        as_of_session=record.as_of_session,
        universe_id=record.universe_id,
        composite=record.composite,
        candidate_state=record.instantaneous_candidate_state,
        confirmed_state=record.confirmed_state,
        candidate_band_text=candidate_text,
        transition_text=transition_text,
        supporting_dimension_ids=record.supporting_dimension_ids,
        conflicting_dimension_ids=record.conflicting_dimension_ids,
        threshold_distances=record.threshold_distances,
        confirmation_sessions_remaining=record.confirmation_sessions_remaining,
        in_hysteresis_band=record.in_hysteresis_band,
        source_input_references=references,
        reason_codes=record.reason_codes,
        disclaimers=STATE_DISCLAIMERS,
    )


def _transition_text(record: MarketRegimeStateRecordV1) -> str:
    confirmed = record.confirmed_state.value if record.confirmed_state is not None else "uninitialized"
    pending = record.pending_target_state.value if record.pending_target_state is not None else "none"
    return (
        f"Transition status {record.transition_status.value}; confirmed state {confirmed}; "
        f"pending target {pending}; {record.confirmation_sessions_remaining} confirmation session(s) remain."
    )


def _initialization_status(runtime: _RuntimeState) -> RegimeInitializationStatus:
    if runtime.confirmed is None:
        return (
            RegimeInitializationStatus.AWAITING_CONFIRMATION
            if runtime.pending is not None
            else RegimeInitializationStatus.UNINITIALIZED_UNAVAILABLE
        )
    return (
        RegimeInitializationStatus.INITIALIZED_PROVISIONAL
        if runtime.provisional
        else RegimeInitializationStatus.INITIALIZED
    )


def _required_for_pending(current: RegimeState | None, target: RegimeState | None) -> int:
    if target is None:
        return 0
    if current is None:
        return BOOTSTRAP_CONFIRMATION_SESSIONS
    rules = [
        item
        for item in TRANSITION_RULES
        if item.target_state == target.value
        and (item.current_state == current.value or (item.current_state == "any_non_stress" and current is not RegimeState.STRESS))
    ]
    return min(rules, key=lambda item: item.priority).confirmation_sessions if rules else 0


def _more_defensive(left: RegimeState, right: RegimeState) -> RegimeState:
    return left if DEFENSIVE_RANK[left.value] >= DEFENSIVE_RANK[right.value] else right


def _matches(value: Decimal, operator: str, threshold: Decimal) -> bool:
    return {
        ">=": value >= threshold,
        ">": value > threshold,
        "<=": value <= threshold,
        "<": value < threshold,
    }[operator]


def _validate_expected_sessions(sessions: tuple[date, ...], calendar: MarketSessionCalendar) -> None:
    if not sessions or tuple(sorted(sessions)) != sessions or len(set(sessions)) != len(sessions):
        raise MarketRegimeStateError("state sessions must be unique and ascending")
    for session in sessions:
        if not calendar.is_session(session):
            raise MarketRegimeStateError("state history contains a non-XNYS session")
    for previous, current in zip(sessions, sessions[1:], strict=False):
        if calendar.previous_session(current) != previous:
            raise MarketRegimeStateError("state session sequence has an XNYS gap")


def _validate_existing_history(history: Sequence[MarketRegimeStateRecordV1], universe_id: str) -> None:
    sessions = tuple(item.as_of_session for item in history)
    if tuple(sorted(sessions)) != sessions or len(set(sessions)) != len(sessions):
        raise MarketRegimeStateError("persisted history is not unique and ascending")
    if any(item.universe_id != universe_id for item in history):
        raise MarketRegimeStateError("persisted history mixes Universes")


def _score(value: Decimal | str) -> Decimal:
    with localcontext(_context()):
        result = Decimal(value)
        if not result.is_finite() or result < ZERO or result > HUNDRED:
            raise MarketRegimeStateError("Composite must be finite and within [0,100]")
        return result.quantize(SCORE_QUANTUM)


def _score_string(value: Decimal) -> str:
    with localcontext(_context()):
        return format(value.quantize(SCORE_QUANTUM), "f")


def _with_fingerprint(record: MarketRegimeStateRecordV1) -> MarketRegimeStateRecordV1:
    payload = record.model_dump(mode="json", exclude={"logical_fingerprint"})
    return record.model_copy(update={"logical_fingerprint": _fingerprint(payload)})


def _context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    return context


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
