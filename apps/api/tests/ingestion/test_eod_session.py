"""Tests for the one-session EOD ingestion service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tests.providers.support.in_memory_market_data_provider import InMemoryMarketDataProvider
from tip_api.contracts.market_data.v1 import EodPriceBarV1, QualityStatus
from tip_api.ingestion import (
    EmptyEodSessionError,
    EodSessionIngestionService,
    EodSessionValidationError,
)
from tip_api.persistence.eod_bars import EodPriceBarRepository, EodPriceBarWriteResult
from tip_api.persistence.parquet import ParquetEodPriceBarRepository
from tip_api.providers.market_data import ProviderCapability, ProviderUnavailableError

SESSION = date(2026, 8, 13)
INGESTED_AT = datetime(2026, 8, 14, 1, 30, tzinfo=UTC)
TESTA_ID = UUID("00000000-0000-4000-8000-000000000001")
TESTB_ID = UUID("00000000-0000-4000-8000-000000000002")


def make_bar(
    instrument_id: UUID = TESTA_ID,
    *,
    session_date: date = SESSION,
    source: str = "mocked_provider",
    revision: int = 1,
    is_latest_revision: bool = True,
) -> EodPriceBarV1:
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=session_date,
        open=Decimal("20.00"),
        high=Decimal("20.50"),
        low=Decimal("19.75"),
        close=Decimal("20.25"),
        volume=2000,
        vwap=Decimal("20.10"),
        trade_count=200,
        notional=Decimal("40500.00"),
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=Decimal("20.25"),
        source=source,
        source_record_id=f"{instrument_id}:{session_date}:{source}:{revision}",
        ingested_at=INGESTED_AT,
        revision=revision,
        is_latest_revision=is_latest_revision,
        quality_status=QualityStatus.VALID,
        quality_flags=("mock_fixture",),
    )


@dataclass(frozen=True)
class CapturingRepository:
    result_path: Path
    records: tuple[EodPriceBarV1, ...] = ()

    def publish_session(
        self,
        records: tuple[EodPriceBarV1, ...],
        *,
        session_date: date,
        provider_id: str,
    ) -> EodPriceBarWriteResult:
        object.__setattr__(self, "records", records)
        return EodPriceBarWriteResult(
            schema_version="1.0",
            session_date=session_date,
            provider_id=provider_id,
            record_count=len(records),
            written_record_count=len(records),
            partition_path=self.result_path,
            content_sha256="0" * 64,
            status="published",
        )


class FailingProvider:
    @property
    def provider_id(self) -> str:
        return "failing_provider"

    @property
    def capabilities(self) -> frozenset[ProviderCapability]:
        return frozenset({ProviderCapability.EOD_PRICE_BARS})

    def get_eod_bars(self, query: object) -> tuple[EodPriceBarV1, ...]:
        raise ProviderUnavailableError(self.provider_id, "provider unavailable")


def provider(records: tuple[EodPriceBarV1, ...]) -> InMemoryMarketDataProvider:
    return InMemoryMarketDataProvider(
        provider_id="mocked_provider",
        capabilities=frozenset({ProviderCapability.EOD_PRICE_BARS}),
        eod_bars=records,
    )


def test_successful_ingestion_result(tmp_path: Path) -> None:
    records = (make_bar(TESTB_ID), make_bar(TESTA_ID))
    service = EodSessionIngestionService(
        provider=provider(records),
        repository=ParquetEodPriceBarRepository(root=tmp_path, created_at=INGESTED_AT),
        instrument_ids=(TESTA_ID, TESTB_ID),
    )
    result = service.ingest_session(SESSION)
    assert result.schema_version == "1.0"
    assert result.session_date == SESSION
    assert result.provider_id == "mocked_provider"
    assert result.fetched_record_count == 2
    assert result.validated_record_count == 2
    assert result.written_record_count == 2
    assert result.status == "published"
    assert result.partition_path.exists()


def test_service_uses_single_day_query_and_deterministic_sort(tmp_path: Path) -> None:
    records = (make_bar(TESTB_ID), make_bar(TESTA_ID))
    repo = CapturingRepository(tmp_path / "partition")
    service = EodSessionIngestionService(provider=provider(records), repository=repo, instrument_ids=(TESTA_ID, TESTB_ID))
    service.ingest_session(SESSION)
    assert [record.instrument_id for record in repo.records] == [TESTA_ID, TESTB_ID]


def test_empty_provider_result_rejected(tmp_path: Path) -> None:
    service = EodSessionIngestionService(provider=provider(()), repository=CapturingRepository(tmp_path), instrument_ids=(TESTA_ID,))
    with pytest.raises(EmptyEodSessionError):
        service.ingest_session(SESSION)


def test_wrong_session_date_rejected(tmp_path: Path) -> None:
    bad_record = make_bar(session_date=date(2026, 8, 12))
    class WrongSessionProvider:
        provider_id = "mocked_provider"
        capabilities = frozenset({ProviderCapability.EOD_PRICE_BARS})
        def get_eod_bars(self, query: object) -> tuple[EodPriceBarV1, ...]:
            return (bad_record,)

    service = EodSessionIngestionService(
        provider=WrongSessionProvider(), repository=CapturingRepository(tmp_path), instrument_ids=(TESTA_ID,)
    )
    with pytest.raises(EodSessionValidationError, match="outside"):
        service.ingest_session(SESSION)


def test_duplicate_business_key_rejected(tmp_path: Path) -> None:
    record = make_bar()
    class DuplicateProvider:
        provider_id = "mocked_provider"
        capabilities = frozenset({ProviderCapability.EOD_PRICE_BARS})
        def get_eod_bars(self, query: object) -> tuple[EodPriceBarV1, ...]:
            return (record, record)

    service = EodSessionIngestionService(
        provider=DuplicateProvider(), repository=CapturingRepository(tmp_path), instrument_ids=(TESTA_ID,)
    )
    with pytest.raises(EodSessionValidationError, match="duplicate"):
        service.ingest_session(SESSION)


def test_contradictory_latest_revision_rejected(tmp_path: Path) -> None:
    records = (make_bar(revision=1, is_latest_revision=True), make_bar(revision=2, is_latest_revision=True))
    class RevisionProvider:
        provider_id = "mocked_provider"
        capabilities = frozenset({ProviderCapability.EOD_PRICE_BARS})
        def get_eod_bars(self, query: object) -> tuple[EodPriceBarV1, ...]:
            return records

    service = EodSessionIngestionService(
        provider=RevisionProvider(), repository=CapturingRepository(tmp_path), instrument_ids=(TESTA_ID,)
    )
    with pytest.raises(EodSessionValidationError, match="latest"):
        service.ingest_session(SESSION)


def test_provider_error_propagates(tmp_path: Path) -> None:
    service = EodSessionIngestionService(
        provider=FailingProvider(), repository=CapturingRepository(tmp_path), instrument_ids=(TESTA_ID,)
    )
    with pytest.raises(ProviderUnavailableError):
        service.ingest_session(SESSION)


def test_empty_instrument_boundary_rejected(tmp_path: Path) -> None:
    service = EodSessionIngestionService(provider=provider((make_bar(),)), repository=CapturingRepository(tmp_path), instrument_ids=())
    with pytest.raises(EodSessionValidationError, match="instrument_ids"):
        service.ingest_session(SESSION)


def test_idempotent_ingestion_result(tmp_path: Path) -> None:
    service = EodSessionIngestionService(
        provider=provider((make_bar(TESTA_ID), make_bar(TESTB_ID))),
        repository=ParquetEodPriceBarRepository(root=tmp_path, created_at=INGESTED_AT),
        instrument_ids=(TESTA_ID, TESTB_ID),
    )
    first = service.ingest_session(SESSION)
    second = service.ingest_session(SESSION)
    assert first.content_sha256 == second.content_sha256
    assert second.status == "already_present"
    assert second.written_record_count == 0
