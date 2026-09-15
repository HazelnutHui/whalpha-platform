"""Pure, outcome-blind calculator for Quant Research Factor Catalog V1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from statistics import median

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    QUANT_RESEARCH_FACTOR_SOURCE_SESSION_COUNT,
    QuantResearchFactorAvailability,
    QuantResearchFactorValueV1,
    factor_definition_fingerprint,
)


ZERO = Decimal("0")
ONE = Decimal("1")
VALUE_QUANTUM = Decimal("0.0000000001")


class QuantResearchFactorCalculationError(ValueError):
    """Raised when the input panel violates the registered structural contract."""


@dataclass(frozen=True, slots=True)
class QuantResearchFactorBar:
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def calculate_quant_research_factor_values(
    *,
    stock_series: tuple[QuantResearchFactorBar, ...],
    benchmark_series: tuple[QuantResearchFactorBar, ...],
) -> tuple[QuantResearchFactorValueV1, ...]:
    """Calculate all 12 registered values without reading or accepting outcomes."""

    stock_issue = _series_issue(stock_series, label="stock")
    benchmark_issue = _series_issue(benchmark_series, label="benchmark")
    if stock_issue is None and benchmark_issue is None and tuple(
        item.session for item in stock_series
    ) != tuple(item.session for item in benchmark_series):
        raise QuantResearchFactorCalculationError(
            "stock and benchmark sessions are not exactly aligned"
        )

    if stock_issue is not None:
        return tuple(_unavailable(factor_id, stock_issue) for factor_id in QUANT_RESEARCH_FACTOR_ORDER)

    assert len(stock_series) == QUANT_RESEARCH_FACTOR_SOURCE_SESSION_COUNT
    computations: dict[str, Decimal | str] = {}
    if benchmark_issue is None:
        computations["relative_return_spy_20s"] = _log_return(stock_series, 0, 20) - _log_return(
            benchmark_series, 0, 20
        )
        computations["relative_return_acceleration_5_vs_prior15"] = (
            _log_return(stock_series, 15, 20)
            - _log_return(benchmark_series, 15, 20)
            - (
                _log_return(stock_series, 0, 15)
                - _log_return(benchmark_series, 0, 15)
            )
            / Decimal(3)
        )
    else:
        computations["relative_return_spy_20s"] = benchmark_issue
        computations["relative_return_acceleration_5_vs_prior15"] = benchmark_issue

    returns_10 = tuple(
        _ln(stock_series[index].close / stock_series[index - 1].close)
        for index in range(11, 21)
    )
    absolute_return_sum = sum((abs(value) for value in returns_10), ZERO)
    if absolute_return_sum == ZERO:
        computations["signed_path_efficiency_10s"] = "zero_absolute_return_sum"
        computations["largest_absolute_return_share_10s"] = (
            "zero_absolute_return_sum"
        )
    else:
        computations["signed_path_efficiency_10s"] = (
            sum(returns_10, ZERO) / absolute_return_sum
        )
        computations["largest_absolute_return_share_10s"] = (
            max(abs(value) for value in returns_10) / absolute_return_sum
        )
    computations["positive_session_share_10s"] = Decimal(
        sum(value > ZERO for value in returns_10)
    ) / Decimal(10)

    atr14 = _atr(stock_series, first_current_index=6, last_current_index=19)
    atr5 = _atr(stock_series, first_current_index=15, last_current_index=19)
    if atr14 == ZERO:
        for factor_id in (
            "prior_atr_ratio_5_to_14",
            "prior_close_range_10s_atr14",
            "close_vs_prior_high_20s_atr14",
            "absolute_overnight_gap_atr14",
        ):
            computations[factor_id] = "zero_prior_atr14"
    else:
        computations["prior_atr_ratio_5_to_14"] = atr5 / atr14
        prior_ten_closes = tuple(item.close for item in stock_series[10:20])
        computations["prior_close_range_10s_atr14"] = (
            max(prior_ten_closes) - min(prior_ten_closes)
        ) / atr14
        computations["close_vs_prior_high_20s_atr14"] = (
            stock_series[20].close
            - max(item.close for item in stock_series[:20])
        ) / atr14
        computations["absolute_overnight_gap_atr14"] = abs(
            stock_series[20].open - stock_series[19].close
        ) / atr14

    current_dollar_volume = stock_series[20].close * stock_series[20].volume
    prior_dollar_volume_median = median(
        tuple(item.close * item.volume for item in stock_series[:20])
    )
    computations["dollar_volume_surprise_1_to_20"] = (
        "zero_prior_dollar_volume_median"
        if prior_dollar_volume_median == ZERO
        else current_dollar_volume / prior_dollar_volume_median
    )

    current_range = stock_series[20].high - stock_series[20].low
    computations["close_location_value_1s"] = (
        "zero_signal_session_range"
        if current_range == ZERO
        else (stock_series[20].close - stock_series[20].low) / current_range
    )
    computations["rolling_maximum_drawdown_10s"] = _maximum_drawdown(
        tuple(item.close for item in stock_series[10:21])
    )

    if set(computations) != set(QUANT_RESEARCH_FACTOR_ORDER):
        raise QuantResearchFactorCalculationError("factor implementation is incomplete")
    return tuple(
        _unavailable(factor_id, value)
        if isinstance(value, str)
        else _available(factor_id, value)
        for factor_id in QUANT_RESEARCH_FACTOR_ORDER
        for value in (computations[factor_id],)
    )


def _series_issue(
    series: tuple[QuantResearchFactorBar, ...], *, label: str
) -> str | None:
    if len(series) != QUANT_RESEARCH_FACTOR_SOURCE_SESSION_COUNT:
        return f"{label}_source_session_count"
    sessions = tuple(item.session for item in series)
    if sessions != tuple(sorted(set(sessions))):
        return f"{label}_source_session_order"
    for item in series:
        values = (item.open, item.high, item.low, item.close, item.volume)
        if not all(value.is_finite() for value in values):
            return f"{label}_non_finite_bar"
        if min(item.open, item.high, item.low, item.close) <= ZERO:
            return f"{label}_non_positive_price"
        if item.volume < ZERO:
            return f"{label}_negative_volume"
        if item.low > min(item.open, item.close) or item.high < max(item.open, item.close):
            return f"{label}_invalid_ohlc_geometry"
    return None


def _log_return(
    series: tuple[QuantResearchFactorBar, ...], start: int, end: int
) -> Decimal:
    return _ln(series[end].close / series[start].close)


def _ln(value: Decimal) -> Decimal:
    with localcontext(_context()):
        return value.ln()


def _atr(
    series: tuple[QuantResearchFactorBar, ...], *, first_current_index: int, last_current_index: int
) -> Decimal:
    with localcontext(_context()):
        true_ranges = tuple(
            max(
                series[index].high - series[index].low,
                abs(series[index].high - series[index - 1].close),
                abs(series[index].low - series[index - 1].close),
            )
            for index in range(first_current_index, last_current_index + 1)
        )
        return sum(true_ranges, ZERO) / Decimal(len(true_ranges))


def _maximum_drawdown(closes: tuple[Decimal, ...]) -> Decimal:
    peak = closes[0]
    drawdown = ZERO
    for close in closes[1:]:
        drawdown = min(drawdown, close / peak - ONE)
        peak = max(peak, close)
    return drawdown


def _available(factor_id: str, value: Decimal) -> QuantResearchFactorValueV1:
    with localcontext(_context()):
        quantized = value.quantize(VALUE_QUANTUM)
        if quantized == ZERO:
            quantized = abs(quantized)
        rendered = format(quantized, "f")
    return QuantResearchFactorValueV1(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
        availability=QuantResearchFactorAvailability.AVAILABLE,
        value=rendered,
    )


def _unavailable(factor_id: str, reason: str) -> QuantResearchFactorValueV1:
    return QuantResearchFactorValueV1(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
        availability=QuantResearchFactorAvailability.UNAVAILABLE,
        reason_codes=(reason,),
    )


def _context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    return context
