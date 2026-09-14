"""Pure outcome-blind diagnostics for the first canonical research method."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import Iterable

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChronologicalPlanV1,
    StrongLeaderPullbackCohortRole,
    StrongLeaderPullbackMethodV1,
    StrongLeaderPullbackObservationV1,
    strong_leader_pullback_method_v1,
)
from tip_api.contracts.analytics.v1.strong_leader_pullback_diagnostics import (
    STRONG_LEADER_PULLBACK_BOOLEAN_DIAGNOSTIC_ORDER,
    STRONG_LEADER_PULLBACK_DIAGNOSTICS_CONTRACT_VERSION,
    STRONG_LEADER_PULLBACK_NUMERIC_DIAGNOSTIC_ORDER,
    DiagnosticConcentrationAxis,
    StrongLeaderPullbackBooleanDiagnosticV1,
    StrongLeaderPullbackCategoryCountV1,
    StrongLeaderPullbackCombinationDiagnosticV1,
    StrongLeaderPullbackConcentrationV1,
    StrongLeaderPullbackDiagnosticExcludedPathV1,
    StrongLeaderPullbackDiagnosticReasonCountV1,
    StrongLeaderPullbackFeatureCoverageV1,
    StrongLeaderPullbackMethodDiagnosticsV1,
    StrongLeaderPullbackNumericDiagnosticV1,
    StrongLeaderPullbackThresholdProximityV1,
    strong_leader_pullback_diagnostics_fingerprint,
)
from tip_api.services.candidate_strategy_research_execution import (
    classify_strong_leader_pullback_observation,
    compile_strong_leader_pullback_execution_rules,
    enumerate_strong_leader_pullback_parameters,
)


RATIO_QUANTUM = Decimal("0.0001")
VALUE_QUANTUM = Decimal("0.0000000001")
DIAGNOSTIC_TOLERANCES = {
    "relative_leadership_20s": Decimal("0.01"),
    "trend_quality": Decimal("1"),
    "atr_pullback_depth": Decimal("0.10"),
    "volume_contraction": Decimal("0.05"),
}


class StrongLeaderPullbackDiagnosticsError(ValueError):
    """Raised when an outcome-blind diagnostic population is not auditable."""


def build_strong_leader_pullback_method_diagnostics(
    *,
    plan: CandidateStrategyChronologicalPlanV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    excluded_paths: tuple[StrongLeaderPullbackDiagnosticExcludedPathV1, ...],
    known_split_adjustment_applied_path_count: int,
    method: StrongLeaderPullbackMethodV1 | None = None,
) -> StrongLeaderPullbackMethodDiagnosticsV1:
    """Summarize feature geometry and triggers without reading any outcome."""

    canonical_method = method or strong_leader_pullback_method_v1()
    if canonical_method != strong_leader_pullback_method_v1():
        raise StrongLeaderPullbackDiagnosticsError(
            "diagnostics require the exact canonical first method"
        )
    if plan.experiment_fingerprint != canonical_method.source_experiment_fingerprint:
        raise StrongLeaderPullbackDiagnosticsError(
            "diagnostic plan and canonical method differ"
        )
    observation_keys = tuple(_path_key(item) for item in observations)
    exclusion_keys = tuple(_path_key(item) for item in excluded_paths)
    if observation_keys != tuple(sorted(set(observation_keys))):
        raise StrongLeaderPullbackDiagnosticsError(
            "diagnostic observations must be unique and sorted"
        )
    if exclusion_keys != tuple(sorted(set(exclusion_keys))):
        raise StrongLeaderPullbackDiagnosticsError(
            "diagnostic exclusions must be unique and sorted"
        )
    if set(observation_keys) & set(exclusion_keys):
        raise StrongLeaderPullbackDiagnosticsError(
            "a diagnostic path cannot be complete and excluded"
        )
    planned_sessions = set(plan.ordered_sessions)
    if any(key[0] not in planned_sessions for key in (*observation_keys, *exclusion_keys)):
        raise StrongLeaderPullbackDiagnosticsError(
            "diagnostic path is outside the chronological plan"
        )
    if any(
        not item.membership_included
        or item.membership_session != item.as_of_session
        or item.source_max_session > item.as_of_session
        for item in observations
    ):
        raise StrongLeaderPullbackDiagnosticsError(
            "complete diagnostic observation is not source-dated and eligible"
        )

    combinations = enumerate_strong_leader_pullback_parameters(method=canonical_method)
    execution_rules = compile_strong_leader_pullback_execution_rules(canonical_method)
    diagnostic_thresholds = {
        "relative_leadership_20s": tuple(
            sorted({item[0] for item in execution_rules.leadership_gates.values()})
        ),
        "trend_quality": tuple(
            sorted({item[1] for item in execution_rules.leadership_gates.values()})
        ),
        "atr_pullback_depth": tuple(
            sorted(
                {
                    bound
                    for interval in execution_rules.pullback_bands.values()
                    for bound in interval
                }
            )
        ),
        "volume_contraction": tuple(sorted(set(execution_rules.volume_caps.values()))),
    }
    assignment_by_session = {item.session: item for item in plan.assignments}
    combination_rows: list[StrongLeaderPullbackCombinationDiagnosticV1] = []
    for combination in combinations:
        counts: Counter[StrongLeaderPullbackCohortRole] = Counter()
        signal_sessions = set()
        signal_instruments = set()
        for observation in observations:
            role, _, _, _ = classify_strong_leader_pullback_observation(
                observation=observation,
                combination=combination,
                session_assignment=assignment_by_session[observation.as_of_session],
                execution_rules=execution_rules,
            )
            counts[role] += 1
            if role is StrongLeaderPullbackCohortRole.SIGNAL:
                signal_sessions.add(observation.as_of_session)
                signal_instruments.add(observation.instrument_id)
        leader_count = (
            counts[StrongLeaderPullbackCohortRole.SIGNAL]
            + counts[StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL]
        )
        combination_rows.append(
            StrongLeaderPullbackCombinationDiagnosticV1(
                parameter_combination_id=combination.combination_id,
                signal_count=counts[StrongLeaderPullbackCohortRole.SIGNAL],
                eligible_leader_control_count=counts[
                    StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL
                ],
                excluded_chronological_boundary_count=counts[
                    StrongLeaderPullbackCohortRole.EXCLUDED_CHRONOLOGICAL_BOUNDARY
                ],
                excluded_membership_count=counts[
                    StrongLeaderPullbackCohortRole.EXCLUDED_MEMBERSHIP
                ],
                excluded_not_leader_count=counts[
                    StrongLeaderPullbackCohortRole.EXCLUDED_NOT_LEADER
                ],
                unavailable_input_count=len(excluded_paths),
                signal_rate_among_eligible_leaders=_ratio(
                    counts[StrongLeaderPullbackCohortRole.SIGNAL], leader_count
                ),
                distinct_signal_session_count=len(signal_sessions),
                distinct_signal_instrument_count=len(signal_instruments),
            )
        )
    combination_rows.sort(key=lambda item: item.parameter_combination_id)

    numeric_values = {
        "relative_leadership_20s": tuple(
            Decimal(item.relative_strength_20s_percentile) for item in observations
        ),
        "trend_quality": tuple(
            Decimal(item.trend_quality_score) for item in observations
        ),
        "atr_pullback_depth": tuple(
            Decimal(item.pullback_depth_atr) for item in observations
        ),
        "volume_contraction": tuple(
            Decimal(item.pullback_volume_ratio) for item in observations
        ),
    }
    boolean_values = {
        "close_above_prior_close": tuple(
            item.close_above_prior_close for item in observations
        ),
        "close_above_prior_high": tuple(
            item.close_above_prior_high for item in observations
        ),
    }
    expected_path_count = len(observations) + len(excluded_paths)
    values: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": STRONG_LEADER_PULLBACK_DIAGNOSTICS_CONTRACT_VERSION,
        "method_version": canonical_method.method_version,
        "method_fingerprint": canonical_method.logical_fingerprint,
        "experiment_fingerprint": canonical_method.source_experiment_fingerprint,
        "input_feature_fingerprint": canonical_method.input_feature_fingerprint,
        "evidence_tier": (
            "reconstructed_latest_vintage_method_engineering_only"
        ),
        "as_operated": False,
        "price_feature_basis": (
            "sparse_known_split_adjustment_proxy_with_unproven_neutral_rows"
        ),
        "market_regime_basis": "recomputed_reconstructed_same_session_proxy",
        "canonical_feature_values_authorized": False,
        "chronological_plan_fingerprint": plan.logical_fingerprint,
        "source_population_fingerprint": _source_population_fingerprint(
            plan=plan,
            observations=observations,
            excluded_paths=excluded_paths,
        ),
        "first_session": plan.ordered_sessions[0],
        "last_session": plan.ordered_sessions[-1],
        "session_count": len(plan.ordered_sessions),
        "expected_path_count": expected_path_count,
        "complete_observation_count": len(observations),
        "excluded_path_count": len(excluded_paths),
        "known_split_adjustment_applied_path_count": (
            known_split_adjustment_applied_path_count
        ),
        "known_split_adjustment_applied_path_rate": _ratio(
            known_split_adjustment_applied_path_count, len(observations)
        ),
        "feature_coverage": _feature_coverage(
            canonical_method=canonical_method,
            complete_count=len(observations),
            excluded_paths=excluded_paths,
        ),
        "numeric_diagnostics": tuple(
            _numeric_summary(feature_id, numeric_values[feature_id])
            for feature_id in STRONG_LEADER_PULLBACK_NUMERIC_DIAGNOSTIC_ORDER
        ),
        "boolean_diagnostics": tuple(
            _boolean_summary(feature_id, boolean_values[feature_id])
            for feature_id in STRONG_LEADER_PULLBACK_BOOLEAN_DIAGNOSTIC_ORDER
        ),
        "market_regime_counts": tuple(
            StrongLeaderPullbackCategoryCountV1(category=category, count=count)
            for category, count in sorted(
                Counter(item.market_regime for item in observations).items()
            )
        ),
        "threshold_proximity": tuple(
            _threshold_proximity(
                feature_id,
                numeric_values[feature_id],
                diagnostic_thresholds[feature_id],
            )
            for feature_id in STRONG_LEADER_PULLBACK_NUMERIC_DIAGNOSTIC_ORDER
        ),
        "observation_concentration": (
            _concentration(
                DiagnosticConcentrationAxis.SESSION,
                (item.as_of_session.isoformat() for item in observations),
            ),
            _concentration(
                DiagnosticConcentrationAxis.INSTRUMENT,
                (str(item.instrument_id) for item in observations),
            ),
        ),
        "parameter_combinations": tuple(combination_rows),
        "limitation_codes": tuple(
            sorted(
                {
                    "diagnostic_population_not_formal_research_sample",
                    "point_in_time_sector_concentration_unavailable",
                    "recomputed_regime_not_as_operated",
                    "reconstructed_membership_not_as_operated",
                    "sparse_adjustment_proxy_not_formal_adjustment_evidence",
                    "trigger_counts_not_parameter_selection_evidence",
                    *(
                        {"incomplete_paths_excluded_from_feature_distributions"}
                        if excluded_paths
                        else set()
                    ),
                }
            )
        ),
        "contains_outcome_blind_trigger_counts": True,
        "contains_forward_outcomes": False,
        "contains_performance_metrics": False,
        "trigger_counts_reusable_for_parameter_selection": False,
        "parameter_selection_authorized": False,
        "formal_development_authorized": False,
        "validation_authorized": False,
        "holdout_access_authorized": False,
        "candidate_activation_authorized": False,
        "external_request_count": 0,
        "canonical_data_write_count": 0,
        "production_write_count": 0,
    }
    provisional = StrongLeaderPullbackMethodDiagnosticsV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackMethodDiagnosticsV1.model_validate(
        {
            **values,
            "logical_fingerprint": strong_leader_pullback_diagnostics_fingerprint(
                provisional
            ),
        }
    )


def _path_key(
    value: StrongLeaderPullbackObservationV1
    | StrongLeaderPullbackDiagnosticExcludedPathV1,
) -> tuple[date, str]:
    return (value.as_of_session, str(value.instrument_id))


def _feature_coverage(
    *,
    canonical_method: StrongLeaderPullbackMethodV1,
    complete_count: int,
    excluded_paths: tuple[StrongLeaderPullbackDiagnosticExcludedPathV1, ...],
) -> tuple[StrongLeaderPullbackFeatureCoverageV1, ...]:
    output: list[StrongLeaderPullbackFeatureCoverageV1] = []
    expected_count = complete_count + len(excluded_paths)
    for feature in canonical_method.features:
        unavailable = tuple(
            item
            for item in excluded_paths
            if feature.feature_id
            in tuple(value.feature_id for value in item.unavailable_features)
        )
        reasons = Counter(
            reason
            for item in unavailable
            for unavailable_feature in item.unavailable_features
            if unavailable_feature.feature_id == feature.feature_id
            for reason in unavailable_feature.reason_codes
        )
        output.append(
            StrongLeaderPullbackFeatureCoverageV1(
                feature_id=feature.feature_id,
                source_available_count=expected_count - len(unavailable),
                source_unavailable_count=len(unavailable),
                complete_distribution_observation_count=complete_count,
                availability_rate=_ratio(
                    expected_count - len(unavailable), expected_count
                ),
                unavailable_reason_counts=tuple(
                    StrongLeaderPullbackDiagnosticReasonCountV1(
                        reason_code=reason, count=count
                    )
                    for reason, count in sorted(reasons.items())
                ),
            )
        )
    return tuple(output)


def _numeric_summary(
    feature_id: str,
    values: tuple[Decimal, ...],
) -> StrongLeaderPullbackNumericDiagnosticV1:
    ordered = tuple(sorted(values))
    distinct = len(set(ordered))
    common: dict[str, object] = {
        "feature_id": feature_id,
        "observation_count": len(ordered),
        "distinct_value_count": distinct,
        "duplicate_excess_count": len(ordered) - distinct,
        "duplicate_excess_rate": _ratio(len(ordered) - distinct, len(ordered)),
    }
    if not ordered:
        return StrongLeaderPullbackNumericDiagnosticV1(**common)
    return StrongLeaderPullbackNumericDiagnosticV1(
        **common,
        minimum=_value(ordered[0]),
        p05=_value(_nearest_rank(ordered, Decimal("0.05"))),
        p25=_value(_nearest_rank(ordered, Decimal("0.25"))),
        median=_value(_nearest_rank(ordered, Decimal("0.50"))),
        p75=_value(_nearest_rank(ordered, Decimal("0.75"))),
        p95=_value(_nearest_rank(ordered, Decimal("0.95"))),
        maximum=_value(ordered[-1]),
    )


def _boolean_summary(
    feature_id: str,
    values: tuple[bool, ...],
) -> StrongLeaderPullbackBooleanDiagnosticV1:
    true_count = sum(values)
    return StrongLeaderPullbackBooleanDiagnosticV1(
        feature_id=feature_id,
        observation_count=len(values),
        true_count=true_count,
        false_count=len(values) - true_count,
        true_rate=_ratio(true_count, len(values)),
    )


def _threshold_proximity(
    feature_id: str,
    values: tuple[Decimal, ...],
    thresholds: tuple[Decimal, ...],
) -> StrongLeaderPullbackThresholdProximityV1:
    tolerance = DIAGNOSTIC_TOLERANCES[feature_id]
    near_count = sum(
        min(abs(value - threshold) for threshold in thresholds) <= tolerance
        for value in values
    )
    return StrongLeaderPullbackThresholdProximityV1(
        feature_id=feature_id,
        tolerance=_value(tolerance),
        thresholds=tuple(_value(item) for item in thresholds),
        observation_count=len(values),
        near_threshold_count=near_count,
        near_threshold_rate=_ratio(near_count, len(values)),
    )


def _concentration(
    axis: DiagnosticConcentrationAxis, values: Iterable[str]
) -> StrongLeaderPullbackConcentrationV1:
    counts = tuple(sorted(Counter(values).values(), reverse=True))
    observation_count = sum(counts)
    if observation_count == 0:
        return StrongLeaderPullbackConcentrationV1(
            axis=axis,
            observation_count=0,
            group_count=0,
            maximum_group_count=0,
            maximum_group_share="0.0000",
            top_ten_group_share="0.0000",
            herfindahl_index="0.0000",
        )
    denominator = Decimal(observation_count)
    return StrongLeaderPullbackConcentrationV1(
        axis=axis,
        observation_count=observation_count,
        group_count=len(counts),
        maximum_group_count=counts[0],
        maximum_group_share=_ratio(counts[0], observation_count),
        top_ten_group_share=_ratio(sum(counts[:10]), observation_count),
        herfindahl_index=format(
            sum((Decimal(item) / denominator) ** 2 for item in counts).quantize(
                RATIO_QUANTUM
            ),
            "f",
        ),
    )


def _nearest_rank(values: tuple[Decimal, ...], percentile: Decimal) -> Decimal:
    position = int(
        (percentile * Decimal(len(values))).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    return values[max(0, position - 1)]


def _ratio(numerator: int, denominator: int) -> str:
    result = (
        Decimal("0")
        if denominator == 0
        else (Decimal(numerator) / Decimal(denominator)).quantize(RATIO_QUANTUM)
    )
    return format(result, "f")


def _value(value: Decimal) -> str:
    return format(value.quantize(VALUE_QUANTUM), "f")


def _source_population_fingerprint(
    *,
    plan: CandidateStrategyChronologicalPlanV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    excluded_paths: tuple[StrongLeaderPullbackDiagnosticExcludedPathV1, ...],
) -> str:
    digest = hashlib.sha256()
    digest.update(plan.logical_fingerprint.encode("ascii"))
    for marker, rows in ((b"O", observations), (b"X", excluded_paths)):
        for item in rows:
            digest.update(marker)
            digest.update(
                json.dumps(
                    item.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                ).encode("utf-8")
            )
    return digest.hexdigest()
