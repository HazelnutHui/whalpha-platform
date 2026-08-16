"""SEC provider configuration with redacted contact identity."""

from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Mapping

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

SEC_USER_AGENT_ENV = "TIP_SEC_USER_AGENT"
DEFAULT_SEC_TIMEOUT_SECONDS = Decimal("15")
DEFAULT_SEC_MAX_REQUESTS_PER_SECOND = Decimal("2")


class SecProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    user_agent: SecretStr
    request_timeout_seconds: Decimal = DEFAULT_SEC_TIMEOUT_SECONDS
    max_requests_per_second: Decimal = DEFAULT_SEC_MAX_REQUESTS_PER_SECOND
    max_retries: int = 2

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> SecProviderConfig:
        source = MappingProxyType(dict(os.environ if environ is None else environ))
        return cls(user_agent=source.get(SEC_USER_AGENT_ENV, ""))

    @field_validator("user_agent", mode="before")
    @classmethod
    def validate_user_agent(cls, value: object) -> SecretStr:
        text = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not isinstance(text, str):
            raise ValueError("SEC User-Agent is not configured")
        normalized = text.strip()
        if not (10 <= len(normalized) <= 256):
            raise ValueError("SEC User-Agent is not configured correctly")
        if "trading-intelligence-platform" not in normalized.lower() or not re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized
        ):
            raise ValueError("SEC User-Agent is not configured correctly")
        if any(ord(char) < 32 or ord(char) > 126 for char in normalized):
            raise ValueError("SEC User-Agent is not configured correctly")
        return SecretStr(normalized)

    @field_validator("request_timeout_seconds", "max_requests_per_second", mode="before")
    @classmethod
    def validate_decimal(cls, value: object, info: object) -> Decimal:
        try:
            parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
        except (InvalidOperation, AttributeError) as exc:
            raise ValueError("SEC numeric configuration is invalid") from exc
        if not parsed.is_finite() or parsed <= 0:
            raise ValueError("SEC numeric configuration must be positive and finite")
        if getattr(info, "field_name", "") == "max_requests_per_second" and parsed > 2:
            raise ValueError("SEC rate limit must not exceed two requests per second")
        return parsed

    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, value: int) -> int:
        if value < 0 or value > 3:
            raise ValueError("SEC retries must be bounded")
        return value
