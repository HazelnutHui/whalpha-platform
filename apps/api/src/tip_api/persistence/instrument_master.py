"""Provider-neutral Instrument Master snapshot persistence boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Protocol

from tip_api.contracts.market_data.v1 import InstrumentMasterV1, ProviderInstrumentIdentityV1


class InstrumentMasterSnapshotPersistenceError(Exception):
    """Base class for Instrument Master snapshot persistence errors."""


class InstrumentMasterSnapshotConflictError(InstrumentMasterSnapshotPersistenceError):
    """Raised when an existing snapshot conflicts with requested content."""


class InstrumentMasterSnapshotCorruptionError(InstrumentMasterSnapshotPersistenceError):
    """Raised when an existing snapshot or partition is incomplete or inconsistent."""


@dataclass(frozen=True)
class InstrumentMasterSnapshotWriteResult:
    """Audit result for a point-in-time Instrument Master snapshot publish."""

    schema_version: str
    as_of_date: date
    provider_id: str
    instrument_count: int
    identity_count: int
    written_instrument_count: int
    written_identity_count: int
    instrument_partition_path: Path
    identity_partition_path: Path
    snapshot_manifest_path: Path
    instrument_content_sha256: str
    identity_content_sha256: str
    snapshot_content_sha256: str
    status: Literal["published", "already_present"]


class InstrumentMasterSnapshotRepository(Protocol):
    """Repository boundary for point-in-time Instrument Master snapshots."""

    def publish_snapshot(
        self,
        *,
        instruments: tuple[InstrumentMasterV1, ...],
        identities: tuple[ProviderInstrumentIdentityV1, ...],
        as_of_date: date,
        provider_id: str,
        quality_summary: dict[str, object],
    ) -> InstrumentMasterSnapshotWriteResult:
        """Publish one logical snapshot and return non-sensitive audit metadata."""
        ...

