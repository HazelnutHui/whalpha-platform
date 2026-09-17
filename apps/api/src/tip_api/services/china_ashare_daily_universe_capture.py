"""Build and publish the bounded A-share daily Universe package."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tip_api.persistence.china_ashare_daily_universe_package import (
    ChinaAshareDailyUniversePackageResultV1,
    publish_china_ashare_daily_universe_package,
)
from tip_api.persistence.china_ashare_identity_lifecycle_package import (
    read_china_ashare_identity_lifecycle_package,
)
from tip_api.persistence.china_ashare_pilot_package import (
    read_china_ashare_pilot_daily_package,
)
from tip_api.services.china_ashare_daily_universe import (
    build_daily_universe_for_pilot,
)


def build_and_publish_china_ashare_daily_universe(
    *,
    daily_package_path: Path,
    identity_lifecycle_package_path: Path,
    custody_root: Path,
    evaluated_at: datetime,
) -> ChinaAshareDailyUniversePackageResultV1:
    daily = read_china_ashare_pilot_daily_package(package_path=daily_package_path)
    identity = read_china_ashare_identity_lifecycle_package(
        package_path=identity_lifecycle_package_path
    )
    decisions, report = build_daily_universe_for_pilot(
        daily_package=daily,
        identity_lifecycle_package=identity,
        evaluated_at=evaluated_at,
    )
    return publish_china_ashare_daily_universe_package(
        custody_root=custody_root,
        decisions=decisions,
        report=report,
        created_at=evaluated_at,
    )
