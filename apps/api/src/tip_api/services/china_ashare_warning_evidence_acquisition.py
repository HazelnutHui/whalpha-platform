"""Outcome-blind adapters for the frozen official warning acquisition batch."""

from __future__ import annotations

import gzip
import hashlib
import json
import socket
import zlib
from collections import Counter
from datetime import UTC, date, datetime, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
)
from tip_api.contracts.china_ashare.v1.official_evidence_reuse import (
    ChinaAshareWarningBatchRequestV1,
)
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import (
    ChinaAshareWarningAcquisitionCaptureV1,
    ChinaAshareWarningAcquisitionCensusV1,
    ChinaAshareWarningAcquisitionPlanV1,
    ChinaAshareWarningAcquisitionStatus,
    ChinaAshareWarningAnnouncementLocatorV1,
    build_contract,
)


SSE_QUERY_URL = "https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do"
CNINFO_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE = "https://static.cninfo.com.cn/"
CHALLENGE_MARKERS = (b"acw_sc__v2", b"document.cookie", b"enable javascript", b"captcha")
ALLOWED_FINAL_HOSTS = {
    ChinaAshareOfficialEvidenceAuthority.SSE: frozenset({"query.sse.com.cn"}),
    ChinaAshareOfficialEvidenceAuthority.CNINFO: frozenset({"www.cninfo.com.cn"}),
}


def build_warning_acquisition_plan(*, reuse_package, cninfo_route_map_capture, cninfo_route_map_raw: bytes) -> ChinaAshareWarningAcquisitionPlanV1:
    warning = reuse_package.warning_batch
    if warning.logical_fingerprint != "85335587d38619cc23653e9af1e21bbb143bd0bd0abc13d1e9cd6a61c564404c":
        raise ValueError("warning batch fingerprint differs from frozen batch")
    if reuse_package.manifest.logical_fingerprint != "a53db0767c5c37110bf6f5ec4aa4e1395193369cd49fe0c63c06205ce277f882":
        raise ValueError("reuse package fingerprint differs from frozen package")
    raw_sha = hashlib.sha256(cninfo_route_map_raw).hexdigest()
    if cninfo_route_map_capture.raw_sha256 != raw_sha:
        raise ValueError("CNINFO route map raw bytes differ")
    registered = [item for item in reuse_package.inventory.evidence if item.raw_sha256 == raw_sha and str(item.authority) == "cninfo"]
    if not registered:
        raise ValueError("CNINFO route map is absent from reuse inventory")
    route_map = parse_cninfo_route_map(cninfo_route_map_raw)
    cninfo_codes = {
        item.source_security_id.split(".", 1)[1]
        for item in warning.requests
        if item.authority is ChinaAshareOfficialEvidenceAuthority.CNINFO
    }
    missing = sorted(cninfo_codes - route_map.keys())
    if missing:
        raise ValueError("CNINFO route map lacks warning targets")
    return build_contract(
        ChinaAshareWarningAcquisitionPlanV1,
        input_reuse_package_fingerprint=reuse_package.manifest.logical_fingerprint,
        input_warning_batch_fingerprint=warning.logical_fingerprint,
        cninfo_route_map_raw_sha256=raw_sha,
        cninfo_route_map_capture_fingerprint=cninfo_route_map_capture.logical_fingerprint,
    )


def parse_cninfo_route_map(raw: bytes) -> dict[str, str]:
    try:
        rows = json.loads(raw)["stockList"]
        if not isinstance(rows, list):
            raise TypeError
        pairs = [(str(item["code"]), str(item["orgId"]).strip()) for item in rows]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        raise ValueError("CNINFO route map schema differs") from None
    if any(len(code) != 6 or not code.isdigit() or not org for code, org in pairs):
        raise ValueError("CNINFO route map row differs")
    route_map = dict(pairs)
    if len(route_map) != len(pairs):
        raise ValueError("CNINFO route map contains duplicate codes")
    return route_map


def acquire_warning_attempt(*, plan: ChinaAshareWarningAcquisitionPlanV1, batch_request: ChinaAshareWarningBatchRequestV1, attempt_number: int, cninfo_route_map: dict[str, str], retrieved_at: datetime | None = None):
    retrieved_at = retrieved_at or datetime.now(UTC)
    method, url, params = _request_spec(batch_request, cninfo_route_map)
    raw = None
    status = None
    content_type = None
    final_url = None
    transport_blocker = None
    request_body = None if method == "GET" else urlencode(params).encode()
    requested_url = url if method == "POST" else f"{url}?{urlencode(params)}"
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "WHAlphaResearch/1.0 bounded-warning-evidence",
        "Referer": "https://www.sse.com.cn/disclosure/listedinfo/announcement/" if batch_request.authority is ChinaAshareOfficialEvidenceAuthority.SSE else "https://www.cninfo.com.cn/",
    }
    if method == "POST":
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Origin"] = "https://www.cninfo.com.cn"
    try:
        with urlopen(Request(url if method == "POST" else requested_url, data=request_body, headers=headers, method=method), timeout=30) as response:
            raw = response.read(batch_request.maximum_response_bytes + 1)
            status = int(response.status)
            content_type = str(response.headers.get("Content-Type", ""))
            final_url = str(response.geturl())
    except HTTPError as exc:
        raw = exc.read(batch_request.maximum_response_bytes + 1)
        status = int(exc.code)
        content_type = str(exc.headers.get("Content-Type", ""))
        final_url = str(exc.geturl())
    except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
        transport_blocker = f"transport_{type(exc).__name__.lower()}"
    if raw is not None and len(raw) > batch_request.maximum_response_bytes:
        raw = raw[: batch_request.maximum_response_bytes]
        return _capture(
            plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
            method=method, params=params, retrieved_at=retrieved_at, raw=raw, status=status,
            content_type=content_type, final_url=final_url,
            acquisition_status=ChinaAshareWarningAcquisitionStatus.SCHEMA_BLOCKED,
            blocker="response_byte_ceiling_exceeded",
        )
    if raw is None:
        return _capture(
            plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
            method=method, params=params, retrieved_at=retrieved_at, raw=None, status=None,
            content_type=None, final_url=None,
            acquisition_status=ChinaAshareWarningAcquisitionStatus.TRANSPORT_BLOCKED,
            blocker=transport_blocker or "transport_unknown",
        )
    decoded = _decode(raw)
    lowered = decoded[:1_048_576].lower()
    marker = next((item.decode() for item in CHALLENGE_MARKERS if item in lowered), None)
    if marker:
        return _capture(
            plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
            method=method, params=params, retrieved_at=retrieved_at, raw=raw, status=status,
            content_type=content_type, final_url=final_url,
            acquisition_status=ChinaAshareWarningAcquisitionStatus.CHALLENGE_BLOCKED,
            blocker="official_challenge_page", challenge_marker=marker,
        )
    parsed = urlparse(final_url or "")
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_FINAL_HOSTS[batch_request.authority]:
        return _capture(
            plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
            method=method, params=params, retrieved_at=retrieved_at, raw=raw, status=status,
            content_type=content_type, final_url=final_url,
            acquisition_status=ChinaAshareWarningAcquisitionStatus.SEMANTIC_BLOCKED,
            blocker="official_final_url_boundary_failed",
        )
    if status != 200:
        return _capture(
            plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
            method=method, params=params, retrieved_at=retrieved_at, raw=raw, status=status,
            content_type=content_type, final_url=final_url,
            acquisition_status=ChinaAshareWarningAcquisitionStatus.HTTP_BLOCKED,
            blocker=f"http_{status}",
        )
    try:
        total, locators, semantic_blocker = (
            _parse_sse(raw=decoded, source_security_id=batch_request.source_security_id)
            if batch_request.authority is ChinaAshareOfficialEvidenceAuthority.SSE
            else _parse_cninfo(raw=decoded, source_security_id=batch_request.source_security_id)
        )
    except ValueError as exc:
        return _capture(
            plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
            method=method, params=params, retrieved_at=retrieved_at, raw=raw, status=status,
            content_type=content_type, final_url=final_url,
            acquisition_status=ChinaAshareWarningAcquisitionStatus.SCHEMA_BLOCKED,
            blocker=str(exc),
        )
    if semantic_blocker:
        acquisition_status = ChinaAshareWarningAcquisitionStatus.SEMANTIC_BLOCKED
    elif total == 0:
        acquisition_status = ChinaAshareWarningAcquisitionStatus.PARSED_ZERO_RESULTS
    else:
        acquisition_status = ChinaAshareWarningAcquisitionStatus.PARSED_PENDING_ADJUDICATION
    return _capture(
        plan=plan, unit=batch_request, attempt=attempt_number, requested_url=requested_url,
        method=method, params=params, retrieved_at=retrieved_at, raw=raw, status=status,
        content_type=content_type, final_url=final_url,
        acquisition_status=acquisition_status, blocker=semantic_blocker,
        total=total, locators=locators,
    )


def build_acquisition_census(*, plan, captures, stopped_early: bool, stop_code: str | None):
    captures = tuple(captures)
    latest = {}
    for capture in captures:
        if capture.request_id not in latest or capture.attempt_number > latest[capture.request_id].attempt_number:
            latest[capture.request_id] = capture
    terminal = {
        ChinaAshareWarningAcquisitionStatus.PARSED_PENDING_ADJUDICATION,
        ChinaAshareWarningAcquisitionStatus.PARSED_ZERO_RESULTS,
        ChinaAshareWarningAcquisitionStatus.CHALLENGE_BLOCKED,
        ChinaAshareWarningAcquisitionStatus.SCHEMA_BLOCKED,
        ChinaAshareWarningAcquisitionStatus.SEMANTIC_BLOCKED,
    }
    completed = [item for item in latest.values() if item.status in terminal or item.attempt_number == 2 or (item.status is ChinaAshareWarningAcquisitionStatus.HTTP_BLOCKED and item.http_status not in plan.retryable_http_statuses)]
    status_counts = Counter(str(item.status) for item in latest.values())
    locators = [locator for item in latest.values() for locator in item.locators]
    # Search locators are inputs to a later immutable document stage. They are
    # never adjudication-ready until official document bytes and effective
    # event fields have been captured and parsed under that separate contract.
    ready = 0
    return build_contract(
        ChinaAshareWarningAcquisitionCensusV1,
        plan_fingerprint=plan.logical_fingerprint,
        warning_batch_fingerprint=plan.input_warning_batch_fingerprint,
        capture_fingerprints=tuple(sorted(item.logical_fingerprint for item in captures)),
        completed_logical_unit_count=len(completed), http_attempt_count=len(captures),
        counts_by_status=tuple(sorted(status_counts.items())),
        announcement_locator_count=len(locators),
        observed_publication_clock_count=sum(item.publication_clock_observed for item in locators),
        adjudication_ready_unit_count=ready,
        zero_result_unit_count=status_counts.get(str(ChinaAshareWarningAcquisitionStatus.PARSED_ZERO_RESULTS), 0),
        stopped_early=stopped_early, stop_code=stop_code,
    )


def should_retry(*, plan, capture) -> bool:
    if capture.attempt_number >= plan.maximum_http_attempts_per_request:
        return False
    if capture.status is ChinaAshareWarningAcquisitionStatus.TRANSPORT_BLOCKED:
        return True
    return capture.status is ChinaAshareWarningAcquisitionStatus.HTTP_BLOCKED and capture.http_status in plan.retryable_http_statuses


def is_endpoint_stop(capture) -> bool:
    return capture.status in {
        ChinaAshareWarningAcquisitionStatus.CHALLENGE_BLOCKED,
        ChinaAshareWarningAcquisitionStatus.SCHEMA_BLOCKED,
        ChinaAshareWarningAcquisitionStatus.SEMANTIC_BLOCKED,
    }


def _request_spec(unit, route_map):
    start = unit.effective_from.isoformat()
    end = unit.effective_to.isoformat()
    code = unit.source_security_id.split(".", 1)[1]
    if unit.authority is ChinaAshareOfficialEvidenceAuthority.SSE:
        params = tuple(sorted({
            "BULLETIN_TYPE": "", "END_DATE": end, "SECURITY_CODE": code,
            "START_DATE": start, "STOCK_TYPE": "", "TITLE": "风险警示",
            "isPagination": "true", "pageHelp.cacheSize": "1", "pageHelp.pageNo": "1",
            "pageHelp.pageSize": "100",
        }.items()))
        return "GET", SSE_QUERY_URL, params
    org_id = route_map.get(code)
    if not org_id:
        raise ValueError("CNINFO route map target missing")
    params = tuple(sorted({
        "column": "szse", "pageNum": "1", "pageSize": "30", "plate": "sz",
        "searchkey": "风险警示", "seDate": f"{start}~{end}", "secid": "",
        "sortName": "", "sortType": "", "stock": f"{code},{org_id}", "tabName": "fulltext",
    }.items()))
    return "POST", CNINFO_QUERY_URL, params


def _parse_sse(*, raw: bytes, source_security_id: str):
    try:
        doc = json.loads(raw)
        rows = doc["result"]
        total = int(doc["pageHelp"]["total"])
        if not isinstance(rows, list):
            raise TypeError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise ValueError("sse_warning_query_schema_differs") from None
    # SSE counts announcement groups. A group may also contain an audit/report
    # attachment with the same bulletin ID; only ORG_FILE_TYPE=0 is the primary
    # announcement locator for this acquisition lane.
    groups = tuple(tuple(item) if isinstance(item, list) else (item,) for item in rows)
    if total != len(groups) or total > 100:
        return total, (), "sse_warning_result_pagination_incomplete"
    code = source_security_id.split(".", 1)[1]
    locators = []
    for group in groups:
        primary = tuple(
            row for row in group
            if "ORG_FILE_TYPE" not in row or int(row["ORG_FILE_TYPE"]) == 0
        )
        if len(primary) != 1:
            return total, (), "sse_warning_primary_announcement_differs"
        row = primary[0]
        try:
            if str(row["SECURITY_CODE"]) != code:
                return total, (), "sse_warning_security_binding_differs"
            relative = str(row["URL"])
            locators.append(ChinaAshareWarningAnnouncementLocatorV1(
                document_id=str(row.get("ORG_BULLETIN_ID") or hashlib.sha256(relative.encode()).hexdigest()),
                source_security_id=source_security_id,
                document_url=relative if relative.startswith("https://") else f"https://static.sse.com.cn{relative}",
                published_at=datetime.combine(date.fromisoformat(str(row["SSEDATE"])[:10]), time.min, UTC),
                publication_clock_observed=False,
            ))
        except (KeyError, TypeError, ValueError):
            raise ValueError("sse_warning_announcement_row_differs") from None
    return total, tuple(sorted(locators, key=lambda item: (item.published_at, item.document_id))), None


def _parse_cninfo(*, raw: bytes, source_security_id: str):
    try:
        doc = json.loads(raw)
        total = int(doc["totalAnnouncement"])
        rows = doc["announcements"]
        if rows is None and total == 0:
            rows = []
        if not isinstance(rows, list):
            raise TypeError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise ValueError("cninfo_warning_query_schema_differs") from None
    if total != len(rows) or total > 30:
        return total, (), "cninfo_warning_result_pagination_incomplete"
    code = source_security_id.split(".", 1)[1]
    locators = []
    for row in rows:
        try:
            if str(row["secCode"]) != code:
                return total, (), "cninfo_warning_security_binding_differs"
            path = str(row["adjunctUrl"])
            locators.append(ChinaAshareWarningAnnouncementLocatorV1(
                document_id=str(row["announcementId"]), source_security_id=source_security_id,
                document_url=path if path.startswith("https://") else CNINFO_STATIC_BASE + path.lstrip("/"),
                published_at=datetime.fromtimestamp(int(row["announcementTime"]) / 1000, tz=UTC),
                publication_clock_observed=True,
            ))
        except (KeyError, TypeError, ValueError, OSError):
            raise ValueError("cninfo_warning_announcement_row_differs") from None
    return total, tuple(sorted(locators, key=lambda item: (item.published_at, item.document_id))), None


def _capture(*, plan, unit, attempt, requested_url, method, params, retrieved_at, raw, status, content_type, final_url, acquisition_status, blocker=None, challenge_marker=None, total=None, locators=()):
    return build_contract(
        ChinaAshareWarningAcquisitionCaptureV1,
        plan_fingerprint=plan.logical_fingerprint,
        warning_batch_fingerprint=plan.input_warning_batch_fingerprint,
        request_id=unit.request_id, stable_subject_id=unit.stable_subject_id,
        source_security_id=unit.source_security_id, authority=unit.authority,
        attempt_number=attempt, requested_url=requested_url, http_method=method,
        request_parameters=params, retrieved_at=retrieved_at,
        final_url=final_url, http_status=status, content_type=content_type,
        raw_byte_size=None if raw is None else len(raw),
        raw_sha256=None if raw is None else hashlib.sha256(raw).hexdigest(),
        status=acquisition_status, blocker_code=blocker,
        detected_challenge_marker=challenge_marker, result_total=total,
        locators=locators,
    ), raw


def _decode(raw: bytes) -> bytes:
    if raw.startswith(b"\x1f\x8b"):
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    try:
        return zlib.decompress(raw)
    except zlib.error:
        return raw
