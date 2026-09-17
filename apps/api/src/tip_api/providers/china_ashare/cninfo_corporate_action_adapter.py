"""Explicit CNINFO distribution capture with exact raw-response retention."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Mapping, Protocol
from urllib.parse import urlparse
from uuid import UUID

from tip_api.contracts.china_ashare.v1.corporate_actions import (
    ChinaAshareCorporateActionObservationV1,
    build_corporate_action_observation,
)
from tip_api.contracts.common import QualityStatus
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


CNINFO_CORPORATE_ACTION_PROVIDER_ID = "cninfo_webapi_p_sysapi1139"
CNINFO_CORPORATE_ACTION_URL = "https://webapi.cninfo.com.cn/api/sysapi/p_sysapi1139"
CNINFO_RIGHTS_ISSUE_PROVIDER_ID = "cninfo_webapi_p_stock2232"
CNINFO_RIGHTS_ISSUE_URL = "https://webapi.cninfo.com.cn/api/stock/p_stock2232"
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class CninfoCorporateActionSourceKind(StrEnum):
    DISTRIBUTION = "distribution"
    RIGHTS_ISSUE = "rights_issue"


@dataclass(frozen=True, slots=True)
class CninfoCorporateActionHttpResponseV1:
    status: int
    content_type: str
    final_url: str
    body: bytes


@dataclass(frozen=True, slots=True)
class CapturedCninfoCorporateActionsV1:
    source_kind: CninfoCorporateActionSourceKind
    source_security_id: str
    instrument_id: UUID
    retrieved_at: datetime
    final_url: str
    content_type: str
    raw_bytes: bytes
    observations: tuple[ChinaAshareCorporateActionObservationV1, ...]


class CninfoCorporateActionHttpFetcher(Protocol):
    def fetch_distribution(
        self, *, source_code: str
    ) -> CninfoCorporateActionHttpResponseV1: ...

    def fetch_rights_issues(
        self, *, source_code: str, start_date: date, end_date: date
    ) -> CninfoCorporateActionHttpResponseV1: ...


class AkshareTransportCninfoCorporateActionFetcher:
    """Fetch exact CNINFO bytes using AKShare's installed token transport.

    Construction performs no import, network request, retry, sleep, or write.
    The private AKShare token helper is isolated here because CNINFO currently
    requires its time-varying ``Accept-Enckey`` header. Schema parsing and
    custody do not depend on AKShare.
    """

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("CNINFO timeout is outside its safety range")
        self._timeout_seconds = timeout_seconds

    def fetch_distribution(
        self, *, source_code: str
    ) -> CninfoCorporateActionHttpResponseV1:
        return self._fetch(
            source_code=source_code,
            url=CNINFO_CORPORATE_ACTION_URL,
            params={"scode": source_code},
            helper_module="akshare.stock.stock_dividend_cninfo",
            helper_name="_get_file_content_ths",
        )

    def fetch_rights_issues(
        self, *, source_code: str, start_date: date, end_date: date
    ) -> CninfoCorporateActionHttpResponseV1:
        return self._fetch(
            source_code=source_code,
            url=CNINFO_RIGHTS_ISSUE_URL,
            params={
                "scode": source_code,
                "sdate": start_date.isoformat(),
                "edate": end_date.isoformat(),
            },
            helper_module="akshare.stock.stock_allotment_cninfo",
            helper_name="_get_file_content_cninfo",
        )

    def _fetch(
        self,
        *,
        source_code: str,
        url: str,
        params: Mapping[str, str],
        helper_module: str,
        helper_name: str,
    ) -> CninfoCorporateActionHttpResponseV1:
        if len(source_code) != 6 or not source_code.isdigit():
            raise ValueError("CNINFO source code must contain six digits")
        try:
            import importlib
            import requests

            module = importlib.import_module(helper_module)
            py_mini_racer = getattr(module, "py_mini_racer")
            get_file_content = getattr(module, helper_name)
            js_code = py_mini_racer.MiniRacer()
            js_code.eval(get_file_content("cninfo.js"))
            encrypted_key = js_code.call("getResCode1")
            response = requests.post(
                url,
                params=params,
                headers={
                    "Accept": "application/json,*/*",
                    "Accept-Enckey": encrypted_key,
                    "Origin": "https://webapi.cninfo.com.cn",
                    "Referer": "https://webapi.cninfo.com.cn/",
                    "User-Agent": "WHAlphaResearch/1.0 CNINFO-evidence",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=self._timeout_seconds,
            )
        except Exception as exc:  # provider libraries expose unstable errors
            raise ProviderUnavailableError(
                CNINFO_CORPORATE_ACTION_PROVIDER_ID,
                "CNINFO corporate-action request failed",
            ) from exc
        body = bytes(response.content)
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ProviderDataError(
                CNINFO_CORPORATE_ACTION_PROVIDER_ID,
                "CNINFO corporate-action response exceeds its byte ceiling",
            )
        return CninfoCorporateActionHttpResponseV1(
            status=int(response.status_code),
            content_type=str(response.headers.get("Content-Type", "")),
            final_url=str(response.url),
            body=body,
        )


def capture_cninfo_corporate_actions(
    *,
    source_security_id: str,
    instrument_id: UUID,
    start_date: date,
    end_date: date,
    retrieved_at: datetime,
    fetcher: CninfoCorporateActionHttpFetcher,
) -> CapturedCninfoCorporateActionsV1:
    """Fetch and normalize one exact CNINFO response without persistence."""

    prefix, source_code = _source_identity(source_security_id)
    del prefix
    if end_date < start_date:
        raise ValueError("corporate-action range is reversed")
    response = fetcher.fetch_distribution(source_code=source_code)
    parsed_url = urlparse(response.final_url)
    if (
        response.status != 200
        or parsed_url.scheme != "https"
        or parsed_url.hostname != "webapi.cninfo.com.cn"
    ):
        raise ProviderUnavailableError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action response failed its transport boundary",
        )
    if "json" not in response.content_type.lower():
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action response is not JSON",
        )
    if not response.body or len(response.body) > _MAX_RESPONSE_BYTES:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action response byte size is invalid",
        )
    try:
        document = json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action response is malformed JSON",
        ) from exc
    if not isinstance(document, Mapping) or not isinstance(document.get("records"), list):
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action response schema differs",
        )
    raw_hash = hashlib.sha256(response.body).hexdigest()
    observations: list[ChinaAshareCorporateActionObservationV1] = []
    seen: set[date] = set()
    for raw_row in document["records"]:
        if not isinstance(raw_row, Mapping):
            raise ProviderDataError(
                CNINFO_CORPORATE_ACTION_PROVIDER_ID,
                "CNINFO corporate-action row is malformed",
            )
        ex_date = _required_date(raw_row.get("F020D"), field_name="F020D")
        if not start_date <= ex_date <= end_date:
            continue
        if ex_date in seen:
            raise ProviderDataError(
                CNINFO_CORPORATE_ACTION_PROVIDER_ID,
                "CNINFO corporate-action response has duplicate ex-dates",
            )
        seen.add(ex_date)
        cash = _optional_decimal(raw_row.get("F012N")) / Decimal("10")
        bonus = _optional_decimal(raw_row.get("F010N")) / Decimal("10")
        capitalization = _optional_decimal(raw_row.get("F011N")) / Decimal("10")
        action_type = _action_type(cash=cash, bonus=bonus, capitalization=capitalization)
        observations.append(
            build_corporate_action_observation(
                instrument_id=instrument_id,
                source_security_id=source_security_id,
                action_type=action_type,
                implementation_announcement_date=_required_date(
                    raw_row.get("F006D"), field_name="F006D"
                ),
                record_date=_required_date(raw_row.get("F018D"), field_name="F018D"),
                ex_date=ex_date,
                payment_date=_optional_date(raw_row.get("F023D"), field_name="F023D"),
                shares_arrival_date=_optional_date(
                    raw_row.get("F025D"), field_name="F025D"
                ),
                cash_dividend_per_share_cny=cash,
                bonus_share_ratio=bonus,
                capitalization_ratio=capitalization,
                action_description=_required_text(raw_row.get("F007V"), field_name="F007V"),
                report_period=_optional_text(raw_row.get("F001V")),
                source=CNINFO_CORPORATE_ACTION_PROVIDER_ID,
                source_retrieved_at=retrieved_at,
                raw_payload_sha256=raw_hash,
                quality_status=QualityStatus.WARNING,
                reason_codes=(
                    "implementation_terms_observed",
                    "independent_cross_source_pending",
                ),
                normalized_return_authorized=False,
            )
        )
    return CapturedCninfoCorporateActionsV1(
        source_kind=CninfoCorporateActionSourceKind.DISTRIBUTION,
        source_security_id=source_security_id,
        instrument_id=instrument_id,
        retrieved_at=retrieved_at,
        final_url=response.final_url,
        content_type=response.content_type,
        raw_bytes=response.body,
        observations=tuple(sorted(observations, key=lambda item: item.ex_date)),
    )


def capture_cninfo_rights_issues(
    *,
    source_security_id: str,
    instrument_id: UUID,
    start_date: date,
    end_date: date,
    retrieved_at: datetime,
    fetcher: CninfoCorporateActionHttpFetcher,
) -> CapturedCninfoCorporateActionsV1:
    """Fetch and normalize one exact CNINFO rights-issue response."""

    _, source_code = _source_identity(source_security_id)
    if end_date < start_date:
        raise ValueError("rights-issue range is reversed")
    response = fetcher.fetch_rights_issues(
        source_code=source_code,
        start_date=start_date,
        end_date=end_date,
    )
    parsed_url = urlparse(response.final_url)
    if (
        response.status != 200
        or parsed_url.scheme != "https"
        or parsed_url.hostname != "webapi.cninfo.com.cn"
    ):
        raise ProviderUnavailableError(
            CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
            "CNINFO rights-issue response failed its transport boundary",
        )
    if "json" not in response.content_type.lower() or not response.body:
        raise ProviderDataError(
            CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
            "CNINFO rights-issue response is not non-empty JSON",
        )
    try:
        document = json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderDataError(
            CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
            "CNINFO rights-issue response is malformed JSON",
        ) from exc
    if not isinstance(document, Mapping) or not isinstance(document.get("records"), list):
        raise ProviderDataError(
            CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
            "CNINFO rights-issue response schema differs",
        )
    raw_hash = hashlib.sha256(response.body).hexdigest()
    observations: list[ChinaAshareCorporateActionObservationV1] = []
    seen: set[date] = set()
    for raw_row in document["records"]:
        if not isinstance(raw_row, Mapping):
            raise ProviderDataError(
                CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
                "CNINFO rights-issue row is malformed",
            )
        row_code = str(raw_row.get("SECCODE") or "").strip()
        if row_code != source_code:
            raise ProviderDataError(
                CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
                "CNINFO rights-issue row security differs",
            )
        ex_date = _required_date(raw_row.get("F012D"), field_name="F012D")
        if not start_date <= ex_date <= end_date:
            raise ProviderDataError(
                CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
                "CNINFO rights-issue row falls outside requested interval",
            )
        if ex_date in seen:
            raise ProviderDataError(
                CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
                "CNINFO rights-issue response has duplicate ex-dates",
            )
        seen.add(ex_date)
        ratio = _optional_decimal(raw_row.get("F004N")) / Decimal("10")
        price = _optional_decimal(raw_row.get("F005N"))
        observations.append(
            build_corporate_action_observation(
                instrument_id=instrument_id,
                source_security_id=source_security_id,
                action_type="rights_issue",
                implementation_announcement_date=_required_date(
                    raw_row.get("DECLAREDATE"), field_name="DECLAREDATE"
                ),
                record_date=_required_date(raw_row.get("F011D"), field_name="F011D"),
                ex_date=ex_date,
                payment_date=None,
                shares_arrival_date=_optional_date(
                    raw_row.get("F038D"), field_name="F038D"
                ),
                cash_dividend_per_share_cny=Decimal("0"),
                bonus_share_ratio=Decimal("0"),
                capitalization_ratio=Decimal("0"),
                rights_issue_ratio=ratio,
                rights_issue_price_per_share_cny=price,
                action_description=f"rights_issue_ratio={ratio};price_cny={price}",
                report_period=None,
                source=CNINFO_RIGHTS_ISSUE_PROVIDER_ID,
                source_retrieved_at=retrieved_at,
                raw_payload_sha256=raw_hash,
                quality_status=QualityStatus.WARNING,
                reason_codes=(
                    "implementation_terms_observed",
                    "independent_cross_source_pending",
                ),
                normalized_return_authorized=False,
            )
        )
    return CapturedCninfoCorporateActionsV1(
        source_kind=CninfoCorporateActionSourceKind.RIGHTS_ISSUE,
        source_security_id=source_security_id,
        instrument_id=instrument_id,
        retrieved_at=retrieved_at,
        final_url=response.final_url,
        content_type=response.content_type,
        raw_bytes=response.body,
        observations=tuple(sorted(observations, key=lambda item: item.ex_date)),
    )


def _source_identity(value: str) -> tuple[str, str]:
    normalized = str(value).strip().lower()
    try:
        prefix, code = normalized.split(".", 1)
    except ValueError as exc:
        raise ValueError("source_security_id is malformed") from exc
    if prefix not in {"sh", "sz", "bj"} or len(code) != 6 or not code.isdigit():
        raise ValueError("source_security_id is malformed")
    return prefix, code


def _required_date(value: object, *, field_name: str) -> date:
    parsed = _optional_date(value, field_name=field_name)
    if parsed is None:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            f"CNINFO {field_name} is absent",
        )
    return parsed


def _optional_date(value: object, *, field_name: str) -> date | None:
    if value is None or str(value).strip() in {"", "None", "NaT", "nan"}:
        return None
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            f"CNINFO {field_name} is not an ISO date",
        ) from exc


def _optional_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, float) and math.isnan(value):
        return Decimal("0")
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan"}:
        return Decimal("0")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action amount is not decimal",
        ) from exc
    if not result.is_finite() or result < 0:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            "CNINFO corporate-action amount is invalid",
        )
    return result


def _required_text(value: object, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ProviderDataError(
            CNINFO_CORPORATE_ACTION_PROVIDER_ID,
            f"CNINFO {field_name} is absent",
        )
    return normalized


def _optional_text(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _action_type(*, cash: Decimal, bonus: Decimal, capitalization: Decimal) -> str:
    positive = sum(value > 0 for value in (cash, bonus, capitalization))
    if positive > 1:
        return "composite_distribution"
    if cash > 0:
        return "cash_dividend"
    if bonus > 0:
        return "stock_dividend"
    if capitalization > 0:
        return "capitalization"
    raise ProviderDataError(
        CNINFO_CORPORATE_ACTION_PROVIDER_ID,
        "CNINFO corporate-action row has no economic distribution",
    )
