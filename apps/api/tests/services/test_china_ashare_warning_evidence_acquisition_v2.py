from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import ChinaAshareOfficialEvidenceAuthority
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import ChinaAshareWarningAnnouncementLocatorV1
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition_v2 import (
    ChinaAshareWarningAcquisitionPlanV2,
    ChinaAshareWarningPageCaptureV2,
    ChinaAshareWarningPageStatus,
    ChinaAshareWarningV2UnitV1,
    build_contract,
)
from tip_api.persistence.china_ashare_warning_evidence_acquisition_v2 import (
    publish_v2_capture, publish_v2_plan, read_v2_capture,
)
from tip_api.services.china_ashare_warning_evidence_acquisition_v2 import validate_and_merge_pages


H = "a" * 64


def _locator(index: int, *, url_suffix: str = ""):
    return ChinaAshareWarningAnnouncementLocatorV1(
        document_id=f"doc-{index:03d}", source_security_id="sz.002872",
        document_url=f"https://static.cninfo.com.cn/doc-{index:03d}{url_suffix}.pdf",
        published_at=datetime(2026, 9, 18, tzinfo=timezone.utc) + timedelta(seconds=index),
        publication_clock_observed=True,
    )


def _plan():
    units = []
    for ordinal in range(1, 493):
        authority = ChinaAshareOfficialEvidenceAuthority.SSE if ordinal <= 225 else ChinaAshareOfficialEvidenceAuthority.CNINFO
        imported = ordinal <= 19 or 226 <= ordinal <= 244
        values = dict(
            ordinal=ordinal, request_id=hashlib.sha256(f"unit-{ordinal}".encode()).hexdigest(),
            source_security_id=(f"sh.{ordinal:06d}" if authority is ChinaAshareOfficialEvidenceAuthority.SSE else f"sz.{ordinal:06d}"),
            stable_subject_id=f"instrument:{ordinal}", authority=authority,
            page_size=100 if authority is ChinaAshareOfficialEvidenceAuthority.SSE else 30,
            maximum_pages=2 if authority is ChinaAshareOfficialEvidenceAuthority.SSE else 4,
        )
        if imported:
            total = 60 if ordinal == 226 else 1
            values.update(
                imported_page1_capture_fingerprint=hashlib.sha256(f"capture-{ordinal}".encode()).hexdigest(),
                imported_page1_raw_sha256=hashlib.sha256(f"raw-{ordinal}".encode()).hexdigest(),
                imported_page1_total=total, imported_page1_locator_count=30 if total == 60 else 1,
                required_page_count=2 if total == 60 else 1,
            )
        units.append(ChinaAshareWarningV2UnitV1(**values))
    return build_contract(
        ChinaAshareWarningAcquisitionPlanV2,
        input_reuse_package_fingerprint=H, input_warning_batch_fingerprint="b" * 64,
        input_v1_plan_fingerprint="c" * 64, input_v1_partial_census_fingerprint="d" * 64,
        input_v1_capture_set_fingerprint="e" * 64, cninfo_route_map_raw_sha256="f" * 64,
        units=tuple(units),
    )


def test_sz_002872_two_page_path_is_deduplicated_and_ordered():
    unit = ChinaAshareWarningV2UnitV1(
        ordinal=1, request_id=H, source_security_id="sz.002872", stable_subject_id="instrument:fixture",
        authority=ChinaAshareOfficialEvidenceAuthority.CNINFO, page_size=30, maximum_pages=4,
        imported_page1_capture_fingerprint="b" * 64, imported_page1_raw_sha256="c" * 64,
        imported_page1_total=60, imported_page1_locator_count=30, required_page_count=2,
    )
    page1 = tuple(_locator(i) for i in range(30))
    page2 = tuple(_locator(i) for i in range(30, 60))
    merged, blocker = validate_and_merge_pages(unit=unit, pages=((1, 60, page1), (2, 60, page2)))
    assert blocker is None
    assert len(merged) == 60
    assert tuple(item.document_id for item in merged) == tuple(f"doc-{i:03d}" for i in range(60))


def test_total_drift_empty_and_duplicate_conflict_stop():
    unit = ChinaAshareWarningV2UnitV1(
        ordinal=1, request_id=H, source_security_id="sz.002872", stable_subject_id="instrument:fixture",
        authority=ChinaAshareOfficialEvidenceAuthority.CNINFO, page_size=30, maximum_pages=4,
        imported_page1_capture_fingerprint="b" * 64, imported_page1_raw_sha256="c" * 64,
        imported_page1_total=60, imported_page1_locator_count=30, required_page_count=2,
    )
    page1 = tuple(_locator(i) for i in range(30))
    assert validate_and_merge_pages(unit=unit, pages=((1, 60, page1), (2, 61, tuple(_locator(i) for i in range(30, 60)))))[1] == "total_drift"
    assert validate_and_merge_pages(unit=unit, pages=((1, 60, page1), (2, 60, ())))[1] == "empty_page_before_completion"
    conflict = (_locator(0, url_suffix="-changed"),) + tuple(_locator(i) for i in range(30, 59))
    assert validate_and_merge_pages(unit=unit, pages=((1, 60, page1), (2, 60, conflict)))[1] == "duplicate_document_conflict"


def test_page2_checkpoint_is_append_only_and_exactly_restartable(tmp_path):
    plan = _plan(); root = publish_v2_plan(custody_root=tmp_path, plan=plan)
    unit = plan.units[225]
    raw = b'{"fixture":"page2"}'
    capture = build_contract(
        ChinaAshareWarningPageCaptureV2,
        plan_fingerprint=plan.logical_fingerprint, request_id=unit.request_id,
        source_security_id=unit.source_security_id, authority=unit.authority,
        page_number=2, page_size=30, attempt_number=1,
        requested_url="https://www.cninfo.com.cn/new/hisAnnouncement/query",
        http_method="POST", request_parameters=(("pageNum", "2"),),
        retrieved_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
        final_url="https://www.cninfo.com.cn/new/hisAnnouncement/query", http_status=200,
        content_type="application/json", raw_byte_size=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(), status=ChinaAshareWarningPageStatus.PARSED,
        reported_total=60, required_page_count=2,
        locators=tuple(_locator(i) for i in range(30, 60)),
    )
    target = publish_v2_capture(plan_root=root, capture=capture, raw_bytes=raw)
    assert publish_v2_capture(plan_root=root, capture=capture, raw_bytes=raw) == target
    assert read_v2_capture(plan_root=root, request_id=unit.request_id, page_number=2, attempt_number=1) == (capture, raw)
    assert target.stat().st_mode & 0o777 == 0o700
    assert all(item.stat().st_mode & 0o777 == 0o400 for item in target.iterdir())
