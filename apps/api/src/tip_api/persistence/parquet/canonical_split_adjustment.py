"""Deterministic custody for sparse canonical split-adjustment publications."""

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
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CanonicalSplitAdjustmentPublicationV1,
    build_canonical_split_adjustment_publication,
    canonical_split_adjustment_publication_bytes,
)
from tip_api.persistence.parquet.historical_research import (
    ADJUSTMENT_LEDGER_ARROW_SCHEMA,
)
from tip_api.persistence.parquet.manifest import decimal_to_string


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"
MAXIMUM_MANIFEST_BYTES = 16 * 1024 * 1024


class CanonicalSplitAdjustmentPersistenceError(RuntimeError):
    """Raised when sparse split-adjustment custody cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitAdjustmentPublicationRead:
    root: Path
    publication: CanonicalSplitAdjustmentPublicationV1
    records: tuple[AdjustmentLedgerEntryV1, ...]
    manifest_sha256: str


def write_canonical_split_adjustment_candidate(
    *,
    output_root: Path,
    records: tuple[AdjustmentLedgerEntryV1, ...],
    publication_values: Mapping[str, object],
) -> CanonicalSplitAdjustmentPublicationRead:
    """Atomically write one owner-only, publication-exact candidate."""

    target = output_root.absolute()
    if target.exists() or target.is_symlink():
        existing = read_canonical_split_adjustment_candidate(output_root=target)
        if existing.records != _ordered_records(records):
            raise CanonicalSplitAdjustmentPersistenceError(
                "existing split-adjustment candidate rows differ"
            )
        expected = build_canonical_split_adjustment_publication(
            **publication_values,
            adjustment_logical_fingerprint=(
                canonical_split_adjustment_rows_fingerprint(existing.records)
            ),
            adjustment_parquet_sha256=_file_sha256(target / PARQUET_FILE),
            adjustment_parquet_bytes=(target / PARQUET_FILE).stat().st_size,
        )
        if existing.publication != expected:
            raise CanonicalSplitAdjustmentPersistenceError(
                "existing split-adjustment candidate manifest differs"
            )
        return existing
    if (
        not target.parent.is_dir()
        or target.parent.is_symlink()
        or target.parent.resolve(strict=True) != target.parent
    ):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment candidate parent is unsafe"
        )
    ordered = _ordered_records(records)
    _validate_records(ordered)
    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment candidate staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        table = pa.Table.from_pylist(
            [_arrow_row(item) for item in ordered],
            schema=ADJUSTMENT_LEDGER_ARROW_SCHEMA,
        )
        parquet_path = staging / PARQUET_FILE
        pq.write_table(table, parquet_path, compression="zstd", use_dictionary=False)
        parquet_path.chmod(0o400)
        _fsync_file(parquet_path)
        publication = build_canonical_split_adjustment_publication(
            **publication_values,
            adjustment_logical_fingerprint=(
                canonical_split_adjustment_rows_fingerprint(ordered)
            ),
            adjustment_parquet_sha256=_file_sha256(parquet_path),
            adjustment_parquet_bytes=parquet_path.stat().st_size,
        )
        manifest_path = staging / MANIFEST_FILE
        manifest_path.write_bytes(
            canonical_split_adjustment_publication_bytes(publication)
        )
        manifest_path.chmod(0o400)
        _fsync_file(manifest_path)
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(target.parent)
    except Exception as exc:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
            _fsync_directory(staging.parent)
        if isinstance(exc, CanonicalSplitAdjustmentPersistenceError):
            raise
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment candidate write failed"
        ) from exc
    reread = read_canonical_split_adjustment_candidate(output_root=target)
    if reread.records != ordered or reread.publication != publication:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment candidate formal reread differs"
        )
    return reread


def read_canonical_split_adjustment_candidate(
    *, output_root: Path
) -> CanonicalSplitAdjustmentPublicationRead:
    return _read_publication(
        output_root.absolute(), directory_mode=0o700, file_mode=0o400
    )


def read_canonical_split_adjustment_publication(
    *, data_root: Path, publication_root: Path
) -> CanonicalSplitAdjustmentPublicationRead:
    root = _validated_data_root(data_root)
    target = publication_root if publication_root.is_absolute() else root / publication_root
    _reject_symlink_chain(root, target)
    result = _read_publication(target, directory_mode=0o755, file_mode=0o644)
    expected = (
        root
        / "market-data"
        / "adjustment-ledger"
        / "schema_version=1"
        / f"methodology_version={result.publication.methodology_version}"
        / f"basis_session={result.publication.basis_session.isoformat()}"
        / f"coverage_id={result.publication.logical_fingerprint}"
    )
    if result.root != expected:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment publication path differs"
        )
    return result


def canonical_split_adjustment_rows_fingerprint(
    records: tuple[AdjustmentLedgerEntryV1, ...],
) -> str:
    payload = json.dumps(
        [_canonical_value(item.model_dump(mode="python")) for item in _ordered_records(records)],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_publication(
    root: Path, *, directory_mode: int, file_mode: int
) -> CanonicalSplitAdjustmentPublicationRead:
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) != directory_mode
        or root.stat().st_uid != os.getuid()
        or {item.name for item in root.iterdir()} != {PARQUET_FILE, MANIFEST_FILE}
    ):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment publication directory differs"
        )
    manifest_path = root / MANIFEST_FILE
    parquet_path = root / PARQUET_FILE
    _regular_file(manifest_path, file_mode)
    _regular_file(parquet_path, file_mode)
    raw = manifest_path.read_bytes()
    if len(raw) < 1 or len(raw) > MAXIMUM_MANIFEST_BYTES:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment manifest size differs"
        )
    try:
        publication = CanonicalSplitAdjustmentPublicationV1.model_validate_json(raw)
    except Exception as exc:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment manifest is invalid"
        ) from exc
    if raw != canonical_split_adjustment_publication_bytes(publication):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment manifest bytes are not canonical"
        )
    if (
        parquet_path.stat().st_size != publication.adjustment_parquet_bytes
        or _file_sha256(parquet_path) != publication.adjustment_parquet_sha256
    ):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment Parquet binding differs"
        )
    try:
        table = pq.ParquetFile(parquet_path).read()
    except (pa.ArrowException, OSError) as exc:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment Parquet is unreadable"
        ) from exc
    if not table.schema.equals(ADJUSTMENT_LEDGER_ARROW_SCHEMA, check_metadata=False):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment schema differs"
        )
    try:
        records = tuple(
            AdjustmentLedgerEntryV1.model_validate(item)
            for item in table.to_pylist()
        )
    except Exception as exc:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment row is invalid"
        ) from exc
    _validate_records(records)
    clear_ids = {
        item.instrument_id
        for item in records
        if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
    }
    quarantine_ids = {
        item.instrument_id
        for item in records
        if item.split_adjustment_status
        is AdjustmentAvailabilityStatus.QUARANTINED
    }
    if (
        len(records) != publication.record_count
        or canonical_split_adjustment_rows_fingerprint(records)
        != publication.adjustment_logical_fingerprint
        or sum(
            item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
            for item in records
        )
        != publication.clear_record_count
        or sum(
            item.split_adjustment_status
            is AdjustmentAvailabilityStatus.QUARANTINED
            for item in records
        )
        != publication.quarantined_record_count
        or len(clear_ids) != publication.clear_instrument_count
        or len(quarantine_ids) != publication.quarantined_instrument_count
        or any(
            item.basis_session != publication.basis_session
            or item.calculation_methodology_version
            != publication.methodology_version
            or item.source_data_cutoff != publication.source_data_cutoff
            or item.calculated_at != publication.calculated_at
            or not publication.first_source_session
            <= item.source_session
            <= publication.last_source_session
            for item in records
        )
    ):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment counts or lineage differ"
        )
    return CanonicalSplitAdjustmentPublicationRead(
        root=root,
        publication=publication,
        records=records,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _validate_records(records: tuple[AdjustmentLedgerEntryV1, ...]) -> None:
    if not records or records != _ordered_records(records):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment rows are empty or unordered"
        )
    keys = tuple(
        (item.instrument_id, item.source_session, item.basis_session, item.revision)
        for item in records
    )
    if len(keys) != len(set(keys)):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment rows contain duplicate identity"
        )
    if any(
        item.total_return_adjustment_status
        is not AdjustmentAvailabilityStatus.UNAVAILABLE
        or item.total_return_multiplier_to_basis is not None
        or "total_return_adjustment_unavailable" not in item.quality_flags
        or "sparse_affected_path_only" not in item.quality_flags
        or "absent_row_neutrality_unauthorized" not in item.quality_flags
        or "outcome_reconciliation_only" not in item.quality_flags
        for item in records
    ):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment row boundary differs"
        )


def _ordered_records(
    records: tuple[AdjustmentLedgerEntryV1, ...],
) -> tuple[AdjustmentLedgerEntryV1, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                str(item.instrument_id),
                item.source_session,
                item.basis_session,
                item.calculation_methodology_version,
                item.revision,
            ),
        )
    )


def _arrow_row(item: AdjustmentLedgerEntryV1) -> dict[str, Any]:
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
        return decimal_to_string(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment data root is not approved"
        )
    return resolved


def _reject_symlink_chain(root: Path, target: Path) -> None:
    if target != root and root not in target.parents:
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment path escaped the data root"
        )
    current = target
    while True:
        if current.is_symlink():
            raise CanonicalSplitAdjustmentPersistenceError(
                "split-adjustment path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _regular_file(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment file is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_uid != os.getuid()
    ):
        raise CanonicalSplitAdjustmentPersistenceError(
            "split-adjustment file custody differs"
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
