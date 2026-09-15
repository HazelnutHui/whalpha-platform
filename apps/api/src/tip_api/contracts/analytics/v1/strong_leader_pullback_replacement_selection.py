"""Frozen coverage-corrected selection protocol for Strong-Leader Pullback."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_research import STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
from .strong_leader_pullback_development_statistics import (
    DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT,
)
from .strong_leader_pullback_method import STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT


REPLACEMENT_SELECTION_CONTRACT_VERSION = (
    "strong-leader-pullback-reconstructed-replacement-selection/1.0"
)
REPLACEMENT_SELECTION_POLICY_VERSION = (
    "strong-leader-pullback-reconstructed-replacement-selection-policy/2.0.0"
)
REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256 = (
    "c29f04b5e6da95e2256c137f23d00898b313325ac09e982a991bb823ce0f7852"
)
REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT = (
    "f0006fa38a7a729dca5b2cd34369e7c3bd2110aa17096bcd091d72875ce71f7f"
)
REPLACEMENT_SELECTION_PRIMARY_HORIZON = 3
REPLACEMENT_SELECTION_COST_BPS_PER_SIDE = 25
REPLACEMENT_SELECTION_MAXIMUM_SESSION_CONCENTRATION = "0.2000000000"
REPLACEMENT_SELECTION_MINIMUM_POSITIVE_SESSION_RATIO = "0.5000000000"
REPLACEMENT_SELECTION_VALIDATION_FAMILYWISE_ALPHA = "0.050000"
REPLACEMENT_SELECTION_PARAMETER_BUDGET = 24
REPLACEMENT_SELECTION_PRIOR_PROTOCOL_TRIALS = 1
REPLACEMENT_SELECTION_TOTAL_PROTOCOL_TRIALS = 2
REPLACEMENT_SELECTION_RUN_BUDGET = 1

_DESIGN_EVIDENCE = {
    "primary_inference_eligible_combination_count": 23,
    "primary_regime_floor_combination_count": 1,
    "primary_signal_count_minimum": 46,
    "primary_signal_count_maximum": 1513,
    "primary_control_count_minimum": 12224,
    "primary_control_count_maximum": 25982,
    "primary_paired_session_count_minimum": 35,
    "primary_paired_session_count_maximum": 105,
    "sparse_defensive_combination_count": 19,
    "sparse_defensive_signal_count_minimum": 1,
    "sparse_defensive_signal_count_maximum": 47,
    "primary_signal_unavailable_evidence_count": 0,
    "primary_control_unavailable_evidence_count": 0,
}
_ELIGIBILITY_RULES = (
    "evaluate_all_24_registered_combinations",
    "eligible_per_combination_in_all_three_endpoint_scenarios",
    "minimum_60_numeric_signals",
    "minimum_60_numeric_controls",
    "minimum_20_comparable_sessions",
    "any_primary_family_unavailable_evidence_blocks_selection",
    "unexecutable_rows_remain_explicit_no_result_not_zero",
)
_SELECTION_RULES = (
    "common_eligible_set_ranked_independently_in_each_endpoint_scenario",
    "maximum_primary_3s_90pct_lower_session_balanced_contrast",
    "then_mean_contrast_then_signal_count_then_stable_id",
    "same_winner_required_in_all_three_endpoint_scenarios",
)
_ROBUSTNESS_GATES = (
    "contrast_adverse_primary_lower_90pct_strictly_positive",
    "signal_median_spy_relative_return_net_25bps_per_side_strictly_positive",
    "first_chronological_half_mean_contrast_strictly_positive",
    "second_chronological_half_mean_contrast_strictly_positive",
    "positive_paired_session_ratio_strictly_above_one_half",
    "largest_absolute_session_contrast_share_at_most_one_fifth",
)
_REGIME_RULES = (
    "regime_not_a_primary_selection_eligibility_gate",
    "every_regime_count_and_descriptive_contrast_retained",
    "regime_specific_inference_requires_at_least_60_signals",
    "sparse_regime_is_inconclusive_and_cannot_support_a_regime_claim",
)
_VALIDATION_RULES = (
    "validation_cannot_change_the_parameter_lock",
    "full_24_member_family_retained_for_multiplicity",
    "holm_bonferroni_familywise_alpha_0.05_after_two_protocol_trials",
    "validation_failure_closes_holdout_without_retuning",
)
_HOLDOUT_RULES = (
    "sealed_holdout_consumed_once_only_after_validation_pass",
    "locked_combination_only",
    "positive_primary_3s_90pct_lower_contrast_required",
    "positive_25bps_median_spy_relative_return_required",
)

_POLICY_PAYLOAD = {
    "policy_version": REPLACEMENT_SELECTION_POLICY_VERSION,
    "source_report_sha256": REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256,
    "source_report_fingerprint": REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT,
    "source_policy_fingerprint": DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT,
    "experiment_fingerprint": STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
    "method_fingerprint": STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    "design_evidence": _DESIGN_EVIDENCE,
    "outcome_values_used_in_design": False,
    "parameter_budget": REPLACEMENT_SELECTION_PARAMETER_BUDGET,
    "primary_horizon_sessions": REPLACEMENT_SELECTION_PRIMARY_HORIZON,
    "eligibility_rules": _ELIGIBILITY_RULES,
    "selection_rules": _SELECTION_RULES,
    "robustness_gates": _ROBUSTNESS_GATES,
    "regime_rules": _REGIME_RULES,
    "cost_basis_points_per_side": REPLACEMENT_SELECTION_COST_BPS_PER_SIDE,
    "maximum_session_concentration": (
        REPLACEMENT_SELECTION_MAXIMUM_SESSION_CONCENTRATION
    ),
    "minimum_positive_session_ratio": (
        REPLACEMENT_SELECTION_MINIMUM_POSITIVE_SESSION_RATIO
    ),
    "validation_familywise_alpha": (
        REPLACEMENT_SELECTION_VALIDATION_FAMILYWISE_ALPHA
    ),
    "validation_rules": _VALIDATION_RULES,
    "holdout_rules": _HOLDOUT_RULES,
    "prior_protocol_trials": REPLACEMENT_SELECTION_PRIOR_PROTOCOL_TRIALS,
    "total_protocol_trials": REPLACEMENT_SELECTION_TOTAL_PROTOCOL_TRIALS,
    "replacement_run_budget": REPLACEMENT_SELECTION_RUN_BUDGET,
    "validation_or_holdout_access": False,
    "candidate_or_publication_authority": False,
}
REPLACEMENT_SELECTION_POLICY_FINGERPRINT = hashlib.sha256(
    json.dumps(
        _POLICY_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()


class StrongLeaderPullbackReplacementSelectionProtocolV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal[
        "strong-leader-pullback-reconstructed-replacement-selection/1.0"
    ] = REPLACEMENT_SELECTION_CONTRACT_VERSION
    policy_version: Literal[
        "strong-leader-pullback-reconstructed-replacement-selection-policy/2.0.0"
    ] = REPLACEMENT_SELECTION_POLICY_VERSION
    policy_fingerprint: Literal[REPLACEMENT_SELECTION_POLICY_FINGERPRINT] = (
        REPLACEMENT_SELECTION_POLICY_FINGERPRINT
    )
    source_report_sha256: Literal[REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256] = (
        REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256
    )
    source_report_fingerprint: Literal[
        REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
    ] = REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
    source_policy_fingerprint: Literal[DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT] = (
        DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    method_fingerprint: Literal[STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT] = (
        STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    )
    design_evidence: dict[str, int] = Field(
        default_factory=lambda: dict(_DESIGN_EVIDENCE)
    )
    outcome_values_used_in_design: Literal[False] = False
    parameter_budget: Literal[24] = REPLACEMENT_SELECTION_PARAMETER_BUDGET
    primary_horizon_sessions: Literal[3] = REPLACEMENT_SELECTION_PRIMARY_HORIZON
    eligibility_rules: tuple[str, ...] = _ELIGIBILITY_RULES
    selection_rules: tuple[str, ...] = _SELECTION_RULES
    robustness_gates: tuple[str, ...] = _ROBUSTNESS_GATES
    regime_rules: tuple[str, ...] = _REGIME_RULES
    cost_basis_points_per_side: Literal[25] = REPLACEMENT_SELECTION_COST_BPS_PER_SIDE
    maximum_session_concentration: Literal["0.2000000000"] = (
        REPLACEMENT_SELECTION_MAXIMUM_SESSION_CONCENTRATION
    )
    minimum_positive_session_ratio: Literal["0.5000000000"] = (
        REPLACEMENT_SELECTION_MINIMUM_POSITIVE_SESSION_RATIO
    )
    validation_familywise_alpha: Literal["0.050000"] = (
        REPLACEMENT_SELECTION_VALIDATION_FAMILYWISE_ALPHA
    )
    validation_rules: tuple[str, ...] = _VALIDATION_RULES
    holdout_rules: tuple[str, ...] = _HOLDOUT_RULES
    prior_protocol_trials: Literal[1] = REPLACEMENT_SELECTION_PRIOR_PROTOCOL_TRIALS
    total_protocol_trials: Literal[2] = REPLACEMENT_SELECTION_TOTAL_PROTOCOL_TRIALS
    replacement_run_budget: Literal[1] = REPLACEMENT_SELECTION_RUN_BUDGET
    validation_data_accessed: Literal[False] = False
    holdout_data_accessed: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def protocol_reconciles(
        self,
    ) -> "StrongLeaderPullbackReplacementSelectionProtocolV1":
        if (
            self.design_evidence != _DESIGN_EVIDENCE
            or self.eligibility_rules != _ELIGIBILITY_RULES
            or self.selection_rules != _SELECTION_RULES
            or self.robustness_gates != _ROBUSTNESS_GATES
            or self.regime_rules != _REGIME_RULES
            or self.validation_rules != _VALIDATION_RULES
            or self.holdout_rules != _HOLDOUT_RULES
            or replacement_selection_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("replacement selection protocol differs")
        return self


def strong_leader_pullback_replacement_selection_protocol_v1(
) -> StrongLeaderPullbackReplacementSelectionProtocolV1:
    payload = {
        "design_evidence": dict(_DESIGN_EVIDENCE),
    }
    provisional = StrongLeaderPullbackReplacementSelectionProtocolV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackReplacementSelectionProtocolV1.model_validate(
        {
            **payload,
            "logical_fingerprint": replacement_selection_fingerprint(provisional),
        }
    )


def replacement_selection_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(
            mode="json",
            exclude=exclude or {"logical_fingerprint"},
        )
    else:
        payload = {
            key: item
            for key, item in value.items()
            if key not in (exclude or {"logical_fingerprint"})
        }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
