from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import (
    EodPriceBarV1,
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    QualityStatus,
)
from tip_api.providers.market_data import (
    EodBarQuery,
    InstrumentQuery,
    ProviderCapability,
    ProviderDataError,
    RevisionSelection,
    UnsupportedCapabilityError,
)
from tests.providers.support.in_memory_market_data_provider import InMemoryMarketDataProvider

ID1 = UUID(int=1)
ID2 = UUID(int=2)
ID3 = UUID(int=3)


def instrument_record(
    *,
    instrument_id: UUID = ID1,
    ticker: str = "AAA",
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    status: InstrumentStatus = InstrumentStatus.ACTIVE,
) -> InstrumentMasterV1:
    return InstrumentMasterV1(
        instrument_id=instrument_id,
        issuer_id=None,
        instrument_type=InstrumentType.COMMON_STOCK,
        status=status,
        ticker=ticker,
        name=f"{ticker} Company",
        primary_exchange="XNYS",
        listing_country="US",
        currency="USD",
        figi=None,
        cik=None,
        valid_from=valid_from,
        valid_to=valid_to,
        first_trade_date=valid_from,
        last_trade_date=None,
        as_of_date=max(valid_from, date(2026, 8, 13)),
        source="test_source",
        source_instrument_id=f"source-{instrument_id.int}",
        ingested_at=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
        quality_status=QualityStatus.VALID,
        quality_notes=None,
    )


def eod_bar(
    *,
    instrument_id: UUID = ID1,
    session_date: date = date(2026, 8, 13),
    source: str = "source_a",
    revision: int = 1,
    is_latest_revision: bool = True,
    close: Decimal = Decimal("101"),
    notional: Decimal = Decimal("1000"),
    adjusted_close: Decimal = Decimal("101"),
) -> EodPriceBarV1:
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=session_date,
        open=Decimal("100"),
        high=max(Decimal("102"), close),
        low=Decimal("99"),
        close=close,
        volume=10,
        vwap=None,
        trade_count=None,
        notional=notional,
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=adjusted_close,
        source=source,
        source_record_id=None,
        ingested_at=datetime(2026, 8, 13, 22, 0, tzinfo=UTC),
        revision=revision,
        is_latest_revision=is_latest_revision,
        quality_status=QualityStatus.VALID,
        quality_flags=(),
    )


def provider_with_instruments(*records: InstrumentMasterV1, capabilities: frozenset[ProviderCapability] | None = None) -> InMemoryMarketDataProvider:
    return InMemoryMarketDataProvider(
        provider_id="test_provider",
        capabilities=frozenset({ProviderCapability.INSTRUMENT_MASTER}) if capabilities is None else capabilities,
        instruments=tuple(records),
    )


def provider_with_bars(*records: EodPriceBarV1, capabilities: frozenset[ProviderCapability] | None = None) -> InMemoryMarketDataProvider:
    return InMemoryMarketDataProvider(
        provider_id="test_provider",
        capabilities=frozenset({ProviderCapability.EOD_PRICE_BARS}) if capabilities is None else capabilities,
        eod_bars=tuple(records),
    )


def test_provider_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError):
        InMemoryMarketDataProvider(provider_id="   ", capabilities=frozenset())


def test_instrument_capability_required() -> None:
    provider = provider_with_instruments(capabilities=frozenset())

    with pytest.raises(UnsupportedCapabilityError):
        provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))


def test_instrument_as_of_filtering_and_inclusive_boundaries() -> None:
    valid_from = instrument_record(instrument_id=ID1, ticker="BBB", valid_from=date(2026, 8, 13), valid_to=date(2026, 8, 20))
    valid_to = instrument_record(instrument_id=ID2, ticker="AAA", valid_from=date(2026, 1, 1), valid_to=date(2026, 8, 13))
    before = instrument_record(instrument_id=ID3, ticker="CCC", valid_from=date(2026, 8, 14))
    provider = provider_with_instruments(valid_from, valid_to, before)

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))

    assert result == (valid_from, valid_to)


def test_instrument_after_valid_to_is_excluded() -> None:
    expired = instrument_record(valid_from=date(2026, 1, 1), valid_to=date(2026, 8, 12))
    provider = provider_with_instruments(expired)

    assert provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13))) == ()


def test_instrument_id_filtering() -> None:
    first = instrument_record(instrument_id=ID1)
    second = instrument_record(instrument_id=ID2)
    provider = provider_with_instruments(first, second)

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13), instrument_ids=(ID2,)))

    assert result == (second,)


def test_active_only_behavior_and_inactive_included_when_false() -> None:
    active = instrument_record(instrument_id=ID1, status=InstrumentStatus.ACTIVE)
    inactive = instrument_record(instrument_id=ID2, status=InstrumentStatus.INACTIVE)
    provider = provider_with_instruments(active, inactive)

    all_result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))
    active_result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13), active_only=True))

    assert all_result == (active, inactive)
    assert active_result == (active,)


def test_instrument_empty_result_is_tuple() -> None:
    provider = provider_with_instruments()

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))

    assert result == ()
    assert isinstance(result, tuple)


def test_instrument_results_sort_by_uuid_not_ticker() -> None:
    high_ticker_low_id = instrument_record(instrument_id=ID1, ticker="ZZZ")
    low_ticker_high_id = instrument_record(instrument_id=ID2, ticker="AAA")
    provider = provider_with_instruments(low_ticker_high_id, high_ticker_low_id)

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))

    assert result == (high_ticker_low_id, low_ticker_high_id)


def test_historical_non_overlapping_versions_are_allowed() -> None:
    old = instrument_record(instrument_id=ID1, ticker="OLD", valid_from=date(2020, 1, 1), valid_to=date(2025, 12, 31))
    new = instrument_record(instrument_id=ID1, ticker="NEW", valid_from=date(2026, 1, 1), valid_to=None)
    provider = provider_with_instruments(old, new)

    assert provider.get_instruments(InstrumentQuery(as_of_date=date(2025, 6, 1))) == (old,)
    assert provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13))) == (new,)


def test_overlapping_effective_instrument_versions_raise_data_error() -> None:
    first = instrument_record(instrument_id=ID1, ticker="ONE", valid_from=date(2026, 1, 1), valid_to=None)
    second = instrument_record(instrument_id=ID1, ticker="TWO", valid_from=date(2026, 6, 1), valid_to=None)
    provider = provider_with_instruments(first, second)

    with pytest.raises(ProviderDataError):
        provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))


def test_instrument_input_records_unchanged_and_result_tuple_immutable() -> None:
    records = (instrument_record(instrument_id=ID1),)
    provider = provider_with_instruments(*records)

    result = provider.get_instruments(InstrumentQuery(as_of_date=date(2026, 8, 13)))

    assert records == (instrument_record(instrument_id=ID1),)
    assert isinstance(result, tuple)
    with pytest.raises(AttributeError):
        result.append(records[0])  # type: ignore[attr-defined]


def test_eod_capability_required() -> None:
    provider = provider_with_bars(capabilities=frozenset())

    with pytest.raises(UnsupportedCapabilityError):
        provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))


def test_eod_filters_instruments_and_inclusive_date_range() -> None:
    start = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 12))
    middle = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 13))
    end = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 14))
    outside_date = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 15))
    outside_id = eod_bar(instrument_id=ID2, session_date=date(2026, 8, 13))
    provider = provider_with_bars(outside_date, end, outside_id, middle, start)

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 12), end_date=date(2026, 8, 14)))

    assert result == (start, middle, end)


def test_latest_mode_returns_latest_only_and_all_mode_returns_all_revisions() -> None:
    old = eod_bar(revision=1, is_latest_revision=False, close=Decimal("100"))
    latest = eod_bar(revision=2, is_latest_revision=True, close=Decimal("101"))
    provider = provider_with_bars(latest, old)
    query_base = {"instrument_ids": (ID1,), "start_date": date(2026, 8, 13), "end_date": date(2026, 8, 13)}

    latest_result = provider.get_eod_bars(EodBarQuery(**query_base))
    all_result = provider.get_eod_bars(EodBarQuery(**query_base, revision_selection=RevisionSelection.ALL))

    assert latest_result == (latest,)
    assert all_result == (old, latest)


def test_multiple_latest_records_raise_data_error() -> None:
    first = eod_bar(revision=1, is_latest_revision=True)
    second = eod_bar(revision=2, is_latest_revision=True)
    provider = provider_with_bars(first, second)

    with pytest.raises(ProviderDataError):
        provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))


def test_no_latest_record_raises_in_latest_mode_but_all_mode_returns_records() -> None:
    old = eod_bar(revision=1, is_latest_revision=False)
    provider = provider_with_bars(old)
    base = {"instrument_ids": (ID1,), "start_date": date(2026, 8, 13), "end_date": date(2026, 8, 13)}

    with pytest.raises(ProviderDataError):
        provider.get_eod_bars(EodBarQuery(**base))
    assert provider.get_eod_bars(EodBarQuery(**base, revision_selection=RevisionSelection.ALL)) == (old,)


def test_duplicate_business_key_raises_data_error() -> None:
    first = eod_bar(revision=1, is_latest_revision=True)
    duplicate = eod_bar(revision=1, is_latest_revision=True)
    provider = provider_with_bars(first, duplicate)

    with pytest.raises(ProviderDataError):
        provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))


def test_same_session_source_different_revisions_allowed_when_consistent() -> None:
    first = eod_bar(revision=1, is_latest_revision=False)
    second = eod_bar(revision=2, is_latest_revision=True)
    provider = provider_with_bars(second, first)

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13), revision_selection=RevisionSelection.ALL))

    assert result == (first, second)


def test_different_sources_remain_separate() -> None:
    source_b = eod_bar(source="source_b", revision=1, close=Decimal("102"))
    source_a = eod_bar(source="source_a", revision=1, close=Decimal("101"))
    provider = provider_with_bars(source_b, source_a)

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))

    assert result == (source_a, source_b)


def test_eod_deterministic_sort_order() -> None:
    later_source = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 14), source="source_b", revision=2, close=Decimal("104"))
    earlier_source = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 14), source="source_a", revision=1, close=Decimal("103"))
    first_id = eod_bar(instrument_id=ID1, session_date=date(2026, 8, 13), source="source_a", revision=1, close=Decimal("102"))
    second_id = eod_bar(instrument_id=ID2, session_date=date(2026, 8, 13), source="source_a", revision=1, close=Decimal("101"))
    provider = provider_with_bars(second_id, later_source, first_id, earlier_source)

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID2, ID1), start_date=date(2026, 8, 13), end_date=date(2026, 8, 14)))

    assert result == (first_id, earlier_source, later_source, second_id)


def test_eod_empty_result_is_tuple() -> None:
    provider = provider_with_bars()

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))

    assert result == ()
    assert isinstance(result, tuple)


def test_query_range_isolation_for_unrelated_invalid_records() -> None:
    valid = eod_bar(session_date=date(2026, 8, 13), revision=1, is_latest_revision=True)
    invalid_outside_range_a = eod_bar(session_date=date(2026, 8, 10), revision=1, is_latest_revision=True)
    invalid_outside_range_b = eod_bar(session_date=date(2026, 8, 10), revision=2, is_latest_revision=True)
    provider = provider_with_bars(valid, invalid_outside_range_a, invalid_outside_range_b)

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))

    assert result == (valid,)


def test_eod_input_records_unchanged_and_result_tuple_immutable() -> None:
    record = eod_bar(notional=Decimal("1.23"), adjusted_close=Decimal("88.88"))
    records = (record,)
    provider = provider_with_bars(*records)

    result = provider.get_eod_bars(EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13)))

    assert records == (record,)
    assert result == (record,)
    assert result[0].notional == Decimal("1.23")
    assert result[0].adjusted_close == Decimal("88.88")
    with pytest.raises(AttributeError):
        result.append(record)  # type: ignore[attr-defined]
