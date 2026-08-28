"""Pure, descriptive continuation facts with no score or status decision."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    CandidateContinuationFactsBatchV1,
    CandidateContinuationFactsV1,
    CandidateContinuationMetricsV1,
    CandidateEntryGeometryBatchV1,
    ContinuationFactAvailability,
    OpportunityCandidateBatchV1,
    continuation_facts_fingerprint,
)
from tip_api.parameters.market_regime.candidate_continuation_facts_v1_0_0 import (
    CONTINUATION_FACTS_ATR_LONG_WINDOW,
    CONTINUATION_FACTS_ATR_SHORT_WINDOW,
    CONTINUATION_FACTS_CALCULATION_VERSION,
    CONTINUATION_FACTS_CONTRACT_VERSION,
    CONTINUATION_FACTS_PANEL_SESSION_COUNT,
    CONTINUATION_FACTS_PARAMETER_FINGERPRINT,
    CONTINUATION_FACTS_PARAMETER_SET_ID,
    CONTINUATION_FACTS_PRIOR_VOLUME_WINDOW,
    CONTINUATION_FACTS_RAW_DECIMAL_SCALE,
    CONTINUATION_FACTS_RECENT_VOLUME_WINDOW,
    CONTINUATION_FACTS_REQUIRED_SESSION_COUNT,
    CONTINUATION_FACTS_RETURN_WINDOW,
    CONTINUATION_FACTS_SMA_SLOPE_LAG,
    CONTINUATION_FACTS_SMA_WINDOW,
    CONTINUATION_FACTS_STRUCTURE_WINDOW,
)
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel


ZERO = Decimal("0")
ONE = Decimal("1")
RAW_QUANTUM = Decimal(1).scaleb(-CONTINUATION_FACTS_RAW_DECIMAL_SCALE)


class CandidateContinuationFactsCalculationError(RuntimeError):
    """Raised when descriptive continuation facts cannot preserve source custody."""


def calculate_candidate_continuation_facts(
    *,
    panel: MarketRegimeInputPanel,
    candidate_batch: OpportunityCandidateBatchV1,
    entry_geometry_batch: CandidateEntryGeometryBatchV1,
) -> CandidateContinuationFactsBatchV1:
    """Calculate source-bound facts without changing any strategy result."""

    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        return _calculate(
            panel=panel,
            candidate_batch=candidate_batch,
            entry_geometry_batch=entry_geometry_batch,
        )


def _calculate(*, panel, candidate_batch, entry_geometry_batch):
    if (
        len(panel.sessions) != CONTINUATION_FACTS_PANEL_SESSION_COUNT
        or panel.sessions[-1] != panel.as_of_session
    ):
        raise CandidateContinuationFactsCalculationError(
            "continuation facts require the exact completed panel"
        )
    if (
        candidate_batch.as_of_session != panel.as_of_session
        or entry_geometry_batch.as_of_session != panel.as_of_session
        or candidate_batch.universe_id != entry_geometry_batch.universe_id
    ):
        raise CandidateContinuationFactsCalculationError(
            "continuation fact source identities differ"
        )
    if (
        candidate_batch.history_source_fingerprint != panel.history_source_fingerprint
        or entry_geometry_batch.source_candidate_batch_fingerprint
        != candidate_batch.logical_fingerprint
        or entry_geometry_batch.source_history_fingerprint
        != panel.history_source_fingerprint
    ):
        raise CandidateContinuationFactsCalculationError(
            "continuation fact source lineage differs"
        )

    universes = {row.universe_id: row for row in panel.universes}
    universe = universes.get(candidate_batch.universe_id)
    if (
        universe is None
        or candidate_batch.membership_fingerprint != universe.membership_fingerprint
        or candidate_batch.universe_member_count != len(universe.member_ids)
    ):
        raise CandidateContinuationFactsCalculationError(
            "continuation fact Universe custody differs"
        )

    candidates = {row.instrument_id: row for row in candidate_batch.candidates}
    entries = {row.instrument_id: row for row in entry_geometry_batch.records}
    if (
        len(candidates) != len(candidate_batch.candidates)
        or len(entries) != len(entry_geometry_batch.records)
        or set(candidates) != set(entries)
        or not set(candidates).issubset(universe.member_ids)
    ):
        raise CandidateContinuationFactsCalculationError(
            "continuation facts require exact Candidate and Entry coverage"
        )

    bars_by_id: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    required_sessions = panel.sessions[-CONTINUATION_FACTS_REQUIRED_SESSION_COUNT:]
    session_set = set(required_sessions)
    for bar in panel.bars:
        if bar.session_date not in session_set:
            continue
        if bar.session_date in bars_by_id[bar.instrument_id]:
            raise CandidateContinuationFactsCalculationError(
                "duplicate continuation instrument/session bar"
            )
        bars_by_id[bar.instrument_id][bar.session_date] = bar

    records = []
    for instrument_id in sorted(candidates, key=str):
        candidate = candidates[instrument_id]
        entry = entries[instrument_id]
        if (
            entry.source_candidate_fingerprint != candidate.logical_fingerprint
            or entry.ticker != candidate.ticker
            or entry.security_type != candidate.security_type
        ):
            raise CandidateContinuationFactsCalculationError(
                "continuation Candidate and Entry records differ"
            )
        metrics = _metrics(
            required_sessions=required_sessions,
            bars=bars_by_id[instrument_id],
        )
        body = {
            "schema_version": "1.0",
            "contract_version": CONTINUATION_FACTS_CONTRACT_VERSION,
            "calculation_version": CONTINUATION_FACTS_CALCULATION_VERSION,
            "parameter_set_id": CONTINUATION_FACTS_PARAMETER_SET_ID,
            "parameter_fingerprint": CONTINUATION_FACTS_PARAMETER_FINGERPRINT,
            "as_of_session": panel.as_of_session.isoformat(),
            "universe_id": candidate_batch.universe_id,
            "instrument_id": str(instrument_id),
            "ticker": candidate.ticker,
            "security_type": candidate.security_type,
            "source_candidate_fingerprint": candidate.logical_fingerprint,
            "source_entry_geometry_fingerprint": entry.logical_fingerprint,
            "metrics": metrics.model_dump(mode="json"),
            "warnings": (
                "descriptive_facts_not_strategy_score_or_status",
                "short_window_adaptation_not_published_factor_replication",
                "price_volume_not_fund_flow",
                "underlying_stock_result_not_option_return",
            ),
        }
        body["logical_fingerprint"] = continuation_facts_fingerprint(body)
        records.append(CandidateContinuationFactsV1.model_validate(body))

    assessed = sum(
        row.metrics.availability is ContinuationFactAvailability.AVAILABLE
        for row in records
    )
    body = {
        "schema_version": "1.0",
        "contract_version": CONTINUATION_FACTS_CONTRACT_VERSION,
        "calculation_version": CONTINUATION_FACTS_CALCULATION_VERSION,
        "parameter_set_id": CONTINUATION_FACTS_PARAMETER_SET_ID,
        "parameter_fingerprint": CONTINUATION_FACTS_PARAMETER_FINGERPRINT,
        "as_of_session": panel.as_of_session.isoformat(),
        "universe_id": candidate_batch.universe_id,
        "source_candidate_batch_fingerprint": candidate_batch.logical_fingerprint,
        "source_entry_geometry_batch_fingerprint": entry_geometry_batch.logical_fingerprint,
        "source_history_fingerprint": panel.history_source_fingerprint,
        "assessed_count": assessed,
        "unavailable_count": len(records) - assessed,
        "availability_counts": dict(
            Counter(row.metrics.availability.value for row in records)
        ),
        "records": [row.model_dump(mode="json") for row in records],
        "strategy_score_input": False,
        "outcome_or_performance_claim": False,
        "warnings": (
            "shadow_only_not_strategy_rank_input",
            "descriptive_facts_not_chronologically_validated_signal",
            "no_threshold_or_outcome_fitting",
            "price_volume_not_fund_flow",
            "underlying_stock_result_not_option_return",
        ),
    }
    body["logical_fingerprint"] = continuation_facts_fingerprint(body)
    return CandidateContinuationFactsBatchV1.model_validate(body)


def _metrics(*, required_sessions, bars) -> CandidateContinuationMetricsV1:
    missing = tuple(session for session in required_sessions if session not in bars)
    if missing:
        return _unavailable(("missing_contiguous_twenty_session_history",))
    ordered = [bars[session] for session in required_sessions]
    if any(
        bar.open <= ZERO
        or bar.high <= ZERO
        or bar.low <= ZERO
        or bar.close <= ZERO
        or bar.volume < ZERO
        or bar.high < max(bar.open, bar.close, bar.low)
        or bar.low > min(bar.open, bar.close, bar.high)
        for bar in ordered
    ):
        return _unavailable(("invalid_continuation_source_bar",))

    closes = tuple(row.close for row in ordered)
    simple_returns = tuple(
        closes[index] / closes[index - 1] - ONE
        for index in range(len(closes) - CONTINUATION_FACTS_RETURN_WINDOW, len(closes))
    )
    log_returns = tuple((ONE + value).ln() for value in simple_returns)
    absolute_path = sum((abs(value) for value in log_returns), ZERO)
    net_log = sum(log_returns, ZERO)
    nonzero = tuple(value for value in simple_returns if value != ZERO)
    positive_count = sum(value > ZERO for value in simple_returns)
    negative_count = sum(value < ZERO for value in simple_returns)
    net_return = closes[-1] / closes[-CONTINUATION_FACTS_RETURN_WINDOW - 1] - ONE
    direction = ONE if net_return > ZERO else -ONE if net_return < ZERO else ZERO
    information_discreteness = (
        ZERO
        if not nonzero
        else direction
        * (Decimal(negative_count) - Decimal(positive_count))
        / Decimal(len(nonzero))
    )

    above_sma = 0
    for endpoint in range(len(closes) - CONTINUATION_FACTS_RETURN_WINDOW, len(closes)):
        start = endpoint - CONTINUATION_FACTS_SMA_WINDOW + 1
        above_sma += closes[endpoint] > _mean(closes[start : endpoint + 1])
    sma_current = _mean(closes[-CONTINUATION_FACTS_SMA_WINDOW:])
    prior_end = len(closes) - CONTINUATION_FACTS_SMA_SLOPE_LAG
    sma_prior = _mean(
        closes[
            prior_end - CONTINUATION_FACTS_SMA_WINDOW : prior_end
        ]
    )

    true_ranges = tuple(
        max(
            ordered[index].high - ordered[index].low,
            abs(ordered[index].high - ordered[index - 1].close),
            abs(ordered[index].low - ordered[index - 1].close),
        )
        for index in range(1, len(ordered))
    )
    atr_long = _mean(true_ranges[-CONTINUATION_FACTS_ATR_LONG_WINDOW:])
    atr_short = _mean(true_ranges[-CONTINUATION_FACTS_ATR_SHORT_WINDOW:])
    prior_volume = _median(
        tuple(
            row.volume
            for row in ordered[
                -(
                    CONTINUATION_FACTS_RECENT_VOLUME_WINDOW
                    + CONTINUATION_FACTS_PRIOR_VOLUME_WINDOW
                ) : -CONTINUATION_FACTS_RECENT_VOLUME_WINDOW
            ]
        )
    )
    if atr_long <= ZERO or prior_volume <= ZERO:
        return _unavailable(("nonpositive_continuation_atr_or_prior_volume",))

    recent = closes[-CONTINUATION_FACTS_STRUCTURE_WINDOW:]
    prior = closes[
        -2 * CONTINUATION_FACTS_STRUCTURE_WINDOW : -CONTINUATION_FACTS_STRUCTURE_WINDOW
    ]
    recent_volume = _median(
        tuple(row.volume for row in ordered[-CONTINUATION_FACTS_RECENT_VOLUME_WINDOW:])
    )
    return CandidateContinuationMetricsV1(
        availability=ContinuationFactAvailability.AVAILABLE,
        net_return_10=_raw(net_return),
        information_discreteness_10=_raw(information_discreteness),
        return_path_efficiency_10=_raw(
            ZERO if absolute_path == ZERO else abs(net_log) / absolute_path
        ),
        largest_absolute_return_share_10=_raw(
            ZERO
            if absolute_path == ZERO
            else max(abs(value) for value in log_returns) / absolute_path
        ),
        positive_return_share_10=_raw(
            Decimal(positive_count) / Decimal(CONTINUATION_FACTS_RETURN_WINDOW)
        ),
        above_sma10_share_10=_raw(
            Decimal(above_sma) / Decimal(CONTINUATION_FACTS_RETURN_WINDOW)
        ),
        sma10_slope_5_atr=_raw((sma_current - sma_prior) / atr_long),
        atr_5_to_14=_raw(atr_short / atr_long),
        close_drawdown_from_high_20_atr=_raw((max(closes) - closes[-1]) / atr_long),
        recent_close_low_vs_prior_5_atr=_raw((min(recent) - min(prior)) / atr_long),
        recent_close_high_vs_prior_5_atr=_raw((max(recent) - max(prior)) / atr_long),
        recent_volume_median_ratio_5_to_prior_15=_raw(recent_volume / prior_volume),
        missing_reason_codes=(),
    )


def _unavailable(codes: tuple[str, ...]) -> CandidateContinuationMetricsV1:
    return CandidateContinuationMetricsV1(
        availability=ContinuationFactAvailability.UNAVAILABLE,
        net_return_10=None,
        information_discreteness_10=None,
        return_path_efficiency_10=None,
        largest_absolute_return_share_10=None,
        positive_return_share_10=None,
        above_sma10_share_10=None,
        sma10_slope_5_atr=None,
        atr_5_to_14=None,
        close_drawdown_from_high_20_atr=None,
        recent_close_low_vs_prior_5_atr=None,
        recent_close_high_vs_prior_5_atr=None,
        recent_volume_median_ratio_5_to_prior_15=None,
        missing_reason_codes=codes,
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _raw(value: Decimal) -> str:
    return format(value.quantize(RAW_QUANTUM, rounding=ROUND_HALF_EVEN), "f")
