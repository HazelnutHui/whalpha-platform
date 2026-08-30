from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, localcontext
from uuid import UUID, uuid5

import pytest
from pydantic import ValidationError

from tip_api.parameters.sector_etf_rotation_v1_0_0 import SECTOR_ETFS
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.sector_etf_rotation import (
    SectorEtfRotationError,
    calculate_sector_etf_rotation,
)
from tip_api.services.sector_etf_rotation_oracle import (
    compare_with_independent_sector_rotation_oracle,
)


NS = UUID("ee78566b-9997-40bf-b802-15ec20f949a6")


def _panel() -> MarketRegimeInputPanel:
    calendar = ExchangeCalendar()
    as_of = date(2026, 8, 28)
    sessions = calendar.sessions_before(as_of, 25) + (as_of,)
    tickers = ("SPY", *(item.ticker for item in SECTOR_ETFS))
    bars = []
    for order, ticker in enumerate(tickers):
        for day, session in enumerate(sessions):
            centered = Decimal(order - 6)
            close = Decimal("100") + Decimal(day) * Decimal("0.4")
            if ticker != "SPY":
                close += centered * Decimal(day) * Decimal("0.06")
                close += centered * Decimal(day * day) / Decimal("1000")
            bars.append(
                MarketRegimeBar(
                    uuid5(NS, ticker), ticker, "etf", "ARCX", session,
                    close, close, close, close, Decimal("1000000"),
                )
            )
    sources = tuple(
        MarketRegimeSourceSession(
            session, f"eod/{session}", len(tickers), f"{index + 1:064x}",
            f"{index + 101:064x}", session, f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    universes = (
        MarketRegimeUniverseSource("primary", "Primary", True, 0, frozenset(), "a" * 64),
        MarketRegimeUniverseSource("secondary", "Secondary", False, 1, frozenset(), "b" * 64),
    )
    return MarketRegimeInputPanel(
        as_of, "XNYS", calendar.calendar_version, sessions, sources, tuple(bars),
        universes, "c" * 64, "d" * 64, "e" * 64, "f" * 64, "1" * 64,
    )


def test_product_has_fixed_sector_registry_independent_window_ranks_and_no_score() -> None:
    result = calculate_sector_etf_rotation(panel=_panel())

    assert result.contract_version == "sector-etf-rotation/1.0"
    assert result.theme_status == "unavailable_no_governed_membership"
    assert tuple(item.ticker for item in result.records) == tuple(item.ticker for item in SECTOR_ETFS)
    assert all(tuple(window.window_sessions for window in item.windows) == (5, 10, 20) for item in result.records)
    assert all(window.available_peer_count == 11 for item in result.records for window in item.windows)
    assert result.records[-1].windows[2].relative_rank == 1
    assert result.records[0].windows[2].relative_rank == 11
    assert "score" not in result.model_dump(mode="json")
    assert "price_return_not_fund_flow" in result.warnings
    oracle = compare_with_independent_sector_rotation_oracle(panel=_panel(), product=result)
    assert oracle.mismatch_count == 0, oracle.mismatches


def test_quadrant_is_explainable_from_twenty_day_relative_return_and_acceleration() -> None:
    result = calculate_sector_etf_rotation(panel=_panel())
    strongest = result.records[-1]
    weakest = result.records[0]

    assert strongest.posture.value == "leading_improving"
    assert Decimal(strongest.windows[2].relative_return or "0") > 0
    assert Decimal(strongest.five_day_relative_acceleration or "0") > 0
    assert weakest.posture.value == "lagging_weakening"
    assert "relative_leadership_20_non_positive" in weakest.counterevidence_codes
    assert "five_day_relative_acceleration_positive" in strongest.supporting_fact_codes


def test_missing_long_window_is_visible_and_excluded_only_from_that_rank() -> None:
    panel = _panel()
    twenty_session_start = panel.sessions[-21]
    modified = replace(
        panel,
        bars=tuple(
            item for item in panel.bars
            if not (item.ticker == "XLU" and item.session_date == twenty_session_start)
        ),
    )
    result = calculate_sector_etf_rotation(panel=modified)
    xlu = result.records[-1]

    assert xlu.windows[0].availability.value == "available"
    assert xlu.windows[1].availability.value == "available"
    assert xlu.windows[2].availability.value == "unavailable"
    assert xlu.windows[2].available_peer_count == 10
    assert xlu.posture.value == "unavailable"
    assert all(item.windows[2].available_peer_count == 10 for item in result.records[:-1])
    oracle = compare_with_independent_sector_rotation_oracle(panel=modified, product=result)
    assert oracle.mismatch_count == 0, oracle.mismatches


def test_independent_oracle_detects_rank_drift() -> None:
    panel = _panel()
    result = calculate_sector_etf_rotation(panel=panel)
    first = result.records[0]
    windows = (first.windows[0].model_copy(update={"relative_rank": 1}), *first.windows[1:])
    changed = result.model_copy(
        update={"records": (first.model_copy(update={"windows": windows}), *result.records[1:])}
    )
    oracle = compare_with_independent_sector_rotation_oracle(panel=panel, product=changed)
    assert "XLC:5:relative_rank" in oracle.mismatches


def test_product_contract_rejects_peer_coverage_drift() -> None:
    result = calculate_sector_etf_rotation(panel=_panel())
    payload = result.model_dump(mode="json")
    payload["records"][0]["windows"][0]["available_peer_count"] = 10
    with pytest.raises(ValidationError, match="peer coverage"):
        type(result).model_validate(payload)


def test_duplicate_illegal_close_non_etf_and_session_gap_fail_closed() -> None:
    panel = _panel()
    with pytest.raises(SectorEtfRotationError, match="duplicate"):
        calculate_sector_etf_rotation(panel=replace(panel, bars=panel.bars + (panel.bars[0],)))
    with pytest.raises(SectorEtfRotationError, match="positive"):
        calculate_sector_etf_rotation(
            panel=replace(panel, bars=(replace(panel.bars[0], close=Decimal("0")), *panel.bars[1:]))
        )
    with pytest.raises(SectorEtfRotationError, match="not an ETF"):
        calculate_sector_etf_rotation(
            panel=replace(
                panel,
                bars=(replace(panel.bars[0], instrument_type="common_stock"), *panel.bars[1:]),
            )
        )
    sessions = panel.sessions[:10] + panel.sessions[11:]
    with pytest.raises(SectorEtfRotationError, match="gap"):
        calculate_sector_etf_rotation(panel=replace(panel, sessions=sessions))


@pytest.mark.parametrize("precision", (12, 28, 50))
@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP))
def test_decimal_context_does_not_change_output(precision: int, rounding: str) -> None:
    panel = _panel()
    expected = calculate_sector_etf_rotation(panel=panel)
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        actual = calculate_sector_etf_rotation(panel=panel)
    assert actual.logical_fingerprint == expected.logical_fingerprint
    assert tuple(item.logical_fingerprint for item in actual.records) == tuple(
        item.logical_fingerprint for item in expected.records
    )
