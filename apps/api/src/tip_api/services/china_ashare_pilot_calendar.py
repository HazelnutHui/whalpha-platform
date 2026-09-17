"""Calendar/source-state alignment for the temporary China A-share pilot."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from tip_api.contracts.china_ashare.v1 import (
    ChinaAsharePilotCalendarCoverageReportV1,
    ChinaAsharePilotCalendarInstrumentCoverageV1,
    ChinaAsharePilotIdentityDisposition,
    build_china_ashare_pilot_calendar_coverage_report,
)
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
    read_china_ashare_pilot_daily_package,
)
from tip_api.services.market_calendar import ExchangeCalendar


XSHG_CALENDAR_ID = "XSHG"
CHINA_MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")


class ChinaAshareCalendar(Protocol):
    calendar_id: str
    calendar_version: str
    timezone: ZoneInfo

    def sessions_in_range(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[date, ...]: ...


def build_china_ashare_pilot_calendar_coverage(
    *,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    evaluated_at: datetime,
    calendar: ChinaAshareCalendar | None = None,
) -> ChinaAsharePilotCalendarCoverageReportV1:
    """Compare retained source states with an offline XSHG calendar."""

    session_calendar = calendar or ExchangeCalendar(
        calendar_id=XSHG_CALENDAR_ID,
        timezone=CHINA_MARKET_TIMEZONE,
    )
    if session_calendar.calendar_id != XSHG_CALENDAR_ID:
        raise ValueError("A-share pilot calendar must use XSHG")
    if getattr(session_calendar.timezone, "key", None) != CHINA_MARKET_TIMEZONE.key:
        raise ValueError("A-share pilot calendar must use Asia/Shanghai")
    expected_sessions = session_calendar.sessions_in_range(
        daily_package.plan.history_start_date,
        daily_package.plan.history_end_date,
    )
    if expected_sessions != tuple(sorted(set(expected_sessions))):
        raise ValueError("A-share pilot calendar sessions must be unique and ordered")
    expected_set = set(expected_sessions)
    states_by_instrument: dict[object, set[date]] = {}
    for state in daily_package.captured.daily_batch.trading_states:
        states_by_instrument.setdefault(state.instrument_id, set()).add(
            state.session_date
        )

    bound = tuple(
        item
        for item in daily_package.captured.identity_decisions
        if item.disposition
        is ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
    )
    coverage: list[ChinaAsharePilotCalendarInstrumentCoverageV1] = []
    for decision in bound:
        if decision.pilot_instrument_id is None:
            raise ValueError("bound A-share pilot decision lacks an instrument ID")
        observed = states_by_instrument.get(decision.pilot_instrument_id, set())
        missing = tuple(sorted(expected_set - observed))
        unexpected = tuple(sorted(observed - expected_set))
        coverage.append(
            ChinaAsharePilotCalendarInstrumentCoverageV1(
                source_security_id=decision.source_security_id,
                pilot_instrument_id=decision.pilot_instrument_id,
                exchange=decision.exchange,
                board=decision.board,
                expected_session_count=len(expected_sessions),
                observed_state_count=len(observed),
                missing_session_dates=missing,
                unexpected_state_dates=unexpected,
                source_alignment_complete=not missing and not unexpected,
            )
        )
    coverage.sort(key=lambda item: item.source_security_id)
    covered_ids = {item.pilot_instrument_id for item in coverage}
    if set(states_by_instrument) != covered_ids:
        raise ValueError("A-share pilot state instruments differ from bound identities")

    observed_union = set().union(*states_by_instrument.values())
    missing_union = tuple(sorted(expected_set - observed_union))
    unexpected_union = tuple(sorted(observed_union - expected_set))
    alignment_complete = (
        not missing_union
        and not unexpected_union
        and bool(coverage)
        and all(item.source_alignment_complete for item in coverage)
    )
    reasons = {
        "official_exchange_calendar_not_retained",
        "official_exchange_notice_not_machine_reconciled",
    }
    if alignment_complete:
        reasons.add("library_and_source_state_dates_align")
    else:
        reasons.add("library_and_source_state_dates_differ")
    return build_china_ashare_pilot_calendar_coverage_report(
        plan_fingerprint=daily_package.plan.logical_fingerprint,
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        evaluated_at=evaluated_at,
        calendar_id=XSHG_CALENDAR_ID,
        calendar_version=session_calendar.calendar_version,
        calendar_timezone=CHINA_MARKET_TIMEZONE.key,
        start_date=daily_package.plan.history_start_date,
        end_date=daily_package.plan.history_end_date,
        expected_session_count=len(expected_sessions),
        expected_sessions_fingerprint=_sessions_fingerprint(expected_sessions),
        observed_union_session_count=len(observed_union),
        missing_union_session_dates=missing_union,
        unexpected_union_state_dates=unexpected_union,
        instrument_coverage=tuple(coverage),
        library_source_alignment_complete=alignment_complete,
        official_exchange_notice_retained=False,
        calendar_reconciled=False,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=tuple(sorted(reasons)),
    )


def inspect_china_ashare_pilot_calendar_package(
    *,
    daily_package_path: Path,
    evaluated_at: datetime,
) -> ChinaAsharePilotCalendarCoverageReportV1:
    package = read_china_ashare_pilot_daily_package(
        package_path=daily_package_path
    )
    return build_china_ashare_pilot_calendar_coverage(
        daily_package=package,
        evaluated_at=evaluated_at,
    )


def _sessions_fingerprint(sessions: tuple[date, ...]) -> str:
    payload = json.dumps(
        tuple(item.isoformat() for item in sessions),
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
