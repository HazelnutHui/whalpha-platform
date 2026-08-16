from decimal import Decimal
from email.message import Message
from io import BytesIO
import socket
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from tip_api.providers.sec.transport import (
    BoundedSecTransport,
    FakeSecTransport,
    SecRateLimiter,
    SecRetryPolicy,
    SecTransportError,
    redirect_is_allowed,
    validate_sec_url,
)
from tip_api.providers.sec.live_ingestion import SEC_LIVE_MAX_RETRIES

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


class Response(BytesIO):
    status = 200

    def __init__(self, value: bytes, content_type="application/json", content_length=None):
        super().__init__(value)
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)


class Opener:
    def __init__(self, responses):
        self.responses = list(responses)

    def open(self, request, timeout):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_zero_retry_policy_stops_after_first_recoverable_failure() -> None:
    assert SEC_LIVE_MAX_RETRIES == 0
    headers = Message()
    failure = HTTPError("https://www.sec.gov/files/source.json", 503, "fixture", headers, None)
    opener = Opener([failure, Response(b"must-not-be-requested")])
    transport = BoundedSecTransport(
        request_ceiling=12,
        retry_policy=SecRetryPolicy(max_retries=0),
        opener=opener,
    )
    with pytest.raises(SecTransportError) as caught:
        transport.get_bytes(
            "https://www.sec.gov/files/source.json",
            user_agent=UA,
            timeout_seconds=Decimal("2"),
        )
    assert caught.value.status_code == 503
    assert transport.request_count == 1
    assert transport.retry_count == 0
    assert len(opener.responses) == 1


def test_bounded_transport_streams_and_enforces_request_ceiling_without_leaking_contact(tmp_path) -> None:
    transport = BoundedSecTransport(request_ceiling=1, opener=Opener([Response(b"fixture")]))
    target = tmp_path / "source.json"
    result = transport.download(
        "https://www.sec.gov/files/source.json", target,
        user_agent=UA, timeout_seconds=Decimal("2"), max_bytes=100,
    )
    assert target.read_bytes() == b"fixture" and result.byte_count == 7
    assert transport.request_count == 1 and "fixture-contact" not in repr(result)
    with pytest.raises(SecTransportError, match="ceiling"):
        transport.get_bytes("https://www.sec.gov/files/second.json", user_agent=UA, timeout_seconds=Decimal("2"))


def test_bounded_transport_rejects_declared_and_streamed_oversize(tmp_path) -> None:
    first = BoundedSecTransport(opener=Opener([Response(b"x", content_length=101)]))
    with pytest.raises(SecTransportError, match="size"):
        first.download("https://www.sec.gov/files/a", tmp_path / "a", user_agent=UA, timeout_seconds=Decimal("2"), max_bytes=100)
    second = BoundedSecTransport(opener=Opener([Response(b"x" * 101)]))
    with pytest.raises(SecTransportError, match="size"):
        second.download("https://www.sec.gov/files/b", tmp_path / "b", user_agent=UA, timeout_seconds=Decimal("2"), max_bytes=100)
