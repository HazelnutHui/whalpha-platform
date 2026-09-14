"""Sealed, outcome-free inputs for the first strategy research experiment."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime

from .candidate_strategy_evaluation import StrategyMembershipMode
from .candidate_strategy_research import (
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
)
from .candidate_strategy_research_execution import (
    StrongLeaderPullbackObservationV1,
)
from .strong_leader_pullback_method import (
    STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION,
    STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
)


STRONG_LEADER_PULLBACK_INPUT_CONTRACT_VERSION = (
    "strong-leader-pullback-research-input/1.0"
)
STRONG_LEADER_PULLBACK_REQUIRED_DATASET_FAMILIES = (
    "adjustment_ledger",
    "corporate_action",
    "eod_price_bar",
    "instrument_lifecycle",
    "point_in_time_identity",
    "universe_membership",
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackDatasetBindingV1(FrozenModel):
    family: str
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class StrongLeaderPullbackResearchInputBatchV1(FrozenModel):
    """One complete Primary cross-section with no forward outcome information."""

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        STRONG_LEADER_PULLBACK_INPUT_CONTRACT_VERSION
    ] = STRONG_LEADER_PULLBACK_INPUT_CONTRACT_VERSION
    calculation_version: Literal[
        STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION
    ] = STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION
    feature_fingerprint: Literal[
        STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    ] = STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    experiment_fingerprint: Literal[
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    ] = STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    as_of_session: date
    entry_session_date: date
    next_session_open_at: datetime
    universe_id: Literal["primary"] = "primary"
    membership_mode: Literal[StrategyMembershipMode.POINT_IN_TIME] = (
        StrategyMembershipMode.POINT_IN_TIME
    )
    source_sessions: tuple[date, ...] = Field(min_length=21, max_length=21)
    benchmark_instrument_id: UUID
    benchmark_ticker: Literal["SPY"] = "SPY"
    benchmark_20_session_return: str
    readiness_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    membership_publication_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    membership_partition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    membership_knowledge_time_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    market_regime_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cross_section_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_bindings: tuple[StrongLeaderPullbackDatasetBindingV1, ...]
    expected_member_count: int = Field(ge=1)
    observation_count: int = Field(ge=1)
    observations: tuple[StrongLeaderPullbackObservationV1, ...]
    contains_forward_outcomes: Literal[False] = False
    development_authorized: Literal[False] = False
    performance_claims_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("next_session_open_at")
    @classmethod
    def next_open_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("benchmark_20_session_return")
    @classmethod
    def benchmark_return_is_decimal(cls, value: str) -> str:
        try:
            parsed = Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("benchmark return must be a Decimal string") from exc
        if not parsed.is_finite() or value != format(
            parsed.quantize(Decimal("0.0000000001")), "f"
        ):
            raise ValueError("benchmark return must use scale 10")
        return value

    @model_validator(mode="after")
    def batch_reconciles(self) -> "StrongLeaderPullbackResearchInputBatchV1":
        if self.source_sessions != tuple(sorted(set(self.source_sessions))):
            raise ValueError("source sessions must be unique and chronological")
        if self.source_sessions[-1] != self.as_of_session:
            raise ValueError("input batch must end on its as-of session")
        if (
            self.entry_session_date <= self.as_of_session
            or self.next_session_open_at.date() != self.entry_session_date
        ):
            raise ValueError("research entry boundary differs from next-session open")
        families = tuple(item.family for item in self.dataset_bindings)
        if families != tuple(sorted(set(families))) or not set(
            STRONG_LEADER_PULLBACK_REQUIRED_DATASET_FAMILIES
        ).issubset(families):
            raise ValueError("research input requires every required dataset in sorted order")
        keys = tuple(str(item.instrument_id) for item in self.observations)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("research observations must be unique and stable-ID sorted")
        if self.expected_member_count != len(self.observations):
            raise ValueError("complete Primary membership count differs")
        if self.observation_count != len(self.observations):
            raise ValueError("research observation count differs")
        if any(
            item.as_of_session != self.as_of_session
            or item.universe_id != self.universe_id
            or item.membership_mode is not StrategyMembershipMode.POINT_IN_TIME
            or item.membership_session != self.as_of_session
            or not item.membership_included
            or item.source_max_session != self.as_of_session
            for item in self.observations
        ):
            raise ValueError("research observations differ from batch boundaries")
        if research_input_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research input batch fingerprint mismatch")
        return self


def research_input_fingerprint(
    value: BaseModel,
    *,
    exclude: set[str] | None = None,
) -> str:
    payload = value.model_dump(mode="json", exclude=(exclude or set()) | {"logical_fingerprint"})
    return _fingerprint(payload)
