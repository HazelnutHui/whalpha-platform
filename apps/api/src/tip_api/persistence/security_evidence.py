"""Persistence boundary for provider security-type evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Protocol

from tip_api.contracts.security_classification.v1 import (
    ProviderInstrumentSecurityEvidenceV1,
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


class SecurityEvidenceRepository(Protocol):
    def publish_catalog(
        self,
        records: tuple[ProviderSecurityTypeCatalogV1, ...],
        *,
        observed_date: date,
        provider_id: str,
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
