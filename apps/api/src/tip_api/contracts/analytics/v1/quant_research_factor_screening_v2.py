"""Frozen before-outcomes screening protocol for Factor Catalog V2."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_discovery_trial_ledger import (
    quant_research_discovery_trial_ledger_v1,
)
from .quant_research_factor_catalog import (
    factor_definition_fingerprint,
    quant_research_factor_catalog_v1,
)
from .quant_research_factor_catalog_v2 import (
    QuantResearchFactorExpectedRelationshipV2,
    QuantResearchFactorRoleV2,
    quant_research_factor_catalog_v2,
)
from .quant_research_factor_screening import (
    QUANT_RESEARCH_FACTOR_SCREENING_CHRONOLOGICAL_PLAN_FINGERPRINT,
    QuantResearchFactorScreeningEndpointRule,
    QuantResearchFactorScreeningTarget,
)


QUANT_RESEARCH_FACTOR_SCREENING_V2_CONTRACT_VERSION = (
    "quant-research-factor-screening-protocol/2.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_VERSION = (
    "quant-research-factor-screening/2.0.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_EVIDENCE_TIER = (
    "reconstructed_latest_vintage_development_only"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_QUALIFICATION_FINGERPRINT = (
    "f49b17d74b9ec0960278405475ec962361c8169bd071030deda7fa36557aee90"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_QUALIFICATION_SHA256 = (
    "48b36f422e4a07e18de45e8b9a7bd8ea8d5469fc2961a84ab1037a554260999e"
)
QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID = "relative_return_spy_20s"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorScreeningHypothesisV2(FrozenModel):
    trial_id: str = Field(
        pattern=r"^whalpha\.discovery-trial\.daily-behavior-v2\.[a-z0-9_]+\.h3$"
    )
    factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    factor_version: str = Field(pattern=r"^whalpha\.factor\.[a-z0-9_.-]+/1\.0\.0$")
    factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: QuantResearchFactorRoleV2
    target: QuantResearchFactorScreeningTarget
    expected_relationship: QuantResearchFactorExpectedRelationshipV2
    related_factor_group: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    endpoint_rule: QuantResearchFactorScreeningEndpointRule
    formal_trial_count: Literal[1] = 1
    standalone_rank_ic_required: Literal[True] = True
    partial_rank_ic_baseline_factor_id: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    ] = QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    primary_horizon_sessions: Literal[3] = 3
    decay_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)

    @model_validator(mode="after")
    def hypothesis_reconciles(self) -> "QuantResearchFactorScreeningHypothesisV2":
        definition = next(
            (
                item
                for item in quant_research_factor_catalog_v2().definitions
                if item.factor_id == self.factor_id
            ),
            None,
        )
        if (
            definition is None
            or definition.role != self.role
            or definition.factor_version != self.factor_version
            or definition.logical_fingerprint != self.factor_definition_fingerprint
            or definition.expected_relationship != self.expected_relationship
            or definition.related_factor_group != self.related_factor_group
            or self.trial_id
            != f"whalpha.discovery-trial.daily-behavior-v2.{self.factor_id}.h3"
        ):
            raise ValueError("screening hypothesis differs from Factor Catalog V2")
        if self.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA:
            if (
                self.target
                is not QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN
                or self.endpoint_rule
                is not QuantResearchFactorScreeningEndpointRule.LOWER_AND_UPPER_MUST_AGREE
            ):
                raise ValueError("candidate-Alpha V2 screening target differs")
        elif self.role is QuantResearchFactorRoleV2.RISK_GUARD:
            if (
                self.target
                is not QuantResearchFactorScreeningTarget.MAXIMUM_ADVERSE_EXCURSION
                or self.endpoint_rule
                is not QuantResearchFactorScreeningEndpointRule.COMPLETE_PATH_EXACT_ONLY
            ):
                raise ValueError("risk-guard V2 screening target differs")
        else:
            raise ValueError("nonformal V2 role cannot consume an outcome trial")
        return self


class QuantResearchFactorScreeningProtocolV2(FrozenModel):
    schema_version: Literal["2.0"] = "2.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_V2_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_V2_CONTRACT_VERSION
    protocol_version: Literal[QUANT_RESEARCH_FACTOR_SCREENING_V2_VERSION] = (
        QUANT_RESEARCH_FACTOR_SCREENING_V2_VERSION
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    evidence_tier: Literal[QUANT_RESEARCH_FACTOR_SCREENING_V2_EVIDENCE_TIER] = (
        QUANT_RESEARCH_FACTOR_SCREENING_V2_EVIDENCE_TIER
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_qualification_fingerprint: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_V2_QUALIFICATION_FINGERPRINT
    ] = QUANT_RESEARCH_FACTOR_SCREENING_V2_QUALIFICATION_FINGERPRINT
    source_qualification_sha256: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_V2_QUALIFICATION_SHA256
    ] = QUANT_RESEARCH_FACTOR_SCREENING_V2_QUALIFICATION_SHA256
    source_qualification_status: Literal[
        "ready_for_screening_protocol_review"
    ] = "ready_for_screening_protocol_review"
    prior_discovery_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    chronological_plan_fingerprint: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_CHRONOLOGICAL_PLAN_FINGERPRINT
    ] = QUANT_RESEARCH_FACTOR_SCREENING_CHRONOLOGICAL_PLAN_FINGERPRINT
    source_signal_session_count: Literal[287] = 287
    qualified_signal_session_count: Literal[267] = 267
    development_declared_session_count: Literal[106] = 106
    development_declared_path_count: Literal[167860] = 167860
    first_development_signal_session: Literal[date(2025, 7, 22)] = date(2025, 7, 22)
    last_development_signal_session: Literal[date(2026, 1, 7)] = date(2026, 1, 7)
    cohort_rule: Literal[
        "qualification_eligible_session_and_signal_membership_path_in_development"
    ] = "qualification_eligible_session_and_signal_membership_path_in_development"
    stock_factor_missingness_rule: Literal[
        "exclude_only_affected_stable_id_factor_trial"
    ] = "exclude_only_affected_stable_id_factor_trial"
    benchmark_factor_missingness_rule: Literal[
        "exclude_complete_session_for_all_trials"
    ] = "exclude_complete_session_for_all_trials"
    label_missingness_rule: Literal[
        "retain_nonnumeric_exclusion_reason_never_zero_fill"
    ] = "retain_nonnumeric_exclusion_reason_never_zero_fill"
    membership_tier: Literal["reconstructed_latest_vintage_research_only"] = (
        "reconstructed_latest_vintage_research_only"
    )
    signal_cutoff: Literal["completed_session_close"] = "completed_session_close"
    entry_basis: Literal["next_session_open"] = "next_session_open"
    exit_basis: Literal["horizon_session_close"] = "horizon_session_close"
    primary_horizon_sessions: Literal[3] = 3
    decay_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)
    formal_hypotheses: tuple[QuantResearchFactorScreeningHypothesisV2, ...] = Field(
        min_length=6, max_length=6
    )
    formal_trial_count: Literal[6] = 6
    prior_consumed_trial_count: Literal[8] = 8
    cumulative_trial_count_after_registration: Literal[14] = 14
    candidate_alpha_trial_count: Literal[4] = 4
    risk_guard_trial_count: Literal[2] = 2
    setup_conditioner_trial_count: Literal[0] = 0
    applicability_input_trial_count: Literal[0] = 0
    setup_conditioner_disposition: Literal[
        "registered_not_screened_requires_separate_interaction_protocol"
    ] = "registered_not_screened_requires_separate_interaction_protocol"
    applicability_input_disposition: Literal[
        "registered_for_capacity_analysis_not_standalone_alpha"
    ] = "registered_for_capacity_analysis_not_standalone_alpha"
    factor_transform: Literal[
        "same_session_average_rank_oriented_to_expected_better_state"
    ] = "same_session_average_rank_oriented_to_expected_better_state"
    target_transform: Literal["same_session_average_rank"] = (
        "same_session_average_rank"
    )
    winsorization_rule: Literal["none_rank_statistics_are_primary"] = (
        "none_rank_statistics_are_primary"
    )
    minimum_instruments_per_session: Literal[100] = 100
    minimum_primary_sessions: Literal[80] = 80
    minimum_chronological_half_sessions: Literal[40] = 40
    bootstrap_method: Literal["deterministic_circular_session_block"] = (
        "deterministic_circular_session_block"
    )
    bootstrap_block_sessions: Literal[5] = 5
    bootstrap_replicates: Literal[10000] = 10000
    confidence_level: Literal["0.9000000000"] = "0.9000000000"
    one_sided_familywise_alpha: Literal["0.0500000000"] = "0.0500000000"
    multiplicity_method: Literal["holm_within_registered_role_family"] = (
        "holm_within_registered_role_family"
    )
    gate_origin: Literal[
        "factor_screening_v1_thresholds_reused_unchanged_before_v2_outcomes"
    ] = "factor_screening_v1_thresholds_reused_unchanged_before_v2_outcomes"
    minimum_primary_mean_rank_ic: Literal["0.0150000000"] = "0.0150000000"
    minimum_incremental_mean_partial_rank_ic: Literal["0.0050000000"] = (
        "0.0050000000"
    )
    minimum_positive_session_share: Literal["0.5500000000"] = "0.5500000000"
    maximum_absolute_session_contribution_share: Literal["0.1500000000"] = (
        "0.1500000000"
    )
    bucket_count: Literal[5] = 5
    minimum_bucket_monotonic_spearman: Literal["0.8000000000"] = "0.8000000000"
    minimum_bucket_top_minus_bottom: Literal["0.0000000000"] = "0.0000000000"
    minimum_decay_rank_ic: Literal["-0.0100000000"] = "-0.0100000000"
    chronological_stability_rule: Literal[
        "both_halves_positive_with_minimum_session_floor"
    ] = "both_halves_positive_with_minimum_session_floor"
    regime_stability_rule: Literal[
        "descriptive_only_historical_regime_diversity_not_proven"
    ] = "descriptive_only_historical_regime_diversity_not_proven"
    industry_neutralization_rule: Literal[
        "unavailable_no_historical_classification_may_be_inferred"
    ] = "unavailable_no_historical_classification_may_be_inferred"
    incremental_baseline_factor_id: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    ] = QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    incremental_baseline_factor_version: str = Field(
        pattern=r"^whalpha\.factor\.[a-z0-9_.-]+/1\.0\.0$"
    )
    incremental_baseline_definition_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    incremental_baseline_rule: Literal[
        "same_session_linear_rank_residual_control_not_formal_v2_trial"
    ] = "same_session_linear_rank_residual_control_not_formal_v2_trial"
    incremental_baseline_was_consumed_v1_alpha_trial: Literal[True] = True
    cost_scenarios_bps_per_side: tuple[
        Literal[0], Literal[10], Literal[25], Literal[50]
    ] = (0, 10, 25, 50)
    alpha_cost_diagnostic: Literal[
        "quintile_long_short_gross_spread_minus_four_sides_cost"
    ] = "quintile_long_short_gross_spread_minus_four_sides_cost"
    cost_gate_applied: Literal[False] = False
    cost_gate_reason: Literal[
        "factor_screen_is_not_a_strategy_expression_or_portfolio"
    ] = "factor_screen_is_not_a_strategy_expression_or_portfolio"
    maximum_model_candidate_factors: Literal[3] = 3
    maximum_model_candidate_alpha_factors: Literal[2] = 2
    maximum_model_risk_guard_factors: Literal[1] = 1
    maximum_per_related_factor_group: Literal[1] = 1
    selection_order: Literal[
        "gate_pass_then_worst_case_effect_then_lower_bound_then_factor_id"
    ] = "gate_pass_then_worst_case_effect_then_lower_bound_then_factor_id"
    model_phase_requires_candidate_alpha: Literal[True] = True
    stopping_rule: Literal[
        "one_report_one_exact_replay_no_formula_threshold_role_label_or_selection_revision"
    ] = "one_report_one_exact_replay_no_formula_threshold_role_label_or_selection_revision"
    campaign_is_adaptive_to_consumed_development_evidence: Literal[True] = True
    prior_strategy_outcomes_prohibited: Literal[True] = True
    source_qualification_contains_forward_outcomes: Literal[False] = False
    development_outcome_read_authorized: Literal[True] = True
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def protocol_reconciles(self) -> "QuantResearchFactorScreeningProtocolV2":
        catalog = quant_research_factor_catalog_v2()
        prior_ledger = quant_research_discovery_trial_ledger_v1()
        baseline = next(
            item
            for item in quant_research_factor_catalog_v1().definitions
            if item.factor_id == QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
        )
        if (
            self.catalog_fingerprint != catalog.logical_fingerprint
            or self.prior_discovery_ledger_fingerprint
            != prior_ledger.logical_fingerprint
            or self.incremental_baseline_factor_version != baseline.factor_version
            or self.incremental_baseline_definition_fingerprint
            != factor_definition_fingerprint(baseline.factor_id)
            or self.formal_hypotheses != _formal_hypotheses()
            or len({item.trial_id for item in self.formal_hypotheses}) != 6
            or sum(item.formal_trial_count for item in self.formal_hypotheses) != 6
            or factor_screening_v2_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Factor Catalog V2 screening protocol differs")
        return self


def factor_screening_v2_fingerprint(value: BaseModel | dict[str, object]) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    else:
        payload = {key: item for key, item in value.items() if key != "logical_fingerprint"}
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def quant_research_factor_screening_protocol_v2() -> QuantResearchFactorScreeningProtocolV2:
    baseline = next(
        item
        for item in quant_research_factor_catalog_v1().definitions
        if item.factor_id == QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
    )
    payload: dict[str, object] = {
        "catalog_fingerprint": quant_research_factor_catalog_v2().logical_fingerprint,
        "prior_discovery_ledger_fingerprint": (
            quant_research_discovery_trial_ledger_v1().logical_fingerprint
        ),
        "incremental_baseline_factor_version": baseline.factor_version,
        "incremental_baseline_definition_fingerprint": (
            factor_definition_fingerprint(baseline.factor_id)
        ),
        "formal_hypotheses": _formal_hypotheses(),
    }
    provisional = QuantResearchFactorScreeningProtocolV2.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorScreeningProtocolV2.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_screening_v2_fingerprint(provisional),
        }
    )


@lru_cache(maxsize=1)
def _formal_hypotheses() -> tuple[QuantResearchFactorScreeningHypothesisV2, ...]:
    return tuple(
        QuantResearchFactorScreeningHypothesisV2(
            trial_id=(
                f"whalpha.discovery-trial.daily-behavior-v2.{definition.factor_id}.h3"
            ),
            factor_id=definition.factor_id,
            factor_version=definition.factor_version,
            factor_definition_fingerprint=definition.logical_fingerprint,
            role=definition.role,
            target=(
                QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN
                if definition.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
                else QuantResearchFactorScreeningTarget.MAXIMUM_ADVERSE_EXCURSION
            ),
            expected_relationship=definition.expected_relationship,
            related_factor_group=definition.related_factor_group,
            endpoint_rule=(
                QuantResearchFactorScreeningEndpointRule.LOWER_AND_UPPER_MUST_AGREE
                if definition.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
                else QuantResearchFactorScreeningEndpointRule.COMPLETE_PATH_EXACT_ONLY
            ),
        )
        for definition in quant_research_factor_catalog_v2().definitions
        if definition.role
        in {
            QuantResearchFactorRoleV2.CANDIDATE_ALPHA,
            QuantResearchFactorRoleV2.RISK_GUARD,
        }
    )
