"""Bounded reference-evidence capture for the isolated China A-share pilot."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid5

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareExchange,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareLifecycleSourceObservationV1,
    ChinaAshareListingStatus,
    ChinaAsharePilotAnchorV1,
    ChinaAsharePilotIdentityDecisionV1,
    ChinaAsharePilotIdentityDisposition,
    ChinaAsharePilotPlanV1,
    ChinaAshareSecurityForm,
    build_china_ashare_pilot_identity_decision,
    build_china_ashare_pilot_plan,
    china_ashare_pilot_source_observation_fingerprint,
)
from tip_api.persistence.china_ashare_pilot_package import (
    CapturedChinaAsharePilotReferenceV1,
    CapturedChinaAsharePilotDailyV1,
    ChinaAsharePilotDailyPackageResultV1,
    ChinaAsharePilotPackageResultV1,
    publish_china_ashare_pilot_reference_package,
    publish_china_ashare_pilot_daily_package,
)
from tip_api.providers.china_ashare import (
    AKSHARE_ASHARE_REFERENCE_PROVIDER_ID,
    BAOSTOCK_ASHARE_PROVIDER_ID,
    ChinaAshareIdentityBindingV1,
    ChinaAshareInstrumentSourceBatchV1,
    ChinaAshareDailySourceBatchV1,
    ChinaAshareSourceDailyQuery,
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
        source_security_id="sh.600053",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        scenario_tags=(
            "current_common_stock",
            "risk_warning_history_candidate",
        ),
    ),
    ChinaAsharePilotAnchorV1(
        source_security_id="sh.600301",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        scenario_tags=(
            "current_common_stock",
            "suspension_history_candidate",
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
_PILOT_IDENTITY_NAMESPACE = UUID("7b476390-b188-4c88-952a-b98643b67f17")


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


class BaoStockDailyAdapter(Protocol):
    def get_daily_observations(
        self,
        query: ChinaAshareSourceDailyQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    ) -> ChinaAshareDailySourceBatchV1:
        ...

    def get_adjustment_factor_observations(
        self,
        query: ChinaAshareSourceDailyQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    ) -> tuple[ChinaAshareAdjustmentFactorObservationV1, ...]:
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


def adjudicate_china_ashare_pilot_identities(
    *,
    plan: ChinaAsharePilotPlanV1,
    captured: CapturedChinaAsharePilotReferenceV1,
    reference_package_fingerprint: str,
    evaluated_at: datetime,
) -> tuple[ChinaAsharePilotIdentityDecisionV1, ...]:
    official_by_id = {
        item.source_security_id: item for item in captured.official_current_instruments
    }
    baostock_by_id = {
        item.source_security_id: item for item in captured.baostock_instruments
    }
    state_by_id = {
        item.source_security_id: item for item in captured.baostock_source_states
    }
    decisions: list[ChinaAsharePilotIdentityDecisionV1] = []
    for anchor in plan.anchors:
        official = official_by_id.get(anchor.source_security_id)
        baostock = baostock_by_id.get(anchor.source_security_id)
        state = state_by_id.get(anchor.source_security_id)
        reasons: set[str] = set()
        if official is None:
            reasons.add("official_current_observation_missing")
        else:
            if official.exchange is not anchor.exchange:
                reasons.add("official_exchange_differs_from_plan")
            if official.board is not anchor.board:
                reasons.add("official_board_differs_from_plan")
            if official.security_form is not ChinaAshareSecurityForm.COMMON_STOCK:
                reasons.add("official_common_stock_form_unproven")
            if official.listing_status is not ChinaAshareListingStatus.LISTED:
                reasons.add("official_current_listing_unproven")
            if official.list_date is None:
                reasons.add("official_list_date_missing")
        if baostock is None:
            reasons.add("baostock_instrument_observation_missing")
        elif baostock.exchange is not anchor.exchange:
            reasons.add("baostock_exchange_differs_from_plan")
        if state is None:
            reasons.add("baostock_source_state_missing")
        name_agreement = (
            None
            if official is None or baostock is None
            else official.name == baostock.name
        )
        if name_agreement is False:
            reasons.add("cross_source_name_mismatch")
        can_bind = not reasons
        if can_bind:
            assert official is not None
            assert baostock is not None
            assert state is not None
            assert official.list_date is not None
            reasons.add("pilot_only_not_canonical")
            pilot_instrument_id = uuid5(
                _PILOT_IDENTITY_NAMESPACE,
                "|".join(
                    (
                        anchor.source_security_id,
                        anchor.exchange.value,
                        anchor.board.value,
                        official.list_date.isoformat(),
                    )
                ),
            )
            disposition = (
                ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
            )
        else:
            pilot_instrument_id = None
            disposition = ChinaAsharePilotIdentityDisposition.QUARANTINED
        decisions.append(
            build_china_ashare_pilot_identity_decision(
                source_security_id=anchor.source_security_id,
                exchange=anchor.exchange,
                board=(official.board if official is not None else ChinaAshareBoard.UNKNOWN),
                pilot_instrument_id=pilot_instrument_id,
                disposition=disposition,
                official_observation_fingerprint=(
                    None
                    if official is None
                    else china_ashare_pilot_source_observation_fingerprint(official)
                ),
                baostock_observation_fingerprint=(
                    None
                    if baostock is None
                    else china_ashare_pilot_source_observation_fingerprint(baostock)
                ),
                baostock_state_fingerprint=(
                    None
                    if state is None
                    else china_ashare_pilot_source_observation_fingerprint(state)
                ),
                reference_package_fingerprint=reference_package_fingerprint,
                name_agreement=name_agreement,
                evaluated_at=evaluated_at,
                reason_codes=tuple(sorted(reasons)),
                canonical_apply_authorized=False,
                research_backtest_authorized=False,
            )
        )
    return tuple(decisions)


def build_china_ashare_pilot_identity_bindings(
    decisions: tuple[ChinaAsharePilotIdentityDecisionV1, ...],
) -> tuple[ChinaAshareIdentityBindingV1, ...]:
    bindings = tuple(
        ChinaAshareIdentityBindingV1(
            source_security_id=item.source_security_id,
            instrument_id=item.pilot_instrument_id,
            board=item.board,
            security_form=ChinaAshareSecurityForm.COMMON_STOCK,
            evidence_fingerprints=(item.logical_fingerprint,),
        )
        for item in decisions
        if item.disposition
        is ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
        and item.pilot_instrument_id is not None
    )
    return tuple(sorted(bindings, key=lambda item: item.source_security_id))


def capture_china_ashare_pilot_daily(
    *,
    custody_root: Path,
    plan: ChinaAsharePilotPlanV1,
    reference_package_fingerprint: str,
    reference_evidence: CapturedChinaAsharePilotReferenceV1,
    baostock_adapter: BaoStockDailyAdapter,
    created_at: datetime,
) -> ChinaAsharePilotDailyPackageResultV1:
    decisions = adjudicate_china_ashare_pilot_identities(
        plan=plan,
        captured=reference_evidence,
        reference_package_fingerprint=reference_package_fingerprint,
        evaluated_at=created_at,
    )
    bindings = build_china_ashare_pilot_identity_bindings(decisions)
    query = ChinaAshareSourceDailyQuery(
        source_security_ids=tuple(item.source_security_id for item in bindings),
        start_date=plan.history_start_date,
        end_date=plan.history_end_date,
    )
    daily_batch = baostock_adapter.get_daily_observations(
        query,
        identity_bindings=bindings,
    )
    adjustment_observations = baostock_adapter.get_adjustment_factor_observations(
        query,
        identity_bindings=bindings,
    )
    captured = CapturedChinaAsharePilotDailyV1(
        identity_decisions=decisions,
        daily_batch=daily_batch,
        adjustment_observations=adjustment_observations,
        source_request_count=(
            daily_batch.source_request_count + len(query.source_security_ids)
        ),
    )
    return publish_china_ashare_pilot_daily_package(
        custody_root=custody_root,
        plan=plan,
        reference_package_fingerprint=reference_package_fingerprint,
        captured=captured,
        created_at=created_at,
    )


def _five_year_start(end_date: date) -> date:
    try:
        return end_date.replace(year=end_date.year - 5)
    except ValueError:
        return end_date.replace(year=end_date.year - 5, day=28)
