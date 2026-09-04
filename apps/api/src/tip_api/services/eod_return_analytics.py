"""Provider-neutral close-to-close EOD return analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.persistence.eod_read import EodSessionNotFoundError
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.read_models.market import EodReturnReadModel, LiquidityMapNodeV1, LiquidityMapV1, MarketSummaryV1, MoversV1
from tip_api.services.eod_market_data import EodMarketDataQueryService, EodQueryValidationError

DEFAULT_LIQUIDITY_THRESHOLD = Decimal("5000000")


@dataclass(frozen=True, slots=True)
class EodReturnAnalyticsService:
    query_service: EodMarketDataQueryService

    def get_latest_session_pair(self) -> tuple[date, date]:
        session_dates = self.query_service.list_session_dates()
        if len(session_dates) < 2:
            raise EodSessionNotFoundError("at least two completed EOD sessions are required")
        return session_dates[-1], session_dates[-2]

    def compute_returns(self, *, current_session_date: date, previous_session_date: date) -> tuple[EodReturnReadModel, ...]:
        current = self.query_service.repository.read_bars(current_session_date)
        previous = self.query_service.repository.read_bars(previous_session_date)
        previous_by_id = {bar.instrument_id: bar for bar in previous}
        returns: list[EodReturnReadModel] = []
        for bar in current:
            previous_bar = previous_by_id.get(bar.instrument_id)
            if previous_bar is None:
                continue
            if previous_bar.close <= 0 or bar.close <= 0:
                raise EodQueryValidationError("close prices must be positive for return analytics")
            close_return = (bar.close / previous_bar.close) - Decimal("1")
            proxy = bar.close * bar.volume
            flags = tuple(dict.fromkeys((*bar.quality_flags, "close_times_volume_proxy")))
            status = QualityStatus.WARNING if flags else bar.quality_status
            returns.append(
                EodReturnReadModel(
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
                    current_dollar_volume_proxy=proxy,
                    quality_status=status,
                    quality_flags=flags,
                )
            )
        return tuple(sorted(returns, key=lambda item: (item.ticker, str(item.instrument_id))))

    def get_latest_returns_page(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        ticker: str | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> tuple[tuple[EodReturnReadModel, ...], int, date, date]:
        if limit < 1 or limit > 200:
            raise EodQueryValidationError("limit must be between 1 and 200")
        if offset < 0:
            raise EodQueryValidationError("offset must be greater than or equal to zero")
        current_date, previous_date = self.get_latest_session_pair()
        rows = self.compute_returns(current_session_date=current_date, previous_session_date=previous_date)
        if ticker is not None:
            normalized = ticker.strip().upper()
            rows = tuple(row for row in rows if row.ticker == normalized)
        if instrument_type is not None:
            rows = tuple(row for row in rows if row.instrument_type is instrument_type)
        return rows[offset : offset + limit], len(rows), current_date, previous_date

    def get_latest_summary(self) -> MarketSummaryV1:
        current_date, previous_date = self.get_latest_session_pair()
        current = self.query_service.repository.read_bars(current_date)
        previous = self.query_service.repository.read_bars(previous_date)
        returns = self.compute_returns(current_session_date=current_date, previous_session_date=previous_date)
        current_ids = {bar.instrument_id for bar in current}
        previous_ids = {bar.instrument_id for bar in previous}
        advancers = tuple(row for row in returns if row.close_to_close_return > 0)
        decliners = tuple(row for row in returns if row.close_to_close_return < 0)
        unchanged = tuple(row for row in returns if row.close_to_close_return == 0)
        advancer_volume = sum((row.current_volume for row in advancers), Decimal("0"))
        decliner_volume = sum((row.current_volume for row in decliners), Decimal("0"))
        count = len(returns)
        return MarketSummaryV1(
            current_session_date=current_date,
            previous_session_date=previous_date,
            comparable_instrument_count=count,
            current_only_count=len(current_ids - previous_ids),
            previous_only_count=len(previous_ids - current_ids),
            advancer_count=len(advancers),
            decliner_count=len(decliners),
            unchanged_count=len(unchanged),
            advance_decline_ratio=(Decimal(len(advancers)) / Decimal(len(decliners))) if decliners else None,
            advance_decline_net=len(advancers) - len(decliners),
            advancer_volume=advancer_volume,
            decliner_volume=decliner_volume,
            up_down_volume_ratio=(advancer_volume / decliner_volume) if decliner_volume else None,
            equal_weight_return=_mean(tuple(row.close_to_close_return for row in returns)),
            median_return=_median(tuple(row.close_to_close_return for row in returns)),
            positive_return_share=(Decimal(len(advancers)) / Decimal(count)) if count else None,
            negative_return_share=(Decimal(len(decliners)) / Decimal(count)) if count else None,
            common_stock_comparable_count=sum(1 for row in returns if row.instrument_type is InstrumentType.COMMON_STOCK),
            etf_comparable_count=sum(1 for row in returns if row.instrument_type is InstrumentType.ETF),
            quality_warning_count=sum(1 for row in returns if row.quality_flags),
            data_status="complete" if count else "insufficient_data",
        )

    def get_latest_movers(self, *, per_side: int = 10, threshold: Decimal = DEFAULT_LIQUIDITY_THRESHOLD) -> MoversV1:
        if per_side < 1 or per_side > 50:
            raise EodQueryValidationError("per_side must be between 1 and 50")
        current_date, previous_date = self.get_latest_session_pair()
        rows = tuple(row for row in self.compute_returns(current_session_date=current_date, previous_session_date=previous_date) if row.current_dollar_volume_proxy >= threshold)
        gainers = tuple(sorted((row for row in rows if row.close_to_close_return > 0), key=lambda row: (-row.close_to_close_return, -row.current_dollar_volume_proxy, row.ticker))[:per_side])
        losers = tuple(sorted((row for row in rows if row.close_to_close_return < 0), key=lambda row: (row.close_to_close_return, -row.current_dollar_volume_proxy, row.ticker))[:per_side])
        return MoversV1(current_session_date=current_date, previous_session_date=previous_date, threshold=threshold, top_gainers=gainers, top_losers=losers)

    def get_latest_liquidity_map(self, *, limit: int = 300, threshold: Decimal = DEFAULT_LIQUIDITY_THRESHOLD) -> LiquidityMapV1:
        if limit < 1 or limit > 500:
            raise EodQueryValidationError("limit must be between 1 and 500")
        current_date, previous_date = self.get_latest_session_pair()
        rows = [row for row in self.compute_returns(current_session_date=current_date, previous_session_date=previous_date) if row.current_dollar_volume_proxy >= threshold]
        rows.sort(key=lambda row: (-row.current_dollar_volume_proxy, row.ticker, str(row.instrument_id)))
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
            for index, row in enumerate(rows[:limit])
        )
        return LiquidityMapV1(
            map_type="liquidity",
            size_metric="close_times_volume_proxy",
            color_metric="close_to_close_return",
            is_market_cap_weighted=False,
            is_sector_grouped=False,
            threshold=threshold,
            current_session_date=current_date,
            previous_session_date=previous_date,
            nodes=nodes,
        )


def _mean(values: tuple[Decimal, ...]) -> Decimal | None:
    return (sum(values, Decimal("0")) / Decimal(len(values))) if values else None


def _median(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")
