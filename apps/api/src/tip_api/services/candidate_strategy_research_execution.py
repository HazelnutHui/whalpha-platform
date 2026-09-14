"""Pure chronological mechanics for the first Quant Research Lab experiment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import product
from typing import Any

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChronologicalPlanV1,
    CandidateStrategyForwardOutcomeV1,
    CandidateStrategyResearchExperimentV1,
    CandidateStrategySignalV1,
    ResearchSessionExclusionCode,
    StrategyChannel,
    StrategyCorporateActionStatus,
    StrategyEvaluationSplit,
    StrategyMembershipMode,
    StrategyOutcomeStatus,
    StrategyResearchSessionAssignmentV1,
    StrongLeaderPullbackCohortAssignmentV1,
    StrongLeaderPullbackCohortRole,
    StrongLeaderPullbackMechanicsBatchV1,
    StrongLeaderPullbackMethodV1,
    StrongLeaderPullbackObservationV1,
    StrongLeaderPullbackParameterCombinationV1,
    research_execution_fingerprint,
    strategy_channel_logical_fingerprint,
    strong_leader_pullback_method_v1,
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


MINIMUM_RESEARCH_SESSIONS = 252
FEATURE_WARMUP_SESSIONS = 20
MAXIMUM_OUTCOME_HORIZON = 5
PURGE_SESSIONS = 5
EMBARGO_SESSIONS = 5
RETURN_QUANTUM = Decimal("0.0000000001")


class CandidateStrategyResearchExecutionError(ValueError):
    """Raised when research mechanics would violate the frozen design."""


@dataclass(frozen=True, slots=True)
class ResearchOutcomeBarV1:
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class _StrongLeaderPullbackExecutionRules:
    leadership_gates: dict[str, tuple[Decimal, Decimal]]
    pullback_bands: dict[str, tuple[Decimal, Decimal]]
    recovery_triggers: frozenset[str]
    volume_caps: dict[str, Decimal]


def build_candidate_strategy_chronological_plan(
    *,
    ordered_sessions: tuple[date, ...],
    experiment: CandidateStrategyResearchExperimentV1 | None = None,
    calendar: MarketSessionCalendar | None = None,
) -> CandidateStrategyChronologicalPlanV1:
    """Create fixed 50/25/25 splits with explicit purge and embargo gaps."""

    frozen = experiment or strong_stock_pullback_research_experiment_v1()
    _validate_frozen_experiment(frozen)
    if len(ordered_sessions) < MINIMUM_RESEARCH_SESSIONS:
        raise CandidateStrategyResearchExecutionError(
            "chronological research requires at least 252 sessions"
        )
    if ordered_sessions != tuple(sorted(set(ordered_sessions))):
        raise CandidateStrategyResearchExecutionError(
            "research sessions must be unique and chronological"
        )
    session_calendar = calendar or ExchangeCalendar()
    if any(not session_calendar.is_session(item) for item in ordered_sessions):
        raise CandidateStrategyResearchExecutionError(
            "research plan requires XNYS sessions"
        )
    if any(
        session_calendar.next_session(left) != right
        for left, right in zip(ordered_sessions, ordered_sessions[1:])
    ):
        raise CandidateStrategyResearchExecutionError(
            "research plan requires contiguous XNYS sessions"
        )

    count = len(ordered_sessions)
    validation_start = count // 2
    holdout_start = validation_start + count // 4
    assignments: list[StrategyResearchSessionAssignmentV1] = []
    for index, session in enumerate(ordered_sessions):
        split = _raw_split(index, validation_start, holdout_start)
        exclusions: set[ResearchSessionExclusionCode] = set()
        if index < FEATURE_WARMUP_SESSIONS:
            exclusions.add(ResearchSessionExclusionCode.FEATURE_WARMUP)
        if index + MAXIMUM_OUTCOME_HORIZON >= count:
            exclusions.add(ResearchSessionExclusionCode.OUTCOME_NOT_MATURE)
        for boundary in (validation_start, holdout_start):
            if boundary - PURGE_SESSIONS <= index < boundary:
                exclusions.add(ResearchSessionExclusionCode.BOUNDARY_PURGE)
            if boundary <= index < boundary + EMBARGO_SESSIONS:
                exclusions.add(ResearchSessionExclusionCode.BOUNDARY_EMBARGO)
        exclusion_codes = tuple(sorted(exclusions))
        usable = not exclusion_codes
        assignments.append(
            StrategyResearchSessionAssignmentV1(
                session=session,
                raw_split=split,
                usable_for_signal_evaluation=usable,
                exclusion_codes=exclusion_codes,
                maximum_outcome_session=(
                    ordered_sessions[index + MAXIMUM_OUTCOME_HORIZON]
                    if usable
                    else None
                ),
            )
        )
    payload: dict[str, object] = {
        "experiment_id": frozen.experiment_id,
        "experiment_fingerprint": frozen.logical_fingerprint,
        "evaluation_policy_fingerprint": frozen.evaluation_policy_fingerprint,
        "ordered_sessions": ordered_sessions,
        "development_last_session": ordered_sessions[validation_start - 1],
        "validation_first_session": ordered_sessions[validation_start],
        "validation_last_session": ordered_sessions[holdout_start - 1],
        "holdout_first_session": ordered_sessions[holdout_start],
        "feature_warmup_sessions": FEATURE_WARMUP_SESSIONS,
        "maximum_outcome_horizon_sessions": MAXIMUM_OUTCOME_HORIZON,
        "purge_sessions": PURGE_SESSIONS,
        "embargo_sessions": EMBARGO_SESSIONS,
        "random_split_prohibited": True,
        "assignments": tuple(assignments),
        "raw_split_session_counts": _assignment_counts(assignments, usable=False),
        "usable_signal_session_counts": _assignment_counts(assignments, usable=True),
    }
    provisional = CandidateStrategyChronologicalPlanV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return CandidateStrategyChronologicalPlanV1.model_validate(
        {
            **payload,
            "logical_fingerprint": research_execution_fingerprint(provisional),
        }
    )


def build_strong_leader_pullback_observation(
    **values: Any,
) -> StrongLeaderPullbackObservationV1:
    """Seal one source-dated input row without any outcome fields."""

    payload = dict(values)
    provisional = StrongLeaderPullbackObservationV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackObservationV1.model_validate(
        {
            **payload,
            "logical_fingerprint": research_execution_fingerprint(provisional),
        }
    )


def enumerate_strong_leader_pullback_parameters(
    *,
    experiment: CandidateStrategyResearchExperimentV1 | None = None,
    method: StrongLeaderPullbackMethodV1 | None = None,
) -> tuple[StrongLeaderPullbackParameterCombinationV1, ...]:
    """Enumerate exactly the preregistered 24 development combinations."""

    frozen = experiment or strong_stock_pullback_research_experiment_v1()
    canonical_method = method or strong_leader_pullback_method_v1()
    _validate_frozen_experiment(frozen)
    _validate_canonical_method(canonical_method)
    if canonical_method.source_experiment_fingerprint != frozen.logical_fingerprint:
        raise CandidateStrategyResearchExecutionError(
            "method and frozen experiment differ"
        )
    dimensions = {
        item.parameter_id: item.canonical_candidate_values
        for item in canonical_method.parameters
    }
    required = (
        "leadership_gate",
        "pullback_depth_atr_band",
        "recovery_trigger",
        "volume_contraction_ratio_max",
    )
    if tuple(sorted(dimensions)) != tuple(sorted(required)):
        raise CandidateStrategyResearchExecutionError(
            "preregistered parameter dimensions differ"
        )
    combinations: list[StrongLeaderPullbackParameterCombinationV1] = []
    for values in product(*(dimensions[item] for item in required)):
        payload = dict(zip(required, values, strict=True))
        fingerprint = research_execution_fingerprint(payload, exclude=set())
        combinations.append(
            StrongLeaderPullbackParameterCombinationV1(
                **payload,
                combination_id=fingerprint,
                logical_fingerprint=fingerprint,
            )
        )
    if len(combinations) != frozen.parameter_combination_count:
        raise CandidateStrategyResearchExecutionError(
            "parameter enumeration differs from preregistration"
        )
    return tuple(combinations)


def build_strong_leader_pullback_mechanics(
    *,
    plan: CandidateStrategyChronologicalPlanV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    experiment: CandidateStrategyResearchExperimentV1 | None = None,
    method: StrongLeaderPullbackMethodV1 | None = None,
) -> StrongLeaderPullbackMechanicsBatchV1:
    """Assign signal versus same-session eligible-leader control without labels."""

    frozen = experiment or strong_stock_pullback_research_experiment_v1()
    canonical_method = method or strong_leader_pullback_method_v1()
    _validate_frozen_experiment(frozen)
    _validate_canonical_method(canonical_method)
    if canonical_method.source_experiment_fingerprint != frozen.logical_fingerprint:
        raise CandidateStrategyResearchExecutionError(
            "method and frozen experiment differ"
        )
    if plan.experiment_fingerprint != frozen.logical_fingerprint:
        raise CandidateStrategyResearchExecutionError(
            "chronological plan and experiment differ"
        )
    observation_keys = tuple(
        (item.as_of_session, item.universe_id, str(item.instrument_id))
        for item in observations
    )
    if observation_keys != tuple(sorted(set(observation_keys))):
        raise CandidateStrategyResearchExecutionError(
            "research observations must be unique and sorted"
        )
    assignment_by_session = {item.session: item for item in plan.assignments}
    if any(item.as_of_session not in assignment_by_session for item in observations):
        raise CandidateStrategyResearchExecutionError(
            "research observation is outside the chronological plan"
        )
    combinations = enumerate_strong_leader_pullback_parameters(
        experiment=frozen,
        method=canonical_method,
    )
    execution_rules = _execution_rules(canonical_method)
    assignments: list[StrongLeaderPullbackCohortAssignmentV1] = []
    for combination in combinations:
        for observation in observations:
            session_assignment = assignment_by_session[observation.as_of_session]
            role, leader, setup, reasons = _cohort_role(
                observation=observation,
                combination=combination,
                session_assignment=session_assignment,
                execution_rules=execution_rules,
            )
            payload: dict[str, object] = {
                "as_of_session": observation.as_of_session,
                "universe_id": observation.universe_id,
                "instrument_id": observation.instrument_id,
                "observation_fingerprint": observation.logical_fingerprint,
                "parameter_combination_id": combination.combination_id,
                "evaluation_split": session_assignment.raw_split,
                "cohort_role": role,
                "leader_eligible": leader,
                "setup_triggered": setup,
                "reason_codes": reasons,
                "sealed_without_outcomes": True,
            }
            provisional = StrongLeaderPullbackCohortAssignmentV1.model_construct(
                **payload,
                logical_fingerprint="0" * 64,
            )
            assignments.append(
                StrongLeaderPullbackCohortAssignmentV1.model_validate(
                    {
                        **payload,
                        "logical_fingerprint": research_execution_fingerprint(
                            provisional
                        ),
                    }
                )
            )
    role_counts: dict[str, int] = {}
    for item in assignments:
        role_counts[item.cohort_role.value] = role_counts.get(item.cohort_role.value, 0) + 1
    payload = {
        "experiment_fingerprint": frozen.logical_fingerprint,
        "method_version": canonical_method.method_version,
        "method_fingerprint": canonical_method.logical_fingerprint,
        "chronological_plan_fingerprint": plan.logical_fingerprint,
        "parameter_combinations": combinations,
        "observation_count": len(observations),
        "assignments": tuple(assignments),
        "role_counts": dict(sorted(role_counts.items())),
        "contains_forward_outcomes": False,
        "performance_claim_authorized": False,
    }
    provisional_batch = StrongLeaderPullbackMechanicsBatchV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackMechanicsBatchV1.model_validate(
        {
            **payload,
            "logical_fingerprint": research_execution_fingerprint(provisional_batch),
        }
    )


def schedule_pending_strategy_outcomes(
    *,
    signal: CandidateStrategySignalV1,
    plan: CandidateStrategyChronologicalPlanV1,
) -> tuple[CandidateStrategyForwardOutcomeV1, ...]:
    """Create only pending 1/3/5-session labels from a sealed eligible signal."""

    if signal.channel is not StrategyChannel.STRONG_STOCK_PULLBACK:
        raise CandidateStrategyResearchExecutionError(
            "first research execution accepts only strong-stock-pullback signals"
        )
    if not signal.evaluation_eligible or (
        signal.membership_mode is not StrategyMembershipMode.POINT_IN_TIME
    ):
        raise CandidateStrategyResearchExecutionError(
            "pending outcomes require a point-in-time evaluation-eligible signal"
        )
    assignment = next(
        (item for item in plan.assignments if item.session == signal.as_of_session),
        None,
    )
    if (
        assignment is None
        or not assignment.usable_for_signal_evaluation
        or assignment.raw_split is not signal.evaluation_split
    ):
        raise CandidateStrategyResearchExecutionError(
            "signal is outside its usable chronological split"
        )
    index = plan.ordered_sessions.index(signal.as_of_session)
    outcomes: list[CandidateStrategyForwardOutcomeV1] = []
    for horizon in (1, 3, 5):
        path = plan.ordered_sessions[index + 1 : index + 1 + horizon]
        if len(path) != horizon:
            raise CandidateStrategyResearchExecutionError(
                "signal outcome path is not matureable inside the plan"
            )
        payload: dict[str, object] = {
            "signal_id": signal.signal_id,
            "signal_logical_fingerprint": signal.logical_fingerprint,
            "signal_session": signal.as_of_session,
            "universe_id": signal.universe_id,
            "instrument_id": signal.instrument_id,
            "channel": signal.channel,
            "horizon_sessions": horizon,
            "expected_entry_session": path[0],
            "expected_exit_session": path[-1],
            "expected_path_sessions": path,
            "observed_entry_session": None,
            "observed_exit_session": None,
            "status": StrategyOutcomeStatus.PENDING,
            "entry_price": None,
            "exit_price": None,
            "underlying_price_return": None,
            "benchmark_price_return": None,
            "relative_to_benchmark_return": None,
            "maximum_favorable_excursion": None,
            "maximum_adverse_excursion": None,
            "corporate_action_status": StrategyCorporateActionStatus.UNAVAILABLE,
            "source_eod_fingerprint": None,
            "label_source_max_session": None,
            "reason_codes": ("outcome_not_yet_mature",),
        }
        outcomes.append(_build_forward_outcome(payload))
    return tuple(outcomes)


def mature_strategy_outcome(
    *,
    signal: CandidateStrategySignalV1,
    pending: CandidateStrategyForwardOutcomeV1,
    known_through_session: date,
    instrument_bars: tuple[ResearchOutcomeBarV1, ...] = (),
    benchmark_bars: tuple[ResearchOutcomeBarV1, ...] = (),
    corporate_action_status: StrategyCorporateActionStatus = (
        StrategyCorporateActionStatus.CLEAR
    ),
    source_eod_fingerprint: str | None = None,
    quarantine_reason_codes: tuple[str, ...] = (),
) -> CandidateStrategyForwardOutcomeV1:
    """Attach labels only after the exact future path is knowable."""

    _validate_pending_binding(signal, pending)
    if known_through_session < pending.expected_exit_session:
        if instrument_bars or benchmark_bars or source_eod_fingerprint is not None:
            raise CandidateStrategyResearchExecutionError(
                "immature outcome cannot receive future source evidence"
            )
        return pending
    if source_eod_fingerprint is None or len(source_eod_fingerprint) != 64:
        raise CandidateStrategyResearchExecutionError(
            "mature outcome requires exact EOD source evidence"
        )
    if corporate_action_status is StrategyCorporateActionStatus.REVIEW_REQUIRED:
        if not quarantine_reason_codes:
            raise CandidateStrategyResearchExecutionError(
                "corporate-action quarantine requires reasons"
            )
        payload = pending.model_dump(mode="python")
        payload.update(
            {
                "observed_entry_session": pending.expected_entry_session,
                "observed_exit_session": pending.expected_exit_session,
                "status": StrategyOutcomeStatus.QUARANTINED,
                "corporate_action_status": corporate_action_status,
                "source_eod_fingerprint": source_eod_fingerprint,
                "label_source_max_session": pending.expected_exit_session,
                "reason_codes": tuple(sorted(set(quarantine_reason_codes))),
            }
        )
        return _build_forward_outcome(payload)
    if corporate_action_status is not StrategyCorporateActionStatus.CLEAR:
        raise CandidateStrategyResearchExecutionError(
            "mature numeric outcome requires clear corporate-action status"
        )
    _validate_outcome_bars(pending, instrument_bars, "instrument")
    _validate_outcome_bars(pending, benchmark_bars, "benchmark")
    entry = instrument_bars[0].open
    exit_price = instrument_bars[-1].close
    stock_return = _return(exit_price, entry)
    benchmark_return = _return(benchmark_bars[-1].close, benchmark_bars[0].open)
    favorable = max(
        Decimal("0"),
        *(_return(item.high, entry) for item in instrument_bars),
    )
    adverse = min(
        Decimal("0"),
        *(_return(item.low, entry) for item in instrument_bars),
    )
    payload = pending.model_dump(mode="python")
    payload.update(
        {
            "observed_entry_session": pending.expected_entry_session,
            "observed_exit_session": pending.expected_exit_session,
            "status": StrategyOutcomeStatus.AVAILABLE,
            "entry_price": _decimal_string(entry),
            "exit_price": _decimal_string(exit_price),
            "underlying_price_return": _decimal_string(stock_return),
            "benchmark_price_return": _decimal_string(benchmark_return),
            "relative_to_benchmark_return": _decimal_string(
                (stock_return - benchmark_return).quantize(RETURN_QUANTUM)
            ),
            "maximum_favorable_excursion": _decimal_string(favorable),
            "maximum_adverse_excursion": _decimal_string(adverse),
            "corporate_action_status": corporate_action_status,
            "source_eod_fingerprint": source_eod_fingerprint,
            "label_source_max_session": pending.expected_exit_session,
            "reason_codes": (),
        }
    )
    return _build_forward_outcome(payload)


def _build_forward_outcome(
    payload: dict[str, object],
) -> CandidateStrategyForwardOutcomeV1:
    normalized = dict(payload)
    normalized.pop("logical_fingerprint", None)
    provisional = CandidateStrategyForwardOutcomeV1.model_construct(
        **normalized,
        logical_fingerprint="0" * 64,
    )
    normalized = provisional.model_dump(mode="python")
    normalized["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        provisional,
        exclude={"logical_fingerprint"},
    )
    return CandidateStrategyForwardOutcomeV1.model_validate(normalized)


def _cohort_role(
    *,
    observation: StrongLeaderPullbackObservationV1,
    combination: StrongLeaderPullbackParameterCombinationV1,
    session_assignment: StrategyResearchSessionAssignmentV1,
    execution_rules: _StrongLeaderPullbackExecutionRules,
) -> tuple[StrongLeaderPullbackCohortRole, bool, bool, tuple[str, ...]]:
    if not session_assignment.usable_for_signal_evaluation:
        return (
            StrongLeaderPullbackCohortRole.EXCLUDED_CHRONOLOGICAL_BOUNDARY,
            False,
            False,
            tuple(
                sorted(f"session_{item.value}" for item in session_assignment.exclusion_codes)
            ),
        )
    if (
        observation.membership_mode is not StrategyMembershipMode.POINT_IN_TIME
        or observation.membership_session != observation.as_of_session
        or not observation.membership_included
    ):
        return (
            StrongLeaderPullbackCohortRole.EXCLUDED_MEMBERSHIP,
            False,
            False,
            ("point_in_time_membership_not_eligible",),
        )
    try:
        rs_min, trend_min = execution_rules.leadership_gates[
            combination.leadership_gate
        ]
    except KeyError as exc:
        raise CandidateStrategyResearchExecutionError(
            "unknown preregistered leadership gate"
        ) from exc
    rs = Decimal(observation.relative_strength_20s_percentile)
    trend = Decimal(observation.trend_quality_score)
    leader = rs >= rs_min and trend >= trend_min
    if not leader:
        return (
            StrongLeaderPullbackCohortRole.EXCLUDED_NOT_LEADER,
            False,
            False,
            ("leadership_gate_not_met",),
        )
    try:
        depth_min, depth_max = execution_rules.pullback_bands[
            combination.pullback_depth_atr_band
        ]
    except KeyError as exc:
        raise CandidateStrategyResearchExecutionError(
            "unknown preregistered pullback band"
        ) from exc
    depth = Decimal(observation.pullback_depth_atr)
    volume = Decimal(observation.pullback_volume_ratio)
    depth_ok = depth_min <= depth <= depth_max
    if combination.recovery_trigger not in execution_rules.recovery_triggers:
        raise CandidateStrategyResearchExecutionError(
            "unknown preregistered recovery trigger"
        )
    recovery_ok = (
        observation.close_above_prior_close
        if combination.recovery_trigger == "close_above_prior_close"
        else observation.close_above_prior_high
    )
    try:
        volume_cap = execution_rules.volume_caps[
            combination.volume_contraction_ratio_max
        ]
    except KeyError as exc:
        raise CandidateStrategyResearchExecutionError(
            "unknown preregistered volume cap"
        ) from exc
    volume_ok = volume <= volume_cap
    if depth_ok and recovery_ok and volume_ok:
        return (
            StrongLeaderPullbackCohortRole.SIGNAL,
            True,
            True,
            ("all_registered_setup_rules_met",),
        )
    reasons = []
    if not depth_ok:
        reasons.append("pullback_depth_outside_band")
    if not recovery_ok:
        reasons.append("recovery_trigger_not_met")
    if not volume_ok:
        reasons.append("volume_contraction_above_cap")
    return (
        StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL,
        True,
        False,
        tuple(sorted(reasons)),
    )


def _validate_pending_binding(
    signal: CandidateStrategySignalV1,
    pending: CandidateStrategyForwardOutcomeV1,
) -> None:
    if pending.status is not StrategyOutcomeStatus.PENDING:
        raise CandidateStrategyResearchExecutionError("only pending outcome may mature")
    if (
        pending.signal_id != signal.signal_id
        or pending.signal_logical_fingerprint != signal.logical_fingerprint
        or pending.signal_session != signal.as_of_session
        or pending.universe_id != signal.universe_id
        or pending.instrument_id != signal.instrument_id
        or pending.channel is not signal.channel
    ):
        raise CandidateStrategyResearchExecutionError("pending outcome and signal differ")


def _validate_outcome_bars(
    pending: CandidateStrategyForwardOutcomeV1,
    bars: tuple[ResearchOutcomeBarV1, ...],
    label: str,
) -> None:
    if tuple(item.session for item in bars) != pending.expected_path_sessions:
        raise CandidateStrategyResearchExecutionError(
            f"{label} bars do not match the exact expected path"
        )
    for item in bars:
        values = (item.open, item.high, item.low, item.close)
        if any(not value.is_finite() or value <= 0 for value in values):
            raise CandidateStrategyResearchExecutionError(
                f"{label} bar contains invalid prices"
            )
        if item.high < max(item.open, item.close) or item.low > min(item.open, item.close):
            raise CandidateStrategyResearchExecutionError(
                f"{label} bar OHLC does not reconcile"
            )


def _validate_frozen_experiment(
    experiment: CandidateStrategyResearchExperimentV1,
) -> None:
    expected = strong_stock_pullback_research_experiment_v1()
    if experiment != expected:
        raise CandidateStrategyResearchExecutionError(
            "research execution requires the exact frozen first experiment"
        )


def _raw_split(
    index: int,
    validation_start: int,
    holdout_start: int,
) -> StrategyEvaluationSplit:
    if index < validation_start:
        return StrategyEvaluationSplit.DEVELOPMENT
    if index < holdout_start:
        return StrategyEvaluationSplit.VALIDATION
    return StrategyEvaluationSplit.HOLDOUT


def _assignment_counts(
    assignments: list[StrategyResearchSessionAssignmentV1],
    *,
    usable: bool,
) -> dict[str, int]:
    counts = {
        StrategyEvaluationSplit.DEVELOPMENT.value: 0,
        StrategyEvaluationSplit.VALIDATION.value: 0,
        StrategyEvaluationSplit.HOLDOUT.value: 0,
    }
    for item in assignments:
        if not usable or item.usable_for_signal_evaluation:
            counts[item.raw_split.value] += 1
    return counts


def _execution_rules(
    method: StrongLeaderPullbackMethodV1,
) -> _StrongLeaderPullbackExecutionRules:
    values = {
        item.parameter_id: item.canonical_candidate_values
        for item in method.parameters
    }
    leadership_pattern = re.compile(
        r"^rs20_percentile_gte_(\d+\.\d+)_and_trend_quality_gte_(\d+)$"
    )
    band_pattern = re.compile(r"^(\d+\.\d+)_to_(\d+\.\d+)$")
    leadership: dict[str, tuple[Decimal, Decimal]] = {}
    for value in values["leadership_gate"]:
        match = leadership_pattern.fullmatch(value)
        if match is None:
            raise CandidateStrategyResearchExecutionError(
                "canonical leadership gate is not executable"
            )
        leadership[value] = (Decimal(match[1]), Decimal(match[2]))
    bands: dict[str, tuple[Decimal, Decimal]] = {}
    for value in values["pullback_depth_atr_band"]:
        match = band_pattern.fullmatch(value)
        if match is None:
            raise CandidateStrategyResearchExecutionError(
                "canonical pullback band is not executable"
            )
        bounds = (Decimal(match[1]), Decimal(match[2]))
        if bounds[0] > bounds[1]:
            raise CandidateStrategyResearchExecutionError(
                "canonical pullback band is reversed"
            )
        bands[value] = bounds
    recoveries = frozenset(values["recovery_trigger"])
    if recoveries != frozenset(
        {"close_above_prior_close", "close_above_prior_high"}
    ):
        raise CandidateStrategyResearchExecutionError(
            "canonical recovery triggers are not executable"
        )
    volume_caps = {
        value: Decimal(value)
        for value in values["volume_contraction_ratio_max"]
    }
    return _StrongLeaderPullbackExecutionRules(
        leadership_gates=leadership,
        pullback_bands=bands,
        recovery_triggers=recoveries,
        volume_caps=volume_caps,
    )


def _validate_canonical_method(method: StrongLeaderPullbackMethodV1) -> None:
    if method != strong_leader_pullback_method_v1():
        raise CandidateStrategyResearchExecutionError(
            "research execution requires the exact canonical first method"
        )


def _return(exit_price: Decimal, entry_price: Decimal) -> Decimal:
    return (exit_price / entry_price - Decimal("1")).quantize(RETURN_QUANTUM)


def _decimal_string(value: Decimal) -> str:
    return format(value.quantize(RETURN_QUANTUM), "f")
