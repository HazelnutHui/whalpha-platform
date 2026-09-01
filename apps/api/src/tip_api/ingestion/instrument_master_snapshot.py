"""Point-in-time Instrument Master snapshot ingestion service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from tip_api.contracts.market_data.v1 import InstrumentMasterV1, ProviderInstrumentIdentityV1, ProviderTickerResolverV1
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotRepository

SNAPSHOT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class InstrumentMasterSnapshotQualityGates:
    minimum_raw_records: int = 5000
    minimum_eligible_identity_coverage_ratio: float = 0.80
    maximum_malformed_ratio: float = 0.01
    maximum_ticker_ambiguity_ratio: float = 0.001
    maximum_stable_identifier_collision_ratio: float = 0.001
    maximum_request_count: int = 20


@dataclass(frozen=True)
class InstrumentMasterSnapshotIngestionResult:
    schema_version: str
    as_of_date: date
    provider: str
    request_count: int
    raw_record_count: int
    eligible_record_count: int
    expected_exclusion_count: int
    malformed_rejected_count: int
    resolved_eligible_count: int
    unresolved_eligible_count: int
    ambiguous_ticker_record_count: int
    stable_identifier_collision_count: int
    canonical_instrument_count: int
    resolver_entry_count: int
    unique_provider_ticker_count: int
    duplicate_provider_ticker_count: int
    eligible_identity_coverage_ratio: float
    malformed_ratio: float
    expected_exclusion_ratio: float
    ticker_ambiguity_ratio: float
    stable_identifier_collision_ratio: float
    written_instrument_count: int
    written_identity_count: int
    written_resolver_count: int
    instrument_content_sha256: str | None
    identity_content_sha256: str | None
    resolver_content_sha256: str | None
    snapshot_content_sha256: str | None
    instrument_partition_path: Path | None
    identity_partition_path: Path | None
    resolver_partition_path: Path | None
    snapshot_manifest_path: Path | None
    status: Literal["published", "already_present", "quality_gate_failed"]
    quality_gate_passed: bool
    quality_gate_failures: tuple[str, ...]

    def safe_lines(self) -> tuple[str, ...]:
        pairs = (
            ("schema_version", self.schema_version), ("as_of_date", self.as_of_date.isoformat()), ("provider", self.provider),
            ("request_count", self.request_count), ("raw_record_count", self.raw_record_count),
            ("eligible_record_count", self.eligible_record_count), ("expected_exclusion_count", self.expected_exclusion_count),
            ("malformed_rejected_count", self.malformed_rejected_count), ("resolved_eligible_count", self.resolved_eligible_count),
            ("unresolved_eligible_count", self.unresolved_eligible_count), ("ambiguous_ticker_record_count", self.ambiguous_ticker_record_count),
            ("stable_identifier_collision_count", self.stable_identifier_collision_count), ("canonical_instrument_count", self.canonical_instrument_count),
            ("resolver_entry_count", self.resolver_entry_count), ("unique_provider_ticker_count", self.unique_provider_ticker_count),
            ("duplicate_provider_ticker_count", self.duplicate_provider_ticker_count),
            ("eligible_identity_coverage_ratio", f"{self.eligible_identity_coverage_ratio:.6f}"),
            ("malformed_ratio", f"{self.malformed_ratio:.6f}"), ("expected_exclusion_ratio", f"{self.expected_exclusion_ratio:.6f}"),
            ("ticker_ambiguity_ratio", f"{self.ticker_ambiguity_ratio:.6f}"),
            ("stable_identifier_collision_ratio", f"{self.stable_identifier_collision_ratio:.6f}"),
            ("written_instrument_count", self.written_instrument_count), ("written_identity_count", self.written_identity_count),
            ("written_resolver_count", self.written_resolver_count), ("instrument_content_sha256", self.instrument_content_sha256 or ""),
            ("identity_content_sha256", self.identity_content_sha256 or ""), ("resolver_content_sha256", self.resolver_content_sha256 or ""),
            ("snapshot_content_sha256", self.snapshot_content_sha256 or ""), ("quality_gate_passed", str(self.quality_gate_passed).lower()),
            ("quality_gate_failures", ",".join(self.quality_gate_failures)), ("publish_ready", str(self.quality_gate_passed).lower()),
            ("status", self.status),
        )
        return tuple(f"{key}={value}" for key, value in pairs)


class InstrumentMasterSnapshotIngestionService:
    def __init__(self, *, repository: InstrumentMasterSnapshotRepository, gates: InstrumentMasterSnapshotQualityGates | None = None) -> None:
        self._repository = repository
        self._gates = gates or InstrumentMasterSnapshotQualityGates()

    def publish_snapshot(self, *, as_of_date: date, provider_id: str, instruments: tuple[InstrumentMasterV1, ...], identities: tuple[ProviderInstrumentIdentityV1, ...], resolvers: tuple[ProviderTickerResolverV1, ...], request_count: int, raw_record_count: int, eligible_record_count: int, expected_exclusion_count: int, malformed_rejected_count: int, resolved_eligible_count: int, unresolved_eligible_count: int, ambiguous_ticker_record_count: int, stable_identifier_collision_count: int, unique_provider_ticker_count: int, duplicate_provider_ticker_count: int) -> InstrumentMasterSnapshotIngestionResult:
        eligible_denominator = (
            resolved_eligible_count
            + unresolved_eligible_count
            + ambiguous_ticker_record_count
            + stable_identifier_collision_count
        )
        coverage = resolved_eligible_count / eligible_denominator if eligible_denominator else 0.0
        malformed_ratio = malformed_rejected_count / raw_record_count if raw_record_count else 1.0
        exclusion_ratio = expected_exclusion_count / raw_record_count if raw_record_count else 0.0
        ambiguity_ratio = ambiguous_ticker_record_count / eligible_denominator if eligible_denominator else 0.0
        collision_ratio = stable_identifier_collision_count / eligible_denominator if eligible_denominator else 0.0
        failures = self._quality_gate_failures(request_count=request_count, raw_record_count=raw_record_count, eligible_record_count=eligible_record_count, expected_exclusion_count=expected_exclusion_count, malformed_rejected_count=malformed_rejected_count, resolved_eligible_count=resolved_eligible_count, unresolved_eligible_count=unresolved_eligible_count, ambiguous_ticker_record_count=ambiguous_ticker_record_count, stable_identifier_collision_count=stable_identifier_collision_count, instruments=instruments, identities=identities, resolvers=resolvers, as_of_date=as_of_date, coverage=coverage, malformed_ratio=malformed_ratio, ambiguity_ratio=ambiguity_ratio, collision_ratio=collision_ratio)
        if failures:
            return self._result(as_of_date, provider_id, request_count, raw_record_count, eligible_record_count, expected_exclusion_count, malformed_rejected_count, resolved_eligible_count, unresolved_eligible_count, ambiguous_ticker_record_count, stable_identifier_collision_count, len(instruments), len(resolvers), unique_provider_ticker_count, duplicate_provider_ticker_count, coverage, malformed_ratio, exclusion_ratio, ambiguity_ratio, collision_ratio, 0, 0, 0, None, None, None, None, None, None, None, None, "quality_gate_failed", False, failures)
        write_result = self._repository.publish_snapshot(instruments=instruments, identities=identities, resolvers=resolvers, as_of_date=as_of_date, provider_id=provider_id, quality_summary={"raw_record_count": raw_record_count, "eligible_record_count": eligible_record_count, "expected_exclusion_count": expected_exclusion_count, "malformed_rejected_count": malformed_rejected_count, "resolved_eligible_count": resolved_eligible_count, "unresolved_eligible_count": unresolved_eligible_count, "ambiguous_ticker_record_count": ambiguous_ticker_record_count, "stable_identifier_collision_count": stable_identifier_collision_count, "eligible_identity_coverage_ratio": coverage, "malformed_ratio": malformed_ratio, "expected_exclusion_ratio": exclusion_ratio, "ticker_ambiguity_ratio": ambiguity_ratio, "stable_identifier_collision_ratio": collision_ratio})
        return self._result(as_of_date, provider_id, request_count, raw_record_count, eligible_record_count, expected_exclusion_count, malformed_rejected_count, resolved_eligible_count, unresolved_eligible_count, ambiguous_ticker_record_count, stable_identifier_collision_count, len(instruments), len(resolvers), unique_provider_ticker_count, duplicate_provider_ticker_count, coverage, malformed_ratio, exclusion_ratio, ambiguity_ratio, collision_ratio, write_result.written_instrument_count, write_result.written_identity_count, write_result.written_resolver_count, write_result.instrument_content_sha256, write_result.identity_content_sha256, write_result.resolver_content_sha256, write_result.snapshot_content_sha256, write_result.instrument_partition_path, write_result.identity_partition_path, write_result.resolver_partition_path, write_result.snapshot_manifest_path, write_result.status, True, ())

    def _quality_gate_failures(self, **kwargs) -> tuple[str, ...]:
        g = self._gates; failures=[]
        if kwargs["raw_record_count"] <= g.minimum_raw_records: failures.append("raw_record_count_below_gate")
        if kwargs["request_count"] > g.maximum_request_count: failures.append("request_count_above_gate")
        if kwargs["collision_ratio"] > g.maximum_stable_identifier_collision_ratio: failures.append("stable_identifier_collision_ratio_above_gate")
        if kwargs["malformed_ratio"] > g.maximum_malformed_ratio: failures.append("malformed_ratio_above_gate")
        if kwargs["coverage"] < g.minimum_eligible_identity_coverage_ratio: failures.append("eligible_identity_coverage_below_gate")
        if kwargs["ambiguity_ratio"] > g.maximum_ticker_ambiguity_ratio: failures.append("ticker_ambiguity_ratio_above_gate")
        if len(kwargs["instruments"]) != kwargs["resolved_eligible_count"]: failures.append("canonical_instrument_count_mismatch")
        if len(kwargs["identities"]) != kwargs["raw_record_count"]: failures.append("identity_record_count_mismatch")
        if any(r.as_of_date != kwargs["as_of_date"] for r in kwargs["instruments"]): failures.append("instrument_as_of_date_mismatch")
        if any(r.as_of_date != kwargs["as_of_date"] for r in kwargs["identities"]): failures.append("identity_as_of_date_mismatch")
        if any(r.as_of_date != kwargs["as_of_date"] for r in kwargs["resolvers"]): failures.append("resolver_as_of_date_mismatch")
        return tuple(failures)

    def _result(self, *args) -> InstrumentMasterSnapshotIngestionResult:
        return InstrumentMasterSnapshotIngestionResult(SNAPSHOT_SCHEMA_VERSION, *args)
