"""Deterministic fixture statistics for the first Quant Research Lab design."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from decimal import Decimal
from random import Random
from statistics import median
from typing import Iterable

from tip_api.contracts.analytics.v1 import (
    MINIMUM_COMPARABLE_SESSIONS,
    MINIMUM_SIGNAL_OBSERVATIONS,
    RESEARCH_BLOCK_LENGTH_SESSIONS,
    RESEARCH_BOOTSTRAP_REPLICATES,
    ResearchCostScenarioV1,
    ResearchGateEvaluationV1,
    ResearchGateStatus,
    ResearchInferenceStatus,
    ResearchParameterLockV1,
    ResearchParameterSummaryV1,
    ResearchStatisticsStage,
    StrategyEvaluationSplit,
    StrategyOutcomeStatus,
    StrongLeaderPullbackCohortAssignmentV1,
    StrongLeaderPullbackCohortOutcomeV1,
    StrongLeaderPullbackCohortRole,
    StrongLeaderPullbackMechanicsBatchV1,
    StrongLeaderPullbackObservationV1,
    StrongLeaderPullbackStatisticsReportV1,
    research_statistics_fingerprint,
)


RETURN_QUANTUM = Decimal("0.0000000001")
PROBABILITY_QUANTUM = Decimal("0.000001")
COVERAGE_QUANTUM = Decimal("0.0001")
COST_SCENARIOS_BPS = (0, 10, 25, 50)
REPORTED_REGIMES = ("Balanced", "Defensive", "Risk-on")


class CandidateStrategyResearchStatisticsError(ValueError):
    """Raised when fixture statistics would violate the registered sequence."""


def build_fixture_cohort_outcome(
    *,
    assignment: StrongLeaderPullbackCohortAssignmentV1,
    horizon_sessions: int,
    status: StrategyOutcomeStatus,
    underlying_price_return: str | None = None,
    benchmark_price_return: str | None = None,
    relative_to_benchmark_return: str | None = None,
    maximum_favorable_excursion: str | None = None,
    maximum_adverse_excursion: str | None = None,
    source_eod_fingerprint: str | None = None,
    reason_codes: tuple[str, ...] = (),
) -> StrongLeaderPullbackCohortOutcomeV1:
    """Build one explicitly synthetic label for signal or control mechanics."""

    payload: dict[str, object] = {
        "assignment_fingerprint": assignment.logical_fingerprint,
        "horizon_sessions": horizon_sessions,
        "status": status,
        "underlying_price_return": underlying_price_return,
        "benchmark_price_return": benchmark_price_return,
        "relative_to_benchmark_return": relative_to_benchmark_return,
        "maximum_favorable_excursion": maximum_favorable_excursion,
        "maximum_adverse_excursion": maximum_adverse_excursion,
        "source_eod_fingerprint": source_eod_fingerprint,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "fixture_only": True,
    }
    payload["label_fingerprint"] = research_statistics_fingerprint(
        payload,
        exclude=set(),
    )
    provisional = StrongLeaderPullbackCohortOutcomeV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackCohortOutcomeV1.model_validate(
        {
            **payload,
            "logical_fingerprint": research_statistics_fingerprint(provisional),
        }
    )


def evaluate_development_statistics_fixture(
    *,
    mechanics: StrongLeaderPullbackMechanicsBatchV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    outcomes: tuple[StrongLeaderPullbackCohortOutcomeV1, ...],
) -> StrongLeaderPullbackStatisticsReportV1:
    """Evaluate all frozen combinations and lock at most one before validation."""

    summaries = _summaries_for_stage(
        mechanics=mechanics,
        observations=observations,
        outcomes=outcomes,
        split=StrategyEvaluationSplit.DEVELOPMENT,
        selected_combination_id=None,
        apply_holm=False,
    )
    primary = [item for item in summaries if item.horizon_sessions == 3]
    selectable = [
        item
        for item in primary
        if item.inference_status is ResearchInferenceStatus.AVAILABLE
        and item.contrast_lower_90pct is not None
        and item.session_balanced_mean_contrast is not None
    ]
    parameter_lock = None
    selected = None
    reasons = ["fixture_only_no_stage_transition_authority"]
    if selectable:
        selected_summary = sorted(
            selectable,
            key=lambda item: (
                -Decimal(item.contrast_lower_90pct or "0"),
                -Decimal(item.session_balanced_mean_contrast or "0"),
                -item.signal_available_count,
                item.parameter_combination_id,
            ),
        )[0]
        selected = selected_summary.parameter_combination_id
        evidence = _summary_evidence_fingerprint(summaries)
        lock_payload: dict[str, object] = {
            "parameter_combination_id": selected,
            "development_evidence_fingerprint": evidence,
            "selection_objective": (
                "maximum_development_lower_90pct_session_balanced_3s_contrast"
            ),
            "objective_value": selected_summary.contrast_lower_90pct,
            "secondary_tiebreak_value": (
                selected_summary.session_balanced_mean_contrast
            ),
            "selected_before_validation": True,
            "validation_cannot_change_parameters": True,
            "holdout_cannot_change_parameters": True,
        }
        provisional = ResearchParameterLockV1.model_construct(
            **lock_payload,
            logical_fingerprint="0" * 64,
        )
        parameter_lock = ResearchParameterLockV1.model_validate(
            {
                **lock_payload,
                "logical_fingerprint": research_statistics_fingerprint(provisional),
            }
        )
        reasons.append("one_parameter_combination_locked_from_development_fixture")
    else:
        reasons.append("development_fixture_inconclusive_no_parameter_lock")
    return _build_report(
        mechanics=mechanics,
        stage=ResearchStatisticsStage.DEVELOPMENT,
        outcomes=outcomes,
        summaries=summaries,
        selected=selected,
        parameter_lock=parameter_lock,
        prior_stage_report_fingerprint=None,
        gates=(),
        holdout_consumed=False,
        reasons=tuple(reasons),
    )


def evaluate_validation_statistics_fixture(
    *,
    mechanics: StrongLeaderPullbackMechanicsBatchV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    outcomes: tuple[StrongLeaderPullbackCohortOutcomeV1, ...],
    development_report: StrongLeaderPullbackStatisticsReportV1,
) -> StrongLeaderPullbackStatisticsReportV1:
    """Apply multiplicity-aware validation without changing the lock."""

    if (
        development_report.stage is not ResearchStatisticsStage.DEVELOPMENT
        or development_report.parameter_lock is None
        or development_report.selected_parameter_combination_id is None
    ):
        raise CandidateStrategyResearchStatisticsError(
            "validation requires one conclusive development fixture lock"
        )
    _validate_report_mechanics(development_report, mechanics)
    summaries = _summaries_for_stage(
        mechanics=mechanics,
        observations=observations,
        outcomes=outcomes,
        split=StrategyEvaluationSplit.VALIDATION,
        selected_combination_id=None,
        apply_holm=True,
    )
    selected = development_report.selected_parameter_combination_id
    primary = _selected_primary_summary(summaries, selected)
    gates = _validation_gates(primary)
    return _build_report(
        mechanics=mechanics,
        stage=ResearchStatisticsStage.VALIDATION,
        outcomes=outcomes,
        summaries=summaries,
        selected=selected,
        parameter_lock=development_report.parameter_lock,
        prior_stage_report_fingerprint=development_report.logical_fingerprint,
        gates=gates,
        holdout_consumed=False,
        reasons=(
            "fixture_only_no_stage_transition_authority",
            "validation_parameters_unchanged_from_development_lock",
        ),
    )


def evaluate_holdout_statistics_fixture(
    *,
    mechanics: StrongLeaderPullbackMechanicsBatchV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    outcomes: tuple[StrongLeaderPullbackCohortOutcomeV1, ...],
    validation_report: StrongLeaderPullbackStatisticsReportV1,
) -> StrongLeaderPullbackStatisticsReportV1:
    """Consume only the locked holdout after every validation gate passes."""

    if (
        validation_report.stage is not ResearchStatisticsStage.VALIDATION
        or validation_report.parameter_lock is None
        or validation_report.selected_parameter_combination_id is None
        or not validation_report.all_required_gates_passed
    ):
        raise CandidateStrategyResearchStatisticsError(
            "holdout requires a validation fixture that passed every registered gate"
        )
    _validate_report_mechanics(validation_report, mechanics)
    selected = validation_report.selected_parameter_combination_id
    summaries = _summaries_for_stage(
        mechanics=mechanics,
        observations=observations,
        outcomes=outcomes,
        split=StrategyEvaluationSplit.HOLDOUT,
        selected_combination_id=selected,
        apply_holm=False,
    )
    primary = _selected_primary_summary(summaries, selected)
    gates = _holdout_gates(primary)
    return _build_report(
        mechanics=mechanics,
        stage=ResearchStatisticsStage.HOLDOUT,
        outcomes=outcomes,
        summaries=summaries,
        selected=selected,
        parameter_lock=validation_report.parameter_lock,
        prior_stage_report_fingerprint=validation_report.logical_fingerprint,
        gates=gates,
        holdout_consumed=True,
        reasons=(
            "fixture_only_no_stage_transition_authority",
            "holdout_fixture_exposed_for_locked_parameter",
            "single_use_holdout_custody_not_implemented",
        ),
    )


def _summaries_for_stage(
    *,
    mechanics: StrongLeaderPullbackMechanicsBatchV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    outcomes: tuple[StrongLeaderPullbackCohortOutcomeV1, ...],
    split: StrategyEvaluationSplit,
    selected_combination_id: str | None,
    apply_holm: bool,
) -> tuple[ResearchParameterSummaryV1, ...]:
    assignment_map, observation_map = _validated_maps(mechanics, observations)
    outcome_map = _validated_stage_outcomes(
        outcomes=outcomes,
        assignment_map=assignment_map,
        split=split,
        selected_combination_id=selected_combination_id,
    )
    combination_ids = (
        (selected_combination_id,)
        if selected_combination_id is not None
        else tuple(item.combination_id for item in mechanics.parameter_combinations)
    )
    summaries = tuple(
        _build_summary(
            mechanics=mechanics,
            observation_map=observation_map,
            outcome_map=outcome_map,
            combination_id=combination_id,
            split=split,
            horizon=horizon,
        )
        for combination_id in combination_ids
        for horizon in (1, 3, 5)
    )
    if not apply_holm:
        return summaries
    primary = [item for item in summaries if item.horizon_sessions == 3]
    adjusted = _holm_adjusted_values(primary)
    result = []
    for item in summaries:
        value = adjusted.get(item.parameter_combination_id)
        if item.horizon_sessions != 3 or value is None:
            result.append(item)
            continue
        payload = item.model_dump(mode="python")
        payload["holm_adjusted_p_value"] = _probability_string(value)
        result.append(_rebuild_summary(payload))
    return tuple(result)


def _build_summary(
    *,
    mechanics: StrongLeaderPullbackMechanicsBatchV1,
    observation_map: dict[str, StrongLeaderPullbackObservationV1],
    outcome_map: dict[tuple[str, int], StrongLeaderPullbackCohortOutcomeV1],
    combination_id: str,
    split: StrategyEvaluationSplit,
    horizon: int,
) -> ResearchParameterSummaryV1:
    assignments = [
        item
        for item in mechanics.assignments
        if item.parameter_combination_id == combination_id
        and item.evaluation_split is split
        and item.universe_id == "primary"
        and item.cohort_role
        in {
            StrongLeaderPullbackCohortRole.SIGNAL,
            StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL,
        }
    ]
    by_role = {
        role: [item for item in assignments if item.cohort_role is role]
        for role in (
            StrongLeaderPullbackCohortRole.SIGNAL,
            StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL,
        )
    }
    signal = _role_values(by_role[StrongLeaderPullbackCohortRole.SIGNAL], outcome_map, horizon)
    control = _role_values(
        by_role[StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL],
        outcome_map,
        horizon,
    )
    signal_available = signal["available"]
    control_available = control["available"]
    session_contrasts = _session_balanced_contrasts(
        signal_available,
        control_available,
    )
    enough = (
        len(signal_available) >= MINIMUM_SIGNAL_OBSERVATIONS
        and len(control_available) >= MINIMUM_SIGNAL_OBSERVATIONS
        and len(session_contrasts) >= MINIMUM_COMPARABLE_SESSIONS
    )
    reasons = []
    if len(signal_available) < MINIMUM_SIGNAL_OBSERVATIONS:
        reasons.append("signal_observation_floor_not_met")
    if len(control_available) < MINIMUM_SIGNAL_OBSERVATIONS:
        reasons.append("control_observation_floor_not_met")
    if len(session_contrasts) < MINIMUM_COMPARABLE_SESSIONS:
        reasons.append("comparable_session_floor_not_met")
    signal_returns = [
        Decimal(outcome.underlying_price_return or "0")
        for _, outcome in signal_available
    ]
    signal_relative = [
        Decimal(outcome.relative_to_benchmark_return or "0")
        for _, outcome in signal_available
    ]
    signal_mfe = [
        Decimal(outcome.maximum_favorable_excursion or "0")
        for _, outcome in signal_available
    ]
    signal_mae = [
        Decimal(outcome.maximum_adverse_excursion or "0")
        for _, outcome in signal_available
    ]
    contrast_mean = _mean(session_contrasts) if session_contrasts else None
    lower = upper = raw_p = None
    replicates = 0
    if enough:
        lower, upper, raw_p = _block_bootstrap(
            session_contrasts,
            seed_material=f"{split.value}:{combination_id}:{horizon}",
        )
        replicates = RESEARCH_BOOTSTRAP_REPLICATES
    regime_counts = {item: 0 for item in REPORTED_REGIMES}
    for assignment, _ in signal_available:
        regime = observation_map[assignment.observation_fingerprint].market_regime
        regime_counts[regime] += 1
    payload: dict[str, object] = {
        "parameter_combination_id": combination_id,
        "evaluation_split": split,
        "horizon_sessions": horizon,
        "signal_assigned_count": len(by_role[StrongLeaderPullbackCohortRole.SIGNAL]),
        "control_assigned_count": len(
            by_role[StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL]
        ),
        "signal_available_count": len(signal_available),
        "control_available_count": len(control_available),
        "signal_quarantined_count": signal["quarantined"],
        "control_quarantined_count": control["quarantined"],
        "signal_unavailable_or_pending_count": signal["other"],
        "control_unavailable_or_pending_count": control["other"],
        "signal_coverage_ratio": _coverage(
            len(signal_available),
            len(by_role[StrongLeaderPullbackCohortRole.SIGNAL]),
        ),
        "control_coverage_ratio": _coverage(
            len(control_available),
            len(by_role[StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL]),
        ),
        "paired_session_count": len(session_contrasts),
        "signal_market_regime_counts": regime_counts,
        "inference_status": (
            ResearchInferenceStatus.AVAILABLE
            if enough
            else ResearchInferenceStatus.INCONCLUSIVE
        ),
        "signal_mean_underlying_return": _optional_decimal_string(
            _mean_or_none(signal_returns)
        ),
        "signal_median_underlying_return": _optional_decimal_string(_median(signal_returns)),
        "signal_median_spy_relative_return": _optional_decimal_string(_median(signal_relative)),
        "signal_hit_rate": _optional_decimal_string(_hit_rate(signal_returns)),
        "signal_mean_maximum_favorable_excursion": _optional_decimal_string(
            _mean_or_none(signal_mfe)
        ),
        "signal_mean_maximum_adverse_excursion": _optional_decimal_string(
            _mean_or_none(signal_mae)
        ),
        "session_balanced_mean_contrast": _optional_decimal_string(contrast_mean),
        "contrast_lower_90pct": _optional_decimal_string(lower),
        "contrast_upper_90pct": _optional_decimal_string(upper),
        "one_sided_raw_p_value": (
            _probability_string(raw_p) if raw_p is not None else None
        ),
        "holm_adjusted_p_value": None,
        "bootstrap_replicates": replicates,
        "cost_scenarios": tuple(
            ResearchCostScenarioV1(
                basis_points_per_side=bps,
                signal_median_spy_relative_return_net=(
                    _optional_decimal_string(
                        _median(signal_relative)
                        - Decimal(2 * bps) / Decimal("10000")
                    )
                    if signal_relative
                    else None
                ),
            )
            for bps in COST_SCENARIOS_BPS
        ),
        "reason_codes": tuple(sorted(reasons)),
    }
    return _rebuild_summary(payload)


def _role_values(assignments, outcome_map, horizon):
    available = []
    quarantined = 0
    other = 0
    for assignment in assignments:
        outcome = outcome_map.get((assignment.logical_fingerprint, horizon))
        if outcome is None:
            other += 1
        elif outcome.status is StrategyOutcomeStatus.AVAILABLE:
            available.append((assignment, outcome))
        elif outcome.status is StrategyOutcomeStatus.QUARANTINED:
            quarantined += 1
        else:
            other += 1
    return {"available": available, "quarantined": quarantined, "other": other}


def _session_balanced_contrasts(signal, control):
    signal_by_session = defaultdict(list)
    control_by_session = defaultdict(list)
    for assignment, outcome in signal:
        signal_by_session[assignment.as_of_session].append(
            Decimal(outcome.underlying_price_return or "0")
        )
    for assignment, outcome in control:
        control_by_session[assignment.as_of_session].append(
            Decimal(outcome.underlying_price_return or "0")
        )
    return tuple(
        _mean(signal_by_session[session]) - _mean(control_by_session[session])
        for session in sorted(set(signal_by_session) & set(control_by_session))
    )


def _block_bootstrap(
    values: tuple[Decimal, ...],
    *,
    seed_material: str,
) -> tuple[Decimal, Decimal, Decimal]:
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
        bootstrap_means.append(_mean(tuple(values[index] for index in sampled_indices)))
        null_means.append(_mean(tuple(centered[index] for index in sampled_indices)))
    bootstrap_means.sort()
    lower = _quantile(bootstrap_means, Decimal("0.05"))
    upper = _quantile(bootstrap_means, Decimal("0.95"))
    exceedances = sum(item >= observed for item in null_means)
    p_value = Decimal(exceedances + 1) / Decimal(RESEARCH_BOOTSTRAP_REPLICATES + 1)
    return lower, upper, p_value


def _holm_adjusted_values(
    summaries: list[ResearchParameterSummaryV1],
) -> dict[str, Decimal]:
    values = [
        (item.parameter_combination_id, Decimal(item.one_sided_raw_p_value))
        for item in summaries
        if item.one_sided_raw_p_value is not None
    ]
    values.sort(key=lambda item: (item[1], item[0]))
    result: dict[str, Decimal] = {}
    running = Decimal("0")
    count = len(summaries)
    for rank, (combination_id, raw) in enumerate(values, start=1):
        running = max(running, min(Decimal("1"), raw * (count - rank + 1)))
        result[combination_id] = running
    return result


def _validation_gates(
    summary: ResearchParameterSummaryV1,
) -> tuple[ResearchGateEvaluationV1, ...]:
    return (
        _numeric_gate(
            gate_id="familywise_adjusted_parameter_evidence",
            metric_id="block_bootstrap_holm_adjusted_p_value",
            split=StrategyEvaluationSplit.VALIDATION,
            value=summary.holm_adjusted_p_value,
            threshold="0.10",
            comparison="le",
        ),
        _numeric_gate(
            gate_id="net_primary_median_positive",
            metric_id="median_3s_spy_relative_return_net_25bps_per_side",
            split=StrategyEvaluationSplit.VALIDATION,
            value=_cost_value(summary, 25),
            threshold="0.0000",
            comparison="gt",
        ),
        _regime_gate(summary, StrategyEvaluationSplit.VALIDATION),
    )


def _holdout_gates(
    summary: ResearchParameterSummaryV1,
) -> tuple[ResearchGateEvaluationV1, ...]:
    return (
        _numeric_gate(
            gate_id="holdout_primary_contrast_positive",
            metric_id="block_bootstrap_lower_90pct_primary_3s_contrast",
            split=StrategyEvaluationSplit.HOLDOUT,
            value=summary.contrast_lower_90pct,
            threshold="0.0000",
            comparison="gt",
        ),
        _numeric_gate(
            gate_id="net_primary_median_positive",
            metric_id="median_3s_spy_relative_return_net_25bps_per_side",
            split=StrategyEvaluationSplit.HOLDOUT,
            value=_cost_value(summary, 25),
            threshold="0.0000",
            comparison="gt",
        ),
        _regime_gate(summary, StrategyEvaluationSplit.HOLDOUT),
    )


def _numeric_gate(*, gate_id, metric_id, split, value, threshold, comparison):
    if value is None:
        return ResearchGateEvaluationV1(
            gate_id=gate_id,
            metric_id=metric_id,
            evaluation_split=split,
            status=ResearchGateStatus.INCONCLUSIVE,
            observed_value=None,
            threshold=threshold,
            reason_codes=("required_metric_inconclusive",),
        )
    observed = Decimal(value)
    boundary = Decimal(threshold)
    passed = observed <= boundary if comparison == "le" else observed > boundary
    return ResearchGateEvaluationV1(
        gate_id=gate_id,
        metric_id=metric_id,
        evaluation_split=split,
        status=ResearchGateStatus.PASS if passed else ResearchGateStatus.FAIL,
        observed_value=value,
        threshold=threshold,
        reason_codes=("registered_gate_passed" if passed else "registered_gate_failed",),
    )


def _regime_gate(summary, split):
    observed = [count for count in summary.signal_market_regime_counts.values() if count]
    if not observed:
        return ResearchGateEvaluationV1(
            gate_id="regime_observation_floor",
            metric_id="reported_observations_per_regime",
            evaluation_split=split,
            status=ResearchGateStatus.INCONCLUSIVE,
            observed_value=None,
            threshold="60",
            reason_codes=("no_reportable_regime_observations",),
        )
    minimum = min(observed)
    passed = minimum >= 60
    return ResearchGateEvaluationV1(
        gate_id="regime_observation_floor",
        metric_id="reported_observations_per_regime",
        evaluation_split=split,
        status=ResearchGateStatus.PASS if passed else ResearchGateStatus.FAIL,
        observed_value=str(minimum),
        threshold="60",
        reason_codes=("registered_gate_passed" if passed else "registered_gate_failed",),
    )


def _validated_maps(mechanics, observations):
    if mechanics.contains_forward_outcomes or mechanics.performance_claim_authorized:
        raise CandidateStrategyResearchStatisticsError(
            "statistics require the sealed outcome-free mechanics batch"
        )
    observation_map = {item.logical_fingerprint: item for item in observations}
    if len(observation_map) != len(observations):
        raise CandidateStrategyResearchStatisticsError(
            "research observations must have unique fingerprints"
        )
    assignment_map = {item.logical_fingerprint: item for item in mechanics.assignments}
    if len(assignment_map) != len(mechanics.assignments):
        raise CandidateStrategyResearchStatisticsError(
            "research assignments must have unique fingerprints"
        )
    if any(
        item.observation_fingerprint not in observation_map
        for item in mechanics.assignments
    ):
        raise CandidateStrategyResearchStatisticsError(
            "mechanics assignment is missing its source observation"
        )
    return assignment_map, observation_map


def _validated_stage_outcomes(
    *,
    outcomes,
    assignment_map,
    split,
    selected_combination_id,
):
    outcome_map = {}
    for outcome in outcomes:
        assignment = assignment_map.get(outcome.assignment_fingerprint)
        if assignment is None:
            raise CandidateStrategyResearchStatisticsError(
                "fixture outcome does not bind a mechanics assignment"
            )
        if assignment.evaluation_split is not split:
            raise CandidateStrategyResearchStatisticsError(
                "fixture report cannot inspect another chronological split"
            )
        if assignment.universe_id != "primary" or assignment.cohort_role not in {
            StrongLeaderPullbackCohortRole.SIGNAL,
            StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL,
        }:
            raise CandidateStrategyResearchStatisticsError(
                "fixture outcome is outside the primary signal-control contrast"
            )
        if (
            selected_combination_id is not None
            and assignment.parameter_combination_id != selected_combination_id
        ):
            raise CandidateStrategyResearchStatisticsError(
                "holdout fixture cannot inspect an unlocked parameter combination"
            )
        key = (outcome.assignment_fingerprint, outcome.horizon_sessions)
        if key in outcome_map:
            raise CandidateStrategyResearchStatisticsError(
                "fixture outcome identity is duplicated"
            )
        outcome_map[key] = outcome
    return outcome_map


def _build_report(
    *, mechanics, stage, outcomes, summaries, selected, parameter_lock,
    prior_stage_report_fingerprint, gates, holdout_consumed, reasons,
):
    payload: dict[str, object] = {
        "mechanics_batch_fingerprint": mechanics.logical_fingerprint,
        "stage": stage,
        "universe_id": "primary",
        "prior_stage_report_fingerprint": prior_stage_report_fingerprint,
        "input_outcome_count": len(outcomes),
        "summaries": summaries,
        "selected_parameter_combination_id": selected,
        "parameter_lock": parameter_lock,
        "gate_evaluations": gates,
        "all_required_gates_passed": bool(gates) and all(
            item.status is ResearchGateStatus.PASS for item in gates
        ),
        "fixture_only": True,
        "stage_transition_authorized": False,
        "performance_claim_authorized": False,
        "holdout_consumed": holdout_consumed,
        "single_use_holdout_custody_implemented": False,
        "reason_codes": tuple(sorted(set(reasons))),
    }
    provisional = StrongLeaderPullbackStatisticsReportV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackStatisticsReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": research_statistics_fingerprint(provisional),
        }
    )


def _rebuild_summary(payload):
    payload = dict(payload)
    payload.pop("logical_fingerprint", None)
    payload["cost_scenarios"] = tuple(
        item
        if isinstance(item, ResearchCostScenarioV1)
        else ResearchCostScenarioV1.model_validate(item)
        for item in payload["cost_scenarios"]
    )
    provisional = ResearchParameterSummaryV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    payload["logical_fingerprint"] = research_statistics_fingerprint(provisional)
    return ResearchParameterSummaryV1.model_validate(payload)


def _selected_primary_summary(summaries, selected):
    match = [
        item
        for item in summaries
        if item.parameter_combination_id == selected and item.horizon_sessions == 3
    ]
    if len(match) != 1:
        raise CandidateStrategyResearchStatisticsError(
            "locked primary-horizon summary is unavailable"
        )
    return match[0]


def _validate_report_mechanics(report, mechanics):
    if report.mechanics_batch_fingerprint != mechanics.logical_fingerprint:
        raise CandidateStrategyResearchStatisticsError(
            "prior fixture report and mechanics batch differ"
        )


def _summary_evidence_fingerprint(summaries):
    return research_statistics_fingerprint(
        {"summary_fingerprints": tuple(item.logical_fingerprint for item in summaries)},
        exclude=set(),
    )


def _cost_value(summary, bps):
    return next(
        item.signal_median_spy_relative_return_net
        for item in summary.cost_scenarios
        if item.basis_points_per_side == bps
    )


def _coverage(available: int, assigned: int) -> str:
    value = Decimal("0") if not assigned else Decimal(available) / Decimal(assigned)
    return format(value.quantize(COVERAGE_QUANTUM), "f")


def _mean(values: Iterable[Decimal]) -> Decimal:
    items = tuple(values)
    if not items:
        raise CandidateStrategyResearchStatisticsError("mean requires observations")
    return sum(items, Decimal("0")) / Decimal(len(items))


def _mean_or_none(values: Iterable[Decimal]) -> Decimal | None:
    items = tuple(values)
    return _mean(items) if items else None


def _median(values: Iterable[Decimal]) -> Decimal | None:
    items = tuple(values)
    return Decimal(median(items)) if items else None


def _hit_rate(values: Iterable[Decimal]) -> Decimal | None:
    items = tuple(values)
    if not items:
        return None
    return Decimal(sum(item > 0 for item in items)) / Decimal(len(items))


def _quantile(values: list[Decimal], probability: Decimal) -> Decimal:
    if not values:
        raise CandidateStrategyResearchStatisticsError("quantile requires observations")
    position = probability * Decimal(len(values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)
    weight = position - Decimal(lower_index)
    return values[lower_index] + (values[upper_index] - values[lower_index]) * weight


def _optional_decimal_string(value: Decimal | None) -> str | None:
    return None if value is None else format(value.quantize(RETURN_QUANTUM), "f")


def _probability_string(value: Decimal) -> str:
    return format(value.quantize(PROBABILITY_QUANTUM), "f")
