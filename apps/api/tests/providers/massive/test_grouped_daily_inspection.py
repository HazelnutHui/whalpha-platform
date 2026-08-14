"""Tests for safe Massive Grouped Daily inspection."""

from __future__ import annotations

import socket
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.grouped_daily_inspection import (
    GROUPED_DAILY_ENDPOINT_TEMPLATE,
    MappingIdentityResolver,
    inspect_grouped_daily_payload,
    inspect_grouped_daily_session,
    main,
    parse_session_date,
)

SESSION = date(2026, 8, 13)
ENDPOINT = GROUPED_DAILY_ENDPOINT_TEMPLATE.format(session_date=SESSION.isoformat())
INGESTED_AT = datetime(2026, 8, 14, 1, 0, tzinfo=UTC)
TESTA_ID = UUID("00000000-0000-4000-8000-000000000001")
TESTB_ID = UUID("00000000-0000-4000-8000-000000000002")
SENTINEL_SECRET = "test-secret-must-never-appear"


def session_timestamp_ms(session_date: date = SESSION) -> int:
    dt = datetime(session_date.year, session_date.month, session_date.day, 13, 30, tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def record(ticker: str = "TESTA", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "T": ticker,
        "o": 10.0,
        "h": 10.5,
        "l": 9.75,
        "c": 10.25,
        "v": 1000,
        "vw": 10.1,
        "n": 10,
        "t": session_timestamp_ms(),
    }
    payload.update(overrides)
    return payload


def payload(*records: dict[str, object], results_count: int | None = None) -> dict[str, object]:
    data: dict[str, object] = {"status": "OK", "results": list(records)}
    data["resultsCount"] = len(records) if results_count is None else results_count
    return data


class FakeTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object], bool]] = []

    def get_json(self, path, *, params, api_key, timeout_seconds, base_url):
        self.calls.append((path, dict(params), bool(api_key.get_secret_value())))
        return self.response


def config() -> MassiveProviderConfig:
    return MassiveProviderConfig(api_key=SecretStr(SENTINEL_SECRET))


def test_cli_requires_session_date(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_cli_rejects_bad_date(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--session-date", "not-a-date"]) == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_cli_rejects_unauthorized_date(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--session-date", "2026-08-12"]) == 2
    assert "not-authorized" in capsys.readouterr().err


def test_parse_session_date_rejects_future_date() -> None:
    with pytest.raises(ValueError, match="completed"):
        parse_session_date("2026-08-14", today=date(2026, 8, 14))


def test_inspection_sends_adjusted_false_and_one_request() -> None:
    transport = FakeTransport(payload(record()))
    result = inspect_grouped_daily_session(config=config(), transport=transport, session_date=SESSION, ingested_at=INGESTED_AT)
    assert result.request_count == 1
    assert result.adjusted is False
    assert transport.calls == [(ENDPOINT, {"adjusted": False}, True)]


def test_valid_mocked_grouped_daily_inspection_unresolved_identity() -> None:
    result = inspect_grouped_daily_payload(payload(record("TESTA"), record("TESTB")), endpoint=ENDPOINT, session_date=SESSION, ingested_at=INGESTED_AT)
    assert result.raw_result_count == 2
    assert result.unique_ticker_count == 2
    assert result.valid_ohlcv_count == 2
    assert result.identity_resolved_count == 0
    assert result.identity_unresolved_count == 2
    assert result.canonical_mapping_ready_count == 0
    assert result.publish_ready is False
    assert result.status == "identity-resolution-blocked"


def test_empty_results() -> None:
    result = inspect_grouped_daily_payload(payload(), endpoint=ENDPOINT, session_date=SESSION)
    assert result.raw_result_count == 0
    assert result.status == "empty-results"
    assert result.publish_ready is False


def test_malformed_root_and_results() -> None:
    result = inspect_grouped_daily_payload({"status": "OK", "results": "bad"}, endpoint=ENDPOINT, session_date=SESSION)
    assert result.status == "malformed-results"
    assert result.raw_result_count == 0


def test_malformed_results_item() -> None:
    result = inspect_grouped_daily_payload({"status": "OK", "results": ["bad"], "resultsCount": 1}, endpoint=ENDPOINT, session_date=SESSION)
    assert result.invalid_record_count == 1


def test_results_count_mismatch() -> None:
    result = inspect_grouped_daily_payload(payload(record(), results_count=2), endpoint=ENDPOINT, session_date=SESSION)
    assert result.results_count_mismatch is True
    assert result.status == "results-count-mismatch"


def test_duplicate_ticker() -> None:
    result = inspect_grouped_daily_payload(payload(record("TESTA"), record("testa")), endpoint=ENDPOINT, session_date=SESSION)
    assert result.unique_ticker_count == 1
    assert result.duplicate_ticker_count == 1


@pytest.mark.parametrize(
    "field, stat",
    [("o", "missing_open_count"), ("h", "missing_high_count"), ("l", "missing_low_count"), ("c", "missing_close_count"), ("v", "missing_volume_count")],
)
def test_missing_ohlcv(field: str, stat: str) -> None:
    item = record()
    item.pop(field)
    result = inspect_grouped_daily_payload(payload(item), endpoint=ENDPOINT, session_date=SESSION)
    assert getattr(result, stat) == 1
    assert result.invalid_record_count == 1


def test_integral_float_volume_and_trade_count_are_accepted() -> None:
    result = inspect_grouped_daily_payload(payload(record(v=1000.0, n=10.0)), endpoint=ENDPOINT, session_date=SESSION)
    assert result.numeric_conversion_failure_count == 0
    assert result.valid_ohlcv_count == 1


def test_fractional_volume_is_rejected() -> None:
    result = inspect_grouped_daily_payload(payload(record(v=1000.5)), endpoint=ENDPOINT, session_date=SESSION)
    assert result.numeric_conversion_failure_count == 1
    assert result.invalid_record_count == 1


def test_bad_numeric_conversion() -> None:
    result = inspect_grouped_daily_payload(payload(record(o="bad")), endpoint=ENDPOINT, session_date=SESSION)
    assert result.numeric_conversion_failure_count == 1
    assert result.invalid_record_count == 1


def test_nonpositive_prices() -> None:
    result = inspect_grouped_daily_payload(payload(record(o=0)), endpoint=ENDPOINT, session_date=SESSION)
    assert result.nonpositive_price_count == 1
    assert result.invalid_record_count == 1


def test_ohlc_inconsistency() -> None:
    result = inspect_grouped_daily_payload(payload(record(h=9.0)), endpoint=ENDPOINT, session_date=SESSION)
    assert result.ohlc_consistency_failure_count == 1
    assert result.invalid_record_count == 1


def test_timestamp_mismatch() -> None:
    wrong = int(datetime(2026, 8, 12, 13, 30, tzinfo=UTC).timestamp() * 1000)
    result = inspect_grouped_daily_payload(payload(record(t=wrong)), endpoint=ENDPOINT, session_date=SESSION)
    assert result.timestamp_session_mismatch_count == 1
    assert result.invalid_record_count == 1


def test_zero_volume() -> None:
    result = inspect_grouped_daily_payload(payload(record(v=0)), endpoint=ENDPOINT, session_date=SESSION)
    assert result.zero_volume_count == 1
    assert result.valid_ohlcv_count == 1


def test_missing_optional_vwap_and_trade_count() -> None:
    item = record()
    item.pop("vw")
    item.pop("n")
    result = inspect_grouped_daily_payload(payload(item), endpoint=ENDPOINT, session_date=SESSION)
    assert result.missing_vwap_count == 1
    assert result.missing_trade_count == 1
    assert result.valid_ohlcv_count == 1


def test_partially_resolved_identity_and_canonical_mapping_ready() -> None:
    resolver = MappingIdentityResolver({"TESTA": TESTA_ID})
    result = inspect_grouped_daily_payload(
        payload(record("TESTA"), record("TESTB")),
        endpoint=ENDPOINT,
        session_date=SESSION,
        identity_resolver=resolver,
        ingested_at=INGESTED_AT,
    )
    assert result.identity_resolved_count == 1
    assert result.identity_unresolved_count == 1
    assert result.canonical_mapping_ready_count == 1
    assert result.canonical_mapping_failed_count == 0
    assert result.publish_ready is False


def test_canonical_validation_failure() -> None:
    resolver = MappingIdentityResolver({"TESTA": TESTA_ID})
    result = inspect_grouped_daily_payload(
        payload(record("TESTA", vw=-1)),
        endpoint=ENDPOINT,
        session_date=SESSION,
        identity_resolver=resolver,
        ingested_at=INGESTED_AT,
    )
    assert result.identity_resolved_count == 1
    assert result.canonical_mapping_ready_count == 0
    assert result.canonical_mapping_failed_count == 1


def test_publish_ready_always_false_even_when_resolved() -> None:
    resolver = MappingIdentityResolver({"TESTA": TESTA_ID})
    result = inspect_grouped_daily_payload(payload(record("TESTA")), endpoint=ENDPOINT, session_date=SESSION, identity_resolver=resolver, ingested_at=INGESTED_AT)
    assert result.publish_ready is False


def test_safe_lines_do_not_include_secret() -> None:
    result = inspect_grouped_daily_payload(payload(record()), endpoint=ENDPOINT, session_date=SESSION)
    assert SENTINEL_SECRET not in "\\n".join(result.safe_lines())


def test_no_output_artifact(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())
    inspect_grouped_daily_payload(payload(record()), endpoint=ENDPOINT, session_date=SESSION)
    assert set(tmp_path.iterdir()) == before


def test_no_network_in_payload_inspection(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", fail_socket)
    result = inspect_grouped_daily_payload(payload(record()), endpoint=ENDPOINT, session_date=SESSION)
    assert result.raw_result_count == 1


def test_no_retry_after_transport_error() -> None:
    class FailingTransport:
        def __init__(self) -> None:
            self.calls = 0
        def get_json(self, *args, **kwargs):
            self.calls += 1
            raise RuntimeError("transport failed")

    transport = FailingTransport()
    with pytest.raises(RuntimeError):
        inspect_grouped_daily_session(config=config(), transport=transport, session_date=SESSION)
    assert transport.calls == 1


def test_repository_publish_never_called_by_inspection() -> None:
    source = Path("apps/api/src/tip_api/providers/massive/grouped_daily_inspection.py").read_text()
    assert "publish_session" not in source
    assert "ParquetEodPriceBarRepository" not in source
