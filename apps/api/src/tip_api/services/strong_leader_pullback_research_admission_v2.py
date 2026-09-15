"""Outcome-blind research-grade admission for Strong-Leader Pullback.

This module separates a usable, explicitly reconstructed research lane from a
claim that the data were observed as operated.  It never reads outcomes.  A
positive decision requires complete same-session feature cross-sections and a
finite, pre-outcome interval for every non-exact terminal reference.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "strong-leader-pullback-research-admission/2.1"
POLICY_VERSION = "strong-leader-pullback-missingness-policy/1.0"
MINIMUM_COMPLETE_FEATURE_SESSIONS = 252
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ResearchAdmissionV2Status(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_RECONSTRUCTED_DEVELOPMENT = (
        "ready_for_reconstructed_development"
    )


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FeatureSessionExclusionV1(_FrozenModel):
    reason_code: Literal[
        "feature_regime_bootstrap_unavailable",
        "split_evidence_quarantined",
    ]
    session_count: int = Field(ge=1)
    path_count: int = Field(ge=1)


class ReconstructedFeatureEvidenceV1(_FrozenModel):
    diagnostics_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    diagnostics_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    total_session_count: int = Field(ge=MINIMUM_COMPLETE_FEATURE_SESSIONS)
    feature_window_warmup_session_count: int = Field(ge=0)
    rankable_cross_section_session_count: int = Field(ge=0)
    complete_cross_section_session_count: int = Field(ge=0)
    excluded_session_count: int = Field(ge=0)
    expected_path_count: int = Field(ge=1)
    complete_path_count: int = Field(ge=0)
    excluded_path_count: int = Field(ge=0)
    exclusions: tuple[FeatureSessionExclusionV1, ...]
    membership_evidence_tier: Literal[
        "reconstructed_point_in_time_latest_vintage"
    ] = "reconstructed_point_in_time_latest_vintage"
    as_operated: Literal[False] = False
    complete_cross_section_feature_calculation: Literal[True] = True
    coverage_selection_uses_outcomes: Literal[False] = False
    partial_cross_section_ranking_allowed: Literal[False] = False

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "ReconstructedFeatureEvidenceV1":
        reasons = tuple(item.reason_code for item in self.exclusions)
        if reasons != tuple(sorted(set(reasons))):
            raise ValueError("feature exclusion reasons must be unique and sorted")
        if (
            self.feature_window_warmup_session_count
            + self.rankable_cross_section_session_count
            != self.total_session_count
            or self.complete_cross_section_session_count
            + self.excluded_session_count
            != self.rankable_cross_section_session_count
            or self.complete_path_count + self.excluded_path_count
            != self.expected_path_count
            or sum(item.session_count for item in self.exclusions)
            != self.excluded_session_count
            or sum(item.path_count for item in self.exclusions)
            != self.excluded_path_count
        ):
            raise ValueError("feature evidence counts do not reconcile")
        return self


class MechanicalAdjustmentEvidenceV1(_FrozenModel):
    source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_range_naturally_complete: bool
    independent_range_composition_matches: bool
    repeated_economic_rows_match: bool
    source_vintage_frozen: bool
    adjustment_use_only_not_predictor: Literal[True] = True
    known_action_terms_applied_only: Literal[True] = True
    inferred_action_count: Literal[0] = 0
    unresolved_action_hazard_sessions_excluded: bool
    unexplained_price_moves_retained_as_observations: Literal[True] = True
    point_in_time_announcement_clock_claimed: Literal[False] = False


class TerminalReferenceEvidenceV1(_FrozenModel):
    terminal_population_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    crossing_path_count: int = Field(ge=0)
    exact_terminal_reference_path_count: int = Field(ge=0)
    interval_terminal_reference_path_count: int = Field(ge=0)
    unbounded_terminal_reference_path_count: int = Field(ge=0)
    interval_lower_bound_floor: Literal["-1.0000000000"] = "-1.0000000000"
    interval_upper_bounds_required_finite: Literal[True] = True
    missing_reference_point_imputation_allowed: Literal[False] = False
    complete_case_headline_allowed: Literal[False] = False
    adversarial_interval_evaluation_required: Literal[True] = True
    decision_invariance_required: Literal[True] = True
    interval_rules_frozen_before_outcomes: bool

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "TerminalReferenceEvidenceV1":
        if (
            self.exact_terminal_reference_path_count
            + self.interval_terminal_reference_path_count
            + self.unbounded_terminal_reference_path_count
            != self.crossing_path_count
        ):
            raise ValueError("terminal reference path counts do not reconcile")
        return self


class ResearchControlEvidenceV1(_FrozenModel):
    chronological_plan_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    parameter_budget: Literal[24] = 24
    transaction_cost_scenarios_bps_per_side: tuple[
        Literal[0], Literal[10], Literal[25], Literal[50]
    ] = (0, 10, 25, 50)
    development_selection_only: Literal[True] = True
    validation_locked_after_selection: Literal[True] = True
    holdout_sealed_and_unconsumed: bool
    prior_real_outcome_count: Literal[0] = 0
    prior_parameter_selection_count: Literal[0] = 0
    prior_holdout_access_count: Literal[0] = 0


class StrongLeaderPullbackResearchAdmissionV2(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-research-admission/2.1"
    ] = CONTRACT_VERSION
    policy_version: Literal[
        "strong-leader-pullback-missingness-policy/1.0"
    ] = POLICY_VERSION
    status: ResearchAdmissionV2Status
    feature_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    adjustment_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    terminal_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    control_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    minimum_complete_feature_sessions: Literal[252] = 252
    observed_complete_feature_sessions: int = Field(ge=0)
    unresolved_gate_ids: tuple[str, ...]
    reconstructed_not_as_operated_disclosure_required: Literal[True] = True
    exact_and_interval_evidence_reported_separately: Literal[True] = True
    stock_outcomes_never_option_returns: Literal[True] = True
    development_label_construction_authorized: bool
    development_parameter_selection_authorized: bool
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackResearchAdmissionV2":
        if self.unresolved_gate_ids != tuple(sorted(set(self.unresolved_gate_ids))):
            raise ValueError("research admission gates must be unique and sorted")
        ready = (
            self.status
            is ResearchAdmissionV2Status.READY_FOR_RECONSTRUCTED_DEVELOPMENT
        )
        if (
            ready != (not self.unresolved_gate_ids)
            or self.development_label_construction_authorized != ready
            or self.development_parameter_selection_authorized != ready
            or _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
            != self.logical_fingerprint
        ):
            raise ValueError("research admission decision does not reconcile")
        return self


def assess_strong_leader_pullback_research_admission_v2(
    *,
    features: ReconstructedFeatureEvidenceV1,
    adjustments: MechanicalAdjustmentEvidenceV1,
    terminal_references: TerminalReferenceEvidenceV1,
    controls: ResearchControlEvidenceV1,
) -> StrongLeaderPullbackResearchAdmissionV2:
    """Assess research use without reading a return or selecting a parameter."""

    gates: list[str] = []
    if (
        features.complete_cross_section_session_count
        < MINIMUM_COMPLETE_FEATURE_SESSIONS
    ):
        gates.append("minimum_complete_feature_sessions")
    if not all(
        (
            adjustments.source_range_naturally_complete,
            adjustments.independent_range_composition_matches,
            adjustments.repeated_economic_rows_match,
            adjustments.source_vintage_frozen,
            adjustments.unresolved_action_hazard_sessions_excluded,
        )
    ):
        gates.append("mechanical_split_adjustment_evidence")
    if terminal_references.unbounded_terminal_reference_path_count:
        gates.append("finite_terminal_reference_intervals")
    if not terminal_references.interval_rules_frozen_before_outcomes:
        gates.append("preoutcome_terminal_interval_policy")
    if not controls.holdout_sealed_and_unconsumed:
        gates.append("sealed_unconsumed_holdout")
    unresolved = tuple(sorted(gates))
    ready = not unresolved
    values = {
        "status": (
            ResearchAdmissionV2Status.READY_FOR_RECONSTRUCTED_DEVELOPMENT
            if ready
            else ResearchAdmissionV2Status.BLOCKED
        ),
        "feature_evidence_fingerprint": _fingerprint(
            features.model_dump(mode="json")
        ),
        "adjustment_evidence_fingerprint": _fingerprint(
            adjustments.model_dump(mode="json")
        ),
        "terminal_evidence_fingerprint": _fingerprint(
            terminal_references.model_dump(mode="json")
        ),
        "control_evidence_fingerprint": _fingerprint(
            controls.model_dump(mode="json")
        ),
        "observed_complete_feature_sessions": (
            features.complete_cross_section_session_count
        ),
        "unresolved_gate_ids": unresolved,
        "development_label_construction_authorized": ready,
        "development_parameter_selection_authorized": ready,
    }
    provisional = StrongLeaderPullbackResearchAdmissionV2.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackResearchAdmissionV2.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
