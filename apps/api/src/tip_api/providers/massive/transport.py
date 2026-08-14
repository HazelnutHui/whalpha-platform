"""HTTP transport boundary for Massive provider adapters."""

from __future__ import annotations

import json
import socket
from decimal import Decimal
from typing import Callable, Mapping, Protocol, TypeAlias
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import SecretStr

MassiveParamValue: TypeAlias = str | int | bool
MassiveParams: TypeAlias = Mapping[str, MassiveParamValue]
MassiveJson: TypeAlias = Mapping[str, object]
UrlOpen = Callable[[Request, float], object]


class MassiveHttpTransport(Protocol):
    """Synchronous JSON transport used by Massive adapters.

    The API key travels through this credential boundary and must not be mixed
    into ordinary query params.
    """

    def get_json(
        self,
        path: str,
        *,
        params: MassiveParams,
        api_key: SecretStr,
        timeout_seconds: Decimal,
        base_url: str,
    ) -> MassiveJson:
        """Return a Massive JSON object for a relative API path."""
        ...


class MassiveTransportError(Exception):
    """Base transport error that carries only safe metadata."""


class MassiveTransportTimeoutError(MassiveTransportError):
    """Raised when the transport times out."""


class MassiveTransportUnavailableError(MassiveTransportError):
    """Raised when the transport cannot reach the provider."""


class MassiveTransportDataError(MassiveTransportError):
    """Raised when a transport response cannot be parsed as canonical JSON."""


class MassiveTransportResponseError(MassiveTransportError):
    """Raised for provider HTTP error responses without storing raw bodies."""

    def __init__(self, status_code: int, message: str, retry_after_seconds: int | None = None) -> None:
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be greater than or equal to zero")
        self.status_code = status_code
        self.message = message.strip() or "Massive HTTP error"
        self.retry_after_seconds = retry_after_seconds
        super().__init__(self.message)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: object, code: int, msg: str, headers: object, newurl: str) -> None:
        return None


class MassiveUrllibTransport:
    """Minimal HTTPS JSON transport for Massive using Python standard library."""

    def __init__(self, *, allowed_host: str = "api.massive.com", user_agent: str = "trading-intelligence-platform/0.1") -> None:
        self._allowed_host = _normalize_host(allowed_host)
        self._user_agent = user_agent.strip() or "trading-intelligence-platform/0.1"
        opener = build_opener(_NoRedirectHandler)
        self._urlopen: UrlOpen = lambda request, timeout: opener.open(request, timeout=timeout)

    def get_json(
        self,
        path: str,
        *,
        params: MassiveParams,
        api_key: SecretStr,
        timeout_seconds: Decimal,
        base_url: str,
    ) -> MassiveJson:
        url = self._build_url(base_url=base_url, path=path, params=params)
        timeout = _timeout_float(timeout_seconds)
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key.get_secret_value()}",
                "User-Agent": self._user_agent,
            },
            method="GET",
        )
        try:
            with self._urlopen(request, timeout) as response:
                body = response.read()
        except HTTPError as exc:
            retry_after_seconds = _retry_after_seconds(exc.headers.get("Retry-After"))
            if 300 <= exc.code < 400:
                raise MassiveTransportResponseError(exc.code, "Massive redirect response rejected") from exc
            if exc.code >= 500:
                raise MassiveTransportUnavailableError("Massive server error") from exc
            raise MassiveTransportResponseError(exc.code, "Massive HTTP error", retry_after_seconds) from exc
        except TimeoutError as exc:
            raise MassiveTransportTimeoutError("Massive request timed out") from exc
        except (URLError, OSError, socket.timeout) as exc:
            raise MassiveTransportUnavailableError("Massive transport unavailable") from exc
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MassiveTransportDataError("Massive response was not valid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise MassiveTransportDataError("Massive response JSON must be an object")
        return parsed

    def _build_url(self, *, base_url: str, path: str, params: MassiveParams) -> str:
        parsed_base = urlparse(base_url)
        if parsed_base.scheme != "https":
            raise MassiveTransportUnavailableError("Massive transport requires HTTPS")
        if _normalize_host(parsed_base.netloc) != self._allowed_host:
            raise MassiveTransportUnavailableError("Massive transport rejected unapproved host")
        if not path.startswith("/") or "?" in path:
            raise MassiveTransportDataError("Massive transport path must be a relative absolute path without query")
        if any(key.lower() == "apikey" for key in params):
            raise MassiveTransportDataError("Massive API key must not be sent as a query parameter")
        query = urlencode({key: _param_to_string(value) for key, value in params.items()})
        return f"{base_url.rstrip('/')}{path}" + (f"?{query}" if query else "")


def _param_to_string(value: MassiveParamValue) -> str | int:
    if isinstance(value, bool):
        return str(value).lower()
    return value


def _normalize_host(value: str) -> str:
    return value.strip().lower()


def _timeout_float(value: Decimal) -> float:
    if not value.is_finite() or value <= 0:
        raise MassiveTransportUnavailableError("Massive timeout must be positive and finite")
    return float(value)


def _retry_after_seconds(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value.strip())
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
