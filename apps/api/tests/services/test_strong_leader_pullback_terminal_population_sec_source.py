from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult
from tip_api.services import strong_leader_pullback_terminal_population_sec_source as service
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_source,
)


INSTRUMENT_ID = UUID("ff8ae3f6-a3ae-5127-983b-0f94386f0055")


def _plan_result() -> SimpleNamespace:
    specs = (
        (
            "0000876661-25-000952",
            "25-NSE",
            date(2025, 12, 10),
            "xslF25X02/primary_doc.xml",
        ),
        (
            "0001193125-25-315864",
            "8-K",
            date(2025, 12, 11),
            "d77540d8k.htm",
        ),
        (
            "0001193125-25-327599",
            "15-12G",
            date(2025, 12, 22),
            "d45344d1512g.htm",
        ),
    )
    items = []
    for sequence, (accession, form, filing_date, document) in enumerate(specs, 1):
        relation = (
            "after_last_eod_before_provider_delist_candidate"
            if sequence == 1
            else "on_provider_delist_candidate"
            if sequence == 2
            else "after_provider_delist_candidate"
        )
        items.append(
            plan_source.TerminalPopulationSecSourceItemV1(
                request_sequence=sequence,
                instrument_id=INSTRUMENT_ID,
                cik="0001050825",
                accession_number=accession,
                form=form,
                filing_date=filing_date,
                acceptance_datetime=datetime(
                    2025, 12, min(filing_date.day, 22), 16, tzinfo=UTC
                ),
                primary_document=document,
                request_url=plan_source.document_plan._document_url(
                    cik="0001050825",
                    accession=accession,
                    primary_document=document,
                ),
                source_member_name="CIK0001050825.json",
                locator_categories=("direct_lifecycle_form",),
                structured_items=(),
                relation_to_eod_boundary=relation,
            )
        )
    report = SimpleNamespace(
        planned_at=datetime(2026, 9, 14, 10, tzinfo=UTC),
        maximum_requests_per_second=2,
        maximum_retries_per_request=2,
        planned_request_count=3,
        logical_fingerprint="1" * 64,
        items=tuple(items),
    )
    return SimpleNamespace(report=report, report_sha256="2" * 64)


class _FakeTransport:
    def __init__(self, requests: list[str], *, fail: bool = False) -> None:
        self.request_count = 0
        self._requests = requests
        self._fail = fail

    def download(self, url: str, target: Path, **_: object) -> SecDownloadResult:
        self.request_count += 1
        self._requests.append(url)
        if self._fail:
            raise RuntimeError("fixture transport failure")
        payload = f"fixture:{url}".encode()
        target.write_bytes(payload)
        return SecDownloadResult(
            url=url,
            content_type="text/html",
            byte_count=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            retry_count=0,
        )


def _clock():
    value = datetime(2026, 9, 14, 11, tzinfo=UTC)

    def now() -> datetime:
        nonlocal value
        current = value
        value += timedelta(seconds=1)
        return current

    return now


def _config() -> SecProviderConfig:
    return SecProviderConfig(
        user_agent="trading-intelligence-platform test@example.com",
        request_timeout_seconds=Decimal("15"),
        max_requests_per_second=Decimal("2"),
        max_retries=2,
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    custody = tmp_path / "source"
    custody.mkdir(mode=0o700)
    return custody, custody / "source=test"


def test_acquires_three_documents_formally_rereads_and_replays_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service.plan_source,
        "read_strong_leader_pullback_terminal_population_sec_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    requests: list[str] = []
    result = service.acquire_strong_leader_pullback_terminal_population_sec_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport(requests),
        clock=_clock(),
    )

    assert result.status == "published"
    assert result.completed_document_count == 3
    assert result.network_request_count == 3
    assert len(requests) == 3
    assert result.manifest.complete_source_custody is True
    assert result.manifest.content_type_counts == (("text/html", 3),)
    assert not (custody / ".source=test.partial").exists()
    assert all(
        path.stat().st_mode & 0o777 == 0o400
        for path in target.rglob("*")
        if path.is_file()
    )

    requests.clear()
    replay = service.acquire_strong_leader_pullback_terminal_population_sec_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport(requests),
        clock=_clock(),
    )
    assert replay.status == "already_present"
    assert replay.network_request_count == 0
    assert requests == []


def test_failed_atomic_acquisition_leaves_no_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service.plan_source,
        "read_strong_leader_pullback_terminal_population_sec_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    calls = 0

    def factory(_: object) -> _FakeTransport:
        nonlocal calls
        calls += 1
        return _FakeTransport([], fail=calls == 2)

    with pytest.raises(RuntimeError, match="fixture transport failure"):
        service.acquire_strong_leader_pullback_terminal_population_sec_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
            config=_config(),
            implementation_revision="a" * 40,
            transport_factory=factory,
            clock=_clock(),
        )
    assert not target.exists()
    assert not (custody / ".source=test.partial").exists()


def test_tampered_document_fails_formal_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service.plan_source,
        "read_strong_leader_pullback_terminal_population_sec_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    service.acquire_strong_leader_pullback_terminal_population_sec_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )
    document = target / "request=000001" / service.DOCUMENT_FILE
    document.chmod(0o600)
    document.write_bytes(b"tampered")
    document.chmod(0o400)
    with pytest.raises(RuntimeError):
        service.read_strong_leader_pullback_terminal_population_sec_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
        )


def test_acquisition_rejects_a_plan_from_the_future(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    plan.report.planned_at = datetime(2026, 9, 14, 12, tzinfo=UTC)
    monkeypatch.setattr(
        service.plan_source,
        "read_strong_leader_pullback_terminal_population_sec_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    with pytest.raises(
        service.StrongLeaderPullbackTerminalPopulationSecSourceError,
        match="precedes its plan",
    ):
        service.acquire_strong_leader_pullback_terminal_population_sec_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
            config=_config(),
            implementation_revision="a" * 40,
            transport_factory=lambda _: _FakeTransport([]),
            clock=_clock(),
        )
    assert not target.exists()
