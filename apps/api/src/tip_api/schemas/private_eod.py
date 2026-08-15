"""Private EOD market-data API response contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor, EodSessionPage, EodSessionSummary


def _decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.normalize(), "f")


class EodSessionDescriptorResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    session_date: date
    record_count: int
    completion_status: str
    identity_as_of_date: date
    available_at: datetime
    quality_warning_count: int

    @classmethod
    def from_read_model(cls, model: EodSessionDescriptor) -> EodSessionDescriptorResponse:
        return cls(
            schema_version=model.schema_version,
            session_date=model.session_date,
            record_count=model.record_count,
            completion_status=model.completion_status,
            identity_as_of_date=model.identity_as_of_date,
            available_at=model.available_at,
            quality_warning_count=model.quality_warning_count,
        )


class EodSessionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sessions: tuple[EodSessionDescriptorResponse, ...]


class EodMarketBarResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: UUID
    ticker: str
    name: str
    instrument_type: str
    session_date: date
    open: str = Field(description="Exact decimal string")
    high: str = Field(description="Exact decimal string")
    low: str = Field(description="Exact decimal string")
    close: str = Field(description="Exact decimal string")
    volume: str = Field(description="Exact decimal string")
    vwap: str | None = Field(default=None, description="Exact decimal string when available")
    trade_count: int | None
    currency: str
    source: str
    quality_status: str
    quality_flags: tuple[str, ...]

    @classmethod
    def from_read_model(cls, model: EodMarketBarReadModel) -> EodMarketBarResponse:
        return cls(
            instrument_id=model.instrument_id,
            ticker=model.ticker,
            name=model.name,
            instrument_type=model.instrument_type.value,
            session_date=model.session_date,
            open=_decimal_string(model.open) or "",
            high=_decimal_string(model.high) or "",
            low=_decimal_string(model.low) or "",
            close=_decimal_string(model.close) or "",
            volume=_decimal_string(model.volume) or "",
            vwap=_decimal_string(model.vwap),
            trade_count=model.trade_count,
            currency=model.currency,
            source=model.source,
            quality_status=model.quality_status.value,
            quality_flags=model.quality_flags,
        )


class EodSessionPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_date: date
    total_count: int
    limit: int
    offset: int
    items: tuple[EodMarketBarResponse, ...]

    @classmethod
    def from_read_model(cls, model: EodSessionPage) -> EodSessionPageResponse:
        return cls(
            session_date=model.session_date,
            total_count=model.total_count,
            limit=model.limit,
            offset=model.offset,
            items=tuple(EodMarketBarResponse.from_read_model(item) for item in model.items),
        )


class EodSessionSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_date: date
    total_records: int
    common_stock_count: int
    etf_count: int
    other_supported_count: int
    missing_vwap_count: int
    missing_trade_count_count: int
    zero_volume_count: int
    quality_warning_count: int
    source: str
    identity_as_of_date: date

    @classmethod
    def from_read_model(cls, model: EodSessionSummary) -> EodSessionSummaryResponse:
        return cls(
            session_date=model.session_date,
            total_records=model.total_records,
            common_stock_count=model.common_stock_count,
            etf_count=model.etf_count,
            other_supported_count=model.other_supported_count,
            missing_vwap_count=model.missing_vwap_count,
            missing_trade_count_count=model.missing_trade_count_count,
            zero_volume_count=model.zero_volume_count,
            quality_warning_count=model.quality_warning_count,
            source=model.source,
            identity_as_of_date=model.identity_as_of_date,
        )
