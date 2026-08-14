"""Deterministic fake Massive transport for adapter tests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from pydantic import SecretStr

from tip_api.providers.massive.transport import MassiveJson, MassiveParamValue, MassiveParams


@dataclass(frozen=True)
class MassiveTransportCall:
    path: str
    params: tuple[tuple[str, MassiveParamValue], ...]
    credential_supplied: bool
    timeout_seconds: Decimal


class FakeMassiveTransport:
    """Route preloaded responses without recording credential values."""

    def __init__(self, responses: Mapping[tuple[str, tuple[tuple[str, MassiveParamValue], ...]], MassiveJson]) -> None:
        self._responses = dict(responses)
        self.calls: list[MassiveTransportCall] = []

    def get_json(
        self,
        path: str,
        *,
        params: MassiveParams,
        api_key: SecretStr,
        timeout_seconds: Decimal,
    ) -> MassiveJson:
        sanitized_params = tuple(sorted(params.items()))
        self.calls.append(
            MassiveTransportCall(
                path=path,
                params=sanitized_params,
                credential_supplied=bool(api_key.get_secret_value()),
                timeout_seconds=timeout_seconds,
            )
        )
        try:
            return self._responses[(path, sanitized_params)]
        except KeyError as exc:
            raise AssertionError(f"unexpected Massive fake request: {path} {sanitized_params}") from exc


def route(path: str, params: Mapping[str, MassiveParamValue]) -> tuple[str, tuple[tuple[str, MassiveParamValue], ...]]:
    return path, tuple(sorted(params.items()))
