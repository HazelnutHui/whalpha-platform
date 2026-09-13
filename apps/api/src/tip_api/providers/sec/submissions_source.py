"""Profile-bound custody for the official SEC Submissions bulk archive."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from tip_api.providers.sec.bulk_sources import SUBMISSIONS_URL
from tip_api.providers.sec.companyfacts_source import (
    ProgressCallback,
    SecArchiveSourceProfile,
    SecCompanyfactsFixedIntervalLimiter,
    SecCompanyfactsPackageResult,
    SecCompanyfactsSourceManifestV1,
    SecCompanyfactsTransport,
    acquire_sec_resumable_zip_source_package,
    read_sec_resumable_zip_source_package,
)
from tip_api.providers.sec.config import SecProviderConfig


CONTRACT_VERSION = "sec-submissions-source-package/1.0"
CHECKPOINT_VERSION = "sec-submissions-source-checkpoint/1.0"
ARCHIVE_FILE = "submissions.zip"
_CIK_MEMBER = re.compile(
    r"CIK(?P<cik>[0-9]{10})(?:-submissions-(?P<shard>[0-9]{3}))?\.json\Z"
)

SUBMISSIONS_PROFILE = SecArchiveSourceProfile(
    source_label="Submissions",
    contract_version=CONTRACT_VERSION,
    checkpoint_version=CHECKPOINT_VERSION,
    source_family="submissions_bulk_archive",
    url=SUBMISSIONS_URL,
    archive_file=ARCHIVE_FILE,
    member_pattern=_CIK_MEMBER,
    allowed_non_cik_members=frozenset({"placeholder.txt"}),
    require_unique_cik_per_member=False,
    require_root_member_per_cik=True,
    maximum_member_count=1_000_000,
    maximum_member_bytes=64 * 1024 * 1024,
    maximum_total_uncompressed_bytes=128 * 1024 * 1024 * 1024,
    maximum_compression_ratio=200,
    source_availability_semantics=(
        "snapshot_observed_now_acceptance_timestamps_preserved_downstream"
    ),
)

SecSubmissionsSourceManifestV1 = SecCompanyfactsSourceManifestV1
SecSubmissionsPackageResult = SecCompanyfactsPackageResult


def acquire_sec_submissions_source_package(
    *,
    config: SecProviderConfig,
    package_path: Path,
    approved_custody_root: Path,
    transport: SecCompanyfactsTransport | None = None,
    rate_limiter: SecCompanyfactsFixedIntervalLimiter | None = None,
    clock: Callable[[], datetime] | None = None,
    progress: ProgressCallback | None = None,
) -> SecSubmissionsPackageResult:
    """Acquire or resume one exact official SEC Submissions ZIP snapshot."""

    return acquire_sec_resumable_zip_source_package(
        profile=SUBMISSIONS_PROFILE,
        config=config,
        package_path=package_path,
        approved_custody_root=approved_custody_root,
        transport=transport,
        rate_limiter=rate_limiter,
        clock=clock,
        progress=progress,
    )


def read_sec_submissions_source_package(
    *, package_path: Path, approved_custody_root: Path
) -> SecSubmissionsSourceManifestV1:
    """Formally reread an immutable profile-bound Submissions package."""

    return read_sec_resumable_zip_source_package(
        profile=SUBMISSIONS_PROFILE,
        package_path=package_path,
        approved_custody_root=approved_custody_root,
    )
