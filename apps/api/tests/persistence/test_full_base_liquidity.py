from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_UP, Rounded, localcontext
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest
import pyarrow as pa

from tip_api.contracts.market_data.v1 import EodSessionIntegrityV1, InstrumentType, QualityStatus, TrailingLiquiditySourceSessionV1
from tip_api.contracts.market_data.v1.full_base_liquidity import (
    FullBaseDatasetReferenceV1, FullBaseDecisionV1, FullBaseDisposition, FullBaseFunnelStageV1,
    FullBaseMembershipV1, FullBaseMetricV1, FullBasePolicySummaryV1, FullBaseSetDiffV1,
)
from tip_api.persistence.eod_read import EodHistorySessionRead
from tip_api.persistence.parquet.full_base_liquidity import (
    EXACT_DECIMAL_TYPE, MEDIAN_MAX_INTEGER_DIGITS, MEDIAN_MAX_PRECISION, MEDIAN_MAX_SCALE,
    METRIC_SCHEMA, ParquetFullBaseScopeReviewRepository, read_completed_full_base_scope_review,
    validate_full_base_physical_round_trip,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.eod_history import exact_even_median, plan_eod_history_window
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID, build_full_base_scope_review
from tip_api.services.full_base_liquidity_cli import _exact_arithmetic_reconciliation, _freeze_metric_records, main as cli_main
from tip_api.services.full_base_security_form_cli import main as superseding_cli_main
from tip_api.contracts.security_classification.v1 import SecurityForm
from tip_api.contracts.security_classification.v1.universe_review import (
    ReviewedSecurityFormCoveredFact, ReviewedSecurityFormEvidenceType, ReviewedSecurityFormEvidenceV1,
    ReviewedSecurityFormSourceV1, validate_reviewed_security_form_intervals,
)
from tip_api.persistence.parquet.superseding_full_base import (
    ParquetSupersedingFullBaseRepository, read_completed_superseding_full_base,
)
from tip_api.services.market_calendar import ExchangeCalendar

D = date(2026, 8, 19); E = date(2026, 8, 14); NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)
NS = UUID("10000000-0000-4000-8000-000000000001")
H1 = "a" * 64; H2 = "b" * 64


def iid(name): return uuid5(NS, name)


def reviewed_form(instrument_id, *, effective_from=date(2026, 7, 10), effective_to=None, source_date=date(2026, 7, 10)):
    return ReviewedSecurityFormEvidenceV1(
        evidence_id=iid(f"review-{instrument_id}-{effective_from}"), instrument_id=instrument_id,
        effective_from=effective_from, effective_to=effective_to,
        reviewed_security_form=SecurityForm.ADR_ADS,
        evidence_type=ReviewedSecurityFormEvidenceType.AUTHORITATIVE_REGULATORY_FILING,
        sources=(ReviewedSecurityFormSourceV1(
            filing_type="Form 6-K", document_date=source_date, filing_date=source_date,
            covered_fact=ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS,
            fact_effective_from=effective_from,
            official_source_url="https://www.sec.gov/Archives/edgar/data/1/reviewed.htm",
            supported_conclusion="The listed security is an ADS.",
        ),), reviewer_identifier="fixture-reviewer", reason_code="authoritative_ads",
        reason="Reviewed filing establishes the listed ADS form.", recorded_at=NOW, reviewed_at=NOW,
    )


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


def fixture_bundle(*, empty_legacy=False, reverse=False, rescued_previous_volume="1000000", return_inputs=False):
    calendar = ExchangeCalendar(); days = calendar.sessions_before(D, 20)
    rescued_cs, rescued_adrc, false_friend = iid("rescued-cs"), iid("rescued-adrc"), iid("false-friend")
    ids = (rescued_cs, rescued_adrc, false_friend)
    rows = {}
    for index, day in enumerate(days):
        values = [
            bar(rescued_cs, day, ticker="RCS", volume=rescued_previous_volume if day == days[-1] else "3000000"),
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
    if return_inputs:
        return bundle, SimpleNamespace(
            repo=repo, descriptor=descriptor, evidence=evidence,
            instruments=instruments, current_bars=current,
        )
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


@pytest.mark.parametrize(("volume", "expected"), (
    ("2000000", False),
    ("1999999.99999999999", True),
    ("2000000.00000000001", False),
))
def test_previous_session_threshold_boolean_uses_full_decimal_precision(volume, expected):
    bundle, cs, *_ = fixture_bundle(rescued_previous_volume=volume)
    metric = next(item for item in bundle.metrics if item.instrument_id == cs)
    assert metric.previous_dollar_volume_below_threshold is expected


def test_v1_metric_reproduction_compares_decimal_values_not_scale():
    bundle, *_ = fixture_bundle()
    metric = bundle.metrics[0]
    left = metric.model_copy(update={"median_dollar_volume_proxy_20s": Decimal("25695393.29024274000000000000")})
    right = metric.model_copy(update={"median_dollar_volume_proxy_20s": Decimal("25695393.2902427400")})
    assert _freeze_metric_records((left,)) == _freeze_metric_records((right,))


def test_legacy_membership_and_input_order_do_not_change_corrected_result():
    first, *_ = fixture_bundle(empty_legacy=False, reverse=False)
    second, *_ = fixture_bundle(empty_legacy=True, reverse=True)
    assert first.final_memberships == second.final_memberships
    assert [item.membership_fingerprint for item in first.summaries] == [item.membership_fingerprint for item in second.summaries]


@pytest.mark.parametrize(("precision", "rounding"), ((9, ROUND_DOWN), (28, ROUND_UP), (50, ROUND_DOWN)))
def test_full_base_decisions_analytics_and_fingerprints_ignore_global_decimal_context(precision, rounding):
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        bundle, *_ = fixture_bundle()
    with localcontext() as context:
        context.prec = 28
        reference, *_ = fixture_bundle()
    assert bundle.final_memberships == reference.final_memberships
    assert bundle.analytics == reference.analytics
    assert [item.membership_fingerprint for item in bundle.summaries] == [item.membership_fingerprint for item in reference.summaries]


def test_nonmembership_analytics_does_not_inherit_traps_or_leak_flags():
    with localcontext() as context:
        context.prec = 9
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        context.clear_flags()
        bundle, *_ = fixture_bundle()
        assert bundle.analytics
        assert context.flags[Inexact] is False
        assert context.flags[Rounded] is False


def test_fraction_oracle_rebuilds_decisions_from_raw_inputs_without_bundle_metrics():
    bundle, inputs = fixture_bundle(return_inputs=True)
    result = _exact_arithmetic_reconciliation(
        repo=inputs.repo,
        descriptor=inputs.descriptor,
        evidence=inputs.evidence,
        instruments=inputs.instruments,
        current_bars=inputs.current_bars,
        actual_decisions=bundle.decisions,
        actual_memberships=bundle.final_memberships,
        v1_metrics=(),
        overrides=(),
    )
    assert result["daily_product_mismatch_count"] == 0
    assert result["median_mismatch_count"] == 0
    assert result["decision_mismatch_count"] == 0
    assert result["membership_mismatch_count"] == 0
    assert result["first_difference"] is None
    assert result["expected_membership_fingerprints"] == {
        item.policy_id: item.membership_fingerprint for item in bundle.summaries
    }


def test_primary_subset_and_security_type_boundary():
    bundle, *_ = fixture_bundle()
    assert bundle.final_memberships[FULL_BASE_A_ID] <= bundle.final_memberships[FULL_BASE_B_ID]
    by_id = {item.instrument_id:item.provider_type_code for item in bundle.metrics}
    assert {by_id[item] for item in bundle.final_memberships[FULL_BASE_B_ID]-bundle.final_memberships[FULL_BASE_A_ID]} == {"ADRC"}


def test_reviewed_security_form_reclassifies_stable_id_without_bypassing_gates():
    baseline, inputs = fixture_bundle(return_inputs=True)
    target = next(item for item in baseline.final_memberships[FULL_BASE_A_ID])
    old = {"provider_classified_common_shares_v1": frozenset(),
           "provider_classified_common_shares_plus_adrs_v1": frozenset()}
    corrected = build_full_base_scope_review(
        descriptor=inputs.descriptor, repository=inputs.repo, evidence=inputs.evidence,
        instruments=inputs.instruments, current_bars=inputs.current_bars,
        membership_evidence_as_of_date=E, reviewed_overrides=(), old_memberships=old,
        calculated_at=NOW, reviewed_security_forms=(reviewed_form(target),),
    )
    decisions = {(item.policy_id, item.instrument_id): item for item in corrected.decisions}
    assert decisions[(FULL_BASE_A_ID, target)].disposition is FullBaseDisposition.TARGET_SECURITY_FORM
    assert decisions[(FULL_BASE_B_ID, target)].included is True
    assert target not in corrected.final_memberships[FULL_BASE_A_ID]
    assert target in corrected.final_memberships[FULL_BASE_B_ID]
    assert corrected.original_provider_types[target] == "CS"
    assert corrected.effective_provider_types[target] == "ADRC"
    assert len(corrected.decisions) == 2 * len(corrected.metrics)


@pytest.mark.parametrize(("precision", "rounding"), ((9, ROUND_DOWN), (28, ROUND_UP), (50, ROUND_DOWN)))
def test_reviewed_security_form_decisions_ignore_decimal_context(precision, rounding):
    baseline, inputs = fixture_bundle(return_inputs=True)
    target = next(item for item in baseline.final_memberships[FULL_BASE_A_ID])
    kwargs = dict(descriptor=inputs.descriptor, repository=inputs.repo, evidence=inputs.evidence,
        instruments=inputs.instruments, current_bars=inputs.current_bars,
        membership_evidence_as_of_date=E, reviewed_overrides=(),
        old_memberships={"provider_classified_common_shares_v1": frozenset(),
                         "provider_classified_common_shares_plus_adrs_v1": frozenset()},
        calculated_at=NOW, reviewed_security_forms=(reviewed_form(target),))
    with localcontext() as context:
        context.prec = precision; context.rounding = rounding
        context.traps[Inexact] = True; context.traps[Rounded] = True; context.clear_flags()
        actual = build_full_base_scope_review(**kwargs)
        assert context.flags[Inexact] is False and context.flags[Rounded] is False
    reference = build_full_base_scope_review(**kwargs)
    assert actual.final_memberships == reference.final_memberships
    assert [item.membership_fingerprint for item in actual.summaries] == [item.membership_fingerprint for item in reference.summaries]


def test_reviewed_security_form_contract_rejects_future_unsafe_duplicate_and_overlap():
    target = iid("reviewed")
    unsupported_source = ReviewedSecurityFormSourceV1(
        filing_type="Form 6-K", document_date=date(2026, 7, 10), filing_date=date(2026, 7, 10),
        covered_fact=ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS,
        fact_effective_from=date(2026, 7, 10),
        official_source_url="https://www.sec.gov/Archives/edgar/data/1/reviewed.htm",
        supported_conclusion="The listed security is an ADS.",
    )
    with pytest.raises(ValueError, match="unsupported or future"):
        ReviewedSecurityFormEvidenceV1(
            evidence_id=iid("future-review"), instrument_id=target,
            effective_from=date(2026, 7, 9), reviewed_security_form=SecurityForm.ADR_ADS,
            evidence_type=ReviewedSecurityFormEvidenceType.AUTHORITATIVE_REGULATORY_FILING,
            sources=(unsupported_source,), reviewer_identifier="fixture-reviewer",
            reason_code="authoritative_ads", reason="Reviewed filing establishes ADS form.",
            recorded_at=NOW, reviewed_at=NOW,
        )
    with pytest.raises(ValueError, match="safe public SEC"):
        ReviewedSecurityFormSourceV1(filing_type="6-K", document_date=date(2026, 7, 10), filing_date=date(2026, 7, 10),
            covered_fact=ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS,
            fact_effective_from=date(2026, 7, 10),
            official_source_url="https://sec.gov.evil.test/Archives/edgar/data/1/x.htm",
            supported_conclusion="ADS")
    first = reviewed_form(target, effective_to=date(2026, 8, 1))
    overlap = reviewed_form(target, effective_from=date(2026, 7, 20))
    with pytest.raises(ValueError, match="overlap"):
        validate_reviewed_security_form_intervals((first, overlap))
    with pytest.raises(ValueError, match="duplicate"):
        validate_reviewed_security_form_intervals((first, first))


@pytest.mark.parametrize(
    ("session", "expected"),
    (
        (date(2023, 2, 8), False),
        (date(2023, 2, 9), True),
        (date(2026, 7, 9), True),
        (date(2026, 7, 10), True),
        (date(2026, 8, 19), True),
        (date(2035, 1, 1), True),
    ),
)
def test_hsai_reviewed_form_historical_boundaries(session, expected):
    from tip_api.services.full_base_security_form_cli import hsai_reviewed_security_form

    evidence = hsai_reviewed_security_form()
    assert evidence.effective_from == date(2023, 2, 9)
    assert evidence.effective_to is None
    assert evidence.is_effective_on(session) is expected
    assert evidence.recorded_at == datetime(2026, 8, 21, tzinfo=UTC)
    assert evidence.reviewed_at == datetime(2026, 8, 21, tzinfo=UTC)
    assert [source.official_source_url for source in evidence.sources] == [
        "https://www.sec.gov/Archives/edgar/data/1861737/000110465923017567/tm2120356-28_424b4.htm",
        "https://www.sec.gov/Archives/edgar/data/1861737/000110465924051452/hsai-20231231x20f.htm",
        "https://www.sec.gov/Archives/edgar/data/1861737/000110465926048025/hsai-20251231x20f.htm",
        "https://www.sec.gov/Archives/edgar/data/1861737/000110465926082432/tm2620203d1_6k.htm",
    ]
    assert [source.filing_date for source in evidence.sources] == [
        date(2023, 2, 8), None, None, date(2026, 7, 10),
    ]
    ratio_sources = [
        source for source in evidence.sources
        if source.covered_fact is ReviewedSecurityFormCoveredFact.ADS_RATIO_CHANGED
    ]
    assert len(ratio_sources) == 1
    assert ratio_sources[0].fact_effective_from == date(2026, 7, 10)
    assert all(
        source.covered_fact is ReviewedSecurityFormCoveredFact.LISTED_SECURITY_IS_ADS
        for source in evidence.sources[:3]
    )


def test_reviewed_security_form_ratio_only_and_orphan_fail_closed():
    target = iid("ratio-only")
    ratio_source = ReviewedSecurityFormSourceV1(
        filing_type="Form 6-K", document_date=date(2026, 7, 10), filing_date=date(2026, 7, 10),
        covered_fact=ReviewedSecurityFormCoveredFact.ADS_RATIO_CHANGED,
        fact_effective_from=date(2026, 7, 10),
        official_source_url="https://www.sec.gov/Archives/edgar/data/1/ratio.htm",
        supported_conclusion="The ADS ratio changed while the listed form remained ADS.",
    )
    with pytest.raises(ValueError, match="security-form source"):
        ReviewedSecurityFormEvidenceV1(
            evidence_id=iid("ratio-only-evidence"), instrument_id=target,
            effective_from=date(2026, 7, 10), reviewed_security_form=SecurityForm.ADR_ADS,
            evidence_type=ReviewedSecurityFormEvidenceType.AUTHORITATIVE_REGULATORY_FILING,
            sources=(ratio_source,), reviewer_identifier="fixture-reviewer",
            reason_code="ratio_only", reason="Ratio evidence alone is not a form origin.",
            recorded_at=NOW, reviewed_at=NOW,
        )
    _, inputs = fixture_bundle(return_inputs=True)
    with pytest.raises(ValueError, match="orphan reviewed security-form"):
        build_full_base_scope_review(
            descriptor=inputs.descriptor, repository=inputs.repo, evidence=inputs.evidence,
            instruments=inputs.instruments, current_bars=inputs.current_bars,
            membership_evidence_as_of_date=E, reviewed_overrides=(),
            old_memberships={
                "provider_classified_common_shares_v1": frozenset(),
                "provider_classified_common_shares_plus_adrs_v1": frozenset(),
            },
            calculated_at=NOW, reviewed_security_forms=(reviewed_form(iid("orphan")),),
        )


def test_superseding_repository_round_trip_and_existing_target(tmp_path):
    baseline, inputs = fixture_bundle(return_inputs=True)
    target_id = next(item for item in baseline.final_memberships[FULL_BASE_A_ID])
    corrected = build_full_base_scope_review(
        descriptor=inputs.descriptor, repository=inputs.repo, evidence=inputs.evidence,
        instruments=inputs.instruments, current_bars=inputs.current_bars,
        membership_evidence_as_of_date=E, reviewed_overrides=(),
        old_memberships={"provider_classified_common_shares_v1": frozenset(),
                         "provider_classified_common_shares_plus_adrs_v1": frozenset()},
        calculated_at=NOW, reviewed_security_forms=(reviewed_form(target_id),),
    )
    result = ParquetSupersedingFullBaseRepository(tmp_path).publish(
        analysis_session=D, membership_evidence_as_of_date=E,
        reviewed_security_forms=(reviewed_form(target_id),), metrics=corrected.metrics,
        decisions=corrected.decisions, memberships=corrected.memberships, diffs=corrected.diffs,
        funnels=corrected.funnels, policies=corrected.summaries,
        source_full_base_logical_path="market-data/snapshots/source",
        source_full_base_logical_fingerprint=H1, source_descriptor_fingerprint=corrected.metrics[0].source_window_fingerprint,
        created_at=NOW,
    )
    assert len(result.reviewed_security_forms) == 1
    reread = read_completed_superseding_full_base(tmp_path, analysis_session=D)
    assert reread.memberships == result.memberships
    with pytest.raises(Exception, match="already exists"):
        ParquetSupersedingFullBaseRepository(tmp_path).publish(
            analysis_session=D, membership_evidence_as_of_date=E,
            reviewed_security_forms=(reviewed_form(target_id),), metrics=corrected.metrics,
            decisions=corrected.decisions, memberships=corrected.memberships, diffs=corrected.diffs,
            funnels=corrected.funnels, policies=corrected.summaries,
            source_full_base_logical_path="market-data/snapshots/source",
            source_full_base_logical_fingerprint=H1, source_descriptor_fingerprint=corrected.metrics[0].source_window_fingerprint,
            created_at=NOW,
        )


def test_superseding_failed_formal_reread_removes_new_target(tmp_path, monkeypatch):
    import tip_api.persistence.parquet.superseding_full_base as persistence
    baseline, inputs = fixture_bundle(return_inputs=True)
    target_id = next(item for item in baseline.final_memberships[FULL_BASE_A_ID])
    corrected = build_full_base_scope_review(
        descriptor=inputs.descriptor, repository=inputs.repo, evidence=inputs.evidence,
        instruments=inputs.instruments, current_bars=inputs.current_bars,
        membership_evidence_as_of_date=E, reviewed_overrides=(),
        old_memberships={"provider_classified_common_shares_v1": frozenset(),
                         "provider_classified_common_shares_plus_adrs_v1": frozenset()},
        calculated_at=NOW, reviewed_security_forms=(reviewed_form(target_id),),
    )
    monkeypatch.setattr(persistence, "read_completed_superseding_full_base", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic reread")))
    with pytest.raises(RuntimeError, match="synthetic reread"):
        ParquetSupersedingFullBaseRepository(tmp_path).publish(
            analysis_session=D, membership_evidence_as_of_date=E,
            reviewed_security_forms=(reviewed_form(target_id),), metrics=corrected.metrics,
            decisions=corrected.decisions, memberships=corrected.memberships, diffs=corrected.diffs,
            funnels=corrected.funnels, policies=corrected.summaries,
            source_full_base_logical_path="market-data/snapshots/source",
            source_full_base_logical_fingerprint=H1, source_descriptor_fingerprint=corrected.metrics[0].source_window_fingerprint,
            created_at=NOW,
        )
    assert not list(tmp_path.rglob("analysis_session=2026-08-19"))
    assert not list(tmp_path.rglob("*.staging-*"))


def test_superseding_cli_rejects_unknown_and_multiple_arguments():
    with pytest.raises(SystemExit) as unknown:
        superseding_cli_main(["--unknown"])
    assert unknown.value.code == 2
    with pytest.raises(SystemExit) as multiple:
        superseding_cli_main(["--apply", "extra"])
    assert multiple.value.code == 2


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
        median_dollar_volume_proxy_20s=Decimal("320686.75045605845000000000"),metric_status="passed",quality_flags=(),source_window_fingerprint=H1,calculated_at=NOW)
    decision = FullBaseDecisionV1(analysis_session=D,membership_evidence_as_of_date=E,policy_id=FULL_BASE_A_ID,instrument_id=metric.instrument_id,
        provider_type_code="CS",disposition="included",included=True,stage_id="final_membership",reason_codes=("passed",),reviewed_override_decision=None,calculated_at=NOW)
    membership = FullBaseMembershipV1(analysis_session=D,policy_id=FULL_BASE_A_ID,instrument_id=metric.instrument_id,provider_type_code="CS")
    diff = FullBaseSetDiffV1(analysis_session=D,policy_id=FULL_BASE_A_ID,instrument_id=metric.instrument_id,provider_type_code="CS",direction="corrected_added",
        reason_code="full_base_not_in_legacy_scope",rescued_from_previous_session_scope=False,median_dollar_volume_proxy_20s=Decimal("320686.75045605845000000000"))
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
    assert METRIC_SCHEMA.field("median_dollar_volume_proxy_20s").type == EXACT_DECIMAL_TYPE
    assert completed.metrics[0].median_dollar_volume_proxy_20s == Decimal("320686.75045605845000000000")
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


def test_exact_decimal_tuple_contract_and_theoretical_boundary(tmp_path):
    metric,decision,membership,diff,funnel,_ = sample_records()
    boundary = Decimal("9" * MEDIAN_MAX_INTEGER_DIGITS + "." + "9" * MEDIAN_MAX_SCALE)
    metric = metric.model_copy(update={"median_dollar_volume_proxy_20s": boundary})
    diff = diff.model_copy(update={"median_dollar_volume_proxy_20s": boundary})
    counts = validate_full_base_physical_round_trip(metrics=(metric,),decisions=(decision,),memberships=(membership,),
        diffs=(diff,),funnels=(funnel,),temp_root=tmp_path)
    assert counts == {"metric":1,"decision":1,"membership":1,"diff":1,"funnel":1}
    assert len(boundary.as_tuple().digits) == MEDIAN_MAX_PRECISION and -boundary.as_tuple().exponent == MEDIAN_MAX_SCALE


def test_decimal256_cannot_cover_theoretical_even_median_precision():
    assert pa.decimal256(76, 20).precision == 76
    with pytest.raises(Exception):
        pa.decimal256(77, 21)


def test_exact_decimal_tuple_rejects_beyond_theoretical_limit_with_context(tmp_path):
    metric,decision,membership,diff,funnel,_ = sample_records()
    metric = metric.model_copy(update={"median_dollar_volume_proxy_20s": Decimal("1e56")})
    with pytest.raises(Exception) as failure:
        validate_full_base_physical_round_trip(metrics=(metric,),decisions=(decision,),memberships=(membership,),
            diffs=(diff,),funnels=(funnel,),temp_root=tmp_path)
    message = str(failure.value)
    assert all(token in message for token in (
        "dataset=trailing-liquidity-full-base-metrics", "field=median_dollar_volume_proxy_20s",
        f"instrument_id={metric.instrument_id}", "ticker=ONE", "observed_precision=1", "observed_scale=0",
        "approved_precision=77", "approved_scale=21",
    ))


def test_even_median_preserves_half_unit_at_additional_scale():
    values = [Decimal(index) for index in range(9)] + [Decimal("10.00000000000000000000"), Decimal("10.00000000000000000001")] + [Decimal(20 + index) for index in range(9)]
    assert exact_even_median(values) == Decimal("10.000000000000000000005")


def test_cli_argument_contract_does_not_touch_data():
    with pytest.raises(SystemExit) as invalid: cli_main(["--unknown"])
    assert invalid.value.code==2
    with pytest.raises(SystemExit) as help_exit: cli_main(["--help"])
    assert help_exit.value.code==0
