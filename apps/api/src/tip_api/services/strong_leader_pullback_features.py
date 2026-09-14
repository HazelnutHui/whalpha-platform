"""Single pure calculator for Strong-Leader Pullback outcome-free features."""

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
from typing import Mapping
from uuid import UUID


SOURCE_SESSION_COUNT = 21
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
SCORE_QUANTUM = Decimal("0.0001")


class StrongLeaderPullbackFeatureError(ValueError):
    """Raised when a feature panel cannot produce the registered calculation."""


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackFeatureBar:
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackComputedFeatures:
    instrument_id: UUID
    relative_strength_20s_percentile: str
    trend_quality_score: str
    pullback_depth_atr: str
    close_above_prior_close: bool
    close_above_prior_high: bool
    pullback_volume_ratio: str


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackFeaturePanel:
    benchmark_20_session_return: Decimal
    features: tuple[StrongLeaderPullbackComputedFeatures, ...]


def calculate_strong_leader_pullback_features(
    *,
    member_ids: frozenset[UUID],
    benchmark_instrument_id: UUID,
    series_by_instrument: Mapping[
        UUID, tuple[StrongLeaderPullbackFeatureBar, ...]
    ],
) -> StrongLeaderPullbackFeaturePanel:
    """Calculate the exact registered 21-session features without outcomes."""

    if not member_ids or benchmark_instrument_id in member_ids:
        raise StrongLeaderPullbackFeatureError(
            "feature population or benchmark identity differs"
        )
    required_ids = member_ids | {benchmark_instrument_id}
    if set(series_by_instrument) != required_ids:
        raise StrongLeaderPullbackFeatureError(
            "feature panel does not exactly cover members and benchmark"
        )
    expected_sessions: tuple[date, ...] | None = None
    for instrument_id in sorted(required_ids, key=str):
        series = series_by_instrument[instrument_id]
        sessions = tuple(item.session for item in series)
        if (
            len(series) != SOURCE_SESSION_COUNT
            or sessions != tuple(sorted(set(sessions)))
            or (expected_sessions is not None and sessions != expected_sessions)
            or any(
                not all(
                    value.is_finite()
                    for value in (
                        item.open,
                        item.high,
                        item.low,
                        item.close,
                        item.volume,
                    )
                )
                or min(item.open, item.high, item.low, item.close) <= ZERO
                or item.volume < ZERO
                or item.low > min(item.open, item.close)
                or item.high < max(item.open, item.close)
                for item in series
            )
        ):
            raise StrongLeaderPullbackFeatureError(
                "feature series is incomplete or invalid"
            )
        expected_sessions = sessions

    benchmark_return = _return_20(
        series_by_instrument[benchmark_instrument_id]
    )
    relative_returns = {
        instrument_id: _return_20(series_by_instrument[instrument_id])
        - benchmark_return
        for instrument_id in member_ids
    }
    percentiles = _average_rank_percentiles(relative_returns)
    output = []
    for instrument_id in sorted(member_ids, key=str):
        series = series_by_instrument[instrument_id]
        current = series[-1]
        prior = series[-2]
        atr = _atr14(series)
        if atr <= ZERO:
            raise StrongLeaderPullbackFeatureError(
                f"non-positive ATR for {instrument_id}"
            )
        prior_close_high = max(item.close for item in series[:-1])
        prior_median_volume = Decimal(
            str(median(tuple(item.volume for item in series[:-1])))
        )
        if prior_median_volume <= ZERO:
            raise StrongLeaderPullbackFeatureError(
                f"non-positive prior volume median for {instrument_id}"
            )
        output.append(
            StrongLeaderPullbackComputedFeatures(
                instrument_id=instrument_id,
                relative_strength_20s_percentile=_score(
                    percentiles[instrument_id]
                ),
                trend_quality_score=_score(_trend_quality(series)),
                pullback_depth_atr=_score(
                    _divide(prior_close_high - current.close, atr)
                ),
                close_above_prior_close=current.close > prior.close,
                close_above_prior_high=current.close > prior.high,
                pullback_volume_ratio=_score(
                    _divide(current.volume, prior_median_volume)
                ),
            )
        )
    return StrongLeaderPullbackFeaturePanel(
        benchmark_20_session_return=benchmark_return,
        features=tuple(output),
    )


def _return_20(series: tuple[StrongLeaderPullbackFeatureBar, ...]) -> Decimal:
    with localcontext(_context()):
        return series[-1].close / series[0].close - ONE


def _trend_quality(
    series: tuple[StrongLeaderPullbackFeatureBar, ...],
) -> Decimal:
    with localcontext(_context()):
        closes = tuple(item.close for item in series)
        sma10 = sum(closes[-10:], ZERO) / Decimal(10)
        sma20 = sum(closes[-20:], ZERO) / Decimal(20)
        above = HUNDRED if closes[-1] > sma10 else ZERO
        ratio = _linear(
            sma10 / sma20 - ONE, Decimal("-0.03"), Decimal("0.03")
        )
        drawdown = abs(_maximum_drawdown(closes[-6:]))
        drawdown_score = HUNDRED - _linear(
            drawdown, Decimal("0.02"), Decimal("0.12")
        )
        return (
            Decimal("0.35") * above
            + Decimal("0.35") * ratio
            + Decimal("0.30") * drawdown_score
        )


def _atr14(series: tuple[StrongLeaderPullbackFeatureBar, ...]) -> Decimal:
    with localcontext(_context()):
        true_ranges = tuple(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
            for previous, current in zip(
                series[-15:-1], series[-14:], strict=True
            )
        )
        return sum(true_ranges, ZERO) / Decimal(14)


def _average_rank_percentiles(
    values: Mapping[UUID, Decimal],
) -> dict[UUID, Decimal]:
    if not values:
        raise StrongLeaderPullbackFeatureError(
            "relative-strength cross-section is empty"
        )
    if len(set(values.values())) == 1:
        return {key: Decimal("0.5") for key in values}
    with localcontext(_context()):
        groups: dict[Decimal, list[UUID]] = {}
        for key, value in values.items():
            groups.setdefault(value, []).append(key)
        output = {}
        rank_start = 1
        denominator = Decimal(len(values) - 1)
        for value in sorted(groups):
            keys = sorted(groups[value], key=str)
            rank_end = rank_start + len(keys) - 1
            average_rank = (Decimal(rank_start) + Decimal(rank_end)) / Decimal(2)
            percentile = (average_rank - ONE) / denominator
            for key in keys:
                output[key] = percentile
            rank_start = rank_end + 1
        return output


def _maximum_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    peak = values[0]
    drawdown = ZERO
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - ONE)
    return drawdown


def _linear(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(HUNDRED, max(ZERO, HUNDRED * (value - low) / (high - low)))


def _divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    with localcontext(_context()):
        return numerator / denominator


def _score(value: Decimal) -> str:
    with localcontext(_context()):
        return format(value.quantize(SCORE_QUANTUM), "f")


def _context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    return context
