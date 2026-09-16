from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAshareIdentityResolutionStatus,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareLifecycleEventType,
    ChinaAshareLifecycleSourceObservationV1,
    ChinaAshareLifecycleSubjectKind,
    ChinaAshareListingStatus,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareSecurityForm,
    ChinaAshareSourceSecuritySnapshotStateV1,
    ChinaAshareTradingStatus,
    build_china_ashare_pilot_plan,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_pilot_package import (
    CapturedChinaAsharePilotReferenceV1,
    CapturedChinaAsharePilotDailyV1,
    ChinaAsharePilotPackageConflictError,
    ChinaAsharePilotPackageCorruptionError,
    publish_china_ashare_pilot_reference_package,
    publish_china_ashare_pilot_daily_package,
    read_china_ashare_pilot_daily_package,
    read_china_ashare_pilot_reference_package,
)
from tip_api.services.china_ashare_pilot_reference import (
    adjudicate_china_ashare_pilot_identities,
    build_china_ashare_pilot_identity_bindings,
)
from tip_api.providers.china_ashare import (
    BAOSTOCK_ASHARE_PROVIDER_ID,
    ChinaAshareDailySourceBatchV1,
    ChinaAshareSourceDailyQuery,
)


NOW = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
AS_OF = date(2026, 9, 17)
ANCHORS = (
    ("bj.920000", ChinaAshareExchange.BSE, ChinaAshareBoard.BSE),
    ("sh.600519", ChinaAshareExchange.SSE, ChinaAshareBoard.SSE_MAIN),
    ("sh.688001", ChinaAshareExchange.SSE, ChinaAshareBoard.STAR),
    ("sz.000001", ChinaAshareExchange.SZSE, ChinaAshareBoard.SZSE_MAIN),
    ("sz.300001", ChinaAshareExchange.SZSE, ChinaAshareBoard.CHINEXT),
)


def _plan():
    from tip_api.contracts.china_ashare.v1 import ChinaAsharePilotAnchorV1

    return build_china_ashare_pilot_plan(
        planned_at=NOW,
        official_reference_as_of_date=AS_OF,
        baostock_snapshot_date=AS_OF,
        history_start_date=date(2021, 9, 17),
        history_end_date=date(2026, 9, 16),
        anchors=tuple(
            ChinaAsharePilotAnchorV1(
                source_security_id=source_id,
                exchange=exchange,
                board=board,
                scenario_tags=("board_coverage", "current_common_stock"),
            )
            for source_id, exchange, board in ANCHORS
        ),
        lifecycle_subject_keys=("sse_issuer.600001", "szse_security.000003"),
        provider_ids=("akshare_official_lists", "baostock_free"),
        maximum_source_requests=12,
        raw_upstream_payload_retained=False,
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )


def _instrument(
    source_id: str,
    exchange: ChinaAshareExchange,
    board: ChinaAshareBoard,
    *,
    source: str,
) -> ChinaAshareInstrumentSourceObservationV1:
    code = source_id.split(".", maxsplit=1)[1]
    suffix = {
        ChinaAshareExchange.SSE: "SH",
        ChinaAshareExchange.SZSE: "SZ",
        ChinaAshareExchange.BSE: "BJ",
    }[exchange]
    official = source == "akshare_official_list"
    return ChinaAshareInstrumentSourceObservationV1(
        source_security_id=source_id,
        source_code=code,
        display_ticker=f"{code}.{suffix}",
        name=f"sample-{code}",
        exchange=exchange,
        board=board if official else ChinaAshareBoard.UNKNOWN,
        security_form=(
            ChinaAshareSecurityForm.COMMON_STOCK
            if official
            else ChinaAshareSecurityForm.UNKNOWN
        ),
        listing_status=ChinaAshareListingStatus.LISTED,
        list_date=date(2000, 1, 1),
        as_of_date=AS_OF,
        resolution_status=ChinaAshareIdentityResolutionStatus.QUARANTINED,
        source=source,
        source_available_at=NOW if official else None,
        ingested_at=NOW,
        quality_status=QualityStatus.PENDING_REVIEW,
        reason_codes=("stable_identity_unproven",),
    )


def _captured(*, omit_official: str | None = None):
    official = tuple(
        _instrument(source_id, exchange, board, source="akshare_official_list")
        for source_id, exchange, board in ANCHORS
        if source_id != omit_official
    )
    baostock_anchors = ANCHORS[1:]
    baostock = tuple(
        _instrument(source_id, exchange, board, source="baostock_free")
        for source_id, exchange, board in baostock_anchors
    )
    states = tuple(
        ChinaAshareSourceSecuritySnapshotStateV1(
            source_security_id=source_id,
            session_date=AS_OF,
            trading_status=ChinaAshareTradingStatus.TRADING,
            source="baostock_free",
            source_available_at=None,
            ingested_at=NOW,
            quality_status=QualityStatus.VALID,
            reason_codes=("source_available_time_unreported",),
        )
        for source_id, _, _ in baostock_anchors
    )
    lifecycle = (
        ChinaAshareLifecycleSourceObservationV1(
            source_subject_key="sse_issuer.600001",
            source_subject_code="600001",
            subject_kind=ChinaAshareLifecycleSubjectKind.ISSUER_CODE,
            source_security_id=None,
            display_ticker=None,
            source_row_sequence=1,
            name="sample-sse-lifecycle",
            exchange=ChinaAshareExchange.SSE,
            event_type=ChinaAshareLifecycleEventType.PAUSED_OR_TERMINATED_LISTING,
            list_date=date(1998, 1, 22),
            event_date=date(2009, 12, 29),
            as_of_date=AS_OF,
            source="akshare_sse_official_delist",
            source_available_at=NOW,
            ingested_at=NOW,
            quality_status=QualityStatus.WARNING,
            reason_codes=(
                "issuer_security_identity_unproven",
                "source_status_conflates_pause_and_termination",
            ),
        ),
        ChinaAshareLifecycleSourceObservationV1(
            source_subject_key="szse_security.000003",
            source_subject_code="000003",
            subject_kind=ChinaAshareLifecycleSubjectKind.SECURITY_CODE,
            source_security_id="sz.000003",
            display_ticker="000003.SZ",
            source_row_sequence=1,
            name="sample-szse-lifecycle",
            exchange=ChinaAshareExchange.SZSE,
            event_type=ChinaAshareLifecycleEventType.TERMINATED_LISTING,
            list_date=date(1991, 7, 3),
            event_date=date(2002, 6, 14),
            as_of_date=AS_OF,
            source="akshare_szse_official_delist",
            source_available_at=NOW,
            ingested_at=NOW,
            quality_status=QualityStatus.PENDING_REVIEW,
        ),
    )
    return CapturedChinaAsharePilotReferenceV1(
        official_current_instruments=official,
        baostock_instruments=baostock,
        baostock_source_states=states,
        official_lifecycle=lifecycle,
        source_request_count=7,
    )


def _publish(tmp_path: Path, *, captured=None):
    return publish_china_ashare_pilot_reference_package(
        custody_root=tmp_path / "china-a-share-research-pilot",
        plan=_plan(),
        captured=captured or _captured(),
        created_at=NOW,
    )


def test_reference_package_round_trip_is_exact_and_non_authorizing(
    tmp_path: Path,
) -> None:
    published = _publish(tmp_path)
    reread = read_china_ashare_pilot_reference_package(
        package_path=published.package_path
    )
    again = _publish(tmp_path)

    assert published.status == "published"
    assert reread.manifest == published.manifest
    assert reread.captured == published.captured
    assert again.status == "already_present"
    assert reread.file_count == 7
    assert reread.quality_report.reference_evidence_complete is True
    assert reread.quality_report.baostock_snapshot_missing_ids == ("bj.920000",)
    assert reread.manifest.raw_upstream_payload_retained is False
    assert reread.manifest.research_backtest_authorized is False
    assert reread.manifest.canonical_apply_authorized is False
    assert reread.manifest.product_publication_authorized is False
    assert reread.manifest.deployment_authorized is False


def test_reference_package_reports_missing_official_anchor(tmp_path: Path) -> None:
    result = _publish(
        tmp_path,
        captured=_captured(omit_official="sh.688001"),
    )

    assert result.quality_report.reference_evidence_complete is False
    assert result.quality_report.official_current_missing_ids == ("sh.688001",)
    assert "official_reference_evidence_incomplete" in (
        result.quality_report.reason_codes
    )


def test_reference_package_supports_only_evidence_bound_pilot_identities(
    tmp_path: Path,
) -> None:
    result = _publish(tmp_path)

    decisions = adjudicate_china_ashare_pilot_identities(
        plan=result.plan,
        captured=result.captured,
        reference_package_fingerprint=result.manifest.logical_fingerprint,
        evaluated_at=NOW,
    )
    bindings = build_china_ashare_pilot_identity_bindings(decisions)

    bound = [item for item in decisions if item.pilot_instrument_id is not None]
    quarantined = [item for item in decisions if item.pilot_instrument_id is None]
    assert len(bound) == 4
    assert [item.source_security_id for item in quarantined] == ["bj.920000"]
    assert quarantined[0].reason_codes == (
        "baostock_instrument_observation_missing",
        "baostock_source_state_missing",
    )
    assert len(bindings) == 4
    assert all(item.source_security_id != "bj.920000" for item in bindings)


def test_reference_package_rejects_changed_artifact(tmp_path: Path) -> None:
    result = _publish(tmp_path)
    artifact = result.package_path / "normalized/baostock-instruments.json"
    artifact.chmod(0o600)
    artifact.write_text('{"changed":true}\n', encoding="utf-8")
    artifact.chmod(0o400)

    with pytest.raises(
        ChinaAsharePilotPackageCorruptionError,
        match="artifact custody differs",
    ):
        read_china_ashare_pilot_reference_package(package_path=result.package_path)


def test_reference_package_rejects_unplanned_security(tmp_path: Path) -> None:
    captured = _captured()
    unexpected = _instrument(
        "sh.600000",
        ChinaAshareExchange.SSE,
        ChinaAshareBoard.SSE_MAIN,
        source="akshare_official_list",
    )
    changed = CapturedChinaAsharePilotReferenceV1(
        official_current_instruments=tuple(
            sorted(
                (*captured.official_current_instruments, unexpected),
                key=lambda item: item.source_security_id,
            )
        ),
        baostock_instruments=captured.baostock_instruments,
        baostock_source_states=captured.baostock_source_states,
        official_lifecycle=captured.official_lifecycle,
        source_request_count=captured.source_request_count,
    )

    with pytest.raises(
        ChinaAsharePilotPackageConflictError,
        match="unplanned security",
    ):
        _publish(tmp_path, captured=changed)


def test_daily_package_round_trip_preserves_pilot_only_authority(
    tmp_path: Path,
) -> None:
    reference = _publish(tmp_path)
    decisions = adjudicate_china_ashare_pilot_identities(
        plan=reference.plan,
        captured=reference.captured,
        reference_package_fingerprint=reference.manifest.logical_fingerprint,
        evaluated_at=NOW,
    )
    bindings = build_china_ashare_pilot_identity_bindings(decisions)
    query = ChinaAshareSourceDailyQuery(
        source_security_ids=tuple(item.source_security_id for item in bindings),
        start_date=reference.plan.history_start_date,
        end_date=reference.plan.history_end_date,
    )
    rows = sorted(bindings, key=lambda item: str(item.instrument_id))
    bars = tuple(
        ChinaAshareDailyBarV1(
            instrument_id=item.instrument_id,
            session_date=query.start_date,
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10.5"),
            pre_close=Decimal("10"),
            volume_shares=Decimal("1000"),
            turnover_amount_cny=Decimal("10500"),
            source=BAOSTOCK_ASHARE_PROVIDER_ID,
            source_record_id=f"{item.source_security_id}:{query.start_date.isoformat()}",
            source_available_at=None,
            ingested_at=NOW,
            revision=1,
            quality_status=QualityStatus.WARNING,
            reason_codes=("source_available_time_unreported",),
        )
        for item in rows
    )
    states = tuple(
        ChinaAshareDailyTradingStateV1(
            instrument_id=item.instrument_id,
            session_date=query.start_date,
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
            ingested_at=NOW,
            quality_status=QualityStatus.WARNING,
            reason_codes=(
                "price_limit_requires_official_rule_resolution",
                "source_available_time_unreported",
            ),
        )
        for item in rows
    )
    first = rows[0]
    adjustment = ChinaAshareAdjustmentFactorObservationV1(
        instrument_id=first.instrument_id,
        session_date=query.start_date,
        provider_factor=Decimal("1.1"),
        fore_adjust_factor=Decimal("0.9"),
        back_adjust_factor=Decimal("1.1"),
        provider_semantics="fixture source factors; return semantics unreconciled",
        source=BAOSTOCK_ASHARE_PROVIDER_ID,
        source_available_at=None,
        ingested_at=NOW,
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
            source_request_count=len(bindings),
        ),
        adjustment_observations=(adjustment,),
        source_request_count=len(bindings) * 2,
    )

    published = publish_china_ashare_pilot_daily_package(
        custody_root=tmp_path / "china-a-share-research-pilot",
        plan=reference.plan,
        reference_package_fingerprint=reference.manifest.logical_fingerprint,
        captured=captured,
        created_at=NOW,
    )
    reread = read_china_ashare_pilot_daily_package(
        package_path=published.package_path
    )

    assert published.status == "published"
    assert reread.manifest == published.manifest
    assert reread.captured == published.captured
    assert reread.file_count == 7
    assert reread.quality_report.source_capture_complete is True
    assert reread.quality_report.diverse_scenarios_observed is False
    assert reread.quality_report.research_backtest_authorized is False
    assert reread.manifest.canonical_apply_authorized is False
