from __future__ import annotations

import socket
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import InstrumentStatus, InstrumentType, QualityStatus
from tip_api.providers.market_data import (
    EodBarQuery,
    InstrumentQuery,
    MarketDataProvider,
    ProviderAuthenticationError,
    ProviderCapability,
    ProviderDataError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    RevisionSelection,
    UnsupportedCapabilityError,
)
from tip_api.providers.massive import MassiveMarketDataProvider, MassiveProviderConfig, stable_massive_instrument_id
from tip_api.providers.massive.transport import (
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)
from tests.providers.support.massive_fake_transport import FakeMassiveTransport, route

SENTINEL_SECRET = "test-secret-must-never-appear"
NOW = datetime(2026, 8, 14, 22, 0, tzinfo=UTC)
AS_OF = date(2026, 8, 14)
AAA_ID = stable_massive_instrument_id("ticker=AAA|composite_figi=BBG000AAA|share_class_figi=BBG001AAA|cik=0000000001")
BBB_ID = stable_massive_instrument_id("ticker=BBB|composite_figi=|share_class_figi=|cik=")


def config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SENTINEL_SECRET)


def provider(
    responses: dict[tuple[str, tuple[tuple[str, object], ...]], dict[str, object]],
    *,
    instrument_tickers: dict[UUID, str] | None = None,
    strategy: str = "grouped_daily",
    max_pages: int = 20,
) -> tuple[MassiveMarketDataProvider, FakeMassiveTransport]:
    transport = FakeMassiveTransport(responses)  # type: ignore[arg-type]
    adapter = MassiveMarketDataProvider(
        config=config(),
        transport=transport,
        instrument_tickers=instrument_tickers,
        eod_bar_strategy=strategy,  # type: ignore[arg-type]
        clock=lambda: NOW,
        max_pages=max_pages,
    )
    return adapter, transport


def ticker_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ticker": "aaa",
        "name": "AAA Corp",
        "market": "stocks",
        "locale": "us",
        "primary_exchange": "xnys",
        "currency_symbol": "usd",
        "type": "CS",
        "active": True,
        "composite_figi": "bbg000aaa",
        "share_class_figi": "bbg001aaa",
        "cik": "0000000001",
    }
    payload.update(overrides)
    return payload


def grouped_bar(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "T": "AAA",
        "o": 10.10,
        "h": 11.25,
        "l": 9.95,
        "c": 10.75,
        "v": 12345,
        "vw": 10.55,
        "n": 321,
        "t": 1786665600000,
    }
    payload.update(overrides)
    return payload


def custom_bar(**overrides: object) -> dict[str, object]:
    payload = grouped_bar(**overrides)
    payload.pop("T", None)
    return payload


def test_adapter_satisfies_market_data_provider_protocol() -> None:
    adapter, _ = provider({})

    assert isinstance(adapter, MarketDataProvider)
    assert adapter.provider_id == "massive_stocks_basic"
    assert adapter.capabilities == frozenset({ProviderCapability.INSTRUMENT_MASTER, ProviderCapability.EOD_PRICE_BARS})



def test_unsupported_capability_uses_provider_exception() -> None:
    class InstrumentOnlyMassiveProvider(MassiveMarketDataProvider):
        _capabilities = frozenset({ProviderCapability.INSTRUMENT_MASTER})

    adapter = InstrumentOnlyMassiveProvider(
        config=config(),
        transport=FakeMassiveTransport({}),
        instrument_tickers={AAA_ID: "AAA"},
        clock=lambda: NOW,
    )

    with pytest.raises(UnsupportedCapabilityError) as exc_info:
        adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))

    assert exc_info.value.capability is ProviderCapability.EOD_PRICE_BARS
    assert SENTINEL_SECRET not in str(exc_info.value)

def test_all_tickers_mapping_success_and_secret_not_recorded() -> None:
    adapter, transport = provider(
        {
            route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {
                "results": [ticker_payload()],
                "request_id": "req-reference",
            }
        }
    )

    results = adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))

    assert len(results) == 1
    record = results[0]
    assert record.instrument_id == AAA_ID
    assert record.ticker == "AAA"
    assert record.name == "AAA Corp"
    assert record.primary_exchange == "XNYS"
    assert record.listing_country == "US"
    assert record.currency == "USD"
    assert record.figi == "BBG000AAA"
    assert record.cik == "0000000001"
    assert record.instrument_type is InstrumentType.COMMON_STOCK
    assert record.status is InstrumentStatus.ACTIVE
    assert record.source == "massive_stocks_basic"
    assert record.source_instrument_id != record.ticker
    assert record.ingested_at == NOW
    assert transport.calls[0].credential_supplied is True
    assert SENTINEL_SECRET not in repr(transport.calls)
    assert all(key.lower() != "apikey" for key, _ in transport.calls[0].params)


def test_ticker_normalization_stable_uuid_reproducibility_and_extra_fields_do_not_leak() -> None:
    adapter, _ = provider(
        {
            route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {
                "results": [ticker_payload(ticker=" brk.b ", composite_figi="bbg000aaa", share_class_figi="bbg001aaa", ignored="x")]
            }
        }
    )

    record = adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))[0]

    assert record.ticker == "BRK.B"
    assert record.instrument_id == stable_massive_instrument_id("ticker=BRK.B|composite_figi=BBG000AAA|share_class_figi=BBG001AAA|cik=0000000001")
    assert "ignored" not in record.model_fields_set


def test_missing_optional_reference_fields_are_none_and_etf_maps() -> None:
    adapter, _ = provider(
        {
            route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {
                "results": [ticker_payload(ticker="bbb", type="ETF", composite_figi=None, share_class_figi=None, cik=None)]
            }
        }
    )

    record = adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))[0]

    assert record.instrument_id == BBB_ID
    assert record.instrument_type is InstrumentType.ETF
    assert record.figi is None
    assert record.cik is None


def test_malformed_required_reference_field_raises_data_error() -> None:
    adapter, _ = provider(
        {route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {"results": [ticker_payload(name=" ")]}}
    )

    with pytest.raises(ProviderDataError, match="required field"):
        adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))


def test_unsupported_instrument_type_is_skipped() -> None:
    adapter, _ = provider(
        {route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {"results": [ticker_payload(type="WARRANT")]}}
    )

    assert adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF)) == ()


def test_active_only_filters_inactive_records() -> None:
    adapter, _ = provider(
        {
            route("/v3/reference/tickers", {"active": True, "date": AS_OF.isoformat(), "limit": 1000}): {
                "results": [ticker_payload(active=False)]
            }
        }
    )

    assert adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF, active_only=True)) == ()


def test_grouped_daily_mapping_success_uses_adjusted_false() -> None:
    adapter, transport = provider(
        {
            route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {
                "request_id": "req-grouped",
                "results": [grouped_bar()],
            }
        },
        instrument_tickers={AAA_ID: "AAA"},
    )

    records = adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))

    assert len(records) == 1
    bar = records[0]
    assert bar.instrument_id == AAA_ID
    assert bar.session_date == AS_OF
    assert bar.open == Decimal("10.1")
    assert bar.high == Decimal("11.25")
    assert bar.low == Decimal("9.95")
    assert bar.close == Decimal("10.75")
    assert bar.volume == Decimal(12345)
    assert bar.vwap == Decimal("10.55")
    assert bar.trade_count == 321
    assert bar.notional == Decimal("0")
    assert bar.adjusted_close == Decimal("10.75")
    assert bar.split_adjustment_factor == Decimal("1")
    assert bar.dividend_adjustment_factor == Decimal("1")
    assert bar.total_return_adjustment_factor == Decimal("1")
    assert bar.quality_flags == ("adjustment_factors_unverified",)
    assert bar.is_latest_revision is True
    assert transport.calls[0].params == (("adjusted", False),)


def test_custom_bars_mapping_success() -> None:
    adapter, transport = provider(
        {
            route("/v2/aggs/ticker/AAA/range/1/day/2026-08-14/2026-08-14", {"adjusted": False, "limit": 50000, "sort": "asc"}): {
                "results": [custom_bar()]
            }
        },
        instrument_tickers={AAA_ID: "aaa"},
        strategy="custom_bars",
    )

    records = adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))

    assert len(records) == 1
    assert records[0].instrument_id == AAA_ID
    assert transport.calls[0].path == "/v2/aggs/ticker/AAA/range/1/day/2026-08-14/2026-08-14"
    assert ("adjusted", False) in transport.calls[0].params


def test_malformed_ohlc_and_missing_required_ohlc_raise_data_error() -> None:
    adapter_bad_ohlc, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar(h=9.0)]}},
        instrument_tickers={AAA_ID: "AAA"},
    )
    with pytest.raises(ProviderDataError, match="canonical validation"):
        adapter_bad_ohlc.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))

    adapter_missing, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar(o=None)]}},
        instrument_tickers={AAA_ID: "AAA"},
    )
    with pytest.raises(ProviderDataError, match="decimal field"):
        adapter_missing.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))


def test_grouped_daily_fractional_volume_maps_to_decimal() -> None:
    adapter, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar(v=12345.5)]}},
        instrument_tickers={AAA_ID: "AAA"},
    )

    bar = adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))[0]

    assert bar.volume == Decimal("12345.5")


def test_custom_bars_fractional_volume_maps_to_decimal() -> None:
    adapter, _ = provider(
        {route("/v2/aggs/ticker/AAA/range/1/day/2026-08-14/2026-08-14", {"adjusted": False, "limit": 50000, "sort": "asc"}): {"results": [custom_bar(v=Decimal("456.125"))]}},
        instrument_tickers={AAA_ID: "AAA"},
        strategy="custom_bars",
    )

    bar = adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))[0]

    assert bar.volume == Decimal("456.125")


def test_malformed_volume_raises_data_error() -> None:
    adapter, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar(v=True)]}},
        instrument_tickers={AAA_ID: "AAA"},
    )

    with pytest.raises(ProviderDataError, match="decimal field"):
        adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))


def test_fractional_trade_count_is_rejected() -> None:
    adapter, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar(n=10.5)]}},
        instrument_tickers={AAA_ID: "AAA"},
    )

    with pytest.raises(ProviderDataError, match="integer field"):
        adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))


def test_null_optional_bar_values_remain_none_and_utc_ingested_at() -> None:
    adapter, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar(vw=None, n=None)]}},
        instrument_tickers={AAA_ID: "AAA"},
    )

    bar = adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))[0]

    assert bar.vwap is None
    assert bar.trade_count is None
    assert bar.ingested_at == NOW


def test_unresolved_ticker_raises_data_error() -> None:
    adapter, _ = provider({}, instrument_tickers={})

    with pytest.raises(ProviderDataError, match="cannot resolve"):
        adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))


def test_latest_and_all_revision_modes_return_same_single_revision_records() -> None:
    adapter, _ = provider(
        {route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {"results": [grouped_bar()]}},
        instrument_tickers={AAA_ID: "AAA"},
    )

    latest = adapter.get_eod_bars(EodBarQuery(instrument_ids=(AAA_ID,), start_date=AS_OF, end_date=AS_OF))
    all_revisions = adapter.get_eod_bars(
        EodBarQuery(
            instrument_ids=(AAA_ID,),
            start_date=AS_OF,
            end_date=AS_OF,
            revision_selection=RevisionSelection.ALL,
        )
    )

    assert latest == all_revisions
    assert latest[0].revision == 1
    assert latest[0].is_latest_revision is True


def test_deterministic_ordering_for_instruments_and_bars() -> None:
    adapter, _ = provider(
        {
            route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {
                "results": [ticker_payload(ticker="bbb", type="ETF", composite_figi=None, share_class_figi=None, cik=None), ticker_payload()]
            },
            route("/v2/aggs/grouped/locale/us/market/stocks/2026-08-14", {"adjusted": False}): {
                "results": [grouped_bar(T="BBB", h=Decimal("21"), c=Decimal("20")), grouped_bar(T="AAA")]
            },
        },
        instrument_tickers={AAA_ID: "AAA", BBB_ID: "BBB"},
    )

    instruments = adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))
    bars = adapter.get_eod_bars(EodBarQuery(instrument_ids=(BBB_ID, AAA_ID), start_date=AS_OF, end_date=AS_OF))

    assert [record.instrument_id for record in instruments] == sorted([AAA_ID, BBB_ID], key=str)
    assert [record.instrument_id for record in bars] == sorted([AAA_ID, BBB_ID], key=str)


def test_authentication_rate_limit_and_unavailable_errors() -> None:
    class RaisingTransport:
        def __init__(self, exc: Exception) -> None:
            self.exc = exc

        def get_json(self, *args: object, **kwargs: object) -> dict[str, object]:
            raise self.exc

    query = InstrumentQuery(as_of_date=AS_OF)
    with pytest.raises(ProviderAuthenticationError) as auth_exc:
        MassiveMarketDataProvider(config=config(), transport=RaisingTransport(MassiveTransportResponseError(401, "bad auth"))).get_instruments(query)  # type: ignore[arg-type]
    assert SENTINEL_SECRET not in str(auth_exc.value)

    with pytest.raises(ProviderRateLimitError) as rate_exc:
        MassiveMarketDataProvider(config=config(), transport=RaisingTransport(MassiveTransportResponseError(429, "limited", retry_after_seconds=7))).get_instruments(query)  # type: ignore[arg-type]
    assert rate_exc.value.retry_after_seconds == 7
    assert SENTINEL_SECRET not in str(rate_exc.value)

    for exc in (MassiveTransportTimeoutError("timeout"), MassiveTransportUnavailableError("offline"), MassiveTransportResponseError(500, "server")):
        with pytest.raises(ProviderUnavailableError):
            MassiveMarketDataProvider(config=config(), transport=RaisingTransport(exc)).get_instruments(query)  # type: ignore[arg-type]


def test_malformed_provider_response_raises_data_error() -> None:
    adapter, _ = provider({route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {"results": {"bad": "shape"}}})

    with pytest.raises(ProviderDataError, match="results must be a list"):
        adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))


def test_pagination_strips_api_key_and_has_loop_protection() -> None:
    first = {"results": [], "next_url": "https://api.massive.com/v3/reference/tickers?cursor=abc&apiKey=SHOULD_NOT_RECORD"}
    second = {"results": [ticker_payload()]}
    adapter, transport = provider(
        {
            route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): first,
            route("/v3/reference/tickers", {"cursor": "abc"}): second,
        }
    )

    assert len(adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))) == 1
    assert transport.calls[1].params == (("cursor", "abc"),)
    assert SENTINEL_SECRET not in repr(transport.calls)

    looping_adapter, _ = provider(
        {route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): first},
        max_pages=1,
    )
    with pytest.raises(ProviderDataError, match="page limit"):
        looping_adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))


def test_no_network_access(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", fail_socket)
    adapter, _ = provider(
        {route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): {"results": [ticker_payload()]}}
    )

    assert adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))[0].ticker == "AAA"


def test_adapter_rejects_api_key_query_parameter() -> None:
    adapter, _ = provider({})

    with pytest.raises(ProviderDataError, match="query parameter"):
        adapter._request_json("/v3/reference/tickers", {"apiKey": "bad"})  # type: ignore[attr-defined]


def test_next_url_host_mismatch_is_rejected() -> None:
    first = {"results": [], "next_url": "https://example.test/v3/reference/tickers?cursor=abc"}
    adapter, _ = provider({route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): first})

    with pytest.raises(ProviderDataError, match="host"):
        adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))


def test_pagination_loop_is_rejected() -> None:
    looping = {"results": [], "next_url": "https://api.massive.com/v3/reference/tickers?date=2026-08-14&limit=1000"}
    adapter, _ = provider({
        route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": 1000}): looping,
        route("/v3/reference/tickers", {"date": AS_OF.isoformat(), "limit": "1000"}): looping,
    })

    with pytest.raises(ProviderDataError, match="loop"):
        adapter.get_instruments(InstrumentQuery(as_of_date=AS_OF))
