"""Independent descriptive Oracle for Quant Research Lab fixture statistics."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from tip_api.contracts.analytics.v1 import (
    MINIMUM_COMPARABLE_SESSIONS,
    MINIMUM_SIGNAL_OBSERVATIONS,
    RESEARCH_BLOCK_LENGTH_SESSIONS,
    RESEARCH_BOOTSTRAP_REPLICATES,
    StrategyEvaluationSplit,
    StrategyOutcomeStatus,
    StrongLeaderPullbackCohortOutcomeV1,
    StrongLeaderPullbackCohortRole,
    StrongLeaderPullbackMechanicsBatchV1,
    StrongLeaderPullbackObservationV1,
)


QUANTUM = Decimal("0.0000000001")
COVERAGE_QUANTUM = Decimal("0.0001")
PROBABILITY_QUANTUM = Decimal("0.000001")
_UINT32_MASK = (1 << 32) - 1
_MT_SIZE = 624


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
    contrast_lower_90pct: str | None
    contrast_upper_90pct: str | None
    one_sided_raw_p_value: str | None
    bootstrap_replicates: int


@dataclass(frozen=True, slots=True)
class ResearchInferenceOracleResult:
    lower_90pct: Decimal
    upper_90pct: Decimal
    one_sided_p_value: Decimal
    replicate_count: int


class _ReferenceMt19937:
    """Independent CPython-compatible integer MT19937 reference."""

    def __init__(self, seed: int) -> None:
        key = []
        remaining = abs(seed)
        while remaining:
            key.append(remaining & _UINT32_MASK)
            remaining >>= 32
        if not key:
            key = [0]
        self._state = [0] * _MT_SIZE
        self._state[0] = 19650218
        for index in range(1, _MT_SIZE):
            previous = self._state[index - 1]
            self._state[index] = (
                1812433253 * (previous ^ (previous >> 30)) + index
            ) & _UINT32_MASK
        index = 1
        key_index = 0
        for _ in range(max(_MT_SIZE, len(key))):
            previous = self._state[index - 1]
            self._state[index] = (
                (self._state[index] ^ ((previous ^ (previous >> 30)) * 1664525))
                + key[key_index]
                + key_index
            ) & _UINT32_MASK
            index += 1
            key_index += 1
            if index >= _MT_SIZE:
                self._state[0] = self._state[-1]
                index = 1
            if key_index >= len(key):
                key_index = 0
        for _ in range(_MT_SIZE - 1):
            previous = self._state[index - 1]
            self._state[index] = (
                (self._state[index] ^ ((previous ^ (previous >> 30)) * 1566083941))
                - index
            ) & _UINT32_MASK
            index += 1
            if index >= _MT_SIZE:
                self._state[0] = self._state[-1]
                index = 1
        self._state[0] = 0x80000000
        self._index = _MT_SIZE

    def randbelow(self, upper: int) -> int:
        if upper <= 0:
            raise CandidateStrategyResearchStatisticsOracleError(
                "Oracle random bound must be positive"
            )
        bits = upper.bit_length()
        value = self._getrandbits(bits)
        while value >= upper:
            value = self._getrandbits(bits)
        return value

    def _getrandbits(self, bits: int) -> int:
        return self._next_uint32() >> (32 - bits)

    def _next_uint32(self) -> int:
        if self._index >= _MT_SIZE:
            self._twist()
        value = self._state[self._index]
        self._index += 1
        value ^= value >> 11
        value ^= (value << 7) & 0x9D2C5680
        value ^= (value << 15) & 0xEFC60000
        value ^= value >> 18
        return value & _UINT32_MASK

    def _twist(self) -> None:
        for index in range(_MT_SIZE):
            combined = (
                (self._state[index] & 0x80000000)
                | (self._state[(index + 1) % _MT_SIZE] & 0x7FFFFFFF)
            )
            value = self._state[(index + 397) % _MT_SIZE] ^ (combined >> 1)
            if combined & 1:
                value ^= 0x9908B0DF
            self._state[index] = value & _UINT32_MASK
        self._index = 0


def calculate_block_bootstrap_inference_oracle(
    values: tuple[Decimal, ...],
    *,
    seed_material: str,
) -> ResearchInferenceOracleResult:
    """Independently reproduce the registered circular-block inference."""

    if not values:
        raise CandidateStrategyResearchStatisticsOracleError(
            "Oracle inference requires observations"
        )
    if not seed_material:
        raise CandidateStrategyResearchStatisticsOracleError(
            "Oracle inference requires seed material"
        )
    count = len(values)
    block_length = min(RESEARCH_BLOCK_LENGTH_SESSIONS, count)
    seed_payload = seed_material + ":" + ",".join(
        format(item, "f") for item in values
    )
    seed = int.from_bytes(
        hashlib.sha256(seed_payload.encode("utf-8")).digest()[:8],
        "big",
    )
    generator = _ReferenceMt19937(seed)
    observed = sum(values, Decimal("0")) / Decimal(count)
    centered = tuple(value - observed for value in values)
    means = []
    null_exceedances = 0
    for _ in range(RESEARCH_BOOTSTRAP_REPLICATES):
        sampled_sum = Decimal("0")
        centered_sum = Decimal("0")
        sampled_count = 0
        while sampled_count < count:
            start = generator.randbelow(count)
            take = min(block_length, count - sampled_count)
            for offset in range(take):
                index = (start + offset) % count
                sampled_sum += values[index]
                centered_sum += centered[index]
            sampled_count += take
        sampled_mean = sampled_sum / Decimal(count)
        means.append(sampled_mean)
        if centered_sum / Decimal(count) >= observed:
            null_exceedances += 1
    means.sort()
    return ResearchInferenceOracleResult(
        lower_90pct=_reference_quantile(means, Decimal("0.05")),
        upper_90pct=_reference_quantile(means, Decimal("0.95")),
        one_sided_p_value=(
            Decimal(null_exceedances + 1)
            / Decimal(RESEARCH_BOOTSTRAP_REPLICATES + 1)
        ),
        replicate_count=RESEARCH_BOOTSTRAP_REPLICATES,
    )


def calculate_holm_adjustment_oracle(
    raw_probabilities: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Independently apply ordered Holm family-wise adjustment."""

    ordered = sorted(raw_probabilities.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, Decimal] = {}
    monotone_floor = Decimal("0")
    family_size = len(ordered)
    for offset, (identifier, probability) in enumerate(ordered):
        if probability < 0 or probability > 1:
            raise CandidateStrategyResearchStatisticsOracleError(
                "Oracle Holm probability is outside [0,1]"
            )
        candidate = min(Decimal("1"), probability * (family_size - offset))
        monotone_floor = max(monotone_floor, candidate)
        adjusted[identifier] = monotone_floor
    return adjusted


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
    evidence_floor_met = (
        len(signal_available) >= MINIMUM_SIGNAL_OBSERVATIONS
        and len(control_available) >= MINIMUM_SIGNAL_OBSERVATIONS
        and len(contrasts) >= MINIMUM_COMPARABLE_SESSIONS
    )
    inference = (
        calculate_block_bootstrap_inference_oracle(
            contrasts,
            seed_material=f"{split.value}:{combination_id}:{horizon}",
        )
        if evidence_floor_met
        else None
    )
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
        evidence_floor_met=evidence_floor_met,
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
        contrast_lower_90pct=(
            _formatted(inference.lower_90pct) if inference else None
        ),
        contrast_upper_90pct=(
            _formatted(inference.upper_90pct) if inference else None
        ),
        one_sided_raw_p_value=(
            _probability(inference.one_sided_p_value) if inference else None
        ),
        bootstrap_replicates=inference.replicate_count if inference else 0,
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


def _probability(value: Decimal) -> str:
    return format(value.quantize(PROBABILITY_QUANTUM), "f")


def _reference_quantile(
    ordered_values: list[Decimal],
    probability: Decimal,
) -> Decimal:
    scaled = probability * Decimal(len(ordered_values) - 1)
    left = int(scaled)
    fraction = scaled - Decimal(left)
    if fraction == 0:
        return ordered_values[left]
    return (
        ordered_values[left] * (Decimal("1") - fraction)
        + ordered_values[left + 1] * fraction
    )
