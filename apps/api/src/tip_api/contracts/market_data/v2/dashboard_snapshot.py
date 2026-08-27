"""Dashboard Snapshot V2 publication, active-pointer, and approval contracts."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.analytics.v1.review_deployment import ReviewDeploymentAuthorizationV1


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
    snapshot_contract_version: Literal["1.4", "1.5", "1.6", "1.7"] = "1.4"
    dashboard_contract_version: Literal["2.1", "2.2", "2.3", "2.4"] = "2.1"
    generated_at: datetime
    analysis_session: date
    expected_latest_completed_session: date
    actual_latest_completed_session: date
    freshness_status: Literal["fresh", "stale"]
    session_lag: int = Field(ge=0)
    review_mode: bool = False
    normal_freshness: bool = False
    activation_allowed_by_review_authorization: bool = False
    review_deployment: ReviewDeploymentAuthorizationV1 | None = None
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
    market_intelligence_publication_id: str | None = None
    market_intelligence_payload_sha256: str | None = None
    market_intelligence_logical_fingerprint: str | None = None
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

    @field_validator("market_intelligence_payload_sha256", "market_intelligence_logical_fingerprint")
    @classmethod
    def optional_digests(cls, value: str | None) -> str | None:
        return _sha(value) if value is not None else None

    @model_validator(mode="after")
    def market_intelligence_binding(self) -> "DashboardSnapshotApprovalPlanV2":
        values = (
            self.market_intelligence_publication_id,
            self.market_intelligence_payload_sha256,
            self.market_intelligence_logical_fingerprint,
        )
        if self.snapshot_contract_version in {"1.5", "1.6", "1.7"}:
            expected = (
                "2.4" if self.snapshot_contract_version == "1.7"
                else "2.3" if self.snapshot_contract_version == "1.6"
                else "2.2"
            )
            if self.dashboard_contract_version != expected or any(value is None for value in values):
                raise ValueError(
                    f"Snapshot {self.snapshot_contract_version} requires Dashboard {expected} and Market Intelligence"
                )
        elif self.dashboard_contract_version != "2.1" or any(value is not None for value in values):
            raise ValueError("Snapshot 1.4 cannot bind Market Intelligence")
        return self
    @model_validator(mode="after")
    def freshness_authorization_reconciles(self) -> "DashboardSnapshotApprovalPlanV2":
        normal = (
            self.freshness_status == "fresh"
            and self.session_lag == 0
            and self.expected_latest_completed_session == self.actual_latest_completed_session
        )
        if self.normal_freshness != normal:
            raise ValueError("normal snapshot freshness authorization differs")
        if self.review_mode != (self.review_deployment is not None):
            raise ValueError("snapshot review mode and authorization differ")
        review_allowed = self.review_deployment is not None and (
            self.analysis_session == self.review_deployment.approved_as_of_session
            and self.actual_latest_completed_session
            == self.review_deployment.approved_as_of_session
            and self.expected_latest_completed_session
            == self.review_deployment.expected_latest_session
            and self.session_lag == self.review_deployment.expected_lag_sessions
            and self.freshness_status == "stale"
        )
        if self.activation_allowed_by_review_authorization != review_allowed:
            raise ValueError("snapshot review freshness authorization differs")
        if normal and self.review_deployment is not None:
            raise ValueError("fresh snapshot must not carry stale-review authorization")
        return self


class DashboardSnapshotApprovalPlanV2_1(DashboardSnapshotApprovalPlanV2):
    """Snapshot 1.6 approval plan with immutable Candidate consumer bindings."""

    plan_version: Literal["2.1"] = "2.1"
    snapshot_contract_version: Literal["1.6"] = "1.6"
    dashboard_contract_version: Literal["2.3"] = "2.3"
    candidate_contract_version: Literal["opportunity-candidate/1.1"]
    candidate_analytics_logical_fingerprint: str
    candidate_audit_logical_fingerprint: str
    candidate_parameter_fingerprint: str
    candidate_state_parameter_fingerprint: str

    @field_validator(
        "candidate_analytics_logical_fingerprint",
        "candidate_audit_logical_fingerprint",
        "candidate_parameter_fingerprint",
        "candidate_state_parameter_fingerprint",
    )
    @classmethod
    def candidate_digests(cls, value: str) -> str:
        return _sha(value)


class DashboardSnapshotApprovalPlanV2_2(DashboardSnapshotApprovalPlanV2_1):
    """Snapshot 1.7 approval plan with entry-geometry consumer bindings."""

    plan_version: Literal["2.2"] = "2.2"
    snapshot_contract_version: Literal["1.7"] = "1.7"
    dashboard_contract_version: Literal["2.4"] = "2.4"
    candidate_publication_contract_version: Literal[
        "opportunity-candidate-publication/1.1"
    ]
    entry_geometry_contract_version: Literal["candidate-entry-geometry/1.0"]
    entry_geometry_audit_logical_fingerprint: str
    entry_geometry_parameter_fingerprint: str
    entry_lane_consumer_parameter_fingerprint: str

    @field_validator(
        "entry_geometry_audit_logical_fingerprint",
        "entry_geometry_parameter_fingerprint",
        "entry_lane_consumer_parameter_fingerprint",
    )
    @classmethod
    def entry_digests(cls, value: str) -> str:
        return _sha(value)


def _sha(value: str) -> str:
    value = value.lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("value must be SHA-256 hexadecimal")
    return value
