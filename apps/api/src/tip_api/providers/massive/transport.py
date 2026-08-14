"""HTTP transport boundary for Massive provider adapters."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Protocol, TypeAlias

from pydantic import SecretStr

MassiveParamValue: TypeAlias = str | int | bool
MassiveParams: TypeAlias = Mapping[str, MassiveParamValue]
MassiveJson: TypeAlias = Mapping[str, object]


class MassiveHttpTransport(Protocol):
    """Synchronous JSON transport used by Massive adapters.

    No production network transport is implemented yet. Adapter tests inject a
    deterministic fake transport. The API key travels through this credential
    boundary and must not be mixed into ordinary query params.
    """

    def get_json(
        self,
        path: str,
        *,
        params: MassiveParams,
        api_key: SecretStr,
        timeout_seconds: Decimal,
    ) -> MassiveJson:
        """Return a Massive JSON object for a relative API path."""
        ...


class MassiveTransportError(Exception):
    """Base transport error that carries only safe metadata."""


class MassiveTransportTimeoutError(MassiveTransportError):
    """Raised when the transport times out."""


class MassiveTransportUnavailableError(MassiveTransportError):
    """Raised when the transport cannot reach the provider."""


class MassiveTransportResponseError(MassiveTransportError):
    """Raised for provider HTTP error responses without storing raw bodies."""

    def __init__(self, status_code: int, message: str, retry_after_seconds: int | None = None) -> None:
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be greater than or equal to zero")
        self.status_code = status_code
        self.message = message.strip() or "Massive HTTP error"
        self.retry_after_seconds = retry_after_seconds
        super().__init__(self.message)
