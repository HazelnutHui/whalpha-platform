"""Frozen coverage-corrected selection protocol for Strong-Leader Pullback."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
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
REPLACEMENT_SELECTION_OUTPUT_DIRECTORY = "report=20260915-v1"
REPLACEMENT_SELECTION_GATE_IDS = (
    "positive_adverse_lower_90pct",
    "positive_25bps_median_spy_relative",
    "positive_first_half_contrast",
    "positive_second_half_contrast",
    "positive_paired_session_majority",
    "bounded_single_session_concentration",
)
_RETURN_PATTERN = r"^-?(?:0|[1-9][0-9]*)\.[0-9]{10}$"

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


class ReplacementSelectionStatus(StrEnum):
    LOCKED = "locked"
    BLOCKED_SOURCE_EVIDENCE = "blocked_source_evidence"
    REJECTED_NO_COMMON_ELIGIBLE = "rejected_no_common_eligible"
    REJECTED_ENDPOINT_INSTABILITY = "rejected_endpoint_instability"
    REJECTED_ROBUSTNESS_GATES = "rejected_robustness_gates"


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


class ReplacementParameterEligibilityV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parameter_combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible_in_all_endpoint_scenarios: bool
    eligible_endpoint_scenarios: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def eligibility_reconciles(self) -> "ReplacementParameterEligibilityV1":
        expected = tuple(sorted(set(self.eligible_endpoint_scenarios)))
        if (
            self.eligible_endpoint_scenarios != expected
            or any(
                item not in ("all_lower", "all_upper", "contrast_adverse")
                for item in expected
            )
            or self.eligible_in_all_endpoint_scenarios != (len(expected) == 3)
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("replacement parameter eligibility differs")
        return self


class ReplacementSelectionGateV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: Literal[
        "positive_adverse_lower_90pct",
        "positive_25bps_median_spy_relative",
        "positive_first_half_contrast",
        "positive_second_half_contrast",
        "positive_paired_session_majority",
        "bounded_single_session_concentration",
    ]
    observed_value: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    comparison: Literal["strictly_greater_than", "less_than_or_equal_to"]
    threshold: str = Field(pattern=_RETURN_PATTERN)
    passed: bool

    @model_validator(mode="after")
    def gate_reconciles(self) -> "ReplacementSelectionGateV1":
        threshold = Decimal(self.threshold)
        expected = False
        if self.observed_value is not None:
            observed = Decimal(self.observed_value)
            expected = (
                observed > threshold
                if self.comparison == "strictly_greater_than"
                else observed <= threshold
            )
        if self.passed != expected:
            raise ValueError("replacement selection gate differs")
        return self


class StrongLeaderPullbackReplacementParameterLockV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parameter_combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_development_report_fingerprint: Literal[
        REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
    ] = REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
    replacement_policy_fingerprint: Literal[
        REPLACEMENT_SELECTION_POLICY_FINGERPRINT
    ] = REPLACEMENT_SELECTION_POLICY_FINGERPRINT
    endpoint_winner_ids: dict[str, str]
    gate_results_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_before_validation: Literal[True] = True
    validation_cannot_change_parameters: Literal[True] = True
    holdout_cannot_change_parameters: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def lock_reconciles(
        self,
    ) -> "StrongLeaderPullbackReplacementParameterLockV1":
        if (
            tuple(sorted(self.endpoint_winner_ids))
            != ("all_lower", "all_upper", "contrast_adverse")
            or set(self.endpoint_winner_ids.values())
            != {self.parameter_combination_id}
            or replacement_selection_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("replacement parameter lock differs")
        return self


class StrongLeaderPullbackReplacementSelectionReportV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal[
        "strong-leader-pullback-reconstructed-replacement-selection-result/1.0"
    ] = "strong-leader-pullback-reconstructed-replacement-selection-result/1.0"
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    created_at: datetime
    protocol_fingerprint: Literal[REPLACEMENT_SELECTION_POLICY_FINGERPRINT] = (
        REPLACEMENT_SELECTION_POLICY_FINGERPRINT
    )
    protocol_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_report_sha256: Literal[REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256] = (
        REPLACEMENT_SELECTION_SOURCE_REPORT_SHA256
    )
    source_report_fingerprint: Literal[
        REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
    ] = REPLACEMENT_SELECTION_SOURCE_REPORT_FINGERPRINT
    source_selection_status: Literal["inconclusive_evidence_floor"] = (
        "inconclusive_evidence_floor"
    )
    source_summary_count: Literal[216] = 216
    parameter_combination_count: Literal[24] = 24
    eligibility: tuple[ReplacementParameterEligibilityV1, ...]
    common_eligible_parameter_count: int = Field(ge=0, le=24)
    endpoint_winner_ids: dict[str, str | None]
    provisional_winner_id: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    gate_results: tuple[ReplacementSelectionGateV1, ...]
    selection_status: ReplacementSelectionStatus
    selected_parameter_combination_id: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    parameter_lock: StrongLeaderPullbackReplacementParameterLockV1 | None
    prior_protocol_trials: Literal[1] = 1
    total_protocol_trials: Literal[2] = 2
    replacement_run_count: Literal[1] = 1
    reconstructed_latest_vintage: Literal[True] = True
    as_operated: Literal[False] = False
    development_only: Literal[True] = True
    validation_data_accessed: Literal[False] = False
    holdout_data_accessed: Literal[False] = False
    validation_transition_authorized: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    network_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackReplacementSelectionReportV1":
        ids = tuple(item.parameter_combination_id for item in self.eligibility)
        endpoint_values = tuple(self.endpoint_winner_ids.values())
        stable_winner = (
            endpoint_values[0]
            if endpoint_values
            and endpoint_values[0] is not None
            and len(set(endpoint_values)) == 1
            else None
        )
        locked = self.selection_status is ReplacementSelectionStatus.LOCKED
        all_gates_pass = bool(self.gate_results) and all(
            item.passed for item in self.gate_results
        )
        source_evidence_blocked = any(
            reason.endswith(":unavailable_source_evidence")
            for item in self.eligibility
            for reason in item.reason_codes
        )
        if source_evidence_blocked:
            expected_status = ReplacementSelectionStatus.BLOCKED_SOURCE_EVIDENCE
            expected_reasons = (
                "primary_family_contains_unavailable_source_evidence",
            )
        elif self.common_eligible_parameter_count == 0:
            expected_status = ReplacementSelectionStatus.REJECTED_NO_COMMON_ELIGIBLE
            expected_reasons = (
                "no_parameter_is_eligible_in_every_endpoint_scenario",
            )
        elif stable_winner is None:
            expected_status = ReplacementSelectionStatus.REJECTED_ENDPOINT_INSTABILITY
            expected_reasons = (
                "endpoint_scenarios_select_different_parameters",
            )
        elif all_gates_pass:
            expected_status = ReplacementSelectionStatus.LOCKED
            expected_reasons = (
                "parameter_locked_formal_validation_review_required",
            )
        else:
            expected_status = ReplacementSelectionStatus.REJECTED_ROBUSTNESS_GATES
            expected_reasons = tuple(
                sorted(
                    f"failed_{item.gate_id}"
                    for item in self.gate_results
                    if not item.passed
                )
            )
        expected_gate_fingerprint = replacement_selection_fingerprint(
            {
                "gate_results": [
                    item.model_dump(mode="json") for item in self.gate_results
                ]
            },
            exclude=set(),
        )
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or len(ids) != 24
            or ids != tuple(sorted(set(ids)))
            or self.common_eligible_parameter_count
            != sum(item.eligible_in_all_endpoint_scenarios for item in self.eligibility)
            or tuple(sorted(self.endpoint_winner_ids))
            != ("all_lower", "all_upper", "contrast_adverse")
            or self.provisional_winner_id != stable_winner
            or bool(self.gate_results) != (stable_winner is not None)
            or (
                self.gate_results
                and tuple(item.gate_id for item in self.gate_results)
                != REPLACEMENT_SELECTION_GATE_IDS
            )
            or locked != all_gates_pass
            or locked != (self.selected_parameter_combination_id is not None)
            or locked != (self.parameter_lock is not None)
            or self.selection_status is not expected_status
            or self.reason_codes != expected_reasons
            or (
                locked
                and self.selected_parameter_combination_id
                != self.provisional_winner_id
            )
            or (
                self.parameter_lock is not None
                and (
                    self.parameter_lock.parameter_combination_id
                    != self.selected_parameter_combination_id
                    or self.parameter_lock.endpoint_winner_ids
                    != self.endpoint_winner_ids
                    or self.parameter_lock.gate_results_fingerprint
                    != expected_gate_fingerprint
                )
            )
            or replacement_selection_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("replacement selection report differs")
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
