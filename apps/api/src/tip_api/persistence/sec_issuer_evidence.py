"""Persistence protocol for canonical SEC issuer-structure evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from tip_api.contracts.security_classification.v1 import SecIssuerEvidenceObservationV1, SecIssuerStructureEvidenceV1


class SecIssuerEvidencePersistenceError(Exception):
    pass


class SecIssuerEvidenceConflictError(SecIssuerEvidencePersistenceError):
    pass


class SecIssuerEvidenceCorruptionError(SecIssuerEvidencePersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class SecIssuerEvidenceWriteResult:
    partition_path: Path
    record_count: int
    content_sha256: str
    parquet_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class SecIssuerEvidenceSnapshotWriteResult:
    manifest_path: Path
    logical_content_sha256: str
    status: Literal["published", "already_present"]


class SecIssuerEvidenceRepository(Protocol):
    def publish_observations(
        self,
        records: tuple[SecIssuerEvidenceObservationV1, ...],
        *,
        as_of_date: object,
        source_cache_manifest_sha256: str,
    ) -> SecIssuerEvidenceWriteResult: ...

    def publish(
        self,
        records: tuple[SecIssuerStructureEvidenceV1, ...],
        *,
        source_datasets: tuple[str, ...],
    ) -> SecIssuerEvidenceWriteResult: ...
