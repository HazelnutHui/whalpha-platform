"""Independent raw-panel Oracle for Candidate entry geometry.

The module intentionally does not import the production entry-geometry service.
It repeats the fixed price-location facts and classification rules from raw bars.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateDataQualityStatus,
    CandidateEntryGeometryBatchV1,
    CandidateOpportunityStage,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.parameters.market_regime import candidate_entry_v1_0_0 as p
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel


ZERO = Decimal("0")
ONE = Decimal("1")
RAW_QUANTUM = Decimal(1).scaleb(-p.ENTRY_GEOMETRY_RAW_DECIMAL_SCALE)
ORACLE_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class CandidateEntryGeometryOracleComparisonV1:
    record_count: int
    mismatch_count: int
    mismatches: tuple[str, ...]
    input_permutation_match: bool
    oracle_fingerprint: str


def compare_with_independent_entry_geometry_oracle(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    state_records: tuple[OpportunityCandidateStateRecordV1, ...],
    actual: CandidateEntryGeometryBatchV1,
) -> CandidateEntryGeometryOracleComparisonV1:
    """Recalculate technical facts and classifications without production helpers."""

    with localcontext(ORACLE_CONTEXT):
        expected = _expected_rows(panel=panel, candidate_batch=candidate_batch, state_records=state_records)
        mismatches: list[str] = []
        actual_by_id = {item.instrument_id: item for item in actual.records}
        if set(actual_by_id) != set(expected):
            mismatches.append("record_stable_id_set_mismatch")
        compared_fields = (
            "metrics",
            "volume_climax_risk_candidate",
            "extension_risk",
            "technical_setup",
            "review_posture",
            "first_rejection_code",
        )
        for instrument_id in sorted(set(actual_by_id) & set(expected), key=str):
            row = actual_by_id[instrument_id].model_dump(mode="json")
            wanted = expected[instrument_id]
            for field in compared_fields:
                if row[field] != wanted[field]:
                    mismatches.append(f"{instrument_id}:{field}")
        permuted = replace(panel, bars=tuple(reversed(panel.bars)))
        permuted_expected = _expected_rows(
            panel=permuted,
            candidate_batch=candidate_batch,
            state_records=tuple(reversed(state_records)),
        )
        canonical_expected = {str(key): expected[key] for key in sorted(expected, key=str)}
        canonical_permuted = {
            str(key): permuted_expected[key] for key in sorted(permuted_expected, key=str)
        }
        permutation_match = _fingerprint(canonical_expected) == _fingerprint(canonical_permuted)
        if not permutation_match:
            mismatches.append("input_permutation_changed_oracle_output")
        oracle_fingerprint = _fingerprint(
            {
                "rows": canonical_expected,
                "input_permutation_match": permutation_match,
            }
        )
    return CandidateEntryGeometryOracleComparisonV1(
        record_count=len(expected),
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        input_permutation_match=permutation_match,
        oracle_fingerprint=oracle_fingerprint,
    )


def _expected_rows(*, panel, candidate_batch, state_records) -> dict[UUID, dict[str, Any]]:
    states = {item.instrument_id: item for item in state_records}
    by_id: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    for bar in sorted(panel.bars, key=lambda item: (str(item.instrument_id), item.session_date)):
        if bar.session_date in set(panel.sessions):
            if bar.session_date in by_id[bar.instrument_id]:
                raise ValueError("entry Oracle rejected duplicate instrument/session input")
            by_id[bar.instrument_id][bar.session_date] = bar
    rows = {}
    for candidate in candidate_batch.candidates:
        metrics = _metrics(panel.sessions, by_id[candidate.instrument_id], candidate)
        outcome = _classification(candidate, states[candidate.instrument_id], metrics)
        rows[candidate.instrument_id] = {"metrics": metrics, **outcome}
    return rows


def _metrics(sessions, bars, candidate) -> dict[str, Any]:
    required = sessions[-p.ENTRY_GEOMETRY_SMA_LONG_WINDOW :]
    if any(session not in bars for session in required):
        return _unavailable(("missing_contiguous_twenty_session_history",))
    ordered = [bars[session] for session in required]
    if any(bar.close <= ZERO or bar.high < bar.low or bar.volume < ZERO for bar in ordered):
        return _unavailable(("invalid_entry_geometry_bar",))
    current = ordered[-1]
    sma10 = sum((item.close for item in ordered[-p.ENTRY_GEOMETRY_SMA_SHORT_WINDOW :]), ZERO) / Decimal(
        p.ENTRY_GEOMETRY_SMA_SHORT_WINDOW
    )
    sma20 = sum((item.close for item in ordered), ZERO) / Decimal(p.ENTRY_GEOMETRY_SMA_LONG_WINDOW)
    prior_close = ordered[-p.ENTRY_GEOMETRY_ATR_WINDOW - 1].close
    true_ranges = []
    for bar in ordered[-p.ENTRY_GEOMETRY_ATR_WINDOW :]:
        true_ranges.append(max(bar.high - bar.low, abs(bar.high - prior_close), abs(bar.low - prior_close)))
        prior_close = bar.close
    atr = sum(true_ranges, ZERO) / Decimal(p.ENTRY_GEOMETRY_ATR_WINDOW)
    if atr <= ZERO:
        return _unavailable(("nonpositive_atr14",))
    if candidate.annualized_volatility_10 is None or candidate.current_volume_ratio is None:
        return _unavailable(("candidate_volatility_or_volume_fact_unavailable",))
    volatility = Decimal(candidate.annualized_volatility_10)
    if volatility <= ZERO:
        return _unavailable(("nonpositive_realized_volatility",))
    current_range = current.high - current.low
    if current_range <= ZERO:
        return _unavailable(("nonpositive_current_session_range",))
    prior5 = ordered[-p.ENTRY_GEOMETRY_PRIOR_BREAKOUT_WINDOW - 1 : -1]
    high = max(item.close for item in prior5)
    low = min(item.close for item in prior5)
    consecutive = 0
    for index in range(len(ordered) - 1, len(ordered) - 1 - p.ENTRY_GEOMETRY_TRAILING_UP_CAP, -1):
        if ordered[index].close <= ordered[index - 1].close:
            break
        consecutive += 1
    supports = (("sma20", sma20, 0), ("prior_five_session_close_low", low, 1))
    below = [item for item in supports if item[1] <= current.close]
    support = max(below, key=lambda item: (item[1], -item[2])) if below else None
    expected_move = volatility / Decimal(252).sqrt() * Decimal(5).sqrt()
    breakout = (current.close - high) / atr
    return {
        "availability": "available",
        "close": _raw(current.close),
        "sma_10": _raw(sma10),
        "sma_20": _raw(sma20),
        "atr_14": _raw(atr),
        "return_3": _raw(current.close / ordered[-4].close - ONE),
        "return_5": _raw(current.close / ordered[-6].close - ONE),
        "close_to_sma_10_atr": _raw((current.close - sma10) / atr),
        "close_to_sma_20_atr": _raw((current.close - sma20) / atr),
        "move_5_volatility_units": _raw((current.close / ordered[-6].close - ONE) / expected_move),
        "consecutive_up_sessions": consecutive,
        "current_gap_atr": _raw((current.open - ordered[-2].close) / atr),
        "current_range_atr": _raw(current_range / atr),
        "current_close_location": _raw((current.close - current.low) / current_range),
        "current_volume_ratio": _raw(Decimal(candidate.current_volume_ratio)),
        "prior_five_session_close_high": _raw(high),
        "prior_five_session_close_low": _raw(low),
        "breakout_distance_atr": _raw(breakout),
        "pullback_from_prior_high_atr": _raw(breakout),
        "reference_support_kind": None if support is None else support[0],
        "reference_support_value": None if support is None else _raw(support[1]),
        "reference_support_distance_pct": None if support is None else _raw((current.close - support[1]) / current.close),
        "missing_reason_codes": [],
    }


def _unavailable(reasons) -> dict[str, Any]:
    names = (
        "close", "sma_10", "sma_20", "atr_14", "return_3", "return_5",
        "close_to_sma_10_atr", "close_to_sma_20_atr", "move_5_volatility_units",
        "consecutive_up_sessions", "current_gap_atr", "current_range_atr",
        "current_close_location", "current_volume_ratio", "prior_five_session_close_high",
        "prior_five_session_close_low", "breakout_distance_atr", "pullback_from_prior_high_atr",
        "reference_support_kind", "reference_support_value", "reference_support_distance_pct",
    )
    return {"availability": "unavailable", **{name: None for name in names}, "missing_reason_codes": list(reasons)}


def _classification(candidate, state, metrics):
    if metrics["availability"] == "unavailable":
        return {
            "volume_climax_risk_candidate": None,
            "extension_risk": "unavailable",
            "technical_setup": "unavailable",
            "review_posture": "not_assessable",
            "first_rejection_code": "entry_geometry_required_facts_unavailable",
        }
    d = {key: Decimal(metrics[key]) for key in (
        "close", "sma_20", "close_to_sma_10_atr", "close_to_sma_20_atr",
        "move_5_volatility_units", "current_gap_atr", "current_range_atr",
        "current_close_location", "current_volume_ratio", "breakout_distance_atr",
        "pullback_from_prior_high_atr",
    )}
    climax = (
        d["current_volume_ratio"] >= Decimal(p.VOLUME_CLIMAX_RATIO)
        and d["current_range_atr"] >= Decimal(p.VOLUME_CLIMAX_RANGE_ATR)
        and d["current_close_location"] >= Decimal(p.VOLUME_CLIMAX_CLOSE_LOCATION)
    )
    extension = _extension(d, metrics["consecutive_up_sessions"], climax)
    components = {item.component_id: item.score for item in candidate.components}
    base = None if candidate.base_score is None else Decimal(candidate.base_score)
    relative = None if components["stock_relative_strength"] is None else Decimal(components["stock_relative_strength"])
    trend = None if components["trend_quality"] is None else Decimal(components["trend_quality"])
    strong = (
        base is not None and relative is not None and trend is not None
        and base >= Decimal(p.ENTRY_GEOMETRY_STRONG_SCORE)
        and relative >= Decimal(p.ENTRY_GEOMETRY_COMPONENT_FLOOR)
        and trend >= Decimal(p.ENTRY_GEOMETRY_COMPONENT_FLOOR)
    )
    setup, posture, rejection = "no_viable_setup", "monitor_for_trigger", "no_viable_entry_geometry"
    if state.final_stage is CandidateOpportunityStage.INVALIDATED:
        posture, rejection = "deprioritized", "candidate_state_invalidated"
    elif candidate.data_quality_status in {CandidateDataQualityStatus.QUARANTINED, CandidateDataQualityStatus.FAILED}:
        posture, rejection = "deprioritized", "candidate_source_quality_blocked"
    elif base is None or base < Decimal(p.ENTRY_GEOMETRY_SCORE_FLOOR):
        posture, rejection = "deprioritized", "candidate_score_below_research_floor"
    elif extension in {"high", "extreme"}:
        setup = "strong_but_extended" if strong else "no_viable_setup"
        posture = "wait_for_reset"
        rejection = f"extension_risk_{extension}"
    elif strong and base >= Decimal(p.ENTRY_GEOMETRY_BREAKOUT_SCORE) and _breakout(d):
        setup, posture, rejection = "breakout_confirmed", "technical_review_ready", None
    elif strong and _pullback(d):
        setup, posture, rejection = "pullback", "technical_review_ready", None
    elif strong and _breakout_watch(d):
        setup, posture, rejection = "breakout_watch", "monitor_for_trigger", "breakout_not_confirmed"
    return {
        "volume_climax_risk_candidate": climax,
        "extension_risk": extension,
        "technical_setup": setup,
        "review_posture": posture,
        "first_rejection_code": rejection,
    }


def _extension(d, consecutive, climax):
    if (
        d["close_to_sma_20_atr"] >= Decimal(p.EXTREME_SMA20_EXTENSION_ATR)
        or d["move_5_volatility_units"] >= Decimal(p.EXTREME_MOVE_5_VOLATILITY_UNITS)
        or (d["current_gap_atr"] >= Decimal(p.EXTREME_POSITIVE_GAP_ATR) and d["close_to_sma_20_atr"] >= Decimal(p.HIGH_SMA20_EXTENSION_ATR))
    ):
        return "extreme"
    if (
        d["close_to_sma_20_atr"] >= Decimal(p.HIGH_SMA20_EXTENSION_ATR)
        or d["move_5_volatility_units"] >= Decimal(p.HIGH_MOVE_5_VOLATILITY_UNITS)
        or (consecutive >= p.HIGH_TRAILING_UP_SESSIONS and d["close_to_sma_10_atr"] >= Decimal(p.HIGH_SMA10_EXTENSION_ATR))
        or climax
    ):
        return "high"
    if (
        d["close_to_sma_20_atr"] >= Decimal(p.MODERATE_SMA20_EXTENSION_ATR)
        or d["move_5_volatility_units"] >= Decimal(p.MODERATE_MOVE_5_VOLATILITY_UNITS)
        or (consecutive >= p.MODERATE_TRAILING_UP_SESSIONS and d["close_to_sma_10_atr"] >= Decimal(p.MODERATE_SMA10_EXTENSION_ATR))
        or d["current_gap_atr"] >= Decimal(p.MODERATE_POSITIVE_GAP_ATR)
    ):
        return "moderate"
    return "low"


def _breakout(d):
    return (
        ZERO < d["breakout_distance_atr"] <= Decimal(p.BREAKOUT_MAX_DISTANCE_ATR)
        and Decimal(p.BREAKOUT_MIN_VOLUME_RATIO) <= d["current_volume_ratio"] <= Decimal(p.BREAKOUT_MAX_VOLUME_RATIO)
        and d["current_close_location"] >= Decimal(p.BREAKOUT_MIN_CLOSE_LOCATION)
    )


def _breakout_watch(d):
    return (
        -Decimal(p.BREAKOUT_WATCH_MAX_DISTANCE_ATR) <= d["breakout_distance_atr"] <= ZERO
        and d["current_volume_ratio"] <= Decimal(p.BREAKOUT_WATCH_MAX_VOLUME_RATIO)
    )


def _pullback(d):
    depth = -d["pullback_from_prior_high_atr"]
    return (
        d["close"] >= d["sma_20"]
        and abs(d["close_to_sma_10_atr"]) <= Decimal(p.PULLBACK_SMA10_DISTANCE_ATR)
        and Decimal(p.PULLBACK_FROM_HIGH_MIN_ATR) <= depth <= Decimal(p.PULLBACK_FROM_HIGH_MAX_ATR)
        and d["current_volume_ratio"] <= Decimal(p.PULLBACK_MAX_VOLUME_RATIO)
        and d["current_close_location"] >= Decimal(p.PULLBACK_MIN_CLOSE_LOCATION)
    )


def _raw(value):
    return format(value.quantize(RAW_QUANTUM), "f")


def _fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
