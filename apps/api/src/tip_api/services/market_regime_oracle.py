"""Independent raw-panel oracle for Market Regime Phase 1a.

This module deliberately does not import or invoke the production calculation
service. It rebuilds every metric, normalization, missingness decision, weight,
dimension, and composite from the formal raw panel.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, replace
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

from tip_api.contracts.analytics.v1 import MarketRegimeCompositeV1, OracleComparisonV1
from tip_api.parameters.market_regime.v1_0_0 import (
    BROAD_BENCHMARK_TICKERS,
    DIMENSION_PARAMETERS,
    MINIMUM_COMPOSITE_WEIGHT,
    MINIMUM_DIMENSION_INTERNAL_WEIGHT,
    PARAMETER_SET_FINGERPRINT,
    REQUIRED_COMPOSITE_DIMENSIONS,
)
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


ZERO = Decimal(0)
HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class _Observed:
    value: Decimal | None
    actual: int
    minimum: int
    coverage: Decimal | None
    missing: int
    reason: str | None
    reason_codes: tuple[str, ...]


def compare_with_independent_oracle(
    *,
    panel: MarketRegimeInputPanel,
    result: MarketRegimeCompositeV1,
) -> OracleComparisonV1:
    """Compare every Phase 1a ledger field with a separate implementation."""

    with localcontext(_context()):
        expected = _oracle(panel, result.universe_id)
        shuffled = _oracle(replace(panel, bars=tuple(reversed(panel.bars))), result.universe_id)
    mismatches: list[str] = []
    actual_metrics = {
        metric.metric_id: metric
        for dimension in result.dimensions
        for metric in dimension.raw_metrics
    }
    for metric_id in expected["metric_order"]:
        actual = actual_metrics.get(metric_id)
        oracle = expected["metrics"][metric_id]
        if actual is None:
            mismatches.append(f"{metric_id}: missing production metric")
            continue
        checks = {
            "raw_value": actual.raw_value,
            "normalized_value": actual.normalized_value,
            "configured_weight": actual.configured_weight,
            "effective_weight": actual.effective_weight,
            "weighted_contribution": actual.weighted_contribution,
            "actual_observations": actual.actual_observations,
            "minimum_observations": actual.minimum_observations,
            "coverage_ratio": actual.coverage_ratio,
            "missing_count": actual.missing_count,
            "availability": actual.availability.value,
            "missing_reason": actual.missing_reason,
            "reason_codes": list(actual.reason_codes),
        }
        for field, actual_value in checks.items():
            if actual_value != oracle[field]:
                mismatches.append(
                    f"{metric_id}.{field}: production={actual_value!r} oracle={oracle[field]!r}"
                )

    actual_dimensions = {item.dimension_id: item for item in result.dimensions}
    for dimension_id in expected["dimension_order"]:
        actual = actual_dimensions[dimension_id]
        oracle = expected["dimensions"][dimension_id]
        checks = {
            "score": actual.score,
            "configured_weight": actual.configured_weight,
            "effective_weight": actual.effective_weight,
            "internal_configured_weight_available": actual.internal_configured_weight_available,
            "score_contribution": actual.score_contribution,
            "availability": actual.availability.value,
            "reason_codes": list(actual.reason_codes),
        }
        for field, actual_value in checks.items():
            if actual_value != oracle[field]:
                mismatches.append(
                    f"{dimension_id}.{field}: production={actual_value!r} oracle={oracle[field]!r}"
                )
    if result.regime_score != expected["regime_score"]:
        mismatches.append(
            f"regime_score: production={result.regime_score!r} oracle={expected['regime_score']!r}"
        )
    if result.configured_weight_available != expected["configured_weight_available"]:
        mismatches.append(
            "configured_weight_available: production="
            f"{result.configured_weight_available!r} oracle={expected['configured_weight_available']!r}"
        )
    if result.parameter_set_fingerprint != PARAMETER_SET_FINGERPRINT:
        mismatches.append("parameter set fingerprint mismatch")

    reconciliation: list[str] = []
    for dimension in result.dimensions:
        if dimension.score is not None:
            summed = _s4(sum(
                (Decimal(item.weighted_contribution) for item in dimension.raw_metrics if item.weighted_contribution is not None),
                ZERO,
            ))
            if summed != dimension.score:
                reconciliation.append(
                    f"{dimension.dimension_id}: metric contributions {summed} != score {dimension.score}"
                )
    if result.regime_score is not None:
        summed = _s4(sum(
            (Decimal(item.score_contribution) for item in result.dimensions if item.score_contribution is not None),
            ZERO,
        ))
        if summed != result.regime_score:
            reconciliation.append(f"composite contributions {summed} != score {result.regime_score}")

    future_count = 0
    wrong_universe_count = 0
    for metric in actual_metrics.values():
        for reference in metric.source_input_references:
            if reference.startswith("eod:") and reference.split(":", 2)[1] > result.as_of_session.isoformat():
                future_count += 1
            if reference.startswith("activation:") and not reference.startswith(f"activation:{result.universe_id}:"):
                wrong_universe_count += 1
    if future_count:
        mismatches.append(f"future source references: {future_count}")
    if wrong_universe_count:
        mismatches.append(f"wrong Universe source references: {wrong_universe_count}")
    permutation_match = expected["fingerprint"] == shuffled["fingerprint"]
    if not permutation_match:
        mismatches.append("oracle input permutation changed output")

    oracle_payload = {
        "universe_id": result.universe_id,
        "as_of_session": result.as_of_session.isoformat(),
        "expected_fingerprint": expected["fingerprint"],
        "mismatches": mismatches,
        "reconciliation": reconciliation,
        "future_session_reference_count": future_count,
        "wrong_universe_reference_count": wrong_universe_count,
        "input_permutation_fingerprint_match": permutation_match,
    }
    return OracleComparisonV1(
        as_of_session=result.as_of_session,
        universe_id=result.universe_id,
        compared_metric_count=len(expected["metric_order"]),
        mismatch_count=len(mismatches) + len(reconciliation),
        mismatches=tuple(mismatches),
        contribution_reconciliation_mismatches=tuple(reconciliation),
        future_session_reference_count=future_count,
        wrong_universe_reference_count=wrong_universe_count,
        input_permutation_fingerprint_match=permutation_match,
        oracle_fingerprint=_fp(oracle_payload),
    )


def _oracle(panel: MarketRegimeInputPanel, universe_id: str) -> dict[str, object]:
    universe = panel.select_universe(universe_id)
    sessions = panel.sessions
    if tuple(sorted(sessions)) != sessions or sessions[-1] != panel.as_of_session:
        raise ValueError("oracle input sessions are invalid")
    by_date: dict[object, dict[UUID, object]] = {session: {} for session in sessions}
    history: dict[UUID, dict[object, object]] = defaultdict(dict)
    for row in panel.bars:
        if row.session_date > panel.as_of_session or row.session_date not in by_date:
            raise ValueError("oracle found future/out-of-window row")
        if row.instrument_id in by_date[row.session_date]:
            raise ValueError("oracle found duplicate business key")
        by_date[row.session_date][row.instrument_id] = row
        history[row.instrument_id][row.session_date] = row
    if any(not by_date[item] for item in sessions):
        raise ValueError("oracle found session gap")
    current_rows = by_date[panel.as_of_session].values()
    bench: dict[str, UUID] = {}
    for ticker in BROAD_BENCHMARK_TICKERS:
        ids = sorted(
            (row.instrument_id for row in current_rows if row.ticker == ticker and row.instrument_type == "etf"),
            key=str,
        )
        if len(ids) != 1:
            raise ValueError("oracle broad benchmark resolution failure")
        bench[ticker] = ids[0]

    def simple_return(instrument_id: UUID, lookback: int) -> Decimal | None:
        if len(sessions) <= lookback:
            return None
        last = by_date[sessions[-1]].get(instrument_id)
        first = by_date[sessions[-1 - lookback]].get(instrument_id)
        return None if last is None or first is None else last.close / first.close - Decimal(1)

    def closes(instrument_id: UUID, count: int) -> tuple[Decimal, ...] | None:
        rows = [by_date[session].get(instrument_id) for session in sessions[-count:]]
        return None if len(sessions) < count or any(row is None for row in rows) else tuple(row.close for row in rows)

    def benchmark_returns(lookback: int) -> dict[str, Decimal]:
        result = {}
        for ticker, instrument_id in bench.items():
            value = simple_return(instrument_id, lookback)
            if value is not None:
                result[ticker] = value
        return result

    def member_returns(lookback: int) -> dict[UUID, Decimal]:
        result = {}
        for instrument_id in sorted(universe.member_ids, key=str):
            value = simple_return(instrument_id, lookback)
            if value is not None:
                result[instrument_id] = value
        return result

    member_count = len(universe.member_ids)
    all_observed: dict[str, _Observed] = {}

    r20_bench = benchmark_returns(20)
    r5_bench = benchmark_returns(5)
    sma_bench = []
    for instrument_id in bench.values():
        values = closes(instrument_id, 20)
        if values is not None:
            sma_bench.append(Decimal(values[-1] > _avg(values)))
    median_bench = _med(tuple(r5_bench.values())) if r5_bench else None
    agreement_bench = [
        Decimal(_sgn(value) == _sgn(median_bench)) for value in r5_bench.values()
    ] if median_bench is not None else []
    all_observed.update({
        "broad_return_20": _count(_med(tuple(r20_bench.values())) if len(r20_bench) == 4 else None, len(r20_bench), 4),
        "broad_return_5": _count(_med(tuple(r5_bench.values())) if len(r5_bench) == 4 else None, len(r5_bench), 4),
        "broad_above_sma20_share": _count(_avg(tuple(sma_bench)) if len(sma_bench) >= 3 else None, len(sma_bench), 3),
        "broad_direction_agreement": _count(_avg(tuple(agreement_bench)) if len(agreement_bench) >= 3 else None, len(agreement_bench), 3),
    })

    r1 = member_returns(1)
    r5 = member_returns(5)
    member_sma = []
    member_high_low = []
    for instrument_id in sorted(universe.member_ids, key=str):
        values = closes(instrument_id, 20)
        if values is not None:
            member_sma.append(Decimal(values[-1] > _avg(values)))
            member_high_low.append((values[-1] == max(values), values[-1] == min(values)))
    all_observed.update({
        "advancer_share_1": _coverage(_positive_share(tuple(r1.values())), len(r1), member_count, Decimal("0.80"), 500),
        "positive_return_share_5": _coverage(_positive_share(tuple(r5.values())), len(r5), member_count, Decimal("0.80"), 0),
        "above_sma20_share": _coverage(_avg(tuple(member_sma)) if member_sma else None, len(member_sma), member_count, Decimal("0.75"), 0),
        "high_low_balance_20": _coverage(
            (Decimal(sum(high for high, _ in member_high_low)) - Decimal(sum(low for _, low in member_high_low))) / Decimal(len(member_high_low)) if member_high_low else None,
            len(member_high_low), member_count, Decimal("0.75"), 0,
        ),
    })

    def log_returns(instrument_id: UUID) -> tuple[Decimal, ...] | None:
        values = closes(instrument_id, 11)
        return None if values is None else tuple((values[i] / values[i - 1]).ln() for i in range(1, 11))

    spy_logs = log_returns(bench["SPY"])
    spy_vol = _annual_std(spy_logs) if spy_logs is not None else None
    stock_vols = []
    for instrument_id in sorted(universe.member_ids, key=str):
        values = log_returns(instrument_id)
        if values is not None:
            stock_vols.append(_annual_std(values))
    tail = []
    for offset in range(5, 0, -1):
        current_index = len(sessions) - offset
        for instrument_id in universe.member_ids:
            current = by_date[sessions[current_index]].get(instrument_id)
            previous = by_date[sessions[current_index - 1]].get(instrument_id)
            if current is not None and previous is not None:
                tail.append(current.close / previous.close - Decimal(1))
    tail_total = member_count * 5
    tail_value = Decimal(sum(value <= Decimal("-0.04") for value in tail)) / Decimal(len(tail)) if tail else None
    all_observed.update({
        "spy_realized_volatility_10": _count(spy_vol, len(spy_logs or ()), 10),
        "median_stock_realized_volatility_10": _coverage(_med(tuple(stock_vols)) if stock_vols else None, len(stock_vols), member_count, Decimal("0.70"), 0),
        "downside_tail_frequency_5": _coverage(tail_value, len(tail), tail_total, Decimal("0.70"), 0),
        "cross_sectional_dispersion_1": _count(Decimal("1.4826") * _mad(tuple(r1.values())) if r1 else None, len(r1), 500),
    })

    prior_sums = []
    valid_prior = 0
    for session in sessions[-21:-1]:
        rows = [by_date[session].get(item) for item in universe.member_ids]
        valid = [item for item in rows if item is not None]
        if Decimal(len(valid)) / Decimal(member_count) >= Decimal("0.80"):
            valid_prior += 1
            prior_sums.append(sum((_exact_product(item.close, item.volume) for item in valid), ZERO))
    current = sessions[-1]
    current_valid = [by_date[current].get(item) for item in universe.member_ids]
    current_valid = [item for item in current_valid if item is not None]
    current_cov = Decimal(len(current_valid)) / Decimal(member_count)
    current_sum = sum((_exact_product(item.close, item.volume) for item in current_valid), ZERO)
    prior_median = _med(tuple(prior_sums)) if prior_sums else None
    aggregate_reason = None
    aggregate_value = None
    if current_cov < Decimal("0.80"):
        aggregate_reason = "insufficient_coverage"
    elif valid_prior < 18:
        aggregate_reason = "insufficient_reference_sessions"
    elif prior_median is None or prior_median <= 0:
        aggregate_reason = "zero_denominator"
    else:
        aggregate_value = current_sum / prior_median
    all_observed["aggregate_participation_ratio"] = _Observed(
        aggregate_value, valid_prior, 18, current_cov, 20 - valid_prior, aggregate_reason,
        _codes(aggregate_reason, proxy=True),
    )
    comparable = []
    for instrument_id, value in r1.items():
        row = by_date[current].get(instrument_id)
        if row is not None:
            comparable.append((value, row))
    comp_cov = Decimal(len(comparable)) / Decimal(member_count)
    total = sum((_exact_product(row.close, row.volume) for _, row in comparable), ZERO)
    up = sum((_exact_product(row.close, row.volume) for value, row in comparable if value > 0), ZERO)
    up_reason = "insufficient_coverage" if comp_cov < Decimal("0.80") else "zero_denominator" if total <= 0 else None
    all_observed["up_participation_share"] = _Observed(
        up / total if up_reason is None else None, len(comparable), 0, comp_cov,
        member_count - len(comparable), up_reason, _codes(up_reason, proxy=True),
    )
    volume_flags = []
    for instrument_id in sorted(universe.member_ids, key=str):
        row = by_date[current].get(instrument_id)
        history_volumes = tuple(
            candidate.volume for session in sessions[-21:-1]
            if (candidate := by_date[session].get(instrument_id)) is not None
        )
        if row is not None and len(history_volumes) >= 15:
            volume_flags.append(row.volume > _med(history_volumes))
    volume_cov = Decimal(len(volume_flags)) / Decimal(member_count)
    volume_reason = None if volume_cov >= Decimal("0.70") else "insufficient_coverage"
    all_observed["above_own_volume_median_share"] = _Observed(
        Decimal(sum(volume_flags)) / Decimal(len(volume_flags)) if volume_flags and volume_reason is None else None,
        len(volume_flags), 15, volume_cov, member_count - len(volume_flags), volume_reason,
        _codes(volume_reason, proxy=True),
    )

    positive = sorted(
        ((instrument_id, value) for instrument_id, value in r5.items() if value > 0),
        key=lambda item: (-item[1], str(item[0])),
    )
    r5_cov = Decimal(len(r5)) / Decimal(member_count)
    winner_reason = None
    winner_value = None
    if r5_cov < Decimal("0.70"):
        winner_reason = "insufficient_coverage"
    elif len(positive) < 200:
        winner_reason = "insufficient_positive_observations"
    else:
        count = max(1, (len(positive) + 9) // 10)
        denominator = sum((value for _, value in positive), ZERO)
        winner_reason = "zero_denominator" if denominator <= 0 else None
        if winner_reason is None:
            winner_value = sum((value for _, value in positive[:count]), ZERO) / denominator
    all_observed["winner_concentration_5"] = _Observed(
        winner_value, len(positive), 200, r5_cov, member_count - len(r5), winner_reason,
        _codes(winner_reason, extra=("winner_top_decile_ceiling_stable_tiebreak",)),
    )
    agree = [Decimal(_sgn(value) == _sgn(median_bench)) for value in r5_bench.values()] if median_bench is not None else []
    all_observed["benchmark_direction_agreement_5"] = _count(
        _avg(tuple(agree)) if len(agree) >= 3 else None, len(agree), 3
    )
    all_observed["return_dispersion_5"] = _count(
        Decimal("1.4826") * _mad(tuple(r5.values())) if r5 else None, len(r5), 500
    )

    output_metrics: dict[str, dict[str, object]] = {}
    output_dimensions: dict[str, dict[str, object]] = {}
    metric_order: list[str] = []
    dimension_order: list[str] = []
    available_dimension_weight = ZERO
    for dimension in DIMENSION_PARAMETERS:
        dimension_order.append(dimension.dimension_id)
        available_internal = sum(
            metric.configured_weight for metric in dimension.metrics if all_observed[metric.metric_id].value is not None
        )
        dimension_available = available_internal >= MINIMUM_DIMENSION_INTERNAL_WEIGHT
        present = [metric for metric in dimension.metrics if all_observed[metric.metric_id].value is not None]
        effective = {metric.metric_id: Decimal("0.0000") for metric in dimension.metrics}
        running = ZERO
        if dimension_available:
            for metric in present[:-1]:
                value = _d4(Decimal(metric.configured_weight) * HUNDRED / Decimal(available_internal))
                effective[metric.metric_id] = value
                running += value
            if present:
                effective[present[-1].metric_id] = HUNDRED - running
        contributions = []
        for metric in dimension.metrics:
            metric_order.append(metric.metric_id)
            observed = all_observed[metric.metric_id]
            normalized = _normal(observed.value, metric) if observed.value is not None else None
            contribution = (
                _d4(normalized * effective[metric.metric_id] / HUNDRED)
                if normalized is not None and dimension_available
                else Decimal("0.0000") if normalized is not None else None
            )
            if contribution is not None:
                contributions.append(contribution)
            output_metrics[metric.metric_id] = {
                "raw_value": _s10(observed.value) if observed.value is not None else None,
                "normalized_value": _s4(normalized) if normalized is not None else None,
                "configured_weight": _s4(Decimal(metric.configured_weight)),
                "effective_weight": _s4(effective[metric.metric_id] if observed.value is not None else ZERO),
                "weighted_contribution": _s4(contribution) if contribution is not None else None,
                "actual_observations": observed.actual,
                "minimum_observations": observed.minimum,
                "coverage_ratio": _s10(observed.coverage) if observed.coverage is not None else None,
                "missing_count": observed.missing,
                "availability": "available" if observed.value is not None else "unavailable",
                "missing_reason": observed.reason,
                "reason_codes": list(observed.reason_codes),
            }
        score = _d4(sum(contributions, ZERO)) if dimension_available else None
        score_contribution = _d4(score * Decimal(dimension.configured_weight) / HUNDRED) if score is not None else None
        reasons = ["dimension_available" if dimension_available else "dimension_unavailable_insufficient_internal_weight"]
        if dimension_available and available_internal < 100:
            reasons.append("internal_weight_redistributed")
        output_dimensions[dimension.dimension_id] = {
            "score": _s4(score) if score is not None else None,
            "configured_weight": _s4(Decimal(dimension.configured_weight)),
            "effective_weight": _s4(Decimal(dimension.configured_weight) if dimension_available else ZERO),
            "internal_configured_weight_available": _s4(Decimal(available_internal)),
            "score_contribution": _s4(score_contribution) if score_contribution is not None else None,
            "availability": "available" if dimension_available else "unavailable",
            "reason_codes": reasons,
        }
        if dimension_available:
            available_dimension_weight += Decimal(dimension.configured_weight)
    required_present = all(output_dimensions[item]["availability"] == "available" for item in REQUIRED_COMPOSITE_DIMENSIONS)
    composite = (
        _s4(sum((Decimal(item["score_contribution"]) for item in output_dimensions.values() if item["score_contribution"] is not None), ZERO))
        if available_dimension_weight >= MINIMUM_COMPOSITE_WEIGHT and required_present else None
    )
    payload = {
        "metric_order": metric_order,
        "dimension_order": dimension_order,
        "metrics": output_metrics,
        "dimensions": output_dimensions,
        "regime_score": composite,
        "configured_weight_available": _s4(available_dimension_weight),
    }
    payload["fingerprint"] = _fp(payload)
    return payload


def _count(value: Decimal | None, actual: int, minimum: int) -> _Observed:
    reason = None if value is not None and actual >= minimum else "insufficient_observations"
    return _Observed(value if reason is None else None, actual, minimum, None, max(0, minimum - actual), reason, _codes(reason))


def _coverage(value, actual, total, threshold, minimum) -> _Observed:
    coverage = Decimal(actual) / Decimal(total) if total else ZERO
    reason = "insufficient_coverage" if coverage < threshold else "insufficient_observations" if actual < minimum else "zero_denominator" if value is None else None
    return _Observed(value if reason is None else None, actual, minimum, coverage, max(0, total - actual), reason, _codes(reason))


def _codes(reason: str | None, *, proxy: bool = False, extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    values = ["metric_available" if reason is None else reason]
    if proxy:
        values.append("participation_proxy_not_fund_flow")
    values.extend(extra)
    return tuple(values)


def _normal(value, metric) -> Decimal:
    low, high = Decimal(metric.low), Decimal(metric.high)
    if metric.normalizer == "triangular":
        center = Decimal(metric.center)
        if value <= low or value >= high:
            return ZERO
        return min(HUNDRED, max(ZERO, HUNDRED * (value - low) / (center - low))) if value <= center else min(HUNDRED, max(ZERO, HUNDRED * (high - value) / (high - center)))
    rising = min(HUNDRED, max(ZERO, HUNDRED * (value - low) / (high - low)))
    return HUNDRED - rising if metric.normalizer == "declining" else rising


def _avg(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _med(values: tuple[Decimal, ...]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _mad(values: tuple[Decimal, ...]) -> Decimal:
    center = _med(values)
    return _med(tuple(abs(value - center) for value in values))


def _positive_share(values: tuple[Decimal, ...]) -> Decimal | None:
    return Decimal(sum(value > 0 for value in values)) / Decimal(len(values)) if values else None


def _annual_std(values: tuple[Decimal, ...]) -> Decimal:
    mean = _avg(values)
    variance = sum(((value - mean) ** 2 for value in values), ZERO) / Decimal(len(values) - 1)
    return variance.sqrt() * Decimal(252).sqrt()


def _exact_product(left: Decimal, right: Decimal) -> Decimal:
    left_coefficient, left_scale = _coefficient_scale(left)
    right_coefficient, right_scale = _coefficient_scale(right)
    coefficient = left_coefficient * right_coefficient
    scale = left_scale + right_scale
    sign = 1 if coefficient < 0 else 0
    digits = tuple(int(char) for char in str(abs(coefficient)))
    return Decimal((sign, digits, -scale))


def _coefficient_scale(value: Decimal) -> tuple[int, int]:
    sign, digits, exponent = value.as_tuple()
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    if sign:
        coefficient = -coefficient
    if exponent >= 0:
        return coefficient * (10 ** exponent), 0
    return coefficient, -exponent


def _sgn(value: Decimal) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    return context


def _d4(value: Decimal) -> Decimal:
    with localcontext(_context()):
        return value.quantize(Decimal("0.0001"))


def _s4(value: Decimal) -> str:
    return format(_d4(value), "f")


def _s10(value: Decimal) -> str:
    with localcontext(_context()):
        return format(value.quantize(Decimal("0.0000000001")), "f")


def _fp(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
