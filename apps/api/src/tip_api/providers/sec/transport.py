"""Bounded SEC HTTPS transport with offline-testable policy controls."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import monotonic, sleep
from email.message import Message
from pathlib import Path
from typing import BinaryIO, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlparse

from pydantic import SecretStr

SEC_ALLOWED_HOSTS = frozenset({"www.sec.gov", "data.sec.gov"})


class SecTransportError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SecTransport(Protocol):
    def get_bytes(
        self,
        url: str,
        *,
        user_agent: SecretStr,
        timeout_seconds: Decimal,
    ) -> bytes: ...


@dataclass(frozen=True, slots=True)
class SecDownloadResult:
    url: str
    content_type: str
    byte_count: int
    sha256: str
    retry_count: int


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


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: BinaryIO, code: int, msg: str, headers: Message, newurl: str) -> Request | None:
        if not redirect_is_allowed(req.full_url, newurl):
            raise SecTransportError("SEC redirect rejected by transport policy")
        return Request(newurl, headers={"User-Agent": req.headers.get("User-agent", "")}, method="GET")


class BoundedSecTransport:
    """Serial streaming transport; response content and contact identity are never logged."""

    def __init__(
        self,
        *,
        request_ceiling: int = 12,
        rate_limiter: SecRateLimiter | None = None,
        retry_policy: SecRetryPolicy | None = None,
        opener: object | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if request_ceiling <= 0 or request_ceiling > 12:
            raise ValueError("SEC request ceiling must be in (0, 12]")
        self.request_ceiling = request_ceiling
        self.request_count = 0
        self.retry_count = 0
        self._rate_limiter = rate_limiter or SecRateLimiter()
        self._retry_policy = retry_policy or SecRetryPolicy()
        self._opener = opener or build_opener(_SafeRedirectHandler())
        self._sleeper = sleeper

    def get_bytes(self, url: str, *, user_agent: SecretStr, timeout_seconds: Decimal, max_bytes: int = 16 * 1024 * 1024) -> bytes:
        from io import BytesIO

        target = BytesIO()
        self._download(url, target, user_agent=user_agent, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
        return target.getvalue()

    def download(self, url: str, target: Path, *, user_agent: SecretStr, timeout_seconds: Decimal, max_bytes: int) -> SecDownloadResult:
        if target.exists() or target.is_symlink():
            raise SecTransportError("SEC download target already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as handle:
                result = self._download(url, handle, user_agent=user_agent, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
            return result
        except Exception:
            target.unlink(missing_ok=True)
            raise

    def _download(self, url: str, target: BinaryIO, *, user_agent: SecretStr, timeout_seconds: Decimal, max_bytes: int) -> SecDownloadResult:
        import hashlib

        validate_sec_url(url)
        if not timeout_seconds.is_finite() or timeout_seconds <= 0 or max_bytes <= 0:
            raise SecTransportError("SEC request configuration is invalid")
        contact = user_agent.get_secret_value()
        if not contact:
            raise SecTransportError("SEC request configuration is invalid")
        completed_retries = 0
        while True:
            if self.request_count >= self.request_ceiling:
                raise SecTransportError("SEC request ceiling exceeded")
            self._rate_limiter.wait()
            self.request_count += 1
            request = Request(url, headers={"User-Agent": contact, "Accept-Encoding": "identity"}, method="GET")
            try:
                response = self._opener.open(request, timeout=float(timeout_seconds))
                status = int(getattr(response, "status", 200))
                if status != 200:
                    raise SecTransportError("SEC returned an unexpected response", status_code=status)
                content_type = str(response.headers.get_content_type()).lower()
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) > max_bytes:
                    raise SecTransportError("SEC response exceeds the configured size limit")
                digest = hashlib.sha256()
                count = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > max_bytes:
                        raise SecTransportError("SEC response exceeds the configured size limit")
                    digest.update(chunk)
                    target.write(chunk)
                return SecDownloadResult(url, content_type, count, digest.hexdigest(), completed_retries)
            except HTTPError as exc:
                status = int(exc.code)
                if status in {401, 403} or not self._retry_policy.should_retry(status_code=status, completed_retries=completed_retries):
                    raise SecTransportError("SEC HTTP request failed", status_code=status) from exc
                completed_retries += 1
                self.retry_count += 1
                delay = _retry_after_seconds(exc.headers.get("Retry-After"))
                self._sleeper(delay)
            except (URLError, TimeoutError, OSError) as exc:
                raise SecTransportError("SEC network request failed") from exc


def _retry_after_seconds(value: str | None) -> float:
    if value is None:
        return 1.0
    try:
        parsed = float(value)
    except ValueError:
        return 1.0
    return min(max(parsed, 0.0), 60.0)


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
