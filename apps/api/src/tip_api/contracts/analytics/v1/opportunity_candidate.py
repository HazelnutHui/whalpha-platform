"""Typed Phase 5A opportunity-candidate score and risk-mode ledgers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandidateMetricAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CandidateDataQualityStatus(StrEnum):
    PASSED = "passed"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class CandidateRiskMode(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class CandidateMetricV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metric_id: str
    raw_value: str | None
    raw_unit: str
    normalized_value: str | None
    availability: CandidateMetricAvailability
    missing_reason: str | None
    evidence_type: Literal["fact", "proxy", "statistical_inference", "data_quality"]
    source_sessions: tuple[date, ...]
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def availability_reconciles(self) -> "CandidateMetricV1":
        if self.availability is CandidateMetricAvailability.AVAILABLE:
            if self.raw_value is None or self.normalized_value is None or self.missing_reason is not None:
                raise ValueError("available candidate metric must carry raw and normalized values")
        elif self.raw_value is not None or self.normalized_value is not None or self.missing_reason is None:
            raise ValueError("unavailable candidate metric must be null with a reason")
        return self


class CandidateComponentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    component_id: str
    configured_weight: str
    effective_weight: str
    score: str | None
    contribution: str | None
    availability: CandidateMetricAvailability
    cap_applied: str | None
    metrics: tuple[CandidateMetricV1, ...]
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def component_reconciles(self) -> "CandidateComponentV1":
        if self.availability is CandidateMetricAvailability.AVAILABLE:
            if self.score is None or self.contribution is None:
                raise ValueError("available component must carry score and contribution")
        elif self.score is not None or self.contribution is not None or self.effective_weight != "0.0000":
            raise ValueError("unavailable component must be null with zero effective weight")
        return self


class CandidateConfidenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_completeness: str
    history_completeness: str
    relationship_support: str
    state_confirmation_support: str
    confirmation_session_count: int = Field(ge=0)
    confidence: str
    disclaimer: Literal["data_support_not_success_probability"] = "data_support_not_success_probability"


class OpportunityCandidateScoreV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["opportunity-candidate/1.0"] = "opportunity-candidate/1.0"
    calculation_version: Literal["market-regime-opportunity-candidate-v1.0.0"] = (
        "market-regime-opportunity-candidate-v1.0.0"
    )
    parameter_set_id: Literal["mrom-candidate-v1-fixed-baseline-1"] = (
        "mrom-candidate-v1-fixed-baseline-1"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    latest_data_session: date
    base_score: str | None
    regime_adjustment: Literal["0.0000"] = "0.0000"
    adjusted_score: str | None
    configured_weight_available: str
    missingness_penalty: str
    components: tuple[CandidateComponentV1, ...]
    confidence: CandidateConfidenceV1
    latest_price: str
    median_dollar_volume_20: str | None
    annualized_volatility_10: str | None
    maximum_absolute_open_gap_5: str | None
    current_volume_ratio: str | None
    primary_driver_ticker: str | None
    driver_correlation_20: str | None
    relationship_kind: Literal["price_derived_exposure_proxy"] | None
    corporate_action_review_required: bool
    data_quality_status: CandidateDataQualityStatus
    supporting_evidence: tuple[str, ...]
    counterevidence: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def score_reconciles(self) -> "OpportunityCandidateScoreV1":
        expected = (
            "market_alignment",
            "etf_sector_alignment",
            "stock_relative_strength",
            "trend_quality",
            "volume_participation",
            "volatility_risk",
            "liquidity_suitability",
        )
        if tuple(item.component_id for item in self.components) != expected:
            raise ValueError("candidate components must use fixed contract order")
        if self.latest_data_session != self.as_of_session:
            raise ValueError("candidate display metadata must come from the as-of session")
        if (self.base_score is None) != (self.adjusted_score is None):
            raise ValueError("base and adjusted score nullability must match")
        if self.base_score != self.adjusted_score:
            raise ValueError("V1 adjusted score must equal the fixed base score")
        displayed_contributions = sum(
            (Decimal(item.contribution) for item in self.components if item.contribution is not None),
            Decimal("0"),
        ).quantize(Decimal("0.0001"))
        if self.base_score is not None and displayed_contributions != Decimal(self.base_score):
            raise ValueError("base score must equal displayed component contributions")
        if self.corporate_action_review_required and self.data_quality_status is not CandidateDataQualityStatus.QUARANTINED:
            raise ValueError("corporate-action review must quarantine the candidate")
        return self


class OpportunityCandidateBatchV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-candidate-v1.0.0"] = (
        "market-regime-opportunity-candidate-v1.0.0"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    universe_member_count: int = Field(gt=0)
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    regime_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    history_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    bar_covered_member_count: int = Field(ge=0)
    missing_member_ids: tuple[UUID, ...]
    candidates: tuple[OpportunityCandidateScoreV1, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def batch_reconciles(self) -> "OpportunityCandidateBatchV1":
        if self.bar_covered_member_count + len(self.missing_member_ids) != self.universe_member_count:
            raise ValueError("candidate batch coverage does not reconcile")
        keys = tuple(str(item.instrument_id) for item in self.candidates)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("candidate rows must be unique and stable-ID ordered")
        if len(self.candidates) != self.bar_covered_member_count:
            raise ValueError("every as-of bar-covered member requires a candidate fact row")
        return self


class CandidateRiskAssessmentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: UUID
    ticker: str
    risk_mode: CandidateRiskMode
    eligible: bool
    risk_adjusted_rank: int | None = Field(default=None, ge=1)
    concentration_key: str
    rejection_reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def eligibility_reconciles(self) -> "CandidateRiskAssessmentV1":
        if self.eligible and (self.risk_adjusted_rank is None or self.rejection_reason_codes):
            raise ValueError("eligible risk row requires rank and no rejection reasons")
        if not self.eligible and (self.risk_adjusted_rank is not None or not self.rejection_reason_codes):
            raise ValueError("rejected risk row requires reasons and no rank")
        return self


class CandidateRiskModeResultV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-candidate-v1.0.0"] = (
        "market-regime-opportunity-candidate-v1.0.0"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    risk_mode: CandidateRiskMode
    parameter_row: tuple[tuple[str, str], ...]
    assessments: tuple[CandidateRiskAssessmentV1, ...]
    eligible_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def result_reconciles(self) -> "CandidateRiskModeResultV1":
        if self.eligible_count + self.rejected_count != len(self.assessments):
            raise ValueError("risk-mode counts do not reconcile")
        ranks = sorted(item.risk_adjusted_rank for item in self.assessments if item.eligible)
        if ranks != list(range(1, self.eligible_count + 1)):
            raise ValueError("risk-adjusted ranks must be contiguous")
        return self
