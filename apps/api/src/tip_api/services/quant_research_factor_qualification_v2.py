"""Streaming outcome-blind qualification for Factor Catalog V2."""

from __future__ import annotations

import hashlib
from array import array
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorRoleV2,
    quant_research_factor_catalog_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER,
    QuantResearchFactorConcentrationAxisV2,
    QuantResearchFactorConcentrationV2,
    QuantResearchFactorCoverageV2,
    QuantResearchFactorDistributionV2,
    QuantResearchFactorPairCorrelationV2,
    QuantResearchFactorQualificationDecisionV2,
    QuantResearchFactorQualificationReportV2,
    QuantResearchFactorQualificationV2Decision,
    QuantResearchFactorQualificationV2Status,
    QuantResearchFactorReasonCountV2,
    factor_qualification_v2_fingerprint,
    quant_research_factor_qualification_protocol_v2,
)


FloatArray = NDArray[np.float64]
VALUE_QUANTUM = Decimal("0.0000000001")


class QuantResearchFactorQualificationV2Error(ValueError):
    """Raised when V2 diagnostic inputs violate the frozen protocol."""


class QuantResearchFactorQualificationAccumulatorV2:
    """Accumulate factor values and quality evidence without accepting outcomes."""

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
        first_source_session: date,
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
        if any(
            len(item) != 64 or set(item) - set("0123456789abcdef")
            for item in fingerprints
        ):
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 diagnostic source fingerprint differs"
            )
        if not limitation_codes or limitation_codes != tuple(
            sorted(set(limitation_codes))
        ):
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 diagnostic limitations differ"
            )
        self._metadata = {
            "chronological_plan_fingerprint": chronological_plan_fingerprint,
            "source_population_fingerprint": source_population_fingerprint,
            "source_eod_fingerprint": source_eod_fingerprint,
            "source_membership_fingerprint": source_membership_fingerprint,
            "source_action_fingerprint": source_action_fingerprint,
            "source_adjustment_fingerprint": source_adjustment_fingerprint,
            "calculation_code_sha256": calculation_code_sha256,
            "diagnostic_code_sha256": diagnostic_code_sha256,
            "first_source_session": first_source_session,
            "limitation_codes": limitation_codes,
        }
        self._sessions: list[date] = []
        self._expected_paths = 0
        self._complete_vectors = 0
        self._values = {
            factor_id: array("d") for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        }
        self._available = Counter()
        self._unavailable = Counter()
        self._reasons = {
            factor_id: Counter() for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        }
        self._session_counts = {
            factor_id: [] for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        }
        self._instrument_counts = {
            factor_id: Counter() for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        }
        self._tie_excess = Counter()
        self._pair_session_values: dict[
            tuple[str, str], list[tuple[float, int]]
        ] = {pair: [] for pair in QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER}

    def add_session(
        self,
        *,
        as_of_session: date,
        instrument_ids: tuple[str, ...],
        factor_values: dict[str, FloatArray],
        reason_codes: dict[str, tuple[tuple[str, ...], ...]],
    ) -> None:
        if self._sessions and as_of_session <= self._sessions[-1]:
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 sessions are not strictly ordered"
            )
        if instrument_ids != tuple(sorted(set(instrument_ids))):
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 instruments are not stable-ID ordered"
            )
        if tuple(factor_values) != QUANT_RESEARCH_FACTOR_V2_ORDER or tuple(
            reason_codes
        ) != QUANT_RESEARCH_FACTOR_V2_ORDER:
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 factor order differs"
            )
        count = len(instrument_ids)
        normalized: dict[str, FloatArray] = {}
        availability_masks: dict[str, NDArray[np.bool_]] = {}
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
            values = np.asarray(factor_values[factor_id], dtype=np.float64)
            reasons = reason_codes[factor_id]
            if values.shape != (count,) or len(reasons) != count:
                raise QuantResearchFactorQualificationV2Error(
                    "Factor Catalog V2 session shape differs"
                )
            available = np.isfinite(values)
            if any(
                bool(available[index]) == bool(reasons[index])
                for index in range(count)
            ):
                raise QuantResearchFactorQualificationV2Error(
                    "Factor Catalog V2 availability and reason differ"
                )
            quantized = np.round(values, decimals=10)
            normalized[factor_id] = quantized
            availability_masks[factor_id] = available

        self._sessions.append(as_of_session)
        self._expected_paths += count
        complete = np.logical_and.reduce(
            tuple(availability_masks[factor_id] for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER)
        )
        self._complete_vectors += int(complete.sum())
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
            values = normalized[factor_id]
            available = availability_masks[factor_id]
            available_values = values[available]
            available_count = int(available.sum())
            unavailable_count = count - available_count
            self._available[factor_id] += available_count
            self._unavailable[factor_id] += unavailable_count
            self._values[factor_id].extend(float(item) for item in available_values)
            self._session_counts[factor_id].append(available_count)
            if available_count:
                self._tie_excess[factor_id] += available_count - int(
                    np.unique(available_values).size
                )
            for instrument, is_available in zip(instrument_ids, available):
                if bool(is_available):
                    self._instrument_counts[factor_id][instrument] += 1
            for row_reasons in reason_codes[factor_id]:
                if row_reasons != tuple(sorted(set(row_reasons))):
                    raise QuantResearchFactorQualificationV2Error(
                        "Factor Catalog V2 reason order differs"
                    )
                for reason in row_reasons:
                    self._reasons[factor_id][reason] += 1
        self._append_pair_correlations(normalized, availability_masks)

    def build(self) -> QuantResearchFactorQualificationReportV2:
        protocol = quant_research_factor_qualification_protocol_v2()
        if len(self._sessions) != protocol.expected_signal_session_count:
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 signal-session count differs"
            )
        if self._expected_paths != protocol.expected_signal_path_count:
            raise QuantResearchFactorQualificationV2Error(
                "Factor Catalog V2 expected path count differs"
            )
        coverage = tuple(
            self._coverage(factor_id) for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        )
        distributions = tuple(
            self._distribution(factor_id)
            for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        )
        concentration = tuple(
            self._concentration(factor_id, axis)
            for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
            for axis in QuantResearchFactorConcentrationAxisV2
        )
        pairwise = tuple(
            self._pair_report(pair) for pair in QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER
        )
        decisions, cross_group_pairs = _qualification_decisions(
            coverage=coverage,
            distributions=distributions,
            pairwise=pairwise,
        )
        role_counts = {
            role: sum(
                item.role is role
                and item.decision
                is QuantResearchFactorQualificationV2Decision.ELIGIBLE_FOR_SCREENING_PROTOCOL_REVIEW
                for item in decisions
            )
            for role in QuantResearchFactorRoleV2
        }
        ready = (
            role_counts[QuantResearchFactorRoleV2.CANDIDATE_ALPHA]
            >= protocol.minimum_candidate_alpha_factors_after_redundancy
            and not cross_group_pairs
        )
        if cross_group_pairs:
            status = (
                QuantResearchFactorQualificationV2Status
                .REQUIRES_OUTCOME_BLIND_REDUNDANCY_ADJUDICATION
            )
        elif ready:
            status = (
                QuantResearchFactorQualificationV2Status
                .READY_FOR_SCREENING_PROTOCOL_REVIEW
            )
        else:
            status = (
                QuantResearchFactorQualificationV2Status
                .REJECTED_DATA_OR_IMPLEMENTATION
            )
        expected_cells = self._expected_paths * len(QUANT_RESEARCH_FACTOR_V2_ORDER)
        available_cells = sum(self._available.values())
        payload = {
            **self._metadata,
            "protocol_fingerprint": protocol.logical_fingerprint,
            "catalog_fingerprint": protocol.catalog_fingerprint,
            "prior_discovery_ledger_fingerprint": (
                protocol.prior_discovery_ledger_fingerprint
            ),
            "first_signal_session": self._sessions[0],
            "last_signal_session": self._sessions[-1],
            "signal_session_count": len(self._sessions),
            "expected_path_count": self._expected_paths,
            "complete_factor_vector_count": self._complete_vectors,
            "incomplete_factor_vector_count": (
                self._expected_paths - self._complete_vectors
            ),
            "expected_factor_cell_count": expected_cells,
            "available_factor_cell_count": available_cells,
            "unavailable_factor_cell_count": expected_cells - available_cells,
            "factor_coverage": coverage,
            "distributions": distributions,
            "concentration": concentration,
            "pairwise_same_session_spearman": pairwise,
            "decisions": decisions,
            "eligible_candidate_alpha_count": role_counts[
                QuantResearchFactorRoleV2.CANDIDATE_ALPHA
            ],
            "eligible_setup_conditioner_count": role_counts[
                QuantResearchFactorRoleV2.SETUP_CONDITIONER
            ],
            "eligible_applicability_input_count": role_counts[
                QuantResearchFactorRoleV2.APPLICABILITY_INPUT
            ],
            "eligible_risk_guard_count": role_counts[
                QuantResearchFactorRoleV2.RISK_GUARD
            ],
            "cross_group_near_duplicate_pairs": cross_group_pairs,
            "status": status,
        }
        provisional = QuantResearchFactorQualificationReportV2.model_construct(
            **payload,
            logical_fingerprint="0" * 64,
        )
        return QuantResearchFactorQualificationReportV2.model_validate(
            {
                **payload,
                "logical_fingerprint": factor_qualification_v2_fingerprint(
                    provisional
                ),
            }
        )

    def _coverage(self, factor_id: str) -> QuantResearchFactorCoverageV2:
        counts = self._session_counts[factor_id]
        split = len(counts) // 2
        minimum = (
            quant_research_factor_qualification_protocol_v2()
            .minimum_instruments_per_eligible_session
        )
        eligible = [count >= minimum for count in counts]
        available = self._available[factor_id]
        return QuantResearchFactorCoverageV2(
            factor_id=factor_id,
            expected_count=self._expected_paths,
            available_count=available,
            unavailable_count=self._unavailable[factor_id],
            availability_rate=_ratio(available, self._expected_paths),
            eligible_session_count=sum(eligible),
            first_half_eligible_session_count=sum(eligible[:split]),
            second_half_eligible_session_count=sum(eligible[split:]),
            unavailable_reason_counts=tuple(
                QuantResearchFactorReasonCountV2(reason_code=reason, count=count)
                for reason, count in sorted(self._reasons[factor_id].items())
            ),
        )

    def _distribution(self, factor_id: str) -> QuantResearchFactorDistributionV2:
        values = np.sort(np.asarray(self._values[factor_id], dtype=np.float64))
        count = int(values.size)
        ties = self._tie_excess[factor_id]
        if count == 0:
            return QuantResearchFactorDistributionV2(
                factor_id=factor_id,
                observation_count=0,
                distinct_value_count=0,
                same_session_tie_excess_count=0,
                same_session_tie_excess_rate=_ratio(0, 0),
                outer_outlier_count=0,
                outer_outlier_rate=_ratio(0, 0),
            )
        quantiles = np.quantile(
            values,
            (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99),
            method="linear",
        )
        iqr = float(quantiles[4] - quantiles[2])
        lower = float(quantiles[2]) - 3.0 * iqr
        upper = float(quantiles[4]) + 3.0 * iqr
        outliers = int(np.logical_or(values < lower, values > upper).sum())
        return QuantResearchFactorDistributionV2(
            factor_id=factor_id,
            observation_count=count,
            distinct_value_count=int(np.unique(values).size),
            same_session_tie_excess_count=ties,
            same_session_tie_excess_rate=_ratio(ties, count),
            minimum=_render(float(values[0])),
            p01=_render(float(quantiles[0])),
            p05=_render(float(quantiles[1])),
            p25=_render(float(quantiles[2])),
            median=_render(float(quantiles[3])),
            p75=_render(float(quantiles[4])),
            p95=_render(float(quantiles[5])),
            p99=_render(float(quantiles[6])),
            maximum=_render(float(values[-1])),
            outer_outlier_count=outliers,
            outer_outlier_rate=_ratio(outliers, count),
        )

    def _concentration(
        self, factor_id: str, axis: QuantResearchFactorConcentrationAxisV2
    ) -> QuantResearchFactorConcentrationV2:
        counts = (
            self._session_counts[factor_id]
            if axis is QuantResearchFactorConcentrationAxisV2.SESSION
            else self._instrument_counts[factor_id].values()
        )
        ordered = sorted((int(item) for item in counts if item), reverse=True)
        total = sum(ordered)
        maximum = ordered[0] if ordered else 0
        hhi = sum((count / total) ** 2 for count in ordered) if total else 0.0
        return QuantResearchFactorConcentrationV2(
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
        self,
        values: dict[str, FloatArray],
        masks: dict[str, NDArray[np.bool_]],
    ) -> None:
        minimum = (
            quant_research_factor_qualification_protocol_v2()
            .pair_minimum_observations_per_session
        )
        for pair in QUANT_RESEARCH_FACTOR_V2_PAIR_ORDER:
            common = np.logical_and(masks[pair[0]], masks[pair[1]])
            count = int(common.sum())
            if count < minimum:
                continue
            left = values[pair[0]][common]
            right = values[pair[1]][common]
            if np.unique(left).size < 2 or np.unique(right).size < 2:
                continue
            rho = _pearson(_average_ranks(left), _average_ranks(right))
            self._pair_session_values[pair].append((rho, count))

    def _pair_report(
        self, pair: tuple[str, str]
    ) -> QuantResearchFactorPairCorrelationV2:
        protocol = quant_research_factor_qualification_protocol_v2()
        observations = self._pair_session_values[pair]
        if not observations:
            return QuantResearchFactorPairCorrelationV2(
                left_factor_id=pair[0],
                right_factor_id=pair[1],
                eligible_session_count=0,
                shared_observation_count=0,
                high_absolute_correlation_session_count=0,
                high_absolute_correlation_session_share=_ratio(0, 0),
                positive_session_count=0,
                negative_session_count=0,
                zero_session_count=0,
                dominant_sign_session_share=_ratio(0, 0),
                near_duplicate=False,
            )
        correlations = np.asarray([item[0] for item in observations])
        weights = np.asarray([item[1] for item in observations])
        threshold = float(protocol.near_duplicate_absolute_spearman)
        high = int((np.abs(correlations) >= threshold).sum())
        positive = int((correlations > 0).sum())
        negative = int((correlations < 0).sum())
        zero = len(observations) - positive - negative
        nonzero = positive + negative
        high_share = high / len(observations)
        sign_share = max(positive, negative) / nonzero if nonzero else 0.0
        near_duplicate = (
            len(observations) >= protocol.near_duplicate_minimum_sessions
            and high_share >= float(protocol.near_duplicate_session_share)
            and sign_share >= float(protocol.near_duplicate_dominant_sign_share)
        )
        quantiles = np.quantile(correlations, (0.05, 0.50, 0.95), method="linear")
        return QuantResearchFactorPairCorrelationV2(
            left_factor_id=pair[0],
            right_factor_id=pair[1],
            eligible_session_count=len(observations),
            shared_observation_count=int(weights.sum()),
            weighted_mean_spearman=_render(
                float(np.average(correlations, weights=weights))
            ),
            median_session_spearman=_render(float(quantiles[1])),
            p05_session_spearman=_render(float(quantiles[0])),
            p95_session_spearman=_render(float(quantiles[2])),
            high_absolute_correlation_session_count=high,
            high_absolute_correlation_session_share=_ratio(
                high, len(observations)
            ),
            positive_session_count=positive,
            negative_session_count=negative,
            zero_session_count=zero,
            dominant_sign_session_share=_ratio(max(positive, negative), nonzero),
            near_duplicate=near_duplicate,
        )


def _qualification_decisions(
    *,
    coverage: tuple[QuantResearchFactorCoverageV2, ...],
    distributions: tuple[QuantResearchFactorDistributionV2, ...],
    pairwise: tuple[QuantResearchFactorPairCorrelationV2, ...],
) -> tuple[
    tuple[QuantResearchFactorQualificationDecisionV2, ...],
    tuple[tuple[str, str], ...],
]:
    protocol = quant_research_factor_qualification_protocol_v2()
    catalog = quant_research_factor_catalog_v2()
    definitions = {item.factor_id: item for item in catalog.definitions}
    coverage_by_id = {item.factor_id: item for item in coverage}
    distributions_by_id = {item.factor_id: item for item in distributions}
    duplicate_of: dict[str, str] = {}
    cross_group = []
    for pair in pairwise:
        if not pair.near_duplicate:
            continue
        left = definitions[pair.left_factor_id]
        right = definitions[pair.right_factor_id]
        if left.related_factor_group != right.related_factor_group:
            cross_group.append((left.factor_id, right.factor_id))
            continue
        higher_priority, lower_priority = sorted(
            (left, right), key=lambda item: (item.redundancy_priority, item.factor_id)
        )
        duplicate_of[lower_priority.factor_id] = higher_priority.factor_id

    decisions = []
    for definition in catalog.definitions:
        current_coverage = coverage_by_id[definition.factor_id]
        distribution = distributions_by_id[definition.factor_id]
        reasons = []
        if Decimal(current_coverage.availability_rate) < Decimal(
            protocol.minimum_factor_availability_rate
        ):
            reasons.append("availability_below_floor")
        if (
            current_coverage.eligible_session_count
            < protocol.minimum_factor_eligible_session_count
        ):
            reasons.append("eligible_sessions_below_floor")
        if (
            current_coverage.first_half_eligible_session_count
            < protocol.minimum_factor_first_half_session_count
        ):
            reasons.append("first_half_sessions_below_floor")
        if (
            current_coverage.second_half_eligible_session_count
            < protocol.minimum_factor_second_half_session_count
        ):
            reasons.append("second_half_sessions_below_floor")
        if distribution.distinct_value_count < protocol.minimum_distinct_factor_values:
            reasons.append("distinct_values_below_floor")
        if Decimal(distribution.same_session_tie_excess_rate) > Decimal(
            protocol.maximum_same_session_tie_excess_rate
        ):
            reasons.append("same_session_ties_above_ceiling")
        prior = duplicate_of.get(definition.factor_id)
        if prior is not None:
            reasons.append("lower_priority_within_group_near_duplicate")
        reason_codes = tuple(sorted(set(reasons)))
        decisions.append(
            QuantResearchFactorQualificationDecisionV2(
                factor_id=definition.factor_id,
                role=definition.role,
                decision=(
                    QuantResearchFactorQualificationV2Decision.REJECTED_QUALIFICATION
                    if reason_codes
                    else (
                        QuantResearchFactorQualificationV2Decision
                        .ELIGIBLE_FOR_SCREENING_PROTOCOL_REVIEW
                    )
                ),
                reason_codes=reason_codes,
                lower_priority_near_duplicate_of=prior,
            )
        )
    return tuple(decisions), tuple(sorted(set(cross_group)))


def _average_ranks(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    sorted_ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        sorted_ranks[start:end] = (start + 1 + end) / 2.0
        start = end
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = sorted_ranks
    return ranks


def _pearson(left: FloatArray, right: FloatArray) -> float:
    left_centered = left - left.mean()
    right_centered = right - right.mean()
    denominator = float(
        np.sqrt(np.square(left_centered).sum() * np.square(right_centered).sum())
    )
    if denominator == 0.0:
        raise QuantResearchFactorQualificationV2Error(
            "Factor Catalog V2 rank variance is zero"
        )
    return float((left_centered * right_centered).sum() / denominator)


def _ratio(numerator: int, denominator: int) -> str:
    value = (
        Decimal("0")
        if denominator == 0
        else Decimal(numerator) / Decimal(denominator)
    )
    return _render(value)


def _render(value: float | Decimal) -> str:
    parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    quantized = parsed.quantize(VALUE_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, "f")


def combined_code_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for raw_path in sorted(paths, key=lambda item: str(item)):
        payload = raw_path.read_bytes()
        digest.update(raw_path.name.encode("utf-8"))
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()
