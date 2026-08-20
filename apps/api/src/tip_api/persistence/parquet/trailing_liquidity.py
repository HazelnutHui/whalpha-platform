"""Atomic Parquet publication for trailing-liquidity shadow datasets."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import (
    TrailingLiquidityCandidateSummaryV1,
    TrailingLiquidityDatasetReferenceV1,
    TrailingLiquidityMetricV1,
    TrailingLiquidityShadowDecisionV1,
    TrailingLiquidityShadowManifestV1,
    TrailingLiquiditySourceSessionV1,
)
from tip_api.persistence.parquet.manifest import decimal_to_string
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.security_evidence import read_completed_security_evidence_snapshot
from tip_api.persistence.trailing_liquidity import (
    CompletedTrailingLiquidityPublication,
    TrailingLiquidityConflictError,
    TrailingLiquidityCorruptionError,
    TrailingLiquidityPersistenceError,
    TrailingLiquidityPublicationResult,
)

SCHEMA_VERSION = "1.0"
SCHEMA_PARTITION = "1"
PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"
METRIC_DATASET = "trailing-liquidity-metrics"
DECISION_DATASET = "trailing-liquidity-shadow-decisions"
METRIC_DIRECTORY = "market-data/derived/trailing-liquidity-metrics"
DECISION_DIRECTORY = "market-data/derived/trailing-liquidity-shadow-decisions"
LOGICAL_DIRECTORY = "market-data/snapshots/trailing-liquidity-shadow"
DECIMAL_PRECISION = 38
DECIMAL_SCALE = 10

METRIC_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("analysis_session", pa.date32(), nullable=False),
        pa.field("window_start", pa.date32(), nullable=False),
        pa.field("window_end", pa.date32(), nullable=False),
        pa.field("window_session_count", pa.int16(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("display_ticker", pa.string(), nullable=False),
        pa.field("provider_type_code", pa.string(), nullable=False),
        pa.field("observation_count", pa.int16(), nullable=False),
        pa.field("previous_session", pa.date32(), nullable=False),
        pa.field("previous_close", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("median_dollar_volume_proxy_20s", pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), nullable=True),
        pa.field("metric_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
        pa.field("source_window_fingerprint", pa.string(), nullable=False),
        pa.field("calculated_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)

DECISION_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("analysis_session", pa.date32(), nullable=False),
        pa.field("universe_id", pa.string(), nullable=False),
        pa.field("universe_version", pa.string(), nullable=False),
        pa.field("membership_evidence_as_of_date", pa.date32(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("provider_type_code", pa.string(), nullable=False),
        pa.field("metric_schema_version", pa.string(), nullable=False),
        pa.field("eligibility_status", pa.string(), nullable=False),
        pa.field("price_gate_passed", pa.bool_(), nullable=True),
        pa.field("liquidity_gate_passed", pa.bool_(), nullable=True),
        pa.field("included", pa.bool_(), nullable=False),
        pa.field("primary_reason", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
        pa.field("decision_reasons", pa.list_(pa.string()), nullable=False),
        pa.field("calculated_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)


@dataclass(frozen=True, slots=True)
class ParquetTrailingLiquidityRepository:
    root: Path

    def publish(
        self,
        *,
        analysis_session: date,
        metrics: tuple[TrailingLiquidityMetricV1, ...],
        decisions: tuple[TrailingLiquidityShadowDecisionV1, ...],
        calendar_name: str,
        calendar_version: str,
        window_sessions: tuple[date, ...],
        source_sessions: tuple[TrailingLiquiditySourceSessionV1, ...],
        source_descriptor_fingerprint: str,
        membership_evidence_path: str,
        membership_evidence_as_of_date: date,
        membership_evidence_fingerprint: str,
        candidates: tuple[TrailingLiquidityCandidateSummaryV1, ...],
        previous_close_threshold: Decimal,
        median_dollar_volume_threshold: Decimal,
        policy_version: str,
        created_at: datetime,
    ) -> TrailingLiquidityPublicationResult:
        root = _validated_root(self.root)
        _validate_records(metrics, decisions, analysis_session)
        metric_rows = [_metric_row(item) for item in sorted(metrics, key=lambda item: str(item.instrument_id))]
        decision_rows = [
            _decision_row(item)
            for item in sorted(decisions, key=lambda item: (item.universe_id, str(item.instrument_id)))
        ]
        metric_content = _rows_fingerprint(metric_rows)
        decision_content = _rows_fingerprint(decision_rows)
        metric_target, decision_target, logical_target = _targets(root, analysis_session)
        targets = (metric_target, decision_target, logical_target)
        for target in targets:
            _reject_symlink_chain(root, target)
        states = tuple(path.exists() or path.is_symlink() for path in targets)
        if any(states):
            if not all(states):
                raise TrailingLiquidityCorruptionError("partial trailing-liquidity publication exists")
            completed = read_completed_trailing_liquidity_publication(
                root, analysis_session=analysis_session, validate_sources=False
            )
            manifest = completed.manifest
            if (
                manifest.metric_dataset.content_fingerprint != metric_content
                or manifest.decision_dataset.content_fingerprint != decision_content
                or manifest.source_descriptor_fingerprint != source_descriptor_fingerprint
                or manifest.membership_evidence_fingerprint != membership_evidence_fingerprint
            ):
                raise TrailingLiquidityConflictError("existing trailing-liquidity publication conflicts")
            return TrailingLiquidityPublicationResult(
                metric_target,
                decision_target,
                logical_target / MANIFEST_FILE,
                manifest.metric_dataset.record_count,
                manifest.decision_dataset.record_count,
                manifest.metric_dataset.content_fingerprint,
                manifest.decision_dataset.content_fingerprint,
                manifest.metric_dataset.parquet_sha256,
                manifest.decision_dataset.parquet_sha256,
                manifest.logical_content_fingerprint,
                "already_present",
            )

        created_at = created_at.astimezone(UTC)
        metric_staging = _staging(metric_target)
        decision_staging = _staging(decision_target)
        logical_staging = _staging(logical_target)
        renamed: list[Path] = []
        try:
            metric_ref = _stage_partition(metric_staging, METRIC_DATASET, METRIC_SCHEMA, metric_rows, metric_content, created_at)
            decision_ref = _stage_partition(decision_staging, DECISION_DATASET, DECISION_SCHEMA, decision_rows, decision_content, created_at)
            metric_ref = metric_ref.model_copy(update={"dataset_path": metric_target.relative_to(root).as_posix()})
            decision_ref = decision_ref.model_copy(update={"dataset_path": decision_target.relative_to(root).as_posix()})
            logical_payload = {
                "analysis_session": analysis_session.isoformat(),
                "calendar_name": calendar_name,
                "calendar_version": calendar_version,
                "window_sessions": [item.isoformat() for item in window_sessions],
                "source_descriptor_fingerprint": source_descriptor_fingerprint,
                "source_sessions": [item.model_dump(mode="json") for item in source_sessions],
                "membership_evidence_path": membership_evidence_path,
                "membership_evidence_as_of_date": membership_evidence_as_of_date.isoformat(),
                "membership_evidence_fingerprint": membership_evidence_fingerprint,
                "metric_dataset": metric_ref.model_dump(mode="json"),
                "decision_dataset": decision_ref.model_dump(mode="json"),
                "candidates": [item.model_dump(mode="json") for item in candidates],
                "previous_close_threshold": decimal_to_string(previous_close_threshold),
                "median_dollar_volume_threshold": decimal_to_string(median_dollar_volume_threshold),
                "decimal_precision": DECIMAL_PRECISION,
                "decimal_scale": DECIMAL_SCALE,
                "methodology_mode": "current_as_of_constituent_liquidity",
                "policy_version": policy_version,
            }
            logical_fingerprint = _json_fingerprint(logical_payload)
            manifest = TrailingLiquidityShadowManifestV1(
                **logical_payload,
                created_at=created_at,
                logical_content_fingerprint=logical_fingerprint,
            )
            logical_staging.mkdir()
            _write_json(logical_staging / MANIFEST_FILE, manifest.model_dump(mode="json"))
            reread_manifest = TrailingLiquidityShadowManifestV1.model_validate_json(
                (logical_staging / MANIFEST_FILE).read_text(encoding="utf-8")
            )
            if reread_manifest != manifest:
                raise TrailingLiquidityCorruptionError("logical manifest staging reread mismatch")
            _fsync_directory(logical_staging)
            for staging, target in ((metric_staging, metric_target), (decision_staging, decision_target), (logical_staging, logical_target)):
                target.parent.mkdir(parents=True, exist_ok=True)
                if os.stat(root).st_dev != os.stat(target.parent).st_dev:
                    raise TrailingLiquidityPersistenceError("staging and target filesystem differ")
                staging.replace(target)
                renamed.append(target)
                _fsync_directory(target.parent)
            completed = read_completed_trailing_liquidity_publication(
                root, analysis_session=analysis_session, validate_sources=False
            )
            if completed.manifest.logical_content_fingerprint != logical_fingerprint:
                raise TrailingLiquidityCorruptionError("production reread logical fingerprint mismatch")
            return TrailingLiquidityPublicationResult(
                metric_target,
                decision_target,
                logical_target / MANIFEST_FILE,
                len(metrics),
                len(decisions),
                metric_content,
                decision_content,
                metric_ref.parquet_sha256,
                decision_ref.parquet_sha256,
                logical_fingerprint,
                "published",
            )
        except Exception:
            for path in reversed(renamed):
                if path.exists() and not path.is_symlink():
                    shutil.rmtree(path)
            for path in (metric_staging, decision_staging, logical_staging):
                if path.exists() and not path.is_symlink():
                    shutil.rmtree(path)
            raise


def read_completed_trailing_liquidity_publication(
    root: Path, *, analysis_session: date, validate_sources: bool = True
) -> CompletedTrailingLiquidityPublication:
    root = _validated_root(root)
    metric_target, decision_target, logical_target = _targets(root, analysis_session)
    for path in (metric_target, decision_target, logical_target):
        _reject_symlink_chain(root, path)
        if path.is_symlink() or not path.is_dir():
            raise TrailingLiquidityCorruptionError("completed trailing-liquidity target is unavailable")
    manifest_path = logical_target / MANIFEST_FILE
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise TrailingLiquidityCorruptionError("logical completion manifest is unavailable")
    manifest = TrailingLiquidityShadowManifestV1.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if manifest.analysis_session != analysis_session:
        raise TrailingLiquidityCorruptionError("logical manifest analysis session mismatch")
    logical_payload = manifest.model_dump(mode="json", exclude={"created_at", "logical_content_fingerprint", "manifest_version", "completion_status"})
    if _json_fingerprint(logical_payload) != manifest.logical_content_fingerprint:
        raise TrailingLiquidityCorruptionError("logical content fingerprint mismatch")
    metric_count = _read_partition(root, manifest.metric_dataset, METRIC_DATASET, METRIC_SCHEMA, TrailingLiquidityMetricV1)
    decision_count = _read_partition(root, manifest.decision_dataset, DECISION_DATASET, DECISION_SCHEMA, TrailingLiquidityShadowDecisionV1)
    if sum(item.requested_count for item in manifest.candidates) != decision_count:
        raise TrailingLiquidityCorruptionError("candidate counts do not reconcile with decisions")
    if validate_sources:
        _validate_source_references(root, manifest)
    return CompletedTrailingLiquidityPublication(manifest, metric_count, decision_count)


def _validate_source_references(root: Path, manifest: TrailingLiquidityShadowManifestV1) -> None:
    repository = CanonicalEodReadRepository(root)
    for reference in manifest.source_sessions:
        expected_path = (
            "market-data/eod-price-bars/schema_version=1/"
            f"session_date={reference.session_date.isoformat()}"
        )
        if reference.dataset_path != expected_path:
            raise TrailingLiquidityCorruptionError("EOD source path is inconsistent")
        actual = repository.inspect_session(reference.session_date)
        expected = (
            reference.record_count,
            reference.content_fingerprint,
            reference.parquet_sha256,
            reference.identity_snapshot_date,
            reference.identity_snapshot_fingerprint,
        )
        observed = (
            actual.record_count,
            actual.content_fingerprint,
            actual.parquet_sha256,
            actual.identity_snapshot_date,
            actual.identity_snapshot_fingerprint,
        )
        if observed != expected:
            raise TrailingLiquidityCorruptionError("EOD source reference mismatch")
    evidence = read_completed_security_evidence_snapshot(
        root, as_of_date=manifest.membership_evidence_as_of_date
    )
    if (
        evidence.manifest.evidence_path != manifest.membership_evidence_path
        or evidence.manifest.logical_content_sha256 != manifest.membership_evidence_fingerprint
    ):
        raise TrailingLiquidityCorruptionError("membership evidence reference mismatch")


def _stage_partition(
    staging: Path,
    dataset: str,
    schema: pa.Schema,
    rows: list[dict[str, Any]],
    content_fingerprint: str,
    created_at: datetime,
) -> TrailingLiquidityDatasetReferenceV1:
    staging.mkdir()
    parquet = staging / PARQUET_FILE
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, parquet)
    _fsync_file(parquet)
    parquet_hash = _file_sha256(parquet)
    reread = pq.ParquetFile(parquet).read()
    _validate_table(reread, schema, len(rows), content_fingerprint)
    manifest = {
        "manifest_version": "1.0",
        "dataset_name": dataset,
        "schema_version": SCHEMA_VERSION,
        "record_count": len(rows),
        "content_fingerprint": content_fingerprint,
        "parquet_sha256": parquet_hash,
        "parquet_file": PARQUET_FILE,
        "created_at": created_at.isoformat(),
        "completion_status": "completed",
    }
    _write_json(staging / MANIFEST_FILE, manifest)
    _fsync_directory(staging)
    return TrailingLiquidityDatasetReferenceV1(
        dataset_path="staging",
        record_count=len(rows),
        content_fingerprint=content_fingerprint,
        parquet_sha256=parquet_hash,
    )


def _read_partition(
    root: Path,
    reference: TrailingLiquidityDatasetReferenceV1,
    dataset: str,
    schema: pa.Schema,
    model: type[Any],
) -> int:
    partition = root / reference.dataset_path
    try:
        partition.relative_to(root)
    except ValueError as exc:
        raise TrailingLiquidityCorruptionError("dataset reference escapes root") from exc
    _reject_symlink_chain(root, partition)
    manifest_path, parquet_path = partition / MANIFEST_FILE, partition / PARQUET_FILE
    if any(item.is_symlink() for item in (partition, manifest_path, parquet_path)):
        raise TrailingLiquidityCorruptionError("dataset reference contains symlink")
    if not manifest_path.is_file() or not parquet_path.is_file():
        raise TrailingLiquidityCorruptionError("dataset reference is incomplete")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "dataset_name": dataset,
        "schema_version": SCHEMA_VERSION,
        "record_count": reference.record_count,
        "content_fingerprint": reference.content_fingerprint,
        "parquet_sha256": reference.parquet_sha256,
        "parquet_file": PARQUET_FILE,
        "completion_status": "completed",
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise TrailingLiquidityCorruptionError("dataset manifest reference mismatch")
    table = pq.ParquetFile(parquet_path).read()
    _validate_table(table, schema, reference.record_count, reference.content_fingerprint)
    if _file_sha256(parquet_path) != reference.parquet_sha256:
        raise TrailingLiquidityCorruptionError("dataset physical hash mismatch")
    for row in table.to_pylist():
        model.model_validate(row)
    return table.num_rows


def _metric_row(record: TrailingLiquidityMetricV1) -> dict[str, Any]:
    _validate_decimal(record.previous_close)
    _validate_decimal(record.median_dollar_volume_proxy_20s)
    row = record.model_dump(mode="python")
    row["instrument_id"] = str(record.instrument_id)
    row["metric_status"] = record.metric_status.value
    row["quality_flags"] = list(record.quality_flags)
    return row


def _decision_row(record: TrailingLiquidityShadowDecisionV1) -> dict[str, Any]:
    row = record.model_dump(mode="python")
    row["instrument_id"] = str(record.instrument_id)
    row["eligibility_status"] = record.eligibility_status.value
    row["quality_flags"] = list(record.quality_flags)
    row["decision_reasons"] = list(record.decision_reasons)
    return row


def _validate_records(
    metrics: tuple[TrailingLiquidityMetricV1, ...],
    decisions: tuple[TrailingLiquidityShadowDecisionV1, ...],
    analysis_session: date,
) -> None:
    if not metrics or not decisions:
        raise TrailingLiquidityPersistenceError("metric and decision records are required")
    if any(item.analysis_session != analysis_session for item in (*metrics, *decisions)):
        raise TrailingLiquidityPersistenceError("record analysis session mismatch")
    metric_ids = [item.instrument_id for item in metrics]
    decision_keys = [(item.universe_id, item.instrument_id) for item in decisions]
    if len(metric_ids) != len(set(metric_ids)) or len(decision_keys) != len(set(decision_keys)):
        raise TrailingLiquidityPersistenceError("duplicate publication business key")
    if any(item.instrument_id not in set(metric_ids) for item in decisions):
        raise TrailingLiquidityPersistenceError("decision contains an orphan metric reference")


def _validate_decimal(value: Decimal | None) -> None:
    if value is None:
        return
    quantum = Decimal(1).scaleb(-DECIMAL_SCALE)
    try:
        quantized = value.quantize(quantum)
    except InvalidOperation as exc:
        raise TrailingLiquidityPersistenceError("Decimal exceeds decimal128 precision") from exc
    if quantized != value:
        raise TrailingLiquidityPersistenceError("Decimal exceeds approved scale")
    digits = len(quantized.as_tuple().digits)
    if digits > DECIMAL_PRECISION:
        raise TrailingLiquidityPersistenceError("Decimal exceeds decimal128 precision")


def _normalized_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                normalized[key] = value.astimezone(UTC).isoformat()
            elif isinstance(value, date):
                normalized[key] = value.isoformat()
            elif isinstance(value, Decimal):
                normalized[key] = decimal_to_string(value)
            else:
                normalized[key] = value
        output.append(normalized)
    return sorted(output, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def _rows_fingerprint(rows: list[dict[str, Any]]) -> str:
    return _json_fingerprint(_normalized_rows(rows))


def _validate_table(table: pa.Table, schema: pa.Schema, count: int, fingerprint: str) -> None:
    if not table.schema.equals(schema, check_metadata=False):
        raise TrailingLiquidityCorruptionError("Parquet schema mismatch")
    if table.num_rows != count or _rows_fingerprint(table.to_pylist()) != fingerprint:
        raise TrailingLiquidityCorruptionError("Parquet count or fingerprint mismatch")


def _targets(root: Path, analysis_session: date) -> tuple[Path, Path, Path]:
    suffix = f"analysis_session={analysis_session.isoformat()}"
    return (
        root / METRIC_DIRECTORY / f"schema_version={SCHEMA_PARTITION}" / suffix,
        root / DECISION_DIRECTORY / f"schema_version={SCHEMA_PARTITION}" / suffix,
        root / LOGICAL_DIRECTORY / suffix,
    )


def _staging(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    path = target.parent / f".{target.name}.staging.{os.getpid()}"
    if path.exists() or path.is_symlink():
        raise TrailingLiquidityConflictError("publication staging path already exists")
    return path


def _validated_root(root: Path) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise TrailingLiquidityPersistenceError("data root is unavailable")
    resolved = root.resolve()
    _reject_symlink_chain(resolved, resolved)
    return resolved


def _reject_symlink_chain(root: Path, target: Path) -> None:
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise TrailingLiquidityPersistenceError("path escapes data root") from exc
    cursor = root
    if cursor.is_symlink():
        raise TrailingLiquidityPersistenceError("data root must not be a symlink")
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise TrailingLiquidityPersistenceError("publication path contains a symlink")


def _json_fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _fsync_file(temporary)
    temporary.replace(path)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
