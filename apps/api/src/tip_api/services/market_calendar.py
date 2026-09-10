"""Provider-neutral market-session calendar and EOD freshness boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from importlib.metadata import version
from typing import Protocol
from zoneinfo import ZoneInfo

import exchange_calendars as exchange_calendars
import pandas as pd

XNYS_CALENDAR_ID = "XNYS"
XNYS_TIMEZONE = ZoneInfo("America/New_York")


class MarketCalendarError(RuntimeError):
    """Raised when a market calendar cannot answer a bounded query."""


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class MarketSessionCalendar(Protocol):
    calendar_id: str
    timezone: ZoneInfo
    calendar_version: str

    def is_session(self, session_date: date) -> bool: ...

    def previous_session(self, session_date: date) -> date: ...

    def next_session(self, session_date: date) -> date: ...

    def session_open(self, session_date: date) -> datetime: ...

    def session_close(self, session_date: date) -> datetime: ...

    def latest_completed_session(self, as_of_datetime: datetime) -> date: ...

    def session_lag(self, actual_session: date, expected_session: date) -> int: ...

    def sessions_before(self, session_date: date, count: int) -> tuple[date, ...]: ...

    def sessions_in_range(
        self, start_date: date, end_date: date
    ) -> tuple[date, ...]: ...


@dataclass(frozen=True, slots=True)
class MarketDataFreshness:
    actual_latest_completed_session: date | None
    expected_latest_completed_session: date | None
    session_lag: int | None
    freshness_status: FreshnessStatus
    calendar_id: str
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class ExchangeCalendar:
    """Offline exchange-calendars adapter for one exchange calendar."""

    calendar_id: str = XNYS_CALENDAR_ID
    timezone: ZoneInfo = XNYS_TIMEZONE
    _calendar: object | None = None

    @property
    def calendar_version(self) -> str:
        return version("exchange-calendars")

    def __post_init__(self) -> None:
        if self._calendar is None:
            try:
                object.__setattr__(self, "_calendar", exchange_calendars.get_calendar(self.calendar_id))
            except Exception as exc:  # pragma: no cover - depends on installed calendar data
                raise MarketCalendarError("market calendar is unavailable") from exc

    @property
    def calendar(self):
        if self._calendar is None:  # pragma: no cover - guarded by __post_init__
            raise MarketCalendarError("market calendar is unavailable")
        return self._calendar

    def is_session(self, session_date: date) -> bool:
        try:
            return bool(self.calendar.is_session(pd.Timestamp(session_date)))
        except Exception as exc:
            raise MarketCalendarError("market calendar could not classify session") from exc

    def previous_session(self, session_date: date) -> date:
        try:
            label = self.calendar.previous_session(pd.Timestamp(session_date))
            return label.date()
        except Exception as exc:
            raise MarketCalendarError("market calendar could not find previous session") from exc

    def next_session(self, session_date: date) -> date:
        try:
            label = self.calendar.next_session(pd.Timestamp(session_date))
            return label.date()
        except Exception as exc:
            raise MarketCalendarError("market calendar could not find next session") from exc

    def session_close(self, session_date: date) -> datetime:
        try:
            if not self.is_session(session_date):
                raise MarketCalendarError("close date must be a market session")
            return (
                self.calendar.session_close(pd.Timestamp(session_date))
                .to_pydatetime()
                .astimezone(UTC)
            )
        except MarketCalendarError:
            raise
        except Exception as exc:
            raise MarketCalendarError("market calendar could not determine session close") from exc

    def session_open(self, session_date: date) -> datetime:
        try:
            if not self.is_session(session_date):
                raise MarketCalendarError("open date must be a market session")
            return (
                self.calendar.session_open(pd.Timestamp(session_date))
                .to_pydatetime()
                .astimezone(UTC)
            )
        except MarketCalendarError:
            raise
        except Exception as exc:
            raise MarketCalendarError(
                "market calendar could not determine session open"
            ) from exc

    def latest_completed_session(self, as_of_datetime: datetime) -> date:
        checked_at = _require_aware_utc(as_of_datetime)
        market_date = checked_at.astimezone(self.timezone).date()
        try:
            label = pd.Timestamp(market_date)
            if self.calendar.is_session(label):
                close = self.calendar.session_close(label).to_pydatetime().astimezone(UTC)
                if checked_at >= close:
                    return market_date
                return self.calendar.previous_session(label).date()
            return self.calendar.date_to_session(label, direction="previous").date()
        except Exception as exc:
            raise MarketCalendarError("market calendar could not determine latest completed session") from exc

    def session_lag(self, actual_session: date, expected_session: date) -> int:
        try:
            if not self.is_session(actual_session) or not self.is_session(expected_session):
                raise MarketCalendarError("freshness dates must be market sessions")
            if actual_session > expected_session:
                raise MarketCalendarError("actual session cannot be later than expected session")
            sessions = self.calendar.sessions_in_range(pd.Timestamp(actual_session), pd.Timestamp(expected_session))
            return max(0, len(sessions) - 1)
        except MarketCalendarError:
            raise
        except Exception as exc:
            raise MarketCalendarError("market calendar could not calculate session lag") from exc

    def sessions_before(self, session_date: date, count: int) -> tuple[date, ...]:
        if count <= 0:
            raise MarketCalendarError("history session count must be positive")
        try:
            if not self.is_session(session_date):
                raise MarketCalendarError("analysis date must be a market session")
            previous = self.calendar.previous_session(pd.Timestamp(session_date))
            labels = self.calendar.sessions_window(previous, -count)
            result = tuple(label.date() for label in labels)
            if len(result) != count or result[-1] != previous.date():
                raise MarketCalendarError("market calendar returned an incomplete history window")
            return result
        except MarketCalendarError:
            raise
        except Exception as exc:
            raise MarketCalendarError("market calendar could not build history window") from exc

    def sessions_in_range(
        self, start_date: date, end_date: date
    ) -> tuple[date, ...]:
        if end_date < start_date:
            raise MarketCalendarError("session range end must not precede start")
        try:
            labels = self.calendar.sessions_in_range(
                pd.Timestamp(start_date), pd.Timestamp(end_date)
            )
            result = tuple(label.date() for label in labels)
            if not result:
                raise MarketCalendarError("session range contains no market sessions")
            return result
        except MarketCalendarError:
            raise
        except Exception as exc:
            raise MarketCalendarError(
                "market calendar could not build session range"
            ) from exc


def evaluate_market_data_freshness(
    *,
    calendar: MarketSessionCalendar,
    actual_latest_completed_session: date | None,
    checked_at: datetime,
) -> MarketDataFreshness:
    checked_at_utc = _require_aware_utc(checked_at)
    try:
        expected = calendar.latest_completed_session(checked_at_utc)
        if actual_latest_completed_session is None:
            raise MarketCalendarError("actual completed session is unavailable")
        lag = calendar.session_lag(actual_latest_completed_session, expected)
    except Exception:
        return MarketDataFreshness(
            actual_latest_completed_session=actual_latest_completed_session,
            expected_latest_completed_session=None,
            session_lag=None,
            freshness_status=FreshnessStatus.UNAVAILABLE,
            calendar_id=calendar.calendar_id,
            checked_at=checked_at_utc,
        )
    return MarketDataFreshness(
        actual_latest_completed_session=actual_latest_completed_session,
        expected_latest_completed_session=expected,
        session_lag=lag,
        freshness_status=FreshnessStatus.FRESH if lag == 0 else FreshnessStatus.STALE,
        calendar_id=calendar.calendar_id,
        checked_at=checked_at_utc,
    )


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)
