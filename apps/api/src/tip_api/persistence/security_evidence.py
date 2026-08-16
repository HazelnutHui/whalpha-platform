"""Persistence boundary for provider security-type evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Protocol

from tip_api.contracts.security_classification.v1 import (
    ProviderInstrumentSecurityEvidenceV1,
    ProviderSecurityEvidenceSnapshotManifestV1,
    ProviderSecurityObservationV1,
    ProviderSecurityTypeCatalogV1,
)


class SecurityEvidencePersistenceError(Exception):
    pass


class SecurityEvidenceConflictError(SecurityEvidencePersistenceError):
    pass


class SecurityEvidenceCorruptionError(SecurityEvidencePersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class SecurityEvidenceWriteResult:
    dataset_name: str
    partition_path: Path
    record_count: int
    content_sha256: str
    parquet_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class FailedDiagnosticWriteResult:
    diagnostic_path: Path
    run_id: str
    status: Literal["written"]


@dataclass(frozen=True, slots=True)
class SecurityEvidenceSnapshotWriteResult:
    manifest_path: Path
    logical_content_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class CompletedSecurityEvidenceSnapshot:
    manifest: ProviderSecurityEvidenceSnapshotManifestV1
    catalog: tuple[ProviderSecurityTypeCatalogV1, ...]
    observations: tuple[ProviderSecurityObservationV1, ...]
    evidence: tuple[ProviderInstrumentSecurityEvidenceV1, ...]


class SecurityEvidenceRepository(Protocol):
    def publish_catalog(
        self,
        records: tuple[ProviderSecurityTypeCatalogV1, ...],
        *,
        observed_date: date,
        provider_id: str,
    ) -> SecurityEvidenceWriteResult: ...

    def publish_observations(
        self,
        records: tuple[ProviderSecurityObservationV1, ...],
        *,
        as_of_date: date,
        provider_id: str,
        catalog_content_sha256: str,
        quality_summary: dict[str, object],
    ) -> SecurityEvidenceWriteResult: ...

    def publish_instrument_evidence(
        self,
        records: tuple[ProviderInstrumentSecurityEvidenceV1, ...],
        *,
        as_of_date: date,
        provider_id: str,
        catalog_content_sha256: str,
        quality_summary: dict[str, object],
    ) -> SecurityEvidenceWriteResult: ...

    def publish_logical_snapshot(
        self,
        *,
        as_of_date: date,
        observed_date: date,
        provider_id: str,
        created_at: datetime,
        request_count: int,
        catalog: SecurityEvidenceWriteResult,
        observations: SecurityEvidenceWriteResult,
        evidence: SecurityEvidenceWriteResult,
    ) -> SecurityEvidenceSnapshotWriteResult: ...
