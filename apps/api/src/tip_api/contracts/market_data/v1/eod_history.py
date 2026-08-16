"""Provider-neutral contracts for point-in-time EOD history readiness."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EodHistoryMethodologyMode(StrEnum):
    CURRENT_AS_OF_CONSTITUENT_LIQUIDITY = "current_as_of_constituent_liquidity"
    POINT_IN_TIME_HISTORICAL_PANEL = "point_in_time_historical_panel"


class EodHistoryReadinessStatus(StrEnum):
    READY = "ready"
    INSUFFICIENT_HISTORY = "insufficient_history"
    CORRUPT_OR_UNAVAILABLE = "corrupt_or_unavailable"


class TrailingLiquidityEligibilityStatus(StrEnum):
    PASSED = "passed"
    BELOW_PRICE_THRESHOLD = "below_price_threshold"
    BELOW_LIQUIDITY_THRESHOLD = "below_liquidity_threshold"
    INSUFFICIENT_HISTORY = "insufficient_history"
    MISSING_PREVIOUS_BAR = "missing_previous_bar"
    IDENTITY_REFERENCE_FAILURE = "identity_reference_failure"
    DATA_QUALITY_FAILURE = "data_quality_failure"


class EodSessionIntegrityV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    session_date: date
    record_count: int = Field(ge=0)
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    parquet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_snapshot_date: date
    identity_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    duplicate_instrument_session_count: int = Field(ge=0)
    multiple_latest_revision_count: int = Field(ge=0)
    future_identity_reference_count: int = Field(ge=0)


class EodHistoryWindowDescriptorV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calendar_name: str
    calendar_version: str
    analysis_session: date
    previous_session: date
    window_start: date
    window_end: date
    expected_session_count: int = Field(ge=1)
    expected_sessions: tuple[date, ...]
    completed_sessions: tuple[date, ...]
    missing_sessions: tuple[date, ...]
    corrupt_or_unavailable_sessions: tuple[date, ...]
    readiness_status: EodHistoryReadinessStatus
    methodology_mode: EodHistoryMethodologyMode
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_reconciliation(self) -> "EodHistoryWindowDescriptorV1":
        if len(self.expected_sessions) != self.expected_session_count:
            raise ValueError("expected session count does not reconcile")
        if not self.expected_sessions or self.window_start != self.expected_sessions[0] or self.window_end != self.expected_sessions[-1]:
            raise ValueError("history window boundaries do not reconcile")
        if self.previous_session != self.window_end or self.analysis_session in self.expected_sessions:
            raise ValueError("analysis session must be excluded and window must end at previous session")
        groups = set(self.completed_sessions), set(self.missing_sessions), set(self.corrupt_or_unavailable_sessions)
        if any(left & right for index, left in enumerate(groups) for right in groups[index + 1 :]):
            raise ValueError("session states overlap")
        if set().union(*groups) != set(self.expected_sessions):
            raise ValueError("session states do not reconcile")
        return self


class TrailingLiquidityResultV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    analysis_session: date
    window_start: date
    window_end: date
    expected_observation_count: Literal[20] = 20
    observed_observation_count: int = Field(ge=0, le=20)
    missing_observation_count: int = Field(ge=0, le=20)
    median_dollar_volume_proxy: Decimal | None
    threshold: Decimal
    price_gate_status: str
    liquidity_gate_status: str
    eligibility_status: TrailingLiquidityEligibilityStatus
    reason_codes: tuple[str, ...]
    source_session_fingerprints: tuple[tuple[date, str], ...]
    methodology_mode: EodHistoryMethodologyMode
    policy_version: str
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_counts(self) -> "TrailingLiquidityResultV1":
        if self.observed_observation_count + self.missing_observation_count != 20:
            raise ValueError("observation counts do not reconcile")
        if self.observed_observation_count < 20 and self.median_dollar_volume_proxy is not None:
            raise ValueError("incomplete history cannot produce a 20-session median")
        return self


class HistoricalEodBackfillPlanV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    required_eod_sessions: tuple[date, ...]
    existing_eod_sessions: tuple[date, ...]
    missing_eod_sessions: tuple[date, ...]
    corrupt_eod_sessions: tuple[date, ...]
    same_day_identity_resolver_available: tuple[date, ...]
    sessions_requiring_identity_acquisition: tuple[date, ...]
    sessions_requiring_grouped_daily_acquisition: tuple[date, ...]
    per_session_request_ceiling: int = Field(ge=0)
    conservative_request_ceiling: int = Field(ge=0)
    estimated_request_range: tuple[int, int]
    chronological_batch_plan: tuple[tuple[date, ...], ...]
    retry_count: Literal[0] = 0
    serial_rate_limit_seconds: Literal[15] = 15
    resume_idempotency_policy: str
    methodology_mode: EodHistoryMethodologyMode
    plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str

    @model_validator(mode="after")
    def validate_plan(self) -> "HistoricalEodBackfillPlanV1":
        if set(self.existing_eod_sessions) | set(self.missing_eod_sessions) | set(self.corrupt_eod_sessions) != set(self.required_eod_sessions):
            raise ValueError("backfill session states do not reconcile")
        flattened = tuple(item for batch in self.chronological_batch_plan for item in batch)
        if flattened != self.sessions_requiring_grouped_daily_acquisition:
            raise ValueError("batch plan does not reconcile")
        return self
