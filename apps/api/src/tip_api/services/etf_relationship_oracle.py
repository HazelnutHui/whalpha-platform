"""Independent raw-panel Oracle for Phase 2 ETF relationships.

This module intentionally does not import the production relationship calculator.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from typing import Any, Mapping, Sequence

from tip_api.contracts.analytics.v1.etf_relationship import (
    EtfRelationshipOracleComparisonV1,
    EtfRelationshipRecordV1,
)
from tip_api.parameters.market_regime.relationship_v1_0_0 import (
    CORRELATION_PERTURBATION_WINDOWS,
    CORRELATION_POSITIVE_THRESHOLD,
    DIVERGENCE_SPREAD_THRESHOLD,
    ETF_BASKET,
    ETF_PAIRS,
    NUMERIC_SCALE,
    RELATIONSHIP_BREAK_CHANGE_THRESHOLD,
    RELATIONSHIP_BREAK_CURRENT_THRESHOLD,
    RELATIONSHIP_BREAK_PRIOR_THRESHOLD,
    RELATIONSHIP_PARAMETER_FINGERPRINT,
    RATIO_PERCENTILE_WINDOW,
    RATIO_STATISTICS_MINIMUM_OBSERVATIONS,
    RATIO_STATISTICS_WINDOW,
    ROTATION_Z_THRESHOLD,
    WINDOWS,
)
from tip_api.services.market_regime_sources import MarketRegimeInputPanel
from tip_api.contracts.market_data.v1 import InstrumentType


ORACLE_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
for _signal in (InvalidOperation, DivisionByZero, Overflow):
    ORACLE_CONTEXT.traps[_signal] = True


def compare_with_independent_relationship_oracle(
    *, panel: MarketRegimeInputPanel, records: Sequence[EtfRelationshipRecordV1],
    append_full_replay_match: bool, input_permutation_match: bool, future_prefix_stable: bool,
) -> EtfRelationshipOracleComparisonV1:
    with localcontext(ORACLE_CONTEXT):
        expected = _oracle_history(panel)
    actual = {(item.as_of_session, item.pair_id): item for item in records}
    mismatches: list[str] = []
    if set(actual) != set(expected):
        mismatches.append(f"record_key_set:actual={len(actual)}:oracle={len(expected)}")
    fields = (
        "left_ticker", "right_ticker", "relationship_family", "ratio_level", "ratio_robust_z",
        "ratio_percentile", "correlation_20_prior_5", "correlation_change_5",
        "correlation_perturbations", "perturbation_state_consistent", "relationship_state",
        "previous_relationship_state", "confidence", "availability", "missing_reason",
        "paired_close_observation_count", "source_first_session", "source_last_session",
        "reason_codes",
    )
    for key in sorted(set(actual) & set(expected)):
        record = actual[key]
        oracle = expected[key]
        for field in fields:
            observed = _plain(getattr(record, field))
            wanted = oracle[field]
            if observed != wanted:
                mismatches.append(f"{key[0]}:{key[1]}:{field}:actual={observed}:oracle={wanted}")
        for index, window in enumerate(record.windows):
            for field, wanted in oracle["windows"][index].items():
                observed = _plain(getattr(window, field))
                if observed != wanted:
                    mismatches.append(
                        f"{key[0]}:{key[1]}:window_{window.window_sessions}:{field}:actual={observed}:oracle={wanted}"
                    )
    oracle_fingerprint = _hash([
        {"session": key[0].isoformat(), "pair_id": key[1], **value}
        for key, value in sorted(expected.items())
    ])
    return EtfRelationshipOracleComparisonV1(
        parameter_fingerprint=RELATIONSHIP_PARAMETER_FINGERPRINT,
        pair_count=len(ETF_PAIRS), history_record_count=len(records),
        mismatch_count=len(mismatches), mismatches=tuple(mismatches),
        append_full_replay_match=append_full_replay_match,
        input_permutation_match=input_permutation_match,
        future_prefix_stable=future_prefix_stable,
        oracle_history_fingerprint=oracle_fingerprint,
    )


def _oracle_history(panel: MarketRegimeInputPanel) -> dict[tuple[date, str], dict[str, Any]]:
    sessions = tuple(panel.sessions)
    registered = {item.ticker for item in ETF_BASKET}
    closes: dict[str, dict[date, Decimal]] = defaultdict(dict)
    identifiers: dict[str, object] = {}
    for bar in sorted(panel.bars, key=lambda row: (row.ticker, row.session_date, str(row.instrument_id))):
        if bar.ticker not in registered or bar.session_date not in set(sessions):
            continue
        if bar.instrument_type != InstrumentType.ETF.value or not bar.close.is_finite() or bar.close <= 0:
            raise RuntimeError(f"Oracle rejected registered ETF input: {bar.ticker}")
        if bar.session_date in closes[bar.ticker] or (bar.ticker in identifiers and identifiers[bar.ticker] != bar.instrument_id):
            raise RuntimeError(f"Oracle rejected ambiguous ticker business key: {bar.ticker}")
        identifiers[bar.ticker] = bar.instrument_id
        closes[bar.ticker][bar.session_date] = bar.close
    output: dict[tuple[date, str], dict[str, Any]] = {}
    previous: dict[str, str] = {}
    previous_z: dict[str, Decimal | None] = {}
    previous_spread: dict[str, Decimal | None] = {}
    for end in range(5, len(sessions)):
        for pair in ETF_PAIRS:
            window_rows = [_oracle_window(pair.left_ticker, pair.right_ticker, sessions, closes, end, window) for window in WINDOWS]
            five = window_rows[0]
            paired = sum(
                session in closes.get(pair.left_ticker, {}) and session in closes.get(pair.right_ticker, {})
                for session in sessions[: end + 1]
            )
            current_corr = _maybe_decimal(window_rows[2]["rolling_correlation"])
            prior_corr = _oracle_corr(pair.left_ticker, pair.right_ticker, sessions, closes, end - 5, 20) if end >= 25 else None
            change = current_corr - prior_corr if current_corr is not None and prior_corr is not None else None
            perturbations = tuple((n, _serialize(_oracle_corr(pair.left_ticker, pair.right_ticker, sessions, closes, end, n))) for n in CORRELATION_PERTURBATION_WINDOWS)
            bands = tuple(None if value is None else Decimal(value) >= CORRELATION_POSITIVE_THRESHOLD for _, value in perturbations)
            stable = all(item is not None for item in bands) and len(set(bands)) == 1
            if five["left_return"] is None:
                availability, missing = "unavailable", five["missing_reason"]
            elif all(item["availability"] == "available" for item in window_rows):
                availability, missing = "available", None
            else:
                availability, missing = "partial", "one_or_more_long_windows_unavailable"
            ratio_z, ratio_percentile = _oracle_ratio(pair.left_ticker,pair.right_ticker,sessions,closes,end)
            state, reasons = _oracle_state(
                five,current_corr,prior_corr,change,availability,ratio_z,
                previous_z.get(pair.pair_id),previous_spread.get(pair.pair_id),
            )
            block_stable=_oracle_nonoverlap(pair.left_ticker,pair.right_ticker,sessions,closes,end)
            confidence = "insufficient" if paired < 21 else "low" if paired < 60 else "medium" if paired < 120 and stable else "low" if paired < 120 else "low" if not stable else "high" if block_stable else "medium"
            reasons = tuple(dict.fromkeys((*reasons, f"confidence_{confidence}")))
            current_left = closes.get(pair.left_ticker, {}).get(sessions[end])
            current_right = closes.get(pair.right_ticker, {}).get(sessions[end])
            output[(sessions[end], pair.pair_id)] = {
                "left_ticker": pair.left_ticker, "right_ticker": pair.right_ticker,
                "relationship_family": pair.relationship_family, "windows": window_rows,
                "ratio_level": _serialize(_log(current_left / current_right)) if current_left is not None and current_right is not None else None,
                "ratio_robust_z": _serialize(ratio_z), "ratio_percentile": _serialize(ratio_percentile),
                "correlation_20_prior_5": _serialize(prior_corr), "correlation_change_5": _serialize(change),
                "correlation_perturbations": [list(item) for item in perturbations],
                "perturbation_state_consistent": stable, "relationship_state": state,
                "previous_relationship_state": previous.get(pair.pair_id), "confidence": confidence,
                "availability": availability, "missing_reason": missing,
                "paired_close_observation_count": paired,
                "source_first_session": sessions[0].isoformat() if paired else None,
                "source_last_session": sessions[end].isoformat(), "reason_codes": list(reasons),
            }
            previous[pair.pair_id] = state
            previous_z[pair.pair_id] = ratio_z
            previous_spread[pair.pair_id] = _maybe_decimal(five["relative_return"])
    return output


def _oracle_window(left_ticker, right_ticker, sessions, closes, end, window):
    if end < window:
        return _missing(window, sessions[end], "insufficient_session_history")
    selected = sessions[end - window : end + 1]
    left, right = closes.get(left_ticker, {}), closes.get(right_ticker, {})
    if any(item not in left for item in selected):
        return _missing(window, sessions[end], f"missing_ticker_session:{left_ticker}")
    if any(item not in right for item in selected):
        return _missing(window, sessions[end], f"missing_ticker_session:{right_ticker}")
    lvals, rvals = tuple(left[item] for item in selected), tuple(right[item] for item in selected)
    lr, rr = lvals[-1] / lvals[0] - 1, rvals[-1] / rvals[0] - 1
    corr = _pearson(tuple(_log(lvals[i] / lvals[i - 1]) for i in range(1, len(lvals))), tuple(_log(rvals[i] / rvals[i - 1]) for i in range(1, len(rvals))))
    direction = "both_positive" if lr > 0 and rr > 0 else "both_negative" if lr < 0 and rr < 0 else "left_positive_right_negative" if lr > 0 and rr < 0 else "left_negative_right_positive" if lr < 0 and rr > 0 else "equal_returns" if lr == rr else "flat_or_mixed"
    partial = corr is None
    return {
        "window_sessions": window, "start_session": selected[0].isoformat(), "end_session": sessions[end].isoformat(),
        "left_start_close": _serialize(lvals[0]), "left_end_close": _serialize(lvals[-1]),
        "right_start_close": _serialize(rvals[0]), "right_end_close": _serialize(rvals[-1]),
        "left_return": _serialize(lr), "right_return": _serialize(rr), "relative_return": _serialize(lr - rr),
        "daily_return_observation_count": window, "rolling_correlation": _serialize(corr),
        "direction_combination": direction, "availability": "partial" if partial else "available",
        "missing_reason": "correlation_zero_variance" if partial else None,
        "reason_codes": ["return_metrics_available", "correlation_undefined_zero_variance"] if partial else ["paired_window_complete", "return_and_correlation_available"],
    }


def _missing(window, end, reason):
    return {"window_sessions": window, "start_session": None, "end_session": end.isoformat(), "left_start_close": None, "left_end_close": None, "right_start_close": None, "right_end_close": None, "left_return": None, "right_return": None, "relative_return": None, "daily_return_observation_count": 0, "rolling_correlation": None, "direction_combination": None, "availability": "unavailable", "missing_reason": reason, "reason_codes": ["window_unavailable", reason]}


def _oracle_corr(left_ticker, right_ticker, sessions, closes, end, window):
    if end < window or end < 0: return None
    selected = sessions[end-window:end+1]
    left, right = closes.get(left_ticker, {}), closes.get(right_ticker, {})
    if any(item not in left or item not in right for item in selected): return None
    return _pearson(tuple(_log(left[selected[i]] / left[selected[i-1]]) for i in range(1,len(selected))), tuple(_log(right[selected[i]] / right[selected[i-1]]) for i in range(1,len(selected))))


def _pearson(left, right):
    with localcontext(ORACLE_CONTEXT):
        n = Decimal(len(left)); lm = sum(left,Decimal(0))/n; rm = sum(right,Decimal(0))/n
        lc=tuple(item-lm for item in left); rc=tuple(item-rm for item in right)
        lss=sum((item*item for item in lc),Decimal(0)); rss=sum((item*item for item in rc),Decimal(0))
        if lss == 0 or rss == 0: return None
        return sum((a*b for a,b in zip(lc,rc,strict=True)),Decimal(0))/(lss*rss).sqrt()


def _oracle_state(five, current, prior, change, availability,ratio_z=None,prior_z=None,prior_spread=None):
    if availability == "unavailable": return "unavailable", ("relationship_unavailable",)
    left, right, spread = Decimal(five["left_return"]), Decimal(five["right_return"]), Decimal(five["relative_return"])
    if current is not None and prior is not None and change is not None and prior >= RELATIONSHIP_BREAK_PRIOR_THRESHOLD and current <= RELATIONSHIP_BREAK_CURRENT_THRESHOLD and change <= RELATIONSHIP_BREAK_CHANGE_THRESHOLD:
        return "relationship_break_candidate", ("relationship_break_thresholds_met",)
    if ratio_z is not None and prior_z is not None and prior_spread is not None and abs(ratio_z)>=ROTATION_Z_THRESHOLD and abs(prior_z)>=ROTATION_Z_THRESHOLD and _same_sign(ratio_z,spread) and _same_sign(prior_z,prior_spread):
        return "rotation_candidate", ("rotation_two_session_confirmation_met",)
    if left * right < 0 and abs(spread) >= DIVERGENCE_SPREAD_THRESHOLD:
        return "divergence", ("opposite_return_signs", "five_session_spread_threshold_met")
    if left > 0 and right > 0 and current is not None and current >= CORRELATION_POSITIVE_THRESHOLD:
        return "synchronous_strengthening", ("both_five_session_returns_positive", "positive_correlation_threshold_met")
    if left < 0 and right < 0 and current is not None and current >= CORRELATION_POSITIVE_THRESHOLD:
        return "synchronous_weakening", ("both_five_session_returns_negative", "positive_correlation_threshold_met")
    return "neutral", ("no_higher_priority_relationship_rule_met",)


def _oracle_ratio(left_ticker,right_ticker,sessions,closes,end):
    if end+1<RATIO_STATISTICS_MINIMUM_OBSERVATIONS: return None,None
    left,right=closes.get(left_ticker,{}),closes.get(right_ticker,{})
    selected=sessions[end-RATIO_STATISTICS_WINDOW+1:end+1]
    if any(item not in left or item not in right for item in selected): return None,None
    levels=tuple(_log(left[item]/right[item]) for item in selected)
    median=_median(levels); deviations=tuple(abs(item-median) for item in levels); mad=_median(deviations)
    z=None if mad==0 else (levels[-1]-median)/mad
    percentile_sessions=sessions[end-RATIO_PERCENTILE_WINDOW+1:end+1]
    if len(percentile_sessions)<RATIO_PERCENTILE_WINDOW or any(item not in left or item not in right for item in percentile_sessions): return z,None
    population=tuple(_log(left[item]/right[item]) for item in percentile_sessions)
    below=sum(item<population[-1] for item in population); equal=sum(item==population[-1] for item in population)
    return z,(Decimal(below)+Decimal(equal)/2)/Decimal(len(population))


def _oracle_nonoverlap(left_ticker,right_ticker,sessions,closes,end):
    if end<40: return False
    current=_oracle_spread(left_ticker,right_ticker,sessions,closes,end,20)
    prior=_oracle_spread(left_ticker,right_ticker,sessions,closes,end-20,20)
    return current is not None and prior is not None and _same_sign(current,prior)


def _oracle_spread(left_ticker,right_ticker,sessions,closes,end,window):
    selected=sessions[end-window:end+1]; left,right=closes.get(left_ticker,{}),closes.get(right_ticker,{})
    if len(selected)!=window+1 or any(item not in left or item not in right for item in selected): return None
    return (left[selected[-1]]/left[selected[0]]-1)-(right[selected[-1]]/right[selected[0]]-1)


def _median(values):
    ordered=sorted(values); middle=len(ordered)//2
    return ordered[middle] if len(ordered)%2 else (ordered[middle-1]+ordered[middle])/2


def _same_sign(left,right): return left!=0 and right!=0 and (left>0)==(right>0)


def _log(value):
    with localcontext(ORACLE_CONTEXT): return value.ln()


def _serialize(value):
    if value is None: return None
    with localcontext(ORACLE_CONTEXT): value=value.quantize(NUMERIC_SCALE)
    if value == 0: value=abs(value)
    return format(value,"f")


def _maybe_decimal(value): return None if value is None else Decimal(value)


def _plain(value):
    if isinstance(value, date): return value.isoformat()
    if isinstance(value, tuple): return [_plain(item) for item in value]
    if isinstance(value, list): return [_plain(item) for item in value]
    if hasattr(value,"value"): return value.value
    return value


def _hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
