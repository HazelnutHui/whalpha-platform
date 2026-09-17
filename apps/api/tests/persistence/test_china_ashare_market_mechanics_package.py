from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareMarketMechanicsReportV1,
    ChinaAsharePilotPriceLimitDecisionV1,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
    build_market_mechanics_report,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_market_mechanics_package import (
    ChinaAshareMarketMechanicsPackageCorruptionError,
    publish_china_ashare_market_mechanics_package,
    read_china_ashare_market_mechanics_package,
)
from tip_api.providers.china_ashare.official_market_mechanics_adapter import (
    CapturedOfficialMarketMechanicsSourceV1,
)
from tip_api.services.china_ashare_market_mechanics import (
    build_official_market_mechanics_sources,
    build_pilot_fee_rules,
    build_pilot_trading_rules,
    build_ping_an_account_cost_scenario,
)


NOW = datetime(2026, 9, 17, tzinfo=UTC)


def test_market_mechanics_package_exact_reread_and_tamper_detection(tmp_path) -> None:
    sources = build_official_market_mechanics_sources(retrieved_at=NOW)
    captured = tuple(_capture(item) for item in sources)
    captured_references = tuple(item.reference for item in captured)
    trading_rules = build_pilot_trading_rules(
        source_references=captured_references
    )
    fee_rules = build_pilot_fee_rules(source_references=captured_references)
    scenario = build_ping_an_account_cost_scenario(
        first_target_session=date(2021, 9, 16), confirmed_at=NOW
    )
    decisions = (_decision(),)
    report = _report(
        source_count=len(captured),
        trading_rule_count=len(trading_rules),
        fee_rule_count=len(fee_rules),
    )
    custody = tmp_path / "china-a-share-research-pilot"
    custody.mkdir(mode=0o700)

    result = publish_china_ashare_market_mechanics_package(
        custody_root=custody,
        captured_sources=captured,
        trading_rules=trading_rules,
        fee_rules=fee_rules,
        account_cost_scenario=scenario,
        price_limit_decisions=decisions,
        report=report,
    )
    reread = read_china_ashare_market_mechanics_package(
        package_path=result.package_path
    )

    assert reread.status == "exact_reread_complete"
    assert reread.report == report
    assert reread.source_references == tuple(
        sorted(captured_references, key=lambda item: item.source_id)
    )
    assert reread.file_count == 20
    assert reread.manifest.research_backtest_authorized is False

    source_path = result.package_path / "raw/commission-standard-2002.html"
    source_path.chmod(0o600)
    source_path.write_bytes(b"changed")
    source_path.chmod(0o400)
    with pytest.raises(
        ChinaAshareMarketMechanicsPackageCorruptionError,
        match="bytes differ",
    ):
        read_china_ashare_market_mechanics_package(package_path=result.package_path)


def _capture(reference):
    raw = f"<!doctype html><html>{reference.source_id}</html>".encode()
    captured_reference = reference.model_copy(
        update={
            "final_url": reference.source_url,
            "content_type": "text/html",
            "raw_byte_size": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    return CapturedOfficialMarketMechanicsSourceV1(
        reference=captured_reference,
        raw_bytes=raw,
    )


def _decision() -> ChinaAsharePilotPriceLimitDecisionV1:
    return ChinaAsharePilotPriceLimitDecisionV1(
        instrument_id=UUID("00000000-0000-0000-0000-000000000001"),
        session_date=date(2026, 9, 16),
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        trading_status=ChinaAshareTradingStatus.TRADING,
        risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
        price_limit_regime=ChinaAsharePriceLimitRegime.PERCENT_10,
        rule_id="sse-main-normal-registration-v1",
        pre_close=Decimal("10"),
        theoretical_up_limit=Decimal("11"),
        theoretical_down_limit=Decimal("9"),
        bar_high=Decimal("10.5"),
        bar_low=Decimal("9.5"),
        observed_bar_within_limits=True,
        quality_status=QualityStatus.VALID,
        reason_codes=(
            "official_effective_dated_rule_applied",
            "theoretical_limit_not_source_observed",
        ),
    )


def _report(
    *, source_count: int, trading_rule_count: int, fee_rule_count: int
) -> ChinaAshareMarketMechanicsReportV1:
    return build_market_mechanics_report(
        daily_package_fingerprint="a" * 64,
        calendar_package_fingerprint="b" * 64,
        evaluated_at=NOW,
        target_session_count=1,
        source_reference_count=source_count,
        trading_rule_count=trading_rule_count,
        fee_rule_count=fee_rule_count,
        price_limit_decision_count=1,
        price_limit_bar_count=1,
        suspended_decision_count=0,
        price_limit_violation_count=0,
        unresolved_rule_count=0,
        effective_dated_rules_reconciled=True,
        effective_dated_fees_reconciled=True,
        account_cost_scenario_registered=True,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=(
            "market_mechanics_gate_reconciled",
            "research_authority_requires_remaining_foundation_families",
        ),
    )
