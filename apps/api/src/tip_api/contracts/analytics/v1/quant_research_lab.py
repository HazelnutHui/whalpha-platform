"""Transparent Lab model records and fail-closed research publications."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_evaluation import STRATEGY_EVALUATION_POLICY_FINGERPRINT
from .candidate_strategy_research import (
    PERSONAL_MODEL_DISCLOSURE_VERSION,
    STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
    STRONG_STOCK_PULLBACK_RESEARCH_VERSION,
    StrategyResearchStage,
)
from .candidate_strategy_research_input import (
    STRONG_LEADER_PULLBACK_INPUT_CALCULATION_VERSION,
    STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
)


LAB_MODEL_RECORD_CONTRACT_VERSION = "quant-research-lab-model-record/1.0"
LAB_RESULT_PUBLICATION_CONTRACT_VERSION = "quant-research-lab-result/1.0"
LAB_MODEL_CATALOG_CONTRACT_VERSION = "quant-research-lab-catalog/1.0"
STRONG_LEADER_PULLBACK_MODEL_ID = "whalpha.strong-leader-pullback"
MAXIMUM_ACTIVE_CANDIDATE_MODELS = 3


class ResearchEvidenceScope(StrEnum):
    METHOD_ONLY = "method_only"
    FIXTURE_ONLY = "fixture_only"
    SIGNAL_EVENT_STUDY = "signal_event_study"
    PORTFOLIO_SIMULATION = "portfolio_simulation"


class ResearchApplicabilityState(StrEnum):
    NOT_ASSESSED = "not_assessed"
    SUPPORTED = "supported"
    MIXED = "mixed"
    UNSUPPORTED = "unsupported"


class ResearchMetricId(StrEnum):
    SIGNAL_COUNT = "signal_count"
    CONTROL_COUNT = "control_count"
    COMPARABLE_SESSION_COUNT = "comparable_session_count"
    NET_EXPECTANCY = "net_expectancy"
    MEDIAN_OUTCOME = "median_outcome"
    SIGNAL_CONTROL_CONTRAST = "signal_control_contrast"
    WIN_RATE = "win_rate"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    PAYOFF_RATIO = "payoff_ratio"
    PROFIT_FACTOR = "profit_factor"
    MAXIMUM_FAVORABLE_EXCURSION = "maximum_favorable_excursion"
    MAXIMUM_ADVERSE_EXCURSION = "maximum_adverse_excursion"
    CHASE_RATE = "chase_rate"
    COVERAGE_RATE = "coverage_rate"
    QUARANTINE_RATE = "quarantine_rate"
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    VOLATILITY = "volatility"
    BETA = "beta"
    ALPHA = "alpha"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    INFORMATION_RATIO = "information_ratio"
    TURNOVER = "turnover"
    EXPOSURE = "exposure"
    CAPACITY = "capacity"
    COST_ATTRIBUTION = "cost_attribution"
    WORST_PERIOD = "worst_period"


class ResearchMetricSplit(StrEnum):
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    HOLDOUT = "holdout"
    PROSPECTIVE_SHADOW = "prospective_shadow"
    FIXTURE = "fixture"


class ResearchMetricUnit(StrEnum):
    COUNT = "count"
    RETURN = "return"
    RATIO = "ratio"
    BASIS_POINTS = "basis_points"
    USD = "usd"
    SHARES = "shares"
    SESSIONS = "sessions"


PORTFOLIO_ONLY_METRICS = frozenset(
    {
        ResearchMetricId.TOTAL_RETURN,
        ResearchMetricId.ANNUALIZED_RETURN,
        ResearchMetricId.MAXIMUM_DRAWDOWN,
        ResearchMetricId.VOLATILITY,
        ResearchMetricId.BETA,
        ResearchMetricId.ALPHA,
        ResearchMetricId.SHARPE_RATIO,
        ResearchMetricId.SORTINO_RATIO,
        ResearchMetricId.CALMAR_RATIO,
        ResearchMetricId.INFORMATION_RATIO,
        ResearchMetricId.TURNOVER,
        ResearchMetricId.EXPOSURE,
        ResearchMetricId.CAPACITY,
        ResearchMetricId.COST_ATTRIBUTION,
        ResearchMetricId.WORST_PERIOD,
    }
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LabFeatureDisclosureV1(FrozenModel):
    feature_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    source_family: str
    source_fields: tuple[str, ...] = Field(min_length=1)
    availability_cutoff: str
    lookback_sessions: int = Field(ge=0, le=5040)
    exact_formula: str
    transform: str
    unit: str
    expected_direction: str
    missingness_rule: str


class LabParameterDisclosureV1(FrozenModel):
    parameter_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    candidate_values: tuple[str, ...] = Field(min_length=1)
    selection_scope: str
    rationale: str

    @model_validator(mode="after")
    def candidates_are_unique(self) -> "LabParameterDisclosureV1":
        if len(self.candidate_values) != len(set(self.candidate_values)):
            raise ValueError("Lab parameter candidates must be unique")
        return self


class LabEvaluationDesignV1(FrozenModel):
    evidence_type: Literal[ResearchEvidenceScope.SIGNAL_EVENT_STUDY] = (
        ResearchEvidenceScope.SIGNAL_EVENT_STUDY
    )
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

    @model_validator(mode="after")
    def design_reconciles(self) -> "LabEvaluationDesignV1":
        if self.cost_scenarios_bps_per_side != tuple(
            sorted(set(self.cost_scenarios_bps_per_side))
        ):
            raise ValueError("Lab cost scenarios must be unique and sorted")
        return self


class QuantResearchLabModelRecordV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[LAB_MODEL_RECORD_CONTRACT_VERSION] = (
        LAB_MODEL_RECORD_CONTRACT_VERSION
    )
    model_id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    model_version: str
    display_name: str
    display_name_zh: str
    family: str
    owner: str
    ownership_notice_code: str
    disclosure_version: str
    registered_on: date
    lifecycle_state: StrategyResearchStage
    evidence_scope: ResearchEvidenceScope
    candidate_eligible: bool
    candidate_activation_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    applicability_state: ResearchApplicabilityState
    applicability_reason: str
    last_validation_date: date | None
    next_required_decision: str
    out_of_sample_scope: str
    out_of_sample_observation_count: int = Field(ge=0)
    decision_use: str
    hypothesis: str
    economic_rationale: str
    primary_universe: str
    sensitivity_universes: tuple[str, ...]
    signal_cutoff: str
    entry_basis: str
    target_holding_sessions: tuple[int, ...]
    underlying_stock_result_not_option_return: Literal[True] = True
    signal_rule: str
    ranking_rule: str
    feature_disclosures: tuple[LabFeatureDisclosureV1, ...] = Field(min_length=1)
    parameter_disclosures: tuple[LabParameterDisclosureV1, ...] = Field(min_length=1)
    evaluation_design: LabEvaluationDesignV1
    decision_gates: tuple[str, ...] = Field(min_length=1)
    primary_strength: str
    primary_weakness: str
    counterevidence_requirements: tuple[str, ...] = Field(min_length=1)
    invalidation_conditions: tuple[str, ...] = Field(min_length=1)
    blocker_codes: tuple[str, ...]
    risk_disclosure_codes: tuple[str, ...] = Field(min_length=1)
    source_experiment_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_experiment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_feature_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    implementation_revision_reason: str
    result_publication_id: str | None = None
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def record_reconciles(self) -> "QuantResearchLabModelRecordV1":
        for label, values in (
            ("feature", tuple(item.feature_id for item in self.feature_disclosures)),
            ("parameter", tuple(item.parameter_id for item in self.parameter_disclosures)),
            ("blocker", self.blocker_codes),
            ("risk disclosure", self.risk_disclosure_codes),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Lab model {label} values must be unique")
        if self.lifecycle_state is StrategyResearchStage.ACTIVE:
            if not self.candidate_eligible or self.candidate_activation_fingerprint is None:
                raise ValueError("active Lab model requires separate Candidate activation")
        elif self.candidate_eligible or self.candidate_activation_fingerprint is not None:
            raise ValueError("non-active Lab model cannot claim Candidate eligibility")
        if self.lifecycle_state in {
            StrategyResearchStage.VALIDATED_RESEARCH,
            StrategyResearchStage.SHADOW,
            StrategyResearchStage.ACTIVE,
        } and self.evidence_scope not in {
            ResearchEvidenceScope.SIGNAL_EVENT_STUDY,
            ResearchEvidenceScope.PORTFOLIO_SIMULATION,
        }:
            raise ValueError("advanced Lab lifecycle requires real evaluated evidence")
        if self.lifecycle_state is StrategyResearchStage.PREREGISTERED_DATA_BLOCKED:
            if not self.blocker_codes:
                raise ValueError("data-blocked Lab model must disclose blockers")
        elif self.blocker_codes:
            raise ValueError("unblocked Lab lifecycle cannot retain blockers")
        if self.evidence_scope is ResearchEvidenceScope.METHOD_ONLY:
            if (
                self.result_publication_id is not None
                or self.last_validation_date is not None
                or self.out_of_sample_observation_count != 0
            ):
                raise ValueError("method-only Lab model cannot claim evaluated evidence")
        elif (
            self.result_publication_id is None
            or self.last_validation_date is None
            or self.out_of_sample_observation_count == 0
        ):
            raise ValueError("evaluated Lab model requires a bound result publication")
        if lab_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Lab model record fingerprint mismatch")
        return self


class LabResearchMetricV1(FrozenModel):
    metric_id: ResearchMetricId
    value: str
    unit: ResearchMetricUnit
    split: ResearchMetricSplit
    horizon_sessions: int | None = Field(default=None, ge=1)
    slice_code: str = "all"
    sample_count: int = Field(ge=0)
    net_of_costs: bool
    benchmark: str | None = None
    uncertainty_lower: str | None = None
    uncertainty_upper: str | None = None

    @model_validator(mode="after")
    def metric_reconciles(self) -> "LabResearchMetricV1":
        for label, value in (
            ("value", self.value),
            ("uncertainty lower", self.uncertainty_lower),
            ("uncertainty upper", self.uncertainty_upper),
        ):
            if value is None:
                continue
            try:
                parsed = Decimal(value)
            except (InvalidOperation, ValueError) as exc:
                raise ValueError(f"Lab metric {label} must be numeric") from exc
            if not parsed.is_finite():
                raise ValueError(f"Lab metric {label} must be finite")
        if (self.uncertainty_lower is None) != (self.uncertainty_upper is None):
            raise ValueError("Lab metric uncertainty bounds must be paired")
        if (
            self.uncertainty_lower is not None
            and Decimal(self.uncertainty_lower) > Decimal(self.uncertainty_upper)
        ):
            raise ValueError("Lab metric uncertainty bounds are reversed")
        return self


class QuantResearchLabResultPublicationV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[LAB_RESULT_PUBLICATION_CONTRACT_VERSION] = (
        LAB_RESULT_PUBLICATION_CONTRACT_VERSION
    )
    publication_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._:@-]*$")
    model_id: str
    model_record_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_scope: ResearchEvidenceScope
    fixture_only: bool
    performance_claims_authorized: bool
    candidate_authority_granted: Literal[False] = False
    period_start: date | None = None
    period_end: date | None = None
    source_dataset_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    portfolio_construction_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    metrics: tuple[LabResearchMetricV1, ...]
    supporting_evidence: tuple[str, ...]
    counterevidence: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def publication_reconciles(self) -> "QuantResearchLabResultPublicationV1":
        metric_keys = tuple(
            (item.metric_id, item.split, item.horizon_sessions, item.slice_code)
            for item in self.metrics
        )
        if len(metric_keys) != len(set(metric_keys)):
            raise ValueError("Lab result metric split/horizon/slice keys must be unique")
        if self.evidence_scope is ResearchEvidenceScope.METHOD_ONLY:
            if (
                self.fixture_only
                or self.performance_claims_authorized
                or self.period_start is not None
                or self.period_end is not None
                or self.source_dataset_fingerprint is not None
                or self.portfolio_construction_fingerprint is not None
                or self.metrics
            ):
                raise ValueError("method-only publication cannot carry results")
        elif self.evidence_scope is ResearchEvidenceScope.FIXTURE_ONLY:
            if not self.fixture_only or self.performance_claims_authorized:
                raise ValueError("fixture publication cannot authorize performance claims")
        else:
            if self.fixture_only or not self.performance_claims_authorized:
                raise ValueError("real research result requires explicit performance authority")
            if (
                self.period_start is None
                or self.period_end is None
                or self.period_start > self.period_end
                or self.source_dataset_fingerprint is None
                or not self.metrics
            ):
                raise ValueError("real research result requires period, source, and metrics")
            if not self.counterevidence or not self.limitation_codes:
                raise ValueError(
                    "real research result must disclose counterevidence and limitations"
                )
        if self.evidence_scope is ResearchEvidenceScope.SIGNAL_EVENT_STUDY:
            if PORTFOLIO_ONLY_METRICS.intersection(item.metric_id for item in self.metrics):
                raise ValueError("event study cannot carry portfolio-only metrics")
            if self.portfolio_construction_fingerprint is not None:
                raise ValueError("event study cannot bind portfolio construction")
        if self.evidence_scope is ResearchEvidenceScope.PORTFOLIO_SIMULATION:
            if self.portfolio_construction_fingerprint is None:
                raise ValueError("portfolio result requires frozen portfolio construction")
        if lab_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Lab result publication fingerprint mismatch")
        return self


class QuantResearchLabCatalogV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[LAB_MODEL_CATALOG_CONTRACT_VERSION] = (
        LAB_MODEL_CATALOG_CONTRACT_VERSION
    )
    featured_model_id: str
    models: tuple[QuantResearchLabModelRecordV1, ...] = Field(min_length=1)
    active_candidate_model_ids: tuple[str, ...] = Field(
        max_length=MAXIMUM_ACTIVE_CANDIDATE_MODELS
    )
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def catalog_reconciles(self) -> "QuantResearchLabCatalogV1":
        model_by_id = {item.model_id: item for item in self.models}
        if len(model_by_id) != len(self.models):
            raise ValueError("Lab catalog model IDs must be unique")
        if self.featured_model_id not in model_by_id:
            raise ValueError("Lab catalog featured model is absent")
        if len(self.active_candidate_model_ids) != len(
            set(self.active_candidate_model_ids)
        ):
            raise ValueError("Lab catalog active model IDs must be unique")
        for model_id in self.active_candidate_model_ids:
            model = model_by_id.get(model_id)
            if (
                model is None
                or model.lifecycle_state is not StrategyResearchStage.ACTIVE
                or not model.candidate_eligible
                or model.candidate_activation_fingerprint is None
            ):
                raise ValueError("Lab catalog active model lacks reviewed activation")
        if lab_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Lab catalog fingerprint mismatch")
        return self


def strong_leader_pullback_lab_model_record_v1() -> QuantResearchLabModelRecordV1:
    """Project the frozen preregistration into a transparent method record."""

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": LAB_MODEL_RECORD_CONTRACT_VERSION,
        "model_id": STRONG_LEADER_PULLBACK_MODEL_ID,
        "model_version": STRONG_STOCK_PULLBACK_RESEARCH_VERSION,
        "display_name": "Strong-Leader Pullback",
        "display_name_zh": "强势股回撤",
        "family": "short_horizon_equity_selection",
        "owner": "WH Alpha Personal Quantitative Research",
        "ownership_notice_code": "personal_research_model_owned_by_wh_alpha",
        "disclosure_version": PERSONAL_MODEL_DISCLOSURE_VERSION,
        "registered_on": date(2026, 8, 30),
        "lifecycle_state": StrategyResearchStage.PREREGISTERED_DATA_BLOCKED,
        "evidence_scope": ResearchEvidenceScope.METHOD_ONLY,
        "candidate_eligible": False,
        "candidate_activation_fingerprint": None,
        "applicability_state": ResearchApplicabilityState.NOT_ASSESSED,
        "applicability_reason": "No real validation or prospective evidence exists.",
        "last_validation_date": None,
        "next_required_decision": (
            "Close the exact mandatory data families, then issue a separate "
            "development-readiness review."
        ),
        "out_of_sample_scope": "none_no_real_evaluation",
        "out_of_sample_observation_count": 0,
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
        "underlying_stock_result_not_option_return": True,
        "signal_rule": (
            "leadership_gate AND pullback_depth_atr_band AND "
            "volume_contraction_ratio_max AND recovery_trigger"
        ),
        "ranking_rule": (
            "No Product rank is authorized; the primary study compares triggered "
            "leaders with eligible non-trigger leaders by session."
        ),
        "feature_disclosures": (
            {
                "feature_id": "adjusted_ohlcv_panel",
                "role": "population",
                "source_family": "historical-research-adjustment-ledger-v1",
                "source_fields": ("open", "high", "low", "close", "volume"),
                "availability_cutoff": "strictly_before_modeled_next_open",
                "lookback_sessions": 20,
                "exact_formula": (
                    "Every member and SPY has 21 contiguous split-adjusted bars "
                    "on the signal-session basis."
                ),
                "transform": "split_adjust_to_signal_session",
                "unit": "usd_and_shares",
                "expected_direction": "not_applicable_population_gate",
                "missingness_rule": "reject_complete_cross_section",
            },
            {
                "feature_id": "atr_pullback_depth",
                "role": "setup",
                "source_family": "historical-eod-price-bars-v1",
                "source_fields": ("high", "low", "close"),
                "availability_cutoff": "completed_session_close",
                "lookback_sessions": 20,
                "exact_formula": "(max(close[t-20:t-1]) - close[t]) / mean(latest_14_true_ranges)",
                "transform": "none",
                "unit": "atr",
                "expected_direction": "inside_preregistered_positive_band",
                "missingness_rule": "reject_complete_cross_section",
            },
            {
                "feature_id": "daily_primary_membership",
                "role": "population",
                "source_family": "historical-universe-membership-v1.1",
                "source_fields": ("instrument_id", "session_date", "decision", "knowledge_time"),
                "availability_cutoff": "signal_session_knowledge_time",
                "lookback_sessions": 0,
                "exact_formula": (
                    "Include only same-session signal-eligible Primary decisions "
                    "keyed by stable instrument_id."
                ),
                "transform": "none",
                "unit": "boolean",
                "expected_direction": "required_true",
                "missingness_rule": "reject_complete_cross_section",
            },
            {
                "feature_id": "market_regime_state",
                "role": "stratification",
                "source_family": "market-regime-state-v1.0.1",
                "source_fields": ("state", "availability", "transition_status"),
                "availability_cutoff": "completed_session_close",
                "lookback_sessions": 20,
                "exact_formula": (
                    "Use the same-session confirmed non-stale Primary state without "
                    "merging Risk-on, Balanced, Defensive, or Stress."
                ),
                "transform": "categorical_stratification_only",
                "unit": "state",
                "expected_direction": "not_preregistered_as_signal",
                "missingness_rule": "do_not_report_regime_cell",
            },
            {
                "feature_id": "recovery_trigger",
                "role": "trigger",
                "source_family": "historical-eod-price-bars-v1",
                "source_fields": ("close", "high"),
                "availability_cutoff": "completed_session_close",
                "lookback_sessions": 2,
                "exact_formula": (
                    "close[t] > close[t-1], or close[t] > high[t-1], according "
                    "to the selected registered branch."
                ),
                "transform": "boolean",
                "unit": "boolean",
                "expected_direction": "true",
                "missingness_rule": "reject_complete_cross_section",
            },
            {
                "feature_id": "relative_leadership_20s",
                "role": "leadership",
                "source_family": "historical-eod-price-bars-v1",
                "source_fields": ("close", "spy_close", "instrument_id"),
                "availability_cutoff": "completed_session_close",
                "lookback_sessions": 20,
                "exact_formula": (
                    "average-rank inclusive percentile of (stock 20-session "
                    "return - SPY 20-session return) across the complete "
                    "point-in-time Primary cross-section; stable-ID tie order; "
                    "all ties=0.5000"
                ),
                "transform": "cross_sectional_inclusive_percentile",
                "unit": "percentile_0_to_1",
                "expected_direction": "higher",
                "missingness_rule": "reject_complete_cross_section",
            },
            {
                "feature_id": "trend_quality",
                "role": "leadership",
                "source_family": "historical-eod-price-bars-v1",
                "source_fields": ("close",),
                "availability_cutoff": "completed_session_close",
                "lookback_sessions": 20,
                "exact_formula": (
                    "0.35*(close>SMA10) + "
                    "0.35*clip_norm(SMA10/SMA20-1,-3%,+3%) + "
                    "0.30*reverse_clip_norm(abs(max_drawdown_5s),2%,12%)"
                ),
                "transform": "weighted_score_0_to_100",
                "unit": "score_0_to_100",
                "expected_direction": "higher",
                "missingness_rule": "reject_complete_cross_section",
            },
            {
                "feature_id": "volume_contraction",
                "role": "risk",
                "source_family": "historical-eod-price-bars-v1",
                "source_fields": ("volume",),
                "availability_cutoff": "completed_session_close",
                "lookback_sessions": 20,
                "exact_formula": "volume[t] / median(volume[t-20:t-1]) after split adjustment",
                "transform": "ratio",
                "unit": "multiple",
                "expected_direction": "lower_or_equal_to_selected_cap",
                "missingness_rule": "reject_complete_cross_section",
            },
        ),
        "parameter_disclosures": (
            {
                "parameter_id": "leadership_gate",
                "candidate_values": (
                    "rs20_percentile>=0.80 AND trend_quality>=70",
                    "rs20_percentile>=0.90 AND trend_quality>=75",
                ),
                "selection_scope": "development_only",
                "rationale": "Compare two bounded definitions of an established leader.",
            },
            {
                "parameter_id": "pullback_depth_atr_band",
                "candidate_values": ("0.50..1.50", "0.75..2.00", "1.00..2.50"),
                "selection_scope": "development_only",
                "rationale": (
                    "Test shallow through moderate resets without an unbounded "
                    "threshold search."
                ),
            },
            {
                "parameter_id": "recovery_trigger",
                "candidate_values": ("close>prior_close", "close>prior_high"),
                "selection_scope": "development_only",
                "rationale": "Compare weak and strict close-confirmed recovery.",
            },
            {
                "parameter_id": "volume_contraction_ratio_max",
                "candidate_values": ("0.80", "1.00"),
                "selection_scope": "development_only",
                "rationale": "Test whether a quieter pullback contributes beyond price geometry.",
            },
        ),
        "evaluation_design": {
            "evidence_type": ResearchEvidenceScope.SIGNAL_EVENT_STUDY,
            "split_rule": "chronological_50pct_development_25pct_validation_25pct_sealed_holdout",
            "warmup_sessions": 20,
            "purge_sessions": 5,
            "embargo_sessions": 5,
            "primary_outcome": "three_session_underlying_stock_return_from_next_open",
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
        "decision_gates": (
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
            "Complete point-in-time history and a real evaluation do not yet exist."
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
        "blocker_codes": (
            "historical_point_in_time_membership_incomplete",
            "instrument_lifecycle_terminal_coverage_incomplete",
            "corporate_action_availability_and_revision_coverage_incomplete",
            "adjustment_neutrality_and_total_return_semantics_incomplete",
            "final_transitive_historical_coverage_absent",
            "observed_execution_cost_calibration_absent",
            "real_chronological_dataset_and_sealed_holdout_absent",
        ),
        "risk_disclosure_codes": (
            "historical_performance_does_not_predict_future_results",
            "market_regime_change_can_weaken_or_invalidate_parameters",
            "personal_research_model_not_independent_investment_advice",
            "research_priority_output_not_trade_instruction",
            "stock_outcome_cannot_be_presented_as_option_return",
        ),
        "source_experiment_id": STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
        "source_experiment_fingerprint": STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
        "input_feature_fingerprint": STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
        "evaluation_policy_fingerprint": STRATEGY_EVALUATION_POLICY_FINGERPRINT,
        "implementation_revision": None,
        "implementation_revision_reason": "No real dataset execution or result publication exists.",
        "result_publication_id": None,
    }
    payload["logical_fingerprint"] = lab_fingerprint(payload)
    return QuantResearchLabModelRecordV1.model_validate(payload)


def strong_leader_pullback_lab_catalog_v1() -> QuantResearchLabCatalogV1:
    record = strong_leader_pullback_lab_model_record_v1()
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": LAB_MODEL_CATALOG_CONTRACT_VERSION,
        "featured_model_id": record.model_id,
        "models": (record.model_dump(mode="json"),),
        "active_candidate_model_ids": (),
    }
    payload["logical_fingerprint"] = lab_fingerprint(payload)
    return QuantResearchLabCatalogV1.model_validate(payload)


def lab_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(
            mode="json",
            exclude=(exclude or set()) | {"logical_fingerprint"},
        )
    else:
        payload = dict(value)
        for key in (exclude or set()) | {"logical_fingerprint"}:
            payload.pop(key, None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
