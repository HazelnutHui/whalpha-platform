"""Transparent Lab model records and fail-closed research publications."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_research import (
    PERSONAL_MODEL_DISCLOSURE_VERSION,
    StrategyResearchStage,
)
from .strong_leader_pullback_method import (
    STRONG_LEADER_PULLBACK_METHOD_ID,
    strong_leader_pullback_method_v1,
)


LAB_MODEL_RECORD_CONTRACT_VERSION = "quant-research-lab-model-record/1.2"
LAB_RESULT_PUBLICATION_CONTRACT_VERSION = "quant-research-lab-result/1.0"
LAB_MODEL_CATALOG_CONTRACT_VERSION = "quant-research-lab-catalog/1.0"
STRONG_LEADER_PULLBACK_MODEL_ID = STRONG_LEADER_PULLBACK_METHOD_ID
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
    requirement_source_family: str
    raw_source_families: tuple[str, ...] = Field(min_length=1)
    source_fields: tuple[str, ...] = Field(min_length=1)
    availability_cutoff: str
    lookback_sessions: int = Field(ge=0, le=5040)
    exact_formula: str
    transform: str
    unit: str
    expected_direction: str
    missingness_rule: str

    @model_validator(mode="after")
    def sources_are_unique_and_sorted(self) -> "LabFeatureDisclosureV1":
        if self.raw_source_families != tuple(
            sorted(set(self.raw_source_families))
        ):
            raise ValueError("Lab raw source families must be unique and sorted")
        return self


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


class LabMethodEngineeringEvidenceV1(FrozenModel):
    status: Literal["replayed_reconstructed_proxy"] = (
        "replayed_reconstructed_proxy"
    )
    report_contract_version: Literal[
        "strong-leader-pullback-method-diagnostics/1.1"
    ] = "strong-leader-pullback-method-diagnostics/1.1"
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    method_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_feature_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_session: date
    last_session: date
    session_count: int = Field(ge=1)
    complete_feature_session_count: int = Field(ge=0)
    expected_path_count: int = Field(ge=1)
    complete_observation_count: int = Field(ge=0)
    excluded_path_count: int = Field(ge=0)
    complete_observation_rate: str
    known_split_adjustment_applied_path_count: int = Field(ge=0)
    price_feature_basis: Literal[
        "sparse_known_split_adjustment_proxy_with_unproven_neutral_rows"
    ]
    market_regime_basis: Literal[
        "recomputed_reconstructed_same_session_proxy"
    ]
    observed_regime_states: tuple[str, ...]
    unobserved_regime_states: tuple[str, ...]
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    as_operated: Literal[False] = False
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "LabMethodEngineeringEvidenceV1":
        with localcontext() as context:
            context.prec = 50
            expected_rate = (
                Decimal(self.complete_observation_count)
                / Decimal(self.expected_path_count)
            ).quantize(Decimal("0.0001"))
        if (
            self.first_session > self.last_session
            or self.complete_feature_session_count > self.session_count
            or self.expected_path_count
            != self.complete_observation_count + self.excluded_path_count
            or self.known_split_adjustment_applied_path_count
            > self.complete_observation_count
            or self.complete_observation_rate != format(expected_rate, "f")
            or self.observed_regime_states
            != tuple(sorted(set(self.observed_regime_states)))
            or self.unobserved_regime_states
            != tuple(sorted(set(self.unobserved_regime_states)))
            or set(self.observed_regime_states) & set(self.unobserved_regime_states)
            or set(self.observed_regime_states) | set(self.unobserved_regime_states)
            != {"Balanced", "Defensive", "Risk-on", "Stress"}
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
        ):
            raise ValueError("Lab method-engineering evidence differs")
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
    method_engineering_evidence: LabMethodEngineeringEvidenceV1 | None = None
    decision_gates: tuple[str, ...] = Field(min_length=1)
    primary_strength: str
    primary_weakness: str
    counterevidence_requirements: tuple[str, ...] = Field(min_length=1)
    invalidation_conditions: tuple[str, ...] = Field(min_length=1)
    blocker_codes: tuple[str, ...]
    risk_disclosure_codes: tuple[str, ...] = Field(min_length=1)
    source_method_contract_version: str = Field(
        pattern=r"^[a-z0-9][a-z0-9.-]*/[0-9]+\.[0-9]+$"
    )
    source_method_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
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
        if self.method_engineering_evidence is not None and (
            self.method_engineering_evidence.method_fingerprint
            != self.source_method_fingerprint
            or self.method_engineering_evidence.input_feature_fingerprint
            != self.input_feature_fingerprint
            or self.implementation_revision is None
            or self.method_engineering_evidence.implementation_revision
            != self.implementation_revision
        ):
            raise ValueError("Lab method-engineering evidence binding differs")
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
    """Project the canonical method into a transparent, outcome-free Lab record."""

    method = strong_leader_pullback_method_v1()
    feature_disclosures = tuple(
        {
            "feature_id": feature.feature_id,
            "role": feature.role,
            "requirement_source_family": feature.requirement_source_family,
            "raw_source_families": feature.raw_source_families,
            "source_fields": feature.source_fields,
            "availability_cutoff": feature.availability_cutoff,
            "lookback_sessions": feature.lookback_sessions,
            "exact_formula": feature.exact_formula,
            "transform": feature.transform,
            "unit": feature.unit,
            "expected_direction": feature.expected_direction,
            "missingness_rule": feature.missingness_rule,
        }
        for feature in method.features
    )
    parameter_disclosures = tuple(
        {
            "parameter_id": parameter.parameter_id,
            "candidate_values": parameter.display_candidate_values,
            "selection_scope": parameter.selection_scope,
            "rationale": parameter.rationale,
        }
        for parameter in method.parameters
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": LAB_MODEL_RECORD_CONTRACT_VERSION,
        "model_id": method.method_id,
        "model_version": method.method_version,
        "display_name": method.display_name,
        "display_name_zh": method.display_name_zh,
        "family": method.family,
        "owner": method.owner,
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
            "Complete and review the outcome-blind signal implementation; open "
            "real outcomes only after a separate formal data admission."
        ),
        "out_of_sample_scope": "none_no_real_evaluation",
        "out_of_sample_observation_count": 0,
        "decision_use": method.decision_use,
        "hypothesis": method.hypothesis,
        "economic_rationale": method.economic_rationale,
        "primary_universe": method.primary_universe,
        "sensitivity_universes": method.sensitivity_universes,
        "signal_cutoff": method.signal_cutoff,
        "entry_basis": method.entry_basis,
        "target_holding_sessions": method.target_holding_sessions,
        "underlying_stock_result_not_option_return": True,
        "signal_rule": method.signal_rule,
        "ranking_rule": method.ranking_rule,
        "feature_disclosures": feature_disclosures,
        "parameter_disclosures": parameter_disclosures,
        "evaluation_design": method.evaluation.model_dump(mode="json"),
        "method_engineering_evidence": {
            "status": "replayed_reconstructed_proxy",
            "report_contract_version": (
                "strong-leader-pullback-method-diagnostics/1.1"
            ),
            "report_sha256": (
                "8bcd602c64c7a1ab403a9c97bea21c8edb1758b60d46f879cf23b4bf7c015b36"
            ),
            "report_logical_fingerprint": (
                "c082566f283516b9a93d5658832450fb85071a3b59892cb8d922c1f37af34bd8"
            ),
            "implementation_revision": (
                "9879f2e890840487c90a89078eb31f0cbff273c0"
            ),
            "method_fingerprint": method.logical_fingerprint,
            "input_feature_fingerprint": method.input_feature_fingerprint,
            "first_session": date(2025, 6, 23),
            "last_session": date(2026, 8, 12),
            "session_count": 287,
            "complete_feature_session_count": 254,
            "expected_path_count": 437_402,
            "complete_observation_count": 417_209,
            "excluded_path_count": 20_193,
            "complete_observation_rate": "0.9538",
            "known_split_adjustment_applied_path_count": 700,
            "price_feature_basis": (
                "sparse_known_split_adjustment_proxy_with_unproven_neutral_rows"
            ),
            "market_regime_basis": (
                "recomputed_reconstructed_same_session_proxy"
            ),
            "observed_regime_states": (
                "Balanced",
                "Defensive",
                "Risk-on",
            ),
            "unobserved_regime_states": ("Stress",),
            "limitation_codes": (
                "point_in_time_sector_concentration_unavailable",
                "recomputed_regime_not_as_operated",
                "reconstructed_membership_not_as_operated",
                "sparse_adjustment_proxy_not_formal_adjustment_evidence",
            ),
            "as_operated": False,
            "contains_forward_outcomes": False,
            "contains_performance_metrics": False,
            "parameter_selection_authorized": False,
            "candidate_activation_authorized": False,
        },
        "decision_gates": method.decision_gate_disclosures,
        "primary_strength": method.primary_strength,
        "primary_weakness": method.primary_weakness,
        "counterevidence_requirements": method.counterevidence_requirements,
        "invalidation_conditions": method.invalidation_conditions,
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
        "source_method_contract_version": method.contract_version,
        "source_method_fingerprint": method.logical_fingerprint,
        "source_experiment_id": method.source_experiment_id,
        "source_experiment_fingerprint": method.source_experiment_fingerprint,
        "input_feature_fingerprint": method.input_feature_fingerprint,
        "evaluation_policy_fingerprint": method.evaluation_policy_fingerprint,
        "implementation_revision": (
            "9879f2e890840487c90a89078eb31f0cbff273c0"
        ),
        "implementation_revision_reason": (
            "The canonical method and reconstructed outcome-blind diagnostics "
            "are implemented and replayed; no real outcome or result publication "
            "exists."
        ),
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
