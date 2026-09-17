from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from tip_api.providers.china_ashare import BaoStockClientSession
from tip_api.providers.market_data import ProviderUnavailableError


@dataclass
class Result:
    error_code: str = "0"
    error_msg: str = ""


class FakeModule:
    def __init__(self, *, login_code: str = "0") -> None:
        self.login_code = login_code
        self.login_count = 0
        self.logout_count = 0
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def login(self) -> Result:
        self.login_count += 1
        return Result(error_code=self.login_code)

    def logout(self) -> Result:
        self.logout_count += 1
        return Result()

    def query_all_stock(self, *args: object, **kwargs: object) -> Result:
        self.calls.append(("query_all_stock", args, kwargs))
        return Result()

    def query_stock_basic(self, *args: object, **kwargs: object) -> Result:
        self.calls.append(("query_stock_basic", args, kwargs))
        return Result()


class FakeSocket:
    def __init__(self, *, received: bytes = b"response") -> None:
        self.received = received
        self.timeout: float | None = None
        self.close_count = 0

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def recv(self, *args: object, **kwargs: object) -> bytes:
        return self.received

    def close(self) -> None:
        self.close_count += 1


class SocketReadingFakeModule(FakeModule):
    def __init__(self, *, socket_context: Any) -> None:
        super().__init__()
        self.socket_context = socket_context

    def query_all_stock(self, *args: object, **kwargs: object) -> Result:
        self.socket_context.default_socket.recv(8192)
        return super().query_all_stock(*args, **kwargs)


def test_session_connects_and_disconnects_only_inside_context() -> None:
    module = FakeModule()
    session = BaoStockClientSession(module=module)

    assert module.login_count == 0
    with session as opened:
        result = opened.query_all_stock(day="2026-09-16")
        assert result.error_code == "0"
        assert module.login_count == 1
        assert module.logout_count == 0
    assert module.logout_count == 1


def test_session_rejects_calls_when_not_open() -> None:
    session = BaoStockClientSession(module=FakeModule())

    with pytest.raises(ProviderUnavailableError, match="not open"):
        session.query_all_stock(day="2026-09-16")


def test_session_exposes_security_basic_only_while_open() -> None:
    module = FakeModule()

    with BaoStockClientSession(module=module) as session:
        result = session.query_stock_basic(code="", code_name="")

    assert result.error_code == "0"
    assert module.calls == [("query_stock_basic", (), {"code": "", "code_name": ""})]


def test_failed_login_never_marks_session_open() -> None:
    module = FakeModule(login_code="1001")
    session = BaoStockClientSession(module=module)

    with pytest.raises(ProviderUnavailableError, match="login failed"):
        with session:
            pass
    assert module.login_count == 1
    assert module.logout_count == 0


def test_session_bounds_socket_reads_and_closes_the_connection() -> None:
    socket = FakeSocket()
    context = SimpleNamespace(default_socket=socket)
    module = SocketReadingFakeModule(socket_context=context)

    with BaoStockClientSession(
        module=module,
        socket_context=context,
        socket_read_timeout_seconds=12.5,
    ) as session:
        result = session.query_all_stock(day="2026-09-16")

    assert result.error_code == "0"
    assert socket.timeout == 12.5
    assert socket.close_count == 1


def test_session_turns_socket_eof_into_provider_unavailable() -> None:
    socket = FakeSocket(received=b"")
    context = SimpleNamespace(default_socket=socket)
    module = SocketReadingFakeModule(socket_context=context)

    with BaoStockClientSession(module=module, socket_context=context) as session:
        with pytest.raises(ProviderUnavailableError, match="source call failed"):
            session.query_all_stock(day="2026-09-16")

    assert socket.close_count == 1


def test_session_rejects_non_positive_socket_timeout() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        BaoStockClientSession(module=FakeModule(), socket_read_timeout_seconds=0)
