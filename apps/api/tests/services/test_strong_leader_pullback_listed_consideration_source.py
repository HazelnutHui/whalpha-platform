from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult
from tip_api.services import strong_leader_pullback_listed_consideration_source as service


def _plan_result() -> SimpleNamespace:
    decisions = tuple(
        SimpleNamespace(
            request_sequence=index,
            target_instrument_id=UUID(int=index),
            proposed_consideration_instrument_id=UUID(int=100 + index),
            proposed_cik=f"{index:010d}",
            registration_accession_number=f"9999999999-26-{index:06d}",
            registration_document_url=(
                "https://www.sec.gov/Archives/edgar/data/"
                f"{index}/999999999926{index:06d}/filing-{index}.htm"
            ),
            logical_fingerprint=f"{index:064x}",
        )
        for index in range(1, 13)
    )
    return SimpleNamespace(
        report=SimpleNamespace(
            decisions=decisions,
            logical_fingerprint="a" * 64,
        ),
        report_sha256="b" * 64,
    )


class _FakeTransport:
    def __init__(self, requests: list[str], *, wrong_url: bool = False) -> None:
        self.request_count = 0
        self._requests = requests
        self._wrong_url = wrong_url

    def download(self, url: str, target: Path, **_: object) -> SecDownloadResult:
        self.request_count += 1
        self._requests.append(url)
        payload = f"fixture:{url}".encode()
        target.write_bytes(payload)
        return SecDownloadResult(
            url="https://www.sec.gov/wrong" if self._wrong_url else url,
            content_type="text/html",
            byte_count=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            retry_count=0,
        )


def _clock():
    value = datetime(2026, 9, 14, 20, tzinfo=UTC)

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


def test_acquisition_resumes_and_formally_rereads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_listed_consideration_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    requests: list[str] = []
    factory = lambda _: _FakeTransport(requests)

    first = service.acquire_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="c" * 40,
        maximum_new_documents=1,
        transport_factory=factory,
        clock=_clock(),
    )
    assert first.status == "in_progress"
    assert first.completed_document_count == first.new_document_count == 1
    assert not target.exists()

    completed = service.acquire_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="c" * 40,
        transport_factory=factory,
        clock=_clock(),
    )
    assert completed.status == "published"
    assert completed.completed_document_count == 12
    assert completed.new_document_count == 11
    assert len(requests) == len(set(requests)) == 12
    assert completed.manifest is not None
    assert completed.manifest.content_type_counts == (("text/html", 12),)
    assert completed.manifest.consideration_security_identity_assignment_count == 0
    assert completed.manifest.terminal_value_count == 0

    reread = service.read_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
    )
    assert reread.manifest == completed.manifest
    assert Counter(
        path.stat().st_mode & 0o777 for path in target.rglob("*") if path.is_file()
    ) == Counter({0o400: 25})


def test_completed_partial_is_adopted_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_listed_consideration_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    requests: list[str] = []
    factory = lambda _: _FakeTransport(requests)
    service.acquire_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="c" * 40,
        transport_factory=factory,
        clock=_clock(),
    )
    partial = custody / ".source=test.partial"
    target.replace(partial)
    requests.clear()

    adopted = service.acquire_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="c" * 40,
        transport_factory=factory,
        clock=_clock(),
    )
    assert adopted.status == "published"
    assert adopted.new_document_count == adopted.network_request_count == 0
    assert requests == []
    assert target.is_dir() and not partial.exists()


def test_interrupted_staging_is_removed_before_safe_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_listed_consideration_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    partial = custody / ".source=test.partial"
    partial.mkdir(mode=0o700)
    staging = partial / ".request=000001.partial"
    staging.mkdir(mode=0o700)
    fragment = staging / "fragment"
    fragment.write_bytes(b"incomplete")
    fragment.chmod(0o400)

    result = service.acquire_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="c" * 40,
        maximum_new_documents=1,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )
    assert result.status == "in_progress"
    assert not staging.exists()
    assert (partial / "request=000001").is_dir()


def test_changed_response_and_tampered_document_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    monkeypatch.setattr(
        service,
        "read_strong_leader_pullback_listed_consideration_source_plan",
        lambda **_: plan,
    )
    custody, target = _roots(tmp_path)
    with pytest.raises(service.StrongLeaderPullbackListedConsiderationSourceError):
        service.acquire_strong_leader_pullback_listed_consideration_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
            config=_config(),
            implementation_revision="c" * 40,
            transport_factory=lambda _: _FakeTransport([], wrong_url=True),
            clock=_clock(),
        )
    assert not (custody / ".source=test.partial" / ".request=000001.partial").exists()

    service.acquire_strong_leader_pullback_listed_consideration_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="c" * 40,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )
    document = target / "request=000001" / service.DOCUMENT_FILE
    document.chmod(0o600)
    document.write_bytes(b"tampered")
    document.chmod(0o400)
    with pytest.raises(service.StrongLeaderPullbackListedConsiderationSourceError):
        service.read_strong_leader_pullback_listed_consideration_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
        )
