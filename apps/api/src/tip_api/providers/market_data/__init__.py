"""Public market-data provider boundary."""

from tip_api.providers.market_data.capabilities import ProviderCapability
from tip_api.providers.market_data.errors import (
    MarketDataProviderError,
    ProviderAuthenticationError,
    ProviderDataError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)
from tip_api.providers.market_data.protocol import MarketDataProvider
from tip_api.providers.market_data.queries import EodBarQuery, InstrumentQuery, RevisionSelection

__all__ = [
    "EodBarQuery",
    "InstrumentQuery",
    "MarketDataProvider",
    "MarketDataProviderError",
    "ProviderAuthenticationError",
    "ProviderCapability",
    "ProviderDataError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "RevisionSelection",
    "UnsupportedCapabilityError",
]
