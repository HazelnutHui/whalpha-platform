"""Build and formally reread a disconnected inactive-lifecycle resolution shadow."""

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
from pathlib import Path
from typing import Iterator, Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    DECISION_ROW_CONTRACT_VERSION,
    MANIFEST_CONTRACT_VERSION,
    REVIEW_LIMITATION_CODES,
    SOURCE_FIELD_NAMES,
    SOURCE_ROW_CONTRACT_VERSION,
    HistoricalInactiveLifecycleResolutionDecisionV1,
    HistoricalInactiveLifecycleResolutionShadowManifestV1,
    HistoricalInactiveLifecycleSourceObservationV1,
    InactiveLifecycleDisposition,
    InactiveLifecycleIdentityType,
    InactiveLifecycleShadowArtifactV1,
    inactive_lifecycle_fingerprint,
    inactive_lifecycle_rows_fingerprint,
)
from tip_api.contracts.market_data.v1.provider_instrument_identity import (
    ResolutionStatus,
)
from tip_api.ingestion.instrument_identity import (
    canonical_instrument_id_for_identity,
    select_stable_identity,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    INSTRUMENT_MASTER_ARROW_SCHEMA,
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.historical_inactive_lifecycle_source import (
    HistoricalInactiveLifecycleSourceError,
    read_historical_inactive_lifecycle_source_payloads,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
SOURCE_FILE = "source-observations.parquet"
DECISION_FILE = "resolution-decisions.parquet"
MANIFEST_FILE = "manifest.json"
SCHEMA_PARTITION = "1"
_SOURCE_WRAPPER_FIELDS = frozenset({"count", "results", "status"})
_SOURCE_STRING_FIELDS = tuple(field for field in SOURCE_FIELD_NAMES if field != "active")
_SHA256_PATTERN = frozenset("0123456789abcdef")

SOURCE_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("anchor_date", pa.date32(), nullable=False),
        pa.field("source_observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("source_page_sequence", pa.int32(), nullable=False),
        pa.field("source_row_sequence", pa.int32(), nullable=False),
        pa.field("active", pa.bool_(), nullable=False),
        *[pa.field(field, pa.string(), nullable=True) for field in _SOURCE_STRING_FIELDS],
        pa.field("source_payload_fingerprint", pa.string(), nullable=False),
        pa.field("source_observation_fingerprint", pa.string(), nullable=False),
    ]
)

DECISION_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("anchor_date", pa.date32(), nullable=False),
        pa.field("source_observation_fingerprint", pa.string(), nullable=False),
        pa.field("source_payload_fingerprint", pa.string(), nullable=False),
        pa.field("source_page_sequence", pa.int32(), nullable=False),
        pa.field("source_row_sequence", pa.int32(), nullable=False),
        pa.field("selected_identity_type", pa.string(), nullable=True),
        pa.field("selected_identity_value", pa.string(), nullable=True),
        pa.field("identity_resolution_status", pa.string(), nullable=False),
        pa.field("canonical_instrument_id", pa.string(), nullable=True),
        pa.field("canonical_first_observed_date", pa.date32(), nullable=True),
        pa.field("canonical_last_observed_date", pa.date32(), nullable=True),
        pa.field("effective_date_candidate", pa.date32(), nullable=True),
        pa.field("ticker_seen_in_canonical_history", pa.bool_(), nullable=True),
        pa.field("disposition", pa.string(), nullable=False),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("source_package_logical_fingerprint", pa.string(), nullable=False),
        pa.field("canonical_instrument_history_fingerprint", pa.string(), nullable=False),
        pa.field("evaluated_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)


class HistoricalInactiveLifecycleResolutionShadowError(RuntimeError):
    """Raised when the disconnected resolution shadow cannot be trusted."""


@dataclass(frozen=True, slots=True)
class HistoricalInactiveLifecycleResolutionShadowReadResult:
    partition_path: Path
    manifest: HistoricalInactiveLifecycleResolutionShadowManifestV1
    source_observations: tuple[HistoricalInactiveLifecycleSourceObservationV1, ...]
    decisions: tuple[HistoricalInactiveLifecycleResolutionDecisionV1, ...]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class HistoricalInactiveLifecycleResolutionShadowWriteResult:
    partition_path: Path
    manifest: HistoricalInactiveLifecycleResolutionShadowManifestV1
    manifest_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class _CanonicalHistory:
    first_date: date
    last_date: date
    session_count: int
    record_count: int
    by_instrument: Mapping[str, tuple[date, date, frozenset[str]]]
    fingerprint: str


def build_historical_inactive_lifecycle_resolution_shadow(
    *,
    data_root: Path,
    source_package_path: Path,
    output_root: Path,
    anchor_date: date,
    materialized_at: datetime,
    source_custody_root: Path | None = None,
) -> HistoricalInactiveLifecycleResolutionShadowWriteResult:
    """Build one immutable owner-only shadow without network or canonical writes."""

    with _network_prohibited():
        return _build_shadow(
            data_root=data_root,
            source_package_path=source_package_path,
            output_root=output_root,
            anchor_date=anchor_date,
            materialized_at=materialized_at,
            source_custody_root=source_custody_root,
        )


def _build_shadow(
    *,
    data_root: Path,
    source_package_path: Path,
    output_root: Path,
    anchor_date: date,
    materialized_at: datetime,
    source_custody_root: Path | None,
) -> HistoricalInactiveLifecycleResolutionShadowWriteResult:
    canonical_root = _validated_canonical_root(data_root)
    candidate_root = _validated_tmp_root(output_root)
    materialized_at = normalize_utc_datetime(materialized_at)
    try:
        package = read_historical_inactive_lifecycle_source_payloads(
            package_path=source_package_path,
            expected_anchor_date=anchor_date,
            approved_custody_root=source_custody_root,
        )
    except HistoricalInactiveLifecycleSourceError as exc:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle source package failed formal reread"
        ) from exc
    canonical = _read_canonical_history(canonical_root, anchor_date)
    observations = _normalize_source(package.pages, anchor_date)
    if len(observations) != package.manifest.record_count:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "normalized source count differs from package"
        )
    decisions = _resolve_observations(
        observations=observations,
        source_package_fingerprint=package.manifest.logical_fingerprint,
        canonical=canonical,
        evaluated_at=materialized_at,
    )

    partition = _partition_path(candidate_root, anchor_date)
    existing = _read_if_present(candidate_root, anchor_date)
    if existing is not None:
        if (
            existing.manifest.source_package_manifest_sha256
            != package.manifest_sha256
            or existing.manifest.source_package_logical_fingerprint
            != package.manifest.logical_fingerprint
            or existing.manifest.canonical_instrument_history_fingerprint
            != canonical.fingerprint
            or existing.source_observations != observations
            or existing.decisions != decisions
        ):
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "existing shadow differs from current source or canonical history"
            )
        return HistoricalInactiveLifecycleResolutionShadowWriteResult(
            partition_path=partition,
            manifest=existing.manifest,
            manifest_sha256=existing.manifest_sha256,
            status="already_present",
        )

    _mkdirs_owner_only(partition.parent, candidate_root)
    staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow staging path already exists"
        )
    staging.mkdir(mode=0o700)
    try:
        source_artifact = _write_parquet(
            path=staging / SOURCE_FILE,
            rows=observations,
            schema=SOURCE_ARROW_SCHEMA,
            row_contract_version=SOURCE_ROW_CONTRACT_VERSION,
        )
        decision_artifact = _write_parquet(
            path=staging / DECISION_FILE,
            rows=decisions,
            schema=DECISION_ARROW_SCHEMA,
            row_contract_version=DECISION_ROW_CONTRACT_VERSION,
        )
        disposition_counts = _count_values(item.disposition.value for item in decisions)
        resolution_counts = _count_values(
            item.identity_resolution_status.value for item in decisions
        )
        reason_counts = _count_values(
            reason for item in decisions for reason in item.reason_codes
        )
        base = {
            "contract_version": MANIFEST_CONTRACT_VERSION,
            "completion_status": "completed",
            "dataset_name": "historical-inactive-lifecycle-resolution-shadow",
            "provider": MASSIVE_PROVIDER_ID,
            "anchor_date": anchor_date,
            "materialized_at": materialized_at,
            "source_package_manifest_sha256": package.manifest_sha256,
            "source_package_logical_fingerprint": package.manifest.logical_fingerprint,
            "source_package_record_count": package.manifest.record_count,
            "canonical_history_first_date": canonical.first_date,
            "canonical_history_last_date": canonical.last_date,
            "canonical_history_session_count": canonical.session_count,
            "canonical_history_record_count": canonical.record_count,
            "canonical_history_unique_instrument_count": len(canonical.by_instrument),
            "canonical_instrument_history_fingerprint": canonical.fingerprint,
            "source_artifact": source_artifact,
            "decision_artifact": decision_artifact,
            "disposition_counts": disposition_counts,
            "resolution_status_counts": resolution_counts,
            "reason_counts": reason_counts,
            "source_decision_one_to_one": True,
            "ticker_positive_resolution_count": 0,
            "cik_positive_resolution_count": 0,
            "external_request_count": 0,
            "canonical_data_write_count": 0,
            "analytics_execution_count": 0,
            "publication_count": 0,
            "deployment_count": 0,
            "scheduler_change_count": 0,
        }
        manifest = HistoricalInactiveLifecycleResolutionShadowManifestV1.model_validate(
            {
                **base,
                "logical_fingerprint": inactive_lifecycle_fingerprint(base),
            }
        )
        manifest_path = staging / MANIFEST_FILE
        manifest_path.write_bytes(_pretty_json(manifest.model_dump(mode="json")))
        manifest_path.chmod(0o400)
        _fsync_file(manifest_path)
        _fsync_directory(staging)
        staging.replace(partition)
        _fsync_directory(partition.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink() and staging.parent == partition.parent:
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise

    reread = read_historical_inactive_lifecycle_resolution_shadow(
        root=candidate_root,
        anchor_date=anchor_date,
    )
    if reread.source_observations != observations or reread.decisions != decisions:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow formal reread differs"
        )
    return HistoricalInactiveLifecycleResolutionShadowWriteResult(
        partition_path=partition,
        manifest=reread.manifest,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def read_historical_inactive_lifecycle_resolution_shadow(
    *,
    root: Path,
    anchor_date: date,
) -> HistoricalInactiveLifecycleResolutionShadowReadResult:
    """Formally reread a completed owner-only shadow and prove one-to-one lineage."""

    candidate_root = _validated_tmp_root(root)
    partition = _partition_path(candidate_root, anchor_date)
    _owner_only_directory_chain(partition, candidate_root)
    if partition.is_symlink() or not partition.is_dir():
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow partition is unavailable"
        )
    if stat.S_IMODE(partition.stat().st_mode) != 0o700:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow partition mode differs"
        )
    if {item.name for item in partition.iterdir()} != {
        SOURCE_FILE,
        DECISION_FILE,
        MANIFEST_FILE,
    }:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow file set differs"
        )
    for name in (SOURCE_FILE, DECISION_FILE, MANIFEST_FILE):
        _require_regular_file(partition / name, 0o400)
    manifest_path = partition / MANIFEST_FILE
    try:
        manifest = HistoricalInactiveLifecycleResolutionShadowManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow manifest is invalid"
        ) from exc
    if manifest.anchor_date != anchor_date:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow anchor differs"
        )
    observations = _read_rows(
        partition / SOURCE_FILE,
        SOURCE_ARROW_SCHEMA,
        HistoricalInactiveLifecycleSourceObservationV1,
    )
    decisions = _read_rows(
        partition / DECISION_FILE,
        DECISION_ARROW_SCHEMA,
        HistoricalInactiveLifecycleResolutionDecisionV1,
    )
    _validate_artifact(partition / SOURCE_FILE, observations, manifest.source_artifact)
    _validate_artifact(partition / DECISION_FILE, decisions, manifest.decision_artifact)
    source_keys = tuple(item.source_observation_fingerprint for item in observations)
    decision_keys = tuple(item.source_observation_fingerprint for item in decisions)
    if (
        len(set(source_keys)) != len(source_keys)
        or source_keys != decision_keys
        or any(
            source.source_payload_fingerprint != decision.source_payload_fingerprint
            or source.source_page_sequence != decision.source_page_sequence
            or source.source_row_sequence != decision.source_row_sequence
            for source, decision in zip(observations, decisions, strict=True)
        )
    ):
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow source-decision lineage differs"
        )
    if manifest.disposition_counts != _count_values(
        item.disposition.value for item in decisions
    ) or manifest.resolution_status_counts != _count_values(
        item.identity_resolution_status.value for item in decisions
    ) or manifest.reason_counts != _count_values(
        reason for item in decisions for reason in item.reason_codes
    ):
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow aggregate counts differ"
        )
    return HistoricalInactiveLifecycleResolutionShadowReadResult(
        partition_path=partition,
        manifest=manifest,
        source_observations=observations,
        decisions=decisions,
        manifest_sha256=_file_sha256(manifest_path),
    )


def _normalize_source(
    pages: tuple[object, ...], anchor_date: date
) -> tuple[HistoricalInactiveLifecycleSourceObservationV1, ...]:
    observations: list[HistoricalInactiveLifecycleSourceObservationV1] = []
    for page in pages:
        response = page.sanitized_response
        if set(response) - _SOURCE_WRAPPER_FIELDS:
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "inactive lifecycle source wrapper contains unreviewed fields"
            )
        results = response.get("results")
        if not isinstance(results, list):
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "inactive lifecycle source results are invalid"
            )
        for row_sequence, raw in enumerate(results, start=1):
            if not isinstance(raw, Mapping) or set(raw) - set(SOURCE_FIELD_NAMES):
                raise HistoricalInactiveLifecycleResolutionShadowError(
                    "inactive lifecycle source row contains unreviewed fields"
                )
            payload = {field: raw.get(field) for field in SOURCE_FIELD_NAMES}
            if payload["active"] is not False or any(
                value is not None and not isinstance(value, str)
                for field, value in payload.items()
                if field != "active"
            ):
                raise HistoricalInactiveLifecycleResolutionShadowError(
                    "inactive lifecycle source row types differ"
                )
            payload_fingerprint = inactive_lifecycle_fingerprint(payload)
            occurrence = {
                "anchor_date": anchor_date,
                "source_page_sequence": page.sequence,
                "source_row_sequence": row_sequence,
                "source_payload_fingerprint": payload_fingerprint,
            }
            observations.append(
                HistoricalInactiveLifecycleSourceObservationV1(
                    provider=MASSIVE_PROVIDER_ID,
                    anchor_date=anchor_date,
                    source_observed_at=page.source_observed_at,
                    source_page_sequence=page.sequence,
                    source_row_sequence=row_sequence,
                    **payload,
                    source_payload_fingerprint=payload_fingerprint,
                    source_observation_fingerprint=inactive_lifecycle_fingerprint(
                        occurrence
                    ),
                )
            )
    return tuple(observations)


def _resolve_observations(
    *,
    observations: tuple[HistoricalInactiveLifecycleSourceObservationV1, ...],
    source_package_fingerprint: str,
    canonical: _CanonicalHistory,
    evaluated_at: datetime,
) -> tuple[HistoricalInactiveLifecycleResolutionDecisionV1, ...]:
    selected = [_selected_identity(item) for item in observations]
    identity_counts = Counter(item for item in selected if item is not None)
    decisions: list[HistoricalInactiveLifecycleResolutionDecisionV1] = []
    for observation, identity in zip(observations, selected, strict=True):
        reasons: set[str] = set()
        effective_date, date_reason = _parse_delisted_date(observation.delisted_utc)
        if date_reason is not None:
            reasons.add(date_reason)
        elif effective_date is not None and effective_date > observation.anchor_date:
            reasons.add("delisted_date_after_anchor")

        identity_type = None
        identity_value = None
        status = ResolutionStatus.UNRESOLVED
        canonical_id = None
        first_date = None
        last_date = None
        ticker_seen = None
        if identity is None:
            reasons.add("missing_stable_security_identifier")
        else:
            identity_type = InactiveLifecycleIdentityType(identity[0])
            identity_value = identity[1]
            if identity_counts[identity] > 1:
                status = ResolutionStatus.AMBIGUOUS
                reasons.add("stable_identifier_collision")
            else:
                candidate = select_stable_identity(
                    share_class_figi=(identity_value if identity_type.value == "share_class_figi" else None),
                    composite_figi=(identity_value if identity_type.value == "composite_figi" else None),
                    provider_instrument_id=None,
                )
                if candidate is None:
                    raise HistoricalInactiveLifecycleResolutionShadowError(
                        "selected stable identity unexpectedly disappeared"
                    )
                candidate_id = str(canonical_instrument_id_for_identity(candidate))
                history = canonical.by_instrument.get(candidate_id)
                if history is None:
                    reasons.add("stable_identifier_absent_from_canonical_history")
                else:
                    status = ResolutionStatus.RESOLVED
                    canonical_id = candidate_id
                    first_date, last_date, tickers = history
                    normalized_ticker = _normalized_identifier(observation.ticker)
                    ticker_seen = normalized_ticker is not None and normalized_ticker in tickers
                    if not ticker_seen:
                        reasons.add("source_ticker_absent_from_canonical_history")
                    if effective_date is not None and last_date > effective_date:
                        reasons.add("canonical_instrument_seen_after_delisted_date")

        if not reasons and status is ResolutionStatus.RESOLVED:
            disposition = InactiveLifecycleDisposition.REVIEW_CANDIDATE
            reason_codes = REVIEW_LIMITATION_CODES
        else:
            disposition = InactiveLifecycleDisposition.QUARANTINED
            reason_codes = tuple(sorted(reasons))
        decisions.append(
            HistoricalInactiveLifecycleResolutionDecisionV1(
                provider=MASSIVE_PROVIDER_ID,
                anchor_date=observation.anchor_date,
                source_observation_fingerprint=observation.source_observation_fingerprint,
                source_payload_fingerprint=observation.source_payload_fingerprint,
                source_page_sequence=observation.source_page_sequence,
                source_row_sequence=observation.source_row_sequence,
                selected_identity_type=identity_type,
                selected_identity_value=identity_value,
                identity_resolution_status=status,
                canonical_instrument_id=canonical_id,
                canonical_first_observed_date=first_date,
                canonical_last_observed_date=last_date,
                effective_date_candidate=effective_date,
                ticker_seen_in_canonical_history=ticker_seen,
                disposition=disposition,
                reason_codes=reason_codes,
                source_package_logical_fingerprint=source_package_fingerprint,
                canonical_instrument_history_fingerprint=canonical.fingerprint,
                evaluated_at=evaluated_at,
            )
        )
    return tuple(decisions)


def _read_canonical_history(root: Path, anchor_date: date) -> _CanonicalHistory:
    snapshot_root = root / "market-data" / "snapshots" / "instrument-master"
    if snapshot_root.is_symlink() or not snapshot_root.is_dir():
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "canonical Instrument snapshot root is unavailable"
        )
    sessions: list[date] = []
    for item in snapshot_root.iterdir():
        if item.is_symlink() or not item.is_dir() or not item.name.startswith("as_of_date="):
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "canonical Instrument snapshot inventory contains an unsafe entry"
            )
        try:
            session = date.fromisoformat(item.name.removeprefix("as_of_date="))
        except ValueError as exc:
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "canonical Instrument snapshot date is malformed"
            ) from exc
        if session <= anchor_date:
            sessions.append(session)
    sessions.sort()
    if not sessions:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "canonical Instrument history is empty"
        )
    repository = ParquetInstrumentMasterSnapshotRepository(root=root)
    mutable: dict[str, list[object]] = {}
    inventory: list[dict[str, object]] = []
    record_count = 0
    for session in sessions:
        try:
            snapshot = repository.inspect_snapshot(session)
        except Exception as exc:
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "canonical Instrument snapshot failed formal reread"
            ) from exc
        parquet_path = snapshot.instrument_partition_path / "part-00000.parquet"
        _require_regular_file(parquet_path)
        table = pq.ParquetFile(parquet_path).read(
            columns=["instrument_id", "as_of_date", "ticker"]
        )
        if table.num_rows != snapshot.instrument_count:
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "canonical Instrument row count differs"
            )
        for raw in table.to_pylist():
            if raw["as_of_date"] != session:
                raise HistoricalInactiveLifecycleResolutionShadowError(
                    "canonical Instrument row date differs"
                )
            instrument_id = raw["instrument_id"]
            ticker = raw["ticker"]
            if not isinstance(instrument_id, str) or not isinstance(ticker, str):
                raise HistoricalInactiveLifecycleResolutionShadowError(
                    "canonical Instrument history types differ"
                )
            normalized_ticker = _normalized_identifier(ticker)
            if normalized_ticker is None:
                raise HistoricalInactiveLifecycleResolutionShadowError(
                    "canonical Instrument ticker is empty"
                )
            current = mutable.get(instrument_id)
            if current is None:
                mutable[instrument_id] = [session, session, {normalized_ticker}]
            else:
                current[1] = session
                current[2].add(normalized_ticker)
        record_count += table.num_rows
        inventory.append(
            {
                "as_of_date": session,
                "instrument_count": snapshot.instrument_count,
                "instrument_content_sha256": snapshot.instrument_content_sha256,
                "snapshot_content_sha256": snapshot.snapshot_content_sha256,
            }
        )
    by_instrument = {
        key: (value[0], value[1], frozenset(value[2]))
        for key, value in mutable.items()
    }
    return _CanonicalHistory(
        first_date=sessions[0],
        last_date=sessions[-1],
        session_count=len(sessions),
        record_count=record_count,
        by_instrument=by_instrument,
        fingerprint=inactive_lifecycle_fingerprint(inventory),
    )


def _selected_identity(
    observation: HistoricalInactiveLifecycleSourceObservationV1,
) -> tuple[str, str] | None:
    candidate = select_stable_identity(
        share_class_figi=observation.share_class_figi,
        composite_figi=observation.composite_figi,
        provider_instrument_id=None,
    )
    return None if candidate is None else (candidate.identity_type.value, candidate.identity_value)


def _parse_delisted_date(value: str | None) -> tuple[date | None, str | None]:
    if value is None or not value.strip():
        return None, "delisted_date_missing"
    normalized = value.strip()
    try:
        if len(normalized) == 10:
            return date.fromisoformat(normalized), None
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        return parsed.date(), None
    except ValueError:
        return None, "delisted_date_malformed"


def _normalized_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _write_parquet(
    *, path: Path, rows: tuple[object, ...], schema: pa.Schema, row_contract_version: str
) -> InactiveLifecycleShadowArtifactV1:
    dictionaries = [item.model_dump(mode="python") for item in rows]
    for row in dictionaries:
        if row.get("canonical_instrument_id") is not None:
            row["canonical_instrument_id"] = str(row["canonical_instrument_id"])
        for key, value in tuple(row.items()):
            if hasattr(value, "value"):
                row[key] = value.value
    table = pa.Table.from_pylist(dictionaries, schema=schema)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=6,
        use_dictionary=True,
        write_statistics=True,
    )
    path.chmod(0o400)
    _fsync_file(path)
    return InactiveLifecycleShadowArtifactV1(
        file_name=path.name,
        row_contract_version=row_contract_version,
        record_count=len(rows),
        byte_size=path.stat().st_size,
        content_fingerprint=inactive_lifecycle_rows_fingerprint(rows),
        physical_sha256=_file_sha256(path),
    )


def _read_rows(path: Path, schema: pa.Schema, model: type) -> tuple:
    try:
        table = pq.ParquetFile(path).read()
    except Exception as exc:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow Parquet is unreadable"
        ) from exc
    if table.schema != schema:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow Parquet schema differs"
        )
    try:
        return tuple(model.model_validate(item) for item in table.to_pylist())
    except Exception as exc:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow row validation failed"
        ) from exc


def _validate_artifact(path: Path, rows: tuple, artifact: InactiveLifecycleShadowArtifactV1) -> None:
    if (
        artifact.file_name != path.name
        or artifact.record_count != len(rows)
        or artifact.byte_size != path.stat().st_size
        or artifact.physical_sha256 != _file_sha256(path)
        or artifact.content_fingerprint != inactive_lifecycle_rows_fingerprint(rows)
    ):
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow artifact binding differs"
        )


def _partition_path(root: Path, anchor_date: date) -> Path:
    return (
        root
        / "market-data"
        / "historical-inactive-lifecycle-resolution-shadow"
        / f"schema_version={SCHEMA_PARTITION}"
        / f"provider={MASSIVE_PROVIDER_ID}"
        / f"anchor_date={anchor_date.isoformat()}"
    )


def _read_if_present(
    root: Path, anchor_date: date
) -> HistoricalInactiveLifecycleResolutionShadowReadResult | None:
    partition = _partition_path(root, anchor_date)
    if not partition.exists() and not partition.is_symlink():
        return None
    return read_historical_inactive_lifecycle_resolution_shadow(
        root=root, anchor_date=anchor_date
    )


def _validated_canonical_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT or resolved != path:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _validated_tmp_root(path: Path) -> Path:
    tmp = Path("/tmp").resolve(strict=True)
    if (
        not path.is_absolute()
        or tmp not in path.parents
        or not path.exists()
        or path.is_symlink()
    ):
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow root must be an existing /tmp directory"
        )
    _reject_symlink_chain(path, tmp)
    resolved = path.resolve(strict=True)
    if resolved != path or tmp not in resolved.parents or not resolved.is_dir():
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow root is unsafe"
        )
    if stat.S_IMODE(resolved.stat().st_mode) != 0o700:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow root must be owner-only"
        )
    return resolved


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    current = path.absolute()
    while current != stop:
        if current.is_symlink():
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "inactive lifecycle shadow path contains a symlink"
            )
        if stop not in current.parents:
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "inactive lifecycle shadow path escapes /tmp"
            )
        current = current.parent


def _owner_only_directory_chain(path: Path, root: Path) -> None:
    current = path
    while current != root:
        if current.is_symlink() or not current.is_dir():
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "inactive lifecycle shadow directory chain is unsafe"
            )
        if stat.S_IMODE(current.stat().st_mode) != 0o700:
            raise HistoricalInactiveLifecycleResolutionShadowError(
                "inactive lifecycle shadow directory chain is not owner-only"
            )
        current = current.parent


def _mkdirs_owner_only(path: Path, root: Path) -> None:
    missing: list[Path] = []
    current = path
    while current != root:
        if current.exists() or current.is_symlink():
            break
        missing.append(current)
        current = current.parent
    if current != root and root not in current.parents:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow directory escapes output root"
        )
    for item in reversed(missing):
        item.mkdir(mode=0o700)
    _owner_only_directory_chain(path, root)


def _require_regular_file(path: Path, mode: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow file is unsafe"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or (
        mode is not None and stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "inactive lifecycle shadow file mode differs"
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_values(values: Iterator[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalInactiveLifecycleResolutionShadowError(
            "network access is prohibited while building lifecycle shadow"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
