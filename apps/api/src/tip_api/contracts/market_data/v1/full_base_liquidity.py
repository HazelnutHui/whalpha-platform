"""Contracts for the full provider-classified trailing-liquidity scope review."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1.trailing_liquidity_publication import TrailingLiquiditySourceSessionV1


class FullBaseDisposition(StrEnum):
    INCLUDED = "included"
    UNSUPPORTED_EXCHANGE = "unsupported_exchange"
    MISSING_CURRENT_BAR = "missing_current_bar"
    MISSING_PREVIOUS_BAR = "missing_previous_bar"
    BELOW_PREVIOUS_CLOSE = "below_previous_close"
    INSUFFICIENT_HISTORY = "insufficient_history"
    BELOW_TRAILING_LIQUIDITY = "below_trailing_liquidity"
    OUTLIER_QUARANTINE = "outlier_quarantine"
    REVIEWED_EXCLUSION = "reviewed_exclusion"
    REVIEWED_QUARANTINE = "reviewed_quarantine"
    INVALID_INPUT = "invalid_input"


class FullBaseMetricV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    membership_evidence_as_of_date: date
    instrument_id: UUID
    display_ticker: str
    provider_type_code: str
    primary_exchange: str | None
    supported_exchange: bool
    current_bar_present: bool
    previous_bar_present: bool
    previous_close: Decimal | None
    previous_dollar_volume_below_threshold: bool | None
    observation_count: int = Field(ge=0, le=20)
    median_dollar_volume_proxy_20s: Decimal | None
    metric_status: str
    quality_flags: tuple[str, ...]
    source_window_fingerprint: str
    calculated_at: datetime

    @field_validator("display_ticker", "provider_type_code", mode="before")
    @classmethod
    def code(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("primary_exchange", mode="before")
    @classmethod
    def exchange(cls, value: str | None) -> str | None:
        return None if value is None else normalize_required_string(value, field_name="primary_exchange", uppercase=True)

    @field_validator("metric_status", mode="before")
    @classmethod
    def text(cls, value: str) -> str:
        return normalize_required_string(value, field_name="metric_status")

    @field_validator("quality_flags", mode="before")
    @classmethod
    def flags(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("quality_flags must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name="quality_flags") for item in value}))

    @field_validator("source_window_fingerprint")
    @classmethod
    def source_hash(cls, value: str) -> str:
        return _sha(value, "source_window_fingerprint")

    @field_validator("calculated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def consistency(self) -> "FullBaseMetricV1":
        if self.median_dollar_volume_proxy_20s is not None and self.observation_count != 20:
            raise ValueError("20-session median requires exactly 20 observations")
        if not self.previous_bar_present and (self.previous_close is not None or self.previous_dollar_volume_below_threshold is not None):
            raise ValueError("missing previous bar cannot expose previous values")
        return self


class FullBaseDecisionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    membership_evidence_as_of_date: date
    policy_id: str
    instrument_id: UUID
    provider_type_code: str
    disposition: FullBaseDisposition
    included: bool
    stage_id: str
    reason_codes: tuple[str, ...]
    reviewed_override_decision: str | None
    calculated_at: datetime

    @field_validator("policy_id", "stage_id", mode="before")
    @classmethod
    def text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("provider_type_code", mode="before")
    @classmethod
    def provider_type(cls, value: str) -> str:
        return normalize_required_string(value, field_name="provider_type_code", uppercase=True)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("reason_codes must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name="reason_codes") for item in value}))

    @field_validator("calculated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def consistency(self) -> "FullBaseDecisionV1":
        if self.included != (self.disposition is FullBaseDisposition.INCLUDED):
            raise ValueError("included must match disposition")
        return self


class FullBaseMembershipV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    policy_id: str
    instrument_id: UUID
    provider_type_code: str


class FullBaseSetDiffV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    policy_id: str
    instrument_id: UUID
    provider_type_code: str
    direction: Literal["old_retained", "old_removed", "corrected_added"]
    reason_code: str
    rescued_from_previous_session_scope: bool
    median_dollar_volume_proxy_20s: Decimal | None


class FullBaseFunnelStageV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    membership_evidence_as_of_date: date
    policy_id: str
    stage_order: int = Field(ge=1)
    stage_id: str
    stage_label: str
    stage_kind: Literal["sequential", "overlapping"]
    input_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    remaining_count: int = Field(ge=0)
    exclusion_reason_codes: tuple[str, ...]
    source_fingerprints: tuple[str, ...]
    calculation_version: Literal["full-classified-base-trailing-liquidity-v1"] = "full-classified-base-trailing-liquidity-v1"

    @model_validator(mode="after")
    def reconcile(self) -> "FullBaseFunnelStageV1":
        if self.stage_kind == "sequential" and self.input_count - self.excluded_count != self.remaining_count:
            raise ValueError("sequential funnel stage does not reconcile")
        return self


class FullBaseDatasetReferenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    dataset_path: str
    record_count: int = Field(ge=0)
    content_fingerprint: str
    parquet_sha256: str

    @field_validator("dataset_path")
    @classmethod
    def path(cls, value: str) -> str:
        value = normalize_required_string(value, field_name="dataset_path")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("dataset_path must be normalized and relative")
        return value

    @field_validator("content_fingerprint", "parquet_sha256")
    @classmethod
    def hashes(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)


class FullBasePolicySummaryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    policy_id: str
    base_count: int = Field(ge=0)
    final_count: int = Field(ge=0)
    cs_count: int = Field(ge=0)
    adrc_count: int = Field(ge=0)
    membership_fingerprint: str
    old_count: int = Field(ge=0)
    retained_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    added_count: int = Field(ge=0)
    rescued_previous_day_below_threshold_count: int = Field(ge=0)

    @field_validator("membership_fingerprint")
    @classmethod
    def membership_hash(cls, value: str) -> str:
        return _sha(value, "membership_fingerprint")

    @model_validator(mode="after")
    def reconcile(self) -> "FullBasePolicySummaryV1":
        if self.cs_count + self.adrc_count != self.final_count:
            raise ValueError("security composition does not reconcile")
        if self.retained_count + self.removed_count != self.old_count:
            raise ValueError("old membership comparison does not reconcile")
        if self.retained_count + self.added_count != self.final_count:
            raise ValueError("corrected membership comparison does not reconcile")
        return self


class FullBaseScopeReviewManifestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    manifest_version: Literal["1.0"] = "1.0"
    completion_status: Literal["completed"] = "completed"
    analysis_session: date
    membership_evidence_as_of_date: date
    calendar_name: Literal["XNYS"]
    calendar_version: str
    window_sessions: tuple[date, ...]
    source_sessions: tuple[TrailingLiquiditySourceSessionV1, ...]
    source_descriptor_fingerprint: str
    security_evidence_path: str
    security_evidence_fingerprint: str
    legacy_v1_logical_path: str
    legacy_v1_logical_fingerprint: str
    legacy_v1_reproduced: Literal[True] = True
    reviewed_override_logical_path: str
    reviewed_override_fingerprint: str
    metric_dataset: FullBaseDatasetReferenceV1
    decision_dataset: FullBaseDatasetReferenceV1
    membership_dataset: FullBaseDatasetReferenceV1
    diff_dataset: FullBaseDatasetReferenceV1
    funnel_dataset: FullBaseDatasetReferenceV1
    policies: tuple[FullBasePolicySummaryV1, ...]
    previous_close_threshold: Decimal
    median_dollar_volume_threshold: Decimal
    methodology_mode: Literal["current_as_of_constituent_liquidity"] = "current_as_of_constituent_liquidity"
    calculation_version: Literal["full-classified-base-trailing-liquidity-v1"] = "full-classified-base-trailing-liquidity-v1"
    created_at: datetime
    logical_content_fingerprint: str

    @field_validator("security_evidence_path", "legacy_v1_logical_path", "reviewed_override_logical_path")
    @classmethod
    def paths(cls, value: str) -> str:
        value = normalize_required_string(value, field_name="source_path")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("source path must be normalized and relative")
        return value

    @field_validator("source_descriptor_fingerprint", "security_evidence_fingerprint", "legacy_v1_logical_fingerprint", "reviewed_override_fingerprint", "logical_content_fingerprint")
    @classmethod
    def hashes(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def consistency(self) -> "FullBaseScopeReviewManifestV1":
        if len(self.window_sessions) != 20 or tuple(sorted(self.window_sessions)) != self.window_sessions:
            raise ValueError("manifest requires exactly 20 ordered sessions")
        if tuple(item.session_date for item in self.source_sessions) != self.window_sessions:
            raise ValueError("source session references do not match window")
        if len({item.policy_id for item in self.policies}) != len(self.policies):
            raise ValueError("policy summaries must be unique")
        return self


def _sha(value: str, field_name: str) -> str:
    value = normalize_required_string(value, field_name=field_name).lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field_name} must be SHA-256 hexadecimal")
    return value
