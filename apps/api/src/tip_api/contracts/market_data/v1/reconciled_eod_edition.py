"""Contracts for one immutable reconciled EOD research edition."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime


SESSION_CONTRACT_VERSION = "reconciled-eod-price-bar-edition-session/1.0"
INTERVAL_CONTRACT_VERSION = "reconciled-eod-price-bar-edition-interval/1.0"
APPLY_PLAN_CONTRACT_VERSION = "reconciled-eod-price-bar-edition-apply-plan/1.0"
DATASET_NAME = "reconciled-eod-price-bar-editions"
MAPPER_POLICY_ID = "massive-exact-provider-symbol-v1"
_SHA256 = r"^[0-9a-f]{64}$"
_REVISION = r"^[0-9a-f]{40}$"
_EDITION_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReconciledEodSourceProvenance(StrEnum):
    RETAINED_ORIGINAL = "retained_original"
    LATER_REACQUISITION = "later_reacquisition"


class ReconciledEodDiffDisposition(StrEnum):
    IDENTICAL = "identical"
    ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY = (
        "accepted_case_sensitive_additions_only"
    )
    ACCEPTED_LATER_REACQUISITION = "accepted_later_reacquisition"
    QUARANTINED = "quarantined"


class ReconciledEodDiffSummaryV1(FrozenModel):
    base_record_count: int = Field(ge=1)
    rebuilt_record_count: int = Field(ge=1)
    unchanged_record_count: int = Field(ge=0)
    provenance_only_change_count: int = Field(ge=0)
    unexpected_provenance_change_count: int = Field(ge=0)
    added_record_count: int = Field(ge=0)
    unexpected_added_record_count: int = Field(ge=0)
    absent_record_count: int = Field(ge=0)
    economic_change_record_count: int = Field(ge=0)
    disposition: ReconciledEodDiffDisposition
    quarantine_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def counts_and_disposition_reconcile(self) -> "ReconciledEodDiffSummaryV1":
        shared = (
            self.unchanged_record_count
            + self.provenance_only_change_count
            + self.economic_change_record_count
        )
        if self.base_record_count != shared + self.absent_record_count:
            raise ValueError("base EOD diff counts do not reconcile")
        if self.rebuilt_record_count != shared + self.added_record_count:
            raise ValueError("rebuilt EOD diff counts do not reconcile")
        if self.unexpected_added_record_count > self.added_record_count:
            raise ValueError("unexpected additions exceed all additions")
        if self.unexpected_provenance_change_count > self.provenance_only_change_count:
            raise ValueError("unexpected provenance changes exceed all such changes")
        blocking = (
            self.unexpected_added_record_count
            + self.unexpected_provenance_change_count
            + self.absent_record_count
            + self.economic_change_record_count
        )
        if self.disposition == ReconciledEodDiffDisposition.QUARANTINED:
            if blocking == 0 or not self.quarantine_reasons:
                raise ValueError("quarantined EOD diff lacks a blocking reason")
            return self
        if blocking or self.quarantine_reasons:
            raise ValueError("accepted EOD diff contains a blocking difference")
        if self.disposition == ReconciledEodDiffDisposition.IDENTICAL:
            if self.added_record_count or self.provenance_only_change_count:
                raise ValueError("identical EOD diff contains changed records")
        elif (
            self.disposition
            == ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY
            and self.added_record_count == 0
        ):
            raise ValueError("addition-only disposition has no additions")
        return self


class ReconciledEodSessionManifestV1(FrozenModel):
    contract_version: Literal[
        "reconciled-eod-price-bar-edition-session/1.0"
    ] = SESSION_CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "reconciled-eod-price-bar-editions"
    ] = DATASET_NAME
    data_family_id: Literal["reconciled_eod_price_bar"] = (
        "reconciled_eod_price_bar"
    )
    data_layer: Literal["research_candidate"] = "research_candidate"
    content_scope: Literal["internal_only"] = "internal_only"
    edition_id: str
    session_date: date
    provider: str
    mapper_policy_id: Literal[
        "massive-exact-provider-symbol-v1"
    ] = MAPPER_POLICY_ID
    implementation_revision: str = Field(pattern=_REVISION)
    source_provenance: ReconciledEodSourceProvenance
    source_observed_at: datetime
    source_package_manifest_sha256: str = Field(pattern=_SHA256)
    source_package_content_sha256: str = Field(pattern=_SHA256)
    identity_as_of_date: date
    identity_snapshot_fingerprint: str = Field(pattern=_SHA256)
    identity_source_fingerprint: str = Field(pattern=_SHA256)
    base_eod_fingerprint: str = Field(pattern=_SHA256)
    rebuilt_eod_fingerprint: str = Field(pattern=_SHA256)
    diff: ReconciledEodDiffSummaryV1
    quality_summary_fingerprint: str = Field(pattern=_SHA256)
    quality_warnings: tuple[str, ...] = ()
    parquet_file: Literal["part-00000.parquet"] = "part-00000.parquet"
    parquet_sha256: str = Field(pattern=_SHA256)
    created_at: datetime
    candidate_authority: Literal[False] = False
    production_authority: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("edition_id")
    @classmethod
    def edition_id_is_bounded(cls, value: str) -> str:
        if not isinstance(value, str) or not _EDITION_ID.fullmatch(value):
            raise ValueError("edition_id is invalid")
        return value

    @field_validator("provider")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider is required")
        return value.strip()

    @field_validator("source_observed_at", "created_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("quality_warnings")
    @classmethod
    def warnings_are_unique_and_ordered(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))):
            raise ValueError("quality warnings must be unique and ordered")
        return value

    @model_validator(mode="after")
    def bindings_reconcile(
        self,
        info: ValidationInfo,
    ) -> "ReconciledEodSessionManifestV1":
        if self.identity_as_of_date != self.session_date:
            raise ValueError("reconciled EOD requires same-session Identity")
        if self.diff.disposition == ReconciledEodDiffDisposition.QUARANTINED:
            raise ValueError("quarantined EOD diff cannot publish a completed session")
        if self.rebuilt_eod_fingerprint == self.base_eod_fingerprint:
            if self.diff.disposition != ReconciledEodDiffDisposition.IDENTICAL:
                raise ValueError("matching EOD fingerprints require identical diff")
        elif self.diff.disposition == ReconciledEodDiffDisposition.IDENTICAL:
            raise ValueError("identical diff requires matching EOD fingerprints")
        if (
            self.diff.disposition
            == ReconciledEodDiffDisposition.ACCEPTED_LATER_REACQUISITION
            and self.source_provenance
            != ReconciledEodSourceProvenance.LATER_REACQUISITION
        ):
            raise ValueError("reacquisition diff requires later source provenance")
        if (
            self.source_provenance
            == ReconciledEodSourceProvenance.LATER_REACQUISITION
            and self.diff.disposition
            == ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY
        ):
            raise ValueError("later source must retain its reacquisition disposition")
        if info.context and info.context.get("allow_unsealed_manifest"):
            return self
        expected = reconciled_eod_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("reconciled EOD session fingerprint mismatch")
        return self


class ReconciledEodIntervalSessionReferenceV1(FrozenModel):
    session_date: date
    session_manifest_fingerprint: str = Field(pattern=_SHA256)
    rebuilt_eod_fingerprint: str = Field(pattern=_SHA256)
    record_count: int = Field(ge=1)
    added_record_count: int = Field(ge=0)
    source_provenance: ReconciledEodSourceProvenance
    disposition: Literal[
        "identical",
        "accepted_case_sensitive_additions_only",
        "accepted_later_reacquisition",
    ]


class ReconciledEodIntervalManifestV1(FrozenModel):
    contract_version: Literal[
        "reconciled-eod-price-bar-edition-interval/1.0"
    ] = INTERVAL_CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "reconciled-eod-price-bar-editions"
    ] = DATASET_NAME
    edition_id: str
    provider: str
    mapper_policy_id: Literal[
        "massive-exact-provider-symbol-v1"
    ] = MAPPER_POLICY_ID
    implementation_revision: str = Field(pattern=_REVISION)
    evaluation_first_session: date
    evaluation_last_session: date
    warmup_first_session: date | None = None
    warmup_last_session: date | None = None
    sessions: tuple[ReconciledEodIntervalSessionReferenceV1, ...]
    retained_original_session_count: int = Field(ge=0)
    later_reacquisition_session_count: int = Field(ge=0)
    added_record_count: int = Field(ge=0)
    source_gap_count: Literal[0] = 0
    quarantine_count: Literal[0] = 0
    created_at: datetime
    candidate_authority: Literal[False] = False
    production_authority: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("edition_id")
    @classmethod
    def edition_id_is_bounded(cls, value: str) -> str:
        if not isinstance(value, str) or not _EDITION_ID.fullmatch(value):
            raise ValueError("edition_id is invalid")
        return value

    @field_validator("provider")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider is required")
        return value.strip()

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def interval_reconciles(
        self,
        info: ValidationInfo,
    ) -> "ReconciledEodIntervalManifestV1":
        if self.evaluation_first_session > self.evaluation_last_session:
            raise ValueError("evaluation interval is reversed")
        if (self.warmup_first_session is None) != (self.warmup_last_session is None):
            raise ValueError("warmup bounds must both be present or absent")
        if self.warmup_first_session is not None:
            if not (
                self.warmup_first_session
                <= self.warmup_last_session
                < self.evaluation_first_session
            ):
                raise ValueError("warmup interval is invalid")
        dates = tuple(item.session_date for item in self.sessions)
        if not dates or dates != tuple(sorted(set(dates))):
            raise ValueError("edition sessions must be non-empty, unique, and ordered")
        if dates[-1] != self.evaluation_last_session:
            raise ValueError("edition does not end at the evaluation boundary")
        expected_first = self.warmup_first_session or self.evaluation_first_session
        if dates[0] != expected_first or self.evaluation_first_session not in dates:
            raise ValueError("edition does not cover its declared first boundary")
        if (
            self.retained_original_session_count
            + self.later_reacquisition_session_count
            != len(self.sessions)
        ):
            raise ValueError("edition provenance counts do not reconcile")
        if self.retained_original_session_count != sum(
            item.source_provenance
            == ReconciledEodSourceProvenance.RETAINED_ORIGINAL
            for item in self.sessions
        ):
            raise ValueError("retained-original session count differs")
        if self.added_record_count != sum(
            item.added_record_count for item in self.sessions
        ):
            raise ValueError("edition added-record count is inconsistent")
        if any(
            (
                item.disposition == ReconciledEodDiffDisposition.IDENTICAL
                and item.added_record_count != 0
            )
            or (
                item.disposition
                == ReconciledEodDiffDisposition.ACCEPTED_CASE_SENSITIVE_ADDITIONS_ONLY
                and item.added_record_count == 0
            )
            for item in self.sessions
        ):
            raise ValueError("session addition count differs from disposition")
        if info.context and info.context.get("allow_unsealed_manifest"):
            return self
        expected = reconciled_eod_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("reconciled EOD interval fingerprint mismatch")
        return self


class ReconciledEodEditionApplyArtifactV1(FrozenModel):
    relative_path: str
    size: int = Field(ge=1)
    sha256: str = Field(pattern=_SHA256)

    @field_validator("relative_path")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
            or len(path.parts) not in {1, 2}
        ):
            raise ValueError("reconciled EOD artifact relative path is invalid")
        if len(path.parts) == 1:
            if value != "interval-manifest.json":
                raise ValueError("reconciled EOD root artifact is invalid")
        elif (
            not path.parts[0].startswith("session_date=")
            or path.parts[1] not in {"manifest.json", "part-00000.parquet"}
        ):
            raise ValueError("reconciled EOD session artifact is invalid")
        return value


class ReconciledEodEditionApplyPlanV1(FrozenModel):
    contract_version: Literal[
        "reconciled-eod-price-bar-edition-apply-plan/1.0"
    ] = APPLY_PLAN_CONTRACT_VERSION
    operation: Literal["publish_complete_reconciled_eod_edition"] = (
        "publish_complete_reconciled_eod_edition"
    )
    status: Literal["ready_for_separate_apply"] = "ready_for_separate_apply"
    created_at: datetime
    planner_revision: str = Field(pattern=_REVISION)
    candidate_implementation_revision: str = Field(pattern=_REVISION)
    edition_id: str
    data_root: str
    candidate_location_fingerprint: str = Field(pattern=_SHA256)
    target_edition_path: str
    expected_current_state_fingerprint: str = Field(pattern=_SHA256)
    candidate_interval_manifest_fingerprint: str = Field(pattern=_SHA256)
    candidate_inventory_fingerprint: str = Field(pattern=_SHA256)
    candidate_session_count: int = Field(ge=1)
    candidate_record_count: int = Field(ge=1)
    candidate_added_record_count: int = Field(ge=0)
    artifacts: tuple[ReconciledEodEditionApplyArtifactV1, ...]
    inventory_change_file_count: int = Field(ge=3)
    inventory_change_bytes: int = Field(ge=1)
    target_absent_partition_count: Literal[1] = 1
    candidate_formal_read_complete: Literal[True] = True
    target_absence_verified: Literal[True] = True
    current_inventory_bound: Literal[True] = True
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    candidate_authority: Literal[False] = False
    production_authority: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("edition_id")
    @classmethod
    def edition_id_is_bounded(cls, value: str) -> str:
        if not isinstance(value, str) or not _EDITION_ID.fullmatch(value):
            raise ValueError("edition_id is invalid")
        return value

    @field_validator("data_root", "target_edition_path")
    @classmethod
    def roots_are_absolute(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("reconciled EOD plan root is invalid")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self, info: ValidationInfo) -> "ReconciledEodEditionApplyPlanV1":
        target_edition = (
            PurePosixPath(self.data_root)
            / "market-data"
            / DATASET_NAME
            / "contract_version=1"
            / f"edition_id={self.edition_id}"
        )
        if PurePosixPath(self.target_edition_path) != target_edition:
            raise ValueError("reconciled EOD target edition path differs")
        relative_paths = tuple(item.relative_path for item in self.artifacts)
        expected_order = tuple(
            sorted(path for path in relative_paths if path != "interval-manifest.json")
        ) + ("interval-manifest.json",)
        if relative_paths != expected_order or len(set(relative_paths)) != len(
            relative_paths
        ):
            raise ValueError("reconciled EOD Apply artifacts are unordered")
        session_files: dict[str, set[str]] = {}
        for item in self.artifacts:
            relative = PurePosixPath(item.relative_path)
            if len(relative.parts) == 2:
                session_files.setdefault(relative.parts[0], set()).add(
                    relative.parts[1]
                )
        if (
            len(session_files) != self.candidate_session_count
            or any(
                names != {"manifest.json", "part-00000.parquet"}
                for names in session_files.values()
            )
        ):
            raise ValueError("reconciled EOD session artifact set differs")
        if self.inventory_change_file_count != len(self.artifacts):
            raise ValueError("reconciled EOD inventory file count differs")
        if self.inventory_change_bytes != sum(item.size for item in self.artifacts):
            raise ValueError("reconciled EOD inventory bytes differ")
        if self.candidate_inventory_fingerprint != (
            reconciled_eod_apply_inventory_fingerprint(self.artifacts)
        ):
            raise ValueError("reconciled EOD candidate inventory differs")
        if info.context and info.context.get("allow_unsealed_manifest"):
            return self
        expected = reconciled_eod_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("reconciled EOD Apply-plan fingerprint mismatch")
        return self


def reconciled_eod_fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def seal_reconciled_eod_session_manifest(
    values: Mapping[str, object],
) -> ReconciledEodSessionManifestV1:
    """Populate defaults, seal one deterministic fingerprint, then validate."""

    if "logical_fingerprint" in values:
        raise ValueError("logical_fingerprint is computed, not supplied")
    draft = ReconciledEodSessionManifestV1.model_validate(
        {**dict(values), "logical_fingerprint": "0" * 64},
        context={"allow_unsealed_manifest": True},
    )
    payload = draft.model_dump(mode="json", exclude={"logical_fingerprint"})
    payload["logical_fingerprint"] = reconciled_eod_fingerprint(payload)
    return ReconciledEodSessionManifestV1.model_validate(payload)


def seal_reconciled_eod_interval_manifest(
    values: Mapping[str, object],
) -> ReconciledEodIntervalManifestV1:
    """Populate defaults, seal the final interval fingerprint, then validate."""

    if "logical_fingerprint" in values:
        raise ValueError("logical_fingerprint is computed, not supplied")
    draft = ReconciledEodIntervalManifestV1.model_validate(
        {**dict(values), "logical_fingerprint": "0" * 64},
        context={"allow_unsealed_manifest": True},
    )
    payload = draft.model_dump(mode="json", exclude={"logical_fingerprint"})
    payload["logical_fingerprint"] = reconciled_eod_fingerprint(payload)
    return ReconciledEodIntervalManifestV1.model_validate(payload)


def reconciled_eod_apply_inventory_fingerprint(
    artifacts: tuple[ReconciledEodEditionApplyArtifactV1, ...],
) -> str:
    return reconciled_eod_fingerprint(
        tuple(item.model_dump(mode="json") for item in artifacts)
    )


def seal_reconciled_eod_apply_plan(
    values: Mapping[str, object],
) -> ReconciledEodEditionApplyPlanV1:
    if "logical_fingerprint" in values:
        raise ValueError("logical_fingerprint is computed, not supplied")
    draft = ReconciledEodEditionApplyPlanV1.model_validate(
        {**dict(values), "logical_fingerprint": "0" * 64},
        context={"allow_unsealed_manifest": True},
    )
    payload = draft.model_dump(mode="json", exclude={"logical_fingerprint"})
    payload["logical_fingerprint"] = reconciled_eod_fingerprint(payload)
    return ReconciledEodEditionApplyPlanV1.model_validate(payload)
