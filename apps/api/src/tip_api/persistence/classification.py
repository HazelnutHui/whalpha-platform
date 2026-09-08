"""Persistence result and error types for Classification V1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tip_api.contracts.market_data.v1 import (
    ClassificationCoverageDecisionV1,
    ClassificationDefinitionV1,
    ClassificationMembershipV1,
    ClassificationSnapshotManifestV1,
    ClassificationSourceObservationV1,
)


class ClassificationPersistenceError(RuntimeError):
    """Base error for classification snapshot persistence."""


class ClassificationConflictError(ClassificationPersistenceError):
    """Raised when immutable classification identity conflicts."""


class ClassificationCorruptionError(ClassificationPersistenceError):
    """Raised when a completed classification snapshot fails formal reread."""


@dataclass(frozen=True, slots=True)
class ClassificationSnapshotWriteResult:
    partition_path: Path
    manifest_path: Path
    logical_fingerprint: str
    definition_count: int
    observation_count: int
    coverage_count: int
    membership_count: int
    status: Literal["published", "already_present", "reread"]


@dataclass(frozen=True, slots=True)
class CompletedClassificationSnapshot:
    manifest: ClassificationSnapshotManifestV1
    definitions: tuple[ClassificationDefinitionV1, ...]
    observations: tuple[ClassificationSourceObservationV1, ...]
    coverage: tuple[ClassificationCoverageDecisionV1, ...]
    memberships: tuple[ClassificationMembershipV1, ...]
