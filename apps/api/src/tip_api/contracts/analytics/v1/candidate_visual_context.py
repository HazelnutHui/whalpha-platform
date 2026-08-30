"""Source-bound visual context for Candidate decision support."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .opportunity_candidate import CandidateOpportunityStage


VISUAL_CONTEXT_CONTRACT_VERSION = "candidate-visual-context/1.0"
VISUAL_CONTEXT_CALCULATION_VERSION = "candidate-visual-context-v1.0.0"
VISUAL_CONTEXT_PATH_SESSION_COUNT = 20


class VisualContextAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CandidatePricePathPointV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_date: date
    close: str

    @model_validator(mode="after")
    def close_is_valid(self) -> "CandidatePricePathPointV1":
        if _scale_ten(self.close, "price-path close") <= 0:
            raise ValueError("price-path close must be positive")
        return self


class CandidateVisualReferenceLevelsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_close: str
    sma_10: str
    sma_20: str
    prior_five_session_close_high: str
    prior_five_session_close_low: str
    reference_support_kind: Literal["sma20", "prior_five_session_close_low"] | None
    reference_support_value: str | None

    @model_validator(mode="after")
    def levels_are_valid(self) -> "CandidateVisualReferenceLevelsV1":
        for name in (
            "current_close",
            "sma_10",
            "sma_20",
            "prior_five_session_close_high",
            "prior_five_session_close_low",
        ):
            if _scale_ten(getattr(self, name), name) <= 0:
                raise ValueError("Candidate visual reference levels must be positive")
        if (self.reference_support_kind is None) != (self.reference_support_value is None):
            raise ValueError("Candidate visual support kind and value must share nullability")
        if self.reference_support_value is not None and _scale_ten(
            self.reference_support_value, "reference_support_value"
        ) <= 0:
            raise ValueError("Candidate visual support must be positive")
        return self


class CandidateObservedStateAgeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    final_stage: CandidateOpportunityStage
    first_observed_session: date
    observed_age_sessions: int = Field(ge=1)
    left_censored: bool
    current_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CandidateVisualContextV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[VISUAL_CONTEXT_CONTRACT_VERSION] = VISUAL_CONTEXT_CONTRACT_VERSION
    calculation_version: Literal[VISUAL_CONTEXT_CALCULATION_VERSION] = VISUAL_CONTEXT_CALCULATION_VERSION
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    source_candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    price_path_availability: VisualContextAvailability
    price_path: tuple[CandidatePricePathPointV1, ...]
    reference_levels: CandidateVisualReferenceLevelsV1 | None
    price_path_missing_reason_codes: tuple[str, ...]
    state_age_availability: VisualContextAvailability
    observed_state_age: CandidateObservedStateAgeV1 | None
    state_age_missing_reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def record_reconciles(self) -> "CandidateVisualContextV1":
        sessions = tuple(point.session_date for point in self.price_path)
        if self.price_path_availability is VisualContextAvailability.AVAILABLE:
            if (
                len(self.price_path) != VISUAL_CONTEXT_PATH_SESSION_COUNT
                or sessions != tuple(sorted(sessions))
                or len(set(sessions)) != len(sessions)
                or sessions[-1] != self.as_of_session
                or self.reference_levels is None
                or self.price_path_missing_reason_codes
                or self.price_path[-1].close != self.reference_levels.current_close
            ):
                raise ValueError("available Candidate visual path is incomplete")
        elif self.price_path or self.reference_levels is not None or not self.price_path_missing_reason_codes:
            raise ValueError("unavailable Candidate visual path must be empty with a reason")
        if self.state_age_availability is VisualContextAvailability.AVAILABLE:
            if self.observed_state_age is None or self.state_age_missing_reason_codes:
                raise ValueError("available Candidate state age is incomplete")
            if self.observed_state_age.first_observed_session > self.as_of_session:
                raise ValueError("Candidate observed state age starts after as-of")
        elif self.observed_state_age is not None or not self.state_age_missing_reason_codes:
            raise ValueError("unavailable Candidate state age must be empty with a reason")
        if visual_context_fingerprint(self, exclude={"logical_fingerprint"}) != self.logical_fingerprint:
            raise ValueError("Candidate visual-context record fingerprint mismatch")
        return self


class CandidateVisualContextBatchV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[VISUAL_CONTEXT_CONTRACT_VERSION] = VISUAL_CONTEXT_CONTRACT_VERSION
    calculation_version: Literal[VISUAL_CONTEXT_CALCULATION_VERSION] = VISUAL_CONTEXT_CALCULATION_VERSION
    as_of_session: date
    universe_id: str
    source_candidate_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_state_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(ge=0)
    price_path_availability_counts: dict[str, int]
    state_age_availability_counts: dict[str, int]
    records: tuple[CandidateVisualContextV1, ...]
    strategy_score_input: Literal[False] = False
    outcome_or_performance_claim: Literal[False] = False
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def batch_reconciles(self) -> "CandidateVisualContextBatchV1":
        ids = tuple(str(record.instrument_id) for record in self.records)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("Candidate visual-context rows must be unique and stable-ID ordered")
        if self.record_count != len(self.records):
            raise ValueError("Candidate visual-context record count differs")
        if self.price_path_availability_counts != dict(
            Counter(record.price_path_availability.value for record in self.records)
        ) or self.state_age_availability_counts != dict(
            Counter(record.state_age_availability.value for record in self.records)
        ):
            raise ValueError("Candidate visual-context availability counts differ")
        if any(
            record.as_of_session != self.as_of_session or record.universe_id != self.universe_id
            for record in self.records
        ):
            raise ValueError("Candidate visual-context row identity differs from batch")
        if visual_context_fingerprint(self, exclude={"logical_fingerprint"}) != self.logical_fingerprint:
            raise ValueError("Candidate visual-context batch fingerprint mismatch")
        return self


def visual_context_fingerprint(
    value: BaseModel | dict[str, object], *, exclude: set[str] | None = None
) -> str:
    payload = (
        value.model_dump(mode="json", exclude=exclude or set())
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key not in (exclude or set())}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _scale_ten(value: str, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a Decimal string") from exc
    if not parsed.is_finite() or value != format(parsed.quantize(Decimal("0.0000000001")), "f"):
        raise ValueError(f"{label} must be finite and use scale 10")
    return parsed
