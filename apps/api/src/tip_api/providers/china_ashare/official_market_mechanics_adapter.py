"""Bounded exact-byte capture for official A-share mechanics sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen

from tip_api.contracts.china_ashare.v1 import ChinaAshareOfficialSourceReferenceV1


_MAX_SOURCE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class OfficialMarketMechanicsHttpResponseV1:
    status: int
    content_type: str
    final_url: str
    body: bytes


@dataclass(frozen=True, slots=True)
class CapturedOfficialMarketMechanicsSourceV1:
    reference: ChinaAshareOfficialSourceReferenceV1
    raw_bytes: bytes


class OfficialMarketMechanicsHttpFetcher(Protocol):
    def fetch(self, *, url: str) -> OfficialMarketMechanicsHttpResponseV1: ...


class UrllibOfficialMarketMechanicsHttpFetcher:
    """Explicit fetcher whose construction performs no network access."""

    def __init__(self, *, timeout_seconds: float = 45.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("market mechanics fetch timeout is outside its safety range")
        self._timeout_seconds = timeout_seconds

    def fetch(self, *, url: str) -> OfficialMarketMechanicsHttpResponseV1:
        request = Request(
            url,
            headers={
                "User-Agent": "WHAlphaResearch/1.0 official-market-mechanics-evidence",
                "Accept": "text/html,application/xhtml+xml,application/pdf",
            },
        )
        with urlopen(request, timeout=self._timeout_seconds) as response:
            body = response.read(_MAX_SOURCE_BYTES + 1)
            if len(body) > _MAX_SOURCE_BYTES:
                raise ValueError("official market mechanics source exceeds its byte ceiling")
            return OfficialMarketMechanicsHttpResponseV1(
                status=response.status,
                content_type=response.headers.get_content_type(),
                final_url=response.geturl(),
                body=body,
            )


def capture_official_market_mechanics_source(
    *,
    reference: ChinaAshareOfficialSourceReferenceV1,
    fetcher: OfficialMarketMechanicsHttpFetcher,
) -> CapturedOfficialMarketMechanicsSourceV1:
    if reference.raw_sha256 is not None:
        raise ValueError("official source reference is already captured")
    response = fetcher.fetch(url=reference.source_url)
    if response.status != 200:
        raise ValueError("official market mechanics source did not return HTTP 200")
    content_type = response.content_type.lower()
    if content_type not in {"text/html", "application/pdf"}:
        raise ValueError("official market mechanics source content type is unsupported")
    if not response.body or len(response.body) > _MAX_SOURCE_BYTES:
        raise ValueError("official market mechanics source byte size is invalid")
    if content_type == "text/html" and not _looks_like_html(response.body):
        raise ValueError("official market mechanics HTML payload is malformed")
    if content_type == "application/pdf" and not response.body.startswith(b"%PDF"):
        raise ValueError("official market mechanics PDF payload is malformed")
    captured_reference = ChinaAshareOfficialSourceReferenceV1.model_validate(
        {
            **reference.model_dump(mode="python"),
            "final_url": response.final_url,
            "content_type": content_type,
            "raw_byte_size": len(response.body),
            "raw_sha256": hashlib.sha256(response.body).hexdigest(),
        }
    )
    return CapturedOfficialMarketMechanicsSourceV1(
        reference=captured_reference,
        raw_bytes=response.body,
    )


def _looks_like_html(payload: bytes) -> bool:
    sample = payload[:8192].lower()
    return b"<html" in sample or b"<!doctype html" in sample
