from datetime import UTC, date, datetime
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
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotConflictError, InstrumentMasterSnapshotCorruptionError
from tip_api.persistence.parquet.instrument_master_snapshot import (
    INSTRUMENT_MASTER_ARROW_SCHEMA,
    PROVIDER_IDENTITY_ARROW_SCHEMA,
    ParquetInstrumentMasterSnapshotRepository,
    identity_records_to_table,
    instrument_content_fingerprint,
    instrument_records_to_table,
)

AS_OF = date(2026, 8, 13)
INGESTED_AT = datetime(2026, 8, 14, 12, tzinfo=UTC)
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
        figi=f"FIGI{ticker}",
        cik="000123",
        valid_from=AS_OF,
        as_of_date=AS_OF,
        source="massive_stocks_basic",
        source_instrument_id=f"share_class_figi:FIGI{ticker}",
        ingested_at=INGESTED_AT,
        quality_status=QualityStatus.VALID,
    )


def identity(instrument_id=ID1, ticker="TESTA"):
    return ProviderInstrumentIdentityV1(
        provider="massive_stocks_basic",
        as_of_date=AS_OF,
        provider_ticker=ticker,
        share_class_figi=f"FIGI{ticker}",
        canonical_instrument_id=instrument_id,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI,
        valid_from=AS_OF,
        ingested_at=INGESTED_AT,
        quality_status=QualityStatus.VALID,
    )



def resolver(instrument_id=ID1, ticker="TESTA"):
    return ProviderTickerResolverV1(
        provider="massive_stocks_basic",
        as_of_date=AS_OF,
        provider_ticker=ticker,
        canonical_instrument_id=instrument_id,
        resolution_method="share_class_figi",
        source_identity_key=f"share_class_figi:FIGI{ticker}",
        ingested_at=INGESTED_AT,
    )

def test_explicit_arrow_schemas_and_round_trip(tmp_path):
    instruments = (instrument(ID2, "TESTB"), instrument(ID1, "TESTA"))
    identities = (identity(ID2, "TESTB"), identity(ID1, "TESTA"))
    resolvers = (resolver(ID2, "TESTB"), resolver(ID1, "TESTA"))
    assert instrument_records_to_table(instruments).schema.equals(INSTRUMENT_MASTER_ARROW_SCHEMA, check_metadata=False)
    assert identity_records_to_table(identities).schema.equals(PROVIDER_IDENTITY_ARROW_SCHEMA, check_metadata=False)
    repo = ParquetInstrumentMasterSnapshotRepository(tmp_path, created_at=INGESTED_AT)
    result = repo.publish_snapshot(
        instruments=instruments,
        identities=identities,
        resolvers=resolvers,
        as_of_date=AS_OF,
        provider_id="massive_stocks_basic",
        quality_summary={"resolved_count": 2},
    )
    assert result.status == "published"
    assert result.written_instrument_count == 2
    assert result.snapshot_manifest_path.exists()
    assert (result.instrument_partition_path / "part-00000.parquet").exists()
    assert (result.identity_partition_path / "part-00000.parquet").exists()


def test_fingerprint_input_order_independent():
    records_a = (instrument(ID1, "TESTA"), instrument(ID2, "TESTB"))
    records_b = tuple(reversed(records_a))
    assert instrument_content_fingerprint(records_a) == instrument_content_fingerprint(records_b)


def test_idempotent_rerun_and_conflict(tmp_path):
    repo = ParquetInstrumentMasterSnapshotRepository(tmp_path, created_at=INGESTED_AT)
    kwargs = dict(
        instruments=(instrument(ID1, "TESTA"),),
        identities=(identity(ID1, "TESTA"),),
        resolvers=(resolver(ID1, "TESTA"),),
        as_of_date=AS_OF,
        provider_id="massive_stocks_basic",
        quality_summary={"resolved_count": 1},
    )
    repo.publish_snapshot(**kwargs)
    again = repo.publish_snapshot(**kwargs)
    assert again.status == "already_present"
    with pytest.raises(InstrumentMasterSnapshotConflictError):
        repo.publish_snapshot(**{**kwargs, "instruments": (instrument(ID2, "TESTB"),), "identities": (identity(ID2, "TESTB"),), "resolvers": (resolver(ID2, "TESTB"),)})


def test_incomplete_existing_partition_rejected(tmp_path):
    partial = tmp_path / "market-data" / "instrument-master" / "schema_version=1" / "as_of_date=2026-08-13"
    partial.mkdir(parents=True)
    repo = ParquetInstrumentMasterSnapshotRepository(tmp_path, created_at=INGESTED_AT)
    with pytest.raises(InstrumentMasterSnapshotCorruptionError):
        repo.publish_snapshot(
            instruments=(instrument(),),
            identities=(identity(),),
            resolvers=(resolver(),),
            as_of_date=AS_OF,
            provider_id="massive_stocks_basic",
            quality_summary={},
        )


def test_symlink_root_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    repo = ParquetInstrumentMasterSnapshotRepository(link, created_at=INGESTED_AT)
    with pytest.raises(Exception):
        repo.publish_snapshot(
            instruments=(instrument(),),
            identities=(identity(),),
            resolvers=(resolver(),),
            as_of_date=AS_OF,
            provider_id="massive_stocks_basic",
            quality_summary={},
        )

