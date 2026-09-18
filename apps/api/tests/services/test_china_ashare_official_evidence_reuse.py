from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone

import pytest

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
)
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
    ChinaAshareOfficialEvidenceRequestPurpose,
)
from tip_api.contracts.china_ashare.v1.official_evidence_reuse import (
    ChinaAshareLocalEvidenceDescriptorV1,
    ChinaAshareLocalEvidenceInventoryV1,
    ChinaAshareLocalEvidenceKind,
    ChinaAshareOfficialEvidenceReuseCensusV1,
    ChinaAshareOfficialEvidenceReuseDecisionV1,
    ChinaAshareReuseDisposition,
    ChinaAshareWarningBatchRequestV1,
    ChinaAshareWarningCaptureStatus,
    ChinaAshareWarningEvidenceBatchManifestV1,
    ChinaAshareWarningRawCaptureV1,
    ChinaAshareWarningAdjudicationInputV1,
    build_contract,
)
from tip_api.persistence.china_ashare_official_evidence_reuse import (
    ChinaAshareOfficialEvidenceReusePackageError,
    publish_china_ashare_official_evidence_reuse_package,
    read_china_ashare_official_evidence_reuse_package,
)
from tip_api.services.china_ashare_official_evidence_reuse import (
    classify_warning_response,
)


H = "a" * 64


def _package_values():
    inventory = build_contract(
        ChinaAshareLocalEvidenceInventoryV1,
        source_package_fingerprints=(H,), evidence=(), evidence_count=0,
        positive_evidence_eligible_count=0,
    )
    decisions = []
    requests = []
    for ordinal in range(1, 493):
        request_id = hashlib.sha256(f"warning-{ordinal:03d}".encode()).hexdigest()
        source = f"{'sh' if ordinal % 2 else 'sz'}.{ordinal:06d}"
        decisions.append(ChinaAshareOfficialEvidenceReuseDecisionV1(
            request_id=request_id, stable_subject_id=f"instrument:{ordinal}",
            source_security_id=source,
            family=ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
            purpose=ChinaAshareOfficialEvidenceRequestPurpose.RISK_WARNING_TRANSITION_HISTORY,
            disposition=ChinaAshareReuseDisposition.NETWORK_REQUIRED,
            reason_codes=("network_required_fail_closed",),
        ))
    decisions.sort(key=lambda item: item.request_id)
    census = build_contract(
        ChinaAshareOfficialEvidenceReuseCensusV1,
        input_priority_plan_package_fingerprint=H,
        input_priority_plan_fingerprint="b" * 64,
        local_evidence_inventory_fingerprint=inventory.logical_fingerprint,
        decisions=tuple(decisions), request_count=492, reusable_request_count=0,
        network_required_request_count=492, counts_by_family=(("risk_warning", 492),),
    )
    for ordinal, decision in enumerate(decisions, 1):
        requests.append(ChinaAshareWarningBatchRequestV1(
            ordinal=ordinal, request_id=decision.request_id,
            stable_subject_id=decision.stable_subject_id,
            source_security_id=decision.source_security_id,
            authority=(ChinaAshareOfficialEvidenceAuthority.SSE
                       if decision.source_security_id.startswith("sh.")
                       else ChinaAshareOfficialEvidenceAuthority.CNINFO),
            effective_from=date(2020, 1, 1), effective_to=date(2026, 1, 1),
            expected_fields=(
                "document_id", "document_url", "effective_from", "effective_to",
                "event_kind", "published_at", "raw_sha256", "warning_subtype",
            ),
        ))
    warning = build_contract(
        ChinaAshareWarningEvidenceBatchManifestV1,
        input_priority_plan_package_fingerprint=H,
        input_reuse_census_fingerprint=census.logical_fingerprint,
        requests=tuple(requests),
    )
    return inventory, census, warning


def test_positive_reuse_requires_all_strict_fields():
    with pytest.raises(ValueError, match="positive evidence eligibility differs"):
        ChinaAshareLocalEvidenceDescriptorV1(
            evidence_id=H, evidence_kind=ChinaAshareLocalEvidenceKind.OFFICIAL_DOCUMENT_CAPTURE,
            authority=ChinaAshareOfficialEvidenceAuthority.SSE,
            source_package_fingerprint=H, source_capture_fingerprint=H,
            source_security_id="sh.600053", stable_subject_id=None,
            exact_security_binding=False, raw_sha256=H,
            parse_status="parsed", structured_fields=("document_id",),
            positive_evidence_eligible=True,
        )


@pytest.mark.parametrize(
    ("status", "raw", "expected", "marker"),
    [
        (200, b'<script>document.cookie="acw_sc__v2=x"</script>', ChinaAshareWarningCaptureStatus.CHALLENGE_BLOCKED, "acw_sc__v2"),
        (200, b'{"announcements":[]}', ChinaAshareWarningCaptureStatus.CAPTURED_PENDING_ADJUDICATION, None),
        (503, b"temporarily unavailable", ChinaAshareWarningCaptureStatus.HTTP_BLOCKED, None),
        (None, None, ChinaAshareWarningCaptureStatus.TRANSPORT_BLOCKED, None),
    ],
)
def test_challenge_classifier_is_defensive_only(status, raw, expected, marker):
    assert classify_warning_response(http_status=status, raw_bytes=raw) == (expected, marker)


def test_raw_capture_and_adjudication_are_separate_contracts():
    capture = ChinaAshareWarningRawCaptureV1(
        batch_fingerprint=H, request_id="b" * 64, attempt_number=1,
        authority=ChinaAshareOfficialEvidenceAuthority.SSE,
        requested_url="https://www.sse.com.cn/", final_url="https://www.sse.com.cn/",
        retrieved_at=datetime(2026, 9, 18, tzinfo=timezone.utc), http_status=200,
        content_type="application/json", raw_byte_size=2,
        raw_sha256=hashlib.sha256(b"{}").hexdigest(),
        status=ChinaAshareWarningCaptureStatus.CAPTURED_PENDING_ADJUDICATION,
    )
    assert capture.positive_evidence_authorized is False
    adjudication = ChinaAshareWarningAdjudicationInputV1(
        request_id="b" * 64, stable_subject_id="instrument:fixture",
        source_security_id="sh.600053", authority=ChinaAshareOfficialEvidenceAuthority.SSE,
        search_raw_sha256=capture.raw_sha256, document_id="doc-1",
        document_url="https://www.sse.com.cn/doc.pdf", document_raw_sha256="c" * 64,
        published_at=datetime(2026, 9, 18, 8, tzinfo=timezone.utc),
        effective_from=date(2026, 9, 19), effective_to=date(2026, 9, 20),
        event_kind="warning_implemented", warning_subtype="st",
    )
    assert adjudication.exact_security_binding is True
    assert adjudication.ticker_only_evidence_authorized is False


def test_challenge_capture_requires_detected_marker():
    with pytest.raises(ValueError, match="challenge capture lacks marker"):
        ChinaAshareWarningRawCaptureV1(
            batch_fingerprint=H, request_id="b" * 64, attempt_number=1,
            authority=ChinaAshareOfficialEvidenceAuthority.SSE,
            requested_url="https://www.sse.com.cn/", final_url="https://www.sse.com.cn/",
            retrieved_at=datetime(2026, 9, 18, tzinfo=timezone.utc), http_status=200,
            content_type="text/html", raw_byte_size=1, raw_sha256="c" * 64,
            status=ChinaAshareWarningCaptureStatus.CHALLENGE_BLOCKED,
        )


def test_owner_only_closed_set_exact_reread_and_replay(tmp_path):
    inventory, census, warning = _package_values()
    primary = publish_china_ashare_official_evidence_reuse_package(
        custody_root=tmp_path / "primary", inventory=inventory, census=census,
        warning_batch=warning,
    )
    replay = publish_china_ashare_official_evidence_reuse_package(
        custody_root=tmp_path / "replay", inventory=inventory, census=census,
        warning_batch=warning,
    )
    assert primary.manifest == replay.manifest
    assert {item.name: item.read_bytes() for item in primary.package_path.iterdir()} == {
        item.name: item.read_bytes() for item in replay.package_path.iterdir()
    }
    assert primary.package_path.stat().st_mode & 0o777 == 0o700
    assert all(item.stat().st_mode & 0o777 == 0o400 for item in primary.package_path.iterdir())
    (primary.package_path / "extra").write_text("x")
    with pytest.raises(ChinaAshareOfficialEvidenceReusePackageError, match="closed file set"):
        read_china_ashare_official_evidence_reuse_package(package_path=primary.package_path)
