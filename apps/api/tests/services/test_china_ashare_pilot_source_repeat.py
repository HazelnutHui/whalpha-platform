from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareBoard,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAsharePilotAnchorV1,
    ChinaAsharePilotIdentityDisposition,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
    build_china_ashare_pilot_identity_decision,
    build_china_ashare_pilot_plan,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_pilot_package import (
    CapturedChinaAsharePilotDailyV1,
    publish_china_ashare_pilot_daily_package,
)
from tip_api.providers.china_ashare import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    ChinaAshareDailySourceBatchV1,
    ChinaAshareSourceDailyQuery,
)
from tip_api.services.china_ashare_pilot_source_repeat import (
    ChinaAsharePilotRepeatFamily,
    ChinaAsharePilotSourceRepeatError,
    compare_china_ashare_pilot_daily_packages,
    read_china_ashare_pilot_source_repeat,
)


NOW = datetime(2026, 9, 17, 1, 0, tzinfo=UTC)
SOURCE_ID = "sh.600519"
REFERENCE_FINGERPRINT = "a" * 64
ANCHORS = (
    ("bj.920000", ChinaAshareExchange.BSE, ChinaAshareBoard.BSE),
    ("sh.600519", ChinaAshareExchange.SSE, ChinaAshareBoard.SSE_MAIN),
    ("sh.688001", ChinaAshareExchange.SSE, ChinaAshareBoard.STAR),
    ("sz.000001", ChinaAshareExchange.SZSE, ChinaAshareBoard.SZSE_MAIN),
    ("sz.300001", ChinaAshareExchange.SZSE, ChinaAshareBoard.CHINEXT),
)
INSTRUMENT_IDS = {
    "sh.600519": UUID("94a0cb10-0cc5-5b43-9099-d76ba8d4669d"),
    "sh.688001": UUID("57f83f45-596b-5ef3-94c5-264959d90483"),
    "sz.000001": UUID("90f99aa4-53f9-5097-b50d-89630dd67fca"),
    "sz.300001": UUID("70ed8677-a2bd-50c4-8da3-d3bb667e8186"),
}


def _plan():
    return build_china_ashare_pilot_plan(
        planned_at=NOW - timedelta(days=1),
        official_reference_as_of_date=date(2026, 9, 17),
        baostock_snapshot_date=date(2026, 9, 16),
        history_start_date=date(2021, 9, 16),
        history_end_date=date(2026, 9, 16),
        anchors=tuple(
            ChinaAsharePilotAnchorV1(
                source_security_id=source_id,
                exchange=exchange,
                board=board,
                scenario_tags=("current_common_stock",),
            )
            for source_id, exchange, board in ANCHORS
        ),
        lifecycle_subject_keys=("sse_issuer.600001", "szse_security.000003"),
        provider_ids=("akshare_official_lists", BAOSTOCK_ASHARE_PROVIDER_ID),
        maximum_source_requests=12,
        raw_upstream_payload_retained=False,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )


def _publish_daily(
    tmp_path: Path,
    *,
    created_at: datetime,
    close: Decimal = Decimal("10.5"),
):
    plan = _plan()
    decisions = tuple(
        build_china_ashare_pilot_identity_decision(
            source_security_id=source_id,
            exchange=exchange,
            board=board,
            pilot_instrument_id=INSTRUMENT_IDS.get(source_id),
            disposition=(
                ChinaAsharePilotIdentityDisposition.QUARANTINED
                if source_id.startswith("bj.")
                else ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
            ),
            official_observation_fingerprint="b" * 64,
            baostock_observation_fingerprint=(
                None if source_id.startswith("bj.") else "c" * 64
            ),
            baostock_state_fingerprint=(
                None if source_id.startswith("bj.") else "d" * 64
            ),
            reference_package_fingerprint=REFERENCE_FINGERPRINT,
            name_agreement=(None if source_id.startswith("bj.") else True),
            evaluated_at=created_at,
            reason_codes=(
                ("baostock_instrument_observation_missing",)
                if source_id.startswith("bj.")
                else ("pilot_only_not_canonical",)
            ),
            canonical_apply_authorized=False,
            research_backtest_authorized=False,
        )
        for source_id, exchange, board in ANCHORS
    )
    bound = tuple(
        item
        for item in decisions
        if item.disposition
        is ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
    )
    query = ChinaAshareSourceDailyQuery(
        source_security_ids=tuple(item.source_security_id for item in bound),
        start_date=plan.history_start_date,
        end_date=plan.history_end_date,
    )
    bars = tuple(
        sorted(
            (
                ChinaAshareDailyBarV1(
                    instrument_id=item.pilot_instrument_id,
                    session_date=plan.history_start_date,
                    open=Decimal("10"),
                    high=Decimal("11"),
                    low=Decimal("9"),
                    close=(close if item.source_security_id == SOURCE_ID else Decimal("10.5")),
                    pre_close=Decimal("10"),
                    volume_shares=Decimal("1000"),
                    turnover_amount_cny=Decimal("10500"),
                    source=BAOSTOCK_ASHARE_PROVIDER_ID,
                    source_record_id=(
                        f"{item.source_security_id}:{plan.history_start_date.isoformat()}"
                    ),
                    source_available_at=None,
                    ingested_at=created_at,
                    revision=1,
                    quality_status=QualityStatus.WARNING,
                    reason_codes=("source_available_time_unreported",),
                )
                for item in bound
            ),
            key=lambda item: (str(item.instrument_id), item.session_date),
        )
    )
    states = tuple(
        sorted(
            (
                ChinaAshareDailyTradingStateV1(
                    instrument_id=item.pilot_instrument_id,
                    session_date=plan.history_start_date,
                    exchange=(
                        ChinaAshareExchange.SSE
                        if item.source_security_id.startswith("sh.")
                        else ChinaAshareExchange.SZSE
                    ),
                    board=item.board,
                    trading_status=ChinaAshareTradingStatus.TRADING,
                    risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
                    price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
                    pre_close=Decimal("10"),
                    exact_limit_prices_source_observed=False,
                    source=BAOSTOCK_ASHARE_PROVIDER_ID,
                    source_available_at=None,
                    ingested_at=created_at,
                    quality_status=QualityStatus.WARNING,
                    reason_codes=(
                        "price_limit_requires_official_rule_resolution",
                        "source_available_time_unreported",
                    ),
                )
                for item in bound
            ),
            key=lambda item: (str(item.instrument_id), item.session_date),
        )
    )
    adjustment = ChinaAshareAdjustmentFactorObservationV1(
        instrument_id=INSTRUMENT_IDS[SOURCE_ID],
        session_date=plan.history_start_date,
        provider_factor=Decimal("1.1"),
        fore_adjust_factor=Decimal("0.9"),
        back_adjust_factor=Decimal("1.1"),
        provider_semantics="fixture factors; return semantics unreconciled",
        source=BAOSTOCK_ASHARE_PROVIDER_ID,
        source_available_at=None,
        ingested_at=created_at,
        normalized_return_authorized=False,
        quality_status=QualityStatus.WARNING,
        reason_codes=(
            "return_semantics_unreconciled",
            "source_available_time_unreported",
        ),
    )
    captured = CapturedChinaAsharePilotDailyV1(
        identity_decisions=decisions,
        daily_batch=ChinaAshareDailySourceBatchV1(
            provider_id=BAOSTOCK_ASHARE_PROVIDER_ID,
            query=query,
            bars=bars,
            trading_states=states,
            source_request_count=len(bound),
        ),
        adjustment_observations=(adjustment,),
        source_request_count=len(bound) * 2,
    )
    return publish_china_ashare_pilot_daily_package(
        custody_root=tmp_path / "china-a-share-research-pilot",
        plan=plan,
        reference_package_fingerprint=REFERENCE_FINGERPRINT,
        captured=captured,
        created_at=created_at,
    )


def test_source_repeat_ignores_only_ingestion_time_and_rereads_exactly(
    tmp_path: Path,
) -> None:
    baseline = _publish_daily(tmp_path, created_at=NOW)
    repeat = _publish_daily(tmp_path, created_at=NOW + timedelta(hours=1))

    result = compare_china_ashare_pilot_daily_packages(
        baseline_package_path=baseline.package_path,
        repeat_package_path=repeat.package_path,
        compared_at=NOW + timedelta(hours=2),
    )
    reread = read_china_ashare_pilot_source_repeat(output_path=result.output_path)

    assert result.status == "published"
    assert result.changes == ()
    assert result.report.total_change_count == 0
    assert result.report.economic_values_stable is True
    assert result.report.source_repeat_qualified is True
    assert result.report.ignored_fields == ("ingested_at",)
    assert reread.report == result.report
    assert reread.changes == result.changes
    assert reread.report.research_backtest_authorized is False
    assert reread.report.canonical_apply_authorized is False


def test_source_repeat_detects_changed_economic_value(tmp_path: Path) -> None:
    baseline = _publish_daily(tmp_path, created_at=NOW)
    repeat = _publish_daily(
        tmp_path,
        created_at=NOW + timedelta(hours=1),
        close=Decimal("10.75"),
    )

    result = compare_china_ashare_pilot_daily_packages(
        baseline_package_path=baseline.package_path,
        repeat_package_path=repeat.package_path,
        compared_at=NOW + timedelta(hours=2),
    )

    assert result.report.total_change_count == 1
    assert result.report.economic_values_stable is False
    assert result.report.source_repeat_qualified is False
    assert result.changes[0].family is ChinaAsharePilotRepeatFamily.DAILY_BAR
    assert result.changes[0].changed_fields == ("close",)


def test_source_repeat_rejects_same_package(tmp_path: Path) -> None:
    package = _publish_daily(tmp_path, created_at=NOW)

    with pytest.raises(
        ChinaAsharePilotSourceRepeatError,
        match="requires distinct daily packages",
    ):
        compare_china_ashare_pilot_daily_packages(
            baseline_package_path=package.package_path,
            repeat_package_path=package.package_path,
            compared_at=NOW + timedelta(hours=1),
        )
