from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source as service,
)


def _plan_result() -> SimpleNamespace:
    decision = SimpleNamespace(
        request_sequence=174,
        target_instrument_id=UUID(int=1),
        proposed_consideration_instrument_id=UUID(int=2),
        proposed_cik="0000035527",
        replacement_registration_accession_number="0001193125-25-297171",
        replacement_registration_document_url=(
            "https://www.sec.gov/Archives/edgar/data/35527/"
            "000119312525297171/d942117d424b3.htm"
        ),
        new_source_request_count=1,
        logical_fingerprint="1" * 64,
    )
    return SimpleNamespace(
        report=SimpleNamespace(
            planned_source_document_count=1,
            decisions=(decision,),
            logical_fingerprint="2" * 64,
        ),
        report_sha256="3" * 64,
    )


class _FakeTransport:
    def __init__(self, requests: list[str], *, wrong_url: bool = False) -> None:
        self.request_count = 0
        self.requests = requests
        self.wrong_url = wrong_url

    def download(self, url: str, target: Path, **_: object) -> SecDownloadResult:
        self.request_count += 1
        self.requests.append(url)
        payload = f"fixture:{url}".encode()
        target.write_bytes(payload)
        return SecDownloadResult(
            url="https://www.sec.gov/wrong" if self.wrong_url else url,
            content_type="text/html",
            byte_count=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            retry_count=0,
        )


def _clock():
    value = datetime(2026, 9, 14, 6, tzinfo=UTC)

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
    return custody, custody / "source=fixture"


def _patch_plan(monkeypatch: pytest.MonkeyPatch, plan: object) -> None:
    monkeypatch.setattr(
        service.residual_plan,
        "read_strong_leader_pullback_listed_consideration_residual_source_plan",
        lambda **_: plan,
    )


def test_acquires_exactly_one_document_and_formally_rereads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    _patch_plan(monkeypatch, plan)
    custody, target = _roots(tmp_path)
    requests: list[str] = []

    result = service.acquire_strong_leader_pullback_listed_consideration_residual_source(
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
    assert result.new_document_count == result.network_request_count == 1
    assert len(requests) == 1
    assert result.manifest.completed_document_count == 1
    assert result.manifest.consideration_security_identity_assignment_count == 0
    assert result.manifest.terminal_value_count == 0
    reread = service.read_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
    )
    assert reread.manifest == result.manifest
    assert all(
        item.stat().st_mode & 0o777 == 0o400
        for item in target.rglob("*")
        if item.is_file()
    )
    replay_requests: list[str] = []
    replay = service.acquire_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport(replay_requests),
        clock=_clock(),
    )
    assert replay.status == "already_present"
    assert replay.new_document_count == replay.network_request_count == 0
    assert replay_requests == []


def test_completed_partial_is_adopted_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    _patch_plan(monkeypatch, plan)
    custody, target = _roots(tmp_path)
    service.acquire_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )
    partial = custody / ".source=fixture.partial"
    target.replace(partial)
    requests: list[str] = []

    adopted = service.acquire_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport(requests),
        clock=_clock(),
    )

    assert adopted.status == "published"
    assert adopted.new_document_count == adopted.network_request_count == 0
    assert requests == []
    assert target.is_dir() and not partial.exists()


def test_interrupted_staging_is_removed_before_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    _patch_plan(monkeypatch, plan)
    custody, target = _roots(tmp_path)
    partial = custody / ".source=fixture.partial"
    partial.mkdir(mode=0o700)
    staging = partial / ".request=000174.partial"
    staging.mkdir(mode=0o700)
    fragment = staging / "fragment"
    fragment.write_bytes(b"incomplete")
    fragment.chmod(0o400)

    result = service.acquire_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )

    assert result.status == "published"
    assert not staging.exists()


def test_changed_response_and_tampered_document_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan_result()
    _patch_plan(monkeypatch, plan)
    custody, target = _roots(tmp_path)
    with pytest.raises(RuntimeError):
        service.acquire_strong_leader_pullback_listed_consideration_residual_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
            config=_config(),
            implementation_revision="a" * 40,
            transport_factory=lambda _: _FakeTransport([], wrong_url=True),
            clock=_clock(),
        )
    service.acquire_strong_leader_pullback_listed_consideration_residual_source(
        plan_root=Path("/unused/plan"),
        plan_custody_root=Path("/unused"),
        output_root=target,
        output_custody_root=custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport([]),
        clock=_clock(),
    )
    document = target / "request=000174" / base_document_name()
    document.chmod(0o600)
    document.write_bytes(b"tampered")
    document.chmod(0o400)
    with pytest.raises(RuntimeError):
        service.read_strong_leader_pullback_listed_consideration_residual_source(
            plan_root=Path("/unused/plan"),
            plan_custody_root=Path("/unused"),
            output_root=target,
            output_custody_root=custody,
        )


def base_document_name() -> str:
    return service.base.DOCUMENT_FILE
