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
        if not self.completion_manifest.path.endswith("/manifest.json"):
            raise ValueError("completion manifest path must end with manifest.json")
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
