"""Research-only custody contracts for reconstructed Universe Membership."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_research import (
    UniverseMembershipOrigin,
)


CUSTODY_VERSION = "research-universe-membership-custody/1.0"
APPLY_PLAN_VERSION = "research-universe-membership-apply-plan/1.0"
EVIDENCE_TIER = "reconstructed_point_in_time_latest_vintage"
PATH_EVIDENCE_TIER = "reconstructed-latest-vintage-v1"
PERMITTED_USES = (
    "coverage_census",
    "input_completeness",
    "lineage_audit",
    "missingness_analysis",
)
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResearchUniverseMembershipCustodyV1(FrozenContract):
    """Marker proving one reconstructed partition is research-only custody."""

    contract_version: Literal[CUSTODY_VERSION] = CUSTODY_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["research-universe-membership"] = (
        "research-universe-membership"
    )
    evidence_tier: Literal[
        "reconstructed_point_in_time_latest_vintage"
    ] = EVIDENCE_TIER
    knowledge_time_status: Literal["not_as_operated"] = "not_as_operated"
    permitted_uses: tuple[str, ...] = PERMITTED_USES
    session_date: date
    represented_session_close_at: datetime
    methodology_version: str
    membership_partition_path: str
    membership_manifest_sha256: str = Field(pattern=_SHA256)
    membership_parquet_sha256: str = Field(pattern=_SHA256)
    membership_logical_fingerprint: str = Field(pattern=_SHA256)
    record_count: int = Field(ge=1)
    evaluated_base_count: int = Field(ge=1)
    origin: Literal[UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME] = (
        UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME
    )
    source_fingerprints: tuple[str, ...] = Field(min_length=1)
    source_data_cutoff: datetime
    evaluated_at: datetime
    created_at: datetime
    signal_authorized: Literal[False] = False
    development_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_authorized: Literal[False] = False
    performance_authorized: Literal[False] = False
    candidate_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    web_publication_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("session_date", mode="before")
    @classmethod
    def date_only(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must contain a date")
        return value

    @field_validator("methodology_version", mode="before")
    @classmethod
    def methodology_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="methodology_version")

    @field_validator("membership_partition_path")
    @classmethod
    def relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("membership partition path must be normalized and relative")
        return value

    @field_validator("source_fingerprints", mode="before")
    @classmethod
    def source_hashes(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("source_fingerprints must be an ordered collection")
        result = tuple(value)
        if (
            not result
            or result != tuple(sorted(set(result)))
            or any(
                not isinstance(item, str)
                or len(item) != 64
                or any(character not in "0123456789abcdef" for character in item)
                for item in result
            )
        ):
            raise ValueError("source_fingerprints must be unique sorted SHA-256 values")
        return result

    @field_validator(
        "represented_session_close_at",
        "source_data_cutoff",
        "evaluated_at",
        "created_at",
    )
    @classmethod
    def utc_times(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("permitted_uses", mode="before")
    @classmethod
    def fixed_uses(cls, value: Any) -> tuple[str, ...]:
        result = tuple(value) if isinstance(value, (tuple, list)) else ()
        if result != PERMITTED_USES:
            raise ValueError("research Membership permitted uses differ")
        return result

    @model_validator(mode="after")
    def marker_reconciles(self) -> "ResearchUniverseMembershipCustodyV1":
        if self.source_data_cutoff <= self.represented_session_close_at:
            raise ValueError("latest-vintage source cutoff must follow session close")
        if self.evaluated_at < self.source_data_cutoff:
            raise ValueError("Membership evaluation precedes its source cutoff")
        if self.created_at < self.evaluated_at:
            raise ValueError("research custody creation precedes evaluation")
        if research_universe_membership_custody_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research Membership custody fingerprint differs")
        return self


class ResearchUniverseMembershipPlanArtifactV1(FrozenContract):
    file_name: Literal["manifest.json", "part-00000.parquet"]
    source_path: str
    target_path: str
    size: int = Field(ge=1)
    sha256: str = Field(pattern=_SHA256)

    @field_validator("source_path", "target_path")
    @classmethod
    def absolute_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("research Membership Apply path must be normalized and absolute")
        return value


class ResearchUniverseMembershipApplyPlanV1(FrozenContract):
    contract_version: Literal[APPLY_PLAN_VERSION] = APPLY_PLAN_VERSION
    operation: Literal["publish_research_universe_membership"] = (
        "publish_research_universe_membership"
    )
    status: Literal["ready_for_execution"] = "ready_for_execution"
    created_at: datetime
    data_root: str
    candidate_membership_partition: str
    target_membership_partition: str
    target_absent_at_plan: Literal[True] = True
    artifacts: tuple[ResearchUniverseMembershipPlanArtifactV1, ...]
    custody: ResearchUniverseMembershipCustodyV1
    custody_bytes: int = Field(ge=1)
    custody_sha256: str = Field(pattern=_SHA256)
    inventory_change_file_count: Literal[3] = 3
    inventory_change_bytes: int = Field(ge=1)
    external_request_count: Literal[0] = 0
    overwritten_partition_count: Literal[0] = 0
    deleted_partition_count: Literal[0] = 0
    performance_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def utc_created_at(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "data_root",
        "candidate_membership_partition",
        "target_membership_partition",
    )
    @classmethod
    def absolute_roots(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("research Membership Apply root must be absolute")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ResearchUniverseMembershipApplyPlanV1":
        if self.created_at != self.custody.created_at:
            raise ValueError("Apply plan and custody creation times differ")
        if tuple(item.file_name for item in self.artifacts) != (
            "manifest.json",
            "part-00000.parquet",
        ):
            raise ValueError("research Membership artifacts are incomplete or unordered")
        if tuple(item.target_path for item in self.artifacts) != tuple(
            str(PurePosixPath(self.target_membership_partition) / item.file_name)
            for item in self.artifacts
        ):
            raise ValueError("research Membership artifact target paths differ")
        relative_target = PurePosixPath(self.target_membership_partition).relative_to(
            PurePosixPath(self.data_root)
        ).as_posix()
        if self.custody.membership_partition_path != relative_target:
            raise ValueError("research Membership custody target binding differs")
        if self.inventory_change_bytes != (
            sum(item.size for item in self.artifacts) + self.custody_bytes
        ):
            raise ValueError("research Membership Apply bytes differ")
        if research_universe_membership_apply_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research Membership Apply-plan fingerprint differs")
        return self


def build_research_universe_membership_custody(
    **values: object,
) -> ResearchUniverseMembershipCustodyV1:
    provisional = ResearchUniverseMembershipCustodyV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ResearchUniverseMembershipCustodyV1.model_validate(
        {
            **values,
            "logical_fingerprint": research_universe_membership_custody_fingerprint(
                provisional
            ),
        }
    )


def build_research_universe_membership_apply_plan(
    **values: object,
) -> ResearchUniverseMembershipApplyPlanV1:
    provisional = ResearchUniverseMembershipApplyPlanV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ResearchUniverseMembershipApplyPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": research_universe_membership_apply_plan_fingerprint(
                provisional
            ),
        }
    )


def research_universe_membership_custody_fingerprint(
    custody: ResearchUniverseMembershipCustodyV1,
) -> str:
    return _fingerprint(custody.model_dump(mode="json", exclude={"logical_fingerprint"}))


def research_universe_membership_apply_plan_fingerprint(
    plan: ResearchUniverseMembershipApplyPlanV1,
) -> str:
    return _fingerprint(plan.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()
