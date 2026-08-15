"""Provider-neutral read boundary for canonical EOD market data."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from tip_api.read_models.eod import EodMarketBarReadModel, EodSessionDescriptor


class EodReadError(Exception):
    """Base class for canonical EOD read failures."""


class EodSessionNotFoundError(EodReadError):
    """Raised when a requested completed EOD session is unavailable."""


class EodDatasetUnavailableError(EodReadError):
    """Raised when completed EOD data is incomplete or inconsistent."""


class EodReadRepository(Protocol):
    def list_sessions(self) -> tuple[EodSessionDescriptor, ...]:
        """Return validated completed sessions."""
        ...

    def read_bars(self, session_date: date) -> tuple[EodMarketBarReadModel, ...]:
        """Return joined canonical bars for one completed session."""
        ...
