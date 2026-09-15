"""Pure calculator for the outcome-blind Quant Research market-state vector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
    QuantResearchMarketStateAvailability,
    QuantResearchMarketStateMetricValueV1,
    market_state_metric_definition_fingerprint,
)


ZERO = Decimal("0")
VALUE_QUANTUM = Decimal("0.0000000001")
MEMBER_COVERAGE_FLOOR = Decimal("0.75")
MEMBER_COUNT_FLOOR = 500


class QuantResearchMarketStateCalculationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QuantResearchMarketStateBarV1:
    session: date
    close: Decimal


@dataclass(frozen=True, slots=True)
class QuantResearchMarketStateMemberSeriesV1:
    instrument_id: str
    bars: tuple[QuantResearchMarketStateBarV1, ...]


def calculate_quant_research_market_state_vector_v1(
    *,
    benchmark_series: dict[str, tuple[QuantResearchMarketStateBarV1, ...]],
    member_series: tuple[QuantResearchMarketStateMemberSeriesV1, ...],
    declared_member_count: int,
) -> tuple[QuantResearchMarketStateMetricValueV1, ...]:
    """Calculate raw state metrics without accepting a forward outcome."""

    with localcontext(_context()):
        return _calculate(
            benchmark_series=benchmark_series,
            member_series=member_series,
            declared_member_count=declared_member_count,
        )


def _calculate(*, benchmark_series, member_series, declared_member_count):
    if set(benchmark_series) != {"SPY", "QQQ", "IWM", "DIA"}:
        raise QuantResearchMarketStateCalculationError(
            "benchmark identity set differs"
        )
    sessions = _validate_series(benchmark_series["SPY"], label="SPY")
    for ticker in ("QQQ", "IWM", "DIA"):
        if _validate_series(benchmark_series[ticker], label=ticker) != sessions:
            raise QuantResearchMarketStateCalculationError(
                "benchmark sessions are not exactly aligned"
            )
    if declared_member_count < 0 or len(member_series) > declared_member_count:
        raise QuantResearchMarketStateCalculationError("member counts differ")
    ids = tuple(item.instrument_id for item in member_series)
    if ids != tuple(sorted(set(ids))):
        raise QuantResearchMarketStateCalculationError(
            "member series must be uniquely sorted"
        )
    for item in member_series:
        if _validate_series(item.bars, label=item.instrument_id) != sessions:
            raise QuantResearchMarketStateCalculationError(
                "member sessions are not exactly aligned"
            )

    spy = benchmark_series["SPY"]
    computations = {
        "spy_log_return_20s": _log_return(spy, 0, 20),
        "spy_realized_volatility_20s": Decimal(252).sqrt()
        * _sample_std(_daily_log_returns(spy)),
        "qqq_spy_relative_log_return_20s": _log_return(
            benchmark_series["QQQ"], 0, 20
        )
        - _log_return(spy, 0, 20),
        "iwm_spy_relative_log_return_20s": _log_return(
            benchmark_series["IWM"], 0, 20
        )
        - _log_return(spy, 0, 20),
        "dia_spy_relative_log_return_20s": _log_return(
            benchmark_series["DIA"], 0, 20
        )
        - _log_return(spy, 0, 20),
        "broad_etf_above_sma20_share": sum(
            Decimal(
                benchmark_series[ticker][-1].close
                > _mean(
                    tuple(bar.close for bar in benchmark_series[ticker][-20:])
                )
            )
            for ticker in ("SPY", "QQQ", "IWM", "DIA")
        )
        / Decimal(4),
    }
    result = [
        _available(
            metric_id,
            value,
            actual=(20 if metric_id == "spy_realized_volatility_20s" else 21),
            expected=(20 if metric_id == "spy_realized_volatility_20s" else 21),
        )
        for metric_id, value in computations.items()
    ]

    complete = len(member_series)
    coverage = (
        Decimal(complete) / Decimal(declared_member_count)
        if declared_member_count
        else ZERO
    )
    cross_ids = QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER[6:]
    if complete < MEMBER_COUNT_FLOOR or coverage < MEMBER_COVERAGE_FLOOR:
        reasons = []
        if complete < MEMBER_COUNT_FLOOR:
            reasons.append("complete_member_count_below_floor")
        if coverage < MEMBER_COVERAGE_FLOOR:
            reasons.append("complete_member_coverage_below_floor")
        result.extend(
            _unavailable(
                metric_id,
                reasons=tuple(reasons),
                actual=complete,
                expected=max(declared_member_count, 1),
            )
            for metric_id in cross_ids
        )
    else:
        returns_5 = tuple(_log_return(item.bars, 15, 20) for item in member_series)
        returns_20 = tuple(_log_return(item.bars, 0, 20) for item in member_series)
        cross_values = {
            "reconstructed_member_positive_log_return_5s_share": sum(
                Decimal(value > ZERO) for value in returns_5
            ) / Decimal(complete),
            "reconstructed_member_above_sma20_share": sum(
                Decimal(
                    item.bars[-1].close
                    > _mean(tuple(bar.close for bar in item.bars[-20:]))
                )
                for item in member_series
            ) / Decimal(complete),
            "reconstructed_member_log_return_dispersion_5s": Decimal("1.4826")
            * _mad(returns_5),
            "reconstructed_member_log_return_dispersion_20s": Decimal("1.4826")
            * _mad(returns_20),
        }
        result.extend(
            _available(
                metric_id,
                value,
                actual=complete,
                expected=declared_member_count,
            )
            for metric_id, value in cross_values.items()
        )

    if tuple(item.metric_id for item in result) != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER:
        raise QuantResearchMarketStateCalculationError(
            "market-state implementation is incomplete"
        )
    return tuple(result)


def _validate_series(series, *, label: str) -> tuple[date, ...]:
    if len(series) != 21:
        raise QuantResearchMarketStateCalculationError(
            f"{label} source session count differs"
        )
    sessions = tuple(item.session for item in series)
    if sessions != tuple(sorted(set(sessions))):
        raise QuantResearchMarketStateCalculationError(
            f"{label} sessions are not uniquely ordered"
        )
    if any(not item.close.is_finite() or item.close <= ZERO for item in series):
        raise QuantResearchMarketStateCalculationError(
            f"{label} close is invalid"
        )
    return sessions


def _log_return(series, start: int, end: int) -> Decimal:
    return (series[end].close / series[start].close).ln()


def _daily_log_returns(series) -> tuple[Decimal, ...]:
    return tuple(_log_return(series, index - 1, index) for index in range(1, 21))


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal:
    ordered = tuple(sorted(values))
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def _mad(values: tuple[Decimal, ...]) -> Decimal:
    center = _median(values)
    return _median(tuple(abs(value - center) for value in values))


def _sample_std(values: tuple[Decimal, ...]) -> Decimal:
    center = _mean(values)
    return (
        sum(((value - center) ** 2 for value in values), ZERO)
        / Decimal(len(values) - 1)
    ).sqrt()


def _available(metric_id, value, *, actual: int, expected: int):
    return QuantResearchMarketStateMetricValueV1(
        metric_id=metric_id,
        definition_fingerprint=market_state_metric_definition_fingerprint(metric_id),
        availability=QuantResearchMarketStateAvailability.AVAILABLE,
        value=_render(value),
        actual_observations=actual,
        expected_observations=expected,
        coverage_ratio=_render(Decimal(actual) / Decimal(expected)),
    )


def _unavailable(metric_id, *, reasons, actual: int, expected: int):
    return QuantResearchMarketStateMetricValueV1(
        metric_id=metric_id,
        definition_fingerprint=market_state_metric_definition_fingerprint(metric_id),
        availability=QuantResearchMarketStateAvailability.UNAVAILABLE,
        actual_observations=actual,
        expected_observations=expected,
        coverage_ratio=_render(Decimal(actual) / Decimal(expected)),
        reason_codes=tuple(sorted(reasons)),
    )


def _render(value: Decimal) -> str:
    quantized = value.quantize(VALUE_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized == ZERO:
        quantized = abs(quantized)
    return format(quantized, "f")


def _context() -> Context:
    return Context(prec=50, rounding=ROUND_HALF_EVEN)
