"""Typed deterministic Market Regime Phase 1b state and transition ledgers."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RegimeState(StrEnum):
    RISK_ON = "risk_on"
    BALANCED = "balanced"
    DEFENSIVE = "defensive"
    STRESS = "stress"


class RegimeStateAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class RegimeTransitionStatus(StrEnum):
    INITIALIZATION_PENDING = "initialization_pending"
    INITIALIZED_CONFIRMED = "initialized_confirmed"
    INITIALIZED_PROVISIONAL = "initialized_provisional"
    HELD = "held"
    HYSTERESIS_HELD = "hysteresis_held"
    PENDING = "pending"
    PENDING_REVERSED = "pending_reversed"
    SWITCHED = "switched"
    IMMEDIATE_STRESS_OVERRIDE = "immediate_stress_override"
    PROVISIONAL_CLEARED = "provisional_cleared"
    UNAVAILABLE_STALE = "unavailable_stale"
    UNAVAILABLE_UNINITIALIZED = "unavailable_uninitialized"


class RegimeInitializationStatus(StrEnum):
    UNINITIALIZED_UNAVAILABLE = "uninitialized_unavailable"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    INITIALIZED = "initialized"
    INITIALIZED_PROVISIONAL = "initialized_provisional"


class StateThresholdDistanceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    threshold_id: str
    threshold: str
    signed_distance: str
    boundary_operator: Literal[">=", ">", "<=", "<"]
    threshold_kind: Literal["candidate_boundary", "transition_boundary"]


class MarketRegimeStateRecordV1(BaseModel):
    """One replayable state-machine result for one Universe/session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["market-regime-state/1.0"] = "market-regime-state/1.0"
    calculation_version: Literal[
        "market-regime-opportunity-map-state-v1.0.0",
        "market-regime-opportunity-map-state-v1.0.1",
    ] = (
        "market-regime-opportunity-map-state-v1.0.1"
    )
    phase1a_calculation_version: Literal["market-regime-opportunity-map-v1.0.0"] = (
        "market-regime-opportunity-map-v1.0.0"
    )
    state_parameter_set_id: Literal[
        "mrom-regime-state-v1-fixed-baseline-1",
        "mrom-regime-state-v1-stable-prefix-2",
    ] = (
        "mrom-regime-state-v1-stable-prefix-2"
    )
    state_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase1a_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    composite: str | None
    instantaneous_candidate_state: RegimeState | None
    confirmed_state: RegimeState | None
    previous_confirmed_state: RegimeState | None
    state_is_provisional: bool
    transition_status: RegimeTransitionStatus
    transition_rule_id: str
    pending_target_state: RegimeState | None
    consecutive_confirmation_sessions: int = Field(ge=0)
    required_confirmation_sessions: int = Field(ge=0)
    entry_threshold: str | None
    exit_threshold: str | None
    boundary_operator: Literal[">=", ">", "<=", "<"] | None
    initialization_status: RegimeInitializationStatus
    state_availability: RegimeStateAvailability
    stale_state: bool
    in_hysteresis_band: bool
    confirmation_sessions_remaining: int = Field(ge=0)
    threshold_distances: tuple[StateThresholdDistanceV1, ...]
    supporting_dimension_ids: tuple[str, ...]
    conflicting_dimension_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    source_composite_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def state_reconciles(self) -> "MarketRegimeStateRecordV1":
        if self.state_availability is RegimeStateAvailability.AVAILABLE:
            if self.composite is None or self.instantaneous_candidate_state is None:
                raise ValueError("available state row requires composite and candidate")
            if self.source_composite_fingerprint is None or self.stale_state:
                raise ValueError("available state row requires a live composite source")
        else:
            if self.composite is not None or self.instantaneous_candidate_state is not None:
                raise ValueError("unavailable state row cannot carry a candidate")
            if self.source_composite_fingerprint is not None or not self.stale_state:
                raise ValueError("unavailable state row must be stale without a source composite")
        if self.pending_target_state is None and self.transition_status is RegimeTransitionStatus.PENDING:
            raise ValueError("pending transition requires a target")
        if self.confirmation_sessions_remaining > self.required_confirmation_sessions:
            raise ValueError("confirmation remainder exceeds rule requirement")
        if self.initialization_status is RegimeInitializationStatus.AWAITING_CONFIRMATION:
            if self.confirmed_state is not None or self.pending_target_state is None:
                raise ValueError("bootstrap confirmation fields do not reconcile")
        if self.state_is_provisional and self.confirmed_state is None:
            raise ValueError("provisional state requires a confirmed label")
        return self


class MarketRegimeStateExplanationV1(BaseModel):
    """Fixed-template state explanation; no free-text model judgment is used."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal[
        "market-regime-opportunity-map-state-v1.0.0",
        "market-regime-opportunity-map-state-v1.0.1",
    ] = (
        "market-regime-opportunity-map-state-v1.0.1"
    )
    state_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    template_id: Literal["market_regime_state_transition_v1"] = "market_regime_state_transition_v1"
    composite: str | None
    candidate_state: RegimeState | None
    confirmed_state: RegimeState | None
    candidate_band_text: str
    transition_text: str
    supporting_dimension_ids: tuple[str, ...]
    conflicting_dimension_ids: tuple[str, ...]
    threshold_distances: tuple[StateThresholdDistanceV1, ...]
    confirmation_sessions_remaining: int = Field(ge=0)
    in_hysteresis_band: bool
    source_input_references: tuple[str, ...]
    reason_codes: tuple[str, ...]
    disclaimers: tuple[str, ...]


class StateOracleComparisonV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    calculation_version: Literal[
        "market-regime-opportunity-map-state-v1.0.0",
        "market-regime-opportunity-map-state-v1.0.1",
    ] = (
        "market-regime-opportunity-map-state-v1.0.1"
    )
    state_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    universe_id: str
    first_session: date
    last_session: date
    compared_session_count: int = Field(gt=0)
    mismatch_count: int = Field(ge=0)
    mismatches: tuple[str, ...]
    append_full_replay_match: bool
    restart_replay_match: bool
    input_permutation_match: bool
    future_prefix_stable: bool
    oracle_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
