"""Provider Ticker Resolver V1 point-in-time projection."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


class ProviderTickerResolverV1(BaseModel):
    """Unique provider ticker to canonical instrument mapping for one as-of date."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    provider: str
    as_of_date: date
    provider_ticker: str
    canonical_instrument_id: UUID
    resolution_method: str
    source_identity_key: str
    ingested_at: datetime

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_for_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime values")
        return value

    @field_validator("provider", "source_identity_key", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("provider_ticker", mode="before")
    @classmethod
    def normalize_provider_ticker(cls, value: str) -> str:
        return normalize_required_string(value, field_name="provider_ticker", uppercase=True)

    @field_validator("ingested_at")
    @classmethod
    def normalize_ingested_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

