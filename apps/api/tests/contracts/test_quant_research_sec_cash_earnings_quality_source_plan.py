from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_source_plan import (
    SecCashEarningsQualitySourceEngineeringPlanV1,
    quant_research_sec_cash_quality_source_plan_v1,
    sec_cash_quality_source_plan_fingerprint,
)
from tip_api.contracts.analytics.v1.quant_research_successor_source_qualification import (
    quant_research_successor_source_qualification_v1,
)


def test_sec_cash_quality_plan_preserves_closed_source_blocked_authority() -> None:
    plan = quant_research_sec_cash_quality_source_plan_v1()
    closed = quant_research_successor_source_qualification_v1()

    assert plan.lifecycle_state == "plan_only_closed_successor_intake_unchanged"
    assert plan.source_closed_qualification_status == "closed_source_blocked"
    assert plan.source_closed_qualification_fingerprint == closed.logical_fingerprint
    assert plan.source_execution_authorized is False
    assert plan.external_request_authorized is False
    assert plan.feature_materialization_authorized is False
    assert plan.coverage_report_authorized is False
    assert plan.development_outcome_access_authorized is False
    assert plan.validation_access_authorized is False
    assert plan.holdout_access_authorized is False
    assert plan.formal_trial_registration_authorized is False
    assert plan.logical_fingerprint == sec_cash_quality_source_plan_fingerprint(plan)


def test_sec_cash_quality_plan_freezes_ttm_and_amendment_semantics() -> None:
    plan = quant_research_sec_cash_quality_source_plan_v1()
    by_id = {item.line_item_id: item for item in plan.line_items}

    assert tuple(by_id) == ("operating_cash_flow", "net_income", "total_assets")
    assert (
        by_id["operating_cash_flow"].concept_name
        == "NetCashProvidedByUsedInOperatingActivities"
    )
    assert by_id["net_income"].concept_name == "NetIncomeLoss"
    assert by_id["total_assets"].concept_name == "Assets"
    assert all(item.concept_fallback_authorized is False for item in plan.line_items)
    assert plan.duration_component_rules == (
        "q1_discrete_equals_q1_reported_duration",
        "q2_discrete_equals_q2_ytd_minus_q1_ytd_same_fiscal_year",
        "q3_discrete_equals_q3_ytd_minus_q2_ytd_same_fiscal_year",
        "q4_discrete_equals_fy_duration_minus_q3_ytd_same_fiscal_year",
    )
    assert "never_rewrite_prior_cutoffs" in plan.prior_snapshot_rule
    assert "same_clean_accession" in plan.coherent_accession_rule


def test_sec_cash_quality_plan_freezes_identity_coverage_and_replay_stops() -> None:
    plan = quant_research_sec_cash_quality_source_plan_v1()

    assert plan.ticker_identity_authorized is False
    assert plan.multi_common_security_projection_authorized is False
    assert plan.current_classification_backfill_authorized is False
    assert plan.financial_or_unknown_applicability_behavior == "quarantine"
    assert plan.expected_session_count == 106
    assert plan.minimum_complete_session_count == 96
    assert plan.minimum_complete_sessions_per_half == 48
    assert plan.minimum_complete_instruments_per_session == 500
    assert plan.minimum_joint_formula_availability_rate == "0.7500000000"
    assert plan.raw_concept_presence_is_feature_coverage is False
    assert "coverage_floor_not_met" in plan.hard_stop_reason_codes
    assert "canonical_report_replay_mismatch" in plan.hard_stop_reason_codes
    assert plan.replay_mismatch_behavior == "stop_without_feature_or_trial"


def test_sec_cash_quality_plan_rejects_formula_authority_and_binding_drift() -> None:
    source = quant_research_sec_cash_quality_source_plan_v1()

    formula = source.model_dump(mode="python")
    formula["average_assets_rule"] = "assets_at_closing_boundary"
    formula["logical_fingerprint"] = sec_cash_quality_source_plan_fingerprint(formula)
    with pytest.raises(ValidationError, match="Input should be"):
        SecCashEarningsQualitySourceEngineeringPlanV1.model_validate(formula)

    authority = source.model_dump(mode="python")
    authority["coverage_report_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        SecCashEarningsQualitySourceEngineeringPlanV1.model_validate(authority)

    binding = source.model_dump(mode="python")
    binding["source_closed_qualification_fingerprint"] = "f" * 64
    binding["logical_fingerprint"] = sec_cash_quality_source_plan_fingerprint(binding)
    with pytest.raises(
        ValidationError, match="SEC cash-earnings-quality source plan differs"
    ):
        SecCashEarningsQualitySourceEngineeringPlanV1.model_validate(binding)

    line_item = source.model_dump(mode="python")
    changed = list(deepcopy(line_item["line_items"]))
    changed[0]["concept_name"] = "OperatingIncomeLoss"
    line_item["line_items"] = changed
    line_item["logical_fingerprint"] = sec_cash_quality_source_plan_fingerprint(
        line_item
    )
    with pytest.raises(ValidationError):
        SecCashEarningsQualitySourceEngineeringPlanV1.model_validate(line_item)
