"""Typed Phase 5 opportunity-candidate score, risk, and state ledgers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_CALCULATION_VERSION,
    CANDIDATE_CONTRACT_VERSION,
    CANDIDATE_PARAMETER_SET_ID,
    CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
    CONFIDENCE_HISTORY_WEIGHT,
    CONFIDENCE_RELATIONSHIP_WEIGHT,
    CONFIDENCE_SOURCE_WEIGHT,
    CONFIDENCE_STATE_WEIGHT,
    RELATIONSHIP_SUPPORT_LEVELS,
    STATE_CONFIRMATION_SUPPORT_SESSION_CAP,
)

from .market_regime_state import RegimeState


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


class CandidateOpportunityStage(StrEnum):
    WATCH = "watch"
    PREPARE = "prepare"
    ENTER = "enter"
    INVALIDATED = "invalidated"


class CandidateStateAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CandidateStateTransitionStatus(StrEnum):
    NOT_LISTED = "not_listed"
    LISTED = "listed"
    HELD = "held"
    PENDING = "pending"
    PENDING_REVERSED = "pending_reversed"
    SWITCHED = "switched"
    INVALIDATED = "invalidated"
    CONFIRMATION_PAUSED = "confirmation_paused"
    UNAVAILABLE_STALE = "unavailable_stale"
    UNAVAILABLE_NULL = "unavailable_null"


class CandidateConfirmationCountSource(StrEnum):
    PRIOR_CANDIDATE_STATE_HISTORY = "prior_candidate_state_history"


class CandidateBreakoutAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


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


class CandidatePriorStateSupportV1(BaseModel):
    """One stable-ID fact from the immediately preceding candidate-state ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: UUID
    prior_stage: CandidateOpportunityStage | None
    stage_confirmation_session_count: int = Field(
        ge=0,
        le=STATE_CONFIRMATION_SUPPORT_SESSION_CAP,
    )
    source_state_record_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def support_reconciles(self) -> "CandidatePriorStateSupportV1":
        if self.prior_stage is None:
            if self.stage_confirmation_session_count != 0:
                raise ValueError("a missing prior candidate stage must carry zero confirmation support")
        elif self.stage_confirmation_session_count < 1 or self.source_state_record_fingerprint is None:
            raise ValueError("a prior candidate stage requires positive capped support and its record fingerprint")
        return self


class CandidatePriorStateSourceV1(BaseModel):
    """Typed, source-bound prior state input for one current candidate batch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    universe_id: str
    as_of_session: date
    decision_context: Literal["candidate"] = "candidate"
    bootstrap: bool
    source_state_session: date | None
    state_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    supports: tuple[CandidatePriorStateSupportV1, ...]

    @model_validator(mode="after")
    def source_reconciles(self) -> "CandidatePriorStateSourceV1":
        keys = tuple(str(item.instrument_id) for item in self.supports)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("prior candidate-state support rows must be unique and stable-ID ordered")
        if self.bootstrap:
            if self.source_state_session is not None or self.supports:
                raise ValueError("candidate-state bootstrap cannot cite prior rows or a prior session")
            if self.state_history_fingerprint != CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT:
                raise ValueError("candidate-state bootstrap requires the fixed explicit-bootstrap fingerprint")
        elif self.source_state_session is None or self.source_state_session >= self.as_of_session:
            raise ValueError("candidate prior-state source must identify an earlier completed session")
        return self


class CandidateConfidenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_completeness: str
    history_completeness: str
    relationship_support: str
    state_confirmation_support: str
    confirmation_session_count: int = Field(ge=0, le=STATE_CONFIRMATION_SUPPORT_SESSION_CAP)
    prior_state_record_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    confidence: str
    disclaimer: Literal["data_support_not_success_probability"] = "data_support_not_success_probability"

    @model_validator(mode="after")
    def confidence_reconciles(self) -> "CandidateConfidenceV1":
        terms = {
            "source_completeness": _scale_four_unit_decimal(self.source_completeness, "source completeness"),
            "history_completeness": _scale_four_unit_decimal(self.history_completeness, "history completeness"),
            "relationship_support": _scale_four_unit_decimal(self.relationship_support, "relationship support"),
            "state_confirmation_support": _scale_four_unit_decimal(
                self.state_confirmation_support,
                "state confirmation support",
            ),
        }
        allowed_relationship_support = {Decimal(value).quantize(Decimal("0.0001")) for _, value in RELATIONSHIP_SUPPORT_LEVELS}
        if terms["relationship_support"] not in allowed_relationship_support:
            raise ValueError("relationship support must use a fixed evidence-support level")
        expected_state_support = (
            Decimal(self.confirmation_session_count) / Decimal(STATE_CONFIRMATION_SUPPORT_SESSION_CAP)
        ).quantize(Decimal("0.0001"))
        if terms["state_confirmation_support"] != expected_state_support:
            raise ValueError("state confirmation support must reconcile with its capped session count")
        if self.confirmation_session_count > 0 and self.prior_state_record_fingerprint is None:
            raise ValueError("positive candidate state support requires its prior state-record fingerprint")
        expected = (
            Decimal(CONFIDENCE_SOURCE_WEIGHT) * terms["source_completeness"]
            + Decimal(CONFIDENCE_HISTORY_WEIGHT) * terms["history_completeness"]
            + Decimal(CONFIDENCE_RELATIONSHIP_WEIGHT) * terms["relationship_support"]
            + Decimal(CONFIDENCE_STATE_WEIGHT) * terms["state_confirmation_support"]
        ).quantize(Decimal("0.0001"))
        actual = _scale_four_unit_decimal(self.confidence, "candidate confidence")
        if actual != expected:
            raise ValueError("candidate confidence must reconcile with the fixed four-term formula")
        return self


class OpportunityCandidateScoreV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.1"] = "1.1"
    contract_version: Literal[CANDIDATE_CONTRACT_VERSION] = CANDIDATE_CONTRACT_VERSION
    calculation_version: Literal[CANDIDATE_CALCULATION_VERSION] = CANDIDATE_CALCULATION_VERSION
    parameter_set_id: Literal[CANDIDATE_PARAMETER_SET_ID] = CANDIDATE_PARAMETER_SET_ID
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
    primary_driver_instrument_id: UUID | None
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
        driver_fields = (
            self.primary_driver_instrument_id,
            self.primary_driver_ticker,
            self.driver_correlation_20,
            self.relationship_kind,
        )
        if any(item is None for item in driver_fields) and not all(item is None for item in driver_fields):
            raise ValueError("candidate driver stable ID, ticker, correlation, and relationship kind must share nullability")
        return self


class OpportunityCandidateBatchV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.1"] = "1.1"
    calculation_version: Literal[CANDIDATE_CALCULATION_VERSION] = CANDIDATE_CALCULATION_VERSION
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    universe_member_count: int = Field(gt=0)
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    regime_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    history_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_state_source: CandidatePriorStateSourceV1
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
        if self.prior_state_source.universe_id != self.universe_id or self.prior_state_source.as_of_session != self.as_of_session:
            raise ValueError("candidate batch and typed prior-state source identity must match")
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

    schema_version: Literal["1.1"] = "1.1"
    calculation_version: Literal[CANDIDATE_CALCULATION_VERSION] = CANDIDATE_CALCULATION_VERSION
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


class CandidateBreakoutFactV1(BaseModel):
    """Source facts for the one-session Prepare-to-Enter breakout route."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of_session: date
    instrument_id: UUID
    availability: CandidateBreakoutAvailability
    close: str | None
    prior_five_session_close_high: str | None
    current_volume_ratio: str | None
    prior_five_sessions: tuple[date, ...]
    triggered: bool | None
    missing_reason: str | None
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def breakout_fact_reconciles(self) -> "CandidateBreakoutFactV1":
        values = (self.close, self.prior_five_session_close_high, self.current_volume_ratio)
        if self.availability is CandidateBreakoutAvailability.AVAILABLE:
            if any(value is None for value in values) or self.triggered is None or self.missing_reason is not None:
                raise ValueError("available breakout fact requires all raw facts and a derived result")
            if len(self.prior_five_sessions) != 5:
                raise ValueError("available breakout fact requires exactly five prior sessions")
            if tuple(sorted(self.prior_five_sessions)) != self.prior_five_sessions:
                raise ValueError("breakout prior sessions must be unique and ascending")
            if len(set(self.prior_five_sessions)) != 5 or self.prior_five_sessions[-1] >= self.as_of_session:
                raise ValueError("breakout prior sessions must precede the as-of session")
            close = _finite_decimal(self.close, "breakout close")
            prior_high = _finite_decimal(self.prior_five_session_close_high, "breakout prior high")
            volume_ratio = _finite_decimal(self.current_volume_ratio, "breakout volume ratio")
            if close <= 0 or prior_high <= 0 or volume_ratio < 0:
                raise ValueError("breakout price facts must be positive and volume ratio nonnegative")
            expected = close > prior_high and volume_ratio >= Decimal("1.20")
            if self.triggered is not expected:
                raise ValueError("breakout trigger must reconcile with raw close, high, and volume-ratio facts")
        else:
            if any(value is not None for value in values) or self.triggered is not None:
                raise ValueError("unavailable breakout fact cannot carry derived or raw values")
            if self.missing_reason is None:
                raise ValueError("unavailable breakout fact requires a missing reason")
        return self


class CandidateStateObservationV1(BaseModel):
    """One immutable daily score plus the typed facts needed by state replay."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: OpportunityCandidateScoreV1
    regime_state: RegimeState | None
    breakout_fact: CandidateBreakoutFactV1
    confirmation_count_source: CandidateConfirmationCountSource = (
        CandidateConfirmationCountSource.PRIOR_CANDIDATE_STATE_HISTORY
    )
    declared_invalidation_fired: bool = False
    declared_invalidation_reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def observation_reconciles(self) -> "CandidateStateObservationV1":
        if self.breakout_fact.as_of_session != self.candidate.as_of_session:
            raise ValueError("breakout and candidate sessions must match")
        if self.breakout_fact.instrument_id != self.candidate.instrument_id:
            raise ValueError("breakout and candidate stable IDs must match")
        if self.declared_invalidation_fired != bool(self.declared_invalidation_reason_codes):
            raise ValueError("declared invalidation flag and reason codes must reconcile")
        return self


class CandidateStateGateResultV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    passed: bool | None
    actual_value: str | None
    threshold: str | None
    boundary_operator: Literal[">=", ">", "<=", "<", "is", "is_not"] | None
    reason_codes: tuple[str, ...]


class OpportunityCandidateStateRecordV1(BaseModel):
    """Replayable candidate-context transition row; never a sale instruction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["opportunity-candidate-state/1.0"] = "opportunity-candidate-state/1.0"
    calculation_version: Literal["market-regime-opportunity-candidate-state-v1.0.0"] = (
        "market-regime-opportunity-candidate-state-v1.0.0"
    )
    parameter_set_id: Literal["mrom-candidate-state-v1-fixed-baseline-1"] = (
        "mrom-candidate-state-v1-fixed-baseline-1"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    decision_context: Literal["candidate"] = "candidate"
    stage_display_semantics: Literal["candidate_discovery"] = "candidate_discovery"
    prior_stage: CandidateOpportunityStage | None
    proposed_stage: CandidateOpportunityStage | None
    final_stage: CandidateOpportunityStage | None
    transition_status: CandidateStateTransitionStatus
    transition_rule_id: str
    pending_target_stage: CandidateOpportunityStage | None
    confirmation_count_before: int = Field(ge=0)
    confirmation_count_after: int = Field(ge=0)
    required_confirmation_sessions: int = Field(ge=0)
    confirmation_count_source: CandidateConfirmationCountSource
    input_confidence_confirmation_session_count: int = Field(ge=0)
    stage_confirmation_count_before: int = Field(ge=0, le=STATE_CONFIRMATION_SUPPORT_SESSION_CAP)
    stage_confirmation_count_after: int = Field(ge=0, le=STATE_CONFIRMATION_SUPPORT_SESSION_CAP)
    regime_state: RegimeState | None
    base_score: str | None
    confidence: str | None
    breakout_triggered: bool | None
    state_availability: CandidateStateAvailability
    stale_state: bool
    consecutive_missing_sessions: int = Field(ge=0)
    manual_review_required: bool
    anomaly_or_quarantine: bool
    gate_results: tuple[CandidateStateGateResultV1, ...]
    reason_codes: tuple[str, ...]
    human_explanation: str
    source_candidate_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def state_record_reconciles(self) -> "OpportunityCandidateStateRecordV1":
        if self.state_availability is CandidateStateAvailability.AVAILABLE:
            if self.base_score is None or self.confidence is None or self.source_candidate_fingerprint is None:
                raise ValueError("available candidate state requires score, confidence, and source fingerprint")
            if self.stale_state or self.consecutive_missing_sessions:
                raise ValueError("available candidate state cannot be stale or missing")
        else:
            if self.base_score is not None or self.confidence is not None or self.source_candidate_fingerprint is not None:
                raise ValueError("unavailable candidate state cannot carry live score facts")
            if self.consecutive_missing_sessions < 1:
                raise ValueError("unavailable candidate state requires a missing-session count")
            if self.stale_state != (self.final_stage is not None):
                raise ValueError("stale state is true only while the prior stage is held")
        if self.transition_status is CandidateStateTransitionStatus.PENDING and self.pending_target_stage is None:
            raise ValueError("pending candidate transition requires a target")
        if self.confirmation_count_after > self.required_confirmation_sessions and self.required_confirmation_sessions:
            raise ValueError("candidate confirmation count exceeds its fixed requirement")
        if self.final_stage is CandidateOpportunityStage.INVALIDATED and self.decision_context != "candidate":
            raise ValueError("invalidated semantics are reserved for candidate context")
        if self.transition_rule_id == "active_to_invalidated" and self.final_stage is not CandidateOpportunityStage.INVALIDATED:
            raise ValueError("candidate invalidation rule must end in invalidated state")
        if self.consecutive_missing_sessions > 1 and (self.final_stage is not None or not self.manual_review_required):
            raise ValueError("candidate state must become null with manual review after one missing session")
        if self.input_confidence_confirmation_session_count != self.stage_confirmation_count_before:
            raise ValueError("candidate confidence must use the preceding stage-confirmation count")
        if self.final_stage is None and self.stage_confirmation_count_after != 0:
            raise ValueError("a null candidate stage must have zero stage-confirmation support")
        if self.final_stage is not None and self.stage_confirmation_count_after < 1:
            raise ValueError("an available candidate stage requires positive stage-confirmation support")
        return self


def _finite_decimal(value: str | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"{label} is required")
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError(f"{label} must be finite")
    return parsed


def _scale_four_unit_decimal(value: str, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except Exception as exc:
        raise ValueError(f"{label} must be a decimal string") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > 1:
        raise ValueError(f"{label} must be finite and within [0,1]")
    if value != format(parsed.quantize(Decimal("0.0001")), "f"):
        raise ValueError(f"{label} must use scale 4")
    return parsed
