from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import InstrumentType, QualityStatus
from tip_api.persistence.eod_read import EodReadRepository, EodSessionNotFoundError
from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor
from tip_api.services.eod_market_data import EodMarketDataQueryService, EodQueryValidationError
from tip_api.services.eod_return_analytics import EodReturnAnalyticsService

CURRENT = date(2026, 8, 13)
PREVIOUS = date(2026, 8, 12)
CREATED = datetime(2026, 8, 14, tzinfo=UTC)
ID_A = UUID("00000000-0000-5000-8000-100000000001")
ID_B = UUID("00000000-0000-5000-8000-100000000002")
ID_C = UUID("00000000-0000-5000-8000-100000000003")
ID_D = UUID("00000000-0000-5000-8000-100000000004")


def bar(instrument_id, ticker, close, volume, session, instrument_type=InstrumentType.COMMON_STOCK, name=None, exchange="XNYS"):
    close_d = Decimal(str(close))
    return EodMarketBarReadModel(
        instrument_id=instrument_id,
        ticker=ticker,
        name=name or f"{ticker} Test",
        instrument_type=instrument_type,
        primary_exchange=exchange,
        session_date=session,
        open=close_d,
        high=close_d,
        low=close_d,
        close=close_d,
        volume=Decimal(str(volume)),
        vwap=None,
        trade_count=None,
        currency="USD",
        source="test_provider",
        quality_status=QualityStatus.VALID,
        quality_flags=(),
    )


class FakeRepo(EodReadRepository):
    def __init__(self, sessions):
        self.sessions = sessions

    def list_sessions(self):
        return tuple(
            EodSessionDescriptor("1.0", session, len(rows), "completed", session, CREATED, 0)
            for session, rows in sorted(self.sessions.items())
        )

    def read_bars(self, session_date):
        try:
            return self.sessions[session_date]
        except KeyError as exc:
            raise EodSessionNotFoundError("missing") from exc


def analytics(rows_current=None, rows_previous=None):
    current = rows_current or (
        bar(ID_A, "TESTA", "110", "100000", CURRENT),
        bar(ID_B, "TESTB", "90", "100000", CURRENT, InstrumentType.ETF),
        bar(ID_C, "TESTC", "100", "100", CURRENT),
        bar(ID_D, "TESTD", "50", "1000", CURRENT),
    )
    previous = rows_previous or (
        bar(ID_A, "OLDTA", "100", "100000", PREVIOUS),
        bar(ID_B, "TESTB", "100", "100000", PREVIOUS, InstrumentType.ETF),
        bar(ID_C, "TESTC", "100", "100", PREVIOUS),
    )
    return EodReturnAnalyticsService(EodMarketDataQueryService(FakeRepo({PREVIOUS: previous, CURRENT: current})))


def test_join_by_instrument_id_survives_ticker_change():
    rows = analytics().compute_returns(current_session_date=CURRENT, previous_session_date=PREVIOUS)
    testa = next(row for row in rows if row.instrument_id == ID_A)
    assert testa.ticker == "TESTA"
    assert testa.close_to_close_return == Decimal("0.1")


def test_previous_missing_and_current_missing_counts():
    summary = analytics().get_latest_summary()
    assert summary.comparable_instrument_count == 3
    assert summary.current_only_count == 1
    assert summary.previous_only_count == 0


def test_positive_negative_unchanged_breadth_and_ratios():
    summary = analytics().get_latest_summary()
    assert summary.advancer_count == 1
    assert summary.decliner_count == 1
    assert summary.unchanged_count == 1
    assert summary.advance_decline_ratio == Decimal("1")
    assert summary.advance_decline_net == 0
    assert summary.positive_return_share == Decimal("0.3333333333333333333333333333")
    assert summary.negative_return_share == Decimal("0.3333333333333333333333333333")


def test_equal_weight_and_median_decimal_exact():
    summary = analytics().get_latest_summary()
    assert summary.equal_weight_return == Decimal("0")
    assert summary.median_return == Decimal("0")


def test_median_even_count_decimal_safe():
    svc = analytics(
        rows_current=(bar(ID_A, "A", "110", 1, CURRENT), bar(ID_B, "B", "120", 1, CURRENT)),
        rows_previous=(bar(ID_A, "A", "100", 1, PREVIOUS), bar(ID_B, "B", "100", 1, PREVIOUS)),
    )
    assert svc.get_latest_summary().median_return == Decimal("0.15")


def test_zero_decliner_ratio_is_none():
    svc = analytics(rows_current=(bar(ID_A, "A", "110", 1, CURRENT),), rows_previous=(bar(ID_A, "A", "100", 1, PREVIOUS),))
    summary = svc.get_latest_summary()
    assert summary.advance_decline_ratio is None
    assert summary.up_down_volume_ratio is None


def test_previous_close_zero_rejected():
    svc = analytics(rows_current=(bar(ID_A, "A", "10", 1, CURRENT),), rows_previous=(bar(ID_A, "A", "0", 1, PREVIOUS),))
    with pytest.raises(EodQueryValidationError):
        svc.get_latest_summary()


def test_dollar_volume_proxy_and_label_flags():
    row = analytics().compute_returns(current_session_date=CURRENT, previous_session_date=PREVIOUS)[0]
    assert row.current_dollar_volume_proxy == row.current_close * row.current_volume
    assert "close_times_volume_proxy" in row.quality_flags


def test_movers_threshold_and_ordering():
    movers = analytics().get_latest_movers(per_side=10, threshold=Decimal("5000000"))
    assert [row.ticker for row in movers.top_gainers] == ["TESTA"]
    assert [row.ticker for row in movers.top_losers] == ["TESTB"]


def test_liquidity_map_metadata_and_top_n():
    liquidity = analytics().get_latest_liquidity_map(limit=2, threshold=Decimal("0"))
    assert liquidity.map_type == "liquidity"
    assert liquidity.size_metric == "close_times_volume_proxy"
    assert liquidity.color_metric == "close_to_close_return"
    assert liquidity.is_market_cap_weighted is False
    assert liquidity.is_sector_grouped is False
    assert len(liquidity.nodes) == 2
    assert [node.rank for node in liquidity.nodes] == [1, 2]


def test_returns_page_filters_and_limit():
    items, total, current, previous = analytics().get_latest_returns_page(limit=1, offset=0, instrument_type=InstrumentType.ETF)
    assert total == 1
    assert items[0].ticker == "TESTB"
    assert current == CURRENT
    assert previous == PREVIOUS
    with pytest.raises(EodQueryValidationError):
        analytics().get_latest_returns_page(limit=201)
