from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone

import pytest

from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
)
from tip_api.contracts.china_ashare.v1.official_evidence_reuse import (
    ChinaAshareWarningBatchRequestV1,
)
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import (
    ChinaAshareWarningAcquisitionPlanV1,
    ChinaAshareWarningAcquisitionStatus,
    build_contract,
)
from tip_api.persistence.china_ashare_warning_evidence_acquisition import (
    publish_warning_acquisition_capture,
    publish_warning_acquisition_plan,
    read_warning_acquisition_capture,
)
from tip_api.services import china_ashare_warning_evidence_acquisition as service


H = "a" * 64
EXPECTED = (
    "document_id", "document_url", "effective_from", "effective_to",
    "event_kind", "published_at", "raw_sha256", "warning_subtype",
)


class _Response:
    def __init__(self, raw, url, content_type="application/json"):
        self.raw = raw
        self.status = 200
        self.headers = {"Content-Type": content_type}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.raw[:limit]

    def geturl(self):
        return self.url


def _plan():
    return build_contract(
        ChinaAshareWarningAcquisitionPlanV1,
        input_reuse_package_fingerprint=H,
        input_warning_batch_fingerprint="b" * 64,
        cninfo_route_map_raw_sha256="c" * 64,
        cninfo_route_map_capture_fingerprint="d" * 64,
    )


def _unit(authority, source):
    return ChinaAshareWarningBatchRequestV1(
        ordinal=1, request_id=hashlib.sha256(source.encode()).hexdigest(),
        stable_subject_id="instrument:fixture", source_security_id=source,
        authority=authority, effective_from=date(2021, 9, 16),
        effective_to=date(2026, 9, 16), expected_fields=EXPECTED,
    )


def test_sse_zero_result_remains_non_evidence(monkeypatch):
    raw = json.dumps({"result": [], "pageHelp": {"total": 0}}).encode()
    monkeypatch.setattr(service, "urlopen", lambda *a, **k: _Response(raw, service.SSE_QUERY_URL))
    capture, stored = service.acquire_warning_attempt(
        plan=_plan(),
        batch_request=_unit(ChinaAshareOfficialEvidenceAuthority.SSE, "sh.600001"),
        attempt_number=1, cninfo_route_map={},
        retrieved_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )
    assert stored == raw
    assert capture.status is ChinaAshareWarningAcquisitionStatus.PARSED_ZERO_RESULTS
    assert capture.zero_results_prove_no_event is False
    assert capture.positive_event_evidence_authorized is False


def test_sse_group_count_excludes_secondary_attachment(monkeypatch):
    primary = {
        "ORG_BULLETIN_ID": "doc-1", "ORG_FILE_TYPE": 0,
        "SECURITY_CODE": "600001", "SSEDATE": "2026-09-18",
        "URL": "/primary.pdf",
    }
    attachment = {
        "ORG_BULLETIN_ID": "doc-1", "ORG_FILE_TYPE": 1,
        "SECURITY_CODE": "600001", "SSEDATE": "2026-09-18",
        "URL": "/attachment.pdf",
    }
    raw = json.dumps({"result": [[primary, attachment]], "pageHelp": {"total": 1}}).encode()
    monkeypatch.setattr(service, "urlopen", lambda *a, **k: _Response(raw, service.SSE_QUERY_URL))
    capture, _ = service.acquire_warning_attempt(
        plan=_plan(),
        batch_request=_unit(ChinaAshareOfficialEvidenceAuthority.SSE, "sh.600001"),
        attempt_number=1, cninfo_route_map={},
    )
    assert capture.status is ChinaAshareWarningAcquisitionStatus.PARSED_PENDING_ADJUDICATION
    assert capture.result_total == 1
    assert tuple(item.document_id for item in capture.locators) == ("doc-1",)


def test_cninfo_locator_retains_observed_publication_clock(monkeypatch):
    raw = json.dumps({
        "totalAnnouncement": 1,
        "announcements": [{
            "secCode": "002109", "announcementId": "doc-1",
            "announcementTime": 1789747200000,
            "adjunctUrl": "finalpage/2026-09-18/doc.pdf",
        }],
    }).encode()
    monkeypatch.setattr(service, "urlopen", lambda *a, **k: _Response(raw, service.CNINFO_QUERY_URL))
    capture, _ = service.acquire_warning_attempt(
        plan=_plan(),
        batch_request=_unit(ChinaAshareOfficialEvidenceAuthority.CNINFO, "sz.002109"),
        attempt_number=1, cninfo_route_map={"002109": "9900002009"},
        retrieved_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )
    assert capture.status is ChinaAshareWarningAcquisitionStatus.PARSED_PENDING_ADJUDICATION
    assert len(capture.locators) == 1
    assert capture.locators[0].publication_clock_observed is True
    assert capture.positive_event_evidence_authorized is False


def test_cninfo_pagination_incomplete_fails_closed(monkeypatch):
    rows = [{
        "secCode": "002109", "announcementId": f"doc-{index}",
        "announcementTime": 1789747200000 + index,
        "adjunctUrl": f"finalpage/doc-{index}.pdf",
    } for index in range(30)]
    raw = json.dumps({"totalAnnouncement": 60, "announcements": rows}).encode()
    monkeypatch.setattr(service, "urlopen", lambda *a, **k: _Response(raw, service.CNINFO_QUERY_URL))
    capture, _ = service.acquire_warning_attempt(
        plan=_plan(),
        batch_request=_unit(ChinaAshareOfficialEvidenceAuthority.CNINFO, "sz.002109"),
        attempt_number=1, cninfo_route_map={"002109": "9900002009"},
    )
    assert capture.status is ChinaAshareWarningAcquisitionStatus.SEMANTIC_BLOCKED
    assert capture.blocker_code == "cninfo_warning_result_pagination_incomplete"
    assert capture.locators == ()
    assert service.should_retry(plan=_plan(), capture=capture) is False


def test_challenge_is_terminal_and_not_retryable(monkeypatch):
    raw = b'<script>document.cookie="acw_sc__v2=x"</script>'
    monkeypatch.setattr(service, "urlopen", lambda *a, **k: _Response(raw, service.SSE_QUERY_URL, "text/html"))
    capture, _ = service.acquire_warning_attempt(
        plan=_plan(),
        batch_request=_unit(ChinaAshareOfficialEvidenceAuthority.SSE, "sh.600001"),
        attempt_number=1, cninfo_route_map={},
    )
    assert capture.status is ChinaAshareWarningAcquisitionStatus.CHALLENGE_BLOCKED
    assert service.should_retry(plan=_plan(), capture=capture) is False
    assert service.is_endpoint_stop(capture) is True


def test_owner_only_capture_exact_reread(tmp_path, monkeypatch):
    plan = _plan()
    root = publish_warning_acquisition_plan(custody_root=tmp_path, plan=plan)
    raw = json.dumps({"result": [], "pageHelp": {"total": 0}}).encode()
    monkeypatch.setattr(service, "urlopen", lambda *a, **k: _Response(raw, service.SSE_QUERY_URL))
    capture, stored = service.acquire_warning_attempt(
        plan=plan,
        batch_request=_unit(ChinaAshareOfficialEvidenceAuthority.SSE, "sh.600001"),
        attempt_number=1, cninfo_route_map={},
    )
    target = publish_warning_acquisition_capture(plan_root=root, capture=capture, raw_bytes=stored)
    assert read_warning_acquisition_capture(plan_root=root, request_id=capture.request_id, attempt_number=1) == (capture, stored)
    assert target.stat().st_mode & 0o777 == 0o700
    assert all(item.stat().st_mode & 0o777 == 0o400 for item in target.iterdir())
