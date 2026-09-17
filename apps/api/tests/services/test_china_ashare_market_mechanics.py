from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareCommissionBasis,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareExchange,
    ChinaAsharePilotPriceLimitDecisionV1,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradeSide,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.common import QualityStatus
from tip_api.services.china_ashare_market_mechanics import (
    build_official_market_mechanics_sources,
    build_pilot_fee_rules,
    build_pilot_market_mechanics_report,
    build_pilot_trading_rules,
    build_ping_an_account_cost_scenario,
    calculate_execution_cost,
    reconcile_pilot_price_limits,
)


NOW = datetime(2026, 9, 17, tzinfo=UTC)
INSTRUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


def _sources():
    return build_official_market_mechanics_sources(retrieved_at=NOW)


def _scenario():
    return build_ping_an_account_cost_scenario(
        first_target_session=date(2021, 9, 16), confirmed_at=NOW
    )


def test_user_reported_ping_an_cost_scenario_is_explicitly_provisional() -> None:
    scenario = _scenario()

    assert scenario.commission_rate_per_side == Decimal("0.0001")
    assert scenario.minimum_commission_cny_per_order == Decimal("5")
    assert scenario.commission_basis is ChinaAshareCommissionBasis.ALL_IN
    assert "all_in_commission_basis_pending_statement_confirmation" in scenario.reason_codes


def test_all_in_wanyi_minimum_five_avoids_duplicate_regulatory_fees() -> None:
    fees = build_pilot_fee_rules(source_references=_sources())
    buy = calculate_execution_cost(
        session_date=date(2026, 9, 16),
        exchange=ChinaAshareExchange.SSE,
        side=ChinaAshareTradeSide.BUY,
        gross_notional_cny=Decimal("10000"),
        fee_rules=fees,
        scenario=_scenario(),
    )
    sell = calculate_execution_cost(
        session_date=date(2026, 9, 16),
        exchange=ChinaAshareExchange.SSE,
        side=ChinaAshareTradeSide.SELL,
        gross_notional_cny=Decimal("10000"),
        fee_rules=fees,
        scenario=_scenario(),
    )

    assert buy.broker_commission_cny == Decimal("5.00")
    assert buy.securities_regulatory_fee_cny == Decimal("0.00")
    assert buy.exchange_handling_fee_cny == Decimal("0.00")
    assert buy.transfer_fee_cny == Decimal("0.10")
    assert buy.stamp_duty_cny == Decimal("0.00")
    assert buy.total_cost_cny == Decimal("10.10")
    assert sell.stamp_duty_cny == Decimal("5.00")
    assert sell.total_cost_cny == Decimal("15.10")


def test_fee_schedule_changes_on_the_official_effective_dates() -> None:
    fees = build_pilot_fee_rules(source_references=_sources())
    scenario = _scenario()
    before_transfer = calculate_execution_cost(
        session_date=date(2022, 4, 28),
        exchange=ChinaAshareExchange.SZSE,
        side=ChinaAshareTradeSide.BUY,
        gross_notional_cny=Decimal("100000"),
        fee_rules=fees,
        scenario=scenario,
    )
    after_transfer = calculate_execution_cost(
        session_date=date(2022, 4, 29),
        exchange=ChinaAshareExchange.SZSE,
        side=ChinaAshareTradeSide.BUY,
        gross_notional_cny=Decimal("100000"),
        fee_rules=fees,
        scenario=scenario,
    )
    before_tax_cut = calculate_execution_cost(
        session_date=date(2023, 8, 27),
        exchange=ChinaAshareExchange.SSE,
        side=ChinaAshareTradeSide.SELL,
        gross_notional_cny=Decimal("100000"),
        fee_rules=fees,
        scenario=scenario,
    )
    after_tax_cut = calculate_execution_cost(
        session_date=date(2023, 8, 28),
        exchange=ChinaAshareExchange.SSE,
        side=ChinaAshareTradeSide.SELL,
        gross_notional_cny=Decimal("100000"),
        fee_rules=fees,
        scenario=scenario,
    )

    assert before_transfer.transfer_fee_cny == Decimal("2.00")
    assert after_transfer.transfer_fee_cny == Decimal("1.00")
    assert before_tax_cut.stamp_duty_cny == Decimal("100.00")
    assert after_tax_cut.stamp_duty_cny == Decimal("50.00")


def test_risk_warning_limit_changes_from_five_to_ten_percent() -> None:
    rules = build_pilot_trading_rules(source_references=_sources())
    states = (
        _state(date(2026, 7, 3), risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED),
        _state(date(2026, 7, 6), risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED),
    )
    bars = (
        _bar(date(2026, 7, 3), high="10.50", low="9.50"),
        _bar(date(2026, 7, 6), high="11.00", low="9.00"),
    )
    package = _daily_package(states=states, bars=bars)

    decisions = reconcile_pilot_price_limits(
        daily_package=package, trading_rules=rules
    )

    assert decisions[0].price_limit_regime is ChinaAsharePriceLimitRegime.PERCENT_5
    assert decisions[0].theoretical_up_limit == Decimal("10.50")
    assert decisions[1].price_limit_regime is ChinaAsharePriceLimitRegime.PERCENT_10
    assert decisions[1].theoretical_up_limit == Decimal("11.00")
    assert all(item.observed_bar_within_limits for item in decisions)


def test_limit_decision_rejects_a_false_reconciliation_claim() -> None:
    with pytest.raises(ValidationError, match="result differs"):
        ChinaAsharePilotPriceLimitDecisionV1(
            instrument_id=INSTRUMENT_ID,
            session_date=date(2026, 9, 16),
            exchange=ChinaAshareExchange.SSE,
            board=ChinaAshareBoard.SSE_MAIN,
            trading_status=ChinaAshareTradingStatus.TRADING,
            risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
            price_limit_regime=ChinaAsharePriceLimitRegime.PERCENT_10,
            rule_id="example",
            pre_close=Decimal("10"),
            theoretical_up_limit=Decimal("11"),
            theoretical_down_limit=Decimal("9"),
            bar_high=Decimal("12"),
            bar_low=Decimal("10"),
            observed_bar_within_limits=True,
            quality_status=QualityStatus.REJECTED,
            reason_codes=("test_violation",),
        )


def test_market_mechanics_report_never_opens_research_by_itself() -> None:
    sources = _sources()
    rules = build_pilot_trading_rules(source_references=sources)
    fees = build_pilot_fee_rules(source_references=sources)
    package = _daily_package(
        states=(_state(date(2026, 9, 16)),),
        bars=(_bar(date(2026, 9, 16), high="10.50", low="9.50"),),
    )
    decisions = reconcile_pilot_price_limits(
        daily_package=package, trading_rules=rules
    )

    report = build_pilot_market_mechanics_report(
        daily_package=package,
        calendar_package_fingerprint="b" * 64,
        source_references=sources,
        trading_rules=rules,
        fee_rules=fees,
        decisions=decisions,
        account_cost_scenario=_scenario(),
        evaluated_at=NOW,
    )

    assert report.effective_dated_rules_reconciled is True
    assert report.effective_dated_fees_reconciled is True
    assert report.account_cost_scenario_registered is True
    assert report.research_backtest_authorized is False


def _state(
    session_date: date,
    *,
    risk: ChinaAshareRiskWarningStatus = ChinaAshareRiskWarningStatus.NONE,
) -> ChinaAshareDailyTradingStateV1:
    return ChinaAshareDailyTradingStateV1(
        instrument_id=INSTRUMENT_ID,
        session_date=session_date,
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        trading_status=ChinaAshareTradingStatus.TRADING,
        risk_warning_status=risk,
        price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
        pre_close=Decimal("10"),
        exact_limit_prices_source_observed=False,
        source="baostock_ashare",
        source_available_at=None,
        ingested_at=NOW,
        quality_status=QualityStatus.WARNING,
        reason_codes=("price_limit_requires_official_rule_resolution",),
    )


def _bar(session_date: date, *, high: str, low: str) -> ChinaAshareDailyBarV1:
    return ChinaAshareDailyBarV1(
        instrument_id=INSTRUMENT_ID,
        session_date=session_date,
        open=Decimal("10"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("10"),
        pre_close=Decimal("10"),
        volume_shares=Decimal("1000"),
        turnover_amount_cny=Decimal("10000"),
        source="baostock_ashare",
        source_available_at=None,
        ingested_at=NOW,
        revision=1,
        quality_status=QualityStatus.WARNING,
        reason_codes=("source_available_time_unreported",),
    )


def _daily_package(*, states, bars):
    batch = SimpleNamespace(trading_states=states, bars=bars)
    captured = SimpleNamespace(daily_batch=batch)
    manifest = SimpleNamespace(logical_fingerprint="a" * 64)
    return SimpleNamespace(captured=captured, manifest=manifest)
