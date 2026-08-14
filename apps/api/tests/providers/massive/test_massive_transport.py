from __future__ import annotations

import socket
from decimal import Decimal
from urllib.error import HTTPError, URLError

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.transport import (
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
    MassiveUrllibTransport,
)

SENTINEL_SECRET = "test-secret-must-never-appear"
BASE_URL = "https://api.massive.com"


class FakeHeaders(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str | None:
        return super().get(key, default)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def make_transport(opener):
    transport = MassiveUrllibTransport()
    transport._urlopen = opener  # type: ignore[attr-defined]
    return transport


def test_authorization_bearer_header_is_injected_and_api_key_not_in_query() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse(b'{"results": []}')

    response = make_transport(opener).get_json(
        "/v3/reference/tickers",
        params={"market": "stocks", "active": True, "limit": 1},
        api_key=SecretStr(SENTINEL_SECRET),
        timeout_seconds=Decimal("3.5"),
        base_url=BASE_URL,
    )

    assert response == {"results": []}
    assert captured["url"] == "https://api.massive.com/v3/reference/tickers?market=stocks&active=true&limit=1"
    assert "apiKey" not in captured["url"]
    auth_header = captured["headers"]["Authorization"]
    assert auth_header.startswith("Bearer ")
    if auth_header.removeprefix("Bearer ") != SENTINEL_SECRET:
        pytest.fail("authorization credential mismatch")
    assert captured["headers"]["User-agent"] == "trading-intelligence-platform/0.1"
    assert captured["timeout"] == 3.5


def test_secret_not_exposed_in_transport_exception() -> None:
    def opener(request, timeout):
        raise HTTPError(request.full_url, 401, "unauthorized", FakeHeaders(), None)

    with pytest.raises(MassiveTransportResponseError) as exc_info:
        make_transport(opener).get_json(
            "/v3/reference/tickers",
            params={"limit": 1},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=BASE_URL,
        )

    assert exc_info.value.status_code == 401
    assert SENTINEL_SECRET not in str(exc_info.value)


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_status_is_transport_response_error(status: int) -> None:
    def opener(request, timeout):
        raise HTTPError(request.full_url, status, "auth", FakeHeaders(), None)

    with pytest.raises(MassiveTransportResponseError) as exc_info:
        make_transport(opener).get_json(
            "/v3/reference/tickers",
            params={"limit": 1},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=BASE_URL,
        )
    assert exc_info.value.status_code == status


def test_rate_limit_retry_after_is_preserved() -> None:
    def opener(request, timeout):
        raise HTTPError(request.full_url, 429, "limited", FakeHeaders({"Retry-After": "9"}), None)

    with pytest.raises(MassiveTransportResponseError) as exc_info:
        make_transport(opener).get_json(
            "/v3/reference/tickers",
            params={"limit": 1},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=BASE_URL,
        )
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_seconds == 9


def test_timeout_connection_and_5xx_mapping() -> None:
    for raised, expected in (
        (TimeoutError("timeout"), MassiveTransportTimeoutError),
        (URLError("dns"), MassiveTransportUnavailableError),
        (HTTPError("https://api.massive.com/test", 500, "server", FakeHeaders(), None), MassiveTransportUnavailableError),
    ):
        def opener(request, timeout, raised=raised):
            raise raised

        with pytest.raises(expected):
            make_transport(opener).get_json(
                "/v3/reference/tickers",
                params={"limit": 1},
                api_key=SecretStr(SENTINEL_SECRET),
                timeout_seconds=Decimal("2"),
                base_url=BASE_URL,
            )


@pytest.mark.parametrize("body", [b"not-json", b"[]"])
def test_malformed_json_and_unexpected_shape_are_data_errors(body: bytes) -> None:
    def opener(request, timeout):
        return FakeResponse(body)

    with pytest.raises(MassiveTransportDataError):
        make_transport(opener).get_json(
            "/v3/reference/tickers",
            params={"limit": 1},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=BASE_URL,
        )


def test_redirect_status_is_rejected() -> None:
    def opener(request, timeout):
        raise HTTPError(request.full_url, 302, "redirect", FakeHeaders({"Location": "https://example.test/"}), None)

    with pytest.raises(MassiveTransportResponseError, match="redirect"):
        make_transport(opener).get_json(
            "/v3/reference/tickers",
            params={"limit": 1},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=BASE_URL,
        )


@pytest.mark.parametrize("base_url", ["http://api.massive.com", "https://example.test"])
def test_rejects_insecure_or_unapproved_host(base_url: str) -> None:
    with pytest.raises(MassiveTransportUnavailableError):
        MassiveUrllibTransport().get_json(
            "/v3/reference/tickers",
            params={"limit": 1},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=base_url,
        )


def test_rejects_api_key_query_parameter() -> None:
    with pytest.raises(MassiveTransportDataError):
        MassiveUrllibTransport().get_json(
            "/v3/reference/tickers",
            params={"apiKey": "bad"},
            api_key=SecretStr(SENTINEL_SECRET),
            timeout_seconds=Decimal("2"),
            base_url=BASE_URL,
        )


def test_no_network_for_unit_test_when_socket_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", fail_socket)

    def opener(request, timeout):
        return FakeResponse(b'{"results": []}')

    assert make_transport(opener).get_json(
        "/v3/reference/tickers",
        params={"limit": 1},
        api_key=SecretStr(SENTINEL_SECRET),
        timeout_seconds=Decimal("2"),
        base_url=BASE_URL,
    ) == {"results": []}
