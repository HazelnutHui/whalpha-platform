from __future__ import annotations

import json
from datetime import UTC, date, datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1 import EodPriceBarV1, QualityStatus

INSTRUMENT_ID = UUID(int=4)



def bar_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "session_date": date(2026, 8, 13),
        "open": Decimal("100.10"),
        "high": Decimal("105.25"),
        "low": Decimal("99.95"),
        "close": Decimal("104.125"),
        "volume": 1234567,
        "vwap": Decimal("102.123456789123456789"),
        "trade_count": 12345,
        "notional": Decimal("126066665.55"),
        "currency": "usd",
        "split_adjustment_factor": Decimal("1"),
        "dividend_adjustment_factor": Decimal("1"),
        "total_return_adjustment_factor": Decimal("1"),
        "adjusted_close": Decimal("104.125"),
        "source": " test-source ",
        "source_record_id": " record-1 ",
        "ingested_at": datetime(2026, 8, 13, 21, 5, tzinfo=UTC),
        "revision": 1,
        "is_latest_revision": True,
        "quality_status": QualityStatus.VALID,
        "quality_flags": (" Provider Warning ", "provider-warning", "halt_review"),
    }
    payload.update(overrides)
    return payload


def test_complete_valid_bar() -> None:
    bar = EodPriceBarV1(**bar_payload())

    assert bar.instrument_id == INSTRUMENT_ID
    assert bar.session_date == date(2026, 8, 13)
    assert bar.open == Decimal("100.10")
    assert bar.currency == "USD"
    assert bar.source == "test-source"
    assert bar.source_record_id == "record-1"
    assert bar.revision == 1
    assert bar.schema_version == "1.0"


@pytest.mark.parametrize("field", ["vwap", "trade_count", "source_record_id"])
def test_nullable_fields_can_be_none(field: str) -> None:
    bar = EodPriceBarV1(**bar_payload(**{field: None}))

    assert getattr(bar, field) is None


def test_volume_zero_is_allowed() -> None:
    bar = EodPriceBarV1(**bar_payload(volume=0))

    assert bar.volume == Decimal(0)


def test_fractional_decimal_volume_is_allowed() -> None:
    bar = EodPriceBarV1(**bar_payload(volume=Decimal(1000.125)))

    assert bar.volume == Decimal(1000.125)


def test_revision_one_is_allowed() -> None:
    bar = EodPriceBarV1(**bar_payload(revision=1))

    assert bar.revision == 1


def test_revision_zero_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(revision=0))


def test_negative_volume_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(volume=-1))


def test_negative_trade_count_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(trade_count=-1))


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1")])
def test_zero_or_negative_ohlc_is_rejected(field: str, value: Decimal) -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(**{field: value}))


def test_high_below_open_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(high=Decimal("99")))


def test_high_below_close_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(high=Decimal("103")))


def test_low_above_open_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(low=Decimal("101")))


def test_low_above_close_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(low=Decimal("105")))


@pytest.mark.parametrize(
    "field",
    ["split_adjustment_factor", "dividend_adjustment_factor", "total_return_adjustment_factor"],
)
@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1")])
def test_zero_or_negative_adjustment_factor_is_rejected(field: str, value: Decimal) -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(**{field: value}))


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1")])
def test_zero_or_negative_adjusted_close_is_rejected(value: Decimal) -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(adjusted_close=value))


def test_negative_notional_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(notional=Decimal("-0.01")))


def test_invalid_currency_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(currency="US"))


def test_empty_source_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(source="   "))


def test_empty_source_record_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(source_record_id="   "))


def test_naive_ingested_at_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(ingested_at=datetime(2026, 8, 13, 21, 5)))


def test_timezone_offset_is_normalized_to_utc() -> None:
    offset_dt = datetime(2026, 8, 13, 17, 5, tzinfo=timezone(timedelta(hours=-4)))

    bar = EodPriceBarV1(**bar_payload(ingested_at=offset_dt))

    assert bar.ingested_at == datetime(2026, 8, 13, 21, 5, tzinfo=UTC)
    assert bar.ingested_at.tzinfo is UTC


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_non_finite_decimal_is_rejected(value: Decimal) -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(close=value))


@pytest.mark.parametrize("field", ["close", "volume"])
def test_float_decimal_input_is_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(**{field: 104.125}))


def test_bool_volume_input_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(volume=True))


def test_quality_flags_are_normalized_and_deduplicated() -> None:
    bar = EodPriceBarV1(
        **bar_payload(quality_flags=(" Provider Warning ", "provider-warning", "HALT REVIEW"))
    )

    assert bar.quality_flags == ("provider_warning", "halt_review")


def test_empty_quality_flag_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(quality_flags=("valid_flag", "   ")))


def test_single_string_quality_flags_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(quality_flags="provider_warning"))


def test_extra_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(ticker="AAPL"))


def test_frozen_model_rejects_mutation() -> None:
    bar = EodPriceBarV1(**bar_payload())

    with pytest.raises(ValidationError):
        bar.close = Decimal("1")  # type: ignore[misc]


def test_json_serialization_preserves_decimal_precision_and_utc() -> None:
    bar = EodPriceBarV1(**bar_payload(close=Decimal("104.123456789123456789")))

    payload = json.loads(bar.model_dump_json())

    assert payload["close"] == "104.123456789123456789"
    assert payload["ingested_at"] == "2026-08-13T21:05:00Z"
    assert payload["schema_version"] == "1.0"


def test_session_date_does_not_accept_datetime() -> None:
    with pytest.raises(ValidationError):
        EodPriceBarV1(**bar_payload(session_date=datetime(2026, 8, 13, 0, 0, tzinfo=UTC)))


def test_model_does_not_compute_notional_or_adjusted_close() -> None:
    bar = EodPriceBarV1(
        **bar_payload(
            close=Decimal("104.125"),
            volume=Decimal(10),
            notional=Decimal("1.23"),
            adjusted_close=Decimal("88.88"),
        )
    )

    assert bar.notional == Decimal("1.23")
    assert bar.adjusted_close == Decimal("88.88")


def test_model_dump_keeps_decimal_instances() -> None:
    bar = EodPriceBarV1(**bar_payload())

    dumped = bar.model_dump()

    assert isinstance(dumped["close"], Decimal)
    assert dumped["close"] == Decimal("104.125")
