"""Persistence result and error types for historical research foundations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tip_api.contracts.market_data.v1 import HistoricalDatasetFamily


class HistoricalResearchPersistenceError(RuntimeError):
    """Base error for historical research persistence operations."""


class HistoricalResearchConflictError(HistoricalResearchPersistenceError):
    """Raised when an immutable partition already contains different data."""


class HistoricalResearchCorruptionError(HistoricalResearchPersistenceError):
    """Raised when a completed partition cannot be formally reread."""


@dataclass(frozen=True)
class HistoricalResearchPartitionWriteResult:
    family: HistoricalDatasetFamily
    partition_path: Path
    parquet_path: Path
    manifest_path: Path
    record_count: int
    written_record_count: int
    logical_fingerprint: str
    physical_sha256: str
    status: str
