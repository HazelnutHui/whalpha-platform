from __future__ import annotations

import json
from datetime import UTC, date, datetime
from io import BytesIO
from types import SimpleNamespace

import pandas as pd

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareSecurityForm,
    build_research_instrument_identity,
)
from tip_api.providers.china_ashare.official_identity_evidence_adapter import (
    CapturedOfficialIdentityArtifactV1,
    OfficialIdentityArtifactKind,
)
from tip_api.services.china_ashare_identity_lifecycle import (
    validate_official_identity_artifacts_for_pilot,
)


NOW = datetime(2026, 9, 17, tzinfo=UTC)


def test_research_identity_is_stable_for_occurrence_and_changes_on_relisting() -> None:
    first = _identity(date(1997, 4, 18))
    replay = _identity(date(1997, 4, 18))
    relisted = _identity(date(2027, 1, 4))

    assert first.instrument_id == replay.instrument_id
    assert first.logical_fingerprint == replay.logical_fingerprint
    assert relisted.instrument_id != first.instrument_id
    assert first.ticker_is_permanent_key is False


def test_official_raw_identity_validation_normalizes_compact_sse_date() -> None:
    reference = SimpleNamespace(
        captured=SimpleNamespace(
            official_current_instruments=(
                SimpleNamespace(
                    source_security_id="sh.600053",
                    name="*ST九鼎",
                    list_date=date(1997, 4, 18),
                    board=ChinaAshareBoard.SSE_MAIN,
                ),
                SimpleNamespace(
                    source_security_id="sz.000001",
                    name="平安银行",
                    list_date=date(1991, 4, 3),
                    board=ChinaAshareBoard.SZSE_MAIN,
                ),
            )
        )
    )
    sources = (
        _artifact(
            OfficialIdentityArtifactKind.SSE_MAIN_CURRENT,
            ChinaAshareExchange.SSE,
            _json_bytes(
                {
                    "result": [
                        {
                            "A_STOCK_CODE": "600053",
                            "SEC_NAME_CN": "*ST九鼎",
                            "LIST_DATE": "19970418",
                        }
                    ]
                }
            ),
        ),
        _artifact(
            OfficialIdentityArtifactKind.SSE_STAR_CURRENT,
            ChinaAshareExchange.SSE,
            _json_bytes({"result": []}),
        ),
        _artifact(
            OfficialIdentityArtifactKind.SZSE_A_CURRENT,
            ChinaAshareExchange.SZSE,
            _xlsx_bytes(
                pd.DataFrame(
                    [
                        {
                            "板块": "主板",
                            "A股代码": "000001",
                            "A股简称": "平安银行",
                            "A股上市日期": datetime(1991, 4, 3),
                        }
                    ]
                )
            ),
        ),
        _artifact(
            OfficialIdentityArtifactKind.SSE_DELIST,
            ChinaAshareExchange.SSE,
            _json_bytes({"result": []}),
        ),
        _artifact(
            OfficialIdentityArtifactKind.SZSE_DELIST,
            ChinaAshareExchange.SZSE,
            _xlsx_bytes(pd.DataFrame({"证券代码": []})),
        ),
    )

    assert validate_official_identity_artifacts_for_pilot(
        reference_package=reference,
        captured_sources=sources,
    )


def _identity(listing_date: date):
    return build_research_instrument_identity(
        source_security_id="sh.600053",
        display_ticker="600053.SH",
        current_name="*ST九鼎",
        exchange=ChinaAshareExchange.SSE,
        board=ChinaAshareBoard.SSE_MAIN,
        security_form=ChinaAshareSecurityForm.COMMON_STOCK,
        listing_date=listing_date,
        alias_valid_from=listing_date,
        official_observation_fingerprint="a" * 64,
        baostock_observation_fingerprint="b" * 64,
        pilot_decision_fingerprint="c" * 64,
        append_only=True,
        ticker_is_permanent_key=False,
        reason_codes=("listed_occurrence_keyed",),
        canonical_apply_authorized=False,
    )


def _artifact(kind, exchange, raw_bytes):
    return CapturedOfficialIdentityArtifactV1(
        artifact_kind=kind,
        exchange=exchange,
        retrieved_at=NOW,
        final_url=(
            "https://query.sse.com.cn/source"
            if exchange is ChinaAshareExchange.SSE
            else "https://www.szse.cn/source"
        ),
        content_type=(
            "application/json"
            if kind in {
                OfficialIdentityArtifactKind.SSE_MAIN_CURRENT,
                OfficialIdentityArtifactKind.SSE_STAR_CURRENT,
                OfficialIdentityArtifactKind.SSE_DELIST,
            }
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        raw_bytes=raw_bytes,
    )


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode()


def _xlsx_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_excel(buffer, index=False)
    return buffer.getvalue()
