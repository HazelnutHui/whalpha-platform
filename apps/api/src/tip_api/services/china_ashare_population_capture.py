"""Capture and publish the five-year A-share source population."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from tip_api.persistence.china_ashare_identity_lifecycle_package import (
    read_china_ashare_identity_lifecycle_package,
)
from tip_api.persistence.china_ashare_population_package import (
    ChinaAsharePopulationPackageResultV1,
    publish_china_ashare_population_package,
)
from tip_api.providers.china_ashare.baostock_population_adapter import (
    capture_baostock_security_basic,
)
from tip_api.providers.china_ashare.baostock_session import BaoStockClientSession
from tip_api.services.china_ashare_population import build_five_year_population


def capture_and_publish_china_ashare_population(
    *,
    identity_lifecycle_package_path: Path,
    custody_root: Path,
    interval_start: date,
    interval_end: date,
    captured_at: datetime,
) -> ChinaAsharePopulationPackageResultV1:
    identity = read_china_ashare_identity_lifecycle_package(
        package_path=identity_lifecycle_package_path
    )
    with BaoStockClientSession() as session:
        basic = capture_baostock_security_basic(
            session=session, ingested_at=captured_at
        )
    occurrences, report = build_five_year_population(
        identity_lifecycle_package=identity,
        baostock_basic_records=basic,
        interval_start=interval_start,
        interval_end=interval_end,
        evaluated_at=captured_at,
    )
    return publish_china_ashare_population_package(
        custody_root=custody_root,
        identity_lifecycle_package=identity,
        baostock_basic_records=basic,
        occurrences=occurrences,
        report=report,
        created_at=captured_at,
    )
