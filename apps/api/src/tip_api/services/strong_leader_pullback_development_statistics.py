"""Pure, development-only statistics for reconstructed Strong-Leader Pullback labels."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from random import Random
from statistics import median
from typing import Iterable

from tip_api.contracts.analytics.v1 import (
    DEVELOPMENT_STATISTICS_COST_SCENARIOS_BPS_PER_SIDE,
    DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS,
    DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT,
    DEVELOPMENT_STATISTICS_PRIMARY_HORIZON_SESSIONS,
    DEVELOPMENT_STATISTICS_REGIME_OBSERVATION_FLOOR,
    MINIMUM_COMPARABLE_SESSIONS,
    MINIMUM_SIGNAL_OBSERVATIONS,
    RESEARCH_BLOCK_LENGTH_SESSIONS,
    RESEARCH_BOOTSTRAP_REPLICATES,
    DevelopmentCostMetricsV1,
    DevelopmentDispositionCountsV1,
    DevelopmentEndpointScenario,
    DevelopmentSelectionStatus,
    DevelopmentStabilitySliceV1,
    ReconstructedDevelopmentLabelState,
    StrategyEvaluationSplit,
    StrategyResearchSessionAssignmentV1,
    StrongLeaderPullbackCohortRole,
    StrongLeaderPullbackDevelopmentParameterLockV1,
    StrongLeaderPullbackDevelopmentParameterSummaryV1,
    StrongLeaderPullbackDevelopmentStatisticsReportV1,
    StrongLeaderPullbackObservationV1,
    StrongLeaderPullbackReconstructedDevelopmentLabelV1,
    development_statistics_fingerprint,
    strong_leader_pullback_method_v1,
)
from tip_api.services.candidate_strategy_research_execution import (
    classify_strong_leader_pullback_observation,
    compile_strong_leader_pullback_execution_rules,
    enumerate_strong_leader_pullback_parameters,
)


_RETURN_QUANTUM = Decimal("0.0000000001")
_PROBABILITY_QUANTUM = Decimal("0.000001")
_REGIMES = ("Balanced", "Defensive", "Risk-on", "Stress")
_NUMERIC_STATES = frozenset(
    {
        ReconstructedDevelopmentLabelState.OBSERVED_EOD_EXACT,
        ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_EXACT,
        ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_INTERVAL,
    }
)


class StrongLeaderPullbackDevelopmentStatisticsError(ValueError):
    """Raised when a development comparison violates its frozen boundary."""


def evaluate_strong_leader_pullback_development_statistics(
    *,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    labels: tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...],
    source_dataset_manifest_sha256: str,
    source_dataset_logical_fingerprint: str,
    implementation_revision: str,
    created_at: datetime,
) -> StrongLeaderPullbackDevelopmentStatisticsReportV1:
    """Evaluate the complete 24 × 3 × 3 development matrix and lock at most one."""

    ordered_observations, labels_by_observation = _validated_inputs(
        observations,
        labels,
    )
    ordered_sessions = tuple(sorted({item.as_of_session for item in observations}))
    session_assignments = _development_session_assignments(labels_by_observation)
    method = strong_leader_pullback_method_v1()
    combinations = enumerate_strong_leader_pullback_parameters(method=method)
    if len(combinations) != 24:
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development parameter budget differs"
        )
    execution_rules = compile_strong_leader_pullback_execution_rules(method)
    summaries = []
    for combination in combinations:
        signal_observations = []
        control_observations = []
        for observation in ordered_observations:
            role, _, _, _ = classify_strong_leader_pullback_observation(
                observation=observation,
                combination=combination,
                session_assignment=session_assignments[observation.as_of_session],
                execution_rules=execution_rules,
            )
            if role is StrongLeaderPullbackCohortRole.SIGNAL:
                signal_observations.append(observation)
            elif role is StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL:
                control_observations.append(observation)
        for horizon in (1, 3, 5):
            signal = tuple(
                (item, labels_by_observation[item.logical_fingerprint][horizon])
                for item in signal_observations
            )
            control = tuple(
                (item, labels_by_observation[item.logical_fingerprint][horizon])
                for item in control_observations
            )
            for scenario in DevelopmentEndpointScenario:
                summaries.append(
                    _build_summary(
                        combination=combination,
                        horizon=horizon,
                        scenario=scenario,
                        signal=signal,
                        control=control,
                        ordered_sessions=ordered_sessions,
                    )
                )
    summaries_tuple = tuple(summaries)
    if len(summaries_tuple) != 216:
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development summary matrix differs"
        )
    primary = tuple(
        item
        for item in summaries_tuple
        if item.horizon_sessions == DEVELOPMENT_STATISTICS_PRIMARY_HORIZON_SESSIONS
    )
    endpoint_winners = {
        scenario.value: _scenario_winner(primary, scenario)
        for scenario in DevelopmentEndpointScenario
    }
    any_unavailable = any(
        item.signal_disposition.unavailable_evidence_count
        or item.control_disposition.unavailable_evidence_count
        for item in primary
    )
    if any_unavailable:
        selection_status = DevelopmentSelectionStatus.BLOCKED_UNAVAILABLE_EVIDENCE
        selected = None
        reasons = (
            "primary_family_contains_unavailable_source_evidence",
            "validation_requires_separate_formal_review",
        )
    elif any(value is None for value in endpoint_winners.values()):
        selection_status = DevelopmentSelectionStatus.INCONCLUSIVE_EVIDENCE_FLOOR
        selected = None
        reasons = (
            "at_least_one_endpoint_scenario_has_no_eligible_winner",
            "validation_requires_separate_formal_review",
        )
    elif len(set(endpoint_winners.values())) != 1:
        selection_status = DevelopmentSelectionStatus.REJECTED_ENDPOINT_INSTABILITY
        selected = None
        reasons = (
            "parameter_winner_changes_under_interval_endpoint_assignment",
            "validation_requires_separate_formal_review",
        )
    else:
        selection_status = DevelopmentSelectionStatus.LOCKED
        selected = next(iter(endpoint_winners.values()))
        reasons = (
            "one_parameter_locked_before_validation",
            "validation_requires_separate_formal_review",
        )
    evidence_fingerprint = development_statistics_fingerprint(
        {
            "policy_fingerprint": DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT,
            "summary_fingerprints": tuple(
                item.logical_fingerprint for item in summaries_tuple
            ),
        },
        exclude=set(),
    )
    parameter_lock = (
        _build_lock(
            selected=selected,
            endpoint_winners=endpoint_winners,
            primary=primary,
            evidence_fingerprint=evidence_fingerprint,
        )
        if selected is not None
        else None
    )
    payload: dict[str, object] = {
        "implementation_revision": implementation_revision,
        "created_at": created_at,
        "source_dataset_manifest_sha256": source_dataset_manifest_sha256,
        "source_dataset_logical_fingerprint": source_dataset_logical_fingerprint,
        "source_observation_count": len(ordered_observations),
        "source_label_count": len(labels),
        "first_signal_session": ordered_sessions[0],
        "last_signal_session": ordered_sessions[-1],
        "parameter_combination_count": 24,
        "summary_count": len(summaries_tuple),
        "endpoint_winner_ids": endpoint_winners,
        "selection_status": selection_status,
        "selected_parameter_combination_id": selected,
        "parameter_lock": parameter_lock,
        "summaries": summaries_tuple,
        "reason_codes": tuple(sorted(reasons)),
    }
    return _build_report(payload)


def calculate_development_block_bootstrap(
    values: tuple[Decimal, ...],
    *,
    seed_material: str,
) -> tuple[Decimal, Decimal, Decimal]:
    """Run the frozen primary inference path for independent Oracle comparison."""

    if not values or not seed_material:
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development bootstrap requires values and seed material"
        )
    count = len(values)
    block_length = min(RESEARCH_BLOCK_LENGTH_SESSIONS, count)
    seed = int.from_bytes(
        hashlib.sha256(
            (
                seed_material
                + ":"
                + ",".join(format(item, "f") for item in values)
            ).encode("utf-8")
        ).digest()[:8],
        "big",
    )
    random = Random(seed)
    observed = _mean(values)
    centered = tuple(item - observed for item in values)
    bootstrap_means = []
    null_means = []
    for _ in range(RESEARCH_BOOTSTRAP_REPLICATES):
        sampled_indices = []
        while len(sampled_indices) < count:
            start = random.randrange(count)
            sampled_indices.extend(
                (start + offset) % count for offset in range(block_length)
            )
        sampled_indices = sampled_indices[:count]
        bootstrap_means.append(
            _mean(tuple(values[index] for index in sampled_indices))
        )
        null_means.append(_mean(tuple(centered[index] for index in sampled_indices)))
    bootstrap_means.sort()
    lower = _quantile(bootstrap_means, Decimal("0.05"))
    upper = _quantile(bootstrap_means, Decimal("0.95"))
    exceedances = sum(item >= observed for item in null_means)
    probability = Decimal(exceedances + 1) / Decimal(
        RESEARCH_BOOTSTRAP_REPLICATES + 1
    )
    return lower, upper, probability


def _validated_inputs(observations, labels):
    if not observations or not labels:
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development statistics require observations and labels"
        )
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.as_of_session,
                item.universe_id,
                str(item.instrument_id),
            ),
        )
    )
    if ordered != observations or any(item.universe_id != "primary" for item in ordered):
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development observations must be sorted Primary rows"
        )
    by_observation: dict[
        str, dict[int, StrongLeaderPullbackReconstructedDevelopmentLabelV1]
    ] = defaultdict(dict)
    observation_map = {item.logical_fingerprint: item for item in ordered}
    if len(observation_map) != len(ordered):
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development observations are duplicated"
        )
    for label in labels:
        observation = observation_map.get(label.observation_fingerprint)
        if (
            observation is None
            or label.evaluation_split is not StrategyEvaluationSplit.DEVELOPMENT
            or label.signal_session != observation.as_of_session
            or label.instrument_id != observation.instrument_id
            or label.horizon_sessions in by_observation[label.observation_fingerprint]
        ):
            raise StrongLeaderPullbackDevelopmentStatisticsError(
                "development label binding differs"
            )
        by_observation[label.observation_fingerprint][label.horizon_sessions] = label
    if len(labels) != len(ordered) * 3 or any(
        set(by_observation[item.logical_fingerprint]) != {1, 3, 5} for item in ordered
    ):
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development label population differs"
        )
    return ordered, by_observation


def _development_session_assignments(labels_by_observation):
    maximum_by_session = {}
    for labels in labels_by_observation.values():
        label = labels[5]
        prior = maximum_by_session.get(label.signal_session)
        if prior is not None and prior != label.expected_exit_session:
            raise StrongLeaderPullbackDevelopmentStatisticsError(
                "development session has inconsistent maximum outcome"
            )
        maximum_by_session[label.signal_session] = label.expected_exit_session
    return {
        session: StrategyResearchSessionAssignmentV1(
            session=session,
            raw_split=StrategyEvaluationSplit.DEVELOPMENT,
            usable_for_signal_evaluation=True,
            exclusion_codes=(),
            maximum_outcome_session=maximum,
        )
        for session, maximum in maximum_by_session.items()
    }


def _build_summary(
    *,
    combination,
    horizon,
    scenario,
    signal,
    control,
    ordered_sessions,
):
    signal_disposition = _disposition(signal)
    control_disposition = _disposition(control)
    signal_numeric = _numeric_events(signal, scenario=scenario, signal_role=True)
    control_numeric = _numeric_events(control, scenario=scenario, signal_role=False)
    contrasts, contrast_regimes = _session_contrasts(signal_numeric, control_numeric)
    enough = (
        len(signal_numeric) >= MINIMUM_SIGNAL_OBSERVATIONS
        and len(control_numeric) >= MINIMUM_SIGNAL_OBSERVATIONS
        and len(contrasts) >= MINIMUM_COMPARABLE_SESSIONS
    )
    signal_returns = tuple(item[2] for item in signal_numeric)
    signal_relative = tuple(item[3] for item in signal_numeric)
    signal_regimes = Counter(item[0].market_regime for item in signal_numeric)
    regime_counts = {regime: signal_regimes.get(regime, 0) for regime in _REGIMES}
    observed_regimes = [value for value in regime_counts.values() if value]
    regime_floor = bool(observed_regimes) and min(observed_regimes) >= (
        DEVELOPMENT_STATISTICS_REGIME_OBSERVATION_FLOOR
    )
    lower = upper = probability = None
    if enough:
        lower, upper, probability = calculate_development_block_bootstrap(
            tuple(value for _, value in contrasts),
            seed_material=(
                f"development:{combination.combination_id}:{horizon}:"
                f"{scenario.value}:{DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT}"
            ),
        )
    excursions = tuple(
        (
            Decimal(label.maximum_favorable_excursion),
            Decimal(label.maximum_adverse_excursion),
        )
        for _, label in signal
        if label.state in _NUMERIC_STATES
        and label.maximum_favorable_excursion is not None
        and label.maximum_adverse_excursion is not None
    )
    wins = tuple(value for value in signal_returns if value > 0)
    losses = tuple(value for value in signal_returns if value < 0)
    reasons = []
    if len(signal_numeric) < MINIMUM_SIGNAL_OBSERVATIONS:
        reasons.append("signal_observation_floor_not_met")
    if len(control_numeric) < MINIMUM_SIGNAL_OBSERVATIONS:
        reasons.append("control_observation_floor_not_met")
    if len(contrasts) < MINIMUM_COMPARABLE_SESSIONS:
        reasons.append("comparable_session_floor_not_met")
    if not regime_floor:
        reasons.append("reported_regime_observation_floor_not_met")
    if signal_disposition.unavailable_evidence_count:
        reasons.append("signal_unavailable_source_evidence")
    if control_disposition.unavailable_evidence_count:
        reasons.append("control_unavailable_source_evidence")
    if signal_disposition.unexecutable_no_next_open_count:
        reasons.append("signal_no_next_open_not_executed")
    if control_disposition.unexecutable_no_next_open_count:
        reasons.append("control_no_next_open_not_executed")
    if len(excursions) < len(signal_numeric):
        reasons.append("signal_excursion_coverage_incomplete")
    payload = {
        "parameter_combination_id": combination.combination_id,
        "leadership_gate": combination.leadership_gate,
        "pullback_depth_atr_band": combination.pullback_depth_atr_band,
        "recovery_trigger": combination.recovery_trigger,
        "volume_contraction_ratio_max": combination.volume_contraction_ratio_max,
        "horizon_sessions": horizon,
        "endpoint_scenario": scenario,
        "signal_disposition": signal_disposition,
        "control_disposition": control_disposition,
        "paired_session_count": len(contrasts),
        "signal_market_regime_counts": regime_counts,
        "reported_regime_floor_met": regime_floor,
        "inference_available": enough,
        "signal_mean_underlying_return": _string(_mean_or_none(signal_returns)),
        "signal_median_underlying_return": _string(_median(signal_returns)),
        "signal_median_spy_relative_return": _string(_median(signal_relative)),
        "signal_win_rate": _ratio(signal_returns, lambda value: value > 0),
        "signal_average_win": _string(_mean_or_none(wins)),
        "signal_average_loss": _string(_mean_or_none(losses)),
        "signal_payoff_ratio": _string(_payoff_ratio(wins, losses)),
        "signal_profit_factor": _string(_profit_factor(wins, losses)),
        "signal_mean_maximum_favorable_excursion": _string(
            _mean_or_none(tuple(item[0] for item in excursions))
        ),
        "signal_mean_maximum_adverse_excursion": _string(
            _mean_or_none(tuple(item[1] for item in excursions))
        ),
        "signal_excursion_count": len(excursions),
        "session_balanced_mean_contrast": _string(
            _mean_or_none(tuple(value for _, value in contrasts))
        ),
        "contrast_lower_90pct": _string(lower),
        "contrast_upper_90pct": _string(upper),
        "one_sided_raw_p_value": _probability_string(probability),
        "bootstrap_replicates": RESEARCH_BOOTSTRAP_REPLICATES if enough else 0,
        "positive_paired_session_ratio": _ratio(
            tuple(value for _, value in contrasts), lambda value: value > 0
        ),
        "largest_absolute_session_contrast_share": _concentration(contrasts),
        "cost_metrics": tuple(
            _cost_metrics(signal_returns, signal_relative, bps)
            for bps in DEVELOPMENT_STATISTICS_COST_SCENARIOS_BPS_PER_SIDE
        ),
        "stability_slices": _stability_slices(
            signal_numeric=signal_numeric,
            control_numeric=control_numeric,
            contrasts=contrasts,
            contrast_regimes=contrast_regimes,
            ordered_sessions=ordered_sessions,
        ),
        "reason_codes": tuple(sorted(set(reasons))),
    }
    return _build_summary_model(payload)


def _numeric_events(rows, *, scenario, signal_role):
    result = []
    for observation, label in rows:
        if label.state not in _NUMERIC_STATES:
            continue
        use_upper = scenario is DevelopmentEndpointScenario.ALL_UPPER or (
            scenario is DevelopmentEndpointScenario.CONTRAST_ADVERSE
            and not signal_role
        )
        underlying = Decimal(
            label.underlying_price_return_upper
            if use_upper
            else label.underlying_price_return_lower
        )
        relative = Decimal(
            label.relative_to_benchmark_return_upper
            if use_upper
            else label.relative_to_benchmark_return_lower
        )
        result.append((observation, label, underlying, relative))
    return tuple(result)


def _disposition(rows):
    counts = Counter(label.state for _, label in rows)
    return DevelopmentDispositionCountsV1(
        assigned_count=len(rows),
        observed_eod_exact_count=counts[
            ReconstructedDevelopmentLabelState.OBSERVED_EOD_EXACT
        ],
        terminal_reference_exact_count=counts[
            ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_EXACT
        ],
        terminal_reference_interval_count=counts[
            ReconstructedDevelopmentLabelState.TERMINAL_REFERENCE_INTERVAL
        ],
        unavailable_evidence_count=counts[
            ReconstructedDevelopmentLabelState.UNAVAILABLE_EVIDENCE
        ],
        unexecutable_no_next_open_count=counts[
            ReconstructedDevelopmentLabelState.UNEXECUTABLE_NO_NEXT_OPEN
        ],
        numeric_count=sum(counts[state] for state in _NUMERIC_STATES),
    )


def _session_contrasts(signal, control):
    signal_by_session = defaultdict(list)
    control_by_session = defaultdict(list)
    regime_by_session = {}
    for observation, _, underlying, _ in signal:
        signal_by_session[observation.as_of_session].append(underlying)
        _set_session_regime(regime_by_session, observation)
    for observation, _, underlying, _ in control:
        control_by_session[observation.as_of_session].append(underlying)
        _set_session_regime(regime_by_session, observation)
    sessions = sorted(set(signal_by_session) & set(control_by_session))
    return (
        tuple(
            (
                session,
                _mean(tuple(signal_by_session[session]))
                - _mean(tuple(control_by_session[session])),
            )
            for session in sessions
        ),
        {session: regime_by_session[session] for session in sessions},
    )


def _set_session_regime(regime_by_session, observation):
    prior = regime_by_session.get(observation.as_of_session)
    if prior is not None and prior != observation.market_regime:
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development session contains multiple Regime states"
        )
    regime_by_session[observation.as_of_session] = observation.market_regime


def _stability_slices(
    *, signal_numeric, control_numeric, contrasts, contrast_regimes, ordered_sessions
):
    midpoint = len(ordered_sessions) // 2
    first_sessions = set(ordered_sessions[:midpoint])
    second_sessions = set(ordered_sessions[midpoint:])
    result = [
        _one_stability_slice(
            slice_type="chronological_half",
            slice_code="first_half",
            sessions=first_sessions,
            signal_numeric=signal_numeric,
            control_numeric=control_numeric,
            contrasts=contrasts,
        ),
        _one_stability_slice(
            slice_type="chronological_half",
            slice_code="second_half",
            sessions=second_sessions,
            signal_numeric=signal_numeric,
            control_numeric=control_numeric,
            contrasts=contrasts,
        ),
    ]
    for regime in _REGIMES:
        sessions = {
            session for session, value in contrast_regimes.items() if value == regime
        }
        result.append(
            _one_stability_slice(
                slice_type="market_regime",
                slice_code=regime,
                sessions=sessions,
                signal_numeric=signal_numeric,
                control_numeric=control_numeric,
                contrasts=contrasts,
            )
        )
    return tuple(result)


def _one_stability_slice(
    *, slice_type, slice_code, sessions, signal_numeric, control_numeric, contrasts
):
    values = tuple(value for session, value in contrasts if session in sessions)
    return DevelopmentStabilitySliceV1(
        slice_type=slice_type,
        slice_code=slice_code,
        signal_numeric_count=sum(
            observation.as_of_session in sessions for observation, *_ in signal_numeric
        ),
        control_numeric_count=sum(
            observation.as_of_session in sessions for observation, *_ in control_numeric
        ),
        paired_session_count=len(values),
        session_balanced_mean_contrast=_string(_mean_or_none(values)),
    )


def _cost_metrics(signal_returns, signal_relative, basis_points):
    cost = Decimal(2 * basis_points) / Decimal("10000")
    net = tuple(value - cost for value in signal_returns)
    relative_net = tuple(value - cost for value in signal_relative)
    wins = tuple(value for value in net if value > 0)
    losses = tuple(value for value in net if value < 0)
    return DevelopmentCostMetricsV1(
        basis_points_per_side=basis_points,
        signal_mean_underlying_return_net=_string(_mean_or_none(net)),
        signal_median_underlying_return_net=_string(_median(net)),
        signal_median_spy_relative_return_net=_string(_median(relative_net)),
        signal_win_rate_net=_ratio(net, lambda value: value > 0),
        signal_average_win_net=_string(_mean_or_none(wins)),
        signal_average_loss_net=_string(_mean_or_none(losses)),
        signal_payoff_ratio_net=_string(_payoff_ratio(wins, losses)),
        signal_profit_factor_net=_string(_profit_factor(wins, losses)),
    )


def _scenario_winner(primary, scenario):
    candidates = [
        item
        for item in primary
        if item.endpoint_scenario is scenario
        and item.inference_available
        and item.reported_regime_floor_met
        and item.contrast_lower_90pct is not None
        and item.session_balanced_mean_contrast is not None
    ]
    if len(candidates) != 24:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            -Decimal(item.contrast_lower_90pct),
            -Decimal(item.session_balanced_mean_contrast),
            -item.signal_disposition.numeric_count,
            item.parameter_combination_id,
        ),
    )[0].parameter_combination_id


def _build_lock(*, selected, endpoint_winners, primary, evidence_fingerprint):
    summary = next(
        item
        for item in primary
        if item.parameter_combination_id == selected
        and item.endpoint_scenario is DevelopmentEndpointScenario.CONTRAST_ADVERSE
    )
    payload = {
        "parameter_combination_id": selected,
        "development_evidence_fingerprint": evidence_fingerprint,
        "objective_value": summary.contrast_lower_90pct,
        "secondary_tiebreak_value": summary.session_balanced_mean_contrast,
        "endpoint_winner_ids": endpoint_winners,
    }
    provisional = StrongLeaderPullbackDevelopmentParameterLockV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackDevelopmentParameterLockV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_statistics_fingerprint(provisional),
        }
    )


def _build_summary_model(payload):
    provisional = StrongLeaderPullbackDevelopmentParameterSummaryV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackDevelopmentParameterSummaryV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_statistics_fingerprint(provisional),
        }
    )


def _build_report(payload):
    provisional = StrongLeaderPullbackDevelopmentStatisticsReportV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackDevelopmentStatisticsReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": development_statistics_fingerprint(provisional),
        }
    )


def _mean(values: Iterable[Decimal]) -> Decimal:
    items = tuple(values)
    if not items:
        raise StrongLeaderPullbackDevelopmentStatisticsError(
            "development mean requires values"
        )
    return sum(items, Decimal("0")) / Decimal(len(items))


def _mean_or_none(values: Iterable[Decimal]) -> Decimal | None:
    items = tuple(values)
    return _mean(items) if items else None


def _median(values: Iterable[Decimal]) -> Decimal | None:
    items = tuple(values)
    return Decimal(median(items)) if items else None


def _payoff_ratio(wins, losses):
    if not wins or not losses:
        return None
    return _mean(wins) / abs(_mean(losses))


def _profit_factor(wins, losses):
    if not losses:
        return None
    return sum(wins, Decimal("0")) / abs(sum(losses, Decimal("0")))


def _ratio(values, predicate):
    items = tuple(values)
    if not items:
        return None
    value = Decimal(sum(predicate(item) for item in items)) / Decimal(len(items))
    return format(value.quantize(_RETURN_QUANTUM), "f")


def _concentration(contrasts):
    absolute = tuple(abs(value) for _, value in contrasts)
    total = sum(absolute, Decimal("0"))
    if not absolute or total == 0:
        return None
    return format((max(absolute) / total).quantize(_RETURN_QUANTUM), "f")


def _quantile(values, probability):
    position = probability * Decimal(len(values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)
    weight = position - Decimal(lower_index)
    return values[lower_index] + (values[upper_index] - values[lower_index]) * weight


def _string(value):
    return None if value is None else format(value.quantize(_RETURN_QUANTUM), "f")


def _probability_string(value):
    return (
        None
        if value is None
        else format(value.quantize(_PROBABILITY_QUANTUM), "f")
    )
