from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareExchange,
    ChinaAshareOfficialCalendarClosureRangeV1,
    ChinaAshareOfficialCalendarNoticeSpecV1,
    ChinaAshareOfficialCalendarNoticeV1,
    build_official_calendar_evidence_plan,
    build_official_calendar_evidence_report,
)
from tip_api.persistence.china_ashare_calendar_evidence_package import (
    publish_china_ashare_calendar_evidence_package,
    read_china_ashare_calendar_evidence_package,
)
from tip_api.providers.china_ashare.official_calendar_adapter import (
    CapturedOfficialCalendarNoticeV1,
)


def _fingerprint_dates(values: tuple[date, ...]) -> str:
    payload = json.dumps(
        tuple(item.isoformat() for item in values),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_calendar_evidence_package_exact_reread(tmp_path) -> None:
    captured_at = datetime(2026, 9, 17, tzinfo=UTC)
    specs = tuple(
        ChinaAshareOfficialCalendarNoticeSpecV1(
            exchange=exchange,
            notice_year=2025,
            source_url=(
                "https://www.sse.com.cn/2025.html"
                if exchange is ChinaAshareExchange.SSE
                else "https://www.szse.cn/2025.html"
            ),
        )
        for exchange in (ChinaAshareExchange.SSE, ChinaAshareExchange.SZSE)
    )
    plan = build_official_calendar_evidence_plan(
        planned_at=captured_at,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 3),
        notice_specs=specs,
        raw_upstream_payload_required=True,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    captured = []
    for spec in specs:
        raw = f"<title>2025年休市安排</title>{spec.exchange.value}".encode()
        observation = ChinaAshareOfficialCalendarNoticeV1(
            exchange=spec.exchange,
            notice_year=2025,
            source_url=spec.source_url,
            final_url=spec.source_url,
            retrieved_at=captured_at,
            http_status=200,
            content_type="text/html",
            raw_byte_size=len(raw),
            raw_sha256=hashlib.sha256(raw).hexdigest(),
            title="2025年休市安排",
            closure_ranges=(
                ChinaAshareOfficialCalendarClosureRangeV1(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 1),
                ),
            ),
            weekday_closure_dates=(date(2025, 1, 1),),
        )
        captured.append(
            CapturedOfficialCalendarNoticeV1(
                observation=observation,
                raw_bytes=raw,
            )
        )
    closures = (date(2025, 1, 1),)
    report = build_official_calendar_evidence_report(
        plan_fingerprint=plan.logical_fingerprint,
        daily_package_fingerprint="1" * 64,
        evaluated_at=captured_at,
        calendar_id="XSHG",
        calendar_version="test",
        calendar_timezone="Asia/Shanghai",
        start_date=plan.start_date,
        end_date=plan.end_date,
        notice_count=2,
        expected_session_count=2,
        expected_sessions_fingerprint="2" * 64,
        official_weekday_closure_dates=closures,
        official_closure_fingerprint=_fingerprint_dates(closures),
        library_closures_missing_from_official=(),
        official_closures_missing_from_library=(),
        sse_closures_missing_from_szse=(),
        szse_closures_missing_from_sse=(),
        library_source_alignment_complete=True,
        official_exchange_notice_retained=True,
        calendar_reconciled=True,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=("calendar_reconciled",),
    )
    custody = tmp_path / "china-a-share-research-pilot"
    custody.mkdir(mode=0o700)
    result = publish_china_ashare_calendar_evidence_package(
        custody_root=custody,
        plan=plan,
        captured_notices=tuple(captured),
        report=report,
        created_at=captured_at,
    )
    reread = read_china_ashare_calendar_evidence_package(
        package_path=result.package_path
    )

    assert reread.status == "exact_reread_complete"
    assert reread.report.calendar_reconciled is True
    assert reread.file_count == 6
    assert reread.total_bytes > 0
