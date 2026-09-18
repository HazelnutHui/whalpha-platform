"""Restartable execution CLI for pagination-aware warning acquisition V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path

from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition_v2 import ChinaAshareWarningPageStatus
from tip_api.persistence.china_ashare_cninfo_event_evidence import read_cninfo_event_capture, read_cninfo_event_plan
from tip_api.persistence.china_ashare_official_evidence_reuse import read_china_ashare_official_evidence_reuse_package
from tip_api.persistence.china_ashare_warning_evidence_acquisition import (
    read_all_warning_acquisition_captures, read_warning_acquisition_capture,
    read_warning_acquisition_census, read_warning_acquisition_plan,
)
from tip_api.persistence.china_ashare_warning_evidence_acquisition_v2 import (
    publish_v2_capture, publish_v2_census, publish_v2_plan, read_all_v2_captures,
    read_v2_capture, read_v2_census,
)
from tip_api.services.china_ashare_warning_evidence_acquisition import parse_cninfo_route_map, _decode
from tip_api.services.china_ashare_warning_evidence_acquisition_v2 import (
    acquire_v2_page, build_v2_census, build_v2_plan, parse_page,
    should_retry_v2, validate_and_merge_pages,
)


TERMINAL = {
    ChinaAshareWarningPageStatus.CHALLENGE_BLOCKED,
    ChinaAshareWarningPageStatus.SCHEMA_BLOCKED,
    ChinaAshareWarningPageStatus.TOTAL_DRIFT_BLOCKED,
    ChinaAshareWarningPageStatus.EMPTY_PAGE_BLOCKED,
    ChinaAshareWarningPageStatus.DUPLICATE_CONFLICT_BLOCKED,
    ChinaAshareWarningPageStatus.MAX_PAGES_BLOCKED,
    ChinaAshareWarningPageStatus.SECURITY_BINDING_BLOCKED,
}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-package", type=Path, required=True)
    parser.add_argument("--v1-plan-root", type=Path, required=True)
    parser.add_argument("--v1-census-fingerprint", required=True)
    parser.add_argument("--cninfo-route-map-plan-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    args = parser.parse_args(argv)

    reuse = read_china_ashare_official_evidence_reuse_package(package_path=args.reuse_package)
    v1plan = read_warning_acquisition_plan(plan_root=args.v1_plan_root)
    v1census = read_warning_acquisition_census(plan_root=args.v1_plan_root, census_fingerprint=args.v1_census_fingerprint)
    v1captures = read_all_warning_acquisition_captures(plan_root=args.v1_plan_root)
    v1raws = {}; raw_by_request = {}
    latest_v1 = {}
    for capture in v1captures:
        _, raw = read_warning_acquisition_capture(plan_root=args.v1_plan_root, request_id=capture.request_id, attempt_number=capture.attempt_number)
        if raw is not None: v1raws[capture.logical_fingerprint] = raw
        if capture.request_id not in latest_v1 or capture.attempt_number > latest_v1[capture.request_id].attempt_number:
            latest_v1[capture.request_id] = capture
            raw_by_request[capture.request_id] = raw
    cnplan = read_cninfo_event_plan(plan_root=args.cninfo_route_map_plan_root)
    cnquery = next(item for item in cnplan.queries if item.request_kind.value == "security_map")
    cncapture, cnraw = read_cninfo_event_capture(plan_root=args.cninfo_route_map_plan_root, query_id=cnquery.query_id)
    if cnraw is None: raise RuntimeError("warning V2 CNINFO route map lacks bytes")
    plan = build_v2_plan(
        reuse_package=reuse, v1_plan=v1plan, v1_census=v1census,
        v1_captures=v1captures, v1_raw_by_capture_fingerprint=v1raws,
        cninfo_route_map_raw_sha256=cncapture.raw_sha256,
    )
    plan_root = publish_v2_plan(custody_root=args.custody_root, plan=plan)
    route_map = parse_cninfo_route_map(cnraw)
    request_by_id = {item.request_id: item for item in reuse.warning_batch.requests}
    imported_pages = []
    for unit in plan.units:
        if unit.imported_page1_capture_fingerprint:
            raw = raw_by_request[unit.request_id]
            total, locators = parse_page(authority=unit.authority, raw=_decode(raw), source_security_id=unit.source_security_id)
            imported_pages.append((unit.request_id, total, locators))

    captures = list(read_all_v2_captures(plan_root=plan_root))
    latest = {}
    for capture in captures:
        key = (capture.request_id, capture.page_number)
        if key not in latest or capture.attempt_number > latest[key].attempt_number:
            latest[key] = capture
    stopped = False; stop_code = None; last_request = None
    imported_by_id = {request_id: (total, locators) for request_id, total, locators in imported_pages}
    for unit in plan.units:
        page_values = []
        if unit.request_id in imported_by_id:
            total, locators = imported_by_id[unit.request_id]; page_values.append((1, total, locators))
        elif (unit.request_id, 1) in latest and latest[(unit.request_id, 1)].status is ChinaAshareWarningPageStatus.PARSED:
            item = latest[(unit.request_id, 1)]; page_values.append((1, item.reported_total, item.locators))
        elif (unit.request_id, 1) in latest and latest[(unit.request_id, 1)].status in TERMINAL:
            stopped = True; stop_code = f"existing_{latest[(unit.request_id, 1)].status.value}"
            break
        expected_total = page_values[0][1] if page_values else None
        required = unit.required_page_count or (None if expected_total is None else max(1, (expected_total + unit.page_size - 1) // unit.page_size))
        next_page = 1 if not page_values else 2
        while required is None or next_page <= required:
            key = (unit.request_id, next_page)
            prior = latest.get(key)
            if prior is not None and prior.status is ChinaAshareWarningPageStatus.PARSED:
                page_values.append((next_page, prior.reported_total, prior.locators))
                expected_total = page_values[0][1]; required = prior.required_page_count; next_page += 1
                continue
            if prior is not None and prior.status in TERMINAL:
                stopped = True; stop_code = f"existing_{prior.status.value}"; break
            attempt = 1 if prior is None else prior.attempt_number + 1
            unique_pages = {(item.request_id, item.page_number) for item in captures}
            if key not in unique_pages and len(unique_pages) >= plan.maximum_new_page_request_count:
                stopped = True; stop_code = "maximum_new_page_request_count_reached"; break
            if len(captures) >= plan.maximum_new_http_attempt_count:
                stopped = True; stop_code = "maximum_new_http_attempt_count_reached"; break
            if last_request is not None:
                wait = plan.minimum_request_interval_milliseconds / 1000 - (time.monotonic() - last_request)
                if wait > 0: time.sleep(wait)
            last_request = time.monotonic()
            request = request_by_id[unit.request_id]
            capture, raw = acquire_v2_page(
                plan=plan, unit=unit, page_number=next_page, attempt_number=attempt,
                route_map=route_map, interval_start=request.effective_from,
                interval_end=request.effective_to, expected_total=expected_total,
            )
            publish_v2_capture(plan_root=plan_root, capture=capture, raw_bytes=raw)
            reread, reread_raw = read_v2_capture(plan_root=plan_root, request_id=unit.request_id, page_number=next_page, attempt_number=attempt)
            if reread != capture or reread_raw != raw: raise RuntimeError("warning V2 exact capture reread differs")
            captures.append(capture); latest[key] = capture
            print(json.dumps({
                "event": "warning_v2_page_capture", "ordinal": unit.ordinal,
                "request_id": unit.request_id, "source_security_id": unit.source_security_id,
                "authority": str(unit.authority), "page_number": next_page,
                "attempt_number": attempt, "status": str(capture.status),
                "http_status": capture.http_status, "reported_total": capture.reported_total,
                "required_page_count": capture.required_page_count,
                "locator_count": len(capture.locators), "raw_sha256": capture.raw_sha256,
                "blocker_code": capture.blocker_code,
            }, sort_keys=True), flush=True)
            if capture.status in TERMINAL:
                stopped = True; stop_code = f"{unit.authority.value}_{capture.status.value}_{capture.blocker_code}"; break
            if capture.status is not ChinaAshareWarningPageStatus.PARSED:
                if should_retry_v2(plan=plan, capture=capture):
                    continue
                stopped = True; stop_code = f"{unit.authority.value}_{capture.status.value}_{capture.blocker_code}"; break
            page_values.append((next_page, capture.reported_total, capture.locators))
            expected_total = page_values[0][1]; required = capture.required_page_count
            merged, merge_blocker = validate_and_merge_pages(unit=unit, pages=tuple(page_values))
            if merge_blocker and len(page_values) == required:
                stopped = True; stop_code = merge_blocker; break
            next_page += 1
        if stopped: break

    census = build_v2_census(plan=plan, imported_pages=tuple(imported_pages), new_captures=tuple(captures), stopped_early=stopped, stop_code=stop_code)
    census_path = publish_v2_census(plan_root=plan_root, census=census)
    if read_v2_census(plan_root=plan_root, census_fingerprint=census.logical_fingerprint) != census: raise RuntimeError("warning V2 census reread differs")
    print(json.dumps({
        "event": "warning_v2_census", "plan_fingerprint": plan.logical_fingerprint,
        "plan_root": str(plan_root), "census_fingerprint": census.logical_fingerprint,
        "census_path": str(census_path), "completed_unit_count": census.completed_unit_count,
        "new_attempt_count": census.new_attempt_count, "total_attempt_count": census.total_attempt_count,
        "new_page_request_count": census.new_page_request_count,
        "deduplicated_locator_count": census.deduplicated_locator_count,
        "observed_publication_clock_count": census.observed_publication_clock_count,
        "adjudication_ready_unit_count": 0, "stopped_early": stopped, "stop_code": stop_code,
    }, sort_keys=True), flush=True)
    return 2 if stopped else 0


if __name__ == "__main__": raise SystemExit(main())
