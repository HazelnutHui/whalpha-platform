"""Explicit network adapter for official SSE/SZSE annual closure notices."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Protocol
from urllib.request import Request, urlopen

from tip_api.contracts.china_ashare.v1.calendar_evidence import (
    CALENDAR_NOTICE_PARSER_VERSION,
    ChinaAshareOfficialCalendarClosureRangeV1,
    ChinaAshareOfficialCalendarNoticeSpecV1,
    ChinaAshareOfficialCalendarNoticeV1,
)


_RANGE_PATTERN = re.compile(
    r"(?:(?P<start_year>20\d{2})年)?"
    r"(?P<start_month>\d{1,2})月(?P<start_day>\d{1,2})日"
    r"(?:（[^）]*）)?至"
    r"(?:(?P<end_year>20\d{2})年)?"
    r"(?P<end_month>\d{1,2})月(?P<end_day>\d{1,2})日"
    r"(?:（[^）]*）)?休市"
)
_SINGLE_PATTERN = re.compile(
    r"(?<!至)(?:(?P<year>20\d{2})年)?"
    r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日"
    r"(?:（[^）]*）)?休市"
)
_MAX_NOTICE_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class OfficialCalendarHttpResponseV1:
    status: int
    content_type: str
    final_url: str
    body: bytes


@dataclass(frozen=True, slots=True)
class CapturedOfficialCalendarNoticeV1:
    observation: ChinaAshareOfficialCalendarNoticeV1
    raw_bytes: bytes


class OfficialCalendarHttpFetcher(Protocol):
    def fetch(self, *, url: str) -> OfficialCalendarHttpResponseV1: ...


class UrllibOfficialCalendarHttpFetcher:
    """Small explicit fetcher; construction performs no network access."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("calendar fetch timeout is outside its safety range")
        self._timeout_seconds = timeout_seconds

    def fetch(self, *, url: str) -> OfficialCalendarHttpResponseV1:
        request = Request(
            url,
            headers={
                "User-Agent": "WHAlphaResearch/1.0 official-calendar-evidence",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self._timeout_seconds) as response:
            body = response.read(_MAX_NOTICE_BYTES + 1)
            if len(body) > _MAX_NOTICE_BYTES:
                raise ValueError("official calendar notice exceeds its byte ceiling")
            return OfficialCalendarHttpResponseV1(
                status=response.status,
                content_type=response.headers.get_content_type(),
                final_url=response.geturl(),
                body=body,
            )


def capture_official_calendar_notice(
    *,
    spec: ChinaAshareOfficialCalendarNoticeSpecV1,
    retrieved_at: datetime,
    fetcher: OfficialCalendarHttpFetcher,
) -> CapturedOfficialCalendarNoticeV1:
    """Fetch and parse one exact official notice without persisting it."""

    response = fetcher.fetch(url=spec.source_url)
    if response.status != 200:
        raise ValueError("official calendar notice did not return HTTP 200")
    if response.content_type.lower() != "text/html":
        raise ValueError("official calendar notice is not HTML")
    if not response.body or len(response.body) > _MAX_NOTICE_BYTES:
        raise ValueError("official calendar notice byte size is invalid")
    try:
        decoded = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("official calendar notice is not UTF-8") from exc
    parser = _VisibleTextParser()
    parser.feed(decoded)
    parser.close()
    title = parser.title.strip()
    compact = re.sub(r"\s+", "", "".join(parser.visible_text))
    if not compact or "休市" not in compact:
        raise ValueError("official calendar notice lacks closure text")
    ranges = _extract_closure_ranges(compact, notice_year=spec.notice_year)
    weekday_dates = _weekday_closure_dates(ranges, notice_year=spec.notice_year)
    observation = ChinaAshareOfficialCalendarNoticeV1(
        exchange=spec.exchange,
        notice_year=spec.notice_year,
        source_url=spec.source_url,
        final_url=response.final_url,
        retrieved_at=retrieved_at,
        http_status=200,
        content_type="text/html",
        raw_byte_size=len(response.body),
        raw_sha256=hashlib.sha256(response.body).hexdigest(),
        parser_version=CALENDAR_NOTICE_PARSER_VERSION,
        title=title,
        closure_ranges=ranges,
        weekday_closure_dates=weekday_dates,
    )
    return CapturedOfficialCalendarNoticeV1(
        observation=observation,
        raw_bytes=response.body,
    )


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible_text: list[str] = []
        self._ignored_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self._title_parts if part.strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.visible_text.append(data)
        if self._in_title:
            self._title_parts.append(data)


def _extract_closure_ranges(
    compact_text: str,
    *,
    notice_year: int,
) -> tuple[ChinaAshareOfficialCalendarClosureRangeV1, ...]:
    values: set[tuple[date, date]] = set()
    occupied_spans: list[tuple[int, int]] = []
    for match in _RANGE_PATTERN.finditer(compact_text):
        start = date(
            int(match.group("start_year") or notice_year),
            int(match.group("start_month")),
            int(match.group("start_day")),
        )
        end = date(
            int(match.group("end_year") or notice_year),
            int(match.group("end_month")),
            int(match.group("end_day")),
        )
        values.add((start, end))
        occupied_spans.append(match.span())
    for match in _SINGLE_PATTERN.finditer(compact_text):
        if any(start <= match.start() < end for start, end in occupied_spans):
            continue
        value = date(
            int(match.group("year") or notice_year),
            int(match.group("month")),
            int(match.group("day")),
        )
        values.add((value, value))
    if not values:
        raise ValueError("official calendar notice yielded no closure ranges")
    return tuple(
        ChinaAshareOfficialCalendarClosureRangeV1(start_date=start, end_date=end)
        for start, end in sorted(values)
    )


def _weekday_closure_dates(
    ranges: tuple[ChinaAshareOfficialCalendarClosureRangeV1, ...],
    *,
    notice_year: int,
) -> tuple[date, ...]:
    values: set[date] = set()
    for item in ranges:
        cursor = item.start_date
        while cursor <= item.end_date:
            if cursor.year == notice_year and cursor.weekday() < 5:
                values.add(cursor)
            cursor += timedelta(days=1)
    if not values:
        raise ValueError("official calendar notice yielded no weekday closures")
    return tuple(sorted(values))
