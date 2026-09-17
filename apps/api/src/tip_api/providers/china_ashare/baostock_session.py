"""Explicit BaoStock connection lifecycle for bounded live operations."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

from tip_api.providers.market_data import ProviderUnavailableError

from .baostock_adapter import BAOSTOCK_ASHARE_PROVIDER_ID, BaoStockCursor


class BaoStockClientSession:
    """Open BaoStock only inside an explicit context manager.

    Constructing this object does not import BaoStock, connect, log in, query,
    retry, sleep, or write.  This class intentionally exposes only the bounded
    bounded methods required by the source adapter.
    """

    def __init__(self, *, module: ModuleType | Any | None = None) -> None:
        self._module = module
        self._connected = False

    def __enter__(self) -> "BaoStockClientSession":
        if self._connected:
            raise RuntimeError("BaoStock session is already open")
        module = self._module
        if module is None:
            try:
                module = importlib.import_module("baostock")
            except ImportError as exc:
                raise ProviderUnavailableError(
                    BAOSTOCK_ASHARE_PROVIDER_ID,
                    "BaoStock optional dependency is not installed",
                ) from exc
            self._module = module
        try:
            result = module.login()
        except Exception as exc:  # source library exposes no stable error hierarchy
            raise ProviderUnavailableError(
                BAOSTOCK_ASHARE_PROVIDER_ID,
                "BaoStock login failed",
            ) from exc
        if str(getattr(result, "error_code", "")) != "0":
            raise ProviderUnavailableError(
                BAOSTOCK_ASHARE_PROVIDER_ID,
                "BaoStock login failed",
            )
        self._connected = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if not self._connected:
            return
        try:
            assert self._module is not None
            self._module.logout()
        finally:
            self._connected = False

    def query_all_stock(self, day: str = "") -> BaoStockCursor:
        return self._call("query_all_stock", day=day)

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str = "",
        end_date: str = "",
        frequency: str = "d",
        adjustflag: str = "3",
    ) -> BaoStockCursor:
        return self._call(
            "query_history_k_data_plus",
            code,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
        )

    def query_adjust_factor(
        self,
        code: str,
        start_date: str = "",
        end_date: str = "",
    ) -> BaoStockCursor:
        return self._call(
            "query_adjust_factor",
            code,
            start_date=start_date,
            end_date=end_date,
        )

    def query_stock_basic(
        self,
        code: str = "",
        code_name: str = "",
    ) -> BaoStockCursor:
        return self._call("query_stock_basic", code=code, code_name=code_name)

    def _call(self, method_name: str, *args: object, **kwargs: object) -> BaoStockCursor:
        if not self._connected or self._module is None:
            raise ProviderUnavailableError(
                BAOSTOCK_ASHARE_PROVIDER_ID,
                "BaoStock session is not open",
            )
        try:
            method = getattr(self._module, method_name)
            return method(*args, **kwargs)
        except Exception as exc:  # source library exposes no stable error hierarchy
            raise ProviderUnavailableError(
                BAOSTOCK_ASHARE_PROVIDER_ID,
                "BaoStock source call failed",
            ) from exc
