from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.sec.companyfacts_source import (
    ARCHIVE_FILE,
    CHECKPOINT_FILE,
    COMPANYFACTS_URL,
    ProgressCallback,
    SecCompanyfactsFixedIntervalLimiter,
    SecCompanyfactsPackageResult,
    SecCompanyfactsRangeResult,
    SecCompanyfactsRemoteMetadataV1,
    SecCompanyfactsSourceError,
    acquire_sec_companyfacts_source_package,
    read_sec_companyfacts_source_package,
)
from tip_api.providers.sec.config import SecProviderConfig


NOW = datetime(2026, 9, 10, 13, tzinfo=UTC)


class NoWait(SecCompanyfactsFixedIntervalLimiter):
    def __init__(self) -> None:
        pass

    def wait(self) -> None:
        return None


class FixtureTransport:
    def __init__(
        self,
        payload: bytes,
        *,
        fail_first_range: bool = False,
        changed_head_on_resume: bool = False,
    ) -> None:
        self.payload = payload
        self.fail_first_range = fail_first_range
        self.changed_head_on_resume = changed_head_on_resume
        self.head_count = 0
        self.range_count = 0

    def head(self, **kwargs: object) -> SecCompanyfactsRemoteMetadataV1:
        self.head_count += 1
        changed = self.changed_head_on_resume and self.head_count > 1
        return SecCompanyfactsRemoteMetadataV1(
            url=COMPANYFACTS_URL,
            content_type="application/zip",
            content_length=len(self.payload) + (1 if changed else 0),
            last_modified=(
                datetime(2026, 9, 11, 3, tzinfo=UTC)
                if changed
                else datetime(2026, 9, 10, 3, tzinfo=UTC)
            ),
            etag='"changed"' if changed else '"fixture"',
            accept_ranges="bytes",
            observed_at=kwargs["observed_at"],  # type: ignore[arg-type]
        )

    def download_range(self, **kwargs: object) -> SecCompanyfactsRangeResult:
        self.range_count += 1
        start = int(kwargs["byte_start"])
        end = int(kwargs["byte_end"])
        target = kwargs["target"]
        selected = self.payload[start : end + 1]
        if self.fail_first_range and self.range_count == 1:
            target.write(selected[: max(1, len(selected) // 2)])  # type: ignore[attr-defined]
            raise SecCompanyfactsSourceError("fixture interruption")
        target.write(selected)  # type: ignore[attr-defined]
        return SecCompanyfactsRangeResult(
            byte_count=len(selected),
            physical_sha256=hashlib.sha256(selected).hexdigest(),
        )


def _archive(*, unsafe_member: bool = False) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("../escape.json" if unsafe_member else "CIK0000000001.json", b'{"cik":1}')
        archive.writestr("CIK0000000002.json", b'{"cik":2}')
    return target.getvalue()


def _config() -> SecProviderConfig:
    return SecProviderConfig(
        user_agent=SecretStr("trading-intelligence-platform test@example.com"),
        request_timeout_seconds=Decimal("15"),
    )


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "companyfacts"
    root.mkdir(mode=0o700)
    return root


def _acquire(
    root: Path,
    transport: FixtureTransport,
    *,
    progress: ProgressCallback | None = None,
) -> SecCompanyfactsPackageResult:
    return acquire_sec_companyfacts_source_package(
        config=_config(),
        package_path=root / "snapshot=2026-09-10",
        approved_custody_root=root,
        transport=transport,
        rate_limiter=NoWait(),
        clock=lambda: NOW,
        progress=progress,
    )


def test_companyfacts_package_is_resumable_immutable_and_formally_readable(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payload = _archive()
    checkpoints: list[tuple[int, int]] = []
    result = _acquire(
        root,
        FixtureTransport(payload),
        progress=lambda _chunk, committed, total: checkpoints.append(
            (committed, total)
        ),
    )

    assert result.status == "published"
    assert result.manifest.archive_bytes == len(payload)
    assert result.manifest.archive_sha256 == hashlib.sha256(payload).hexdigest()
    assert checkpoints == [(len(payload), len(payload))]
    assert result.manifest.member_count == 2
    assert result.manifest.unique_cik_count == 2
    assert result.manifest.request_count == 2
    assert result.manifest.external_request_count == 2
    assert result.manifest.canonical_data_write_count == 0
    assert result.manifest.member_payload_validation_status == "deferred_to_normalization"
    assert result.package_path.stat().st_mode & 0o777 == 0o700
    assert all(
        item.stat().st_mode & 0o777 in {0o400, 0o600}
        for item in root.rglob("*")
        if item.is_file()
    )
    assert read_sec_companyfacts_source_package(
        package_path=result.package_path, approved_custody_root=root
    ) == result.manifest
    assert _acquire(root, FixtureTransport(payload)).status == "already_present"


def test_interrupted_range_is_truncated_to_checkpoint_before_resume(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payload = _archive()
    first = FixtureTransport(payload, fail_first_range=True)
    with pytest.raises(SecCompanyfactsSourceError, match="fixture interruption"):
        _acquire(root, first)

    partial = root / ".snapshot=2026-09-10.partial"
    assert (partial / ARCHIVE_FILE).stat().st_size > 0
    assert (partial / CHECKPOINT_FILE).stat().st_mode & 0o777 == 0o600

    checkpoints: list[tuple[int, int]] = []
    result = _acquire(
        root,
        FixtureTransport(payload),
        progress=lambda _chunk, committed, total: checkpoints.append(
            (committed, total)
        ),
    )
    assert result.status == "recovered_and_published"
    assert result.manifest.request_count == 3
    assert result.manifest.head_request_count == 2
    assert result.manifest.archive_sha256 == hashlib.sha256(payload).hexdigest()
    assert checkpoints == [(len(payload), len(payload))]


def test_resume_stops_on_remote_object_drift_without_publishing(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payload = _archive()
    first = FixtureTransport(payload, fail_first_range=True)
    with pytest.raises(SecCompanyfactsSourceError):
        _acquire(root, first)

    drift = FixtureTransport(payload, changed_head_on_resume=True)
    drift.head_count = 1
    with pytest.raises(SecCompanyfactsSourceError, match="remote object changed"):
        _acquire(root, drift)
    assert not (root / "snapshot=2026-09-10").exists()
    assert (root / ".snapshot=2026-09-10.partial").exists()


def test_unsafe_zip_member_stops_before_package_publication(tmp_path: Path) -> None:
    root = _root(tmp_path)
    with pytest.raises(SecCompanyfactsSourceError, match="member is unsafe"):
        _acquire(root, FixtureTransport(_archive(unsafe_member=True)))
    assert not (root / "snapshot=2026-09-10").exists()


def test_formal_reader_detects_archive_tamper(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = _acquire(root, FixtureTransport(_archive()))
    archive = result.package_path / ARCHIVE_FILE
    archive.chmod(0o600)
    with archive.open("ab") as handle:
        handle.write(b"tamper")
    archive.chmod(0o400)

    with pytest.raises(SecCompanyfactsSourceError, match="archive hash differs"):
        read_sec_companyfacts_source_package(
            package_path=result.package_path, approved_custody_root=root
        )


def test_completed_partial_is_adopted_without_another_request(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = _acquire(root, FixtureTransport(_archive()))
    partial = root / ".snapshot=2026-09-10.partial"
    result.package_path.replace(partial)
    transport = FixtureTransport(_archive())

    recovered = _acquire(root, transport)

    assert recovered.status == "recovered_and_published"
    assert transport.head_count == 0
    assert transport.range_count == 0
    assert recovered.manifest == result.manifest
