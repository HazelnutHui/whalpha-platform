"""Pure, outcome-blind calculator for Quant Research Factor Catalog V2."""

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

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QUANT_RESEARCH_FACTOR_V2_SOURCE_SESSION_COUNT,
    QuantResearchFactorAvailabilityV2,
    QuantResearchFactorValueV2,
    factor_definition_v2_fingerprint,
)


ZERO = Decimal("0")
ONE_MILLION = Decimal("1000000")
VALUE_QUANTUM = Decimal("0.0000000001")


class QuantResearchFactorCalculationV2Error(ValueError):
    """Raised when a V2 input panel violates the structural contract."""


@dataclass(frozen=True, slots=True)
class QuantResearchFactorBarV2:
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def calculate_quant_research_factor_values_v2(
    *,
    stock_series: tuple[QuantResearchFactorBarV2, ...],
    benchmark_series: tuple[QuantResearchFactorBarV2, ...],
) -> tuple[QuantResearchFactorValueV2, ...]:
    """Calculate all registered V2 values without accepting an outcome field."""

    with localcontext(_context()):
        return _calculate_quant_research_factor_values_v2(
            stock_series=stock_series,
            benchmark_series=benchmark_series,
        )


def _calculate_quant_research_factor_values_v2(
    *,
    stock_series: tuple[QuantResearchFactorBarV2, ...],
    benchmark_series: tuple[QuantResearchFactorBarV2, ...],
) -> tuple[QuantResearchFactorValueV2, ...]:

    stock_issue = _series_issue(stock_series, label="stock")
    benchmark_issue = _series_issue(benchmark_series, label="benchmark")
    if stock_issue is None and benchmark_issue is None and tuple(
        item.session for item in stock_series
    ) != tuple(item.session for item in benchmark_series):
        raise QuantResearchFactorCalculationV2Error(
            "stock and benchmark sessions are not exactly aligned"
        )
    if stock_issue is not None:
        return tuple(
            _unavailable(factor_id, stock_issue)
            for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        )

    assert len(stock_series) == QUANT_RESEARCH_FACTOR_V2_SOURCE_SESSION_COUNT
    computations: dict[str, Decimal | str] = {}
    if benchmark_issue is None:
        computations["medium_term_relative_momentum_126s_skip5"] = (
            _log_return(stock_series, 0, 121)
            - _log_return(benchmark_series, 0, 121)
        )
        computations["short_term_relative_reversal_5s"] = -(
            _log_return(stock_series, 121, 126)
            - _log_return(benchmark_series, 121, 126)
        )
        computations["intraday_relative_pressure_reversal_5s"] = -sum(
            (
                _ln(stock_series[index].close / stock_series[index].open)
                - _ln(
                    benchmark_series[index].close
                    / benchmark_series[index].open
                )
                for index in range(122, 127)
            ),
            ZERO,
        )
        computations["overnight_relative_persistence_5s"] = sum(
            (
                _ln(stock_series[index].open / stock_series[index - 1].close)
                - _ln(
                    benchmark_series[index].open
                    / benchmark_series[index - 1].close
                )
                for index in range(122, 127)
            ),
            ZERO,
        )
        stock_returns = _daily_log_returns(stock_series, start_current=67)
        benchmark_returns = _daily_log_returns(
            benchmark_series, start_current=67
        )
        down_relative = tuple(
            stock - benchmark
            for stock, benchmark in zip(stock_returns, benchmark_returns)
            if benchmark < ZERO
        )
        computations["down_market_relative_resilience_60s"] = (
            sum(down_relative, ZERO) / Decimal(len(down_relative))
            if len(down_relative) >= 12
            else "fewer_than_twelve_negative_benchmark_sessions"
        )
        computations["single_index_residual_volatility_60s"] = (
            _single_index_residual_volatility(
                stock_returns=stock_returns,
                benchmark_returns=benchmark_returns,
            )
        )
        computations["relative_downside_semideviation_60s"] = (
            _relative_downside_semideviation(
                stock_returns=stock_returns,
                benchmark_returns=benchmark_returns,
            )
        )
    else:
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
            if factor_id != "amihud_illiquidity_20s":
                computations[factor_id] = benchmark_issue

    amihud_terms = []
    for index in range(107, 127):
        dollar_volume = stock_series[index].close * stock_series[index].volume
        if dollar_volume == ZERO:
            amihud_terms = []
            computations["amihud_illiquidity_20s"] = "zero_dollar_volume"
            break
        amihud_terms.append(
            abs(_ln(stock_series[index].close / stock_series[index - 1].close))
            / dollar_volume
        )
    if amihud_terms:
        computations["amihud_illiquidity_20s"] = (
            ONE_MILLION * sum(amihud_terms, ZERO) / Decimal(20)
        )

    if set(computations) != set(QUANT_RESEARCH_FACTOR_V2_ORDER):
        raise QuantResearchFactorCalculationV2Error(
            "Factor Catalog V2 implementation is incomplete"
        )
    return tuple(
        _unavailable(factor_id, value)
        if isinstance(value, str)
        else _available(factor_id, value)
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        for value in (computations[factor_id],)
    )


def _series_issue(
    series: tuple[QuantResearchFactorBarV2, ...], *, label: str
) -> str | None:
    if len(series) != QUANT_RESEARCH_FACTOR_V2_SOURCE_SESSION_COUNT:
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
    series: tuple[QuantResearchFactorBarV2, ...], start: int, end: int
) -> Decimal:
    return _ln(series[end].close / series[start].close)


def _daily_log_returns(
    series: tuple[QuantResearchFactorBarV2, ...], *, start_current: int
) -> tuple[Decimal, ...]:
    return tuple(
        _ln(series[index].close / series[index - 1].close)
        for index in range(start_current, len(series))
    )


def _single_index_residual_volatility(
    *, stock_returns: tuple[Decimal, ...], benchmark_returns: tuple[Decimal, ...]
) -> Decimal | str:
    count = len(stock_returns)
    if count != 60 or len(benchmark_returns) != count:
        raise QuantResearchFactorCalculationV2Error(
            "residual-volatility return window differs"
        )
    stock_mean = sum(stock_returns, ZERO) / Decimal(count)
    benchmark_mean = sum(benchmark_returns, ZERO) / Decimal(count)
    benchmark_variance_sum = sum(
        ((value - benchmark_mean) ** 2 for value in benchmark_returns), ZERO
    )
    if benchmark_variance_sum == ZERO:
        return "zero_benchmark_return_variance"
    covariance_sum = sum(
        (
            (stock - stock_mean) * (benchmark - benchmark_mean)
            for stock, benchmark in zip(stock_returns, benchmark_returns)
        ),
        ZERO,
    )
    beta = covariance_sum / benchmark_variance_sum
    alpha = stock_mean - beta * benchmark_mean
    residual_sum_squares = sum(
        (
            (stock - alpha - beta * benchmark) ** 2
            for stock, benchmark in zip(stock_returns, benchmark_returns)
        ),
        ZERO,
    )
    return Decimal(252).sqrt() * (
        residual_sum_squares / Decimal(count - 2)
    ).sqrt()


def _relative_downside_semideviation(
    *, stock_returns: tuple[Decimal, ...], benchmark_returns: tuple[Decimal, ...]
) -> Decimal:
    downside_squares = tuple(
        min(stock - benchmark, ZERO) ** 2
        for stock, benchmark in zip(stock_returns, benchmark_returns)
    )
    return Decimal(252).sqrt() * (
        sum(downside_squares, ZERO) / Decimal(len(downside_squares))
    ).sqrt()


def _ln(value: Decimal) -> Decimal:
    with localcontext(_context()):
        return value.ln()


def _available(factor_id: str, value: Decimal) -> QuantResearchFactorValueV2:
    with localcontext(_context()):
        quantized = value.quantize(VALUE_QUANTUM)
        if quantized == ZERO:
            quantized = abs(quantized)
        rendered = format(quantized, "f")
    return QuantResearchFactorValueV2(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_v2_fingerprint(factor_id),
        availability=QuantResearchFactorAvailabilityV2.AVAILABLE,
        value=rendered,
    )


def _unavailable(factor_id: str, reason: str) -> QuantResearchFactorValueV2:
    return QuantResearchFactorValueV2(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_v2_fingerprint(factor_id),
        availability=QuantResearchFactorAvailabilityV2.UNAVAILABLE,
        reason_codes=(reason,),
    )


def _context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    return context
