from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from tip_api.providers.china_ashare.cninfo_corporate_action_adapter import (
    CNINFO_CORPORATE_ACTION_URL,
    CNINFO_RIGHTS_ISSUE_URL,
    CninfoCorporateActionHttpResponseV1,
    capture_cninfo_corporate_actions,
    capture_cninfo_rights_issues,
)


NOW = datetime(2026, 9, 17, tzinfo=UTC)
INSTRUMENT_ID = UUID("00000000-0000-0000-0000-000000600519")


class _Fetcher:
    def fetch_distribution(self, *, source_code: str):
        assert source_code == "600519"
        body = json.dumps(
            {
                "records": [
                    {
                        "F020D": "2023-12-20 00:00:00",
                        "F018D": "2023-12-19 00:00:00",
                        "F006D": "2023-12-14 00:00:00",
                        "F023D": "2023-12-20 00:00:00",
                        "F025D": None,
                        "F012N": 191.06,
                        "F010N": 0,
                        "F011N": 0,
                        "F007V": "10派191.06元（含税）",
                        "F001V": "2023三季度",
                    }
                ]
            },
            separators=(",", ":"),
        ).encode()
        return CninfoCorporateActionHttpResponseV1(
            status=200,
            content_type="application/json;charset=utf-8",
            final_url=f"{CNINFO_CORPORATE_ACTION_URL}?scode=600519",
            body=body,
        )

    def fetch_rights_issues(self, *, source_code: str, start_date: date, end_date: date):
        assert source_code == "600519"
        assert start_date == date(2021, 9, 16)
        assert end_date == date(2026, 9, 16)
        return CninfoCorporateActionHttpResponseV1(
            status=200,
            content_type="application/json",
            final_url=f"{CNINFO_RIGHTS_ISSUE_URL}?scode=600519",
            body=b'{"records":[]}',
        )


def test_cninfo_distribution_retains_raw_and_normalizes_per_share_terms() -> None:
    captured = capture_cninfo_corporate_actions(
        source_security_id="sh.600519",
        instrument_id=INSTRUMENT_ID,
        start_date=date(2021, 9, 16),
        end_date=date(2026, 9, 16),
        retrieved_at=NOW,
        fetcher=_Fetcher(),
    )

    assert captured.raw_bytes.startswith(b'{"records"')
    assert len(captured.observations) == 1
    action = captured.observations[0]
    assert action.ex_date == date(2023, 12, 20)
    assert action.cash_dividend_per_share_cny == Decimal("19.106")
    assert action.normalized_return_authorized is False


def test_cninfo_empty_rights_issue_response_is_retained_evidence() -> None:
    captured = capture_cninfo_rights_issues(
        source_security_id="sh.600519",
        instrument_id=INSTRUMENT_ID,
        start_date=date(2021, 9, 16),
        end_date=date(2026, 9, 16),
        retrieved_at=NOW,
        fetcher=_Fetcher(),
    )

    assert captured.raw_bytes == b'{"records":[]}'
    assert captured.observations == ()
