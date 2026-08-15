"""Dashboard V1.1 universe-aware market overview analytics."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Callable, Iterable

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.persistence.eod_read import EodSessionNotFoundError
from tip_api.read_models.market import EodReturnReadModel, LiquidityMapNodeV1, LiquidityMapV1, MarketSummaryV1, MoversV1
from tip_api.services.eod_market_data import EodMarketDataQueryService, EodQueryValidationError
from tip_api.services.eod_return_analytics import _mean, _median
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar, evaluate_market_data_freshness

DEFAULT_TRADABLE_PRICE = Decimal("5")
DEFAULT_TRADABLE_PREVIOUS_DOLLAR_VOLUME = Decimal("20000000")
DEFAULT_MAP_NODE_LIMIT = 100
MAJOR_US_EXCHANGES = frozenset({"XNYS", "XNAS", "ARCX", "BATS"})
SNAPSHOT_VALIDATION_STATUS = "file_schema_consistency_checks_passed"

TRADABLE_UNIVERSE_ID = "tradable_us_listed_equities_v1"
OPERATING_UNIVERSE_ID = "all_operating_equities"
ELIGIBLE_UNIVERSE_ID = "all_eligible_instruments"

SECTOR_BENCHMARKS = (
    ("XLC", "Communication Services"),
    ("XLY", "Consumer Discretionary"),
    ("XLP", "Consumer Staples"),
    ("XLE", "Energy"),
    ("XLF", "Financials"),
    ("XLV", "Health Care"),
    ("XLI", "Industrials"),
    ("XLB", "Materials"),
    ("XLRE", "Real Estate"),
    ("XLK", "Information Technology"),
    ("XLU", "Utilities"),
)

MARKET_BENCHMARKS = (
    ("SPY", "S&P 500 ETF"),
    ("QQQ", "Nasdaq 100 ETF"),
    ("IWM", "Russell 2000 ETF"),
    ("DIA", "Dow Industrials ETF"),
)


@dataclass(frozen=True, slots=True)
class DashboardUniverseDefinition:
    universe_id: str
    name: str
    display_name: str
    description: str


@dataclass(frozen=True, slots=True)
class DashboardUniverseAudit:
    raw_comparable_count: int
    common_stock_count: int
    adr_count: int | None
    etf_count: int
    other_excluded_type_count: int
    major_exchange_count: int
    price_gate_count: int
    final_count: int
    exclusion_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class DashboardUniverseView:
    definition: DashboardUniverseDefinition
    audit: DashboardUniverseAudit
    summary: MarketSummaryV1
    movers: MoversV1
    trading_activity_map: LiquidityMapV1
    outlier_review_count: int
    quality_flag_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class SectorBenchmarkEtf:
    ticker: str
    sector: str
    available: bool
    current_session_date: date
    previous_session_date: date
    previous_close: Decimal | None
    current_close: Decimal | None
    close_to_close_return: Decimal | None
    relative_to_spy_return: Decimal | None
    quality_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MarketBenchmark:
    benchmark_id: str
    label: str
    ticker: str | None
    available: bool
    current_session_date: date
    previous_session_date: date
    previous_close: Decimal | None
    current_close: Decimal | None
    close_to_close_return: Decimal | None
    quality_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DashboardOverviewV11:
    contract_version: str
    default_universe_id: str
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
    universes: tuple[DashboardUniverseView, ...]
    market_benchmarks: tuple[MarketBenchmark, ...]
    sector_benchmarks: tuple[SectorBenchmarkEtf, ...]
    data_status: str


@dataclass(frozen=True, slots=True)
class DashboardReturnRow:
    row: EodReturnReadModel
    previous_dollar_volume_proxy: Decimal
    universe_reasons: tuple[str, ...]
    is_operating_equity: bool
    is_major_exchange: bool
    is_price_eligible: bool
    is_liquidity_eligible: bool
    is_outlier: bool


@dataclass(frozen=True, slots=True)
class DashboardOverviewService:
    query_service: EodMarketDataQueryService
    market_calendar: MarketSessionCalendar = field(default_factory=ExchangeCalendar)
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC), repr=False)

    def get_latest_session_pair(self) -> tuple[date, date]:
        sessions = self.query_service.list_sessions()
        if len(sessions) < 2:
            raise EodSessionNotFoundError("at least two completed EOD sessions are required")
        ordered = tuple(sorted(sessions, key=lambda item: item.session_date))
        return ordered[-1].session_date, ordered[-2].session_date

    def get_latest_overview(self, *, checked_at: datetime | None = None) -> DashboardOverviewV11:
        current_date, previous_date = self.get_latest_session_pair()
        evaluation_time = checked_at or self.clock()
        freshness = evaluate_market_data_freshness(
            calendar=self.market_calendar,
            actual_latest_completed_session=current_date,
            checked_at=evaluation_time,
        )
        rows = self._compute_rows(current_session_date=current_date, previous_session_date=previous_date)
        universe_views = (
            self._build_universe(TRADABLE_UNIVERSE_ID, rows, current_date, previous_date),
            self._build_universe(OPERATING_UNIVERSE_ID, rows, current_date, previous_date),
            self._build_universe(ELIGIBLE_UNIVERSE_ID, rows, current_date, previous_date),
        )
        return DashboardOverviewV11(
            contract_version="1.2",
            default_universe_id=TRADABLE_UNIVERSE_ID,
            current_session_date=current_date,
            previous_session_date=previous_date,
            data_as_of_label=f"Data as of {current_date.isoformat()} EOD",
            snapshot_generated_at=None,
            snapshot_validation_status=SNAPSHOT_VALIDATION_STATUS,
            freshness_status=freshness.freshness_status.value,
            expected_latest_completed_session=freshness.expected_latest_completed_session,
            actual_latest_completed_session=freshness.actual_latest_completed_session,
            session_lag=freshness.session_lag,
            calendar_id=freshness.calendar_id,
            freshness_checked_at=freshness.checked_at,
            universes=universe_views,
            market_benchmarks=self._market_benchmarks(rows, universe_views[0], current_date, previous_date),
            sector_benchmarks=self._sector_benchmarks(rows, current_date, previous_date),
            data_status=SNAPSHOT_VALIDATION_STATUS if rows else "insufficient_data",
        )

    def _compute_rows(self, *, current_session_date: date, previous_session_date: date) -> tuple[DashboardReturnRow, ...]:
        current = self.query_service.repository.read_bars(current_session_date)
        previous = self.query_service.repository.read_bars(previous_session_date)
        previous_by_id = {bar.instrument_id: bar for bar in previous}
        rows: list[DashboardReturnRow] = []
        for bar in current:
            previous_bar = previous_by_id.get(bar.instrument_id)
            if previous_bar is None:
                continue
            if previous_bar.close <= 0 or bar.close <= 0:
                raise EodQueryValidationError("close prices must be positive for dashboard overview")
            close_return = (bar.close / previous_bar.close) - Decimal("1")
            current_proxy = bar.close * bar.volume
            previous_proxy = previous_bar.close * previous_bar.volume
            flags = tuple(dict.fromkeys((*bar.quality_flags, "close_times_volume_proxy")))
            status = QualityStatus.WARNING if flags else bar.quality_status
            return_row = EodReturnReadModel(
                instrument_id=bar.instrument_id,
                ticker=bar.ticker,
                name=bar.name,
                instrument_type=bar.instrument_type,
                current_session_date=current_session_date,
                previous_session_date=previous_session_date,
                previous_close=previous_bar.close,
                current_close=bar.close,
                close_to_close_return=close_return,
                current_volume=bar.volume,
                current_vwap=bar.vwap,
                current_dollar_volume_proxy=current_proxy,
                quality_status=status,
                quality_flags=flags,
            )
            is_operating = bar.instrument_type is InstrumentType.COMMON_STOCK
            is_major = bar.primary_exchange in MAJOR_US_EXCHANGES
            is_price = previous_bar.close >= DEFAULT_TRADABLE_PRICE
            is_liquid = previous_proxy >= DEFAULT_TRADABLE_PREVIOUS_DOLLAR_VOLUME
            reasons: list[str] = []
            if not is_operating:
                reasons.append("excluded_instrument_type")
            if not is_major:
                reasons.append("non_major_exchange")
            if not is_price:
                reasons.append("previous_close_below_5")
            if not is_liquid:
                reasons.append("previous_dollar_volume_below_20m")
            ratio = bar.close / previous_bar.close
            is_outlier = ratio >= Decimal("2") or ratio <= Decimal("0.5")
            if is_outlier:
                flags = tuple(dict.fromkeys((*return_row.quality_flags, "unverified_price_discontinuity")))
                return_row = replace(return_row, quality_flags=flags, quality_status=QualityStatus.WARNING)
            rows.append(
                DashboardReturnRow(
                    row=return_row,
                    previous_dollar_volume_proxy=previous_proxy,
                    universe_reasons=tuple(reasons),
                    is_operating_equity=is_operating,
                    is_major_exchange=is_major,
                    is_price_eligible=is_price,
                    is_liquidity_eligible=is_liquid,
                    is_outlier=is_outlier,
                )
            )
        return tuple(sorted(rows, key=lambda item: (item.row.ticker, str(item.row.instrument_id))))

    def _build_universe(
        self, universe_id: str, rows: tuple[DashboardReturnRow, ...], current_date: date, previous_date: date
    ) -> DashboardUniverseView:
        if universe_id == TRADABLE_UNIVERSE_ID:
            definition = DashboardUniverseDefinition(
                universe_id=universe_id,
                name="Tradable U.S.-Listed Equities V1",
                display_name="Tradable U.S. Equities",
                description="Operating common-equity securities on supported U.S. exchanges with previous-session price and liquidity gates.",
            )
            selected = tuple(item for item in rows if not item.universe_reasons)
        elif universe_id == OPERATING_UNIVERSE_ID:
            definition = DashboardUniverseDefinition(
                universe_id=universe_id,
                name="All Operating Equities",
                display_name="All Operating Equities",
                description="Operating common-equity securities without the V1 price and liquidity gates.",
            )
            selected = tuple(item for item in rows if item.is_operating_equity and item.is_major_exchange)
        elif universe_id == ELIGIBLE_UNIVERSE_ID:
            definition = DashboardUniverseDefinition(
                universe_id=universe_id,
                name="All Eligible Instruments",
                display_name="All Eligible Instruments",
                description="Broad comparable research view; may include ETFs and other supported products.",
            )
            selected = rows
        else:
            raise EodQueryValidationError("unknown dashboard universe")
        selected_rows = tuple(item.row for item in selected)
        non_outlier = tuple(item.row for item in selected if not item.is_outlier)
        return DashboardUniverseView(
            definition=definition,
            audit=_audit(rows, selected),
            summary=_summary(selected_rows, current_date, previous_date, rows),
            movers=_movers(non_outlier, current_date, previous_date),
            trading_activity_map=_trading_activity_map(non_outlier, current_date, previous_date, limit=DEFAULT_MAP_NODE_LIMIT),
            outlier_review_count=sum(1 for item in selected if item.is_outlier),
            quality_flag_counts=_quality_flag_counts(selected_rows),
        )

    def _sector_benchmarks(
        self, rows: tuple[DashboardReturnRow, ...], current_date: date, previous_date: date
    ) -> tuple[SectorBenchmarkEtf, ...]:
        by_ticker = {item.row.ticker: item.row for item in rows}
        result: list[SectorBenchmarkEtf] = []
        for ticker, sector in SECTOR_BENCHMARKS:
            row = by_ticker.get(ticker)
            if row is None or row.instrument_type is not InstrumentType.ETF:
                result.append(
                    SectorBenchmarkEtf(
                        ticker=ticker,
                        sector=sector,
                        available=False,
                        current_session_date=current_date,
                        previous_session_date=previous_date,
                        previous_close=None,
                        current_close=None,
                        close_to_close_return=None,
                        relative_to_spy_return=None,
                        quality_flags=("benchmark_unavailable",),
                    )
                )
                continue
            result.append(
                SectorBenchmarkEtf(
                    ticker=ticker,
                    sector=sector,
                    available=True,
                    current_session_date=current_date,
                    previous_session_date=previous_date,
                    previous_close=row.previous_close,
                    current_close=row.current_close,
                    close_to_close_return=row.close_to_close_return,
                    relative_to_spy_return=None,
                    quality_flags=row.quality_flags,
                )
            )
        spy = by_ticker.get("SPY")
        spy_return = spy.close_to_close_return if spy is not None and spy.instrument_type is InstrumentType.ETF else None
        with_relative = tuple(
            replace(item, relative_to_spy_return=(item.close_to_close_return - spy_return) if item.close_to_close_return is not None and spy_return is not None else None)
            for item in result
        )
        return tuple(sorted(with_relative, key=lambda item: (item.close_to_close_return is None, -(item.close_to_close_return or Decimal("-999")), item.ticker)))

    def _market_benchmarks(
        self,
        rows: tuple[DashboardReturnRow, ...],
        default_universe: DashboardUniverseView,
        current_date: date,
        previous_date: date,
    ) -> tuple[MarketBenchmark, ...]:
        by_ticker = {item.row.ticker: item.row for item in rows}
        result: list[MarketBenchmark] = []
        for ticker, label in MARKET_BENCHMARKS:
            row = by_ticker.get(ticker)
            if row is None or row.instrument_type is not InstrumentType.ETF:
                result.append(
                    MarketBenchmark(
                        benchmark_id=ticker.lower(),
                        label=label,
                        ticker=ticker,
                        available=False,
                        current_session_date=current_date,
                        previous_session_date=previous_date,
                        previous_close=None,
                        current_close=None,
                        close_to_close_return=None,
                        quality_flags=("benchmark_unavailable",),
                    )
                )
                continue
            result.append(
                MarketBenchmark(
                    benchmark_id=ticker.lower(),
                    label=label,
                    ticker=ticker,
                    available=True,
                    current_session_date=current_date,
                    previous_session_date=previous_date,
                    previous_close=row.previous_close,
                    current_close=row.current_close,
                    close_to_close_return=row.close_to_close_return,
                    quality_flags=row.quality_flags,
                )
            )
        result.append(
            MarketBenchmark(
                benchmark_id="equal_weight_universe",
                label="Equal-Weight Universe",
                ticker=None,
                available=default_universe.summary.equal_weight_return is not None,
                current_session_date=current_date,
                previous_session_date=previous_date,
                previous_close=None,
                current_close=None,
                close_to_close_return=default_universe.summary.equal_weight_return,
                quality_flags=("equal_weight_not_index_return",),
            )
        )
        return tuple(result)


def _audit(rows: tuple[DashboardReturnRow, ...], selected: tuple[DashboardReturnRow, ...]) -> DashboardUniverseAudit:
    exclusion_counts: dict[str, int] = {}
    for item in rows:
        for reason in item.universe_reasons:
            exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
    return DashboardUniverseAudit(
        raw_comparable_count=len(rows),
        common_stock_count=sum(1 for item in rows if item.row.instrument_type is InstrumentType.COMMON_STOCK),
        adr_count=None,
        etf_count=sum(1 for item in rows if item.row.instrument_type is InstrumentType.ETF),
        other_excluded_type_count=sum(1 for item in rows if item.row.instrument_type not in {InstrumentType.COMMON_STOCK, InstrumentType.ETF}),
        major_exchange_count=sum(1 for item in rows if item.is_major_exchange),
        price_gate_count=sum(1 for item in rows if item.is_operating_equity and item.is_major_exchange and item.is_price_eligible),
        final_count=len(selected),
        exclusion_counts=dict(sorted(exclusion_counts.items())),
    )


def _summary(rows: tuple[EodReturnReadModel, ...], current_date: date, previous_date: date, all_rows: tuple[DashboardReturnRow, ...]) -> MarketSummaryV1:
    advancers = tuple(row for row in rows if row.close_to_close_return > 0)
    decliners = tuple(row for row in rows if row.close_to_close_return < 0)
    unchanged = tuple(row for row in rows if row.close_to_close_return == 0)
    advancer_volume = sum((row.current_volume for row in advancers), Decimal("0"))
    decliner_volume = sum((row.current_volume for row in decliners), Decimal("0"))
    count = len(rows)
    return MarketSummaryV1(
        current_session_date=current_date,
        previous_session_date=previous_date,
        comparable_instrument_count=count,
        current_only_count=0,
        previous_only_count=0,
        advancer_count=len(advancers),
        decliner_count=len(decliners),
        unchanged_count=len(unchanged),
        advance_decline_ratio=(Decimal(len(advancers)) / Decimal(len(decliners))) if decliners else None,
        advance_decline_net=len(advancers) - len(decliners),
        advancer_volume=advancer_volume,
        decliner_volume=decliner_volume,
        up_down_volume_ratio=(advancer_volume / decliner_volume) if decliner_volume else None,
        equal_weight_return=_mean(tuple(row.close_to_close_return for row in rows)),
        median_return=_median(tuple(row.close_to_close_return for row in rows)),
        positive_return_share=(Decimal(len(advancers)) / Decimal(count)) if count else None,
        negative_return_share=(Decimal(len(decliners)) / Decimal(count)) if count else None,
        common_stock_comparable_count=sum(1 for row in rows if row.instrument_type is InstrumentType.COMMON_STOCK),
        etf_comparable_count=sum(1 for row in rows if row.instrument_type is InstrumentType.ETF),
        quality_warning_count=sum(1 for row in rows if row.quality_flags),
        data_status="complete" if all_rows else "insufficient_data",
    )


def _movers(rows: tuple[EodReturnReadModel, ...], current_date: date, previous_date: date) -> MoversV1:
    gainers = tuple(sorted((row for row in rows if row.close_to_close_return > 0), key=lambda row: (-row.close_to_close_return, -row.current_dollar_volume_proxy, row.ticker))[:10])
    losers = tuple(sorted((row for row in rows if row.close_to_close_return < 0), key=lambda row: (row.close_to_close_return, -row.current_dollar_volume_proxy, row.ticker))[:10])
    return MoversV1(current_session_date=current_date, previous_session_date=previous_date, threshold=DEFAULT_TRADABLE_PREVIOUS_DOLLAR_VOLUME, top_gainers=gainers, top_losers=losers)


def _trading_activity_map(
    rows: tuple[EodReturnReadModel, ...], current_date: date, previous_date: date, *, limit: int
) -> LiquidityMapV1:
    ranked = sorted(rows, key=lambda row: (-row.current_dollar_volume_proxy, row.ticker, str(row.instrument_id)))
    nodes = tuple(
        LiquidityMapNodeV1(
            instrument_id=row.instrument_id,
            ticker=row.ticker,
            name=row.name,
            instrument_type=row.instrument_type,
            size_value=row.current_dollar_volume_proxy,
            color_value=row.close_to_close_return,
            current_close=row.current_close,
            current_volume=row.current_volume,
            rank=index + 1,
            quality_flags=row.quality_flags,
        )
        for index, row in enumerate(ranked[:limit])
    )
    return LiquidityMapV1(
        map_type="trading_activity",
        size_metric="close_times_volume_proxy",
        color_metric="close_to_close_return",
        is_market_cap_weighted=False,
        is_sector_grouped=False,
        threshold=DEFAULT_TRADABLE_PREVIOUS_DOLLAR_VOLUME,
        current_session_date=current_date,
        previous_session_date=previous_date,
        nodes=nodes,
    )


def _quality_flag_counts(rows: Iterable[EodReturnReadModel]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for flag in row.quality_flags:
            counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))
