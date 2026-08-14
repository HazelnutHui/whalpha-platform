"""Massive Stocks adapter skeleton and configuration boundary."""

from tip_api.providers.massive.adapter import MassiveMarketDataProvider
from tip_api.providers.massive.config import (
    DEFAULT_MASSIVE_BASE_URL,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    MASSIVE_API_KEY_ENV,
    MASSIVE_BASE_URL_ENV,
    MASSIVE_TIMEOUT_ENV,
    MassiveProviderConfig,
)
from tip_api.providers.massive.mapping import stable_massive_instrument_id
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)

__all__ = [
    "DEFAULT_MASSIVE_BASE_URL",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "MASSIVE_API_KEY_ENV",
    "MASSIVE_BASE_URL_ENV",
    "MASSIVE_TIMEOUT_ENV",
    "MassiveHttpTransport",
    "MassiveMarketDataProvider",
    "MassiveProviderConfig",
    "MassiveTransportResponseError",
    "MassiveTransportTimeoutError",
    "MassiveTransportUnavailableError",
    "stable_massive_instrument_id",
]
