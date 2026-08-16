"""Point-in-time SEC issuer-structure evidence contracts."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tip_api.contracts.common import (
    QualityStatus,
    normalize_optional_string,
    normalize_required_string,
    normalize_utc_datetime,
)
from tip_api.contracts.security_classification.v1.security_classification import (
    IssuerStructure,
    ListingScope,
    SecurityForm,
    UniverseDisposition,
)


class SecEvidenceGrade(StrEnum):
    AUTHORITATIVE_EXPLICIT = "authoritative_explicit"
    AUTHORITATIVE_FILING_COVER = "authoritative_filing_cover"
    AUTHORITATIVE_STATE_MACHINE = "authoritative_state_machine"
    CORROBORATING_REFERENCE = "corroborating_reference"
    HEURISTIC_REVIEW_ONLY = "heuristic_review_only"
    INSUFFICIENT = "insufficient"


class SecEvidenceResolutionStatus(StrEnum):
    CANONICAL_MAPPED = "canonical_mapped"
    EXPECTED_UNJOINED = "expected_unjoined"
    AMBIGUOUS = "ambiguous"
    COLLISION = "collision"
    MALFORMED = "malformed"


class SecEvidenceSubject(StrEnum):
    SECURITY = "security"
    ISSUER_STRUCTURE = "issuer_structure"
    FUND_STATUS = "fund_status"
    BDC_STATUS = "bdc_status"
    REPORTING_STATUS = "reporting_status"
    IDENTITY_REFERENCE = "identity_reference"


class SecIssuerEvidenceObservationV1(BaseModel):
    """One normalized SEC assertion; raw SEC payloads are intentionally excluded."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    observation_id: str
    instrument_id: UUID | None = None
    cik: str
    source_dataset: str
    source_document_type: str
    form_type: str | None = None
    accession_number: str | None = None
    filing_date: date
    effective_from: date
    effective_to: date | None = None
    ticker: str | None = None
    exchange: str | None = None
    share_class_figi: str | None = None
    composite_figi: str | None = None
    provider_stable_identifier: str | None = None
    evidence_subject: SecEvidenceSubject
    asserted_security_form: SecurityForm | None = None
    asserted_issuer_structure: IssuerStructure | None = None
    asserted_listing_scope: ListingScope | None = None
    evidence_grade: SecEvidenceGrade
    resolution_status: SecEvidenceResolutionStatus
    decision_reasons: tuple[str, ...]
    source_observed_at: datetime
    quality_status: QualityStatus
    quality_flags: tuple[str, ...]

    @field_validator("filing_date", "effective_from", "effective_to", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("observation_id")
    @classmethod
    def validate_observation_id(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="observation_id").lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("observation_id must be SHA-256 hexadecimal")
        return normalized

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="cik")
        if not normalized.isdigit() or len(normalized) > 10:
            raise ValueError("cik must contain at most ten digits")
        return normalized.zfill(10)

    @field_validator("source_dataset", "source_document_type", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("form_type", "accession_number", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=info.field_name == "form_type")

    @field_validator("ticker", "exchange", "share_class_figi", "composite_figi", mode="before")
    @classmethod
    def normalize_optional_upper(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("provider_stable_identifier", mode="before")
    @classmethod
    def normalize_provider_identifier(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="provider_stable_identifier")

    @field_validator("decision_reasons", "quality_flags", mode="before")
    @classmethod
    def normalize_sets(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))

    @field_validator("source_observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_semantics(self) -> SecIssuerEvidenceObservationV1:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if self.filing_date > self.effective_from:
            raise ValueError("evidence cannot be effective before its filing date")
        if self.resolution_status is SecEvidenceResolutionStatus.CANONICAL_MAPPED:
            if self.instrument_id is None:
                raise ValueError("canonical_mapped evidence requires instrument_id")
        elif self.instrument_id is not None:
            raise ValueError("non-mapped evidence must not carry instrument_id")
        if self.evidence_grade in {SecEvidenceGrade.HEURISTIC_REVIEW_ONLY, SecEvidenceGrade.INSUFFICIENT}:
            if any((self.asserted_security_form, self.asserted_issuer_structure, self.asserted_listing_scope)):
                raise ValueError("weak evidence cannot make positive classification assertions")
        return self

    def is_effective_on(self, as_of_date: date) -> bool:
        return self.effective_from <= as_of_date and (
            self.effective_to is None or as_of_date < self.effective_to
        )


class SecIssuerStructureEvidenceV1(BaseModel):
    """Canonical evidence created only from uniquely resolved SEC observations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    evidence_kind: Literal["sec_issuer_structure"] = "sec_issuer_structure"
    evidence_version: Literal["1"] = "1"
    as_of_date: date
    instrument_id: UUID
    cik: str
    asserted_security_form: SecurityForm | None = None
    asserted_issuer_structure: IssuerStructure | None = None
    asserted_listing_scope: ListingScope | None = None
    evidence_grade: SecEvidenceGrade
    universe_disposition: UniverseDisposition
    source_observation_ids: tuple[str, ...]
    decision_reasons: tuple[str, ...]
    quality_status: QualityStatus
    quality_flags: tuple[str, ...]
    source_observed_at: datetime

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime")
        return value

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="cik")
        if not normalized.isdigit() or len(normalized) > 10:
            raise ValueError("cik must contain at most ten digits")
        return normalized.zfill(10)

    @field_validator("source_observation_ids", "decision_reasons", "quality_flags", mode="before")
    @classmethod
    def normalize_sets(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)) or (
            info.field_name == "source_observation_ids" and not value
        ):
            raise ValueError(f"{info.field_name} must be a valid collection")
        result = tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))
        if info.field_name == "source_observation_ids" and any(
            len(item) != 64 or any(char not in "0123456789abcdef" for char in item.lower()) for item in result
        ):
            raise ValueError("source_observation_ids must contain SHA-256 hexadecimal values")
        return tuple(item.lower() if info.field_name == "source_observation_ids" else item for item in result)

    @field_validator("source_observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @property
    def business_key(self) -> tuple[UUID, date, str, str]:
        return self.instrument_id, self.as_of_date, self.evidence_kind, self.evidence_version


class SecIssuerEvidenceManifestV1(BaseModel):
    """Completion manifest for a canonical SEC evidence partition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    dataset_name: Literal["sec-issuer-structure-evidence"] = "sec-issuer-structure-evidence"
    completion_status: Literal["completed"] = "completed"
    as_of_date: date
    record_count: int
    content_sha256: str
    parquet_sha256: str
    source_datasets: tuple[str, ...]
    created_at: datetime

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_manifest_datetime(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime")
        return value

    @field_validator("record_count")
    @classmethod
    def validate_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("record_count must be non-negative")
        return value

    @field_validator("content_sha256", "parquet_sha256")
    @classmethod
    def validate_hash(cls, value: str, info: Any) -> str:
        normalized = normalize_required_string(value, field_name=info.field_name).lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError(f"{info.field_name} must be SHA-256 hexadecimal")
        return normalized

    @field_validator("source_datasets", mode="before")
    @classmethod
    def normalize_sources(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)) or not value:
            raise ValueError("source_datasets must be non-empty")
        return tuple(sorted({normalize_required_string(item, field_name="source_datasets") for item in value}))

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class SecEvidenceDatasetReferenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_name: str
    partition_path: str
    record_count: int
    content_sha256: str
    parquet_sha256: str

    @field_validator("dataset_name", "partition_path", mode="before")
    @classmethod
    def normalize_text(cls, value: str, info: Any) -> str:
        normalized = normalize_required_string(value, field_name=info.field_name)
        if info.field_name == "partition_path" and (normalized.startswith("/") or ".." in normalized.split("/")):
            raise ValueError("partition_path must be a safe relative path")
        return normalized

    @field_validator("record_count")
    @classmethod
    def nonnegative_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("record_count must be non-negative")
        return value

    @field_validator("content_sha256", "parquet_sha256")
    @classmethod
    def hashes(cls, value: str, info: Any) -> str:
        normalized = normalize_required_string(value, field_name=info.field_name).lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError(f"{info.field_name} must be SHA-256 hexadecimal")
        return normalized


class SecIssuerEvidenceSnapshotManifestV1(BaseModel):
    """Logical completion marker; readers must not infer completion from one partition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    dataset_name: Literal["sec-issuer-structure-evidence-snapshot"] = "sec-issuer-structure-evidence-snapshot"
    completion_status: Literal["completed"] = "completed"
    as_of_date: date
    observed_at: datetime
    source_cache_manifest_sha256: str
    observation: SecEvidenceDatasetReferenceV1
    canonical_evidence: SecEvidenceDatasetReferenceV1
    quality_summary: dict[str, int | float | str]
    logical_content_sha256: str

    @field_validator("as_of_date", mode="before")
    @classmethod
    def strict_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime")
        return value

    @field_validator("observed_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("source_cache_manifest_sha256", "logical_content_sha256")
    @classmethod
    def snapshot_hashes(cls, value: str, info: Any) -> str:
        normalized = normalize_required_string(value, field_name=info.field_name).lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError(f"{info.field_name} must be SHA-256 hexadecimal")
        return normalized
