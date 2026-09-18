from __future__ import annotations

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

from tip_api.contracts.china_ashare.v1.cninfo_event_evidence import (
    ChinaAshareCninfoParseStatus,
    ChinaAshareCninfoRequestKind,
)
from tip_api.persistence.china_ashare_cninfo_event_evidence import (
    publish_cninfo_event_capture,
    publish_cninfo_event_plan,
    read_cninfo_event_capture,
    read_cninfo_event_plan,
)
from tip_api.services import china_ashare_cninfo_event_evidence as service


def test_cninfo_plan_is_one_sample_six_requests_and_outcome_blind() -> None:
    plan = service.plan_cninfo_event_sample(source_plan=_source_plan())

    assert plan.partition_index == 47
    assert plan.source_security_id == "sz.000001"
    assert len(plan.queries) == 6
    assert sum(
        item.request_kind is ChinaAshareCninfoRequestKind.SECURITY_MAP
        for item in plan.queries
    ) == 1
    assert all(item.maximum_attempts == 1 for item in plan.queries)
    assert plan.outcome_read_count == 0
    assert plan.historical_coverage_authorized is False


def test_cninfo_mapping_and_announcement_query_are_official_and_exact(
    monkeypatch, tmp_path
) -> None:
    plan = service.plan_cninfo_event_sample(source_plan=_source_plan())
    map_query = next(
        item
        for item in plan.queries
        if item.request_kind is ChinaAshareCninfoRequestKind.SECURITY_MAP
    )
    query = next(item for item in plan.queries if item.keyword == "风险警示")
    map_raw = json.dumps(
        {"stockList": [{"code": "000001", "orgId": "gssz0000001"}]}
    ).encode()
    event_raw = json.dumps(
        {
            "totalAnnouncement": 1,
            "announcements": [
                {
                    "secCode": "000001",
                    "announcementId": "123",
                    "announcementTitle": "关于撤销股票交易风险警示的公告",
                    "announcementTime": 1_700_000_000_000,
                    "adjunctUrl": "finalpage/2023-01-01/test.PDF",
                }
            ],
        },
        ensure_ascii=False,
    ).encode()
    responses = iter(
        (
            _Response(map_raw, plan.security_map_url),
            _Response(event_raw, plan.announcement_query_url),
        )
    )
    monkeypatch.setattr(service, "urlopen", lambda request, timeout: next(responses))

    map_capture, actual_map_raw = service.capture_cninfo_security_map(
        plan=plan,
        query=map_query,
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    event_capture, actual_event_raw = service.capture_cninfo_announcement_query(
        plan=plan,
        query=query,
        resolved_org_id=map_capture.resolved_org_id,
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    root = publish_cninfo_event_plan(
        custody_root=tmp_path / "cninfo", plan=plan
    )
    for capture, raw in (
        (map_capture, actual_map_raw),
        (event_capture, actual_event_raw),
    ):
        publish_cninfo_event_capture(
            plan_root=root, capture=capture, raw_bytes=raw
        )
        assert read_cninfo_event_capture(
            plan_root=root, query_id=capture.query_id
        ) == (capture, raw)

    assert read_cninfo_event_plan(plan_root=root) == plan
    assert map_capture.parse_status is ChinaAshareCninfoParseStatus.PARSED
    assert map_capture.resolved_org_id == "gssz0000001"
    assert event_capture.parse_status is ChinaAshareCninfoParseStatus.PARSED
    assert len(event_capture.announcements) == 1
    assert event_capture.announcements[0].document_url.startswith(
        service.CNINFO_STATIC_DOCUMENT_BASE
    )
    assert root.stat().st_mode & 0o777 == 0o700


def test_cninfo_antibot_is_typed_and_not_retried(monkeypatch) -> None:
    plan = service.plan_cninfo_event_sample(source_plan=_source_plan())
    query = next(
        item
        for item in plan.queries
        if item.request_kind is ChinaAshareCninfoRequestKind.SECURITY_MAP
    )
    calls = 0

    def blocked(request, timeout):
        nonlocal calls
        calls += 1
        return _Response(b"<script>acw_sc__v2</script>", plan.security_map_url)

    monkeypatch.setattr(service, "urlopen", blocked)
    capture, raw = service.capture_cninfo_security_map(
        plan=plan,
        query=query,
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
    )

    assert raw is not None
    assert calls == 1
    assert capture.attempt_count == 1
    assert capture.parse_status is ChinaAshareCninfoParseStatus.ANTIBOT_BLOCKED
    assert capture.blocker_code == "cninfo_antibot_challenge"


def test_cninfo_null_announcements_is_canonical_empty_result() -> None:
    raw = json.dumps(
        {"totalAnnouncement": 0, "announcements": None}
    ).encode()

    status, announcements, conflicts, blocker = service._parse_announcements(
        raw=raw, keyword="风险警示"
    )

    assert status is ChinaAshareCninfoParseStatus.PARSED
    assert announcements == ()
    assert conflicts == ()
    assert blocker is None


def test_cninfo_replay_reparses_exact_bytes_without_checkpoint_mutation(
    monkeypatch,
) -> None:
    plan = service.plan_cninfo_event_sample(source_plan=_source_plan())
    query = next(item for item in plan.queries if item.keyword == "风险警示")
    raw = json.dumps(
        {"totalAnnouncement": 0, "announcements": None}
    ).encode()
    monkeypatch.setattr(
        service,
        "urlopen",
        lambda request, timeout: _Response(raw, plan.announcement_query_url),
    )
    captured, captured_raw = service.capture_cninfo_announcement_query(
        plan=plan,
        query=query,
        resolved_org_id="gssz0000001",
        retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
    )

    replay = service.replay_cninfo_capture(
        plan=plan, query=query, capture=captured, raw=captured_raw
    )

    assert replay.parse_status is ChinaAshareCninfoParseStatus.PARSED
    assert replay.announcements == ()
    assert replay.raw_sha256 == captured.raw_sha256


def _source_plan():
    partitions = [
        SimpleNamespace(
            partition_index=index,
            logical_fingerprint=f"{index + 2:064x}",
            targets=(),
        )
        for index in range(48)
    ]
    partitions[47] = SimpleNamespace(
        partition_index=47,
        logical_fingerprint="2" * 64,
        targets=(SimpleNamespace(source_security_id="sz.000001"),),
    )
    return SimpleNamespace(
        plan=SimpleNamespace(
            logical_fingerprint="1" * 64,
            interval_start=date(2021, 9, 16),
            interval_end=date(2026, 9, 16),
            partitions=tuple(partitions),
        )
    )


class _Headers:
    def get(self, key, default=None):
        return "application/json"


class _Response:
    status = 200
    headers = _Headers()

    def __init__(self, payload, url):
        self.payload = payload
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, maximum):
        return self.payload

    def geturl(self):
        return self.url
