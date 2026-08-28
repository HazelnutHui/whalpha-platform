"""Immutable caller-root storage for source permission reviews and assessments."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.data_governance.v1 import (
    SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
    SourcePermissionReviewV1,
    SourceUseAssessmentV1,
    source_permission_review_fingerprint,
)


_SOURCE_ID = re.compile(r"[a-z][a-z0-9_]{1,63}")


class SourcePermissionRepositoryError(ValueError):
    """Raised for unsafe roots, conflicts, incomplete data, or corruption."""


class SourcePermissionReviewManifestV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    dataset_type: Literal["source_permission_review"] = "source_permission_review"
    source_id: str
    review_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessments_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_count: int = Field(gt=0)
    data_family_ids: tuple[str, ...]
    created_at: datetime
    logical_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("data_family_ids")
    @classmethod
    def families_are_canonical(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or value != tuple(sorted(set(value))):
            raise ValueError("manifest data families must be sorted and unique")
        return value


@dataclass(frozen=True, slots=True)
class SourcePermissionReviewPublicationV1:
    status: Literal["published", "already_present"]
    partition_path: Path
    manifest_path: Path
    manifest: SourcePermissionReviewManifestV1


@dataclass(frozen=True, slots=True)
class CompletedSourcePermissionReviewV1:
    partition_path: Path
    manifest_path: Path
    manifest: SourcePermissionReviewManifestV1
    review: SourcePermissionReviewV1
    assessments: tuple[SourceUseAssessmentV1, ...]


class SourcePermissionReviewRepository:
    """Publish immutable evidence below one explicit, caller-owned root."""

    def __init__(self, root: Path) -> None:
        self._root = _safe_root(root)

    def publish(
        self,
        *,
        review: SourcePermissionReviewV1,
        assessments: tuple[SourceUseAssessmentV1, ...],
        created_at: datetime,
    ) -> SourcePermissionReviewPublicationV1:
        checked_review = SourcePermissionReviewV1.model_validate(
            review.model_dump(mode="json")
        )
        checked_created_at = normalize_utc_datetime(created_at)
        checked_assessments = _validate_assessments(checked_review, assessments)
        review_fingerprint = source_permission_review_fingerprint(checked_review)
        target = _partition_path(
            self._root,
            checked_review.source_id,
            review_fingerprint,
        )
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_path(parent)

        review_bytes = _canonical_json_bytes(checked_review.model_dump(mode="json"))
        assessment_payload = [
            item.model_dump(mode="json") for item in checked_assessments
        ]
        assessments_bytes = _canonical_json_bytes(assessment_payload)
        logical_payload = {
            "policy_fingerprint": SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
            "review_fingerprint": review_fingerprint,
            "review_sha256": _sha256(review_bytes),
            "assessments_sha256": _sha256(assessments_bytes),
            "data_family_ids": [
                item.data_family_id for item in checked_assessments
            ],
        }
        manifest = SourcePermissionReviewManifestV1(
            source_id=checked_review.source_id,
            review_fingerprint=review_fingerprint,
            policy_fingerprint=SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
            review_sha256=logical_payload["review_sha256"],
            assessments_sha256=logical_payload["assessments_sha256"],
            assessment_count=len(checked_assessments),
            data_family_ids=tuple(logical_payload["data_family_ids"]),
            created_at=checked_created_at,
            logical_content_fingerprint=_fingerprint(logical_payload),
        )

        if target.exists() or target.is_symlink():
            completed = read_completed_source_permission_review(
                self._root,
                source_id=checked_review.source_id,
                review_fingerprint=review_fingerprint,
            )
            if (
                completed.review != checked_review
                or completed.assessments != checked_assessments
                or completed.manifest.logical_content_fingerprint
                != manifest.logical_content_fingerprint
            ):
                raise SourcePermissionRepositoryError(
                    "existing source permission review conflicts with requested content"
                )
            return SourcePermissionReviewPublicationV1(
                status="already_present",
                partition_path=target,
                manifest_path=target / "manifest.json",
                manifest=completed.manifest,
            )

        stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=parent))
        try:
            _write_fsynced(stage / "review.json", review_bytes)
            _write_fsynced(stage / "assessments.json", assessments_bytes)
            manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
            _write_fsynced(stage / "manifest.json", manifest_bytes)
            _fsync_directory(stage)
            os.replace(stage, target)
            _fsync_directory(parent)
            completed = read_completed_source_permission_review(
                self._root,
                source_id=checked_review.source_id,
                review_fingerprint=review_fingerprint,
            )
        except Exception:
            if stage.exists() and stage.parent == parent and stage.name.startswith(
                ".staging-"
            ):
                shutil.rmtree(stage)
            if target.exists() and not (target / "manifest.json").is_file():
                raise SourcePermissionRepositoryError(
                    "source permission publication left an incomplete target"
                )
            raise
        return SourcePermissionReviewPublicationV1(
            status="published",
            partition_path=target,
            manifest_path=target / "manifest.json",
            manifest=completed.manifest,
        )


def read_completed_source_permission_review(
    root: Path,
    *,
    source_id: str,
    review_fingerprint: str,
) -> CompletedSourcePermissionReviewV1:
    checked_root = _safe_root(root)
    if not review_fingerprint or len(review_fingerprint) != 64 or any(
        item not in "0123456789abcdef" for item in review_fingerprint
    ):
        raise SourcePermissionRepositoryError("review fingerprint is malformed")
    target = _partition_path(checked_root, source_id, review_fingerprint)
    _reject_symlink_path(target)
    if not target.is_dir():
        raise SourcePermissionRepositoryError("source permission review is not complete")

    review_bytes = _required_file_bytes(target / "review.json")
    assessments_bytes = _required_file_bytes(target / "assessments.json")
    manifest_bytes = _required_file_bytes(target / "manifest.json")
    try:
        review = SourcePermissionReviewV1.model_validate(json.loads(review_bytes))
        assessment_payload = json.loads(assessments_bytes)
        if not isinstance(assessment_payload, list):
            raise TypeError("assessment payload must be a list")
        assessments = tuple(
            SourceUseAssessmentV1.model_validate(item) for item in assessment_payload
        )
        manifest = SourcePermissionReviewManifestV1.model_validate(
            json.loads(manifest_bytes)
        )
    except Exception as exc:
        raise SourcePermissionRepositoryError(
            "source permission review payload is malformed"
        ) from exc

    checked_assessments = _validate_assessments(review, assessments)
    expected_review_fingerprint = source_permission_review_fingerprint(review)
    logical_payload = {
        "policy_fingerprint": SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
        "review_fingerprint": expected_review_fingerprint,
        "review_sha256": _sha256(review_bytes),
        "assessments_sha256": _sha256(assessments_bytes),
        "data_family_ids": [item.data_family_id for item in checked_assessments],
    }
    if (
        manifest.source_id != source_id
        or review.source_id != source_id
        or manifest.review_fingerprint != review_fingerprint
        or expected_review_fingerprint != review_fingerprint
        or manifest.policy_fingerprint != SOURCE_PERMISSION_POLICY_FINGERPRINT_V1
        or manifest.review_sha256 != logical_payload["review_sha256"]
        or manifest.assessments_sha256 != logical_payload["assessments_sha256"]
        or manifest.assessment_count != len(checked_assessments)
        or manifest.data_family_ids
        != tuple(item.data_family_id for item in checked_assessments)
        or manifest.logical_content_fingerprint != _fingerprint(logical_payload)
    ):
        raise SourcePermissionRepositoryError(
            "source permission review fingerprints do not reconcile"
        )
    return CompletedSourcePermissionReviewV1(
        partition_path=target,
        manifest_path=target / "manifest.json",
        manifest=manifest,
        review=review,
        assessments=checked_assessments,
    )


def _validate_assessments(
    review: SourcePermissionReviewV1,
    assessments: tuple[SourceUseAssessmentV1, ...],
) -> tuple[SourceUseAssessmentV1, ...]:
    if not assessments:
        raise SourcePermissionRepositoryError("at least one assessment is required")
    try:
        assessments = tuple(
            SourceUseAssessmentV1.model_validate(item.model_dump(mode="json"))
            for item in assessments
        )
    except Exception as exc:
        raise SourcePermissionRepositoryError(
            "source permission assessment is malformed"
        ) from exc
    review_fingerprint = source_permission_review_fingerprint(review)
    family_ids = tuple(item.data_family_id for item in assessments)
    if family_ids != tuple(sorted(set(family_ids))):
        raise SourcePermissionRepositoryError(
            "source permission assessments must be ordered and family-unique"
        )
    if any(
        item.source_id != review.source_id
        or item.permission_review_fingerprint != review_fingerprint
        or item.permission_review_valid_until != review.valid_until
        for item in assessments
    ):
        raise SourcePermissionRepositoryError(
            "source permission assessments do not bind the review"
        )
    return assessments


def _partition_path(root: Path, source_id: str, review_fingerprint: str) -> Path:
    if not _SOURCE_ID.fullmatch(source_id):
        raise SourcePermissionRepositoryError("source ID is unsafe")
    return (
        root
        / "governance"
        / "source-permission-reviews"
        / "schema_version=1"
        / f"source={source_id}"
        / f"review={review_fingerprint}"
    )


def _safe_root(root: Path) -> Path:
    candidate = Path(root).absolute()
    if candidate == Path(candidate.anchor):
        raise SourcePermissionRepositoryError("filesystem root cannot be a repository root")
    _reject_symlink_path(candidate)
    return candidate


def _reject_symlink_path(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise SourcePermissionRepositoryError("symlink paths are not permitted")
        if current.parent == current:
            break
        current = current.parent


def _required_file_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise SourcePermissionRepositoryError("source permission review is incomplete")
    return path.read_bytes()


def _write_fsynced(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fingerprint(value: Any) -> str:
    return _sha256(_canonical_json_bytes(value))
