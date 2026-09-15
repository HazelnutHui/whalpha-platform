"""Frozen before-outcomes screening protocol for Factor Catalog V1."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_factor_catalog import (
    QuantResearchFactorExpectedRelationship,
    QuantResearchFactorRole,
    quant_research_factor_catalog_v1,
)


QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_CONTRACT_VERSION = (
    "quant-research-factor-screening-protocol/1.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_VERSION = (
    "quant-research-factor-screening/1.0.0"
)
QUANT_RESEARCH_FACTOR_SCREENING_EVIDENCE_TIER = (
    "reconstructed_latest_vintage_development_only"
)
QUANT_RESEARCH_FACTOR_SCREENING_DIAGNOSTICS_FINGERPRINT = (
    "fb92e95acb146af66fb4d9e286c96852374a51884936f5d69536c4accacdab02"
)
QUANT_RESEARCH_FACTOR_SCREENING_DIAGNOSTICS_SHA256 = (
    "3767c39e327e8e3959d184ae8a16d2c5be3e1425fda416093b6aeefc51485e5e"
)
QUANT_RESEARCH_FACTOR_SCREENING_CHRONOLOGICAL_PLAN_FINGERPRINT = (
    "e793471617c35de7596aee27950e3f5ded0bcd51cf4370ac8b20742cb9b24515"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchFactorScreeningTarget(StrEnum):
    SPY_RELATIVE_RETURN = "spy_relative_next_open_to_horizon_close"
    MAXIMUM_ADVERSE_EXCURSION = "maximum_adverse_excursion_from_next_open"


class QuantResearchFactorScreeningEndpointRule(StrEnum):
    LOWER_AND_UPPER_MUST_AGREE = "lower_and_upper_interval_endpoints_must_agree"
    COMPLETE_PATH_EXACT_ONLY = "complete_path_excursion_exact_only"


class QuantResearchFactorScreeningHypothesisV1(FrozenModel):
    factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    role: QuantResearchFactorRole
    target: QuantResearchFactorScreeningTarget
    expected_relationship: QuantResearchFactorExpectedRelationship
    related_factor_group: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    endpoint_rule: QuantResearchFactorScreeningEndpointRule
    formal_trial_count: Literal[1] = 1
    standalone_rank_ic_required: Literal[True] = True
    partial_rank_ic_baseline_factor_id: str | None
    primary_horizon_sessions: Literal[3] = 3
    decay_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)

    @model_validator(mode="after")
    def hypothesis_reconciles(self) -> "QuantResearchFactorScreeningHypothesisV1":
        catalog = quant_research_factor_catalog_v1()
        definition = next(
            (item for item in catalog.definitions if item.factor_id == self.factor_id),
            None,
        )
        if (
            definition is None
            or definition.role != self.role
            or definition.expected_relationship != self.expected_relationship
            or definition.related_factor_group != self.related_factor_group
            or self.role is QuantResearchFactorRole.SETUP_CONDITIONER
        ):
            raise ValueError("screening hypothesis differs from Factor Catalog V1")
        if self.role is QuantResearchFactorRole.CANDIDATE_ALPHA:
            if (
                self.target
                is not QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN
                or self.endpoint_rule
                is not QuantResearchFactorScreeningEndpointRule.LOWER_AND_UPPER_MUST_AGREE
            ):
                raise ValueError("candidate-Alpha screening target differs")
        elif (
            self.target
            is not QuantResearchFactorScreeningTarget.MAXIMUM_ADVERSE_EXCURSION
            or self.endpoint_rule
            is not QuantResearchFactorScreeningEndpointRule.COMPLETE_PATH_EXACT_ONLY
        ):
            raise ValueError("risk-guard screening target differs")
        baseline = "relative_return_spy_20s"
        expected_baseline = None if self.factor_id == baseline else baseline
        if self.partial_rank_ic_baseline_factor_id != expected_baseline:
            raise ValueError("incremental baseline differs")
        return self


class QuantResearchFactorScreeningProtocolV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_CONTRACT_VERSION
    ] = QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_CONTRACT_VERSION
    protocol_version: Literal[QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_VERSION] = (
        QUANT_RESEARCH_FACTOR_SCREENING_PROTOCOL_VERSION
    )
    registered_date: Literal[date(2026, 9, 15)] = date(2026, 9, 15)
    evidence_tier: Literal[QUANT_RESEARCH_FACTOR_SCREENING_EVIDENCE_TIER] = (
        QUANT_RESEARCH_FACTOR_SCREENING_EVIDENCE_TIER
    )
    catalog_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_diagnostics_fingerprint: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_DIAGNOSTICS_FINGERPRINT
    ] = QUANT_RESEARCH_FACTOR_SCREENING_DIAGNOSTICS_FINGERPRINT
    source_diagnostics_sha256: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_DIAGNOSTICS_SHA256
    ] = QUANT_RESEARCH_FACTOR_SCREENING_DIAGNOSTICS_SHA256
    chronological_plan_fingerprint: Literal[
        QUANT_RESEARCH_FACTOR_SCREENING_CHRONOLOGICAL_PLAN_FINGERPRINT
    ] = QUANT_RESEARCH_FACTOR_SCREENING_CHRONOLOGICAL_PLAN_FINGERPRINT
    source_session_count: Literal[287] = 287
    development_eligible_session_count: Literal[106] = 106
    development_expected_path_count: Literal[167860] = 167860
    first_development_signal_session: Literal[date(2025, 7, 22)] = date(2025, 7, 22)
    last_development_signal_session: Literal[date(2026, 1, 7)] = date(2026, 1, 7)
    cohort_rule: Literal[
        "complete_twelve_factor_vector_and_usable_chronological_development_session"
    ] = "complete_twelve_factor_vector_and_usable_chronological_development_session"
    incomplete_cross_section_rule: Literal["exclude_complete_session"] = (
        "exclude_complete_session"
    )
    membership_tier: Literal["reconstructed_latest_vintage_research_only"] = (
        "reconstructed_latest_vintage_research_only"
    )
    signal_cutoff: Literal["completed_session_close"] = "completed_session_close"
    entry_basis: Literal["next_session_open"] = "next_session_open"
    exit_basis: Literal["horizon_session_close"] = "horizon_session_close"
    primary_horizon_sessions: Literal[3] = 3
    decay_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)
    factor_transform: Literal[
        "same_session_average_rank_oriented_to_expected_better_state"
    ] = "same_session_average_rank_oriented_to_expected_better_state"
    target_transform: Literal["same_session_average_rank"] = "same_session_average_rank"
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
    incremental_baseline_factor_id: Literal["relative_return_spy_20s"] = (
        "relative_return_spy_20s"
    )
    incremental_method: Literal[
        "same_session_partial_spearman_after_linear_rank_residualization"
    ] = "same_session_partial_spearman_after_linear_rank_residualization"
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
    formal_hypotheses: tuple[QuantResearchFactorScreeningHypothesisV1, ...] = Field(
        min_length=8, max_length=8
    )
    formal_trial_count: Literal[8] = 8
    candidate_alpha_trial_count: Literal[5] = 5
    risk_guard_trial_count: Literal[3] = 3
    setup_conditioner_trial_count: Literal[0] = 0
    setup_conditioner_disposition: Literal[
        "registered_not_outcome_screened_requires_future_interaction_protocol"
    ] = "registered_not_outcome_screened_requires_future_interaction_protocol"
    maximum_model_candidate_factors: Literal[3] = 3
    maximum_model_candidate_alpha_factors: Literal[2] = 2
    maximum_model_risk_guard_factors: Literal[1] = 1
    maximum_per_related_factor_group: Literal[1] = 1
    selection_order: Literal[
        "gate_pass_then_worst_case_effect_then_lower_bound_then_factor_id"
    ] = "gate_pass_then_worst_case_effect_then_lower_bound_then_factor_id"
    model_phase_requires_candidate_alpha: Literal[True] = True
    stopping_rule: Literal[
        "one_report_one_exact_replay_no_formula_threshold_role_or_label_revision"
    ] = "one_report_one_exact_replay_no_formula_threshold_role_or_label_revision"
    prior_strategy_outcomes_prohibited: Literal[True] = True
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
    def protocol_reconciles(self) -> "QuantResearchFactorScreeningProtocolV1":
        catalog = quant_research_factor_catalog_v1()
        if self.catalog_fingerprint != catalog.logical_fingerprint:
            raise ValueError("screening protocol catalog identity differs")
        if self.formal_hypotheses != _formal_hypotheses():
            raise ValueError("screening hypothesis registry differs")
        if sum(item.formal_trial_count for item in self.formal_hypotheses) != 8:
            raise ValueError("screening trial count differs")
        if factor_screening_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("screening protocol fingerprint differs")
        return self


def factor_screening_fingerprint(value: BaseModel | dict[str, object]) -> str:
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
def quant_research_factor_screening_protocol_v1() -> QuantResearchFactorScreeningProtocolV1:
    hypotheses = _formal_hypotheses()
    payload: dict[str, object] = {
        "catalog_fingerprint": quant_research_factor_catalog_v1().logical_fingerprint,
        "formal_hypotheses": hypotheses,
    }
    provisional = QuantResearchFactorScreeningProtocolV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchFactorScreeningProtocolV1.model_validate(
        {
            **payload,
            "logical_fingerprint": factor_screening_fingerprint(provisional),
        }
    )


def _formal_hypotheses() -> tuple[QuantResearchFactorScreeningHypothesisV1, ...]:
    catalog = quant_research_factor_catalog_v1()
    result = []
    for definition in catalog.definitions:
        if definition.role is QuantResearchFactorRole.SETUP_CONDITIONER:
            continue
        alpha = definition.role is QuantResearchFactorRole.CANDIDATE_ALPHA
        result.append(
            QuantResearchFactorScreeningHypothesisV1(
                factor_id=definition.factor_id,
                role=definition.role,
                target=(
                    QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN
                    if alpha
                    else QuantResearchFactorScreeningTarget.MAXIMUM_ADVERSE_EXCURSION
                ),
                expected_relationship=definition.expected_relationship,
                related_factor_group=definition.related_factor_group,
                endpoint_rule=(
                    QuantResearchFactorScreeningEndpointRule.LOWER_AND_UPPER_MUST_AGREE
                    if alpha
                    else QuantResearchFactorScreeningEndpointRule.COMPLETE_PATH_EXACT_ONLY
                ),
                partial_rank_ic_baseline_factor_id=(
                    None
                    if definition.factor_id == "relative_return_spy_20s"
                    else "relative_return_spy_20s"
                ),
            )
        )
    return tuple(result)
