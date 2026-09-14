"""Provider-neutral read boundary for canonical EOD market data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from tip_api.contracts.market_data.v1 import EodSessionIntegrityV1
from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor


class EodReadError(Exception):
    """Base class for canonical EOD read failures."""


class EodSessionNotFoundError(EodReadError):
    """Raised when a requested completed EOD session is unavailable."""


class EodDatasetUnavailableError(EodReadError):
    """Raised when completed EOD data is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class EodHistorySessionRead:
    """Validated immutable historical session read."""

    integrity: EodSessionIntegrityV1
    bars: tuple[EodMarketBarReadModel, ...]
    available_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EodInstrumentPresenceSessionRead:
    """Validated session integrity plus a bounded stable-ID presence projection."""

    integrity: EodSessionIntegrityV1
    instrument_ids: frozenset[UUID]
    available_at: datetime | None = None


class EodReadRepository(Protocol):
    def list_sessions(self) -> tuple[EodSessionDescriptor, ...]:
        """Return validated completed sessions."""
        ...

    def read_bars(self, session_date: date) -> tuple[EodMarketBarReadModel, ...]:
        """Return joined canonical bars for one completed session."""
        ...

    def inspect_session(self, session_date: date) -> EodSessionIntegrityV1:
        """Validate one completed session and return non-provider integrity metadata."""
        ...

    def read_history_sessions(self, session_dates: tuple[date, ...]) -> tuple[EodHistorySessionRead, ...]:
        """Read only the requested sessions, joined by persisted stable instrument IDs."""
        ...

    def read_instrument_presence_sessions(
        self,
        session_dates: tuple[date, ...],
        instrument_ids: frozenset[UUID],
    ) -> tuple[EodInstrumentPresenceSessionRead, ...]:
        """Validate sessions and return presence only for requested stable IDs."""
        ...
