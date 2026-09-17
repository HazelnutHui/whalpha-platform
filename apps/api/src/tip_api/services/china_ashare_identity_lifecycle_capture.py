"""Capture and publish the bounded A-share identity/lifecycle gate."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tip_api.persistence.china_ashare_identity_lifecycle_package import (
    ChinaAshareIdentityLifecyclePackageResultV1,
    publish_china_ashare_identity_lifecycle_package,
)
from tip_api.persistence.china_ashare_pilot_package import (
    read_china_ashare_pilot_daily_package,
    read_china_ashare_pilot_reference_package,
)
from tip_api.providers.china_ashare.official_identity_evidence_adapter import (
    OfficialIdentityHttpFetcher,
    capture_official_identity_sources,
)
from tip_api.services.china_ashare_identity_lifecycle import (
    build_identity_lifecycle_report_for_pilot,
    validate_official_identity_artifacts_for_pilot,
)


def capture_and_publish_china_ashare_identity_lifecycle(
    *,
    reference_package_path: Path,
    daily_package_path: Path,
    custody_root: Path,
    captured_at: datetime,
    fetcher: OfficialIdentityHttpFetcher | None = None,
) -> ChinaAshareIdentityLifecyclePackageResultV1:
    reference = read_china_ashare_pilot_reference_package(
        package_path=reference_package_path
    )
    daily = read_china_ashare_pilot_daily_package(package_path=daily_package_path)
    sources = capture_official_identity_sources(
        retrieved_at=captured_at,
        fetcher=fetcher,
    )
    retained_and_reconciled = validate_official_identity_artifacts_for_pilot(
        reference_package=reference,
        captured_sources=sources,
    )
    report = build_identity_lifecycle_report_for_pilot(
        reference_package=reference,
        daily_package=daily,
        exact_official_source_bytes_retained=retained_and_reconciled,
        evaluated_at=captured_at,
    )
    return publish_china_ashare_identity_lifecycle_package(
        custody_root=custody_root,
        captured_sources=sources,
        report=report,
        created_at=captured_at,
    )
