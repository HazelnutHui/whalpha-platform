"""Canonical split-action rows and bounded publication contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import (
    QualityStatus,
    ensure_finite_decimal,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)
from tip_api.contracts.market_data.v1.historical_research import (
    CorporateActionRecordStatus,
    CorporateActionType,
    KnowledgeTimeStatus,
)


PUBLICATION_VERSION = "canonical-split-action-publication/1.0"
APPLY_PLAN_VERSION = "canonical-split-action-apply-plan/1.0"
ROW_SCHEMA_VERSION = "1.0"
_SHA256 = r"^[0-9a-f]{64}$"
_GIT_REVISION = r"^[0-9a-f]{40}$"
_SPLIT_TYPES = frozenset(
    {
        CorporateActionType.STOCK_SPLIT,
        CorporateActionType.REVERSE_SPLIT,
        CorporateActionType.STOCK_DIVIDEND,
    }
)


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CanonicalSplitActionV1(FrozenContract):
    """One resolved provider action in a stable-ID/effective-date event group."""

    schema_version: Literal["1.0"] = ROW_SCHEMA_VERSION
    corporate_action_id: UUID
    instrument_id: UUID
    action_type: CorporateActionType
    effective_date: date
    split_ratio_from: Decimal
    split_ratio_to: Decimal
    source: str
    source_action_id: str
    source_revision: int = Field(ge=1)
    canonical_revision: int = Field(ge=1)
    source_action_set_fingerprint: str = Field(pattern=_SHA256)
    source_publication_fingerprint: str = Field(pattern=_SHA256)
    event_group_size: int = Field(ge=1)
    record_status: CorporateActionRecordStatus
    knowledge_time_status: Literal[KnowledgeTimeStatus.FIRST_OBSERVED_ONLY] = (
        KnowledgeTimeStatus.FIRST_OBSERVED_ONLY
    )
    source_available_at: None = None
    first_observed_at: datetime
    ingested_at: datetime
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    quality_status: QualityStatus
    quality_flags: tuple[str, ...]

    @field_validator("effective_date", mode="before")
    @classmethod
    def reject_datetime_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("effective_date must not receive datetime values")
        return value

    @field_validator("split_ratio_from", "split_ratio_to", mode="before")
    @classmethod
    def reject_float_ratios(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator("split_ratio_from", "split_ratio_to")
    @classmethod
    def positive_ratios(cls, value: Decimal, info: Any) -> Decimal:
        normalized = ensure_finite_decimal(value, field_name=info.field_name)
        if normalized <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return normalized

    @field_validator("source", "source_action_id", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("first_observed_at", "ingested_at")
    @classmethod
    def utc_times(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def normalized_flags(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("quality_flags must be a collection")
        return tuple(
            sorted(
                {
                    normalize_required_string(item, field_name="quality_flags")
                    .lower()
                    .replace("-", "_")
                    .replace(" ", "_")
                    for item in value
                }
            )
        )

    @model_validator(mode="after")
    def row_reconciles(self) -> "CanonicalSplitActionV1":
        if self.action_type not in _SPLIT_TYPES:
            raise ValueError("canonical split action has a non-split action type")
        if self.first_observed_at > self.ingested_at:
            raise ValueError("canonical split action precedes source observation")
        if "source_available_time_unavailable" not in self.quality_flags:
            raise ValueError("canonical split action must preserve unavailable source time")
        if "outcome_reconciliation_only" not in self.quality_flags:
            raise ValueError("canonical split action must preserve outcome-only status")
        if self.event_group_size == 1:
            if (
                self.record_status is not CorporateActionRecordStatus.ACTIVE
                or self.quality_status is not QualityStatus.VALID
                or "multiple_same_date_split_actions" in self.quality_flags
                or "ledger_admission_quarantined" in self.quality_flags
            ):
                raise ValueError("single split action status differs")
        elif (
            self.record_status is not CorporateActionRecordStatus.QUARANTINED
            or self.quality_status is not QualityStatus.PENDING_REVIEW
            or "multiple_same_date_split_actions" not in self.quality_flags
            or "ledger_admission_quarantined" not in self.quality_flags
        ):
            raise ValueError("multiple split-action group must remain quarantined")
        return self


class CanonicalSplitActionQuarantineImpactV1(FrozenContract):
    """One stable ID conservatively exposed to unresolved source rows."""

    instrument_id: UUID
    provider_tickers: tuple[str, ...] = Field(min_length=1)
    effective_dates: tuple[date, ...] = Field(min_length=1)
    source_action_ids: tuple[str, ...] = Field(min_length=1)
    source_action_set_fingerprint: str = Field(pattern=_SHA256)
    source_publication_fingerprint: str = Field(pattern=_SHA256)
    impact_status: Literal["quarantined"] = "quarantined"
    assignment_authorized: Literal[False] = False
    quality_flags: tuple[str, ...] = (
        "unresolved_split_possible_historical_identity",
        "ticker_presence_does_not_assign_action",
    )

    @model_validator(mode="after")
    def impact_reconciles(self) -> "CanonicalSplitActionQuarantineImpactV1":
        if (
            self.provider_tickers != tuple(sorted(set(self.provider_tickers)))
            or self.effective_dates != tuple(sorted(set(self.effective_dates)))
            or self.source_action_ids != tuple(sorted(set(self.source_action_ids)))
            or self.quality_flags
            != (
                "unresolved_split_possible_historical_identity",
                "ticker_presence_does_not_assign_action",
            )
        ):
            raise ValueError("split quarantine impact evidence is not ordered")
        return self


class CanonicalSplitActionPublicationV1(FrozenContract):
    """One immutable split-only canonical Corporate Action publication."""

    manifest_version: Literal[
        "canonical-split-action-publication/1.0"
    ] = PUBLICATION_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["canonical-corporate-action"] = (
        "canonical-corporate-action"
    )
    action_scope: Literal["split_only"] = "split_only"
    source_revision: str = Field(pattern=_GIT_REVISION)
    source_publication_path: str
    source_publication_sha256: str = Field(pattern=_SHA256)
    source_publication_logical_fingerprint: str = Field(pattern=_SHA256)
    candidate_file_sha256: str = Field(pattern=_SHA256)
    candidate_logical_fingerprint: str = Field(pattern=_SHA256)
    start_date: date
    end_date: date
    source_data_cutoff: datetime
    action_file: Literal["actions.parquet"] = "actions.parquet"
    action_record_count: int = Field(ge=1)
    active_action_record_count: int = Field(ge=0)
    quarantined_action_record_count: int = Field(ge=0)
    event_group_count: int = Field(ge=1)
    clear_event_group_count: int = Field(ge=0)
    quarantined_event_group_count: int = Field(ge=0)
    unresolved_source_action_count: int = Field(ge=0)
    possible_impact_instrument_count: int = Field(ge=0)
    possible_unresolved_impacts: tuple[CanonicalSplitActionQuarantineImpactV1, ...]
    action_logical_fingerprint: str = Field(pattern=_SHA256)
    action_parquet_sha256: str = Field(pattern=_SHA256)
    action_parquet_bytes: int = Field(ge=1)
    source_coverage_status: Literal["bounded_query_snapshot_only"] = (
        "bounded_query_snapshot_only"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    canonical_split_action_scope_published: Literal[True] = True
    full_corporate_action_coverage_authorized: Literal[False] = False
    neutral_factor_inference_authorized: Literal[False] = False
    adjustment_ledger_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    created_at: datetime
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("source_publication_path")
    @classmethod
    def source_path_is_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
            or not value.endswith("/manifest.json")
        ):
            raise ValueError("split-action source publication path is invalid")
        return value

    @field_validator("source_data_cutoff", "created_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def publication_reconciles(self) -> "CanonicalSplitActionPublicationV1":
        if self.end_date < self.start_date or self.source_data_cutoff > self.created_at:
            raise ValueError("canonical split-action time boundary differs")
        if self.action_record_count != (
            self.active_action_record_count + self.quarantined_action_record_count
        ):
            raise ValueError("canonical split-action record counts differ")
        if self.event_group_count != (
            self.clear_event_group_count + self.quarantined_event_group_count
        ):
            raise ValueError("canonical split-action event counts differ")
        if (
            self.possible_impact_instrument_count
            != len(self.possible_unresolved_impacts)
            or self.possible_unresolved_impacts
            != tuple(
                sorted(
                    self.possible_unresolved_impacts,
                    key=lambda item: str(item.instrument_id),
                )
            )
            or any(
                item.source_publication_fingerprint
                != self.source_publication_logical_fingerprint
                for item in self.possible_unresolved_impacts
            )
        ):
            raise ValueError("canonical split-action impacts differ")
        if canonical_split_action_publication_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("canonical split-action publication fingerprint differs")
        return self


class CanonicalSplitActionPlanArtifactV1(FrozenContract):
    file_name: Literal["actions.parquet", "manifest.json"]
    source_path: str
    target_path: str
    size: int = Field(ge=1)
    sha256: str = Field(pattern=_SHA256)

    @field_validator("source_path", "target_path")
    @classmethod
    def paths_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("canonical split-action plan path is invalid")
        return value


class CanonicalSplitActionApplyPlanV1(FrozenContract):
    contract_version: Literal[
        "canonical-split-action-apply-plan/1.0"
    ] = APPLY_PLAN_VERSION
    operation: Literal["publish_canonical_split_actions"] = (
        "publish_canonical_split_actions"
    )
    status: Literal["ready_for_separate_review"] = "ready_for_separate_review"
    source_revision: str = Field(pattern=_GIT_REVISION)
    created_at: datetime
    data_root: str
    split_candidate_root: str
    candidate_root: str
    target_publication_root: str
    expected_current_state_fingerprint: str = Field(pattern=_SHA256)
    artifacts: tuple[CanonicalSplitActionPlanArtifactV1, ...]
    publication: CanonicalSplitActionPublicationV1
    inventory_change_file_count: Literal[2] = 2
    inventory_change_bytes: int = Field(ge=1)
    target_absent_count: Literal[1] = 1
    external_request_count: Literal[0] = 0
    overwritten_file_count: Literal[0] = 0
    deleted_file_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    adjustment_ledger_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "data_root",
        "split_candidate_root",
        "candidate_root",
        "target_publication_root",
    )
    @classmethod
    def roots_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("canonical split-action plan root is invalid")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "CanonicalSplitActionApplyPlanV1":
        if (
            self.created_at != self.publication.created_at
            or self.source_revision != self.publication.source_revision
        ):
            raise ValueError("split-action plan/publication time differs")
        if tuple(item.file_name for item in self.artifacts) != (
            "actions.parquet",
            "manifest.json",
        ):
            raise ValueError("split-action plan artifact set differs")
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
            raise ValueError("split-action plan artifact binding differs")
        expected_target = (
            PurePosixPath(self.data_root)
            / "market-data"
            / "canonical-corporate-actions"
            / "schema_version=1"
            / "action_scope=split"
            / f"coverage_id={self.publication.logical_fingerprint}"
        )
        if PurePosixPath(self.target_publication_root) != expected_target:
            raise ValueError("split-action target publication path differs")
        if canonical_split_action_apply_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("canonical split-action Apply-plan fingerprint differs")
        return self


def build_canonical_split_action_publication(
    **values: object,
) -> CanonicalSplitActionPublicationV1:
    provisional = CanonicalSplitActionPublicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return CanonicalSplitActionPublicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": canonical_split_action_publication_fingerprint(
                provisional
            ),
        }
    )


def build_canonical_split_action_apply_plan(
    **values: object,
) -> CanonicalSplitActionApplyPlanV1:
    provisional = CanonicalSplitActionApplyPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return CanonicalSplitActionApplyPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": canonical_split_action_apply_plan_fingerprint(
                provisional
            ),
        }
    )


def canonical_split_action_publication_bytes(
    publication: CanonicalSplitActionPublicationV1,
) -> bytes:
    return (
        json.dumps(publication.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def canonical_split_action_publication_fingerprint(
    publication: CanonicalSplitActionPublicationV1,
) -> str:
    return _fingerprint(
        publication.model_dump(mode="json", exclude={"logical_fingerprint"})
    )


def canonical_split_action_apply_plan_fingerprint(
    plan: CanonicalSplitActionApplyPlanV1,
) -> str:
    return _fingerprint(plan.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
