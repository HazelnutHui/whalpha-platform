"""Bounded inactive-security and lifecycle-field coverage probe."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Callable, Mapping
from urllib.parse import parse_qsl, urlparse

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveParamValue,
    MassiveTransportDataError,
    MassiveTransportResponseError,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)

CONTRACT_VERSION = "massive-historical-lifecycle-coverage-probe/1.0"
ALL_TICKERS_PATH = "/v3/reference/tickers"
PAGE_LIMIT = 1_000
MAXIMUM_REQUEST_COUNT = 2
_LIFECYCLE_FIELDS = (
    "delisted_utc",
    "last_updated_utc",
    "cik",
    "composite_figi",
    "share_class_figi",
)


class LifecycleProbeStatus(StrEnum):
    COMPLETED = "completed"
    TRUNCATED_AT_CEILING = "truncated_at_ceiling"
    AUTHENTICATION_FAILED = "authentication_failed"
    ENTITLEMENT_DENIED = "entitlement_denied"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    HTTP_ERROR = "http_error"


@dataclass(frozen=True)
class MassiveHistoricalLifecycleProbeV1:
    contract_version: str
    anchor_date: str
    status: LifecycleProbeStatus
    request_count: int
    page_count: int
    result_count: int
    pagination_complete: bool
    active_false_count: int
    active_true_conflict_count: int
    active_missing_count: int
    duplicate_ticker_count: int
    field_presence_counts: tuple[tuple[str, int], ...]
    retry_after_seconds: int | None
    response_body_retained: bool
    data_write_count: int
    coverage_conclusion_authorized: bool
    pilot_authorized: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def required_lifecycle_probe_acknowledgement(
    *, anchor_date: date, revision: str
) -> str:
    normalized = revision.strip().lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("revision must be a full 40-character Git SHA")
    binding = _fingerprint(
        {
            "anchor_date": anchor_date.isoformat(),
            "contract_version": CONTRACT_VERSION,
            "maximum_request_count": MAXIMUM_REQUEST_COUNT,
            "page_limit": PAGE_LIMIT,
            "revision": normalized,
        }
    )
    return f"I_AUTHORIZE_MASSIVE_LIFECYCLE_PROBE_{binding}"


def probe_massive_historical_lifecycle_coverage(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    anchor_date: date,
    before_request: Callable[[int], None] | None = None,
) -> MassiveHistoricalLifecycleProbeV1:
    """Inspect at most two inactive-Ticker pages and retain aggregate facts only."""

    path = ALL_TICKERS_PATH
    params: dict[str, MassiveParamValue] = {
        "market": "stocks",
        "active": False,
        "date": anchor_date.isoformat(),
        "limit": PAGE_LIMIT,
        "sort": "ticker",
        "order": "asc",
    }
    rows: list[Mapping[str, object]] = []
    seen_requests: set[
        tuple[str, tuple[tuple[str, MassiveParamValue], ...]]
    ] = set()
    request_count = 0
    page_count = 0
    retry_after: int | None = None
    status = LifecycleProbeStatus.COMPLETED
    pagination_complete = False
    try:
        for index in range(MAXIMUM_REQUEST_COUNT):
            request_key = (path, tuple(sorted(params.items())))
            if request_key in seen_requests:
                raise MassiveTransportDataError("Massive pagination loop detected")
            seen_requests.add(request_key)
            if before_request is not None:
                before_request(index)
            request_count += 1
            page = transport.get_json(
                path,
                params=params,
                api_key=config.api_key,
                timeout_seconds=config.request_timeout_seconds,
                base_url=config.base_url,
            )
            page_rows = _results(page)
            rows.extend(page_rows)
            page_count += 1
            next_url = page.get("next_url")
            if next_url is None:
                pagination_complete = True
                break
            if index == MAXIMUM_REQUEST_COUNT - 1:
                status = LifecycleProbeStatus.TRUNCATED_AT_CEILING
                break
            path, params = _next_page(
                next_url, config.base_url, anchor_date=anchor_date
            )
    except MassiveTransportResponseError as exc:
        retry_after = exc.retry_after_seconds
        if exc.status_code == 401:
            status = LifecycleProbeStatus.AUTHENTICATION_FAILED
        elif exc.status_code == 403:
            status = LifecycleProbeStatus.ENTITLEMENT_DENIED
        elif exc.status_code == 429:
            status = LifecycleProbeStatus.RATE_LIMITED
        else:
            status = LifecycleProbeStatus.HTTP_ERROR
    except (MassiveTransportTimeoutError, MassiveTransportUnavailableError):
        status = LifecycleProbeStatus.UNAVAILABLE
    except MassiveTransportDataError:
        status = LifecycleProbeStatus.MALFORMED_RESPONSE

    summary = _summarize(rows)
    payload = {
        "contract_version": CONTRACT_VERSION,
        "anchor_date": anchor_date.isoformat(),
        "status": status.value,
        "request_count": request_count,
        "page_count": page_count,
        "result_count": len(rows),
        "pagination_complete": pagination_complete,
        **summary,
        "retry_after_seconds": retry_after,
        "response_body_retained": False,
        "data_write_count": 0,
        "coverage_conclusion_authorized": False,
        "pilot_authorized": False,
    }
    return MassiveHistoricalLifecycleProbeV1(
        contract_version=CONTRACT_VERSION,
        anchor_date=anchor_date.isoformat(),
        status=status,
        request_count=request_count,
        page_count=page_count,
        result_count=len(rows),
        pagination_complete=pagination_complete,
        active_false_count=summary["active_false_count"],
        active_true_conflict_count=summary["active_true_conflict_count"],
        active_missing_count=summary["active_missing_count"],
        duplicate_ticker_count=summary["duplicate_ticker_count"],
        field_presence_counts=summary["field_presence_counts"],
        retry_after_seconds=retry_after,
        response_body_retained=False,
        data_write_count=0,
        coverage_conclusion_authorized=False,
        pilot_authorized=False,
        logical_content_fingerprint=_fingerprint(payload),
    )


def _results(page: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = page.get("results")
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise MassiveTransportDataError("Massive results are malformed")
    return tuple(value)


def _next_page(
    value: object, base_url: str, *, anchor_date: date
) -> tuple[str, dict[str, MassiveParamValue]]:
    if not isinstance(value, str) or not value.strip():
        raise MassiveTransportDataError("Massive next_url is invalid")
    parsed = urlparse(value)
    base = urlparse(base_url)
    if parsed.netloc and parsed.netloc != base.netloc:
        raise MassiveTransportDataError("Massive pagination host changed")
    if parsed.path != ALL_TICKERS_PATH:
        raise MassiveTransportDataError("Massive pagination path changed")
    params = {
        key: item
        for key, item in parse_qsl(parsed.query, keep_blank_values=False)
        if key.lower() != "apikey"
    }
    if not params:
        raise MassiveTransportDataError("Massive pagination params are absent")
    required = {
        "market": "stocks",
        "active": "false",
        "date": anchor_date.isoformat(),
        "limit": str(PAGE_LIMIT),
        "sort": "ticker",
        "order": "asc",
    }
    for key, expected in required.items():
        actual = params.get(key)
        if actual is not None and str(actual).lower() != expected:
            raise MassiveTransportDataError("Massive pagination scope changed")
        params[key] = expected
    return parsed.path, params


def _summarize(rows: list[Mapping[str, object]]) -> dict[str, object]:
    active_false = sum(row.get("active") is False for row in rows)
    active_true = sum(row.get("active") is True for row in rows)
    active_missing = len(rows) - active_false - active_true
    tickers = [
        value.strip().upper()
        for row in rows
        if isinstance((value := row.get("ticker")), str) and value.strip()
    ]
    field_counts = tuple(
        (field, sum(_present(row.get(field)) for row in rows))
        for field in _LIFECYCLE_FIELDS
    )
    return {
        "active_false_count": active_false,
        "active_true_conflict_count": active_true,
        "active_missing_count": active_missing,
        "duplicate_ticker_count": len(tickers) - len(set(tickers)),
        "field_presence_counts": field_counts,
    }


def _present(value: object) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


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
