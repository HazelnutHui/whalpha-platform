"""Exact official SSE/SZSE source capture for identity and lifecycle review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Mapping, Protocol
from urllib.parse import urlparse

from tip_api.contracts.china_ashare.v1.foundation import ChinaAshareExchange
from tip_api.providers.market_data import ProviderDataError, ProviderUnavailableError


OFFICIAL_IDENTITY_PROVIDER_ID = "china_ashare_official_identity_sources"
_SSE_CURRENT_URL = "https://query.sse.com.cn/sseQuery/commonQuery.do"
_SSE_DELIST_URL = "https://query.sse.com.cn/commonQuery.do"
_SZSE_REPORT_URL = "https://www.szse.cn/api/report/ShowReport"
_MAXIMUM_BYTES = 16 * 1024 * 1024


class OfficialIdentityArtifactKind(StrEnum):
    SSE_MAIN_CURRENT = "sse_main_current"
    SSE_STAR_CURRENT = "sse_star_current"
    SZSE_A_CURRENT = "szse_a_current"
    SSE_DELIST = "sse_delist"
    SZSE_DELIST = "szse_delist"


@dataclass(frozen=True, slots=True)
class OfficialIdentityHttpResponseV1:
    status: int
    content_type: str
    final_url: str
    body: bytes


@dataclass(frozen=True, slots=True)
class CapturedOfficialIdentityArtifactV1:
    artifact_kind: OfficialIdentityArtifactKind
    exchange: ChinaAshareExchange
    retrieved_at: datetime
    final_url: str
    content_type: str
    raw_bytes: bytes


class OfficialIdentityHttpFetcher(Protocol):
    def fetch(
        self,
        *,
        url: str,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> OfficialIdentityHttpResponseV1: ...


class RequestsOfficialIdentityHttpFetcher:
    """Explicit bounded requests transport; construction performs no I/O."""

    def __init__(self, *, timeout_seconds: float = 45.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("official identity timeout is outside safety range")
        self._timeout_seconds = timeout_seconds

    def fetch(
        self,
        *,
        url: str,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> OfficialIdentityHttpResponseV1:
        try:
            import requests

            response = requests.get(
                url,
                params=dict(params),
                headers=dict(headers),
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            raise ProviderUnavailableError(
                OFFICIAL_IDENTITY_PROVIDER_ID,
                "official identity source request failed",
            ) from exc
        body = bytes(response.content)
        if not body or len(body) > _MAXIMUM_BYTES:
            raise ProviderDataError(
                OFFICIAL_IDENTITY_PROVIDER_ID,
                "official identity source response size is invalid",
            )
        return OfficialIdentityHttpResponseV1(
            status=int(response.status_code),
            content_type=str(response.headers.get("Content-Type", "")),
            final_url=str(response.url),
            body=body,
        )


def capture_official_identity_sources(
    *,
    retrieved_at: datetime,
    fetcher: OfficialIdentityHttpFetcher | None = None,
) -> tuple[CapturedOfficialIdentityArtifactV1, ...]:
    active_fetcher = fetcher or RequestsOfficialIdentityHttpFetcher()
    sse_headers = {
        "Referer": "https://www.sse.com.cn/assortment/stock/list/share/",
        "User-Agent": "WHAlphaResearch/1.0 official-identity-evidence",
    }
    common_sse = {
        "REG_PROVINCE": "",
        "CSRC_CODE": "",
        "STOCK_CODE": "",
        "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
        "type": "inParams",
        "isPagination": "true",
        "pageHelp.cacheSize": "1",
        "pageHelp.beginPage": "1",
        "pageHelp.pageNo": "1",
        "pageHelp.endPage": "1",
    }
    specs = (
        (
            OfficialIdentityArtifactKind.SSE_MAIN_CURRENT,
            ChinaAshareExchange.SSE,
            _SSE_CURRENT_URL,
            {
                **common_sse,
                "STOCK_TYPE": "1",
                "COMPANY_STATUS": "2,4,5,7,8",
                "pageHelp.pageSize": "10000",
            },
            sse_headers,
            "json",
        ),
        (
            OfficialIdentityArtifactKind.SSE_STAR_CURRENT,
            ChinaAshareExchange.SSE,
            _SSE_CURRENT_URL,
            {
                **common_sse,
                "STOCK_TYPE": "8",
                "COMPANY_STATUS": "2,4,5,7,8",
                "pageHelp.pageSize": "10000",
            },
            sse_headers,
            "json",
        ),
        (
            OfficialIdentityArtifactKind.SZSE_A_CURRENT,
            ChinaAshareExchange.SZSE,
            _SZSE_REPORT_URL,
            {
                "SHOWTYPE": "xlsx",
                "CATALOGID": "1110",
                "TABKEY": "tab1",
                "random": "0.6935816432433362",
            },
            {},
            "spreadsheet",
        ),
        (
            OfficialIdentityArtifactKind.SSE_DELIST,
            ChinaAshareExchange.SSE,
            _SSE_DELIST_URL,
            {
                **common_sse,
                "STOCK_TYPE": "1,2,8",
                "COMPANY_STATUS": "3",
                "pageHelp.pageSize": "500",
            },
            sse_headers,
            "json",
        ),
        (
            OfficialIdentityArtifactKind.SZSE_DELIST,
            ChinaAshareExchange.SZSE,
            _SZSE_REPORT_URL,
            {
                "SHOWTYPE": "xlsx",
                "CATALOGID": "1793_ssgs",
                "TABKEY": "tab2",
                "random": "0.6935816432433362",
            },
            {},
            "spreadsheet",
        ),
    )
    captured = []
    for kind, exchange, url, params, headers, expected_type in specs:
        response = active_fetcher.fetch(url=url, params=params, headers=headers)
        parsed = urlparse(response.final_url)
        if (
            response.status != 200
            or parsed.scheme != "https"
            or parsed.hostname not in {"query.sse.com.cn", "www.szse.cn"}
        ):
            raise ProviderUnavailableError(
                OFFICIAL_IDENTITY_PROVIDER_ID,
                "official identity response failed its transport boundary",
            )
        content_type = response.content_type.lower()
        if expected_type == "json" and "json" not in content_type:
            raise ProviderDataError(
                OFFICIAL_IDENTITY_PROVIDER_ID,
                "official SSE identity response is not JSON",
            )
        if expected_type == "spreadsheet" and not any(
            marker in content_type
            for marker in ("spreadsheet", "excel", "octet-stream", "application/zip")
        ):
            raise ProviderDataError(
                OFFICIAL_IDENTITY_PROVIDER_ID,
                "official SZSE identity response is not a spreadsheet",
            )
        captured.append(
            CapturedOfficialIdentityArtifactV1(
                artifact_kind=kind,
                exchange=exchange,
                retrieved_at=retrieved_at,
                final_url=response.final_url,
                content_type=response.content_type,
                raw_bytes=response.body,
            )
        )
    return tuple(captured)
