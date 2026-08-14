"""Synchronous market-data provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tip_api.contracts.market_data.v1 import EodPriceBarV1, InstrumentMasterV1
from tip_api.providers.market_data.capabilities import ProviderCapability
from tip_api.providers.market_data.queries import EodBarQuery, InstrumentQuery


@runtime_checkable
class MarketDataProvider(Protocol):
    """Provider-neutral synchronous market-data boundary.

    Implementations return canonical immutable contract tuples, not provider
    payloads, dictionaries, DataFrames, generators, or raw JSON.

    Required ordering:
    - get_instruments: instrument_id string ascending
    - get_eod_bars: instrument_id string, session_date, source, revision ascending
    """

    @property
    def provider_id(self) -> str:
        """Stable non-secret internal provider name."""
        ...

    @property
    def capabilities(self) -> frozenset[ProviderCapability]:
        """Immutable set of supported provider capabilities."""
        ...

    def get_instruments(self, query: InstrumentQuery) -> tuple[InstrumentMasterV1, ...]:
        """Return Instrument Master records satisfying the query."""
        ...

    def get_eod_bars(self, query: EodBarQuery) -> tuple[EodPriceBarV1, ...]:
        """Return EOD Price Bar records satisfying the query."""
        ...
