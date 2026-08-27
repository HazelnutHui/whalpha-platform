from __future__ import annotations

import shutil
import tempfile
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

import pytest

from tip_api.services.market_regime_panel_cache import (
    MarketRegimePanelCacheError,
    MarketRegimePanelCacheMiss,
    panel_source_boundary,
    read_market_regime_panel_cache,
    write_market_regime_panel_cache,
)
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)


NS = UUID("b5e87f06-1d63-5ca0-86ae-c77743bc3591")


def _panel() -> MarketRegimeInputPanel:
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(26))
    stock = uuid5(NS, "stock")
    etf = uuid5(NS, "spy")
    bars = tuple(
        MarketRegimeBar(
            instrument_id=instrument_id,
            ticker=ticker,
            instrument_type=kind,
            primary_exchange="XNYS",
            session_date=session,
            open=Decimal("10") + index,
            high=Decimal("11") + index,
            low=Decimal("9") + index,
            close=Decimal("10.5") + index,
            volume=Decimal("1000000.0001") + index,
            quality_flags=("reviewed",) if index == 0 else (),
        )
        for index, session in enumerate(sessions)
        for instrument_id, ticker, kind in (
            (stock, "AAA", "common_stock"),
            (etf, "SPY", "etf"),
        )
    )
    sources = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"eod/{session.isoformat()}",
            record_count=2,
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    universes = (
        MarketRegimeUniverseSource("primary", "Primary", True, 0, frozenset({stock}), "a" * 64),
        MarketRegimeUniverseSource("secondary", "Secondary", False, 1, frozenset({stock}), "b" * 64),
    )
    return MarketRegimeInputPanel(
        as_of_session=sessions[-1],
        calendar_id="XNYS",
        calendar_version="fixture",
        sessions=sessions,
        source_sessions=sources,
        bars=bars,
        universes=universes,
        activation_pointer_fingerprint="c" * 64,
        identity_logical_fingerprint="d" * 64,
        eod_content_fingerprint="e" * 64,
        eod_business_key_fingerprint="f" * 64,
        history_source_fingerprint="1" * 64,
    )


def test_panel_cache_is_content_addressed_rereadable_and_idempotent() -> None:
    panel = _panel()
    root = Path(tempfile.mkdtemp(prefix="mrom-panel-cache-", dir="/tmp"))
    root.chmod(0o700)
    try:
        first = write_market_regime_panel_cache(cache_root=root, panel=panel)
        second = write_market_regime_panel_cache(cache_root=root, panel=panel)
        reread, manifest = read_market_regime_panel_cache(
            cache_root=root,
            expected_source=panel_source_boundary(panel),
        )
        assert first == second == manifest
        assert reread == panel
        assert len(tuple(root.iterdir())) == 1
        assert manifest["bar_record_count"] == len(panel.bars)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_panel_cache_miss_tamper_and_symlink_fail_closed(tmp_path: Path) -> None:
    panel = _panel()
    root = Path(tempfile.mkdtemp(prefix="mrom-panel-cache-gates-", dir="/tmp"))
    root.chmod(0o700)
    link = Path(f"{root}-link")
    try:
        manifest = write_market_regime_panel_cache(cache_root=root, panel=panel)
        changed = panel_source_boundary(panel)
        changed["history_source_fingerprint"] = "2" * 64
        with pytest.raises(MarketRegimePanelCacheMiss):
            read_market_regime_panel_cache(cache_root=root, expected_source=changed)

        bars = root / manifest["cache_key"] / "bars.parquet"
        bars.chmod(0o600)
        with bars.open("ab") as handle:
            handle.write(b"tamper")
        bars.chmod(0o400)
        with pytest.raises(MarketRegimePanelCacheError, match="physical fingerprint"):
            read_market_regime_panel_cache(
                cache_root=root,
                expected_source=panel_source_boundary(panel),
            )

        link.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(MarketRegimePanelCacheError, match="symlink"):
            write_market_regime_panel_cache(cache_root=link, panel=panel)
    finally:
        link.unlink(missing_ok=True)
        shutil.rmtree(root, ignore_errors=True)


def test_panel_cache_rejects_malformed_source_boundary() -> None:
    source = panel_source_boundary(_panel())
    source["source_sessions"][0]["content_fingerprint"] = "not-a-fingerprint"
    with pytest.raises(MarketRegimePanelCacheError, match="malformed"):
        read_market_regime_panel_cache(
            cache_root=Path("/tmp/unused-panel-cache"),
            expected_source=source,
        )


def test_panel_cache_rejects_duplicate_bar_before_creating_root() -> None:
    panel = _panel()
    malformed = replace(panel, bars=(*panel.bars, panel.bars[0]))
    root = Path(tempfile.mkdtemp(prefix="mrom-panel-cache-invalid-", dir="/tmp"))
    shutil.rmtree(root)
    with pytest.raises(MarketRegimePanelCacheError, match="unique complete"):
        write_market_regime_panel_cache(cache_root=root, panel=malformed)
    assert not root.exists()
