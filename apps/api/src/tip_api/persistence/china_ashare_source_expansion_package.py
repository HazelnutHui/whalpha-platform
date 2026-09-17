"""Persistent restartable Parquet custody for raw A-share source expansion."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, replace
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.source_expansion import (
    ChinaAshareRawAdjustmentSourceRowV1,
    ChinaAshareRawDailySourceRowV1,
    ChinaAshareSourceExpansionPartitionManifestV1,
    ChinaAshareSourceExpansionPartitionSpecV1,
    ChinaAshareSourceExpansionPlanV1,
    build_source_expansion_partition_manifest,
)
from tip_api.providers.china_ashare.baostock_source_expansion_adapter import (
    CapturedChinaAshareSourceExpansionPartitionV1,
)


PLAN_FILE = "source-expansion-plan.json"
PARTITION_MANIFEST_FILE = "partition-manifest.json"
DAILY_FILE = "raw-daily.parquet"
ADJUSTMENT_FILE = "raw-adjustments.parquet"
MAXIMUM_PLAN_BYTES = 16 * 1024 * 1024
MAXIMUM_PARTITION_FILE_BYTES = 512 * 1024 * 1024
_DAILY_SCHEMA = pa.schema(
    [
        ("source_security_id", pa.string()),
        ("session_date", pa.string()),
        ("open", pa.string()),
        ("high", pa.string()),
        ("low", pa.string()),
        ("close", pa.string()),
        ("pre_close", pa.string()),
        ("volume", pa.string()),
        ("amount", pa.string()),
        ("provider_trade_status", pa.string()),
        ("provider_risk_warning", pa.string()),
        ("ingested_at", pa.string()),
    ]
)
_ADJUSTMENT_SCHEMA = pa.schema(
    [
        ("source_security_id", pa.string()),
        ("session_date", pa.string()),
        ("provider_factor", pa.string()),
        ("fore_adjust_factor", pa.string()),
        ("back_adjust_factor", pa.string()),
        ("ingested_at", pa.string()),
    ]
)


class ChinaAshareSourceExpansionPackageError(RuntimeError):
    pass


class ChinaAshareSourceExpansionPackageConflictError(
    ChinaAshareSourceExpansionPackageError
):
    pass


class ChinaAshareSourceExpansionPackageCorruptionError(
    ChinaAshareSourceExpansionPackageError
):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareSourceExpansionPlanResultV1:
    plan: ChinaAshareSourceExpansionPlanV1
    plan_root: Path
    plan_path: Path
    plan_physical_sha256: str
    status: str


@dataclass(frozen=True, slots=True)
class ChinaAshareSourceExpansionPartitionResultV1:
    manifest: ChinaAshareSourceExpansionPartitionManifestV1
    partition: ChinaAshareSourceExpansionPartitionSpecV1
    captured: CapturedChinaAshareSourceExpansionPartitionV1
    partition_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_source_expansion_plan(
    *, custody_root: Path, plan: ChinaAshareSourceExpansionPlanV1
) -> ChinaAshareSourceExpansionPlanResultV1:
    custody = _custody_root(custody_root)
    plan_root = custody / f"plan={plan.logical_fingerprint}"
    if plan_root.exists():
        return replace(
            read_china_ashare_source_expansion_plan(plan_root=plan_root),
            status="already_present",
        )
    staging = custody / f".{plan_root.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion plan staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        _write(staging / PLAN_FILE, _canonical_json_bytes(plan.model_dump(mode="json")))
        (staging / "partitions").mkdir(mode=0o700)
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(plan_root)
        _fsync_directory(custody)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_source_expansion_plan(plan_root=plan_root),
        status="published",
    )


def read_china_ashare_source_expansion_plan(
    *, plan_root: Path
) -> ChinaAshareSourceExpansionPlanResultV1:
    root = plan_root.expanduser().resolve()
    if not root.is_dir() or root.is_symlink():
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion plan root is invalid"
        )
    payload = _read(root / PLAN_FILE, maximum_bytes=MAXIMUM_PLAN_BYTES)
    try:
        plan = ChinaAshareSourceExpansionPlanV1.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion plan is invalid"
        ) from exc
    if root.name != f"plan={plan.logical_fingerprint}":
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion plan path differs"
        )
    partition_root = root / "partitions"
    if not partition_root.is_dir() or partition_root.is_symlink():
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition root is invalid"
        )
    if (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion plan mode differs"
        )
    if (root / PLAN_FILE).stat().st_mode & 0o777 != 0o400:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion plan file mode differs"
        )
    return ChinaAshareSourceExpansionPlanResultV1(
        plan=plan,
        plan_root=root,
        plan_path=root / PLAN_FILE,
        plan_physical_sha256=_sha(payload),
        status="exact_reread_complete",
    )


def publish_china_ashare_source_expansion_partition(
    *,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    partition: ChinaAshareSourceExpansionPartitionSpecV1,
    captured: CapturedChinaAshareSourceExpansionPartitionV1,
    captured_at: datetime,
) -> ChinaAshareSourceExpansionPartitionResultV1:
    plan = plan_result.plan
    if partition.partition_index >= len(plan.partitions) or (
        plan.partitions[partition.partition_index] != partition
    ):
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion partition differs from plan"
        )
    _validate_captured(partition, captured, plan)
    daily_bytes = _parquet_bytes(captured.daily_rows, _DAILY_SCHEMA)
    adjustment_bytes = _parquet_bytes(captured.adjustment_rows, _ADJUSTMENT_SCHEMA)
    manifest = build_source_expansion_partition_manifest(
        plan_fingerprint=plan.logical_fingerprint,
        partition_fingerprint=partition.logical_fingerprint,
        partition_index=partition.partition_index,
        captured_at=captured_at,
        target_count=len(partition.targets),
        source_request_count=captured.source_request_count,
        daily_row_count=len(captured.daily_rows),
        adjustment_row_count=len(captured.adjustment_rows),
        daily_zero_row_ids=captured.daily_zero_row_ids,
        adjustment_zero_row_ids=captured.adjustment_zero_row_ids,
        daily_parquet_bytes=len(daily_bytes),
        daily_parquet_sha256=_sha(daily_bytes),
        adjustment_parquet_bytes=len(adjustment_bytes),
        adjustment_parquet_sha256=_sha(adjustment_bytes),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    target = plan_result.plan_root / "partitions" / f"{partition.partition_index:05d}"
    if target.exists():
        existing = read_china_ashare_source_expansion_partition(
            plan_result=plan_result, partition_index=partition.partition_index
        )
        return replace(existing, status="already_present")
    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion partition staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        _write(staging / DAILY_FILE, daily_bytes)
        _write(staging / ADJUSTMENT_FILE, adjustment_bytes)
        _write(staging / PARTITION_MANIFEST_FILE, manifest_bytes)
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(target.parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_source_expansion_partition(
            plan_result=plan_result, partition_index=partition.partition_index
        ),
        status="published",
    )


def read_china_ashare_source_expansion_partition(
    *, plan_result: ChinaAshareSourceExpansionPlanResultV1, partition_index: int
) -> ChinaAshareSourceExpansionPartitionResultV1:
    plan = plan_result.plan
    if partition_index < 0 or partition_index >= len(plan.partitions):
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition index is invalid"
        )
    partition = plan.partitions[partition_index]
    root = plan_result.plan_root / "partitions" / f"{partition_index:05d}"
    if not root.is_dir() or root.is_symlink():
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition path is invalid"
        )
    manifest_payload = _read(
        root / PARTITION_MANIFEST_FILE, maximum_bytes=MAXIMUM_PLAN_BYTES
    )
    daily_payload = _read(
        root / DAILY_FILE, maximum_bytes=MAXIMUM_PARTITION_FILE_BYTES
    )
    adjustment_payload = _read(
        root / ADJUSTMENT_FILE, maximum_bytes=MAXIMUM_PARTITION_FILE_BYTES
    )
    try:
        manifest = ChinaAshareSourceExpansionPartitionManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition manifest is invalid"
        ) from exc
    if (
        manifest.plan_fingerprint != plan.logical_fingerprint
        or manifest.partition_fingerprint != partition.logical_fingerprint
        or manifest.partition_index != partition_index
    ):
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition binding differs"
        )
    if (
        len(daily_payload) != manifest.daily_parquet_bytes
        or _sha(daily_payload) != manifest.daily_parquet_sha256
        or len(adjustment_payload) != manifest.adjustment_parquet_bytes
        or _sha(adjustment_payload) != manifest.adjustment_parquet_sha256
    ):
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion Parquet custody differs"
        )
    daily = tuple(
        ChinaAshareRawDailySourceRowV1.model_validate(item)
        for item in _parquet_rows(daily_payload, _DAILY_SCHEMA)
    )
    adjustments = tuple(
        ChinaAshareRawAdjustmentSourceRowV1.model_validate(item)
        for item in _parquet_rows(adjustment_payload, _ADJUSTMENT_SCHEMA)
    )
    captured = CapturedChinaAshareSourceExpansionPartitionV1(
        daily_rows=daily,
        adjustment_rows=adjustments,
        daily_zero_row_ids=manifest.daily_zero_row_ids,
        adjustment_zero_row_ids=manifest.adjustment_zero_row_ids,
        source_request_count=manifest.source_request_count,
    )
    _validate_captured(partition, captured, plan)
    if (
        len(daily) != manifest.daily_row_count
        or len(adjustments) != manifest.adjustment_row_count
    ):
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition row count differs"
        )
    expected_files = {DAILY_FILE, ADJUSTMENT_FILE, PARTITION_MANIFEST_FILE}
    actual_files = set()
    total_bytes = 0
    if (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition mode differs"
        )
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ChinaAshareSourceExpansionPackageCorruptionError(
                "source expansion partition contains a symlink"
            )
        if item.is_file():
            actual_files.add(item.relative_to(root).as_posix())
            total_bytes += item.stat().st_size
            if (item.stat().st_mode & 0o777) != 0o400:
                raise ChinaAshareSourceExpansionPackageCorruptionError(
                    "source expansion partition file mode differs"
                )
    if actual_files != expected_files:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion partition file set differs"
        )
    return ChinaAshareSourceExpansionPartitionResultV1(
        manifest=manifest,
        partition=partition,
        captured=captured,
        partition_path=root,
        manifest_path=root / PARTITION_MANIFEST_FILE,
        manifest_physical_sha256=_sha(manifest_payload),
        file_count=len(actual_files),
        total_bytes=total_bytes,
        status="exact_reread_complete",
    )


def completed_source_expansion_partition_indices(
    *, plan_result: ChinaAshareSourceExpansionPlanResultV1
) -> tuple[int, ...]:
    completed = []
    for partition in plan_result.plan.partitions:
        path = plan_result.plan_root / "partitions" / f"{partition.partition_index:05d}"
        if path.exists():
            read_china_ashare_source_expansion_partition(
                plan_result=plan_result,
                partition_index=partition.partition_index,
            )
            completed.append(partition.partition_index)
    return tuple(completed)


def _validate_captured(
    partition: ChinaAshareSourceExpansionPartitionSpecV1,
    captured: CapturedChinaAshareSourceExpansionPartitionV1,
    plan: ChinaAshareSourceExpansionPlanV1,
) -> None:
    target_ids = {item.source_security_id for item in partition.targets}
    if captured.source_request_count != len(target_ids) * 2:
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion request count differs"
        )
    daily_keys = tuple(
        (item.source_security_id, item.session_date) for item in captured.daily_rows
    )
    adjustment_keys = tuple(
        (item.source_security_id, item.session_date)
        for item in captured.adjustment_rows
    )
    if daily_keys != tuple(sorted(set(daily_keys))):
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion daily keys differ"
        )
    if adjustment_keys != tuple(sorted(set(adjustment_keys))):
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion adjustment keys differ"
        )
    daily_ids = {item.source_security_id for item in captured.daily_rows}
    adjustment_ids = {item.source_security_id for item in captured.adjustment_rows}
    daily_zero = set(captured.daily_zero_row_ids)
    adjustment_zero = set(captured.adjustment_zero_row_ids)
    if daily_ids & daily_zero or daily_ids | daily_zero != target_ids:
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion daily target coverage differs"
        )
    if adjustment_ids & adjustment_zero or adjustment_ids | adjustment_zero != target_ids:
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion adjustment target coverage differs"
        )
    if any(
        not plan.interval_start <= item.session_date <= plan.interval_end
        for item in captured.daily_rows
    ):
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion daily interval differs"
        )
    listing_dates = {
        item.source_security_id: item.listing_date for item in partition.targets
    }
    if any(
        not listing_dates[item.source_security_id]
        <= item.session_date
        <= plan.interval_end
        for item in captured.adjustment_rows
    ):
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion adjustment interval differs"
        )


def _parquet_bytes(rows: tuple[Any, ...], schema: pa.Schema) -> bytes:
    payload = [item.model_dump(mode="json") for item in rows]
    table = pa.Table.from_pylist(payload, schema=schema)
    stream = BytesIO()
    pq.write_table(
        table,
        stream,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
    )
    return stream.getvalue()


def _parquet_rows(payload: bytes, schema: pa.Schema) -> list[dict[str, Any]]:
    try:
        table = pq.read_table(pa.BufferReader(payload))
    except (pa.ArrowException, OSError) as exc:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion Parquet cannot be read"
        ) from exc
    if table.schema != schema:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion Parquet schema differs"
        )
    return table.to_pylist()


def _custody_root(value: Path) -> Path:
    root = value.expanduser().resolve()
    if root == Path("/"):
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise ChinaAshareSourceExpansionPackageConflictError(
            "source expansion custody root is invalid"
        )
    os.chmod(root, 0o700)
    return root


def _read(path: Path, *, maximum_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise ChinaAshareSourceExpansionPackageCorruptionError(
            "source expansion file size is invalid"
        )
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _owner_only(root: Path) -> None:
    for item in root.rglob("*"):
        os.chmod(item, 0o700 if item.is_dir() else 0o400)
    os.chmod(root, 0o700)


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_tree(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        _fsync_directory(Path(directory))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
