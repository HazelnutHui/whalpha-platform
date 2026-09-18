"""Minimal official CNINFO adapter for one bounded SZSE event sample."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from tip_api.contracts.china_ashare.v1.cninfo_event_evidence import (
    ChinaAshareCninfoAnnouncementV1,
    ChinaAshareCninfoEventPlanV1,
    ChinaAshareCninfoParseStatus,
    ChinaAshareCninfoQueryV1,
    ChinaAshareCninfoRequestKind,
    build_cninfo_event_capture,
    build_cninfo_event_plan,
)


CNINFO_SECURITY_MAP_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_ANNOUNCEMENT_QUERY_URL = (
    "https://www.cninfo.com.cn/new/hisAnnouncement/query"
)
CNINFO_STATIC_DOCUMENT_BASE = "https://static.cninfo.com.cn/"


def plan_cninfo_event_sample(
    *, source_plan, minimum_request_interval_milliseconds: int = 1000
) -> ChinaAshareCninfoEventPlanV1:
    """Freeze exactly sz.000001 from the first source partition containing SZSE."""

    partition = source_plan.plan.partitions[47]
    if partition.partition_index != 47:
        raise ValueError("CNINFO sample partition differs")
    target = next(
        (item for item in partition.targets if item.source_security_id == "sz.000001"),
        None,
    )
    if target is None:
        raise ValueError("CNINFO sample target is absent")
    keyword_specs = (
        ("delisting-period", "退市整理"),
        ("relisting", "重新上市"),
        ("resume-listing", "恢复上市"),
        ("risk-warning", "风险警示"),
        ("termination", "终止上市"),
    )
    queries = [
        ChinaAshareCninfoQueryV1(
            query_id="sz-000001-security-map",
            request_kind=ChinaAshareCninfoRequestKind.SECURITY_MAP,
            maximum_response_bytes=8 * 1024 * 1024,
            maximum_attempts=1,
        )
    ]
    queries.extend(
        ChinaAshareCninfoQueryV1(
            query_id=f"sz-000001-{suffix}",
            request_kind=ChinaAshareCninfoRequestKind.ANNOUNCEMENT_QUERY,
            keyword=keyword,
            maximum_response_bytes=4 * 1024 * 1024,
            maximum_attempts=1,
        )
        for suffix, keyword in keyword_specs
    )
    return build_cninfo_event_plan(
        source_expansion_plan_fingerprint=source_plan.plan.logical_fingerprint,
        source_partition_manifest_fingerprint=partition.logical_fingerprint,
        partition_index=47,
        source_security_id="sz.000001",
        interval_start=source_plan.plan.interval_start,
        interval_end=source_plan.plan.interval_end,
        security_map_url=CNINFO_SECURITY_MAP_URL,
        announcement_query_url=CNINFO_ANNOUNCEMENT_QUERY_URL,
        queries=tuple(sorted(queries, key=lambda item: item.query_id)),
        minimum_request_interval_milliseconds=minimum_request_interval_milliseconds,
        credentials_required=False,
        outcome_read_count=0,
        as_operated_claim_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
    )


def capture_cninfo_security_map(
    *,
    plan: ChinaAshareCninfoEventPlanV1,
    query: ChinaAshareCninfoQueryV1,
    retrieved_at: datetime,
):
    if query.request_kind is not ChinaAshareCninfoRequestKind.SECURITY_MAP:
        raise ValueError("CNINFO query is not a security map")
    response = _request(
        url=plan.security_map_url,
        method="GET",
        parameters=(),
        maximum_response_bytes=query.maximum_response_bytes,
    )
    if response[0] is None:
        return _transport_blocked(
            plan=plan,
            query=query,
            requested_url=plan.security_map_url,
            method="GET",
            parameters=(),
            retrieved_at=retrieved_at,
            blocker=response[-1],
        ), None
    raw, status, content_type, final_url, boundary_blocker = response
    if boundary_blocker is not None:
        parse_status, org_id, conflicts, blocker = (
            ChinaAshareCninfoParseStatus.SCHEMA_BLOCKED,
            None,
            (),
            boundary_blocker,
        )
    else:
        parse_status, org_id, conflicts, blocker = _parse_security_map(raw)
    capture = build_cninfo_event_capture(
        plan_fingerprint=plan.logical_fingerprint,
        query_id=query.query_id,
        requested_url=plan.security_map_url,
        http_method="GET",
        request_parameters=(),
        final_url=final_url,
        retrieved_at=retrieved_at,
        http_status=status,
        content_type=content_type,
        raw_byte_size=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        parse_status=parse_status,
        resolved_org_id=org_id,
        announcements=(),
        conflict_codes=conflicts,
        blocker_code=blocker,
        attempt_count=1,
        outcome_read_count=0,
    )
    return capture, raw


def capture_cninfo_announcement_query(
    *,
    plan: ChinaAshareCninfoEventPlanV1,
    query: ChinaAshareCninfoQueryV1,
    resolved_org_id: str,
    retrieved_at: datetime,
):
    if (
        query.request_kind is not ChinaAshareCninfoRequestKind.ANNOUNCEMENT_QUERY
        or query.keyword is None
    ):
        raise ValueError("CNINFO query is not an announcement query")
    parameters = tuple(
        sorted(
            {
                "column": "szse",
                "pageNum": "1",
                "pageSize": "30",
                "plate": "sz",
                "searchkey": query.keyword,
                "seDate": (
                    f"{plan.interval_start.isoformat()}~{plan.interval_end.isoformat()}"
                ),
                "secid": "",
                "sortName": "",
                "sortType": "",
                "stock": f"000001,{resolved_org_id}",
                "tabName": "fulltext",
            }.items()
        )
    )
    response = _request(
        url=plan.announcement_query_url,
        method="POST",
        parameters=parameters,
        maximum_response_bytes=query.maximum_response_bytes,
    )
    if response[0] is None:
        return _transport_blocked(
            plan=plan,
            query=query,
            requested_url=plan.announcement_query_url,
            method="POST",
            parameters=parameters,
            retrieved_at=retrieved_at,
            blocker=response[-1],
        ), None
    raw, status, content_type, final_url, boundary_blocker = response
    if boundary_blocker is not None:
        parse_status, announcements, conflicts, blocker = (
            ChinaAshareCninfoParseStatus.SCHEMA_BLOCKED,
            (),
            (),
            boundary_blocker,
        )
    else:
        parse_status, announcements, conflicts, blocker = _parse_announcements(
            raw=raw, keyword=query.keyword
        )
    capture = build_cninfo_event_capture(
        plan_fingerprint=plan.logical_fingerprint,
        query_id=query.query_id,
        requested_url=plan.announcement_query_url,
        http_method="POST",
        request_parameters=parameters,
        final_url=final_url,
        retrieved_at=retrieved_at,
        http_status=status,
        content_type=content_type,
        raw_byte_size=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        parse_status=parse_status,
        resolved_org_id=resolved_org_id,
        announcements=announcements,
        conflict_codes=conflicts,
        blocker_code=blocker,
        attempt_count=1,
        outcome_read_count=0,
    )
    return capture, raw


def replay_cninfo_capture(
    *,
    plan: ChinaAshareCninfoEventPlanV1,
    query: ChinaAshareCninfoQueryV1,
    capture,
    raw: bytes,
):
    """Reparse exact captured bytes without mutating an immutable checkpoint."""

    if (
        capture.plan_fingerprint != plan.logical_fingerprint
        or capture.query_id != query.query_id
        or capture.raw_sha256 != hashlib.sha256(raw).hexdigest()
        or capture.raw_byte_size != len(raw)
    ):
        raise ValueError("CNINFO replay binding differs")
    if query.request_kind is ChinaAshareCninfoRequestKind.SECURITY_MAP:
        status, org_id, conflicts, blocker = _parse_security_map(raw)
        announcements = ()
    else:
        status, announcements, conflicts, blocker = _parse_announcements(
            raw=raw, keyword=query.keyword
        )
        org_id = capture.resolved_org_id
    return build_cninfo_event_capture(
        plan_fingerprint=plan.logical_fingerprint,
        query_id=query.query_id,
        requested_url=capture.requested_url,
        http_method=capture.http_method,
        request_parameters=capture.request_parameters,
        final_url=capture.final_url,
        retrieved_at=capture.retrieved_at,
        http_status=capture.http_status,
        content_type=capture.content_type,
        raw_byte_size=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        parse_status=status,
        resolved_org_id=org_id,
        announcements=announcements,
        conflict_codes=conflicts,
        blocker_code=blocker,
        attempt_count=1,
        outcome_read_count=0,
    )


def _request(
    *,
    url: str,
    method: str,
    parameters: tuple[tuple[str, str], ...],
    maximum_response_bytes: int,
):
    data = None if method == "GET" else urlencode(parameters).encode()
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.cninfo.com.cn/",
        "User-Agent": "WHAlphaResearch/1.0 official-cninfo-event",
    }
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Origin"] = "https://www.cninfo.com.cn"
    try:
        with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
            raw = response.read(maximum_response_bytes + 1)
            if len(raw) > maximum_response_bytes:
                raise ValueError("response_byte_ceiling_exceeded")
            status = int(response.status)
            content_type = str(response.headers.get("Content-Type", ""))
            final_url = str(response.geturl())
    except Exception as exc:
        return None, None, None, None, f"transport_{type(exc).__name__.lower()}"
    parsed = urlparse(final_url)
    if (
        status != 200
        or parsed.scheme != "https"
        or parsed.hostname != "www.cninfo.com.cn"
    ):
        return raw, status, content_type, final_url, "official_boundary_failed"
    return raw, status, content_type, final_url, None


def _parse_security_map(raw: bytes):
    try:
        document = json.loads(raw)
        rows = document["stockList"]
        if not isinstance(rows, list):
            raise TypeError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return _blocked_status(raw), None, (), _blocked_code(raw, "security_map_schema_differs")
    matches = [item for item in rows if str(item.get("code")) == "000001"]
    if len(matches) != 1 or not str(matches[0].get("orgId", "")).strip():
        return ChinaAshareCninfoParseStatus.SCHEMA_BLOCKED, None, (), "security_map_target_differs"
    return (
        ChinaAshareCninfoParseStatus.PARSED,
        str(matches[0]["orgId"]).strip(),
        (),
        None,
    )


def _parse_announcements(*, raw: bytes, keyword: str):
    try:
        document = json.loads(raw)
        rows = document["announcements"]
        total = int(document["totalAnnouncement"])
        if rows is None and total == 0:
            rows = []
        if not isinstance(rows, list):
            raise TypeError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _blocked_status(raw), (), (), _blocked_code(raw, "announcement_schema_differs")
    conflicts: set[str] = set()
    if total > 30:
        conflicts.add("query_result_exceeds_single_page_ceiling")
    announcements = []
    for row in rows:
        try:
            code = str(row["secCode"])
            announcement_id = str(row["announcementId"])
            title = str(row["announcementTitle"]).replace("<em>", "").replace("</em>", "").strip()
            published_at = datetime.fromtimestamp(
                int(row["announcementTime"]) / 1000, tz=UTC
            )
            path = str(row["adjunctUrl"])
        except (KeyError, TypeError, ValueError, OSError):
            return (
                ChinaAshareCninfoParseStatus.SCHEMA_BLOCKED,
                (),
                (),
                "announcement_row_schema_differs",
            )
        if code != "000001":
            conflicts.add("security_code_mismatch")
        if keyword not in title:
            conflicts.add("title_keyword_mismatch")
        document_url = (
            path
            if path.startswith("https://")
            else CNINFO_STATIC_DOCUMENT_BASE + path.lstrip("/")
        )
        announcements.append(
            ChinaAshareCninfoAnnouncementV1(
                announcement_id=announcement_id,
                source_security_id="sz.000001",
                title=title,
                published_at=published_at,
                document_url=document_url,
            )
        )
    return (
        ChinaAshareCninfoParseStatus.PARSED,
        tuple(sorted(announcements, key=lambda item: (item.published_at, item.announcement_id))),
        tuple(sorted(conflicts)),
        None,
    )


def _blocked_status(raw: bytes) -> ChinaAshareCninfoParseStatus:
    lowered = raw[:32_768].lower()
    return (
        ChinaAshareCninfoParseStatus.ANTIBOT_BLOCKED
        if b"acw_sc__v2" in lowered or b"captcha" in lowered
        else ChinaAshareCninfoParseStatus.SCHEMA_BLOCKED
    )


def _blocked_code(raw: bytes, schema_code: str) -> str:
    return (
        "cninfo_antibot_challenge"
        if _blocked_status(raw) is ChinaAshareCninfoParseStatus.ANTIBOT_BLOCKED
        else schema_code
    )


def _transport_blocked(
    *, plan, query, requested_url, method, parameters, retrieved_at, blocker
):
    return build_cninfo_event_capture(
        plan_fingerprint=plan.logical_fingerprint,
        query_id=query.query_id,
        requested_url=requested_url,
        http_method=method,
        request_parameters=parameters,
        retrieved_at=retrieved_at,
        parse_status=ChinaAshareCninfoParseStatus.TRANSPORT_BLOCKED,
        blocker_code=blocker,
        attempt_count=1,
        outcome_read_count=0,
    )
