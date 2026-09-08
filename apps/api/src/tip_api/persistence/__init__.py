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
from tip_api.persistence.classification import (
    ClassificationConflictError,
    ClassificationCorruptionError,
    ClassificationPersistenceError,
    ClassificationSnapshotWriteResult,
    CompletedClassificationSnapshot,
)

__all__ = [
    "ClassificationConflictError",
    "ClassificationCorruptionError",
    "ClassificationPersistenceError",
    "ClassificationSnapshotWriteResult",
    "CompletedClassificationSnapshot",
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
