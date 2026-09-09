"""Sparse canonical split-adjustment publication contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime


PUBLICATION_VERSION = "canonical-split-adjustment-publication/1.0"
APPLY_PLAN_VERSION = "canonical-split-adjustment-apply-plan/1.0"
METHODOLOGY_VERSION = "canonical-split-ratio-to-basis-v1"
_SHA256 = r"^[0-9a-f]{64}$"
_GIT_REVISION = r"^[0-9a-f]{40}$"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CanonicalSplitAdjustmentPublicationV1(FrozenContract):
    """One sparse, affected-path-only split adjustment publication."""

    manifest_version: Literal[
        "canonical-split-adjustment-publication/1.0"
    ] = PUBLICATION_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["adjustment-ledger"] = "adjustment-ledger"
    methodology_version: Literal[
        "canonical-split-ratio-to-basis-v1"
    ] = METHODOLOGY_VERSION
    source_revision: str = Field(pattern=_GIT_REVISION)
    basis_session: date
    first_source_session: date
    last_source_session: date
    source_session_count: int = Field(ge=1)
    source_eod_record_count: int = Field(ge=1)
    canonical_action_publication_path: str
    canonical_action_publication_sha256: str = Field(pattern=_SHA256)
    canonical_action_publication_fingerprint: str = Field(pattern=_SHA256)
    eod_evidence_path: str
    eod_evidence_sha256: str = Field(pattern=_SHA256)
    eod_evidence_fingerprint: str = Field(pattern=_SHA256)
    source_data_cutoff: datetime
    calculated_at: datetime
    selected_instrument_count: int = Field(ge=1)
    selected_eod_row_count: int = Field(ge=1)
    selected_without_eod_count: int = Field(ge=0)
    record_count: int = Field(ge=1)
    clear_record_count: int = Field(ge=0)
    quarantined_record_count: int = Field(ge=0)
    clear_instrument_count: int = Field(ge=0)
    quarantined_instrument_count: int = Field(ge=0)
    active_action_record_count: int = Field(ge=0)
    quarantined_action_record_count: int = Field(ge=0)
    unresolved_source_action_count: int = Field(ge=0)
    possible_impact_instrument_count: int = Field(ge=0)
    adjustment_file: Literal["part-00000.parquet"] = "part-00000.parquet"
    adjustment_logical_fingerprint: str = Field(pattern=_SHA256)
    adjustment_parquet_sha256: str = Field(pattern=_SHA256)
    adjustment_parquet_bytes: int = Field(ge=1)
    row_scope: Literal["affected_or_quarantined_eod_rows_only"] = (
        "affected_or_quarantined_eod_rows_only"
    )
    factor_direction: Literal["multiply_raw_value_to_basis"] = (
        "multiply_raw_value_to_basis"
    )
    split_adjustment_scope: Literal["split_only"] = "split_only"
    source_coverage_status: Literal["bounded_query_snapshot_only"] = (
        "bounded_query_snapshot_only"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    absent_row_neutrality_authorized: Literal[False] = False
    total_return_adjustment_authorized: Literal[False] = False
    full_adjustment_coverage_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator(
        "canonical_action_publication_path", "eod_evidence_path"
    )
    @classmethod
    def evidence_paths_are_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
            or not value.endswith("/manifest.json")
        ):
            raise ValueError("split-adjustment evidence path is invalid")
        return value

    @field_validator("source_data_cutoff", "calculated_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def publication_reconciles(
        self,
    ) -> "CanonicalSplitAdjustmentPublicationV1":
        if not (
            self.first_source_session
            <= self.last_source_session
            == self.basis_session
        ):
            raise ValueError("split-adjustment session range differs")
        if self.source_data_cutoff > self.calculated_at:
            raise ValueError("split-adjustment calculation precedes source cutoff")
        if self.record_count != (
            self.clear_record_count + self.quarantined_record_count
        ):
            raise ValueError("split-adjustment row counts differ")
        if self.clear_instrument_count > self.selected_instrument_count or (
            self.quarantined_instrument_count > self.selected_instrument_count
        ):
            raise ValueError("split-adjustment instrument counts differ")
        if self.selected_without_eod_count > self.selected_instrument_count:
            raise ValueError("split-adjustment missing-EOD count differs")
        if canonical_split_adjustment_publication_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("split-adjustment publication fingerprint differs")
        return self


class CanonicalSplitAdjustmentPlanArtifactV1(FrozenContract):
    file_name: Literal["part-00000.parquet", "manifest.json"]
    source_path: str
    target_path: str
    size: int = Field(ge=1)
    sha256: str = Field(pattern=_SHA256)

    @field_validator("source_path", "target_path")
    @classmethod
    def paths_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("canonical split-adjustment plan path is invalid")
        return value


class CanonicalSplitAdjustmentApplyPlanV1(FrozenContract):
    contract_version: Literal[
        "canonical-split-adjustment-apply-plan/1.0"
    ] = APPLY_PLAN_VERSION
    operation: Literal["publish_canonical_split_adjustment"] = (
        "publish_canonical_split_adjustment"
    )
    status: Literal["ready_for_separate_review"] = "ready_for_separate_review"
    planner_source_revision: str = Field(pattern=_GIT_REVISION)
    created_at: datetime
    data_root: str
    candidate_root: str
    target_publication_root: str
    expected_current_state_fingerprint: str = Field(pattern=_SHA256)
    artifacts: tuple[CanonicalSplitAdjustmentPlanArtifactV1, ...]
    publication: CanonicalSplitAdjustmentPublicationV1
    inventory_change_file_count: Literal[2] = 2
    inventory_change_bytes: int = Field(ge=1)
    target_absent_count: Literal[1] = 1
    external_request_count: Literal[0] = 0
    overwritten_file_count: Literal[0] = 0
    deleted_file_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    absent_row_neutrality_authorized: Literal[False] = False
    total_return_adjustment_authorized: Literal[False] = False
    full_adjustment_coverage_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("data_root", "candidate_root", "target_publication_root")
    @classmethod
    def roots_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("canonical split-adjustment plan root is invalid")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "CanonicalSplitAdjustmentApplyPlanV1":
        if self.created_at < self.publication.calculated_at:
            raise ValueError("split-adjustment plan precedes candidate calculation")
        if tuple(item.file_name for item in self.artifacts) != (
            "part-00000.parquet",
            "manifest.json",
        ):
            raise ValueError("split-adjustment plan artifact set differs")
        expected_sources = tuple(
            str(PurePosixPath(self.candidate_root) / item.file_name)
            for item in self.artifacts
        )
        expected_targets = tuple(
            str(PurePosixPath(self.target_publication_root) / item.file_name)
            for item in self.artifacts
        )
        if (
            tuple(item.source_path for item in self.artifacts) != expected_sources
            or tuple(item.target_path for item in self.artifacts) != expected_targets
            or self.inventory_change_bytes != sum(item.size for item in self.artifacts)
        ):
            raise ValueError("split-adjustment plan artifact binding differs")
        expected_target = (
            PurePosixPath(self.data_root)
            / "market-data"
            / "adjustment-ledger"
            / "schema_version=1"
            / f"methodology_version={self.publication.methodology_version}"
            / f"basis_session={self.publication.basis_session.isoformat()}"
            / f"coverage_id={self.publication.logical_fingerprint}"
        )
        if PurePosixPath(self.target_publication_root) != expected_target:
            raise ValueError("split-adjustment target publication path differs")
        if canonical_split_adjustment_apply_plan_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("canonical split-adjustment Apply-plan fingerprint differs")
        return self


def build_canonical_split_adjustment_publication(
    **values: object,
) -> CanonicalSplitAdjustmentPublicationV1:
    provisional = CanonicalSplitAdjustmentPublicationV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return CanonicalSplitAdjustmentPublicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": (
                canonical_split_adjustment_publication_fingerprint(provisional)
            ),
        }
    )


def build_canonical_split_adjustment_apply_plan(
    **values: object,
) -> CanonicalSplitAdjustmentApplyPlanV1:
    provisional = CanonicalSplitAdjustmentApplyPlanV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return CanonicalSplitAdjustmentApplyPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": canonical_split_adjustment_apply_plan_fingerprint(
                provisional
            ),
        }
    )


def canonical_split_adjustment_publication_bytes(
    publication: CanonicalSplitAdjustmentPublicationV1,
) -> bytes:
    return (
        json.dumps(publication.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def canonical_split_adjustment_publication_fingerprint(
    publication: CanonicalSplitAdjustmentPublicationV1,
) -> str:
    payload = json.dumps(
        to_jsonable_python(
            publication.model_dump(mode="json", exclude={"logical_fingerprint"})
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_split_adjustment_apply_plan_fingerprint(
    plan: CanonicalSplitAdjustmentApplyPlanV1,
) -> str:
    payload = json.dumps(
        to_jsonable_python(
            plan.model_dump(mode="json", exclude={"logical_fingerprint"})
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
