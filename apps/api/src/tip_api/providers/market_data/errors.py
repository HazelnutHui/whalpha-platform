"""Market-data provider exception hierarchy."""

from __future__ import annotations

from tip_api.providers.market_data.capabilities import ProviderCapability


def _normalize_provider_id(provider_id: str) -> str:
    if not isinstance(provider_id, str):
        raise TypeError("provider_id must be a string")
    normalized = provider_id.strip()
    if not normalized:
        raise ValueError("provider_id must not be empty")
    return normalized


def _normalize_message(message: str) -> str:
    if not isinstance(message, str):
        raise TypeError("message must be a string")
    normalized = message.strip()
    if not normalized:
        raise ValueError("message must not be empty")
    return normalized


class MarketDataProviderError(Exception):
    """Base class for safe market-data provider errors."""

    def __init__(self, provider_id: str, message: str) -> None:
        self.provider_id = _normalize_provider_id(provider_id)
        self.message = _normalize_message(message)
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.provider_id}: {self.message}"


class ProviderUnavailableError(MarketDataProviderError):
    """Raised when a provider cannot currently serve a supported request."""


class ProviderAuthenticationError(MarketDataProviderError):
    """Raised when provider authentication fails without exposing credentials."""


class ProviderRateLimitError(MarketDataProviderError):
    """Raised when a provider rejects a request due to rate limits."""

    def __init__(self, provider_id: str, message: str, retry_after_seconds: int | None = None) -> None:
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be greater than or equal to zero")
        self.retry_after_seconds = retry_after_seconds
        super().__init__(provider_id, message)


class ProviderDataError(MarketDataProviderError):
    """Raised when provider data cannot satisfy canonical contracts."""


class UnsupportedCapabilityError(MarketDataProviderError):
    """Raised when a provider does not support a requested capability."""

    def __init__(self, provider_id: str, capability: ProviderCapability) -> None:
        self.capability = capability
        super().__init__(provider_id, f"unsupported provider capability: {capability.value}")
