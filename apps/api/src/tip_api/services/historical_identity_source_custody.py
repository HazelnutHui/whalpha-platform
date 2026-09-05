"""Tmp-only normalized custody for profile-bound historical Identity sources."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import shutil
import socket
import stat
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    CONTRACT_VERSION,
    DATASET_NAME,
    ROW_CONTRACT_VERSION,
    SOURCE_FIELD_NAMES,
    HistoricalIdentityReferenceObservationV1,
    HistoricalIdentitySourceArtifactV1,
    HistoricalIdentitySourceCustodyManifestV1,
    build_historical_identity_reference_observation,
    historical_identity_source_content_fingerprint,
    historical_identity_source_fingerprint,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import FetchPackageManifestV1
from tip_api.providers.massive.instrument_master_snapshot import (
    ReferenceSnapshotBuildResult,
    build_snapshot_from_payloads,
)
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotReadResult
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
    identity_content_fingerprint,
    instrument_content_fingerprint,
    resolver_content_fingerprint,
)
from tip_api.services.historical_identity_rebuild_profile_map import (
    HistoricalIdentityRebuildProfile,
    HistoricalIdentityRebuildProfileMapV1,
    profile_binding_for_session,
)
from tip_api.services.historical_universe_membership_shadow import (
    HistoricalUniverseMembershipShadowError,
    apply_historical_identity_rebuild_profile,
    inspect_historical_identity_package_equivalence,
    read_identity_replay_ingested_at,
)


PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"
SCHEMA_PARTITION = "1"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
MAXIMUM_SESSIONS_PER_INVOCATION = 303
_SOURCE_WRAPPER_FIELDS = frozenset(
    {"count", "next_url", "request_id", "results", "status"}
)

ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("source_observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("source_page_sequence", pa.int32(), nullable=False),
        pa.field("source_row_sequence", pa.int32(), nullable=False),
        pa.field("active", pa.bool_(), nullable=True),
        pa.field("cik", pa.string(), nullable=True),
        pa.field("composite_figi", pa.string(), nullable=True),
        pa.field("currency_name", pa.string(), nullable=True),
        pa.field("last_updated_utc", pa.string(), nullable=True),
        pa.field("locale", pa.string(), nullable=True),
        pa.field("market", pa.string(), nullable=True),
        pa.field("name", pa.string(), nullable=True),
        pa.field("primary_exchange", pa.string(), nullable=True),
        pa.field("share_class_figi", pa.string(), nullable=True),
        pa.field("ticker", pa.string(), nullable=True),
        pa.field("type", pa.string(), nullable=True),
        pa.field("source_record_fingerprint", pa.string(), nullable=False),
    ]
)


class HistoricalIdentitySourceCustodyError(RuntimeError):
    """Fail-closed error at the normalized source-custody boundary."""


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceCustodyReadResult:
    partition_path: Path
    manifest: HistoricalIdentitySourceCustodyManifestV1
    records: tuple[HistoricalIdentityReferenceObservationV1, ...]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceCustodyWriteResult:
    partition_path: Path
    manifest: HistoricalIdentitySourceCustodyManifestV1
    manifest_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceCustodyEquivalence:
    session_date: date
    rebuild_profile: HistoricalIdentityRebuildProfile
    identity_replay_ingested_at: datetime
    identity: InstrumentMasterSnapshotReadResult
    rebuilt_identity: ReferenceSnapshotBuildResult
    instrument_fingerprint: str
    identity_fingerprint: str
    resolver_fingerprint: str
    instrument_match: bool
    identity_match: bool
    resolver_match: bool

    @property
    def exact_match(self) -> bool:
        return self.instrument_match and self.identity_match and self.resolver_match


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceCustodyBatchItem:
    session_date: date
    rebuild_profile: str
    status: str
    record_count: int
    source_response_bytes: int
    normalized_parquet_bytes: int
    content_fingerprint: str
    parquet_sha256: str
    manifest_sha256: str
    logical_fingerprint: str


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceCustodyBatchResult:
    contract_version: str
    worker_count: int
    maximum_sessions: int
    bound_session_count: int
    completed_before_count: int
    selected_session_count: int
    completed_after_count: int
    remaining_session_count: int
    status: str
    items: tuple[HistoricalIdentitySourceCustodyBatchItem, ...]
    external_request_count: int = 0
    canonical_data_write_count: int = 0
    universe_membership_write_count: int = 0


def build_historical_identity_source_custody_candidate(
    *,
    data_root: Path,
    package_path: Path,
    output_root: Path,
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    session_date: date,
    materialized_at: datetime,
) -> HistoricalIdentitySourceCustodyWriteResult:
    """Normalize one exact retained package into a tmp-only immutable partition."""

    canonical_root = data_root.resolve(strict=True)
    if canonical_root != APPROVED_DATA_ROOT or data_root.is_symlink():
        raise HistoricalIdentitySourceCustodyError(
            "canonical data root is not the approved Dell root"
        )
    candidate_root = _validated_tmp_output_root(output_root)
    materialized_at = normalize_utc_datetime(materialized_at)
    binding = profile_binding_for_session(profile_map, session_date)
    try:
        equivalence = inspect_historical_identity_package_equivalence(
            data_root=canonical_root,
            package_path=package_path,
            session_date=session_date,
            rebuild_profile=binding.rebuild_profile,
        )
    except HistoricalUniverseMembershipShadowError as exc:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity package equivalence failed"
        ) from exc
    if not equivalence.exact_match:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity package is not exact under its bound profile"
        )
    _validate_profile_binding(
        profile_map=profile_map,
        package_path=package_path,
        session_date=session_date,
        equivalence=equivalence,
    )
    records, artifacts = _normalize_package_pages(
        pages=equivalence.package.pages,
        package_artifacts=equivalence.package.manifest.artifacts,
        provider=equivalence.package.manifest.provider_id,
        session_date=session_date,
        observed_at=equivalence.package.manifest.fetched_at,
    )
    partition = _partition_path(
        candidate_root,
        provider=equivalence.package.manifest.provider_id,
        session_date=session_date,
    )
    existing = _read_if_present(candidate_root, partition)
    if existing is not None:
        _validate_existing_source_identity(
            existing=existing,
            records=records,
            artifacts=artifacts,
            profile_map=profile_map,
            binding=binding,
            package_manifest_sha256=equivalence.package.package_manifest_sha256,
        )
        if not inspect_historical_identity_source_custody_equivalence(
            data_root=canonical_root,
            custody=existing,
        ).exact_match:
            raise HistoricalIdentitySourceCustodyError(
                "existing normalized source does not reconstruct accepted Identity"
            )
        return HistoricalIdentitySourceCustodyWriteResult(
            partition_path=partition,
            manifest=existing.manifest,
            manifest_sha256=existing.manifest_sha256,
            status="already_present",
        )

    staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
    _mkdirs_owner_only(partition.parent, candidate_root)
    if staging.exists() or staging.is_symlink():
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody staging path already exists"
        )
    staging.mkdir(mode=0o700)
    try:
        parquet_path = staging / PARQUET_FILE
        table = pa.Table.from_pylist(
            [item.model_dump(mode="python") for item in records],
            schema=ARROW_SCHEMA,
        )
        pq.write_table(
            table,
            parquet_path,
            compression="zstd",
            compression_level=6,
            use_dictionary=True,
            write_statistics=True,
        )
        parquet_path.chmod(0o400)
        _fsync_file(parquet_path)
        parquet_sha256 = _file_sha256(parquet_path)
        content_fingerprint = historical_identity_source_content_fingerprint(
            records
        )
        base = {
            "contract_version": CONTRACT_VERSION,
            "completion_status": "completed",
            "dataset_name": DATASET_NAME,
            "data_family_id": "point_in_time_identity",
            "data_layer": "source_observation",
            "content_scope": "internal_only",
            "retention_class": "canonical_no_auto_expiry",
            "point_in_time_eligibility": "outcome_reconciliation_only",
            "provider": equivalence.package.manifest.provider_id,
            "as_of_date": session_date,
            "materialized_at": materialized_at,
            "source_package_fetched_at": equivalence.package.manifest.fetched_at,
            "source_locator_sha256": binding.source_locator_sha256,
            "source_package_manifest_sha256": (
                equivalence.package.package_manifest_sha256
            ),
            "source_package_content_sha256": (
                equivalence.package.manifest.package_content_sha256
            ),
            "source_request_count": equivalence.package.manifest.request_count,
            "source_artifacts": artifacts,
            "source_field_names": SOURCE_FIELD_NAMES,
            "identity_rebuild_profile": binding.rebuild_profile,
            "identity_profile_map_fingerprint": profile_map.logical_fingerprint,
            "identity_profile_binding_fingerprint": binding.logical_fingerprint,
            "canonical_snapshot_fingerprint": (
                binding.canonical_snapshot_fingerprint
            ),
            "canonical_instrument_fingerprint": (
                binding.canonical_instrument_fingerprint
            ),
            "canonical_identity_fingerprint": binding.canonical_identity_fingerprint,
            "canonical_resolver_fingerprint": (
                binding.canonical_resolver_fingerprint
            ),
            "parquet_file": PARQUET_FILE,
            "record_count": len(records),
            "content_fingerprint": content_fingerprint,
            "parquet_sha256": parquet_sha256,
            "raw_response_retained": False,
            "response_url_retained": False,
            "request_identifier_retained": False,
            "credential_material_retained": False,
            "external_request_count": 0,
            "canonical_data_write_count": 0,
            "universe_membership_write_count": 0,
            "historical_coverage_authorized": False,
            "research_performance_authorized": False,
        }
        manifest = HistoricalIdentitySourceCustodyManifestV1.model_validate(
            {
                **base,
                "logical_fingerprint": historical_identity_source_fingerprint(
                    _json_ready(base)
                ),
            }
        )
        manifest_path = staging / MANIFEST_FILE
        manifest_path.write_bytes(_pretty_json_bytes(manifest.model_dump(mode="json")))
        manifest_path.chmod(0o400)
        _fsync_file(manifest_path)
        _fsync_directory(staging)
        staging.replace(partition)
        _fsync_directory(partition.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise

    reread = read_historical_identity_source_custody_candidate(
        root=candidate_root,
        provider=equivalence.package.manifest.provider_id,
        session_date=session_date,
    )
    if reread.records != records or reread.manifest != manifest:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody formal reread differs"
        )
    normalized_equivalence = inspect_historical_identity_source_custody_equivalence(
        data_root=canonical_root,
        custody=reread,
    )
    if not normalized_equivalence.exact_match:
        raise HistoricalIdentitySourceCustodyError(
            "normalized historical Identity source does not reconstruct "
            "accepted Identity"
        )
    return HistoricalIdentitySourceCustodyWriteResult(
        partition_path=partition,
        manifest=manifest,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def run_historical_identity_source_custody_batch(
    *,
    data_root: Path,
    package_roots: tuple[Path, ...],
    output_root: Path,
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    materialized_at: datetime,
    maximum_sessions: int,
    workers: int = 1,
    sessions: tuple[date, ...] | None = None,
) -> HistoricalIdentitySourceCustodyBatchResult:
    """Build a bounded, resumable set of independent tmp-only partitions."""

    if not 1 <= maximum_sessions <= MAXIMUM_SESSIONS_PER_INVOCATION:
        raise HistoricalIdentitySourceCustodyError(
            "maximum sessions must be between one and 303"
        )
    if not 1 <= workers <= 4:
        raise HistoricalIdentitySourceCustodyError(
            "source-custody workers must be between one and four"
        )
    canonical_root = data_root.resolve(strict=True)
    if canonical_root != APPROVED_DATA_ROOT or data_root.is_symlink():
        raise HistoricalIdentitySourceCustodyError(
            "canonical data root is not the approved Dell root"
        )
    candidate_root = _validated_tmp_output_root(output_root)
    materialized_at = normalize_utc_datetime(materialized_at)
    package_by_session = _discover_profile_bound_packages(
        package_roots=package_roots,
        output_root=candidate_root,
        profile_map=profile_map,
    )
    provider_parent = (
        candidate_root
        / "market-data"
        / DATASET_NAME
        / f"schema_version={SCHEMA_PARTITION}"
        / f"provider={MASSIVE_PROVIDER_ID}"
    )
    _mkdirs_owner_only(provider_parent, candidate_root)

    completed_before: list[date] = []
    pending: list[date] = []
    for binding in profile_map.bindings:
        partition = _partition_path(
            candidate_root,
            provider=MASSIVE_PROVIDER_ID,
            session_date=binding.session_date,
        )
        if partition.exists() or partition.is_symlink():
            existing = read_historical_identity_source_custody_candidate(
                root=candidate_root,
                provider=MASSIVE_PROVIDER_ID,
                session_date=binding.session_date,
            )
            if (
                existing.manifest.identity_profile_map_fingerprint
                != profile_map.logical_fingerprint
                or existing.manifest.identity_profile_binding_fingerprint
                != binding.logical_fingerprint
                or existing.manifest.source_locator_sha256
                != binding.source_locator_sha256
                or existing.manifest.source_package_manifest_sha256
                != binding.package_manifest_sha256
                or existing.manifest.source_package_content_sha256
                != binding.package_content_sha256
                or not inspect_historical_identity_source_custody_equivalence(
                    data_root=canonical_root,
                    custody=existing,
                ).exact_match
            ):
                raise HistoricalIdentitySourceCustodyError(
                    "completed source-custody partition differs from current bindings"
                )
            completed_before.append(binding.session_date)
        else:
            pending.append(binding.session_date)

    if sessions is None:
        selected = tuple(pending[:maximum_sessions])
    else:
        if (
            not sessions
            or len(sessions) > maximum_sessions
            or len(sessions) != len(set(sessions))
        ):
            raise HistoricalIdentitySourceCustodyError(
                "explicit sessions must be unique and within the batch ceiling"
            )
        bound_sessions = {item.session_date for item in profile_map.bindings}
        if set(sessions) - bound_sessions:
            raise HistoricalIdentitySourceCustodyError(
                "explicit session is not profile-bound"
            )
        selected = tuple(sorted(sessions))

    jobs = tuple(
        (
            canonical_root,
            package_by_session[session],
            candidate_root,
            profile_map,
            session,
            materialized_at,
        )
        for session in selected
    )
    writes: list[HistoricalIdentitySourceCustodyWriteResult] = []
    if workers == 1:
        for job in jobs:
            writes.append(_build_custody_worker(job))
    elif jobs:
        context = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_disable_network_in_worker,
        ) as executor:
            futures = {
                executor.submit(_build_custody_worker, job): job[4]
                for job in jobs
            }
            try:
                for future in as_completed(futures):
                    writes.append(future.result())
            except Exception:
                for future in futures:
                    future.cancel()
                raise
    writes.sort(key=lambda item: item.manifest.as_of_date)
    items = tuple(
        HistoricalIdentitySourceCustodyBatchItem(
            session_date=item.manifest.as_of_date,
            rebuild_profile=item.manifest.identity_rebuild_profile,
            status=item.status,
            record_count=item.manifest.record_count,
            source_response_bytes=sum(
                artifact.source_response_bytes
                for artifact in item.manifest.source_artifacts
            ),
            normalized_parquet_bytes=(
                item.partition_path / PARQUET_FILE
            ).stat().st_size,
            content_fingerprint=item.manifest.content_fingerprint,
            parquet_sha256=item.manifest.parquet_sha256,
            manifest_sha256=item.manifest_sha256,
            logical_fingerprint=item.manifest.logical_fingerprint,
        )
        for item in writes
    )
    completed_before_set = set(completed_before)
    completed_after = len(completed_before) + sum(
        item.manifest.as_of_date not in completed_before_set for item in writes
    )
    remaining = profile_map.bound_session_count - completed_after
    return HistoricalIdentitySourceCustodyBatchResult(
        contract_version=CONTRACT_VERSION,
        worker_count=workers,
        maximum_sessions=maximum_sessions,
        bound_session_count=profile_map.bound_session_count,
        completed_before_count=len(completed_before),
        selected_session_count=len(selected),
        completed_after_count=completed_after,
        remaining_session_count=remaining,
        status="complete" if remaining == 0 else "batch_complete",
        items=items,
    )


def read_historical_identity_source_custody_candidate(
    *,
    root: Path,
    provider: str,
    session_date: date,
) -> HistoricalIdentitySourceCustodyReadResult:
    """Formally reread one owner-only tmp candidate partition."""

    candidate_root = _validated_tmp_output_root(root)
    partition = _partition_path(
        candidate_root,
        provider=provider,
        session_date=session_date,
    )
    _owner_only_directory_chain(partition, candidate_root)
    if partition.is_symlink() or not partition.is_dir():
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody partition is unavailable"
        )
    if stat.S_IMODE(partition.stat().st_mode) != 0o700:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody partition is not owner-only"
        )
    return _read_historical_identity_source_custody_partition(
        partition=partition,
        provider=provider,
        session_date=session_date,
        expected_file_mode=0o400,
    )


def read_historical_identity_source_custody(
    *,
    data_root: Path,
    provider: str,
    session_date: date,
) -> HistoricalIdentitySourceCustodyReadResult:
    """Formally reread one canonical Dell historical source partition."""

    canonical_root = _validated_canonical_data_root(data_root)
    partition = _partition_path(
        canonical_root,
        provider=provider,
        session_date=session_date,
    )
    _canonical_directory_chain(partition, canonical_root)
    if stat.S_IMODE(partition.stat().st_mode) != 0o755:
        raise HistoricalIdentitySourceCustodyError(
            "canonical historical source partition mode differs"
        )
    return _read_historical_identity_source_custody_partition(
        partition=partition,
        provider=provider,
        session_date=session_date,
        expected_file_mode=0o644,
    )


def _read_historical_identity_source_custody_partition(
    *,
    partition: Path,
    provider: str,
    session_date: date,
    expected_file_mode: int,
) -> HistoricalIdentitySourceCustodyReadResult:
    entries = {item.name for item in partition.iterdir()}
    if entries != {PARQUET_FILE, MANIFEST_FILE}:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody file set differs"
        )
    manifest_path = partition / MANIFEST_FILE
    parquet_path = partition / PARQUET_FILE
    for path in (manifest_path, parquet_path):
        _regular_file_with_mode(path, expected_file_mode)
    try:
        manifest = HistoricalIdentitySourceCustodyManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody manifest is invalid"
        ) from exc
    if (
        manifest.provider != provider
        or manifest.as_of_date != session_date
        or manifest.parquet_file != PARQUET_FILE
    ):
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody partition identity differs"
        )
    if _file_sha256(parquet_path) != manifest.parquet_sha256:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody Parquet hash differs"
        )
    try:
        table = pq.ParquetFile(parquet_path).read()
    except Exception as exc:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody Parquet is unreadable"
        ) from exc
    if table.schema != ARROW_SCHEMA or table.num_rows != manifest.record_count:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody schema or count differs"
        )
    try:
        records = tuple(
            HistoricalIdentityReferenceObservationV1.model_validate(item)
            for item in table.to_pylist()
        )
    except Exception as exc:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody records are invalid"
        ) from exc
    expected_order = tuple(
        sorted(
            records,
            key=lambda item: (item.source_page_sequence, item.source_row_sequence),
        )
    )
    if records != expected_order or len(
        {
            (item.source_page_sequence, item.source_row_sequence)
            for item in records
        }
    ) != len(records):
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody record order differs"
        )
    if historical_identity_source_content_fingerprint(records) != (
        manifest.content_fingerprint
    ):
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody content fingerprint differs"
        )
    page_counts: dict[int, int] = {}
    for item in records:
        page_counts[item.source_page_sequence] = (
            page_counts.get(item.source_page_sequence, 0) + 1
        )
    if tuple(
        page_counts.get(item.sequence, 0) for item in manifest.source_artifacts
    ) != tuple(item.row_count for item in manifest.source_artifacts):
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity source-custody page counts differ"
        )
    return HistoricalIdentitySourceCustodyReadResult(
        partition_path=partition,
        manifest=manifest,
        records=records,
        manifest_sha256=_file_sha256(manifest_path),
    )


def inspect_historical_identity_source_custody_equivalence(
    *,
    data_root: Path,
    custody: HistoricalIdentitySourceCustodyReadResult,
) -> HistoricalIdentitySourceCustodyEquivalence:
    """Rebuild accepted Identity from normalized rows without the source package."""

    canonical_root = data_root.resolve(strict=True)
    if canonical_root != APPROVED_DATA_ROOT or data_root.is_symlink():
        raise HistoricalIdentitySourceCustodyError(
            "canonical data root is not the approved Dell root"
        )
    manifest = custody.manifest
    accepted = ParquetInstrumentMasterSnapshotRepository(
        canonical_root
    ).inspect_snapshot(manifest.as_of_date)
    if (
        accepted.snapshot_content_sha256 != manifest.canonical_snapshot_fingerprint
        or accepted.instrument_content_sha256
        != manifest.canonical_instrument_fingerprint
        or accepted.identity_content_sha256 != manifest.canonical_identity_fingerprint
        or accepted.resolver_content_sha256 != manifest.canonical_resolver_fingerprint
    ):
        raise HistoricalIdentitySourceCustodyError(
            "normalized source manifest differs from accepted canonical Identity"
        )
    identity_replay_ingested_at = read_identity_replay_ingested_at(accepted)
    rebuilt = build_snapshot_from_payloads(
        payloads=tuple(item.source_payload() for item in custody.records),
        as_of_date=manifest.as_of_date,
        ingested_at=identity_replay_ingested_at,
        request_count=manifest.source_request_count,
        pagination_complete=True,
    )
    rebuilt = apply_historical_identity_rebuild_profile(
        rebuilt,
        rebuild_profile=manifest.identity_rebuild_profile,
    )
    if rebuilt.raw_record_count != manifest.record_count:
        raise HistoricalIdentitySourceCustodyError(
            "normalized source rebuild record count differs"
        )
    instrument_fingerprint = instrument_content_fingerprint(rebuilt.instruments)
    identity_fingerprint = identity_content_fingerprint(rebuilt.identities)
    resolver_fingerprint = resolver_content_fingerprint(rebuilt.resolvers)
    return HistoricalIdentitySourceCustodyEquivalence(
        session_date=manifest.as_of_date,
        rebuild_profile=manifest.identity_rebuild_profile,
        identity_replay_ingested_at=identity_replay_ingested_at,
        identity=accepted,
        rebuilt_identity=rebuilt,
        instrument_fingerprint=instrument_fingerprint,
        identity_fingerprint=identity_fingerprint,
        resolver_fingerprint=resolver_fingerprint,
        instrument_match=(
            instrument_fingerprint == manifest.canonical_instrument_fingerprint
        ),
        identity_match=(
            identity_fingerprint == manifest.canonical_identity_fingerprint
        ),
        resolver_match=(
            resolver_fingerprint == manifest.canonical_resolver_fingerprint
        ),
    )


def _normalize_package_pages(
    *,
    pages: tuple[Mapping[str, object], ...],
    package_artifacts: tuple[object, ...],
    provider: str,
    session_date: date,
    observed_at: datetime,
) -> tuple[
    tuple[HistoricalIdentityReferenceObservationV1, ...],
    tuple[HistoricalIdentitySourceArtifactV1, ...],
]:
    if len(pages) != len(package_artifacts) or not pages:
        raise HistoricalIdentitySourceCustodyError(
            "source pages and package artifacts differ"
        )
    records: list[HistoricalIdentityReferenceObservationV1] = []
    artifact_rows: list[HistoricalIdentitySourceArtifactV1] = []
    for page_sequence, (page, package_artifact) in enumerate(
        zip(pages, package_artifacts),
        1,
    ):
        unexpected_wrapper_fields = set(page) - _SOURCE_WRAPPER_FIELDS
        if unexpected_wrapper_fields:
            raise HistoricalIdentitySourceCustodyError(
                "source page contains an unreviewed wrapper field"
            )
        results = page.get("results")
        if not isinstance(results, list) or not all(
            isinstance(item, Mapping) for item in results
        ):
            raise HistoricalIdentitySourceCustodyError(
                "source page results are malformed"
            )
        reported_count = page.get("count")
        if reported_count is not None and (
            not isinstance(reported_count, int)
            or isinstance(reported_count, bool)
            or reported_count != len(results)
        ):
            raise HistoricalIdentitySourceCustodyError(
                "source page reported count differs from results"
            )
        status_value = page.get("status")
        if status_value is not None and not isinstance(status_value, str):
            raise HistoricalIdentitySourceCustodyError(
                "source page status is not a string"
            )
        next_url = page.get("next_url")
        pagination_continues = isinstance(next_url, str) and bool(next_url.strip())
        if pagination_continues != (page_sequence < len(pages)):
            raise HistoricalIdentitySourceCustodyError(
                "source page pagination envelope differs"
            )
        request_id = page.get("request_id")
        if request_id is not None and not isinstance(request_id, str):
            raise HistoricalIdentitySourceCustodyError(
                "source page request identifier has an unsupported type"
            )
        for row_sequence, source in enumerate(results, 1):
            unexpected_source_fields = set(source) - set(SOURCE_FIELD_NAMES)
            if unexpected_source_fields:
                raise HistoricalIdentitySourceCustodyError(
                    "source result contains an unreviewed field"
                )
            records.append(
                build_historical_identity_reference_observation(
                    provider=provider,
                    as_of_date=session_date,
                    source_observed_at=observed_at,
                    source_page_sequence=page_sequence,
                    source_row_sequence=row_sequence,
                    source_payload=dict(source),
                )
            )
        artifact_rows.append(
            HistoricalIdentitySourceArtifactV1(
                sequence=page_sequence,
                source_response_sha256=package_artifact.canonical_response_sha256,
                source_response_bytes=package_artifact.response_bytes,
                row_count=len(results),
                reported_count=reported_count,
                reported_status=status_value,
                pagination_continues=pagination_continues,
            )
        )
    return tuple(records), tuple(artifact_rows)


def _discover_profile_bound_packages(
    *,
    package_roots: tuple[Path, ...],
    output_root: Path,
    profile_map: HistoricalIdentityRebuildProfileMapV1,
) -> dict[date, Path]:
    resolved_roots = _validate_package_roots(package_roots)
    if any(
        root == output_root
        or root in output_root.parents
        or output_root in root.parents
        for root in resolved_roots
    ):
        raise HistoricalIdentitySourceCustodyError(
            "source package and custody output roots overlap"
        )
    discovered: list[tuple[date, Path, str, str, str]] = []
    unroutable = 0
    for root in resolved_roots:
        for manifest_path in _manifest_paths(root):
            try:
                _regular_nonsymlink_file(manifest_path)
                raw = manifest_path.read_bytes()
                manifest = FetchPackageManifestV1.model_validate_json(raw)
            except Exception:
                unroutable += 1
                continue
            if manifest.package_type != "identity_reference":
                continue
            package_path = manifest_path.parent.resolve(strict=True)
            discovered.append(
                (
                    manifest.session_date,
                    package_path,
                    hashlib.sha256(str(package_path).encode("utf-8")).hexdigest(),
                    hashlib.sha256(raw).hexdigest(),
                    manifest.package_content_sha256,
                )
            )
    if unroutable:
        raise HistoricalIdentitySourceCustodyError(
            "source package roots contain an unroutable manifest"
        )
    discovered.sort(key=lambda item: (item[0], item[3], item[4], item[2]))
    inventory = [
        {
            "session_date": item[0].isoformat(),
            "package_manifest_sha256": item[3],
            "package_content_sha256": item[4],
            "source_locator_sha256": item[2],
        }
        for item in discovered
    ]
    if (
        len(discovered)
        != profile_map.bound_session_count
        + len(profile_map.unbound_identity_mismatch_session_dates)
        or historical_identity_source_fingerprint(inventory)
        != profile_map.discovered_package_inventory_fingerprint
    ):
        raise HistoricalIdentitySourceCustodyError(
            "discovered package inventory differs from the profile map"
        )
    bindings = {item.session_date: item for item in profile_map.bindings}
    unbound_sessions = set(profile_map.unbound_identity_mismatch_session_dates)
    discovered_unbound_sessions: set[date] = set()
    result: dict[date, Path] = {}
    for session, package_path, locator, manifest_sha, content_sha in discovered:
        binding = bindings.get(session)
        if binding is None:
            if (
                session not in unbound_sessions
                or session in discovered_unbound_sessions
            ):
                raise HistoricalIdentitySourceCustodyError(
                    "discovered package session is not uniquely declared unbound"
                )
            discovered_unbound_sessions.add(session)
            continue
        if session in result:
            raise HistoricalIdentitySourceCustodyError(
                "multiple source packages exist for one session"
            )
        if (
            locator != binding.source_locator_sha256
            or manifest_sha != binding.package_manifest_sha256
            or content_sha != binding.package_content_sha256
        ):
            raise HistoricalIdentitySourceCustodyError(
                "discovered package differs from its profile binding"
            )
        result[session] = package_path
    if set(result) != set(bindings):
        raise HistoricalIdentitySourceCustodyError(
            "profile-bound package set is incomplete"
        )
    if discovered_unbound_sessions != unbound_sessions:
        raise HistoricalIdentitySourceCustodyError(
            "profile-map unbound package set is incomplete"
        )
    return result


def _validate_package_roots(package_roots: tuple[Path, ...]) -> tuple[Path, ...]:
    if not package_roots:
        raise HistoricalIdentitySourceCustodyError(
            "at least one explicit source package root is required"
        )
    temporary_root = Path("/tmp").resolve(strict=True)
    resolved: list[Path] = []
    for raw in package_roots:
        if (
            not raw.is_absolute()
            or temporary_root not in raw.parents
            or raw.is_symlink()
        ):
            raise HistoricalIdentitySourceCustodyError(
                "source package root must not be a symlink"
            )
        _reject_symlink_chain(raw, temporary_root)
        item = raw.resolve(strict=True)
        if temporary_root not in item.parents or not item.is_dir():
            raise HistoricalIdentitySourceCustodyError(
                "source package root must be an existing directory below /tmp"
            )
        if any(
            item == existing
            or item in existing.parents
            or existing in item.parents
            for existing in resolved
        ):
            raise HistoricalIdentitySourceCustodyError(
                "source package roots must be unique and non-overlapping"
            )
        resolved.append(item)
    return tuple(sorted(resolved))


def _manifest_paths(root: Path) -> tuple[Path, ...]:
    manifests: list[Path] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            item for item in directories if not (current_path / item).is_symlink()
        )
        if "package.json" not in files:
            continue
        manifests.append(current_path / "package.json")
        directories[:] = []
    return tuple(sorted(manifests))


def _build_custody_worker(
    job: tuple[
        Path,
        Path,
        Path,
        HistoricalIdentityRebuildProfileMapV1,
        date,
        datetime,
    ],
) -> HistoricalIdentitySourceCustodyWriteResult:
    data_root, package_path, output_root, profile_map, session, materialized_at = job
    return build_historical_identity_source_custody_candidate(
        data_root=data_root,
        package_path=package_path,
        output_root=output_root,
        profile_map=profile_map,
        session_date=session,
        materialized_at=materialized_at,
    )


def _disable_network_in_worker() -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalIdentitySourceCustodyError(
            "network access is disabled in historical source-custody workers"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]


def _validate_profile_binding(
    *,
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    package_path: Path,
    session_date: date,
    equivalence: object,
) -> None:
    binding = profile_binding_for_session(profile_map, session_date)
    package = equivalence.package
    identity = equivalence.identity
    locator = hashlib.sha256(
        str(package_path.resolve(strict=True)).encode("utf-8")
    ).hexdigest()
    package_facts_match = (
        locator == binding.source_locator_sha256
        and package.package_manifest_sha256 == binding.package_manifest_sha256
        and package.manifest.package_content_sha256
        == binding.package_content_sha256
        and normalize_utc_datetime(package.manifest.fetched_at)
        == normalize_utc_datetime(binding.package_fetched_at)
    )
    canonical_facts_match = (
        identity.snapshot_content_sha256 == binding.canonical_snapshot_fingerprint
        and identity.instrument_content_sha256
        == binding.canonical_instrument_fingerprint
        and identity.identity_content_sha256 == binding.canonical_identity_fingerprint
        and identity.resolver_content_sha256 == binding.canonical_resolver_fingerprint
    )
    if not package_facts_match or not canonical_facts_match:
        raise HistoricalIdentitySourceCustodyError(
            "historical Identity profile binding differs from source or canonical facts"
        )


def _validate_existing_source_identity(
    *,
    existing: HistoricalIdentitySourceCustodyReadResult,
    records: tuple[HistoricalIdentityReferenceObservationV1, ...],
    artifacts: tuple[HistoricalIdentitySourceArtifactV1, ...],
    profile_map: HistoricalIdentityRebuildProfileMapV1,
    binding: object,
    package_manifest_sha256: str,
) -> None:
    manifest = existing.manifest
    if existing.records != records or (
        manifest.source_artifacts != artifacts
        or manifest.identity_profile_map_fingerprint
        != profile_map.logical_fingerprint
        or manifest.identity_profile_binding_fingerprint
        != binding.logical_fingerprint
        or manifest.source_package_manifest_sha256 != package_manifest_sha256
        or manifest.source_package_content_sha256
        != binding.package_content_sha256
        or manifest.source_locator_sha256 != binding.source_locator_sha256
    ):
        raise HistoricalIdentitySourceCustodyError(
            "existing historical Identity source custody conflicts"
        )


def _partition_path(root: Path, *, provider: str, session_date: date) -> Path:
    if not provider or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in provider
    ):
        raise HistoricalIdentitySourceCustodyError("provider path component is invalid")
    return (
        root
        / "market-data"
        / DATASET_NAME
        / f"schema_version={SCHEMA_PARTITION}"
        / f"provider={provider}"
        / f"as_of_date={session_date.isoformat()}"
    )


def _validated_tmp_output_root(path: Path) -> Path:
    temporary_root = Path("/tmp").resolve(strict=True)
    if (
        not path.is_absolute()
        or temporary_root not in path.parents
        or not path.exists()
        or path.is_symlink()
    ):
        raise HistoricalIdentitySourceCustodyError(
            "source-custody output root must be an existing directory"
        )
    _reject_symlink_chain(path, temporary_root)
    resolved = path.resolve(strict=True)
    if (
        resolved != path
        or temporary_root not in resolved.parents
        or not resolved.is_dir()
    ):
        raise HistoricalIdentitySourceCustodyError(
            "source-custody output root must be below /tmp"
        )
    if stat.S_IMODE(resolved.stat().st_mode) != 0o700:
        raise HistoricalIdentitySourceCustodyError(
            "source-custody output root must be owner-only"
        )
    return resolved


def _validated_canonical_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalIdentitySourceCustodyError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT or resolved != path:
        raise HistoricalIdentitySourceCustodyError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _read_if_present(
    root: Path,
    partition: Path,
) -> HistoricalIdentitySourceCustodyReadResult | None:
    if not partition.exists() and not partition.is_symlink():
        return None
    return read_historical_identity_source_custody_candidate(
        root=root,
        provider=MASSIVE_PROVIDER_ID,
        session_date=date.fromisoformat(partition.name.removeprefix("as_of_date=")),
    )


def _mkdirs_owner_only(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while current != root:
        if current.exists() or current.is_symlink():
            break
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        raise HistoricalIdentitySourceCustodyError(
            "source-custody parent path is unsafe"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o700)
        _fsync_directory(item.parent)
    _reject_symlink_chain(path, root)
    current = path
    while True:
        if stat.S_IMODE(current.stat().st_mode) != 0o700:
            raise HistoricalIdentitySourceCustodyError(
                "source-custody directory is not owner-only"
            )
        if current == root:
            break
        current = current.parent


def _reject_symlink_chain(path: Path, root: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise HistoricalIdentitySourceCustodyError(
                "source-custody path contains a symlink"
            )
        if current == root:
            return
        if root not in current.parents:
            raise HistoricalIdentitySourceCustodyError(
                "source-custody path escapes its root"
            )
        current = current.parent


def _regular_owner_read_only_file(path: Path) -> None:
    _regular_file_with_mode(path, 0o400)


def _regular_file_with_mode(path: Path, expected_mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalIdentitySourceCustodyError(
            "source-custody artifact is not a regular file"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != expected_mode
    ):
        raise HistoricalIdentitySourceCustodyError(
            "source-custody artifact mode differs"
        )


def _owner_only_directory_chain(path: Path, root: Path) -> None:
    _reject_symlink_chain(path, root)
    current = path
    while True:
        if not current.is_dir() or stat.S_IMODE(current.stat().st_mode) != 0o700:
            raise HistoricalIdentitySourceCustodyError(
                "source-custody directory chain is not owner-only"
            )
        if current == root:
            return
        current = current.parent


def _canonical_directory_chain(path: Path, root: Path) -> None:
    _reject_symlink_chain(path, root)
    current = path
    while True:
        if not current.is_dir() or stat.S_IMODE(current.stat().st_mode) & 0o002:
            raise HistoricalIdentitySourceCustodyError(
                "canonical historical source directory chain is unsafe"
            )
        if current == root:
            return
        current = current.parent


def _regular_nonsymlink_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalIdentitySourceCustodyError(
            "source package manifest is not a regular file"
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pretty_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _json_ready(value: object) -> object:
    return to_jsonable_python(value)


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
