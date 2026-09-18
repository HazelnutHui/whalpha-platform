"""Restartable CLI for the frozen 492-unit official warning batch."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
)
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import (
    ChinaAshareWarningAcquisitionStatus,
)
from tip_api.persistence.china_ashare_cninfo_event_evidence import (
    read_cninfo_event_capture,
    read_cninfo_event_plan,
)
from tip_api.persistence.china_ashare_official_evidence_reuse import (
    read_china_ashare_official_evidence_reuse_package,
)
from tip_api.persistence.china_ashare_warning_evidence_acquisition import (
    publish_warning_acquisition_capture,
    publish_warning_acquisition_census,
    publish_warning_acquisition_plan,
    read_all_warning_acquisition_captures,
    read_warning_acquisition_capture,
    read_warning_acquisition_census,
)
from tip_api.services.china_ashare_warning_evidence_acquisition import (
    acquire_warning_attempt,
    build_acquisition_census,
    build_warning_acquisition_plan,
    is_endpoint_stop,
    parse_cninfo_route_map,
    should_retry,
)


SUCCESS = {
    ChinaAshareWarningAcquisitionStatus.PARSED_PENDING_ADJUDICATION,
    ChinaAshareWarningAcquisitionStatus.PARSED_ZERO_RESULTS,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-package", type=Path, required=True)
    parser.add_argument("--cninfo-route-map-plan-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute-all", action="store_true")
    args = parser.parse_args(argv)

    reuse = read_china_ashare_official_evidence_reuse_package(package_path=args.reuse_package)
    cninfo_plan = read_cninfo_event_plan(plan_root=args.cninfo_route_map_plan_root)
    route_query = next(item for item in cninfo_plan.queries if item.request_kind.value == "security_map")
    route_capture, route_raw = read_cninfo_event_capture(plan_root=args.cninfo_route_map_plan_root, query_id=route_query.query_id)
    if route_raw is None:
        raise RuntimeError("CNINFO route map capture lacks raw bytes")
    plan = build_warning_acquisition_plan(
        reuse_package=reuse, cninfo_route_map_capture=route_capture,
        cninfo_route_map_raw=route_raw,
    )
    plan_root = publish_warning_acquisition_plan(custody_root=args.custody_root, plan=plan)
    route_map = parse_cninfo_route_map(route_raw)
    captures = list(read_all_warning_acquisition_captures(plan_root=plan_root))
    by_request = defaultdict(list)
    for capture in captures:
        by_request[capture.request_id].append(capture)

    if args.execute_all:
        successful_authorities = {item.authority for item in captures if item.status in SUCCESS}
        required = {ChinaAshareOfficialEvidenceAuthority.SSE, ChinaAshareOfficialEvidenceAuthority.CNINFO}
        if successful_authorities != required:
            raise RuntimeError("both authority preflights must succeed before full execution")
        selected = reuse.warning_batch.requests
    else:
        selected = tuple(
            next(
                item for item in reuse.warning_batch.requests
                if item.authority is authority and not by_request[item.request_id]
            )
            for authority in (
                ChinaAshareOfficialEvidenceAuthority.SSE,
                ChinaAshareOfficialEvidenceAuthority.CNINFO,
            )
        )

    stopped = False
    stop_code = None
    last_request_monotonic = None
    for unit in selected:
        prior = sorted(by_request[unit.request_id], key=lambda item: item.attempt_number)
        if prior and (prior[-1].status in SUCCESS or is_endpoint_stop(prior[-1]) or not should_retry(plan=plan, capture=prior[-1])):
            continue
        attempt = 1 if not prior else prior[-1].attempt_number + 1
        while attempt <= plan.maximum_http_attempts_per_request:
            if len(captures) >= plan.maximum_total_http_attempts:
                stopped, stop_code = True, "maximum_total_http_attempts_reached"
                break
            if last_request_monotonic is not None:
                elapsed = time.monotonic() - last_request_monotonic
                wait = plan.minimum_request_interval_milliseconds / 1000 - elapsed
                if wait > 0:
                    time.sleep(wait)
            last_request_monotonic = time.monotonic()
            capture, raw = acquire_warning_attempt(
                plan=plan, batch_request=unit, attempt_number=attempt,
                cninfo_route_map=route_map,
            )
            publish_warning_acquisition_capture(plan_root=plan_root, capture=capture, raw_bytes=raw)
            reread, reread_raw = read_warning_acquisition_capture(
                plan_root=plan_root, request_id=capture.request_id,
                attempt_number=capture.attempt_number,
            )
            if reread != capture or reread_raw != raw:
                raise RuntimeError("warning capture exact reread differs")
            captures.append(capture)
            by_request[unit.request_id].append(capture)
            print(json.dumps({
                "event": "warning_evidence_capture",
                "ordinal": unit.ordinal,
                "request_id": unit.request_id,
                "source_security_id": unit.source_security_id,
                "authority": str(unit.authority),
                "attempt_number": attempt,
                "status": str(capture.status),
                "http_status": capture.http_status,
                "raw_sha256": capture.raw_sha256,
                "result_total": capture.result_total,
                "locator_count": len(capture.locators),
                "blocker_code": capture.blocker_code,
                "capture_fingerprint": capture.logical_fingerprint,
            }, sort_keys=True), flush=True)
            if is_endpoint_stop(capture):
                stopped, stop_code = True, f"{unit.authority.value}_{capture.status.value}_{capture.blocker_code}"
                break
            if not should_retry(plan=plan, capture=capture):
                if capture.status not in SUCCESS:
                    stopped, stop_code = True, f"{unit.authority.value}_{capture.status.value}_{capture.blocker_code}"
                break
            attempt += 1
        if stopped:
            break

    census = build_acquisition_census(plan=plan, captures=captures, stopped_early=stopped, stop_code=stop_code)
    census_path = publish_warning_acquisition_census(plan_root=plan_root, census=census)
    if read_warning_acquisition_census(plan_root=plan_root, census_fingerprint=census.logical_fingerprint) != census:
        raise RuntimeError("warning acquisition census exact reread differs")
    print(json.dumps({
        "event": "warning_evidence_acquisition_census",
        "mode": "preflight" if args.preflight else "execute_all",
        "plan_root": str(plan_root),
        "plan_fingerprint": plan.logical_fingerprint,
        "census_path": str(census_path),
        "census_fingerprint": census.logical_fingerprint,
        "completed_logical_unit_count": census.completed_logical_unit_count,
        "http_attempt_count": census.http_attempt_count,
        "counts_by_status": census.counts_by_status,
        "announcement_locator_count": census.announcement_locator_count,
        "observed_publication_clock_count": census.observed_publication_clock_count,
        "adjudication_ready_unit_count": census.adjudication_ready_unit_count,
        "zero_result_unit_count": census.zero_result_unit_count,
        "stopped_early": census.stopped_early,
        "stop_code": census.stop_code,
        "outcome_read_count": 0,
    }, sort_keys=True), flush=True)
    return 2 if stopped else 0


if __name__ == "__main__":
    raise SystemExit(main())
