"""Read models for private market summary analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus


@dataclass(frozen=True, slots=True)
class EodReturnReadModel:
    instrument_id: UUID
    ticker: str
    name: str
    instrument_type: InstrumentType
    current_session_date: date
    previous_session_date: date
    previous_close: Decimal
    current_close: Decimal
    close_to_close_return: Decimal
    current_volume: Decimal
    current_vwap: Decimal | None
    current_dollar_volume_proxy: Decimal
    quality_status: QualityStatus
    quality_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MarketSummaryV1:
    current_session_date: date
    previous_session_date: date
    comparable_instrument_count: int
    current_only_count: int
    previous_only_count: int
    advancer_count: int
    decliner_count: int
    unchanged_count: int
    advance_decline_ratio: Decimal | None
    advance_decline_net: int
    advancer_volume: Decimal
    decliner_volume: Decimal
    up_down_volume_ratio: Decimal | None
    equal_weight_return: Decimal | None
    median_return: Decimal | None
    positive_return_share: Decimal | None
    negative_return_share: Decimal | None
    common_stock_comparable_count: int
    etf_comparable_count: int
    quality_warning_count: int
    data_status: str


@dataclass(frozen=True, slots=True)
class MoversV1:
    current_session_date: date
    previous_session_date: date
    threshold: Decimal
    top_gainers: tuple[EodReturnReadModel, ...]
    top_losers: tuple[EodReturnReadModel, ...]


@dataclass(frozen=True, slots=True)
class LiquidityMapNodeV1:
    instrument_id: UUID
    ticker: str
    name: str
    instrument_type: InstrumentType
    size_value: Decimal
    color_value: Decimal
    current_close: Decimal
    current_volume: Decimal
    rank: int
    quality_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LiquidityMapV1:
    map_type: str
    size_metric: str
    color_metric: str
    is_market_cap_weighted: bool
    is_sector_grouped: bool
    threshold: Decimal
    current_session_date: date
    previous_session_date: date
    nodes: tuple[LiquidityMapNodeV1, ...]
