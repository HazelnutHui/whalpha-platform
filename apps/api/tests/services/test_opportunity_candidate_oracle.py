from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal, Inexact, ROUND_DOWN, Rounded, localcontext
from pathlib import Path
from uuid import UUID, uuid5

from tip_api.contracts.analytics.v1 import (
    CandidateBreakoutAvailability,
    CandidateBreakoutFactV1,
    CandidateDataQualityStatus,
    CandidatePriorStateSourceV1,
    CandidateRiskMode,
    CandidateStateObservationV1,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_NON_BLOCKING_QUALITY_FLAGS,
    CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
)
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.opportunity_candidate_oracle import (
    CandidateStateOracleCase,
    compare_with_independent_candidate_oracle,
)
from tip_api.services.opportunity_candidate_state import replay_opportunity_candidate_state_history
from tip_api.services.opportunity_candidates import calculate_opportunity_candidate_scores, rank_opportunity_candidates


PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"
NS = UUID("2a2776f0-156e-50cf-b012-b48090549bd0")


def _id(label: str) -> UUID:
    return uuid5(NS, label)


def _panel() -> MarketRegimeInputPanel:
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(26))
    primary = tuple(_id(f"stock-{index}") for index in range(24))
    adrs = tuple(_id(f"adr-{index}") for index in range(4))
    etfs = {ticker: _id(f"etf-{ticker}") for ticker in ("SPY", "QQQ", "IWM", "DIA", "XLK", "SMH")}
    bars = []
    for day_index, session in enumerate(sessions):
        day = Decimal(day_index)
        for index, instrument_id in enumerate((*primary, *adrs)):
            base = Decimal("28") + Decimal(index)
            # ADR slopes are deliberately extreme so Secondary normalization differs.
            slope = Decimal("0.13") + Decimal(index % 7) / Decimal("100")
            if index >= len(primary):
                slope += Decimal(index - len(primary) + 1) / Decimal("5")
            close = base + slope * day + Decimal((index % 3) - 1) * day * day / Decimal("10000")
            volume = Decimal("2400000") + Decimal(index * 24000 + day_index * 18000)
            ticker = f"S{index:02d}" if index < len(primary) else f"A{index-len(primary):02d}"
            bars.append(_bar(instrument_id, ticker, "common_stock", session, close, volume))
        for index, (ticker, instrument_id) in enumerate(etfs.items()):
            close = Decimal("85") + Decimal(index * 8) + day * (Decimal("0.18") + Decimal(index) / Decimal("45")) + day * day * Decimal(index + 1) / Decimal("18000")
            bars.append(_bar(instrument_id, ticker, "etf", session, close, Decimal("9000000") + Decimal(index * 300000 + day_index * 25000)))
    sources = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"market-data/eod/session={session}",
            record_count=len(primary) + len(adrs) + len(etfs),
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    return MarketRegimeInputPanel(
        as_of_session=sessions[-1],
        calendar_id="XNYS",
        calendar_version="oracle-fixture",
        sessions=sessions,
        source_sessions=sources,
        bars=tuple(bars),
        universes=(
            MarketRegimeUniverseSource(PRIMARY, "Primary", True, 0, frozenset(primary), "a" * 64),
            MarketRegimeUniverseSource(SECONDARY, "Secondary", False, 1, frozenset((*primary, *adrs)), "b" * 64),
        ),
        activation_pointer_fingerprint="c" * 64,
        identity_logical_fingerprint="d" * 64,
        eod_content_fingerprint="e" * 64,
        eod_business_key_fingerprint="f" * 64,
        history_source_fingerprint="1" * 64,
    )


def _bar(instrument_id, ticker, kind, session, close, volume):
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


def _bootstrap(panel, universe_id):
    return CandidatePriorStateSourceV1(
        universe_id=universe_id,
        as_of_session=panel.as_of_session,
        bootstrap=True,
        source_state_session=None,
        state_history_fingerprint=CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
        supports=(),
    )


def _actuals(panel):
    batches = tuple(
        calculate_opportunity_candidate_scores(
            panel=panel,
            universe_id=universe_id,
            regime_score=score,
            regime_state=state,
            regime_source_fingerprint=("2" if universe_id == PRIMARY else "3") * 64,
            prior_state_source=_bootstrap(panel, universe_id),
        )
        for universe_id, score, state in (
            (PRIMARY, Decimal("62.5000"), RegimeState.BALANCED),
            (SECONDARY, Decimal("58.2500"), RegimeState.DEFENSIVE),
        )
    )
    risks = tuple(
        rank_opportunity_candidates(batch=batch, risk_mode=mode)
        for batch in batches
        for mode in CandidateRiskMode
    )
    return batches, risks


def _state_case(panel, batch):
    candidate = batch.candidates[0]
    bars = {
        item.session_date: item
        for item in panel.bars
        if item.instrument_id == candidate.instrument_id
    }
    prior_sessions = panel.sessions[-6:-1]
    prior_high = max(bars[item].close for item in prior_sessions)
    close = bars[panel.as_of_session].close
    ratio = Decimal(candidate.current_volume_ratio)
    triggered = close > prior_high and ratio >= Decimal("1.20")
    breakout = CandidateBreakoutFactV1(
        as_of_session=panel.as_of_session,
        instrument_id=candidate.instrument_id,
        availability=CandidateBreakoutAvailability.AVAILABLE,
        close=f"{close:.10f}",
        prior_five_session_close_high=f"{prior_high:.10f}",
        current_volume_ratio=candidate.current_volume_ratio,
        prior_five_sessions=prior_sessions,
        triggered=triggered,
        missing_reason=None,
        reason_codes=("typed_breakout_fact",),
    )
    observation = CandidateStateObservationV1(
        candidate=candidate,
        regime_state=RegimeState.BALANCED,
        breakout_fact=breakout,
    )
    actual = replay_opportunity_candidate_state_history(
        observations=(observation,),
        expected_sessions=(panel.as_of_session,),
        universe_id=batch.universe_id,
        instrument_id=candidate.instrument_id,
        ticker=candidate.ticker,
        security_type=candidate.security_type,
    )
    return CandidateStateOracleCase(
        observations=(observation,),
        expected_sessions=(panel.as_of_session,),
        universe_id=batch.universe_id,
        instrument_id=candidate.instrument_id,
        ticker=candidate.ticker,
        security_type=candidate.security_type,
        actual_records=actual,
    )


def _compare(panel, batches, risks, state_cases=()):
    return compare_with_independent_candidate_oracle(
        panel=panel,
        batches=batches,
        regime_context_by_universe={
            PRIMARY: (Decimal("62.5000"), RegimeState.BALANCED),
            SECONDARY: (Decimal("58.2500"), RegimeState.DEFENSIVE),
        },
        risk_results=risks,
        state_cases=state_cases,
    )


def test_independent_oracle_reproduces_scores_risks_and_bootstrap_state() -> None:
    panel = _panel()
    batches, risks = _actuals(panel)
    report = _compare(panel, batches, risks, (_state_case(panel, batches[0]),))
    assert report.mismatch_count == 0, report.mismatches[:10]
    assert report.candidate_count == 52
    assert report.risk_result_count == 6
    assert report.state_record_count == 1
    assert report.shared_raw_fact_match
    assert report.input_permutation_match


def test_one_field_mutation_is_reported() -> None:
    panel = _panel()
    batches, risks = _actuals(panel)
    changed_candidate = batches[0].candidates[0].model_copy(update={"latest_price": "999.0000000000"})
    changed_batch = batches[0].model_copy(update={"candidates": (changed_candidate, *batches[0].candidates[1:])})
    report = _compare(panel, (changed_batch, batches[1]), risks)
    assert report.mismatch_count > 0
    assert any("latest_price" in item for item in report.mismatches)


def test_oracle_is_decimal_context_and_input_order_invariant() -> None:
    panel = _panel()
    batches, risks = _actuals(panel)
    expected = _compare(panel, batches, risks)
    with localcontext() as context:
        context.prec = 9
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        actual = _compare(replace(panel, bars=tuple(reversed(panel.bars))), batches, risks)
    assert actual.mismatch_count == 0
    assert actual.oracle_fingerprint == expected.oracle_fingerprint


def test_shared_raw_facts_are_equal_but_universe_scores_may_differ() -> None:
    panel = _panel()
    batches, risks = _actuals(panel)
    report = _compare(panel, batches, risks)
    assert report.shared_raw_fact_match
    primary = {item.instrument_id: item for item in batches[0].candidates}
    secondary = {item.instrument_id: item for item in batches[1].candidates}
    assert any(primary[key].base_score != secondary[key].base_score for key in primary)


def test_oracle_module_does_not_import_production_candidate_services() -> None:
    source = Path(__file__).parents[2] / "src/tip_api/services/opportunity_candidate_oracle.py"
    text = source.read_text(encoding="utf-8")
    assert "tip_api.services.opportunity_candidates" not in text
    assert "tip_api.services.opportunity_candidate_state" not in text


def test_oracle_matches_allowlisted_unknown_and_nonunit_quality_policy() -> None:
    target = _id("stock-0")
    baseline = _panel()
    cases = (
        ({"quality_flags": CANDIDATE_NON_BLOCKING_QUALITY_FLAGS}, False),
        ({"quality_flags": ("unregistered_provider_flag",)}, True),
        ({"split_adjustment_factor": Decimal("2")}, True),
    )
    for changes, quarantined in cases:
        panel = replace(
            baseline,
            bars=tuple(
                replace(item, **changes)
                if item.instrument_id == target and item.session_date == baseline.as_of_session
                else item
                for item in baseline.bars
            ),
        )
        batches, risks = _actuals(panel)
        report = _compare(panel, batches, risks)
        assert report.mismatch_count == 0, report.mismatches[:10]
        candidate = next(item for item in batches[0].candidates if item.instrument_id == target)
        assert candidate.corporate_action_review_required is quarantined
        if quarantined:
            assert candidate.data_quality_status is CandidateDataQualityStatus.QUARANTINED
        else:
            assert candidate.data_quality_status is CandidateDataQualityStatus.DEGRADED
            assert all(
                f"non_blocking_source_quality_flag:{flag}" in candidate.warnings
                for flag in CANDIDATE_NON_BLOCKING_QUALITY_FLAGS
            )
