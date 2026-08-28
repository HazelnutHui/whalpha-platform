from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionType,
    KnowledgeTimeStatus,
    ResolutionStatus,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.providers.massive import map_massive_corporate_action_payloads

OBSERVED_AT = datetime(2026, 8, 28, 4, 0, tzinfo=UTC)
INGESTED_AT = OBSERVED_AT + timedelta(minutes=2)
AAA_ID = UUID("11111111-1111-4111-8111-111111111111")
BBB_ID = UUID("22222222-2222-4222-8222-222222222222")
CCC_ID = UUID("33333333-3333-4333-8333-333333333333")
OTHER_ID = UUID("44444444-4444-4444-8444-444444444444")
FIXTURE_PATH = (
    Path(__file__).parents[2]
    / "fixtures"
    / "massive"
    / "corporate_actions_v1.json"
)


def load_fixture() -> dict[str, object]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def split_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "adjustment_type": "forward_split",
        "execution_date": "2026-08-20",
        "historical_adjustment_factor": 0.5,
        "id": "split-test",
        "split_from": 1,
        "split_to": 2,
        "ticker": "AAA",
    }
    payload.update(overrides)
    return payload


def dividend_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "cash_amount": 0.25,
        "currency": "USD",
        "declaration_date": "2026-08-01",
        "distribution_type": "recurring",
        "ex_dividend_date": "2026-08-15",
        "frequency": 4,
        "historical_adjustment_factor": 0.9975,
        "id": "dividend-test",
        "pay_date": "2026-08-22",
        "record_date": "2026-08-15",
        "split_adjusted_cash_amount": 0.25,
        "ticker": "AAA",
    }
    payload.update(overrides)
    return payload


def map_batch(
    *,
    splits: list[object] | None = None,
    dividends: list[object] | None = None,
    resolutions: dict[str, UUID | tuple[UUID, ...]] | None = None,
):
    return map_massive_corporate_action_payloads(
        split_payloads=splits or [],  # type: ignore[arg-type]
        dividend_payloads=dividends or [],  # type: ignore[arg-type]
        ticker_resolutions=resolutions or {"AAA": AAA_ID},
        first_observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )


def test_saved_synthetic_current_endpoint_shapes_map_without_network() -> None:
    fixture = load_fixture()
    batch = map_massive_corporate_action_payloads(
        split_payloads=fixture["splits"],  # type: ignore[arg-type]
        dividend_payloads=fixture["dividends"],  # type: ignore[arg-type]
        ticker_resolutions={"AAA": AAA_ID, "BBB": BBB_ID, "CCC": CCC_ID},
        first_observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )

    assert batch.input_count == 4
    assert batch.accepted_record_count == 4
    assert batch.quarantined_record_count == 0
    assert batch.quarantined_without_record_count == 0
    assert batch.issues == ()

    by_id = {record.source_action_id: record for record in batch.records}
    forward = by_id["synthetic-split-forward-aaa"]
    reverse = by_id["synthetic-split-reverse-bbb"]
    stock_dividend = by_id["synthetic-stock-dividend-ccc"]
    dividend = by_id["synthetic-dividend-aaa"]

    assert forward.action_type is CorporateActionType.STOCK_SPLIT
    assert forward.schema_version == "1.1"
    assert forward.split_ratio_from == Decimal("1")
    assert forward.split_ratio_to == Decimal("4")
    assert forward.provider_historical_adjustment_factor == Decimal("0.25")
    assert reverse.action_type is CorporateActionType.REVERSE_SPLIT
    assert stock_dividend.action_type is CorporateActionType.STOCK_DIVIDEND
    assert stock_dividend.split_ratio_to == Decimal("1.05")
    assert dividend.action_type is CorporateActionType.CASH_DIVIDEND
    assert dividend.cash_amount == Decimal("0.35")
    assert dividend.provider_split_adjusted_cash_amount == Decimal("0.35")
    assert dividend.distribution_type == "recurring"
    assert dividend.frequency == 4

    assert all(
        record.knowledge_time_status is KnowledgeTimeStatus.FIRST_OBSERVED_ONLY
        and record.source_available_at is None
        and record.first_observed_at == OBSERVED_AT
        and record.ingested_at == INGESTED_AT
        for record in batch.records
    )


def test_mapped_fixture_round_trips_through_temporary_parquet(tmp_path) -> None:
    fixture = load_fixture()
    batch = map_massive_corporate_action_payloads(
        split_payloads=fixture["splits"],  # type: ignore[arg-type]
        dividend_payloads=fixture["dividends"],  # type: ignore[arg-type]
        ticker_resolutions={"AAA": AAA_ID, "BBB": BBB_ID, "CCC": CCC_ID},
        first_observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )
    repository = ParquetHistoricalResearchRepository(tmp_path, created_at=INGESTED_AT)
    result = repository.publish_corporate_action_observations(
        batch.records,
        provider_id="massive_stocks_basic",
        event_year=2026,
    )

    reread = repository.read_corporate_action_observations(result.partition_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert reread == batch.records
    assert result.record_count == 4
    assert manifest["schema_version"] == "1.1"


def test_resolution_is_point_in_time_and_ambiguity_is_quarantined() -> None:
    batch = map_batch(
        splits=[
            split_payload(id="resolved", ticker="aaa"),
            split_payload(id="ambiguous", ticker="BBB"),
            split_payload(id="unresolved", ticker="CCC"),
        ],
        resolutions={"AAA": AAA_ID, "BBB": (BBB_ID, OTHER_ID)},
    )
    by_id = {record.source_action_id: record for record in batch.records}

    assert by_id["resolved"].instrument_resolution_status is ResolutionStatus.RESOLVED
    assert by_id["resolved"].instrument_id == AAA_ID
    assert by_id["resolved"].record_status is CorporateActionRecordStatus.ACTIVE
    assert by_id["ambiguous"].instrument_resolution_status is ResolutionStatus.AMBIGUOUS
    assert by_id["ambiguous"].instrument_id is None
    assert "ambiguous_ticker_resolution" in by_id["ambiguous"].quality_flags
    assert by_id["unresolved"].instrument_resolution_status is ResolutionStatus.UNRESOLVED
    assert "unresolved_ticker" in by_id["unresolved"].quality_flags
    assert batch.accepted_record_count == 1
    assert batch.quarantined_record_count == 2


def test_missing_provider_id_uses_deterministic_quarantined_identifier() -> None:
    first = map_batch(splits=[split_payload(id=None, ignored_secret="do-not-retain")])
    second = map_batch(splits=[split_payload(id=None, ignored_secret="different")])

    record = first.records[0]
    assert record.source_action_id == second.records[0].source_action_id
    assert record.source_action_id.startswith("synthetic-AAA-2026-08-20-")
    assert record.record_status is CorporateActionRecordStatus.QUARANTINED
    assert record.quality_status is QualityStatus.PENDING_REVIEW
    assert "provider_action_id_missing" in record.quality_flags
    assert "do-not-retain" not in repr(first)


def test_incomplete_but_anchored_rows_are_preserved_as_quarantine() -> None:
    batch = map_batch(
        splits=[split_payload(id="split-incomplete", split_to=None)],
        dividends=[
            dividend_payload(
                id="dividend-incomplete",
                cash_amount=None,
                currency=None,
            )
        ],
    )
    by_id = {record.source_action_id: record for record in batch.records}

    assert by_id["split-incomplete"].split_ratio_to is None
    assert "missing_split_to" in by_id["split-incomplete"].quality_flags
    assert by_id["dividend-incomplete"].cash_amount is None
    assert by_id["dividend-incomplete"].currency is None
    assert "missing_cash_amount" in by_id["dividend-incomplete"].quality_flags
    assert "missing_currency" in by_id["dividend-incomplete"].quality_flags
    assert batch.quarantined_record_count == 2


def test_direction_conflicts_and_invalid_optional_fields_do_not_pass_as_valid() -> None:
    batch = map_batch(
        splits=[split_payload(id="direction", split_from=2, split_to=1)],
        dividends=[
            dividend_payload(
                id="optional-invalid",
                declaration_date="not-a-date",
                currency="USDX",
                distribution_type="unsupported",
                frequency=2.5,
                historical_adjustment_factor="not-a-number",
            )
        ],
    )
    by_id = {record.source_action_id: record for record in batch.records}

    assert "split_direction_conflict" in by_id["direction"].quality_flags
    optional = by_id["optional-invalid"]
    assert optional.announcement_date is None
    assert optional.frequency is None
    assert optional.provider_historical_adjustment_factor is None
    assert {
        "invalid_declaration_date",
        "invalid_currency",
        "invalid_distribution_type",
        "invalid_frequency",
        "invalid_historical_adjustment_factor",
    }.issubset(optional.quality_flags)
    assert batch.quarantined_record_count == 2


def test_unanchored_or_untyped_payloads_remain_explicit_mapping_issues() -> None:
    batch = map_batch(
        splits=[
            split_payload(ticker=None),
            split_payload(execution_date="bad-date"),
            split_payload(adjustment_type="unknown"),
            "not-an-object",
        ],
        dividends=[dividend_payload(ex_dividend_date=None)],
    )

    assert batch.records == ()
    assert batch.input_count == 5
    assert batch.quarantined_without_record_count == 5
    assert {issue.reason_code for issue in batch.issues} == {
        "missing_or_invalid_ticker",
        "missing_or_invalid_execution_date",
        "missing_or_unsupported_adjustment_type",
        "payload_not_object",
        "missing_or_invalid_ex_dividend_date",
    }
    assert all(len(issue.payload_fingerprint) == 64 for issue in batch.issues)


def test_normalized_resolution_conflict_and_clock_order_fail_before_mapping() -> None:
    with pytest.raises(ValueError, match="normalized-key conflict"):
        map_massive_corporate_action_payloads(
            split_payloads=[],
            dividend_payloads=[],
            ticker_resolutions={"AAA": AAA_ID, " aaa ": BBB_ID},
            first_observed_at=OBSERVED_AT,
            ingested_at=INGESTED_AT,
        )

    with pytest.raises(ValueError, match="must not precede"):
        map_massive_corporate_action_payloads(
            split_payloads=[],
            dividend_payloads=[],
            ticker_resolutions={},
            first_observed_at=OBSERVED_AT,
            ingested_at=OBSERVED_AT - timedelta(seconds=1),
        )
