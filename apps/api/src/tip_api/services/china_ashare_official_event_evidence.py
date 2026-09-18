"""Plan and capture bounded partition-0 SSE official-event evidence."""

from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, date, datetime, time
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from tip_api.contracts.china_ashare.v1.official_event_evidence import (
    ChinaAshareOfficialEventAnnouncementV1,
    ChinaAshareOfficialEventEvidencePlanV1,
    ChinaAshareOfficialEventFamily,
    ChinaAshareOfficialEventParseStatus,
    ChinaAshareOfficialEventQueryV1,
    build_official_event_capture,
    build_official_event_evidence_plan,
)


SSE_ANNOUNCEMENT_QUERY_URL = (
    "https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do"
)
SSE_LEGACY_TRADING_RULE_URL = (
    "https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/"
    "10785127/files/b39b8db2daa74eac916d8b3d6907af51.docx"
)


def plan_partition0_official_event_evidence(
    *, source_plan, source_partition, minimum_request_interval_milliseconds: int = 1000
) -> ChinaAshareOfficialEventEvidencePlanV1:
    if source_partition.partition.partition_index != 0:
        raise ValueError("official-event evidence is restricted to partition 0")
    targets = tuple(
        item.source_security_id for item in source_partition.partition.targets
    )
    if len(targets) != 50 or any(not item.startswith("sh.") for item in targets):
        raise ValueError("partition-0 official-event target scope differs")
    keyword_specs = (
        ("risk-warning", ChinaAshareOfficialEventFamily.RISK_WARNING, "风险警示"),
        (
            "relisting",
            ChinaAshareOfficialEventFamily.RELISTING_OR_RESUMPTION,
            "重新上市",
        ),
        (
            "resume-listing",
            ChinaAshareOfficialEventFamily.RELISTING_OR_RESUMPTION,
            "恢复上市",
        ),
        (
            "termination",
            ChinaAshareOfficialEventFamily.TERMINATION_OR_DELISTING_PERIOD,
            "终止上市",
        ),
        (
            "delisting-period",
            ChinaAshareOfficialEventFamily.TERMINATION_OR_DELISTING_PERIOD,
            "退市整理",
        ),
    )
    queries = []
    for source_security_id in targets:
        code = source_security_id.split(".", 1)[1]
        for suffix, family, keyword in keyword_specs:
            params = tuple(
                sorted(
                    {
                        "BULLETIN_TYPE": "",
                        "END_DATE": source_plan.plan.interval_end.isoformat(),
                        "SECURITY_CODE": code,
                        "START_DATE": source_plan.plan.interval_start.isoformat(),
                        "STOCK_TYPE": "",
                        "TITLE": keyword,
                        "isPagination": "true",
                        "pageHelp.cacheSize": "1",
                        "pageHelp.pageNo": "1",
                        "pageHelp.pageSize": "100",
                    }.items()
                )
            )
            queries.append(
                ChinaAshareOfficialEventQueryV1(
                    query_id=f"{source_security_id.replace('.', '-')}-{suffix}",
                    event_family=family,
                    source_security_id=source_security_id,
                    source_url=SSE_ANNOUNCEMENT_QUERY_URL,
                    request_parameters=params,
                    title_keyword=keyword,
                    maximum_response_bytes=4 * 1024 * 1024,
                    maximum_attempts=1,
                )
            )
    queries.append(
        ChinaAshareOfficialEventQueryV1(
            query_id="sse-main-legacy-trading-rule-2020",
            event_family=ChinaAshareOfficialEventFamily.LEGACY_IPO_RULE,
            source_url=SSE_LEGACY_TRADING_RULE_URL,
            request_parameters=(),
            maximum_response_bytes=16 * 1024 * 1024,
            maximum_attempts=1,
        )
    )
    return build_official_event_evidence_plan(
        source_expansion_plan_fingerprint=source_plan.plan.logical_fingerprint,
        source_partition_manifest_fingerprint=(
            source_partition.manifest.logical_fingerprint
        ),
        partition_index=0,
        interval_start=source_plan.plan.interval_start,
        interval_end=source_plan.plan.interval_end,
        target_source_security_ids=targets,
        queries=tuple(sorted(queries, key=lambda item: item.query_id)),
        minimum_request_interval_milliseconds=(
            minimum_request_interval_milliseconds
        ),
        credentials_required=False,
        aggregate_sources_authorized=False,
        outcome_read_count=0,
        as_operated_claim_authorized=False,
        research_backtest_authorized=False,
    )


def capture_official_event_query(*, plan, query, retrieved_at: datetime):
    if query.query_id not in {item.query_id for item in plan.queries}:
        raise ValueError("official-event query is outside the plan")
    requested_url = query.source_url
    if query.request_parameters:
        requested_url = f"{requested_url}?{urlencode(query.request_parameters)}"
    try:
        request = Request(
            requested_url,
            headers={
                "Accept": "application/json,application/vnd.openxmlformats-officedocument.wordprocessingml.document,*/*",
                "Referer": "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
                "User-Agent": "WHAlphaResearch/1.0 official-event-evidence",
            },
        )
        with urlopen(request, timeout=30) as response:
            raw = response.read(query.maximum_response_bytes + 1)
            if len(raw) > query.maximum_response_bytes:
                raise ValueError("response_byte_ceiling_exceeded")
            status = int(response.status)
            content_type = str(response.headers.get("Content-Type", ""))
            final_url = str(response.geturl())
    except Exception as exc:
        code = type(exc).__name__.lower()
        return (
            build_official_event_capture(
                plan_fingerprint=plan.logical_fingerprint,
                query_id=query.query_id,
                requested_url=requested_url,
                retrieved_at=retrieved_at,
                parse_status=ChinaAshareOfficialEventParseStatus.TRANSPORT_BLOCKED,
                blocker_code=f"transport_{code}",
                attempt_count=1,
                outcome_read_count=0,
            ),
            None,
        )
    parsed = urlparse(final_url)
    if status != 200 or parsed.scheme != "https" or parsed.hostname not in {
        "query.sse.com.cn",
        "www.sse.com.cn",
        "static.sse.com.cn",
    }:
        parse_status = ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED
        blocker = "official_transport_boundary_failed"
        announcements = ()
        conflicts = ()
    elif query.event_family is ChinaAshareOfficialEventFamily.LEGACY_IPO_RULE:
        parse_status, blocker = _parse_legacy_rule_docx(raw)
        announcements = ()
        conflicts = ()
    else:
        parse_status, announcements, conflicts, blocker = _parse_sse_query(
            raw=raw,
            source_security_id=query.source_security_id,
            title_keyword=query.title_keyword,
        )
    capture = build_official_event_capture(
        plan_fingerprint=plan.logical_fingerprint,
        query_id=query.query_id,
        requested_url=requested_url,
        final_url=final_url,
        retrieved_at=retrieved_at,
        http_status=status,
        content_type=content_type,
        raw_byte_size=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        parse_status=parse_status,
        announcements=announcements,
        conflict_codes=conflicts,
        blocker_code=blocker,
        attempt_count=1,
        outcome_read_count=0,
    )
    return capture, raw


def _parse_legacy_rule_docx(raw: bytes):
    if not raw.startswith(b"PK"):
        return ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED, "legacy_rule_docx_signature_missing"
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        text = "".join(root.itertext())
    except (BadZipFile, KeyError, ElementTree.ParseError):
        return ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED, "legacy_rule_docx_schema_differs"
    required = {
        "legacy_main_daily_limit_10_percent": "涨跌幅比例为10%",
        "legacy_main_ipo_first_session_no_limit": "首次公开发行上市的股票",
        "legacy_resume_listing_first_session_no_limit": "暂停上市后恢复上市的股票",
        "legacy_relisting_first_session_no_limit": "退市后重新上市的股票",
        "legacy_special_stage_first_session_only": "首个交易日无价格涨跌幅限制",
    }
    missing = tuple(code for code, phrase in required.items() if phrase not in text)
    if missing:
        return ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED, "legacy_rule_required_clause_missing"
    return ChinaAshareOfficialEventParseStatus.PARSED, None


def _parse_sse_query(*, raw: bytes, source_security_id: str | None, title_keyword: str | None):
    try:
        document = json.loads(raw)
        rows = document["result"]
        total = int(document["pageHelp"]["total"])
        if not isinstance(rows, list):
            raise TypeError
        if rows and all(isinstance(item, list) for item in rows):
            rows = [nested for group in rows for nested in group]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED, (), (), "sse_query_schema_differs"
    conflicts = set()
    if total > 100:
        conflicts.add("query_result_exceeds_single_page_ceiling")
    announcements = []
    expected_code = None if source_security_id is None else source_security_id.split(".", 1)[1]
    for row in rows:
        try:
            code = str(row["SECURITY_CODE"])
            title = str(row["TITLE"]).strip()
            disclosed = datetime.combine(
                date.fromisoformat(str(row["SSEDATE"])[:10]), time.min, UTC
            )
            relative_url = str(row["URL"])
            announcement_id = str(
                row.get("ORG_BULLETIN_ID")
                or hashlib.sha256(relative_url.encode()).hexdigest()
            )
        except (KeyError, TypeError, ValueError):
            return ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED, (), (), "sse_announcement_row_schema_differs"
        if code != expected_code:
            conflicts.add("security_code_mismatch")
        if title_keyword is not None and title_keyword not in title:
            conflicts.add("title_keyword_mismatch")
        document_url = relative_url if relative_url.startswith("https://") else f"https://static.sse.com.cn{relative_url}"
        announcements.append(
            ChinaAshareOfficialEventAnnouncementV1(
                announcement_id=announcement_id,
                source_security_id=f"sh.{code}",
                title=title,
                disclosed_at=disclosed,
                document_url=document_url,
            )
        )
    return (
        ChinaAshareOfficialEventParseStatus.PARSED,
        tuple(sorted(announcements, key=lambda item: (item.disclosed_at, item.announcement_id))),
        tuple(sorted(conflicts)),
        None,
    )
