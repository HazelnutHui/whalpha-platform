"""Deterministic Development-only screening statistics for Factor Catalog V1."""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from random import Random
from statistics import mean

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QuantResearchFactorAvailability,
    QuantResearchFactorExpectedRelationship,
    QuantResearchFactorObservationV1,
    QuantResearchFactorRole,
    quant_research_factor_catalog_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening import (
    QuantResearchFactorScreeningHypothesisV1,
    QuantResearchFactorScreeningTarget,
    quant_research_factor_screening_protocol_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningCostDiagnosticV1,
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
    QuantResearchFactorScreeningHorizonResultV1,
    QuantResearchFactorScreeningLabelState,
    QuantResearchFactorScreeningLabelV1,
    QuantResearchFactorScreeningReportStatus,
    build_factor_screening_decision,
    build_factor_screening_horizon_result,
    build_factor_screening_report,
)


_NUMERIC_ALPHA_STATES = {
    QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT,
    QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_EXACT,
    QuantResearchFactorScreeningLabelState.TERMINAL_REFERENCE_INTERVAL,
}
_QUANTUM = Decimal("0.0000000001")


class QuantResearchFactorScreeningError(ValueError):
    """Raised when frozen screening inputs or statistics do not reconcile."""


def build_quant_research_factor_screening_report(
    *,
    observations: tuple[QuantResearchFactorObservationV1, ...],
    labels: tuple[QuantResearchFactorScreeningLabelV1, ...],
    implementation_revision: str,
    created_at: datetime,
    source_eod_fingerprint: str,
    source_membership_fingerprint: str,
    source_action_fingerprint: str,
    source_adjustment_fingerprint: str,
    factor_calculation_code_sha256: str,
    label_code_sha256: str,
    screening_code_sha256: str,
):
    """Calculate the single frozen factor screen without model authority."""

    protocol = quant_research_factor_screening_protocol_v1()
    ordered, labels_by_observation = _validated_inputs(observations, labels)
    results = tuple(
        _build_horizon_result(
            hypothesis=hypothesis,
            horizon=horizon,
            endpoint=endpoint,
            observations=ordered,
            labels_by_observation=labels_by_observation,
        )
        for hypothesis in protocol.formal_hypotheses
        for horizon in (1, 3, 5)
        for endpoint in (
            (QuantResearchFactorScreeningEndpoint.LOWER,
             QuantResearchFactorScreeningEndpoint.UPPER)
            if hypothesis.role is QuantResearchFactorRole.CANDIDATE_ALPHA
            else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
        )
    )
    decisions, selected = _build_decisions(results)
    selected_alpha = any(
        item.selected_for_model_candidate_set
        and item.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        for item in decisions
    )
    any_alpha_inconclusive = any(
        item.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        and item.status is QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA
        for item in decisions
    )
    if selected_alpha:
        report_status = (
            QuantResearchFactorScreeningReportStatus.READY_FOR_MODEL_PROTOCOL_REVIEW
        )
        report_reasons = ("at_least_one_candidate_alpha_selected",)
    elif any_alpha_inconclusive:
        report_status = QuantResearchFactorScreeningReportStatus.INCONCLUSIVE_DATA
        report_reasons = ("candidate_alpha_screen_has_inconclusive_data",)
    else:
        report_status = QuantResearchFactorScreeningReportStatus.CLOSED_NO_CANDIDATE_ALPHA
        report_reasons = ("no_candidate_alpha_passed_frozen_screen",)
    state_counts = Counter(item.state.value for item in labels)
    catalog = quant_research_factor_catalog_v1()
    conditioners = tuple(
        item.factor_id
        for item in catalog.definitions
        if item.role is QuantResearchFactorRole.SETUP_CONDITIONER
    )
    return build_factor_screening_report(
        implementation_revision=implementation_revision,
        created_at=created_at,
        protocol_fingerprint=protocol.logical_fingerprint,
        source_diagnostics_fingerprint=protocol.source_diagnostics_fingerprint,
        source_diagnostics_sha256=protocol.source_diagnostics_sha256,
        source_eod_fingerprint=source_eod_fingerprint,
        source_membership_fingerprint=source_membership_fingerprint,
        source_action_fingerprint=source_action_fingerprint,
        source_adjustment_fingerprint=source_adjustment_fingerprint,
        factor_calculation_code_sha256=factor_calculation_code_sha256,
        label_code_sha256=label_code_sha256,
        screening_code_sha256=screening_code_sha256,
        first_signal_session=ordered[0].as_of_session,
        last_signal_session=ordered[-1].as_of_session,
        signal_session_count=len({item.as_of_session for item in ordered}),
        observation_count=len(ordered),
        label_count=len(labels),
        label_state_counts={
            state.value: state_counts.get(state.value, 0)
            for state in QuantResearchFactorScreeningLabelState
        },
        results=results,
        decisions=decisions,
        setup_conditioner_factor_ids=conditioners,
        selected_factor_ids=selected,
        status=report_status,
        reason_codes=report_reasons,
        limitation_codes=(
            "fixed_costs_not_execution_calibrated",
            "historical_classification_unavailable",
            "historical_regime_diversity_not_proven",
            "reconstructed_membership_not_as_operated",
            "split_neutral_absence_unproven",
            "temporal_coverage_limited_to_106_development_sessions",
        ),
    )


def calculate_average_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    if not values or any(not math.isfinite(item) for item in values):
        raise QuantResearchFactorScreeningError("average ranks require finite values")
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        value = values[ordered[position]]
        while end < len(ordered) and values[ordered[end]] == value:
            end += 1
        average_rank = ((position + 1) + end) / 2.0
        for offset in range(position, end):
            ranks[ordered[offset]] = average_rank
        position = end
    return tuple(ranks)


def calculate_spearman(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise QuantResearchFactorScreeningError(
            "Spearman inputs must have equal nontrivial length"
        )
    return _pearson(calculate_average_ranks(left), calculate_average_ranks(right))


def calculate_partial_spearman(
    factor: tuple[float, ...], target: tuple[float, ...], baseline: tuple[float, ...]
) -> float:
    if len(factor) != len(target) or len(factor) != len(baseline) or len(factor) < 3:
        raise QuantResearchFactorScreeningError(
            "partial Spearman inputs must have equal nontrivial length"
        )
    x = calculate_average_ranks(factor)
    y = calculate_average_ranks(target)
    z = calculate_average_ranks(baseline)
    x_residual = _linear_residual(x, z)
    y_residual = _linear_residual(y, z)
    return _pearson(x_residual, y_residual)


def calculate_holm_adjustment(raw_probabilities: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw_probabilities.items(), key=lambda item: (item[1], item[0]))
    adjusted = {}
    floor = 0.0
    size = len(ordered)
    for offset, (identifier, probability) in enumerate(ordered):
        if not 0 <= probability <= 1:
            raise QuantResearchFactorScreeningError("Holm probability is outside [0,1]")
        floor = max(floor, min(1.0, probability * (size - offset)))
        adjusted[identifier] = floor
    return adjusted


def calculate_block_bootstrap(
    values: tuple[float, ...], *, seed_material: str
) -> tuple[float, float, float]:
    protocol = quant_research_factor_screening_protocol_v1()
    if not values or not seed_material or any(not math.isfinite(item) for item in values):
        raise QuantResearchFactorScreeningError(
            "screening bootstrap requires finite values and seed material"
        )
    count = len(values)
    block = min(protocol.bootstrap_block_sessions, count)
    observed = mean(values)
    centered = tuple(item - observed for item in values)
    seed = int.from_bytes(
        hashlib.sha256(
            (seed_material + ":" + ",".join(_string(item) for item in values)).encode()
        ).digest()[:8],
        "big",
    )
    generator = Random(seed)
    sample_means = []
    null_exceedances = 0
    for _ in range(protocol.bootstrap_replicates):
        indices = []
        while len(indices) < count:
            start = generator.randrange(count)
            indices.extend((start + offset) % count for offset in range(block))
        indices = indices[:count]
        sample_means.append(mean(values[index] for index in indices))
        if mean(centered[index] for index in indices) >= observed:
            null_exceedances += 1
    sample_means.sort()
    return (
        _quantile(sample_means, 0.05),
        _quantile(sample_means, 0.95),
        (null_exceedances + 1) / (protocol.bootstrap_replicates + 1),
    )


def _validated_inputs(observations, labels):
    protocol = quant_research_factor_screening_protocol_v1()
    ordered = tuple(sorted(observations, key=lambda item: (item.as_of_session, str(item.instrument_id))))
    if (
        ordered != observations
        or len(ordered) != protocol.development_expected_path_count
        or len({item.as_of_session for item in ordered})
        != protocol.development_eligible_session_count
        or ordered[0].as_of_session != protocol.first_development_signal_session
        or ordered[-1].as_of_session != protocol.last_development_signal_session
    ):
        raise QuantResearchFactorScreeningError("screening observation population differs")
    observation_map = {item.logical_fingerprint: item for item in ordered}
    if len(observation_map) != len(ordered) or any(
        item.catalog_fingerprint != protocol.catalog_fingerprint
        or any(
            value.availability is not QuantResearchFactorAvailability.AVAILABLE
            for value in item.factor_values
        )
        for item in ordered
    ):
        raise QuantResearchFactorScreeningError("screening observations are not complete")
    by_observation = defaultdict(dict)
    for label in labels:
        observation = observation_map.get(label.observation_fingerprint)
        if (
            observation is None
            or label.signal_session != observation.as_of_session
            or label.instrument_id != observation.instrument_id
            or label.horizon_sessions in by_observation[label.observation_fingerprint]
        ):
            raise QuantResearchFactorScreeningError("screening-label binding differs")
        by_observation[label.observation_fingerprint][label.horizon_sessions] = label
    if len(labels) != len(ordered) * 3 or any(
        set(by_observation[item.logical_fingerprint]) != {1, 3, 5}
        for item in ordered
    ):
        raise QuantResearchFactorScreeningError("screening-label population differs")
    return ordered, by_observation


def _build_horizon_result(
    *, hypothesis, horizon, endpoint, observations, labels_by_observation
):
    protocol = quant_research_factor_screening_protocol_v1()
    rows_by_session = defaultdict(list)
    state_counts = Counter()
    for observation in observations:
        label = labels_by_observation[observation.logical_fingerprint][horizon]
        state_counts[label.state.value] += 1
        target = _target_value(hypothesis, label, endpoint)
        if target is None:
            continue
        values = {item.factor_id: item for item in observation.factor_values}
        factor = float(values[hypothesis.factor_id].value)
        if hypothesis.expected_relationship is QuantResearchFactorExpectedRelationship.NEGATIVE_MONOTONIC:
            factor = -factor
        baseline = float(values[protocol.incremental_baseline_factor_id].value)
        rows_by_session[observation.as_of_session].append(
            (str(observation.instrument_id), factor, baseline, target)
        )
    daily = []
    daily_partial = []
    bucket_sessions = []
    numeric_count = sum(len(items) for items in rows_by_session.values())
    for session in sorted(rows_by_session):
        rows = sorted(rows_by_session[session])
        if len(rows) < protocol.minimum_instruments_per_session:
            continue
        factors = tuple(item[1] for item in rows)
        baselines = tuple(item[2] for item in rows)
        targets = tuple(item[3] for item in rows)
        try:
            rank_ic = calculate_spearman(factors, targets)
        except QuantResearchFactorScreeningError:
            continue
        daily.append((session, rank_ic))
        if hypothesis.partial_rank_ic_baseline_factor_id is not None:
            try:
                partial = calculate_partial_spearman(factors, targets, baselines)
            except QuantResearchFactorScreeningError:
                partial = None
            if partial is not None:
                daily_partial.append((session, partial))
        buckets = _session_buckets(factors, targets)
        if buckets is not None:
            bucket_sessions.append((session, buckets))
    reasons = []
    if len(daily) < protocol.minimum_primary_sessions:
        reasons.append("eligible_session_floor_not_met")
    if len(daily) < 2:
        return _empty_result(
            hypothesis=hypothesis,
            horizon=horizon,
            endpoint=endpoint,
            assigned=len(observations),
            numeric=numeric_count,
            state_counts=state_counts,
            reasons=tuple(sorted(reasons or ["rank_ic_unavailable"])),
        )
    values = tuple(item[1] for item in daily)
    lower, upper, probability = calculate_block_bootstrap(
        values,
        seed_material=(
            f"{protocol.logical_fingerprint}:{hypothesis.factor_id}:{horizon}:"
            f"{endpoint.value}:standalone"
        ),
    )
    midpoint = len(daily) // 2
    first = tuple(item[1] for item in daily[:midpoint])
    second = tuple(item[1] for item in daily[midpoint:])
    partial_values = tuple(item[1] for item in daily_partial)
    if hypothesis.partial_rank_ic_baseline_factor_id is not None and partial_values:
        partial_lower, partial_upper, partial_probability = calculate_block_bootstrap(
            partial_values,
            seed_material=(
                f"{protocol.logical_fingerprint}:{hypothesis.factor_id}:{horizon}:"
                f"{endpoint.value}:partial"
            ),
        )
    else:
        partial_lower = partial_upper = partial_probability = None
        if hypothesis.partial_rank_ic_baseline_factor_id is not None:
            reasons.append("partial_rank_ic_unavailable")
    bucket_means = tuple(
        mean(buckets[index] for _, buckets in bucket_sessions)
        for index in range(protocol.bucket_count)
    ) if bucket_sessions else ()
    bucket_rho = (
        calculate_spearman(tuple(range(1, 6)), bucket_means)
        if bucket_means
        else None
    )
    spread = bucket_means[-1] - bucket_means[0] if bucket_means else None
    costs = (
        tuple(
            QuantResearchFactorScreeningCostDiagnosticV1(
                basis_points_per_side=bps,
                quintile_long_short_spread_net=_string(
                    spread - 4 * bps / 10000
                ),
            )
            for bps in protocol.cost_scenarios_bps_per_side
        )
        if hypothesis.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        and spread is not None
        else ()
    )
    return build_factor_screening_horizon_result(
        factor_id=hypothesis.factor_id,
        role=hypothesis.role,
        target=hypothesis.target,
        horizon_sessions=horizon,
        endpoint=endpoint,
        assigned_path_count=len(observations),
        numeric_path_count=numeric_count,
        label_state_counts={
            state.value: state_counts.get(state.value, 0)
            for state in QuantResearchFactorScreeningLabelState
        },
        eligible_session_count=len(daily),
        mean_rank_ic=_string(mean(values)),
        rank_ic_lower_90pct=_string(lower),
        rank_ic_upper_90pct=_string(upper),
        one_sided_raw_p_value=_string(probability),
        positive_session_share=_string(sum(item > 0 for item in values) / len(values)),
        largest_absolute_session_contribution_share=_string(
            max(abs(item) for item in values) / sum(abs(item) for item in values)
            if any(item != 0 for item in values)
            else 0
        ),
        first_half_session_count=len(first),
        first_half_mean_rank_ic=_string(mean(first)),
        second_half_session_count=len(second),
        second_half_mean_rank_ic=_string(mean(second)),
        mean_partial_rank_ic=(
            _string(mean(partial_values)) if partial_values else None
        ),
        partial_eligible_session_count=len(partial_values),
        partial_rank_ic_lower_90pct=(
            _string(partial_lower) if partial_lower is not None else None
        ),
        partial_rank_ic_upper_90pct=(
            _string(partial_upper) if partial_upper is not None else None
        ),
        partial_one_sided_raw_p_value=(
            _string(partial_probability) if partial_probability is not None else None
        ),
        bucket_session_count=len(bucket_sessions),
        bucket_target_means=tuple(_string(item) for item in bucket_means),
        bucket_monotonic_spearman=(
            _string(bucket_rho) if bucket_rho is not None else None
        ),
        bucket_top_minus_bottom=(
            _string(spread) if spread is not None else None
        ),
        cost_diagnostics=costs,
        reason_codes=tuple(sorted(reasons)),
    )


def _target_value(hypothesis, label, endpoint):
    if hypothesis.target is QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN:
        if label.state not in _NUMERIC_ALPHA_STATES:
            return None
        value = (
            label.relative_to_benchmark_return_lower
            if endpoint is QuantResearchFactorScreeningEndpoint.LOWER
            else label.relative_to_benchmark_return_upper
        )
        return float(value)
    if (
        endpoint is not QuantResearchFactorScreeningEndpoint.COMPLETE_PATH
        or label.maximum_adverse_excursion is None
    ):
        return None
    return float(label.maximum_adverse_excursion)


def _session_buckets(factors, targets):
    ranks = calculate_average_ranks(factors)
    size = len(ranks)
    buckets = [[] for _ in range(5)]
    for rank, target in zip(ranks, targets, strict=True):
        bucket = min(4, int((rank - 1) * 5 / size))
        buckets[bucket].append(target)
    if any(not items for items in buckets):
        return None
    return tuple(mean(items) for items in buckets)


def _empty_result(*, hypothesis, horizon, endpoint, assigned, numeric, state_counts, reasons):
    return build_factor_screening_horizon_result(
        factor_id=hypothesis.factor_id,
        role=hypothesis.role,
        target=hypothesis.target,
        horizon_sessions=horizon,
        endpoint=endpoint,
        assigned_path_count=assigned,
        numeric_path_count=numeric,
        label_state_counts={
            state.value: state_counts.get(state.value, 0)
            for state in QuantResearchFactorScreeningLabelState
        },
        eligible_session_count=0,
        mean_rank_ic=None,
        rank_ic_lower_90pct=None,
        rank_ic_upper_90pct=None,
        one_sided_raw_p_value=None,
        positive_session_share=None,
        largest_absolute_session_contribution_share=None,
        first_half_session_count=0,
        first_half_mean_rank_ic=None,
        second_half_session_count=0,
        second_half_mean_rank_ic=None,
        mean_partial_rank_ic=None,
        partial_eligible_session_count=0,
        partial_rank_ic_lower_90pct=None,
        partial_rank_ic_upper_90pct=None,
        partial_one_sided_raw_p_value=None,
        bucket_session_count=0,
        bucket_target_means=(),
        bucket_monotonic_spearman=None,
        bucket_top_minus_bottom=None,
        cost_diagnostics=(),
        reason_codes=reasons,
    )


def _build_decisions(results):
    protocol = quant_research_factor_screening_protocol_v1()
    by_factor = defaultdict(list)
    for item in results:
        by_factor[item.factor_id].append(item)
    provisional = {}
    raw_by_role = defaultdict(dict)
    for hypothesis in protocol.formal_hypotheses:
        items = by_factor[hypothesis.factor_id]
        primary = [item for item in items if item.horizon_sessions == 3]
        decay = [item for item in items if item.horizon_sessions in {1, 5}]
        data_inconclusive = any(
            item.eligible_session_count < protocol.minimum_primary_sessions
            or item.first_half_session_count < protocol.minimum_chronological_half_sessions
            or item.second_half_session_count < protocol.minimum_chronological_half_sessions
            or (
                hypothesis.partial_rank_ic_baseline_factor_id is not None
                and item.partial_eligible_session_count
                < protocol.minimum_primary_sessions
            )
            for item in primary
        )
        required_probabilities = [
            float(item.one_sided_raw_p_value)
            for item in primary
            if item.one_sided_raw_p_value is not None
        ]
        required_effects = [
            float(item.mean_rank_ic)
            for item in primary
            if item.mean_rank_ic is not None
        ]
        required_bounds = [
            float(item.rank_ic_lower_90pct)
            for item in primary
            if item.rank_ic_lower_90pct is not None
        ]
        if hypothesis.partial_rank_ic_baseline_factor_id is not None:
            required_probabilities.extend(
                float(item.partial_one_sided_raw_p_value)
                for item in primary
                if item.partial_one_sided_raw_p_value is not None
            )
            required_effects.extend(
                float(item.mean_partial_rank_ic)
                for item in primary
                if item.mean_partial_rank_ic is not None
            )
            required_bounds.extend(
                float(item.partial_rank_ic_lower_90pct)
                for item in primary
                if item.partial_rank_ic_lower_90pct is not None
            )
        raw = max(required_probabilities) if required_probabilities else None
        effect = min(required_effects) if required_effects else None
        bound = min(required_bounds) if required_bounds else None
        failures = set()
        for item in primary:
            if item.mean_rank_ic is None or float(item.mean_rank_ic) < float(protocol.minimum_primary_mean_rank_ic):
                failures.add("primary_mean_rank_ic")
            if item.rank_ic_lower_90pct is None or float(item.rank_ic_lower_90pct) <= 0:
                failures.add("primary_rank_ic_lower_bound")
            if item.positive_session_share is None or float(item.positive_session_share) < float(protocol.minimum_positive_session_share):
                failures.add("positive_session_share")
            if item.largest_absolute_session_contribution_share is None or float(item.largest_absolute_session_contribution_share) > float(protocol.maximum_absolute_session_contribution_share):
                failures.add("session_contribution_concentration")
            if item.first_half_mean_rank_ic is None or float(item.first_half_mean_rank_ic) <= 0:
                failures.add("first_half_direction")
            if item.second_half_mean_rank_ic is None or float(item.second_half_mean_rank_ic) <= 0:
                failures.add("second_half_direction")
            if item.bucket_monotonic_spearman is None or float(item.bucket_monotonic_spearman) < float(protocol.minimum_bucket_monotonic_spearman):
                failures.add("bucket_monotonicity")
            if item.bucket_top_minus_bottom is None or float(item.bucket_top_minus_bottom) <= 0:
                failures.add("bucket_top_minus_bottom")
            if hypothesis.partial_rank_ic_baseline_factor_id is not None:
                if item.mean_partial_rank_ic is None or float(item.mean_partial_rank_ic) < float(protocol.minimum_incremental_mean_partial_rank_ic):
                    failures.add("incremental_mean_partial_rank_ic")
                if item.partial_rank_ic_lower_90pct is None or float(item.partial_rank_ic_lower_90pct) <= 0:
                    failures.add("incremental_partial_rank_ic_lower_bound")
        if any(
            item.mean_rank_ic is None
            or float(item.mean_rank_ic) < float(protocol.minimum_decay_rank_ic)
            for item in decay
        ):
            failures.add("decay_direction")
        provisional[hypothesis.factor_id] = {
            "hypothesis": hypothesis,
            "raw": raw,
            "effect": effect,
            "bound": bound,
            "failures": failures,
            "inconclusive": data_inconclusive,
        }
        if raw is not None:
            raw_by_role[hypothesis.role][hypothesis.factor_id] = raw
    adjusted = {
        role: calculate_holm_adjustment(values)
        for role, values in raw_by_role.items()
    }
    qualified = []
    for factor_id, item in provisional.items():
        probability = adjusted.get(item["hypothesis"].role, {}).get(factor_id)
        if probability is None or probability > float(protocol.one_sided_familywise_alpha):
            item["failures"].add("holm_familywise_significance")
        if not item["inconclusive"] and not item["failures"]:
            qualified.append(item)
    selected = []
    selected_groups = set()
    for role, limit in (
        (QuantResearchFactorRole.CANDIDATE_ALPHA, protocol.maximum_model_candidate_alpha_factors),
        (QuantResearchFactorRole.RISK_GUARD, protocol.maximum_model_risk_guard_factors),
    ):
        candidates = sorted(
            (item for item in qualified if item["hypothesis"].role is role),
            key=lambda item: (-item["effect"], -item["bound"], item["hypothesis"].factor_id),
        )
        for item in candidates:
            group = item["hypothesis"].related_factor_group
            if len([entry for entry in selected if entry["hypothesis"].role is role]) >= limit:
                break
            if group in selected_groups:
                continue
            selected.append(item)
            selected_groups.add(group)
    selected_ids = {item["hypothesis"].factor_id for item in selected}
    decisions = []
    for hypothesis in protocol.formal_hypotheses:
        item = provisional[hypothesis.factor_id]
        is_selected = hypothesis.factor_id in selected_ids
        if item["inconclusive"]:
            status = QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA
            reasons = ("registered_evidence_floor_not_met",)
        elif item["failures"]:
            status = QuantResearchFactorScreeningDecisionStatus.REJECTED_SCREEN
            reasons = ("at_least_one_frozen_gate_failed",)
        elif is_selected:
            status = QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE
            reasons = ("passed_all_gates_and_selected_within_cap",)
        else:
            status = QuantResearchFactorScreeningDecisionStatus.QUALIFIED_NOT_SELECTED_CAP
            reasons = ("passed_gates_but_not_selected_under_group_or_role_cap",)
        probability = adjusted.get(hypothesis.role, {}).get(hypothesis.factor_id)
        decisions.append(
            build_factor_screening_decision(
                factor_id=hypothesis.factor_id,
                role=hypothesis.role,
                related_factor_group=hypothesis.related_factor_group,
                status=status,
                formal_raw_p_value=_optional_string(item["raw"]),
                holm_adjusted_p_value=_optional_string(probability),
                robust_effect=_optional_string(item["effect"]),
                robust_lower_bound=_optional_string(item["bound"]),
                failed_gate_ids=tuple(sorted(item["failures"])),
                selected_for_model_candidate_set=is_selected,
                reason_codes=reasons,
            )
        )
    selected_order = tuple(
        item.factor_id
        for item in decisions
        if item.selected_for_model_candidate_set
    )
    return tuple(decisions), selected_order


def _pearson(left, right):
    left_mean = mean(left)
    right_mean = mean(right)
    left_centered = tuple(item - left_mean for item in left)
    right_centered = tuple(item - right_mean for item in right)
    numerator = sum(x * y for x, y in zip(left_centered, right_centered, strict=True))
    denominator = math.sqrt(
        sum(item * item for item in left_centered)
        * sum(item * item for item in right_centered)
    )
    if denominator == 0:
        raise QuantResearchFactorScreeningError("correlation denominator is zero")
    return numerator / denominator


def _linear_residual(values, control):
    control_mean = mean(control)
    value_mean = mean(values)
    denominator = sum((item - control_mean) ** 2 for item in control)
    if denominator == 0:
        raise QuantResearchFactorScreeningError("partial-correlation control is constant")
    slope = sum(
        (x - control_mean) * (y - value_mean)
        for x, y in zip(control, values, strict=True)
    ) / denominator
    return tuple(
        value - (value_mean + slope * (control_value - control_mean))
        for value, control_value in zip(values, control, strict=True)
    )


def _quantile(values, probability):
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _string(value) -> str:
    parsed = Decimal(str(value)).quantize(_QUANTUM)
    if parsed == 0:
        parsed = Decimal("0").quantize(_QUANTUM)
    return format(parsed, "f")


def _optional_string(value) -> str | None:
    return _string(value) if value is not None else None
