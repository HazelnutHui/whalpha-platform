"""Capture and reconcile official SSE/SZSE annual closure notices."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from tip_api.contracts.china_ashare.v1.calendar_evidence import (
    ChinaAshareOfficialCalendarEvidencePlanV1,
    ChinaAshareOfficialCalendarEvidenceReportV1,
    ChinaAshareOfficialCalendarNoticeSpecV1,
    build_official_calendar_evidence_plan,
    build_official_calendar_evidence_report,
)
from tip_api.contracts.china_ashare.v1.foundation import ChinaAshareExchange
from tip_api.persistence.china_ashare_calendar_evidence_package import (
    ChinaAshareCalendarEvidencePackageResultV1,
    publish_china_ashare_calendar_evidence_package,
)
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
    read_china_ashare_pilot_daily_package,
)
from tip_api.providers.china_ashare.official_calendar_adapter import (
    CapturedOfficialCalendarNoticeV1,
    OfficialCalendarHttpFetcher,
    UrllibOfficialCalendarHttpFetcher,
    capture_official_calendar_notice,
)
from tip_api.services.china_ashare_pilot_calendar import (
    CHINA_MARKET_TIMEZONE,
    XSHG_CALENDAR_ID,
    build_china_ashare_pilot_calendar_coverage,
)
from tip_api.services.market_calendar import ExchangeCalendar


_SSE = "https://www.sse.com.cn/disclosure"
_SZSE = "https://www.szse.cn/disclosure/notice"
OFFICIAL_CALENDAR_NOTICE_URLS: dict[tuple[ChinaAshareExchange, int], str] = {
    (ChinaAshareExchange.SSE, 2021): (
        f"{_SSE}/dealinstruc/closed/c/c_20201224_5286951.shtml"
    ),
    (ChinaAshareExchange.SSE, 2022): (
        f"{_SSE}/announcement/general/c/c_20211220_5662606.shtml"
    ),
    (ChinaAshareExchange.SSE, 2023): (
        f"{_SSE}/announcement/general/c/c_20221227_5714458.shtml"
    ),
    (ChinaAshareExchange.SSE, 2024): (
        f"{_SSE}/announcement/general/c/c_20231226_5733939.shtml"
    ),
    (ChinaAshareExchange.SSE, 2025): (
        f"{_SSE}/dealinstruc/closed/c/c_20241223_10767110.shtml"
    ),
    (ChinaAshareExchange.SSE, 2026): (
        f"{_SSE}/announcement/general/c/c_20251222_10802507.shtml"
    ),
    (ChinaAshareExchange.SZSE, 2021): (
        f"{_SZSE}/general/t20201224_583950.html"
    ),
    (ChinaAshareExchange.SZSE, 2022): f"{_SZSE}/t20211220_590321.html",
    (ChinaAshareExchange.SZSE, 2023): (
        f"{_SZSE}/general/t20221227_598022.html"
    ),
    (ChinaAshareExchange.SZSE, 2024): f"{_SZSE}/t20231226_605108.html",
    (ChinaAshareExchange.SZSE, 2025): (
        "https://investor.szse.cn/disclosure/notice/general/"
        "t20241223_611283.html"
    ),
    (ChinaAshareExchange.SZSE, 2026): f"{_SZSE}/t20251222_618087.html",
}


def build_default_official_calendar_evidence_plan(
    *,
    start_date: date,
    end_date: date,
    planned_at: datetime,
) -> ChinaAshareOfficialCalendarEvidencePlanV1:
    years = range(start_date.year, end_date.year + 1)
    missing = [
        (exchange, year)
        for year in years
        for exchange in (ChinaAshareExchange.SSE, ChinaAshareExchange.SZSE)
        if (exchange, year) not in OFFICIAL_CALENDAR_NOTICE_URLS
    ]
    if missing:
        raise ValueError("official calendar URL registry does not cover the interval")
    specs = tuple(
        ChinaAshareOfficialCalendarNoticeSpecV1(
            exchange=exchange,
            notice_year=year,
            source_url=OFFICIAL_CALENDAR_NOTICE_URLS[(exchange, year)],
        )
        for year in years
        for exchange in (ChinaAshareExchange.SSE, ChinaAshareExchange.SZSE)
    )
    return build_official_calendar_evidence_plan(
        planned_at=planned_at,
        start_date=start_date,
        end_date=end_date,
        notice_specs=specs,
        raw_upstream_payload_required=True,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )


def capture_and_publish_official_calendar_evidence(
    *,
    daily_package_path: Path,
    custody_root: Path,
    captured_at: datetime,
    fetcher: OfficialCalendarHttpFetcher | None = None,
) -> ChinaAshareCalendarEvidencePackageResultV1:
    daily_package = read_china_ashare_pilot_daily_package(
        package_path=daily_package_path
    )
    plan = build_default_official_calendar_evidence_plan(
        start_date=daily_package.plan.history_start_date,
        end_date=daily_package.plan.history_end_date,
        planned_at=captured_at,
    )
    active_fetcher = fetcher or UrllibOfficialCalendarHttpFetcher()
    captured_notices = tuple(
        capture_official_calendar_notice(
            spec=spec,
            retrieved_at=captured_at,
            fetcher=active_fetcher,
        )
        for spec in plan.notice_specs
    )
    report = build_official_calendar_evidence_report_for_pilot(
        plan=plan,
        daily_package=daily_package,
        captured_notices=captured_notices,
        evaluated_at=captured_at,
    )
    return publish_china_ashare_calendar_evidence_package(
        custody_root=custody_root,
        plan=plan,
        captured_notices=captured_notices,
        report=report,
        created_at=captured_at,
    )


def build_official_calendar_evidence_report_for_pilot(
    *,
    plan: ChinaAshareOfficialCalendarEvidencePlanV1,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    captured_notices: tuple[CapturedOfficialCalendarNoticeV1, ...],
    evaluated_at: datetime,
) -> ChinaAshareOfficialCalendarEvidenceReportV1:
    if (plan.start_date, plan.end_date) != (
        daily_package.plan.history_start_date,
        daily_package.plan.history_end_date,
    ):
        raise ValueError("calendar evidence plan differs from daily package interval")
    expected_keys = tuple(
        (item.notice_year, item.exchange.value) for item in plan.notice_specs
    )
    ordered = tuple(
        sorted(
            captured_notices,
            key=lambda item: (
                item.observation.notice_year,
                item.observation.exchange.value,
            ),
        )
    )
    observed_keys = tuple(
        (item.observation.notice_year, item.observation.exchange.value)
        for item in ordered
    )
    if observed_keys != expected_keys:
        raise ValueError("captured official notices differ from the evidence plan")
    session_calendar = ExchangeCalendar(
        calendar_id=XSHG_CALENDAR_ID,
        timezone=ZoneInfo(CHINA_MARKET_TIMEZONE.key),
    )
    sessions = session_calendar.sessions_in_range(plan.start_date, plan.end_date)
    session_set = set(sessions)
    weekdays = _weekdays_in_range(plan.start_date, plan.end_date)
    library_closures = weekdays - session_set
    by_exchange: dict[ChinaAshareExchange, set[date]] = {
        ChinaAshareExchange.SSE: set(),
        ChinaAshareExchange.SZSE: set(),
    }
    for item in ordered:
        by_exchange[item.observation.exchange].update(
            value
            for value in item.observation.weekday_closure_dates
            if plan.start_date <= value <= plan.end_date
        )
    sse = by_exchange[ChinaAshareExchange.SSE]
    szse = by_exchange[ChinaAshareExchange.SZSE]
    official = sse | szse
    library_alignment = build_china_ashare_pilot_calendar_coverage(
        daily_package=daily_package,
        evaluated_at=evaluated_at,
        calendar=session_calendar,
    )
    missing_official = tuple(sorted(library_closures - official))
    missing_library = tuple(sorted(official - library_closures))
    sse_only = tuple(sorted(sse - szse))
    szse_only = tuple(sorted(szse - sse))
    notice_retained = len(ordered) == len(plan.notice_specs) and all(
        item.raw_bytes
        and hashlib.sha256(item.raw_bytes).hexdigest()
        == item.observation.raw_sha256
        for item in ordered
    )
    reconciled = all(
        (
            library_alignment.library_source_alignment_complete,
            notice_retained,
            not missing_official,
            not missing_library,
            not sse_only,
            not szse_only,
        )
    )
    reasons = {
        (
            "official_sse_szse_notices_retained"
            if notice_retained
            else "official_sse_szse_notice_retention_incomplete"
        )
    }
    if library_alignment.library_source_alignment_complete:
        reasons.add("library_and_source_state_dates_align")
    else:
        reasons.add("library_and_source_state_dates_differ")
    if reconciled:
        reasons.add("official_weekday_closures_machine_reconciled")
    else:
        reasons.add("calendar_reconciliation_failed")
    return build_official_calendar_evidence_report(
        plan_fingerprint=plan.logical_fingerprint,
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        evaluated_at=evaluated_at,
        calendar_id=XSHG_CALENDAR_ID,
        calendar_version=session_calendar.calendar_version,
        calendar_timezone=CHINA_MARKET_TIMEZONE.key,
        start_date=plan.start_date,
        end_date=plan.end_date,
        notice_count=len(ordered),
        expected_session_count=len(sessions),
        expected_sessions_fingerprint=_date_fingerprint(tuple(sessions)),
        official_weekday_closure_dates=tuple(sorted(official)),
        official_closure_fingerprint=_date_fingerprint(tuple(sorted(official))),
        library_closures_missing_from_official=missing_official,
        official_closures_missing_from_library=missing_library,
        sse_closures_missing_from_szse=sse_only,
        szse_closures_missing_from_sse=szse_only,
        library_source_alignment_complete=(
            library_alignment.library_source_alignment_complete
        ),
        official_exchange_notice_retained=notice_retained,
        calendar_reconciled=reconciled,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=tuple(sorted(reasons)),
    )


def _weekdays_in_range(start_date: date, end_date: date) -> set[date]:
    values: set[date] = set()
    cursor = start_date
    while cursor <= end_date:
        if cursor.weekday() < 5:
            values.add(cursor)
        cursor += timedelta(days=1)
    return values


def _date_fingerprint(values: tuple[date, ...]) -> str:
    payload = json.dumps(
        tuple(item.isoformat() for item in values),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
