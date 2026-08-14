from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from tip_api.providers.massive import DEFAULT_MASSIVE_BASE_URL, MassiveProviderConfig

SENTINEL_SECRET = "test-secret-must-never-appear"


def test_config_loads_from_environment() -> None:
    config = MassiveProviderConfig.from_environment(
        {
            "TIP_MASSIVE_API_KEY": f"  {SENTINEL_SECRET}  ",
            "TIP_MASSIVE_BASE_URL": "https://api.massive.com/",
            "TIP_MASSIVE_REQUEST_TIMEOUT_SECONDS": "7.5",
        }
    )

    assert config.api_key.get_secret_value() == SENTINEL_SECRET
    assert config.base_url == DEFAULT_MASSIVE_BASE_URL
    assert config.request_timeout_seconds == Decimal("7.5")


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Massive API key is required"):
        MassiveProviderConfig.from_environment({})


def test_blank_api_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Massive API key is required"):
        MassiveProviderConfig.from_environment({"TIP_MASSIVE_API_KEY": "   "})


def test_secret_repr_is_redacted() -> None:
    config = MassiveProviderConfig(api_key=SENTINEL_SECRET)

    assert SENTINEL_SECRET not in repr(config)
    assert "**********" in repr(config)


def test_secret_is_not_exposed_in_validation_errors() -> None:
    with pytest.raises(ValidationError) as exc_info:
        MassiveProviderConfig(api_key=SENTINEL_SECRET, base_url="not-a-url")

    assert SENTINEL_SECRET not in str(exc_info.value)


def test_default_base_url_and_timeout() -> None:
    config = MassiveProviderConfig(api_key=SENTINEL_SECRET)

    assert config.base_url == DEFAULT_MASSIVE_BASE_URL
    assert config.request_timeout_seconds == Decimal("15")


@pytest.mark.parametrize("base_url", ["not-a-url", "ftp://api.massive.com", "https://user:pass@example.test", "https://api.massive.com?x=1"])
def test_invalid_base_url_is_rejected(base_url: str) -> None:
    with pytest.raises(ValidationError):
        MassiveProviderConfig(api_key=SENTINEL_SECRET, base_url=base_url)


@pytest.mark.parametrize("timeout", ["0", "-1", "NaN", "Infinity"])
def test_timeout_must_be_positive_finite(timeout: str) -> None:
    with pytest.raises(ValidationError, match="positive finite"):
        MassiveProviderConfig(api_key=SENTINEL_SECRET, request_timeout_seconds=timeout)


def test_config_is_frozen_and_forbids_extra_fields() -> None:
    config = MassiveProviderConfig(api_key=SENTINEL_SECRET)
    with pytest.raises(ValidationError):
        MassiveProviderConfig(api_key=SENTINEL_SECRET, extra_field="x")
    with pytest.raises(ValidationError):
        config.base_url = "https://example.test"  # type: ignore[misc]
