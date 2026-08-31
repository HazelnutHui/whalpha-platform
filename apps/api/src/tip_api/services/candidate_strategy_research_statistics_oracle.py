"""Independent descriptive Oracle for Quant Research Lab fixture statistics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from tip_api.contracts.analytics.v1 import (
    MINIMUM_COMPARABLE_SESSIONS,
    MINIMUM_SIGNAL_OBSERVATIONS,
    StrategyEvaluationSplit,
    StrategyOutcomeStatus,
    StrongLeaderPullbackCohortOutcomeV1,
    StrongLeaderPullbackCohortRole,
    StrongLeaderPullbackMechanicsBatchV1,
    StrongLeaderPullbackObservationV1,
)


QUANTUM = Decimal("0.0000000001")
COVERAGE_QUANTUM = Decimal("0.0001")


class CandidateStrategyResearchStatisticsOracleError(ValueError):
    """Raised when an Oracle input does not bind the sealed mechanics."""


@dataclass(frozen=True, slots=True)
class ResearchStatisticsOracleSummary:
    parameter_combination_id: str
    evaluation_split: StrategyEvaluationSplit
    horizon_sessions: int
    signal_assigned_count: int
    control_assigned_count: int
    signal_available_count: int
    control_available_count: int
    signal_quarantined_count: int
    control_quarantined_count: int
    signal_other_count: int
    control_other_count: int
    signal_coverage_ratio: str
    control_coverage_ratio: str
    paired_session_count: int
    signal_market_regime_counts: dict[str, int]
    evidence_floor_met: bool
    signal_mean_underlying_return: str | None
    signal_median_underlying_return: str | None
    signal_median_spy_relative_return: str | None
    signal_hit_rate: str | None
    signal_mean_maximum_favorable_excursion: str | None
    signal_mean_maximum_adverse_excursion: str | None
    session_balanced_mean_contrast: str | None


def calculate_research_statistics_oracle(
    *,
    mechanics: StrongLeaderPullbackMechanicsBatchV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    outcomes: tuple[StrongLeaderPullbackCohortOutcomeV1, ...],
    split: StrategyEvaluationSplit,
    selected_combination_id: str | None = None,
) -> tuple[ResearchStatisticsOracleSummary, ...]:
    """Recalculate descriptive statistics without the production evaluator."""

    observation_by_fingerprint = {
        item.logical_fingerprint: item for item in observations
    }
    if len(observation_by_fingerprint) != len(observations):
        raise CandidateStrategyResearchStatisticsOracleError(
            "Oracle observations are not unique"
        )
    assignment_by_fingerprint = {
        item.logical_fingerprint: item for item in mechanics.assignments
    }
    if len(assignment_by_fingerprint) != len(mechanics.assignments):
        raise CandidateStrategyResearchStatisticsOracleError(
            "Oracle assignments are not unique"
        )
    if any(
        item.observation_fingerprint not in observation_by_fingerprint
        for item in mechanics.assignments
    ):
        raise CandidateStrategyResearchStatisticsOracleError(
            "Oracle assignment lacks its observation"
        )
    outcome_by_key = {}
    for outcome in outcomes:
        assignment = assignment_by_fingerprint.get(outcome.assignment_fingerprint)
        if assignment is None or assignment.evaluation_split is not split:
            raise CandidateStrategyResearchStatisticsOracleError(
                "Oracle outcome crosses its requested split"
            )
        key = (outcome.assignment_fingerprint, outcome.horizon_sessions)
        if key in outcome_by_key:
            raise CandidateStrategyResearchStatisticsOracleError(
                "Oracle outcome is duplicated"
            )
        outcome_by_key[key] = outcome
    combination_ids = (
        (selected_combination_id,)
        if selected_combination_id is not None
        else tuple(item.combination_id for item in mechanics.parameter_combinations)
    )
    return tuple(
        _one_summary(
            mechanics=mechanics,
            observations=observation_by_fingerprint,
            outcomes=outcome_by_key,
            split=split,
            combination_id=combination_id,
            horizon=horizon,
        )
        for combination_id in combination_ids
        for horizon in (1, 3, 5)
    )


def _one_summary(
    *,
    mechanics,
    observations,
    outcomes,
    split,
    combination_id,
    horizon,
) -> ResearchStatisticsOracleSummary:
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
    signals = [
        item
        for item in assignments
        if item.cohort_role is StrongLeaderPullbackCohortRole.SIGNAL
    ]
    controls = [
        item
        for item in assignments
        if item.cohort_role
        is StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL
    ]
    signal_available, signal_quarantined, signal_other = _dispositions(
        signals,
        outcomes,
        horizon,
    )
    control_available, control_quarantined, control_other = _dispositions(
        controls,
        outcomes,
        horizon,
    )
    signal_by_session = defaultdict(list)
    control_by_session = defaultdict(list)
    for assignment, outcome in signal_available:
        signal_by_session[assignment.as_of_session].append(
            Decimal(outcome.underlying_price_return or "0")
        )
    for assignment, outcome in control_available:
        control_by_session[assignment.as_of_session].append(
            Decimal(outcome.underlying_price_return or "0")
        )
    contrasts = tuple(
        _mean(signal_by_session[session]) - _mean(control_by_session[session])
        for session in sorted(set(signal_by_session) & set(control_by_session))
    )
    stock = tuple(
        Decimal(outcome.underlying_price_return or "0")
        for _, outcome in signal_available
    )
    relative = tuple(
        Decimal(outcome.relative_to_benchmark_return or "0")
        for _, outcome in signal_available
    )
    favorable = tuple(
        Decimal(outcome.maximum_favorable_excursion or "0")
        for _, outcome in signal_available
    )
    adverse = tuple(
        Decimal(outcome.maximum_adverse_excursion or "0")
        for _, outcome in signal_available
    )
    regimes = {"Balanced": 0, "Defensive": 0, "Risk-on": 0}
    for assignment, _ in signal_available:
        regime = observations[assignment.observation_fingerprint].market_regime
        regimes[regime] += 1
    return ResearchStatisticsOracleSummary(
        parameter_combination_id=combination_id,
        evaluation_split=split,
        horizon_sessions=horizon,
        signal_assigned_count=len(signals),
        control_assigned_count=len(controls),
        signal_available_count=len(signal_available),
        control_available_count=len(control_available),
        signal_quarantined_count=signal_quarantined,
        control_quarantined_count=control_quarantined,
        signal_other_count=signal_other,
        control_other_count=control_other,
        signal_coverage_ratio=_coverage(len(signal_available), len(signals)),
        control_coverage_ratio=_coverage(len(control_available), len(controls)),
        paired_session_count=len(contrasts),
        signal_market_regime_counts=regimes,
        evidence_floor_met=(
            len(signal_available) >= MINIMUM_SIGNAL_OBSERVATIONS
            and len(control_available) >= MINIMUM_SIGNAL_OBSERVATIONS
            and len(contrasts) >= MINIMUM_COMPARABLE_SESSIONS
        ),
        signal_mean_underlying_return=_formatted(_mean(stock) if stock else None),
        signal_median_underlying_return=_formatted(_median(stock)),
        signal_median_spy_relative_return=_formatted(_median(relative)),
        signal_hit_rate=_formatted(
            Decimal(sum(item > 0 for item in stock)) / Decimal(len(stock))
            if stock
            else None
        ),
        signal_mean_maximum_favorable_excursion=_formatted(
            _mean(favorable) if favorable else None
        ),
        signal_mean_maximum_adverse_excursion=_formatted(
            _mean(adverse) if adverse else None
        ),
        session_balanced_mean_contrast=_formatted(
            _mean(contrasts) if contrasts else None
        ),
    )


def _dispositions(assignments, outcomes, horizon):
    available = []
    quarantined = 0
    other = 0
    for assignment in assignments:
        outcome = outcomes.get((assignment.logical_fingerprint, horizon))
        if outcome is None:
            other += 1
        elif outcome.status is StrategyOutcomeStatus.AVAILABLE:
            available.append((assignment, outcome))
        elif outcome.status is StrategyOutcomeStatus.QUARANTINED:
            quarantined += 1
        else:
            other += 1
    return tuple(available), quarantined, other


def _mean(values) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))


def _median(values) -> Decimal | None:
    return Decimal(median(values)) if values else None


def _coverage(available, assigned) -> str:
    value = Decimal("0") if not assigned else Decimal(available) / Decimal(assigned)
    return format(value.quantize(COVERAGE_QUANTUM), "f")


def _formatted(value: Decimal | None) -> str | None:
    return None if value is None else format(value.quantize(QUANTUM), "f")
