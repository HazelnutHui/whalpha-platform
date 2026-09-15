from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.transport import SecDownloadResult
from tip_api.services import strong_leader_pullback_terminal_reference_sec_plan as plan
from tip_api.services import (
    strong_leader_pullback_terminal_reference_sec_source as service,
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
    value = datetime(2026, 9, 15, 13, tzinfo=UTC)

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


def _publish_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    source_root = tmp_path / "submissions"
    package = source_root / "snapshot=2026-09-10"
    package.mkdir(parents=True)
    with zipfile.ZipFile(package / "submissions.zip", "w") as archive:
        for registered in plan._REQUESTS:
            archive.writestr(
                f"CIK{registered['source_cik']}.json",
                json.dumps(
                    {
                        "filings": {
                            "recent": {
                                "accessionNumber": [
                                    registered["accession_number"]
                                ],
                                "form": [registered["form"]],
                                "filingDate": [registered["filing_date"]],
                                "acceptanceDateTime": [
                                    registered["acceptance_datetime"].replace(
                                        "Z", ".000Z"
                                    )
                                ],
                                "primaryDocument": [
                                    registered["submissions_primary_document"]
                                ],
                            }
                        }
                    }
                ),
            )
    monkeypatch.setattr(
        plan,
        "read_sec_submissions_source_package",
        lambda **_: SimpleNamespace(
            logical_fingerprint="1" * 64,
            archive_sha256="2" * 64,
            completed_at=datetime(2026, 9, 10, 15, tzinfo=UTC),
        ),
    )
    plan_custody = tmp_path / "plans"
    plan_custody.mkdir(mode=0o700)
    plan_root = plan_custody / "plan=test"
    plan.publish_strong_leader_pullback_terminal_reference_sec_plan(
        submissions_package_path=package,
        submissions_custody_root=source_root,
        output_root=plan_root,
        output_custody_root=plan_custody,
        implementation_revision="a" * 40,
        planned_at=datetime(2026, 9, 15, 12, tzinfo=UTC),
    )
    return plan_custody, plan_root


def test_acquires_only_five_frozen_documents_and_replays_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_custody, plan_root = _publish_plan(tmp_path, monkeypatch)
    source_custody = tmp_path / "documents"
    source_custody.mkdir(mode=0o700)
    output = source_custody / "source=test"
    requests: list[str] = []

    result = service.acquire_strong_leader_pullback_terminal_reference_sec_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody,
        output_root=output,
        output_custody_root=source_custody,
        config=_config(),
        implementation_revision="a" * 40,
        transport_factory=lambda _: _FakeTransport(requests),
        clock=_clock(),
    )
    replay = service.read_strong_leader_pullback_terminal_reference_sec_source(
        plan_root=plan_root,
        plan_custody_root=plan_custody,
        output_root=output,
        output_custody_root=source_custody,
    )

    assert result.status == "published"
    assert result.completed_document_count == 5
    assert result.network_request_count == 5
    assert len(requests) == 5
    assert replay.manifest == result.manifest
    assert replay.network_request_count == 0
