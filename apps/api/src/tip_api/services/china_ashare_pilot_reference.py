"""Bounded reference-evidence capture for the isolated China A-share pilot."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareLifecycleSourceObservationV1,
    ChinaAsharePilotAnchorV1,
    ChinaAsharePilotPlanV1,
    build_china_ashare_pilot_plan,
)
from tip_api.persistence.china_ashare_pilot_package import (
    CapturedChinaAsharePilotReferenceV1,
    ChinaAsharePilotPackageResultV1,
    publish_china_ashare_pilot_reference_package,
)
from tip_api.providers.china_ashare import (
    AKSHARE_ASHARE_REFERENCE_PROVIDER_ID,
    BAOSTOCK_ASHARE_PROVIDER_ID,
    ChinaAshareIdentityBindingV1,
    ChinaAshareInstrumentSourceBatchV1,
    ChinaAshareSourceInstrumentQuery,
)


DEFAULT_ANCHORS = (
    ChinaAsharePilotAnchorV1(
        source_security_id="bj.920000",
        exchange=ChinaAshareExchange.BSE,
        board=ChinaAshareBoard.BSE,
        scenario_tags=(
            "board_coverage",
            "current_common_stock",
            "known_primary_daily_source_gap",
        ),
    ),
    ChinaAsharePilotAnchorV1(
        source_security_id="sh.600519",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        scenario_tags=(
            "board_coverage",
            "corporate_action_history_target",
            "current_common_stock",
        ),
    ),
    ChinaAsharePilotAnchorV1(
        source_security_id="sh.688001",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.STAR,
        scenario_tags=(
            "board_coverage",
            "current_common_stock",
            "twenty_percent_limit_rule_target",
        ),
    ),
    ChinaAsharePilotAnchorV1(
        source_security_id="sz.000001",
        exchange=ChinaAshareExchange.SZSE,
        board=ChinaAshareBoard.SZSE_MAIN,
        scenario_tags=("board_coverage", "current_common_stock"),
    ),
    ChinaAsharePilotAnchorV1(
        source_security_id="sz.300001",
        exchange=ChinaAshareExchange.SZSE,
        board=ChinaAshareBoard.CHINEXT,
        scenario_tags=(
            "board_coverage",
            "current_common_stock",
            "twenty_percent_limit_rule_target",
        ),
    ),
)
DEFAULT_LIFECYCLE_SUBJECT_KEYS = (
    "sse_issuer.600001",
    "szse_security.000003",
)


class OfficialReferenceAdapter(Protocol):
    def get_current_instrument_observations(
        self,
        query: ChinaAshareSourceInstrumentQuery,
    ) -> tuple[ChinaAshareInstrumentSourceObservationV1, ...]:
        ...

    def get_lifecycle_observations(
        self,
        query: ChinaAshareSourceInstrumentQuery,
    ) -> tuple[ChinaAshareLifecycleSourceObservationV1, ...]:
        ...


class BaoStockSnapshotAdapter(Protocol):
    def get_instrument_snapshot(
        self,
        query: ChinaAshareSourceInstrumentQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...] = (),
    ) -> ChinaAshareInstrumentSourceBatchV1:
        ...


def build_default_china_ashare_pilot_plan(
    *,
    planned_at: datetime,
    official_reference_as_of_date: date,
    baostock_snapshot_date: date,
) -> ChinaAsharePilotPlanV1:
    return build_china_ashare_pilot_plan(
        planned_at=planned_at,
        official_reference_as_of_date=official_reference_as_of_date,
        baostock_snapshot_date=baostock_snapshot_date,
        history_start_date=_five_year_start(baostock_snapshot_date),
        history_end_date=baostock_snapshot_date,
        anchors=DEFAULT_ANCHORS,
        lifecycle_subject_keys=DEFAULT_LIFECYCLE_SUBJECT_KEYS,
        provider_ids=(
            AKSHARE_ASHARE_REFERENCE_PROVIDER_ID,
            BAOSTOCK_ASHARE_PROVIDER_ID,
        ),
        maximum_source_requests=12,
        raw_upstream_payload_retained=False,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )


def capture_china_ashare_pilot_reference(
    *,
    custody_root: Path,
    plan: ChinaAsharePilotPlanV1,
    official_adapter: OfficialReferenceAdapter,
    baostock_adapter: BaoStockSnapshotAdapter,
    created_at: datetime,
) -> ChinaAsharePilotPackageResultV1:
    anchor_ids = {item.source_security_id for item in plan.anchors}
    lifecycle_keys = set(plan.lifecycle_subject_keys)
    official_query = ChinaAshareSourceInstrumentQuery(
        as_of_date=plan.official_reference_as_of_date
    )
    official_rows = tuple(
        item
        for item in official_adapter.get_current_instrument_observations(
            official_query
        )
        if item.source_security_id in anchor_ids
    )
    lifecycle_rows = tuple(
        item
        for item in official_adapter.get_lifecycle_observations(official_query)
        if item.source_subject_key in lifecycle_keys
    )
    snapshot = baostock_adapter.get_instrument_snapshot(
        ChinaAshareSourceInstrumentQuery(as_of_date=plan.baostock_snapshot_date),
        identity_bindings=(),
    )
    baostock_rows = tuple(
        item for item in snapshot.instruments if item.source_security_id in anchor_ids
    )
    baostock_states = tuple(
        item for item in snapshot.source_states if item.source_security_id in anchor_ids
    )
    captured = CapturedChinaAsharePilotReferenceV1(
        official_current_instruments=official_rows,
        baostock_instruments=baostock_rows,
        baostock_source_states=baostock_states,
        official_lifecycle=lifecycle_rows,
        source_request_count=6 + snapshot.source_request_count,
    )
    return publish_china_ashare_pilot_reference_package(
        custody_root=custody_root,
        plan=plan,
        captured=captured,
        created_at=created_at,
    )


def _five_year_start(end_date: date) -> date:
    try:
        return end_date.replace(year=end_date.year - 5)
    except ValueError:
        return end_date.replace(year=end_date.year - 5, day=28)
