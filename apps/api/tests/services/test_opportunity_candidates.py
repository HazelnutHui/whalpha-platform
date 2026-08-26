from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Rounded, localcontext
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateDataQualityStatus,
    CandidateMetricAvailability,
    CandidateRiskMode,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_0_0 import (
    CANDIDATE_PARAMETER_FINGERPRINT,
    COMPONENT_PARAMETERS,
)
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.opportunity_candidates import (
    OpportunityCandidateCalculationError,
    calculate_opportunity_candidate_scores,
    rank_opportunity_candidates,
)


NS = UUID("3d51d5d8-39c8-59c1-a084-01a89b96ea70")
PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"


def _id(label: str) -> UUID:
    return uuid5(NS, label)


def _panel(member_count: int = 40, adrc_count: int = 5) -> MarketRegimeInputPanel:
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(26))
    primary_ids = tuple(_id(f"stock-{index:03d}") for index in range(member_count))
    adrc_ids = tuple(_id(f"adrc-{index:03d}") for index in range(adrc_count))
    etf_tickers = ("SPY", "QQQ", "IWM", "DIA", "XLK", "SMH")
    etf_ids = {ticker: _id(f"etf-{ticker}") for ticker in etf_tickers}
    bars: list[MarketRegimeBar] = []
    for day_index, session in enumerate(sessions):
        day = Decimal(day_index)
        for index, instrument_id in enumerate(primary_ids + adrc_ids):
            base = Decimal("35") + Decimal(index) / Decimal("3")
            slope = Decimal("0.18") + Decimal(index % 9) / Decimal("100")
            curvature = Decimal((index % 5) - 2) / Decimal("10000")
            close = base + slope * day + curvature * day * day
            volume = Decimal("2200000") + Decimal(index * 17000 + day_index * 15000)
            ticker = f"S{index:03d}" if index < member_count else f"A{index - member_count:03d}"
            bars.append(_bar(instrument_id, ticker, "common_stock", session, close, volume))
        for order, (ticker, instrument_id) in enumerate(etf_ids.items()):
            close = (
                Decimal("90")
                + Decimal(order * 7)
                + day * (Decimal("0.20") + Decimal(order) / Decimal("50"))
                + day * day * Decimal(order + 1) / Decimal("20000")
            )
            volume = Decimal("8000000") + Decimal(order * 250000 + day_index * 20000)
            bars.append(_bar(instrument_id, ticker, "etf", session, close, volume))
    sources = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"market-data/eod/session={session.isoformat()}",
            record_count=len(primary_ids) + len(adrc_ids) + len(etf_ids),
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    universes = (
        MarketRegimeUniverseSource(PRIMARY, "Common Shares", True, 0, frozenset(primary_ids), "a" * 64),
        MarketRegimeUniverseSource(
            SECONDARY,
            "Common Shares + ADRs",
            False,
            1,
            frozenset(primary_ids + adrc_ids),
            "b" * 64,
        ),
    )
    return MarketRegimeInputPanel(
        as_of_session=sessions[-1],
        calendar_id="XNYS",
        calendar_version="fixture",
        sessions=sessions,
        source_sessions=sources,
        bars=tuple(bars),
        universes=universes,
        activation_pointer_fingerprint="c" * 64,
        identity_logical_fingerprint="d" * 64,
        eod_content_fingerprint="e" * 64,
        eod_business_key_fingerprint="f" * 64,
        history_source_fingerprint="1" * 64,
    )


def _bar(instrument_id, ticker, kind, session, close, volume) -> MarketRegimeBar:
    return MarketRegimeBar(
        instrument_id=instrument_id,
        ticker=ticker,
        instrument_type=kind,
        primary_exchange="XNYS",
        session_date=session,
        open=close,
        high=close * Decimal("1.01"),
        low=close * Decimal("0.99"),
        close=close,
        volume=volume,
    )


@pytest.fixture(scope="module")
def full_panel() -> MarketRegimeInputPanel:
    return _panel()


def _calculate(panel: MarketRegimeInputPanel, universe_id: str = PRIMARY):
    universe = panel.select_universe(universe_id)
    confirmations = {instrument_id: 3 for instrument_id in universe.member_ids}
    return calculate_opportunity_candidate_scores(
        panel=panel,
        universe_id=universe_id,
        regime_score=Decimal("72.5000"),
        regime_state=RegimeState.RISK_ON,
        regime_source_fingerprint="2" * 64,
        state_confirmation_counts=confirmations,
    )


def test_fixed_parameter_and_complete_candidate_ledger(full_panel: MarketRegimeInputPanel) -> None:
    batch = _calculate(full_panel)
    assert batch.parameter_fingerprint == CANDIDATE_PARAMETER_FINGERPRINT
    assert batch.universe_member_count == 40
    assert batch.bar_covered_member_count == 40
    assert not batch.missing_member_ids
    assert tuple(item.component_id for item in batch.candidates[0].components) == tuple(
        item.component_id for item in COMPONENT_PARAMETERS
    )
    for candidate in batch.candidates:
        assert candidate.base_score == candidate.adjusted_score
        assert candidate.regime_adjustment == "0.0000"
        assert Decimal(candidate.configured_weight_available) >= Decimal("80")
        assert sum(
            Decimal(item.contribution)
            for item in candidate.components
            if item.contribution is not None
        ).quantize(Decimal("0.0001")) == Decimal(candidate.base_score)
        proxy = next(item for item in candidate.components if item.component_id == "etf_sector_alignment")
        if proxy.score is not None:
            assert Decimal(proxy.score) <= Decimal("70")
        assert "candidate_score_not_success_probability" in candidate.warnings
        assert "underlying_stock_score_not_option_return" in candidate.warnings


def test_secondary_marks_only_formal_delta_as_adrc(full_panel: MarketRegimeInputPanel) -> None:
    primary = _calculate(full_panel, PRIMARY)
    secondary = _calculate(full_panel, SECONDARY)
    primary_ids = {item.instrument_id for item in primary.candidates}
    shared = [item for item in secondary.candidates if item.instrument_id in primary_ids]
    extras = [item for item in secondary.candidates if item.instrument_id not in primary_ids]
    assert all(item.security_type == "CS" for item in shared)
    assert len(extras) == 5 and all(item.security_type == "ADRC" for item in extras)


def test_missing_proxy_component_reweights_without_inventing_sector(full_panel: MarketRegimeInputPanel) -> None:
    spy_id = _id("etf-SPY")
    bars = tuple(
        replace(item, open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"))
        if item.instrument_id == spy_id
        else item
        for item in full_panel.bars
    )
    batch = _calculate(replace(full_panel, bars=bars))
    assert batch.candidates
    for candidate in batch.candidates:
        proxy = next(item for item in candidate.components if item.component_id == "etf_sector_alignment")
        if candidate.primary_driver_ticker is None:
            assert proxy.availability is CandidateMetricAvailability.UNAVAILABLE
            assert candidate.relationship_kind is None
            assert Decimal(candidate.configured_weight_available) == Decimal("87.0000")
            assert candidate.base_score is not None


def test_more_than_twenty_missing_weight_makes_score_null(full_panel: MarketRegimeInputPanel) -> None:
    target = _id("stock-000")
    bars = tuple(
        item
        for item in full_panel.bars
        if item.instrument_id != target or item.session_date == full_panel.as_of_session
    )
    batch = _calculate(replace(full_panel, bars=bars))
    candidate = next(item for item in batch.candidates if item.instrument_id == target)
    assert Decimal(candidate.configured_weight_available) < Decimal("80")
    assert candidate.base_score is None
    assert candidate.adjusted_score is None
    assert candidate.data_quality_status is CandidateDataQualityStatus.DEGRADED
    assert "candidate_score_unavailable_due_to_component_missingness" in candidate.warnings


def test_extreme_move_quarantines_and_cannot_rank(full_panel: MarketRegimeInputPanel) -> None:
    target = _id("stock-000")
    latest = full_panel.as_of_session
    original = next(item for item in full_panel.bars if item.instrument_id == target and item.session_date == latest)
    extreme_close = original.close * Decimal("2")
    extreme = replace(
        original,
        open=extreme_close,
        high=extreme_close * Decimal("1.01"),
        low=extreme_close * Decimal("0.99"),
        close=extreme_close,
    )
    bars = tuple(extreme if item.instrument_id == target and item.session_date == latest else item for item in full_panel.bars)
    batch = _calculate(replace(full_panel, bars=bars))
    candidate = next(item for item in batch.candidates if item.instrument_id == target)
    assert candidate.corporate_action_review_required
    assert candidate.data_quality_status is CandidateDataQualityStatus.QUARANTINED
    ranked = rank_opportunity_candidates(batch=batch, risk_mode=CandidateRiskMode.AGGRESSIVE)
    assessment = next(item for item in ranked.assessments if item.instrument_id == target)
    assert not assessment.eligible
    assert "candidate_quarantined" in assessment.rejection_reason_codes


def test_risk_modes_change_only_eligibility_and_rank(full_panel: MarketRegimeInputPanel) -> None:
    batch = _calculate(full_panel, SECONDARY)
    conservative = rank_opportunity_candidates(batch=batch, risk_mode="conservative")
    balanced = rank_opportunity_candidates(batch=batch, risk_mode="balanced")
    aggressive = rank_opportunity_candidates(batch=batch, risk_mode="aggressive")
    assert all(
        not item.eligible
        for item in conservative.assessments
        if next(candidate for candidate in batch.candidates if candidate.instrument_id == item.instrument_id).security_type == "ADRC"
    )
    assert conservative.eligible_count <= 5  # 20% of the fixed 25-row cap for one dominant proxy group.
    assert balanced.eligible_count <= 12  # 25% of 50, rounded down.
    assert aggressive.eligible_count <= 35  # 35% of 100.
    assert batch.logical_fingerprint == _calculate(full_panel, SECONDARY).logical_fingerprint


@pytest.mark.parametrize("precision", (9, 28, 50))
@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP))
def test_decimal_context_and_outer_traps_do_not_change_candidate_fingerprint(
    full_panel: MarketRegimeInputPanel, precision: int, rounding: str
) -> None:
    expected = _calculate(full_panel)
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        actual = _calculate(full_panel)
    assert actual.logical_fingerprint == expected.logical_fingerprint


def test_bad_source_binding_and_unknown_universe_fail_closed(full_panel: MarketRegimeInputPanel) -> None:
    with pytest.raises(OpportunityCandidateCalculationError, match="SHA-256"):
        calculate_opportunity_candidate_scores(
            panel=full_panel,
            universe_id=PRIMARY,
            regime_score="50",
            regime_state="balanced",
            regime_source_fingerprint="bad",
        )
    with pytest.raises(Exception, match="unknown active Universe"):
        calculate_opportunity_candidate_scores(
            panel=full_panel,
            universe_id="legacy",
            regime_score="50",
            regime_state="balanced",
            regime_source_fingerprint="2" * 64,
        )
