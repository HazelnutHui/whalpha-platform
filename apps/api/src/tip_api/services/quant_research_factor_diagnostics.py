"""Streaming, outcome-blind diagnostics for Quant Research Factor Catalog V1."""

from __future__ import annotations

import hashlib
import math
from array import array
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from itertools import combinations
from typing import Iterable

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    QuantResearchFactorAvailability,
    QuantResearchFactorObservationV1,
    quant_research_factor_catalog_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_diagnostics import (
    QUANT_RESEARCH_FACTOR_DIAGNOSTICS_MINIMUM_PAIR_OBSERVATIONS,
    QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_ABSOLUTE_RHO,
    QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_MINIMUM_SESSIONS,
    QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_SESSION_SHARE,
    QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_SIGN_SHARE,
    QUANT_RESEARCH_FACTOR_PAIR_ORDER,
    QuantResearchFactorConcentrationAxis,
    QuantResearchFactorConcentrationV1,
    QuantResearchFactorCoverageV1,
    QuantResearchFactorDiagnosticsV1,
    QuantResearchFactorDistributionV1,
    QuantResearchFactorNearDuplicateGroupV1,
    QuantResearchFactorPairCorrelationV1,
    QuantResearchFactorReasonCountV1,
    QuantResearchFactorSessionAvailabilityV1,
    factor_diagnostics_fingerprint,
)


VALUE_QUANTUM = Decimal("0.0000000001")
ZERO_RENDERED = "0.0000000000"


class QuantResearchFactorDiagnosticsError(ValueError):
    """Raised when the diagnostic population violates the frozen protocol."""


class QuantResearchFactorDiagnosticsAccumulator:
    """Bounded streaming accumulator that never accepts an outcome field."""

    def __init__(
        self,
        *,
        chronological_plan_fingerprint: str,
        source_population_fingerprint: str,
        source_eod_fingerprint: str,
        source_membership_fingerprint: str,
        source_action_fingerprint: str,
        source_adjustment_fingerprint: str,
        calculation_code_sha256: str,
        diagnostic_code_sha256: str,
        limitation_codes: tuple[str, ...],
    ) -> None:
        fingerprints = (
            chronological_plan_fingerprint,
            source_population_fingerprint,
            source_eod_fingerprint,
            source_membership_fingerprint,
            source_action_fingerprint,
            source_adjustment_fingerprint,
            calculation_code_sha256,
            diagnostic_code_sha256,
        )
        if any(len(item) != 64 or set(item) - set("0123456789abcdef") for item in fingerprints):
            raise QuantResearchFactorDiagnosticsError("diagnostic source fingerprint differs")
        if not limitation_codes or limitation_codes != tuple(sorted(set(limitation_codes))):
            raise QuantResearchFactorDiagnosticsError("diagnostic limitations differ")
        self._metadata = {
            "chronological_plan_fingerprint": chronological_plan_fingerprint,
            "source_population_fingerprint": source_population_fingerprint,
            "source_eod_fingerprint": source_eod_fingerprint,
            "source_membership_fingerprint": source_membership_fingerprint,
            "source_action_fingerprint": source_action_fingerprint,
            "source_adjustment_fingerprint": source_adjustment_fingerprint,
            "calculation_code_sha256": calculation_code_sha256,
            "diagnostic_code_sha256": diagnostic_code_sha256,
            "limitation_codes": limitation_codes,
        }
        self._sessions: list[date] = []
        self._expected_paths = 0
        self._complete_vectors = 0
        self._values = {factor_id: array("d") for factor_id in QUANT_RESEARCH_FACTOR_ORDER}
        self._available = Counter()
        self._unavailable = Counter()
        self._reasons = {factor_id: Counter() for factor_id in QUANT_RESEARCH_FACTOR_ORDER}
        self._session_counts = {factor_id: Counter() for factor_id in QUANT_RESEARCH_FACTOR_ORDER}
        self._instrument_counts = {factor_id: Counter() for factor_id in QUANT_RESEARCH_FACTOR_ORDER}
        self._tie_excess = Counter()
        self._session_availability: list[QuantResearchFactorSessionAvailabilityV1] = []
        self._pair_session_values: dict[tuple[str, str], list[tuple[float, int]]] = {
            pair: [] for pair in QUANT_RESEARCH_FACTOR_PAIR_ORDER
        }

    def add_session(
        self,
        *,
        as_of_session: date,
        observations: Iterable[QuantResearchFactorObservationV1],
    ) -> None:
        if self._sessions and as_of_session <= self._sessions[-1]:
            raise QuantResearchFactorDiagnosticsError("diagnostic sessions are not strictly ordered")
        ordered = tuple(observations)
        if ordered != tuple(sorted(ordered, key=lambda item: str(item.instrument_id))):
            raise QuantResearchFactorDiagnosticsError("diagnostic observations are not stable-ID ordered")
        if len({item.instrument_id for item in ordered}) != len(ordered):
            raise QuantResearchFactorDiagnosticsError("diagnostic session repeats an instrument")
        catalog_fingerprint = quant_research_factor_catalog_v1().logical_fingerprint
        if any(
            item.as_of_session != as_of_session
            or item.catalog_fingerprint != catalog_fingerprint
            or item.source_eod_fingerprint != self._metadata["source_eod_fingerprint"]
            or item.source_adjustment_fingerprint != self._metadata["source_adjustment_fingerprint"]
            or item.contains_forward_outcomes
            for item in ordered
        ):
            raise QuantResearchFactorDiagnosticsError("diagnostic observation source differs")

        self._sessions.append(as_of_session)
        self._expected_paths += len(ordered)
        complete_count = sum(
            all(value.availability is QuantResearchFactorAvailability.AVAILABLE for value in item.factor_values)
            for item in ordered
        )
        self._complete_vectors += complete_count
        session_values: dict[str, list[tuple[str, float]]] = {
            factor_id: [] for factor_id in QUANT_RESEARCH_FACTOR_ORDER
        }
        for observation in ordered:
            instrument = str(observation.instrument_id)
            for value in observation.factor_values:
                factor_id = value.factor_id
                if value.availability is QuantResearchFactorAvailability.AVAILABLE:
                    parsed = float(value.value)
                    if not math.isfinite(parsed):
                        raise QuantResearchFactorDiagnosticsError("factor value is not finite")
                    self._values[factor_id].append(parsed)
                    self._available[factor_id] += 1
                    self._session_counts[factor_id][as_of_session.isoformat()] += 1
                    self._instrument_counts[factor_id][instrument] += 1
                    session_values[factor_id].append((instrument, parsed))
                else:
                    self._unavailable[factor_id] += 1
                    for reason in value.reason_codes:
                        self._reasons[factor_id][reason] += 1

        for factor_id in QUANT_RESEARCH_FACTOR_ORDER:
            available = len(session_values[factor_id])
            unavailable = len(ordered) - available
            self._tie_excess[factor_id] += available - len(
                {value for _, value in session_values[factor_id]}
            )
            self._session_availability.append(
                QuantResearchFactorSessionAvailabilityV1(
                    as_of_session=as_of_session,
                    factor_id=factor_id,
                    expected_count=len(ordered),
                    available_count=available,
                    unavailable_count=unavailable,
                    availability_rate=_ratio(available, len(ordered)),
                )
            )
        self._append_pair_correlations(session_values)

    def build(self) -> QuantResearchFactorDiagnosticsV1:
        if not self._sessions:
            raise QuantResearchFactorDiagnosticsError("diagnostic population is empty")
        coverage = tuple(self._coverage(factor_id) for factor_id in QUANT_RESEARCH_FACTOR_ORDER)
        distributions = tuple(
            self._distribution(factor_id) for factor_id in QUANT_RESEARCH_FACTOR_ORDER
        )
        concentration = tuple(
            self._concentration(factor_id, axis)
            for factor_id in QUANT_RESEARCH_FACTOR_ORDER
            for axis in QuantResearchFactorConcentrationAxis
        )
        pairwise = tuple(self._pair_report(pair) for pair in QUANT_RESEARCH_FACTOR_PAIR_ORDER)
        duplicate_groups = _near_duplicate_groups(pairwise)
        available_cells = sum(self._available.values())
        expected_cells = self._expected_paths * len(QUANT_RESEARCH_FACTOR_ORDER)
        payload = {
            **self._metadata,
            "catalog_fingerprint": quant_research_factor_catalog_v1().logical_fingerprint,
            "first_session": self._sessions[0],
            "last_session": self._sessions[-1],
            "session_count": len(self._sessions),
            "expected_path_count": self._expected_paths,
            "complete_factor_vector_count": self._complete_vectors,
            "incomplete_factor_vector_count": self._expected_paths - self._complete_vectors,
            "expected_factor_cell_count": expected_cells,
            "available_factor_cell_count": available_cells,
            "unavailable_factor_cell_count": expected_cells - available_cells,
            "factor_coverage": coverage,
            "session_availability": tuple(self._session_availability),
            "distributions": distributions,
            "concentration": concentration,
            "pairwise_same_session_spearman": pairwise,
            "near_duplicate_groups": duplicate_groups,
        }
        provisional = QuantResearchFactorDiagnosticsV1.model_construct(
            **payload,
            logical_fingerprint="0" * 64,
        )
        return QuantResearchFactorDiagnosticsV1.model_validate(
            {
                **payload,
                "logical_fingerprint": factor_diagnostics_fingerprint(provisional),
            }
        )

    def _coverage(self, factor_id: str) -> QuantResearchFactorCoverageV1:
        available = self._available[factor_id]
        unavailable = self._unavailable[factor_id]
        return QuantResearchFactorCoverageV1(
            factor_id=factor_id,
            expected_count=self._expected_paths,
            available_count=available,
            unavailable_count=unavailable,
            availability_rate=_ratio(available, self._expected_paths),
            unavailable_reason_counts=tuple(
                QuantResearchFactorReasonCountV1(reason_code=reason, count=count)
                for reason, count in sorted(self._reasons[factor_id].items())
            ),
        )

    def _distribution(self, factor_id: str) -> QuantResearchFactorDistributionV1:
        values = sorted(self._values[factor_id])
        count = len(values)
        if count == 0:
            return QuantResearchFactorDistributionV1(
                factor_id=factor_id,
                observation_count=0,
                distinct_value_count=0,
                same_session_tie_excess_count=0,
                same_session_tie_excess_rate=ZERO_RENDERED,
                outer_outlier_count=0,
                outer_outlier_rate=ZERO_RENDERED,
            )
        quantiles = {
            name: _linear_quantile(values, probability)
            for name, probability in (
                ("p01", 0.01),
                ("p05", 0.05),
                ("p25", 0.25),
                ("median", 0.50),
                ("p75", 0.75),
                ("p95", 0.95),
                ("p99", 0.99),
            )
        }
        iqr = quantiles["p75"] - quantiles["p25"]
        outer_low = quantiles["p25"] - 3.0 * iqr
        outer_high = quantiles["p75"] + 3.0 * iqr
        outliers = sum(value < outer_low or value > outer_high for value in values)
        distinct = 1 + sum(left != right for left, right in zip(values, values[1:]))
        return QuantResearchFactorDistributionV1(
            factor_id=factor_id,
            observation_count=count,
            distinct_value_count=distinct,
            same_session_tie_excess_count=self._tie_excess[factor_id],
            same_session_tie_excess_rate=_ratio(self._tie_excess[factor_id], count),
            minimum=_render(values[0]),
            maximum=_render(values[-1]),
            outer_fence_low=_render(outer_low),
            outer_fence_high=_render(outer_high),
            outer_outlier_count=outliers,
            outer_outlier_rate=_ratio(outliers, count),
            **{key: _render(value) for key, value in quantiles.items()},
        )

    def _concentration(
        self, factor_id: str, axis: QuantResearchFactorConcentrationAxis
    ) -> QuantResearchFactorConcentrationV1:
        counts = (
            self._session_counts[factor_id]
            if axis is QuantResearchFactorConcentrationAxis.SESSION
            else self._instrument_counts[factor_id]
        )
        ordered = sorted(counts.values(), reverse=True)
        total = sum(ordered)
        maximum = ordered[0] if ordered else 0
        hhi = sum((count / total) ** 2 for count in ordered) if total else 0.0
        return QuantResearchFactorConcentrationV1(
            factor_id=factor_id,
            axis=axis,
            observation_count=total,
            group_count=len(ordered),
            maximum_group_count=maximum,
            maximum_group_share=_ratio(maximum, total),
            top_ten_group_share=_ratio(sum(ordered[:10]), total),
            herfindahl_index=_render(hhi),
        )

    def _append_pair_correlations(
        self, session_values: dict[str, list[tuple[str, float]]]
    ) -> None:
        value_maps = {
            factor_id: dict(values) for factor_id, values in session_values.items()
        }
        instrument_orders = {
            factor_id: tuple(instrument for instrument, _ in values)
            for factor_id, values in session_values.items()
        }
        common_order = instrument_orders[QUANT_RESEARCH_FACTOR_ORDER[0]]
        if (
            len(common_order)
            >= QUANT_RESEARCH_FACTOR_DIAGNOSTICS_MINIMUM_PAIR_OBSERVATIONS
            and all(
                instrument_orders[factor_id] == common_order
                for factor_id in QUANT_RESEARCH_FACTOR_ORDER[1:]
            )
        ):
            ranks = {
                factor_id: _average_ranks([value for _, value in session_values[factor_id]])
                for factor_id in QUANT_RESEARCH_FACTOR_ORDER
            }
            for pair in QUANT_RESEARCH_FACTOR_PAIR_ORDER:
                if len(set(ranks[pair[0]])) < 2 or len(set(ranks[pair[1]])) < 2:
                    continue
                rho = _pearson(ranks[pair[0]], ranks[pair[1]])
                self._pair_session_values[pair].append((rho, len(common_order)))
            return
        for pair in QUANT_RESEARCH_FACTOR_PAIR_ORDER:
            left, right = pair
            common = sorted(set(value_maps[left]) & set(value_maps[right]))
            if len(common) < QUANT_RESEARCH_FACTOR_DIAGNOSTICS_MINIMUM_PAIR_OBSERVATIONS:
                continue
            left_values = [value_maps[left][instrument] for instrument in common]
            right_values = [value_maps[right][instrument] for instrument in common]
            if len(set(left_values)) < 2 or len(set(right_values)) < 2:
                continue
            rho = _spearman(left_values, right_values)
            self._pair_session_values[pair].append((rho, len(common)))

    def _pair_report(
        self, pair: tuple[str, str]
    ) -> QuantResearchFactorPairCorrelationV1:
        values = self._pair_session_values[pair]
        session_count = len(values)
        observation_count = sum(count for _, count in values)
        if not values:
            return QuantResearchFactorPairCorrelationV1(
                left_factor_id=pair[0],
                right_factor_id=pair[1],
                eligible_session_count=0,
                shared_observation_count=0,
                high_absolute_correlation_session_count=0,
                high_absolute_correlation_session_share=ZERO_RENDERED,
                positive_session_count=0,
                negative_session_count=0,
                zero_session_count=0,
                dominant_sign_session_share=ZERO_RENDERED,
                near_duplicate=False,
            )
        correlations = sorted(value for value, _ in values)
        weighted_mean = sum(value * count for value, count in values) / observation_count
        high_count = sum(
            abs(value) >= float(QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_ABSOLUTE_RHO)
            for value, _ in values
        )
        positive = sum(value > 0 for value, _ in values)
        negative = sum(value < 0 for value, _ in values)
        zero = session_count - positive - negative
        high_share = high_count / session_count
        dominant_share = max(positive, negative) / (positive + negative) if positive + negative else 0.0
        near_duplicate = (
            session_count >= QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_MINIMUM_SESSIONS
            and abs(weighted_mean) >= float(QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_ABSOLUTE_RHO)
            and high_share >= float(QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_SESSION_SHARE)
            and dominant_share >= float(QUANT_RESEARCH_FACTOR_NEAR_DUPLICATE_SIGN_SHARE)
        )
        return QuantResearchFactorPairCorrelationV1(
            left_factor_id=pair[0],
            right_factor_id=pair[1],
            eligible_session_count=session_count,
            shared_observation_count=observation_count,
            weighted_mean_spearman=_render(weighted_mean),
            median_session_spearman=_render(_linear_quantile(correlations, 0.50)),
            p05_session_spearman=_render(_linear_quantile(correlations, 0.05)),
            p95_session_spearman=_render(_linear_quantile(correlations, 0.95)),
            high_absolute_correlation_session_count=high_count,
            high_absolute_correlation_session_share=_ratio(high_count, session_count),
            positive_session_count=positive,
            negative_session_count=negative,
            zero_session_count=zero,
            dominant_sign_session_share=_ratio(max(positive, negative), positive + negative),
            near_duplicate=near_duplicate,
        )


def _spearman(left: list[float], right: list[float]) -> float:
    return _pearson(_average_ranks(left), _average_ranks(right))


def _pearson(left_ranks: list[float], right_ranks: list[float]) -> float:
    left_mean = sum(left_ranks) / len(left_ranks)
    right_mean = sum(right_ranks) / len(right_ranks)
    covariance = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_ranks, right_ranks, strict=True)
    )
    left_ss = sum((value - left_mean) ** 2 for value in left_ranks)
    right_ss = sum((value - right_mean) ** 2 for value in right_ranks)
    denominator = math.sqrt(left_ss * right_ss)
    if denominator == 0:
        raise QuantResearchFactorDiagnosticsError("rank correlation denominator is zero")
    return max(-1.0, min(1.0, covariance / denominator))


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


def _linear_quantile(values: list[float], probability: float) -> float:
    if not values:
        raise QuantResearchFactorDiagnosticsError("cannot quantify an empty distribution")
    position = (len(values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def _near_duplicate_groups(
    pairs: tuple[QuantResearchFactorPairCorrelationV1, ...]
) -> tuple[QuantResearchFactorNearDuplicateGroupV1, ...]:
    graph: dict[str, set[str]] = defaultdict(set)
    for item in pairs:
        if item.near_duplicate:
            graph[item.left_factor_id].add(item.right_factor_id)
            graph[item.right_factor_id].add(item.left_factor_id)
    groups = []
    visited = set()
    for factor_id in QUANT_RESEARCH_FACTOR_ORDER:
        if factor_id in visited or factor_id not in graph:
            continue
        stack = [factor_id]
        component = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(graph[current] - component)
        visited.update(component)
        factor_ids = tuple(sorted(component))
        groups.append(
            QuantResearchFactorNearDuplicateGroupV1(
                group_id=hashlib.sha256("\n".join(factor_ids).encode("utf-8")).hexdigest(),
                factor_ids=factor_ids,
            )
        )
    return tuple(sorted(groups, key=lambda item: item.factor_ids))


def _ratio(numerator: int, denominator: int) -> str:
    value = Decimal("0") if denominator == 0 else Decimal(numerator) / Decimal(denominator)
    return _render(value)


def _render(value: Decimal | float) -> str:
    parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    quantized = parsed.quantize(VALUE_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, "f")
