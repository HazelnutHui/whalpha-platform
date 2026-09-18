from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingRuleV1,
)
from tip_api.contracts.china_ashare.v1.price_limit_resolver import (
    ChinaAshareListingStage,
    ChinaAsharePriceLimitResolutionStatus,
)
from tip_api.contracts.common import QualityStatus
from tip_api.services.china_ashare_price_limit_resolver import (
    build_price_limit_partition_aggregate_from_resolutions,
    plan_china_ashare_price_limit_resolver,
    resolve_china_ashare_price_limit,
)


INSTRUMENT = UUID("00000000-0000-0000-0000-000000000001")
PARTITION = "2" * 64


def test_normal_main_board_and_growth_board_rules_resolve_without_outcomes() -> None:
    plan, rules = _plan()
    main = _resolve(
        plan,
        rules,
        session_date=date(2024, 1, 8),
        listing_date=date(2020, 1, 2),
        listing_session_ordinal=900,
    )
    growth = _resolve(
        plan,
        rules,
        exchange=ChinaAshareExchange.SZSE,
        board=ChinaAshareBoard.CHINEXT,
        session_date=date(2024, 1, 8),
        listing_date=date(2020, 1, 2),
        listing_session_ordinal=900,
    )

    assert main.status is ChinaAsharePriceLimitResolutionStatus.RESOLVED
    assert main.price_limit_regime is ChinaAsharePriceLimitRegime.PERCENT_10
    assert growth.price_limit_regime is ChinaAsharePriceLimitRegime.PERCENT_20
    assert main.outcome_read_count == 0
    assert main.as_operated is False
    assert main.research_eligible is False


def test_proven_post_registration_ipo_session_resolves_no_limit() -> None:
    plan, rules = _plan()
    decision = _resolve(
        plan,
        rules,
        session_date=date(2024, 1, 8),
        listing_date=date(2024, 1, 8),
        listing_stage=ChinaAshareListingStage.ORIGINAL_IPO,
        listing_session_ordinal=1,
    )

    assert decision.status is ChinaAsharePriceLimitResolutionStatus.RESOLVED
    assert decision.price_limit_regime is ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT
    assert decision.daily_price_limit_ratio is None


def test_proven_mature_stage_does_not_require_false_exact_ordinal() -> None:
    plan, rules = _plan()
    decision = _resolve(plan, rules, listing_session_ordinal=None)

    assert decision.status is ChinaAsharePriceLimitResolutionStatus.RESOLVED
    assert decision.price_limit_regime is ChinaAsharePriceLimitRegime.PERCENT_10
    assert "listing_session_ordinal_unproven" not in decision.reason_codes


def test_legacy_ipo_transition_without_specific_rule_is_quarantined() -> None:
    plan, rules = _plan()
    decision = _resolve(
        plan,
        rules,
        session_date=date(2022, 2, 7),
        listing_date=date(2022, 1, 4),
        listing_stage=ChinaAshareListingStage.ORIGINAL_IPO,
        listing_session_ordinal=20,
    )

    assert decision.status is ChinaAsharePriceLimitResolutionStatus.QUARANTINED
    assert decision.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN
    assert "legacy_ipo_stage_transition_rule_missing" in decision.reason_codes


def test_warning_relisting_and_terminal_gaps_each_fail_closed() -> None:
    plan, rules = _plan()
    warning = _resolve(
        plan,
        rules,
        risk_warning_status=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
    )
    relisting = _resolve(plan, rules, relisting_absence_evidence_complete=False)
    terminal = _resolve(
        plan, rules, terminal_boundary_absence_evidence_complete=False
    )

    assert all(
        item.status is ChinaAsharePriceLimitResolutionStatus.QUARANTINED
        for item in (warning, relisting, terminal)
    )
    assert "risk_warning_subtype_or_transition_not_adjudicated" in warning.reason_codes
    assert "relisting_absence_evidence_incomplete" in relisting.reason_codes
    assert "terminal_boundary_evidence_incomplete" in terminal.reason_codes


def test_partition_aggregate_is_deterministic_and_preserves_closed_authority() -> None:
    plan, rules = _plan()
    first = _resolve(plan, rules)
    second = _resolve(plan, rules, risk_warning_evidence_complete=False)
    resolutions = (first, second)

    aggregate = build_price_limit_partition_aggregate_from_resolutions(
        plan=plan,
        partition_index=0,
        input_partition_manifest_fingerprint=PARTITION,
        resolutions=resolutions,
    )
    replay = build_price_limit_partition_aggregate_from_resolutions(
        plan=plan,
        partition_index=0,
        input_partition_manifest_fingerprint=PARTITION,
        resolutions=resolutions,
    )

    assert aggregate.logical_fingerprint == replay.logical_fingerprint
    assert aggregate.state_count == 2
    assert aggregate.resolved_count == 1
    assert aggregate.quarantined_count == 1
    assert aggregate.warning_evidence_gap_count == 1
    assert aggregate.outcome_read_count == 0
    assert aggregate.as_operated_claim_authorized is False
    assert aggregate.research_backtest_authorized is False


def _plan():
    rules = (
        _rule(
            "sse-main-legacy",
            ChinaAshareExchange.SSE,
            ChinaAshareBoard.SSE_MAIN,
            date(2021, 9, 16),
            date(2023, 4, 9),
            "0.10",
            0,
        ),
        _rule(
            "sse-main-registration",
            ChinaAshareExchange.SSE,
            ChinaAshareBoard.SSE_MAIN,
            date(2023, 4, 10),
            None,
            "0.10",
            5,
        ),
        _rule(
            "szse-chinext",
            ChinaAshareExchange.SZSE,
            ChinaAshareBoard.CHINEXT,
            date(2021, 9, 16),
            None,
            "0.20",
            5,
        ),
    )
    mechanics = SimpleNamespace(
        manifest=SimpleNamespace(logical_fingerprint="1" * 64),
        trading_rules=rules,
    )
    return plan_china_ashare_price_limit_resolver(mechanics=mechanics), rules


def _rule(rule_id, exchange, board, effective_from, effective_to, ratio, ipo_count):
    observed = datetime(2026, 9, 1, tzinfo=UTC)
    return ChinaAshareTradingRuleV1(
        rule_id=rule_id,
        exchange=exchange,
        board=board,
        risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
        effective_from=effective_from,
        effective_to=effective_to,
        daily_price_limit_ratio=Decimal(ratio),
        ipo_no_limit_session_count=ipo_count,
        minimum_buy_order_shares=100,
        order_increment_shares=100,
        official_source_url="https://www.sse.com.cn/example",
        source_available_at=observed,
        ingested_at=observed,
        quality_status=QualityStatus.VALID,
    )


def _resolve(
    plan,
    rules,
    *,
    exchange=ChinaAshareExchange.SSE,
    board=ChinaAshareBoard.SSE_MAIN,
    risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
    session_date=date(2024, 1, 8),
    listing_date=date(2020, 1, 2),
    listing_stage=ChinaAshareListingStage.MATURE_LISTING,
    listing_session_ordinal=900,
    original_listing_evidence_complete=True,
    risk_warning_evidence_complete=True,
    relisting_absence_evidence_complete=True,
    terminal_boundary_absence_evidence_complete=True,
):
    return resolve_china_ashare_price_limit(
        plan=plan,
        trading_rules=rules,
        instrument_id=INSTRUMENT,
        session_date=session_date,
        exchange=exchange,
        board=board,
        risk_warning_status=risk_warning_status,
        listing_date=listing_date,
        listing_stage=listing_stage,
        listing_session_ordinal=listing_session_ordinal,
        original_listing_evidence_complete=original_listing_evidence_complete,
        risk_warning_evidence_complete=risk_warning_evidence_complete,
        relisting_absence_evidence_complete=relisting_absence_evidence_complete,
        terminal_boundary_absence_evidence_complete=(
            terminal_boundary_absence_evidence_complete
        ),
        input_partition_manifest_fingerprint=PARTITION,
    )
