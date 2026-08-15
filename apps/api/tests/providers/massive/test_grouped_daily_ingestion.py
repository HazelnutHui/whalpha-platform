from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    ProviderInstrumentIdentityV1,
    ProviderTickerResolverV1,
    ResolutionMethod,
    ResolutionStatus,
)
from tip_api.persistence.parquet.eod_bars import PARQUET_FILE_NAME
from tip_api.persistence.parquet.instrument_master_snapshot import ParquetInstrumentMasterSnapshotRepository
from tip_api.providers.massive.grouped_daily_ingestion import (
    ENDPOINT_TEMPLATE,
    _MissingRequired,
    _NumericFailure,
    load_identity_snapshot,
    parse_date,
    parse_massive_decimal,
    parse_massive_integral,
    process_grouped_daily_payload,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID

AS_OF = date(2026, 8, 13)
INGESTED_AT = datetime(2026, 8, 14, 12, tzinfo=UTC)
TS = int(datetime(2026, 8, 13, 12, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
BASE_UUID = UUID("00000000-0000-4000-8000-000000000001")
ID1 = UUID("11111111-1111-4111-8111-111111111111")
ID2 = UUID("22222222-2222-4222-8222-222222222222")


def instrument(instrument_id=ID1, ticker="TESTA"):
    return InstrumentMasterV1(
        instrument_id=instrument_id,
        instrument_type=InstrumentType.COMMON_STOCK,
        status=InstrumentStatus.ACTIVE,
        ticker=ticker,
        name=f"{ticker} Holdings",
        primary_exchange="XNYS",
        listing_country="US",
        currency="USD",
        valid_from=AS_OF,
        as_of_date=AS_OF,
        source=MASSIVE_PROVIDER_ID,
        source_instrument_id=f"share_class_figi:{ticker}",
        ingested_at=INGESTED_AT,
        quality_status=QualityStatus.VALID,
    )


def identity(status=ResolutionStatus.RESOLVED, ticker="TESTA", instrument_id=ID1, flags=()):
    return ProviderInstrumentIdentityV1(
        provider=MASSIVE_PROVIDER_ID,
        as_of_date=AS_OF,
        provider_ticker=ticker,
        share_class_figi=f"FIGI{ticker}",
        canonical_instrument_id=instrument_id if status is ResolutionStatus.RESOLVED else None,
        resolution_status=status,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI if status is ResolutionStatus.RESOLVED else ResolutionMethod.UNRESOLVED,
        valid_from=AS_OF,
        ingested_at=INGESTED_AT,
        quality_status=QualityStatus.VALID if status is ResolutionStatus.RESOLVED else QualityStatus.WARNING if status in {ResolutionStatus.UNRESOLVED, ResolutionStatus.EXCLUDED} else QualityStatus.REJECTED,
        quality_flags=flags,
    )


def resolver(instrument_id=ID1, ticker="TESTA"):
    return ProviderTickerResolverV1(
        provider=MASSIVE_PROVIDER_ID,
        as_of_date=AS_OF,
        provider_ticker=ticker,
        canonical_instrument_id=instrument_id,
        resolution_method="share_class_figi",
        source_identity_key=f"share_class_figi:{ticker}",
        ingested_at=INGESTED_AT,
    )


def publish_identity_snapshot(tmp_path, *, resolved_count=2):
    instruments = []
    identities = []
    resolvers = []
    if resolved_count == 2:
        instruments = [instrument(ID1, "TESTA"), instrument(ID2, "TESTB")]
        identities = [identity(ticker="TESTA", instrument_id=ID1), identity(ticker="TESTB", instrument_id=ID2)]
        resolvers = [resolver(ID1, "TESTA"), resolver(ID2, "TESTB")]
    else:
        for i in range(resolved_count):
            ticker = f"T{i:05d}"
            instrument_id = uuid5(BASE_UUID, ticker)
            instruments.append(instrument(instrument_id, ticker))
            identities.append(identity(ticker=ticker, instrument_id=instrument_id))
            resolvers.append(resolver(instrument_id, ticker))
    identities.extend(
        [
            identity(status=ResolutionStatus.UNRESOLVED, ticker="TESTU", flags=("no_stable_security_identifier",)),
            identity(status=ResolutionStatus.EXCLUDED, ticker="TESTX", flags=("expected_exclusion",)),
            identity(status=ResolutionStatus.AMBIGUOUS, ticker="TESTM", flags=("ticker_level_ambiguity",)),
            identity(status=ResolutionStatus.REJECTED, ticker="TESTR", flags=("malformed",)),
        ]
    )
    repo = ParquetInstrumentMasterSnapshotRepository(tmp_path, created_at=INGESTED_AT)
    repo.publish_snapshot(
        instruments=tuple(instruments),
        identities=tuple(identities),
        resolvers=tuple(resolvers),
        as_of_date=AS_OF,
        provider_id=MASSIVE_PROVIDER_ID,
        quality_summary={"resolved": resolved_count},
    )
    return load_identity_snapshot(tmp_path, provider_id=MASSIVE_PROVIDER_ID, as_of_date=AS_OF)


def bar(ticker="TESTA", **overrides):
    data = {"T": ticker, "o": 10, "h": 12.0, "l": Decimal("9"), "c": "11.00", "v": 1000.0, "vw": 10.5, "n": 25.0, "t": TS}
    data.update(overrides)
    return data


@pytest.mark.parametrize("value,expected", [(10, Decimal("10")), (10.5, Decimal("10.5")), (Decimal("10.25"), Decimal("10.25")), ("10.125", Decimal("10.125")), (0, Decimal("0"))])
def test_price_numeric_policy_accepts_json_numbers_decimal_and_strings(value, expected):
    assert parse_massive_decimal(value, field_name="o", required=True) == expected


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "", "bad", [], {}])
def test_price_numeric_policy_rejects_unsafe_values(value):
    with pytest.raises(_NumericFailure):
        parse_massive_decimal(value, field_name="o", required=True)


def test_required_none_rejected_but_optional_none_allowed():
    with pytest.raises(_MissingRequired):
        parse_massive_decimal(None, field_name="o", required=True)
    assert parse_massive_decimal(None, field_name="vw", required=False) is None
    assert parse_massive_integral(None, field_name="n", required=False, allow_negative=False) is None


@pytest.mark.parametrize("value,expected", [(10, 10), (10.0, 10), (Decimal("10.0"), 10), ("10", 10), (0, 0)])
def test_integer_semantic_policy_accepts_integral_values(value, expected):
    assert parse_massive_integral(value, field_name="n", required=True, allow_negative=False) == expected


@pytest.mark.parametrize("value", [True, 10.5, Decimal("10.5"), "10.5", -1, float("inf"), "bad"])
def test_integer_semantic_policy_rejects_fractional_bool_negative_and_malformed(value):
    with pytest.raises(_NumericFailure):
        parse_massive_integral(value, field_name="n", required=True, allow_negative=False)



def test_grouped_daily_parse_date_accepts_completed_historical_date():
    assert parse_date("2026-08-12", name="session-date") == date(2026, 8, 12)


def test_grouped_daily_parse_date_rejects_future_date():
    with pytest.raises(ValueError):
        parse_date("2999-01-01", name="session-date")

def test_completed_identity_snapshot_verification(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    assert len(snapshot.resolver) == 2
    assert snapshot.resolver["TESTA"] == ID1
    assert ID1 in snapshot.instrument_ids


def test_identity_classification_before_numeric_validation(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    payload = {"results": [bar("TESTA", v=True), bar("TESTU", o="bad"), bar("TESTX", h="bad"), bar("TESTM"), bar("TESTR"), bar("MISS")]}
    result = process_grouped_daily_payload(payload, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.identity_classified_count == result.raw_result_count == 6
    assert result.resolved_eligible_bar_count == 1
    assert result.unresolved_eligible_bar_count == 1
    assert result.expected_exclusion_bar_count == 1
    assert result.ambiguous_bar_count == 1
    assert result.rejected_identity_bar_count == 1
    assert result.missing_identity_bar_count == 1
    assert result.numeric_conversion_failure_count == 3
    assert result.identity_eligible_denominator == 4


def test_fractional_volume_is_numeric_valid_and_tracked(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    result = process_grouped_daily_payload(
        {"results": [bar("TESTA", v=1000.5)]},
        identity=snapshot,
        session_date=AS_OF,
        endpoint="x",
        data_root=tmp_path,
        ingested_at=INGESTED_AT,
        publish=False,
    )

    assert result.volume_numeric_failure_count == 0
    assert result.fractional_volume_record_count == 1
    assert result.numeric_valid_count == 1
    assert result.canonical_bar_count == 1
    assert "fractional_volume_records_present" in result.quality_warnings


def test_numeric_reconciliation_and_optional_fields(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    payload = {"results": [bar("TESTA", vw=None, n=None, v=0), bar("TESTB")]}
    result = process_grouped_daily_payload(payload, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.numeric_classified_count == 2
    assert result.numeric_valid_count == 2
    assert result.optional_vwap_missing_count == 1
    assert result.optional_trade_count_missing_count == 1
    assert result.zero_volume_count == 1
    assert result.identity_resolved_and_numeric_valid_count == 2
    assert result.count_reconciliation_passed is True


def test_field_level_numeric_failure_metrics(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path, resolved_count=8)
    records = [
        bar("T00000", o="bad"),
        bar("T00001", h="bad"),
        bar("T00002", l="bad"),
        bar("T00003", c="bad"),
        bar("T00004", v="bad"),
        bar("T00005", vw="bad"),
        bar("T00006", n=1.5),
        bar("T00007", t=1.5),
    ]
    result = process_grouped_daily_payload(
        {"results": records},
        identity=snapshot,
        session_date=AS_OF,
        endpoint="x",
        data_root=tmp_path,
        ingested_at=INGESTED_AT,
        publish=False,
    )

    assert result.open_numeric_failure_count == 1
    assert result.high_numeric_failure_count == 1
    assert result.low_numeric_failure_count == 1
    assert result.close_numeric_failure_count == 1
    assert result.volume_numeric_failure_count == 1
    assert result.vwap_numeric_failure_count == 1
    assert result.trade_count_numeric_failure_count == 1
    assert result.timestamp_numeric_failure_count == 1
    assert result.numeric_conversion_failure_count == 8


def test_exact_duplicates_are_deduplicated(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    result = process_grouped_daily_payload({"results": [bar("TESTA"), bar("TESTA"), bar("TESTB")]}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.exact_duplicate_ticker_count == 1
    assert result.exact_duplicate_record_count == 1
    assert result.numeric_classified_count == 2
    assert result.canonical_bar_count == 2
    assert "exact_duplicates_deduplicated" in result.quality_warnings


def test_duplicate_numeric_equivalence_uses_decimal_value_semantics(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    result = process_grouped_daily_payload(
        {"results": [bar("TESTA", v=1000), bar("TESTA", v=1000.0), bar("TESTA", v=Decimal("1000.00")), bar("TESTB")]},
        identity=snapshot,
        session_date=AS_OF,
        endpoint="x",
        data_root=tmp_path,
        ingested_at=INGESTED_AT,
        publish=False,
    )

    assert result.exact_duplicate_ticker_count == 1
    assert result.exact_duplicate_record_count == 2
    assert result.conflicting_duplicate_record_count == 0
    assert result.canonical_bar_count == 2


def test_conflicting_duplicates_are_isolated_below_gate(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path, resolved_count=6002)
    records = [bar(f"T{i:05d}") for i in range(6002)]
    records.extend([bar("T00001", c=12), bar("T00001", c=13)])
    result = process_grouped_daily_payload({"results": records}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=True)
    assert result.conflicting_duplicate_ticker_count == 1
    assert result.conflicting_duplicate_record_count == 3
    assert result.conflicting_duplicate_ratio < 0.001
    assert "conflicting_duplicates_isolated" in result.quality_warnings
    assert result.quality_gate_passed is True
    assert result.status == "published"
    assert result.canonical_bar_count == 6001
    partition = tmp_path / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={AS_OF.isoformat()}"
    assert (partition / PARQUET_FILE_NAME).is_file()


def test_conflicting_duplicates_above_gate_fail(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    records = [bar("TESTA"), bar("TESTA", c=12), bar("TESTB")]
    result = process_grouped_daily_payload({"results": records}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.conflicting_duplicate_ratio > 0.001
    assert "conflicting_duplicate_ratio_above_gate" in result.quality_gate_failures
    assert result.canonical_bar_count == 1


def test_quality_gate_failures_for_required_and_market_fields(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path, resolved_count=6001)
    records = [bar(f"T{i:05d}") for i in range(6001)]
    records[0] = bar("T00000", o=None)
    records[1] = bar("T00001", o=0)
    records[2] = bar("T00002", h=8)
    records[3] = bar("T00003", v=-1)
    records[4] = bar("T00004", t=1)
    result = process_grouped_daily_payload({"results": records}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.required_field_missing_count == 1
    assert result.nonpositive_price_count == 1
    assert result.ohlc_consistency_failure_count == 1
    assert result.negative_volume_count == 1
    assert result.timestamp_session_mismatch_count == 1
    assert result.quality_gate_passed is False


def test_successful_atomic_publication_manifest_contains_quality_warnings(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path, resolved_count=6001)
    records = [bar(f"T{i:05d}") for i in range(6001)]
    records[5] = bar("T00005", vw=None)
    result = process_grouped_daily_payload({"results": records}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=True)
    assert result.quality_gate_passed is True
    assert result.written_record_count == 6001
    assert result.content_sha256
    assert "missing_optional_vwap" in result.quality_warnings
    partition = tmp_path / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={AS_OF.isoformat()}"
    manifest = (partition / "manifest.json").read_text(encoding="utf-8")
    assert "identity_snapshot" in manifest
    assert "missing_optional_vwap" in manifest
    assert "TIP_MASSIVE_API_KEY" not in manifest


def test_no_raw_persistence_on_gate_failure(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    result = process_grouped_daily_payload({"results": [bar("TESTA", v=True)]}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=True)
    assert result.quality_gate_passed is False
    assert not (tmp_path / "market-data" / "eod-price-bars").exists()
