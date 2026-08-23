"""Dashboard Snapshot V2 publication, active-pointer, and approval contracts."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DashboardSnapshotFileReferenceV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    relative_path: str
    size: int = Field(ge=0)
    sha256: str

    @field_validator("relative_path")
    @classmethod
    def path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("snapshot file path must be normalized and relative")
        return value

    @field_validator("sha256")
    @classmethod
    def digest(cls, value: str) -> str:
        return _sha(value)


class DashboardSnapshotTargetReferenceV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reference_version: Literal["2.0"] = "2.0"
    storage_kind: Literal["data_root", "legacy_repo_build"]
    release_id: str
    logical_path: str
    snapshot_contract_version: str
    dashboard_contract_version: str
    aggregate_sha256: str
    manifest_sha256: str

    @field_validator("logical_path")
    @classmethod
    def path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("snapshot target path must be normalized and relative")
        return value

    @field_validator("aggregate_sha256", "manifest_sha256")
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)


class DashboardSnapshotActivePointerV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    pointer_version: Literal["2.0"] = "2.0"
    status: Literal["active"] = "active"
    active: DashboardSnapshotTargetReferenceV2
    rollback: DashboardSnapshotTargetReferenceV2
    switched_at: datetime
    activation_pointer_fingerprint: str
    pointer_content_fingerprint: str

    @field_validator("activation_pointer_fingerprint", "pointer_content_fingerprint")
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)

    @model_validator(mode="after")
    def distinct(self) -> "DashboardSnapshotActivePointerV2":
        if self.active == self.rollback:
            raise ValueError("active and rollback snapshot references must differ")
        return self


class DashboardSnapshotApprovalPlanV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    plan_version: Literal["2.0"] = "2.0"
    revision_id: Literal["universe-funnel-v2"] = "universe-funnel-v2"
    release_id: str
    generated_at: datetime
    analysis_session: date
    expected_latest_completed_session: date
    actual_latest_completed_session: date
    freshness_status: Literal["fresh"]
    session_lag: Literal[0]
    activation_pointer_fingerprint: str
    activation_logical_fingerprint: str
    expected_current_state_fingerprint: str
    target_path: str
    target_logical_path: str
    pointer_path: str
    candidate_path: str
    files: tuple[DashboardSnapshotFileReferenceV2, ...]
    aggregate_sha256: str
    manifest_sha256: str
    planned_pointer_sha256: str
    planned_pointer_fingerprint: str
    rollback: DashboardSnapshotTargetReferenceV2
    plan_content_fingerprint: str

    @field_validator(
        "activation_pointer_fingerprint", "activation_logical_fingerprint",
        "expected_current_state_fingerprint", "aggregate_sha256", "manifest_sha256",
        "planned_pointer_sha256", "planned_pointer_fingerprint", "plan_content_fingerprint",
    )
    @classmethod
    def digests(cls, value: str) -> str:
        return _sha(value)

    @field_validator("target_logical_path")
    @classmethod
    def relative_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("publication paths must be normalized and relative")
        return value

    @field_validator("target_path", "pointer_path")
    @classmethod
    def absolute_paths(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("approved publication paths must be normalized and absolute")
        return value

    @field_validator("candidate_path")
    @classmethod
    def candidate(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or not path.is_relative_to(PurePosixPath("/tmp")) or ".." in path.parts:
            raise ValueError("candidate path must be an absolute /tmp path")
        return value


def _sha(value: str) -> str:
    value = value.lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("value must be SHA-256 hexadecimal")
    return value
