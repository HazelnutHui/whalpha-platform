"""Read models for canonical EOD market data queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus


@dataclass(frozen=True, slots=True)
class EodSessionDescriptor:
    schema_version: str
    session_date: date
    record_count: int
    completion_status: str
    identity_as_of_date: date
    available_at: datetime
    quality_warning_count: int


@dataclass(frozen=True, slots=True)
class EodMarketBarReadModel:
    instrument_id: UUID
    ticker: str
    name: str
    instrument_type: InstrumentType
    primary_exchange: str
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None
    trade_count: int | None
    currency: str
    source: str
    quality_status: QualityStatus
    quality_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EodSessionPage:
    session_date: date
    total_count: int
    limit: int
    offset: int
    items: tuple[EodMarketBarReadModel, ...]


@dataclass(frozen=True, slots=True)
class EodSessionSummary:
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
