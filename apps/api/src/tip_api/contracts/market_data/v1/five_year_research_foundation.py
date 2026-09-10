"""Typed coverage census for the Dell-owned five-year research foundation."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string


CONTRACT_VERSION = "five-year-research-foundation-census/1.0"
SCOPE_ID = "us-equity-five-year-point-in-time-v1"
_SHA256 = r"^[0-9a-f]{64}$"


class FiveYearFoundationFamily(StrEnum):
    EOD_PRICE_BAR = "eod_price_bar"
    POINT_IN_TIME_IDENTITY = "point_in_time_identity"
    POINT_IN_TIME_IDENTITY_SOURCE = "point_in_time_identity_source_observation"
    UNIVERSE_MEMBERSHIP = "universe_membership"
    CORPORATE_ACTION_SOURCE = "corporate_action_source_observation"
    CORPORATE_ACTION = "corporate_action"
    INSTRUMENT_LIFECYCLE = "instrument_lifecycle"
    ADJUSTMENT_LEDGER = "adjustment_ledger"
    POINT_IN_TIME_CLASSIFICATION = "point_in_time_classification"
    POINT_IN_TIME_FUNDAMENTALS = "point_in_time_fundamentals"
    HISTORICAL_COVERAGE_EVIDENCE = "historical_coverage_evidence"
    HISTORICAL_COVERAGE = "historical_coverage"


FIVE_YEAR_FOUNDATION_FAMILY_ORDER = tuple(FiveYearFoundationFamily)

FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES = frozenset(
    {
        FiveYearFoundationFamily.EOD_PRICE_BAR,
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY,
        FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP,
        FiveYearFoundationFamily.CORPORATE_ACTION,
        FiveYearFoundationFamily.INSTRUMENT_LIFECYCLE,
        FiveYearFoundationFamily.ADJUSTMENT_LEDGER,
        FiveYearFoundationFamily.HISTORICAL_COVERAGE,
    }
)

FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES = (
    FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES
    | frozenset(
        {
            FiveYearFoundationFamily.POINT_IN_TIME_CLASSIFICATION,
            FiveYearFoundationFamily.POINT_IN_TIME_FUNDAMENTALS,
        }
    )
)


class FiveYearFoundationCoverageStatus(StrEnum):
    ABSENT = "absent"
    PARTIAL = "partial"
    COVERAGE_UNPUBLISHED = "coverage_unpublished"
    COMPLETE = "complete"


class FiveYearFoundationEvidenceTier(StrEnum):
    MISSING = "missing"
    SOURCE_OBSERVATION = "source_observation"
    RECONSTRUCTED_LATEST_VINTAGE = "reconstructed_latest_vintage"
    AS_OPERATED = "as_operated"
    MIXED = "mixed"
    DERIVED_CANONICAL = "derived_canonical"


class FiveYearFoundationCensusStatus(StrEnum):
    SOURCE_INCOMPLETE = "source_incomplete"
    QUARANTINED = "quarantined"
    COMPLETE = "complete"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FiveYearFoundationFamilyCensusV1(FrozenContract):
    family: FiveYearFoundationFamily
    program_required: bool
    price_strategy_required: bool
    coverage_status: FiveYearFoundationCoverageStatus
    evidence_tier: FiveYearFoundationEvidenceTier
    custody_state: str
    target_session_count: int | None = Field(default=None, ge=1)
    covered_session_count: int | None = Field(default=None, ge=0)
    missing_session_count: int | None = Field(default=None, ge=0)
    first_observed_session: date | None = None
    last_observed_session: date | None = None
    record_count: int | None = Field(default=None, ge=0)
    quarantined_record_count: int | None = Field(default=None, ge=0)
    source_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator(
        "first_observed_session", "last_observed_session", mode="before"
    )
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session fields must contain dates")
        return value

    @field_validator("custody_state", mode="before")
    @classmethod
    def required_text(cls, value: str) -> str:
        return normalize_required_string(value, field_name="custody_state")

    @field_validator("source_ids", "reason_codes", mode="before")
    @classmethod
    def normalized_codes(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError(f"{info.field_name} must be an ordered collection")
        normalized = tuple(
            normalize_required_string(item, field_name=info.field_name)
            for item in value
        )
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError(f"{info.field_name} must be unique and sorted")
        return normalized

    @model_validator(mode="after")
    def coverage_reconciles(self) -> "FiveYearFoundationFamilyCensusV1":
        counts = (
            self.target_session_count,
            self.covered_session_count,
            self.missing_session_count,
        )
        if any(value is not None for value in counts):
            if any(value is None for value in counts):
                raise ValueError("session-grained coverage requires all session counts")
            assert self.target_session_count is not None
            assert self.covered_session_count is not None
            assert self.missing_session_count is not None
            if self.covered_session_count + self.missing_session_count != self.target_session_count:
                raise ValueError("family session counts do not reconcile")
        if (
            self.quarantined_record_count is not None
            and self.record_count is not None
            and self.quarantined_record_count > self.record_count
        ):
            raise ValueError("quarantined count cannot exceed record count")
        if (self.first_observed_session is None) != (
            self.last_observed_session is None
        ):
            raise ValueError("observed session bounds must be both present or absent")
        if (
            self.first_observed_session is not None
            and self.last_observed_session is not None
            and self.last_observed_session < self.first_observed_session
        ):
            raise ValueError("observed session range is reversed")
        if self.coverage_status is FiveYearFoundationCoverageStatus.ABSENT:
            if self.record_count not in (None, 0) or self.covered_session_count not in (None, 0):
                raise ValueError("absent family cannot carry covered evidence")
            if self.evidence_tier is not FiveYearFoundationEvidenceTier.MISSING:
                raise ValueError("absent family must use missing evidence tier")
        if self.coverage_status is FiveYearFoundationCoverageStatus.COMPLETE:
            if self.evidence_tier is FiveYearFoundationEvidenceTier.MISSING:
                raise ValueError("complete family cannot use missing evidence tier")
            if self.missing_session_count not in (None, 0):
                raise ValueError("complete family cannot have missing sessions")
        return self


class FiveYearResearchFoundationCensusV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["five-year-research-foundation-census/1.0"] = (
        CONTRACT_VERSION
    )
    scope_id: Literal["us-equity-five-year-point-in-time-v1"] = SCOPE_ID
    target_definition: Literal["rolling_five_calendar_years"] = (
        "rolling_five_calendar_years"
    )
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str
    target_anchor_date: date
    first_target_session: date
    last_target_session: date
    target_session_count: int = Field(ge=1)
    families: tuple[FiveYearFoundationFamilyCensusV1, ...] = Field(min_length=12)
    status: FiveYearFoundationCensusStatus
    program_complete: bool
    price_strategy_foundation_complete: bool
    program_blocking_families: tuple[FiveYearFoundationFamily, ...]
    price_strategy_blocking_families: tuple[FiveYearFoundationFamily, ...]
    performance_claims_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("target_anchor_date", "first_target_session", "last_target_session", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("target fields must contain dates")
        return value

    @field_validator("calendar_version", mode="before")
    @classmethod
    def required_text(cls, value: str) -> str:
        return normalize_required_string(value, field_name="calendar_version")

    @model_validator(mode="after")
    def census_reconciles(self) -> "FiveYearResearchFoundationCensusV1":
        family_order = tuple(item.family for item in self.families)
        if family_order != FIVE_YEAR_FOUNDATION_FAMILY_ORDER:
            raise ValueError("five-year foundation family set is incomplete or unordered")
        for item in self.families:
            if item.program_required != (
                item.family in FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES
            ):
                raise ValueError("family program-required policy differs")
            if item.price_strategy_required != (
                item.family in FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES
            ):
                raise ValueError("family price-strategy-required policy differs")
        if self.first_target_session < self.target_anchor_date:
            raise ValueError("first target session precedes target anchor")
        if self.last_target_session < self.first_target_session:
            raise ValueError("target session range is reversed")
        expected_program_blockers = tuple(
            item.family
            for item in self.families
            if item.program_required
            and item.coverage_status is not FiveYearFoundationCoverageStatus.COMPLETE
        )
        expected_price_blockers = tuple(
            item.family
            for item in self.families
            if item.price_strategy_required
            and item.coverage_status is not FiveYearFoundationCoverageStatus.COMPLETE
        )
        if self.program_blocking_families != expected_program_blockers:
            raise ValueError("program blocker set differs from family evidence")
        if self.price_strategy_blocking_families != expected_price_blockers:
            raise ValueError("price-strategy blocker set differs from family evidence")
        if self.program_complete != (not expected_program_blockers):
            raise ValueError("program completion differs from blockers")
        if self.price_strategy_foundation_complete != (not expected_price_blockers):
            raise ValueError("price-strategy completion differs from blockers")
        expected_status = (
            FiveYearFoundationCensusStatus.COMPLETE
            if not expected_program_blockers
            else FiveYearFoundationCensusStatus.QUARANTINED
            if any(
                item.quarantined_record_count
                for item in self.families
                if item.program_required
            )
            else FiveYearFoundationCensusStatus.SOURCE_INCOMPLETE
        )
        if self.status is not expected_status:
            raise ValueError("census status differs from family evidence")
        if five_year_foundation_census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("five-year foundation fingerprint differs")
        return self


def build_five_year_research_foundation_census(
    *,
    calendar_version: str,
    target_anchor_date: date,
    target_sessions: tuple[date, ...],
    families: tuple[FiveYearFoundationFamilyCensusV1, ...],
) -> FiveYearResearchFoundationCensusV1:
    if target_sessions != tuple(sorted(set(target_sessions))):
        raise ValueError("target sessions must be unique and ordered")
    if not target_sessions:
        raise ValueError("target sessions must not be empty")
    program_blockers = tuple(
        item.family
        for item in families
        if item.program_required
        and item.coverage_status is not FiveYearFoundationCoverageStatus.COMPLETE
    )
    price_blockers = tuple(
        item.family
        for item in families
        if item.price_strategy_required
        and item.coverage_status is not FiveYearFoundationCoverageStatus.COMPLETE
    )
    status = (
        FiveYearFoundationCensusStatus.COMPLETE
        if not program_blockers
        else FiveYearFoundationCensusStatus.QUARANTINED
        if any(
            item.quarantined_record_count
            for item in families
            if item.program_required
        )
        else FiveYearFoundationCensusStatus.SOURCE_INCOMPLETE
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "contract_version": CONTRACT_VERSION,
        "scope_id": SCOPE_ID,
        "target_definition": "rolling_five_calendar_years",
        "calendar_id": "XNYS",
        "calendar_version": calendar_version,
        "target_anchor_date": target_anchor_date,
        "first_target_session": target_sessions[0],
        "last_target_session": target_sessions[-1],
        "target_session_count": len(target_sessions),
        "families": families,
        "status": status,
        "program_complete": not program_blockers,
        "price_strategy_foundation_complete": not price_blockers,
        "program_blocking_families": program_blockers,
        "price_strategy_blocking_families": price_blockers,
        "performance_claims_authorized": False,
        "external_request_count": 0,
        "canonical_write_count": 0,
        "production_write_count": 0,
    }
    return FiveYearResearchFoundationCensusV1(
        **payload,
        logical_fingerprint=five_year_foundation_census_fingerprint(payload),
    )


def five_year_foundation_census_fingerprint(
    value: FiveYearResearchFoundationCensusV1 | dict[str, Any],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, FiveYearResearchFoundationCensusV1)
        else value
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=_json_default,
        ).encode("utf-8")
    ).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"unsupported fingerprint value: {type(value).__name__}")
