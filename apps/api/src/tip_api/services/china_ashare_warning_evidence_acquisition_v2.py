"""Pagination-aware planning, capture, and deterministic merge for warning evidence."""

from __future__ import annotations

import hashlib
import json
import math
import gzip
import socket
import zlib
from collections import defaultdict
from datetime import UTC, date, datetime, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import ChinaAshareOfficialEvidenceAuthority
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import ChinaAshareWarningAnnouncementLocatorV1
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition_v2 import (
    ChinaAshareWarningAcquisitionCensusV2,
    ChinaAshareWarningAcquisitionPlanV2,
    ChinaAshareWarningPageCaptureV2,
    ChinaAshareWarningPageStatus,
    ChinaAshareWarningV2UnitV1,
    build_contract,
    capture_set_fingerprint,
)
from tip_api.services.china_ashare_warning_evidence_acquisition import (
    ALLOWED_FINAL_HOSTS,
    CHALLENGE_MARKERS,
    CNINFO_QUERY_URL,
    CNINFO_STATIC_BASE,
    SSE_QUERY_URL,
    _decode,
)


def build_v2_plan(*, reuse_package, v1_plan, v1_census, v1_captures, v1_raw_by_capture_fingerprint, cninfo_route_map_raw_sha256: str):
    if reuse_package.manifest.logical_fingerprint != "a53db0767c5c37110bf6f5ec4aa4e1395193369cd49fe0c63c06205ce277f882":
        raise ValueError("warning V2 reuse package differs")
    if reuse_package.warning_batch.logical_fingerprint != "85335587d38619cc23653e9af1e21bbb143bd0bd0abc13d1e9cd6a61c564404c":
        raise ValueError("warning V2 batch differs")
    if v1_census.logical_fingerprint != "08ac1dfd13a33dc00fef293c5b4c2ee6f7a6750e98fc3e8aeb3ce4137a5838ca":
        raise ValueError("warning V2 V1 census differs")
    if len(v1_captures) != 39 or v1_census.http_attempt_count != 39:
        raise ValueError("warning V2 V1 attempts differ")
    latest = {}
    for capture in v1_captures:
        if capture.request_id not in latest or capture.attempt_number > latest[capture.request_id].attempt_number:
            latest[capture.request_id] = capture
    if len(latest) != 38:
        raise ValueError("warning V2 V1 logical units differ")
    units = []
    for request in reuse_package.warning_batch.requests:
        capture = latest.get(request.request_id)
        values = dict(
            ordinal=request.ordinal, request_id=request.request_id,
            source_security_id=request.source_security_id,
            stable_subject_id=request.stable_subject_id, authority=request.authority,
            page_size=100 if request.authority is ChinaAshareOfficialEvidenceAuthority.SSE else 30,
            maximum_pages=2 if request.authority is ChinaAshareOfficialEvidenceAuthority.SSE else 4,
        )
        if capture is not None:
            raw = v1_raw_by_capture_fingerprint.get(capture.logical_fingerprint)
            if raw is None or hashlib.sha256(raw).hexdigest() != capture.raw_sha256:
                raise ValueError("warning V2 imported raw differs")
            total, locators = parse_page(
                authority=request.authority, raw=_decode(raw),
                source_security_id=request.source_security_id,
            )
            pages = max(1, math.ceil(total / values["page_size"]))
            if pages > values["maximum_pages"]:
                raise ValueError("warning V2 imported page count exceeds limit")
            values.update(
                imported_page1_capture_fingerprint=capture.logical_fingerprint,
                imported_page1_raw_sha256=capture.raw_sha256,
                imported_page1_total=total,
                imported_page1_locator_count=len(locators), required_page_count=pages,
            )
        units.append(ChinaAshareWarningV2UnitV1(**values))
    theoretical_maximum_new_pages = sum(
        item.maximum_pages if item.required_page_count is None else item.required_page_count - 1
        for item in units
    )
    if theoretical_maximum_new_pages != 1405:
        raise ValueError("warning V2 continuation page budget differs")
    fingerprints = tuple(item.logical_fingerprint for item in v1_captures)
    return build_contract(
        ChinaAshareWarningAcquisitionPlanV2,
        input_reuse_package_fingerprint=reuse_package.manifest.logical_fingerprint,
        input_warning_batch_fingerprint=reuse_package.warning_batch.logical_fingerprint,
        input_v1_plan_fingerprint=v1_plan.logical_fingerprint,
        input_v1_partial_census_fingerprint=v1_census.logical_fingerprint,
        input_v1_capture_set_fingerprint=capture_set_fingerprint(fingerprints),
        cninfo_route_map_raw_sha256=cninfo_route_map_raw_sha256,
        units=tuple(units),
    )


def parse_page(*, authority, raw: bytes, source_security_id: str):
    if authority is ChinaAshareOfficialEvidenceAuthority.SSE:
        return _parse_sse_page(raw=raw, source_security_id=source_security_id)
    return _parse_cninfo_page(raw=raw, source_security_id=source_security_id)


def validate_and_merge_pages(*, unit, pages: tuple[tuple[int, int, tuple[ChinaAshareWarningAnnouncementLocatorV1, ...]], ...]):
    if not pages or tuple(item[0] for item in pages) != tuple(range(1, len(pages) + 1)):
        return (), "page_sequence_differs"
    total = pages[0][1]
    required = max(1, math.ceil(total / unit.page_size))
    if required > unit.maximum_pages:
        return (), "maximum_pages_exceeded"
    if len(pages) > required:
        return (), "unexpected_extra_page"
    seen = {}
    for page_number, reported_total, locators in pages:
        if reported_total != total:
            return (), "total_drift"
        if total > 0 and page_number <= required and not locators:
            return (), "empty_page_before_completion"
        for locator in locators:
            key = locator.document_id
            existing = seen.get(key)
            if existing is not None and existing != locator:
                return (), "duplicate_document_conflict"
            seen[key] = locator
    merged = tuple(sorted(seen.values(), key=lambda item: (item.published_at, item.document_id)))
    if len(pages) == required and len(merged) != total:
        return (), "deduplicated_total_differs"
    return merged, None


def build_v2_census(*, plan, imported_pages, new_captures, stopped_early, stop_code):
    by_request = defaultdict(list)
    for request_id, total, locators in imported_pages:
        by_request[request_id].append((1, total, locators))
    latest_page_attempt = {}
    for capture in new_captures:
        key = (capture.request_id, capture.page_number)
        if key not in latest_page_attempt or capture.attempt_number > latest_page_attempt[key].attempt_number:
            latest_page_attempt[key] = capture
    for capture in latest_page_attempt.values():
        if capture.status is ChinaAshareWarningPageStatus.PARSED:
            by_request[capture.request_id].append((capture.page_number, capture.reported_total, capture.locators))
    completed = 0
    merged_all = []
    observed = 0
    unit_by_id = {item.request_id: item for item in plan.units}
    for request_id, values in by_request.items():
        merged, blocker = validate_and_merge_pages(unit=unit_by_id[request_id], pages=tuple(sorted(values)))
        required = max(1, math.ceil(values[0][1] / unit_by_id[request_id].page_size))
        if blocker is None and len(values) == required:
            completed += 1
            merged_all.extend(merged)
            observed += sum(item.publication_clock_observed for item in merged)
    unique = {(item.document_id, item.source_security_id): item for item in merged_all}
    return build_contract(
        ChinaAshareWarningAcquisitionCensusV2,
        plan_fingerprint=plan.logical_fingerprint,
        completed_unit_count=completed,
        new_attempt_count=len(new_captures),
        total_attempt_count=plan.imported_http_attempt_count + len(new_captures),
        new_page_request_count=len({(item.request_id, item.page_number) for item in new_captures}),
        deduplicated_locator_count=len(unique), observed_publication_clock_count=observed,
        stopped_early=stopped_early, stop_code=stop_code,
    )


def request_parameters(*, unit, page_number: int, route_map: dict[str, str], interval_start: date, interval_end: date):
    if page_number < 1 or page_number > unit.maximum_pages:
        raise ValueError("warning V2 page number exceeds limit")
    code = unit.source_security_id.split(".", 1)[1]
    if unit.authority is ChinaAshareOfficialEvidenceAuthority.SSE:
        return "GET", SSE_QUERY_URL, tuple(sorted({
            "BULLETIN_TYPE": "", "END_DATE": interval_end.isoformat(), "SECURITY_CODE": code,
            "START_DATE": interval_start.isoformat(), "STOCK_TYPE": "", "TITLE": "风险警示",
            "isPagination": "true", "pageHelp.cacheSize": "1", "pageHelp.pageNo": str(page_number),
            "pageHelp.pageSize": str(unit.page_size),
        }.items()))
    org = route_map.get(code)
    if not org:
        raise ValueError("warning V2 CNINFO route missing")
    return "POST", CNINFO_QUERY_URL, tuple(sorted({
        "column": "szse", "pageNum": str(page_number), "pageSize": str(unit.page_size),
        "plate": "sz", "searchkey": "风险警示",
        "seDate": f"{interval_start.isoformat()}~{interval_end.isoformat()}",
        "secid": "", "sortName": "", "sortType": "", "stock": f"{code},{org}",
        "tabName": "fulltext",
    }.items()))


def acquire_v2_page(*, plan, unit, page_number, attempt_number, route_map, interval_start, interval_end, expected_total=None, retrieved_at=None):
    retrieved_at = retrieved_at or datetime.now(UTC)
    method, url, params = request_parameters(
        unit=unit, page_number=page_number, route_map=route_map,
        interval_start=interval_start, interval_end=interval_end,
    )
    body = None if method == "GET" else urlencode(params).encode()
    requested_url = url if method == "POST" else f"{url}?{urlencode(params)}"
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "WHAlphaResearch/1.0 bounded-warning-evidence-v2",
        "Referer": "https://www.sse.com.cn/disclosure/listedinfo/announcement/" if unit.authority is ChinaAshareOfficialEvidenceAuthority.SSE else "https://www.cninfo.com.cn/",
    }
    if method == "POST":
        headers.update({"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": "https://www.cninfo.com.cn"})
    raw = None; status = None; content_type = None; final_url = None; blocker = None
    try:
        with urlopen(Request(url if method == "POST" else requested_url, data=body, headers=headers, method=method), timeout=30) as response:
            raw = response.read(16 * 1024 * 1024 + 1); status = int(response.status)
            content_type = str(response.headers.get("Content-Type", "")); final_url = str(response.geturl())
    except HTTPError as exc:
        raw = exc.read(16 * 1024 * 1024 + 1); status = int(exc.code)
        content_type = str(exc.headers.get("Content-Type", "")); final_url = str(exc.geturl())
    except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
        blocker = f"transport_{type(exc).__name__.lower()}"
    if raw is None:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, None, None, None, None, ChinaAshareWarningPageStatus.TRANSPORT_BLOCKED, blocker or "transport_unknown")
    if len(raw) > 16 * 1024 * 1024:
        raw = raw[:16 * 1024 * 1024]
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.SCHEMA_BLOCKED, "response_byte_ceiling_exceeded")
    decoded = _decode(raw); lowered = decoded[:1_048_576].lower()
    marker = next((item.decode() for item in CHALLENGE_MARKERS if item in lowered), None)
    if marker:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.CHALLENGE_BLOCKED, "official_challenge_page", challenge_marker=marker)
    parsed_url = urlparse(final_url or "")
    if parsed_url.scheme != "https" or parsed_url.hostname not in ALLOWED_FINAL_HOSTS[unit.authority]:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.SCHEMA_BLOCKED, "official_final_url_boundary_failed")
    if status != 200:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.HTTP_BLOCKED, f"http_{status}")
    try:
        total, locators = parse_page(authority=unit.authority, raw=decoded, source_security_id=unit.source_security_id)
    except ValueError as exc:
        code = str(exc)
        capture_status = ChinaAshareWarningPageStatus.SECURITY_BINDING_BLOCKED if "security_binding" in code else ChinaAshareWarningPageStatus.SCHEMA_BLOCKED
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, capture_status, code)
    required = max(1, math.ceil(total / unit.page_size))
    if required > unit.maximum_pages:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.MAX_PAGES_BLOCKED, "maximum_pages_exceeded", total=total, required=required)
    if expected_total is not None and total != expected_total:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.TOTAL_DRIFT_BLOCKED, "total_drift", total=total, required=required)
    if total > 0 and page_number <= required and not locators:
        return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.EMPTY_PAGE_BLOCKED, "empty_page_before_completion", total=total, required=required)
    return _v2_capture(plan, unit, page_number, attempt_number, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, ChinaAshareWarningPageStatus.PARSED, None, total=total, required=required, locators=locators)


def should_retry_v2(*, plan, capture):
    if capture.attempt_number >= 2: return False
    if capture.status is ChinaAshareWarningPageStatus.TRANSPORT_BLOCKED: return True
    return capture.status is ChinaAshareWarningPageStatus.HTTP_BLOCKED and capture.http_status in plan.retryable_http_statuses


def _v2_capture(plan, unit, page, attempt, requested_url, method, params, retrieved_at, raw, http_status, content_type, final_url, status, blocker, *, challenge_marker=None, total=None, required=None, locators=()):
    return build_contract(
        ChinaAshareWarningPageCaptureV2,
        plan_fingerprint=plan.logical_fingerprint, request_id=unit.request_id,
        source_security_id=unit.source_security_id, authority=unit.authority,
        page_number=page, page_size=unit.page_size, attempt_number=attempt,
        requested_url=requested_url, http_method=method, request_parameters=params,
        retrieved_at=retrieved_at, final_url=final_url, http_status=http_status,
        content_type=content_type, raw_byte_size=None if raw is None else len(raw),
        raw_sha256=None if raw is None else hashlib.sha256(raw).hexdigest(),
        status=status, blocker_code=blocker, detected_challenge_marker=challenge_marker,
        reported_total=total, required_page_count=required, locators=locators,
    ), raw


def _parse_sse_page(*, raw, source_security_id):
    try:
        doc = json.loads(raw); rows = doc["result"]; total = int(doc["pageHelp"]["total"])
        if not isinstance(rows, list): raise TypeError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise ValueError("sse_page_schema_differs") from None
    groups = tuple(tuple(item) if isinstance(item, list) else (item,) for item in rows)
    locators = []
    code = source_security_id.split(".", 1)[1]
    for group in groups:
        try:
            primary = tuple(row for row in group if "ORG_FILE_TYPE" not in row or int(row["ORG_FILE_TYPE"]) == 0)
            if len(primary) != 1: raise ValueError
            row = primary[0]
            if str(row["SECURITY_CODE"]) != code: raise RuntimeError
            relative = str(row["URL"])
            locators.append(ChinaAshareWarningAnnouncementLocatorV1(
                document_id=str(row.get("ORG_BULLETIN_ID") or hashlib.sha256(relative.encode()).hexdigest()),
                source_security_id=source_security_id,
                document_url=relative if relative.startswith("https://") else f"https://static.sse.com.cn{relative}",
                published_at=datetime.combine(date.fromisoformat(str(row["SSEDATE"])[:10]), time.min, UTC),
                publication_clock_observed=False,
            ))
        except RuntimeError:
            raise ValueError("sse_page_security_binding_differs") from None
        except (KeyError, TypeError, ValueError):
            raise ValueError("sse_page_primary_announcement_differs") from None
    return total, tuple(sorted(locators, key=lambda item: (item.published_at, item.document_id)))


def _parse_cninfo_page(*, raw, source_security_id):
    try:
        doc = json.loads(raw); total = int(doc["totalAnnouncement"]); rows = doc["announcements"]
        if rows is None and total == 0: rows = []
        if not isinstance(rows, list): raise TypeError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise ValueError("cninfo_page_schema_differs") from None
    locators = []
    code = source_security_id.split(".", 1)[1]
    for row in rows:
        try:
            if str(row["secCode"]) != code: raise RuntimeError
            path = str(row["adjunctUrl"])
            locators.append(ChinaAshareWarningAnnouncementLocatorV1(
                document_id=str(row["announcementId"]), source_security_id=source_security_id,
                document_url=path if path.startswith("https://") else CNINFO_STATIC_BASE + path.lstrip("/"),
                published_at=datetime.fromtimestamp(int(row["announcementTime"]) / 1000, tz=UTC),
                publication_clock_observed=True,
            ))
        except RuntimeError:
            raise ValueError("cninfo_page_security_binding_differs") from None
        except (KeyError, TypeError, ValueError, OSError):
            raise ValueError("cninfo_page_row_differs") from None
    return total, tuple(sorted(locators, key=lambda item: (item.published_at, item.document_id)))
