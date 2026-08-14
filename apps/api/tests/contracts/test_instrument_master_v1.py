from __future__ import annotations

from datetime import UTC, date, datetime, timezone, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1 import (
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    QualityStatus,
)

INSTRUMENT_ID = UUID(int=1)
ISSUER_ID = UUID(int=2)
OTHER_INSTRUMENT_ID = UUID(int=3)


def instrument_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "issuer_id": None,
        "instrument_type": InstrumentType.COMMON_STOCK,
        "status": InstrumentStatus.ACTIVE,
        "ticker": "aapl",
        "name": " Apple Inc. ",
        "primary_exchange": " nasdaq ",
        "listing_country": "us",
        "currency": "usd",
        "figi": None,
        "cik": None,
        "valid_from": date(1980, 12, 12),
        "valid_to": None,
        "first_trade_date": date(1980, 12, 12),
        "last_trade_date": None,
        "as_of_date": date(2026, 8, 13),
        "source": " test-source ",
        "source_instrument_id": " provider-1 ",
        "ingested_at": datetime(2026, 8, 13, 9, 30, tzinfo=UTC),
        "quality_status": QualityStatus.VALID,
        "quality_notes": None,
    }
    payload.update(overrides)
    return payload


def test_minimal_valid_common_stock() -> None:
    instrument = InstrumentMasterV1(**instrument_payload())

    assert instrument.instrument_id == INSTRUMENT_ID
    assert instrument.instrument_type is InstrumentType.COMMON_STOCK
    assert instrument.status is InstrumentStatus.ACTIVE
    assert instrument.ticker == "AAPL"
    assert instrument.name == "Apple Inc."
    assert instrument.primary_exchange == "NASDAQ"
    assert instrument.listing_country == "US"
    assert instrument.currency == "USD"
    assert instrument.source == "test-source"
    assert instrument.source_instrument_id == "provider-1"
    assert instrument.schema_version == "1.0"


def test_full_record_preserves_optional_identity_fields() -> None:
    instrument = InstrumentMasterV1(
        **instrument_payload(
            issuer_id=ISSUER_ID,
            figi=" bbG000B9XRY4 ",
            cik="0000320193",
            quality_notes=" reviewed ",
        )
    )

    assert instrument.issuer_id == ISSUER_ID
    assert instrument.figi == "BBG000B9XRY4"
    assert instrument.cik == "0000320193"
    assert instrument.quality_notes == "reviewed"


def test_etf_type_is_supported() -> None:
    instrument = InstrumentMasterV1(
        **instrument_payload(
            instrument_type=InstrumentType.ETF,
            ticker="spy",
            name="SPDR S&P 500 ETF Trust",
        )
    )

    assert instrument.instrument_type is InstrumentType.ETF
    assert instrument.ticker == "SPY"


@pytest.mark.parametrize("ticker", ["brk.b", "brk-b", "abc123"])
def test_common_us_ticker_forms_are_accepted(ticker: str) -> None:
    instrument = InstrumentMasterV1(**instrument_payload(ticker=ticker))

    assert instrument.ticker == ticker.upper()


def test_cik_leading_zeroes_are_preserved() -> None:
    instrument = InstrumentMasterV1(**instrument_payload(cik="0000012345"))

    assert instrument.cik == "0000012345"


def test_timezone_offset_is_normalized_to_utc() -> None:
    offset_dt = datetime(2026, 8, 13, 5, 30, tzinfo=timezone(timedelta(hours=-4)))

    instrument = InstrumentMasterV1(**instrument_payload(ingested_at=offset_dt))

    assert instrument.ingested_at == datetime(2026, 8, 13, 9, 30, tzinfo=UTC)
    assert instrument.ingested_at.tzinfo is UTC


def test_naive_ingested_at_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(**instrument_payload(ingested_at=datetime(2026, 8, 13, 9, 30)))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ticker", "   "),
        ("name", "   "),
        ("source", "   "),
        ("source_instrument_id", "   "),
    ],
)
def test_required_strings_reject_empty_values(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(**instrument_payload(**{field: value}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("currency", "US"),
        ("currency", "US1"),
        ("listing_country", "USA"),
        ("listing_country", "U1"),
    ],
)
def test_invalid_currency_and_listing_country_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(**instrument_payload(**{field: value}))


def test_valid_to_before_valid_from_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(
            **instrument_payload(valid_from=date(2026, 1, 2), valid_to=date(2026, 1, 1))
        )


def test_last_trade_date_before_first_trade_date_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(
            **instrument_payload(
                first_trade_date=date(2026, 1, 2),
                last_trade_date=date(2026, 1, 1),
            )
        )


def test_as_of_date_before_valid_from_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(
            **instrument_payload(valid_from=date(2026, 1, 2), as_of_date=date(2026, 1, 1))
        )


def test_extra_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(**instrument_payload(sector="Technology"))


def test_frozen_model_rejects_mutation() -> None:
    instrument = InstrumentMasterV1(**instrument_payload())

    with pytest.raises(ValidationError):
        instrument.ticker = "MSFT"  # type: ignore[misc]


def test_json_serialization_is_stable() -> None:
    instrument = InstrumentMasterV1(**instrument_payload())

    serialized = instrument.model_dump_json()

    assert f'"instrument_id":"{INSTRUMENT_ID}"' in serialized
    assert '"ingested_at":"2026-08-13T09:30:00Z"' in serialized
    assert '"schema_version":"1.0"' in serialized


def test_ticker_does_not_drive_instrument_id() -> None:
    first = InstrumentMasterV1(**instrument_payload(ticker="ABC", instrument_id=INSTRUMENT_ID))
    second = InstrumentMasterV1(**instrument_payload(ticker="ABC", instrument_id=OTHER_INSTRUMENT_ID))

    assert first.ticker == second.ticker == "ABC"
    assert first.instrument_id != second.instrument_id


def test_datetime_is_not_accepted_for_date_fields() -> None:
    with pytest.raises(ValidationError):
        InstrumentMasterV1(
            **instrument_payload(valid_from=datetime(2026, 1, 1, 0, 0, tzinfo=UTC))
        )
