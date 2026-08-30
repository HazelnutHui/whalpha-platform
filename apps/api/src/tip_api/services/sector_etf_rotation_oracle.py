"""Independent raw-panel Oracle for Sector ETF Rotation V1."""

from __future__ import annotations

from decimal import Decimal

from tip_api.contracts.analytics.v1.sector_etf_rotation import (
    SectorEtfRotationSnapshotV1,
    SectorRotationOracleComparisonV1,
)
from tip_api.parameters.sector_etf_rotation_v1_0_0 import SECTOR_ETFS, WINDOWS
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


def compare_with_independent_sector_rotation_oracle(
    *, panel: MarketRegimeInputPanel, product: SectorEtfRotationSnapshotV1
) -> SectorRotationOracleComparisonV1:
    sessions = panel.sessions
    required = {"SPY", *(item.ticker for item in SECTOR_ETFS)}
    closes = {
        (bar.ticker, bar.session_date): bar.close
        for bar in panel.bars
        if bar.ticker in required and bar.session_date in set(sessions)
    }
    relative: dict[tuple[str, int], Decimal | None] = {}
    for definition in SECTOR_ETFS:
        for window in WINDOWS:
            relative[(definition.ticker, window)] = _relative(
                definition.ticker, sessions, closes, len(sessions) - 1, window
            )
    ranks: dict[tuple[str, int], int | None] = {}
    peer_counts: dict[int, int] = {}
    for window in WINDOWS:
        values = sorted(
            {
                value
                for (_, item_window), value in relative.items()
                if item_window == window and value is not None
            },
            reverse=True,
        )
        peer_counts[window] = sum(
            1 for (ticker, item_window), value in relative.items()
            if item_window == window and value is not None
        )
        for ticker in (item.ticker for item in SECTOR_ETFS):
            value = relative[(ticker, window)]
            ranks[(ticker, window)] = values.index(value) + 1 if value is not None else None

    mismatches: list[str] = []
    by_ticker = {item.ticker: item for item in product.records}
    for definition in SECTOR_ETFS:
        record = by_ticker.get(definition.ticker)
        if record is None:
            mismatches.append(f"{definition.ticker}:missing_record")
            continue
        for window_row in record.windows:
            window = window_row.window_sessions
            expected = relative[(definition.ticker, window)]
            actual = Decimal(window_row.relative_return) if window_row.relative_return is not None else None
            if actual != _quantized(expected):
                mismatches.append(f"{definition.ticker}:{window}:relative_return")
            if window_row.relative_rank != ranks[(definition.ticker, window)]:
                mismatches.append(f"{definition.ticker}:{window}:relative_rank")
            expected_peers = peer_counts[window]
            if window_row.available_peer_count != expected_peers:
                mismatches.append(f"{definition.ticker}:{window}:peer_count")
        current_five = relative[(definition.ticker, 5)]
        prior_five = _relative(definition.ticker, sessions, closes, len(sessions) - 6, 5)
        expected_acceleration = (
            current_five - prior_five
            if current_five is not None and prior_five is not None
            else None
        )
        actual_acceleration = (
            Decimal(record.five_day_relative_acceleration)
            if record.five_day_relative_acceleration is not None
            else None
        )
        if actual_acceleration != _quantized(expected_acceleration):
            mismatches.append(f"{definition.ticker}:acceleration")
        expected_posture = _posture(relative[(definition.ticker, 20)], expected_acceleration)
        if record.posture.value != expected_posture:
            mismatches.append(f"{definition.ticker}:posture")
        expected_run, expected_left_censored = _run(definition.ticker, sessions, closes)
        if record.five_day_leadership_run_sessions != expected_run:
            mismatches.append(f"{definition.ticker}:run_count")
        if record.run_reaches_history_start != expected_left_censored:
            mismatches.append(f"{definition.ticker}:run_boundary")

    return SectorRotationOracleComparisonV1(
        as_of_session=product.as_of_session,
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        source_product_fingerprint=product.logical_fingerprint,
    )


def _relative(ticker, sessions, closes, end_index, window):
    if end_index < window:
        return None
    start, end = sessions[end_index - window], sessions[end_index]
    keys = ((ticker, start), (ticker, end), ("SPY", start), ("SPY", end))
    if any(key not in closes for key in keys):
        return None
    stock = (closes[(ticker, end)] - closes[(ticker, start)]) / closes[(ticker, start)]
    market = (closes[("SPY", end)] - closes[("SPY", start)]) / closes[("SPY", start)]
    return stock - market


def _posture(relative_twenty, acceleration):
    if relative_twenty is None or acceleration is None:
        return "unavailable"
    if relative_twenty == 0 or acceleration == 0:
        return "neutral"
    return (
        "leading_improving" if relative_twenty > 0 and acceleration > 0
        else "leading_weakening" if relative_twenty > 0
        else "lagging_improving" if acceleration > 0
        else "lagging_weakening"
    )


def _run(ticker, sessions, closes):
    values = [_relative(ticker, sessions, closes, end, 5) for end in range(5, len(sessions))]
    if not values or values[-1] is None:
        return 0, False
    sign = 1 if values[-1] > 0 else -1 if values[-1] < 0 else 0
    count = 0
    for value in reversed(values):
        if value is None or (1 if value > 0 else -1 if value < 0 else 0) != sign:
            break
        count += 1
    return count, count == len(values)


def _quantized(value):
    return value.quantize(Decimal("0.0000000001")) if value is not None else None
