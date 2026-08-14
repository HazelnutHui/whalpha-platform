"""Massive provider configuration and credential boundary."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

MASSIVE_API_KEY_ENV = "TIP_MASSIVE_API_KEY"
MASSIVE_BASE_URL_ENV = "TIP_MASSIVE_BASE_URL"
MASSIVE_TIMEOUT_ENV = "TIP_MASSIVE_REQUEST_TIMEOUT_SECONDS"
DEFAULT_MASSIVE_BASE_URL = "https://api.massive.com"
DEFAULT_REQUEST_TIMEOUT_SECONDS = Decimal("15")


class MassiveProviderConfig(BaseModel):
    """Configuration for Massive adapter construction.

    API keys are intentionally represented as SecretStr and are loaded only
    through an explicit environment boundary.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    api_key: SecretStr
    base_url: str = DEFAULT_MASSIVE_BASE_URL
    request_timeout_seconds: Decimal = DEFAULT_REQUEST_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> MassiveProviderConfig:
        source = MappingProxyType(dict(os.environ if environ is None else environ))
        values: dict[str, object] = {
            "api_key": source.get(MASSIVE_API_KEY_ENV, ""),
            "base_url": source.get(MASSIVE_BASE_URL_ENV, DEFAULT_MASSIVE_BASE_URL),
            "request_timeout_seconds": source.get(
                MASSIVE_TIMEOUT_ENV,
                str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
            ),
        }
        return cls(**values)

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            secret = value.get_secret_value().strip()
        elif isinstance(value, str):
            secret = value.strip()
        else:
            raise ValueError("Massive API key is required")
        if not secret:
            raise ValueError("Massive API key is required")
        return SecretStr(secret)

    @field_validator("base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Massive base URL must be a string")
        normalized = value.strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Massive base URL must be an absolute HTTP URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Massive base URL must not contain credentials, query, or fragment")
        return normalized

    @field_validator("request_timeout_seconds", mode="before")
    @classmethod
    def normalize_timeout(cls, value: object) -> Decimal:
        try:
            timeout = value if isinstance(value, Decimal) else Decimal(str(value).strip())
        except (AttributeError, InvalidOperation) as exc:
            raise ValueError("Massive request timeout must be a positive finite number") from exc
        if not timeout.is_finite() or timeout <= 0:
            raise ValueError("Massive request timeout must be a positive finite number")
        return timeout
