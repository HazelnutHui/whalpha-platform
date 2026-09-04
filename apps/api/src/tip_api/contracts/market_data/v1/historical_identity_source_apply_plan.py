"""No-write Apply planning contract for historical Identity source custody."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    DATASET_NAME,
    historical_identity_source_fingerprint,
)


PLAN_CONTRACT_VERSION = "historical-identity-source-apply-plan/1.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalIdentitySourcePlanSessionV1(FrozenModel):
    session_date: date
    identity_rebuild_profile: Literal["current_v1", "pre_etv_governance_v1"]
    record_count: int = Field(ge=1)
    source_request_count: int = Field(ge=1)
    source_response_bytes: int = Field(ge=1)
    parquet_bytes: int = Field(ge=1)
    manifest_bytes: int = Field(ge=1)
    content_fingerprint: str = Field(pattern=_SHA256)
    parquet_sha256: str = Field(pattern=_SHA256)
    manifest_sha256: str = Field(pattern=_SHA256)
    logical_fingerprint: str = Field(pattern=_SHA256)
    canonical_snapshot_fingerprint: str = Field(pattern=_SHA256)
    canonical_instrument_fingerprint: str = Field(pattern=_SHA256)
    canonical_identity_fingerprint: str = Field(pattern=_SHA256)
    canonical_resolver_fingerprint: str = Field(pattern=_SHA256)


class HistoricalIdentitySourcePlanArtifactV1(FrozenModel):
    session_date: date
    file_name: Literal["manifest.json", "part-00000.parquet"]
    source_path: str
    target_path: str
    size: int = Field(ge=1)
    sha256: str = Field(pattern=_SHA256)

    @field_validator("source_path", "target_path")
    @classmethod
    def path_is_absolute(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("historical source plan path must be absolute")
        return value


class HistoricalIdentitySourceApplyPlanV1(FrozenModel):
    contract_version: Literal["historical-identity-source-apply-plan/1.0"] = (
        PLAN_CONTRACT_VERSION
    )
    operation: Literal["publish_historical_identity_source_custody"] = (
        "publish_historical_identity_source_custody"
    )
    status: Literal["ready_for_separate_review"] = "ready_for_separate_review"
    created_at: datetime
    data_root: str
    candidate_root: str
    target_dataset_root: str
    dataset_name: Literal["provider-identity-reference-observation"] = DATASET_NAME
    provider: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    identity_profile_map_fingerprint: str = Field(pattern=_SHA256)
    expected_current_state_fingerprint: str = Field(pattern=_SHA256)
    session_index_fingerprint: str = Field(pattern=_SHA256)
    candidate_inventory_fingerprint: str = Field(pattern=_SHA256)
    first_session: date
    last_session: date
    session_count: int = Field(ge=1, le=303)
    current_profile_session_count: int = Field(ge=0)
    legacy_profile_session_count: int = Field(ge=0)
    record_count: int = Field(ge=1)
    source_request_count: int = Field(ge=1)
    source_response_bytes: int = Field(ge=1)
    normalized_parquet_bytes: int = Field(ge=1)
    manifest_bytes: int = Field(ge=1)
    inventory_change_file_count: int = Field(ge=2)
    inventory_change_bytes: int = Field(ge=1)
    target_absent_partition_count: int = Field(ge=1)
    sessions: tuple[HistoricalIdentitySourcePlanSessionV1, ...]
    artifacts: tuple[HistoricalIdentitySourcePlanArtifactV1, ...]
    candidate_formal_read_complete: Literal[True] = True
    target_absence_verified: Literal[True] = True
    current_inventory_bound: Literal[True] = True
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    universe_membership_write_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("data_root", "candidate_root", "target_dataset_root")
    @classmethod
    def root_path_is_absolute(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("historical source plan root must be absolute")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "HistoricalIdentitySourceApplyPlanV1":
        dates = tuple(item.session_date for item in self.sessions)
        if len(self.sessions) != self.session_count or dates != tuple(
            sorted(set(dates))
        ):
            raise ValueError(
                "historical source plan sessions are not unique and ordered"
            )
        if self.first_session != dates[0] or self.last_session != dates[-1]:
            raise ValueError("historical source plan session bounds differ")
        if (
            self.current_profile_session_count
            != sum(
                item.identity_rebuild_profile == "current_v1"
                for item in self.sessions
            )
            or self.legacy_profile_session_count
            != sum(
                item.identity_rebuild_profile == "pre_etv_governance_v1"
                for item in self.sessions
            )
            or self.current_profile_session_count + self.legacy_profile_session_count
            != self.session_count
        ):
            raise ValueError("historical source plan profile counts differ")
        sums = {
            "record_count": sum(item.record_count for item in self.sessions),
            "source_request_count": sum(
                item.source_request_count for item in self.sessions
            ),
            "source_response_bytes": sum(
                item.source_response_bytes for item in self.sessions
            ),
            "normalized_parquet_bytes": sum(
                item.parquet_bytes for item in self.sessions
            ),
            "manifest_bytes": sum(item.manifest_bytes for item in self.sessions),
        }
        if any(getattr(self, name) != value for name, value in sums.items()):
            raise ValueError("historical source plan session aggregates differ")
        expected_artifact_order = tuple(
            (session_date, file_name)
            for session_date in dates
            for file_name in ("manifest.json", "part-00000.parquet")
        )
        artifact_order = tuple(
            (item.session_date, item.file_name) for item in self.artifacts
        )
        if artifact_order != expected_artifact_order:
            raise ValueError(
                "historical source plan artifacts are not complete and ordered"
            )
        if (
            self.inventory_change_file_count != len(self.artifacts)
            or self.inventory_change_file_count != 2 * self.session_count
            or self.inventory_change_bytes != sum(item.size for item in self.artifacts)
            or self.inventory_change_bytes
            != self.normalized_parquet_bytes + self.manifest_bytes
            or self.target_absent_partition_count != self.session_count
        ):
            raise ValueError("historical source plan inventory aggregates differ")
        manifest_by_date = {item.session_date: item for item in self.sessions}
        for artifact in self.artifacts:
            session = manifest_by_date[artifact.session_date]
            expected_size = (
                session.manifest_bytes
                if artifact.file_name == "manifest.json"
                else session.parquet_bytes
            )
            expected_sha = (
                session.manifest_sha256
                if artifact.file_name == "manifest.json"
                else session.parquet_sha256
            )
            if artifact.size != expected_size or artifact.sha256 != expected_sha:
                raise ValueError("historical source plan artifact differs from session")
        expected = historical_identity_source_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("historical source Apply-plan fingerprint mismatch")
        return self
