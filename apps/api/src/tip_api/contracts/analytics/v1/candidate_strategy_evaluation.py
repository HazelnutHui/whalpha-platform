"""Point-in-time signal and later outcome contracts for strategy evaluation."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_channel import (
    StrategyChannel,
    StrategyChannelStatus,
    strategy_channel_logical_fingerprint,
)


STRATEGY_SIGNAL_CONTRACT_VERSION = "candidate-strategy-signal/1.0"
STRATEGY_OUTCOME_CONTRACT_VERSION = "candidate-strategy-forward-outcome/1.0"
STRATEGY_EVALUATION_POLICY_VERSION = "candidate-strategy-evaluation-policy/1.0"


class StrategyEvaluationSplit(StrEnum):
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    HOLDOUT = "holdout"
    WALK_FORWARD = "walk_forward"


class StrategyMembershipMode(StrEnum):
    POINT_IN_TIME = "point_in_time"
    CURRENT_AS_OF_CONSTITUENT_REPLAY = "current_as_of_constituent_replay"


class StrategyOutcomeStatus(StrEnum):
    PENDING = "pending"
    AVAILABLE = "available"
    QUARANTINED = "quarantined"
    UNAVAILABLE = "unavailable"


class StrategyCorporateActionStatus(StrEnum):
    CLEAR = "clear"
    REVIEW_REQUIRED = "review_required"
    UNAVAILABLE = "unavailable"


_POLICY_PAYLOAD = {
    "policy_version": STRATEGY_EVALUATION_POLICY_VERSION,
    "minimum_research_history_sessions": 252,
    "stronger_regime_history_sessions": 504,
    "minimum_reported_regime_observations": 60,
    "development_fraction": "0.5000",
    "validation_fraction": "0.2500",
    "holdout_fraction": "0.2500",
    "forward_horizons_sessions": (1, 3, 5),
    "entry_basis": "next_session_open",
    "exit_basis": "horizon_session_close",
    "maximum_label_horizon_sessions": 5,
    "embargo_sessions": 5,
    "overlapping_labels_purged": True,
    "random_split_prohibited": True,
    "point_in_time_membership_required_for_performance_claims": True,
    "current_constituent_replay_research_only": True,
    "signals_sealed_before_outcomes": True,
    "underlying_stock_result_not_option_return": True,
    "transaction_cost_scenarios_bps_per_side": (0, 10, 25, 50),
}
STRATEGY_EVALUATION_POLICY_FINGERPRINT = hashlib.sha256(
    json.dumps(
        _POLICY_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CandidateStrategyEvaluationPolicyV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal[STRATEGY_EVALUATION_POLICY_VERSION] = STRATEGY_EVALUATION_POLICY_VERSION
    policy_fingerprint: Literal[STRATEGY_EVALUATION_POLICY_FINGERPRINT] = (
        STRATEGY_EVALUATION_POLICY_FINGERPRINT
    )
    minimum_research_history_sessions: Literal[252] = 252
    stronger_regime_history_sessions: Literal[504] = 504
    minimum_reported_regime_observations: Literal[60] = 60
    development_fraction: Literal["0.5000"] = "0.5000"
    validation_fraction: Literal["0.2500"] = "0.2500"
    holdout_fraction: Literal["0.2500"] = "0.2500"
    forward_horizons_sessions: tuple[Literal[1], Literal[3], Literal[5]] = (1, 3, 5)
    entry_basis: Literal["next_session_open"] = "next_session_open"
    exit_basis: Literal["horizon_session_close"] = "horizon_session_close"
    maximum_label_horizon_sessions: Literal[5] = 5
    embargo_sessions: Literal[5] = 5
    overlapping_labels_purged: Literal[True] = True
    random_split_prohibited: Literal[True] = True
    point_in_time_membership_required_for_performance_claims: Literal[True] = True
    current_constituent_replay_research_only: Literal[True] = True
    signals_sealed_before_outcomes: Literal[True] = True
    underlying_stock_result_not_option_return: Literal[True] = True
    transaction_cost_scenarios_bps_per_side: tuple[Literal[0], Literal[10], Literal[25], Literal[50]] = (
        0,
        10,
        25,
        50,
    )


class CandidateStrategySignalV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_SIGNAL_CONTRACT_VERSION] = STRATEGY_SIGNAL_CONTRACT_VERSION
    evaluation_policy_fingerprint: Literal[STRATEGY_EVALUATION_POLICY_FINGERPRINT] = (
        STRATEGY_EVALUATION_POLICY_FINGERPRINT
    )
    signal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    channel: StrategyChannel
    channel_status: StrategyChannelStatus
    channel_score: str | None
    within_channel_rank: int | None = Field(default=None, ge=1)
    assessment_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_market_regime_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sessions: tuple[date, ...] = Field(min_length=1)
    membership_mode: StrategyMembershipMode
    membership_session: date
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    membership_methodology_version: str
    evaluation_eligible: bool
    evaluation_split: StrategyEvaluationSplit
    limitation_codes: tuple[str, ...]
    sealed_without_outcomes: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def signal_reconciles(self) -> "CandidateStrategySignalV1":
        if self.signal_id != candidate_strategy_signal_id(
            as_of_session=self.as_of_session,
            universe_id=self.universe_id,
            instrument_id=self.instrument_id,
            channel=self.channel,
            assessment_logical_fingerprint=self.assessment_logical_fingerprint,
        ):
            raise ValueError("strategy signal ID differs from its sealed business identity")
        if self.source_sessions != tuple(sorted(set(self.source_sessions))):
            raise ValueError("strategy signal source sessions must be unique and ordered")
        if self.source_sessions[-1] > self.as_of_session:
            raise ValueError("strategy signal cannot use a future source session")
        if self.membership_mode is StrategyMembershipMode.POINT_IN_TIME:
            if self.membership_session != self.as_of_session:
                raise ValueError("point-in-time membership must match the signal session")
        elif self.evaluation_eligible or "current_constituent_replay_not_performance_eligible" not in self.limitation_codes:
            raise ValueError("current-constituent replay must remain research-only and explicitly limited")
        if self.channel_status is StrategyChannelStatus.UNAVAILABLE and self.evaluation_eligible:
            raise ValueError("an unavailable strategy result cannot enter performance evaluation")
        if self.evaluation_eligible and self.membership_mode is not StrategyMembershipMode.POINT_IN_TIME:
            raise ValueError("performance evaluation requires point-in-time membership")
        if (self.channel_score is None) != (self.channel_status is StrategyChannelStatus.UNAVAILABLE):
            raise ValueError("strategy signal score availability differs from channel status")
        if self.channel_score is not None:
            _channel_score(self.channel_score)
        if self.channel_status in {
            StrategyChannelStatus.ADVANCE_TO_RESEARCH,
            StrategyChannelStatus.WATCH_FOR_TRIGGER,
        }:
            if self.within_channel_rank is None:
                raise ValueError("ranked strategy status requires its sealed within-channel rank")
        elif self.within_channel_rank is not None:
            raise ValueError("unranked strategy status cannot carry a rank")
        if strategy_channel_logical_fingerprint(
            self,
            exclude={"logical_fingerprint"},
        ) != self.logical_fingerprint:
            raise ValueError("strategy signal logical fingerprint mismatch")
        return self


class CandidateStrategyForwardOutcomeV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_OUTCOME_CONTRACT_VERSION] = STRATEGY_OUTCOME_CONTRACT_VERSION
    evaluation_policy_fingerprint: Literal[STRATEGY_EVALUATION_POLICY_FINGERPRINT] = (
        STRATEGY_EVALUATION_POLICY_FINGERPRINT
    )
    signal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    signal_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    signal_session: date
    universe_id: str
    instrument_id: UUID
    channel: StrategyChannel
    horizon_sessions: Literal[1, 3, 5]
    expected_entry_session: date
    expected_exit_session: date
    expected_path_sessions: tuple[date, ...] = Field(min_length=1, max_length=5)
    observed_entry_session: date | None
    observed_exit_session: date | None
    status: StrategyOutcomeStatus
    return_basis: Literal["next_session_open_to_horizon_session_close"] = (
        "next_session_open_to_horizon_session_close"
    )
    entry_price: str | None
    exit_price: str | None
    underlying_price_return: str | None
    benchmark_price_return: str | None
    relative_to_benchmark_return: str | None
    maximum_favorable_excursion: str | None
    maximum_adverse_excursion: str | None
    corporate_action_status: StrategyCorporateActionStatus
    source_eod_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    label_source_max_session: date | None
    reason_codes: tuple[str, ...]
    underlying_stock_result_not_option_return: Literal[True] = True
    transaction_costs_not_applied: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def outcome_reconciles(self) -> "CandidateStrategyForwardOutcomeV1":
        if not self.signal_session < self.expected_entry_session <= self.expected_exit_session:
            raise ValueError("strategy outcome sessions must follow the sealed signal")
        if (
            len(self.expected_path_sessions) != self.horizon_sessions
            or self.expected_path_sessions != tuple(sorted(set(self.expected_path_sessions)))
            or self.expected_path_sessions[0] != self.expected_entry_session
            or self.expected_path_sessions[-1] != self.expected_exit_session
            or any(session <= self.signal_session for session in self.expected_path_sessions)
        ):
            raise ValueError("strategy outcome path must contain the exact ordered future horizon")
        values = (
            self.entry_price,
            self.exit_price,
            self.underlying_price_return,
            self.benchmark_price_return,
            self.relative_to_benchmark_return,
            self.maximum_favorable_excursion,
            self.maximum_adverse_excursion,
        )
        if self.status is StrategyOutcomeStatus.AVAILABLE:
            if (
                self.observed_entry_session != self.expected_entry_session
                or self.observed_exit_session != self.expected_exit_session
                or self.label_source_max_session != self.expected_exit_session
                or self.source_eod_fingerprint is None
                or self.corporate_action_status is not StrategyCorporateActionStatus.CLEAR
                or any(item is None for item in values)
            ):
                raise ValueError("available strategy outcome requires complete clear matured labels")
            entry = _decimal(self.entry_price, "entry price")
            exit_price = _decimal(self.exit_price, "exit price")
            stock_return = _decimal(self.underlying_price_return, "underlying return")
            benchmark_return = _decimal(self.benchmark_price_return, "benchmark return")
            relative_return = _decimal(self.relative_to_benchmark_return, "relative return")
            favorable = _decimal(self.maximum_favorable_excursion, "maximum favorable excursion")
            adverse = _decimal(self.maximum_adverse_excursion, "maximum adverse excursion")
            if entry <= 0 or exit_price <= 0 or favorable < 0 or adverse > 0:
                raise ValueError("strategy outcome price or excursion sign differs")
            expected_return = (exit_price / entry - Decimal("1")).quantize(Decimal("0.0000000001"))
            if stock_return != expected_return or relative_return != (stock_return - benchmark_return).quantize(
                Decimal("0.0000000001")
            ):
                raise ValueError("strategy outcome return arithmetic does not reconcile")
        elif self.status is StrategyOutcomeStatus.PENDING:
            if (
                any(item is not None for item in values)
                or self.observed_entry_session is not None
                or self.observed_exit_session is not None
                or self.label_source_max_session is not None
                or self.source_eod_fingerprint is not None
                or self.corporate_action_status is not StrategyCorporateActionStatus.UNAVAILABLE
                or not self.reason_codes
            ):
                raise ValueError("pending strategy outcome cannot carry future labels")
        else:
            if any(item is not None for item in values):
                raise ValueError("unavailable or quarantined outcome cannot feed performance values")
            if not self.reason_codes:
                raise ValueError("unavailable or quarantined outcome requires a reason")
            if (
                self.status is StrategyOutcomeStatus.QUARANTINED
                and self.corporate_action_status is not StrategyCorporateActionStatus.REVIEW_REQUIRED
            ):
                raise ValueError("quarantined outcome requires corporate-action review")
            if (
                self.status is StrategyOutcomeStatus.UNAVAILABLE
                and self.corporate_action_status is StrategyCorporateActionStatus.REVIEW_REQUIRED
            ):
                raise ValueError("corporate-action review must use quarantined outcome status")
        if self.label_source_max_session is not None and self.label_source_max_session <= self.signal_session:
            raise ValueError("strategy outcome labels must be strictly later than the signal")
        if strategy_channel_logical_fingerprint(
            self,
            exclude={"logical_fingerprint"},
        ) != self.logical_fingerprint:
            raise ValueError("strategy outcome logical fingerprint mismatch")
        return self


def candidate_strategy_signal_id(
    *,
    as_of_session: date,
    universe_id: str,
    instrument_id: UUID,
    channel: StrategyChannel,
    assessment_logical_fingerprint: str,
) -> str:
    """Create the stable business identifier for one sealed channel signal."""

    return hashlib.sha256(
        json.dumps(
            {
                "as_of_session": as_of_session.isoformat(),
                "universe_id": universe_id,
                "instrument_id": str(instrument_id),
                "channel": channel.value,
                "assessment_logical_fingerprint": assessment_logical_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _channel_score(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("strategy signal score must be a Decimal string") from exc
    if (
        not parsed.is_finite()
        or value != format(parsed.quantize(Decimal("0.0001")), "f")
        or not Decimal("0") <= parsed <= Decimal("100")
    ):
        raise ValueError("strategy signal score must use scale 4 within [0,100]")
    return parsed


def _decimal(value: str | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"{label} is required")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a Decimal string") from exc
    if not parsed.is_finite() or value != format(parsed.quantize(Decimal("0.0000000001")), "f"):
        raise ValueError(f"{label} must be finite and use scale 10")
    return parsed
