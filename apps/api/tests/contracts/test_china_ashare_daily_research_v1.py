from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1 import (
    CHINA_ASHARE_FOUNDATION_FAMILY_ORDER,
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareBoard,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyResearchAdmissionV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAshareFoundationCoverageStatus,
    ChinaAshareFoundationEvidenceTier,
    ChinaAshareFoundationFamily,
    ChinaAshareFoundationFamilyCensusV1,
    ChinaAshareIdentityResolutionStatus,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareListingStatus,
    ChinaAsharePriceLimitRegime,
    ChinaAshareResearchAdmissionStatus,
    ChinaAshareRiskWarningStatus,
    ChinaAshareSecurityForm,
    ChinaAshareTradingRuleV1,
    ChinaAshareTradingStatus,
    ChinaAshareUniverseDecisionV1,
    ChinaAshareUniverseDisposition,
    build_china_ashare_daily_research_admission,
)
from tip_api.contracts.common import QualityStatus


INSTRUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")
AVAILABLE = datetime(2026, 9, 16, 7, 30, tzinfo=UTC)
INGESTED = datetime(2026, 9, 16, 8, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64


def _instrument(**overrides: object) -> ChinaAshareInstrumentSourceObservationV1:
    payload: dict[str, object] = {
        "source_security_id": "600519.SH",
        "source_code": "600519",
        "display_ticker": "600519.SH",
        "name": "示例股份",
        "exchange": ChinaAshareExchange.SSE,
        "board": ChinaAshareBoard.SSE_MAIN,
        "security_form": ChinaAshareSecurityForm.COMMON_STOCK,
        "listing_status": ChinaAshareListingStatus.LISTED,
        "list_date": date(2001, 8, 27),
        "as_of_date": date(2026, 9, 16),
        "instrument_id": INSTRUMENT_ID,
        "resolution_status": ChinaAshareIdentityResolutionStatus.RESOLVED,
        "source": "source-a",
        "source_available_at": AVAILABLE,
        "ingested_at": INGESTED,
        "quality_status": QualityStatus.VALID,
    }
    payload.update(overrides)
    return ChinaAshareInstrumentSourceObservationV1(**payload)


def _bar(**overrides: object) -> ChinaAshareDailyBarV1:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "session_date": date(2026, 9, 16),
        "open": Decimal("100.00"),
        "high": Decimal("105.00"),
        "low": Decimal("99.00"),
        "close": Decimal("104.00"),
        "pre_close": Decimal("100.00"),
        "volume_shares": Decimal("12345600"),
        "turnover_amount_cny": Decimal("1260000000.00"),
        "source": "source-a",
        "source_available_at": AVAILABLE,
        "ingested_at": INGESTED,
        "revision": 1,
        "quality_status": QualityStatus.VALID,
    }
    payload.update(overrides)
    return ChinaAshareDailyBarV1(**payload)


def _trading_state(**overrides: object) -> ChinaAshareDailyTradingStateV1:
    payload: dict[str, object] = {
        "instrument_id": INSTRUMENT_ID,
        "session_date": date(2026, 9, 16),
        "exchange": ChinaAshareExchange.SSE,
        "board": ChinaAshareBoard.SSE_MAIN,
        "trading_status": ChinaAshareTradingStatus.TRADING,
        "risk_warning_status": ChinaAshareRiskWarningStatus.NONE,
        "price_limit_regime": ChinaAsharePriceLimitRegime.PERCENT_10,
        "pre_close": Decimal("100"),
        "up_limit": Decimal("110"),
        "down_limit": Decimal("90"),
        "exact_limit_prices_source_observed": True,
        "source": "source-a",
        "source_available_at": AVAILABLE,
        "ingested_at": INGESTED,
        "quality_status": QualityStatus.VALID,
    }
    payload.update(overrides)
    return ChinaAshareDailyTradingStateV1(**payload)


def _family(
    family: ChinaAshareFoundationFamily,
    *,
    status: ChinaAshareFoundationCoverageStatus = ChinaAshareFoundationCoverageStatus.COMPLETE,
    quarantined: int = 0,
) -> ChinaAshareFoundationFamilyCensusV1:
    return ChinaAshareFoundationFamilyCensusV1(
        family=family,
        required_for_daily_research=True,
        coverage_status=status,
        evidence_tier=(
            ChinaAshareFoundationEvidenceTier.MISSING
            if status is ChinaAshareFoundationCoverageStatus.ABSENT
            else ChinaAshareFoundationEvidenceTier.RECONCILED
        ),
        target_session_count=2,
        covered_session_count=(
            0 if status is ChinaAshareFoundationCoverageStatus.ABSENT else 2
        ),
        missing_session_count=(
            2 if status is ChinaAshareFoundationCoverageStatus.ABSENT else 0
        ),
        record_count=0 if status is ChinaAshareFoundationCoverageStatus.ABSENT else 2,
        quarantined_record_count=quarantined,
        source_ids=() if status is ChinaAshareFoundationCoverageStatus.ABSENT else ("source-a",),
        reason_codes=(
            "source_missing"
            if status is ChinaAshareFoundationCoverageStatus.ABSENT
            else "coverage_complete"
        ,),
    )


def test_resolved_instrument_keeps_market_and_board_explicit() -> None:
    row = _instrument()

    assert row.market_id == "china_a_share"
    assert row.instrument_id == INSTRUMENT_ID
    assert row.board is ChinaAshareBoard.SSE_MAIN


def test_identity_never_resolves_from_name_or_code_alone() -> None:
    with pytest.raises(ValidationError, match="resolved identity requires instrument_id"):
        _instrument(instrument_id=None)

    unresolved = _instrument(
        instrument_id=None,
        resolution_status=ChinaAshareIdentityResolutionStatus.QUARANTINED,
        quality_status=QualityStatus.PENDING_REVIEW,
        reason_codes=("stable_identity_unproven",),
    )
    assert unresolved.instrument_id is None


def test_resolved_identity_requires_source_proven_board_and_security_form() -> None:
    with pytest.raises(ValidationError, match="source-proven board"):
        _instrument(board=ChinaAshareBoard.UNKNOWN)
    with pytest.raises(ValidationError, match="source-proven security form"):
        _instrument(security_form=ChinaAshareSecurityForm.UNKNOWN)


def test_exchange_board_and_ticker_must_agree() -> None:
    with pytest.raises(ValidationError, match="board is incompatible"):
        _instrument(exchange=ChinaAshareExchange.SZSE)
    with pytest.raises(ValidationError, match="display_ticker differs"):
        _instrument(display_ticker="600519.SZ")


def test_delisted_identity_requires_explicit_date() -> None:
    with pytest.raises(ValidationError, match="delisted observations require"):
        _instrument(listing_status=ChinaAshareListingStatus.DELISTED)


def test_raw_daily_bar_rejects_adjusted_or_float_input() -> None:
    row = _bar()
    assert row.adjustment_basis == "unadjusted"
    with pytest.raises(ValidationError):
        _bar(close=104.0)
    with pytest.raises(ValidationError, match="high is inconsistent"):
        _bar(high=Decimal("103"))


def test_adjustment_factor_cannot_grant_return_authority() -> None:
    row = ChinaAshareAdjustmentFactorObservationV1(
        instrument_id=INSTRUMENT_ID,
        session_date=date(2026, 9, 16),
        provider_factor=Decimal("12.345678"),
        provider_semantics="provider cumulative factor; direction not yet reconciled",
        source="source-a",
        source_available_at=AVAILABLE,
        ingested_at=INGESTED,
        quality_status=QualityStatus.WARNING,
        reason_codes=("return_semantics_unreconciled",),
    )

    assert row.normalized_return_authorized is False
    with pytest.raises(ValidationError):
        row.normalized_return_authorized = True  # type: ignore[misc]


def test_daily_limit_prices_are_source_observations_not_name_inference() -> None:
    row = _trading_state()
    assert row.up_limit == Decimal("110")
    with pytest.raises(ValidationError, match="require pre_close and both limits"):
        _trading_state(up_limit=None)
    with pytest.raises(ValidationError, match="require a bounded limit regime"):
        _trading_state(price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN)


def test_no_limit_session_keeps_limit_prices_null() -> None:
    row = _trading_state(
        price_limit_regime=ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT,
        pre_close=None,
        up_limit=None,
        down_limit=None,
        exact_limit_prices_source_observed=False,
    )
    assert row.up_limit is None


def test_unknown_trading_state_is_explicitly_quarantined() -> None:
    with pytest.raises(ValidationError, match="unknown trading state"):
        _trading_state(
            trading_status=ChinaAshareTradingStatus.UNKNOWN,
            exact_limit_prices_source_observed=False,
            pre_close=None,
            up_limit=None,
            down_limit=None,
            price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
        )


def test_trading_rules_are_effective_dated_and_t_plus_one() -> None:
    row = ChinaAshareTradingRuleV1(
        rule_id="sse-main-standard-2026",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
        effective_from=date(2026, 7, 6),
        settlement_rule="t_plus_one",
        daily_price_limit_ratio=Decimal("0.10"),
        ipo_no_limit_session_count=5,
        minimum_buy_order_shares=100,
        order_increment_shares=100,
        official_source_url="https://www.sse.com.cn/example",
        source_available_at=AVAILABLE,
        ingested_at=INGESTED,
        quality_status=QualityStatus.VALID,
    )

    assert row.settlement_rule == "t_plus_one"
    assert row.daily_price_limit_ratio == Decimal("0.10")


def test_universe_decision_requires_explicit_disposition_and_lineage() -> None:
    row = ChinaAshareUniverseDecisionV1(
        instrument_id=INSTRUMENT_ID,
        session_date=date(2026, 9, 16),
        methodology_version="china-a-share-universe-v1",
        disposition=ChinaAshareUniverseDisposition.INCLUDED,
        reason_codes=("common_stock_eligible",),
        source_cutoff_at=AVAILABLE,
        evaluated_at=INGESTED,
        input_fingerprints=(FINGERPRINT,),
        performance_eligible=True,
    )
    assert row.performance_eligible

    with pytest.raises(ValidationError, match="only included"):
        row.model_copy(
            update={
                "disposition": ChinaAshareUniverseDisposition.QUARANTINED,
                "performance_eligible": True,
            }
        ).__class__.model_validate(
            {
                **row.model_dump(mode="json"),
                "disposition": "quarantined",
            }
        )


def test_complete_foundation_is_daily_research_ready_but_not_live_or_intraday() -> None:
    admission = build_china_ashare_daily_research_admission(
        target_sessions=(date(2026, 9, 15), date(2026, 9, 16)),
        families=tuple(_family(family) for family in CHINA_ASHARE_FOUNDATION_FAMILY_ORDER),
    )

    assert admission.status is ChinaAshareResearchAdmissionStatus.RESEARCH_BACKTEST_READY
    assert admission.daily_research_backtest_authorized
    assert admission.intraday_execution_backtest_authorized is False
    assert admission.live_model_authorized is False
    assert admission.product_publication_authorized is False
    assert (
        ChinaAshareDailyResearchAdmissionV1.model_validate(
            admission.model_dump(mode="json")
        )
        == admission
    )


def test_missing_family_blocks_daily_research() -> None:
    families = tuple(
        _family(
            family,
            status=(
                ChinaAshareFoundationCoverageStatus.ABSENT
                if family is ChinaAshareFoundationFamily.RISK_WARNING_STATE
                else ChinaAshareFoundationCoverageStatus.COMPLETE
            ),
        )
        for family in CHINA_ASHARE_FOUNDATION_FAMILY_ORDER
    )
    admission = build_china_ashare_daily_research_admission(
        target_sessions=(date(2026, 9, 15), date(2026, 9, 16)),
        families=families,
    )

    assert admission.status is ChinaAshareResearchAdmissionStatus.SOURCE_INCOMPLETE
    assert admission.blocking_families == (
        ChinaAshareFoundationFamily.RISK_WARNING_STATE,
    )
    assert not admission.daily_research_backtest_authorized


def test_quarantined_family_yields_quarantined_admission() -> None:
    families = tuple(
        _family(
            family,
            status=(
                ChinaAshareFoundationCoverageStatus.PARTIAL
                if family is ChinaAshareFoundationFamily.INSTRUMENT_LIFECYCLE
                else ChinaAshareFoundationCoverageStatus.COMPLETE
            ),
            quarantined=(
                1 if family is ChinaAshareFoundationFamily.INSTRUMENT_LIFECYCLE else 0
            ),
        )
        for family in CHINA_ASHARE_FOUNDATION_FAMILY_ORDER
    )
    admission = build_china_ashare_daily_research_admission(
        target_sessions=(date(2026, 9, 15), date(2026, 9, 16)),
        families=families,
    )
    assert admission.status is ChinaAshareResearchAdmissionStatus.QUARANTINED


def test_admission_rejects_family_order_and_fingerprint_tampering() -> None:
    families = tuple(_family(family) for family in CHINA_ASHARE_FOUNDATION_FAMILY_ORDER)
    with pytest.raises(ValidationError, match="incomplete or unordered"):
        build_china_ashare_daily_research_admission(
            target_sessions=(date(2026, 9, 16),),
            families=tuple(reversed(families)),
        )

    admission = build_china_ashare_daily_research_admission(
        target_sessions=(date(2026, 9, 16),),
        families=families,
    )
    payload = admission.model_dump(mode="json")
    payload["logical_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="fingerprint differs"):
        ChinaAshareDailyResearchAdmissionV1.model_validate(payload)
