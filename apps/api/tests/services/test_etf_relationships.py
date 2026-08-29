from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Rounded, localcontext
from pathlib import Path
import tempfile
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.analytics.v1.etf_relationship import (
    MarketRegimeRelationshipComparisonV1,
    RegimeRelationshipAlignment,
    RelationshipAvailability,
    RelationshipState,
)
from tip_api.parameters.market_regime.relationship_v1_0_0 import ETF_BASKET, ETF_PAIRS, RELATIONSHIP_PARAMETER_FINGERPRINT
from tip_api.services.etf_relationship_audit import read_etf_relationship_audit, read_etf_relationship_planning_evidence, write_etf_relationship_audit
from tip_api.services.etf_relationship_oracle import _oracle_state, compare_with_independent_relationship_oracle
from tip_api.services.etf_relationship_cli import _equivalence_checks, _first_available_sessions
from tip_api.services.etf_relationships import (
    EtfRelationshipError,
    _relationship_state,
    append_etf_relationship_history,
    build_relationship_explanations,
    calculate_etf_relationship_history,
    current_relationship_records,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_sources import MarketRegimeBar, MarketRegimeInputPanel, MarketRegimeSourceSession, MarketRegimeUniverseSource


NS=UUID("3c7d340f-7633-5e27-8f5d-065a46d45117")


def _panel() -> MarketRegimeInputPanel:
    calendar=ExchangeCalendar(); as_of=date(2026,8,21); sessions=calendar.sessions_before(as_of,25)+(as_of,)
    bars=[]
    for order,entry in enumerate(ETF_BASKET):
        instrument_id=uuid5(NS,entry.ticker)
        for day,session in enumerate(sessions):
            drift=Decimal((order%9)-3)/Decimal("20")
            wave=Decimal(((day+order)%5)-2)/Decimal("100")
            close=Decimal(100+order)+Decimal(day)*(Decimal("0.25")+drift)+wave
            bars.append(MarketRegimeBar(instrument_id,entry.ticker,"etf","ARCX",session,close,close,close,close,Decimal(1_000_000+order*1000+day)))
    sources=tuple(MarketRegimeSourceSession(item,f"eod/{item}",len(ETF_BASKET),f"{index+1:064x}",f"{index+101:064x}",item,f"{index+201:064x}") for index,item in enumerate(sessions))
    universes=(MarketRegimeUniverseSource("provider_classified_common_shares_v1","Common Shares",True,0,frozenset(),"a"*64),MarketRegimeUniverseSource("provider_classified_common_shares_plus_adrs_v1","Common Shares + ADRs",False,1,frozenset(),"b"*64))
    return MarketRegimeInputPanel(as_of,"XNYS",calendar.calendar_version,sessions,sources,tuple(bars),universes,"c"*64,"d"*64,"e"*64,"f"*64,"1"*64)


@pytest.fixture(scope="module")
def panel(): return _panel()


def test_registry_is_exact_and_full_history_matches_independent_oracle(panel):
    assert len(ETF_BASKET)==30 and len({item.ticker for item in ETF_BASKET})==30
    assert len(ETF_PAIRS)==16 and len({item.pair_id for item in ETF_PAIRS})==16
    history=calculate_etf_relationship_history(panel=panel)
    assert len(history)==21*16
    current=current_relationship_records(history,as_of_session=panel.as_of_session)
    assert len(current)==16 and all(len(item.windows)==3 for item in current)
    assert all(item.ratio_robust_z is None and item.confidence.value=="low" for item in current)
    assert _first_available_sessions(history)=={"window_5":panel.sessions[5].isoformat(),"window_10":panel.sessions[10].isoformat(),"window_20":panel.sessions[20].isoformat()}
    oracle=compare_with_independent_relationship_oracle(panel=panel,records=history,append_full_replay_match=True,input_permutation_match=True,future_prefix_stable=True)
    assert oracle.mismatch_count==0, oracle.mismatches
    assert all(_equivalence_checks(panel,history).values())


def test_window_endpoints_and_first_availability_are_not_off_by_one(panel):
    history=calculate_etf_relationship_history(panel=panel)
    pair=ETF_PAIRS[0].pair_id
    five=next(item for item in history if item.pair_id==pair and item.as_of_session==panel.sessions[5])
    assert five.windows[0].start_session==panel.sessions[0]
    assert five.windows[0].daily_return_observation_count==5
    assert five.windows[1].availability is RelationshipAvailability.UNAVAILABLE
    ten=next(item for item in history if item.pair_id==pair and item.as_of_session==panel.sessions[10])
    twenty=next(item for item in history if item.pair_id==pair and item.as_of_session==panel.sessions[20])
    assert ten.windows[1].start_session==panel.sessions[0]
    assert twenty.windows[2].start_session==panel.sessions[0]
    assert twenty.windows[2].daily_return_observation_count==20


def test_relationship_state_priority_boundaries(panel):
    history=calculate_etf_relationship_history(panel=panel)
    windows=next(item for item in history if item.as_of_session==panel.as_of_session).windows
    break_state,_=_relationship_state(windows=windows,ratio_z=None,prior_ratio_z=None,prior_spread=None,current_corr=Decimal("0.10"),prior_corr=Decimal("0.50"),corr_change=Decimal("-0.40"),availability=RelationshipAvailability.AVAILABLE)
    assert break_state is RelationshipState.RELATIONSHIP_BREAK_CANDIDATE
    five=windows[0].model_copy(update={"left_return":"0.0200000000","right_return":"-0.0100000000","relative_return":"0.0300000000"})
    divergence,_=_relationship_state(windows=(five,*windows[1:]),ratio_z=None,prior_ratio_z=None,prior_spread=None,current_corr=Decimal("0.90"),prior_corr=None,corr_change=None,availability=RelationshipAvailability.AVAILABLE)
    assert divergence is RelationshipState.DIVERGENCE
    rotation,_=_relationship_state(windows=(five,*windows[1:]),ratio_z=Decimal("1.50"),prior_ratio_z=Decimal("1.50"),prior_spread=Decimal("0.03"),current_corr=Decimal("0.90"),prior_corr=None,corr_change=None,availability=RelationshipAvailability.AVAILABLE)
    assert rotation is RelationshipState.ROTATION_CANDIDATE
    assert _oracle_state({"left_return":"0.0200000000","right_return":"-0.0100000000","relative_return":"0.0300000000"},Decimal("0.90"),None,None,"available",Decimal("1.50"),Decimal("1.50"),Decimal("0.03"))[0]=="rotation_candidate"
    strengthening=five.model_copy(update={"left_return":"0.0200000000","right_return":"0.0100000000","relative_return":"0.0100000000"})
    state,_=_relationship_state(windows=(strengthening,*windows[1:]),ratio_z=None,prior_ratio_z=None,prior_spread=None,current_corr=Decimal("0.35"),prior_corr=None,corr_change=None,availability=RelationshipAvailability.AVAILABLE)
    assert state is RelationshipState.SYNCHRONOUS_STRENGTHENING


def test_missing_ticker_session_zero_variance_duplicate_and_illegal_close(panel):
    missing=replace(panel,bars=tuple(item for item in panel.bars if not(item.ticker=="QQQ" and item.session_date==panel.as_of_session)))
    current=current_relationship_records(calculate_etf_relationship_history(panel=missing),as_of_session=panel.as_of_session)
    growth=next(item for item in current if item.pair_id=="growth_broad")
    assert growth.availability is RelationshipAvailability.UNAVAILABLE
    spy_bars=tuple(item for item in panel.bars if item.ticker=="SPY")
    constant=tuple(replace(item,close=Decimal("100"),open=Decimal("100"),high=Decimal("100"),low=Decimal("100")) if item.ticker=="SPY" else item for item in panel.bars)
    growth=next(item for item in current_relationship_records(calculate_etf_relationship_history(panel=replace(panel,bars=constant)),as_of_session=panel.as_of_session) if item.pair_id=="growth_broad")
    assert growth.windows[2].rolling_correlation is None and growth.availability is RelationshipAvailability.PARTIAL
    with pytest.raises(EtfRelationshipError,match="duplicate"):
        calculate_etf_relationship_history(panel=replace(panel,bars=panel.bars+(panel.bars[0],)))
    bad=replace(panel.bars[0],close=Decimal("0"))
    with pytest.raises(EtfRelationshipError,match="illegal"):
        calculate_etf_relationship_history(panel=replace(panel,bars=(bad,*panel.bars[1:])))


def test_non_xnys_date_and_session_gap_fail_closed(panel):
    bad_sessions=(*panel.sessions[:-1],date(2026,8,22))
    with pytest.raises(EtfRelationshipError,match="non-XNYS"):
        calculate_etf_relationship_history(panel=replace(panel,sessions=bad_sessions,as_of_session=bad_sessions[-1]))
    gap=panel.sessions[:10]+panel.sessions[11:]
    with pytest.raises(EtfRelationshipError,match="gap"):
        calculate_etf_relationship_history(panel=replace(panel,sessions=gap,as_of_session=gap[-1]))


@pytest.mark.parametrize("precision",(9,28,50))
@pytest.mark.parametrize("rounding",(ROUND_DOWN,ROUND_HALF_EVEN,ROUND_UP))
def test_decimal_context_matrix_is_invariant(panel,precision,rounding):
    expected=calculate_etf_relationship_history(panel=panel)
    with localcontext() as context:
        context.prec=precision; context.rounding=rounding; context.traps[Inexact]=True; context.traps[Rounded]=True
        actual=calculate_etf_relationship_history(panel=panel)
        oracle=compare_with_independent_relationship_oracle(panel=panel,records=actual,append_full_replay_match=True,input_permutation_match=True,future_prefix_stable=True)
    assert tuple(item.logical_fingerprint for item in actual)==tuple(item.logical_fingerprint for item in expected)
    assert oracle.mismatch_count==0


def test_append_permutation_and_future_prefix_equivalence(panel):
    full=calculate_etf_relationship_history(panel=panel)
    split=13; existing=tuple(item for item in full if item.as_of_session in panel.sessions[5:split])
    suffix=append_etf_relationship_history(panel=panel,existing_history=existing,append_sessions=panel.sessions[split:])
    assert tuple(item.logical_fingerprint for item in (*existing,*suffix))==tuple(item.logical_fingerprint for item in full)
    shuffled=calculate_etf_relationship_history(panel=replace(panel,bars=tuple(reversed(panel.bars))))
    assert tuple(item.logical_fingerprint for item in shuffled)==tuple(item.logical_fingerprint for item in full)
    sessions=panel.sessions[:-1]
    prefix=calculate_etf_relationship_history(panel=replace(panel,sessions=sessions,as_of_session=sessions[-1],source_sessions=panel.source_sessions[:-1]))
    assert tuple(item.logical_fingerprint for item in prefix)==tuple(item.logical_fingerprint for item in full[:-16])


def test_oracle_reports_perturbed_metric(panel):
    history=calculate_etf_relationship_history(panel=panel)
    first=history[0]; window=first.windows[0].model_copy(update={"relative_return":"9.0000000000"})
    bad=first.model_copy(update={"windows":(window,*first.windows[1:])})
    oracle=compare_with_independent_relationship_oracle(panel=panel,records=(bad,*history[1:]),append_full_replay_match=True,input_permutation_match=True,future_prefix_stable=True)
    assert oracle.mismatch_count>0 and any("relative_return" in item for item in oracle.mismatches)


def test_explanations_and_canonical_audit_round_trip(panel):
    history=calculate_etf_relationship_history(panel=panel); current=current_relationship_records(history,as_of_session=panel.as_of_session)
    explanations=build_relationship_explanations(current)
    assert len(explanations)==16 and all("statistical_relationship_not_causal" in item.disclaimers for item in explanations)
    oracle=compare_with_independent_relationship_oracle(panel=panel,records=history,append_full_replay_match=True,input_permutation_match=True,future_prefix_stable=True)
    comparisons=tuple(MarketRegimeRelationshipComparisonV1(as_of_session=panel.as_of_session,universe_id="provider_classified_common_shares_v1",regime_candidate_state="balanced",regime_confirmed_state="balanced",regime_composite="60.0000",regime_state_record_fingerprint="9"*64,pair_id=item.pair_id,relationship_state=item.relationship_state,alignment=RegimeRelationshipAlignment.NEUTRAL,reason_codes=("test_contemporaneous_only",)) for item in current)
    target=Path(tempfile.mkdtemp(prefix="mrom-etf-test-",dir="/tmp"))
    try:
        manifest=write_etf_relationship_audit(output_dir=target,panel=panel,phase1a_manifest={"logical_content_fingerprint":"7"*64,"composite_fingerprints":[]},phase1b_manifest={"logical_content_fingerprint":"8"*64,"history_logical_fingerprints":{}},history=history,current=current,explanations=explanations,regime_comparisons=comparisons,oracle_report=oracle,first_available_sessions={"window_5":panel.sessions[5].isoformat(),"window_10":panel.sessions[10].isoformat(),"window_20":panel.sessions[20].isoformat()},generated_at=datetime.now(UTC),timings={"test":"0.1"},peak_memory_kib=1)
        reread=read_etf_relationship_audit(target)
        assert reread["logical_content_fingerprint"]==manifest["logical_content_fingerprint"]
        planning=read_etf_relationship_planning_evidence(target)
        assert planning.manifest==manifest
        assert planning.source_manifest["phase1a_audit_logical_fingerprint"]=="7"*64
        assert planning.source_manifest["phase1b_audit_logical_fingerprint"]=="8"*64
    finally:
        for item in target.iterdir(): item.chmod(0o600)
        for item in target.iterdir(): item.unlink()
        target.rmdir()
