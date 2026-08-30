"""Immutable preregistration contract for personal Candidate strategy research."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from math import prod
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_channel import StrategyChannel
from .candidate_strategy_evaluation import (
    STRATEGY_EVALUATION_POLICY_FINGERPRINT,
)


STRATEGY_RESEARCH_EXPERIMENT_CONTRACT_VERSION = (
    "candidate-strategy-research-experiment/1.0"
)
STRONG_STOCK_PULLBACK_RESEARCH_VERSION = "strong-stock-pullback-research/1.0"
PERSONAL_MODEL_DISCLOSURE_VERSION = "whalpha-personal-model-disclosure/1.0"
MAXIMUM_PREREGISTERED_PARAMETER_COMBINATIONS = 24
STRONG_STOCK_PULLBACK_EXPERIMENT_ID = (
    "3ab7175302bbcfb6894233d1db05534aa69bbab83935fa5d31dc9a916002b5d0"
)
STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT = (
    "afc9b38f435484996e614f956b541c20f71b2506f7cff6252042af4da7211a41"
)


class StrategyResearchStage(StrEnum):
    PREREGISTERED_DATA_BLOCKED = "preregistered_data_blocked"
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    HOLDOUT_REVIEW = "holdout_review"
    VALIDATED_RESEARCH = "validated_research"
    REJECTED = "rejected"
    RETIRED = "retired"


class ResearchFeatureRole(StrEnum):
    POPULATION = "population"
    LEADERSHIP = "leadership"
    SETUP = "setup"
    TRIGGER = "trigger"
    RISK = "risk"
    STRATIFICATION = "stratification"


class ResearchGateRule(StrEnum):
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrategyResearchFeatureRequirementV1(FrozenModel):
    feature_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    role: ResearchFeatureRole
    source_family: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    minimum_lookback_sessions: int = Field(ge=0, le=504)
    point_in_time_required: Literal[True] = True
    required_for_primary_test: bool
    definition_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")


class StrategyResearchParameterDimensionV1(FrozenModel):
    parameter_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    candidate_values: tuple[str, ...] = Field(min_length=2, max_length=4)
    selection_split: Literal["development_only"] = "development_only"
    ordered_values: Literal[True] = True

    @model_validator(mode="after")
    def dimension_reconciles(self) -> "StrategyResearchParameterDimensionV1":
        if len(self.candidate_values) != len(set(self.candidate_values)):
            raise ValueError("research parameter candidates must be unique")
        if any(not value or value != value.strip() for value in self.candidate_values):
            raise ValueError("research parameter candidates must be non-empty normalized strings")
        return self


class StrategyResearchDecisionGateV1(FrozenModel):
    gate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    metric_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    split_scope: tuple[Literal["validation", "holdout"], ...] = Field(min_length=1)
    rule: ResearchGateRule
    threshold: str
    comparison_basis: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    multiplicity_adjustment: Literal[
        "not_applicable",
        "holm_bonferroni_fwer",
    ]

    @model_validator(mode="after")
    def gate_reconciles(self) -> "StrategyResearchDecisionGateV1":
        if self.split_scope != tuple(dict.fromkeys(self.split_scope)):
            raise ValueError("research gate split scope must be unique and ordered")
        try:
            threshold = Decimal(self.threshold)
        except InvalidOperation as exc:
            raise ValueError("research gate threshold must be numeric") from exc
        if not threshold.is_finite():
            raise ValueError("research gate threshold must be finite")
        return self


class CandidateStrategyResearchExperimentV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_RESEARCH_EXPERIMENT_CONTRACT_VERSION] = (
        STRATEGY_RESEARCH_EXPERIMENT_CONTRACT_VERSION
    )
    research_version: Literal[STRONG_STOCK_PULLBACK_RESEARCH_VERSION] = (
        STRONG_STOCK_PULLBACK_RESEARCH_VERSION
    )
    experiment_id: Literal[STRONG_STOCK_PULLBACK_EXPERIMENT_ID] = (
        STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    )
    logical_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    registered_on: date
    stage: StrategyResearchStage
    channel: Literal[StrategyChannel.STRONG_STOCK_PULLBACK] = (
        StrategyChannel.STRONG_STOCK_PULLBACK
    )
    model_owner_label: Literal["WH Alpha Personal Quantitative Research"] = (
        "WH Alpha Personal Quantitative Research"
    )
    ownership_notice_code: Literal["personal_research_model_owned_by_wh_alpha"] = (
        "personal_research_model_owned_by_wh_alpha"
    )
    disclosure_version: Literal[PERSONAL_MODEL_DISCLOSURE_VERSION] = (
        PERSONAL_MODEL_DISCLOSURE_VERSION
    )
    research_only: Literal[True] = True
    not_trading_recommendation: Literal[True] = True
    model_may_decay_or_fail: Literal[True] = True
    performance_claims_prohibited_until_separate_activation: Literal[True] = True
    underlying_stock_result_not_option_return: Literal[True] = True
    hypothesis_code: Literal[
        "orderly_pullback_in_prior_leader_improves_short_horizon_outcome"
    ] = "orderly_pullback_in_prior_leader_improves_short_horizon_outcome"
    primary_universe_id: Literal["primary"] = "primary"
    sensitivity_universe_ids: tuple[Literal["secondary"], ...] = ("secondary",)
    signal_cutoff: Literal["session_close"] = "session_close"
    entry_basis: Literal["next_session_open"] = "next_session_open"
    target_holding_sessions: tuple[Literal[1], Literal[3], Literal[5]] = (1, 3, 5)
    primary_horizon_sessions: Literal[3] = 3
    primary_benchmark: Literal["spy_price_return"] = "spy_price_return"
    primary_contrast: Literal[
        "same_session_point_in_time_eligible_leader_non_signal_control"
    ] = "same_session_point_in_time_eligible_leader_non_signal_control"
    evaluation_policy_fingerprint: Literal[STRATEGY_EVALUATION_POLICY_FINGERPRINT] = (
        STRATEGY_EVALUATION_POLICY_FINGERPRINT
    )
    minimum_research_history_sessions: Literal[252] = 252
    preferred_research_history_sessions: Literal[504] = 504
    random_split_prohibited: Literal[True] = True
    overlap_purge_and_embargo_required: Literal[True] = True
    development_selection_then_lock: Literal[True] = True
    untouched_holdout_required: Literal[True] = True
    feature_requirements: tuple[StrategyResearchFeatureRequirementV1, ...] = Field(
        min_length=1
    )
    parameter_grid: tuple[StrategyResearchParameterDimensionV1, ...] = Field(
        min_length=1
    )
    parameter_combination_count: int = Field(ge=1)
    decision_gates: tuple[StrategyResearchDecisionGateV1, ...] = Field(min_length=1)
    activation_blocker_codes: tuple[str, ...]
    risk_disclosure_codes: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def experiment_reconciles(self) -> "CandidateStrategyResearchExperimentV1":
        feature_ids = tuple(item.feature_id for item in self.feature_requirements)
        parameter_ids = tuple(item.parameter_id for item in self.parameter_grid)
        gate_ids = tuple(item.gate_id for item in self.decision_gates)
        for label, values in (
            ("feature", feature_ids),
            ("parameter", parameter_ids),
            ("gate", gate_ids),
        ):
            if values != tuple(sorted(set(values))):
                raise ValueError(f"research {label} IDs must be unique and sorted")
        for label, values in (
            ("sensitivity Universe", self.sensitivity_universe_ids),
            ("activation blocker", self.activation_blocker_codes),
            ("risk disclosure", self.risk_disclosure_codes),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"research {label} values must be unique")
        expected_combinations = prod(
            len(dimension.candidate_values) for dimension in self.parameter_grid
        )
        if (
            self.parameter_combination_count != expected_combinations
            or expected_combinations > MAXIMUM_PREREGISTERED_PARAMETER_COMBINATIONS
        ):
            raise ValueError("research parameter grid exceeds its preregistered bound")
        if self.stage is StrategyResearchStage.PREREGISTERED_DATA_BLOCKED:
            if not self.activation_blocker_codes:
                raise ValueError("data-blocked research must name its activation blockers")
        elif self.activation_blocker_codes:
            raise ValueError("active research stages cannot retain unresolved activation blockers")
        if self.experiment_id != strategy_research_experiment_id(
            research_version=self.research_version,
            registered_on=self.registered_on,
            evaluation_policy_fingerprint=self.evaluation_policy_fingerprint,
        ):
            raise ValueError("strategy research experiment ID mismatch")
        if strategy_research_fingerprint(
            self,
            exclude={"logical_fingerprint"},
        ) != self.logical_fingerprint:
            raise ValueError("strategy research logical fingerprint mismatch")
        return self


def strategy_research_experiment_id(
    *,
    research_version: str,
    registered_on: date,
    evaluation_policy_fingerprint: str,
) -> str:
    return _fingerprint(
        {
            "research_version": research_version,
            "registered_on": registered_on.isoformat(),
            "evaluation_policy_fingerprint": evaluation_policy_fingerprint,
        }
    )


def strategy_research_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude=exclude or set())
    else:
        payload = dict(value)
        for key in exclude or set():
            payload.pop(key, None)
    return _fingerprint(payload)


def strong_stock_pullback_research_experiment_v1() -> CandidateStrategyResearchExperimentV1:
    """Return the first frozen research registration; it performs no evaluation."""

    registered_on = date(2026, 8, 30)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": STRATEGY_RESEARCH_EXPERIMENT_CONTRACT_VERSION,
        "research_version": STRONG_STOCK_PULLBACK_RESEARCH_VERSION,
        "registered_on": registered_on,
        "stage": StrategyResearchStage.PREREGISTERED_DATA_BLOCKED,
        "channel": StrategyChannel.STRONG_STOCK_PULLBACK,
        "model_owner_label": "WH Alpha Personal Quantitative Research",
        "ownership_notice_code": "personal_research_model_owned_by_wh_alpha",
        "disclosure_version": PERSONAL_MODEL_DISCLOSURE_VERSION,
        "research_only": True,
        "not_trading_recommendation": True,
        "model_may_decay_or_fail": True,
        "performance_claims_prohibited_until_separate_activation": True,
        "underlying_stock_result_not_option_return": True,
        "hypothesis_code": (
            "orderly_pullback_in_prior_leader_improves_short_horizon_outcome"
        ),
        "primary_universe_id": "primary",
        "sensitivity_universe_ids": ("secondary",),
        "signal_cutoff": "session_close",
        "entry_basis": "next_session_open",
        "target_holding_sessions": (1, 3, 5),
        "primary_horizon_sessions": 3,
        "primary_benchmark": "spy_price_return",
        "primary_contrast": (
            "same_session_point_in_time_eligible_leader_non_signal_control"
        ),
        "evaluation_policy_fingerprint": STRATEGY_EVALUATION_POLICY_FINGERPRINT,
        "minimum_research_history_sessions": 252,
        "preferred_research_history_sessions": 504,
        "random_split_prohibited": True,
        "overlap_purge_and_embargo_required": True,
        "development_selection_then_lock": True,
        "untouched_holdout_required": True,
        "experiment_id": strategy_research_experiment_id(
            research_version=STRONG_STOCK_PULLBACK_RESEARCH_VERSION,
            registered_on=registered_on,
            evaluation_policy_fingerprint=STRATEGY_EVALUATION_POLICY_FINGERPRINT,
        ),
        "feature_requirements": (
            {
                "feature_id": "adjusted_ohlcv_panel",
                "role": "population",
                "source_family": "historical-research-adjustment-ledger-v1",
                "minimum_lookback_sessions": 252,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "split_reconciled_raw_price_volume_panel",
            },
            {
                "feature_id": "atr_pullback_depth",
                "role": "setup",
                "source_family": "candidate-entry-geometry-v1",
                "minimum_lookback_sessions": 20,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "distance_from_prior_20s_high_in_atr_units",
            },
            {
                "feature_id": "daily_primary_membership",
                "role": "population",
                "source_family": "historical-universe-membership-v1.1",
                "minimum_lookback_sessions": 0,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "same_session_point_in_time_primary_decision",
            },
            {
                "feature_id": "market_regime_state",
                "role": "stratification",
                "source_family": "market-regime-state-v1.0.1",
                "minimum_lookback_sessions": 20,
                "point_in_time_required": True,
                "required_for_primary_test": False,
                "definition_code": "same_session_market_regime_state",
            },
            {
                "feature_id": "recovery_trigger",
                "role": "trigger",
                "source_family": "historical-eod-price-bars-v1",
                "minimum_lookback_sessions": 2,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "close_based_recovery_after_pullback",
            },
            {
                "feature_id": "relative_leadership_20s",
                "role": "leadership",
                "source_family": "opportunity-candidate-v1.1.1",
                "minimum_lookback_sessions": 20,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "stock_relative_spy_and_universe_strength",
            },
            {
                "feature_id": "trend_quality",
                "role": "leadership",
                "source_family": "opportunity-candidate-v1.1.1",
                "minimum_lookback_sessions": 20,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "sma_structure_slope_and_drawdown_quality",
            },
            {
                "feature_id": "volume_contraction",
                "role": "risk",
                "source_family": "historical-eod-price-bars-v1",
                "minimum_lookback_sessions": 20,
                "point_in_time_required": True,
                "required_for_primary_test": True,
                "definition_code": "pullback_volume_to_prior_20s_median_ratio",
            },
        ),
        "parameter_grid": (
            {
                "parameter_id": "leadership_gate",
                "candidate_values": (
                    "rs20_percentile_gte_0.80_and_trend_quality_gte_70",
                    "rs20_percentile_gte_0.90_and_trend_quality_gte_75",
                ),
                "selection_split": "development_only",
                "ordered_values": True,
            },
            {
                "parameter_id": "pullback_depth_atr_band",
                "candidate_values": ("0.50_to_1.50", "0.75_to_2.00", "1.00_to_2.50"),
                "selection_split": "development_only",
                "ordered_values": True,
            },
            {
                "parameter_id": "recovery_trigger",
                "candidate_values": ("close_above_prior_close", "close_above_prior_high"),
                "selection_split": "development_only",
                "ordered_values": True,
            },
            {
                "parameter_id": "volume_contraction_ratio_max",
                "candidate_values": ("0.80", "1.00"),
                "selection_split": "development_only",
                "ordered_values": True,
            },
        ),
        "parameter_combination_count": 24,
        "decision_gates": (
            {
                "gate_id": "familywise_adjusted_parameter_evidence",
                "metric_id": "block_bootstrap_holm_adjusted_p_value",
                "split_scope": ("validation",),
                "rule": "less_than_or_equal",
                "threshold": "0.10",
                "comparison_basis": "finite_preregistered_parameter_grid",
                "multiplicity_adjustment": "holm_bonferroni_fwer",
            },
            {
                "gate_id": "holdout_primary_contrast_positive",
                "metric_id": "block_bootstrap_lower_90pct_primary_3s_contrast",
                "split_scope": ("holdout",),
                "rule": "greater_than",
                "threshold": "0.0000",
                "comparison_basis": "eligible_leader_non_signal_control",
                "multiplicity_adjustment": "not_applicable",
            },
            {
                "gate_id": "net_primary_median_positive",
                "metric_id": "median_3s_spy_relative_return_net_25bps_per_side",
                "split_scope": ("validation", "holdout"),
                "rule": "greater_than",
                "threshold": "0.0000",
                "comparison_basis": "spy_price_return",
                "multiplicity_adjustment": "not_applicable",
            },
            {
                "gate_id": "regime_observation_floor",
                "metric_id": "reported_observations_per_regime",
                "split_scope": ("validation", "holdout"),
                "rule": "greater_than_or_equal",
                "threshold": "60",
                "comparison_basis": "each_reported_market_regime",
                "multiplicity_adjustment": "not_applicable",
            },
        ),
        "activation_blocker_codes": (
            "canonical_252_session_history_absent",
            "daily_point_in_time_membership_absent",
            "corporate_action_coverage_absent",
            "instrument_lifecycle_coverage_absent",
            "adjustment_ledger_not_research_ready",
        ),
        "risk_disclosure_codes": (
            "historical_performance_does_not_predict_future_results",
            "market_regime_change_can_weaken_or_invalidate_parameters",
            "personal_research_model_not_independent_investment_advice",
            "research_priority_output_not_trade_instruction",
            "stock_outcome_cannot_be_presented_as_option_return",
        ),
    }
    payload["logical_fingerprint"] = strategy_research_fingerprint(payload)
    return CandidateStrategyResearchExperimentV1.model_validate(payload)


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
