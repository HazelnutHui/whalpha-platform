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


@dataclass(frozen=True, slots=True)
class QuantResearchMarketStateUnavailableMemberV1:
    instrument_id: str
    reason_codes: tuple[str, ...]


def calculate_quant_research_market_state_vector_v1(
    *,
    expected_sessions: tuple[date, ...],
    benchmark_series: dict[str, tuple[QuantResearchMarketStateBarV1, ...]],
    benchmark_unavailable_reasons: dict[str, tuple[str, ...]],
    declared_member_ids: tuple[str, ...],
    member_series: tuple[QuantResearchMarketStateMemberSeriesV1, ...],
    unavailable_members: tuple[QuantResearchMarketStateUnavailableMemberV1, ...],
) -> tuple[QuantResearchMarketStateMetricValueV1, ...]:
    """Calculate raw state metrics without accepting a forward outcome."""

    with localcontext(_context()):
        return _calculate(
            expected_sessions=expected_sessions,
            benchmark_series=benchmark_series,
            benchmark_unavailable_reasons=benchmark_unavailable_reasons,
            declared_member_ids=declared_member_ids,
            member_series=member_series,
            unavailable_members=unavailable_members,
        )


def _calculate(
    *,
    expected_sessions,
    benchmark_series,
    benchmark_unavailable_reasons,
    declared_member_ids,
    member_series,
    unavailable_members,
):
    benchmark_tickers = ("SPY", "QQQ", "IWM", "DIA")
    if (
        len(expected_sessions) != 21
        or expected_sessions != tuple(sorted(set(expected_sessions)))
        or set(benchmark_series) != set(benchmark_tickers)
        or set(benchmark_unavailable_reasons) - set(benchmark_tickers)
    ):
        raise QuantResearchMarketStateCalculationError(
            "market-state source-session or benchmark identity set differs"
        )
    for ticker in benchmark_tickers:
        series = benchmark_series[ticker]
        reasons = benchmark_unavailable_reasons.get(ticker, ())
        if (
            (series and reasons)
            or (not series and not reasons)
            or reasons != tuple(sorted(set(reasons)))
        ):
            raise QuantResearchMarketStateCalculationError(
                "benchmark availability reconciliation differs"
            )
        if series and _validate_series(series, label=ticker) != expected_sessions:
            raise QuantResearchMarketStateCalculationError(
                "benchmark sessions are not exactly aligned"
            )
    if declared_member_ids != tuple(sorted(set(declared_member_ids))):
        raise QuantResearchMarketStateCalculationError(
            "declared member identities must be uniquely sorted"
        )
    complete_ids = tuple(item.instrument_id for item in member_series)
    unavailable_ids = tuple(item.instrument_id for item in unavailable_members)
    if complete_ids != tuple(sorted(set(complete_ids))):
        raise QuantResearchMarketStateCalculationError(
            "member series must be uniquely sorted"
        )
    if unavailable_ids != tuple(sorted(set(unavailable_ids))):
        raise QuantResearchMarketStateCalculationError(
            "unavailable members must be uniquely sorted"
        )
    if (
        set(complete_ids) & set(unavailable_ids)
        or tuple(sorted((*complete_ids, *unavailable_ids))) != declared_member_ids
        or any(
            not item.reason_codes
            or item.reason_codes != tuple(sorted(set(item.reason_codes)))
            for item in unavailable_members
        )
    ):
        raise QuantResearchMarketStateCalculationError(
            "declared member reconciliation differs"
        )
    for item in member_series:
        if _validate_series(item.bars, label=item.instrument_id) != expected_sessions:
            raise QuantResearchMarketStateCalculationError(
                "member sessions are not exactly aligned"
            )

    result = _benchmark_metrics(
        benchmark_series=benchmark_series,
        unavailable_reasons=benchmark_unavailable_reasons,
    )

    complete = len(member_series)
    declared_member_count = len(declared_member_ids)
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


def _benchmark_metrics(*, benchmark_series, unavailable_reasons):
    dependencies = (
        ("spy_log_return_20s", ("SPY",), 21),
        ("spy_realized_volatility_20s", ("SPY",), 20),
        ("qqq_spy_relative_log_return_20s", ("SPY", "QQQ"), 21),
        ("iwm_spy_relative_log_return_20s", ("SPY", "IWM"), 21),
        ("dia_spy_relative_log_return_20s", ("SPY", "DIA"), 21),
        (
            "broad_etf_mean_log_distance_to_sma20",
            ("SPY", "QQQ", "IWM", "DIA"),
            21,
        ),
    )
    output = []
    for metric_id, tickers, expected in dependencies:
        reasons = tuple(
            sorted(
                {
                    reason
                    for ticker in tickers
                    for reason in unavailable_reasons.get(ticker, ())
                }
            )
        )
        if reasons:
            output.append(
                _unavailable(metric_id, reasons=reasons, actual=0, expected=expected)
            )
            continue
        spy = benchmark_series["SPY"]
        if metric_id == "spy_log_return_20s":
            value = _log_return(spy, 0, 20)
        elif metric_id == "spy_realized_volatility_20s":
            value = Decimal(252).sqrt() * _sample_std(_daily_log_returns(spy))
        elif metric_id == "broad_etf_mean_log_distance_to_sma20":
            value = sum(
                (
                    benchmark_series[ticker][-1].close
                    / _mean(
                        tuple(
                            bar.close for bar in benchmark_series[ticker][-20:]
                        )
                    )
                ).ln()
                for ticker in tickers
            ) / Decimal(4)
        else:
            comparison = {
                "qqq_spy_relative_log_return_20s": "QQQ",
                "iwm_spy_relative_log_return_20s": "IWM",
                "dia_spy_relative_log_return_20s": "DIA",
            }[metric_id]
            value = _log_return(benchmark_series[comparison], 0, 20) - _log_return(
                spy, 0, 20
            )
        output.append(
            _available(metric_id, value, actual=expected, expected=expected)
        )
    return output


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
