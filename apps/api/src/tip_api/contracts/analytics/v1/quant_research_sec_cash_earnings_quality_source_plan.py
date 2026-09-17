"""Outcome-blind SEC cash-earnings-quality source-engineering plan."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.providers.sec.fundamental_query_registry import (
    build_first_sec_fundamental_query_registry,
)

from .quant_research_successor_hypotheses import (
    quant_research_successor_hypothesis_registry_v1,
)
from .quant_research_successor_source_qualification import (
    quant_research_successor_source_qualification_v1,
)


CONTRACT_VERSION = "quant-research-sec-cash-earnings-quality-source-plan/1.0"
PLAN_VERSION = "whalpha.quant-research.sec-cash-earnings-quality-source-plan/1.0.0"
CASH_QUALITY_HYPOTHESIS_ID = (
    "whalpha.hypothesis.successor-one.cash-earnings-quality"
)
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityLineItemPlanV1(FrozenModel):
    line_item_id: Literal["operating_cash_flow", "net_income", "total_assets"]
    namespace: Literal["us-gaap"] = "us-gaap"
    concept_name: Literal[
        "NetCashProvidedByUsedInOperatingActivities",
        "NetIncomeLoss",
        "Assets",
    ]
    unit: Literal["USD"] = "USD"
    period_shape: Literal["duration", "instant"]
    admitted_forms: tuple[str, ...]
    admitted_fiscal_periods: tuple[str, ...]
    concept_fallback_authorized: Literal[False] = False
    unsupported_namespace_behavior: Literal["quarantine"] = "quarantine"

    @model_validator(mode="after")
    def line_item_reconciles(self) -> "SecCashQualityLineItemPlanV1":
        expected = _LINE_ITEMS_BY_ID[self.line_item_id]
        if self.model_dump(mode="python") != expected:
            raise ValueError("SEC cash-quality line-item plan differs")
        return self


class SecCashEarningsQualitySourceEngineeringPlanV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_version: Literal[PLAN_VERSION] = PLAN_VERSION
    frozen_date: Literal[date(2026, 9, 17)] = date(2026, 9, 17)
    lifecycle_state: Literal[
        "plan_only_closed_successor_intake_unchanged"
    ] = "plan_only_closed_successor_intake_unchanged"

    source_successor_registry_fingerprint: str = Field(pattern=_SHA256)
    source_cash_quality_hypothesis_fingerprint: str = Field(pattern=_SHA256)
    source_closed_qualification_fingerprint: str = Field(pattern=_SHA256)
    source_closed_qualification_status: Literal["closed_source_blocked"] = (
        "closed_source_blocked"
    )
    source_sec_query_registry_fingerprint: str = Field(pattern=_SHA256)

    research_question: Literal[
        "can_exact_as_filed_sec_inputs_support_a_point_in_time_"
        "cash_earnings_quality_measure_without_outcomes"
    ] = (
        "can_exact_as_filed_sec_inputs_support_a_point_in_time_"
        "cash_earnings_quality_measure_without_outcomes"
    )
    exact_measurement_formula: Literal[
        "(operating_cash_flow_ttm-net_income_ttm)/average_total_assets"
    ] = "(operating_cash_flow_ttm-net_income_ttm)/average_total_assets"
    ttm_quarter_count: Literal[4] = 4
    line_items: tuple[SecCashQualityLineItemPlanV1, ...] = Field(
        min_length=3, max_length=3
    )

    duration_component_rules: tuple[str, ...] = Field(min_length=4, max_length=4)
    ttm_chain_rule: Literal[
        "sum_latest_four_consecutive_discrete_fiscal_quarters_known_by_cutoff"
    ] = "sum_latest_four_consecutive_discrete_fiscal_quarters_known_by_cutoff"
    average_assets_rule: Literal[
        "(assets_at_opening_boundary_plus_assets_at_closing_boundary)/2"
    ] = "(assets_at_opening_boundary_plus_assets_at_closing_boundary)/2"
    denominator_rule: Literal[
        "positive_finite_average_assets_required_otherwise_quarantine"
    ] = "positive_finite_average_assets_required_otherwise_quarantine"
    currency_rule: Literal[
        "all_components_usd_same_security_fiscal_chain_no_fx_imputation"
    ] = "all_components_usd_same_security_fiscal_chain_no_fx_imputation"

    availability_clock_rule: Literal[
        "sec_acceptance_time_then_first_xnys_open_strictly_after_acceptance"
    ] = "sec_acceptance_time_then_first_xnys_open_strictly_after_acceptance"
    signal_cutoff_rule: Literal[
        "only_accessions_available_not_after_completed_signal_session_close"
    ] = "only_accessions_available_not_after_completed_signal_session_close"
    amendment_rule: Literal[
        "later_clean_amendment_changes_only_cutoffs_at_or_after_its_availability"
    ] = "later_clean_amendment_changes_only_cutoffs_at_or_after_its_availability"
    prior_snapshot_rule: Literal[
        "never_rewrite_prior_cutoffs_with_later_original_or_amended_filing"
    ] = "never_rewrite_prior_cutoffs_with_later_original_or_amended_filing"
    coherent_accession_rule: Literal[
        "cfo_and_net_income_each_cumulative_endpoint_require_same_clean_accession"
    ] = "cfo_and_net_income_each_cumulative_endpoint_require_same_clean_accession"
    conflict_rule: Literal[
        "value_time_period_shape_or_amendment_basis_conflict_quarantines_chain"
    ] = "value_time_period_shape_or_amendment_basis_conflict_quarantines_chain"

    identity_rule: Literal[
        "stable_instrument_id_via_admitted_unique_cik_and_single_common_security_per_cik_session"
    ] = "stable_instrument_id_via_admitted_unique_cik_and_single_common_security_per_cik_session"
    ticker_identity_authorized: Literal[False] = False
    multi_common_security_projection_authorized: Literal[False] = False
    evidence_tiers_reported_separately: tuple[
        Literal[
            "as_operated_next_open",
            "reconstructed_latest_vintage_development_only",
        ],
        ...,
    ] = (
        "as_operated_next_open",
        "reconstructed_latest_vintage_development_only",
    )
    evidence_tier_promotion_authorized: Literal[False] = False
    applicability_rule: Literal[
        "effective_dated_point_in_time_nonfinancial_evidence_required"
    ] = "effective_dated_point_in_time_nonfinancial_evidence_required"
    financial_or_unknown_applicability_behavior: Literal["quarantine"] = "quarantine"
    current_classification_backfill_authorized: Literal[False] = False

    coverage_population_rule: Literal[
        "exact_106_closed_campaign_development_dates_and_point_in_time_"
        "primary_membership_without_labels"
    ] = (
        "exact_106_closed_campaign_development_dates_and_point_in_time_"
        "primary_membership_without_labels"
    )
    expected_session_count: Literal[106] = 106
    minimum_complete_session_count: Literal[96] = 96
    chronological_half_session_counts: tuple[Literal[53], Literal[53]] = (53, 53)
    minimum_complete_sessions_per_half: Literal[48] = 48
    minimum_complete_instruments_per_session: Literal[500] = 500
    minimum_joint_formula_availability_rate: Literal["0.7500000000"] = (
        "0.7500000000"
    )
    missing_value_rule: Literal["explicit_quarantine_never_fill"] = (
        "explicit_quarantine_never_fill"
    )
    raw_concept_presence_is_feature_coverage: Literal[False] = False
    coverage_hard_stops: tuple[str, ...] = Field(min_length=1)

    replay_rule: Literal[
        "one_owner_private_coverage_report_and_one_independent_byte_identical_replay"
    ] = "one_owner_private_coverage_report_and_one_independent_byte_identical_replay"
    replay_bindings: tuple[str, ...] = Field(min_length=1)
    replay_mismatch_behavior: Literal["stop_without_feature_or_trial"] = (
        "stop_without_feature_or_trial"
    )

    planned_stage_order: tuple[str, ...] = Field(min_length=6, max_length=6)
    forbidden_substitutes: tuple[str, ...] = Field(min_length=1)
    hard_stop_reason_codes: tuple[str, ...] = Field(min_length=1)

    source_execution_authorized: Literal[False] = False
    external_request_authorized: Literal[False] = False
    feature_materialization_authorized: Literal[False] = False
    coverage_report_authorized: Literal[False] = False
    development_outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    formal_trial_registration_authorized: Literal[False] = False
    model_input_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "SecCashEarningsQualitySourceEngineeringPlanV1":
        registry = quant_research_successor_hypothesis_registry_v1()
        cash_card = next(
            item for item in registry.cards if item.hypothesis_id == CASH_QUALITY_HYPOTHESIS_ID
        )
        qualification = quant_research_successor_source_qualification_v1()
        sec_registry = build_first_sec_fundamental_query_registry()
        if (
            self.source_successor_registry_fingerprint != registry.logical_fingerprint
            or self.source_cash_quality_hypothesis_fingerprint
            != cash_card.logical_fingerprint
            or self.source_closed_qualification_fingerprint
            != qualification.logical_fingerprint
            or self.source_closed_qualification_status != qualification.status
            or self.source_sec_query_registry_fingerprint
            != sec_registry.logical_fingerprint
            or self.line_items != _line_items()
            or self.duration_component_rules != _DURATION_COMPONENT_RULES
            or self.coverage_hard_stops != _COVERAGE_HARD_STOPS
            or self.replay_bindings != _REPLAY_BINDINGS
            or self.planned_stage_order != _PLANNED_STAGE_ORDER
            or self.forbidden_substitutes != _FORBIDDEN_SUBSTITUTES
            or self.hard_stop_reason_codes != _HARD_STOP_REASON_CODES
            or sec_cash_quality_source_plan_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("SEC cash-earnings-quality source plan differs")
        return self


def sec_cash_quality_source_plan_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def quant_research_sec_cash_quality_source_plan_v1() -> (
    SecCashEarningsQualitySourceEngineeringPlanV1
):
    registry = quant_research_successor_hypothesis_registry_v1()
    cash_card = next(
        item for item in registry.cards if item.hypothesis_id == CASH_QUALITY_HYPOTHESIS_ID
    )
    qualification = quant_research_successor_source_qualification_v1()
    payload: dict[str, object] = {
        "source_successor_registry_fingerprint": registry.logical_fingerprint,
        "source_cash_quality_hypothesis_fingerprint": cash_card.logical_fingerprint,
        "source_closed_qualification_fingerprint": qualification.logical_fingerprint,
        "source_sec_query_registry_fingerprint": (
            build_first_sec_fundamental_query_registry().logical_fingerprint
        ),
        "line_items": _line_items(),
        "duration_component_rules": _DURATION_COMPONENT_RULES,
        "coverage_hard_stops": _COVERAGE_HARD_STOPS,
        "replay_bindings": _REPLAY_BINDINGS,
        "planned_stage_order": _PLANNED_STAGE_ORDER,
        "forbidden_substitutes": _FORBIDDEN_SUBSTITUTES,
        "hard_stop_reason_codes": _HARD_STOP_REASON_CODES,
    }
    provisional = SecCashEarningsQualitySourceEngineeringPlanV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return SecCashEarningsQualitySourceEngineeringPlanV1.model_validate(
        {
            **payload,
            "logical_fingerprint": sec_cash_quality_source_plan_fingerprint(
                provisional
            ),
        }
    )


@lru_cache(maxsize=1)
def _line_items() -> tuple[SecCashQualityLineItemPlanV1, ...]:
    return tuple(
        SecCashQualityLineItemPlanV1.model_validate(payload)
        for payload in _LINE_ITEM_PAYLOADS
    )


_LINE_ITEM_PAYLOADS = (
    {
        "line_item_id": "operating_cash_flow",
        "concept_name": "NetCashProvidedByUsedInOperatingActivities",
        "period_shape": "duration",
        "admitted_forms": ("10-K", "10-K/A", "10-Q", "10-Q/A"),
        "admitted_fiscal_periods": ("FY", "Q1", "Q2", "Q3"),
    },
    {
        "line_item_id": "net_income",
        "concept_name": "NetIncomeLoss",
        "period_shape": "duration",
        "admitted_forms": ("10-K", "10-K/A", "10-Q", "10-Q/A"),
        "admitted_fiscal_periods": ("FY", "Q1", "Q2", "Q3"),
    },
    {
        "line_item_id": "total_assets",
        "concept_name": "Assets",
        "period_shape": "instant",
        "admitted_forms": ("10-K", "10-K/A", "10-Q", "10-Q/A"),
        "admitted_fiscal_periods": ("FY", "Q1", "Q2", "Q3"),
    },
)
_LINE_ITEMS_BY_ID = {
    str(item["line_item_id"]): {
        **item,
        "namespace": "us-gaap",
        "unit": "USD",
        "concept_fallback_authorized": False,
        "unsupported_namespace_behavior": "quarantine",
    }
    for item in _LINE_ITEM_PAYLOADS
}

_DURATION_COMPONENT_RULES = (
    "q1_discrete_equals_q1_reported_duration",
    "q2_discrete_equals_q2_ytd_minus_q1_ytd_same_fiscal_year",
    "q3_discrete_equals_q3_ytd_minus_q2_ytd_same_fiscal_year",
    "q4_discrete_equals_fy_duration_minus_q3_ytd_same_fiscal_year",
)
_COVERAGE_HARD_STOPS = (
    "expected_106_session_index_mismatch",
    "complete_sessions_below_96",
    "either_chronological_half_below_48_complete_sessions",
    "any_complete_session_below_500_complete_instruments",
    "joint_formula_availability_below_0_75",
    "point_in_time_nonfinancial_applicability_missing",
    "strict_and_reconstructed_evidence_tiers_not_separated",
    "raw_concept_counts_present_but_exact_joint_formula_coverage_unmeasured",
)
_REPLAY_BINDINGS = (
    "successor_registry_and_closed_source_qualification_fingerprints",
    "sec_companyfacts_submissions_filing_clock_and_query_registry_fingerprints",
    "stable_instrument_cik_link_and_membership_fingerprints",
    "point_in_time_applicability_source_fingerprint",
    "exact_session_index_formula_plan_and_implementation_revision",
    "coverage_report_logical_and_physical_fingerprints",
)
_PLANNED_STAGE_ORDER = (
    "register_exact_cfo_net_income_and_assets_source_queries",
    "materialize_cutoff_aware_clean_occurrence_selection",
    "derive_coherent_discrete_quarters_and_ttm_components",
    "apply_stable_security_identity_and_nonfinancial_applicability",
    "produce_outcome_blind_joint_coverage_and_quarantine_report",
    "independently_replay_and_compare_canonical_report_bytes",
)
_FORBIDDEN_SUBSTITUTES = (
    "latest_or_restated_current_financials_backfilled_before_availability",
    "annual_cfo_or_net_income_used_as_ttm",
    "ebitda_operating_income_or_free_cash_flow_used_for_cfo",
    "current_sector_or_sic_classification_backfilled_historically",
    "ticker_name_or_cik_broadcast_across_multiple_securities",
    "ifrs_or_extension_concept_fallback_without_new_registered_plan",
    "zero_forward_backward_or_model_based_missing_value_fill",
)
_HARD_STOP_REASON_CODES = (
    "source_fingerprint_or_schema_mismatch",
    "filing_acceptance_or_knowledge_time_missing",
    "duration_period_or_fiscal_chain_ambiguous",
    "amendment_or_cross_concept_accession_basis_incoherent",
    "opening_or_closing_assets_missing_or_nonpositive",
    "stable_security_projection_not_unique",
    "point_in_time_nonfinancial_applicability_unavailable",
    "coverage_floor_not_met",
    "outcome_validation_or_holdout_read_detected",
    "trial_feature_candidate_or_product_authority_requested",
    "canonical_report_replay_mismatch",
)
