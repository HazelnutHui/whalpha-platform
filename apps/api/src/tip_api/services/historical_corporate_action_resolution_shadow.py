"""Resolve corporate-action source rows against exact event-date Identity."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal, Mapping
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    HistoricalDatasetFamily,
    ResolutionStatus,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchPersistenceError,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA,
    records_fingerprint,
    resolver_content_fingerprint,
)
from tip_api.providers.massive.corporate_action_mapping import (
    map_massive_corporate_action_payloads,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    HistoricalCorporateActionSourceError,
    ValidatedCorporateActionSourcePackage,
    read_historical_corporate_action_source_package,
)


CONTRACT_VERSION = "historical-corporate-action-resolution-shadow/1.0"
ARTIFACT_CONTRACT_VERSION = (
    "historical-corporate-action-resolution-shadow-artifact/1.0"
)
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
MANIFEST_FILE = "shadow.json"
PARQUET_FILE = "part-00000.parquet"
PARTITION_MANIFEST_FILE = "manifest.json"
MAXIMUM_JSON_BYTES = 16 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class HistoricalCorporateActionResolutionShadowError(RuntimeError):
    """Raised when the corporate-action resolution shadow is not trustworthy."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorporateActionResolutionShadowArtifactV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-resolution-shadow-artifact/1.0"
    ] = ARTIFACT_CONTRACT_VERSION
    event_year: int = Field(ge=1900, le=2200)
    partition_path: str
    record_count: int = Field(ge=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    parquet_bytes: int = Field(ge=1)
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("partition_path")
    @classmethod
    def path_is_relative_and_normalized(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
        ):
            raise ValueError("shadow artifact path must be normalized and relative")
        return value

    @model_validator(mode="after")
    def path_matches_year(self) -> "CorporateActionResolutionShadowArtifactV1":
        if not self.partition_path.endswith(f"/event_year={self.event_year}"):
            raise ValueError("shadow artifact year and path differ")
        return self


class CorporateActionResolutionShadowManifestV1(FrozenModel):
    contract_version: Literal[
        "historical-corporate-action-resolution-shadow/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "historical-corporate-action-resolution-shadow"
    ] = "historical-corporate-action-resolution-shadow"
    provider: Literal["massive_stocks_basic"] = MASSIVE_PROVIDER_ID
    start_date: date
    end_date: date
    materialized_at: datetime
    source_revision_semantics: Literal["local_observation_baseline_only"] = (
        "local_observation_baseline_only"
    )
    split_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    split_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    split_source_record_count: int = Field(ge=0)
    dividend_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    dividend_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    dividend_source_record_count: int = Field(ge=0)
    identity_evidence_path: str
    identity_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_evidence_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    identity_session_count: int = Field(ge=1)
    used_identity_session_count: int = Field(ge=0)
    identity_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_record_count: int = Field(ge=1)
    mapped_record_count: int = Field(ge=1)
    identity_session_available_record_count: int = Field(ge=0)
    identity_session_unavailable_record_count: int = Field(ge=0)
    resolution_status_counts: tuple[tuple[str, int], ...]
    record_status_counts: tuple[tuple[str, int], ...]
    action_type_counts: tuple[tuple[str, int], ...]
    quality_flag_counts: tuple[tuple[str, int], ...]
    artifacts: tuple[CorporateActionResolutionShadowArtifactV1, ...] = Field(
        min_length=1
    )
    source_mapping_one_to_one: Literal[True] = True
    exact_event_date_resolution_only: Literal[True] = True
    nearest_session_fallback_count: Literal[0] = 0
    latest_ticker_fallback_count: Literal[0] = 0
    current_universe_filter_count: Literal[0] = 0
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("materialized_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("identity_evidence_path")
    @classmethod
    def evidence_path_is_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
            or not value.endswith("/manifest.json")
        ):
            raise ValueError("Identity evidence path must be normalized and relative")
        return value

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "CorporateActionResolutionShadowManifestV1":
        if self.end_date < self.start_date:
            raise ValueError("shadow date range is reversed")
        if self.source_record_count != (
            self.split_source_record_count + self.dividend_source_record_count
        ):
            raise ValueError("shadow source counts differ")
        if self.mapped_record_count != self.source_record_count:
            raise ValueError("shadow is not one-to-one")
        if (
            self.identity_session_available_record_count
            + self.identity_session_unavailable_record_count
            != self.source_record_count
        ):
            raise ValueError("shadow Identity-date counts differ")
        if self.used_identity_session_count > self.identity_session_count:
            raise ValueError("used Identity sessions exceed evidence sessions")
        if sum(count for _, count in self.resolution_status_counts) != (
            self.mapped_record_count
        ):
            raise ValueError("resolution counts differ")
        if sum(count for _, count in self.record_status_counts) != (
            self.mapped_record_count
        ):
            raise ValueError("record-status counts differ")
        if sum(count for _, count in self.action_type_counts) != (
            self.mapped_record_count
        ):
            raise ValueError("action-type counts differ")
        if sum(item.record_count for item in self.artifacts) != (
            self.mapped_record_count
        ):
            raise ValueError("shadow artifact counts differ")
        if tuple(item.event_year for item in self.artifacts) != tuple(
            sorted({item.event_year for item in self.artifacts})
        ):
            raise ValueError("shadow artifact years are not unique and ordered")
        for values in (
            self.resolution_status_counts,
            self.record_status_counts,
            self.action_type_counts,
            self.quality_flag_counts,
        ):
            if values != tuple(sorted(values)) or any(count < 1 for _, count in values):
                raise ValueError("shadow aggregate counts are invalid")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("shadow logical fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class CorporateActionResolutionShadowWriteResult:
    output_root: Path
    manifest: CorporateActionResolutionShadowManifestV1
    records: tuple[CorporateActionSourceObservationV1, ...]
    manifest_sha256: str
    status: Literal["published", "already_present"]


def read_historical_ticker_candidates_bound_to_resolution_shadow(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    provider_tickers: frozenset[str],
) -> dict[str, frozenset[UUID]]:
    """Return conservative historical stable-ID candidates for selected tickers.

    This is a quarantine aid only. It scans every evidence-bound historical
    Resolver and never assigns an unresolved action to any returned ID.
    """

    with _network_prohibited():
        root = _validated_data_root(data_root)
        shadow = read_historical_corporate_action_resolution_shadow(
            output_root=resolution_shadow_output_root
        )
        requested = frozenset(
            normalized
            for value in provider_tickers
            if (normalized := value.strip().upper())
        )
        if len(requested) != len(provider_tickers):
            raise HistoricalCorporateActionResolutionShadowError(
                "historical ticker candidate input is empty or non-normalized"
            )
        identity = _read_identity_evidence(
            root,
            root / PurePosixPath(shadow.manifest.identity_evidence_path),
        )
        expected_identity = {
            "physical_sha256": shadow.manifest.identity_evidence_sha256,
            "logical_fingerprint": (
                shadow.manifest.identity_evidence_logical_fingerprint
            ),
            "session_count": shadow.manifest.identity_session_count,
            "first_session": shadow.manifest.start_date,
            "last_session": shadow.manifest.end_date,
        }
        actual_identity = {
            "physical_sha256": identity.physical_sha256,
            "logical_fingerprint": identity.logical_fingerprint,
            "session_count": len(identity.sessions),
            "first_session": identity.sessions[0],
            "last_session": identity.sessions[-1],
        }
        if actual_identity != expected_identity:
            raise HistoricalCorporateActionResolutionShadowError(
                "resolution shadow Identity evidence binding differs"
            )

        used_dates = {
            item.effective_date
            for item in shadow.records
            if item.effective_date in identity.artifacts_by_session
        }
        candidates: dict[str, set[UUID]] = {
            ticker: set() for ticker in requested
        }
        used_bindings: list[dict[str, object]] = []
        for session in identity.sessions:
            resolver, binding = _read_exact_resolver(
                root,
                identity.artifacts_by_session[session],
                session,
            )
            if session in used_dates:
                used_bindings.append(binding)
            for ticker in requested:
                instrument_id = resolver.get(ticker)
                if instrument_id is not None:
                    candidates[ticker].add(instrument_id)
        if (
            len(used_bindings) != shadow.manifest.used_identity_session_count
            or _fingerprint(tuple(used_bindings))
            != shadow.manifest.identity_binding_fingerprint
        ):
            raise HistoricalCorporateActionResolutionShadowError(
                "resolution shadow used-Resolver binding differs"
            )
        return {
            ticker: frozenset(sorted(ids, key=str))
            for ticker, ids in sorted(candidates.items())
        }


def read_historical_ticker_candidates_bound_to_identity_evidence(
    *,
    data_root: Path,
    identity_evidence_path: Path,
    identity_evidence_sha256: str,
    identity_evidence_logical_fingerprint: str,
    identity_session_count: int,
    first_session: date,
    last_session: date,
    provider_tickers: frozenset[str],
) -> dict[str, frozenset[UUID]]:
    """Return quarantine-only ticker candidates from one exact Identity evidence set.

    The result never resolves an action.  It is intentionally exposed separately
    from the resolution-shadow wrapper so later stages can bind the canonical
    source publication directly instead of depending on its retired `/tmp`
    precursor.
    """

    with _network_prohibited():
        root = _validated_data_root(data_root)
        requested = frozenset(
            normalized
            for value in provider_tickers
            if (normalized := value.strip().upper())
        )
        if len(requested) != len(provider_tickers):
            raise HistoricalCorporateActionResolutionShadowError(
                "historical ticker candidate input is empty or non-normalized"
            )
        identity = _read_identity_evidence(root, identity_evidence_path)
        expected_identity = {
            "physical_sha256": identity_evidence_sha256,
            "logical_fingerprint": identity_evidence_logical_fingerprint,
            "session_count": identity_session_count,
            "first_session": first_session,
            "last_session": last_session,
        }
        actual_identity = {
            "physical_sha256": identity.physical_sha256,
            "logical_fingerprint": identity.logical_fingerprint,
            "session_count": len(identity.sessions),
            "first_session": identity.sessions[0],
            "last_session": identity.sessions[-1],
        }
        if actual_identity != expected_identity:
            raise HistoricalCorporateActionResolutionShadowError(
                "ticker scan Identity evidence binding differs"
            )

        candidates: dict[str, set[UUID]] = {
            ticker: set() for ticker in requested
        }
        for session in identity.sessions:
            resolver, _ = _read_exact_resolver(
                root,
                identity.artifacts_by_session[session],
                session,
            )
            for ticker in requested:
                instrument_id = resolver.get(ticker)
                if instrument_id is not None:
                    candidates[ticker].add(instrument_id)
        return {
            ticker: frozenset(sorted(ids, key=str))
            for ticker, ids in sorted(candidates.items())
        }


@dataclass(frozen=True, slots=True)
class _IdentityEvidence:
    relative_path: str
    physical_sha256: str
    logical_fingerprint: str
    sessions: tuple[date, ...]
    artifacts_by_session: Mapping[date, object]


def build_historical_corporate_action_resolution_shadow(
    *,
    data_root: Path,
    split_source_package_path: Path,
    dividend_source_package_path: Path,
    identity_evidence_path: Path,
    output_root: Path,
    start_date: date,
    end_date: date,
    materialized_at: datetime,
) -> CorporateActionResolutionShadowWriteResult:
    """Build a disconnected exact-event-date resolution shadow."""

    with _network_prohibited():
        return _build_shadow(
            data_root=data_root,
            split_source_package_path=split_source_package_path,
            dividend_source_package_path=dividend_source_package_path,
            identity_evidence_path=identity_evidence_path,
            output_root=output_root,
            start_date=start_date,
            end_date=end_date,
            materialized_at=materialized_at,
        )


def _build_shadow(
    *,
    data_root: Path,
    split_source_package_path: Path,
    dividend_source_package_path: Path,
    identity_evidence_path: Path,
    output_root: Path,
    start_date: date,
    end_date: date,
    materialized_at: datetime,
) -> CorporateActionResolutionShadowWriteResult:
    canonical_root = _validated_data_root(data_root)
    target = _validated_output_target(output_root)
    materialized_at = normalize_utc_datetime(materialized_at)
    split = _read_source(
        split_source_package_path,
        CorporateActionSourceKind.SPLIT,
        start_date,
        end_date,
    )
    dividend = _read_source(
        dividend_source_package_path,
        CorporateActionSourceKind.DIVIDEND,
        start_date,
        end_date,
    )
    if materialized_at < max(
        split.manifest.completed_at, dividend.manifest.completed_at
    ):
        raise HistoricalCorporateActionResolutionShadowError(
            "shadow materialization precedes source completion"
        )
    identity = _read_identity_evidence(canonical_root, identity_evidence_path)
    if (
        identity.sessions[0] != start_date
        or identity.sessions[-1] != end_date
    ):
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity evidence does not span the source range"
        )

    records, identity_bindings, available_rows, unavailable_rows = _map_sources(
        canonical_root=canonical_root,
        split=split,
        dividend=dividend,
        identity=identity,
        materialized_at=materialized_at,
    )
    if len(records) != split.manifest.record_count + dividend.manifest.record_count:
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action source mapping is not one-to-one"
        )
    identity_binding_fingerprint = _fingerprint(identity_bindings)

    existing = _read_if_present(target)
    if existing is not None:
        manifest = existing.manifest
        expected_bindings = {
            "split_source_manifest_sha256": split.manifest_sha256,
            "split_source_logical_fingerprint": split.manifest.logical_fingerprint,
            "dividend_source_manifest_sha256": dividend.manifest_sha256,
            "dividend_source_logical_fingerprint": (
                dividend.manifest.logical_fingerprint
            ),
            "identity_evidence_sha256": identity.physical_sha256,
            "identity_evidence_logical_fingerprint": identity.logical_fingerprint,
            "identity_binding_fingerprint": identity_binding_fingerprint,
            "materialized_at": materialized_at,
        }
        if any(getattr(manifest, key) != value for key, value in expected_bindings.items()) or (
            existing.records != records
        ):
            raise HistoricalCorporateActionResolutionShadowError(
                "existing corporate-action shadow differs"
            )
        return CorporateActionResolutionShadowWriteResult(
            output_root=target,
            manifest=manifest,
            records=records,
            manifest_sha256=existing.manifest_sha256,
            status="already_present",
        )

    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow staging target exists"
        )
    staging.mkdir(mode=0o700)
    try:
        repository = ParquetHistoricalResearchRepository(
            staging,
            created_at=materialized_at,
        )
        by_year: dict[int, list[CorporateActionSourceObservationV1]] = defaultdict(list)
        for record in records:
            by_year[record.effective_date.year].append(record)
        artifacts: list[CorporateActionResolutionShadowArtifactV1] = []
        for event_year, year_records in sorted(by_year.items()):
            result = repository.publish_corporate_action_observations(
                tuple(year_records),
                provider_id=MASSIVE_PROVIDER_ID,
                event_year=event_year,
            )
            relative = result.partition_path.relative_to(staging).as_posix()
            artifacts.append(
                CorporateActionResolutionShadowArtifactV1(
                    event_year=event_year,
                    partition_path=relative,
                    record_count=result.record_count,
                    logical_fingerprint=result.logical_fingerprint,
                    parquet_sha256=result.physical_sha256,
                    parquet_bytes=result.parquet_path.stat().st_size,
                    manifest_sha256=_file_sha256(result.manifest_path),
                )
            )
        values = {
            "contract_version": CONTRACT_VERSION,
            "completion_status": "completed",
            "dataset_name": "historical-corporate-action-resolution-shadow",
            "provider": MASSIVE_PROVIDER_ID,
            "start_date": start_date,
            "end_date": end_date,
            "materialized_at": materialized_at,
            "source_revision_semantics": "local_observation_baseline_only",
            "split_source_manifest_sha256": split.manifest_sha256,
            "split_source_logical_fingerprint": split.manifest.logical_fingerprint,
            "split_source_record_count": split.manifest.record_count,
            "dividend_source_manifest_sha256": dividend.manifest_sha256,
            "dividend_source_logical_fingerprint": (
                dividend.manifest.logical_fingerprint
            ),
            "dividend_source_record_count": dividend.manifest.record_count,
            "identity_evidence_path": identity.relative_path,
            "identity_evidence_sha256": identity.physical_sha256,
            "identity_evidence_logical_fingerprint": identity.logical_fingerprint,
            "identity_session_count": len(identity.sessions),
            "used_identity_session_count": len(identity_bindings),
            "identity_binding_fingerprint": identity_binding_fingerprint,
            "source_record_count": len(records),
            "mapped_record_count": len(records),
            "identity_session_available_record_count": available_rows,
            "identity_session_unavailable_record_count": unavailable_rows,
            "resolution_status_counts": _counts(
                item.instrument_resolution_status.value for item in records
            ),
            "record_status_counts": _counts(item.record_status.value for item in records),
            "action_type_counts": _counts(item.action_type.value for item in records),
            "quality_flag_counts": _counts(
                flag for item in records for flag in item.quality_flags
            ),
            "artifacts": tuple(artifacts),
            "source_mapping_one_to_one": True,
            "exact_event_date_resolution_only": True,
            "nearest_session_fallback_count": 0,
            "latest_ticker_fallback_count": 0,
            "current_universe_filter_count": 0,
            "point_in_time_eligibility": "outcome_reconciliation_only",
            "external_request_count": 0,
            "canonical_data_write_count": 0,
            "adjustment_ledger_write_count": 0,
            "analytics_execution_count": 0,
            "publication_count": 0,
            "deployment_count": 0,
            "scheduler_change_count": 0,
        }
        manifest = CorporateActionResolutionShadowManifestV1.model_validate(
            {**values, "logical_fingerprint": _fingerprint(values)}
        )
        manifest_path = staging / MANIFEST_FILE
        manifest_path.write_bytes(_pretty_json(manifest.model_dump(mode="json")))
        _fsync_file(manifest_path)
        _secure_tree(staging)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink() and staging.parent == target.parent:
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise

    reread = read_historical_corporate_action_resolution_shadow(output_root=target)
    if reread.records != records:
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow formal reread differs"
        )
    return CorporateActionResolutionShadowWriteResult(
        output_root=target,
        manifest=reread.manifest,
        records=reread.records,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def read_historical_corporate_action_resolution_shadow(
    *,
    output_root: Path,
) -> CorporateActionResolutionShadowWriteResult:
    """Formally reread a completed shadow without network or external sources."""

    root = _validated_completed_output(output_root)
    manifest_path = root / MANIFEST_FILE
    _require_regular_file(manifest_path, 0o400)
    try:
        manifest = CorporateActionResolutionShadowManifestV1.model_validate_json(
            _read_bounded_bytes(manifest_path)
        )
    except Exception as exc:
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow manifest is invalid"
        ) from exc
    expected_files = {MANIFEST_FILE}
    expected_directories: set[str] = set()
    records: list[CorporateActionSourceObservationV1] = []
    repository = ParquetHistoricalResearchRepository(root)
    for artifact in manifest.artifacts:
        partition = root / PurePosixPath(artifact.partition_path)
        expected_files.update(
            {
                f"{artifact.partition_path}/{PARQUET_FILE}",
                f"{artifact.partition_path}/{PARTITION_MANIFEST_FILE}",
            }
        )
        current = PurePosixPath(artifact.partition_path)
        while current.parts:
            expected_directories.add(current.as_posix())
            current = current.parent
            if current == PurePosixPath("."):
                break
        _require_regular_file(partition / PARQUET_FILE, 0o400)
        _require_regular_file(partition / PARTITION_MANIFEST_FILE, 0o400)
        try:
            year_records = repository.read_corporate_action_observations(partition)
        except HistoricalResearchPersistenceError as exc:
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow partition failed formal reread"
            ) from exc
        if (
            len(year_records) != artifact.record_count
            or any(item.effective_date.year != artifact.event_year for item in year_records)
            or _file_sha256(partition / PARQUET_FILE) != artifact.parquet_sha256
            or (partition / PARQUET_FILE).stat().st_size != artifact.parquet_bytes
            or _file_sha256(partition / PARTITION_MANIFEST_FILE)
            != artifact.manifest_sha256
        ):
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow artifact differs"
            )
        partition_manifest = _read_json(partition / PARTITION_MANIFEST_FILE)
        if partition_manifest.get("logical_fingerprint") != artifact.logical_fingerprint:
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow partition fingerprint differs"
            )
        records.extend(year_records)
    _validate_tree(root, expected_files, expected_directories)
    ordered = tuple(
        sorted(records, key=lambda item: (item.provider, item.source_action_id, item.source_revision))
    )
    if len(
        {(item.provider, item.source_action_id, item.source_revision) for item in ordered}
    ) != len(ordered):
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow business keys are not unique"
        )
    unavailable_rows = sum(
        "event_date_identity_unavailable" in item.quality_flags for item in ordered
    )
    split_rows = sum(item.action_type.value != "cash_dividend" for item in ordered)
    expected_counts = {
        "split_source_record_count": split_rows,
        "dividend_source_record_count": len(ordered) - split_rows,
        "source_record_count": len(ordered),
        "mapped_record_count": len(ordered),
        "identity_session_available_record_count": len(ordered) - unavailable_rows,
        "identity_session_unavailable_record_count": unavailable_rows,
        "used_identity_session_count": len(
            {
                item.effective_date
                for item in ordered
                if "event_date_identity_unavailable" not in item.quality_flags
            }
        ),
        "resolution_status_counts": _counts(
            item.instrument_resolution_status.value for item in ordered
        ),
        "record_status_counts": _counts(item.record_status.value for item in ordered),
        "action_type_counts": _counts(item.action_type.value for item in ordered),
        "quality_flag_counts": _counts(
            flag for item in ordered for flag in item.quality_flags
        ),
    }
    if any(getattr(manifest, key) != value for key, value in expected_counts.items()):
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow aggregate differs"
        )
    if any(
        item.source_revision != 1
        or item.ingested_at != manifest.materialized_at
        or item.first_observed_at > item.ingested_at
        or item.knowledge_time_status.value != "first_observed_only"
        or item.source_available_at is not None
        for item in ordered
    ):
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow observation semantics differ"
        )
    return CorporateActionResolutionShadowWriteResult(
        output_root=root,
        manifest=manifest,
        records=ordered,
        manifest_sha256=_file_sha256(manifest_path),
        status="already_present",
    )


def _read_source(
    path: Path,
    kind: CorporateActionSourceKind,
    start_date: date,
    end_date: date,
) -> ValidatedCorporateActionSourcePackage:
    try:
        return read_historical_corporate_action_source_package(
            package_path=path,
            expected_action_kind=kind,
            expected_start_date=start_date,
            expected_end_date=end_date,
        )
    except HistoricalCorporateActionSourceError as exc:
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action source package failed formal reread"
        ) from exc


def _read_identity_evidence(
    root: Path,
    path: Path,
) -> _IdentityEvidence:
    absolute = path if path.is_absolute() else root / path
    _contained_path(root, absolute)
    try:
        result = ParquetHistoricalCoverageRepository(root).read_dataset_evidence(
            absolute
        )
    except HistoricalResearchPersistenceError as exc:
        raise HistoricalCorporateActionResolutionShadowError(
            "point-in-time Identity evidence failed formal reread"
        ) from exc
    evidence = result.evidence
    if evidence.family is not HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY:
        raise HistoricalCorporateActionResolutionShadowError(
            "resolution requires point-in-time Identity evidence"
        )
    by_session: dict[date, object] = {}
    for artifact in evidence.artifacts:
        if artifact.first_session != artifact.last_session:
            raise HistoricalCorporateActionResolutionShadowError(
                "Identity evidence artifact must bind one exact session"
            )
        if artifact.first_session in by_session:
            raise HistoricalCorporateActionResolutionShadowError(
                "Identity evidence contains a duplicate session"
            )
        by_session[artifact.first_session] = artifact
    if tuple(sorted(by_session)) != evidence.sessions:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity evidence session and artifact sets differ"
        )
    return _IdentityEvidence(
        relative_path=absolute.relative_to(root).as_posix(),
        physical_sha256=result.physical_sha256,
        logical_fingerprint=evidence.logical_fingerprint,
        sessions=evidence.sessions,
        artifacts_by_session=by_session,
    )


def _map_sources(
    *,
    canonical_root: Path,
    split: ValidatedCorporateActionSourcePackage,
    dividend: ValidatedCorporateActionSourcePackage,
    identity: _IdentityEvidence,
    materialized_at: datetime,
) -> tuple[
    tuple[CorporateActionSourceObservationV1, ...],
    tuple[dict[str, object], ...],
    int,
    int,
]:
    groups: dict[
        tuple[CorporateActionSourceKind, datetime, date],
        list[Mapping[str, object]],
    ] = defaultdict(list)
    for package in (split, dividend):
        date_field = (
            "execution_date"
            if package.manifest.action_kind is CorporateActionSourceKind.SPLIT
            else "ex_dividend_date"
        )
        for page in package.pages:
            results = page.sanitized_response.get("results")
            if not isinstance(results, list):
                raise HistoricalCorporateActionResolutionShadowError(
                    "corporate-action source results changed after reread"
                )
            for payload in results:
                if not isinstance(payload, Mapping):
                    raise HistoricalCorporateActionResolutionShadowError(
                        "corporate-action source row is not an object"
                    )
                raw_date = payload.get(date_field)
                try:
                    event_date = date.fromisoformat(str(raw_date))
                except ValueError as exc:
                    raise HistoricalCorporateActionResolutionShadowError(
                        "corporate-action source effective date is invalid"
                    ) from exc
                groups[(package.manifest.action_kind, page.source_observed_at, event_date)].append(
                    payload
                )

    identity_sessions = set(identity.sessions)
    resolver_cache: dict[date, dict[str, UUID]] = {}
    binding_cache: dict[date, dict[str, object]] = {}
    mapped: list[CorporateActionSourceObservationV1] = []
    available_rows = 0
    unavailable_rows = 0
    for (kind, observed_at, event_date), payloads in sorted(
        groups.items(), key=lambda item: (item[0][2], item[0][0].value, item[0][1])
    ):
        if event_date in identity_sessions:
            if event_date not in resolver_cache:
                resolver_cache[event_date], binding_cache[event_date] = (
                    _read_exact_resolver(
                        canonical_root,
                        identity.artifacts_by_session[event_date],
                        event_date,
                    )
                )
            resolutions = resolver_cache[event_date]
            unresolved_reason = "unresolved_ticker"
            available_rows += len(payloads)
        else:
            resolutions = {}
            unresolved_reason = "event_date_identity_unavailable"
            unavailable_rows += len(payloads)
        batch = map_massive_corporate_action_payloads(
            split_payloads=(payloads if kind is CorporateActionSourceKind.SPLIT else ()),
            dividend_payloads=(
                payloads if kind is CorporateActionSourceKind.DIVIDEND else ()
            ),
            ticker_resolutions=resolutions,
            first_observed_at=observed_at,
            ingested_at=materialized_at,
            source_revision=1,
            unresolved_ticker_reason_code=unresolved_reason,
        )
        if batch.issues or batch.input_count != len(payloads) or len(batch.records) != len(payloads):
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action mapper could not preserve every source row"
            )
        mapped.extend(batch.records)
    ordered = tuple(
        sorted(mapped, key=lambda item: (item.provider, item.source_action_id, item.source_revision))
    )
    if len(
        {(item.provider, item.source_action_id, item.source_revision) for item in ordered}
    ) != len(ordered):
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action source IDs collide across packages"
        )
    return ordered, tuple(binding_cache[key] for key in sorted(binding_cache)), available_rows, unavailable_rows


def _read_exact_resolver(
    root: Path,
    raw_artifact: object,
    session: date,
) -> tuple[dict[str, UUID], dict[str, object]]:
    artifact = raw_artifact
    completion_reference = artifact.completion_manifest
    completion_path = root / PurePosixPath(completion_reference.path)
    completion_bytes = _read_evidence_bound_file(
        root, completion_path, completion_reference.physical_sha256
    )
    completion = _parse_json_bytes(completion_bytes)
    resolver_references = tuple(
        item
        for item in artifact.payload_files
        if "/provider-ticker-resolver/" in f"/{item.path}"
    )
    if len(resolver_references) != 2:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity evidence does not contain one Resolver manifest and Parquet"
        )
    manifest_reference = next(
        (item for item in resolver_references if item.path.endswith("/manifest.json")),
        None,
    )
    parquet_reference = next(
        (item for item in resolver_references if item.path.endswith(f"/{PARQUET_FILE}")),
        None,
    )
    if manifest_reference is None or parquet_reference is None:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity Resolver evidence file roles differ"
        )
    manifest_path = root / PurePosixPath(manifest_reference.path)
    parquet_path = root / PurePosixPath(parquet_reference.path)
    manifest = _parse_json_bytes(
        _read_evidence_bound_file(
            root, manifest_path, manifest_reference.physical_sha256
        )
    )
    parquet_bytes = _read_evidence_bound_file(
        root, parquet_path, parquet_reference.physical_sha256
    )
    expected_partition = parquet_path.parent
    expected_snapshot = {
        "dataset_name": "instrument-master-logical-snapshot",
        "schema_version": "1.0",
        "as_of_date": session.isoformat(),
        "provider_id": MASSIVE_PROVIDER_ID,
        "resolver_partition_path": str(expected_partition),
        "completion_status": "completed",
    }
    if any(completion.get(key) != value for key, value in expected_snapshot.items()):
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity snapshot Resolver binding differs"
        )
    resolver_count = completion.get("resolver_count")
    if type(resolver_count) is not int or resolver_count < 1 or (
        completion.get("instrument_count") != resolver_count
    ):
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity snapshot Resolver count differs"
        )
    component_fingerprints = {
        key: completion.get(key)
        for key in (
            "instrument_content_sha256",
            "identity_content_sha256",
            "resolver_content_sha256",
        )
    }
    if any(not _is_sha(value) for value in component_fingerprints.values()) or (
        records_fingerprint([component_fingerprints])
        != completion.get("snapshot_content_sha256")
    ) or completion.get("snapshot_content_sha256") != artifact.logical_fingerprint:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity snapshot logical fingerprint differs"
        )
    expected_manifest = {
        "dataset_name": "provider-ticker-resolver",
        "schema_version": "1.0",
        "as_of_date": session.isoformat(),
        "provider_id": MASSIVE_PROVIDER_ID,
        "record_count": resolver_count,
        "content_sha256": completion.get("resolver_content_sha256"),
        "parquet_file": PARQUET_FILE,
        "completion_status": "completed",
    }
    if any(manifest.get(key) != value for key, value in expected_manifest.items()):
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity Resolver manifest differs"
        )
    try:
        table = pq.ParquetFile(pa.BufferReader(parquet_bytes)).read()
    except Exception as exc:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity Resolver Parquet is unreadable"
        ) from exc
    if table.schema != PROVIDER_TICKER_RESOLVER_ARROW_SCHEMA or table.num_rows != resolver_count:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity Resolver schema or count differs"
        )
    try:
        from tip_api.contracts.market_data.v1 import ProviderTickerResolverV1

        records = tuple(
            ProviderTickerResolverV1.model_validate(row) for row in table.to_pylist()
        )
    except Exception as exc:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity Resolver rows are invalid"
        ) from exc
    if resolver_content_fingerprint(records) != completion.get(
        "resolver_content_sha256"
    ):
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity Resolver content fingerprint differs"
        )
    by_ticker: dict[str, UUID] = {}
    for record in records:
        if record.provider != MASSIVE_PROVIDER_ID or record.as_of_date != session:
            raise HistoricalCorporateActionResolutionShadowError(
                "Identity Resolver row scope differs"
            )
        if record.provider_ticker in by_ticker:
            raise HistoricalCorporateActionResolutionShadowError(
                "Identity Resolver ticker is not unique"
            )
        by_ticker[record.provider_ticker] = record.canonical_instrument_id
    return by_ticker, {
        "as_of_date": session,
        "snapshot_content_sha256": completion.get("snapshot_content_sha256"),
        "resolver_content_sha256": completion.get("resolver_content_sha256"),
        "resolver_count": resolver_count,
        "resolver_manifest_sha256": manifest_reference.physical_sha256,
        "resolver_parquet_sha256": parquet_reference.physical_sha256,
    }


def _read_evidence_bound_file(root: Path, path: Path, expected_sha256: str) -> bytes:
    _contained_path(root, path)
    raw = _read_bounded_bytes(path, maximum_bytes=512 * 1024 * 1024)
    if _sha256(raw) != expected_sha256:
        raise HistoricalCorporateActionResolutionShadowError(
            "Identity evidence physical hash differs"
        )
    return raw


def _read_if_present(
    target: Path,
) -> CorporateActionResolutionShadowWriteResult | None:
    if not target.exists() and not target.is_symlink():
        return None
    return read_historical_corporate_action_resolution_shadow(output_root=target)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalCorporateActionResolutionShadowError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT or path != resolved:
        raise HistoricalCorporateActionResolutionShadowError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _validated_output_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow must be below /tmp"
        )
    _reject_symlink_chain(target.parent, tmp)
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow parent is unsafe"
        )
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow target is unsafe"
            )
    return target


def _validated_completed_output(path: Path) -> Path:
    root = _validated_output_target(path)
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise HistoricalCorporateActionResolutionShadowError(
            "completed corporate-action shadow is unavailable or not owner-only"
        )
    return root


def _contained_path(root: Path, path: Path) -> None:
    absolute = path.absolute()
    if absolute == root or root not in absolute.parents:
        raise HistoricalCorporateActionResolutionShadowError(
            "evidence path escapes the canonical root"
        )
    _reject_symlink_chain(absolute, root)


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    current = path.absolute()
    while current != stop:
        if current.exists() and current.is_symlink():
            raise HistoricalCorporateActionResolutionShadowError(
                "path contains a symlink"
            )
        if stop not in current.parents:
            raise HistoricalCorporateActionResolutionShadowError(
                "path escapes its trusted root"
            )
        current = current.parent


def _secure_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow contains a symlink"
            )
        path.chmod(0o700 if path.is_dir() else 0o400)
    root.chmod(0o700)


def _validate_tree(root: Path, expected_files: set[str], expected_dirs: set[str]) -> None:
    actual_files: set[str] = set()
    actual_dirs: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow contains a symlink"
            )
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            actual_dirs.add(relative)
            if stat.S_IMODE(path.stat().st_mode) != 0o700:
                raise HistoricalCorporateActionResolutionShadowError(
                    "corporate-action shadow directory mode differs"
                )
        elif path.is_file():
            actual_files.add(relative)
            _require_regular_file(path, 0o400)
        else:
            raise HistoricalCorporateActionResolutionShadowError(
                "corporate-action shadow contains an unsafe entry"
            )
    if actual_files != expected_files or actual_dirs != expected_dirs:
        raise HistoricalCorporateActionResolutionShadowError(
            "corporate-action shadow file set differs"
        )


def _require_regular_file(path: Path, mode: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalCorporateActionResolutionShadowError(
            "required file is missing or unsafe"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or (
        mode is not None and stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HistoricalCorporateActionResolutionShadowError(
            "required file mode differs"
        )


def _read_json(path: Path) -> dict[str, object]:
    return _parse_json_bytes(_read_bounded_bytes(path))


def _parse_json_bytes(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoricalCorporateActionResolutionShadowError(
            "JSON evidence is invalid"
        ) from exc
    if not isinstance(value, dict):
        raise HistoricalCorporateActionResolutionShadowError(
            "JSON evidence must be an object"
        )
    return value


def _read_bounded_bytes(path: Path, *, maximum_bytes: int = MAXIMUM_JSON_BYTES) -> bytes:
    _require_regular_file(path)
    size = path.stat().st_size
    if size < 1 or size > maximum_bytes:
        raise HistoricalCorporateActionResolutionShadowError(
            "evidence file size is invalid"
        )
    return path.read_bytes()


def _counts(values: Iterator[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fingerprint(value: object) -> str:
    raw = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return _sha256(raw)


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


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
        raise HistoricalCorporateActionResolutionShadowError(
            "network access is prohibited while building the resolution shadow"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
