from decimal import Decimal
import socket

import pytest
from pydantic import SecretStr

from tip_api.providers.sec.transport import (
    FakeSecTransport,
    SecRateLimiter,
    SecRetryPolicy,
    SecTransportError,
    redirect_is_allowed,
    validate_sec_url,
)

UA = SecretStr("trading-intelligence-platform fixture-contact@invalid.example")


@pytest.mark.parametrize("url", [
    "https://www.sec.gov/files/company_tickers_exchange.json",
    "https://data.sec.gov/submissions/CIK0000000001.json",
])
def test_https_allowlist(url: str) -> None:
    assert validate_sec_url(url) == url


@pytest.mark.parametrize("url", [
    "http://www.sec.gov/test", "https://example.test/test", "https://user@www.sec.gov/test",
])
def test_transport_rejects_insecure_or_unapproved_urls(url: str) -> None:
    with pytest.raises(SecTransportError):
        validate_sec_url(url)


def test_redirect_never_forwards_to_unapproved_host() -> None:
    source = "https://www.sec.gov/test"
    assert redirect_is_allowed(source, "https://data.sec.gov/test")
    assert not redirect_is_allowed(source, "https://example.test/test")


def test_rate_limiter_is_serial_and_at_most_two_per_second() -> None:
    state = {"now": 10.0}
    sleeps: list[float] = []
    def sleeper(value: float) -> None:
        sleeps.append(value)
        state["now"] += value
    limiter = SecRateLimiter(clock=lambda: state["now"], sleeper=sleeper)
    limiter.wait()
    limiter.wait()
    assert sleeps == [0.5]
    with pytest.raises(ValueError):
        SecRateLimiter(max_requests_per_second=Decimal("2.01"))


def test_retry_policy_is_bounded_to_429_and_recoverable_5xx() -> None:
    policy = SecRetryPolicy(max_retries=2)
    assert policy.should_retry(status_code=429, completed_retries=0)
    assert policy.should_retry(status_code=503, completed_retries=1)
    assert not policy.should_retry(status_code=503, completed_retries=2)
    assert not policy.should_retry(status_code=400, completed_retries=0)


def test_fake_transport_never_opens_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network attempted"))
    url = "https://www.sec.gov/fixture"
    transport = FakeSecTransport({url: b"fixture"})
    assert transport.get_bytes(url, user_agent=UA, timeout_seconds=Decimal("2")) == b"fixture"
    assert transport.requests == [url]
