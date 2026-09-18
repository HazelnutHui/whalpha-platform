from __future__ import annotations

import hashlib
import gzip
import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

from tip_api.contracts.china_ashare.v1.official_event_documents import (
    ChinaAshareOfficialDocumentParseStatus,
    ChinaAshareRiskWarningEventKind,
    ChinaAshareRiskWarningSubtype,
)
from tip_api.contracts.china_ashare.v1.official_event_evidence import (
    ChinaAshareOfficialEventParseStatus,
)
from tip_api.persistence.china_ashare_official_event_documents import (
    completed_official_document_ids,
    publish_official_event_document_capture,
    publish_official_event_document_plan,
    read_official_event_document_capture,
    read_official_event_document_plan,
)
from tip_api.services import china_ashare_official_event_documents as service


def test_sse_stage_two_plan_binds_three_discovered_documents() -> None:
    evidence_plan, evidence_capture, raw = _stage_one()

    plan = service.plan_sse_risk_warning_documents(
        evidence_plan=evidence_plan,
        evidence_capture=evidence_capture,
        raw_bytes=raw,
    )

    assert plan.source_security_id == "sh.600053"
    assert tuple(item.document_id for item in plan.documents) == (
        "26042619200577997000",
        "6639037201496555",
        "6739037201924642",
    )
    assert plan.parent_capture_fingerprint == "2" * 64
    assert plan.parent_raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert all(item.maximum_attempts == 1 for item in plan.documents)
    assert plan.outcome_read_count == 0
    assert plan.historical_coverage_authorized is False


def test_document_parse_extracts_implementation_subtype_and_date() -> None:
    plan = service.plan_sse_risk_warning_documents(
        evidence_plan=_stage_one()[0],
        evidence_capture=_stage_one()[1],
        raw_bytes=_stage_one()[2],
    )
    document = next(
        item for item in plan.documents if item.document_id == "6739037201924642"
    )

    event, conflicts, blocker = service.parse_risk_warning_document(
        document=document,
        text=(
            "公司股票于2026年4月30日停牌一天，"
            "自2026年5月6日开市起实施退市风险警示，股票简称变更为*ST九鼎。"
        ),
    )

    assert blocker is None
    assert conflicts == ()
    assert event is not None
    assert event.event_kind is ChinaAshareRiskWarningEventKind.WARNING_IMPLEMENTED
    assert event.subtype is ChinaAshareRiskWarningSubtype.STAR_ST
    assert event.effective_from == date(2026, 5, 6)
    assert event.publication_clock_time_known is False


def test_document_capture_is_owner_only_and_exact(monkeypatch, tmp_path) -> None:
    evidence_plan, evidence_capture, stage_one_raw = _stage_one()
    plan = service.plan_sse_risk_warning_documents(
        evidence_plan=evidence_plan,
        evidence_capture=evidence_capture,
        raw_bytes=stage_one_raw,
    )
    document = next(
        item for item in plan.documents if item.document_id == "6739037201924642"
    )
    raw_pdf = b"%PDF-1.7\nsynthetic"
    text = "自2026年5月6日起实施退市风险警示。"
    monkeypatch.setattr(service, "urlopen", lambda request, timeout: _Response(raw_pdf))
    monkeypatch.setattr(service, "extract_pdf_text", lambda raw: (text, None))

    capture, raw, extracted = service.capture_official_event_document(
        plan=plan,
        document=document,
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )
    root = publish_official_event_document_plan(
        custody_root=tmp_path / "documents", plan=plan
    )
    publish_official_event_document_capture(
        plan_root=root,
        capture=capture,
        raw_bytes=raw,
        text_bytes=extracted,
    )

    assert read_official_event_document_plan(plan_root=root) == plan
    assert read_official_event_document_capture(
        plan_root=root, document_id=document.document_id
    ) == (capture, raw_pdf, text.encode())
    assert completed_official_document_ids(plan_root=root) == (document.document_id,)
    assert capture.parse_status is ChinaAshareOfficialDocumentParseStatus.PARSED
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(
        item.stat().st_mode & 0o777 == 0o400
        for item in (root / "documents" / document.document_id).iterdir()
    )


def test_unextractable_pdf_is_typed_single_attempt_blocker(monkeypatch) -> None:
    evidence_plan, evidence_capture, raw = _stage_one()
    plan = service.plan_sse_risk_warning_documents(
        evidence_plan=evidence_plan,
        evidence_capture=evidence_capture,
        raw_bytes=raw,
    )
    document = plan.documents[0]
    monkeypatch.setattr(
        service, "urlopen", lambda request, timeout: _Response(b"%PDF-1.7\nimage")
    )
    monkeypatch.setattr(
        service,
        "extract_pdf_text",
        lambda raw: (None, "pdf_embedded_text_unavailable"),
    )

    capture, raw_bytes, text_bytes = service.capture_official_event_document(
        plan=plan,
        document=document,
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )

    assert raw_bytes is not None
    assert text_bytes is None
    assert capture.attempt_count == 1
    assert (
        capture.parse_status
        is ChinaAshareOfficialDocumentParseStatus.CAPTURED_UNPARSED
    )
    assert capture.blocker_code == "pdf_embedded_text_unavailable"


def test_sse_antibot_challenge_is_typed(monkeypatch) -> None:
    evidence_plan, evidence_capture, raw = _stage_one()
    plan = service.plan_sse_risk_warning_documents(
        evidence_plan=evidence_plan,
        evidence_capture=evidence_capture,
        raw_bytes=raw,
    )
    document = plan.documents[0]
    challenge = gzip.compress(b"<script>acw_sc__v2</script>", mtime=0)
    monkeypatch.setattr(
        service, "urlopen", lambda request, timeout: _Response(challenge)
    )

    capture, raw_bytes, text_bytes = service.capture_official_event_document(
        plan=plan,
        document=document,
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
    )

    assert raw_bytes == challenge
    assert text_bytes is None
    assert (
        capture.parse_status
        is ChinaAshareOfficialDocumentParseStatus.ANTIBOT_BLOCKED
    )
    assert capture.blocker_code == "sse_antibot_cookie_challenge"


def _stage_one():
    rows = [
        (
            "6739037201924642",
            "2026-04-29",
            "九鼎投资关于公司股票被实施退市风险警示暨停牌的公告",
            "/disclosure/listedinfo/announcement/c/new/2026-04-29/600053_20260429_BJIL.pdf",
        ),
        (
            "6639037201496555",
            "2026-04-28",
            "九鼎投资关于公司股票可能被实施退市风险警示的第二次风险提示公告",
            "/disclosure/listedinfo/announcement/c/new/2026-04-28/600053_20260428_HRLG.pdf",
        ),
        (
            "26042619200577997000",
            "2026-04-27",
            "关于2025年年度业绩预告更正暨股票可能被实施退市风险警示的风险提示公告",
            "/disclosure/listedinfo/announcement/c/new/2026-04-27/600053_20260427_EVE2.pdf",
        ),
    ]
    raw = json.dumps(
        {
            "pageHelp": {"total": 3},
            "result": [
                [
                    {
                        "SECURITY_CODE": "600053",
                        "TITLE": title,
                        "SSEDATE": published,
                        "URL": url,
                        "ORG_BULLETIN_ID": document_id,
                    }
                ]
                for document_id, published, title, url in rows
            ],
        },
        ensure_ascii=False,
    ).encode()
    plan = SimpleNamespace(logical_fingerprint="1" * 64)
    capture = SimpleNamespace(
        plan_fingerprint="1" * 64,
        query_id="sh-600053-risk-warning",
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        logical_fingerprint="2" * 64,
        parse_status=ChinaAshareOfficialEventParseStatus.SCHEMA_BLOCKED,
    )
    return plan, capture, raw


class _Headers:
    def get(self, key, default=None):
        return "application/pdf"


class _Response:
    status = 200
    headers = _Headers()

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, maximum):
        return self.payload

    def geturl(self):
        return "https://static.sse.com.cn/disclosure/example.pdf"
