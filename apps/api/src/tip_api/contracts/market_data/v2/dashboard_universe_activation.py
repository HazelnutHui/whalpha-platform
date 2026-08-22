"""Versioned Dashboard Universe Activation V2 and active-pointer contracts."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1.dashboard_universe_activation import (
    DashboardUniverseActivationDatasetReferenceV1,
    SecurityTypeCountV1,
)


class DashboardUniverseActivationRecordV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["2.0"] = "2.0"
    activation_id: UUID
    policy_version: Literal["dashboard-universe-v2"] = "dashboard-universe-v2"
    revision_id: Literal["authoritative-security-form-v2"] = "authoritative-security-form-v2"
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
    source_publication_fingerprint: str
    trailing_liquidity_source_fingerprint: str
    reviewed_security_form_fingerprint: str
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

    @field_validator(
        "membership_fingerprint",
        "source_publication_fingerprint",
        "trailing_liquidity_source_fingerprint",
        "reviewed_security_form_fingerprint",
        "current_eod_fingerprint",
        "previous_eod_fingerprint",
    )
    @classmethod
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("legacy_rollback_reference")
    @classmethod
    def rollback_path(cls, value: str) -> str:
        return _relative_path(value, "legacy_rollback_reference")

    @model_validator(mode="after")
    def composition_reconciles(self) -> "DashboardUniverseActivationRecordV2":
        codes = [item.provider_type_code for item in self.security_type_composition]
        if len(codes) != len(set(codes)) or sum(item.count for item in self.security_type_composition) != self.member_count:
            raise ValueError("security type composition does not reconcile")
        return self


class DashboardUniverseActivationManifestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: Literal["2.0"] = "2.0"
    completion_status: Literal["completed"] = "completed"
    policy_version: Literal["dashboard-universe-v2"] = "dashboard-universe-v2"
    revision_id: Literal["authoritative-security-form-v2"] = "authoritative-security-form-v2"
    analysis_session: date
    membership_evidence_as_of: date
    trailing_window_start: date
    trailing_window_end: date
    trailing_window_session_count: Literal[20]
    reviewed_override_count: int = Field(ge=0)
    reviewed_security_form_count: int = Field(ge=0)
    activated_at: datetime
    default_universe_id: str
    available_universe_ids: tuple[str, str]
    activation_dataset: DashboardUniverseActivationDatasetReferenceV1
    source_publication_path: str
    source_publication_fingerprint: str
    reviewed_security_form_fingerprint: str
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

    @field_validator("source_publication_path")
    @classmethod
    def source_path(cls, value: str) -> str:
        return _relative_path(value, "source_publication_path")

    @field_validator(
        "source_publication_fingerprint",
        "reviewed_security_form_fingerprint",
        "legacy_membership_fingerprint",
        "logical_content_fingerprint",
    )
    @classmethod
    def hashes(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def catalog(self) -> "DashboardUniverseActivationManifestV2":
        if len(set(self.available_universe_ids)) != 2 or self.default_universe_id not in self.available_universe_ids:
            raise ValueError("activation catalog must contain two unique universes and its default")
        if self.trailing_window_start > self.trailing_window_end:
            raise ValueError("trailing window is invalid")
        return self


class DashboardUniverseActivationTargetReferenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_version: Literal["1.0"] = "1.0"
    target_schema_version: Literal["1.0", "2.0"]
    revision_id: str | None = None
    analysis_session: date
    logical_path: str
    logical_content_fingerprint: str

    @field_validator("logical_path")
    @classmethod
    def path(cls, value: str) -> str:
        return _relative_path(value, "logical_path")

    @field_validator("logical_content_fingerprint")
    @classmethod
    def fingerprint(cls, value: str) -> str:
        return _sha(value, "logical_content_fingerprint")

    @model_validator(mode="after")
    def revision_semantics(self) -> "DashboardUniverseActivationTargetReferenceV1":
        if self.target_schema_version == "1.0" and self.revision_id is not None:
            raise ValueError("V1 activation reference cannot have a revision")
        if self.target_schema_version == "2.0" and self.revision_id != "authoritative-security-form-v2":
            raise ValueError("V2 activation reference requires the reviewed revision")
        return self


class DashboardUniverseActivationPointerV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pointer_version: Literal["1.0"] = "1.0"
    status: Literal["active"] = "active"
    active: DashboardUniverseActivationTargetReferenceV1
    rollback: DashboardUniverseActivationTargetReferenceV1
    default_universe_id: str
    available_universe_ids: tuple[str, str]
    switched_at: datetime
    pointer_content_fingerprint: str

    @field_validator("default_universe_id", mode="before")
    @classmethod
    def text(cls, value: str) -> str:
        return normalize_required_string(value, field_name="default_universe_id")

    @field_validator("switched_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("pointer_content_fingerprint")
    @classmethod
    def fingerprint(cls, value: str) -> str:
        return _sha(value, "pointer_content_fingerprint")

    @model_validator(mode="after")
    def semantics(self) -> "DashboardUniverseActivationPointerV1":
        if self.active == self.rollback:
            raise ValueError("active and rollback references must differ")
        if self.active.analysis_session != self.rollback.analysis_session:
            raise ValueError("active and rollback analysis sessions must match")
        if len(set(self.available_universe_ids)) != 2 or self.default_universe_id not in self.available_universe_ids:
            raise ValueError("pointer catalog is invalid")
        return self


def _relative_path(value: str, field_name: str) -> str:
    value = normalize_required_string(value, field_name=field_name)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError(f"{field_name} must be normalized and relative")
    return value


def _sha(value: str, field_name: str) -> str:
    value = normalize_required_string(value, field_name=field_name).lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field_name} must be SHA-256 hexadecimal")
    return value
