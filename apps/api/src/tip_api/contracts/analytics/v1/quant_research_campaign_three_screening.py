"""Frozen before-outcomes screening protocol for Campaign Three interactions."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
    quant_research_campaign_three_hypothesis_registry_v1,
)
from .quant_research_discovery_trial_ledger_v3 import (
    quant_research_discovery_trial_ledger_v3,
)
from .quant_research_factor_screening import (
    QuantResearchFactorScreeningEndpointRule,
    QuantResearchFactorScreeningTarget,
)


QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_CONTRACT_VERSION = (
    "quant-research-campaign-three-screening-protocol/1.0"
)
QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_VERSION = (
    "whalpha.quant-research.campaign-three-screening/1.0.0"
)
CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT = (
    "0adfc41aa63277c79f9048344e7d81dfafbc33dc083b85f4b4746bc64a8fb46d"
)
CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256 = (
    "aa51b7cb3bd881fb3b70992ca6b7cc0eaf18ad1602e32f3e9aae2930863d7dbc"
)
CAMPAIGN_THREE_QUALIFIED_HYPOTHESIS_IDS = (
    "whalpha.hypothesis.campaign-three.breakout-breadth",
    "whalpha.hypothesis.campaign-three.volume-participation",
    "whalpha.hypothesis.campaign-three.residual-risk-volatility",
)
CAMPAIGN_THREE_REJECTED_INPUT_HYPOTHESIS_ID = (
    "whalpha.hypothesis.campaign-three.defensive-resilience"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CampaignThreeScreeningHypothesisV1(FrozenModel):
    trial_id: str = Field(
        pattern=r"^whalpha\.discovery-trial\.campaign-three\.[a-z0-9-]+\.h3$"
    )
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    hypothesis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: CampaignThreeHypothesisRole
    source_factor_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    source_factor_version: str
    source_factor_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_factor_orientation: Literal[
        "as_defined", "sign_reversed_lower_is_safer"
    ]
    state_metric_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    state_metric_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    state_transform: str
    target: QuantResearchFactorScreeningTarget
    endpoint_rule: QuantResearchFactorScreeningEndpointRule
    interaction_estimand: Literal[
        "session_rank_ic_q_t_equals_alpha_plus_beta_times_state_s_t_plus_error"
    ] = "session_rank_ic_q_t_equals_alpha_plus_beta_times_state_s_t_plus_error"
    expected_interaction_slope: Literal["beta_greater_than_zero"] = (
        "beta_greater_than_zero"
    )
    related_hypothesis_family: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    primary_horizon_sessions: Literal[3] = 3
    diagnostic_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)
    input_qualification_decision: Literal["qualified_for_protocol_freeze"] = (
        "qualified_for_protocol_freeze"
    )
    formal_trial_count: Literal[1] = 1

    @model_validator(mode="after")
    def hypothesis_reconciles(self) -> "CampaignThreeScreeningHypothesisV1":
        registry = quant_research_campaign_three_hypothesis_registry_v1()
        source = next(
            (item for item in registry.proposals if item.hypothesis_id == self.hypothesis_id),
            None,
        )
        slug = self.hypothesis_id.removeprefix("whalpha.hypothesis.campaign-three.")
        if (
            source is None
            or self.hypothesis_id not in CAMPAIGN_THREE_QUALIFIED_HYPOTHESIS_IDS
            or self.trial_id != f"whalpha.discovery-trial.campaign-three.{slug}.h3"
            or self.hypothesis_fingerprint != source.logical_fingerprint
            or self.role is not source.role
            or self.source_factor_id != source.source_factor_id
            or self.source_factor_version != source.source_factor_version
            or self.source_factor_definition_fingerprint
            != source.source_factor_definition_fingerprint
            or self.source_factor_orientation != source.source_factor_orientation
            or self.state_metric_id != source.state_metric_id
            or self.state_metric_definition_fingerprint
            != source.state_metric_definition_fingerprint
            or self.state_transform != source.state_transform
            or self.related_hypothesis_family != source.related_hypothesis_family
        ):
            raise ValueError("Campaign Three screening hypothesis differs")
        if self.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION:
            if (
                self.target is not QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN
                or self.endpoint_rule
                is not QuantResearchFactorScreeningEndpointRule.LOWER_AND_UPPER_MUST_AGREE
            ):
                raise ValueError("Campaign Three Alpha target differs")
        elif self.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION:
            if (
                self.target
                is not QuantResearchFactorScreeningTarget.MAXIMUM_ADVERSE_EXCURSION
                or self.endpoint_rule
                is not QuantResearchFactorScreeningEndpointRule.COMPLETE_PATH_EXACT_ONLY
            ):
                raise ValueError("Campaign Three risk target differs")
        else:
            raise ValueError("Campaign Three nonformal role cannot consume a trial")
        return self


class CampaignThreeScreeningProtocolV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_CONTRACT_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_CONTRACT_VERSION
    protocol_version: Literal[QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_VERSION] = (
        QUANT_RESEARCH_CAMPAIGN_THREE_SCREENING_VERSION
    )
    registered_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    evidence_tier: Literal["reconstructed_latest_vintage_development_only"] = (
        "reconstructed_latest_vintage_development_only"
    )
    source_hypothesis_registry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_input_qualification_fingerprint: Literal[
        CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
    ] = CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
    source_input_qualification_sha256: Literal[
        CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
    ] = CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
    source_input_qualification_status: Literal["ready_for_protocol_freeze"] = (
        "ready_for_protocol_freeze"
    )
    source_input_qualification_exact_replay_verified: Literal[True] = True
    prior_discovery_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    development_first_session: Literal[date(2025, 7, 22)] = date(2025, 7, 22)
    development_last_session: Literal[date(2026, 1, 7)] = date(2026, 1, 7)
    development_session_count: Literal[106] = 106
    chronological_half_session_counts: tuple[Literal[53], Literal[53]] = (53, 53)
    membership_tier: Literal["reconstructed_latest_vintage_research_only"] = (
        "reconstructed_latest_vintage_research_only"
    )
    signal_cutoff: Literal["completed_session_close"] = "completed_session_close"
    entry_basis: Literal["next_session_open"] = "next_session_open"
    exit_basis: Literal["horizon_session_close"] = "horizon_session_close"
    primary_horizon_sessions: Literal[3] = 3
    diagnostic_horizon_sessions: tuple[Literal[1], Literal[5]] = (1, 5)
    formal_hypotheses: tuple[CampaignThreeScreeningHypothesisV1, ...] = Field(
        min_length=3, max_length=3
    )
    formal_trial_count: Literal[3] = 3
    prior_consumed_trial_count: Literal[14] = 14
    cumulative_trial_count_after_registration: Literal[17] = 17
    candidate_alpha_trial_count: Literal[2] = 2
    risk_guard_trial_count: Literal[1] = 1
    rejected_before_outcomes_count: Literal[2] = 2
    rejected_near_duplicate_count: Literal[1] = 1
    rejected_input_support_count: Literal[1] = 1
    factor_transform: Literal[
        "same_session_average_rank_oriented_to_registered_better_state"
    ] = "same_session_average_rank_oriented_to_registered_better_state"
    target_transform: Literal["same_session_average_rank"] = (
        "same_session_average_rank"
    )
    session_statistic: Literal[
        "spearman_q_t_between_oriented_factor_rank_and_target_rank"
    ] = "spearman_q_t_between_oriented_factor_rank_and_target_rank"
    interaction_regression: Literal[
        "q_t_equals_alpha_plus_beta_times_registered_state_s_t_plus_error"
    ] = "q_t_equals_alpha_plus_beta_times_registered_state_s_t_plus_error"
    minimum_instruments_per_session: Literal[100] = 100
    minimum_primary_sessions: Literal[80] = 80
    minimum_chronological_half_sessions: Literal[40] = 40
    bootstrap_method: Literal["deterministic_circular_session_block"] = (
        "deterministic_circular_session_block"
    )
    primary_bootstrap_block_sessions: Literal[10] = 10
    sensitivity_bootstrap_block_sessions: Literal[20] = 20
    bootstrap_replicates: Literal[10000] = 10000
    confidence_level: Literal["0.9000000000"] = "0.9000000000"
    one_sided_familywise_alpha: Literal["0.0500000000"] = "0.0500000000"
    multiplicity_method: Literal[
        "holm_separate_candidate_alpha_and_risk_guard_families"
    ] = "holm_separate_candidate_alpha_and_risk_guard_families"
    primary_interaction_gate: Literal[
        "beta_positive_and_one_sided_90pct_lower_bound_positive"
    ] = "beta_positive_and_one_sided_90pct_lower_bound_positive"
    chronological_stability_rule: Literal[
        "beta_positive_in_both_halves_with_minimum_session_floor"
    ] = "beta_positive_in_both_halves_with_minimum_session_floor"
    alpha_favorable_state_gate: Literal[
        "candidate_alpha_mean_q_positive_where_registered_state_above_natural_zero"
    ] = "candidate_alpha_mean_q_positive_where_registered_state_above_natural_zero"
    alpha_favorable_state_minimum_sessions: Literal[20] = 20
    risk_guard_favorable_state_gate: Literal[
        "not_applied_continuous_volatility_interaction_uses_beta_gate"
    ] = "not_applied_continuous_volatility_interaction_uses_beta_gate"
    primary_block_required: Literal[True] = True
    sensitivity_block_sign_consistency_required: Literal[True] = True
    diagnostic_horizons_cannot_replace_primary: Literal[True] = True
    cost_scenarios_bps_per_side: tuple[
        Literal[0], Literal[10], Literal[25], Literal[50]
    ] = (0, 10, 25, 50)
    cost_gate_applied: Literal[False] = False
    cost_gate_reason: Literal[
        "factor_interaction_screen_is_not_a_strategy_expression_or_portfolio"
    ] = "factor_interaction_screen_is_not_a_strategy_expression_or_portfolio"
    maximum_selected_candidate_alpha: Literal[1] = 1
    maximum_selected_risk_guard: Literal[1] = 1
    maximum_per_related_hypothesis_family: Literal[1] = 1
    selection_order: Literal[
        "all_gates_then_worst_case_beta_then_lower_bound_then_hypothesis_id"
    ] = "all_gates_then_worst_case_beta_then_lower_bound_then_hypothesis_id"
    model_phase_requires_selected_candidate_alpha: Literal[True] = True
    risk_guard_cannot_open_model_alone: Literal[True] = True
    stopping_rule: Literal[
        "one_report_one_exact_replay_then_close_ledger_without_retuning"
    ] = "one_report_one_exact_replay_then_close_ledger_without_retuning"
    campaign_is_adaptive_to_consumed_development_evidence: Literal[True] = True
    prior_strategy_outcomes_prohibited: Literal[True] = True
    source_input_qualification_contains_forward_outcomes: Literal[False] = False
    development_access_requires_separate_typed_grant: Literal[True] = True
    development_outcome_read_authorized: Literal[False] = False
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
    def protocol_reconciles(self) -> "CampaignThreeScreeningProtocolV1":
        registry = quant_research_campaign_three_hypothesis_registry_v1()
        prior = quant_research_discovery_trial_ledger_v3()
        if (
            self.source_hypothesis_registry_fingerprint != registry.logical_fingerprint
            or self.prior_discovery_ledger_fingerprint != prior.logical_fingerprint
            or self.formal_hypotheses != _formal_hypotheses()
            or tuple(item.hypothesis_id for item in self.formal_hypotheses)
            != CAMPAIGN_THREE_QUALIFIED_HYPOTHESIS_IDS
            or len({item.trial_id for item in self.formal_hypotheses}) != 3
            or sum(item.formal_trial_count for item in self.formal_hypotheses) != 3
            or campaign_three_screening_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three screening protocol differs")
        return self


def campaign_three_screening_fingerprint(
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
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def quant_research_campaign_three_screening_protocol_v1() -> (
    CampaignThreeScreeningProtocolV1
):
    payload: dict[str, object] = {
        "source_hypothesis_registry_fingerprint": (
            quant_research_campaign_three_hypothesis_registry_v1().logical_fingerprint
        ),
        "prior_discovery_ledger_fingerprint": (
            quant_research_discovery_trial_ledger_v3().logical_fingerprint
        ),
        "formal_hypotheses": _formal_hypotheses(),
    }
    provisional = CampaignThreeScreeningProtocolV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeScreeningProtocolV1.model_validate(
        {
            **payload,
            "logical_fingerprint": campaign_three_screening_fingerprint(provisional),
        }
    )


@lru_cache(maxsize=1)
def _formal_hypotheses() -> tuple[CampaignThreeScreeningHypothesisV1, ...]:
    registry = quant_research_campaign_three_hypothesis_registry_v1()
    hypotheses = []
    for hypothesis_id in CAMPAIGN_THREE_QUALIFIED_HYPOTHESIS_IDS:
        source = next(
            item for item in registry.proposals if item.hypothesis_id == hypothesis_id
        )
        slug = hypothesis_id.removeprefix("whalpha.hypothesis.campaign-three.")
        is_alpha = (
            source.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
        )
        hypotheses.append(
            CampaignThreeScreeningHypothesisV1(
                trial_id=f"whalpha.discovery-trial.campaign-three.{slug}.h3",
                hypothesis_id=source.hypothesis_id,
                hypothesis_fingerprint=source.logical_fingerprint,
                role=source.role,
                source_factor_id=source.source_factor_id,
                source_factor_version=source.source_factor_version,
                source_factor_definition_fingerprint=(
                    source.source_factor_definition_fingerprint
                ),
                source_factor_orientation=source.source_factor_orientation,
                state_metric_id=source.state_metric_id,
                state_metric_definition_fingerprint=(
                    source.state_metric_definition_fingerprint
                ),
                state_transform=source.state_transform,
                target=(
                    QuantResearchFactorScreeningTarget.SPY_RELATIVE_RETURN
                    if is_alpha
                    else QuantResearchFactorScreeningTarget.MAXIMUM_ADVERSE_EXCURSION
                ),
                endpoint_rule=(
                    QuantResearchFactorScreeningEndpointRule.LOWER_AND_UPPER_MUST_AGREE
                    if is_alpha
                    else QuantResearchFactorScreeningEndpointRule.COMPLETE_PATH_EXACT_ONLY
                ),
                related_hypothesis_family=source.related_hypothesis_family,
            )
        )
    return tuple(hypotheses)
