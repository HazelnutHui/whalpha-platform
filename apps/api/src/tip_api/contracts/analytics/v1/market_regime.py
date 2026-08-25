"""Typed Phase 1a Market Regime calculation ledgers."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MarketRegimeMetricV1(BaseModel):
    """One raw metric, normalization, weight, and contribution ledger row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-v1.0.0"] = (
        "market-regime-opportunity-map-v1.0.0"
    )
    metric_id: str
    as_of_session: date
    lookback_sessions: int = Field(ge=0)
    raw_value: str | None
    raw_unit: str
    direction: Literal["higher_supportive", "lower_supportive", "two_sided"]
    normalization_method: str
    normalization_parameters: tuple[tuple[str, str], ...]
    normalized_value: str | None
    configured_weight: str
    effective_weight: str
    weighted_contribution: str | None
    actual_observations: int = Field(ge=0)
    minimum_observations: int = Field(ge=0)
    coverage_ratio: str | None
    missing_count: int = Field(ge=0)
    availability: AvailabilityStatus
    missing_reason: str | None
    source_input_references: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def availability_reconciles(self) -> "MarketRegimeMetricV1":
        numeric = (self.raw_value, self.normalized_value, self.weighted_contribution)
        if self.availability is AvailabilityStatus.AVAILABLE:
            if any(value is None for value in numeric) or self.missing_reason is not None:
                raise ValueError("available metric must carry complete numeric values")
        elif any(value is not None for value in numeric) or self.missing_reason is None:
            raise ValueError("unavailable metric must be null with a missing reason")
        return self


class MarketRegimeDimensionV1(BaseModel):
    """One fixed Market Regime dimension and its internal metric ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-v1.0.0"] = (
        "market-regime-opportunity-map-v1.0.0"
    )
    universe_id: str
    dimension_id: str
    as_of_session: date
    direction: Literal["higher_supportive"] = "higher_supportive"
    configured_weight: str
    effective_weight: str
    internal_configured_weight_available: str
    score: str | None
    score_contribution: str | None
    minimum_observations: int = Field(ge=0)
    actual_observations: int = Field(ge=0)
    coverage_ratio: str | None
    missing_count: int = Field(ge=0)
    availability: AvailabilityStatus
    support_status: Literal["supporting", "neutral", "conflicting", "unavailable"]
    explanation_template_id: str
    rendered_explanation: str
    raw_metrics: tuple[MarketRegimeMetricV1, ...]
    warnings: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def dimension_reconciles(self) -> "MarketRegimeDimensionV1":
        if self.availability is AvailabilityStatus.AVAILABLE:
            if self.score is None or self.score_contribution is None or self.support_status == "unavailable":
                raise ValueError("available dimension is incomplete")
        elif self.score is not None or self.score_contribution is not None or self.support_status != "unavailable":
            raise ValueError("unavailable dimension must not carry a score")
        if len({item.metric_id for item in self.raw_metrics}) != len(self.raw_metrics):
            raise ValueError("dimension metric IDs must be unique")
        return self


class MarketRegimeCompositeV1(BaseModel):
    """Phase 1a composite. State/hysteresis is deliberately deferred."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["market-regime-opportunity-map/1.0"] = (
        "market-regime-opportunity-map/1.0"
    )
    calculation_version: Literal["market-regime-opportunity-map-v1.0.0"] = (
        "market-regime-opportunity-map-v1.0.0"
    )
    parameter_set_id: Literal["mrom-v1-fixed-baseline-1"] = "mrom-v1-fixed-baseline-1"
    parameter_set_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    universe_member_count: int = Field(gt=0)
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    activation_pointer_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eod_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    history_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    history_membership_mode: Literal["current_as_of_constituent_replay"] = (
        "current_as_of_constituent_replay"
    )
    history_sessions_used: tuple[date, ...]
    regime_score: str | None
    regime_adjustment: Literal["0.0000"] = "0.0000"
    configured_weight_available: str
    regime_state: None = None
    state_classification_status: Literal["deferred_phase_1a"] = "deferred_phase_1a"
    dimensions: tuple[MarketRegimeDimensionV1, ...]
    missing_metric_ids: tuple[str, ...]
    unavailable_dimension_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def composite_reconciles(self) -> "MarketRegimeCompositeV1":
        expected_order = (
            "trend",
            "breadth",
            "volatility",
            "liquidity_participation",
            "leadership_dispersion",
        )
        if tuple(item.dimension_id for item in self.dimensions) != expected_order:
            raise ValueError("five dimensions must use fixed contract order")
        if not self.history_sessions_used or tuple(sorted(self.history_sessions_used)) != self.history_sessions_used:
            raise ValueError("history sessions must be ordered")
        return self


class ExplanationLedgerEntryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-v1.0.0"] = (
        "market-regime-opportunity-map-v1.0.0"
    )
    as_of_session: date
    universe_id: str
    subject_id: str
    ordinal: int = Field(ge=0)
    evidence_type: Literal["fact", "proxy", "statistical_inference", "data_quality"]
    block_kind: Literal["supporting_evidence", "counterevidence", "data_quality_caveat"]
    template_id: str
    rendered_text: str
    metric_ids: tuple[str, ...]
    source_input_references: tuple[str, ...]
    reason_codes: tuple[str, ...]


class OracleComparisonV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-v1.0.0"] = (
        "market-regime-opportunity-map-v1.0.0"
    )
    as_of_session: date
    universe_id: str
    compared_metric_count: int = Field(ge=0)
    compared_dimension_count: Literal[5] = 5
    mismatch_count: int = Field(ge=0)
    mismatches: tuple[str, ...]
    contribution_reconciliation_mismatches: tuple[str, ...]
    future_session_reference_count: int = Field(ge=0)
    wrong_universe_reference_count: int = Field(ge=0)
    input_permutation_fingerprint_match: bool
    oracle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
