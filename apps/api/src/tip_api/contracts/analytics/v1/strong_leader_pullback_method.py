"""Canonical, outcome-blind method projection for Strong-Leader Pullback."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_evaluation import (
    STRATEGY_EVALUATION_POLICY_FINGERPRINT,
    CandidateStrategyEvaluationPolicyV1,
)
from .candidate_strategy_research import (
    STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
    STRONG_STOCK_PULLBACK_RESEARCH_VERSION,
    strong_stock_pullback_research_experiment_v1,
)


STRONG_LEADER_PULLBACK_METHOD_CONTRACT_VERSION = (
    "strong-leader-pullback-method/1.0"
)
STRONG_LEADER_PULLBACK_METHOD_VERSION = "strong-leader-pullback-method/1.0.0"
STRONG_LEADER_PULLBACK_METHOD_ID = "whalpha.strong-leader-pullback"
STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION = (
    "strong-leader-pullback-input-features/1.0.0"
)
STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_STATUS = (
    "ready_for_outcome_blind_method_engineering"
)
STRONG_LEADER_PULLBACK_FORMAL_DATA_GATE_STATUS = "rejected_data_blocked"
STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_LAUNCH_FINGERPRINT = (
    "1abb4ed53d4a4cb5bb6482432db254a0019168aae2712983a9d00aaa4cffef8c"
)
STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT = (
    "ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba"
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


_INPUT_FEATURE_FINGERPRINT_PAYLOAD = {
    "calculation_version": STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION,
    "price_basis": "split_adjusted_to_signal_session",
    "relative_strength": (
        "average_rank_inclusive_percentile_of_stock_20_session_return_"
        "minus_spy_20_session_return_within_complete_point_in_time_primary"
    ),
    "trend_quality": (
        "35pct_close_above_sma10_plus_35pct_sma10_to_sma20_"
        "ratio_normalized_minus_3pct_to_plus_3pct_plus_30pct_"
        "reverse_5_session_max_drawdown_normalized_2pct_to_12pct"
    ),
    "atr": "simple_atr14_true_range",
    "pullback_depth": "prior_20_session_close_high_minus_close_divided_by_atr14",
    "recovery": "close_above_immediately_prior_close_or_high",
    "volume": "signal_session_volume_divided_by_prior_20_session_median_volume",
    "membership": "same_session_signal_eligible_point_in_time_primary",
    "regime": "same_session_primary_confirmed_non_stale_state",
    "future_fields": False,
}
STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT = _fingerprint(
    _INPUT_FEATURE_FINGERPRINT_PAYLOAD
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackMethodFeatureV1(FrozenModel):
    feature_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    requirement_source_family: str
    raw_source_families: tuple[str, ...] = Field(min_length=1)
    source_fields: tuple[str, ...] = Field(min_length=1)
    availability_cutoff: str
    lookback_sessions: int = Field(ge=0, le=504)
    definition_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    exact_formula: str
    transform: str
    unit: str
    expected_direction: str
    missingness_rule: str
    required_for_primary_test: bool

    @model_validator(mode="after")
    def feature_reconciles(self) -> "StrongLeaderPullbackMethodFeatureV1":
        if self.raw_source_families != tuple(
            sorted(set(self.raw_source_families))
        ):
            raise ValueError("method raw source families must be unique and sorted")
        if self.source_fields != tuple(dict.fromkeys(self.source_fields)):
            raise ValueError("method source fields must be unique and ordered")
        return self


class StrongLeaderPullbackMethodParameterV1(FrozenModel):
    parameter_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    canonical_candidate_values: tuple[str, ...] = Field(min_length=2)
    display_candidate_values: tuple[str, ...] = Field(min_length=2)
    selection_scope: Literal["development_only"] = "development_only"
    rationale: str

    @model_validator(mode="after")
    def parameter_reconciles(self) -> "StrongLeaderPullbackMethodParameterV1":
        if (
            len(self.canonical_candidate_values)
            != len(self.display_candidate_values)
            or len(self.canonical_candidate_values)
            != len(set(self.canonical_candidate_values))
            or len(self.display_candidate_values)
            != len(set(self.display_candidate_values))
        ):
            raise ValueError("method parameter values must be paired and unique")
        return self


class StrongLeaderPullbackMethodEvaluationV1(FrozenModel):
    evidence_type: Literal["signal_event_study"] = "signal_event_study"
    split_rule: str
    warmup_sessions: int = Field(ge=0)
    purge_sessions: int = Field(ge=0)
    embargo_sessions: int = Field(ge=0)
    primary_outcome: str
    secondary_outcomes: tuple[str, ...]
    benchmark: str
    control: str
    inference_method: str
    multiplicity_method: str
    search_budget: int = Field(ge=1)
    cost_scenarios_bps_per_side: tuple[int, ...]
    holdout_rule: str
    portfolio_construction_defined: Literal[False] = False


class StrongLeaderPullbackMethodV1(FrozenModel):
    """One canonical method source for calculation, Lab, and later reports."""

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        STRONG_LEADER_PULLBACK_METHOD_CONTRACT_VERSION
    ] = STRONG_LEADER_PULLBACK_METHOD_CONTRACT_VERSION
    method_version: Literal[
        STRONG_LEADER_PULLBACK_METHOD_VERSION
    ] = STRONG_LEADER_PULLBACK_METHOD_VERSION
    method_id: Literal[
        STRONG_LEADER_PULLBACK_METHOD_ID
    ] = STRONG_LEADER_PULLBACK_METHOD_ID
    research_version: Literal[
        STRONG_STOCK_PULLBACK_RESEARCH_VERSION
    ] = STRONG_STOCK_PULLBACK_RESEARCH_VERSION
    source_experiment_id: Literal[
        STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    ] = STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    source_experiment_fingerprint: Literal[
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    ] = STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    evaluation_policy_fingerprint: Literal[
        STRATEGY_EVALUATION_POLICY_FINGERPRINT
    ] = STRATEGY_EVALUATION_POLICY_FINGERPRINT
    input_calculation_version: Literal[
        STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION
    ] = STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION
    input_feature_fingerprint: Literal[
        STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    ] = STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT
    method_engineering_status: Literal[
        STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_STATUS
    ] = STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_STATUS
    formal_data_gate_status: Literal[
        STRONG_LEADER_PULLBACK_FORMAL_DATA_GATE_STATUS
    ] = STRONG_LEADER_PULLBACK_FORMAL_DATA_GATE_STATUS
    method_engineering_launch_fingerprint: Literal[
        STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_LAUNCH_FINGERPRINT
    ] = STRONG_LEADER_PULLBACK_METHOD_ENGINEERING_LAUNCH_FINGERPRINT
    display_name: Literal["Strong-Leader Pullback"] = "Strong-Leader Pullback"
    display_name_zh: Literal["强势股回撤"] = "强势股回撤"
    family: Literal["short_horizon_equity_selection"] = (
        "short_horizon_equity_selection"
    )
    owner: Literal["WH Alpha Personal Quantitative Research"] = (
        "WH Alpha Personal Quantitative Research"
    )
    decision_use: str
    hypothesis: str
    economic_rationale: str
    primary_universe: str
    sensitivity_universes: tuple[str, ...]
    signal_cutoff: Literal["completed_session_close"] = "completed_session_close"
    entry_basis: Literal["next_session_open"] = "next_session_open"
    target_holding_sessions: tuple[Literal[1], Literal[3], Literal[5]] = (1, 3, 5)
    signal_rule: str
    ranking_rule: str
    features: tuple[StrongLeaderPullbackMethodFeatureV1, ...] = Field(min_length=1)
    parameters: tuple[StrongLeaderPullbackMethodParameterV1, ...] = Field(
        min_length=1
    )
    parameter_combination_count: Literal[24] = 24
    evaluation: StrongLeaderPullbackMethodEvaluationV1
    decision_gate_disclosures: tuple[str, ...] = Field(min_length=1)
    primary_strength: str
    primary_weakness: str
    counterevidence_requirements: tuple[str, ...] = Field(min_length=1)
    invalidation_conditions: tuple[str, ...] = Field(min_length=1)
    contains_forward_outcomes: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    formal_development_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    performance_claims_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    logical_fingerprint: Literal[STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT] = (
        STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    )

    @model_validator(mode="after")
    def method_reconciles(self) -> "StrongLeaderPullbackMethodV1":
        experiment = strong_stock_pullback_research_experiment_v1()
        policy = CandidateStrategyEvaluationPolicyV1()
        feature_by_id = {item.feature_id: item for item in experiment.feature_requirements}
        parameter_by_id = {item.parameter_id: item for item in experiment.parameter_grid}
        if tuple(item.feature_id for item in self.features) != tuple(feature_by_id):
            raise ValueError("method features differ from the frozen experiment order")
        if tuple(item.parameter_id for item in self.parameters) != tuple(parameter_by_id):
            raise ValueError("method parameters differ from the frozen experiment order")
        for item in self.features:
            requirement = feature_by_id[item.feature_id]
            if (
                item.role != requirement.role.value
                or item.requirement_source_family != requirement.source_family
                or item.lookback_sessions != requirement.minimum_lookback_sessions
                or item.definition_code != requirement.definition_code
                or item.required_for_primary_test
                != requirement.required_for_primary_test
            ):
                raise ValueError("method feature differs from frozen requirement metadata")
        for item in self.parameters:
            dimension = parameter_by_id[item.parameter_id]
            if (
                item.canonical_candidate_values != dimension.candidate_values
                or item.selection_scope != dimension.selection_split
            ):
                raise ValueError("method parameter differs from frozen experiment grid")
        if (
            self.source_experiment_id != experiment.experiment_id
            or self.source_experiment_fingerprint != experiment.logical_fingerprint
            or self.evaluation_policy_fingerprint != policy.policy_fingerprint
            or self.target_holding_sessions != experiment.target_holding_sessions
            or self.entry_basis != experiment.entry_basis
            or self.parameter_combination_count
            != experiment.parameter_combination_count
            or self.evaluation.search_budget != experiment.parameter_combination_count
            or self.evaluation.warmup_sessions != 20
            or self.evaluation.purge_sessions != policy.maximum_label_horizon_sessions
            or self.evaluation.embargo_sessions != policy.embargo_sessions
            or self.evaluation.cost_scenarios_bps_per_side
            != policy.transaction_cost_scenarios_bps_per_side
            or _fingerprint(_INPUT_FEATURE_FINGERPRINT_PAYLOAD)
            != self.input_feature_fingerprint
        ):
            raise ValueError("method does not reconcile with registered research policy")
        if strong_leader_pullback_method_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Strong-Leader Pullback method fingerprint mismatch")
        return self


def strong_leader_pullback_method_v1() -> StrongLeaderPullbackMethodV1:
    """Build the canonical method without data access or outcome fields."""

    payload: dict[str, object] = {
        "decision_use": "Prioritize review of prior leaders after an orderly reset.",
        "hypothesis": (
            "An orderly pullback followed by close-based recovery in a prior "
            "leader improves its next 1-, 3-, and 5-session stock outcome."
        ),
        "economic_rationale": (
            "A controlled reset may reduce extension risk while preserving "
            "persistent relative demand; the same-session leader control tests "
            "whether the setup adds information beyond leadership alone."
        ),
        "primary_universe": "same_session_point_in_time_primary",
        "sensitivity_universes": ("same_session_point_in_time_secondary",),
        "signal_cutoff": "completed_session_close",
        "entry_basis": "next_session_open",
        "target_holding_sessions": (1, 3, 5),
        "signal_rule": (
            "leadership_gate AND pullback_depth_atr_band AND "
            "volume_contraction_ratio_max AND recovery_trigger"
        ),
        "ranking_rule": (
            "No Product rank is authorized; the primary study compares triggered "
            "leaders with eligible non-trigger leaders by session."
        ),
        "features": _method_features(),
        "parameters": _method_parameters(),
        "parameter_combination_count": 24,
        "evaluation": {
            "evidence_type": "signal_event_study",
            "split_rule": (
                "chronological_50pct_development_25pct_validation_"
                "25pct_sealed_holdout"
            ),
            "warmup_sessions": 20,
            "purge_sessions": 5,
            "embargo_sessions": 5,
            "primary_outcome": (
                "three_session_underlying_stock_return_from_next_open"
            ),
            "secondary_outcomes": (
                "one_session_underlying_stock_return_from_next_open",
                "five_session_underlying_stock_return_from_next_open",
            ),
            "benchmark": "same_horizon_spy_price_return",
            "control": "same_session_eligible_leader_non_signal_control",
            "inference_method": "session_balanced_block_bootstrap_2000_replicates",
            "multiplicity_method": "holm_bonferroni_familywise",
            "search_budget": 24,
            "cost_scenarios_bps_per_side": (0, 10, 25, 50),
            "holdout_rule": "single_use_after_validation_gates_pass",
            "portfolio_construction_defined": False,
        },
        "decision_gate_disclosures": (
            "All 24 registered combinations have complete validation coverage.",
            "Holm-adjusted one-sided family-wise p-value is at most 0.10.",
            "Median three-session SPY-relative return is positive after 25 bps "
            "per side in validation and holdout.",
            "Every separately reported Regime has at least 60 signal observations.",
            "The sealed-holdout 90% interval lower bound for the primary "
            "leader-control contrast is above zero.",
        ),
        "primary_strength": (
            "Directly tests whether pullback timing adds value beyond prior leadership."
        ),
        "primary_weakness": (
            "Complete performance-grade point-in-time evidence and a real "
            "evaluation do not yet exist."
        ),
        "counterevidence_requirements": (
            "effect_concentrated_in_few_sessions_or_industries",
            "next_open_gap_erases_close_signal_effect",
            "setup_adds_no_value_over_eligible_leader_control",
            "signal_deteriorates_after_realistic_costs",
        ),
        "invalidation_conditions": (
            "registered_validation_gate_failure",
            "sealed_holdout_gate_failure",
            "prospective_decay_beyond_monitoring_limit",
            "source_or_feature_semantics_change_without_new_version",
        ),
        "contains_forward_outcomes": False,
        "parameter_selection_authorized": False,
        "formal_development_authorized": False,
        "validation_authorized": False,
        "holdout_access_authorized": False,
        "performance_claims_authorized": False,
        "candidate_activation_authorized": False,
    }
    typed_payload = {
        **payload,
        "features": tuple(
            StrongLeaderPullbackMethodFeatureV1.model_validate(item)
            for item in payload["features"]
        ),
        "parameters": tuple(
            StrongLeaderPullbackMethodParameterV1.model_validate(item)
            for item in payload["parameters"]
        ),
        "evaluation": StrongLeaderPullbackMethodEvaluationV1.model_validate(
            payload["evaluation"]
        ),
    }
    provisional = StrongLeaderPullbackMethodV1.model_construct(
        **typed_payload,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackMethodV1.model_validate(
        {
            **payload,
            "logical_fingerprint": strong_leader_pullback_method_fingerprint(
                provisional
            ),
        }
    )


def _method_features() -> tuple[dict[str, object], ...]:
    adjusted_sources = (
        "historical-eod-price-bars-v1",
        "historical-research-adjustment-ledger-v1",
    )
    reject = "reject_complete_cross_section"
    return (
        {
            "feature_id": "adjusted_ohlcv_panel",
            "role": "population",
            "requirement_source_family": "historical-research-adjustment-ledger-v1",
            "raw_source_families": adjusted_sources,
            "source_fields": ("open", "high", "low", "close", "volume"),
            "availability_cutoff": "strictly_before_modeled_next_open",
            "lookback_sessions": 20,
            "definition_code": "split_reconciled_raw_price_volume_panel",
            "exact_formula": (
                "Every member and SPY has 21 contiguous bars multiplied by "
                "clear split price/volume factors on the signal-session basis."
            ),
            "transform": "split_adjust_to_signal_session",
            "unit": "usd_and_shares",
            "expected_direction": "not_applicable_population_gate",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
        {
            "feature_id": "atr_pullback_depth",
            "role": "setup",
            "requirement_source_family": "candidate-entry-geometry-v1",
            "raw_source_families": adjusted_sources,
            "source_fields": ("high", "low", "close"),
            "availability_cutoff": "completed_session_close",
            "lookback_sessions": 20,
            "definition_code": "distance_from_prior_20s_high_in_atr_units",
            "exact_formula": (
                "(max(close[t-20:t-1]) - close[t]) / "
                "mean(latest_14_true_ranges)"
            ),
            "transform": "none",
            "unit": "atr",
            "expected_direction": "inside_preregistered_positive_band",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
        {
            "feature_id": "daily_primary_membership",
            "role": "population",
            "requirement_source_family": "historical-universe-membership-v1.1",
            "raw_source_families": ("historical-universe-membership-v1.1",),
            "source_fields": (
                "instrument_id",
                "session_date",
                "decision",
                "knowledge_time",
            ),
            "availability_cutoff": "signal_session_knowledge_time",
            "lookback_sessions": 0,
            "definition_code": "same_session_point_in_time_primary_decision",
            "exact_formula": (
                "Include only same-session signal-eligible Primary decisions "
                "keyed by stable instrument_id."
            ),
            "transform": "none",
            "unit": "boolean",
            "expected_direction": "required_true",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
        {
            "feature_id": "market_regime_state",
            "role": "stratification",
            "requirement_source_family": "market-regime-state-v1.0.1",
            "raw_source_families": ("market-regime-state-v1.0.1",),
            "source_fields": ("state", "availability", "transition_status"),
            "availability_cutoff": "completed_session_close",
            "lookback_sessions": 20,
            "definition_code": "same_session_market_regime_state",
            "exact_formula": (
                "Use the same-session confirmed non-stale Primary state without "
                "merging Risk-on, Balanced, Defensive, or Stress."
            ),
            "transform": "categorical_stratification_only",
            "unit": "state",
            "expected_direction": "not_preregistered_as_signal",
            "missingness_rule": "do_not_report_regime_cell",
            "required_for_primary_test": False,
        },
        {
            "feature_id": "recovery_trigger",
            "role": "trigger",
            "requirement_source_family": "historical-eod-price-bars-v1",
            "raw_source_families": adjusted_sources,
            "source_fields": ("close", "high"),
            "availability_cutoff": "completed_session_close",
            "lookback_sessions": 2,
            "definition_code": "close_based_recovery_after_pullback",
            "exact_formula": (
                "close[t] > close[t-1], or close[t] > high[t-1], according "
                "to the selected registered branch."
            ),
            "transform": "boolean",
            "unit": "boolean",
            "expected_direction": "true",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
        {
            "feature_id": "relative_leadership_20s",
            "role": "leadership",
            "requirement_source_family": "opportunity-candidate-v1.1.1",
            "raw_source_families": adjusted_sources,
            "source_fields": ("close", "spy_close", "instrument_id"),
            "availability_cutoff": "completed_session_close",
            "lookback_sessions": 20,
            "definition_code": "stock_relative_spy_and_universe_strength",
            "exact_formula": (
                "average-rank inclusive percentile of (stock 20-session return "
                "- SPY 20-session return) across the complete point-in-time "
                "Primary cross-section; stable-ID tie order; all ties=0.5000"
            ),
            "transform": "cross_sectional_inclusive_percentile",
            "unit": "percentile_0_to_1",
            "expected_direction": "higher",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
        {
            "feature_id": "trend_quality",
            "role": "leadership",
            "requirement_source_family": "opportunity-candidate-v1.1.1",
            "raw_source_families": adjusted_sources,
            "source_fields": ("close",),
            "availability_cutoff": "completed_session_close",
            "lookback_sessions": 20,
            "definition_code": "sma_structure_slope_and_drawdown_quality",
            "exact_formula": (
                "0.35*(close>SMA10) + "
                "0.35*clip_norm(SMA10/SMA20-1,-3%,+3%) + "
                "0.30*reverse_clip_norm(abs(max_drawdown_5s),2%,12%)"
            ),
            "transform": "weighted_score_0_to_100",
            "unit": "score_0_to_100",
            "expected_direction": "higher",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
        {
            "feature_id": "volume_contraction",
            "role": "risk",
            "requirement_source_family": "historical-eod-price-bars-v1",
            "raw_source_families": adjusted_sources,
            "source_fields": ("volume",),
            "availability_cutoff": "completed_session_close",
            "lookback_sessions": 20,
            "definition_code": "pullback_volume_to_prior_20s_median_ratio",
            "exact_formula": (
                "volume[t] / median(volume[t-20:t-1]) after split adjustment"
            ),
            "transform": "ratio",
            "unit": "multiple",
            "expected_direction": "lower_or_equal_to_selected_cap",
            "missingness_rule": reject,
            "required_for_primary_test": True,
        },
    )


def _method_parameters() -> tuple[dict[str, object], ...]:
    return (
        {
            "parameter_id": "leadership_gate",
            "canonical_candidate_values": (
                "rs20_percentile_gte_0.80_and_trend_quality_gte_70",
                "rs20_percentile_gte_0.90_and_trend_quality_gte_75",
            ),
            "display_candidate_values": (
                "rs20_percentile>=0.80 AND trend_quality>=70",
                "rs20_percentile>=0.90 AND trend_quality>=75",
            ),
            "selection_scope": "development_only",
            "rationale": "Compare two bounded definitions of an established leader.",
        },
        {
            "parameter_id": "pullback_depth_atr_band",
            "canonical_candidate_values": (
                "0.50_to_1.50",
                "0.75_to_2.00",
                "1.00_to_2.50",
            ),
            "display_candidate_values": (
                "0.50..1.50",
                "0.75..2.00",
                "1.00..2.50",
            ),
            "selection_scope": "development_only",
            "rationale": (
                "Test shallow through moderate resets without an unbounded "
                "threshold search."
            ),
        },
        {
            "parameter_id": "recovery_trigger",
            "canonical_candidate_values": (
                "close_above_prior_close",
                "close_above_prior_high",
            ),
            "display_candidate_values": (
                "close>prior_close",
                "close>prior_high",
            ),
            "selection_scope": "development_only",
            "rationale": "Compare weak and strict close-confirmed recovery.",
        },
        {
            "parameter_id": "volume_contraction_ratio_max",
            "canonical_candidate_values": ("0.80", "1.00"),
            "display_candidate_values": ("0.80", "1.00"),
            "selection_scope": "development_only",
            "rationale": (
                "Test whether a quieter pullback contributes beyond price geometry."
            ),
        },
    )


def strong_leader_pullback_method_fingerprint(
    value: BaseModel | dict[str, object],
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    else:
        payload = dict(value)
        payload.pop("logical_fingerprint", None)
    return _fingerprint(payload)
