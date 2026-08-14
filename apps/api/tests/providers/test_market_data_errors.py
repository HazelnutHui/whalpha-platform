from __future__ import annotations

import pytest

from tip_api.providers.market_data import (
    MarketDataProviderError,
    ProviderAuthenticationError,
    ProviderCapability,
    ProviderDataError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)


def test_base_error_string_contains_provider_id_and_safe_message() -> None:
    error = MarketDataProviderError(" test_provider ", " request failed ")

    assert error.provider_id == "test_provider"
    assert error.message == "request failed"
    assert str(error) == "test_provider: request failed"


@pytest.mark.parametrize("provider_id", ["", "   "])
def test_empty_provider_id_is_rejected(provider_id: str) -> None:
    with pytest.raises(ValueError):
        MarketDataProviderError(provider_id, "safe message")


def test_rate_limit_retry_after_none_and_zero_are_accepted() -> None:
    no_hint = ProviderRateLimitError("test_provider", "rate limited")
    zero_hint = ProviderRateLimitError("test_provider", "rate limited", retry_after_seconds=0)

    assert no_hint.retry_after_seconds is None
    assert zero_hint.retry_after_seconds == 0


def test_negative_retry_after_is_rejected() -> None:
    with pytest.raises(ValueError):
        ProviderRateLimitError("test_provider", "rate limited", retry_after_seconds=-1)


def test_unsupported_capability_retains_capability() -> None:
    error = UnsupportedCapabilityError("test_provider", ProviderCapability.EOD_PRICE_BARS)

    assert error.capability is ProviderCapability.EOD_PRICE_BARS
    assert "eod_price_bars" in str(error)


def test_errors_do_not_store_arbitrary_credential_fields() -> None:
    error = ProviderAuthenticationError("test_provider", "authentication failed")

    assert not hasattr(error, "credential")
    assert not hasattr(error, "headers")
    assert not hasattr(error, "raw_response")


def test_subclass_relationships() -> None:
    assert issubclass(ProviderUnavailableError, MarketDataProviderError)
    assert issubclass(ProviderAuthenticationError, MarketDataProviderError)
    assert issubclass(ProviderRateLimitError, MarketDataProviderError)
    assert issubclass(ProviderDataError, MarketDataProviderError)
    assert issubclass(UnsupportedCapabilityError, MarketDataProviderError)
