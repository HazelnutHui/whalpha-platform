"""Typed mechanics for chronological, outcome-separated strategy research."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .candidate_strategy_evaluation import (
    STRATEGY_EVALUATION_POLICY_FINGERPRINT,
    StrategyEvaluationSplit,
    StrategyMembershipMode,
)
from .candidate_strategy_research import (
    STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
)
from .strong_leader_pullback_method import (
    STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_VERSION,
)


RESEARCH_EXECUTION_CONTRACT_VERSION = "candidate-strategy-research-execution/1.2"
STRONG_LEADER_PULLBACK_OBSERVATION_VERSION = (
    "strong-leader-pullback-observation/1.2"
)


class ResearchSessionExclusionCode(StrEnum):
    FEATURE_WARMUP = "feature_warmup"
    BOUNDARY_PURGE = "boundary_purge"
    BOUNDARY_EMBARGO = "boundary_embargo"
    OUTCOME_NOT_MATURE = "outcome_not_mature"


class StrongLeaderPullbackCohortRole(StrEnum):
    SIGNAL = "signal"
    ELIGIBLE_LEADER_CONTROL = "eligible_leader_control"
    EXCLUDED_CHRONOLOGICAL_BOUNDARY = "excluded_chronological_boundary"
    EXCLUDED_MEMBERSHIP = "excluded_membership"
    EXCLUDED_NOT_LEADER = "excluded_not_leader"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrategyResearchSessionAssignmentV1(FrozenModel):
    session: date
    raw_split: StrategyEvaluationSplit
    usable_for_signal_evaluation: bool
    exclusion_codes: tuple[ResearchSessionExclusionCode, ...]
    maximum_outcome_session: date | None

    @model_validator(mode="after")
    def assignment_reconciles(self) -> "StrategyResearchSessionAssignmentV1":
        if self.exclusion_codes != tuple(sorted(set(self.exclusion_codes))):
            raise ValueError("session exclusion codes must be unique and sorted")
        if self.usable_for_signal_evaluation != (not self.exclusion_codes):
            raise ValueError("session usability differs from exclusion evidence")
        if self.usable_for_signal_evaluation != (
            self.maximum_outcome_session is not None
        ):
            raise ValueError("usable session must bind its maximum outcome session")
        if (
            self.maximum_outcome_session is not None
            and self.maximum_outcome_session <= self.session
        ):
            raise ValueError("maximum outcome session must follow the signal session")
        return self


class CandidateStrategyChronologicalPlanV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[RESEARCH_EXECUTION_CONTRACT_VERSION] = (
        RESEARCH_EXECUTION_CONTRACT_VERSION
    )
    experiment_id: Literal[STRONG_STOCK_PULLBACK_EXPERIMENT_ID] = (
        STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    evaluation_policy_fingerprint: Literal[
        STRATEGY_EVALUATION_POLICY_FINGERPRINT
    ] = STRATEGY_EVALUATION_POLICY_FINGERPRINT
    ordered_sessions: tuple[date, ...] = Field(min_length=252)
    development_last_session: date
    validation_first_session: date
    validation_last_session: date
    holdout_first_session: date
    feature_warmup_sessions: Literal[20] = 20
    maximum_outcome_horizon_sessions: Literal[5] = 5
    purge_sessions: Literal[5] = 5
    embargo_sessions: Literal[5] = 5
    random_split_prohibited: Literal[True] = True
    assignments: tuple[StrategyResearchSessionAssignmentV1, ...]
    raw_split_session_counts: dict[str, int]
    usable_signal_session_counts: dict[str, int]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("ordered_sessions", mode="before")
    @classmethod
    def ordered_unique_sessions(cls, value: Any) -> tuple[date, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("ordered sessions must be a collection")
        sessions = tuple(value)
        if any(isinstance(item, datetime) for item in sessions):
            raise ValueError("ordered sessions must contain dates")
        if sessions != tuple(sorted(set(sessions))):
            raise ValueError("ordered sessions must be unique and chronological")
        return sessions

    @model_validator(mode="after")
    def plan_reconciles(self) -> "CandidateStrategyChronologicalPlanV1":
        if len(self.assignments) != len(self.ordered_sessions) or tuple(
            item.session for item in self.assignments
        ) != self.ordered_sessions:
            raise ValueError("chronological assignments must cover every session")
        expected_boundaries = (
            self.development_last_session,
            self.validation_first_session,
            self.validation_last_session,
            self.holdout_first_session,
        )
        if not (
            expected_boundaries[0]
            < expected_boundaries[1]
            <= expected_boundaries[2]
            < expected_boundaries[3]
        ):
            raise ValueError("chronological split boundaries are invalid")
        split_counts = _split_counts(self.assignments, usable_only=False)
        usable_counts = _split_counts(self.assignments, usable_only=True)
        if self.raw_split_session_counts != split_counts:
            raise ValueError("raw split session counts do not reconcile")
        if self.usable_signal_session_counts != usable_counts:
            raise ValueError("usable split session counts do not reconcile")
        if research_execution_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("chronological plan fingerprint mismatch")
        return self


class StrongLeaderPullbackObservationV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRONG_LEADER_PULLBACK_OBSERVATION_VERSION] = (
        STRONG_LEADER_PULLBACK_OBSERVATION_VERSION
    )
    as_of_session: date
    universe_id: Literal["primary", "secondary"]
    instrument_id: UUID
    ticker: str
    membership_mode: StrategyMembershipMode
    membership_session: date
    membership_included: bool
    relative_strength_20s_percentile: str
    trend_quality_score: str
    pullback_depth_atr: str
    close_above_prior_close: bool
    close_above_prior_high: bool
    pullback_volume_ratio: str
    market_regime: Literal["Defensive", "Balanced", "Risk-on", "Stress"]
    source_max_session: date
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("ticker", mode="before")
    @classmethod
    def normalized_ticker(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ticker must be non-empty")
        return value.strip().upper()

    @model_validator(mode="after")
    def observation_reconciles(self) -> "StrongLeaderPullbackObservationV1":
        if self.source_max_session > self.as_of_session:
            raise ValueError("research observation cannot use a future source session")
        if (
            self.membership_mode is StrategyMembershipMode.POINT_IN_TIME
            and self.membership_session != self.as_of_session
        ):
            raise ValueError("point-in-time membership must match the observation session")
        _bounded_decimal(
            self.relative_strength_20s_percentile,
            "relative_strength_20s_percentile",
            Decimal("0"),
            Decimal("1"),
        )
        _bounded_decimal(
            self.trend_quality_score,
            "trend_quality_score",
            Decimal("0"),
            Decimal("100"),
        )
        _scaled_decimal(
            self.pullback_depth_atr,
            "pullback_depth_atr",
        )
        pullback_volume_ratio = _scaled_decimal(
            self.pullback_volume_ratio,
            "pullback_volume_ratio",
        )
        if pullback_volume_ratio < 0:
            raise ValueError("pullback_volume_ratio cannot be negative")
        if research_execution_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research observation fingerprint mismatch")
        return self


class StrongLeaderPullbackParameterCombinationV1(FrozenModel):
    combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    leadership_gate: str
    pullback_depth_atr_band: str
    recovery_trigger: str
    volume_contraction_ratio_max: str
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def combination_reconciles(self) -> "StrongLeaderPullbackParameterCombinationV1":
        expected = research_execution_fingerprint(
            self,
            exclude={"combination_id", "logical_fingerprint"},
        )
        if self.combination_id != expected or self.logical_fingerprint != expected:
            raise ValueError("parameter combination identity differs")
        return self


class StrongLeaderPullbackCohortAssignmentV1(FrozenModel):
    as_of_session: date
    universe_id: Literal["primary", "secondary"]
    instrument_id: UUID
    observation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameter_combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_split: StrategyEvaluationSplit
    cohort_role: StrongLeaderPullbackCohortRole
    leader_eligible: bool
    setup_triggered: bool
    reason_codes: tuple[str, ...]
    sealed_without_outcomes: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def cohort_reconciles(self) -> "StrongLeaderPullbackCohortAssignmentV1":
        if not self.reason_codes or self.reason_codes != tuple(
            sorted(set(self.reason_codes))
        ):
            raise ValueError("cohort reason codes must be non-empty, unique, and sorted")
        if self.cohort_role is StrongLeaderPullbackCohortRole.SIGNAL:
            if not self.leader_eligible or not self.setup_triggered:
                raise ValueError("signal cohort requires leader and setup eligibility")
        elif self.setup_triggered:
            raise ValueError("only signal cohort may carry a triggered setup")
        if (
            self.cohort_role
            is StrongLeaderPullbackCohortRole.ELIGIBLE_LEADER_CONTROL
            and not self.leader_eligible
        ):
            raise ValueError("leader control requires leadership eligibility")
        if research_execution_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cohort assignment fingerprint mismatch")
        return self


class StrongLeaderPullbackMechanicsBatchV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[RESEARCH_EXECUTION_CONTRACT_VERSION] = (
        RESEARCH_EXECUTION_CONTRACT_VERSION
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    method_version: Literal[STRONG_LEADER_PULLBACK_METHOD_VERSION] = (
        STRONG_LEADER_PULLBACK_METHOD_VERSION
    )
    method_fingerprint: Literal[STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT] = (
        STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    )
    chronological_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameter_combinations: tuple[StrongLeaderPullbackParameterCombinationV1, ...]
    observation_count: int = Field(ge=0)
    assignments: tuple[StrongLeaderPullbackCohortAssignmentV1, ...]
    role_counts: dict[str, int]
    contains_forward_outcomes: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def batch_reconciles(self) -> "StrongLeaderPullbackMechanicsBatchV1":
        if len(self.parameter_combinations) != 24:
            raise ValueError("research mechanics must retain all 24 combinations")
        if len(self.assignments) != self.observation_count * 24:
            raise ValueError("research mechanics assignment count differs")
        counts: dict[str, int] = {}
        for item in self.assignments:
            counts[item.cohort_role.value] = counts.get(item.cohort_role.value, 0) + 1
        if self.role_counts != dict(sorted(counts.items())):
            raise ValueError("research mechanics role counts do not reconcile")
        if research_execution_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research mechanics batch fingerprint mismatch")
        return self


def research_execution_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude=exclude or {"logical_fingerprint"})
    else:
        payload = dict(value)
        for key in exclude or {"logical_fingerprint"}:
            payload.pop(key, None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _split_counts(
    assignments: tuple[StrategyResearchSessionAssignmentV1, ...],
    *,
    usable_only: bool,
) -> dict[str, int]:
    counts = {item.value: 0 for item in (
        StrategyEvaluationSplit.DEVELOPMENT,
        StrategyEvaluationSplit.VALIDATION,
        StrategyEvaluationSplit.HOLDOUT,
    )}
    for item in assignments:
        if not usable_only or item.usable_for_signal_evaluation:
            counts[item.raw_split.value] += 1
    return counts


def _bounded_decimal(
    value: str,
    field_name: str,
    minimum: Decimal,
    maximum: Decimal,
) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a Decimal string") from exc
    if (
        not parsed.is_finite()
        or value != format(parsed.quantize(Decimal("0.0001")), "f")
        or not minimum <= parsed <= maximum
    ):
        raise ValueError(f"{field_name} must use scale 4 within its bounds")
    return parsed


def _scaled_decimal(value: str, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a Decimal string") from exc
    if (
        not parsed.is_finite()
        or value != format(parsed.quantize(Decimal("0.0001")), "f")
    ):
        raise ValueError(f"{field_name} must be finite and use scale 4")
    return parsed
