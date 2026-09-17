"""Explicit bounded capture for A-share corporate-action reconciliation evidence."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from tip_api.persistence.china_ashare_corporate_action_package import (
    ChinaAshareCorporateActionPackageResultV1,
    publish_china_ashare_corporate_action_package,
)
from tip_api.persistence.china_ashare_pilot_package import (
    read_china_ashare_pilot_daily_package,
)
from tip_api.providers.china_ashare.baostock_adapter import (
    BaoStockAshareSourceAdapter,
)
from tip_api.providers.china_ashare.baostock_session import BaoStockClientSession
from tip_api.providers.china_ashare.cninfo_corporate_action_adapter import (
    AkshareTransportCninfoCorporateActionFetcher,
    CninfoCorporateActionHttpFetcher,
    capture_cninfo_corporate_actions,
    capture_cninfo_rights_issues,
)
from tip_api.providers.china_ashare.protocol import ChinaAshareSourceDailyQuery
from tip_api.services.china_ashare_corporate_action_reconciliation import (
    build_corporate_action_reconciliation_for_pilot,
    capture_ths_distribution_crosschecks,
)
from tip_api.services.china_ashare_pilot_reference import (
    build_china_ashare_pilot_identity_bindings,
)


FULL_ADJUSTMENT_HISTORY_START = date(1990, 1, 1)


def capture_and_publish_china_ashare_corporate_action_evidence(
    *,
    daily_package_path: Path,
    custody_root: Path,
    captured_at: datetime,
    cninfo_fetcher: CninfoCorporateActionHttpFetcher | None = None,
) -> ChinaAshareCorporateActionPackageResultV1:
    """Capture exact primary bytes, independent terms, and full factor history."""

    daily_package = read_china_ashare_pilot_daily_package(
        package_path=daily_package_path
    )
    bindings = build_china_ashare_pilot_identity_bindings(
        daily_package.captured.identity_decisions
    )
    if not bindings:
        raise ValueError("daily package has no bound identities")
    active_fetcher = cninfo_fetcher or AkshareTransportCninfoCorporateActionFetcher()
    captured_sources = []
    for binding in bindings:
        captured_sources.extend(
            (
                capture_cninfo_corporate_actions(
                    source_security_id=binding.source_security_id,
                    instrument_id=binding.instrument_id,
                    start_date=daily_package.plan.history_start_date,
                    end_date=daily_package.plan.history_end_date,
                    retrieved_at=captured_at,
                    fetcher=active_fetcher,
                ),
                capture_cninfo_rights_issues(
                    source_security_id=binding.source_security_id,
                    instrument_id=binding.instrument_id,
                    start_date=daily_package.plan.history_start_date,
                    end_date=daily_package.plan.history_end_date,
                    retrieved_at=captured_at,
                    fetcher=active_fetcher,
                ),
            )
        )
    ordered_sources = tuple(
        sorted(
            captured_sources,
            key=lambda item: (item.source_security_id, item.source_kind.value),
        )
    )
    actions = tuple(
        sorted(
            (item for captured in ordered_sources for item in captured.observations),
            key=lambda item: (str(item.instrument_id), item.ex_date),
        )
    )
    factor_query = ChinaAshareSourceDailyQuery(
        source_security_ids=tuple(item.source_security_id for item in bindings),
        start_date=FULL_ADJUSTMENT_HISTORY_START,
        end_date=daily_package.plan.history_end_date,
    )
    with BaoStockClientSession() as session:
        adjustments = BaoStockAshareSourceAdapter(
            session=session
        ).get_adjustment_factor_observations(
            factor_query,
            identity_bindings=bindings,
        )
    crosschecks = capture_ths_distribution_crosschecks(
        source_security_ids=tuple(item.source_security_id for item in bindings),
        start_date=daily_package.plan.history_start_date,
        end_date=daily_package.plan.history_end_date,
    )
    report = build_corporate_action_reconciliation_for_pilot(
        daily_package=daily_package,
        actions=actions,
        full_adjustments=adjustments,
        crosschecks=crosschecks,
        raw_upstream_payload_retained=all(
            captured.raw_bytes for captured in ordered_sources
        ),
        evaluated_at=captured_at,
    )
    return publish_china_ashare_corporate_action_package(
        custody_root=custody_root,
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        captured_sources=ordered_sources,
        actions=actions,
        adjustments=adjustments,
        crosschecks=crosschecks,
        report=report,
        created_at=captured_at,
    )
