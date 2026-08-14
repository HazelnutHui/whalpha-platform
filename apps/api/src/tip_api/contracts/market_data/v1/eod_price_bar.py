"""EOD Price Bar V1 provider-neutral contract."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, field_validator, model_validator

from tip_api.contracts.common import (
    QualityStatus,
    ensure_finite_decimal,
    normalize_optional_string,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)

_FLAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class EodPriceBarV1(BaseModel):
    """End-of-day price and volume contract for one trading session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: UUID
    session_date: date

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: StrictInt
    vwap: Decimal | None = None
    trade_count: StrictInt | None = None
    notional: Decimal
    currency: str

    split_adjustment_factor: Decimal
    dividend_adjustment_factor: Decimal
    total_return_adjustment_factor: Decimal
    adjusted_close: Decimal

    source: str
    source_record_id: str | None = None
    ingested_at: datetime
    revision: StrictInt
    is_latest_revision: StrictBool
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()
    schema_version: Literal["1.0"] = "1.0"

    @field_validator("session_date", mode="before")
    @classmethod
    def reject_datetime_for_session_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime value")
        return value

    @field_validator(
        "open",
        "high",
        "low",
        "close",
        "vwap",
        "notional",
        "split_adjustment_factor",
        "dividend_adjustment_factor",
        "total_return_adjustment_factor",
        "adjusted_close",
        mode="before",
    )
    @classmethod
    def reject_float_decimals(cls, value: Any, info: Any) -> Any:
        if value is None:
            return None
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "open",
        "high",
        "low",
        "close",
        "vwap",
        "notional",
        "split_adjustment_factor",
        "dividend_adjustment_factor",
        "total_return_adjustment_factor",
        "adjusted_close",
    )
    @classmethod
    def validate_finite_decimal(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is None:
            return None
        return ensure_finite_decimal(value, field_name=info.field_name)

    @field_validator("open", "high", "low", "close", "vwap", "adjusted_close")
    @classmethod
    def validate_positive_price(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError(f"{info.field_name} must be greater than zero")
        return value

    @field_validator(
        "split_adjustment_factor",
        "dividend_adjustment_factor",
        "total_return_adjustment_factor",
    )
    @classmethod
    def validate_positive_adjustment_factor(cls, value: Decimal, info: Any) -> Decimal:
        if value <= 0:
            raise ValueError(f"{info.field_name} must be greater than zero")
        return value

    @field_validator("notional")
    @classmethod
    def validate_non_negative_notional(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("notional must be greater than or equal to zero")
        return value

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, value: int) -> int:
        if value < 0:
            raise ValueError("volume must be greater than or equal to zero")
        return value

    @field_validator("trade_count")
    @classmethod
    def validate_trade_count(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("trade_count must be greater than or equal to zero")
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = normalize_required_string(value, field_name="currency", uppercase=True)
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter code")
        return currency

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return normalize_required_string(value, field_name="source")

    @field_validator("source_record_id", mode="before")
    @classmethod
    def normalize_source_record_id(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="source_record_id")

    @field_validator("ingested_at")
    @classmethod
    def normalize_ingested_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("revision")
    @classmethod
    def validate_revision(cls, value: int) -> int:
        if value < 1:
            raise ValueError("revision must be greater than or equal to one")
        return value

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalize_quality_flags(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            raise ValueError("quality_flags must be an iterable of strings, not a string")
        seen: set[str] = set()
        normalized_flags: list[str] = []
        for raw_flag in value:
            flag = normalize_required_string(raw_flag, field_name="quality_flags")
            flag = re.sub(r"[\s-]+", "_", flag.lower())
            if not _FLAG_PATTERN.fullmatch(flag):
                raise ValueError("quality_flags must normalize to lowercase snake_case")
            if flag not in seen:
                seen.add(flag)
                normalized_flags.append(flag)
        return tuple(normalized_flags)

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> EodPriceBarV1:
        if self.high < self.open:
            raise ValueError("high must be greater than or equal to open")
        if self.high < self.close:
            raise ValueError("high must be greater than or equal to close")
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if self.low > self.open:
            raise ValueError("low must be less than or equal to open")
        if self.low > self.close:
            raise ValueError("low must be less than or equal to close")
        if self.low > self.high:
            raise ValueError("low must be less than or equal to high")
        return self
