from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.ingestion.instrument_identity import canonical_instrument_id_for_identity, select_stable_identity
from tip_api.ingestion.instrument_master_snapshot import (
    InstrumentMasterSnapshotIngestionService,
    InstrumentMasterSnapshotQualityGates,
)
from tip_api.persistence.parquet.instrument_master_snapshot import ParquetInstrumentMasterSnapshotRepository
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import (
    FixedIntervalRateLimiter,
    build_case_sensitive_provider_ticker_resolution,
    build_snapshot_from_payloads,
    fetch_and_build_snapshot,
    main,
    parse_as_of_date,
)

INGESTED_AT = datetime(2026, 8, 14, 12, tzinfo=UTC)
AS_OF = date(2026, 8, 13)


class FakeTransport:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get_json(self, path, *, params, api_key, timeout_seconds, base_url):
        assert "apiKey" not in params
        self.calls.append((path, dict(params)))
        if not self.pages:
            raise AssertionError("unexpected extra request")
        return self.pages.pop(0)


def payload(ticker="TESTA", share="SHARE1", composite="COMP1", type="CS"):
    return {
        "ticker": ticker,
        "name": f"{ticker} Holdings",
        "market": "stocks",
        "locale": "us",
        "primary_exchange": "XNYS",
        "type": type,
        "active": True,
        "currency_name": "usd",
        "cik": "0001234567",
        "composite_figi": composite,
        "share_class_figi": share,
        "last_updated_utc": "2026-08-13T21:00:00Z",
    }


def test_identity_priority_and_uuid_reproducibility():
    first = select_stable_identity(share_class_figi="share1", composite_figi="comp1", provider_instrument_id="pid1")
    second = select_stable_identity(share_class_figi="SHARE1", composite_figi=None, provider_instrument_id=None)
    assert first == second
    assert canonical_instrument_id_for_identity(first) == canonical_instrument_id_for_identity(second)
    assert select_stable_identity(share_class_figi=None, composite_figi="comp1", provider_instrument_id="pid1").identity_type.value == "composite_figi"
    assert select_stable_identity(share_class_figi=None, composite_figi=None, provider_instrument_id=None) is None


def test_build_snapshot_resolves_figi_and_leaves_cik_only_unresolved():
    result = build_snapshot_from_payloads(
        payloads=(payload("TESTA"), {**payload("TESTB", share=None, composite=None), "cik": "000999"}),
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )
    assert result.resolved_eligible_count == 1
    assert result.unresolved_eligible_count == 1
    assert any(i.resolution_status is ResolutionStatus.UNRESOLVED for i in result.identities)
    assert result.instruments[0].ticker == "TESTA"


def test_unsupported_type_is_rejected_and_collision_is_ambiguous():
    result = build_snapshot_from_payloads(
        payloads=(payload("TESTA", share="SAME"), payload("TESTB", share="SAME"), payload("TESTC", type="WARRANT")),
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )
    assert result.stable_identifier_collision_count == 2
    assert result.expected_exclusion_count == 1
    assert result.resolved_eligible_count == 0


def test_case_sensitive_source_projection_separates_security_forms():
    source = (
        payload("TPC", share="TPC-COMMON", composite="TPC-COMPOSITE"),
        payload("TpC", share=None, composite=None, type="PFD"),
        payload("ECGw", share="ECGW-COMMON", composite="ECGW-COMPOSITE"),
    )
    canonical = build_snapshot_from_payloads(
        payloads=source,
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )
    canonical_resolver = {
        item.provider_ticker: item.canonical_instrument_id
        for item in canonical.resolvers
    }

    exact = build_case_sensitive_provider_ticker_resolution(
        payloads=source,
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        canonical_instrument_ids=frozenset(
            item.instrument_id for item in canonical.instruments
        ),
        canonical_resolver=canonical_resolver,
    )

    assert exact.resolver["TPC"] == canonical_resolver["TPC"]
    assert exact.status["TpC"] == "excluded"
    assert "TpC" not in exact.resolver
    assert exact.resolver["ECGw"] == canonical_resolver["ECGW"]
    assert exact.status["ECGw"] == "resolved"
    assert exact.case_colliding_normalized_tickers == frozenset({"TPC"})
    assert exact.case_colliding_resolved_instrument_ids == frozenset(
        {canonical_resolver["TPC"]}
    )


def test_pagination_success_and_rate_limiter_uses_fake_clock():
    page1 = {"results": [payload("TESTA")], "next_url": "https://api.massive.com/v3/reference/tickers?cursor=abc"}
    page2 = {"results": [payload("TESTB", share="SHARE2", composite="COMP2")]}
    now = [100.0]
    sleeps = []

    def clock():
        return now[0]

    def sleeper(delay):
        sleeps.append(delay)
        now[0] += delay

    result = fetch_and_build_snapshot(
        config=MassiveProviderConfig(api_key="fake-key"),
        transport=FakeTransport([page1, page2]),
        as_of_date=AS_OF,
        rate_limiter=FixedIntervalRateLimiter(clock=clock, sleeper=sleeper),
        ingested_at=INGESTED_AT,
    )
    assert result.request_count == 2
    assert sleeps == [15.0]


def test_foreign_host_next_url_rejected():
    with pytest.raises(RuntimeError):
        fetch_and_build_snapshot(
            config=MassiveProviderConfig(api_key="fake-key"),
            transport=FakeTransport([{"results": [], "next_url": "https://evil.example/v3/reference/tickers?cursor=abc"}]),
            as_of_date=AS_OF,
            rate_limiter=FixedIntervalRateLimiter(sleeper=lambda _: None),
            ingested_at=INGESTED_AT,
        )


def test_quality_gate_failure_does_not_publish(tmp_path):
    build = build_snapshot_from_payloads(payloads=(payload("TESTA"),), as_of_date=AS_OF, ingested_at=INGESTED_AT, request_count=1, pagination_complete=True)
    service = InstrumentMasterSnapshotIngestionService(repository=ParquetInstrumentMasterSnapshotRepository(tmp_path))
    result = service.publish_snapshot(
        as_of_date=AS_OF,
        provider_id="massive_stocks_basic",
        instruments=build.instruments,
        identities=build.identities,
        resolvers=build.resolvers,
        request_count=1,
        raw_record_count=build.raw_record_count,
        eligible_record_count=build.eligible_record_count,
        expected_exclusion_count=build.expected_exclusion_count,
        malformed_rejected_count=build.malformed_rejected_count,
        resolved_eligible_count=build.resolved_eligible_count,
        unresolved_eligible_count=build.unresolved_eligible_count,
        ambiguous_ticker_record_count=build.ambiguous_ticker_record_count,
        stable_identifier_collision_count=build.stable_identifier_collision_count,
        unique_provider_ticker_count=build.unique_provider_ticker_count,
        duplicate_provider_ticker_count=build.duplicate_provider_ticker_count,
    )
    assert result.status == "quality_gate_failed"
    assert not (tmp_path / "market-data").exists()


def test_low_ratio_stable_collisions_remain_ambiguous_but_do_not_block_snapshot(
    tmp_path,
):
    ordinary = tuple(
        payload(
            f"TEST{index:03d}",
            share=f"SHARE{index:03d}",
            composite=f"COMP{index:03d}",
        )
        for index in range(100)
    )
    collision = (
        payload("OLDSYM", share="COLLISION", composite="COLLISION-COMP"),
        payload("NEWSYM", share="COLLISION", composite="COLLISION-COMP"),
    )
    build = build_snapshot_from_payloads(
        payloads=ordinary + collision,
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )
    service = InstrumentMasterSnapshotIngestionService(
        repository=ParquetInstrumentMasterSnapshotRepository(tmp_path),
        gates=InstrumentMasterSnapshotQualityGates(
            minimum_raw_records=0,
            maximum_stable_identifier_collision_ratio=0.02,
        ),
    )

    result = service.publish_snapshot(
        as_of_date=AS_OF,
        provider_id="massive_stocks_basic",
        instruments=build.instruments,
        identities=build.identities,
        resolvers=build.resolvers,
        request_count=build.request_count,
        raw_record_count=build.raw_record_count,
        eligible_record_count=build.eligible_record_count,
        expected_exclusion_count=build.expected_exclusion_count,
        malformed_rejected_count=build.malformed_rejected_count,
        resolved_eligible_count=build.resolved_eligible_count,
        unresolved_eligible_count=build.unresolved_eligible_count,
        ambiguous_ticker_record_count=build.ambiguous_ticker_record_count,
        stable_identifier_collision_count=build.stable_identifier_collision_count,
        unique_provider_ticker_count=build.unique_provider_ticker_count,
        duplicate_provider_ticker_count=build.duplicate_provider_ticker_count,
    )

    assert build.eligible_record_count == 102
    assert result.status == "published"
    assert result.quality_gate_passed is True
    assert result.stable_identifier_collision_count == 2
    assert result.stable_identifier_collision_ratio == pytest.approx(2 / 102)
    assert result.canonical_instrument_count == 100
    assert sum(
        identity.resolution_status is ResolutionStatus.AMBIGUOUS
        for identity in build.identities
    ) == 2


def test_stable_collision_ratio_above_gate_still_blocks_snapshot(tmp_path):
    ordinary = tuple(
        payload(
            f"TEST{index:03d}",
            share=f"SHARE{index:03d}",
            composite=f"COMP{index:03d}",
        )
        for index in range(100)
    )
    build = build_snapshot_from_payloads(
        payloads=ordinary
        + (
            payload("OLDSYM", share="COLLISION", composite="COLLISION-COMP"),
            payload("NEWSYM", share="COLLISION", composite="COLLISION-COMP"),
        ),
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )
    service = InstrumentMasterSnapshotIngestionService(
        repository=ParquetInstrumentMasterSnapshotRepository(tmp_path),
        gates=InstrumentMasterSnapshotQualityGates(
            minimum_raw_records=0,
            maximum_stable_identifier_collision_ratio=0.01,
        ),
    )

    result = service.publish_snapshot(
        as_of_date=AS_OF,
        provider_id="massive_stocks_basic",
        instruments=build.instruments,
        identities=build.identities,
        resolvers=build.resolvers,
        request_count=build.request_count,
        raw_record_count=build.raw_record_count,
        eligible_record_count=build.eligible_record_count,
        expected_exclusion_count=build.expected_exclusion_count,
        malformed_rejected_count=build.malformed_rejected_count,
        resolved_eligible_count=build.resolved_eligible_count,
        unresolved_eligible_count=build.unresolved_eligible_count,
        ambiguous_ticker_record_count=build.ambiguous_ticker_record_count,
        stable_identifier_collision_count=build.stable_identifier_collision_count,
        unique_provider_ticker_count=build.unique_provider_ticker_count,
        duplicate_provider_ticker_count=build.duplicate_provider_ticker_count,
    )

    assert result.status == "quality_gate_failed"
    assert result.quality_gate_failures == (
        "stable_identifier_collision_ratio_above_gate",
    )
    assert not (tmp_path / "market-data").exists()


def test_parse_as_of_date_accepts_completed_historical_dates():
    assert parse_as_of_date("2026-08-12") == date(2026, 8, 12)


def test_cli_argument_limits():
    assert main(["--as-of-date", "2999-01-01", "--data-root", "/data/trading-intelligence-platform"]) == 2
    assert main(["--as-of-date", "2026-08-13", "--data-root", "/tmp/not-approved"]) == 2



def test_unit_type_is_rejected():
    result = build_snapshot_from_payloads(
        payloads=(payload("TESTU", type="UNIT"),),
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )
    assert result.expected_exclusion_count == 1
    assert result.resolved_eligible_count == 0


def test_etv_is_an_expected_exclusion_and_never_inferred_to_be_an_etf():
    result = build_snapshot_from_payloads(
        payloads=(payload("TESTV", type="ETV"),),
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )

    assert result.expected_exclusion_count == 1
    assert result.malformed_rejected_count == 0
    assert result.eligible_record_count == 0
    assert result.instruments == ()
    assert result.resolvers == ()
    assert result.identities[0].resolution_status is ResolutionStatus.EXCLUDED
    assert result.identities[0].quality_flags == ("exchange_traded_vehicle",)


def test_missing_provider_type_remains_malformed_and_quarantined():
    record = payload("TESTM")
    del record["type"]

    result = build_snapshot_from_payloads(
        payloads=(record,),
        as_of_date=AS_OF,
        ingested_at=INGESTED_AT,
        request_count=1,
        pagination_complete=True,
    )

    assert result.expected_exclusion_count == 0
    assert result.malformed_rejected_count == 1
    assert result.eligible_record_count == 0
    assert result.instruments == ()
    assert result.resolvers == ()
    assert result.identities[0].resolution_status is ResolutionStatus.REJECTED
    assert result.identities[0].quality_flags == ("missing_provider_type",)
