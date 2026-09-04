"""Formal read-only source boundary for Market Regime Phase 1a."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from tip_api.contracts.market_data.v1 import InstrumentType
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    active_pointer_state_fingerprint,
    read_active_dashboard_universe_activation,
    read_dashboard_universe_activation_pointer,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.market_calendar import ExchangeCalendar


FROZEN_BASELINE_SESSION = date(2026, 8, 21)
FROZEN_EOD_ROWS = 9941
FROZEN_EOD_CONTENT_FINGERPRINT = "b3d4acc3184e909e233778c6009e9fb81baa5058f67ab2cdd7cef1e84ae4870f"
FROZEN_EOD_BUSINESS_KEY_FINGERPRINT = "76add84ae1ad690f4d349bc3ce6c9a960b455d5e9a37940cf551272c0cca7920"
FROZEN_EOD_PARQUET_SHA256 = "3e934f473d96ae1904260ea2bbde04584a3f42956cbea4f23c1910c35f06a37f"
FROZEN_EOD_MANIFEST_SHA256 = "8bed22cdd9b5a8348f3995bf3e214b1b50729e2f2afae0b7cbe01e121e4b4e32"
FROZEN_IDENTITY_LOGICAL_FINGERPRINT = "9129f3a7cc7bd3b2902471a6c76b64e6c5772cdb27cdc54fb94da5c3f20899d6"
FROZEN_ACTIVATION_POINTER_FINGERPRINT = "dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168"
FROZEN_UNIVERSES = {
    "provider_classified_common_shares_v1": (
        1718,
        "c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978",
        True,
    ),
    "provider_classified_common_shares_plus_adrs_v1": (
        1831,
        "2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295",
        False,
    ),
}


class MarketRegimeSourceError(RuntimeError):
    """Raised when a formal source cannot satisfy the frozen calculation boundary."""


@dataclass(frozen=True, slots=True)
class MarketRegimeBar:
    instrument_id: UUID
    ticker: str
    instrument_type: str
    primary_exchange: str
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    split_adjustment_factor: Decimal = Decimal("1")
    dividend_adjustment_factor: Decimal = Decimal("1")
    total_return_adjustment_factor: Decimal = Decimal("1")
    quality_status: str = "valid"
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketRegimeSourceSession:
    session_date: date
    dataset_path: str
    record_count: int
    content_fingerprint: str
    parquet_sha256: str
    identity_snapshot_date: date
    identity_snapshot_fingerprint: str


@dataclass(frozen=True, slots=True)
class MarketRegimeUniverseSource:
    universe_id: str
    display_name: str
    is_default: bool
    catalog_order: int
    member_ids: frozenset[UUID]
    membership_fingerprint: str


@dataclass(frozen=True, slots=True)
class MarketRegimeInputPanel:
    as_of_session: date
    calendar_id: str
    calendar_version: str
    sessions: tuple[date, ...]
    source_sessions: tuple[MarketRegimeSourceSession, ...]
    bars: tuple[MarketRegimeBar, ...]
    universes: tuple[MarketRegimeUniverseSource, ...]
    activation_pointer_fingerprint: str
    identity_logical_fingerprint: str
    eod_content_fingerprint: str
    eod_business_key_fingerprint: str
    history_source_fingerprint: str

    def select_universe(self, universe_id: str) -> MarketRegimeUniverseSource:
        by_id = {item.universe_id: item for item in self.universes}
        if universe_id not in by_id:
            raise MarketRegimeSourceError("unknown active Universe")
        return by_id[universe_id]


def load_formal_market_regime_panel(
    *,
    data_root: Path,
    as_of_session: date,
) -> MarketRegimeInputPanel:
    """Reread exact immutable EOD/Identity/Activation sources without latest fallback."""

    return load_formal_market_regime_panels(
        data_root=data_root,
        as_of_sessions=(as_of_session,),
    )[0]


def load_formal_market_regime_history_panel(
    *,
    data_root: Path,
    as_of_session: date,
) -> MarketRegimeInputPanel:
    """Load one stable-prefix panel from the first canonical session through as-of."""

    if not data_root.is_absolute() or data_root.is_symlink() or not data_root.is_dir():
        raise MarketRegimeSourceError("data root must be an absolute regular directory")
    safe_root = data_root.resolve(strict=True)
    calendar = ExchangeCalendar()
    session_index = CanonicalEodReadRepository(safe_root).list_session_index()
    sessions = tuple(item for item in session_index if item <= as_of_session)
    if len(sessions) < 26 or sessions[-1] != as_of_session:
        raise MarketRegimeSourceError("stable-prefix history requires at least 26 sessions through as-of")
    if any(calendar.previous_session(right) != left for left, right in zip(sessions, sessions[1:])):
        raise MarketRegimeSourceError("stable-prefix history contains an XNYS session gap")
    rolling_as_of_sessions = sessions[25:]
    panels = load_formal_market_regime_panels(
        data_root=safe_root,
        as_of_sessions=rolling_as_of_sessions,
    )
    source_by_session: dict[date, MarketRegimeSourceSession] = {}
    bars_by_key: dict[tuple[UUID, date], MarketRegimeBar] = {}
    for panel in panels:
        for source in panel.source_sessions:
            previous = source_by_session.get(source.session_date)
            if previous is not None and previous != source:
                raise MarketRegimeSourceError("overlapping stable-prefix source custody differs")
            source_by_session[source.session_date] = source
        for bar in panel.bars:
            key = (bar.instrument_id, bar.session_date)
            previous = bars_by_key.get(key)
            if previous is not None and previous != bar:
                raise MarketRegimeSourceError("overlapping stable-prefix bars differ")
            bars_by_key[key] = bar
    if tuple(sorted(source_by_session)) != sessions:
        raise MarketRegimeSourceError("stable-prefix source ledger is incomplete")
    source_sessions = tuple(source_by_session[item] for item in sessions)
    history_source_fingerprint = _fingerprint(
        [
            {
                "session_date": item.session_date.isoformat(),
                "dataset_path": item.dataset_path,
                "record_count": item.record_count,
                "content_fingerprint": item.content_fingerprint,
                "parquet_sha256": item.parquet_sha256,
                "identity_snapshot_date": item.identity_snapshot_date.isoformat(),
                "identity_snapshot_fingerprint": item.identity_snapshot_fingerprint,
            }
            for item in source_sessions
        ]
    )
    current = panels[-1]
    return MarketRegimeInputPanel(
        as_of_session=current.as_of_session,
        calendar_id=current.calendar_id,
        calendar_version=current.calendar_version,
        sessions=sessions,
        source_sessions=source_sessions,
        bars=tuple(bars_by_key[key] for key in sorted(bars_by_key, key=lambda item: (item[1], str(item[0])))),
        universes=current.universes,
        activation_pointer_fingerprint=current.activation_pointer_fingerprint,
        identity_logical_fingerprint=current.identity_logical_fingerprint,
        eod_content_fingerprint=current.eod_content_fingerprint,
        eod_business_key_fingerprint=current.eod_business_key_fingerprint,
        history_source_fingerprint=history_source_fingerprint,
    )


def load_formal_market_regime_panels(
    *,
    data_root: Path,
    as_of_sessions: tuple[date, ...],
) -> tuple[MarketRegimeInputPanel, ...]:
    """Load overlapping formal panels with each immutable source session read once."""

    if not data_root.is_absolute() or data_root.is_symlink() or not data_root.is_dir():
        raise MarketRegimeSourceError("data root must be an absolute regular directory")
    if not as_of_sessions or tuple(sorted(as_of_sessions)) != as_of_sessions or len(set(as_of_sessions)) != len(
        as_of_sessions
    ):
        raise MarketRegimeSourceError("panel as-of sessions must be non-empty, unique, and ascending")
    safe_root = data_root.resolve(strict=True)
    calendar = ExchangeCalendar()
    panel_sessions_by_as_of = {
        as_of_session: calendar.sessions_before(as_of_session, 25) + (as_of_session,)
        for as_of_session in as_of_sessions
    }
    if any(
        len(sessions) != 26 or sessions[-1] != as_of_session or len(set(sessions)) != 26
        for as_of_session, sessions in panel_sessions_by_as_of.items()
    ):
        raise MarketRegimeSourceError("exact 26-session XNYS panel is required")
    required_sessions = tuple(
        sorted(
            {
                session
                for sessions in panel_sessions_by_as_of.values()
                for session in sessions
            }
        )
    )

    repository = CanonicalEodReadRepository(safe_root)
    completed_sessions = frozenset(repository.list_session_index())
    missing_sessions = tuple(
        item for item in required_sessions if item not in completed_sessions
    )
    if missing_sessions:
        raise MarketRegimeSourceError(
            "required completed EOD sessions are missing: "
            + ",".join(item.isoformat() for item in missing_sessions)
        )
    reads = repository.read_history_sessions(required_sessions)
    if tuple(item.integrity.session_date for item in reads) != required_sessions:
        raise MarketRegimeSourceError("formal reader session order mismatch")

    source_sessions_by_date = {
        item.integrity.session_date: MarketRegimeSourceSession(
            session_date=item.integrity.session_date,
            dataset_path=(
                "market-data/eod-price-bars/schema_version=1/session_date="
                f"{item.integrity.session_date.isoformat()}"
            ),
            record_count=item.integrity.record_count,
            content_fingerprint=item.integrity.content_fingerprint,
            parquet_sha256=item.integrity.parquet_sha256,
            identity_snapshot_date=item.integrity.identity_snapshot_date,
            identity_snapshot_fingerprint=item.integrity.identity_snapshot_fingerprint,
        )
        for item in reads
    }
    integrity_by_date = {item.integrity.session_date: item.integrity for item in reads}

    bars_by_session: dict[date, tuple[MarketRegimeBar, ...]] = {}
    seen_keys: set[tuple[UUID, date]] = set()
    for session_read in reads:
        session_bars: list[MarketRegimeBar] = []
        for item in session_read.bars:
            key = (item.instrument_id, item.session_date)
            if key in seen_keys:
                raise MarketRegimeSourceError("duplicate instrument/session business key")
            seen_keys.add(key)
            _validate_bar(item.open, item.high, item.low, item.close, item.volume)
            session_bars.append(
                MarketRegimeBar(
                    instrument_id=item.instrument_id,
                    ticker=item.ticker,
                    instrument_type=item.instrument_type.value,
                    primary_exchange=item.primary_exchange,
                    session_date=item.session_date,
                    open=item.open,
                    high=item.high,
                    low=item.low,
                    close=item.close,
                    volume=item.volume,
                    split_adjustment_factor=item.split_adjustment_factor,
                    dividend_adjustment_factor=item.dividend_adjustment_factor,
                    total_return_adjustment_factor=item.total_return_adjustment_factor,
                    quality_status=item.quality_status.value,
                    quality_flags=item.quality_flags,
                )
            )
        bars_by_session[session_read.integrity.session_date] = tuple(
            sorted(session_bars, key=lambda item: str(item.instrument_id))
        )

    pointer = read_dashboard_universe_activation_pointer(safe_root)
    if pointer is None:
        raise MarketRegimeSourceError("Activation V2 pointer is required")
    activation = read_active_dashboard_universe_activation(
        safe_root,
        analysis_session=pointer.active.analysis_session,
        validate_sources=True,
    )
    universes: list[MarketRegimeUniverseSource] = []
    for order, record in enumerate(activation.universes):
        member_ids = activation.member_ids_by_universe[record.universe_id]
        universes.append(
            MarketRegimeUniverseSource(
                universe_id=record.universe_id,
                display_name=record.display_name,
                is_default=record.is_default,
                catalog_order=order,
                member_ids=member_ids,
                membership_fingerprint=record.membership_fingerprint,
            )
        )
    pointer_fingerprint = active_pointer_state_fingerprint(safe_root)
    panels: list[MarketRegimeInputPanel] = []
    for as_of_session in as_of_sessions:
        sessions = panel_sessions_by_as_of[as_of_session]
        source_sessions = tuple(source_sessions_by_date[item] for item in sessions)
        as_of_integrity = integrity_by_date[as_of_session]
        if as_of_integrity.identity_snapshot_date != as_of_session:
            raise MarketRegimeSourceError("as-of EOD does not reference same-day Identity")
        bars_tuple = tuple(
            bar
            for session in sessions
            for bar in bars_by_session[session]
        )
        business_key_fingerprint = _as_of_business_key_fingerprint(repository, safe_root, as_of_session)
        history_source_fingerprint = _fingerprint(
            [
                {
                    "session_date": item.session_date.isoformat(),
                    "dataset_path": item.dataset_path,
                    "record_count": item.record_count,
                    "content_fingerprint": item.content_fingerprint,
                    "parquet_sha256": item.parquet_sha256,
                    "identity_snapshot_date": item.identity_snapshot_date.isoformat(),
                    "identity_snapshot_fingerprint": item.identity_snapshot_fingerprint,
                }
                for item in source_sessions
            ]
        )
        panel = MarketRegimeInputPanel(
            as_of_session=as_of_session,
            calendar_id=calendar.calendar_id,
            calendar_version=calendar.calendar_version,
            sessions=sessions,
            source_sessions=source_sessions,
            bars=bars_tuple,
            universes=tuple(universes),
            activation_pointer_fingerprint=pointer_fingerprint,
            identity_logical_fingerprint=as_of_integrity.identity_snapshot_fingerprint,
            eod_content_fingerprint=as_of_integrity.content_fingerprint,
            eod_business_key_fingerprint=business_key_fingerprint,
            history_source_fingerprint=history_source_fingerprint,
        )
        _validate_frozen_baseline(panel, as_of_integrity, safe_root)
        panels.append(panel)
    return tuple(panels)


def _validate_frozen_baseline(panel: MarketRegimeInputPanel, integrity: object, root: Path) -> None:
    if panel.as_of_session != FROZEN_BASELINE_SESSION:
        return
    if (
        integrity.record_count != FROZEN_EOD_ROWS
        or integrity.content_fingerprint != FROZEN_EOD_CONTENT_FINGERPRINT
        or integrity.parquet_sha256 != FROZEN_EOD_PARQUET_SHA256
        or _file_sha256(
            root
            / "market-data/eod-price-bars/schema_version=1/session_date=2026-08-21/manifest.json"
        ) != FROZEN_EOD_MANIFEST_SHA256
        or panel.eod_business_key_fingerprint != FROZEN_EOD_BUSINESS_KEY_FINGERPRINT
        or panel.identity_logical_fingerprint != FROZEN_IDENTITY_LOGICAL_FINGERPRINT
        or panel.activation_pointer_fingerprint != FROZEN_ACTIVATION_POINTER_FINGERPRINT
        or panel.sessions[0] != date(2026, 7, 17)
    ):
        raise MarketRegimeSourceError("frozen 2026-08-21 source anchors do not match")
    if tuple(item.universe_id for item in panel.universes) != tuple(FROZEN_UNIVERSES):
        raise MarketRegimeSourceError("active Universe catalog order mismatch")
    for item in panel.universes:
        count, fingerprint, is_default = FROZEN_UNIVERSES[item.universe_id]
        if (
            len(item.member_ids) != count
            or item.membership_fingerprint != fingerprint
            or item.is_default is not is_default
        ):
            raise MarketRegimeSourceError("frozen active Universe anchor mismatch")
    current_etfs = {
        item.ticker: item
        for item in panel.bars
        if item.session_date == panel.as_of_session and item.instrument_type == InstrumentType.ETF.value
    }
    missing = tuple(ticker for ticker in ("SPY", "QQQ", "IWM", "DIA") if ticker not in current_etfs)
    if missing:
        raise MarketRegimeSourceError("required broad ETF proxies are unavailable")


def _as_of_business_key_fingerprint(
    repository: CanonicalEodReadRepository,
    root: Path,
    session: date,
) -> str:
    _, table = repository._read_valid_eod_partition(root, session_date=session)
    keys = sorted(
        (row["instrument_id"], row["session_date"].isoformat(), row["source"], row["revision"])
        for row in table.to_pylist()
    )
    return _fingerprint([list(item) for item in keys])


def _validate_bar(open_: Decimal, high: Decimal, low: Decimal, close: Decimal, volume: Decimal) -> None:
    values = (open_, high, low, close, volume)
    if any(not item.is_finite() for item in values):
        raise MarketRegimeSourceError("non-finite market input")
    if min(open_, high, low, close) <= 0 or volume < 0:
        raise MarketRegimeSourceError("illegal price or volume input")
    if high < max(open_, low, close) or low > min(open_, high, close):
        raise MarketRegimeSourceError("invalid OHLC input")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
