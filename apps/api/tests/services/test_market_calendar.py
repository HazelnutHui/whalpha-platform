from datetime import UTC, date, datetime

import pytest

from tip_api.services.market_calendar import (
    ExchangeCalendar,
    FreshnessStatus,
    MarketCalendarError,
    evaluate_market_data_freshness,
)


@pytest.fixture(scope="module")
def calendar() -> ExchangeCalendar:
    return ExchangeCalendar()


def test_known_august_2026_sessions_and_weekend(calendar: ExchangeCalendar) -> None:
    assert calendar.is_session(date(2026, 8, 13))
    assert calendar.is_session(date(2026, 8, 14))
    assert not calendar.is_session(date(2026, 8, 15))
    assert not calendar.is_session(date(2026, 8, 16))
    assert calendar.previous_session(date(2026, 8, 14)) == date(2026, 8, 13)


def test_weekend_latest_completed_session_is_friday(calendar: ExchangeCalendar) -> None:
    assert calendar.latest_completed_session(datetime(2026, 8, 15, 18, tzinfo=UTC)) == date(2026, 8, 14)


def test_normal_session_before_and_after_close(calendar: ExchangeCalendar) -> None:
    assert calendar.latest_completed_session(datetime(2026, 8, 14, 19, 59, tzinfo=UTC)) == date(2026, 8, 13)
    assert calendar.latest_completed_session(datetime(2026, 8, 14, 20, 0, tzinfo=UTC)) == date(2026, 8, 14)


def test_holiday_and_early_close(calendar: ExchangeCalendar) -> None:
    assert not calendar.is_session(date(2026, 12, 25))
    assert calendar.latest_completed_session(datetime(2026, 12, 25, 18, tzinfo=UTC)) == date(2026, 12, 24)
    assert calendar.is_session(date(2026, 11, 27))
    assert calendar.latest_completed_session(datetime(2026, 11, 27, 17, 59, tzinfo=UTC)) == date(2026, 11, 25)
    assert calendar.latest_completed_session(datetime(2026, 11, 27, 18, 0, tzinfo=UTC)) == date(2026, 11, 27)


def test_dst_uses_exchange_schedule_utc_close(calendar: ExchangeCalendar) -> None:
    assert calendar.latest_completed_session(datetime(2026, 3, 6, 21, 0, tzinfo=UTC)) == date(2026, 3, 6)
    assert calendar.latest_completed_session(datetime(2026, 3, 9, 19, 59, tzinfo=UTC)) == date(2026, 3, 6)
    assert calendar.latest_completed_session(datetime(2026, 3, 9, 20, 0, tzinfo=UTC)) == date(2026, 3, 9)


def test_stale_and_fresh_session_lag(calendar: ExchangeCalendar) -> None:
    checked_at = datetime(2026, 8, 15, 18, tzinfo=UTC)
    stale = evaluate_market_data_freshness(calendar=calendar, actual_latest_completed_session=date(2026, 8, 13), checked_at=checked_at)
    fresh = evaluate_market_data_freshness(calendar=calendar, actual_latest_completed_session=date(2026, 8, 14), checked_at=checked_at)
    assert stale.expected_latest_completed_session == date(2026, 8, 14)
    assert stale.session_lag == 1
    assert stale.freshness_status is FreshnessStatus.STALE
    assert fresh.session_lag == 0
    assert fresh.freshness_status is FreshnessStatus.FRESH


def test_missing_actual_session_is_unavailable(calendar: ExchangeCalendar) -> None:
    result = evaluate_market_data_freshness(calendar=calendar, actual_latest_completed_session=None, checked_at=datetime(2026, 8, 15, tzinfo=UTC))
    assert result.freshness_status is FreshnessStatus.UNAVAILABLE
    assert result.expected_latest_completed_session is None
    assert result.session_lag is None


def test_calendar_failure_is_safe_unavailable() -> None:
    class BrokenCalendar:
        calendar_id = "XNYS"

        def latest_completed_session(self, value):
            raise MarketCalendarError("offline calendar unavailable")

        def session_lag(self, actual, expected):
            raise AssertionError("must not run")

    result = evaluate_market_data_freshness(calendar=BrokenCalendar(), actual_latest_completed_session=date(2026, 8, 14), checked_at=datetime(2026, 8, 15, tzinfo=UTC))
    assert result.freshness_status is FreshnessStatus.UNAVAILABLE
    assert result.expected_latest_completed_session is None


def test_naive_datetime_is_rejected(calendar: ExchangeCalendar) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        calendar.latest_completed_session(datetime(2026, 8, 15, 12))
