"""Reviewed eligibility override and Universe pre-activation review V1 contracts."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.security_classification.v1 import EvidenceGrade, IssuerStructure, SecurityForm


class ReviewedEligibilityDecision(StrEnum):
    EXCLUDE = "exclude"
    QUARANTINE = "quarantine"
    ALLOW = "allow"


class ReviewedEligibilityOverrideV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    override_id: UUID
    instrument_id: UUID
    effective_from: date
    effective_to: date | None = None
    decision: ReviewedEligibilityDecision
    asserted_security_form: SecurityForm
    asserted_issuer_structure: IssuerStructure
    evidence_grade: EvidenceGrade
    source_reference: str
    source_document_date: date
    reviewer_identifier: str
    reason_code: str
    reason: str
    created_at: datetime

    @field_validator("source_reference", "reviewer_identifier", "reason_code", "reason", mode="before")
    @classmethod
    def text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def semantics(self) -> "ReviewedEligibilityOverrideV1":
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if self.evidence_grade not in {EvidenceGrade.AUTHORITATIVE, EvidenceGrade.REVIEWED_OVERRIDE}:
            raise ValueError("reviewed override requires authoritative or reviewed evidence")
        if self.source_document_date > self.effective_from:
            raise ValueError("future evidence cannot be backfilled before its document date")
        return self

    def is_effective_on(self, session: date) -> bool:
        return self.effective_from <= session and (self.effective_to is None or session < self.effective_to)


def validate_override_intervals(records: tuple[ReviewedEligibilityOverrideV1, ...]) -> None:
    if len({item.override_id for item in records}) != len(records):
        raise ValueError("duplicate override_id")
    keys = [(item.instrument_id, item.effective_from) for item in records]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate reviewed override business key")
    by_id: dict[UUID, list[ReviewedEligibilityOverrideV1]] = {}
    for item in records:
        by_id.setdefault(item.instrument_id, []).append(item)
    for group in by_id.values():
        ordered = sorted(group, key=lambda item: item.effective_from)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.effective_to is None or current.effective_from < previous.effective_to:
                raise ValueError("reviewed override intervals overlap")


class UniverseReviewDecisionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    analysis_session: date
    universe_id: str
    instrument_id: UUID
    provider_type_code: str
    base_included: Literal[True] = True
    override_decision: ReviewedEligibilityDecision | None = None
    final_included: bool
    primary_reason: str
    source_trailing_decision_fingerprint: str
    reviewed_override_fingerprint: str
    created_at: datetime

    @field_validator("universe_id", "provider_type_code", "primary_reason", mode="before")
    @classmethod
    def text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("source_trailing_decision_fingerprint", "reviewed_override_fingerprint")
    @classmethod
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class UniverseSetSummaryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    universe_id: str
    base_passed_count: int = Field(ge=0)
    final_count: int = Field(ge=0)
    reviewed_exclusion_count: int = Field(ge=0)
    reviewed_quarantine_count: int = Field(ge=0)
    membership_fingerprint: str

    @field_validator("universe_id", mode="before")
    @classmethod
    def text(cls, value: str) -> str:
        return normalize_required_string(value, field_name="universe_id")

    @field_validator("membership_fingerprint")
    @classmethod
    def sha(cls, value: str) -> str:
        return _sha(value, "membership_fingerprint")

    @model_validator(mode="after")
    def counts(self) -> "UniverseSetSummaryV1":
        if self.final_count + self.reviewed_exclusion_count + self.reviewed_quarantine_count != self.base_passed_count:
            raise ValueError("review summary counts do not reconcile")
        return self


class UniverseReviewDatasetReferenceV1(BaseModel):
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
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)


class UniversePreActivationManifestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    manifest_version: Literal["1.0"] = "1.0"
    completion_status: Literal["completed"] = "completed"
    analysis_session: date
    membership_evidence_as_of_date: date
    trailing_logical_path: str
    trailing_logical_fingerprint: str
    trailing_decision_fingerprint: str
    legacy_count: int = Field(ge=0)
    legacy_membership_fingerprint: str
    legacy_analysis_session: date
    legacy_previous_session: date
    legacy_current_eod_fingerprint: str
    legacy_previous_eod_fingerprint: str
    legacy_policy_version: Literal["legacy-liquid-screen-provisional-v1"] = "legacy-liquid-screen-provisional-v1"
    override_dataset: UniverseReviewDatasetReferenceV1
    review_dataset: UniverseReviewDatasetReferenceV1
    universes: tuple[UniverseSetSummaryV1, ...]
    created_at: datetime
    logical_content_fingerprint: str

    @field_validator("trailing_logical_path")
    @classmethod
    def path(cls, value: str) -> str:
        value = normalize_required_string(value, field_name="trailing_logical_path")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("trailing_logical_path must be normalized and relative")
        return value

    @field_validator("trailing_logical_fingerprint", "trailing_decision_fingerprint", "legacy_membership_fingerprint", "legacy_current_eod_fingerprint", "legacy_previous_eod_fingerprint", "logical_content_fingerprint")
    @classmethod
    def sha(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def unique_universes(self) -> "UniversePreActivationManifestV1":
        if len({item.universe_id for item in self.universes}) != len(self.universes):
            raise ValueError("universe summaries must be unique")
        return self


def _sha(value: str, field_name: str) -> str:
    value = normalize_required_string(value, field_name=field_name).lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field_name} must be SHA-256 hexadecimal")
    return value
