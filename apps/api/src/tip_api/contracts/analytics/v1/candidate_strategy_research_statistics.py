"""Typed, non-authoritative statistics for preregistered strategy fixtures."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_evaluation import (
    StrategyEvaluationSplit,
    StrategyOutcomeStatus,
)
from .candidate_strategy_research import STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
from .candidate_strategy_research_execution import StrongLeaderPullbackCohortRole


RESEARCH_STATISTICS_CONTRACT_VERSION = "candidate-strategy-research-statistics/1.1"
RESEARCH_BOOTSTRAP_REPLICATES = 2_000
RESEARCH_BLOCK_LENGTH_SESSIONS = 5
MINIMUM_COMPARABLE_SESSIONS = 20
MINIMUM_SIGNAL_OBSERVATIONS = 60


class ResearchStatisticsStage(StrEnum):
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    HOLDOUT = "holdout"


class ResearchInferenceStatus(StrEnum):
    AVAILABLE = "available"
    INCONCLUSIVE = "inconclusive"


class ResearchGateStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    NOT_EVALUATED = "not_evaluated"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackCohortOutcomeV1(FrozenModel):
    assignment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    horizon_sessions: Literal[1, 3, 5]
    status: StrategyOutcomeStatus
    underlying_price_return: str | None
    benchmark_price_return: str | None
    relative_to_benchmark_return: str | None
    maximum_favorable_excursion: str | None
    maximum_adverse_excursion: str | None
    source_eod_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason_codes: tuple[str, ...]
    fixture_only: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def outcome_reconciles(self) -> "StrongLeaderPullbackCohortOutcomeV1":
        expected_label = research_statistics_fingerprint(
            self,
            exclude={"label_fingerprint", "logical_fingerprint"},
        )
        if self.label_fingerprint != expected_label:
            raise ValueError("cohort outcome label fingerprint mismatch")
        values = (
            self.underlying_price_return,
            self.benchmark_price_return,
            self.relative_to_benchmark_return,
            self.maximum_favorable_excursion,
            self.maximum_adverse_excursion,
        )
        if self.status is StrategyOutcomeStatus.AVAILABLE:
            if any(item is None for item in values) or self.source_eod_fingerprint is None:
                raise ValueError("available cohort outcome requires complete source-bound values")
            stock = _scale_ten(self.underlying_price_return, "underlying return")
            benchmark = _scale_ten(self.benchmark_price_return, "benchmark return")
            relative = _scale_ten(
                self.relative_to_benchmark_return,
                "relative return",
            )
            favorable = _scale_ten(
                self.maximum_favorable_excursion,
                "maximum favorable excursion",
            )
            adverse = _scale_ten(
                self.maximum_adverse_excursion,
                "maximum adverse excursion",
            )
            if relative != (stock - benchmark).quantize(Decimal("0.0000000001")):
                raise ValueError("cohort relative return arithmetic differs")
            if favorable < 0 or adverse > 0 or self.reason_codes:
                raise ValueError("available cohort outcome signs or reasons differ")
        else:
            if any(item is not None for item in values):
                raise ValueError("non-available cohort outcome cannot carry statistics")
            if not self.reason_codes:
                raise ValueError("non-available cohort outcome requires reasons")
            if self.status is StrategyOutcomeStatus.PENDING and self.source_eod_fingerprint:
                raise ValueError("pending cohort outcome cannot carry future source evidence")
        if research_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cohort outcome fingerprint mismatch")
        return self


class ResearchCostScenarioV1(FrozenModel):
    basis_points_per_side: Literal[0, 10, 25, 50]
    signal_median_spy_relative_return_net: str | None

    @model_validator(mode="after")
    def scenario_reconciles(self) -> "ResearchCostScenarioV1":
        if self.signal_median_spy_relative_return_net is not None:
            _scale_ten(
                self.signal_median_spy_relative_return_net,
                "net relative return",
            )
        return self


class ResearchParameterSummaryV1(FrozenModel):
    parameter_combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_split: StrategyEvaluationSplit
    horizon_sessions: Literal[1, 3, 5]
    signal_assigned_count: int = Field(ge=0)
    control_assigned_count: int = Field(ge=0)
    signal_available_count: int = Field(ge=0)
    control_available_count: int = Field(ge=0)
    signal_quarantined_count: int = Field(ge=0)
    control_quarantined_count: int = Field(ge=0)
    signal_unavailable_or_pending_count: int = Field(ge=0)
    control_unavailable_or_pending_count: int = Field(ge=0)
    signal_coverage_ratio: str
    control_coverage_ratio: str
    paired_session_count: int = Field(ge=0)
    signal_market_regime_counts: dict[str, int]
    inference_status: ResearchInferenceStatus
    signal_mean_underlying_return: str | None
    signal_median_underlying_return: str | None
    signal_median_spy_relative_return: str | None
    signal_hit_rate: str | None
    signal_mean_maximum_favorable_excursion: str | None
    signal_mean_maximum_adverse_excursion: str | None
    session_balanced_mean_contrast: str | None
    contrast_lower_90pct: str | None
    contrast_upper_90pct: str | None
    one_sided_raw_p_value: str | None
    holm_adjusted_p_value: str | None
    bootstrap_replicates: int = Field(ge=0)
    cost_scenarios: tuple[ResearchCostScenarioV1, ...]
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def summary_reconciles(self) -> "ResearchParameterSummaryV1":
        if self.signal_assigned_count != (
            self.signal_available_count
            + self.signal_quarantined_count
            + self.signal_unavailable_or_pending_count
        ):
            raise ValueError("signal disposition counts differ")
        if self.control_assigned_count != (
            self.control_available_count
            + self.control_quarantined_count
            + self.control_unavailable_or_pending_count
        ):
            raise ValueError("control disposition counts differ")
        _bounded_scale_four(self.signal_coverage_ratio, "signal coverage")
        _bounded_scale_four(self.control_coverage_ratio, "control coverage")
        expected_signal_coverage = _coverage_string(
            self.signal_available_count,
            self.signal_assigned_count,
        )
        expected_control_coverage = _coverage_string(
            self.control_available_count,
            self.control_assigned_count,
        )
        if (
            self.signal_coverage_ratio != expected_signal_coverage
            or self.control_coverage_ratio != expected_control_coverage
        ):
            raise ValueError("research coverage ratio differs from counts")
        if set(self.signal_market_regime_counts) != {
            "Balanced",
            "Defensive",
            "Risk-on",
            "Stress",
        } or any(value < 0 for value in self.signal_market_regime_counts.values()):
            raise ValueError("research Regime counts have invalid keys or values")
        if sum(self.signal_market_regime_counts.values()) != self.signal_available_count:
            raise ValueError("research Regime counts differ from available signals")
        if tuple(item.basis_points_per_side for item in self.cost_scenarios) != (
            0,
            10,
            25,
            50,
        ):
            raise ValueError("research cost scenarios differ from policy")
        descriptive_statistics = (
            self.signal_mean_underlying_return,
            self.signal_median_underlying_return,
            self.signal_median_spy_relative_return,
            self.signal_hit_rate,
            self.signal_mean_maximum_favorable_excursion,
            self.signal_mean_maximum_adverse_excursion,
            self.session_balanced_mean_contrast,
        )
        inferential_statistics = (
            self.contrast_lower_90pct,
            self.contrast_upper_90pct,
            self.one_sided_raw_p_value,
        )
        if self.inference_status is ResearchInferenceStatus.AVAILABLE:
            if any(item is None for item in inferential_statistics):
                raise ValueError("available inference requires complete statistics")
            if self.bootstrap_replicates != RESEARCH_BOOTSTRAP_REPLICATES:
                raise ValueError("available inference requires fixed bootstrap count")
        elif (
            any(item is not None for item in inferential_statistics)
            or self.bootstrap_replicates
        ):
            raise ValueError("inconclusive inference cannot carry inferential statistics")
        for value in descriptive_statistics:
            if value is not None:
                _scale_ten(value, "research statistic")
        if self.signal_hit_rate is not None and not (
            Decimal("0") <= Decimal(self.signal_hit_rate) <= Decimal("1")
        ):
            raise ValueError("signal hit rate must be within [0,1]")
        if (
            self.signal_mean_maximum_favorable_excursion is not None
            and Decimal(self.signal_mean_maximum_favorable_excursion) < 0
        ) or (
            self.signal_mean_maximum_adverse_excursion is not None
            and Decimal(self.signal_mean_maximum_adverse_excursion) > 0
        ):
            raise ValueError("research excursion signs differ")
        for value in inferential_statistics[:2]:
            if value is not None:
                _scale_ten(value, "research statistic")
        for value in inferential_statistics[2:]:
            if value is not None:
                _bounded_scale_six(value, "research probability")
        if self.holm_adjusted_p_value is not None:
            _bounded_scale_six(self.holm_adjusted_p_value, "Holm probability")
            if (
                self.one_sided_raw_p_value is None
                or Decimal(self.holm_adjusted_p_value)
                < Decimal(self.one_sided_raw_p_value)
            ):
                raise ValueError("Holm probability cannot improve the raw probability")
        if (
            self.contrast_lower_90pct is not None
            and self.contrast_upper_90pct is not None
            and Decimal(self.contrast_lower_90pct)
            > Decimal(self.contrast_upper_90pct)
        ):
            raise ValueError("research contrast interval is reversed")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("research summary reasons must be unique and sorted")
        if research_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research summary fingerprint mismatch")
        return self


class ResearchParameterLockV1(FrozenModel):
    parameter_combination_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    development_evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    selection_objective: Literal[
        "maximum_development_lower_90pct_session_balanced_3s_contrast"
    ] = "maximum_development_lower_90pct_session_balanced_3s_contrast"
    objective_value: str
    secondary_tiebreak_value: str
    selected_before_validation: Literal[True] = True
    validation_cannot_change_parameters: Literal[True] = True
    holdout_cannot_change_parameters: Literal[True] = True
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def lock_reconciles(self) -> "ResearchParameterLockV1":
        _scale_ten(self.objective_value, "selection objective")
        _scale_ten(self.secondary_tiebreak_value, "selection tiebreak")
        if research_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research parameter lock fingerprint mismatch")
        return self


class ResearchGateEvaluationV1(FrozenModel):
    gate_id: str
    metric_id: str
    evaluation_split: StrategyEvaluationSplit
    status: ResearchGateStatus
    observed_value: str | None
    threshold: str
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def gate_reconciles(self) -> "ResearchGateEvaluationV1":
        if self.status in {ResearchGateStatus.PASS, ResearchGateStatus.FAIL}:
            if self.observed_value is None:
                raise ValueError("decided gate requires an observed value")
        elif self.observed_value is not None:
            raise ValueError("undecided gate cannot carry an observed value")
        if not self.reason_codes or self.reason_codes != tuple(
            sorted(set(self.reason_codes))
        ):
            raise ValueError("gate reasons must be non-empty, unique, and sorted")
        return self


class StrongLeaderPullbackStatisticsReportV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[RESEARCH_STATISTICS_CONTRACT_VERSION] = (
        RESEARCH_STATISTICS_CONTRACT_VERSION
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    mechanics_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage: ResearchStatisticsStage
    universe_id: Literal["primary"] = "primary"
    prior_stage_report_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    input_outcome_count: int = Field(ge=0)
    summaries: tuple[ResearchParameterSummaryV1, ...]
    selected_parameter_combination_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    parameter_lock: ResearchParameterLockV1 | None
    gate_evaluations: tuple[ResearchGateEvaluationV1, ...]
    all_required_gates_passed: bool
    fixture_only: Literal[True] = True
    stage_transition_authorized: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    holdout_consumed: bool
    single_use_holdout_custody_implemented: Literal[False] = False
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackStatisticsReportV1":
        expected_summary_count = 3 if self.stage is ResearchStatisticsStage.HOLDOUT else 72
        if len(self.summaries) != expected_summary_count:
            raise ValueError("research report summary scope differs from stage")
        summary_keys = tuple(
            (item.parameter_combination_id, item.horizon_sessions)
            for item in self.summaries
        )
        if len(summary_keys) != len(set(summary_keys)):
            raise ValueError("research report summaries must be unique")
        expected_split = StrategyEvaluationSplit(self.stage.value)
        if any(item.evaluation_split is not expected_split for item in self.summaries):
            raise ValueError("research report summary split differs from stage")
        if self.stage is ResearchStatisticsStage.DEVELOPMENT:
            if self.prior_stage_report_fingerprint is not None or self.holdout_consumed:
                raise ValueError("development report cannot cite later-stage evidence")
        else:
            if self.prior_stage_report_fingerprint is None or self.parameter_lock is None:
                raise ValueError("later-stage report requires its locked prior stage")
        if self.stage is ResearchStatisticsStage.HOLDOUT:
            if not self.holdout_consumed:
                raise ValueError("holdout report must mark one-time consumption")
        elif self.holdout_consumed:
            raise ValueError("pre-holdout report cannot consume holdout")
        if self.parameter_lock is not None and (
            self.selected_parameter_combination_id
            != self.parameter_lock.parameter_combination_id
        ):
            raise ValueError("selected parameter and immutable lock differ")
        if (self.parameter_lock is None) != (
            self.selected_parameter_combination_id is None
        ):
            raise ValueError("research selection and parameter lock availability differ")
        if self.stage is ResearchStatisticsStage.DEVELOPMENT and self.parameter_lock:
            expected_evidence = research_statistics_fingerprint(
                {
                    "summary_fingerprints": tuple(
                        item.logical_fingerprint for item in self.summaries
                    )
                },
                exclude=set(),
            )
            if (
                self.parameter_lock.development_evidence_fingerprint
                != expected_evidence
            ):
                raise ValueError("development parameter lock evidence differs")
        expected_gate_ids = {
            ResearchStatisticsStage.DEVELOPMENT: (),
            ResearchStatisticsStage.VALIDATION: (
                "complete_validation_family_evidence",
                "familywise_adjusted_parameter_evidence",
                "net_primary_median_positive",
                "regime_observation_floor",
            ),
            ResearchStatisticsStage.HOLDOUT: (
                "complete_cohort_outcome_coverage",
                "holdout_primary_contrast_positive",
                "net_primary_median_positive",
                "regime_observation_floor",
            ),
        }[self.stage]
        if tuple(item.gate_id for item in self.gate_evaluations) != expected_gate_ids:
            raise ValueError("research gate scope differs from stage")
        if any(
            item.evaluation_split is not expected_split
            for item in self.gate_evaluations
        ):
            raise ValueError("research gate split differs from report stage")
        gate_pass = bool(self.gate_evaluations) and all(
            item.status is ResearchGateStatus.PASS for item in self.gate_evaluations
        )
        if self.all_required_gates_passed != gate_pass:
            raise ValueError("research gate aggregate differs")
        if not self.reason_codes or self.reason_codes != tuple(
            sorted(set(self.reason_codes))
        ):
            raise ValueError("report reasons must be non-empty, unique, and sorted")
        if research_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research statistics report fingerprint mismatch")
        return self


def research_statistics_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude=exclude or {"logical_fingerprint"})
    else:
        payload = dict(value)
        for key in exclude or {"logical_fingerprint"}:
            payload.pop(key, None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _scale_ten(value: str | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"{label} is required")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a Decimal string") from exc
    if not parsed.is_finite() or value != format(
        parsed.quantize(Decimal("0.0000000001")),
        "f",
    ):
        raise ValueError(f"{label} must use scale 10")
    return parsed


def _bounded_scale_four(value: str, label: str) -> Decimal:
    parsed = _scaled_decimal(value, Decimal("0.0001"), label)
    if not Decimal("0") <= parsed <= Decimal("1"):
        raise ValueError(f"{label} must be within [0,1]")
    return parsed


def _bounded_scale_six(value: str, label: str) -> Decimal:
    parsed = _scaled_decimal(value, Decimal("0.000001"), label)
    if not Decimal("0") <= parsed <= Decimal("1"):
        raise ValueError(f"{label} must be within [0,1]")
    return parsed


def _scaled_decimal(value: str, quantum: Decimal, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a Decimal string") from exc
    if not parsed.is_finite() or value != format(parsed.quantize(quantum), "f"):
        raise ValueError(f"{label} has invalid scale")
    return parsed


def _coverage_string(available: int, assigned: int) -> str:
    value = Decimal("0") if not assigned else Decimal(available) / Decimal(assigned)
    return format(value.quantize(Decimal("0.0001")), "f")
