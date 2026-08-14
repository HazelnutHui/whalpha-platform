"""Instrument Master V1 provider-neutral contract."""

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


class InstrumentType(StrEnum):
    """Initial supported instrument types."""

    COMMON_STOCK = "common_stock"
    ETF = "etf"


class InstrumentStatus(StrEnum):
    """Initial supported instrument lifecycle statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELISTED = "delisted"


class InstrumentMasterV1(BaseModel):
    """Stable identity contract for securities."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: UUID
    issuer_id: UUID | None = None
    instrument_type: InstrumentType
    status: InstrumentStatus
    schema_version: Literal["1.0"] = "1.0"

    ticker: str
    name: str
    primary_exchange: str
    listing_country: str
    currency: str
    figi: str | None = None
    cik: str | None = None

    valid_from: date
    valid_to: date | None = None
    first_trade_date: date | None = None
    last_trade_date: date | None = None
    as_of_date: date

    source: str
    source_instrument_id: str
    ingested_at: datetime
    quality_status: QualityStatus
    quality_notes: str | None = None

    @field_validator("valid_from", "valid_to", "first_trade_date", "last_trade_date", "as_of_date", mode="before")
    @classmethod
    def reject_datetime_for_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = normalize_required_string(value, field_name="ticker", uppercase=True)
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        if any(char not in allowed for char in ticker):
            raise ValueError("ticker contains unsupported characters")
        return ticker

    @field_validator("name", "source", "source_instrument_id", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("primary_exchange", "figi", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: str | None, info: Any) -> str | None:
        if info.field_name == "figi":
            return normalize_optional_string(value, field_name=info.field_name, uppercase=True)
        return normalize_required_string(value, field_name=info.field_name, uppercase=True)

    @field_validator("listing_country", mode="before")
    @classmethod
    def normalize_listing_country(cls, value: str) -> str:
        country = normalize_required_string(value, field_name="listing_country", uppercase=True)
        if len(country) != 2 or not country.isalpha():
            raise ValueError("listing_country must be a two-letter country code")
        return country

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = normalize_required_string(value, field_name="currency", uppercase=True)
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter code")
        return currency

    @field_validator("cik", "quality_notes", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name)

    @field_validator("ingested_at")
    @classmethod
    def normalize_ingested_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_date_order(self) -> InstrumentMasterV1:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be earlier than valid_from")
        if (
            self.first_trade_date is not None
            and self.last_trade_date is not None
            and self.last_trade_date < self.first_trade_date
        ):
            raise ValueError("last_trade_date must not be earlier than first_trade_date")
        if self.as_of_date < self.valid_from:
            raise ValueError("as_of_date must not be earlier than valid_from")
        return self
