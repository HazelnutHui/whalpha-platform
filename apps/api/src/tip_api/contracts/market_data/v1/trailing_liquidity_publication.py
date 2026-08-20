"""Versioned contracts for trailing-liquidity shadow publication."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


class TrailingLiquidityMetricStatus(StrEnum):
    AVAILABLE = "available"
    NOT_CALCULATED_BELOW_PRICE = "not_calculated_below_price"
    INSUFFICIENT_HISTORY = "insufficient_history"
    MISSING_PREVIOUS_BAR = "missing_previous_bar"
    INVALID_INPUT = "invalid_input"


class ShadowEligibilityStatus(StrEnum):
    PASSED = "passed"
    MISSING_PREVIOUS_BAR = "missing_previous_bar"
    INSUFFICIENT_HISTORY = "insufficient_history"
    BELOW_PRICE = "below_price"
    BELOW_LIQUIDITY = "below_liquidity"
    QUARANTINED_OR_INVALID_INPUT = "quarantined_or_invalid_input"


class TrailingLiquidityMetricV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    window_start: date
    window_end: date
    window_session_count: Literal[20] = 20
    instrument_id: UUID
    display_ticker: str
    provider_type_code: str
    observation_count: int = Field(ge=0, le=20)
    previous_session: date
    previous_close: Decimal | None
    median_dollar_volume_proxy_20s: Decimal | None
    metric_status: TrailingLiquidityMetricStatus
    quality_flags: tuple[str, ...]
    source_window_fingerprint: str
    calculated_at: datetime

    @field_validator("display_ticker", "provider_type_code", mode="before")
    @classmethod
    def normalize_codes(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("quality_flags must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name="quality_flags") for item in value}))

    @field_validator("source_window_fingerprint")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _sha256(value, "source_window_fingerprint")

    @field_validator("calculated_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_metric(self) -> "TrailingLiquidityMetricV1":
        if self.window_start > self.window_end or self.previous_session != self.window_end:
            raise ValueError("metric window is inconsistent")
        if self.analysis_session <= self.window_end:
            raise ValueError("analysis session must be after the source window")
        if self.observation_count < 20 and self.median_dollar_volume_proxy_20s is not None:
            raise ValueError("incomplete history cannot publish a 20-session median")
        if self.metric_status is TrailingLiquidityMetricStatus.AVAILABLE and self.median_dollar_volume_proxy_20s is None:
            raise ValueError("available metric requires a median")
        return self


class TrailingLiquidityShadowDecisionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    universe_id: str
    universe_version: Literal["1"] = "1"
    membership_evidence_as_of_date: date
    instrument_id: UUID
    provider_type_code: str
    metric_schema_version: Literal["1.0"] = "1.0"
    eligibility_status: ShadowEligibilityStatus
    price_gate_passed: bool | None
    liquidity_gate_passed: bool | None
    included: bool
    primary_reason: str
    quality_flags: tuple[str, ...]
    decision_reasons: tuple[str, ...]
    calculated_at: datetime

    @field_validator("universe_id", "primary_reason", mode="before")
    @classmethod
    def normalize_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("provider_type_code", mode="before")
    @classmethod
    def normalize_provider_type(cls, value: str) -> str:
        return normalize_required_string(value, field_name="provider_type_code", uppercase=True)

    @field_validator("quality_flags", "decision_reasons", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))

    @field_validator("calculated_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_decision(self) -> "TrailingLiquidityShadowDecisionV1":
        if self.included != (self.eligibility_status is ShadowEligibilityStatus.PASSED):
            raise ValueError("included must be equivalent to passed")
        if self.primary_reason != self.eligibility_status.value:
            raise ValueError("primary reason must be the mutually exclusive eligibility status")
        return self


class TrailingLiquiditySourceSessionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    session_date: date
    dataset_path: str
    record_count: int = Field(gt=0)
    content_fingerprint: str
    parquet_sha256: str
    identity_snapshot_date: date
    identity_snapshot_fingerprint: str

    @field_validator("dataset_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _relative_path(value, "dataset_path")

    @field_validator("content_fingerprint", "parquet_sha256", "identity_snapshot_fingerprint")
    @classmethod
    def validate_hashes(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)


class TrailingLiquidityDatasetReferenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    dataset_path: str
    record_count: int = Field(gt=0)
    content_fingerprint: str
    parquet_sha256: str

    @field_validator("dataset_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _relative_path(value, "dataset_path")

    @field_validator("content_fingerprint", "parquet_sha256")
    @classmethod
    def validate_hashes(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)


class TrailingLiquidityCandidateSummaryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    universe_id: str
    requested_count: int = Field(gt=0)
    passed_count: int = Field(ge=0)
    below_liquidity_count: int = Field(ge=0)
    below_price_count: int = Field(ge=0)
    missing_previous_bar_count: int = Field(ge=0)
    insufficient_history_count: int = Field(ge=0)
    full_history_count: int = Field(ge=0)
    non_null_median_count: int = Field(ge=0)
    audit_fingerprint: str

    @field_validator("universe_id", mode="before")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return normalize_required_string(value, field_name="universe_id")

    @field_validator("audit_fingerprint")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _sha256(value, "audit_fingerprint")

    @model_validator(mode="after")
    def validate_counts(self) -> "TrailingLiquidityCandidateSummaryV1":
        primary = self.passed_count + self.below_liquidity_count + self.below_price_count + self.missing_previous_bar_count + self.insufficient_history_count
        if primary != self.requested_count:
            raise ValueError("candidate primary decision counts do not reconcile")
        return self


class TrailingLiquidityShadowManifestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    manifest_version: Literal["1.0"] = "1.0"
    completion_status: Literal["completed"] = "completed"
    analysis_session: date
    calendar_name: Literal["XNYS"]
    calendar_version: str
    window_sessions: tuple[date, ...]
    membership_evidence_path: str
    membership_evidence_as_of_date: date
    membership_evidence_fingerprint: str
    source_descriptor_fingerprint: str
    source_sessions: tuple[TrailingLiquiditySourceSessionV1, ...]
    metric_dataset: TrailingLiquidityDatasetReferenceV1
    decision_dataset: TrailingLiquidityDatasetReferenceV1
    candidates: tuple[TrailingLiquidityCandidateSummaryV1, ...]
    previous_close_threshold: Decimal
    median_dollar_volume_threshold: Decimal
    decimal_precision: Literal[38] = 38
    decimal_scale: Literal[10] = 10
    methodology_mode: Literal["current_as_of_constituent_liquidity"] = "current_as_of_constituent_liquidity"
    policy_version: str
    created_at: datetime
    logical_content_fingerprint: str

    @field_validator("membership_evidence_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _relative_path(value, "membership_evidence_path")

    @field_validator("membership_evidence_fingerprint", "source_descriptor_fingerprint", "logical_content_fingerprint")
    @classmethod
    def validate_hashes(cls, value: str, info: Any) -> str:
        return _sha256(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_manifest(self) -> "TrailingLiquidityShadowManifestV1":
        if len(self.window_sessions) != 20 or tuple(sorted(self.window_sessions)) != self.window_sessions:
            raise ValueError("logical manifest requires exactly 20 ordered sessions")
        if tuple(item.session_date for item in self.source_sessions) != self.window_sessions:
            raise ValueError("source sessions do not match the declared window")
        if len({item.universe_id for item in self.candidates}) != len(self.candidates):
            raise ValueError("candidate summaries must be unique")
        return self


def _sha256(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{field_name} must be SHA-256 hexadecimal")
    return normalized


def _relative_path(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name)
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
        raise ValueError(f"{field_name} must be a normalized relative path")
    return normalized
