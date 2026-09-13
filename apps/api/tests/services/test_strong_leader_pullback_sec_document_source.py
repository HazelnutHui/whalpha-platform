from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult
from tip_api.services import strong_leader_pullback_sec_document_plan as plan_service
from tip_api.services import strong_leader_pullback_sec_document_source as service


def _plan_result() -> SimpleNamespace:
    cases = [
        SimpleNamespace(
            instrument_id=UUID(int=index + 1),
            cik=f"{index + 1:010d}",
            candidate_filings=[],
        )
        for index in range(64)
    ]
    for index in range(219):
        cases[index % 64].candidate_filings.append(
            SimpleNamespace(
                accession_number=f"9999999999-26-{index + 1:06d}",
                form="25-NSE" if index < 64 else "15-12G",
                filing_date=date(2026, 6, 1) + timedelta(days=index // 64),
                acceptance_datetime=datetime(2026, 6, 1, 20, tzinfo=UTC)
                + timedelta(seconds=index),
                primary_document=f"documents/filing-{index}.htm",
                locator_categories=("direct_lifecycle_form",),
                items=(),
                relation_to_last_observation="on_last_observation",
            )
        )
    pilot = SimpleNamespace(
        report=SimpleNamespace(
            completion_status=(
                "metadata_locator_complete_terminal_evidence_incomplete"
            ),
            document_request_count=0,
            terminal_outcome_count=0,
            research_admission_count=0,
            cases=tuple(cases),
            logical_fingerprint="1" * 64,
            evaluated_at=datetime(2026, 9, 13, 13, 42, 15, tzinfo=UTC),
        ),
        report_sha256="2" * 64,
    )
    plan = plan_service._compose_plan(
        pilot=pilot,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 13, 14, tzinfo=UTC),
    )
    return SimpleNamespace(
        plan=plan,
        plan_sha256="3" * 64,
    )


class _FakeTransport:
    def __init__(self, requests: list[str]) -> None:
        self.request_count = 0
        self._requests = requests

    def download(self, url: str, target: Path, **_: object) -> SecDownloadResult:
        self.request_count += 1
        self._requests.append(url)
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
    value = datetime(2026, 9, 13, 14, 30, tzinfo=UTC)

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


def test_acquisition_resumes_without_redownloading_and_formally_rereads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    requests: list[str] = []
    factory_count = 0

    def factory(_: object) -> _FakeTransport:
        nonlocal factory_count
        factory_count += 1
        return _FakeTransport(requests)

    first = service.acquire_strong_leader_pullback_sec_document_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="b" * 40,
        maximum_new_documents=1,
        transport_factory=factory,
        clock=_clock(),
    )
    assert first.status == "in_progress"
    assert first.completed_document_count == 1
    assert first.new_document_count == 1
    assert not target.exists()
    assert (custody / ".source=test.partial" / "request=000001").is_dir()

    completed = service.acquire_strong_leader_pullback_sec_document_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="b" * 40,
        transport_factory=factory,
        clock=_clock(),
    )
    assert completed.status == "published"
    assert completed.completed_document_count == 219
    assert completed.new_document_count == 218
    assert len(requests) == 219
    assert len(set(requests)) == 219
    assert factory_count == 219
    assert not (custody / ".source=test.partial").exists()
    assert completed.manifest is not None
    assert completed.manifest.content_type_counts == (("text/html", 219),)
    assert completed.manifest.external_request_count == 219
    assert completed.manifest.retry_count == 0

    reread = service.read_strong_leader_pullback_sec_document_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
    )
    assert reread.manifest == completed.manifest
    modes = Counter(
        path.stat().st_mode & 0o777
        for path in target.rglob("*")
        if path.is_file()
    )
    assert modes == Counter({0o400: 439})


def test_completed_partial_is_adopted_without_a_network_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    requests: list[str] = []
    factory = lambda _: _FakeTransport(requests)
    service.acquire_strong_leader_pullback_sec_document_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="b" * 40,
        transport_factory=factory,
        clock=_clock(),
    )
    partial = custody / ".source=test.partial"
    target.replace(partial)
    requests.clear()

    adopted = service.acquire_strong_leader_pullback_sec_document_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="b" * 40,
        transport_factory=factory,
        clock=_clock(),
    )
    assert adopted.status == "published"
    assert adopted.new_document_count == 0
    assert adopted.network_request_count == 0
    assert requests == []
    assert target.is_dir()
    assert not partial.exists()


def test_tampered_document_and_unknown_partial_member_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_sec_document_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    service.acquire_strong_leader_pullback_sec_document_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="b" * 40,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )
    document = target / "request=000001" / service.DOCUMENT_FILE
    document.chmod(0o600)
    document.write_bytes(b"tampered")
    document.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecDocumentSourceError):
        service.read_strong_leader_pullback_sec_document_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
        )

    other_custody = tmp_path / "other"
    other_custody.mkdir(mode=0o700)
    partial = other_custody / ".source=test.partial"
    partial.mkdir(mode=0o700)
    unexpected = partial / "unexpected"
    unexpected.write_bytes(b"x")
    unexpected.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackSecDocumentSourceError):
        service.acquire_strong_leader_pullback_sec_document_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=other_custody / "source=test",
            output_custody_root=other_custody,
            config=_config(),
            implementation_revision="b" * 40,
            transport_factory=lambda _: _FakeTransport([]),
            clock=_clock(),
        )
