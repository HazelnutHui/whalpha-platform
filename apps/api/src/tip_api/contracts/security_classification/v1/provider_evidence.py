"""Provider security-type evidence contracts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

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


class ProviderInstrumentSecurityEvidenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    as_of_date: date
    instrument_id: UUID
    provider: str
    provider_ticker: str
    provider_type_code: str
    provider_type_description: str
    primary_exchange: str
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

    @field_validator("cik", "composite_figi", "share_class_figi", mode="before")
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
