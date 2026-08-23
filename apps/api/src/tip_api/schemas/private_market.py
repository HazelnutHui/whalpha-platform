"""Private market summary API response contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.read_models.market import EodReturnReadModel, LiquidityMapNodeV1, LiquidityMapV1, MarketSummaryV1, MoversV1
from tip_api.services.dashboard_overview import (
    DashboardOverviewV11,
    DashboardUniverseAudit,
    DashboardUniverseDefinition,
    DashboardUniverseFunnelStage,
    DashboardUniverseView,
    MarketBenchmark,
    SectorBenchmarkEtf,
)


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
    universe_id: str | None = None
    universe_membership_fingerprint: str | None = None
    universe_member_count: int | None = None


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
    universe_id: str | None = None
    universe_membership_fingerprint: str | None = None
    universe_member_count: int | None = None

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
    universe_id: str | None = None
    universe_membership_fingerprint: str | None = None
    universe_member_count: int | None = None

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
    universe_id: str | None = None
    universe_membership_fingerprint: str | None = None
    universe_member_count: int | None = None

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


class DashboardUniverseDefinitionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    universe_id: str
    name: str
    display_name: str
    description: str
    long_display_name: str
    provisional: bool
    member_count: int
    security_type_composition: dict[str, int]
    membership_fingerprint: str

    @classmethod
    def from_model(cls, model: DashboardUniverseDefinition) -> DashboardUniverseDefinitionResponse:
        return cls(
            universe_id=model.universe_id,
            name=model.name,
            display_name=model.display_name,
            description=model.description,
            long_display_name=model.long_display_name,
            provisional=model.provisional,
            member_count=model.member_count,
            security_type_composition=model.security_type_composition,
            membership_fingerprint=model.membership_fingerprint,
        )


class DashboardUniverseAuditResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    raw_comparable_count: int
    common_stock_count: int
    adr_count: int | None
    etf_count: int
    other_excluded_type_count: int
    major_exchange_count: int
    price_gate_count: int
    final_count: int
    exclusion_counts: dict[str, int]

    @classmethod
    def from_model(cls, model: DashboardUniverseAudit) -> DashboardUniverseAuditResponse:
        return cls(
            raw_comparable_count=model.raw_comparable_count,
            common_stock_count=model.common_stock_count,
            adr_count=model.adr_count,
            etf_count=model.etf_count,
            other_excluded_type_count=model.other_excluded_type_count,
            major_exchange_count=model.major_exchange_count,
            price_gate_count=model.price_gate_count,
            final_count=model.final_count,
            exclusion_counts=model.exclusion_counts,
        )


class DashboardUniverseFunnelStageResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    universe_id: str
    stage_index: int = Field(ge=1, le=10)
    stage_id: str
    display_label: str
    input_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    remaining_count: int = Field(ge=0)
    source_revision: str
    source_session: date
    source_fingerprint: str

    @model_validator(mode="after")
    def closes(self) -> "DashboardUniverseFunnelStageResponse":
        if self.input_count - self.excluded_count != self.remaining_count:
            raise ValueError("Funnel stage does not close")
        return self

    @classmethod
    def from_model(cls, model: DashboardUniverseFunnelStage) -> "DashboardUniverseFunnelStageResponse":
        return cls(universe_id=model.universe_id, stage_index=model.stage_index, stage_id=model.stage_id, display_label=model.display_label, input_count=model.input_count, excluded_count=model.excluded_count, remaining_count=model.remaining_count, source_revision=model.source_revision, source_session=model.source_session, source_fingerprint=model.source_fingerprint)


class DashboardUniverseViewResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    definition: DashboardUniverseDefinitionResponse
    audit: DashboardUniverseAuditResponse
    summary: MarketSummaryResponse
    movers: MoversResponse
    trading_activity_map: LiquidityMapResponse
    outlier_review_count: int
    quality_flag_counts: dict[str, int]
    equal_weight_benchmark: MarketBenchmarkResponse
    funnel: tuple[DashboardUniverseFunnelStageResponse, ...] = ()

    @model_validator(mode="after")
    def funnel_contract(self) -> "DashboardUniverseViewResponse":
        if not self.funnel:
            return self
        if len(self.funnel) != 10 or tuple(item.stage_index for item in self.funnel) != tuple(range(1, 11)):
            raise ValueError("formal Universe Funnel must have ten ordered stages")
        if any(item.universe_id != self.definition.universe_id for item in self.funnel):
            raise ValueError("Funnel stage Universe reference mismatch")
        if any(current.remaining_count != following.input_count for current, following in zip(self.funnel, self.funnel[1:])):
            raise ValueError("Universe Funnel stages do not close sequentially")
        if self.funnel[-1].remaining_count != self.definition.member_count:
            raise ValueError("Universe Funnel final count disagrees with membership")
        return self

    @classmethod
    def from_model(cls, model: DashboardUniverseView) -> DashboardUniverseViewResponse:
        return cls(
            definition=DashboardUniverseDefinitionResponse.from_model(model.definition),
            audit=DashboardUniverseAuditResponse.from_model(model.audit),
            summary=MarketSummaryResponse.from_model(model.summary),
            movers=MoversResponse.from_model(model.movers),
            trading_activity_map=LiquidityMapResponse.from_model(model.trading_activity_map),
            outlier_review_count=model.outlier_review_count,
            quality_flag_counts=model.quality_flag_counts,
            equal_weight_benchmark=MarketBenchmarkResponse.from_model(model.equal_weight_benchmark),
            funnel=tuple(DashboardUniverseFunnelStageResponse.from_model(item) for item in model.funnel),
        )


class SectorBenchmarkEtfResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ticker: str
    sector: str
    available: bool
    current_session_date: date
    previous_session_date: date
    previous_close: str | None
    current_close: str | None
    close_to_close_return: str | None
    relative_to_spy_return: str | None = Field(description="Arithmetic difference between sector ETF return and SPY return; not alpha or risk-adjusted return")
    quality_flags: tuple[str, ...]

    @classmethod
    def from_model(cls, model: SectorBenchmarkEtf) -> SectorBenchmarkEtfResponse:
        return cls(
            ticker=model.ticker,
            sector=model.sector,
            available=model.available,
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            previous_close=decimal_string(model.previous_close),
            current_close=decimal_string(model.current_close),
            close_to_close_return=decimal_string(model.close_to_close_return),
            relative_to_spy_return=decimal_string(model.relative_to_spy_return),
            quality_flags=model.quality_flags,
        )


class MarketBenchmarkResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    benchmark_id: str
    label: str
    ticker: str | None
    available: bool
    current_session_date: date
    previous_session_date: date
    previous_close: str | None
    current_close: str | None
    close_to_close_return: str | None
    quality_flags: tuple[str, ...]

    @classmethod
    def from_model(cls, model: MarketBenchmark) -> MarketBenchmarkResponse:
        return cls(
            benchmark_id=model.benchmark_id,
            label=model.label,
            ticker=model.ticker,
            available=model.available,
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            previous_close=decimal_string(model.previous_close),
            current_close=decimal_string(model.current_close),
            close_to_close_return=decimal_string(model.close_to_close_return),
            quality_flags=model.quality_flags,
        )


class DashboardOverviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    contract_version: str
    default_universe_id: str
    selected_universe_id: str
    universe_definition_id: str
    universe_version: str
    governance_status: str
    classification_as_of_date: date
    trailing_window_start: date
    trailing_window_end: date
    trailing_window_session_count: int
    reviewed_override_count: int
    activation_fingerprint: str
    legacy_rollback_available: bool
    evidence_coverage_status: str
    current_session_date: date
    previous_session_date: date
    data_as_of_label: str
    snapshot_generated_at: str | None
    snapshot_validation_status: str
    freshness_status: str
    expected_latest_completed_session: date | None
    actual_latest_completed_session: date | None
    session_lag: int | None
    calendar_id: str
    freshness_checked_at: datetime
    universes: tuple[DashboardUniverseViewResponse, ...]
    market_benchmarks: tuple[MarketBenchmarkResponse, ...]
    sector_benchmarks: tuple[SectorBenchmarkEtfResponse, ...]
    data_status: str

    @classmethod
    def from_model(cls, model: DashboardOverviewV11) -> DashboardOverviewResponse:
        return cls(
            contract_version=model.contract_version,
            default_universe_id=model.default_universe_id,
            selected_universe_id=model.selected_universe_id,
            universe_definition_id=model.universe_definition_id,
            universe_version=model.universe_version,
            governance_status=model.governance_status,
            classification_as_of_date=model.classification_as_of_date,
            trailing_window_start=model.trailing_window_start,
            trailing_window_end=model.trailing_window_end,
            trailing_window_session_count=model.trailing_window_session_count,
            reviewed_override_count=model.reviewed_override_count,
            activation_fingerprint=model.activation_fingerprint,
            legacy_rollback_available=model.legacy_rollback_available,
            evidence_coverage_status=model.evidence_coverage_status,
            current_session_date=model.current_session_date,
            previous_session_date=model.previous_session_date,
            data_as_of_label=model.data_as_of_label,
            snapshot_generated_at=model.snapshot_generated_at,
            snapshot_validation_status=model.snapshot_validation_status,
            freshness_status=model.freshness_status,
            expected_latest_completed_session=model.expected_latest_completed_session,
            actual_latest_completed_session=model.actual_latest_completed_session,
            session_lag=model.session_lag,
            calendar_id=model.calendar_id,
            freshness_checked_at=model.freshness_checked_at,
            universes=tuple(DashboardUniverseViewResponse.from_model(item) for item in model.universes),
            market_benchmarks=tuple(MarketBenchmarkResponse.from_model(item) for item in model.market_benchmarks),
            sector_benchmarks=tuple(SectorBenchmarkEtfResponse.from_model(item) for item in model.sector_benchmarks),
            data_status=model.data_status,
        )
