from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest

from tip_api.services import market_regime_sources as sources


NS = UUID("e2ba9652-8206-5666-a7bb-79c8ef130b84")
PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"


def _id(label: str) -> UUID:
    return uuid5(NS, label)


class _FixtureCalendar:
    calendar_id = "XNYS"
    calendar_version = "fixture"

    def __init__(self, sessions):
        self.sessions = sessions

    def sessions_before(self, session, count):
        index = self.sessions.index(session)
        return self.sessions[index - count : index]

    def previous_session(self, session):
        return self.sessions[self.sessions.index(session) - 1]


class _FixtureTable:
    def __init__(self, session, instrument_ids):
        self.session = session
        self.instrument_ids = instrument_ids

    def to_pylist(self):
        return [
            {
                "instrument_id": str(instrument_id),
                "session_date": self.session,
                "source": "fixture",
                "revision": 0,
            }
            for instrument_id in self.instrument_ids
        ]


class _FixtureRepository:
    def __init__(self, sessions, bars_by_session):
        self.sessions = sessions
        self.bars_by_session = bars_by_session
        self.history_requests = []
        self.business_key_requests = []

    def list_sessions(self):
        raise AssertionError("date-only source discovery must use the completion index")

    def list_session_index(self):
        return tuple(self.sessions)

    def read_history_sessions(self, requested):
        self.history_requests.append(requested)
        return tuple(
            SimpleNamespace(
                integrity=SimpleNamespace(
                    session_date=session,
                    record_count=len(self.bars_by_session[session]),
                    content_fingerprint=f"{session.toordinal():064x}"[-64:],
                    parquet_sha256=f"{session.toordinal() + 100:064x}"[-64:],
                    identity_snapshot_date=session,
                    identity_snapshot_fingerprint=f"{session.toordinal() + 200:064x}"[-64:],
                ),
                bars=self.bars_by_session[session],
            )
            for session in requested
        )

    def _read_valid_eod_partition(self, root, *, session_date):
        self.business_key_requests.append(session_date)
        instrument_ids = tuple(item.instrument_id for item in self.bars_by_session[session_date])
        return {}, _FixtureTable(session_date, instrument_ids)


def _bar(instrument_id, ticker, session):
    close = Decimal("20") + Decimal(session.toordinal() % 10)
    return SimpleNamespace(
        instrument_id=instrument_id,
        ticker=ticker,
        instrument_type=SimpleNamespace(value="common_stock"),
        primary_exchange="XNYS",
        session_date=session,
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=Decimal("1000000"),
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        quality_status=SimpleNamespace(value="valid"),
        quality_flags=(),
    )


def test_overlapping_formal_panels_read_each_source_session_once(monkeypatch, tmp_path) -> None:
    sessions = tuple(date(2026, 1, 2) + timedelta(days=index) for index in range(27))
    first_id, second_id = _id("first"), _id("second")
    bars_by_session = {
        session: (_bar(first_id, "AAA", session), _bar(second_id, "BBB", session))
        for session in sessions
    }
    repository = _FixtureRepository(sessions, bars_by_session)
    monkeypatch.setattr(sources, "ExchangeCalendar", lambda: _FixtureCalendar(sessions))
    monkeypatch.setattr(sources, "CanonicalEodReadRepository", lambda root: repository)
    monkeypatch.setattr(
        sources,
        "read_dashboard_universe_activation_pointer",
        lambda root: SimpleNamespace(active=SimpleNamespace(analysis_session=sessions[-1])),
    )
    activation = SimpleNamespace(
        universes=(
            SimpleNamespace(
                universe_id=PRIMARY,
                display_name="Primary",
                is_default=True,
                membership_fingerprint="a" * 64,
            ),
            SimpleNamespace(
                universe_id=SECONDARY,
                display_name="Secondary",
                is_default=False,
                membership_fingerprint="b" * 64,
            ),
        ),
        member_ids_by_universe={
            PRIMARY: frozenset((first_id,)),
            SECONDARY: frozenset((first_id, second_id)),
        },
    )
    monkeypatch.setattr(sources, "read_active_dashboard_universe_activation", lambda *args, **kwargs: activation)
    monkeypatch.setattr(sources, "active_pointer_state_fingerprint", lambda root: "c" * 64)

    panels = sources.load_formal_market_regime_panels(
        data_root=tmp_path,
        as_of_sessions=sessions[-2:],
    )

    assert tuple(item.as_of_session for item in panels) == sessions[-2:]
    assert repository.history_requests == [sessions]
    assert repository.business_key_requests == list(sessions[-2:])
    assert all(len(item.sessions) == 26 for item in panels)
    assert all(len(item.bars) == 52 for item in panels)
    assert panels[0].bars[-1].session_date == sessions[-2]
    assert panels[1].bars[-1].session_date == sessions[-1]


def test_stable_prefix_history_panel_retains_canonical_left_boundary(monkeypatch, tmp_path) -> None:
    sessions = tuple(date(2026, 1, 2) + timedelta(days=index) for index in range(29))
    first_id, second_id = _id("first"), _id("second")
    bars_by_session = {
        session: (_bar(first_id, "AAA", session), _bar(second_id, "BBB", session))
        for session in sessions
    }
    repository = _FixtureRepository(sessions, bars_by_session)
    monkeypatch.setattr(sources, "ExchangeCalendar", lambda: _FixtureCalendar(sessions))
    monkeypatch.setattr(sources, "CanonicalEodReadRepository", lambda root: repository)
    monkeypatch.setattr(
        sources,
        "read_dashboard_universe_activation_pointer",
        lambda root: SimpleNamespace(active=SimpleNamespace(analysis_session=sessions[-1])),
    )
    activation = SimpleNamespace(
        universes=(
            SimpleNamespace(
                universe_id=PRIMARY,
                display_name="Primary",
                is_default=True,
                membership_fingerprint="a" * 64,
            ),
            SimpleNamespace(
                universe_id=SECONDARY,
                display_name="Secondary",
                is_default=False,
                membership_fingerprint="b" * 64,
            ),
        ),
        member_ids_by_universe={
            PRIMARY: frozenset((first_id,)),
            SECONDARY: frozenset((first_id, second_id)),
        },
    )
    monkeypatch.setattr(sources, "read_active_dashboard_universe_activation", lambda *args, **kwargs: activation)
    monkeypatch.setattr(sources, "active_pointer_state_fingerprint", lambda root: "c" * 64)

    panel = sources.load_formal_market_regime_history_panel(
        data_root=tmp_path,
        as_of_session=sessions[-1],
    )

    assert panel.sessions == sessions
    assert tuple(item.session_date for item in panel.source_sessions) == sessions
    assert len(panel.bars) == len(sessions) * 2
    assert repository.history_requests == [sessions]
    assert repository.business_key_requests == list(sessions[25:])


@pytest.mark.parametrize(
    "as_of_sessions",
    [(), (date(2026, 1, 3), date(2026, 1, 2)), (date(2026, 1, 2), date(2026, 1, 2))],
)
def test_multi_panel_loader_rejects_ambiguous_as_of_order(as_of_sessions, tmp_path) -> None:
    with pytest.raises(sources.MarketRegimeSourceError, match="non-empty, unique, and ascending"):
        sources.load_formal_market_regime_panels(data_root=tmp_path, as_of_sessions=as_of_sessions)
