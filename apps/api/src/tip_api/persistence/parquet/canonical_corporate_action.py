"""Deterministic Parquet custody for canonical split-action publications."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1 import (
    CanonicalSplitActionPublicationV1,
    CanonicalSplitActionV1,
    build_canonical_split_action_publication,
    canonical_split_action_publication_bytes,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
ACTIONS_FILE = "actions.parquet"
MANIFEST_FILE = "manifest.json"
MAXIMUM_MANIFEST_BYTES = 16 * 1024 * 1024
DECIMAL_PRECISION = 38
DECIMAL_SCALE = 18


CANONICAL_SPLIT_ACTION_ARROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("corporate_action_id", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("action_type", pa.string(), nullable=False),
        pa.field("effective_date", pa.date32(), nullable=False),
        pa.field(
            "split_ratio_from",
            pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE),
            nullable=False,
        ),
        pa.field(
            "split_ratio_to",
            pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE),
            nullable=False,
        ),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_action_id", pa.string(), nullable=False),
        pa.field("source_revision", pa.int32(), nullable=False),
        pa.field("canonical_revision", pa.int32(), nullable=False),
        pa.field("source_action_set_fingerprint", pa.string(), nullable=False),
        pa.field("source_publication_fingerprint", pa.string(), nullable=False),
        pa.field("event_group_size", pa.int32(), nullable=False),
        pa.field("record_status", pa.string(), nullable=False),
        pa.field("knowledge_time_status", pa.string(), nullable=False),
        pa.field("source_available_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("first_observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("point_in_time_eligibility", pa.string(), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)


class CanonicalSplitActionPersistenceError(RuntimeError):
    """Raised when split-action physical custody cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitActionPublicationRead:
    root: Path
    publication: CanonicalSplitActionPublicationV1
    actions: tuple[CanonicalSplitActionV1, ...]
    manifest_sha256: str


def write_canonical_split_action_publication_candidate(
    *,
    output_root: Path,
    actions: tuple[CanonicalSplitActionV1, ...],
    publication_values: Mapping[str, object],
) -> CanonicalSplitActionPublicationRead:
    """Atomically write one owner-only candidate below an already-safe parent."""

    target = output_root.absolute()
    if target.exists() or target.is_symlink():
        existing = read_canonical_split_action_publication_candidate(
            output_root=target
        )
        if existing.actions != _ordered_actions(actions):
            raise CanonicalSplitActionPersistenceError(
                "existing split-action candidate rows differ"
            )
        expected = build_canonical_split_action_publication(
            **publication_values,
            action_logical_fingerprint=canonical_split_action_rows_fingerprint(
                existing.actions
            ),
            action_parquet_sha256=_file_sha256(target / ACTIONS_FILE),
            action_parquet_bytes=(target / ACTIONS_FILE).stat().st_size,
        )
        if existing.publication != expected:
            raise CanonicalSplitActionPersistenceError(
                "existing split-action publication candidate differs"
            )
        return existing
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise CanonicalSplitActionPersistenceError(
            "split-action candidate parent is unavailable"
        )
    ordered = _ordered_actions(actions)
    _validate_action_rows(ordered)
    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise CanonicalSplitActionPersistenceError(
            "split-action candidate staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        table = pa.Table.from_pylist(
            [_arrow_row(item) for item in ordered],
            schema=CANONICAL_SPLIT_ACTION_ARROW_SCHEMA,
        )
        parquet_path = staging / ACTIONS_FILE
        pq.write_table(table, parquet_path, compression="zstd", use_dictionary=False)
        parquet_path.chmod(0o400)
        _fsync_file(parquet_path)
        publication = build_canonical_split_action_publication(
            **publication_values,
            action_logical_fingerprint=canonical_split_action_rows_fingerprint(
                ordered
            ),
            action_parquet_sha256=_file_sha256(parquet_path),
            action_parquet_bytes=parquet_path.stat().st_size,
        )
        manifest_path = staging / MANIFEST_FILE
        manifest_path.write_bytes(canonical_split_action_publication_bytes(publication))
        manifest_path.chmod(0o400)
        _fsync_file(manifest_path)
        _fsync_directory(staging)
        staging.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        raise
    result = read_canonical_split_action_publication_candidate(output_root=target)
    if result.actions != ordered or result.publication != publication:
        raise CanonicalSplitActionPersistenceError(
            "split-action publication candidate formal reread differs"
        )
    return result


def read_canonical_split_action_publication_candidate(
    *, output_root: Path
) -> CanonicalSplitActionPublicationRead:
    root = output_root.absolute()
    return _read_publication(root, directory_mode=0o700, file_mode=0o400)


def read_canonical_split_action_publication(
    *, data_root: Path, publication_root: Path
) -> CanonicalSplitActionPublicationRead:
    root = _validated_data_root(data_root)
    target = publication_root if publication_root.is_absolute() else root / publication_root
    result = _read_publication(target, directory_mode=0o755, file_mode=0o644)
    expected = (
        root
        / "market-data"
        / "canonical-corporate-actions"
        / "schema_version=1"
        / "action_scope=split"
        / f"coverage_id={result.publication.logical_fingerprint}"
    )
    if result.root != expected or root not in result.root.parents:
        raise CanonicalSplitActionPersistenceError(
            "canonical split-action publication path differs"
        )
    return result


def canonical_split_action_rows_fingerprint(
    actions: tuple[CanonicalSplitActionV1, ...],
) -> str:
    ordered = _ordered_actions(actions)
    payload = json.dumps(
        [_canonical_value(item.model_dump(mode="python")) for item in ordered],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_publication(
    root: Path,
    *,
    directory_mode: int,
    file_mode: int,
) -> CanonicalSplitActionPublicationRead:
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) != directory_mode
        or root.stat().st_uid != os.getuid()
        or {item.name for item in root.iterdir()} != {ACTIONS_FILE, MANIFEST_FILE}
    ):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication directory differs"
        )
    manifest_path = root / MANIFEST_FILE
    parquet_path = root / ACTIONS_FILE
    _regular_file(manifest_path, file_mode)
    _regular_file(parquet_path, file_mode)
    raw = manifest_path.read_bytes()
    if len(raw) < 1 or len(raw) > MAXIMUM_MANIFEST_BYTES:
        raise CanonicalSplitActionPersistenceError(
            "split-action publication manifest size differs"
        )
    try:
        publication = CanonicalSplitActionPublicationV1.model_validate_json(raw)
    except Exception as exc:
        raise CanonicalSplitActionPersistenceError(
            "split-action publication manifest is invalid"
        ) from exc
    if raw != canonical_split_action_publication_bytes(publication):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication manifest bytes are not canonical"
        )
    if (
        parquet_path.stat().st_size != publication.action_parquet_bytes
        or _file_sha256(parquet_path) != publication.action_parquet_sha256
    ):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication Parquet binding differs"
        )
    try:
        table = pq.ParquetFile(parquet_path).read()
    except (pa.ArrowException, OSError) as exc:
        raise CanonicalSplitActionPersistenceError(
            "split-action publication Parquet is unreadable"
        ) from exc
    if not table.schema.equals(CANONICAL_SPLIT_ACTION_ARROW_SCHEMA, check_metadata=False):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication schema differs"
        )
    try:
        actions = tuple(
            CanonicalSplitActionV1.model_validate(item) for item in table.to_pylist()
        )
    except Exception as exc:
        raise CanonicalSplitActionPersistenceError(
            "split-action publication row is invalid"
        ) from exc
    _validate_action_rows(actions)
    group_keys = {
        (item.instrument_id, item.effective_date) for item in actions
    }
    clear_groups = {
        (item.instrument_id, item.effective_date)
        for item in actions
        if item.event_group_size == 1
    }
    quarantined_groups = group_keys - clear_groups
    if (
        len(actions) != publication.action_record_count
        or canonical_split_action_rows_fingerprint(actions)
        != publication.action_logical_fingerprint
        or sum(item.record_status.value == "active" for item in actions)
        != publication.active_action_record_count
        or sum(item.record_status.value == "quarantined" for item in actions)
        != publication.quarantined_action_record_count
        or len(group_keys) != publication.event_group_count
        or len(clear_groups) != publication.clear_event_group_count
        or len(quarantined_groups)
        != publication.quarantined_event_group_count
        or any(
            item.source_publication_fingerprint
            != publication.source_publication_logical_fingerprint
            for item in actions
        )
        or any(
            not publication.start_date
            <= item.effective_date
            <= publication.end_date
            for item in actions
        )
    ):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication counts or logical identity differ"
        )
    return CanonicalSplitActionPublicationRead(
        root=root,
        publication=publication,
        actions=actions,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _ordered_actions(
    actions: tuple[CanonicalSplitActionV1, ...],
) -> tuple[CanonicalSplitActionV1, ...]:
    return tuple(
        sorted(
            actions,
            key=lambda item: (
                str(item.instrument_id),
                item.effective_date,
                item.source,
                item.source_action_id,
                item.source_revision,
                item.canonical_revision,
            ),
        )
    )


def _validate_action_rows(actions: tuple[CanonicalSplitActionV1, ...]) -> None:
    if not actions or actions != _ordered_actions(actions):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication rows are empty or unordered"
        )
    action_keys = tuple(
        (item.corporate_action_id, item.canonical_revision) for item in actions
    )
    source_keys = tuple(
        (item.source, item.source_action_id, item.source_revision) for item in actions
    )
    if len(action_keys) != len(set(action_keys)) or len(source_keys) != len(
        set(source_keys)
    ):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication has duplicate action identity"
        )
    event_fingerprints: dict[tuple[UUID, date], str] = {}
    group_sizes: dict[tuple[UUID, date, str], int] = {}
    for item in actions:
        event_key = (item.instrument_id, item.effective_date)
        previous = event_fingerprints.setdefault(
            event_key, item.source_action_set_fingerprint
        )
        if previous != item.source_action_set_fingerprint:
            raise CanonicalSplitActionPersistenceError(
                "split-action event has multiple group fingerprints"
            )
        key = (*event_key, item.source_action_set_fingerprint)
        group_sizes[key] = group_sizes.get(key, 0) + 1
    if any(
        item.event_group_size
        != group_sizes[
            (
                item.instrument_id,
                item.effective_date,
                item.source_action_set_fingerprint,
            )
        ]
        for item in actions
    ):
        raise CanonicalSplitActionPersistenceError(
            "split-action event-group size differs from rows"
        )


def _arrow_row(item: CanonicalSplitActionV1) -> dict[str, Any]:
    return {
        key: _arrow_value(value)
        for key, value in item.model_dump(mode="python").items()
    }


def _arrow_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, tuple):
        return [_arrow_value(item) for item in value]
    return value


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitActionPersistenceError(
            "canonical split-action data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitActionPersistenceError(
            "canonical split-action data root is not approved"
        )
    return resolved


def _regular_file(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise CanonicalSplitActionPersistenceError(
            "split-action publication file is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_uid != os.getuid()
    ):
        raise CanonicalSplitActionPersistenceError(
            "split-action publication file custody differs"
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
