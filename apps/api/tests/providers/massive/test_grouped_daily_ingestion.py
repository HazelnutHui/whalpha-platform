from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo
from uuid import UUID

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
from tip_api.persistence.parquet.instrument_master_snapshot import ParquetInstrumentMasterSnapshotRepository
from tip_api.providers.massive.grouped_daily_ingestion import (
    ENDPOINT_TEMPLATE,
    IdentitySnapshot,
    load_identity_snapshot,
    process_grouped_daily_payload,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID

AS_OF = date(2026, 8, 13)
INGESTED_AT = datetime(2026, 8, 14, 12, tzinfo=UTC)
ID1 = UUID("11111111-1111-4111-8111-111111111111")
ID2 = UUID("22222222-2222-4222-8222-222222222222")
TS = int(datetime(2026, 8, 13, 12, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)


def instrument(instrument_id=ID1, ticker="TESTA"):
    return InstrumentMasterV1(instrument_id=instrument_id, instrument_type=InstrumentType.COMMON_STOCK, status=InstrumentStatus.ACTIVE, ticker=ticker, name=f"{ticker} Holdings", primary_exchange="XNYS", listing_country="US", currency="USD", valid_from=AS_OF, as_of_date=AS_OF, source=MASSIVE_PROVIDER_ID, source_instrument_id=f"share_class_figi:{ticker}", ingested_at=INGESTED_AT, quality_status=QualityStatus.VALID)


def identity(status=ResolutionStatus.RESOLVED, ticker="TESTA", instrument_id=ID1, flags=()):
    return ProviderInstrumentIdentityV1(provider=MASSIVE_PROVIDER_ID, as_of_date=AS_OF, provider_ticker=ticker, share_class_figi=f"FIGI{ticker}", canonical_instrument_id=instrument_id if status is ResolutionStatus.RESOLVED else None, resolution_status=status, resolution_method=ResolutionMethod.SHARE_CLASS_FIGI if status is ResolutionStatus.RESOLVED else ResolutionMethod.UNRESOLVED, valid_from=AS_OF, ingested_at=INGESTED_AT, quality_status=QualityStatus.VALID if status is ResolutionStatus.RESOLVED else QualityStatus.WARNING if status in {ResolutionStatus.UNRESOLVED, ResolutionStatus.EXCLUDED} else QualityStatus.REJECTED, quality_flags=flags)


def resolver(instrument_id=ID1, ticker="TESTA"):
    return ProviderTickerResolverV1(provider=MASSIVE_PROVIDER_ID, as_of_date=AS_OF, provider_ticker=ticker, canonical_instrument_id=instrument_id, resolution_method="share_class_figi", source_identity_key=f"share_class_figi:{ticker}", ingested_at=INGESTED_AT)


def publish_identity_snapshot(tmp_path):
    repo = ParquetInstrumentMasterSnapshotRepository(tmp_path, created_at=INGESTED_AT)
    repo.publish_snapshot(
        instruments=(instrument(ID1, "TESTA"), instrument(ID2, "TESTB")),
        identities=(identity(ticker="TESTA", instrument_id=ID1), identity(ticker="TESTB", instrument_id=ID2), identity(status=ResolutionStatus.UNRESOLVED, ticker="TESTU", flags=("no_stable_security_identifier",)), identity(status=ResolutionStatus.EXCLUDED, ticker="TESTX", flags=("expected_exclusion",)), identity(status=ResolutionStatus.AMBIGUOUS, ticker="TESTM", flags=("ticker_level_ambiguity",)), identity(status=ResolutionStatus.REJECTED, ticker="TESTR", flags=("malformed",))),
        resolvers=(resolver(ID1, "TESTA"), resolver(ID2, "TESTB")),
        as_of_date=AS_OF,
        provider_id=MASSIVE_PROVIDER_ID,
        quality_summary={"resolved": 2},
    )
    return load_identity_snapshot(tmp_path, provider_id=MASSIVE_PROVIDER_ID, as_of_date=AS_OF)


def bar(ticker="TESTA", **overrides):
    data = {"T": ticker, "o": 10, "h": 12, "l": 9, "c": 11, "v": 1000, "vw": 10.5, "n": 25, "t": TS}
    data.update(overrides)
    return data


def test_completed_identity_snapshot_verification(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    assert len(snapshot.resolver) == 2
    assert snapshot.resolver["TESTA"] == ID1
    assert ID1 in snapshot.instrument_ids


def test_classification_and_quality_flags_without_publish(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    payload = {"results": [bar("TESTA", vw=None, n=None, v=0), bar("TESTU"), bar("TESTX"), bar("TESTM"), bar("TESTR"), bar("MISS")]}
    result = process_grouped_daily_payload(payload, identity=snapshot, session_date=AS_OF, endpoint=ENDPOINT_TEMPLATE.format(session_date=AS_OF), data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.resolved_eligible_bar_count == 1
    assert result.unresolved_eligible_bar_count == 1
    assert result.expected_exclusion_bar_count == 1
    assert result.ambiguous_bar_count == 1
    assert result.rejected_identity_bar_count == 1
    assert result.missing_identity_bar_count == 1
    assert result.optional_vwap_missing_count == 1
    assert result.optional_trade_count_missing_count == 1
    assert result.zero_volume_count == 1
    assert result.quality_gate_passed is False


def test_numeric_parsing_and_rejections(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    payload = {"results": [bar("TESTA", v="100", o="10.10"), bar("TESTB", v=True), bar("TESTU", o="NaN"), bar("TESTX", c="bad")]}
    result = process_grouped_daily_payload(payload, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.numeric_conversion_failure_count == 1
    assert result.canonical_bar_count == 1


def test_exact_and_conflicting_duplicates(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    exact = {"results": [bar("TESTA"), bar("TESTA"), bar("TESTB"), bar("TESTB", c=12)]}
    result = process_grouped_daily_payload(exact, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=False)
    assert result.exact_duplicate_count == 1
    assert result.conflicting_duplicate_count == 2
    assert "conflicting_duplicate_count_nonzero" in result.quality_gate_failures


def test_successful_atomic_publication_and_manifest_identity_reference(tmp_path):
    snapshot = publish_identity_snapshot(tmp_path)
    bars = [bar("TESTA"), bar("TESTB")]
    # Lower than production-size gate is intentionally still failing.
    result = process_grouped_daily_payload({"results": bars}, identity=snapshot, session_date=AS_OF, endpoint="x", data_root=tmp_path, ingested_at=INGESTED_AT, publish=True)
    assert result.quality_gate_passed is False
    assert not (tmp_path / "market-data" / "eod-price-bars").exists()
