"""Outcome-blind development-coverage census for Strong-Leader Pullback."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime


STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_CONTRACT_VERSION = (
    "strong-leader-pullback-development-coverage-census/1.0"
)
STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_POLICY_VERSION = (
    "strong-leader-pullback-development-admission/1.0.0"
)
STRONG_LEADER_PULLBACK_RECONSTRUCTION_TIER = (
    "reconstructed_point_in_time_latest_vintage"
)
STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION = date(2025, 6, 23)
STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION = date(2026, 8, 12)
STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT = 287
STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE = (
    "provider_classified_common_shares_v1"
)
STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY = (
    "provider-form-complete-base-point-in-time-v3"
)

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_REQUIRED_FAMILIES = (
    "adjustment_ledger",
    "corporate_action",
    "eod_price_bar",
    "instrument_lifecycle",
    "point_in_time_identity",
    "universe_membership",
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DevelopmentCoverageEvidenceStatus(StrEnum):
    COMPLETE_RECONSTRUCTION_INPUT = "complete_reconstruction_input"
    PARTIAL_OUTCOME_RECONCILIATION_ONLY = (
        "partial_outcome_reconciliation_only"
    )
    UNAVAILABLE = "unavailable"


class DevelopmentCoverageReasonCountV1(FrozenModel):
    reason_code: str = Field(min_length=1)
    count: int = Field(ge=1)

    @field_validator("reason_code")
    @classmethod
    def normalized_reason(cls, value: str) -> str:
        normalized = value.strip()
        if value != normalized or any(character.isspace() for character in value):
            raise ValueError("coverage reason code must be normalized")
        return value


class DevelopmentCoverageDatasetEvidenceV1(FrozenModel):
    family: Literal[
        "adjustment_ledger",
        "corporate_action",
        "eod_price_bar",
        "instrument_lifecycle",
        "point_in_time_identity",
        "universe_membership",
    ]
    status: DevelopmentCoverageEvidenceStatus
    session_count: int = Field(ge=0)
    record_count: int | None = Field(default=None, ge=0)
    logical_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    physical_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def ordered_reasons(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("dataset reason codes must be an ordered collection")
        reasons = tuple(str(item).strip() for item in value)
        if not reasons or reasons != tuple(sorted(set(reasons))):
            raise ValueError("dataset reason codes must be unique and sorted")
        return reasons

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "DevelopmentCoverageDatasetEvidenceV1":
        if self.status is DevelopmentCoverageEvidenceStatus.UNAVAILABLE:
            if (
                self.session_count != 0
                or self.record_count is not None
                or self.logical_fingerprint is not None
                or self.physical_fingerprint is not None
            ):
                raise ValueError("unavailable dataset cannot claim physical evidence")
        elif self.logical_fingerprint is None or self.physical_fingerprint is None:
            raise ValueError("available dataset requires logical and physical evidence")
        return self


class StrongLeaderPullbackDevelopmentSessionCoverageV1(FrozenModel):
    session_date: date
    membership_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    membership_physical_sha256: str = Field(pattern=_SHA256_PATTERN)
    membership_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    evaluated_base_count: int = Field(ge=1)
    primary_included_count: int = Field(ge=0)
    primary_excluded_count: int = Field(ge=0)
    primary_quarantined_count: int = Field(ge=0)
    raw_feature_path_complete_count: int = Field(ge=0)
    sparse_clear_split_exposure_count: int = Field(ge=0)
    split_quarantined_path_count: int = Field(ge=0)
    absent_row_neutrality_unproven_path_count: int = Field(ge=0)
    lifecycle_unavailable_path_count: int = Field(ge=0)
    all_required_evidence_complete_count: Literal[0] = 0
    reason_counts: tuple[DevelopmentCoverageReasonCountV1, ...]

    @model_validator(mode="after")
    def session_reconciles(
        self,
    ) -> "StrongLeaderPullbackDevelopmentSessionCoverageV1":
        if self.evaluated_base_count != (
            self.primary_included_count
            + self.primary_excluded_count
            + self.primary_quarantined_count
        ):
            raise ValueError("session Membership counts differ from evaluated base")
        if (
            self.raw_feature_path_complete_count != self.primary_included_count
            or self.absent_row_neutrality_unproven_path_count
            != self.primary_included_count
            or self.lifecycle_unavailable_path_count != self.primary_included_count
            or self.sparse_clear_split_exposure_count > self.primary_included_count
            or self.split_quarantined_path_count > self.primary_included_count
        ):
            raise ValueError("session feature-path coverage counts differ")
        _validate_reason_counts(self.reason_counts)
        return self


class StrongLeaderPullbackDevelopmentInstrumentCoverageV1(FrozenModel):
    instrument_id: UUID
    evaluated_session_count: int = Field(ge=1)
    absent_from_evaluated_base_count: int = Field(ge=0)
    included_session_count: int = Field(ge=0)
    excluded_session_count: int = Field(ge=0)
    quarantined_session_count: int = Field(ge=0)
    raw_feature_path_complete_count: int = Field(ge=0)
    sparse_clear_split_exposure_count: int = Field(ge=0)
    split_quarantined_path_count: int = Field(ge=0)
    absent_row_neutrality_unproven_path_count: int = Field(ge=0)
    lifecycle_unavailable_path_count: int = Field(ge=0)
    all_required_evidence_complete_count: Literal[0] = 0
    first_evaluated_session: date
    last_evaluated_session: date
    first_included_session: date | None = None
    last_included_session: date | None = None
    reason_counts: tuple[DevelopmentCoverageReasonCountV1, ...]

    @model_validator(mode="after")
    def instrument_reconciles(
        self,
    ) -> "StrongLeaderPullbackDevelopmentInstrumentCoverageV1":
        if self.evaluated_session_count != (
            self.included_session_count
            + self.excluded_session_count
            + self.quarantined_session_count
        ):
            raise ValueError("instrument Membership counts differ")
        if (
            self.evaluated_session_count + self.absent_from_evaluated_base_count
            != STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT
        ):
            raise ValueError("instrument interval coverage differs")
        if (
            self.first_evaluated_session > self.last_evaluated_session
            or self.first_evaluated_session
            < STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION
            or self.last_evaluated_session
            > STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
        ):
            raise ValueError("instrument evaluated-session bounds differ")
        if self.included_session_count == 0:
            if self.first_included_session is not None or self.last_included_session is not None:
                raise ValueError("never-included instrument has included-session bounds")
        elif (
            self.first_included_session is None
            or self.last_included_session is None
            or self.first_included_session > self.last_included_session
            or self.first_included_session < self.first_evaluated_session
            or self.last_included_session > self.last_evaluated_session
        ):
            raise ValueError("included instrument lacks valid session bounds")
        if (
            self.raw_feature_path_complete_count != self.included_session_count
            or self.absent_row_neutrality_unproven_path_count
            != self.included_session_count
            or self.lifecycle_unavailable_path_count != self.included_session_count
            or self.sparse_clear_split_exposure_count > self.included_session_count
            or self.split_quarantined_path_count > self.included_session_count
        ):
            raise ValueError("instrument feature-path coverage counts differ")
        _validate_reason_counts(self.reason_counts)
        return self


class StrongLeaderPullbackDevelopmentCoverageCensusV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_CONTRACT_VERSION
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_CONTRACT_VERSION
    policy_version: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_POLICY_VERSION
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_POLICY_VERSION
    evidence_tier: Literal[
        STRONG_LEADER_PULLBACK_RECONSTRUCTION_TIER
    ] = STRONG_LEADER_PULLBACK_RECONSTRUCTION_TIER
    as_operated: Literal[False] = False
    source_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    calculated_at: datetime
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str = Field(min_length=1)
    first_session: date = STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION
    last_session: date = STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
    session_count: Literal[
        STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT
    ] = STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT
    universe_id: Literal[
        STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
    ] = STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
    membership_methodology_version: Literal[
        STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY
    ] = STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY
    dataset_evidence: tuple[DevelopmentCoverageDatasetEvidenceV1, ...]
    instrument_count: int = Field(ge=1)
    primary_decision_count: int = Field(ge=1)
    primary_included_count: int = Field(ge=0)
    primary_excluded_count: int = Field(ge=0)
    primary_quarantined_count: int = Field(ge=0)
    raw_feature_path_complete_count: int = Field(ge=0)
    sparse_clear_split_exposure_count: int = Field(ge=0)
    split_quarantined_path_count: int = Field(ge=0)
    absent_row_neutrality_unproven_path_count: int = Field(ge=0)
    lifecycle_unavailable_path_count: int = Field(ge=0)
    all_required_evidence_complete_count: Literal[0] = 0
    sessions: tuple[StrongLeaderPullbackDevelopmentSessionCoverageV1, ...]
    instruments: tuple[StrongLeaderPullbackDevelopmentInstrumentCoverageV1, ...]
    contains_strategy_triggers: Literal[False] = False
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    coverage_threshold_selected: Literal[False] = False
    admitted_cohort_selected: Literal[False] = False
    development_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("calculated_at")
    @classmethod
    def calculated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def census_reconciles(
        self,
    ) -> "StrongLeaderPullbackDevelopmentCoverageCensusV1":
        families = tuple(item.family for item in self.dataset_evidence)
        if families != _REQUIRED_FAMILIES:
            raise ValueError("census dataset evidence family set or order differs")
        expected_statuses = {
            "adjustment_ledger": (
                DevelopmentCoverageEvidenceStatus.PARTIAL_OUTCOME_RECONCILIATION_ONLY
            ),
            "corporate_action": (
                DevelopmentCoverageEvidenceStatus.PARTIAL_OUTCOME_RECONCILIATION_ONLY
            ),
            "eod_price_bar": (
                DevelopmentCoverageEvidenceStatus.COMPLETE_RECONSTRUCTION_INPUT
            ),
            "instrument_lifecycle": DevelopmentCoverageEvidenceStatus.UNAVAILABLE,
            "point_in_time_identity": (
                DevelopmentCoverageEvidenceStatus.COMPLETE_RECONSTRUCTION_INPUT
            ),
            "universe_membership": (
                DevelopmentCoverageEvidenceStatus.COMPLETE_RECONSTRUCTION_INPUT
            ),
        }
        if any(
            item.status is not expected_statuses[item.family]
            for item in self.dataset_evidence
        ):
            raise ValueError("census dataset evidence status differs")
        if (
            self.first_session != STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION
            or self.last_session != STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
        ):
            raise ValueError("census fixed policy interval differs")
        session_dates = tuple(item.session_date for item in self.sessions)
        if (
            len(self.sessions) != self.session_count
            or session_dates != tuple(sorted(set(session_dates)))
            or session_dates[0] != self.first_session
            or session_dates[-1] != self.last_session
        ):
            raise ValueError("census session interval differs")
        instrument_ids = tuple(str(item.instrument_id) for item in self.instruments)
        if (
            len(self.instruments) != self.instrument_count
            or instrument_ids != tuple(sorted(set(instrument_ids)))
        ):
            raise ValueError("census instruments must be unique and stable-ID sorted")
        session_totals = _coverage_totals(self.sessions)
        instrument_totals = _coverage_totals(self.instruments)
        expected = (
            self.primary_included_count,
            self.primary_excluded_count,
            self.primary_quarantined_count,
            self.raw_feature_path_complete_count,
            self.sparse_clear_split_exposure_count,
            self.split_quarantined_path_count,
            self.absent_row_neutrality_unproven_path_count,
            self.lifecycle_unavailable_path_count,
        )
        if session_totals != expected or instrument_totals != expected:
            raise ValueError("census session and instrument aggregates differ")
        if self.primary_decision_count != sum(
            item.evaluated_base_count for item in self.sessions
        ) or self.primary_decision_count != sum(expected[:3]):
            raise ValueError("census Primary decision count differs")
        if coverage_census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("coverage census fingerprint mismatch")
        return self


def coverage_census_fingerprint(value: BaseModel) -> str:
    payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _validate_reason_counts(
    values: tuple[DevelopmentCoverageReasonCountV1, ...],
) -> None:
    codes = tuple(item.reason_code for item in values)
    if codes != tuple(sorted(set(codes))):
        raise ValueError("coverage reason counts must be unique and sorted")


def _coverage_totals(values: tuple[BaseModel, ...]) -> tuple[int, ...]:
    included_field = (
        "primary_included_count"
        if values and isinstance(
            values[0], StrongLeaderPullbackDevelopmentSessionCoverageV1
        )
        else "included_session_count"
    )
    excluded_field = (
        "primary_excluded_count"
        if values and isinstance(
            values[0], StrongLeaderPullbackDevelopmentSessionCoverageV1
        )
        else "excluded_session_count"
    )
    quarantined_field = (
        "primary_quarantined_count"
        if values and isinstance(
            values[0], StrongLeaderPullbackDevelopmentSessionCoverageV1
        )
        else "quarantined_session_count"
    )
    return (
        sum(getattr(item, included_field) for item in values),
        sum(getattr(item, excluded_field) for item in values),
        sum(getattr(item, quarantined_field) for item in values),
        sum(item.raw_feature_path_complete_count for item in values),
        sum(item.sparse_clear_split_exposure_count for item in values),
        sum(item.split_quarantined_path_count for item in values),
        sum(item.absent_row_neutrality_unproven_path_count for item in values),
        sum(item.lifecycle_unavailable_path_count for item in values),
    )
