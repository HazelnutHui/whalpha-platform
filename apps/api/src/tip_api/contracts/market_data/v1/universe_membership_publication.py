"""Canonical completion and no-write Apply-plan contracts for Membership."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1.universe_membership_knowledge_time import (
    UniverseMembershipKnowledgeTimeAssessmentV1,
)


PUBLICATION_VERSION = "universe-membership-canonical-publication/1.0"
APPLY_PLAN_VERSION = "universe-membership-apply-plan/1.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class UniverseMembershipCanonicalPublicationV1(FrozenContract):
    """Logical marker published only after Membership physical bytes exist."""

    manifest_version: Literal[PUBLICATION_VERSION] = PUBLICATION_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["universe-membership"] = "universe-membership"
    session_date: date
    methodology_version: str
    membership_partition_path: str
    record_count: int = Field(ge=1)
    membership_logical_fingerprint: str = Field(pattern=_SHA256)
    membership_manifest_sha256: str = Field(pattern=_SHA256)
    membership_parquet_sha256: str = Field(pattern=_SHA256)
    knowledge_time_assessment: UniverseMembershipKnowledgeTimeAssessmentV1
    point_in_time_eligibility: Literal[PointInTimeEligibility.SIGNAL_ELIGIBLE] = (
        PointInTimeEligibility.SIGNAL_ELIGIBLE
    )
    created_at: datetime
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("methodology_version")
    @classmethod
    def methodology_is_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("methodology_version is required")
        return value.strip()

    @field_validator("membership_partition_path")
    @classmethod
    def membership_path_is_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("membership partition path must be normalized and relative")
        return value

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def publication_reconciles(self) -> "UniverseMembershipCanonicalPublicationV1":
        assessment = self.knowledge_time_assessment
        if (
            assessment.point_in_time_eligibility
            is not PointInTimeEligibility.SIGNAL_ELIGIBLE
            or self.session_date != assessment.session_date
            or self.methodology_version != assessment.methodology_version
            or self.membership_logical_fingerprint
            != assessment.membership_logical_fingerprint
            or self.membership_manifest_sha256
            != assessment.membership_manifest_sha256
            or self.membership_parquet_sha256
            != assessment.membership_parquet_sha256
        ):
            raise ValueError("canonical Membership publication evidence differs")
        if self.created_at < assessment.assessed_at:
            raise ValueError("publication cannot precede its timing assessment")
        if (
            universe_membership_publication_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("canonical Membership publication fingerprint mismatch")
        return self


class UniverseMembershipPlanArtifactV1(FrozenContract):
    file_name: Literal["manifest.json", "part-00000.parquet"]
    source_path: str
    target_path: str
    size: int = Field(ge=1)
    sha256: str = Field(pattern=_SHA256)

    @field_validator("source_path", "target_path")
    @classmethod
    def paths_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("Membership Apply path must be normalized and absolute")
        return value


class UniverseMembershipApplyPlanV1(FrozenContract):
    contract_version: Literal[APPLY_PLAN_VERSION] = APPLY_PLAN_VERSION
    operation: Literal["publish_signal_eligible_universe_membership"] = (
        "publish_signal_eligible_universe_membership"
    )
    status: Literal["ready_for_separate_review"] = "ready_for_separate_review"
    created_at: datetime
    data_root: str
    candidate_root: str
    candidate_membership_partition: str
    target_membership_partition: str
    target_publication_partition: str
    expected_current_state_fingerprint: str = Field(pattern=_SHA256)
    candidate_inventory_fingerprint: str = Field(pattern=_SHA256)
    artifacts: tuple[UniverseMembershipPlanArtifactV1, ...]
    publication: UniverseMembershipCanonicalPublicationV1
    publication_manifest_bytes: int = Field(ge=1)
    publication_manifest_sha256: str = Field(pattern=_SHA256)
    inventory_change_file_count: Literal[3] = 3
    inventory_change_bytes: int = Field(ge=1)
    target_absent_partition_count: Literal[2] = 2
    candidate_formal_read_complete: Literal[True] = True
    target_absence_verified: Literal[True] = True
    current_inventory_bound: Literal[True] = True
    knowledge_time_signal_eligible: Literal[True] = True
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "data_root",
        "candidate_root",
        "candidate_membership_partition",
        "target_membership_partition",
        "target_publication_partition",
    )
    @classmethod
    def roots_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("Membership Apply root must be normalized and absolute")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "UniverseMembershipApplyPlanV1":
        if self.created_at != self.publication.created_at:
            raise ValueError("Apply plan and publication creation times differ")
        if tuple(item.file_name for item in self.artifacts) != (
            "manifest.json",
            "part-00000.parquet",
        ):
            raise ValueError("Membership candidate artifacts are incomplete or unordered")
        assessment = self.publication.knowledge_time_assessment
        if assessment.point_in_time_eligibility is not PointInTimeEligibility.SIGNAL_ELIGIBLE:
            raise ValueError("Apply plan requires signal-eligible Membership")
        if (
            self.candidate_inventory_fingerprint
            != universe_membership_candidate_inventory_fingerprint(self.artifacts)
        ):
            raise ValueError("Membership candidate inventory fingerprint differs")
        if self.inventory_change_bytes != (
            sum(item.size for item in self.artifacts)
            + self.publication_manifest_bytes
        ):
            raise ValueError("Membership Apply inventory bytes differ")
        expected_target_files = tuple(
            str(PurePosixPath(self.target_membership_partition) / item.file_name)
            for item in self.artifacts
        )
        if tuple(item.target_path for item in self.artifacts) != expected_target_files:
            raise ValueError("Membership artifact target paths differ")
        relative_membership = PurePosixPath(
            self.target_membership_partition
        ).relative_to(PurePosixPath(self.data_root)).as_posix()
        if self.publication.membership_partition_path != relative_membership:
            raise ValueError("Membership publication target binding differs")
        if universe_membership_apply_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("Membership Apply-plan fingerprint mismatch")
        return self


def build_universe_membership_canonical_publication(
    **values: object,
) -> UniverseMembershipCanonicalPublicationV1:
    provisional = UniverseMembershipCanonicalPublicationV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return UniverseMembershipCanonicalPublicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": universe_membership_publication_fingerprint(
                provisional
            ),
        }
    )


def build_universe_membership_apply_plan(
    **values: object,
) -> UniverseMembershipApplyPlanV1:
    provisional = UniverseMembershipApplyPlanV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return UniverseMembershipApplyPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": universe_membership_apply_plan_fingerprint(
                provisional
            ),
        }
    )


def universe_membership_candidate_inventory_fingerprint(
    artifacts: tuple[UniverseMembershipPlanArtifactV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in artifacts])


def universe_membership_publication_fingerprint(
    publication: UniverseMembershipCanonicalPublicationV1,
) -> str:
    return _fingerprint(
        publication.model_dump(mode="json", exclude={"logical_fingerprint"})
    )


def universe_membership_apply_plan_fingerprint(
    plan: UniverseMembershipApplyPlanV1,
) -> str:
    return _fingerprint(plan.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _fingerprint(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
