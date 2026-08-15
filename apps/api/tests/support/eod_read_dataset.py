from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from tip_api.contracts.market_data.v1 import (
    EodPriceBarV1,
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    ProviderInstrumentIdentityV1,
    ProviderTickerResolverV1,
    QualityStatus,
    ResolutionMethod,
    ResolutionStatus,
)
from tip_api.persistence.parquet.eod_bars import ParquetEodPriceBarRepository
from tip_api.persistence.parquet.instrument_master_snapshot import ParquetInstrumentMasterSnapshotRepository

SESSION_DATE = date(2026, 8, 13)
CREATED_AT = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
PROVIDER_ID = "massive"
TESTA_ID = UUID("00000000-0000-5000-8000-000000000001")
TESTB_ID = UUID("00000000-0000-5000-8000-000000000002")
TESTC_ID = UUID("00000000-0000-5000-8000-000000000003")
EXTRA_ID = UUID("00000000-0000-5000-8000-000000000099")


@dataclass(frozen=True)
class CompletedEodFixture:
    root: Path
    session_date: date
    snapshot_content_sha256: str
    eod_content_sha256: str
    instrument_ids: tuple[UUID, ...]


def instrument(instrument_id: UUID, ticker: str, instrument_type: InstrumentType = InstrumentType.COMMON_STOCK) -> InstrumentMasterV1:
    return InstrumentMasterV1(
        instrument_id=instrument_id,
        issuer_id=None,
        instrument_type=instrument_type,
        status=InstrumentStatus.ACTIVE,
        ticker=ticker,
        name=f"{ticker} Test Instrument",
        primary_exchange="XNYS",
        listing_country="US",
        currency="USD",
        figi=f"BBG{ticker}TEST",
        cik=None,
        valid_from=SESSION_DATE,
        valid_to=None,
        first_trade_date=None,
        last_trade_date=None,
        as_of_date=SESSION_DATE,
        source=PROVIDER_ID,
        source_instrument_id=f"share_class_figi:BBG{ticker}TEST",
        ingested_at=CREATED_AT,
        quality_status=QualityStatus.VALID,
        quality_notes=None,
    )


def identity(instrument_id: UUID, ticker: str) -> ProviderInstrumentIdentityV1:
    return ProviderInstrumentIdentityV1(
        provider=PROVIDER_ID,
        as_of_date=SESSION_DATE,
        provider_ticker=ticker,
        provider_instrument_id=None,
        composite_figi=None,
        share_class_figi=f"BBG{ticker}TEST",
        cik=None,
        canonical_instrument_id=instrument_id,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI,
        valid_from=SESSION_DATE,
        valid_to=None,
        source_updated_at=None,
        ingested_at=CREATED_AT,
        quality_status=QualityStatus.VALID,
        quality_flags=(),
    )


def resolver(instrument_id: UUID, ticker: str) -> ProviderTickerResolverV1:
    return ProviderTickerResolverV1(
        provider=PROVIDER_ID,
        as_of_date=SESSION_DATE,
        provider_ticker=ticker,
        canonical_instrument_id=instrument_id,
        resolution_method=ResolutionMethod.SHARE_CLASS_FIGI.value,
        source_identity_key=f"share_class_figi:BBG{ticker}TEST",
        ingested_at=CREATED_AT,
    )


def bar(
    instrument_id: UUID,
    *,
    open_: Decimal = Decimal("10.10"),
    high: Decimal = Decimal("11.10"),
    low: Decimal = Decimal("9.90"),
    close: Decimal = Decimal("10.90"),
    volume: Decimal = Decimal("100.5"),
    vwap: Decimal | None = Decimal("10.50"),
    trade_count: int | None = 7,
    quality_flags: tuple[str, ...] = (),
) -> EodPriceBarV1:
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=SESSION_DATE,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        vwap=vwap,
        trade_count=trade_count,
        notional=Decimal("1055.25"),
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=close,
        source=PROVIDER_ID,
        source_record_id=None,
        ingested_at=CREATED_AT,
        revision=1,
        is_latest_revision=True,
        quality_status=QualityStatus.WARNING if quality_flags else QualityStatus.VALID,
        quality_flags=quality_flags,
    )


def publish_completed_eod_dataset(root: Path) -> CompletedEodFixture:
    instruments = (
        instrument(TESTC_ID, "TESTC"),
        instrument(TESTA_ID, "TESTA"),
        instrument(TESTB_ID, "TESTB", InstrumentType.ETF),
    )
    identities = tuple(identity(item.instrument_id, item.ticker) for item in instruments)
    resolvers = tuple(resolver(item.instrument_id, item.ticker) for item in instruments)
    snapshot = ParquetInstrumentMasterSnapshotRepository(root, created_at=CREATED_AT).publish_snapshot(
        instruments=instruments,
        identities=identities,
        resolvers=resolvers,
        as_of_date=SESSION_DATE,
        provider_id=PROVIDER_ID,
        quality_summary={"quality_warnings": []},
    )
    bars = (
        bar(TESTC_ID, open_=Decimal("30"), high=Decimal("31"), low=Decimal("29"), close=Decimal("30.5"), volume=Decimal("300")),
        bar(TESTA_ID, volume=Decimal("100.25"), quality_flags=("adjustment_factors_unverified",)),
        bar(TESTB_ID, open_=Decimal("20"), high=Decimal("21"), low=Decimal("19"), close=Decimal("20.5"), volume=Decimal("0"), vwap=None, trade_count=None, quality_flags=("missing_vwap", "missing_trade_count", "zero_volume")),
    )
    eod = ParquetEodPriceBarRepository(root, created_at=CREATED_AT).publish_session(
        bars,
        session_date=SESSION_DATE,
        provider_id=PROVIDER_ID,
        quality_summary={"quality_warnings": ["adjustment_factors_unverified"]},
        identity_snapshot={
            "as_of_date": SESSION_DATE.isoformat(),
            "provider_id": PROVIDER_ID,
            "snapshot_content_sha256": snapshot.snapshot_content_sha256,
            "resolver_count": snapshot.resolver_count,
        },
    )
    return CompletedEodFixture(
        root=root,
        session_date=SESSION_DATE,
        snapshot_content_sha256=snapshot.snapshot_content_sha256,
        eod_content_sha256=eod.content_sha256,
        instrument_ids=(TESTA_ID, TESTB_ID, TESTC_ID),
    )


def eod_manifest_path(root: Path) -> Path:
    return root / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={SESSION_DATE.isoformat()}" / "manifest.json"


def update_json(path: Path, **updates: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(updates)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
