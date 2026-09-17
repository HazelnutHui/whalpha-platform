from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

import pytest

from tip_api.contracts.china_ashare.v1 import ChinaAshareOfficialSourceReferenceV1
from tip_api.providers.china_ashare.official_market_mechanics_adapter import (
    OfficialMarketMechanicsHttpResponseV1,
    capture_official_market_mechanics_source,
)


class _Fetcher:
    def __init__(self, response: OfficialMarketMechanicsHttpResponseV1) -> None:
        self.response = response

    def fetch(self, *, url: str) -> OfficialMarketMechanicsHttpResponseV1:
        assert url == "https://www.sse.com.cn/example.html"
        return self.response


def _reference() -> ChinaAshareOfficialSourceReferenceV1:
    return ChinaAshareOfficialSourceReferenceV1(
        source_id="test-source",
        source_url="https://www.sse.com.cn/example.html",
        publisher="上海证券交易所",
        published_date=date(2026, 4, 24),
        evidence_purpose="测试交易规则",
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )


def test_official_market_mechanics_adapter_retains_exact_bytes() -> None:
    raw = b"<!doctype html><html><body>rule</body></html>"
    captured = capture_official_market_mechanics_source(
        reference=_reference(),
        fetcher=_Fetcher(
            OfficialMarketMechanicsHttpResponseV1(
                status=200,
                content_type="text/html",
                final_url="https://www.sse.com.cn/example.html",
                body=raw,
            )
        ),
    )

    assert captured.raw_bytes == raw
    assert captured.reference.raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert captured.reference.raw_byte_size == len(raw)


def test_official_market_mechanics_adapter_rejects_login_or_json_payload() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        capture_official_market_mechanics_source(
            reference=_reference(),
            fetcher=_Fetcher(
                OfficialMarketMechanicsHttpResponseV1(
                    status=200,
                    content_type="application/json",
                    final_url="https://www.sse.com.cn/example.html",
                    body=b"{}",
                )
            ),
        )

    with pytest.raises(ValueError, match="malformed"):
        capture_official_market_mechanics_source(
            reference=_reference(),
            fetcher=_Fetcher(
                OfficialMarketMechanicsHttpResponseV1(
                    status=200,
                    content_type="text/html",
                    final_url="https://www.sse.com.cn/example.html",
                    body=b"login required",
                )
            ),
        )
