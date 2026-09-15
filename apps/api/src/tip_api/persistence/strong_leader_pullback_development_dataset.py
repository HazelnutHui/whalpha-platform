"""Immutable owner-only custody for reconstructed development observations and labels."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.analytics.v1 import StrongLeaderPullbackObservationV1
from tip_api.contracts.analytics.v1.strong_leader_pullback_development_dataset import (
    ReconstructedDevelopmentLabelState,
    StrongLeaderPullbackReconstructedDevelopmentLabelV1,
    StrongLeaderPullbackReconstructedDevelopmentManifestV1,
    StrongLeaderPullbackTerminalReferenceLedgerEntryV1,
    development_dataset_fingerprint,
)


MANIFEST_FILE = "manifest.json"
OBSERVATION_FILE = "observations.parquet"
LABEL_FILE = "labels.parquet"
OUTPUT_PREFIX = "dataset="
MAXIMUM_MANIFEST_BYTES = 1024 * 1024
MAXIMUM_PARQUET_BYTES = 1024 * 1024 * 1024
PARQUET_WRITE_BATCH_SIZE = 25_000


OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("as_of_session", pa.date32(), nullable=False),
        pa.field("universe_id", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("ticker", pa.string(), nullable=False),
        pa.field("membership_mode", pa.string(), nullable=False),
        pa.field("membership_session", pa.date32(), nullable=False),
        pa.field("membership_included", pa.bool_(), nullable=False),
        pa.field("relative_strength_20s_percentile", pa.string(), nullable=False),
        pa.field("trend_quality_score", pa.string(), nullable=False),
        pa.field("pullback_depth_atr", pa.string(), nullable=False),
        pa.field("close_above_prior_close", pa.bool_(), nullable=False),
        pa.field("close_above_prior_high", pa.bool_(), nullable=False),
        pa.field("pullback_volume_ratio", pa.string(), nullable=False),
        pa.field("market_regime", pa.string(), nullable=False),
        pa.field("source_max_session", pa.date32(), nullable=False),
        pa.field("source_fingerprint", pa.string(), nullable=False),
        pa.field("logical_fingerprint", pa.string(), nullable=False),
    ]
)


LABEL_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("experiment_fingerprint", pa.string(), nullable=False),
        pa.field("method_version", pa.string(), nullable=False),
        pa.field("method_fingerprint", pa.string(), nullable=False),
        pa.field("observation_fingerprint", pa.string(), nullable=False),
        pa.field("signal_session", pa.date32(), nullable=False),
        pa.field("evaluation_split", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("ticker_locator", pa.string(), nullable=False),
        pa.field("horizon_sessions", pa.int8(), nullable=False),
        pa.field("expected_entry_session", pa.date32(), nullable=False),
        pa.field("expected_exit_session", pa.date32(), nullable=False),
        pa.field("expected_path_sessions", pa.list_(pa.date32()), nullable=False),
        pa.field("split_basis_session", pa.date32(), nullable=False),
        pa.field("state", pa.string(), nullable=False),
        pa.field("entry_price_usd", pa.string()),
        pa.field("exit_price_lower_usd", pa.string()),
        pa.field("exit_price_upper_usd", pa.string()),
        pa.field("underlying_price_return_lower", pa.string()),
        pa.field("underlying_price_return_upper", pa.string()),
        pa.field("benchmark_price_return", pa.string()),
        pa.field("relative_to_benchmark_return_lower", pa.string()),
        pa.field("relative_to_benchmark_return_upper", pa.string()),
        pa.field("maximum_favorable_excursion", pa.string()),
        pa.field("maximum_adverse_excursion", pa.string()),
        pa.field("source_eod_fingerprint", pa.string(), nullable=False),
        pa.field("source_adjustment_fingerprint", pa.string(), nullable=False),
        pa.field("terminal_reference_fingerprint", pa.string()),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("reconstructed_latest_vintage", pa.bool_(), nullable=False),
        pa.field("as_operated", pa.bool_(), nullable=False),
        pa.field("underlying_stock_result_not_option_return", pa.bool_(), nullable=False),
        pa.field("transaction_costs_not_applied", pa.bool_(), nullable=False),
        pa.field("point_imputation_used", pa.bool_(), nullable=False),
        pa.field("logical_fingerprint", pa.string(), nullable=False),
    ]
)


class StrongLeaderPullbackDevelopmentDatasetPersistenceError(RuntimeError):
    """Raised when development-dataset custody cannot be proven."""


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackDevelopmentDatasetRead:
    root: Path
    manifest: StrongLeaderPullbackReconstructedDevelopmentManifestV1
    observations: tuple[StrongLeaderPullbackObservationV1, ...]
    labels: tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...]
    manifest_sha256: str
    status: str


def write_strong_leader_pullback_development_dataset(
    *,
    output_root: Path,
    output_custody_root: Path,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    labels: tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...],
    terminal_references: tuple[
        StrongLeaderPullbackTerminalReferenceLedgerEntryV1, ...
    ],
    manifest_values: Mapping[str, object],
) -> StrongLeaderPullbackDevelopmentDatasetRead:
    target, custody = _validated_target(output_root, output_custody_root)
    observations = _ordered_observations(observations)
    labels = _ordered_labels(labels)
    terminal_references = tuple(
        sorted(
            terminal_references,
            key=lambda item: (item.ticker_locator, str(item.instrument_id)),
        )
    )
    _validate_rows(observations, labels)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_development_dataset(
            output_root=target, output_custody_root=custody
        )
        if (
            existing.observations != observations
            or existing.labels != labels
            or existing.manifest.terminal_reference_entries != terminal_references
            or any(
                getattr(existing.manifest, key) != value
                for key, value in manifest_values.items()
            )
        ):
            raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
                "existing development dataset differs"
            )
        return existing

    staging = custody / f".{target.name}.staging.{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        observation_path = staging / OBSERVATION_FILE
        label_path = staging / LABEL_FILE
        _write_parquet(
            observation_path,
            OBSERVATION_SCHEMA,
            observations,
            _observation_row,
        )
        _write_parquet(
            label_path,
            LABEL_SCHEMA,
            labels,
            _label_row,
        )
        values = {
            **dict(manifest_values),
            "observation_count": len(observations),
            "label_count": len(labels),
            "label_state_counts": {
                state.value: sum(item.state is state for item in labels)
                for state in ReconstructedDevelopmentLabelState
            },
            "horizon_label_counts": {
                str(horizon): sum(item.horizon_sessions == horizon for item in labels)
                for horizon in (1, 3, 5)
            },
            "terminal_reference_ledger_fingerprint": development_dataset_fingerprint(
                {
                    "entries": [
                        item.model_dump(mode="json") for item in terminal_references
                    ]
                },
                exclude=set(),
            ),
            "terminal_reference_entries": terminal_references,
            "observation_logical_fingerprint": _rows_fingerprint(observations),
            "observation_parquet_sha256": _file_sha256(observation_path),
            "observation_parquet_bytes": observation_path.stat().st_size,
            "label_logical_fingerprint": _rows_fingerprint(labels),
            "label_parquet_sha256": _file_sha256(label_path),
            "label_parquet_bytes": label_path.stat().st_size,
        }
        provisional = StrongLeaderPullbackReconstructedDevelopmentManifestV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
        manifest = StrongLeaderPullbackReconstructedDevelopmentManifestV1.model_validate(
            {
                **values,
                "logical_fingerprint": development_dataset_fingerprint(provisional),
            }
        )
        _write_exclusive(staging / MANIFEST_FILE, _manifest_bytes(manifest))
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(custody)
    except Exception as exc:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(custody)
        if isinstance(exc, StrongLeaderPullbackDevelopmentDatasetPersistenceError):
            raise
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset write failed"
        ) from exc
    result = read_strong_leader_pullback_development_dataset(
        output_root=target, output_custody_root=custody
    )
    if result.observations != observations or result.labels != labels:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset reread differs"
        )
    return StrongLeaderPullbackDevelopmentDatasetRead(
        root=result.root,
        manifest=result.manifest,
        observations=result.observations,
        labels=result.labels,
        manifest_sha256=result.manifest_sha256,
        status="published",
    )


def read_strong_leader_pullback_development_dataset(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackDevelopmentDatasetRead:
    target, _ = _validated_target(output_root, output_custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.resolve(strict=True) != target
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or {item.name for item in target.iterdir()}
        != {MANIFEST_FILE, OBSERVATION_FILE, LABEL_FILE}
    ):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset directory differs"
        )
    manifest_path = target / MANIFEST_FILE
    observation_path = target / OBSERVATION_FILE
    label_path = target / LABEL_FILE
    manifest_raw = _read_regular(manifest_path, MAXIMUM_MANIFEST_BYTES)
    try:
        manifest = StrongLeaderPullbackReconstructedDevelopmentManifestV1.model_validate_json(
            manifest_raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset manifest is invalid"
        ) from exc
    if manifest_raw != _manifest_bytes(manifest):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset manifest bytes differ"
        )
    observations = tuple(
        StrongLeaderPullbackObservationV1.model_validate(item)
        for item in _read_parquet(observation_path, OBSERVATION_SCHEMA)
    )
    labels = tuple(
        StrongLeaderPullbackReconstructedDevelopmentLabelV1.model_validate(item)
        for item in _read_parquet(label_path, LABEL_SCHEMA)
    )
    observations = _ordered_observations(observations)
    labels = _ordered_labels(labels)
    _validate_rows(observations, labels)
    _validate_manifest_rows(manifest, observations, labels)
    if (
        len(observations) != manifest.observation_count
        or len(labels) != manifest.label_count
        or _rows_fingerprint(observations) != manifest.observation_logical_fingerprint
        or _rows_fingerprint(labels) != manifest.label_logical_fingerprint
        or observation_path.stat().st_size != manifest.observation_parquet_bytes
        or label_path.stat().st_size != manifest.label_parquet_bytes
        or _file_sha256(observation_path) != manifest.observation_parquet_sha256
        or _file_sha256(label_path) != manifest.label_parquet_sha256
    ):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset physical or logical binding differs"
        )
    return StrongLeaderPullbackDevelopmentDatasetRead(
        root=target,
        manifest=manifest,
        observations=observations,
        labels=labels,
        manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
        status="already_present",
    )


def _validate_rows(
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    labels: tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...],
) -> None:
    if not observations:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development observations are empty"
        )
    by_fingerprint = {item.logical_fingerprint: item for item in observations}
    if len(by_fingerprint) != len(observations) or len(labels) != len(observations) * 3:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development row counts differ"
        )
    grouped: dict[str, set[int]] = {key: set() for key in by_fingerprint}
    for label in labels:
        observation = by_fingerprint.get(label.observation_fingerprint)
        if (
            observation is None
            or label.signal_session != observation.as_of_session
            or label.instrument_id != observation.instrument_id
            or label.ticker_locator != observation.ticker
        ):
            raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
                "development label and observation differ"
            )
        grouped[label.observation_fingerprint].add(label.horizon_sessions)
    if any(values != {1, 3, 5} for values in grouped.values()):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development horizons do not cover every observation"
        )


def _validate_manifest_rows(
    manifest: StrongLeaderPullbackReconstructedDevelopmentManifestV1,
    observations: tuple[StrongLeaderPullbackObservationV1, ...],
    labels: tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...],
) -> None:
    sessions = tuple(sorted({item.as_of_session for item in observations}))
    state_counts = {
        state.value: sum(item.state is state for item in labels)
        for state in ReconstructedDevelopmentLabelState
    }
    horizon_counts = {
        str(horizon): sum(item.horizon_sessions == horizon for item in labels)
        for horizon in (1, 3, 5)
    }
    terminal_fingerprints = {
        item.logical_fingerprint for item in manifest.terminal_reference_entries
    }
    referenced_terminal_fingerprints = {
        item.terminal_reference_fingerprint
        for item in labels
        if item.terminal_reference_fingerprint is not None
    }
    if (
        sessions[0] != manifest.first_development_signal_session
        or sessions[-1] != manifest.last_development_signal_session
        or len(sessions) != manifest.development_signal_session_count
        or state_counts != manifest.label_state_counts
        or horizon_counts != manifest.horizon_label_counts
        or not referenced_terminal_fingerprints.issubset(terminal_fingerprints)
    ):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset manifest does not reconcile to rows"
        )


def _ordered_observations(
    values: tuple[StrongLeaderPullbackObservationV1, ...]
) -> tuple[StrongLeaderPullbackObservationV1, ...]:
    ordered = tuple(
        sorted(values, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    if tuple(values) != ordered:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development observations must be ordered"
        )
    return ordered


def _ordered_labels(
    values: tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...]
) -> tuple[StrongLeaderPullbackReconstructedDevelopmentLabelV1, ...]:
    ordered = tuple(
        sorted(
            values,
            key=lambda item: (
                item.signal_session,
                str(item.instrument_id),
                item.horizon_sessions,
            ),
        )
    )
    if tuple(values) != ordered:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development labels must be ordered"
        )
    return ordered


def _observation_row(item: StrongLeaderPullbackObservationV1) -> dict[str, object]:
    row = item.model_dump(mode="python")
    row["instrument_id"] = str(item.instrument_id)
    row["membership_mode"] = item.membership_mode.value
    return row


def _label_row(
    item: StrongLeaderPullbackReconstructedDevelopmentLabelV1,
) -> dict[str, object]:
    row = item.model_dump(mode="python")
    row["evaluation_split"] = item.evaluation_split.value
    row["instrument_id"] = str(item.instrument_id)
    row["state"] = item.state.value
    row["expected_path_sessions"] = list(item.expected_path_sessions)
    row["reason_codes"] = list(item.reason_codes)
    return row


def _read_parquet(path: Path, schema: pa.Schema) -> list[dict[str, object]]:
    _validate_regular(path, MAXIMUM_PARQUET_BYTES)
    try:
        table = pq.ParquetFile(path).read()
    except (pa.ArrowException, OSError) as exc:
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset Parquet is unreadable"
        ) from exc
    if not table.schema.equals(schema, check_metadata=False):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset Parquet schema differs"
        )
    return table.to_pylist()


def _write_parquet(path: Path, schema: pa.Schema, values, row_builder) -> None:
    with pq.ParquetWriter(
        path,
        schema,
        compression="zstd",
        use_dictionary=False,
    ) as writer:
        for start in range(0, len(values), PARQUET_WRITE_BATCH_SIZE):
            rows = [
                row_builder(item)
                for item in values[start : start + PARQUET_WRITE_BATCH_SIZE]
            ]
            writer.write_table(pa.Table.from_pylist(rows, schema=schema))
    path.chmod(0o400)
    _fsync_file(path)


def _validated_target(output_root: Path, output_custody_root: Path) -> tuple[Path, Path]:
    target = output_root.absolute()
    custody = output_custody_root.absolute()
    if (
        custody.is_symlink()
        or not custody.is_dir()
        or custody.resolve(strict=True) != custody
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or target.parent != custody
        or not target.name.startswith(OUTPUT_PREFIX)
        or target.name == OUTPUT_PREFIX
    ):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset custody differs"
        )
    return target, custody


def _read_regular(path: Path, maximum: int) -> bytes:
    _validate_regular(path, maximum)
    return path.read_bytes()


def _validate_regular(path: Path, maximum: int) -> None:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= maximum
    ):
        raise StrongLeaderPullbackDevelopmentDatasetPersistenceError(
            "development dataset file custody differs"
        )


def _manifest_bytes(
    manifest: StrongLeaderPullbackReconstructedDevelopmentManifestV1,
) -> bytes:
    return (
        json.dumps(
            manifest.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _rows_fingerprint(values: tuple[object, ...]) -> str:
    digest = hashlib.sha256()
    digest.update(b"[")
    for index, item in enumerate(values):
        if index:
            digest.update(b",")
        digest.update(
            json.dumps(
                item.model_dump(mode="json"),  # type: ignore[attr-defined]
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
        )
    digest.update(b"]")
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
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
