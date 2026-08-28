"""Persistence boundaries for canonical market-data contracts."""

from tip_api.persistence.eod_bars import (
    EodPriceBarConflictError,
    EodPriceBarCorruptionError,
    EodPriceBarPersistenceError,
    EodPriceBarRepository,
    EodPriceBarWriteResult,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchConflictError,
    HistoricalResearchCorruptionError,
    HistoricalResearchPartitionWriteResult,
    HistoricalResearchPersistenceError,
)
from tip_api.persistence.instrument_master import (
    InstrumentMasterSnapshotConflictError,
    InstrumentMasterSnapshotCorruptionError,
    InstrumentMasterSnapshotPersistenceError,
    InstrumentMasterSnapshotRepository,
    InstrumentMasterSnapshotWriteResult,
)

__all__ = [
    "EodPriceBarConflictError",
    "EodPriceBarCorruptionError",
    "EodPriceBarPersistenceError",
    "EodPriceBarRepository",
    "EodPriceBarWriteResult",
    "HistoricalResearchConflictError",
    "HistoricalResearchCorruptionError",
    "HistoricalResearchPartitionWriteResult",
    "HistoricalResearchPersistenceError",
    "InstrumentMasterSnapshotConflictError",
    "InstrumentMasterSnapshotCorruptionError",
    "InstrumentMasterSnapshotPersistenceError",
    "InstrumentMasterSnapshotRepository",
    "InstrumentMasterSnapshotWriteResult",
]
