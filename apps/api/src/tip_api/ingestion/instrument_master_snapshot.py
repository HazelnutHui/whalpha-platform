"""Point-in-time Instrument Master snapshot ingestion service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from tip_api.contracts.market_data.v1 import InstrumentMasterV1, ProviderInstrumentIdentityV1
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotRepository

SNAPSHOT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class InstrumentMasterSnapshotQualityGates:
    """V1 candidate quality gates for publishing a reference snapshot."""

    minimum_raw_records: int = 5000
    minimum_unique_ticker_ratio: float = 0.999
    minimum_identity_coverage_ratio: float = 0.80
    maximum_rejected_ratio: float = 0.05
    maximum_request_count: int = 20


@dataclass(frozen=True)
class InstrumentMasterSnapshotIngestionResult:
    """Non-sensitive result for a point-in-time Instrument Master snapshot."""

    schema_version: str
    as_of_date: date
    provider: str
    request_count: int
    raw_record_count: int
    unique_ticker_count: int
    duplicate_ticker_count: int
    resolved_count: int
    unresolved_count: int
    ambiguous_count: int
    rejected_count: int
    canonical_instrument_count: int
    identity_coverage_ratio: float
    written_instrument_count: int
    written_identity_count: int
    instrument_content_sha256: str | None
    identity_content_sha256: str | None
    snapshot_content_sha256: str | None
    instrument_partition_path: Path | None
    identity_partition_path: Path | None
    snapshot_manifest_path: Path | None
    status: Literal["published", "already_present", "quality_gate_failed"]
    quality_gate_passed: bool
    quality_gate_failures: tuple[str, ...]

    def safe_lines(self) -> tuple[str, ...]:
        pairs = (
            ("schema_version", self.schema_version),
            ("as_of_date", self.as_of_date.isoformat()),
            ("provider", self.provider),
            ("request_count", self.request_count),
            ("raw_record_count", self.raw_record_count),
            ("unique_ticker_count", self.unique_ticker_count),
            ("duplicate_ticker_count", self.duplicate_ticker_count),
            ("resolved_count", self.resolved_count),
            ("unresolved_count", self.unresolved_count),
            ("ambiguous_count", self.ambiguous_count),
            ("rejected_count", self.rejected_count),
            ("canonical_instrument_count", self.canonical_instrument_count),
            ("identity_coverage_ratio", f"{self.identity_coverage_ratio:.6f}"),
            ("written_instrument_count", self.written_instrument_count),
            ("written_identity_count", self.written_identity_count),
            ("instrument_content_sha256", self.instrument_content_sha256 or ""),
            ("identity_content_sha256", self.identity_content_sha256 or ""),
            ("snapshot_content_sha256", self.snapshot_content_sha256 or ""),
            ("quality_gate_passed", str(self.quality_gate_passed).lower()),
            ("quality_gate_failures", ",".join(self.quality_gate_failures)),
            ("status", self.status),
        )
        return tuple(f"{key}={value}" for key, value in pairs)


class InstrumentMasterSnapshotIngestionService:
    """Validate and publish a bounded point-in-time Instrument Master snapshot."""

    def __init__(
        self,
        *,
        repository: InstrumentMasterSnapshotRepository,
        gates: InstrumentMasterSnapshotQualityGates | None = None,
    ) -> None:
        self._repository = repository
        self._gates = gates or InstrumentMasterSnapshotQualityGates()

    def publish_snapshot(
        self,
        *,
        as_of_date: date,
        provider_id: str,
        instruments: tuple[InstrumentMasterV1, ...],
        identities: tuple[ProviderInstrumentIdentityV1, ...],
        request_count: int,
        raw_record_count: int,
        unique_ticker_count: int,
        duplicate_ticker_count: int,
        resolved_count: int,
        unresolved_count: int,
        ambiguous_count: int,
        rejected_count: int,
    ) -> InstrumentMasterSnapshotIngestionResult:
        failures = self._quality_gate_failures(
            request_count=request_count,
            raw_record_count=raw_record_count,
            unique_ticker_count=unique_ticker_count,
            duplicate_ticker_count=duplicate_ticker_count,
            resolved_count=resolved_count,
            ambiguous_count=ambiguous_count,
            rejected_count=rejected_count,
            instruments=instruments,
            identities=identities,
            as_of_date=as_of_date,
        )
        coverage = resolved_count / raw_record_count if raw_record_count else 0.0
        if failures:
            return InstrumentMasterSnapshotIngestionResult(
                schema_version=SNAPSHOT_SCHEMA_VERSION,
                as_of_date=as_of_date,
                provider=provider_id,
                request_count=request_count,
                raw_record_count=raw_record_count,
                unique_ticker_count=unique_ticker_count,
                duplicate_ticker_count=duplicate_ticker_count,
                resolved_count=resolved_count,
                unresolved_count=unresolved_count,
                ambiguous_count=ambiguous_count,
                rejected_count=rejected_count,
                canonical_instrument_count=len(instruments),
                identity_coverage_ratio=coverage,
                written_instrument_count=0,
                written_identity_count=0,
                instrument_content_sha256=None,
                identity_content_sha256=None,
                snapshot_content_sha256=None,
                instrument_partition_path=None,
                identity_partition_path=None,
                snapshot_manifest_path=None,
                status="quality_gate_failed",
                quality_gate_passed=False,
                quality_gate_failures=failures,
            )
        write_result = self._repository.publish_snapshot(
            instruments=instruments,
            identities=identities,
            as_of_date=as_of_date,
            provider_id=provider_id,
            quality_summary={
                "raw_record_count": raw_record_count,
                "unique_ticker_count": unique_ticker_count,
                "duplicate_ticker_count": duplicate_ticker_count,
                "resolved_count": resolved_count,
                "unresolved_count": unresolved_count,
                "ambiguous_count": ambiguous_count,
                "rejected_count": rejected_count,
                "identity_coverage_ratio": coverage,
            },
        )
        return InstrumentMasterSnapshotIngestionResult(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            as_of_date=as_of_date,
            provider=provider_id,
            request_count=request_count,
            raw_record_count=raw_record_count,
            unique_ticker_count=unique_ticker_count,
            duplicate_ticker_count=duplicate_ticker_count,
            resolved_count=resolved_count,
            unresolved_count=unresolved_count,
            ambiguous_count=ambiguous_count,
            rejected_count=rejected_count,
            canonical_instrument_count=len(instruments),
            identity_coverage_ratio=coverage,
            written_instrument_count=write_result.written_instrument_count,
            written_identity_count=write_result.written_identity_count,
            instrument_content_sha256=write_result.instrument_content_sha256,
            identity_content_sha256=write_result.identity_content_sha256,
            snapshot_content_sha256=write_result.snapshot_content_sha256,
            instrument_partition_path=write_result.instrument_partition_path,
            identity_partition_path=write_result.identity_partition_path,
            snapshot_manifest_path=write_result.snapshot_manifest_path,
            status=write_result.status,
            quality_gate_passed=True,
            quality_gate_failures=(),
        )

    def _quality_gate_failures(
        self,
        *,
        request_count: int,
        raw_record_count: int,
        unique_ticker_count: int,
        duplicate_ticker_count: int,
        resolved_count: int,
        ambiguous_count: int,
        rejected_count: int,
        instruments: tuple[InstrumentMasterV1, ...],
        identities: tuple[ProviderInstrumentIdentityV1, ...],
        as_of_date: date,
    ) -> tuple[str, ...]:
        failures: list[str] = []
        gates = self._gates
        if raw_record_count <= gates.minimum_raw_records:
            failures.append("raw_record_count_below_gate")
        unique_ratio = unique_ticker_count / raw_record_count if raw_record_count else 0.0
        if unique_ratio < gates.minimum_unique_ticker_ratio:
            failures.append("unique_ticker_ratio_below_gate")
        coverage = resolved_count / raw_record_count if raw_record_count else 0.0
        if coverage < gates.minimum_identity_coverage_ratio:
            failures.append("identity_coverage_below_gate")
        rejected_ratio = rejected_count / raw_record_count if raw_record_count else 1.0
        if rejected_ratio > gates.maximum_rejected_ratio:
            failures.append("rejected_ratio_above_gate")
        if ambiguous_count != 0:
            failures.append("ambiguous_identity_count_nonzero")
        if request_count > gates.maximum_request_count:
            failures.append("request_count_above_gate")
        if duplicate_ticker_count != 0:
            failures.append("duplicate_ticker_count_nonzero")
        if len(instruments) != resolved_count:
            failures.append("canonical_instrument_count_mismatch")
        if len(identities) != raw_record_count:
            failures.append("identity_record_count_mismatch")
        if any(record.as_of_date != as_of_date for record in instruments):
            failures.append("instrument_as_of_date_mismatch")
        if any(record.as_of_date != as_of_date for record in identities):
            failures.append("identity_as_of_date_mismatch")
        return tuple(failures)

