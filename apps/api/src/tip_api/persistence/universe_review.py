"""Persistence types for reviewed Universe pre-activation shadow publication."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tip_api.contracts.security_classification.v1.universe_review import UniversePreActivationManifestV1


class UniverseReviewPersistenceError(Exception): pass
class UniverseReviewConflictError(UniverseReviewPersistenceError): pass
class UniverseReviewCorruptionError(UniverseReviewPersistenceError): pass


@dataclass(frozen=True, slots=True)
class UniverseReviewPublicationResult:
    override_path: Path
    review_path: Path
    logical_manifest_path: Path
    override_record_count: int
    review_record_count: int
    override_content_fingerprint: str
    review_content_fingerprint: str
    override_parquet_sha256: str
    review_parquet_sha256: str
    logical_content_fingerprint: str


@dataclass(frozen=True, slots=True)
class CompletedUniverseReviewPublication:
    manifest: UniversePreActivationManifestV1
    override_record_count: int
    review_record_count: int
