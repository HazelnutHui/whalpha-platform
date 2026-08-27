"""Independent Phase 1b state-machine oracle; never imports the production state service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from typing import Sequence

from tip_api.contracts.analytics.v1 import (
    MarketRegimeCompositeV1,
    MarketRegimeStateExplanationV1,
    MarketRegimeStateRecordV1,
    RegimeState,
    StateOracleComparisonV1,
)
from tip_api.parameters.market_regime.state_v1_0_1 import (
    BOOTSTRAP_CONFIRMATION_SESSIONS,
    DEFENSIVE_RANK,
    PHASE1A_PARAMETER_FINGERPRINT,
    STATE_CALCULATION_VERSION,
    STATE_PARAMETER_FINGERPRINT,
    STATE_PARAMETER_SET_ID,
    TRANSITION_RULES,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


DISCLAIMERS = [
    "Market regime is a research-environment label, not a buy recommendation.",
    "A high Composite does not mean an instrument should be purchased.",
    "Liquidity / participation uses participation proxies, not fund-flow data.",
    "A high Leadership / Dispersion score does not imply that current leaders must continue rising.",
    "The state is statistical decision support and does not establish causality.",
]


@dataclass(slots=True)
class _Memory:
    confirmed: str | None = None
    provisional: bool = False
    pending: str | None = None
    count: int = 0


def compare_with_independent_state_oracle(
    *,
    composites: Sequence[MarketRegimeCompositeV1],
    expected_sessions: Sequence[date],
    universe_id: str,
    records: Sequence[MarketRegimeStateRecordV1],
    explanations: Sequence[MarketRegimeStateExplanationV1],
    append_full_replay_match: bool,
    restart_replay_match: bool,
    input_permutation_match: bool,
    future_prefix_stable: bool,
    calendar: MarketSessionCalendar | None = None,
) -> StateOracleComparisonV1:
    """Rebuild every state decision independently and compare every serialized field."""

    oracle_rows, oracle_explanations = _oracle_replay(
        composites=composites,
        expected_sessions=expected_sessions,
        universe_id=universe_id,
        calendar=calendar or ExchangeCalendar(),
    )
    mismatches: list[str] = []
    actual_rows = [item.model_dump(mode="json") for item in records]
    if len(actual_rows) != len(oracle_rows):
        mismatches.append(f"state_history.count:{len(actual_rows)}!={len(oracle_rows)}")
    for index, (actual, expected) in enumerate(zip(actual_rows, oracle_rows, strict=False)):
        _compare_value(f"state_history[{index}]", actual, expected, mismatches)
    actual_explanations = [item.model_dump(mode="json") for item in explanations]
    if len(actual_explanations) != len(oracle_explanations):
        mismatches.append(
            f"state_explanation.count:{len(actual_explanations)}!={len(oracle_explanations)}"
        )
    for index, (actual, expected) in enumerate(
        zip(actual_explanations, oracle_explanations, strict=False)
    ):
        _compare_value(f"state_explanation[{index}]", actual, expected, mismatches)
    for flag, value in (
        ("append_full_replay_match", append_full_replay_match),
        ("restart_replay_match", restart_replay_match),
        ("input_permutation_match", input_permutation_match),
        ("future_prefix_stable", future_prefix_stable),
    ):
        if not value:
            mismatches.append(f"{flag}:false")
    payload = {
        "universe_id": universe_id,
        "sessions": [item.isoformat() for item in expected_sessions],
        "rows": oracle_rows,
        "explanations": oracle_explanations,
    }
    return StateOracleComparisonV1(
        state_parameter_fingerprint=STATE_PARAMETER_FINGERPRINT,
        universe_id=universe_id,
        first_session=expected_sessions[0],
        last_session=expected_sessions[-1],
        compared_session_count=len(expected_sessions),
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        append_full_replay_match=append_full_replay_match,
        restart_replay_match=restart_replay_match,
        input_permutation_match=input_permutation_match,
        future_prefix_stable=future_prefix_stable,
        oracle_history_fingerprint=_fingerprint(payload),
    )


def compare_incremental_with_independent_state_oracle(
    *,
    prior_record: MarketRegimeStateRecordV1,
    composite: MarketRegimeCompositeV1,
    expected_session: date,
    universe_id: str,
    record: MarketRegimeStateRecordV1,
    explanation: MarketRegimeStateExplanationV1,
    restart_match: bool,
    calendar: MarketSessionCalendar | None = None,
) -> StateOracleComparisonV1:
    """Independently append one session from the exact persisted state row."""

    market_calendar = calendar or ExchangeCalendar()
    if prior_record.universe_id != universe_id or composite.universe_id != universe_id:
        raise ValueError("incremental oracle Universe mismatch")
    if market_calendar.previous_session(expected_session) != prior_record.as_of_session:
        raise ValueError("incremental oracle session is not the immediate XNYS successor")
    if composite.as_of_session != expected_session:
        raise ValueError("incremental oracle Composite session mismatch")
    memory = _Memory(
        confirmed=(prior_record.confirmed_state.value if prior_record.confirmed_state else None),
        provisional=prior_record.state_is_provisional,
        pending=(prior_record.pending_target_state.value if prior_record.pending_target_state else None),
        count=(
            prior_record.consecutive_confirmation_sessions
            if prior_record.pending_target_state is not None
            else 0
        ),
    )
    oracle_rows, oracle_explanations = _oracle_replay(
        composites=(composite,),
        expected_sessions=(expected_session,),
        universe_id=universe_id,
        calendar=market_calendar,
        memory=memory,
    )
    mismatches: list[str] = []
    _compare_value("state_history[0]", record.model_dump(mode="json"), oracle_rows[0], mismatches)
    _compare_value(
        "state_explanation[0]",
        explanation.model_dump(mode="json"),
        oracle_explanations[0],
        mismatches,
    )
    if not restart_match:
        mismatches.append("incremental_restart_match:false")
    payload = {
        "universe_id": universe_id,
        "prior_state_record_fingerprint": prior_record.logical_fingerprint,
        "sessions": [expected_session.isoformat()],
        "rows": oracle_rows,
        "explanations": oracle_explanations,
    }
    return StateOracleComparisonV1(
        state_parameter_fingerprint=STATE_PARAMETER_FINGERPRINT,
        universe_id=universe_id,
        first_session=expected_session,
        last_session=expected_session,
        compared_session_count=1,
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        append_full_replay_match=restart_match,
        restart_replay_match=restart_match,
        input_permutation_match=True,
        future_prefix_stable=True,
        oracle_history_fingerprint=_fingerprint(payload),
    )


def _oracle_replay(*, composites, expected_sessions, universe_id, calendar, memory=None):
    sessions = tuple(expected_sessions)
    if not sessions or tuple(sorted(sessions)) != sessions or len(set(sessions)) != len(sessions):
        raise ValueError("oracle sessions invalid")
    for session in sessions:
        if not calendar.is_session(session):
            raise ValueError("oracle non-XNYS session")
    for previous, current in zip(sessions, sessions[1:], strict=False):
        if calendar.previous_session(current) != previous:
            raise ValueError("oracle XNYS session gap")
    by_session = {}
    for composite in composites:
        if composite.universe_id != universe_id:
            raise ValueError("oracle Universe mix")
        if composite.as_of_session not in sessions or composite.as_of_session in by_session:
            raise ValueError("oracle duplicate/out-of-window Composite")
        by_session[composite.as_of_session] = composite

    memory = memory or _Memory()
    rows = []
    explanations = []
    for session in sessions:
        composite = by_session.get(session)
        if composite is None or composite.regime_score is None:
            row = _missing_row(session, universe_id, memory)
        else:
            row = _live_row(composite, memory)
        rows.append(row)
        explanations.append(_explanation(row))
    return rows, explanations


def _live_row(composite, memory):
    score = _decimal_score(composite.regime_score)
    candidate = _candidate(score)
    previous = memory.confirmed
    rule = None
    achieved = 0
    required = 0
    reasons = ["state_input_available", f"candidate_band_{candidate}"]
    if memory.confirmed is None:
        required = 2
        if memory.pending is None:
            memory.pending = candidate
            memory.count = 1
            achieved = 1
            status = "initialization_pending"
            rule_id = "bootstrap_first_candidate"
            reasons += ["bootstrap_started", "first_candidate_not_auto_confirmed"]
        elif memory.pending == candidate:
            memory.confirmed = candidate
            memory.provisional = False
            achieved = 2
            memory.pending = None
            memory.count = 0
            status = "initialized_confirmed"
            rule_id = "bootstrap_two_bands_agree"
            reasons += ["bootstrap_two_consecutive_candidates_confirmed"]
        else:
            memory.confirmed = max((memory.pending, candidate), key=lambda value: DEFENSIVE_RANK[value])
            memory.provisional = True
            achieved = 2
            memory.pending = None
            memory.count = 0
            status = "initialized_provisional"
            rule_id = "bootstrap_disagreement_more_defensive"
            reasons += ["bootstrap_candidates_disagreed", "more_defensive_bootstrap_state_selected"]
    elif memory.provisional and candidate == memory.confirmed:
        memory.provisional = False
        memory.pending = None
        memory.count = 0
        status = "provisional_cleared"
        rule_id = "bootstrap_provisional_match_clear"
        reasons += ["provisional_state_matched_and_cleared"]
    else:
        rule = _rule(memory.confirmed, score)
        if rule is None:
            reversed_pending = memory.pending is not None
            memory.pending = None
            memory.count = 0
            in_band = candidate != memory.confirmed
            status = "pending_reversed" if reversed_pending else "hysteresis_held" if in_band else "held"
            rule_id = "pending_reversed" if reversed_pending else "hysteresis_hold" if in_band else "state_hold"
            reasons += [
                "pending_transition_reversed" if reversed_pending else "candidate_inside_hysteresis_band" if in_band else "confirmed_state_held"
            ]
        elif rule.immediate:
            memory.confirmed = "stress"
            memory.provisional = False
            memory.pending = None
            memory.count = 0
            achieved = required = 1
            status = "immediate_stress_override"
            rule_id = rule.rule_id
            reasons += ["immediate_stress_override", "adjacent_transition_exception_applied"]
        else:
            required = rule.confirmation_sessions
            if memory.pending == rule.target_state:
                memory.count += 1
            else:
                memory.pending = rule.target_state
                memory.count = 1
            achieved = memory.count
            if memory.count >= required:
                memory.confirmed = rule.target_state
                memory.provisional = False
                memory.pending = None
                memory.count = 0
                status = "switched"
                rule_id = rule.rule_id
                reasons += ["transition_confirmation_satisfied", f"state_switched_to_{memory.confirmed}"]
            else:
                status = "pending"
                rule_id = rule.rule_id
                reasons += ["transition_confirmation_pending", f"pending_{rule.target_state}"]

    initialization = (
        "awaiting_confirmation"
        if memory.confirmed is None and memory.pending is not None
        else "uninitialized_unavailable"
        if memory.confirmed is None
        else "initialized_provisional"
        if memory.provisional
        else "initialized"
    )
    nearest = rule or _nearest(memory.confirmed or previous, score)
    entry, exit_, operator = _threshold_metadata(nearest, candidate, memory.confirmed is None)
    in_hysteresis = (
        previous is not None
        and candidate != previous
        and rule is None
        and status in {"hysteresis_held", "pending_reversed"}
    )
    if memory.pending is not None:
        required = _pending_required(memory.confirmed, memory.pending)
        achieved = memory.count
    remaining = max(0, required - achieved)
    supporting, conflicting = _evidence(composite, score)
    row = {
        "schema_version": "1.0",
        "contract_version": "market-regime-state/1.0",
        "calculation_version": STATE_CALCULATION_VERSION,
        "phase1a_calculation_version": "market-regime-opportunity-map-v1.0.0",
        "state_parameter_set_id": STATE_PARAMETER_SET_ID,
        "state_parameter_fingerprint": STATE_PARAMETER_FINGERPRINT,
        "phase1a_parameter_fingerprint": PHASE1A_PARAMETER_FINGERPRINT,
        "as_of_session": composite.as_of_session.isoformat(),
        "universe_id": composite.universe_id,
        "composite": _s4(score),
        "instantaneous_candidate_state": candidate,
        "confirmed_state": memory.confirmed,
        "previous_confirmed_state": previous,
        "state_is_provisional": memory.provisional,
        "transition_status": status,
        "transition_rule_id": rule_id,
        "pending_target_state": memory.pending,
        "consecutive_confirmation_sessions": achieved,
        "required_confirmation_sessions": required,
        "entry_threshold": entry,
        "exit_threshold": exit_,
        "boundary_operator": operator,
        "initialization_status": initialization,
        "state_availability": "available",
        "stale_state": False,
        "in_hysteresis_band": in_hysteresis,
        "confirmation_sessions_remaining": remaining,
        "threshold_distances": _distances(score, previous or memory.confirmed),
        "supporting_dimension_ids": supporting,
        "conflicting_dimension_ids": conflicting,
        "reason_codes": reasons,
        "source_composite_fingerprint": composite.logical_fingerprint,
    }
    row["logical_fingerprint"] = _fingerprint(row)
    return row


def _missing_row(session, universe_id, memory):
    previous = memory.confirmed
    required = _pending_required(memory.confirmed, memory.pending) if memory.pending is not None else 0
    row = {
        "schema_version": "1.0",
        "contract_version": "market-regime-state/1.0",
        "calculation_version": STATE_CALCULATION_VERSION,
        "phase1a_calculation_version": "market-regime-opportunity-map-v1.0.0",
        "state_parameter_set_id": STATE_PARAMETER_SET_ID,
        "state_parameter_fingerprint": STATE_PARAMETER_FINGERPRINT,
        "phase1a_parameter_fingerprint": PHASE1A_PARAMETER_FINGERPRINT,
        "as_of_session": session.isoformat(),
        "universe_id": universe_id,
        "composite": None,
        "instantaneous_candidate_state": None,
        "confirmed_state": memory.confirmed,
        "previous_confirmed_state": previous,
        "state_is_provisional": memory.provisional,
        "transition_status": "unavailable_stale" if memory.confirmed is not None else "unavailable_uninitialized",
        "transition_rule_id": "missing_composite_pause",
        "pending_target_state": memory.pending,
        "consecutive_confirmation_sessions": memory.count,
        "required_confirmation_sessions": required,
        "entry_threshold": None,
        "exit_threshold": None,
        "boundary_operator": None,
        "initialization_status": (
            "awaiting_confirmation"
            if memory.confirmed is None and memory.pending is not None
            else "uninitialized_unavailable"
            if memory.confirmed is None
            else "initialized_provisional"
            if memory.provisional
            else "initialized"
        ),
        "state_availability": "unavailable",
        "stale_state": True,
        "in_hysteresis_band": False,
        "confirmation_sessions_remaining": max(0, required - memory.count),
        "threshold_distances": [],
        "supporting_dimension_ids": [],
        "conflicting_dimension_ids": [],
        "reason_codes": [
            "composite_unavailable",
            "confirmation_counter_paused",
            "prior_confirmed_state_stale" if memory.confirmed is not None else "state_not_initialized",
        ],
        "source_composite_fingerprint": None,
    }
    row["logical_fingerprint"] = _fingerprint(row)
    return row


def _explanation(row):
    if row["composite"] is None:
        candidate_text = "Composite is unavailable; no instantaneous candidate state is formed."
    else:
        candidate_text = (
            f"Composite {row['composite']} maps to {row['instantaneous_candidate_state']} "
            "under the fixed inclusive/exclusive V1 candidate bands."
        )
    confirmed = row["confirmed_state"] or "uninitialized"
    pending = row["pending_target_state"] or "none"
    transition_text = (
        f"Transition status {row['transition_status']}; confirmed state {confirmed}; "
        f"pending target {pending}; {row['confirmation_sessions_remaining']} confirmation session(s) remain."
    )
    return {
        "schema_version": "1.0",
        "calculation_version": STATE_CALCULATION_VERSION,
        "state_parameter_fingerprint": STATE_PARAMETER_FINGERPRINT,
        "as_of_session": row["as_of_session"],
        "universe_id": row["universe_id"],
        "template_id": "market_regime_state_transition_v1",
        "composite": row["composite"],
        "candidate_state": row["instantaneous_candidate_state"],
        "confirmed_state": row["confirmed_state"],
        "candidate_band_text": candidate_text,
        "transition_text": transition_text,
        "supporting_dimension_ids": row["supporting_dimension_ids"],
        "conflicting_dimension_ids": row["conflicting_dimension_ids"],
        "threshold_distances": row["threshold_distances"],
        "confirmation_sessions_remaining": row["confirmation_sessions_remaining"],
        "in_hysteresis_band": row["in_hysteresis_band"],
        "source_input_references": (
            [f"phase1a_composite:{row['source_composite_fingerprint']}"]
            if row["source_composite_fingerprint"] is not None
            else []
        ),
        "reason_codes": row["reason_codes"],
        "disclaimers": DISCLAIMERS,
    }


def _candidate(score):
    return "risk_on" if score >= Decimal("70") else "balanced" if score >= Decimal("50") else "defensive" if score >= Decimal("30") else "stress"


def _rule(current, score):
    values = [
        item for item in TRANSITION_RULES
        if (item.current_state == current or (item.current_state == "any_non_stress" and current != "stress"))
        and _match(score, item.operator, Decimal(item.threshold))
    ]
    return min(values, key=lambda item: item.priority) if values else None


def _nearest(current, score):
    if current is None:
        return None
    values = [
        item for item in TRANSITION_RULES
        if item.current_state == current or (item.current_state == "any_non_stress" and current != "stress")
    ]
    return min(values, key=lambda item: (abs(score - Decimal(item.threshold)), item.priority)) if values else None


def _threshold_metadata(rule, candidate, bootstrap):
    if bootstrap or rule is None:
        return ({"risk_on": "70.0000", "balanced": "50.0000", "defensive": "30.0000", "stress": "30.0000"}[candidate], None, ">=" if candidate != "stress" else "<")
    reciprocal = next((item for item in TRANSITION_RULES if item.current_state == rule.target_state and item.target_state == rule.current_state), None)
    if rule.current_state == "any_non_stress":
        reciprocal = next(item for item in TRANSITION_RULES if item.rule_id == "stress_to_defensive")
    return rule.threshold, reciprocal.threshold if reciprocal else None, rule.operator


def _distances(score, current):
    rows = [
        _distance("candidate_risk_on_lower", "70.0000", score, ">=", "candidate_boundary"),
        _distance("candidate_balanced_lower", "50.0000", score, ">=", "candidate_boundary"),
        _distance("candidate_defensive_lower", "30.0000", score, ">=", "candidate_boundary"),
    ]
    if current is not None:
        for item in sorted(
            (
                rule for rule in TRANSITION_RULES
                if rule.current_state == current or (rule.current_state == "any_non_stress" and current != "stress")
            ),
            key=lambda value: value.priority,
        ):
            rows.append(_distance(item.rule_id, item.threshold, score, item.operator, "transition_boundary"))
    return rows


def _distance(identifier, threshold, score, operator, kind):
    return {
        "threshold_id": identifier,
        "threshold": threshold,
        "signed_distance": _s4(score - Decimal(threshold)),
        "boundary_operator": operator,
        "threshold_kind": kind,
    }


def _evidence(composite, score):
    conflicts = []
    for dimension in composite.dimensions:
        if dimension.score is None:
            continue
        value = Decimal(dimension.score)
        opposite = (score >= Decimal("50") and value < Decimal("50")) or (score < Decimal("50") and value >= Decimal("50"))
        if score - value >= Decimal("20") or opposite:
            conflicts.append((abs(score - value), dimension.dimension_id))
    conflicting = [item[1] for item in sorted(conflicts, key=lambda item: (-item[0], item[1]))]
    conflict_set = set(conflicting)
    supporting = [
        (Decimal(item.score_contribution or "0"), item.dimension_id)
        for item in composite.dimensions
        if item.score is not None and Decimal(item.score) >= Decimal("60") and item.dimension_id not in conflict_set
    ]
    return [item[1] for item in sorted(supporting, key=lambda item: (-item[0], item[1]))], conflicting


def _pending_required(current, target):
    if target is None:
        return 0
    if current is None:
        return BOOTSTRAP_CONFIRMATION_SESSIONS
    values = [
        item for item in TRANSITION_RULES
        if item.target_state == target and (item.current_state == current or (item.current_state == "any_non_stress" and current != "stress"))
    ]
    return min(values, key=lambda item: item.priority).confirmation_sessions if values else 0


def _match(value, operator, threshold):
    if operator == ">=":
        return value >= threshold
    if operator == ">":
        return value > threshold
    if operator == "<=":
        return value <= threshold
    return value < threshold


def _decimal_score(value):
    with localcontext(_context()):
        result = Decimal(value)
        if not result.is_finite() or result < 0 or result > 100:
            raise ValueError("oracle Composite invalid")
        return result.quantize(Decimal("0.0001"))


def _s4(value):
    with localcontext(_context()):
        return format(value.quantize(Decimal("0.0001")), "f")


def _context():
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    return context


def _compare_value(path, actual, expected, mismatches):
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual) != set(expected):
            mismatches.append(f"{path}.keys:{sorted(actual)}!={sorted(expected)}")
            return
        for key in sorted(actual):
            _compare_value(f"{path}.{key}", actual[key], expected[key], mismatches)
        return
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            mismatches.append(f"{path}.length:{len(actual)}!={len(expected)}")
            return
        for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
            _compare_value(f"{path}[{index}]", left, right, mismatches)
        return
    if actual != expected:
        mismatches.append(f"{path}:{actual!r}!={expected!r}")


def _fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
