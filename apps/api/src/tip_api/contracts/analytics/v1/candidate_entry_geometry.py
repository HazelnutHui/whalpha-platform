"""Typed additive entry-location and chase-risk shadow contracts."""

from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.parameters.market_regime.candidate_entry_v1_0_0 import (
    ENTRY_GEOMETRY_CALCULATION_VERSION,
    ENTRY_GEOMETRY_CONTRACT_VERSION,
    ENTRY_GEOMETRY_PARAMETER_SET_ID,
)

from .opportunity_candidate import CandidateOpportunityStage


class EntryGeometryAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CandidateExtensionRisk(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"
    UNAVAILABLE = "unavailable"


class CandidateTechnicalSetup(StrEnum):
    BREAKOUT_CONFIRMED = "breakout_confirmed"
    BREAKOUT_WATCH = "breakout_watch"
    PULLBACK = "pullback"
    STRONG_BUT_EXTENDED = "strong_but_extended"
    NO_VIABLE_SETUP = "no_viable_setup"
    UNAVAILABLE = "unavailable"


class CandidateEntryReviewPosture(StrEnum):
    TECHNICAL_REVIEW_READY = "technical_review_ready"
    MONITOR_FOR_TRIGGER = "monitor_for_trigger"
    WAIT_FOR_RESET = "wait_for_reset"
    DEPRIORITIZED = "deprioritized"
    NOT_ASSESSABLE = "not_assessable"


class CandidateEntryGeometryMetricsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    availability: EntryGeometryAvailability
    close: str | None
    sma_10: str | None
    sma_20: str | None
    atr_14: str | None
    return_3: str | None
    return_5: str | None
    close_to_sma_10_atr: str | None
    close_to_sma_20_atr: str | None
    move_5_volatility_units: str | None
    consecutive_up_sessions: int | None = Field(default=None, ge=0, le=5)
    current_gap_atr: str | None
    current_range_atr: str | None
    current_close_location: str | None
    current_volume_ratio: str | None
    prior_five_session_close_high: str | None
    prior_five_session_close_low: str | None
    breakout_distance_atr: str | None
    pullback_from_prior_high_atr: str | None
    reference_support_kind: Literal["sma20", "prior_five_session_close_low"] | None
    reference_support_value: str | None
    reference_support_distance_pct: str | None
    missing_reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def availability_reconciles(self) -> "CandidateEntryGeometryMetricsV1":
        required = (
            self.close,
            self.sma_10,
            self.sma_20,
            self.atr_14,
            self.return_3,
            self.return_5,
            self.close_to_sma_10_atr,
            self.close_to_sma_20_atr,
            self.move_5_volatility_units,
            self.consecutive_up_sessions,
            self.current_gap_atr,
            self.current_range_atr,
            self.current_close_location,
            self.current_volume_ratio,
            self.prior_five_session_close_high,
            self.prior_five_session_close_low,
            self.breakout_distance_atr,
            self.pullback_from_prior_high_atr,
        )
        if self.availability is EntryGeometryAvailability.AVAILABLE:
            if any(item is None for item in required) or self.missing_reason_codes:
                raise ValueError("available entry geometry requires all fixed technical facts")
            if (self.reference_support_kind is None) != (self.reference_support_value is None):
                raise ValueError("reference support kind and value must share nullability")
            if (self.reference_support_value is None) != (self.reference_support_distance_pct is None):
                raise ValueError("reference support value and distance must share nullability")
            decimals = {
                name: _scale_ten_decimal(getattr(self, name), name)
                for name in (
                    "close",
                    "sma_10",
                    "sma_20",
                    "atr_14",
                    "return_3",
                    "return_5",
                    "close_to_sma_10_atr",
                    "close_to_sma_20_atr",
                    "move_5_volatility_units",
                    "current_gap_atr",
                    "current_range_atr",
                    "current_close_location",
                    "current_volume_ratio",
                    "prior_five_session_close_high",
                    "prior_five_session_close_low",
                    "breakout_distance_atr",
                    "pullback_from_prior_high_atr",
                )
            }
            if any(decimals[name] <= 0 for name in ("close", "sma_10", "sma_20", "atr_14", "current_range_atr")):
                raise ValueError("entry-geometry price, average, ATR, and range facts must be positive")
            if not Decimal("0") <= decimals["current_close_location"] <= Decimal("1"):
                raise ValueError("entry-geometry close location must be within [0,1]")
            if decimals["current_volume_ratio"] < 0:
                raise ValueError("entry-geometry volume ratio cannot be negative")
            if self.reference_support_value is not None:
                support = _scale_ten_decimal(self.reference_support_value, "reference_support_value")
                distance = _scale_ten_decimal(self.reference_support_distance_pct, "reference_support_distance_pct")
                if support <= 0 or distance < 0:
                    raise ValueError("entry-geometry reference support must be positive with nonnegative distance")
        else:
            if any(item is not None for item in required):
                raise ValueError("unavailable entry geometry cannot carry partial technical facts")
            if any(
                item is not None
                for item in (
                    self.reference_support_kind,
                    self.reference_support_value,
                    self.reference_support_distance_pct,
                )
            ):
                raise ValueError("unavailable entry geometry cannot carry reference support")
            if not self.missing_reason_codes:
                raise ValueError("unavailable entry geometry requires a reason")
        return self


class CandidateEntryGeometryV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[ENTRY_GEOMETRY_CONTRACT_VERSION] = ENTRY_GEOMETRY_CONTRACT_VERSION
    calculation_version: Literal[ENTRY_GEOMETRY_CALCULATION_VERSION] = ENTRY_GEOMETRY_CALCULATION_VERSION
    parameter_set_id: Literal[ENTRY_GEOMETRY_PARAMETER_SET_ID] = ENTRY_GEOMETRY_PARAMETER_SET_ID
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    candidate_stage: CandidateOpportunityStage | None
    candidate_base_score: str | None
    relative_strength_component_score: str | None
    trend_component_score: str | None
    source_candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    metrics: CandidateEntryGeometryMetricsV1
    volume_climax_risk_candidate: bool | None
    extension_risk: CandidateExtensionRisk
    technical_setup: CandidateTechnicalSetup
    review_posture: CandidateEntryReviewPosture
    first_rejection_code: str | None
    why_now_codes: tuple[str, ...]
    supporting_fact_codes: tuple[str, ...]
    counterevidence_codes: tuple[str, ...]
    what_would_make_reviewable_codes: tuple[str, ...]
    technical_invalidation_codes: tuple[str, ...]
    required_manual_check_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def posture_reconciles(self) -> "CandidateEntryGeometryV1":
        if self.metrics.availability is EntryGeometryAvailability.UNAVAILABLE:
            if (
                self.extension_risk is not CandidateExtensionRisk.UNAVAILABLE
                or self.technical_setup is not CandidateTechnicalSetup.UNAVAILABLE
                or self.review_posture is not CandidateEntryReviewPosture.NOT_ASSESSABLE
                or self.volume_climax_risk_candidate is not None
                or self.first_rejection_code is None
            ):
                raise ValueError("unavailable entry facts require an unavailable/not-assessable result")
            return self
        if self.extension_risk is CandidateExtensionRisk.UNAVAILABLE or self.volume_climax_risk_candidate is None:
            raise ValueError("available entry facts require an extension and climax assessment")
        if self.technical_setup in {
            CandidateTechnicalSetup.BREAKOUT_CONFIRMED,
            CandidateTechnicalSetup.PULLBACK,
        }:
            if self.review_posture is not CandidateEntryReviewPosture.TECHNICAL_REVIEW_READY:
                raise ValueError("confirmed technical setup must route to technical review")
            if self.extension_risk in {CandidateExtensionRisk.HIGH, CandidateExtensionRisk.EXTREME}:
                raise ValueError("high extension cannot be called technical-review ready")
            if self.first_rejection_code is not None:
                raise ValueError("technical-review-ready setup cannot carry a rejection")
        elif self.first_rejection_code is None:
            raise ValueError("a non-ready entry posture requires its first rejection")
        if self.technical_setup is CandidateTechnicalSetup.BREAKOUT_WATCH:
            if self.review_posture is not CandidateEntryReviewPosture.MONITOR_FOR_TRIGGER:
                raise ValueError("breakout watch must monitor for a trigger")
        if self.technical_setup is CandidateTechnicalSetup.STRONG_BUT_EXTENDED:
            if self.review_posture is not CandidateEntryReviewPosture.WAIT_FOR_RESET:
                raise ValueError("strong but extended must wait for reset")
            if self.extension_risk not in {CandidateExtensionRisk.HIGH, CandidateExtensionRisk.EXTREME}:
                raise ValueError("strong but extended requires high or extreme extension")
        if self.technical_setup is CandidateTechnicalSetup.UNAVAILABLE:
            raise ValueError("available entry facts cannot emit unavailable setup")
        return self


class CandidateEntryGeometryBatchV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[ENTRY_GEOMETRY_CONTRACT_VERSION] = ENTRY_GEOMETRY_CONTRACT_VERSION
    calculation_version: Literal[ENTRY_GEOMETRY_CALCULATION_VERSION] = ENTRY_GEOMETRY_CALCULATION_VERSION
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    universe_id: str
    source_candidate_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessed_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    extension_counts: dict[str, int]
    setup_counts: dict[str, int]
    posture_counts: dict[str, int]
    records: tuple[CandidateEntryGeometryV1, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def batch_reconciles(self) -> "CandidateEntryGeometryBatchV1":
        keys = tuple(str(item.instrument_id) for item in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("entry-geometry records must be unique and stable-ID ordered")
        expected_assessed = sum(
            item.metrics.availability is EntryGeometryAvailability.AVAILABLE for item in self.records
        )
        if self.assessed_count != expected_assessed or self.unavailable_count != len(self.records) - expected_assessed:
            raise ValueError("entry-geometry availability counts do not reconcile")
        if self.extension_counts != dict(Counter(item.extension_risk.value for item in self.records)):
            raise ValueError("entry-geometry extension counts do not reconcile")
        if self.setup_counts != dict(Counter(item.technical_setup.value for item in self.records)):
            raise ValueError("entry-geometry setup counts do not reconcile")
        if self.posture_counts != dict(Counter(item.review_posture.value for item in self.records)):
            raise ValueError("entry-geometry posture counts do not reconcile")
        if any(item.as_of_session != self.as_of_session or item.universe_id != self.universe_id for item in self.records):
            raise ValueError("entry-geometry record identity must match its batch")
        return self


def _scale_ten_decimal(value: str | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"{label} is required")
    try:
        parsed = Decimal(value)
    except Exception as exc:
        raise ValueError(f"{label} must be a Decimal string") from exc
    if not parsed.is_finite() or value != format(parsed.quantize(Decimal("0.0000000001")), "f"):
        raise ValueError(f"{label} must be finite and use scale 10")
    return parsed
