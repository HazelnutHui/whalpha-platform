"""Deterministic, preregistered Phase 2 ETF relationship calculations."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from datetime import date
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from typing import Any, Iterable, Mapping, Sequence

from tip_api.contracts.analytics.v1.etf_relationship import (
    EtfRelationshipExplanationV1,
    EtfRelationshipRecordV1,
    EtfRelationshipWindowMetricV1,
    MarketRegimeRelationshipComparisonV1,
    RegimeRelationshipAlignment,
    RelationshipAvailability,
    RelationshipConfidence,
    RelationshipState,
)
from tip_api.parameters.market_regime.relationship_v1_0_0 import (
    CORRELATION_MINIMUM_OBSERVATIONS,
    CORRELATION_PERTURBATION_WINDOWS,
    CORRELATION_POSITIVE_THRESHOLD,
    DIVERGENCE_SPREAD_THRESHOLD,
    ETF_BASKET,
    ETF_PAIRS,
    NUMERIC_SCALE,
    RATIO_PERCENTILE_WINDOW,
    RATIO_STATISTICS_MINIMUM_OBSERVATIONS,
    RATIO_STATISTICS_WINDOW,
    RELATIONSHIP_BREAK_CHANGE_THRESHOLD,
    RELATIONSHIP_BREAK_CURRENT_THRESHOLD,
    RELATIONSHIP_BREAK_PRIOR_THRESHOLD,
    RELATIONSHIP_CALCULATION_VERSION,
    RELATIONSHIP_PARAMETER_FINGERPRINT,
    ROTATION_Z_THRESHOLD,
    WINDOWS,
    EtfPairDefinition,
)
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.contracts.market_data.v1 import InstrumentType


class EtfRelationshipError(RuntimeError):
    """Raised when a relationship input violates the fail-closed contract."""


INTERNAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
for _signal in (InvalidOperation, DivisionByZero, Overflow):
    INTERNAL_CONTEXT.traps[_signal] = True

DISCLAIMER_SET = (
    "statistical_relationship_not_causal",
    "price_relationship_not_fund_flow",
    "relationship_state_not_trade_instruction",
    "short_history_not_predictive_validation",
)


def calculate_etf_relationship_history(
    *, panel: MarketRegimeInputPanel
) -> tuple[EtfRelationshipRecordV1, ...]:
    """Calculate every registered pair chronologically from one in-memory panel."""

    with localcontext(INTERNAL_CONTEXT):
        return _calculate_etf_relationship_history(panel)


def _calculate_etf_relationship_history(
    panel: MarketRegimeInputPanel,
) -> tuple[EtfRelationshipRecordV1, ...]:

    sessions = _validated_sessions(panel.sessions, panel.as_of_session)
    closes = _index_registered_closes(panel.bars, sessions)
    history: list[EtfRelationshipRecordV1] = []
    previous_by_pair: dict[str, EtfRelationshipRecordV1] = {}
    for end_index in range(min(WINDOWS), len(sessions)):
        for pair in ETF_PAIRS:
            prior = previous_by_pair.get(pair.pair_id)
            record = _calculate_pair(
                pair=pair,
                sessions=sessions,
                closes=closes,
                end_index=end_index,
                history_source_fingerprint=panel.history_source_fingerprint,
                previous=prior,
            )
            history.append(record)
            previous_by_pair[pair.pair_id] = record
    return tuple(history)


def append_etf_relationship_history(
    *,
    panel: MarketRegimeInputPanel,
    existing_history: Sequence[EtfRelationshipRecordV1],
    append_sessions: Sequence[date],
) -> tuple[EtfRelationshipRecordV1, ...]:
    """Return the newly appended suffix; results are derived from the full immutable panel."""

    full = calculate_etf_relationship_history(panel=panel)
    existing_keys = {(item.as_of_session, item.pair_id): item.logical_fingerprint for item in existing_history}
    for item in full:
        key = (item.as_of_session, item.pair_id)
        if key in existing_keys and existing_keys[key] != item.logical_fingerprint:
            raise EtfRelationshipError("existing relationship history does not match deterministic replay")
    wanted = set(append_sessions)
    if len(wanted) != len(tuple(append_sessions)):
        raise EtfRelationshipError("duplicate append session")
    return tuple(item for item in full if item.as_of_session in wanted and (item.as_of_session, item.pair_id) not in existing_keys)


def current_relationship_records(
    history: Sequence[EtfRelationshipRecordV1], *, as_of_session: date
) -> tuple[EtfRelationshipRecordV1, ...]:
    records = tuple(item for item in history if item.as_of_session == as_of_session)
    if tuple(item.pair_id for item in records) != tuple(item.pair_id for item in ETF_PAIRS):
        raise EtfRelationshipError("current relationship set does not match registered pair order")
    return records


def build_relationship_explanations(
    records: Sequence[EtfRelationshipRecordV1],
) -> tuple[EtfRelationshipExplanationV1, ...]:
    return tuple(_explanation(item) for item in records)


def compare_relationships_with_regime(
    *,
    records: Sequence[EtfRelationshipRecordV1],
    regime_summaries: Sequence[Mapping[str, Any]],
) -> tuple[MarketRegimeRelationshipComparisonV1, ...]:
    pairs = {item.pair_id: item for item in ETF_PAIRS}
    output: list[MarketRegimeRelationshipComparisonV1] = []
    for summary in regime_summaries:
        current = summary.get("current", summary)
        candidate = str(current["instantaneous_candidate_state"])
        confirmed = str(current["confirmed_state"])
        universe_id = str(summary.get("universe_id", current["universe_id"]))
        for record in records:
            alignment, codes = _regime_alignment(
                regime_state=confirmed,
                record=record,
                pair=pairs[record.pair_id],
            )
            output.append(
                MarketRegimeRelationshipComparisonV1(
                    as_of_session=record.as_of_session,
                    universe_id=universe_id,
                    regime_candidate_state=candidate,
                    regime_confirmed_state=confirmed,
                    regime_composite=str(current["composite"]),
                    regime_state_record_fingerprint=str(current["logical_fingerprint"]),
                    pair_id=record.pair_id,
                    relationship_state=record.relationship_state,
                    alignment=alignment,
                    reason_codes=codes,
                )
            )
    return tuple(output)


def relationship_history_fingerprint(records: Sequence[EtfRelationshipRecordV1]) -> str:
    ordered = sorted(records, key=lambda item: (item.as_of_session, item.pair_id))
    return _fingerprint([item.logical_fingerprint for item in ordered])


def _calculate_pair(
    *,
    pair: EtfPairDefinition,
    sessions: tuple[date, ...],
    closes: Mapping[str, Mapping[date, Decimal]],
    end_index: int,
    history_source_fingerprint: str,
    previous: EtfRelationshipRecordV1 | None,
) -> EtfRelationshipRecordV1:
    as_of = sessions[end_index]
    windows = tuple(
        _window_metric(pair, sessions, closes, end_index, window) for window in WINDOWS
    )
    paired_count = sum(
        1
        for session in sessions[: end_index + 1]
        if session in closes.get(pair.left_ticker, {}) and session in closes.get(pair.right_ticker, {})
    )
    current_left = closes.get(pair.left_ticker, {}).get(as_of)
    current_right = closes.get(pair.right_ticker, {}).get(as_of)
    ratio_level = _ln(current_left / current_right) if current_left is not None and current_right is not None else None
    ratio_z, ratio_percentile = _ratio_statistics(pair, sessions, closes, end_index)
    prior_corr = _correlation_at(pair, sessions, closes, end_index - 5, 20) if end_index >= 25 else None
    current_corr = _window(windows, 20).rolling_correlation
    corr_change = (
        _d(current_corr) - prior_corr if current_corr is not None and prior_corr is not None else None
    )
    perturbations = tuple(
        (window, _serialized(_correlation_at(pair, sessions, closes, end_index, window)))
        for window in CORRELATION_PERTURBATION_WINDOWS
    )
    perturbation_consistent = _perturbation_consistency(perturbations)
    availability, missing_reason = _overall_availability(windows)
    state, state_reasons = _relationship_state(
        windows=windows,
        ratio_z=ratio_z,
        prior_ratio_z=_d(previous.ratio_robust_z) if previous and previous.ratio_robust_z is not None else None,
        prior_spread=_d(_window(previous.windows, 5).relative_return) if previous and _window(previous.windows, 5).relative_return is not None else None,
        current_corr=_d(current_corr) if current_corr is not None else None,
        prior_corr=prior_corr,
        corr_change=corr_change,
        availability=availability,
    )
    confidence = _confidence(
        paired_count,
        perturbation_consistent,
        _nonoverlap_direction_consistent(pair, sessions, closes, end_index),
    )
    reasons = tuple(dict.fromkeys((*state_reasons, f"confidence_{confidence.value}")))
    warnings = ["statistical_relationship_not_causal", "price_relationship_not_fund_flow"]
    if ratio_z is None:
        warnings.append("ratio_statistics_unavailable_short_history")
    if confidence in {RelationshipConfidence.INSUFFICIENT, RelationshipConfidence.LOW}:
        warnings.append("short_history_limits_reliability")
    payload = {
        "schema_version": "1.0",
        "contract_version": "etf-relationship-map/1.0",
        "calculation_version": RELATIONSHIP_CALCULATION_VERSION,
        "parameter_set_id": "mrom-etf-relationships-v1-fixed-registry-1",
        "parameter_fingerprint": RELATIONSHIP_PARAMETER_FINGERPRINT,
        "pair_id": pair.pair_id,
        "as_of_session": as_of,
        "left_ticker": pair.left_ticker,
        "right_ticker": pair.right_ticker,
        "relationship_family": pair.relationship_family,
        "windows": windows,
        "ratio_level": _serialized(ratio_level),
        "ratio_robust_z": _serialized(ratio_z),
        "ratio_percentile": _serialized(ratio_percentile),
        "correlation_20_prior_5": _serialized(prior_corr),
        "correlation_change_5": _serialized(corr_change),
        "correlation_perturbations": perturbations,
        "perturbation_state_consistent": perturbation_consistent,
        "relationship_state": state,
        "previous_relationship_state": previous.relationship_state if previous else None,
        "confidence": confidence,
        "availability": availability,
        "missing_reason": missing_reason,
        "paired_close_observation_count": paired_count,
        "source_first_session": sessions[0] if paired_count else None,
        "source_last_session": as_of,
        "source_history_fingerprint": history_source_fingerprint,
        "reason_codes": reasons,
        "warnings": tuple(warnings),
    }
    fingerprint = _fingerprint(_jsonable(payload))
    return EtfRelationshipRecordV1(**payload, logical_fingerprint=fingerprint)


def _window_metric(
    pair: EtfPairDefinition,
    sessions: tuple[date, ...],
    closes: Mapping[str, Mapping[date, Decimal]],
    end_index: int,
    window: int,
) -> EtfRelationshipWindowMetricV1:
    end = sessions[end_index]
    if end_index < window:
        return _missing_window(window, end, "insufficient_session_history")
    selected = sessions[end_index - window : end_index + 1]
    left = closes.get(pair.left_ticker, {})
    right = closes.get(pair.right_ticker, {})
    if any(session not in left for session in selected):
        return _missing_window(window, end, f"missing_ticker_session:{pair.left_ticker}")
    if any(session not in right for session in selected):
        return _missing_window(window, end, f"missing_ticker_session:{pair.right_ticker}")
    left_values = tuple(left[session] for session in selected)
    right_values = tuple(right[session] for session in selected)
    left_return = left_values[-1] / left_values[0] - Decimal(1)
    right_return = right_values[-1] / right_values[0] - Decimal(1)
    correlation = _correlation(_daily_log_returns(left_values), _daily_log_returns(right_values))
    if correlation is None:
        return EtfRelationshipWindowMetricV1(
            window_sessions=window,
            start_session=selected[0], end_session=end,
            left_start_close=_serialized(left_values[0]), left_end_close=_serialized(left_values[-1]),
            right_start_close=_serialized(right_values[0]), right_end_close=_serialized(right_values[-1]),
            left_return=_serialized(left_return), right_return=_serialized(right_return),
            relative_return=_serialized(left_return - right_return),
            daily_return_observation_count=window, rolling_correlation=None,
            direction_combination=_direction(left_return, right_return),
            availability=RelationshipAvailability.PARTIAL,
            missing_reason="correlation_zero_variance",
            reason_codes=("return_metrics_available", "correlation_undefined_zero_variance"),
        )
    return EtfRelationshipWindowMetricV1(
        window_sessions=window,
        start_session=selected[0], end_session=end,
        left_start_close=_serialized(left_values[0]), left_end_close=_serialized(left_values[-1]),
        right_start_close=_serialized(right_values[0]), right_end_close=_serialized(right_values[-1]),
        left_return=_serialized(left_return), right_return=_serialized(right_return),
        relative_return=_serialized(left_return - right_return),
        daily_return_observation_count=window, rolling_correlation=_serialized(correlation),
        direction_combination=_direction(left_return, right_return),
        availability=RelationshipAvailability.AVAILABLE, missing_reason=None,
        reason_codes=("paired_window_complete", "return_and_correlation_available"),
    )


def _missing_window(window: int, end: date, reason: str) -> EtfRelationshipWindowMetricV1:
    return EtfRelationshipWindowMetricV1(
        window_sessions=window, start_session=None, end_session=end,
        left_start_close=None, left_end_close=None, right_start_close=None, right_end_close=None,
        left_return=None, right_return=None, relative_return=None,
        daily_return_observation_count=0, rolling_correlation=None, direction_combination=None,
        availability=RelationshipAvailability.UNAVAILABLE, missing_reason=reason,
        reason_codes=("window_unavailable", reason),
    )


def _relationship_state(
    *, windows: Sequence[EtfRelationshipWindowMetricV1], ratio_z: Decimal | None,
    prior_ratio_z: Decimal | None, prior_spread: Decimal | None,
    current_corr: Decimal | None, prior_corr: Decimal | None,
    corr_change: Decimal | None, availability: RelationshipAvailability,
) -> tuple[RelationshipState, tuple[str, ...]]:
    five = _window(windows, 5)
    if availability is RelationshipAvailability.UNAVAILABLE or five.relative_return is None:
        return RelationshipState.UNAVAILABLE, ("relationship_unavailable",)
    left = _d(five.left_return)
    right = _d(five.right_return)
    spread = _d(five.relative_return)
    if (
        current_corr is not None and prior_corr is not None and corr_change is not None
        and prior_corr >= RELATIONSHIP_BREAK_PRIOR_THRESHOLD
        and current_corr <= RELATIONSHIP_BREAK_CURRENT_THRESHOLD
        and corr_change <= RELATIONSHIP_BREAK_CHANGE_THRESHOLD
    ):
        return RelationshipState.RELATIONSHIP_BREAK_CANDIDATE, ("relationship_break_thresholds_met",)
    if (
        ratio_z is not None and prior_ratio_z is not None
        and abs(ratio_z) >= ROTATION_Z_THRESHOLD and abs(prior_ratio_z) >= ROTATION_Z_THRESHOLD
        and prior_spread is not None
        and _same_nonzero_sign(ratio_z, spread) and _same_nonzero_sign(prior_ratio_z, prior_spread)
    ):
        return RelationshipState.ROTATION_CANDIDATE, ("rotation_two_session_confirmation_met",)
    if left * right < 0 and abs(spread) >= DIVERGENCE_SPREAD_THRESHOLD:
        return RelationshipState.DIVERGENCE, ("opposite_return_signs", "five_session_spread_threshold_met")
    if left > 0 and right > 0 and current_corr is not None and current_corr >= CORRELATION_POSITIVE_THRESHOLD:
        return RelationshipState.SYNCHRONOUS_STRENGTHENING, ("both_five_session_returns_positive", "positive_correlation_threshold_met")
    if left < 0 and right < 0 and current_corr is not None and current_corr >= CORRELATION_POSITIVE_THRESHOLD:
        return RelationshipState.SYNCHRONOUS_WEAKENING, ("both_five_session_returns_negative", "positive_correlation_threshold_met")
    return RelationshipState.NEUTRAL, ("no_higher_priority_relationship_rule_met",)


def _ratio_statistics(pair, sessions, closes, end_index):
    if end_index + 1 < RATIO_STATISTICS_MINIMUM_OBSERVATIONS:
        return None, None
    selected = sessions[end_index - RATIO_STATISTICS_WINDOW + 1 : end_index + 1]
    left, right = closes.get(pair.left_ticker, {}), closes.get(pair.right_ticker, {})
    if any(session not in left or session not in right for session in selected):
        return None, None
    ratios = tuple(_ln(left[item] / right[item]) for item in selected)
    med = _median(ratios)
    mad = _median(tuple(abs(item - med) for item in ratios))
    z = None if mad == 0 else (ratios[-1] - med) / mad
    percentile_sessions = sessions[end_index - RATIO_PERCENTILE_WINDOW + 1 : end_index + 1]
    if len(percentile_sessions) < RATIO_PERCENTILE_WINDOW or any(item not in left or item not in right for item in percentile_sessions):
        return z, None
    levels = tuple(_ln(left[item] / right[item]) for item in percentile_sessions)
    below = sum(item < levels[-1] for item in levels)
    equal = sum(item == levels[-1] for item in levels)
    percentile = (Decimal(below) + Decimal(equal) / Decimal(2)) / Decimal(len(levels))
    return z, percentile


def _correlation_at(pair, sessions, closes, end_index, window):
    if end_index < window or end_index < 0:
        return None
    selected = sessions[end_index - window : end_index + 1]
    left, right = closes.get(pair.left_ticker, {}), closes.get(pair.right_ticker, {})
    if any(item not in left or item not in right for item in selected):
        return None
    return _correlation(
        _daily_log_returns(tuple(left[item] for item in selected)),
        _daily_log_returns(tuple(right[item] for item in selected)),
    )


def _correlation(left: Sequence[Decimal], right: Sequence[Decimal]) -> Decimal | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    with localcontext(INTERNAL_CONTEXT):
        n = Decimal(len(left))
        mean_left = sum(left, Decimal(0)) / n
        mean_right = sum(right, Decimal(0)) / n
        centered_left = tuple(item - mean_left for item in left)
        centered_right = tuple(item - mean_right for item in right)
        numerator = sum((a * b for a, b in zip(centered_left, centered_right, strict=True)), Decimal(0))
        left_ss = sum((item * item for item in centered_left), Decimal(0))
        right_ss = sum((item * item for item in centered_right), Decimal(0))
        if left_ss == 0 or right_ss == 0:
            return None
        return numerator / (left_ss * right_ss).sqrt()


def _daily_log_returns(values: Sequence[Decimal]) -> tuple[Decimal, ...]:
    return tuple(_ln(values[index] / values[index - 1]) for index in range(1, len(values)))


def _ln(value: Decimal) -> Decimal:
    with localcontext(INTERNAL_CONTEXT):
        return value.ln()


def _index_registered_closes(bars: Iterable[MarketRegimeBar], sessions: Sequence[date]):
    registered = {item.ticker for item in ETF_BASKET}
    session_set = set(sessions)
    output: dict[str, dict[date, Decimal]] = defaultdict(dict)
    ids: dict[str, object] = {}
    for bar in sorted(bars, key=lambda item: (item.session_date, item.ticker, str(item.instrument_id))):
        if bar.ticker not in registered or bar.session_date not in session_set:
            continue
        if bar.instrument_type != InstrumentType.ETF.value:
            raise EtfRelationshipError(f"registered ticker is not ETF: {bar.ticker}")
        if not bar.close.is_finite() or bar.close <= 0:
            raise EtfRelationshipError(f"illegal registered ETF close: {bar.ticker}")
        if bar.session_date in output[bar.ticker]:
            raise EtfRelationshipError(f"duplicate ETF ticker/session business key: {bar.ticker}")
        if bar.ticker in ids and ids[bar.ticker] != bar.instrument_id:
            raise EtfRelationshipError(f"ETF ticker maps to multiple instruments: {bar.ticker}")
        ids[bar.ticker] = bar.instrument_id
        output[bar.ticker][bar.session_date] = bar.close
    return output


def _validated_sessions(sessions: Sequence[date], as_of_session: date) -> tuple[date, ...]:
    ordered = tuple(sessions)
    if not ordered or ordered[-1] != as_of_session or ordered != tuple(sorted(ordered)) or len(set(ordered)) != len(ordered):
        raise EtfRelationshipError("session sequence must be unique, chronological, and end at as-of")
    calendar = ExchangeCalendar()
    if any(not calendar.is_session(item) for item in ordered):
        raise EtfRelationshipError("non-XNYS session is rejected")
    if any(calendar.previous_session(ordered[index]) != ordered[index - 1] for index in range(1, len(ordered))):
        raise EtfRelationshipError("XNYS session gap is rejected")
    return ordered


def _overall_availability(windows):
    five = _window(windows, 5)
    if five.left_return is None or five.right_return is None:
        return RelationshipAvailability.UNAVAILABLE, five.missing_reason
    if all(item.availability is RelationshipAvailability.AVAILABLE for item in windows):
        return RelationshipAvailability.AVAILABLE, None
    return RelationshipAvailability.PARTIAL, "one_or_more_long_windows_unavailable"


def _confidence(
    paired_count: int,
    perturbation_consistent: bool,
    nonoverlap_direction_consistent: bool,
) -> RelationshipConfidence:
    if paired_count < 21:
        return RelationshipConfidence.INSUFFICIENT
    if paired_count < 60:
        return RelationshipConfidence.LOW
    if paired_count < 120:
        return RelationshipConfidence.MEDIUM if perturbation_consistent else RelationshipConfidence.LOW
    if not perturbation_consistent:
        return RelationshipConfidence.LOW
    return (
        RelationshipConfidence.HIGH
        if nonoverlap_direction_consistent
        else RelationshipConfidence.MEDIUM
    )


def _nonoverlap_direction_consistent(pair, sessions, closes, end_index):
    if end_index < 40:
        return False
    current = _spread_at(pair, sessions, closes, end_index, 20)
    prior = _spread_at(pair, sessions, closes, end_index - 20, 20)
    return current is not None and prior is not None and _same_nonzero_sign(current, prior)


def _spread_at(pair, sessions, closes, end_index, window):
    if end_index < window:
        return None
    selected = sessions[end_index - window : end_index + 1]
    left, right = closes.get(pair.left_ticker, {}), closes.get(pair.right_ticker, {})
    if any(item not in left or item not in right for item in selected):
        return None
    return (left[selected[-1]] / left[selected[0]] - Decimal(1)) - (
        right[selected[-1]] / right[selected[0]] - Decimal(1)
    )


def _perturbation_consistency(values: Sequence[tuple[int, str | None]]) -> bool:
    bands = tuple(None if value is None else _d(value) >= CORRELATION_POSITIVE_THRESHOLD for _, value in values)
    present = tuple(item for item in bands if item is not None)
    return len(present) == len(values) and len(set(present)) == 1


def _explanation(record: EtfRelationshipRecordV1) -> EtfRelationshipExplanationV1:
    five, ten, twenty = (_window(record.windows, item) for item in WINDOWS)
    def return_text(item, side):
        value = item.left_return if side == "left" else item.right_return
        return f"{side}_{item.window_sessions}_session_return={value or 'unavailable'}"
    spread_signs = tuple(_sign(_d(item.relative_return)) if item.relative_return is not None else "unavailable" for item in record.windows)
    supporting = list(record.reason_codes)
    counter = []
    if len(set(item for item in spread_signs if item != "unavailable")) > 1:
        counter.append("relative_strength_direction_differs_across_windows")
    if record.confidence in {RelationshipConfidence.INSUFFICIENT, RelationshipConfidence.LOW}:
        counter.append("short_history_limits_reliability")
    if not record.perturbation_state_consistent:
        counter.append("correlation_threshold_not_stable_across_18_20_22_windows")
    return EtfRelationshipExplanationV1(
        parameter_fingerprint=RELATIONSHIP_PARAMETER_FINGERPRINT,
        pair_id=record.pair_id,
        as_of_session=record.as_of_session,
        relationship_state=record.relationship_state,
        left_observation=";".join(return_text(item, "left") for item in (five, ten, twenty)),
        right_observation=";".join(return_text(item, "right") for item in (five, ten, twenty)),
        relative_strength_observation=";".join(
            f"spread_{item.window_sessions}={item.relative_return or 'unavailable'}" for item in (five, ten, twenty)
        ),
        correlation_observation=";".join(
            f"corr_{item.window_sessions}={item.rolling_correlation or 'unavailable'}" for item in (five, ten, twenty)
        ),
        cross_window_observation="spread_direction_5_10_20=" + ",".join(spread_signs),
        supporting_evidence=tuple(supporting), counterevidence=tuple(counter),
        reason_codes=record.reason_codes,
        source_input_references=(record.source_history_fingerprint, record.source_first_session.isoformat() if record.source_first_session else "unavailable", record.source_last_session.isoformat()),
        disclaimers=DISCLAIMER_SET,
    )


def _regime_alignment(*, regime_state: str, record: EtfRelationshipRecordV1, pair: EtfPairDefinition):
    if record.availability is RelationshipAvailability.UNAVAILABLE:
        return RegimeRelationshipAlignment.NEUTRAL, ("pair_unavailable_no_regime_inference",)
    if record.relationship_state is RelationshipState.RELATIONSHIP_BREAK_CANDIDATE:
        return RegimeRelationshipAlignment.CONFLICT, ("relationship_instability_conflicts_with_regime_narrative",)
    if pair.regime_orientation == "contextual":
        return RegimeRelationshipAlignment.NEUTRAL, ("pair_has_contextual_not_directional_regime_orientation",)
    spread = _d(_window(record.windows, 5).relative_return)
    if record.relationship_state in {RelationshipState.DIVERGENCE, RelationshipState.ROTATION_CANDIDATE}:
        risk_tilt = "risk_on" if (spread > 0) == (pair.regime_orientation == "risk_on_if_left_leads") else "defensive"
        if regime_state == "balanced":
            return RegimeRelationshipAlignment.CONFLICT, (f"directional_{risk_tilt}_tilt_conflicts_with_balanced_regime", "contemporaneous_only")
        return (RegimeRelationshipAlignment.CONSISTENT if regime_state == risk_tilt else RegimeRelationshipAlignment.CONFLICT, (f"directional_{risk_tilt}_tilt_compared_with_{regime_state}", "contemporaneous_only"))
    if record.relationship_state is RelationshipState.NEUTRAL and regime_state == "balanced":
        return RegimeRelationshipAlignment.CONSISTENT, ("neutral_pair_state_consistent_with_balanced_regime", "contemporaneous_only")
    return RegimeRelationshipAlignment.NEUTRAL, ("pair_state_not_directional_for_regime_comparison", "contemporaneous_only")


def _window(windows, value):
    return next(item for item in windows if item.window_sessions == value)


def _direction(left, right):
    if left > 0 and right > 0: return "both_positive"
    if left < 0 and right < 0: return "both_negative"
    if left > 0 and right < 0: return "left_positive_right_negative"
    if left < 0 and right > 0: return "left_negative_right_positive"
    if left == right: return "equal_returns"
    return "flat_or_mixed"


def _same_nonzero_sign(left, right):
    return left != 0 and right != 0 and (left > 0) == (right > 0)


def _sign(value):
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def _median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / Decimal(2)


def _d(value: str | Decimal | None) -> Decimal:
    if value is None:
        raise EtfRelationshipError("required Decimal value is unavailable")
    return value if isinstance(value, Decimal) else Decimal(value)


def _serialized(value: Decimal | None) -> str | None:
    if value is None:
        return None
    with localcontext(INTERNAL_CONTEXT):
        quantized = value.quantize(NUMERIC_SCALE)
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, "f")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, date): return value.isoformat()
    if isinstance(value, Decimal): return _serialized(value)
    if isinstance(value, Mapping): return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)): return [_jsonable(item) for item in value]
    if hasattr(value, "value"): return value.value
    return value


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
