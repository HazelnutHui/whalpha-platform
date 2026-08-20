"""Dashboard Universe Activation V1 contracts."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


class SecurityTypeCountV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider_type_code: Literal["CS", "ADRC"]
    count: int = Field(ge=0)


class DashboardUniverseActivationRecordV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    activation_id: UUID
    policy_version: Literal["dashboard-universe-v1"] = "dashboard-universe-v1"
    analysis_session: date
    membership_evidence_as_of: date
    activated_at: datetime
    universe_id: str
    display_name: str
    long_display_name: str
    description: str
    provisional: Literal[True] = True
    is_default: bool
    member_count: int = Field(gt=0)
    security_type_composition: tuple[SecurityTypeCountV1, ...]
    membership_fingerprint: str
    trailing_liquidity_source_fingerprint: str
    reviewed_override_source_fingerprint: str
    pre_activation_review_fingerprint: str
    current_eod_fingerprint: str
    previous_eod_fingerprint: str
    legacy_rollback_reference: str
    limitations: tuple[str, ...]
    status: Literal["active"] = "active"

    @field_validator("universe_id", "display_name", "long_display_name", "description", mode="before")
    @classmethod
    def text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("activated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("membership_fingerprint", "trailing_liquidity_source_fingerprint", "reviewed_override_source_fingerprint", "pre_activation_review_fingerprint", "current_eod_fingerprint", "previous_eod_fingerprint")
    @classmethod
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("legacy_rollback_reference")
    @classmethod
    def path(cls, value: str) -> str:
        value = normalize_required_string(value, field_name="legacy_rollback_reference")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("legacy rollback reference must be normalized and relative")
        return value

    @model_validator(mode="after")
    def composition_reconciles(self) -> "DashboardUniverseActivationRecordV1":
        codes = [item.provider_type_code for item in self.security_type_composition]
        if len(codes) != len(set(codes)) or sum(item.count for item in self.security_type_composition) != self.member_count:
            raise ValueError("security type composition does not reconcile")
        return self


class DashboardUniverseActivationDatasetReferenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    dataset_path: str
    record_count: Literal[2]
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
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)


class DashboardUniverseActivationManifestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    manifest_version: Literal["1.0"] = "1.0"
    completion_status: Literal["completed"] = "completed"
    policy_version: Literal["dashboard-universe-v1"] = "dashboard-universe-v1"
    analysis_session: date
    membership_evidence_as_of: date
    trailing_window_start: date
    trailing_window_end: date
    trailing_window_session_count: Literal[20]
    reviewed_override_count: int = Field(ge=0)
    activated_at: datetime
    default_universe_id: str
    available_universe_ids: tuple[str, str]
    activation_dataset: DashboardUniverseActivationDatasetReferenceV1
    pre_activation_review_path: str
    pre_activation_review_fingerprint: str
    legacy_member_count: int = Field(gt=0)
    legacy_membership_fingerprint: str
    logical_content_fingerprint: str

    @field_validator("activated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("default_universe_id", mode="before")
    @classmethod
    def text(cls, value: str) -> str:
        return normalize_required_string(value, field_name="default_universe_id")

    @field_validator("pre_activation_review_path")
    @classmethod
    def path(cls, value: str) -> str:
        value = normalize_required_string(value, field_name="pre_activation_review_path")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("review path must be normalized and relative")
        return value

    @field_validator("pre_activation_review_fingerprint", "legacy_membership_fingerprint", "logical_content_fingerprint")
    @classmethod
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def catalog(self) -> "DashboardUniverseActivationManifestV1":
        if len(set(self.available_universe_ids)) != 2 or self.default_universe_id not in self.available_universe_ids:
            raise ValueError("activation catalog must contain two unique universes and its default")
        if self.trailing_window_start > self.trailing_window_end:
            raise ValueError("trailing window is invalid")
        return self


def _sha(value: str, field_name: str) -> str:
    value = normalize_required_string(value, field_name=field_name).lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field_name} must be SHA-256 hexadecimal")
    return value
