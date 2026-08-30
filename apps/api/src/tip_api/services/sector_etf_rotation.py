"""Deterministic, score-free Sector ETF Rotation V1 analytics."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from typing import Any, Mapping

from tip_api.contracts.analytics.v1.sector_etf_rotation import (
    SectorEtfRotationSnapshotV1,
    SectorRotationAvailability,
    SectorRotationPosture,
    SectorRotationRecordV1,
    SectorRotationWindowV1,
)
from tip_api.parameters.sector_etf_rotation_v1_0_0 import (
    PARAMETER_FINGERPRINT,
    SECTOR_ETFS,
    WINDOWS,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


class SectorEtfRotationError(RuntimeError):
    """Raised when the fixed Sector ETF Rotation input boundary is invalid."""


INTERNAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
for _signal in (InvalidOperation, DivisionByZero, Overflow):
    INTERNAL_CONTEXT.traps[_signal] = True

WARNINGS = (
    "sector_etf_price_proxy_not_constituent_breadth",
    "price_return_not_fund_flow",
    "relative_return_not_alpha_or_causal_attribution",
    "descriptive_rotation_not_trade_instruction",
    "theme_membership_unavailable",
)


def calculate_sector_etf_rotation(
    *, panel: MarketRegimeInputPanel
) -> SectorEtfRotationSnapshotV1:
    """Build independent 5/10/20-session sector-relative facts without a total score."""

    with localcontext(INTERNAL_CONTEXT):
        sessions = _validated_sessions(panel)
        closes = _registered_closes(panel, sessions)
        raw = [
            _raw_record(
                ticker=definition.ticker,
                sector=definition.sector,
                registry_order=index,
                sessions=sessions,
                closes=closes,
            )
            for index, definition in enumerate(SECTOR_ETFS)
        ]
        ranked = _apply_cross_sectional_ranks(raw)
        records = tuple(_final_record(item) for item in ranked)
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "contract_version": "sector-etf-rotation/1.0",
            "calculation_version": "sector-etf-rotation-v1.0.0",
            "parameter_set_id": "sector-etf-rotation-fixed-registry-1",
            "parameter_fingerprint": PARAMETER_FINGERPRINT,
            "as_of_session": panel.as_of_session,
            "input_first_session": sessions[0],
            "input_last_session": sessions[-1],
            "input_session_count": len(sessions),
            "benchmark_ticker": "SPY",
            "records": records,
            "theme_status": "unavailable_no_governed_membership",
            "source_history_fingerprint": panel.history_source_fingerprint,
            "warnings": WARNINGS,
        }
        return SectorEtfRotationSnapshotV1(
            **payload,
            logical_fingerprint=_fingerprint(payload),
        )


def _validated_sessions(panel: MarketRegimeInputPanel) -> tuple[date, ...]:
    sessions = panel.sessions
    if len(sessions) < 21 or sessions[-1] != panel.as_of_session:
        raise SectorEtfRotationError("sector rotation requires at least 21 sessions through as-of")
    if len(set(sessions)) != len(sessions) or tuple(sorted(sessions)) != sessions:
        raise SectorEtfRotationError("sector rotation sessions must be unique and ordered")
    calendar = ExchangeCalendar()
    if any(calendar.previous_session(right) != left for left, right in zip(sessions, sessions[1:])):
        raise SectorEtfRotationError("sector rotation input contains an XNYS session gap")
    return sessions


def _registered_closes(
    panel: MarketRegimeInputPanel,
    sessions: tuple[date, ...],
) -> dict[tuple[str, date], Decimal]:
    required = {item.ticker for item in SECTOR_ETFS} | {"SPY"}
    session_set = set(sessions)
    closes: dict[tuple[str, date], Decimal] = {}
    for bar in panel.bars:
        if bar.ticker not in required or bar.session_date not in session_set:
            continue
        if str(bar.instrument_type) not in {"etf", "InstrumentType.ETF"}:
            raise SectorEtfRotationError("registered rotation instrument is not an ETF")
        if bar.close <= 0:
            raise SectorEtfRotationError("registered rotation close must be positive")
        key = (bar.ticker, bar.session_date)
        if key in closes:
            raise SectorEtfRotationError("duplicate registered rotation bar")
        closes[key] = bar.close
    return closes


def _raw_record(
    *,
    ticker: str,
    sector: str,
    registry_order: int,
    sessions: tuple[date, ...],
    closes: Mapping[tuple[str, date], Decimal],
) -> dict[str, Any]:
    end_index = len(sessions) - 1
    windows = tuple(
        _window(ticker=ticker, sessions=sessions, closes=closes, end_index=end_index, window=window)
        for window in WINDOWS
    )
    current_five = _relative_return(ticker, sessions, closes, end_index=end_index, window=5)
    prior_five = _relative_return(ticker, sessions, closes, end_index=end_index - 5, window=5)
    acceleration = current_five - prior_five if current_five is not None and prior_five is not None else None
    relative_twenty = windows[2].relative_return
    posture = _posture(
        Decimal(relative_twenty) if relative_twenty is not None else None,
        acceleration,
    )
    available = posture is not SectorRotationPosture.UNAVAILABLE
    run_count, reaches_start = _leadership_run(ticker, sessions, closes)
    support, counter = _evidence(
        relative_5=current_five,
        relative_20=Decimal(relative_twenty) if relative_twenty is not None else None,
        acceleration=acceleration,
    )
    return {
        "ticker": ticker,
        "sector": sector,
        "registry_order": registry_order,
        "as_of_session": sessions[-1],
        "windows": windows,
        "five_day_relative_acceleration": _text(acceleration),
        "posture": posture,
        "five_day_leadership_run_sessions": run_count,
        "run_reaches_history_start": reaches_start,
        "availability": SectorRotationAvailability.AVAILABLE if available else SectorRotationAvailability.UNAVAILABLE,
        "missing_reason": None if available else "complete_20_session_and_prior_5_session_comparison_required",
        "supporting_fact_codes": support,
        "counterevidence_codes": counter,
        "warnings": WARNINGS,
    }


def _window(
    *, ticker: str, sessions: tuple[date, ...], closes: Mapping[tuple[str, date], Decimal],
    end_index: int, window: int,
) -> SectorRotationWindowV1:
    relative = _relative_return(ticker, sessions, closes, end_index=end_index, window=window)
    if relative is None:
        return SectorRotationWindowV1(
            window_sessions=window, start_session=None, end_session=sessions[end_index],
            etf_return=None, spy_return=None, relative_return=None, relative_rank=None,
            available_peer_count=0, availability=SectorRotationAvailability.UNAVAILABLE,
            missing_reason="complete_etf_and_spy_window_required",
        )
    start = sessions[end_index - window]
    end = sessions[end_index]
    etf_return = closes[(ticker, end)] / closes[(ticker, start)] - Decimal(1)
    spy_return = closes[("SPY", end)] / closes[("SPY", start)] - Decimal(1)
    return SectorRotationWindowV1(
        window_sessions=window, start_session=start, end_session=end,
        etf_return=_text(etf_return), spy_return=_text(spy_return),
        relative_return=_text(relative), relative_rank=None, available_peer_count=0,
        availability=SectorRotationAvailability.AVAILABLE, missing_reason=None,
    )


def _relative_return(
    ticker: str,
    sessions: tuple[date, ...],
    closes: Mapping[tuple[str, date], Decimal],
    *, end_index: int, window: int,
) -> Decimal | None:
    if end_index < window:
        return None
    start, end = sessions[end_index - window], sessions[end_index]
    keys = ((ticker, start), (ticker, end), ("SPY", start), ("SPY", end))
    if any(key not in closes for key in keys):
        return None
    return (closes[(ticker, end)] / closes[(ticker, start)] - Decimal(1)) - (
        closes[("SPY", end)] / closes[("SPY", start)] - Decimal(1)
    )


def _posture(relative_twenty: Decimal | None, acceleration: Decimal | None) -> SectorRotationPosture:
    if relative_twenty is None or acceleration is None:
        return SectorRotationPosture.UNAVAILABLE
    if relative_twenty == 0 or acceleration == 0:
        return SectorRotationPosture.NEUTRAL
    if relative_twenty > 0 and acceleration > 0:
        return SectorRotationPosture.LEADING_IMPROVING
    if relative_twenty > 0:
        return SectorRotationPosture.LEADING_WEAKENING
    if acceleration > 0:
        return SectorRotationPosture.LAGGING_IMPROVING
    return SectorRotationPosture.LAGGING_WEAKENING


def _leadership_run(
    ticker: str, sessions: tuple[date, ...], closes: Mapping[tuple[str, date], Decimal]
) -> tuple[int, bool]:
    observations = [
        _relative_return(ticker, sessions, closes, end_index=end_index, window=5)
        for end_index in range(5, len(sessions))
    ]
    if not observations or observations[-1] is None:
        return 0, False
    sign = _sign(observations[-1])
    count = 0
    for value in reversed(observations):
        if value is None or _sign(value) != sign:
            break
        count += 1
    return count, count == len(observations)


def _apply_cross_sectional_ranks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for window_index in range(len(WINDOWS)):
        available = [
            Decimal(item["windows"][window_index].relative_return)
            for item in records
            if item["windows"][window_index].relative_return is not None
        ]
        ordered = sorted(set(available), reverse=True)
        ranks = {value: index + 1 for index, value in enumerate(ordered)}
        for item in records:
            row = item["windows"][window_index]
            windows = list(item["windows"])
            if row.relative_return is None:
                windows[window_index] = row.model_copy(
                    update={"available_peer_count": len(available)}
                )
                item["windows"] = tuple(windows)
                continue
            value = Decimal(row.relative_return)
            windows[window_index] = row.model_copy(
                update={"relative_rank": ranks[value], "available_peer_count": len(available)}
            )
            item["windows"] = tuple(windows)
    return records


def _evidence(
    *, relative_5: Decimal | None, relative_20: Decimal | None, acceleration: Decimal | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    support: list[str] = []
    counter: list[str] = []
    for value, positive, negative in (
        (relative_20, "relative_leadership_20_positive", "relative_leadership_20_non_positive"),
        (relative_5, "relative_leadership_5_positive", "relative_leadership_5_non_positive"),
        (acceleration, "five_day_relative_acceleration_positive", "five_day_relative_acceleration_non_positive"),
    ):
        if value is None:
            counter.append(f"{negative}_unavailable")
        elif value > 0:
            support.append(positive)
        else:
            counter.append(negative)
    return tuple(support), tuple(counter)


def _final_record(payload: dict[str, Any]) -> SectorRotationRecordV1:
    return SectorRotationRecordV1(**payload, logical_fingerprint=_fingerprint(payload))


def _sign(value: Decimal) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _text(value: Decimal | None) -> str | None:
    return format(value.quantize(Decimal("0.0000000001")), "f") if value is not None else None


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_json_value(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
