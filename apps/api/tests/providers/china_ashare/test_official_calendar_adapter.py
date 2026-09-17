from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareExchange,
    ChinaAshareOfficialCalendarNoticeSpecV1,
)
from tip_api.providers.china_ashare.official_calendar_adapter import (
    OfficialCalendarHttpResponseV1,
    capture_official_calendar_notice,
)


class _Fetcher:
    def __init__(self, response: OfficialCalendarHttpResponseV1) -> None:
        self.response = response

    def fetch(self, *, url: str) -> OfficialCalendarHttpResponseV1:
        assert url == "https://www.sse.com.cn/example.html"
        return self.response


def test_official_calendar_adapter_parses_range_and_single_day() -> None:
    raw = """
    <html><head><title>关于2025年部分节假日休市安排的通知</title></head>
    <body><p>元旦：1月1日（星期三）休市。</p>
    <p>春节：1月28日（星期二）至2月4日（星期二）休市。</p></body></html>
    """.encode()
    captured = capture_official_calendar_notice(
        spec=ChinaAshareOfficialCalendarNoticeSpecV1(
            exchange=ChinaAshareExchange.SSE,
            notice_year=2025,
            source_url="https://www.sse.com.cn/example.html",
        ),
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
        fetcher=_Fetcher(
            OfficialCalendarHttpResponseV1(
                status=200,
                content_type="text/html",
                final_url="https://www.sse.com.cn/example.html",
                body=raw,
            )
        ),
    )

    assert captured.raw_bytes == raw
    assert captured.observation.weekday_closure_dates == (
        date(2025, 1, 1),
        date(2025, 1, 28),
        date(2025, 1, 29),
        date(2025, 1, 30),
        date(2025, 1, 31),
        date(2025, 2, 3),
        date(2025, 2, 4),
    )


def test_official_calendar_adapter_rejects_non_html() -> None:
    with pytest.raises(ValueError, match="not HTML"):
        capture_official_calendar_notice(
            spec=ChinaAshareOfficialCalendarNoticeSpecV1(
                exchange=ChinaAshareExchange.SSE,
                notice_year=2025,
                source_url="https://www.sse.com.cn/example.html",
            ),
            retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
            fetcher=_Fetcher(
                OfficialCalendarHttpResponseV1(
                    status=200,
                    content_type="application/json",
                    final_url="https://www.sse.com.cn/example.html",
                    body=b"{}",
                )
            ),
        )
