"""Independent raw-panel Oracle for descriptive continuation facts.

This module intentionally does not import the Production continuation service.
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
    CandidateContinuationFactsBatchV1,
    CandidateEntryGeometryBatchV1,
    OpportunityCandidateBatchV1,
)
from tip_api.parameters.market_regime import candidate_continuation_facts_v1_0_0 as p
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel


ZERO = Decimal("0")
ONE = Decimal("1")
RAW_QUANTUM = Decimal(1).scaleb(-p.CONTINUATION_FACTS_RAW_DECIMAL_SCALE)
ORACLE_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class CandidateContinuationFactsOracleComparisonV1:
    record_count: int
    mismatch_count: int
    mismatches: tuple[str, ...]
    input_permutation_match: bool
    production_calculator_imported: bool
    oracle_fingerprint: str


def compare_with_independent_continuation_facts_oracle(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    entry_geometry_batch: CandidateEntryGeometryBatchV1,
    actual: CandidateContinuationFactsBatchV1,
) -> CandidateContinuationFactsOracleComparisonV1:
    """Recompute every published fact from raw bars without Production helpers."""

    with localcontext(ORACLE_CONTEXT):
        expected = _expected_rows(
            panel=panel,
            candidate_batch=candidate_batch,
            entry_geometry_batch=entry_geometry_batch,
        )
        actual_by_id = {row.instrument_id: row for row in actual.records}
        mismatches = []
        if set(actual_by_id) != set(expected):
            mismatches.append("record_stable_id_set_mismatch")
        for instrument_id in sorted(set(actual_by_id) & set(expected), key=str):
            if (
                actual_by_id[instrument_id].metrics.model_dump(mode="json")
                != expected[instrument_id]
            ):
                mismatches.append(f"{instrument_id}:metrics")
        if (
            actual.source_candidate_batch_fingerprint != candidate_batch.logical_fingerprint
            or actual.source_entry_geometry_batch_fingerprint
            != entry_geometry_batch.logical_fingerprint
            or actual.source_history_fingerprint != panel.history_source_fingerprint
        ):
            mismatches.append("source_lineage_mismatch")
        if actual.parameter_fingerprint != p.CONTINUATION_FACTS_PARAMETER_FINGERPRINT:
            mismatches.append("parameter_fingerprint_mismatch")

        permuted = replace(panel, bars=tuple(reversed(panel.bars)))
        permuted_expected = _expected_rows(
            panel=permuted,
            candidate_batch=candidate_batch.model_copy(
                update={"candidates": tuple(reversed(candidate_batch.candidates))}
            ),
            entry_geometry_batch=entry_geometry_batch.model_copy(
                update={"records": tuple(reversed(entry_geometry_batch.records))}
            ),
        )
        canonical = {str(key): expected[key] for key in sorted(expected, key=str)}
        canonical_permuted = {
            str(key): permuted_expected[key]
            for key in sorted(permuted_expected, key=str)
        }
        permutation_match = _fingerprint(canonical) == _fingerprint(canonical_permuted)
        if not permutation_match:
            mismatches.append("input_permutation_changed_oracle_output")
        oracle_fingerprint = _fingerprint(
            {
                "rows": canonical,
                "input_permutation_match": permutation_match,
                "production_calculator_imported": False,
            }
        )
    return CandidateContinuationFactsOracleComparisonV1(
        record_count=len(expected),
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        input_permutation_match=permutation_match,
        production_calculator_imported=False,
        oracle_fingerprint=oracle_fingerprint,
    )


def _expected_rows(*, panel, candidate_batch, entry_geometry_batch) -> dict[UUID, dict[str, Any]]:
    universes = {row.universe_id: row for row in panel.universes}
    universe = universes.get(candidate_batch.universe_id)
    if (
        universe is None
        or candidate_batch.membership_fingerprint != universe.membership_fingerprint
        or candidate_batch.universe_member_count != len(universe.member_ids)
    ):
        raise ValueError("continuation Oracle Universe custody differs")
    required = panel.sessions[-p.CONTINUATION_FACTS_REQUIRED_SESSION_COUNT:]
    required_set = set(required)
    bars_by_id: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    for bar in sorted(panel.bars, key=lambda row: (str(row.instrument_id), row.session_date)):
        if bar.session_date not in required_set:
            continue
        if bar.session_date in bars_by_id[bar.instrument_id]:
            raise ValueError("continuation Oracle rejected duplicate instrument/session input")
        bars_by_id[bar.instrument_id][bar.session_date] = bar
    entries = {row.instrument_id: row for row in entry_geometry_batch.records}
    if len(entries) != len(entry_geometry_batch.records):
        raise ValueError("continuation Oracle rejected duplicate Entry input")
    rows = {}
    for candidate in candidate_batch.candidates:
        if candidate.instrument_id not in entries:
            raise ValueError("continuation Oracle requires exact Entry coverage")
        if candidate.instrument_id not in universe.member_ids:
            raise ValueError("continuation Oracle Candidate is outside its Universe")
        rows[candidate.instrument_id] = _metrics(required, bars_by_id[candidate.instrument_id])
    if set(rows) != set(entries):
        raise ValueError("continuation Oracle source coverage differs")
    return rows


def _metrics(required, bars) -> dict[str, Any]:
    if any(session not in bars for session in required):
        return _unavailable(("missing_contiguous_twenty_session_history",))
    ordered = [bars[session] for session in required]
    if any(
        row.open <= ZERO
        or row.high <= ZERO
        or row.low <= ZERO
        or row.close <= ZERO
        or row.volume < ZERO
        or row.high < max(row.open, row.close, row.low)
        or row.low > min(row.open, row.close, row.high)
        for row in ordered
    ):
        return _unavailable(("invalid_continuation_source_bar",))

    closes = tuple(row.close for row in ordered)
    returns = tuple(
        closes[index] / closes[index - 1] - ONE
        for index in range(len(closes) - p.CONTINUATION_FACTS_RETURN_WINDOW, len(closes))
    )
    logs = tuple((ONE + value).ln() for value in returns)
    path = sum((abs(value) for value in logs), ZERO)
    net_log = sum(logs, ZERO)
    nonzero_count = sum(value != ZERO for value in returns)
    positives = sum(value > ZERO for value in returns)
    negatives = sum(value < ZERO for value in returns)
    net = closes[-1] / closes[-p.CONTINUATION_FACTS_RETURN_WINDOW - 1] - ONE
    sign = ONE if net > ZERO else -ONE if net < ZERO else ZERO
    discreteness = (
        ZERO
        if not nonzero_count
        else sign * Decimal(negatives - positives) / Decimal(nonzero_count)
    )

    above = 0
    for endpoint in range(len(closes) - p.CONTINUATION_FACTS_RETURN_WINDOW, len(closes)):
        window = closes[endpoint - p.CONTINUATION_FACTS_SMA_WINDOW + 1 : endpoint + 1]
        above += closes[endpoint] > sum(window, ZERO) / Decimal(len(window))
    current_sma = _mean(closes[-p.CONTINUATION_FACTS_SMA_WINDOW:])
    earlier_end = len(closes) - p.CONTINUATION_FACTS_SMA_SLOPE_LAG
    earlier_sma = _mean(
        closes[earlier_end - p.CONTINUATION_FACTS_SMA_WINDOW : earlier_end]
    )
    ranges = tuple(
        max(
            ordered[index].high - ordered[index].low,
            abs(ordered[index].high - ordered[index - 1].close),
            abs(ordered[index].low - ordered[index - 1].close),
        )
        for index in range(1, len(ordered))
    )
    atr14 = _mean(ranges[-p.CONTINUATION_FACTS_ATR_LONG_WINDOW:])
    atr5 = _mean(ranges[-p.CONTINUATION_FACTS_ATR_SHORT_WINDOW:])
    prior_volume = _median(
        tuple(
            row.volume
            for row in ordered[
                -(
                    p.CONTINUATION_FACTS_RECENT_VOLUME_WINDOW
                    + p.CONTINUATION_FACTS_PRIOR_VOLUME_WINDOW
                ) : -p.CONTINUATION_FACTS_RECENT_VOLUME_WINDOW
            ]
        )
    )
    if atr14 <= ZERO or prior_volume <= ZERO:
        return _unavailable(("nonpositive_continuation_atr_or_prior_volume",))
    recent = closes[-p.CONTINUATION_FACTS_STRUCTURE_WINDOW:]
    prior = closes[
        -2
        * p.CONTINUATION_FACTS_STRUCTURE_WINDOW : -p.CONTINUATION_FACTS_STRUCTURE_WINDOW
    ]
    recent_volume = _median(
        tuple(row.volume for row in ordered[-p.CONTINUATION_FACTS_RECENT_VOLUME_WINDOW:])
    )
    return {
        "availability": "available",
        "net_return_10": _raw(net),
        "information_discreteness_10": _raw(discreteness),
        "return_path_efficiency_10": _raw(ZERO if path == ZERO else abs(net_log) / path),
        "largest_absolute_return_share_10": _raw(
            ZERO if path == ZERO else max(abs(value) for value in logs) / path
        ),
        "positive_return_share_10": _raw(
            Decimal(positives) / Decimal(p.CONTINUATION_FACTS_RETURN_WINDOW)
        ),
        "above_sma10_share_10": _raw(
            Decimal(above) / Decimal(p.CONTINUATION_FACTS_RETURN_WINDOW)
        ),
        "sma10_slope_5_atr": _raw((current_sma - earlier_sma) / atr14),
        "atr_5_to_14": _raw(atr5 / atr14),
        "close_drawdown_from_high_20_atr": _raw((max(closes) - closes[-1]) / atr14),
        "recent_close_low_vs_prior_5_atr": _raw((min(recent) - min(prior)) / atr14),
        "recent_close_high_vs_prior_5_atr": _raw((max(recent) - max(prior)) / atr14),
        "recent_volume_median_ratio_5_to_prior_15": _raw(recent_volume / prior_volume),
        "missing_reason_codes": [],
    }


def _unavailable(reasons) -> dict[str, Any]:
    names = (
        "net_return_10",
        "information_discreteness_10",
        "return_path_efficiency_10",
        "largest_absolute_return_share_10",
        "positive_return_share_10",
        "above_sma10_share_10",
        "sma10_slope_5_atr",
        "atr_5_to_14",
        "close_drawdown_from_high_20_atr",
        "recent_close_low_vs_prior_5_atr",
        "recent_close_high_vs_prior_5_atr",
        "recent_volume_median_ratio_5_to_prior_15",
    )
    return {
        "availability": "unavailable",
        **{name: None for name in names},
        "missing_reason_codes": list(reasons),
    }


def _mean(values) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _median(values) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _raw(value) -> str:
    return format(value.quantize(RAW_QUANTUM, rounding=ROUND_HALF_EVEN), "f")


def _fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
