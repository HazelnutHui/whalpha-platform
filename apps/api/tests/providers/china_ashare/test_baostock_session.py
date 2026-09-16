from __future__ import annotations

from dataclasses import dataclass

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


def test_failed_login_never_marks_session_open() -> None:
    module = FakeModule(login_code="1001")
    session = BaoStockClientSession(module=module)

    with pytest.raises(ProviderUnavailableError, match="login failed"):
        with session:
            pass
    assert module.login_count == 1
    assert module.logout_count == 0
