"""Classify unresolved corporate-action tickers across bound Identity history."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from multiprocessing import get_context
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.services import historical_corporate_action_resolution_shadow as shadow_module


CONTRACT_VERSION = "historical-corporate-action-unresolved-census/1.0"
RECORD_SET_CONTRACT_VERSION = (
    "historical-corporate-action-unresolved-census-record-set/1.0"
)
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
MANIFEST_FILE = "manifest.json"
RECORDS_FILE = "ticker-candidates.json"
DEFAULT_HISTORY_WORKERS = min(8, os.cpu_count() or 1)
MAXIMUM_HISTORY_WORKERS = 32
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_BUILD_NAME_PATTERN = r"^build=[A-Za-z0-9._-]+$"
_CLASSIFICATIONS = (
    "multiple_historical_candidates",
    "one_historical_candidate",
    "zero_historical_candidates",
)
_FAILURE_REASONS = (
    "event_date_identity_unavailable",
    "unresolved_ticker",
)


class HistoricalCorporateActionUnresolvedCensusError(RuntimeError):
    """Raised when the unresolved-ticker census cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalCandidateOccurrenceV1(_FrozenModel):
    instrument_id: UUID
    first_observed_session: date
    last_observed_session: date
    observed_session_count: int = Field(ge=1)

    @model_validator(mode="after")
    def session_range_reconciles(self) -> "HistoricalCandidateOccurrenceV1":
        if self.last_observed_session < self.first_observed_session:
            raise ValueError("historical candidate session range is reversed")
        return self


class UnresolvedTickerCandidateCensusV1(_FrozenModel):
    provider_ticker: str
    classification: Literal[
        "zero_historical_candidates",
        "one_historical_candidate",
        "multiple_historical_candidates",
    ]
    unresolved_source_record_count: int = Field(ge=1)
    exact_date_identity_unavailable_count: int = Field(ge=0)
    exact_date_ticker_absent_count: int = Field(ge=0)
    action_type_counts: tuple[tuple[str, int], ...]
    candidates: tuple[HistoricalCandidateOccurrenceV1, ...]

    @field_validator("provider_ticker")
    @classmethod
    def ticker_is_normalized(cls, value: str) -> str:
        if not value or value != value.strip().upper():
            raise ValueError("unresolved provider ticker is not normalized")
        return value

    @model_validator(mode="after")
    def row_reconciles(self) -> "UnresolvedTickerCandidateCensusV1":
        if (
            self.exact_date_identity_unavailable_count
            + self.exact_date_ticker_absent_count
            != self.unresolved_source_record_count
        ):
            raise ValueError("unresolved ticker failure-reason counts differ")
        if (
            self.action_type_counts != tuple(sorted(self.action_type_counts))
            or any(count < 1 for _, count in self.action_type_counts)
            or sum(count for _, count in self.action_type_counts)
            != self.unresolved_source_record_count
        ):
            raise ValueError("unresolved ticker action-type counts differ")
        candidate_ids = tuple(str(item.instrument_id) for item in self.candidates)
        if candidate_ids != tuple(sorted(set(candidate_ids))):
            raise ValueError("historical candidate IDs are not unique and ordered")
        expected_classification = (
            "zero_historical_candidates"
            if not self.candidates
            else (
                "one_historical_candidate"
                if len(self.candidates) == 1
                else "multiple_historical_candidates"
            )
        )
        if self.classification != expected_classification:
            raise ValueError("historical candidate classification differs")
        return self


class UnresolvedTickerCandidateSetV1(_FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-unresolved-census-record-set/1.0"
    ] = RECORD_SET_CONTRACT_VERSION
    records: tuple[UnresolvedTickerCandidateCensusV1, ...]
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def record_set_reconciles(self) -> "UnresolvedTickerCandidateSetV1":
        tickers = tuple(item.provider_ticker for item in self.records)
        if not tickers or tickers != tuple(sorted(set(tickers))):
            raise ValueError("unresolved ticker records are empty, duplicated, or unordered")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("unresolved ticker record-set fingerprint differs")
        return self


class HistoricalCorporateActionUnresolvedCensusManifestV1(_FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-unresolved-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "historical-corporate-action-unresolved-census"
    ] = "historical-corporate-action-unresolved-census"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    resolution_shadow_path: str
    resolution_shadow_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    resolution_shadow_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    resolution_shadow_source_record_count: int = Field(ge=1)
    resolution_shadow_typed_record_count: int = Field(ge=1)
    unresolved_typed_record_count: int = Field(ge=1)
    unrepresentable_source_record_count: int = Field(ge=0)
    unresolved_unique_ticker_count: int = Field(ge=1)
    identity_first_session: date
    identity_last_session: date
    identity_session_count: int = Field(ge=1)
    identity_evidence_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    scanned_resolver_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    scanned_resolver_session_count: int = Field(ge=1)
    process_count: int = Field(ge=1, le=MAXIMUM_HISTORY_WORKERS)
    ticker_classification_counts: tuple[tuple[str, int], ...]
    source_record_classification_counts: tuple[tuple[str, int], ...]
    action_type_classification_counts: tuple[tuple[str, str, int], ...]
    failure_reason_classification_counts: tuple[tuple[str, str, int], ...]
    candidate_relation_count: int = Field(ge=0)
    distinct_candidate_instrument_count: int = Field(ge=0)
    records_file: Literal["ticker-candidates.json"] = RECORDS_FILE
    records_file_sha256: str = Field(pattern=_SHA256_PATTERN)
    records_file_bytes: int = Field(ge=1, le=MAXIMUM_JSON_BYTES)
    records_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    evidence_role: Literal["quarantine_diagnostic_only"] = (
        "quarantine_diagnostic_only"
    )
    stable_identity_assignment_count: Literal[0] = 0
    source_record_mutation_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("resolution_shadow_path")
    @classmethod
    def shadow_path_is_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
        ):
            raise ValueError("resolution shadow path is not normalized and relative")
        return value

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "HistoricalCorporateActionUnresolvedCensusManifestV1":
        if self.identity_last_session < self.identity_first_session:
            raise ValueError("unresolved census Identity range is reversed")
        if self.resolution_shadow_typed_record_count + self.unrepresentable_source_record_count != (
            self.resolution_shadow_source_record_count
        ):
            raise ValueError("unresolved census source accounting differs")
        if self.unresolved_typed_record_count > self.resolution_shadow_typed_record_count:
            raise ValueError("unresolved census typed population differs")
        if self.scanned_resolver_session_count != self.identity_session_count:
            raise ValueError("unresolved census Resolver session count differs")
        if (
            self.ticker_classification_counts
            != tuple(sorted(self.ticker_classification_counts))
            or tuple(key for key, _ in self.ticker_classification_counts)
            != _CLASSIFICATIONS
            or any(count < 0 for _, count in self.ticker_classification_counts)
            or sum(count for _, count in self.ticker_classification_counts)
            != self.unresolved_unique_ticker_count
        ):
            raise ValueError("unresolved census ticker classifications differ")
        if (
            self.source_record_classification_counts
            != tuple(sorted(self.source_record_classification_counts))
            or tuple(key for key, _ in self.source_record_classification_counts)
            != _CLASSIFICATIONS
            or any(count < 0 for _, count in self.source_record_classification_counts)
            or sum(count for _, count in self.source_record_classification_counts)
            != self.unresolved_typed_record_count
        ):
            raise ValueError("unresolved census source-row classifications differ")
        if any(
            count < 1
            for _, _, count in (
                self.action_type_classification_counts
                + self.failure_reason_classification_counts
            )
        ):
            raise ValueError("unresolved census matrix count differs")
        if sum(count for _, _, count in self.action_type_classification_counts) != (
            self.unresolved_typed_record_count
        ):
            raise ValueError("unresolved census action matrix differs")
        if sum(count for _, _, count in self.failure_reason_classification_counts) != (
            self.unresolved_typed_record_count
        ):
            raise ValueError("unresolved census failure matrix differs")
        if self.action_type_classification_counts != tuple(
            sorted(self.action_type_classification_counts)
        ) or self.failure_reason_classification_counts != tuple(
            sorted(self.failure_reason_classification_counts)
        ):
            raise ValueError("unresolved census matrices are unordered")
        values = self.model_dump(
            mode="json", exclude={"logical_fingerprint", "process_count"}
        )
        if self.logical_fingerprint != _fingerprint(values):
            raise ValueError("unresolved census manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class HistoricalCorporateActionUnresolvedCensusResult:
    output_root: Path
    manifest: HistoricalCorporateActionUnresolvedCensusManifestV1
    records: tuple[UnresolvedTickerCandidateCensusV1, ...]
    manifest_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _TickerSourceStats:
    record_count: int
    unavailable_count: int
    absent_count: int
    action_type_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class _HistoryScanChunk:
    sessions: tuple[date, ...]
    bindings: tuple[dict[str, object], ...]
    observations: Mapping[str, Mapping[UUID, tuple[date, date, int]]]


@dataclass(frozen=True, slots=True)
class _HistoryScan:
    session_count: int
    process_count: int
    resolver_binding_fingerprint: str
    observations: Mapping[str, Mapping[UUID, tuple[date, date, int]]]


def build_historical_corporate_action_unresolved_census(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
    max_workers: int = DEFAULT_HISTORY_WORKERS,
) -> HistoricalCorporateActionUnresolvedCensusResult:
    """Build one immutable, assignment-free unresolved-ticker census."""

    with _network_prohibited():
        return _build_census(
            data_root=data_root,
            resolution_shadow_output_root=resolution_shadow_output_root,
            resolution_shadow_custody_root=resolution_shadow_custody_root,
            output_root=output_root,
            output_custody_root=output_custody_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
            max_workers=max_workers,
        )


def _build_census(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
    max_workers: int,
) -> HistoricalCorporateActionUnresolvedCensusResult:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census implementation revision is invalid"
        )
    canonical_root = _validated_data_root(data_root)
    target = _validated_output_target(output_root, output_custody_root)
    evaluated_at = normalize_utc_datetime(evaluated_at)
    shadow = _read_shadow(
        output_root=resolution_shadow_output_root,
        custody_root=resolution_shadow_custody_root,
    )
    if evaluated_at < shadow.manifest.materialized_at:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census evaluation precedes its resolution shadow"
        )
    unresolved_rows = tuple(
        item
        for item in shadow.records
        if item.instrument_resolution_status is ResolutionStatus.UNRESOLVED
    )
    if not unresolved_rows or any(item.instrument_id is not None for item in unresolved_rows):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census source population is invalid"
        )
    source_stats = _source_stats(unresolved_rows)
    identity = shadow_module._read_bound_identity_set(  # noqa: SLF001
        canonical_root, shadow.manifest
    )
    scan = _scan_identity_history(
        root=canonical_root,
        identity=identity,
        requested_tickers=frozenset(source_stats),
        max_workers=max_workers,
    )
    records = _candidate_records(source_stats=source_stats, scan=scan)
    record_values = {
        "contract_version": RECORD_SET_CONTRACT_VERSION,
        "records": records,
    }
    record_set = UnresolvedTickerCandidateSetV1.model_validate(
        {
            **record_values,
            "logical_fingerprint": _fingerprint(record_values),
        }
    )
    record_bytes = _json_bytes(record_set.model_dump(mode="json"))
    if len(record_bytes) > MAXIMUM_JSON_BYTES:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census record set exceeds byte ceiling"
        )
    manifest = _build_manifest(
        implementation_revision=implementation_revision,
        evaluated_at=evaluated_at,
        shadow=shadow,
        shadow_output_root=resolution_shadow_output_root,
        shadow_custody_root=resolution_shadow_custody_root,
        identity=identity,
        scan=scan,
        record_set=record_set,
        record_bytes=record_bytes,
    )

    if target.exists() or target.is_symlink():
        existing = read_historical_corporate_action_unresolved_census(
            data_root=canonical_root,
            resolution_shadow_output_root=resolution_shadow_output_root,
            resolution_shadow_custody_root=resolution_shadow_custody_root,
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if (
            existing.records != records
            or existing.manifest.logical_fingerprint != manifest.logical_fingerprint
        ):
            raise HistoricalCorporateActionUnresolvedCensusError(
                "existing unresolved census differs"
            )
        return existing

    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(partial / RECORDS_FILE, record_bytes)
        manifest_bytes = _json_bytes(manifest.model_dump(mode="json"))
        _write_exclusive(partial / MANIFEST_FILE, manifest_bytes)
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise

    reread = read_historical_corporate_action_unresolved_census(
        data_root=canonical_root,
        resolution_shadow_output_root=resolution_shadow_output_root,
        resolution_shadow_custody_root=resolution_shadow_custody_root,
        output_root=target,
        output_custody_root=output_custody_root,
    )
    if reread.records != records or reread.manifest != manifest:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census formal reread differs"
        )
    return HistoricalCorporateActionUnresolvedCensusResult(
        output_root=reread.output_root,
        manifest=reread.manifest,
        records=reread.records,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def read_historical_corporate_action_unresolved_census(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> HistoricalCorporateActionUnresolvedCensusResult:
    """Formally reread the census and its immutable source bindings."""

    canonical_root = _validated_data_root(data_root)
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {MANIFEST_FILE, RECORDS_FILE}:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census package members differ"
        )
    manifest_path = root / MANIFEST_FILE
    records_path = root / RECORDS_FILE
    _require_regular_file(manifest_path, 0o400)
    _require_regular_file(records_path, 0o400)
    manifest_bytes = _read_bounded_bytes(manifest_path)
    records_bytes = _read_bounded_bytes(records_path)
    try:
        manifest = HistoricalCorporateActionUnresolvedCensusManifestV1.model_validate_json(
            manifest_bytes
        )
        record_set = UnresolvedTickerCandidateSetV1.model_validate_json(records_bytes)
    except Exception as exc:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census output is invalid"
        ) from exc
    if (
        manifest.records_file_sha256 != _sha256(records_bytes)
        or manifest.records_file_bytes != len(records_bytes)
        or manifest.records_logical_fingerprint != record_set.logical_fingerprint
    ):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census record-set binding differs"
        )
    shadow = _read_shadow(
        output_root=resolution_shadow_output_root,
        custody_root=resolution_shadow_custody_root,
    )
    identity = shadow_module._read_bound_identity_set(  # noqa: SLF001
        canonical_root, shadow.manifest
    )
    _verify_manifest_bindings(
        manifest=manifest,
        shadow=shadow,
        shadow_output_root=resolution_shadow_output_root,
        shadow_custody_root=resolution_shadow_custody_root,
        identity=identity,
    )
    unresolved_rows = tuple(
        item
        for item in shadow.records
        if item.instrument_resolution_status is ResolutionStatus.UNRESOLVED
    )
    source_stats = _source_stats(unresolved_rows)
    if frozenset(source_stats) != frozenset(
        item.provider_ticker for item in record_set.records
    ):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census ticker population differs from source"
        )
    scan = _scan_identity_history(
        root=canonical_root,
        identity=identity,
        requested_tickers=frozenset(source_stats),
        max_workers=manifest.process_count,
    )
    if (
        scan.resolver_binding_fingerprint
        != manifest.scanned_resolver_binding_fingerprint
        or _candidate_records(source_stats=source_stats, scan=scan)
        != record_set.records
    ):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census full Resolver reread differs"
        )
    _verify_record_aggregates(manifest, record_set.records)
    return HistoricalCorporateActionUnresolvedCensusResult(
        output_root=root,
        manifest=manifest,
        records=record_set.records,
        manifest_sha256=_sha256(manifest_bytes),
        status="already_present",
    )


def read_historical_corporate_action_unresolved_census_output(
    *,
    output_root: Path,
    output_custody_root: Path,
) -> HistoricalCorporateActionUnresolvedCensusResult:
    """Validate one immutable output without repeating its upstream history scan.

    A downstream consumer must separately bind the returned manifest to the
    formally reread resolution shadow it uses. This reader proves only the
    completed package's custody, canonical bytes, self-fingerprint, and
    aggregate reconciliation.
    """

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {MANIFEST_FILE, RECORDS_FILE}:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census package members differ"
        )
    manifest_path = root / MANIFEST_FILE
    records_path = root / RECORDS_FILE
    _require_regular_file(manifest_path, 0o400)
    _require_regular_file(records_path, 0o400)
    manifest_bytes = _read_bounded_bytes(manifest_path)
    records_bytes = _read_bounded_bytes(records_path)
    try:
        manifest = HistoricalCorporateActionUnresolvedCensusManifestV1.model_validate_json(
            manifest_bytes
        )
        record_set = UnresolvedTickerCandidateSetV1.model_validate_json(records_bytes)
    except Exception as exc:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census output is invalid"
        ) from exc
    if (
        manifest.records_file_sha256 != _sha256(records_bytes)
        or manifest.records_file_bytes != len(records_bytes)
        or manifest.records_logical_fingerprint != record_set.logical_fingerprint
    ):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census record-set binding differs"
        )
    _verify_record_aggregates(manifest, record_set.records)
    return HistoricalCorporateActionUnresolvedCensusResult(
        output_root=root,
        manifest=manifest,
        records=record_set.records,
        manifest_sha256=_sha256(manifest_bytes),
        status="already_present",
    )


def _source_stats(rows: tuple[object, ...]) -> dict[str, _TickerSourceStats]:
    mutable: dict[str, dict[str, object]] = {}
    for raw in rows:
        ticker = raw.provider_ticker
        if not ticker or ticker != ticker.strip().upper():
            raise HistoricalCorporateActionUnresolvedCensusError(
                "unresolved source ticker is not normalized"
            )
        failure_flags = tuple(flag for flag in raw.quality_flags if flag in _FAILURE_REASONS)
        if len(failure_flags) != 1:
            raise HistoricalCorporateActionUnresolvedCensusError(
                "unresolved source row has an invalid exact-date failure reason"
            )
        current = mutable.setdefault(
            ticker,
            {
                "record_count": 0,
                "unavailable_count": 0,
                "absent_count": 0,
                "action_types": Counter(),
            },
        )
        current["record_count"] += 1
        if failure_flags[0] == "event_date_identity_unavailable":
            current["unavailable_count"] += 1
        else:
            current["absent_count"] += 1
        current["action_types"][raw.action_type.value] += 1
    return {
        ticker: _TickerSourceStats(
            record_count=value["record_count"],
            unavailable_count=value["unavailable_count"],
            absent_count=value["absent_count"],
            action_type_counts=_counts(value["action_types"]),
        )
        for ticker, value in sorted(mutable.items())
    }


def _scan_identity_history(
    *,
    root: Path,
    identity: object,
    requested_tickers: frozenset[str],
    max_workers: int,
) -> _HistoryScan:
    if not isinstance(max_workers, int) or isinstance(max_workers, bool):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census worker count is invalid"
        )
    if max_workers < 1 or max_workers > MAXIMUM_HISTORY_WORKERS:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census worker count is outside bounds"
        )
    sessions = identity.sessions
    worker_count = min(max_workers, len(sessions))
    chunks = _contiguous_session_chunks(sessions, worker_count)
    evidence_paths = tuple(
        str(root / PurePosixPath(item.relative_path)) for item in identity.evidences
    )
    evidence_binding = _identity_evidence_binding(identity)
    arguments = tuple(
        (
            str(root),
            evidence_paths,
            evidence_binding,
            chunk,
            requested_tickers,
        )
        for chunk in chunks
    )
    try:
        if worker_count == 1:
            results = tuple(_history_scan_worker(argument) for argument in arguments)
        else:
            with ProcessPoolExecutor(
                max_workers=worker_count,
                mp_context=get_context("spawn"),
            ) as executor:
                results = tuple(executor.map(_history_scan_worker, arguments))
    except Exception as exc:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census parallel Identity history scan failed"
        ) from exc
    scanned_sessions = tuple(session for result in results for session in result.sessions)
    if scanned_sessions != sessions:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census scanned session coverage differs"
        )
    bindings = tuple(binding for result in results for binding in result.bindings)
    merged: dict[str, dict[UUID, list[object]]] = defaultdict(dict)
    for result in results:
        for ticker, candidates in result.observations.items():
            for instrument_id, (first, last, count) in candidates.items():
                current = merged[ticker].get(instrument_id)
                if current is None:
                    merged[ticker][instrument_id] = [first, last, count]
                else:
                    current[0] = min(current[0], first)
                    current[1] = max(current[1], last)
                    current[2] += count
    return _HistoryScan(
        session_count=len(scanned_sessions),
        process_count=worker_count,
        resolver_binding_fingerprint=_fingerprint(bindings),
        observations={
            ticker: {
                instrument_id: (values[0], values[1], values[2])
                for instrument_id, values in sorted(
                    candidates.items(), key=lambda item: str(item[0])
                )
            }
            for ticker, candidates in sorted(merged.items())
        },
    )


def _history_scan_worker(
    argument: tuple[
        str,
        tuple[str, ...],
        tuple[tuple[object, ...], ...],
        tuple[date, ...],
        frozenset[str],
    ],
) -> _HistoryScanChunk:
    root_value, evidence_paths, expected_binding, sessions, requested_tickers = argument
    root = Path(root_value)
    identity = shadow_module._read_identity_evidence_set(  # noqa: SLF001
        root, tuple(Path(item) for item in evidence_paths)
    )
    if _identity_evidence_binding(identity) != expected_binding:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census worker Identity evidence binding differs"
        )
    if any(session not in identity.artifacts_by_session for session in sessions):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census worker session is outside evidence"
        )
    mutable: dict[str, dict[UUID, list[object]]] = defaultdict(dict)
    bindings: list[dict[str, object]] = []
    for session in sessions:
        resolver, binding = shadow_module._read_exact_resolver(  # noqa: SLF001
            root, identity.artifacts_by_session[session], session
        )
        bindings.append(binding)
        for ticker, instrument_id in resolver.items():
            if ticker not in requested_tickers:
                continue
            current = mutable[ticker].get(instrument_id)
            if current is None:
                mutable[ticker][instrument_id] = [session, session, 1]
            else:
                current[1] = session
                current[2] += 1
    return _HistoryScanChunk(
        sessions=sessions,
        bindings=tuple(bindings),
        observations={
            ticker: {
                instrument_id: (values[0], values[1], values[2])
                for instrument_id, values in candidates.items()
            }
            for ticker, candidates in mutable.items()
        },
    )


def _candidate_records(
    *,
    source_stats: Mapping[str, _TickerSourceStats],
    scan: _HistoryScan,
) -> tuple[UnresolvedTickerCandidateCensusV1, ...]:
    records = []
    for ticker, source in source_stats.items():
        candidate_values = scan.observations.get(ticker, {})
        candidates = tuple(
            HistoricalCandidateOccurrenceV1(
                instrument_id=instrument_id,
                first_observed_session=values[0],
                last_observed_session=values[1],
                observed_session_count=values[2],
            )
            for instrument_id, values in sorted(
                candidate_values.items(), key=lambda item: str(item[0])
            )
        )
        classification = (
            "zero_historical_candidates"
            if not candidates
            else (
                "one_historical_candidate"
                if len(candidates) == 1
                else "multiple_historical_candidates"
            )
        )
        records.append(
            UnresolvedTickerCandidateCensusV1(
                provider_ticker=ticker,
                classification=classification,
                unresolved_source_record_count=source.record_count,
                exact_date_identity_unavailable_count=source.unavailable_count,
                exact_date_ticker_absent_count=source.absent_count,
                action_type_counts=source.action_type_counts,
                candidates=candidates,
            )
        )
    return tuple(records)


def _build_manifest(
    *,
    implementation_revision: str,
    evaluated_at: datetime,
    shadow: object,
    shadow_output_root: Path,
    shadow_custody_root: Path,
    identity: object,
    scan: _HistoryScan,
    record_set: UnresolvedTickerCandidateSetV1,
    record_bytes: bytes,
) -> HistoricalCorporateActionUnresolvedCensusManifestV1:
    ticker_classification = Counter(item.classification for item in record_set.records)
    source_classification: Counter[str] = Counter()
    action_matrix: Counter[tuple[str, str]] = Counter()
    failure_matrix: Counter[tuple[str, str]] = Counter()
    candidate_ids: set[UUID] = set()
    candidate_relations = 0
    for item in record_set.records:
        source_classification[item.classification] += item.unresolved_source_record_count
        candidate_relations += len(item.candidates)
        candidate_ids.update(candidate.instrument_id for candidate in item.candidates)
        for action_type, count in item.action_type_counts:
            action_matrix[(action_type, item.classification)] += count
        failure_matrix[(
            "event_date_identity_unavailable",
            item.classification,
        )] += item.exact_date_identity_unavailable_count
        failure_matrix[("unresolved_ticker", item.classification)] += (
            item.exact_date_ticker_absent_count
        )
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "dataset_name": "historical-corporate-action-unresolved-census",
        "implementation_revision": implementation_revision,
        "evaluated_at": evaluated_at,
        "resolution_shadow_path": shadow_output_root.relative_to(
            shadow_custody_root
        ).as_posix(),
        "resolution_shadow_manifest_sha256": shadow.manifest_sha256,
        "resolution_shadow_logical_fingerprint": shadow.manifest.logical_fingerprint,
        "resolution_shadow_source_record_count": shadow.manifest.source_record_count,
        "resolution_shadow_typed_record_count": shadow.manifest.mapped_record_count,
        "unresolved_typed_record_count": sum(
            item.unresolved_source_record_count for item in record_set.records
        ),
        "unrepresentable_source_record_count": (
            shadow.manifest.unrepresentable_source_record_count
        ),
        "unresolved_unique_ticker_count": len(record_set.records),
        "identity_first_session": identity.sessions[0],
        "identity_last_session": identity.sessions[-1],
        "identity_session_count": len(identity.sessions),
        "identity_evidence_binding_fingerprint": _fingerprint(
            _identity_evidence_binding(identity)
        ),
        "scanned_resolver_binding_fingerprint": scan.resolver_binding_fingerprint,
        "scanned_resolver_session_count": scan.session_count,
        "process_count": scan.process_count,
        "ticker_classification_counts": tuple(
            (key, ticker_classification.get(key, 0)) for key in _CLASSIFICATIONS
        ),
        "source_record_classification_counts": tuple(
            (key, source_classification.get(key, 0)) for key in _CLASSIFICATIONS
        ),
        "action_type_classification_counts": _matrix_counts(action_matrix),
        "failure_reason_classification_counts": _matrix_counts(failure_matrix),
        "candidate_relation_count": candidate_relations,
        "distinct_candidate_instrument_count": len(candidate_ids),
        "records_file": RECORDS_FILE,
        "records_file_sha256": _sha256(record_bytes),
        "records_file_bytes": len(record_bytes),
        "records_logical_fingerprint": record_set.logical_fingerprint,
        "evidence_role": "quarantine_diagnostic_only",
        "stable_identity_assignment_count": 0,
        "source_record_mutation_count": 0,
        "canonical_data_write_count": 0,
        "adjustment_ledger_write_count": 0,
        "historical_coverage_write_count": 0,
        "analytics_execution_count": 0,
        "candidate_write_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
        "external_request_count": 0,
    }
    fingerprint_values = dict(values)
    fingerprint_values.pop("process_count")
    return HistoricalCorporateActionUnresolvedCensusManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(fingerprint_values)}
    )


def _verify_manifest_bindings(
    *,
    manifest: HistoricalCorporateActionUnresolvedCensusManifestV1,
    shadow: object,
    shadow_output_root: Path,
    shadow_custody_root: Path,
    identity: object,
) -> None:
    expected = {
        "resolution_shadow_path": shadow_output_root.relative_to(
            shadow_custody_root
        ).as_posix(),
        "resolution_shadow_manifest_sha256": shadow.manifest_sha256,
        "resolution_shadow_logical_fingerprint": shadow.manifest.logical_fingerprint,
        "resolution_shadow_source_record_count": shadow.manifest.source_record_count,
        "resolution_shadow_typed_record_count": shadow.manifest.mapped_record_count,
        "unresolved_typed_record_count": dict(
            shadow.manifest.resolution_status_counts
        ).get("unresolved", 0),
        "unrepresentable_source_record_count": (
            shadow.manifest.unrepresentable_source_record_count
        ),
        "identity_first_session": identity.sessions[0],
        "identity_last_session": identity.sessions[-1],
        "identity_session_count": len(identity.sessions),
        "identity_evidence_binding_fingerprint": _fingerprint(
            _identity_evidence_binding(identity)
        ),
    }
    if any(getattr(manifest, key) != value for key, value in expected.items()):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census source binding differs"
        )


def _verify_record_aggregates(
    manifest: HistoricalCorporateActionUnresolvedCensusManifestV1,
    records: tuple[UnresolvedTickerCandidateCensusV1, ...],
) -> None:
    ticker_counts = Counter(item.classification for item in records)
    source_counts: Counter[str] = Counter()
    action_matrix: Counter[tuple[str, str]] = Counter()
    failure_matrix: Counter[tuple[str, str]] = Counter()
    relations = 0
    candidate_ids: set[UUID] = set()
    for item in records:
        source_counts[item.classification] += item.unresolved_source_record_count
        relations += len(item.candidates)
        candidate_ids.update(candidate.instrument_id for candidate in item.candidates)
        for action_type, count in item.action_type_counts:
            action_matrix[(action_type, item.classification)] += count
        failure_matrix[(
            "event_date_identity_unavailable",
            item.classification,
        )] += item.exact_date_identity_unavailable_count
        failure_matrix[("unresolved_ticker", item.classification)] += (
            item.exact_date_ticker_absent_count
        )
    expected = {
        "unresolved_unique_ticker_count": len(records),
        "unresolved_typed_record_count": sum(
            item.unresolved_source_record_count for item in records
        ),
        "ticker_classification_counts": tuple(
            (key, ticker_counts.get(key, 0)) for key in _CLASSIFICATIONS
        ),
        "source_record_classification_counts": tuple(
            (key, source_counts.get(key, 0)) for key in _CLASSIFICATIONS
        ),
        "action_type_classification_counts": _matrix_counts(action_matrix),
        "failure_reason_classification_counts": _matrix_counts(failure_matrix),
        "candidate_relation_count": relations,
        "distinct_candidate_instrument_count": len(candidate_ids),
    }
    if any(getattr(manifest, key) != value for key, value in expected.items()):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census record aggregates differ"
        )


def _read_shadow(*, output_root: Path, custody_root: Path) -> object:
    try:
        return shadow_module.read_historical_corporate_action_resolution_shadow(
            output_root=output_root,
            output_custody_root=custody_root,
        )
    except Exception as exc:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census resolution shadow failed formal reread"
        ) from exc


def _identity_evidence_binding(identity: object) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            item.relative_path,
            item.physical_sha256,
            item.logical_fingerprint,
            len(item.sessions),
            item.sessions[0],
            item.sessions[-1],
        )
        for item in identity.evidences
    )


def _contiguous_session_chunks(
    sessions: tuple[date, ...], worker_count: int
) -> tuple[tuple[date, ...], ...]:
    chunk_size = (len(sessions) + worker_count - 1) // worker_count
    chunks = tuple(
        sessions[index : index + chunk_size]
        for index in range(0, len(sessions), chunk_size)
    )
    if not chunks or len(chunks) > worker_count or tuple(
        session for chunk in chunks for session in chunk
    ) != sessions:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census session chunking differs"
        )
    return chunks


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalCorporateActionUnresolvedCensusError(
            "canonical data root is unavailable"
        )
    root = path.resolve(strict=True)
    if root != APPROVED_DATA_ROOT or path != root:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "canonical data root is not the approved Dell root"
        )
    return root


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    root = custody_root.absolute()
    target = path.absolute()
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or target.parent != root
        or re.fullmatch(_BUILD_NAME_PATTERN, target.name) is None
    ):
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census output custody boundary differs"
        )
    if target.exists() or target.is_symlink():
        if (
            target.is_symlink()
            or not target.is_dir()
            or target.resolve(strict=True) != target
            or target.stat().st_uid != os.getuid()
            or stat.S_IMODE(target.stat().st_mode) != 0o700
        ):
            raise HistoricalCorporateActionUnresolvedCensusError(
                "unresolved census output target is unsafe"
            )
    return target


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if not target.is_dir():
        raise HistoricalCorporateActionUnresolvedCensusError(
            "completed unresolved census is unavailable"
        )
    return target


def _require_regular_file(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census file is unsafe"
        )
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census file ownership or mode differs"
        )


def _read_bounded_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "unresolved census file size is invalid"
        )
    return path.read_bytes()


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(0o400)


def _counts(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, value) for key, value in counter.items() if value > 0))


def _matrix_counts(
    counter: Counter[tuple[str, str]],
) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        sorted((first, second, count) for (first, second), count in counter.items() if count > 0)
    )


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalCorporateActionUnresolvedCensusError(
            "network access is prohibited while building the unresolved census"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
