"""Private market summary API response contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tip_api.read_models.market import EodReturnReadModel, LiquidityMapNodeV1, LiquidityMapV1, MarketSummaryV1, MoversV1


def decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.normalize(), "f")


class EodReturnResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    instrument_id: UUID
    ticker: str
    name: str
    instrument_type: str
    current_session_date: date
    previous_session_date: date
    previous_close: str
    current_close: str
    close_to_close_return: str = Field(description="Decimal ratio; 0.05 means 5%")
    current_volume: str
    current_vwap: str | None
    current_dollar_volume_proxy: str = Field(description="current_close times current_volume; not notional, market cap, or fund flow")
    quality_status: str
    quality_flags: tuple[str, ...]

    @classmethod
    def from_model(cls, model: EodReturnReadModel) -> EodReturnResponse:
        return cls(
            instrument_id=model.instrument_id,
            ticker=model.ticker,
            name=model.name,
            instrument_type=model.instrument_type.value,
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            previous_close=decimal_string(model.previous_close) or "",
            current_close=decimal_string(model.current_close) or "",
            close_to_close_return=decimal_string(model.close_to_close_return) or "",
            current_volume=decimal_string(model.current_volume) or "",
            current_vwap=decimal_string(model.current_vwap),
            current_dollar_volume_proxy=decimal_string(model.current_dollar_volume_proxy) or "",
            quality_status=model.quality_status.value,
            quality_flags=model.quality_flags,
        )


class EodReturnsPageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    current_session_date: date
    previous_session_date: date
    total_count: int
    limit: int
    offset: int
    items: tuple[EodReturnResponse, ...]


class MarketSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    current_session_date: date
    previous_session_date: date
    comparable_instrument_count: int
    current_only_count: int
    previous_only_count: int
    advancer_count: int
    decliner_count: int
    unchanged_count: int
    advance_decline_ratio: str | None
    advance_decline_net: int
    advancer_volume: str
    decliner_volume: str
    up_down_volume_ratio: str | None
    equal_weight_return: str | None
    median_return: str | None
    positive_return_share: str | None
    negative_return_share: str | None
    common_stock_comparable_count: int
    etf_comparable_count: int
    quality_warning_count: int
    data_status: str

    @classmethod
    def from_model(cls, model: MarketSummaryV1) -> MarketSummaryResponse:
        return cls(
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            comparable_instrument_count=model.comparable_instrument_count,
            current_only_count=model.current_only_count,
            previous_only_count=model.previous_only_count,
            advancer_count=model.advancer_count,
            decliner_count=model.decliner_count,
            unchanged_count=model.unchanged_count,
            advance_decline_ratio=decimal_string(model.advance_decline_ratio),
            advance_decline_net=model.advance_decline_net,
            advancer_volume=decimal_string(model.advancer_volume) or "0",
            decliner_volume=decimal_string(model.decliner_volume) or "0",
            up_down_volume_ratio=decimal_string(model.up_down_volume_ratio),
            equal_weight_return=decimal_string(model.equal_weight_return),
            median_return=decimal_string(model.median_return),
            positive_return_share=decimal_string(model.positive_return_share),
            negative_return_share=decimal_string(model.negative_return_share),
            common_stock_comparable_count=model.common_stock_comparable_count,
            etf_comparable_count=model.etf_comparable_count,
            quality_warning_count=model.quality_warning_count,
            data_status=model.data_status,
        )


class MoversResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    current_session_date: date
    previous_session_date: date
    threshold: str
    top_gainers: tuple[EodReturnResponse, ...]
    top_losers: tuple[EodReturnResponse, ...]

    @classmethod
    def from_model(cls, model: MoversV1) -> MoversResponse:
        return cls(
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            threshold=decimal_string(model.threshold) or "",
            top_gainers=tuple(EodReturnResponse.from_model(item) for item in model.top_gainers),
            top_losers=tuple(EodReturnResponse.from_model(item) for item in model.top_losers),
        )


class LiquidityMapNodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    instrument_id: UUID
    ticker: str
    name: str
    instrument_type: str
    size_value: str
    color_value: str
    current_close: str
    current_volume: str
    rank: int
    quality_flags: tuple[str, ...]

    @classmethod
    def from_model(cls, model: LiquidityMapNodeV1) -> LiquidityMapNodeResponse:
        return cls(
            instrument_id=model.instrument_id,
            ticker=model.ticker,
            name=model.name,
            instrument_type=model.instrument_type.value,
            size_value=decimal_string(model.size_value) or "",
            color_value=decimal_string(model.color_value) or "",
            current_close=decimal_string(model.current_close) or "",
            current_volume=decimal_string(model.current_volume) or "",
            rank=model.rank,
            quality_flags=model.quality_flags,
        )


class LiquidityMapResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    map_type: str
    size_metric: str
    color_metric: str
    is_market_cap_weighted: bool
    is_sector_grouped: bool
    threshold: str
    current_session_date: date
    previous_session_date: date
    nodes: tuple[LiquidityMapNodeResponse, ...]

    @classmethod
    def from_model(cls, model: LiquidityMapV1) -> LiquidityMapResponse:
        return cls(
            map_type=model.map_type,
            size_metric=model.size_metric,
            color_metric=model.color_metric,
            is_market_cap_weighted=model.is_market_cap_weighted,
            is_sector_grouped=model.is_sector_grouped,
            threshold=decimal_string(model.threshold) or "",
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            nodes=tuple(LiquidityMapNodeResponse.from_model(item) for item in model.nodes),
        )
