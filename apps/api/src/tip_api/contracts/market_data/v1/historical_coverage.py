"""Physical evidence contracts for bounded historical coverage publications."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_research import (
    HistoricalCoverageManifestV1,
    HistoricalDatasetFamily,
    RESEARCH_REQUIRED_DATASET_FAMILIES,
)


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalCoverageFileReferenceV1(FrozenContract):
    path: str
    physical_sha256: str

    @field_validator("path", mode="before")
    @classmethod
    def normalized_path(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("path must be normalized and relative")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def hash_is_valid(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class HistoricalCoverageArtifactEvidenceV1(FrozenContract):
    completion_manifest: HistoricalCoverageFileReferenceV1
    payload_files: tuple[HistoricalCoverageFileReferenceV1, ...] = Field(
        min_length=1
    )
    first_session: date
    last_session: date
    record_count: int = Field(ge=0)
    logical_fingerprint: str

    @field_validator("first_session", "last_session", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session fields must contain dates")
        return value

    @field_validator("logical_fingerprint")
    @classmethod
    def logical_hash_is_valid(cls, value: str) -> str:
        return _sha(value, "logical_fingerprint")

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "HistoricalCoverageArtifactEvidenceV1":
        completion_name = PurePosixPath(self.completion_manifest.path).name
        if completion_name not in {"manifest.json", "interval-manifest.json"}:
            raise ValueError(
                "completion manifest path must name a supported manifest"
            )
        if self.last_session < self.first_session:
            raise ValueError("last_session must not precede first_session")
        paths = tuple(item.path for item in self.payload_files)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("payload file paths must be unique and sorted")
        if self.completion_manifest.path in paths:
            raise ValueError("completion manifest cannot also be a payload file")
        return self


class HistoricalDatasetCoverageEvidenceV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    evidence_version: Literal["historical-dataset-coverage-evidence/1.0"] = (
        "historical-dataset-coverage-evidence/1.0"
    )
    family: HistoricalDatasetFamily
    sessions: tuple[date, ...] = Field(min_length=1)
    artifacts: tuple[HistoricalCoverageArtifactEvidenceV1, ...] = Field(
        min_length=1
    )
    record_count: int = Field(ge=0)
    completed: Literal[True] = True
    quarantined_record_count: int = Field(ge=0)
    created_at: datetime
    logical_fingerprint: str

    @field_validator("sessions", mode="before")
    @classmethod
    def ordered_sessions(cls, value: Any) -> tuple[date, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("sessions must be an ordered collection")
        sessions = tuple(value)
        if any(isinstance(item, datetime) for item in sessions):
            raise ValueError("sessions must contain dates")
        if sessions != tuple(sorted(set(sessions))):
            raise ValueError("sessions must be unique and ordered")
        return sessions

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("logical_fingerprint")
    @classmethod
    def logical_hash_is_valid(cls, value: str) -> str:
        return _sha(value, "logical_fingerprint")

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "HistoricalDatasetCoverageEvidenceV1":
        if self.family not in RESEARCH_REQUIRED_DATASET_FAMILIES:
            raise ValueError("dataset coverage evidence family is not research-required")
        paths = tuple(item.completion_manifest.path for item in self.artifacts)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("artifact completion manifests must be unique and sorted")
        if sum(item.record_count for item in self.artifacts) != self.record_count:
            raise ValueError("artifact record counts do not reconcile")
        if self.quarantined_record_count > self.record_count:
            raise ValueError("quarantined count cannot exceed record count")
        if any(
            not any(
                artifact.first_session <= session <= artifact.last_session
                for artifact in self.artifacts
            )
            for session in self.sessions
        ):
            raise ValueError("artifact coverage does not include every session")
        if (
            historical_dataset_coverage_evidence_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("dataset coverage evidence fingerprint mismatch")
        return self


CURRENT_HISTORICAL_FAMILY_EVIDENCE_PUBLICATION_PLAN_VERSION = (
    "current-historical-family-evidence-publication-plan/1.0"
)
RECONCILED_EOD_HISTORICAL_FAMILY_EVIDENCE_PUBLICATION_PLAN_VERSION = (
    "reconciled-eod-historical-family-evidence-publication-plan/1.0"
)
CURRENT_HISTORICAL_FAMILY_EVIDENCE_PLAN_FAMILIES = (
    HistoricalDatasetFamily.EOD_PRICE_BAR,
    HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY,
)


class CurrentHistoricalFamilyEvidencePlanItemV1(FrozenContract):
    """One exact unpublished family-evidence target and its source-bound bytes."""

    family: HistoricalDatasetFamily
    target_path: str
    expected_target_state: Literal["absent"] = "absent"
    expected_target_state_fingerprint: str
    evidence: HistoricalDatasetCoverageEvidenceV1
    evidence_manifest_bytes: int = Field(ge=1)
    evidence_manifest_sha256: str
    source_artifact_count: int = Field(ge=1)
    source_file_count: int = Field(ge=1)
    record_count: int = Field(ge=0)

    @field_validator("target_path", mode="before")
    @classmethod
    def normalized_target_path(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="target_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("target_path must be normalized and relative")
        return normalized

    @field_validator("expected_target_state_fingerprint", "evidence_manifest_sha256")
    @classmethod
    def hashes_are_valid(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def item_reconciles(self) -> "CurrentHistoricalFamilyEvidencePlanItemV1":
        expected_target = historical_dataset_coverage_evidence_target_path(
            self.evidence
        )
        manifest_bytes = historical_dataset_coverage_evidence_bytes(self.evidence)
        if self.family is not self.evidence.family:
            raise ValueError("planned family differs from embedded evidence")
        if self.target_path != expected_target:
            raise ValueError("family-evidence target path differs")
        if self.expected_target_state_fingerprint != _fingerprint(
            {"path": self.target_path, "state": "absent"}
        ):
            raise ValueError("family-evidence target-state fingerprint differs")
        if self.evidence_manifest_bytes != len(manifest_bytes):
            raise ValueError("family-evidence manifest byte count differs")
        if self.evidence_manifest_sha256 != hashlib.sha256(manifest_bytes).hexdigest():
            raise ValueError("family-evidence manifest SHA-256 differs")
        if self.source_artifact_count != len(self.evidence.artifacts):
            raise ValueError("family-evidence source artifact count differs")
        expected_file_count = sum(
            1 + len(artifact.payload_files) for artifact in self.evidence.artifacts
        )
        if self.source_file_count != expected_file_count:
            raise ValueError("family-evidence source file count differs")
        if self.record_count != self.evidence.record_count:
            raise ValueError("family-evidence record count differs")
        return self


class CurrentHistoricalFamilyEvidencePublicationPlanV1(FrozenContract):
    """Deterministic no-write plan for the current EOD and Identity evidence."""

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        "current-historical-family-evidence-publication-plan/1.0"
    ] = CURRENT_HISTORICAL_FAMILY_EVIDENCE_PUBLICATION_PLAN_VERSION
    operation: Literal["publish_current_historical_family_evidence"] = (
        "publish_current_historical_family_evidence"
    )
    status: Literal["ready_for_separate_review"] = "ready_for_separate_review"
    planned_from_evidence_at: datetime
    data_root: str
    first_session: date
    last_session: date
    session_count: int = Field(ge=1)
    families: tuple[CurrentHistoricalFamilyEvidencePlanItemV1, ...] = Field(
        min_length=2,
        max_length=2,
    )
    family_set_fingerprint: str
    inventory_change_file_count: Literal[2] = 2
    inventory_change_bytes: int = Field(ge=1)
    target_absent_count: Literal[2] = 2
    source_formal_read_complete: Literal[True] = True
    target_absence_verified: Literal[True] = True
    recovery_policy: Literal["verify_exact_then_complete"] = (
        "verify_exact_then_complete"
    )
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    apply_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_development_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("planned_from_evidence_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("data_root", mode="before")
    @classmethod
    def normalized_absolute_root(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="data_root")
        path = PurePosixPath(normalized)
        if not path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("data_root must be normalized and absolute")
        return normalized

    @field_validator("first_session", "last_session", mode="before")
    @classmethod
    def reject_datetime_sessions(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session fields must contain dates")
        return value

    @field_validator("family_set_fingerprint", "logical_fingerprint")
    @classmethod
    def hashes_are_valid(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "CurrentHistoricalFamilyEvidencePublicationPlanV1":
        if tuple(item.family for item in self.families) != (
            CURRENT_HISTORICAL_FAMILY_EVIDENCE_PLAN_FAMILIES
        ):
            raise ValueError("publication plan family set is incomplete or unordered")
        sessions = self.families[0].evidence.sessions
        if any(item.evidence.sessions != sessions for item in self.families[1:]):
            raise ValueError("publication plan family session coverage differs")
        if (
            self.first_session != sessions[0]
            or self.last_session != sessions[-1]
            or self.session_count != len(sessions)
        ):
            raise ValueError("publication plan session summary differs")
        if self.planned_from_evidence_at != max(
            item.evidence.created_at for item in self.families
        ):
            raise ValueError("publication plan evidence time differs")
        if self.family_set_fingerprint != (
            current_historical_family_evidence_plan_family_set_fingerprint(
                self.families
            )
        ):
            raise ValueError("publication plan family-set fingerprint differs")
        if self.inventory_change_bytes != sum(
            item.evidence_manifest_bytes for item in self.families
        ):
            raise ValueError("publication plan inventory byte count differs")
        if (
            current_historical_family_evidence_publication_plan_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("publication plan logical fingerprint differs")
        return self


class ReconciledEodHistoricalFamilyEvidencePublicationPlanV1(
    CurrentHistoricalFamilyEvidencePublicationPlanV1
):
    """Exact no-write plan for one reconciled EOD edition and Identity."""

    contract_version: Literal[
        "reconciled-eod-historical-family-evidence-publication-plan/1.0"
    ] = RECONCILED_EOD_HISTORICAL_FAMILY_EVIDENCE_PUBLICATION_PLAN_VERSION
    operation: Literal[
        "publish_reconciled_eod_historical_family_evidence"
    ] = "publish_reconciled_eod_historical_family_evidence"
    source_edition_id: str
    source_interval_manifest_fingerprint: str

    @field_validator("source_edition_id", mode="before")
    @classmethod
    def edition_id_is_normalized(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="source_edition_id")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
        if (
            len(normalized) > 64
            or normalized[0] == "-"
            or normalized[-1] == "-"
            or any(character not in allowed for character in normalized)
        ):
            raise ValueError("source_edition_id is invalid")
        return normalized

    @field_validator("source_interval_manifest_fingerprint")
    @classmethod
    def source_interval_hash_is_valid(cls, value: str) -> str:
        return _sha(value, "source_interval_manifest_fingerprint")

    @model_validator(mode="after")
    def edition_binding_reconciles(
        self,
    ) -> "ReconciledEodHistoricalFamilyEvidencePublicationPlanV1":
        eod = self.families[0].evidence
        if len(eod.artifacts) != 1:
            raise ValueError("reconciled EOD plan requires one edition artifact")
        artifact = eod.artifacts[0]
        expected_completion = (
            PurePosixPath("market-data")
            / "reconciled-eod-price-bar-editions"
            / "contract_version=1"
            / f"edition_id={self.source_edition_id}"
            / "interval-manifest.json"
        ).as_posix()
        if (
            artifact.completion_manifest.path != expected_completion
            or artifact.logical_fingerprint
            != self.source_interval_manifest_fingerprint
        ):
            raise ValueError("reconciled EOD plan edition binding differs")
        return self


def build_historical_dataset_coverage_evidence(
    *,
    family: HistoricalDatasetFamily,
    sessions: tuple[date, ...],
    artifacts: tuple[HistoricalCoverageArtifactEvidenceV1, ...],
    record_count: int,
    quarantined_record_count: int,
    created_at: datetime,
) -> HistoricalDatasetCoverageEvidenceV1:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_version": "historical-dataset-coverage-evidence/1.0",
        "family": family,
        "sessions": sessions,
        "artifacts": artifacts,
        "record_count": record_count,
        "completed": True,
        "quarantined_record_count": quarantined_record_count,
        "created_at": created_at,
    }
    provisional = HistoricalDatasetCoverageEvidenceV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return HistoricalDatasetCoverageEvidenceV1.model_validate(
        {
            **payload,
            "logical_fingerprint": (
                historical_dataset_coverage_evidence_fingerprint(provisional)
            ),
        }
    )


def build_current_historical_family_evidence_plan_item(
    evidence: HistoricalDatasetCoverageEvidenceV1,
) -> CurrentHistoricalFamilyEvidencePlanItemV1:
    target_path = historical_dataset_coverage_evidence_target_path(evidence)
    manifest_bytes = historical_dataset_coverage_evidence_bytes(evidence)
    return CurrentHistoricalFamilyEvidencePlanItemV1(
        family=evidence.family,
        target_path=target_path,
        expected_target_state="absent",
        expected_target_state_fingerprint=_fingerprint(
            {"path": target_path, "state": "absent"}
        ),
        evidence=evidence,
        evidence_manifest_bytes=len(manifest_bytes),
        evidence_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        source_artifact_count=len(evidence.artifacts),
        source_file_count=sum(
            1 + len(artifact.payload_files) for artifact in evidence.artifacts
        ),
        record_count=evidence.record_count,
    )


def build_current_historical_family_evidence_publication_plan(
    **values: object,
) -> CurrentHistoricalFamilyEvidencePublicationPlanV1:
    provisional = CurrentHistoricalFamilyEvidencePublicationPlanV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return CurrentHistoricalFamilyEvidencePublicationPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": (
                current_historical_family_evidence_publication_plan_fingerprint(
                    provisional
                )
            ),
        }
    )


def build_reconciled_eod_historical_family_evidence_publication_plan(
    **values: object,
) -> ReconciledEodHistoricalFamilyEvidencePublicationPlanV1:
    provisional = (
        ReconciledEodHistoricalFamilyEvidencePublicationPlanV1.model_construct(
            **values,
            logical_fingerprint="0" * 64,
        )
    )
    return ReconciledEodHistoricalFamilyEvidencePublicationPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": (
                current_historical_family_evidence_publication_plan_fingerprint(
                    provisional
                )
            ),
        }
    )


def current_historical_family_evidence_plan_family_set_fingerprint(
    families: tuple[CurrentHistoricalFamilyEvidencePlanItemV1, ...],
) -> str:
    return _fingerprint(
        [
            {
                "family": item.family,
                "target_path": item.target_path,
                "expected_target_state_fingerprint": (
                    item.expected_target_state_fingerprint
                ),
                "evidence_logical_fingerprint": item.evidence.logical_fingerprint,
                "evidence_manifest_sha256": item.evidence_manifest_sha256,
            }
            for item in families
        ]
    )


def current_historical_family_evidence_publication_plan_fingerprint(
    plan: (
        CurrentHistoricalFamilyEvidencePublicationPlanV1
        | ReconciledEodHistoricalFamilyEvidencePublicationPlanV1
    ),
) -> str:
    return _fingerprint(plan.model_dump(mode="json", exclude={"logical_fingerprint"}))


def historical_dataset_coverage_evidence_target_path(
    evidence: HistoricalDatasetCoverageEvidenceV1,
) -> str:
    return (
        PurePosixPath("market-data")
        / "historical-coverage-evidence"
        / "schema_version=1"
        / f"family={evidence.family.value}"
        / f"evidence_id={evidence.logical_fingerprint}"
        / "manifest.json"
    ).as_posix()


def historical_dataset_coverage_evidence_bytes(
    evidence: HistoricalDatasetCoverageEvidenceV1,
) -> bytes:
    return (
        json.dumps(
            evidence.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def historical_dataset_coverage_evidence_fingerprint(
    evidence: HistoricalDatasetCoverageEvidenceV1,
) -> str:
    return _fingerprint(
        evidence.model_dump(mode="json", exclude={"logical_fingerprint"})
    )


def historical_coverage_manifest_fingerprint(
    manifest: HistoricalCoverageManifestV1,
) -> str:
    return _fingerprint(
        manifest.model_dump(mode="json", exclude={"logical_fingerprint"})
    )


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _fingerprint(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=_json_default,
        ).encode("utf-8")
    ).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    raise TypeError(f"unsupported fingerprint value: {type(value).__name__}")
