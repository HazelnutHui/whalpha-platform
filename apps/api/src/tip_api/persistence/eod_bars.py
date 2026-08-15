"""Provider-neutral EOD Price Bar persistence boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Protocol

from tip_api.contracts.market_data.v1 import EodPriceBarV1


class EodPriceBarPersistenceError(Exception):
    """Base class for EOD Price Bar persistence errors."""


class EodPriceBarConflictError(EodPriceBarPersistenceError):
    """Raised when a completed partition conflicts with requested content."""


class EodPriceBarCorruptionError(EodPriceBarPersistenceError):
    """Raised when an existing partition is incomplete or inconsistent."""


@dataclass(frozen=True)
class EodPriceBarWriteResult:
    """Audit result returned by an EOD Price Bar repository publish."""

    schema_version: str
    session_date: date
    provider_id: str
    record_count: int
    written_record_count: int
    partition_path: Path
    content_sha256: str
    status: Literal["published", "already_present"]


class EodPriceBarRepository(Protocol):
    """Repository boundary for canonical EOD Price Bar session partitions."""

    def publish_session(
        self,
        records: tuple[EodPriceBarV1, ...],
        *,
        session_date: date,
        provider_id: str,
        quality_summary: dict[str, Any] | None = None,
        identity_snapshot: dict[str, Any] | None = None,
    ) -> EodPriceBarWriteResult:
        """Publish one validated session and return non-sensitive audit metadata."""
        ...
