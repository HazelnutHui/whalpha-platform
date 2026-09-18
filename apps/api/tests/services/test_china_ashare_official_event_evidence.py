from __future__ import annotations

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

from tip_api.contracts.china_ashare.v1.official_event_evidence import (
    ChinaAshareOfficialEventParseStatus,
)
from tip_api.persistence.china_ashare_official_event_evidence import (
    completed_official_event_query_ids,
    publish_official_event_capture,
    publish_official_event_evidence_plan,
    read_official_event_capture,
    read_official_event_evidence_plan,
)
from tip_api.services import china_ashare_official_event_evidence as service


def test_partition0_plan_is_closed_bounded_and_outcome_blind() -> None:
    plan = _plan()

    assert len(plan.target_source_security_ids) == 50
    assert len(plan.queries) == 251
    assert plan.minimum_request_interval_milliseconds == 1000
    assert all(item.maximum_attempts == 1 for item in plan.queries)
    assert plan.credentials_required is False
    assert plan.aggregate_sources_authorized is False
    assert plan.outcome_read_count == 0
    assert plan.as_operated_claim_authorized is False
    assert plan.research_backtest_authorized is False


def test_capture_and_owner_only_exact_reread(monkeypatch, tmp_path) -> None:
    plan = _plan()
    query = next(item for item in plan.queries if item.query_id == "sh-600000-risk-warning")
    payload = json.dumps(
        {
            "pageHelp": {"total": 1},
            "result": [[{
                "SECURITY_CODE": "600000",
                "TITLE": "关于公司股票被实施风险警示暨停牌的公告",
                "SSEDATE": "2025-04-30",
                "URL": "/disclosure/example.pdf",
                "ORG_BULLETIN_ID": "123",
            }]],
        },
        ensure_ascii=False,
    ).encode()
    monkeypatch.setattr(service, "urlopen", lambda request, timeout: _Response(payload))
    capture, raw = service.capture_official_event_query(
        plan=plan,
        query=query,
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )

    root = publish_official_event_evidence_plan(custody_root=tmp_path / "evidence", plan=plan)
    publish_official_event_capture(plan_root=root, capture=capture, raw_bytes=raw)
    reread_plan = read_official_event_evidence_plan(plan_root=root)
    reread_capture, reread_raw = read_official_event_capture(
        plan_root=root, query_id=query.query_id
    )

    assert reread_plan == plan
    assert reread_capture == capture
    assert reread_raw == payload
    assert capture.parse_status is ChinaAshareOfficialEventParseStatus.PARSED
    assert len(capture.announcements) == 1
    assert completed_official_event_query_ids(plan_root=root) == (query.query_id,)
    assert (root.stat().st_mode & 0o777) == 0o700
    assert all(
        (item.stat().st_mode & 0o777) == 0o400
        for item in (root / "captures" / query.query_id).iterdir()
    )


def test_transport_failure_is_single_attempt_checkpoint(monkeypatch) -> None:
    plan = _plan()
    query = plan.queries[0]

    def fail(request, timeout):
        raise TimeoutError("bounded timeout")

    monkeypatch.setattr(service, "urlopen", fail)
    capture, raw = service.capture_official_event_query(
        plan=plan,
        query=query,
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )

    assert raw is None
    assert capture.parse_status is ChinaAshareOfficialEventParseStatus.TRANSPORT_BLOCKED
    assert capture.blocker_code == "transport_timeouterror"
    assert capture.attempt_count == 1


def _plan():
    targets = tuple(
        SimpleNamespace(source_security_id=f"sh.{600000 + index:06d}")
        for index in range(50)
    )
    source_plan = SimpleNamespace(
        plan=SimpleNamespace(
            logical_fingerprint="1" * 64,
            interval_start=date(2021, 9, 16),
            interval_end=date(2026, 9, 17),
        )
    )
    source_partition = SimpleNamespace(
        partition=SimpleNamespace(partition_index=0, targets=targets),
        manifest=SimpleNamespace(logical_fingerprint="2" * 64),
    )
    return service.plan_partition0_official_event_evidence(
        source_plan=source_plan, source_partition=source_partition
    )


class _Headers:
    def get(self, key, default=None):
        return "application/json"


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
        return service.SSE_ANNOUNCEMENT_QUERY_URL
