"""Provider security-type evidence contracts."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_optional_string, normalize_required_string, normalize_utc_datetime
from tip_api.contracts.security_classification.v1.security_classification import (
    ClassificationStatus,
    EvidenceGrade,
    SecurityForm,
    UniverseDisposition,
)


class ProviderSecurityTypeCatalogV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    provider: str
    provider_type_code: str
    provider_type_description: str
    provider_asset_class: str
    provider_locale: str
    observed_at: datetime
    source_endpoint: str
    evidence_fingerprint: str

    @field_validator("provider", "provider_type_description", "provider_asset_class", "provider_locale", mode="before")
    @classmethod
    def normalize_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("provider_type_code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return normalize_required_string(value, field_name="provider_type_code", uppercase=True)

    @field_validator("source_endpoint", mode="before")
    @classmethod
    def normalize_endpoint(cls, value: str) -> str:
        endpoint = normalize_required_string(value, field_name="source_endpoint")
        if not endpoint.startswith("/") or "?" in endpoint:
            raise ValueError("source_endpoint must be a path without query parameters")
        return endpoint

    @field_validator("evidence_fingerprint")
    @classmethod
    def validate_fingerprint(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="evidence_fingerprint").lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("evidence_fingerprint must be SHA-256 hexadecimal")
        return normalized

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class ProviderObservationStatus(StrEnum):
    """Reconciliation result for one normalized provider observation."""

    CANONICAL_MAPPED = "canonical_mapped"
    EXPECTED_UNJOINED = "expected_unjoined"
    AMBIGUOUS = "ambiguous"
    COLLISION = "collision"
    MALFORMED = "malformed"


class ProviderSecurityObservationV1(BaseModel):
    """Normalized point-in-time provider observation, mapped or unmapped."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    provider_observation_id: str
    as_of_date: date
    instrument_id: UUID | None = None
    provider: str
    provider_ticker: str | None = None
    provider_type_code: str | None = None
    provider_type_description: str | None = None
    primary_exchange: str | None = None
    provider_instrument_id: str | None = None
    cik: str | None = None
    composite_figi: str | None = None
    share_class_figi: str | None = None
    security_form_evidence: SecurityForm
    evidence_source: str
    evidence_grade: EvidenceGrade
    observation_status: ProviderObservationStatus
    resolution_method: str
    reason_codes: tuple[str, ...]
    review_flags: tuple[str, ...]
    occurrence_count: int = Field(default=1, ge=1)
    observed_at: datetime
    ingested_at: datetime

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime")
        return value

    @field_validator("provider_observation_id")
    @classmethod
    def validate_observation_id(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="provider_observation_id").lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("provider_observation_id must be SHA-256 hexadecimal")
        return normalized

    @field_validator("provider", "evidence_source", "resolution_method", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("provider_ticker", "provider_type_code", "primary_exchange", mode="before")
    @classmethod
    def normalize_optional_upper(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("provider_type_description", "cik", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name)

    @field_validator("provider_instrument_id", "composite_figi", "share_class_figi", mode="before")
    @classmethod
    def normalize_optional_identifier(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("reason_codes", "review_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))

    @field_validator("observed_at", "ingested_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_mapping(self) -> ProviderSecurityObservationV1:
        if self.observation_status is ProviderObservationStatus.CANONICAL_MAPPED:
            if self.instrument_id is None:
                raise ValueError("canonical_mapped observation requires instrument_id")
        elif self.instrument_id is not None:
            raise ValueError("non-mapped observation must not carry instrument_id")
        return self


class ProviderInstrumentSecurityEvidenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    evidence_kind: Literal["provider_security_type"] = "provider_security_type"
    evidence_version: Literal["1"] = "1"
    as_of_date: date
    instrument_id: UUID
    provider: str
    provider_ticker: str
    provider_type_code: str
    provider_type_description: str
    primary_exchange: str
    provider_instrument_id: str | None = None
    cik: str | None = None
    composite_figi: str | None = None
    share_class_figi: str | None = None
    security_form_evidence: SecurityForm
    evidence_source: str
    evidence_grade: EvidenceGrade
    classification_status: ClassificationStatus
    universe_disposition: UniverseDisposition
    decision_flags: tuple[str, ...]
    review_flags: tuple[str, ...]
    provider_observation_ids: tuple[str, ...]
    observed_at: datetime
    ingested_at: datetime

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime")
        return value

    @field_validator("provider", "provider_type_description", "evidence_source", mode="before")
    @classmethod
    def normalize_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("provider_ticker", "provider_type_code", "primary_exchange", mode="before")
    @classmethod
    def normalize_upper(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("provider_instrument_id", "cik", "composite_figi", "share_class_figi", mode="before")
    @classmethod
    def normalize_optional(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=info.field_name != "cik")

    @field_validator("decision_flags", "review_flags", mode="before")
    @classmethod
    def normalize_flags(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))

    @field_validator("observed_at", "ingested_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("provider_observation_ids", mode="before")
    @classmethod
    def normalize_observation_ids(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)) or not value:
            raise ValueError("provider_observation_ids must be a non-empty collection")
        if any(not isinstance(item, str) for item in value):
            raise ValueError("provider_observation_ids must contain strings")
        result = tuple(sorted(set(value)))
        if any(len(item) != 64 or any(char not in "0123456789abcdef" for char in item.lower()) for item in result):
            raise ValueError("provider_observation_ids must contain SHA-256 hexadecimal values")
        return tuple(item.lower() for item in result)

    @property
    def business_key(self) -> tuple[UUID, date, str, str, str]:
        return (self.instrument_id, self.as_of_date, self.provider, self.evidence_kind, self.evidence_version)


class SanitizedObservationSummaryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_ticker: str | None = None
    provider_type_code: str | None = None
    observation_status: ProviderObservationStatus
    identifier_types: tuple[str, ...]
    instrument_id: UUID | None = None
    reason_codes: tuple[str, ...]

    @field_validator("provider_ticker", "provider_type_code", mode="before")
    @classmethod
    def normalize_optional_codes(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("identifier_types", "reason_codes", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))


class FailedSecurityEvidenceDiagnosticV1(BaseModel):
    """Sanitized failed-run record, physically separate from completed evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    diagnostic_status: Literal["failed"] = "failed"
    run_id: str
    as_of_date: date
    provider: str
    endpoint_names: tuple[str, ...]
    request_count: int = Field(ge=0)
    ticker_types_request_count: int = Field(ge=0)
    all_tickers_request_count: int = Field(ge=0)
    raw_observation_count: int = Field(ge=0)
    status_counts: dict[str, int]
    linkage_numerator: int = Field(ge=0)
    linkage_denominator: int = Field(ge=0)
    linkage_ratio: str
    exact_duplicate_count: int = Field(ge=0)
    ambiguous_count: int = Field(ge=0)
    collision_count: int = Field(ge=0)
    business_key_conflict_count: int = Field(ge=0)
    reconciliation_status: Literal["passed", "failed"]
    failure_reasons: tuple[str, ...]
    conflicting_observations: tuple[SanitizedObservationSummaryV1, ...]
    created_at: datetime

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="run_id")
        if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in normalized):
            raise ValueError("run_id contains unsupported characters")
        return normalized

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return normalize_required_string(value, field_name="provider")

    @field_validator("endpoint_names", "failure_reasons", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)
