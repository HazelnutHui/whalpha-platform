"""Typed, deterministic Phase 2 ETF relationship and audit ledgers."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RelationshipAvailability(StrEnum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class RelationshipState(StrEnum):
    RELATIONSHIP_BREAK_CANDIDATE = "relationship_break_candidate"
    ROTATION_CANDIDATE = "rotation_candidate"
    DIVERGENCE = "divergence"
    SYNCHRONOUS_STRENGTHENING = "synchronous_strengthening"
    SYNCHRONOUS_WEAKENING = "synchronous_weakening"
    NEUTRAL = "neutral"
    UNAVAILABLE = "unavailable"


class RelationshipConfidence(StrEnum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RegimeRelationshipAlignment(StrEnum):
    CONSISTENT = "consistent"
    CONFLICT = "conflict"
    NEUTRAL = "neutral"


class EtfRelationshipWindowMetricV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_sessions: Literal[5, 10, 20]
    start_session: date | None
    end_session: date
    left_start_close: str | None
    left_end_close: str | None
    right_start_close: str | None
    right_end_close: str | None
    left_return: str | None
    right_return: str | None
    relative_return: str | None
    daily_return_observation_count: int = Field(ge=0)
    rolling_correlation: str | None
    direction_combination: str | None
    availability: RelationshipAvailability
    missing_reason: str | None
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def availability_reconciles(self) -> "EtfRelationshipWindowMetricV1":
        calculated = (
            self.left_return,
            self.right_return,
            self.relative_return,
            self.rolling_correlation,
        )
        if self.availability is RelationshipAvailability.AVAILABLE:
            if any(item is None for item in calculated) or self.missing_reason is not None:
                raise ValueError("available window requires all metrics")
        elif self.missing_reason is None:
            raise ValueError("non-available window requires missing_reason")
        return self


class EtfRelationshipRecordV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["etf-relationship-map/1.0"] = "etf-relationship-map/1.0"
    calculation_version: Literal["market-regime-opportunity-map-etf-relationships-v1.0.0"] = (
        "market-regime-opportunity-map-etf-relationships-v1.0.0"
    )
    parameter_set_id: Literal["mrom-etf-relationships-v1-fixed-registry-1"] = (
        "mrom-etf-relationships-v1-fixed-registry-1"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: str
    as_of_session: date
    left_ticker: str
    right_ticker: str
    relationship_family: str
    windows: tuple[EtfRelationshipWindowMetricV1, ...]
    ratio_level: str | None
    ratio_robust_z: str | None
    ratio_percentile: str | None
    correlation_20_prior_5: str | None
    correlation_change_5: str | None
    correlation_perturbations: tuple[tuple[int, str | None], ...]
    perturbation_state_consistent: bool
    relationship_state: RelationshipState
    previous_relationship_state: RelationshipState | None
    confidence: RelationshipConfidence
    availability: RelationshipAvailability
    missing_reason: str | None
    paired_close_observation_count: int = Field(ge=0)
    source_first_session: date | None
    source_last_session: date
    source_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def registry_shape(self) -> "EtfRelationshipRecordV1":
        if tuple(item.window_sessions for item in self.windows) != (5, 10, 20):
            raise ValueError("window metrics must use fixed 5/10/20 order")
        if self.availability is RelationshipAvailability.UNAVAILABLE:
            if self.relationship_state is not RelationshipState.UNAVAILABLE or self.missing_reason is None:
                raise ValueError("unavailable relationship fields do not reconcile")
        elif self.relationship_state is RelationshipState.UNAVAILABLE:
            raise ValueError("available or partial relationship cannot use unavailable state")
        return self


class EtfRelationshipExplanationV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-etf-relationships-v1.0.0"] = (
        "market-regime-opportunity-map-etf-relationships-v1.0.0"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: str
    as_of_session: date
    template_id: Literal["etf_relationship_evidence_v1"] = "etf_relationship_evidence_v1"
    relationship_state: RelationshipState
    left_observation: str
    right_observation: str
    relative_strength_observation: str
    correlation_observation: str
    cross_window_observation: str
    supporting_evidence: tuple[str, ...]
    counterevidence: tuple[str, ...]
    reason_codes: tuple[str, ...]
    source_input_references: tuple[str, ...]
    disclaimers: tuple[str, ...]


class MarketRegimeRelationshipComparisonV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-etf-relationships-v1.0.0"] = (
        "market-regime-opportunity-map-etf-relationships-v1.0.0"
    )
    as_of_session: date
    universe_id: str
    regime_candidate_state: str
    regime_confirmed_state: str
    regime_composite: str
    regime_state_record_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: str
    relationship_state: RelationshipState
    alignment: RegimeRelationshipAlignment
    reason_codes: tuple[str, ...]
    disclaimer: Literal["contemporaneous_comparison_not_causal"] = "contemporaneous_comparison_not_causal"


class EtfRelationshipOracleComparisonV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal["market-regime-opportunity-map-etf-relationships-v1.0.0"] = (
        "market-regime-opportunity-map-etf-relationships-v1.0.0"
    )
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_count: int = Field(ge=0)
    history_record_count: int = Field(ge=0)
    mismatch_count: int = Field(ge=0)
    mismatches: tuple[str, ...]
    append_full_replay_match: bool
    input_permutation_match: bool
    future_prefix_stable: bool
    oracle_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
