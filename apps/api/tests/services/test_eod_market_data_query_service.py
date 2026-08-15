from __future__ import annotations

from pathlib import Path

import pytest

from tip_api.contracts.market_data.v1 import InstrumentType
from tip_api.persistence.eod_read import EodSessionNotFoundError
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.eod_market_data import EodMarketDataQueryService, EodQueryValidationError
from tests.support.eod_read_dataset import SESSION_DATE, publish_completed_eod_dataset


def service(tmp_path: Path) -> EodMarketDataQueryService:
    publish_completed_eod_dataset(tmp_path)
    return EodMarketDataQueryService(CanonicalEodReadRepository(tmp_path))


def test_latest_session_and_summary(tmp_path: Path) -> None:
    svc = service(tmp_path)
    latest = svc.get_latest_session()
    assert latest.session_date == SESSION_DATE

    summary = svc.get_session_summary(SESSION_DATE)
    assert summary.total_records == 3
    assert summary.common_stock_count == 2
    assert summary.etf_count == 1
    assert summary.other_supported_count == 0
    assert summary.missing_vwap_count == 1
    assert summary.missing_trade_count_count == 1
    assert summary.zero_volume_count == 1
    assert summary.quality_warning_count == 2
    assert not hasattr(summary, "daily_return")
    assert not hasattr(summary, "breadth")


def test_get_bars_page_default_pagination_and_order(tmp_path: Path) -> None:
    page = service(tmp_path).get_bars_page(session_date=SESSION_DATE)
    assert page.limit == 100
    assert page.offset == 0
    assert page.total_count == 3
    assert [item.ticker for item in page.items] == ["TESTA", "TESTB", "TESTC"]


def test_get_bars_page_limit_offset_and_empty_page(tmp_path: Path) -> None:
    svc = service(tmp_path)
    assert [item.ticker for item in svc.get_bars_page(session_date=SESSION_DATE, limit=1, offset=1).items] == ["TESTB"]
    assert svc.get_bars_page(session_date=SESSION_DATE, limit=1, offset=9).items == ()


@pytest.mark.parametrize("limit", [0, 201])
def test_limit_bounds(limit: int, tmp_path: Path) -> None:
    with pytest.raises(EodQueryValidationError):
        service(tmp_path).get_bars_page(session_date=SESSION_DATE, limit=limit)


def test_negative_offset_rejected(tmp_path: Path) -> None:
    with pytest.raises(EodQueryValidationError):
        service(tmp_path).get_bars_page(session_date=SESSION_DATE, offset=-1)


def test_ticker_filter_normalizes(tmp_path: Path) -> None:
    page = service(tmp_path).get_bars_page(session_date=SESSION_DATE, ticker=" testa ")
    assert page.total_count == 1
    assert page.items[0].ticker == "TESTA"


def test_invalid_ticker_filter_rejected(tmp_path: Path) -> None:
    with pytest.raises(EodQueryValidationError):
        service(tmp_path).get_bars_page(session_date=SESSION_DATE, ticker="bad/ticker")


def test_instrument_type_filter(tmp_path: Path) -> None:
    page = service(tmp_path).get_bars_page(session_date=SESSION_DATE, instrument_type=InstrumentType.ETF)
    assert page.total_count == 1
    assert page.items[0].ticker == "TESTB"


def test_unknown_session_propagates_not_found(tmp_path: Path) -> None:
    svc = service(tmp_path)
    with pytest.raises(EodSessionNotFoundError):
        svc.get_session_summary(SESSION_DATE.replace(day=12))
