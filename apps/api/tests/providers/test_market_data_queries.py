from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.providers.market_data import EodBarQuery, InstrumentQuery, RevisionSelection

ID1 = UUID(int=1)
ID2 = UUID(int=2)


def test_instrument_query_valid_minimal() -> None:
    query = InstrumentQuery(as_of_date=date(2026, 8, 13))

    assert query.as_of_date == date(2026, 8, 13)
    assert query.instrument_ids is None
    assert query.active_only is False


def test_instrument_query_rejects_datetime_as_of_date() -> None:
    with pytest.raises(ValidationError):
        InstrumentQuery(as_of_date=datetime(2026, 8, 13, 0, 0, tzinfo=UTC))


def test_instrument_query_rejects_empty_instrument_ids() -> None:
    with pytest.raises(ValidationError):
        InstrumentQuery(as_of_date=date(2026, 8, 13), instrument_ids=())


def test_instrument_query_deduplicates_ids_preserving_first_order() -> None:
    query = InstrumentQuery(as_of_date=date(2026, 8, 13), instrument_ids=(ID2, ID1, ID2, ID1))

    assert query.instrument_ids == (ID2, ID1)


def test_instrument_query_is_frozen_and_forbids_extra_fields() -> None:
    query = InstrumentQuery(as_of_date=date(2026, 8, 13))
    with pytest.raises(ValidationError):
        query.active_only = True  # type: ignore[misc]
    with pytest.raises(ValidationError):
        InstrumentQuery(as_of_date=date(2026, 8, 13), ticker="AAPL")


def test_eod_bar_query_valid_and_defaults_to_latest() -> None:
    query = EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13))

    assert query.instrument_ids == (ID1,)
    assert query.start_date == query.end_date
    assert query.revision_selection is RevisionSelection.LATEST


def test_eod_bar_query_explicit_all_revision_selection() -> None:
    query = EodBarQuery(
        instrument_ids=(ID1,),
        start_date=date(2026, 8, 13),
        end_date=date(2026, 8, 14),
        revision_selection=RevisionSelection.ALL,
    )

    assert query.revision_selection is RevisionSelection.ALL


def test_eod_bar_query_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 14), end_date=date(2026, 8, 13))


def test_eod_bar_query_rejects_empty_instrument_ids() -> None:
    with pytest.raises(ValidationError):
        EodBarQuery(instrument_ids=(), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13))


def test_eod_bar_query_deduplicates_ids_preserving_first_order() -> None:
    query = EodBarQuery(
        instrument_ids=(ID2, ID1, ID2, ID1),
        start_date=date(2026, 8, 13),
        end_date=date(2026, 8, 13),
    )

    assert query.instrument_ids == (ID2, ID1)


@pytest.mark.parametrize("field", ["start_date", "end_date"])
def test_eod_bar_query_rejects_datetime_dates(field: str) -> None:
    payload = {
        "instrument_ids": (ID1,),
        "start_date": date(2026, 8, 13),
        "end_date": date(2026, 8, 13),
        field: datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
    }
    with pytest.raises(ValidationError):
        EodBarQuery(**payload)


def test_eod_bar_query_is_frozen_and_forbids_extra_fields() -> None:
    query = EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13))
    with pytest.raises(ValidationError):
        query.revision_selection = RevisionSelection.ALL  # type: ignore[misc]
    with pytest.raises(ValidationError):
        EodBarQuery(instrument_ids=(ID1,), start_date=date(2026, 8, 13), end_date=date(2026, 8, 13), ticker="AAPL")
