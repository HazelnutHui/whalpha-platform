"""Provider Instrument Identity V1 point-in-time contract."""

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


class ResolutionStatus(StrEnum):
    """Point-in-time provider identity resolution status."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    EXCLUDED = "excluded"
    REJECTED = "rejected"


class ResolutionMethod(StrEnum):
    """Stable identifier method used for canonical instrument resolution."""

    SHARE_CLASS_FIGI = "share_class_figi"
    COMPOSITE_FIGI = "composite_figi"
    PROVIDER_STABLE_ID = "provider_stable_id"
    UNRESOLVED = "unresolved"


class ProviderInstrumentIdentityV1(BaseModel):
    """Provider identity candidate mapped to a canonical instrument identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    provider: str
    as_of_date: date
    provider_ticker: str
    provider_instrument_id: str | None = None
    composite_figi: str | None = None
    share_class_figi: str | None = None
    cik: str | None = None
    canonical_instrument_id: UUID | None = None
    resolution_status: ResolutionStatus
    resolution_method: ResolutionMethod
    valid_from: date
    valid_to: date | None = None
    source_updated_at: datetime | None = None
    ingested_at: datetime
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()

    @field_validator("as_of_date", "valid_from", "valid_to", mode="before")
    @classmethod
    def reject_datetime_for_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return normalize_required_string(value, field_name="provider")

    @field_validator("provider_ticker", mode="before")
    @classmethod
    def normalize_provider_ticker(cls, value: str) -> str:
        ticker = normalize_required_string(value, field_name="provider_ticker", uppercase=True)
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        if any(char not in allowed for char in ticker):
            raise ValueError("provider_ticker contains unsupported characters")
        return ticker

    @field_validator("provider_instrument_id", "composite_figi", "share_class_figi", mode="before")
    @classmethod
    def normalize_optional_identifier(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("cik", mode="before")
    @classmethod
    def normalize_cik(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="cik")

    @field_validator("source_updated_at", "ingested_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_utc_datetime(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_quality_flags(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            items = (value,)
        else:
            try:
                items = tuple(value)
            except TypeError as exc:
                raise ValueError("quality_flags must be an iterable of strings") from exc
        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, str):
                raise ValueError("quality_flags must contain strings")
            flag = item.strip().lower().replace("-", "_").replace(" ", "_")
            if not flag:
                raise ValueError("quality_flags must not contain empty values")
            if flag not in seen:
                normalized.append(flag)
                seen.add(flag)
        return tuple(normalized)

    @model_validator(mode="after")
    def validate_identity_semantics(self) -> ProviderInstrumentIdentityV1:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be earlier than valid_from")
        if self.as_of_date < self.valid_from:
            raise ValueError("as_of_date must not be earlier than valid_from")
        if self.resolution_status is ResolutionStatus.RESOLVED:
            if self.canonical_instrument_id is None:
                raise ValueError("resolved identity requires canonical_instrument_id")
            if self.resolution_method is ResolutionMethod.UNRESOLVED:
                raise ValueError("resolved identity requires a stable resolution method")
        else:
            if self.canonical_instrument_id is not None:
                raise ValueError("non-resolved identity must not carry canonical_instrument_id")
            if self.resolution_method is not ResolutionMethod.UNRESOLVED:
                raise ValueError("non-resolved identity must use unresolved method")
            if self.resolution_status in {ResolutionStatus.AMBIGUOUS, ResolutionStatus.EXCLUDED, ResolutionStatus.REJECTED} and not self.quality_flags:
                raise ValueError("ambiguous, excluded, or rejected identities require quality_flags")
        return self

