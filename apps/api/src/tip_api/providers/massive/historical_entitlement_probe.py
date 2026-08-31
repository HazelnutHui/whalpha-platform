"""Bounded, non-retaining Massive historical endpoint capability probe."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Callable

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveParams,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)

CONTRACT_VERSION = "massive-historical-entitlement-probe/1.0"
MAXIMUM_REQUEST_COUNT = 4


class EntitlementProbeStatus(StrEnum):
    ACCESSIBLE = "accessible"
    AUTHENTICATION_FAILED = "authentication_failed"
    ENTITLEMENT_DENIED = "entitlement_denied"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    HTTP_ERROR = "http_error"


@dataclass(frozen=True)
class EntitlementProbeLineV1:
    capability_id: str
    logical_endpoint: str
    status: EntitlementProbeStatus
    result_count: int | None
    request_count: int
    retry_after_seconds: int | None


@dataclass(frozen=True)
class MassiveHistoricalEntitlementProbeV1:
    contract_version: str
    session_date: str
    lines: tuple[EntitlementProbeLineV1, ...]
    request_count: int
    response_body_retained: bool
    data_write_count: int
    permission_conclusion_authorized: bool
    pilot_authorized: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def required_probe_acknowledgement(*, session_date: date, revision: str) -> str:
    """Bind one probe authorization to an exact date and source revision."""

    normalized_revision = revision.strip().lower()
    if len(normalized_revision) != 40 or any(
        character not in "0123456789abcdef" for character in normalized_revision
    ):
        raise ValueError("revision must be a full 40-character Git SHA")
    binding = _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "maximum_request_count": MAXIMUM_REQUEST_COUNT,
            "revision": normalized_revision,
            "session_date": session_date.isoformat(),
        }
    )
    return f"I_AUTHORIZE_MASSIVE_ENTITLEMENT_PROBE_{binding}"


def probe_massive_historical_entitlements(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    session_date: date,
    before_request: Callable[[int], None] | None = None,
) -> MassiveHistoricalEntitlementProbeV1:
    """Make four serial metadata probes without retaining response bodies."""

    specifications = (
        (
            "grouped_daily_unadjusted",
            f"/v2/aggs/grouped/locale/us/market/stocks/{session_date.isoformat()}",
            {"adjusted": False},
        ),
        (
            "point_in_time_active_tickers",
            "/v3/reference/tickers",
            {
                "market": "stocks",
                "active": True,
                "date": session_date.isoformat(),
                "limit": 1,
            },
        ),
        (
            "splits",
            "/v3/reference/splits",
            {"execution_date": session_date.isoformat(), "limit": 1},
        ),
        (
            "dividends",
            "/v3/reference/dividends",
            {"ex_dividend_date": session_date.isoformat(), "limit": 1},
        ),
    )
    lines: list[EntitlementProbeLineV1] = []
    for index, (capability_id, endpoint, params) in enumerate(specifications):
        if before_request is not None:
            before_request(index)
        lines.append(
            _probe_line(
                capability_id=capability_id,
                endpoint=endpoint,
                params=params,
                config=config,
                transport=transport,
            )
        )
    request_count = sum(line.request_count for line in lines)
    if request_count != MAXIMUM_REQUEST_COUNT:
        raise RuntimeError("historical entitlement probe request count drifted")
    payload = {
        "contract_version": CONTRACT_VERSION,
        "session_date": session_date.isoformat(),
        "lines": [_jsonable(asdict(line)) for line in lines],
        "request_count": request_count,
        "response_body_retained": False,
        "data_write_count": 0,
        "permission_conclusion_authorized": False,
        "pilot_authorized": False,
    }
    return MassiveHistoricalEntitlementProbeV1(
        contract_version=CONTRACT_VERSION,
        session_date=session_date.isoformat(),
        lines=tuple(lines),
        request_count=request_count,
        response_body_retained=False,
        data_write_count=0,
        permission_conclusion_authorized=False,
        pilot_authorized=False,
        logical_content_fingerprint=_fingerprint(payload),
    )


def _probe_line(
    *,
    capability_id: str,
    endpoint: str,
    params: MassiveParams,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
) -> EntitlementProbeLineV1:
    try:
        response = transport.get_json(
            endpoint,
            params=params,
            api_key=config.api_key,
            timeout_seconds=config.request_timeout_seconds,
            base_url=config.base_url,
        )
        results = response.get("results")
        if not isinstance(results, list):
            raise MassiveTransportDataError("Massive response results must be a list")
        return EntitlementProbeLineV1(
            capability_id=capability_id,
            logical_endpoint=endpoint,
            status=EntitlementProbeStatus.ACCESSIBLE,
            result_count=len(results),
            request_count=1,
            retry_after_seconds=None,
        )
    except MassiveTransportResponseError as exc:
        if exc.status_code == 401:
            status = EntitlementProbeStatus.AUTHENTICATION_FAILED
        elif exc.status_code == 403:
            status = EntitlementProbeStatus.ENTITLEMENT_DENIED
        elif exc.status_code == 429:
            status = EntitlementProbeStatus.RATE_LIMITED
        else:
            status = EntitlementProbeStatus.HTTP_ERROR
        return _failed_line(capability_id, endpoint, status, exc.retry_after_seconds)
    except (MassiveTransportTimeoutError, MassiveTransportUnavailableError):
        return _failed_line(
            capability_id, endpoint, EntitlementProbeStatus.UNAVAILABLE, None
        )
    except MassiveTransportDataError:
        return _failed_line(
            capability_id, endpoint, EntitlementProbeStatus.MALFORMED_RESPONSE, None
        )


def _failed_line(
    capability_id: str,
    endpoint: str,
    status: EntitlementProbeStatus,
    retry_after_seconds: int | None,
) -> EntitlementProbeLineV1:
    return EntitlementProbeLineV1(
        capability_id=capability_id,
        logical_endpoint=endpoint,
        status=status,
        result_count=None,
        request_count=1,
        retry_after_seconds=retry_after_seconds,
    )


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    return value
