"""Bounded publication contracts for provider corporate-action observations."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime


PUBLICATION_VERSION = "corporate-action-source-publication/1.0"
APPLY_PLAN_VERSION = "corporate-action-source-apply-plan/1.0"
_SHA256 = r"^[0-9a-f]{64}$"
_GIT_REVISION = r"^[0-9a-f]{40}$"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorporateActionSourceObservationEvidenceV1(FrozenContract):
    """One complete baseline/repeat observation pair for an endpoint family."""

    action_kind: Literal["split", "dividend"]
    baseline_manifest_sha256: str = Field(pattern=_SHA256)
    baseline_logical_fingerprint: str = Field(pattern=_SHA256)
    baseline_content_fingerprint: str = Field(pattern=_SHA256)
    baseline_record_count: int = Field(ge=0)
    repeat_manifest_sha256: str = Field(pattern=_SHA256)
    repeat_logical_fingerprint: str = Field(pattern=_SHA256)
    repeat_content_fingerprint: str = Field(pattern=_SHA256)
    repeat_diff_manifest_sha256: str = Field(pattern=_SHA256)
    repeat_diff_logical_fingerprint: str = Field(pattern=_SHA256)
    baseline_completed_at: datetime
    repeat_started_at: datetime
    repeat_completed_at: datetime
    unchanged_record_count: int = Field(ge=0)
    changed_record_count: Literal[0] = 0
    added_record_count: Literal[0] = 0
    removed_record_count: Literal[0] = 0
    pagination_shape_changed: Literal[False] = False

    @field_validator(
        "baseline_completed_at", "repeat_started_at", "repeat_completed_at"
    )
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "CorporateActionSourceObservationEvidenceV1":
        if not (
            self.baseline_completed_at
            < self.repeat_started_at
            <= self.repeat_completed_at
        ):
            raise ValueError("source observation order differs")
        if (
            self.baseline_record_count != self.unchanged_record_count
            or self.baseline_content_fingerprint
            != self.repeat_content_fingerprint
        ):
            raise ValueError("zero-delta source observation evidence differs")
        return self


class CorporateActionSourcePublicationArtifactV1(FrozenContract):
    event_year: int = Field(ge=1900, le=2200)
    partition_path: str
    record_count: int = Field(ge=1)
    logical_fingerprint: str = Field(pattern=_SHA256)
    manifest_sha256: str = Field(pattern=_SHA256)
    manifest_bytes: int = Field(ge=1)
    parquet_sha256: str = Field(pattern=_SHA256)
    parquet_bytes: int = Field(ge=1)

    @field_validator("partition_path")
    @classmethod
    def path_is_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("corporate-action partition path is invalid")
        return value

    @model_validator(mode="after")
    def artifact_reconciles(self) -> "CorporateActionSourcePublicationArtifactV1":
        if not self.partition_path.endswith(f"/event_year={self.event_year}"):
            raise ValueError("corporate-action artifact year differs")
        return self


class CorporateActionSourcePublicationV1(FrozenContract):
    """Marker-last declaration over one bounded provider query snapshot."""

    manifest_version: Literal[PUBLICATION_VERSION] = PUBLICATION_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["provider-corporate-action-observation"] = (
        "provider-corporate-action-observation"
    )
    provider_id: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    source_revision: str = Field(pattern=_GIT_REVISION)
    start_date: date
    end_date: date
    source_observations: tuple[CorporateActionSourceObservationEvidenceV1, ...]
    identity_evidence_path: str
    identity_evidence_sha256: str = Field(pattern=_SHA256)
    identity_evidence_logical_fingerprint: str = Field(pattern=_SHA256)
    identity_session_count: int = Field(ge=1)
    resolution_shadow_manifest_sha256: str = Field(pattern=_SHA256)
    resolution_shadow_logical_fingerprint: str = Field(pattern=_SHA256)
    source_record_count: int = Field(ge=1)
    resolved_record_count: int = Field(ge=0)
    quarantined_record_count: int = Field(ge=0)
    artifacts: tuple[CorporateActionSourcePublicationArtifactV1, ...]
    query_scope_completion: Literal["complete_as_observed"] = "complete_as_observed"
    source_revision_semantics: Literal["local_observation_baseline_only"] = (
        "local_observation_baseline_only"
    )
    source_stability_semantics: Literal["short_interval_zero_delta_only"] = (
        "short_interval_zero_delta_only"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    canonical_corporate_action_authorized: Literal[False] = False
    adjustment_ledger_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    created_at: datetime
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("identity_evidence_path")
    @classmethod
    def identity_path_is_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
            or not value.endswith("/manifest.json")
        ):
            raise ValueError("Identity evidence path is invalid")
        return value

    @model_validator(mode="after")
    def publication_reconciles(self) -> "CorporateActionSourcePublicationV1":
        if self.end_date < self.start_date:
            raise ValueError("corporate-action publication range is reversed")
        if tuple(item.action_kind for item in self.source_observations) != (
            "split",
            "dividend",
        ):
            raise ValueError("source observation scope is incomplete or unordered")
        years = tuple(item.event_year for item in self.artifacts)
        if not years or years != tuple(sorted(set(years))):
            raise ValueError("corporate-action publication years differ")
        if sum(item.record_count for item in self.artifacts) != self.source_record_count:
            raise ValueError("corporate-action publication artifact counts differ")
        if (
            self.resolved_record_count + self.quarantined_record_count
            != self.source_record_count
        ):
            raise ValueError("corporate-action resolution counts differ")
        if sum(
            item.baseline_record_count for item in self.source_observations
        ) != self.source_record_count:
            raise ValueError("corporate-action source counts differ")
        if corporate_action_source_publication_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("corporate-action publication fingerprint mismatch")
        return self


class CorporateActionSourcePlanArtifactV1(FrozenContract):
    event_year: int = Field(ge=1900, le=2200)
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
            raise ValueError("corporate-action Apply path is invalid")
        return value


class CorporateActionSourceApplyPlanV1(FrozenContract):
    contract_version: Literal[APPLY_PLAN_VERSION] = APPLY_PLAN_VERSION
    operation: Literal["publish_bounded_corporate_action_source"] = (
        "publish_bounded_corporate_action_source"
    )
    status: Literal["ready_for_separate_review"] = "ready_for_separate_review"
    created_at: datetime
    data_root: str
    resolution_shadow_root: str
    split_repeat_diff_root: str
    dividend_repeat_diff_root: str
    target_partition_paths: tuple[str, ...]
    target_publication_partition: str
    expected_current_state_fingerprint: str = Field(pattern=_SHA256)
    candidate_inventory_fingerprint: str = Field(pattern=_SHA256)
    artifacts: tuple[CorporateActionSourcePlanArtifactV1, ...]
    publication: CorporateActionSourcePublicationV1
    publication_manifest_bytes: int = Field(ge=1)
    publication_manifest_sha256: str = Field(pattern=_SHA256)
    inventory_change_file_count: int = Field(ge=3)
    inventory_change_bytes: int = Field(ge=1)
    target_absent_partition_count: int = Field(ge=2)
    candidate_formal_read_complete: Literal[True] = True
    repeat_diff_formal_read_complete: Literal[True] = True
    target_absence_verified: Literal[True] = True
    current_inventory_bound: Literal[True] = True
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    canonical_corporate_action_authorized: Literal[False] = False
    adjustment_ledger_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def plan_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "data_root",
        "resolution_shadow_root",
        "split_repeat_diff_root",
        "dividend_repeat_diff_root",
        "target_publication_partition",
    )
    @classmethod
    def absolute_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("corporate-action plan path is invalid")
        return value

    @field_validator("target_partition_paths")
    @classmethod
    def target_paths_are_ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or value != tuple(sorted(set(value))):
            raise ValueError("corporate-action target partitions are not unique and ordered")
        for item in value:
            path = PurePosixPath(item)
            if not path.is_absolute() or ".." in path.parts or path.as_posix() != item:
                raise ValueError("corporate-action target partition path is invalid")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "CorporateActionSourceApplyPlanV1":
        if self.created_at != self.publication.created_at:
            raise ValueError("corporate-action plan and publication times differ")
        expected_artifact_keys = tuple(
            (year, file_name)
            for year in tuple(item.event_year for item in self.publication.artifacts)
            for file_name in ("manifest.json", "part-00000.parquet")
        )
        if tuple(
            (item.event_year, item.file_name) for item in self.artifacts
        ) != expected_artifact_keys:
            raise ValueError("corporate-action plan artifacts are incomplete or unordered")
        expected_partitions = tuple(
            str(PurePosixPath(self.data_root) / item.partition_path)
            for item in self.publication.artifacts
        )
        if self.target_partition_paths != expected_partitions:
            raise ValueError("corporate-action partition targets differ")
        expected_sources = tuple(
            str(
                PurePosixPath(self.resolution_shadow_root)
                / item.partition_path
                / file_name
            )
            for item in self.publication.artifacts
            for file_name in ("manifest.json", "part-00000.parquet")
        )
        if tuple(item.source_path for item in self.artifacts) != expected_sources:
            raise ValueError("corporate-action artifact sources differ")
        expected_publication = str(
            PurePosixPath(self.data_root)
            / "market-data"
            / "provider-corporate-action-observation-publications"
            / "schema_version=1"
            / f"provider_id={self.publication.provider_id}"
            / f"coverage_id={self.publication.logical_fingerprint}"
        )
        if self.target_publication_partition != expected_publication:
            raise ValueError("corporate-action publication target differs")
        if self.candidate_inventory_fingerprint != (
            corporate_action_source_candidate_inventory_fingerprint(self.artifacts)
        ):
            raise ValueError("corporate-action candidate inventory differs")
        if self.inventory_change_file_count != len(self.artifacts) + 1:
            raise ValueError("corporate-action inventory file count differs")
        if self.inventory_change_bytes != (
            sum(item.size for item in self.artifacts)
            + self.publication_manifest_bytes
        ):
            raise ValueError("corporate-action inventory bytes differ")
        if self.target_absent_partition_count != len(self.target_partition_paths) + 1:
            raise ValueError("corporate-action target count differs")
        expected_targets = tuple(
            str(PurePosixPath(partition) / file_name)
            for partition in self.target_partition_paths
            for file_name in ("manifest.json", "part-00000.parquet")
        )
        if tuple(item.target_path for item in self.artifacts) != expected_targets:
            raise ValueError("corporate-action artifact targets differ")
        if corporate_action_source_apply_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("corporate-action Apply-plan fingerprint mismatch")
        return self


def build_corporate_action_source_publication(
    **values: object,
) -> CorporateActionSourcePublicationV1:
    provisional = CorporateActionSourcePublicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return CorporateActionSourcePublicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": corporate_action_source_publication_fingerprint(
                provisional
            ),
        }
    )


def build_corporate_action_source_apply_plan(
    **values: object,
) -> CorporateActionSourceApplyPlanV1:
    provisional = CorporateActionSourceApplyPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return CorporateActionSourceApplyPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": corporate_action_source_apply_plan_fingerprint(
                provisional
            ),
        }
    )


def corporate_action_source_candidate_inventory_fingerprint(
    artifacts: tuple[CorporateActionSourcePlanArtifactV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in artifacts])


def corporate_action_source_publication_fingerprint(
    publication: CorporateActionSourcePublicationV1,
) -> str:
    return _fingerprint(
        publication.model_dump(mode="json", exclude={"logical_fingerprint"})
    )


def corporate_action_source_apply_plan_fingerprint(
    plan: CorporateActionSourceApplyPlanV1,
) -> str:
    return _fingerprint(plan.model_dump(mode="json", exclude={"logical_fingerprint"}))


def corporate_action_source_publication_bytes(
    publication: CorporateActionSourcePublicationV1,
) -> bytes:
    return (
        json.dumps(
            publication.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
