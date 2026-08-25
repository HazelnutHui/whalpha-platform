"""Pure, deterministic Market Regime V1 Phase 1a calculation service."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    localcontext,
)
from uuid import UUID

from tip_api.contracts.analytics.v1 import (
    AvailabilityStatus,
    ExplanationLedgerEntryV1,
    MarketRegimeCompositeV1,
    MarketRegimeDimensionV1,
    MarketRegimeMetricV1,
)
from tip_api.parameters.market_regime.v1_0_0 import (
    BROAD_BENCHMARK_TICKERS,
    DIMENSION_PARAMETERS,
    MINIMUM_COMPOSITE_WEIGHT,
    MINIMUM_DIMENSION_INTERNAL_WEIGHT,
    PARAMETER_SET_FINGERPRINT,
    REQUIRED_COMPOSITE_DIMENSIONS,
    DimensionParameter,
    MetricParameter,
)
from tip_api.services.eod_history import exact_dollar_volume_proxy
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeUniverseSource,
)


HUNDRED = Decimal("100")
ZERO = Decimal("0")
ANNUALIZATION_SESSIONS = Decimal("252")
MAD_SCALE = Decimal("1.4826")
DOWNSIDE_TAIL = Decimal("-0.04")


class MarketRegimeCalculationError(RuntimeError):
    """Raised when raw calculation input violates a fail-closed boundary."""


@dataclass(frozen=True, slots=True)
class _RawMetric:
    value: Decimal | None
    actual_observations: int
    minimum_observations: int
    coverage_ratio: Decimal | None
    missing_count: int
    missing_reason: str | None
    source_input_references: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PanelIndex:
    by_session: dict[object, dict[UUID, MarketRegimeBar]]
    by_instrument: dict[UUID, dict[object, MarketRegimeBar]]
    benchmark_ids: dict[str, UUID]


def calculate_market_regime(
    *,
    panel: MarketRegimeInputPanel,
    universe_id: str,
) -> tuple[MarketRegimeCompositeV1, tuple[ExplanationLedgerEntryV1, ...]]:
    """Calculate a complete inspectable Phase 1a ledger for one active Universe."""

    with localcontext(_calculation_context()):
        return _calculate_market_regime(panel=panel, universe_id=universe_id)


def _calculate_market_regime(
    *,
    panel: MarketRegimeInputPanel,
    universe_id: str,
) -> tuple[MarketRegimeCompositeV1, tuple[ExplanationLedgerEntryV1, ...]]:

    index = _index_panel(panel)
    universe = panel.select_universe(universe_id)
    dimensions: list[MarketRegimeDimensionV1] = []
    for parameter in DIMENSION_PARAMETERS:
        raw = _dimension_raw_metrics(panel, universe, index, parameter)
        dimensions.append(_build_dimension(panel, universe, parameter, raw))

    available_weight = sum(
        Decimal(item.configured_weight)
        for item in dimensions
        if item.availability is AvailabilityStatus.AVAILABLE
    )
    available_ids = {
        item.dimension_id
        for item in dimensions
        if item.availability is AvailabilityStatus.AVAILABLE
    }
    composite_available = (
        available_weight >= Decimal(MINIMUM_COMPOSITE_WEIGHT)
        and set(REQUIRED_COMPOSITE_DIMENSIONS).issubset(available_ids)
    )
    regime_score = None
    if composite_available:
        regime_score = _q_score(
            sum(Decimal(item.score_contribution) for item in dimensions if item.score_contribution is not None)
        )
    missing_metric_ids = tuple(
        metric.metric_id
        for dimension in dimensions
        for metric in dimension.raw_metrics
        if metric.availability is AvailabilityStatus.UNAVAILABLE
    )
    unavailable_dimensions = tuple(
        item.dimension_id for item in dimensions if item.availability is AvailabilityStatus.UNAVAILABLE
    )
    warnings = ["current_as_of_constituent_replay", "state_and_hysteresis_deferred_phase_1a"]
    if missing_metric_ids:
        warnings.append("metric_missingness_present")
    reasons = ["fixed_parameter_set", "regime_adjustment_fixed_zero", "state_deferred_phase_1a"]
    reasons.append("composite_available" if composite_available else "composite_unavailable")
    provisional = MarketRegimeCompositeV1(
        parameter_set_fingerprint=PARAMETER_SET_FINGERPRINT,
        as_of_session=panel.as_of_session,
        universe_id=universe.universe_id,
        universe_member_count=len(universe.member_ids),
        membership_fingerprint=universe.membership_fingerprint,
        activation_pointer_fingerprint=panel.activation_pointer_fingerprint,
        identity_logical_fingerprint=panel.identity_logical_fingerprint,
        eod_content_fingerprint=panel.eod_content_fingerprint,
        history_source_fingerprint=panel.history_source_fingerprint,
        history_sessions_used=panel.sessions,
        regime_score=regime_score,
        configured_weight_available=_q_weight(available_weight),
        dimensions=tuple(dimensions),
        missing_metric_ids=missing_metric_ids,
        unavailable_dimension_ids=unavailable_dimensions,
        warnings=tuple(warnings),
        reason_codes=tuple(reasons),
        logical_fingerprint="0" * 64,
    )
    payload = provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
    composite = provisional.model_copy(update={"logical_fingerprint": _fingerprint(payload)})
    return composite, _explanation_ledger(composite)


def _index_panel(panel: MarketRegimeInputPanel) -> _PanelIndex:
    if len(panel.sessions) < 21 or panel.sessions[-1] != panel.as_of_session:
        raise MarketRegimeCalculationError("at least 21 ordered sessions ending at as-of are required")
    if tuple(sorted(panel.sessions)) != panel.sessions or len(set(panel.sessions)) != len(panel.sessions):
        raise MarketRegimeCalculationError("session sequence must be unique and ascending")
    allowed_sessions = set(panel.sessions)
    by_session: dict[object, dict[UUID, MarketRegimeBar]] = {item: {} for item in panel.sessions}
    by_instrument: dict[UUID, dict[object, MarketRegimeBar]] = defaultdict(dict)
    for bar in panel.bars:
        if bar.session_date not in allowed_sessions or bar.session_date > panel.as_of_session:
            raise MarketRegimeCalculationError("future or out-of-window market input")
        _validate_bar(bar)
        if bar.instrument_id in by_session[bar.session_date]:
            raise MarketRegimeCalculationError("duplicate instrument/session business key")
        by_session[bar.session_date][bar.instrument_id] = bar
        by_instrument[bar.instrument_id][bar.session_date] = bar
    if any(not by_session[item] for item in panel.sessions):
        raise MarketRegimeCalculationError("session gap in calculation panel")

    current = panel.as_of_session
    candidates: dict[str, list[UUID]] = {ticker: [] for ticker in BROAD_BENCHMARK_TICKERS}
    for bar in by_session[current].values():
        if bar.ticker in candidates and bar.instrument_type == "etf":
            candidates[bar.ticker].append(bar.instrument_id)
    benchmark_ids: dict[str, UUID] = {}
    for ticker in BROAD_BENCHMARK_TICKERS:
        ids = sorted(candidates[ticker], key=str)
        if len(ids) != 1:
            raise MarketRegimeCalculationError(f"required broad ETF {ticker} is not uniquely resolved")
        benchmark_ids[ticker] = ids[0]
    return _PanelIndex(by_session=by_session, by_instrument=dict(by_instrument), benchmark_ids=benchmark_ids)


def _dimension_raw_metrics(
    panel: MarketRegimeInputPanel,
    universe: MarketRegimeUniverseSource,
    index: _PanelIndex,
    parameter: DimensionParameter,
) -> tuple[_RawMetric, ...]:
    calculators = {
        "trend": _trend_metrics,
        "breadth": _breadth_metrics,
        "volatility": _volatility_metrics,
        "liquidity_participation": _participation_metrics,
        "leadership_dispersion": _leadership_metrics,
    }
    return calculators[parameter.dimension_id](panel, universe, index, parameter)


def _trend_metrics(panel, universe, index, parameter) -> tuple[_RawMetric, ...]:
    r20 = _benchmark_returns(panel, index, 20)
    r5 = _benchmark_returns(panel, index, 5)
    sma_flags: list[Decimal] = []
    for instrument_id in index.benchmark_ids.values():
        closes = _closes(panel, index, instrument_id, 20)
        if closes is not None:
            sma_flags.append(Decimal(1) if closes[-1] > _mean(closes) else Decimal(0))
    median5 = _median(tuple(r5.values())) if r5 else None
    agreements: list[Decimal] = []
    if median5 is not None:
        median_sign = _sign(median5)
        agreements = [Decimal(1) if _sign(value) == median_sign else Decimal(0) for value in r5.values()]
    refs20 = _refs(panel, universe, 21)
    refs5 = _refs(panel, universe, 6)
    return (
        _raw_required_count(_median(tuple(r20.values())) if len(r20) == 4 else None, len(r20), 4, refs20),
        _raw_required_count(_median(tuple(r5.values())) if len(r5) == 4 else None, len(r5), 4, refs5),
        _raw_required_count(_mean(tuple(sma_flags)) if len(sma_flags) >= 3 else None, len(sma_flags), 3, refs20),
        _raw_required_count(_mean(tuple(agreements)) if len(agreements) >= 3 else None, len(agreements), 3, refs5),
    )


def _breadth_metrics(panel, universe, index, parameter) -> tuple[_RawMetric, ...]:
    member_count = len(universe.member_ids)
    r1 = _member_returns(panel, universe, index, 1)
    r5 = _member_returns(panel, universe, index, 5)
    sma_values: list[Decimal] = []
    high_low: list[tuple[bool, bool]] = []
    for instrument_id in sorted(universe.member_ids, key=str):
        closes = _closes(panel, index, instrument_id, 20)
        if closes is None:
            continue
        sma_values.append(Decimal(1) if closes[-1] > _mean(closes) else Decimal(0))
        high_low.append((closes[-1] == max(closes), closes[-1] == min(closes)))
    return (
        _raw_coverage(
            _share_positive(tuple(r1.values())), len(r1), member_count, Decimal("0.80"), 500,
            _refs(panel, universe, 2),
        ),
        _raw_coverage(
            _share_positive(tuple(r5.values())), len(r5), member_count, Decimal("0.80"), 0,
            _refs(panel, universe, 6),
        ),
        _raw_coverage(
            _mean(tuple(sma_values)) if sma_values else None, len(sma_values), member_count, Decimal("0.75"), 0,
            _refs(panel, universe, 20),
        ),
        _raw_coverage(
            ((Decimal(sum(high for high, _ in high_low)) - Decimal(sum(low for _, low in high_low))) / Decimal(len(high_low))) if high_low else None,
            len(high_low), member_count, Decimal("0.75"), 0, _refs(panel, universe, 20),
        ),
    )


def _volatility_metrics(panel, universe, index, parameter) -> tuple[_RawMetric, ...]:
    member_count = len(universe.member_ids)
    spy_id = index.benchmark_ids["SPY"]
    spy_returns = _log_returns(panel, index, spy_id, 10)
    spy_value = _annualized_sample_std(spy_returns) if spy_returns is not None else None
    stock_vols: list[Decimal] = []
    for instrument_id in sorted(universe.member_ids, key=str):
        values = _log_returns(panel, index, instrument_id, 10)
        if values is not None:
            stock_vols.append(_annualized_sample_std(values))
    r1 = _member_returns(panel, universe, index, 1)
    dispersion = MAD_SCALE * _mad(tuple(r1.values())) if r1 else None
    tail_values: list[Decimal] = []
    for offset in range(5, 0, -1):
        current_index = len(panel.sessions) - offset
        previous_index = current_index - 1
        if previous_index < 0:
            continue
        current_session = panel.sessions[current_index]
        previous_session = panel.sessions[previous_index]
        for instrument_id in universe.member_ids:
            current = index.by_session[current_session].get(instrument_id)
            previous = index.by_session[previous_session].get(instrument_id)
            if current is not None and previous is not None:
                tail_values.append(_ratio_return(current.close, previous.close))
    possible_tail = member_count * 5
    tail_coverage = Decimal(len(tail_values)) / Decimal(possible_tail) if possible_tail else ZERO
    tail_value = (
        Decimal(sum(value <= DOWNSIDE_TAIL for value in tail_values)) / Decimal(len(tail_values))
        if tail_values else None
    )
    return (
        _raw_required_count(spy_value, len(spy_returns or ()), 10, _refs(panel, universe, 11)),
        _raw_coverage(
            _median(tuple(stock_vols)) if stock_vols else None, len(stock_vols), member_count, Decimal("0.70"), 0,
            _refs(panel, universe, 11),
        ),
        _raw_with_coverage(
            tail_value, len(tail_values), possible_tail, tail_coverage, Decimal("0.70"), 0,
            _refs(panel, universe, 6),
        ),
        _raw_required_count(dispersion, len(r1), 500, _refs(panel, universe, 2)),
    )


def _participation_metrics(panel, universe, index, parameter) -> tuple[_RawMetric, ...]:
    member_count = len(universe.member_ids)
    sessions = panel.sessions
    current = sessions[-1]
    daily_sums: list[Decimal] = []
    valid_reference_sessions = 0
    reference_coverages: list[Decimal] = []
    for session in sessions[-21:-1]:
        bars = [index.by_session[session].get(item) for item in universe.member_ids]
        valid = [item for item in bars if item is not None]
        coverage = Decimal(len(valid)) / Decimal(member_count)
        reference_coverages.append(coverage)
        if coverage >= Decimal("0.80"):
            valid_reference_sessions += 1
            daily_sums.append(sum((exact_dollar_volume_proxy(item.close, item.volume) for item in valid), ZERO))
    current_bars = [index.by_session[current].get(item) for item in universe.member_ids]
    current_valid = [item for item in current_bars if item is not None]
    current_coverage = Decimal(len(current_valid)) / Decimal(member_count)
    current_sum = sum((exact_dollar_volume_proxy(item.close, item.volume) for item in current_valid), ZERO)
    reference_median = _median(tuple(daily_sums)) if daily_sums else None
    aggregate = None
    aggregate_reason = None
    if current_coverage < Decimal("0.80"):
        aggregate_reason = "insufficient_coverage"
    elif valid_reference_sessions < 18:
        aggregate_reason = "insufficient_reference_sessions"
    elif reference_median is None or reference_median <= 0:
        aggregate_reason = "zero_denominator"
    else:
        aggregate = current_sum / reference_median
    aggregate_raw = _RawMetric(
        value=aggregate,
        actual_observations=valid_reference_sessions,
        minimum_observations=18,
        coverage_ratio=current_coverage,
        missing_count=20 - valid_reference_sessions,
        missing_reason=aggregate_reason,
        source_input_references=_refs(panel, universe, 21),
        reason_codes=_reason_codes(aggregate_reason, proxy=True),
    )

    r1 = _member_returns(panel, universe, index, 1)
    comparable = [
        (instrument_id, value, index.by_session[current][instrument_id])
        for instrument_id, value in r1.items()
        if instrument_id in index.by_session[current]
    ]
    comparable_coverage = Decimal(len(comparable)) / Decimal(member_count)
    total_proxy = sum((exact_dollar_volume_proxy(bar.close, bar.volume) for _, _, bar in comparable), ZERO)
    up_proxy = sum(
        (exact_dollar_volume_proxy(bar.close, bar.volume) for _, value, bar in comparable if value > 0), ZERO
    )
    up_value = up_proxy / total_proxy if total_proxy > 0 else None
    up_reason = None
    if comparable_coverage < Decimal("0.80"):
        up_reason = "insufficient_coverage"
        up_value = None
    elif total_proxy <= 0:
        up_reason = "zero_denominator"
    up_raw = _RawMetric(
        value=up_value,
        actual_observations=len(comparable),
        minimum_observations=0,
        coverage_ratio=comparable_coverage,
        missing_count=member_count - len(comparable),
        missing_reason=up_reason,
        source_input_references=_refs(panel, universe, 2),
        reason_codes=_reason_codes(up_reason, proxy=True),
    )

    above: list[bool] = []
    for instrument_id in sorted(universe.member_ids, key=str):
        current_bar = index.by_session[current].get(instrument_id)
        history = [
            index.by_session[session].get(instrument_id)
            for session in sessions[-21:-1]
        ]
        volumes = tuple(item.volume for item in history if item is not None)
        if current_bar is not None and len(volumes) >= 15:
            above.append(current_bar.volume > _median(volumes))
    above_coverage = Decimal(len(above)) / Decimal(member_count)
    above_reason = None if above_coverage >= Decimal("0.70") else "insufficient_coverage"
    above_raw = _RawMetric(
        value=(Decimal(sum(above)) / Decimal(len(above))) if above and above_reason is None else None,
        actual_observations=len(above),
        minimum_observations=15,
        coverage_ratio=above_coverage,
        missing_count=member_count - len(above),
        missing_reason=above_reason,
        source_input_references=_refs(panel, universe, 21),
        reason_codes=_reason_codes(above_reason, proxy=True),
    )
    return aggregate_raw, up_raw, above_raw


def _leadership_metrics(panel, universe, index, parameter) -> tuple[_RawMetric, ...]:
    member_count = len(universe.member_ids)
    r5 = _member_returns(panel, universe, index, 5)
    coverage = Decimal(len(r5)) / Decimal(member_count)
    positive = sorted(
        ((instrument_id, value) for instrument_id, value in r5.items() if value > 0),
        key=lambda item: (-item[1], str(item[0])),
    )
    winner_reason = None
    winner_value = None
    if coverage < Decimal("0.70"):
        winner_reason = "insufficient_coverage"
    elif len(positive) < 200:
        winner_reason = "insufficient_positive_observations"
    else:
        top_count = max(1, (len(positive) + 9) // 10)
        denominator = sum((value for _, value in positive), ZERO)
        if denominator <= 0:
            winner_reason = "zero_denominator"
        else:
            winner_value = sum((value for _, value in positive[:top_count]), ZERO) / denominator
    winner = _RawMetric(
        value=winner_value,
        actual_observations=len(positive),
        minimum_observations=200,
        coverage_ratio=coverage,
        missing_count=member_count - len(r5),
        missing_reason=winner_reason,
        source_input_references=_refs(panel, universe, 6),
        reason_codes=_reason_codes(winner_reason, extra=("winner_top_decile_ceiling_stable_tiebreak",)),
    )
    benchmark = _benchmark_returns(panel, index, 5)
    median = _median(tuple(benchmark.values())) if benchmark else None
    agreements = (
        [Decimal(1) if _sign(value) == _sign(median) else Decimal(0) for value in benchmark.values()]
        if median is not None else []
    )
    agreement = _raw_required_count(
        _mean(tuple(agreements)) if len(agreements) >= 3 else None,
        len(agreements), 3, _refs(panel, universe, 6),
    )
    dispersion = MAD_SCALE * _mad(tuple(r5.values())) if r5 else None
    return winner, agreement, _raw_required_count(dispersion, len(r5), 500, _refs(panel, universe, 6))


def _build_dimension(
    panel: MarketRegimeInputPanel,
    universe: MarketRegimeUniverseSource,
    parameter: DimensionParameter,
    raw_values: tuple[_RawMetric, ...],
) -> MarketRegimeDimensionV1:
    if len(raw_values) != len(parameter.metrics):
        raise MarketRegimeCalculationError("dimension calculator returned wrong metric count")
    available_weight = sum(
        metric.configured_weight
        for metric, raw in zip(parameter.metrics, raw_values, strict=True)
        if raw.value is not None
    )
    dimension_available = available_weight >= MINIMUM_DIMENSION_INTERNAL_WEIGHT
    effective_weights = _effective_internal_weights(parameter, raw_values) if dimension_available else {
        metric.metric_id: Decimal("0.0000") for metric in parameter.metrics
    }
    ledgers: list[MarketRegimeMetricV1] = []
    for metric, raw in zip(parameter.metrics, raw_values, strict=True):
        normalized = _normalize(raw.value, metric) if raw.value is not None else None
        effective = effective_weights[metric.metric_id] if raw.value is not None else Decimal("0.0000")
        contribution = (
            _round4(normalized * effective / HUNDRED)
            if normalized is not None and dimension_available else (Decimal("0.0000") if normalized is not None else None)
        )
        ledgers.append(
            MarketRegimeMetricV1(
                metric_id=metric.metric_id,
                as_of_session=panel.as_of_session,
                lookback_sessions=metric.lookback_sessions,
                raw_value=_q_raw(raw.value) if raw.value is not None else None,
                raw_unit=metric.raw_unit,
                direction=metric.direction,
                normalization_method=metric.normalizer,
                normalization_parameters=_normalization_parameters(metric),
                normalized_value=_q_score(normalized) if normalized is not None else None,
                configured_weight=_q_weight(Decimal(metric.configured_weight)),
                effective_weight=_q_weight(effective),
                weighted_contribution=_q_score(contribution) if contribution is not None else None,
                actual_observations=raw.actual_observations,
                minimum_observations=raw.minimum_observations,
                coverage_ratio=_q_raw(raw.coverage_ratio) if raw.coverage_ratio is not None else None,
                missing_count=raw.missing_count,
                availability=(AvailabilityStatus.AVAILABLE if raw.value is not None else AvailabilityStatus.UNAVAILABLE),
                missing_reason=raw.missing_reason,
                source_input_references=raw.source_input_references,
                reason_codes=raw.reason_codes,
            )
        )
    score = _round4(sum((Decimal(item.weighted_contribution) for item in ledgers if item.weighted_contribution is not None), ZERO)) if dimension_available else None
    score_contribution = _round4(score * Decimal(parameter.configured_weight) / HUNDRED) if score is not None else None
    available_metrics = [item for item in ledgers if item.availability is AvailabilityStatus.AVAILABLE]
    coverages = [Decimal(item.coverage_ratio) for item in ledgers if item.coverage_ratio is not None]
    reasons = ["dimension_available" if dimension_available else "dimension_unavailable_insufficient_internal_weight"]
    if dimension_available and available_weight < 100:
        reasons.append("internal_weight_redistributed")
    warnings = tuple(sorted({code for item in ledgers for code in item.reason_codes if code != "metric_available"}))
    support = "unavailable"
    if score is not None:
        support = "supporting" if score >= 60 else "conflicting" if score <= 40 else "neutral"
    return MarketRegimeDimensionV1(
        universe_id=universe.universe_id,
        dimension_id=parameter.dimension_id,
        as_of_session=panel.as_of_session,
        configured_weight=_q_weight(Decimal(parameter.configured_weight)),
        effective_weight=_q_weight(Decimal(parameter.configured_weight) if dimension_available else ZERO),
        internal_configured_weight_available=_q_weight(Decimal(available_weight)),
        score=_q_score(score) if score is not None else None,
        score_contribution=_q_score(score_contribution) if score_contribution is not None else None,
        minimum_observations=min((item.minimum_observations for item in ledgers), default=0),
        actual_observations=min((item.actual_observations for item in available_metrics), default=0),
        coverage_ratio=_q_raw(min(coverages)) if coverages else None,
        missing_count=max((item.missing_count for item in ledgers), default=0),
        availability=AvailabilityStatus.AVAILABLE if dimension_available else AvailabilityStatus.UNAVAILABLE,
        support_status=support,
        explanation_template_id=parameter.explanation_template_id,
        rendered_explanation=_render_dimension(parameter.dimension_id, score, ledgers),
        raw_metrics=tuple(ledgers),
        warnings=warnings,
        reason_codes=tuple(reasons),
    )


def _effective_internal_weights(parameter, raw_values) -> dict[str, Decimal]:
    total = sum(
        metric.configured_weight
        for metric, raw in zip(parameter.metrics, raw_values, strict=True)
        if raw.value is not None
    )
    available = [metric for metric, raw in zip(parameter.metrics, raw_values, strict=True) if raw.value is not None]
    result: dict[str, Decimal] = {metric.metric_id: Decimal("0.0000") for metric in parameter.metrics}
    running = ZERO
    for metric in available[:-1]:
        value = _round4(Decimal(metric.configured_weight) * HUNDRED / Decimal(total))
        result[metric.metric_id] = value
        running += value
    if available:
        result[available[-1].metric_id] = HUNDRED - running
    return result


def _normalize(value: Decimal, parameter: MetricParameter) -> Decimal:
    low = Decimal(parameter.low) if parameter.low is not None else None
    high = Decimal(parameter.high) if parameter.high is not None else None
    if parameter.normalizer == "triangular":
        center = Decimal(parameter.center)
        assert low is not None and high is not None
        if value <= low or value >= high:
            return ZERO
        if value <= center:
            return _clip100(HUNDRED * (value - low) / (center - low))
        return _clip100(HUNDRED * (high - value) / (high - center))
    assert low is not None and high is not None
    linear = _clip100(HUNDRED * (value - low) / (high - low))
    return HUNDRED - linear if parameter.normalizer == "declining" else linear


def _benchmark_returns(panel, index, lookback) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for ticker in BROAD_BENCHMARK_TICKERS:
        value = _instrument_return(panel, index, index.benchmark_ids[ticker], lookback)
        if value is not None:
            result[ticker] = value
    return result


def _member_returns(panel, universe, index, lookback) -> dict[UUID, Decimal]:
    result: dict[UUID, Decimal] = {}
    for instrument_id in sorted(universe.member_ids, key=str):
        value = _instrument_return(panel, index, instrument_id, lookback)
        if value is not None:
            result[instrument_id] = value
    return result


def _instrument_return(panel, index, instrument_id, lookback) -> Decimal | None:
    if len(panel.sessions) <= lookback:
        return None
    current = index.by_session[panel.sessions[-1]].get(instrument_id)
    previous = index.by_session[panel.sessions[-1 - lookback]].get(instrument_id)
    if current is None or previous is None:
        return None
    return _ratio_return(current.close, previous.close)


def _closes(panel, index, instrument_id, count) -> tuple[Decimal, ...] | None:
    if len(panel.sessions) < count:
        return None
    rows = [index.by_session[session].get(instrument_id) for session in panel.sessions[-count:]]
    if any(item is None for item in rows):
        return None
    return tuple(item.close for item in rows if item is not None)


def _log_returns(panel, index, instrument_id, count) -> tuple[Decimal, ...] | None:
    closes = _closes(panel, index, instrument_id, count + 1)
    if closes is None:
        return None
    with localcontext(_calculation_context()):
        return tuple((closes[index_] / closes[index_ - 1]).ln() for index_ in range(1, len(closes)))


def _annualized_sample_std(values: tuple[Decimal, ...]) -> Decimal:
    if len(values) < 2:
        raise MarketRegimeCalculationError("sample standard deviation needs two observations")
    with localcontext(_calculation_context()):
        mean = sum(values, ZERO) / Decimal(len(values))
        variance = sum(((value - mean) * (value - mean) for value in values), ZERO) / Decimal(len(values) - 1)
        return variance.sqrt() * ANNUALIZATION_SESSIONS.sqrt()


def _raw_required_count(value, actual, minimum, refs) -> _RawMetric:
    reason = None if value is not None and actual >= minimum else "insufficient_observations"
    return _RawMetric(
        value=value if reason is None else None,
        actual_observations=actual,
        minimum_observations=minimum,
        coverage_ratio=None,
        missing_count=max(0, minimum - actual),
        missing_reason=reason,
        source_input_references=refs,
        reason_codes=_reason_codes(reason),
    )


def _raw_coverage(value, actual, total, required_coverage, minimum, refs) -> _RawMetric:
    coverage = Decimal(actual) / Decimal(total) if total else ZERO
    return _raw_with_coverage(value, actual, total, coverage, required_coverage, minimum, refs)


def _raw_with_coverage(value, actual, total, coverage, required_coverage, minimum, refs) -> _RawMetric:
    reason = None
    if coverage < required_coverage:
        reason = "insufficient_coverage"
    elif actual < minimum:
        reason = "insufficient_observations"
    elif value is None:
        reason = "zero_denominator"
    return _RawMetric(
        value=value if reason is None else None,
        actual_observations=actual,
        minimum_observations=minimum,
        coverage_ratio=coverage,
        missing_count=max(0, total - actual),
        missing_reason=reason,
        source_input_references=refs,
        reason_codes=_reason_codes(reason),
    )


def _reason_codes(reason: str | None, *, proxy: bool = False, extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    values = ["metric_available" if reason is None else reason]
    if proxy:
        values.append("participation_proxy_not_fund_flow")
    values.extend(extra)
    return tuple(values)


def _refs(panel, universe, count) -> tuple[str, ...]:
    selected = panel.source_sessions[-count:]
    values = [
        f"eod:{item.session_date.isoformat()}:{item.content_fingerprint}" for item in selected
    ]
    values.append(f"identity:{panel.as_of_session.isoformat()}:{panel.identity_logical_fingerprint}")
    values.append(f"activation:{universe.universe_id}:{universe.membership_fingerprint}")
    return tuple(values)


def _ratio_return(current: Decimal, previous: Decimal) -> Decimal:
    with localcontext(_calculation_context()):
        return current / previous - Decimal(1)


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise MarketRegimeCalculationError("mean requires observations")
    with localcontext(_calculation_context()):
        return sum(values, ZERO) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise MarketRegimeCalculationError("median requires observations")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    with localcontext(_calculation_context()):
        return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _mad(values: tuple[Decimal, ...]) -> Decimal:
    center = _median(values)
    return _median(tuple(abs(value - center) for value in values))


def _share_positive(values: tuple[Decimal, ...]) -> Decimal | None:
    return Decimal(sum(value > 0 for value in values)) / Decimal(len(values)) if values else None


def _sign(value: Decimal) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _normalization_parameters(parameter: MetricParameter) -> tuple[tuple[str, str], ...]:
    values = []
    if parameter.low is not None:
        values.append(("low", parameter.low))
    if parameter.center is not None:
        values.append(("center", parameter.center))
    if parameter.high is not None:
        values.append(("high", parameter.high))
    return tuple(values)


def _render_dimension(dimension_id, score, metrics) -> str:
    if score is None:
        missing = ", ".join(item.metric_id for item in metrics if item.availability is AvailabilityStatus.UNAVAILABLE)
        return f"{dimension_id} is unavailable because required metric weight is missing: {missing}."
    band = "supportive" if score >= 60 else "weak" if score <= 40 else "mixed"
    if dimension_id == "liquidity_participation":
        return f"Liquidity / participation is {band} at {_q_score(score)}; close-times-volume is a participation proxy, not fund flow."
    if dimension_id == "volatility":
        return f"Realized-risk evidence is {band} at {_q_score(score)}; implied volatility is unavailable."
    return f"{dimension_id.replace('_', ' ').title()} evidence is {band} at {_q_score(score)} under fixed V1 thresholds."


def _explanation_ledger(composite) -> tuple[ExplanationLedgerEntryV1, ...]:
    entries: list[ExplanationLedgerEntryV1] = []
    for ordinal, dimension in enumerate(composite.dimensions):
        evidence_type = "proxy" if dimension.dimension_id == "liquidity_participation" else "statistical_inference"
        block = "supporting_evidence" if dimension.support_status == "supporting" else "counterevidence"
        if dimension.availability is AvailabilityStatus.UNAVAILABLE:
            evidence_type = "data_quality"
            block = "data_quality_caveat"
        refs = tuple(dict.fromkeys(ref for metric in dimension.raw_metrics for ref in metric.source_input_references))
        entries.append(
            ExplanationLedgerEntryV1(
                as_of_session=composite.as_of_session,
                universe_id=composite.universe_id,
                subject_id=dimension.dimension_id,
                ordinal=ordinal,
                evidence_type=evidence_type,
                block_kind=block,
                template_id=dimension.explanation_template_id,
                rendered_text=dimension.rendered_explanation,
                metric_ids=tuple(item.metric_id for item in dimension.raw_metrics),
                source_input_references=refs,
                reason_codes=dimension.reason_codes,
            )
        )
    entries.append(
        ExplanationLedgerEntryV1(
            as_of_session=composite.as_of_session,
            universe_id=composite.universe_id,
            subject_id="phase_1a_boundary",
            ordinal=len(entries),
            evidence_type="data_quality",
            block_kind="data_quality_caveat",
            template_id="market_regime_phase_1a_boundary_v1",
            rendered_text=(
                "Phase 1a publishes the fixed composite ledger only. Regime state and hysteresis persistence, "
                "ETF relationships, sector inference, candidates, option outcomes, and fund flow are not calculated."
            ),
            metric_ids=(),
            source_input_references=(f"history:{composite.history_source_fingerprint}",),
            reason_codes=("state_deferred_phase_1a", "current_constituent_replay"),
        )
    )
    return tuple(entries)


def _validate_bar(bar: MarketRegimeBar) -> None:
    values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
    if any(not value.is_finite() for value in values):
        raise MarketRegimeCalculationError("non-finite input")
    if min(bar.open, bar.high, bar.low, bar.close) <= 0 or bar.volume < 0:
        raise MarketRegimeCalculationError("illegal price or volume")
    if bar.high < max(bar.open, bar.low, bar.close) or bar.low > min(bar.open, bar.high, bar.close):
        raise MarketRegimeCalculationError("invalid OHLC")


def _calculation_context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    return context


def _clip100(value: Decimal) -> Decimal:
    return min(HUNDRED, max(ZERO, value))


def _round4(value: Decimal) -> Decimal:
    with localcontext(_calculation_context()):
        return value.quantize(Decimal("0.0001"))


def _q_raw(value: Decimal) -> str:
    with localcontext(_calculation_context()):
        return format(value.quantize(Decimal("0.0000000001")), "f")


def _q_score(value: Decimal) -> str:
    return format(_round4(value), "f")


def _q_weight(value: Decimal) -> str:
    return format(_round4(value), "f")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
