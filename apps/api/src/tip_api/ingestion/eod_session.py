"""One-session EOD ingestion service for canonical price bars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from tip_api.contracts.market_data.v1 import EodPriceBarV1
from tip_api.persistence.eod_bars import EodPriceBarRepository
from tip_api.persistence.parquet.manifest import logical_revision_key, record_business_key, sort_eod_bars
from tip_api.providers.market_data import EodBarQuery, MarketDataProvider, RevisionSelection


class EodSessionIngestionError(Exception):
    """Base class for one-session EOD ingestion errors."""


class EmptyEodSessionError(EodSessionIngestionError):
    """Raised when a provider returns no bars for a required session."""


class EodSessionValidationError(EodSessionIngestionError):
    """Raised when provider-returned canonical bars fail session validation."""


@dataclass(frozen=True)
class EodSessionIngestionResult:
    """Non-sensitive audit result for one EOD session ingestion."""

    schema_version: str
    session_date: date
    provider_id: str
    fetched_record_count: int
    validated_record_count: int
    written_record_count: int
    partition_path: Path
    content_sha256: str
    status: str


@dataclass(frozen=True)
class EodSessionIngestionService:
    """Coordinate provider-neutral one-session EOD bar ingestion."""

    provider: MarketDataProvider
    repository: EodPriceBarRepository
    instrument_ids: tuple[UUID, ...]

    def ingest_session(self, session_date: date) -> EodSessionIngestionResult:
        """Fetch, validate, and publish exactly one EOD session."""

        if not self.instrument_ids:
            raise EodSessionValidationError("instrument_ids must contain at least one UUID")
        query = EodBarQuery(
            instrument_ids=self.instrument_ids,
            start_date=session_date,
            end_date=session_date,
            revision_selection=RevisionSelection.LATEST,
        )
        fetched = self.provider.get_eod_bars(query)
        if len(fetched) == 0:
            raise EmptyEodSessionError("provider returned no EOD bars for the requested session")
        validated = _validate_one_session_records(fetched, session_date=session_date)
        write_result = self.repository.publish_session(
            validated,
            session_date=session_date,
            provider_id=self.provider.provider_id,
        )
        return EodSessionIngestionResult(
            schema_version=write_result.schema_version,
            session_date=session_date,
            provider_id=self.provider.provider_id,
            fetched_record_count=len(fetched),
            validated_record_count=len(validated),
            written_record_count=write_result.written_record_count,
            partition_path=write_result.partition_path,
            content_sha256=write_result.content_sha256,
            status=write_result.status,
        )


def _validate_one_session_records(
    records: tuple[EodPriceBarV1, ...],
    *,
    session_date: date,
) -> tuple[EodPriceBarV1, ...]:
    business_keys: set[tuple[str, str, str, int]] = set()
    latest_counts: dict[tuple[str, str, str], int] = {}
    for record in records:
        if record.session_date != session_date:
            raise EodSessionValidationError("provider returned a bar outside the requested session_date")
        key = record_business_key(record)
        if key in business_keys:
            raise EodSessionValidationError("provider returned duplicate EOD Price Bar business keys")
        business_keys.add(key)
        if record.is_latest_revision:
            latest_key = logical_revision_key(record)
            latest_counts[latest_key] = latest_counts.get(latest_key, 0) + 1
            if latest_counts[latest_key] > 1:
                raise EodSessionValidationError("provider returned contradictory latest EOD revisions")
    return sort_eod_bars(records)
