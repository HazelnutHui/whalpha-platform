from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.sec.companyfacts_source import (
    COMPANYFACTS_URL,
    SecCompanyfactsFixedIntervalLimiter,
    SecCompanyfactsRangeResult,
    SecCompanyfactsRemoteMetadataV1,
    SecCompanyfactsSourceError,
    acquire_sec_companyfacts_source_package,
    read_sec_companyfacts_source_package,
)
from tip_api.providers.sec.config import SecProviderConfig
from tip_api.providers.sec.submissions_source import (
    SUBMISSIONS_URL,
    acquire_sec_submissions_source_package,
    read_sec_submissions_source_package,
)


NOW = datetime(2026, 9, 10, 15, tzinfo=UTC)


class NoWait(SecCompanyfactsFixedIntervalLimiter):
    def __init__(self) -> None:
        pass

    def wait(self) -> None:
        return None


class FixtureTransport:
    def __init__(self, payload: bytes, url: str) -> None:
        self.payload = payload
        self.url = url

    def head(self, **kwargs: object) -> SecCompanyfactsRemoteMetadataV1:
        assert kwargs["url"] == self.url
        return SecCompanyfactsRemoteMetadataV1(
            url=self.url,
            content_type="application/zip",
            content_length=len(self.payload),
            last_modified=datetime(2026, 9, 10, 4, 34, tzinfo=UTC),
            etag='"fixture"',
            accept_ranges="bytes",
            observed_at=kwargs["observed_at"],  # type: ignore[arg-type]
        )

    def download_range(self, **kwargs: object) -> SecCompanyfactsRangeResult:
        assert kwargs["url"] == self.url
        start = int(kwargs["byte_start"])
        end = int(kwargs["byte_end"])
        selected = self.payload[start : end + 1]
        kwargs["target"].write(selected)  # type: ignore[attr-defined]
        return SecCompanyfactsRangeResult(
            byte_count=len(selected),
            physical_sha256=hashlib.sha256(selected).hexdigest(),
        )


def _archive(*, include_shard: bool = True) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for cik in (1, 2):
            archive.writestr(
                f"CIK{cik:010d}.json",
                json.dumps(
                    {
                        "cik": str(cik),
                        "filings": {
                            "recent": {
                                "accessionNumber": [f"{cik:010d}-26-000001"],
                                "acceptanceDateTime": ["20260909163000"],
                            },
                            "files": [],
                        },
                    }
                ),
            )
        if include_shard:
            archive.writestr(
                "CIK0000000001-submissions-001.json",
                json.dumps(
                    {
                        "accessionNumber": ["0000000001-20-000001"],
                        "filingDate": ["2020-03-01"],
                        "acceptanceDateTime": ["20200301163000"],
                        "form": ["10-K"],
                    }
                ),
            )
            archive.writestr("placeholder.txt", "fixture marker")
    return target.getvalue()


def _config() -> SecProviderConfig:
    return SecProviderConfig(
        user_agent=SecretStr("trading-intelligence-platform test@example.com"),
        request_timeout_seconds=Decimal("15"),
    )


def test_submissions_package_uses_shared_resumable_engine_and_exact_profile(
    tmp_path: Path,
) -> None:
    root = tmp_path / "submissions"
    root.mkdir(mode=0o700)
    package = root / "snapshot=2026-09-10"
    payload = _archive()

    result = acquire_sec_submissions_source_package(
        config=_config(),
        package_path=package,
        approved_custody_root=root,
        transport=FixtureTransport(payload, SUBMISSIONS_URL),
        rate_limiter=NoWait(),
        clock=lambda: NOW,
    )

    assert result.manifest.contract_version == "sec-submissions-source-package/1.0"
    assert result.manifest.source_family == "submissions_bulk_archive"
    assert result.manifest.remote.url == SUBMISSIONS_URL
    assert result.manifest.member_count == 4
    assert result.manifest.unique_cik_count == 2
    assert result.manifest.archive_sha256 == hashlib.sha256(payload).hexdigest()
    assert result.manifest.member_payload_validation_status == "deferred_to_normalization"
    assert read_sec_submissions_source_package(
        package_path=package, approved_custody_root=root
    ) == result.manifest
    with pytest.raises(SecCompanyfactsSourceError, match="profile differs"):
        read_sec_companyfacts_source_package(
            package_path=package, approved_custody_root=root
        )


def test_companyfacts_package_cannot_be_read_as_submissions(tmp_path: Path) -> None:
    root = tmp_path / "companyfacts"
    root.mkdir(mode=0o700)
    package = root / "snapshot=2026-09-10"
    acquire_sec_companyfacts_source_package(
        config=_config(),
        package_path=package,
        approved_custody_root=root,
        transport=FixtureTransport(_archive(include_shard=False), COMPANYFACTS_URL),
        rate_limiter=NoWait(),
        clock=lambda: NOW,
    )

    with pytest.raises(SecCompanyfactsSourceError, match="profile differs"):
        read_sec_submissions_source_package(
            package_path=package, approved_custody_root=root
        )
