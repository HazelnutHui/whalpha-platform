"""Missingness-only development-admission decision for Strong-Leader Pullback."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime

from .candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_CONTRACT_VERSION,
    STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_POLICY_VERSION,
    STRONG_LEADER_PULLBACK_RECONSTRUCTION_TIER,
)
from .candidate_strategy_research import (
    STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
)


STRONG_LEADER_PULLBACK_DEVELOPMENT_ADMISSION_CONTRACT_VERSION = (
    "strong-leader-pullback-development-admission-decision/1.0"
)
STRONG_LEADER_PULLBACK_DEVELOPMENT_ADMISSION_POLICY_VERSION = (
    "strong-leader-pullback-development-admission/1.1.0"
)
STRONG_LEADER_PULLBACK_DEVELOPMENT_MINIMUM_SESSIONS = 252
STRONG_LEADER_PULLBACK_DEVELOPMENT_COMPLETENESS_THRESHOLD_BPS = 10_000

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DevelopmentAdmissionDecisionStatus(StrEnum):
    REJECTED_CURRENT_EVIDENCE = "rejected_current_evidence"


class StrongLeaderPullbackDevelopmentAdmissionDecisionV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_ADMISSION_CONTRACT_VERSION
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_ADMISSION_CONTRACT_VERSION
    policy_version: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_ADMISSION_POLICY_VERSION
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_ADMISSION_POLICY_VERSION
    evidence_tier: Literal[
        STRONG_LEADER_PULLBACK_RECONSTRUCTION_TIER
    ] = STRONG_LEADER_PULLBACK_RECONSTRUCTION_TIER
    as_operated: Literal[False] = False
    decision_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    decided_at: datetime
    census_contract_version: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_CONTRACT_VERSION
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_CONTRACT_VERSION
    census_policy_version: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_POLICY_VERSION
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_CENSUS_POLICY_VERSION
    census_source_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    census_calculated_at: datetime
    census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    census_physical_sha256: str = Field(pattern=_SHA256_PATTERN)
    experiment_id: Literal[STRONG_STOCK_PULLBACK_EXPERIMENT_ID] = (
        STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    first_session: date
    last_session: date
    observed_session_count: int = Field(ge=1)
    raw_candidate_session_count: int = Field(ge=0)
    zero_included_session_count: int = Field(ge=0)
    complete_cross_section_session_count: int = Field(ge=0)
    incomplete_cross_section_session_count: int = Field(ge=0)
    raw_feature_path_count: int = Field(ge=0)
    all_required_evidence_complete_path_count: int = Field(ge=0)
    absent_row_neutrality_unproven_path_count: int = Field(ge=0)
    lifecycle_unavailable_path_count: int = Field(ge=0)
    split_quarantined_path_count: int = Field(ge=0)
    incomplete_required_dataset_families: tuple[
        Literal[
            "adjustment_ledger",
            "corporate_action",
            "instrument_lifecycle",
        ],
        ...,
    ] = Field(min_length=1)
    admission_basis: Literal["outcome_blind_missingness_only"] = (
        "outcome_blind_missingness_only"
    )
    admission_unit: Literal["complete_primary_session_cross_section"] = (
        "complete_primary_session_cross_section"
    )
    completeness_threshold_bps: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_COMPLETENESS_THRESHOLD_BPS
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_COMPLETENESS_THRESHOLD_BPS
    minimum_admitted_session_count: Literal[
        STRONG_LEADER_PULLBACK_DEVELOPMENT_MINIMUM_SESSIONS
    ] = STRONG_LEADER_PULLBACK_DEVELOPMENT_MINIMUM_SESSIONS
    incomplete_path_excludes_entire_session: Literal[True] = True
    missing_and_quarantined_records_retained_in_denominator: Literal[True] = True
    zero_included_session_admissible: Literal[False] = False
    coverage_based_instrument_selection_authorized: Literal[False] = False
    decision_status: Literal[
        DevelopmentAdmissionDecisionStatus.REJECTED_CURRENT_EVIDENCE
    ] = DevelopmentAdmissionDecisionStatus.REJECTED_CURRENT_EVIDENCE
    blocker_codes: tuple[str, ...] = Field(min_length=1)
    admitted_session_count: Literal[0] = 0
    admitted_path_count: Literal[0] = 0
    admitted_instrument_count: Literal[0] = 0
    coverage_threshold_selected: Literal[True] = True
    admitted_cohort_selected: Literal[False] = False
    contains_strategy_triggers: Literal[False] = False
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    development_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("decided_at", "census_calculated_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("blocker_codes", mode="before")
    @classmethod
    def blocker_codes_are_sorted(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("development admission blocker codes must be ordered")
        codes = tuple(str(item).strip() for item in value)
        if codes != tuple(sorted(set(codes))) or any(not item for item in codes):
            raise ValueError(
                "development admission blocker codes must be non-empty, unique, and sorted"
            )
        return codes

    @field_validator("incomplete_required_dataset_families", mode="before")
    @classmethod
    def incomplete_families_are_sorted(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("incomplete dataset families must be ordered")
        families = tuple(str(item).strip() for item in value)
        if families != tuple(sorted(set(families))):
            raise ValueError("incomplete dataset families must be unique and sorted")
        return families

    @model_validator(mode="after")
    def decision_reconciles(
        self,
    ) -> "StrongLeaderPullbackDevelopmentAdmissionDecisionV1":
        if self.first_session > self.last_session:
            raise ValueError("development admission session bounds differ")
        if self.decided_at < self.census_calculated_at:
            raise ValueError("development admission predates its census")
        if self.observed_session_count != (
            self.raw_candidate_session_count + self.zero_included_session_count
        ):
            raise ValueError("development admission observed sessions differ")
        if self.raw_candidate_session_count != (
            self.complete_cross_section_session_count
            + self.incomplete_cross_section_session_count
        ):
            raise ValueError("development admission candidate sessions differ")
        if (
            self.complete_cross_section_session_count
            >= self.minimum_admitted_session_count
            or self.all_required_evidence_complete_path_count
            > self.raw_feature_path_count
        ):
            raise ValueError("rejected development admission evidence differs")
        expected_blockers = {"minimum_complete_session_count_not_met"}
        if self.all_required_evidence_complete_path_count == 0:
            expected_blockers.add("all_required_evidence_complete_path_count_zero")
        if self.absent_row_neutrality_unproven_path_count > 0:
            expected_blockers.add("absent_row_neutrality_unproven")
        if self.lifecycle_unavailable_path_count > 0:
            expected_blockers.add("instrument_lifecycle_unavailable")
        if self.split_quarantined_path_count > 0:
            expected_blockers.add("split_path_quarantine_present")
        expected_blockers.update(
            f"{family}_not_complete_reconstruction_input"
            for family in self.incomplete_required_dataset_families
        )
        if self.blocker_codes != tuple(sorted(expected_blockers)):
            raise ValueError("development admission blocker evidence differs")
        if development_admission_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("development admission fingerprint mismatch")
        return self


def development_admission_fingerprint(value: BaseModel) -> str:
    payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
