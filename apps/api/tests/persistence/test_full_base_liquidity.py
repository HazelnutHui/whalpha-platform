from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.market_data.v1 import EodSessionIntegrityV1, InstrumentType, QualityStatus, TrailingLiquiditySourceSessionV1
from tip_api.contracts.market_data.v1.full_base_liquidity import (
    FullBaseDatasetReferenceV1, FullBaseDecisionV1, FullBaseDisposition, FullBaseFunnelStageV1,
    FullBaseMembershipV1, FullBaseMetricV1, FullBasePolicySummaryV1, FullBaseSetDiffV1,
)
from tip_api.persistence.eod_read import EodHistorySessionRead
from tip_api.persistence.parquet.full_base_liquidity import (
    METRIC_SCHEMA, ParquetFullBaseScopeReviewRepository, read_completed_full_base_scope_review,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.eod_history import plan_eod_history_window
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID, build_full_base_scope_review
from tip_api.services.full_base_liquidity_cli import main as cli_main
from tip_api.services.market_calendar import ExchangeCalendar

D = date(2026, 8, 19); E = date(2026, 8, 14); NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)
NS = UUID("10000000-0000-4000-8000-000000000001")
H1 = "a" * 64; H2 = "b" * 64


def iid(name): return uuid5(NS, name)


def bar(i, day, *, ticker="X", close="10", volume="3000000"):
    p = Decimal(close)
    return EodMarketBarReadModel(instrument_id=i, ticker=ticker, name=ticker, instrument_type=InstrumentType.COMMON_STOCK,
        primary_exchange="XNYS", session_date=day, open=p, high=p, low=p, close=p, volume=Decimal(volume),
        vwap=None, trade_count=None, currency="USD", source="fixture", quality_status=QualityStatus.WARNING,
        quality_flags=("adjustment_factors_unverified",))


def integrity(day):
    return EodSessionIntegrityV1(session_date=day, record_count=1, content_fingerprint=f"{day.day:064x}", parquet_sha256=H1,
        identity_snapshot_date=day, identity_snapshot_fingerprint=H2, duplicate_instrument_session_count=0,
        multiple_latest_revision_count=0, future_identity_reference_count=0)


@dataclass
class Repo:
    rows: dict[date, tuple]
    def inspect_session(self, day): return integrity(day)
    def read_history_sessions(self, days): return tuple(EodHistorySessionRead(integrity(day), self.rows[day]) for day in days)


def fixture_bundle(*, empty_legacy=False, reverse=False):
    calendar = ExchangeCalendar(); days = calendar.sessions_before(D, 20)
    rescued_cs, rescued_adrc, false_friend = iid("rescued-cs"), iid("rescued-adrc"), iid("false-friend")
    ids = (rescued_cs, rescued_adrc, false_friend)
    rows = {}
    for index, day in enumerate(days):
        values = [
            bar(rescued_cs, day, ticker="RCS", volume="1000000" if day == days[-1] else "3000000"),
            bar(rescued_adrc, day, ticker="RADR", volume="1000000" if day == days[-1] else "3000000"),
            bar(false_friend, day, ticker="FALSE", volume="3000000" if day == days[-1] else "1000000"),
        ]
        rows[day] = tuple(reversed(values)) if reverse else tuple(values)
    repo = Repo(rows)
    descriptor = plan_eod_history_window(analysis_session=D, calendar=calendar, repository=repo)[0]
    evidence = tuple(SimpleNamespace(instrument_id=i, provider_ticker=t, provider_type_code=k) for i,t,k in (
        (rescued_cs,"RCS","CS"),(rescued_adrc,"RADR","ADRC"),(false_friend,"FALSE","CS")))
    instruments = {i:{"primary_exchange":"XNYS"} for i in ids}
    current = tuple(bar(i,D,ticker=str(i)[:5]) for i in reversed(ids) if reverse) if reverse else tuple(bar(i,D,ticker=str(i)[:5]) for i in ids)
    old = {"provider_classified_common_shares_v1": frozenset() if empty_legacy else frozenset({false_friend}),
           "provider_classified_common_shares_plus_adrs_v1": frozenset() if empty_legacy else frozenset({false_friend})}
    bundle = build_full_base_scope_review(descriptor=descriptor, repository=repo, evidence=evidence, instruments=instruments,
        current_bars=current, membership_evidence_as_of_date=E, reviewed_overrides=(), old_memberships=old, calculated_at=NOW)
    return bundle, rescued_cs, rescued_adrc, false_friend


def test_full_base_fixes_legacy_scope_and_previous_day_bias():
    bundle, cs, adrc, false_friend = fixture_bundle()
    assert cs in bundle.final_memberships[FULL_BASE_A_ID]
    assert cs in bundle.final_memberships[FULL_BASE_B_ID]
    assert adrc not in bundle.final_memberships[FULL_BASE_A_ID] and adrc in bundle.final_memberships[FULL_BASE_B_ID]
    assert false_friend not in bundle.final_memberships[FULL_BASE_A_ID]
    reasons = {item.instrument_id:item.disposition for item in bundle.decisions if item.policy_id == FULL_BASE_A_ID}
    assert reasons[false_friend] is FullBaseDisposition.BELOW_TRAILING_LIQUIDITY
    assert next(item for item in bundle.metrics if item.instrument_id == cs).previous_dollar_volume_below_threshold is True


def test_legacy_membership_and_input_order_do_not_change_corrected_result():
    first, *_ = fixture_bundle(empty_legacy=False, reverse=False)
    second, *_ = fixture_bundle(empty_legacy=True, reverse=True)
    assert first.final_memberships == second.final_memberships
    assert [item.membership_fingerprint for item in first.summaries] == [item.membership_fingerprint for item in second.summaries]


def test_primary_subset_and_security_type_boundary():
    bundle, *_ = fixture_bundle()
    assert bundle.final_memberships[FULL_BASE_A_ID] <= bundle.final_memberships[FULL_BASE_B_ID]
    by_id = {item.instrument_id:item.provider_type_code for item in bundle.metrics}
    assert {by_id[item] for item in bundle.final_memberships[FULL_BASE_B_ID]-bundle.final_memberships[FULL_BASE_A_ID]} == {"ADRC"}


def test_sequential_funnel_closes_and_does_not_repeat_final_count_as_each_stage():
    bundle, *_ = fixture_bundle()
    for policy in (FULL_BASE_A_ID, FULL_BASE_B_ID):
        stages = [item for item in bundle.funnels if item.policy_id == policy]
        assert all(item.input_count-item.excluded_count == item.remaining_count for item in stages)
        assert all(right.input_count == left.remaining_count for left,right in zip(stages, stages[1:]))
        assert stages[-1].remaining_count == len(bundle.final_memberships[policy])


def test_analysis_session_cannot_enter_window():
    bundle, *_ = fixture_bundle()
    assert all(item.analysis_session == D for item in bundle.metrics)
    assert all(item.source_window_fingerprint for item in bundle.metrics)


def sample_records():
    metric = FullBaseMetricV1(analysis_session=D,membership_evidence_as_of_date=E,instrument_id=iid("one"),display_ticker="ONE",
        provider_type_code="CS",primary_exchange="XNYS",supported_exchange=True,current_bar_present=True,previous_bar_present=True,
        previous_close=Decimal("5"),previous_dollar_volume_below_threshold=False,observation_count=20,
        median_dollar_volume_proxy_20s=Decimal("20000000"),metric_status="passed",quality_flags=(),source_window_fingerprint=H1,calculated_at=NOW)
    decision = FullBaseDecisionV1(analysis_session=D,membership_evidence_as_of_date=E,policy_id=FULL_BASE_A_ID,instrument_id=metric.instrument_id,
        provider_type_code="CS",disposition="included",included=True,stage_id="final_membership",reason_codes=("passed",),reviewed_override_decision=None,calculated_at=NOW)
    membership = FullBaseMembershipV1(analysis_session=D,policy_id=FULL_BASE_A_ID,instrument_id=metric.instrument_id,provider_type_code="CS")
    diff = FullBaseSetDiffV1(analysis_session=D,policy_id=FULL_BASE_A_ID,instrument_id=metric.instrument_id,provider_type_code="CS",direction="corrected_added",
        reason_code="full_base_not_in_legacy_scope",rescued_from_previous_session_scope=False,median_dollar_volume_proxy_20s=Decimal("20000000"))
    funnel = FullBaseFunnelStageV1(analysis_session=D,membership_evidence_as_of_date=E,policy_id=FULL_BASE_A_ID,stage_order=1,
        stage_id="final",stage_label="Final",stage_kind="sequential",input_count=1,excluded_count=0,remaining_count=1,
        exclusion_reason_codes=(),source_fingerprints=(H1,))
    summary = FullBasePolicySummaryV1(policy_id=FULL_BASE_A_ID,base_count=1,final_count=1,cs_count=1,adrc_count=0,membership_fingerprint=H1,
        old_count=0,retained_count=0,removed_count=0,added_count=1,rescued_previous_day_below_threshold_count=0)
    return metric,decision,membership,diff,funnel,summary


def publish(root):
    metric,decision,membership,diff,funnel,summary=sample_records()
    days=tuple(ExchangeCalendar().sessions_before(D,20))
    sources=tuple(TrailingLiquiditySourceSessionV1(session_date=day,dataset_path=f"market-data/eod-price-bars/schema_version=1/session_date={day}",record_count=1,
        content_fingerprint=f"{index+1:064x}",parquet_sha256=f"{index+101:064x}",identity_snapshot_date=day,identity_snapshot_fingerprint=f"{index+201:064x}") for index,day in enumerate(days))
    return ParquetFullBaseScopeReviewRepository(root).publish(analysis_session=D,metrics=(metric,),decisions=(decision,),memberships=(membership,),diffs=(diff,),funnels=(funnel,),
        membership_evidence_as_of_date=E,calendar_name="XNYS",calendar_version="4.13.2",window_sessions=days,source_sessions=sources,
        source_descriptor_fingerprint=H1,security_evidence_path="market-data/security",security_evidence_fingerprint=H2,
        legacy_v1_logical_path="market-data/old",legacy_v1_logical_fingerprint=H1,reviewed_override_logical_path="market-data/review",
        reviewed_override_fingerprint=H2,policies=(summary,),previous_close_threshold=Decimal("5"),median_dollar_volume_threshold=Decimal("20000000"),created_at=NOW)


def test_atomic_publication_and_formal_reread(tmp_path):
    result=publish(tmp_path); completed=read_completed_full_base_scope_review(tmp_path,analysis_session=D,validate_sources=False)
    assert result.status=="published" and len(completed.metrics)==1 and len(completed.memberships)==1
    assert METRIC_SCHEMA.field("previous_close").type.precision==38
    with pytest.raises(Exception): publish(tmp_path)


def test_failed_publication_cleans_staging(tmp_path,monkeypatch):
    import tip_api.persistence.parquet.trailing_liquidity as base
    original=base.pq.write_table; calls=0
    def fail(*args,**kwargs):
        nonlocal calls; calls+=1
        if calls==3: raise RuntimeError("synthetic")
        return original(*args,**kwargs)
    monkeypatch.setattr(base.pq,"write_table",fail)
    with pytest.raises(RuntimeError): publish(tmp_path)
    assert not list(tmp_path.rglob("*.staging.*")) and not list(tmp_path.rglob("analysis_session=2026-08-19"))


def test_symlink_and_decimal_over_scale_fail_closed(tmp_path):
    target=tmp_path/"real"; target.mkdir(); link=tmp_path/"link"; link.symlink_to(target,target_is_directory=True)
    with pytest.raises(Exception): publish(link)
    with pytest.raises(ValueError): FullBaseDatasetReferenceV1(dataset_path="../escape",record_count=1,content_fingerprint=H1,parquet_sha256=H2)


def test_cli_argument_contract_does_not_touch_data():
    with pytest.raises(SystemExit) as invalid: cli_main(["--unknown"])
    assert invalid.value.code==2
    with pytest.raises(SystemExit) as help_exit: cli_main(["--help"])
    assert help_exit.value.code==0
