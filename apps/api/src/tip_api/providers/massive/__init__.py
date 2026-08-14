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
from tip_api.providers.massive.credential import (
    DEFAULT_MASSIVE_ENV_FILE,
    MASSIVE_ENV_FILE_ENV,
    MassiveCredentialFileError,
    load_massive_provider_config_from_file,
)
from tip_api.providers.massive.mapping import stable_massive_instrument_id
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)

__all__ = [
    "DEFAULT_MASSIVE_BASE_URL",
    "DEFAULT_MASSIVE_ENV_FILE",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "MASSIVE_API_KEY_ENV",
    "MASSIVE_BASE_URL_ENV",
    "MASSIVE_TIMEOUT_ENV",
    "MASSIVE_ENV_FILE_ENV",
    "MassiveCredentialFileError",
    "MassiveHttpTransport",
    "MassiveMarketDataProvider",
    "MassiveProviderConfig",
    "MassiveTransportDataError",
    "MassiveTransportResponseError",
    "MassiveTransportTimeoutError",
    "MassiveTransportUnavailableError",
    "MassiveUrllibTransport",
    "load_massive_provider_config_from_file",
    "stable_massive_instrument_id",
]
