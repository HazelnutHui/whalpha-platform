"""Offline-testable SEC transport policy and protocol; no live implementation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import monotonic, sleep
from typing import Callable, Mapping, Protocol
from urllib.parse import urlparse

from pydantic import SecretStr

SEC_ALLOWED_HOSTS = frozenset({"www.sec.gov", "data.sec.gov"})


class SecTransportError(Exception):
    pass


class SecTransport(Protocol):
    def get_bytes(
        self,
        url: str,
        *,
        user_agent: SecretStr,
        timeout_seconds: Decimal,
    ) -> bytes: ...


def validate_sec_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in SEC_ALLOWED_HOSTS:
        raise SecTransportError("SEC request rejected by transport policy")
    if parsed.username or parsed.password or parsed.fragment:
        raise SecTransportError("SEC request URL is invalid")
    return url


def redirect_is_allowed(source_url: str, target_url: str) -> bool:
    try:
        validate_sec_url(source_url)
        validate_sec_url(target_url)
    except SecTransportError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class SecRetryPolicy:
    max_retries: int = 2

    def should_retry(self, *, status_code: int, completed_retries: int) -> bool:
        return completed_retries < self.max_retries and (status_code == 429 or 500 <= status_code < 600)


class SecRateLimiter:
    """Serial fixed-interval limiter with injectable monotonic clock and sleeper."""

    def __init__(
        self,
        *,
        max_requests_per_second: Decimal = Decimal("2"),
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if not max_requests_per_second.is_finite() or max_requests_per_second <= 0 or max_requests_per_second > 2:
            raise ValueError("SEC request rate must be in (0, 2]")
        self._minimum_interval = float(Decimal(1) / max_requests_per_second)
        self._clock = clock
        self._sleeper = sleeper
        self._last_request_at: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self._minimum_interval - (now - self._last_request_at)
            if remaining > 0:
                self._sleeper(remaining)
                now = self._clock()
        self._last_request_at = now


class FakeSecTransport:
    """Deterministic transport for fixtures; it never opens a socket."""

    def __init__(self, responses: Mapping[str, bytes]) -> None:
        self._responses = dict(responses)
        self.requests: list[str] = []

    def get_bytes(self, url: str, *, user_agent: SecretStr, timeout_seconds: Decimal) -> bytes:
        validate_sec_url(url)
        if not user_agent.get_secret_value() or not timeout_seconds.is_finite() or timeout_seconds <= 0:
            raise SecTransportError("SEC request configuration is invalid")
        self.requests.append(url)
        try:
            return self._responses[url]
        except KeyError as exc:
            raise SecTransportError("SEC fixture response is unavailable") from exc
