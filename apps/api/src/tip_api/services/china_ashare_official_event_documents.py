"""Bounded second-stage capture and parsing of official event documents."""

from __future__ import annotations

import hashlib
import gzip
import re
import zlib
from datetime import UTC, date, datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from tip_api.contracts.china_ashare.v1.official_event_documents import (
    ChinaAshareOfficialDocumentParseStatus,
    ChinaAshareOfficialDocumentProvider,
    ChinaAshareOfficialDocumentSpecV1,
    ChinaAshareOfficialEventDocumentCaptureV1,
    ChinaAshareRiskWarningEventKind,
    ChinaAshareRiskWarningEventV1,
    ChinaAshareRiskWarningSubtype,
    build_official_event_document_capture,
    build_official_event_document_plan,
)
from tip_api.contracts.china_ashare.v1.official_event_evidence import (
    ChinaAshareOfficialEventCaptureV1,
    ChinaAshareOfficialEventEvidencePlanV1,
    ChinaAshareOfficialEventParseStatus,
)
from tip_api.services.china_ashare_official_event_evidence import _parse_sse_query


_SSE_DOCUMENT_HOSTS = frozenset({"static.sse.com.cn", "www.sse.com.cn"})
_CNINFO_DOCUMENT_HOSTS = frozenset({"static.cninfo.com.cn", "www.cninfo.com.cn"})
_DATE_PATTERN = re.compile(
    r"(?P<year>20\d{2})\s*年\s*(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日"
)


def plan_sse_risk_warning_documents(
    *,
    evidence_plan: ChinaAshareOfficialEventEvidencePlanV1,
    evidence_capture: ChinaAshareOfficialEventCaptureV1,
    raw_bytes: bytes,
    minimum_request_interval_milliseconds: int = 1000,
):
    """Create a new immutable document plan without altering stage-one custody."""

    query_id = "sh-600053-risk-warning"
    if evidence_capture.plan_fingerprint != evidence_plan.logical_fingerprint:
        raise ValueError("stage-one official-event binding differs")
    if evidence_capture.query_id != query_id:
        raise ValueError("SSE document plan is restricted to sh.600053")
    if evidence_capture.raw_sha256 != hashlib.sha256(raw_bytes).hexdigest():
        raise ValueError("stage-one official-event raw bytes differ")
    if evidence_capture.parse_status is not ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED:
        raise ValueError("expected immutable schema-blocked stage-one checkpoint")
    status, announcements, conflicts, blocker = _parse_sse_query(
        raw=raw_bytes,
        source_security_id="sh.600053",
        title_keyword="风险警示",
    )
    if (
        status is not ChinaAshareOfficialEventParseStatus.PARSED
        or blocker is not None
        or conflicts
        or len(announcements) != 3
    ):
        raise ValueError("stage-one SSE announcement discovery differs")
    documents = tuple(
        sorted(
            (
                ChinaAshareOfficialDocumentSpecV1(
                    document_id=item.announcement_id,
                    provider=ChinaAshareOfficialDocumentProvider.SSE,
                    source_security_id=item.source_security_id,
                    title=item.title,
                    published_on=item.disclosed_at.date(),
                    document_url=item.document_url,
                    maximum_response_bytes=16 * 1024 * 1024,
                    maximum_attempts=1,
                )
                for item in announcements
            ),
            key=lambda item: item.document_id,
        )
    )
    return build_official_event_document_plan(
        provider=ChinaAshareOfficialDocumentProvider.SSE,
        source_security_id="sh.600053",
        parent_evidence_plan_fingerprint=evidence_plan.logical_fingerprint,
        parent_query_id=query_id,
        parent_capture_fingerprint=evidence_capture.logical_fingerprint,
        parent_raw_sha256=evidence_capture.raw_sha256,
        documents=documents,
        minimum_request_interval_milliseconds=minimum_request_interval_milliseconds,
        credentials_required=False,
        outcome_read_count=0,
        as_operated_claim_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
    )


def capture_official_event_document(
    *, plan, document: ChinaAshareOfficialDocumentSpecV1, retrieved_at: datetime
) -> tuple[ChinaAshareOfficialEventDocumentCaptureV1, bytes | None, bytes | None]:
    if document.document_id not in {item.document_id for item in plan.documents}:
        raise ValueError("official document is outside the plan")
    allowed_hosts = (
        _SSE_DOCUMENT_HOSTS
        if document.provider is ChinaAshareOfficialDocumentProvider.SSE
        else _CNINFO_DOCUMENT_HOSTS
    )
    requested = urlparse(document.document_url)
    if requested.scheme != "https" or requested.hostname not in allowed_hosts:
        raise ValueError("official document source boundary differs")
    try:
        request = Request(
            document.document_url,
            headers={
                "Accept": "application/pdf,text/html,*/*",
                "Referer": (
                    "https://www.sse.com.cn/disclosure/listedinfo/announcement/"
                    if document.provider is ChinaAshareOfficialDocumentProvider.SSE
                    else "https://www.cninfo.com.cn/"
                ),
                "User-Agent": "WHAlphaResearch/1.0 official-event-document",
            },
        )
        with urlopen(request, timeout=30) as response:
            raw = response.read(document.maximum_response_bytes + 1)
            if len(raw) > document.maximum_response_bytes:
                raise ValueError("response_byte_ceiling_exceeded")
            status = int(response.status)
            content_type = str(response.headers.get("Content-Type", ""))
            final_url = str(response.geturl())
    except Exception as exc:
        capture = build_official_event_document_capture(
            plan_fingerprint=plan.logical_fingerprint,
            document_id=document.document_id,
            requested_url=document.document_url,
            retrieved_at=retrieved_at,
            parse_status=ChinaAshareOfficialDocumentParseStatus.TRANSPORT_BLOCKED,
            blocker_code=f"transport_{type(exc).__name__.lower()}",
            attempt_count=1,
            outcome_read_count=0,
        )
        return capture, None, None
    final = urlparse(final_url)
    if status != 200 or final.scheme != "https" or final.hostname not in allowed_hosts:
        parse_status = ChinaAshareOfficialDocumentParseStatus.SCHEMA_BLOCKED
        text_bytes = None
        events = ()
        conflicts = ()
        blocker = "official_document_transport_boundary_failed"
    elif not raw.startswith(b"%PDF-"):
        decoded = _decode_transport_body(raw)
        challenged = b"acw_sc__v2" in decoded.lower()
        parse_status = (
            ChinaAshareOfficialDocumentParseStatus.ANTIBOT_BLOCKED
            if challenged
            else ChinaAshareOfficialDocumentParseStatus.SCHEMA_BLOCKED
        )
        text_bytes = None
        events = ()
        conflicts = ()
        blocker = (
            "sse_antibot_cookie_challenge"
            if challenged
            else "official_document_pdf_signature_missing"
        )
    else:
        text, extraction_blocker = extract_pdf_text(raw)
        if text is None:
            parse_status = ChinaAshareOfficialDocumentParseStatus.CAPTURED_UNPARSED
            text_bytes = None
            events = ()
            conflicts = ()
            blocker = extraction_blocker
        else:
            text_bytes = text.encode("utf-8")
            event, conflicts, blocker = parse_risk_warning_document(
                document=document, text=text
            )
            if event is None:
                parse_status = ChinaAshareOfficialDocumentParseStatus.SCHEMA_BLOCKED
                events = ()
            else:
                parse_status = ChinaAshareOfficialDocumentParseStatus.PARSED
                events = (event,)
    capture = build_official_event_document_capture(
        plan_fingerprint=plan.logical_fingerprint,
        document_id=document.document_id,
        requested_url=document.document_url,
        final_url=final_url,
        retrieved_at=retrieved_at,
        http_status=status,
        content_type=content_type,
        raw_byte_size=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        text_byte_size=None if text_bytes is None else len(text_bytes),
        text_sha256=(
            None if text_bytes is None else hashlib.sha256(text_bytes).hexdigest()
        ),
        parse_status=parse_status,
        risk_warning_events=events,
        conflict_codes=conflicts,
        blocker_code=blocker,
        attempt_count=1,
        outcome_read_count=0,
    )
    return capture, raw, text_bytes


def parse_risk_warning_document(
    *, document: ChinaAshareOfficialDocumentSpecV1, text: str
) -> tuple[ChinaAshareRiskWarningEventV1 | None, tuple[str, ...], str | None]:
    normalized = re.sub(r"\s+", "", text)
    title = re.sub(r"\s+", "", document.title)
    conflicts: set[str] = set()
    if "可能被实施" in title or "可能被实施" in normalized:
        kind = ChinaAshareRiskWarningEventKind.WARNING_EXPECTED
    elif "撤销" in title:
        kind = ChinaAshareRiskWarningEventKind.WARNING_REMOVED
    elif "变更" in title:
        kind = ChinaAshareRiskWarningEventKind.WARNING_CHANGED
    elif "被实施" in title:
        kind = ChinaAshareRiskWarningEventKind.WARNING_IMPLEMENTED
    else:
        return None, (), "risk_warning_event_kind_unresolved"

    has_delisting = "退市风险警示" in normalized or "退市风险警示" in title
    has_other = "其他风险警示" in normalized or "其他风险警示" in title
    if has_delisting and has_other:
        subtype = ChinaAshareRiskWarningSubtype.COMBINED
    elif has_delisting:
        subtype = ChinaAshareRiskWarningSubtype.STAR_ST
    elif has_other:
        subtype = ChinaAshareRiskWarningSubtype.OTHER_RISK_WARNING
    elif "ST" in normalized or "ST" in title:
        subtype = ChinaAshareRiskWarningSubtype.ST
    else:
        subtype = ChinaAshareRiskWarningSubtype.UNKNOWN
        conflicts.add("risk_warning_subtype_unresolved")

    effective_from = _effective_date(normalized, kind)
    if kind is ChinaAshareRiskWarningEventKind.WARNING_EXPECTED:
        effective_from = None
    elif effective_from is None:
        return None, tuple(sorted(conflicts)), "risk_warning_effective_date_missing"
    if effective_from is not None and effective_from < document.published_on:
        conflicts.add("effective_date_precedes_publication_date")

    markers = {kind.value, subtype.value}
    if effective_from is not None:
        markers.add("effective_date_explicit")
    event = ChinaAshareRiskWarningEventV1(
        document_id=document.document_id,
        source_security_id=document.source_security_id,
        event_kind=kind,
        subtype=subtype,
        published_on=document.published_on,
        effective_from=effective_from,
        effective_to=None,
        publication_clock_time_known=False,
        evidence_markers=tuple(sorted(markers)),
    )
    return event, tuple(sorted(conflicts)), None


def validate_risk_warning_document_set(
    *, plan, captures: tuple[ChinaAshareOfficialEventDocumentCaptureV1, ...]
) -> tuple[str, ...]:
    """Validate closed plan coverage and conservative event chronology."""

    conflicts: set[str] = set()
    by_id = {item.document_id: item for item in captures}
    expected = {item.document_id for item in plan.documents}
    if set(by_id) != expected or len(by_id) != len(captures):
        conflicts.add("document_capture_set_differs")
        return tuple(sorted(conflicts))
    events = [
        event
        for capture in captures
        for event in capture.risk_warning_events
    ]
    conflicts.update(
        conflict for capture in captures for conflict in capture.conflict_codes
    )
    implementations = [
        item
        for item in events
        if item.event_kind is ChinaAshareRiskWarningEventKind.WARNING_IMPLEMENTED
    ]
    if len(implementations) > 1:
        conflicts.add("multiple_warning_implementation_events")
    for expected_event in (
        item
        for item in events
        if item.event_kind is ChinaAshareRiskWarningEventKind.WARNING_EXPECTED
    ):
        if any(
            implementation.published_on < expected_event.published_on
            for implementation in implementations
        ):
            conflicts.add("implementation_precedes_warning_notice")
    return tuple(sorted(conflicts))


def extract_pdf_text(raw: bytes) -> tuple[str | None, str | None]:
    """Extract embedded text from simple official PDFs without adding a dependency."""

    streams: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        payload = match.group(1)
        prefix = raw[max(0, match.start() - 300) : match.start()]
        if b"/FlateDecode" in prefix:
            try:
                payload = zlib.decompress(payload)
            except zlib.error:
                continue
        streams.append(payload)
    maps = [_parse_tounicode_map(item) for item in streams if b"begincmap" in item]
    maps = [item for item in maps if item]
    fragments: list[str] = []
    for stream in streams:
        if b"BT" not in stream:
            continue
        for token in re.findall(rb"<([0-9A-Fa-f]+)>\s*Tj", stream):
            fragment = _decode_pdf_hex(token, maps)
            if fragment:
                fragments.append(fragment)
        for array in re.findall(rb"\[(.*?)\]\s*TJ", stream, re.S):
            fragment = "".join(
                _decode_pdf_hex(token, maps)
                for token in re.findall(rb"<([0-9A-Fa-f]+)>", array)
            )
            if fragment:
                fragments.append(fragment)
        for literal in re.findall(rb"\(([^()]*)\)\s*Tj", stream):
            try:
                fragment = literal.decode("utf-8")
            except UnicodeDecodeError:
                fragment = literal.decode("latin-1", errors="ignore")
            if fragment:
                fragments.append(fragment)
    text = "\n".join(fragments)
    if len(text) < 20 or not any("\u4e00" <= char <= "\u9fff" for char in text):
        return None, "pdf_embedded_text_unavailable"
    return text, None


def _decode_transport_body(raw: bytes) -> bytes:
    if raw.startswith(b"\x1f\x8b"):
        try:
            return gzip.decompress(raw)
        except (gzip.BadGzipFile, EOFError, OSError):
            return raw
    return raw


def _parse_tounicode_map(stream: bytes) -> dict[bytes, str]:
    mapping: dict[bytes, str] = {}
    for source, target in re.findall(
        rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", stream
    ):
        try:
            mapping[bytes.fromhex(source.decode())] = bytes.fromhex(
                target.decode()
            ).decode("utf-16-be")
        except (ValueError, UnicodeDecodeError):
            continue
    for start, end, target in re.findall(
        rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
        stream,
    ):
        try:
            first = int(start, 16)
            last = int(end, 16)
            base = int(target, 16)
            width = len(start) // 2
            for offset, code in enumerate(range(first, last + 1)):
                mapping[code.to_bytes(width, "big")] = chr(base + offset)
        except (ValueError, OverflowError):
            continue
    return mapping


def _decode_pdf_hex(token: bytes, maps: list[dict[bytes, str]]) -> str:
    try:
        payload = bytes.fromhex(token.decode())
    except ValueError:
        return ""
    candidates = []
    for mapping in maps:
        widths = sorted({len(key) for key in mapping}, reverse=True)
        decoded = []
        index = 0
        while index < len(payload):
            matched = False
            for width in widths:
                value = mapping.get(payload[index : index + width])
                if value is not None:
                    decoded.append(value)
                    index += width
                    matched = True
                    break
            if not matched:
                index += 1
        candidates.append("".join(decoded))
    if payload.startswith((b"\xfe\xff", b"\xff\xfe")):
        try:
            candidates.append(payload.decode("utf-16"))
        except UnicodeDecodeError:
            pass
    return max(candidates, key=len, default="")


def _effective_date(
    text: str, kind: ChinaAshareRiskWarningEventKind
) -> date | None:
    if kind is ChinaAshareRiskWarningEventKind.WARNING_EXPECTED:
        return None
    action = {
        ChinaAshareRiskWarningEventKind.WARNING_IMPLEMENTED: "实施",
        ChinaAshareRiskWarningEventKind.WARNING_REMOVED: "撤销",
        ChinaAshareRiskWarningEventKind.WARNING_CHANGED: "变更",
    }[kind]
    marker = re.search(rf"{action}[^。；]{{0,15}}风险警示", text)
    if marker is None:
        return None
    candidates = tuple(_DATE_PATTERN.finditer(text[max(0, marker.start() - 80) : marker.start()]))
    if not candidates:
        return None
    parsed = candidates[-1]
    return date(
        int(parsed.group("year")),
        int(parsed.group("month")),
        int(parsed.group("day")),
    )
