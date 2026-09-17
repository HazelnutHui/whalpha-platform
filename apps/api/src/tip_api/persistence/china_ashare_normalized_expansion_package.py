"""Immutable Parquet custody for normalized A-share expansion partitions."""

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

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.normalized_expansion import (
    ChinaAshareNormalizedExpansionPartitionManifestV1,
    build_normalized_expansion_partition_manifest,
    normalized_expansion_run_fingerprint,
)
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.persistence.china_ashare_population_package import (
    ChinaAsharePopulationPackageResultV1,
)
from tip_api.persistence.china_ashare_source_expansion_package import (
    ChinaAshareSourceExpansionPartitionResultV1,
    ChinaAshareSourceExpansionPlanResultV1,
)
from tip_api.services.china_ashare_source_expansion_normalization import (
    NormalizedChinaAshareSourceExpansionPartitionV1,
)


MANIFEST_FILE = "normalized-partition-manifest.json"
BAR_FILE = "normalized-bars.parquet"
STATE_FILE = "normalized-states.parquet"
ADJUSTMENT_FILE = "normalized-adjustments.parquet"
MAXIMUM_FILE_BYTES = 512 * 1024 * 1024
_BAR_SCHEMA = pa.schema(
    [
        ("schema_version", pa.string()),
        ("market_id", pa.string()),
        ("instrument_id", pa.string()),
        ("session_date", pa.string()),
        ("open", pa.string()),
        ("high", pa.string()),
        ("low", pa.string()),
        ("close", pa.string()),
        ("pre_close", pa.string()),
        ("volume_shares", pa.string()),
        ("turnover_amount_cny", pa.string()),
        ("adjustment_basis", pa.string()),
        ("source", pa.string()),
        ("source_record_id", pa.string()),
        ("source_available_at", pa.string()),
        ("ingested_at", pa.string()),
        ("revision", pa.int64()),
        ("quality_status", pa.string()),
        ("reason_codes", pa.list_(pa.string())),
    ]
)
_STATE_SCHEMA = pa.schema(
    [
        ("schema_version", pa.string()),
        ("market_id", pa.string()),
        ("instrument_id", pa.string()),
        ("session_date", pa.string()),
        ("exchange", pa.string()),
        ("board", pa.string()),
        ("trading_status", pa.string()),
        ("risk_warning_status", pa.string()),
        ("price_limit_regime", pa.string()),
        ("pre_close", pa.string()),
        ("up_limit", pa.string()),
        ("down_limit", pa.string()),
        ("exact_limit_prices_source_observed", pa.bool_()),
        ("source", pa.string()),
        ("source_available_at", pa.string()),
        ("ingested_at", pa.string()),
        ("quality_status", pa.string()),
        ("reason_codes", pa.list_(pa.string())),
    ]
)
_ADJUSTMENT_SCHEMA = pa.schema(
    [
        ("schema_version", pa.string()),
        ("market_id", pa.string()),
        ("instrument_id", pa.string()),
        ("session_date", pa.string()),
        ("provider_factor", pa.string()),
        ("fore_adjust_factor", pa.string()),
        ("back_adjust_factor", pa.string()),
        ("provider_semantics", pa.string()),
        ("source", pa.string()),
        ("source_available_at", pa.string()),
        ("ingested_at", pa.string()),
        ("normalized_return_authorized", pa.bool_()),
        ("quality_status", pa.string()),
        ("reason_codes", pa.list_(pa.string())),
    ]
)


class ChinaAshareNormalizedExpansionPackageError(RuntimeError):
    pass


class ChinaAshareNormalizedExpansionPackageConflictError(
    ChinaAshareNormalizedExpansionPackageError
):
    pass


class ChinaAshareNormalizedExpansionPackageCorruptionError(
    ChinaAshareNormalizedExpansionPackageError
):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareNormalizedExpansionPartitionResultV1:
    manifest: ChinaAshareNormalizedExpansionPartitionManifestV1
    normalized: NormalizedChinaAshareSourceExpansionPartitionV1
    run_root: Path
    partition_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_normalized_expansion_partition(
    *,
    custody_root: Path,
    population_package: ChinaAsharePopulationPackageResultV1,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    source_partition: ChinaAshareSourceExpansionPartitionResultV1,
    normalized: NormalizedChinaAshareSourceExpansionPartitionV1,
    normalized_at: datetime,
) -> ChinaAshareNormalizedExpansionPartitionResultV1:
    _validate_normalized(
        population_package=population_package,
        plan_result=plan_result,
        source_partition=source_partition,
        normalized=normalized,
    )
    bar_bytes = _parquet_bytes(normalized.bars, _BAR_SCHEMA)
    state_bytes = _parquet_bytes(normalized.states, _STATE_SCHEMA)
    adjustment_bytes = _parquet_bytes(normalized.adjustments, _ADJUSTMENT_SCHEMA)
    run_fingerprint = normalized_expansion_run_fingerprint(
        plan_fingerprint=plan_result.plan.logical_fingerprint,
        population_package_fingerprint=(
            population_package.manifest.logical_fingerprint
        ),
    )
    manifest = build_normalized_expansion_partition_manifest(
        run_fingerprint=run_fingerprint,
        plan_fingerprint=plan_result.plan.logical_fingerprint,
        population_package_fingerprint=(
            population_package.manifest.logical_fingerprint
        ),
        source_partition_manifest_fingerprint=(
            source_partition.manifest.logical_fingerprint
        ),
        partition_index=source_partition.partition.partition_index,
        normalized_at=normalized_at,
        target_count=len(source_partition.partition.targets),
        resolved_target_count=normalized.resolved_target_count,
        quarantined_target_count=len(normalized.quarantined_target_ids),
        source_daily_row_count=source_partition.manifest.daily_row_count,
        source_adjustment_row_count=(
            source_partition.manifest.adjustment_row_count
        ),
        normalized_bar_count=len(normalized.bars),
        normalized_state_count=len(normalized.states),
        normalized_adjustment_count=len(normalized.adjustments),
        suspended_state_count=sum(
            item.trading_status is ChinaAshareTradingStatus.SUSPENDED
            for item in normalized.states
        ),
        unknown_trading_state_count=sum(
            item.trading_status is ChinaAshareTradingStatus.UNKNOWN
            for item in normalized.states
        ),
        risk_warning_present_state_count=sum(
            item.risk_warning_status
            not in {
                ChinaAshareRiskWarningStatus.NONE,
                ChinaAshareRiskWarningStatus.UNKNOWN,
            }
            for item in normalized.states
        ),
        quarantined_daily_row_count=normalized.quarantined_daily_row_count,
        quarantined_adjustment_row_count=(
            normalized.quarantined_adjustment_row_count
        ),
        quarantined_target_ids=normalized.quarantined_target_ids,
        bar_parquet_bytes=len(bar_bytes),
        bar_parquet_sha256=_sha(bar_bytes),
        state_parquet_bytes=len(state_bytes),
        state_parquet_sha256=_sha(state_bytes),
        adjustment_parquet_bytes=len(adjustment_bytes),
        adjustment_parquet_sha256=_sha(adjustment_bytes),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    run_root = _ensure_run_root(custody_root, run_fingerprint)
    target = (
        run_root
        / "partitions"
        / f"{source_partition.partition.partition_index:05d}"
    )
    if target.exists():
        return replace(
            read_china_ashare_normalized_expansion_partition(
                custody_root=custody_root,
                population_package=population_package,
                plan_result=plan_result,
                source_partition=source_partition,
            ),
            status="already_present",
        )
    staging = target.parent / f".{target.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion staging path exists"
        )
    staging.mkdir(mode=0o700)
    try:
        _write(staging / BAR_FILE, bar_bytes)
        _write(staging / STATE_FILE, state_bytes)
        _write(staging / ADJUSTMENT_FILE, adjustment_bytes)
        _write(
            staging / MANIFEST_FILE,
            _canonical_json_bytes(manifest.model_dump(mode="json")),
        )
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(target.parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_normalized_expansion_partition(
            custody_root=custody_root,
            population_package=population_package,
            plan_result=plan_result,
            source_partition=source_partition,
        ),
        status="published",
    )


def read_china_ashare_normalized_expansion_partition(
    *,
    custody_root: Path,
    population_package: ChinaAsharePopulationPackageResultV1,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    source_partition: ChinaAshareSourceExpansionPartitionResultV1,
) -> ChinaAshareNormalizedExpansionPartitionResultV1:
    run_fingerprint = normalized_expansion_run_fingerprint(
        plan_fingerprint=plan_result.plan.logical_fingerprint,
        population_package_fingerprint=(
            population_package.manifest.logical_fingerprint
        ),
    )
    run_root = _existing_run_root(custody_root, run_fingerprint)
    root = (
        run_root
        / "partitions"
        / f"{source_partition.partition.partition_index:05d}"
    )
    if not root.is_dir() or root.is_symlink():
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion partition path is invalid"
        )
    manifest_payload = _read(root / MANIFEST_FILE, 16 * 1024 * 1024)
    bar_payload = _read(root / BAR_FILE, MAXIMUM_FILE_BYTES)
    state_payload = _read(root / STATE_FILE, MAXIMUM_FILE_BYTES)
    adjustment_payload = _read(root / ADJUSTMENT_FILE, MAXIMUM_FILE_BYTES)
    try:
        manifest = ChinaAshareNormalizedExpansionPartitionManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion manifest is invalid"
        ) from exc
    if (
        manifest.run_fingerprint != run_fingerprint
        or manifest.plan_fingerprint != plan_result.plan.logical_fingerprint
        or manifest.population_package_fingerprint
        != population_package.manifest.logical_fingerprint
        or manifest.source_partition_manifest_fingerprint
        != source_partition.manifest.logical_fingerprint
        or manifest.partition_index != source_partition.partition.partition_index
    ):
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion binding differs"
        )
    for payload, size, fingerprint, label in (
        (
            bar_payload,
            manifest.bar_parquet_bytes,
            manifest.bar_parquet_sha256,
            "bar",
        ),
        (
            state_payload,
            manifest.state_parquet_bytes,
            manifest.state_parquet_sha256,
            "state",
        ),
        (
            adjustment_payload,
            manifest.adjustment_parquet_bytes,
            manifest.adjustment_parquet_sha256,
            "adjustment",
        ),
    ):
        if len(payload) != size or _sha(payload) != fingerprint:
            raise ChinaAshareNormalizedExpansionPackageCorruptionError(
                f"normalized expansion {label} custody differs"
            )
    try:
        normalized = NormalizedChinaAshareSourceExpansionPartitionV1(
            bars=tuple(
                ChinaAshareDailyBarV1.model_validate(item)
                for item in _parquet_rows(bar_payload, _BAR_SCHEMA)
            ),
            states=tuple(
                ChinaAshareDailyTradingStateV1.model_validate(item)
                for item in _parquet_rows(state_payload, _STATE_SCHEMA)
            ),
            adjustments=tuple(
                ChinaAshareAdjustmentFactorObservationV1.model_validate(item)
                for item in _parquet_rows(
                    adjustment_payload, _ADJUSTMENT_SCHEMA
                )
            ),
            resolved_target_count=manifest.resolved_target_count,
            quarantined_target_ids=manifest.quarantined_target_ids,
            quarantined_daily_row_count=manifest.quarantined_daily_row_count,
            quarantined_adjustment_row_count=(
                manifest.quarantined_adjustment_row_count
            ),
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion rows are invalid"
        ) from exc
    _validate_normalized(
        population_package=population_package,
        plan_result=plan_result,
        source_partition=source_partition,
        normalized=normalized,
    )
    if (
        len(normalized.bars) != manifest.normalized_bar_count
        or len(normalized.states) != manifest.normalized_state_count
        or len(normalized.adjustments) != manifest.normalized_adjustment_count
    ):
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion row counts differ"
        )
    expected_files = {MANIFEST_FILE, BAR_FILE, STATE_FILE, ADJUSTMENT_FILE}
    actual_files = set()
    total_bytes = 0
    if (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion partition mode differs"
        )
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ChinaAshareNormalizedExpansionPackageCorruptionError(
                "normalized expansion partition contains a symlink"
            )
        if item.is_file():
            actual_files.add(item.relative_to(root).as_posix())
            total_bytes += item.stat().st_size
            if (item.stat().st_mode & 0o777) != 0o400:
                raise ChinaAshareNormalizedExpansionPackageCorruptionError(
                    "normalized expansion file mode differs"
                )
    if actual_files != expected_files:
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion file set differs"
        )
    return ChinaAshareNormalizedExpansionPartitionResultV1(
        manifest=manifest,
        normalized=normalized,
        run_root=run_root,
        partition_path=root,
        manifest_path=root / MANIFEST_FILE,
        manifest_physical_sha256=_sha(manifest_payload),
        file_count=len(actual_files),
        total_bytes=total_bytes,
        status="exact_reread_complete",
    )


def _validate_normalized(
    *,
    population_package: ChinaAsharePopulationPackageResultV1,
    plan_result: ChinaAshareSourceExpansionPlanResultV1,
    source_partition: ChinaAshareSourceExpansionPartitionResultV1,
    normalized: NormalizedChinaAshareSourceExpansionPartitionV1,
) -> None:
    if plan_result.plan.population_package_fingerprint != (
        population_package.manifest.logical_fingerprint
    ):
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion population differs"
        )
    targets = source_partition.partition.targets
    occurrences = {
        item.logical_fingerprint: item for item in population_package.occurrences
    }
    quarantined_ids = tuple(
        item.source_security_id
        for item in targets
        if item.disposition is ChinaAsharePopulationDisposition.QUARANTINED
    )
    resolved_instrument_ids = set()
    for target in targets:
        occurrence = occurrences.get(target.population_occurrence_fingerprint)
        if occurrence is None or occurrence.source_security_id != (
            target.source_security_id
        ):
            raise ChinaAshareNormalizedExpansionPackageConflictError(
                "normalized expansion population target differs"
            )
        if target.disposition is ChinaAsharePopulationDisposition.RESOLVED:
            if occurrence.instrument_id is None:
                raise ChinaAshareNormalizedExpansionPackageConflictError(
                    "normalized expansion resolved target lacks identity"
                )
            resolved_instrument_ids.add(str(occurrence.instrument_id))
    if normalized.quarantined_target_ids != quarantined_ids or (
        normalized.resolved_target_count + len(quarantined_ids) != len(targets)
    ):
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion target dispositions differ"
        )
    if len(normalized.states) + normalized.quarantined_daily_row_count != (
        source_partition.manifest.daily_row_count
    ):
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion daily rows differ"
        )
    if (
        len(normalized.adjustments)
        + normalized.quarantined_adjustment_row_count
        != source_partition.manifest.adjustment_row_count
    ):
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion adjustment rows differ"
        )
    for rows, label in (
        (normalized.bars, "bar"),
        (normalized.states, "state"),
        (normalized.adjustments, "adjustment"),
    ):
        keys = tuple((str(item.instrument_id), item.session_date) for item in rows)
        if keys != tuple(sorted(set(keys))):
            raise ChinaAshareNormalizedExpansionPackageConflictError(
                f"normalized expansion {label} keys differ"
            )
        if any(
            str(item.instrument_id) not in resolved_instrument_ids for item in rows
        ):
            raise ChinaAshareNormalizedExpansionPackageConflictError(
                f"normalized expansion {label} identity differs"
            )
    bar_keys = {
        (str(item.instrument_id), item.session_date) for item in normalized.bars
    }
    state_keys = {
        (str(item.instrument_id), item.session_date) for item in normalized.states
    }
    if not bar_keys <= state_keys:
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion bar lacks daily state"
        )
    forbidden_bar_keys = {
        (str(item.instrument_id), item.session_date)
        for item in normalized.states
        if item.trading_status
        in {ChinaAshareTradingStatus.SUSPENDED, ChinaAshareTradingStatus.NOT_LISTED}
    }
    required_bar_keys = {
        (str(item.instrument_id), item.session_date)
        for item in normalized.states
        if item.trading_status
        in {ChinaAshareTradingStatus.TRADING, ChinaAshareTradingStatus.RESUMED}
    }
    if bar_keys & forbidden_bar_keys or not required_bar_keys <= bar_keys:
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion bar and trading state differ"
        )


def _ensure_run_root(custody_root: Path, run_fingerprint: str) -> Path:
    candidate = custody_root.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion custody root is unsafe"
        )
    root = candidate.resolve()
    if root == Path("/"):
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.is_dir() or (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion custody root is invalid"
        )
    run_root = root / f"run={run_fingerprint}"
    run_root.mkdir(mode=0o700, exist_ok=True)
    partitions = run_root / "partitions"
    partitions.mkdir(mode=0o700, exist_ok=True)
    if (
        run_root.is_symlink()
        or partitions.is_symlink()
        or (run_root.stat().st_mode & 0o777) != 0o700
        or (partitions.stat().st_mode & 0o777) != 0o700
    ):
        raise ChinaAshareNormalizedExpansionPackageConflictError(
            "normalized expansion run path is unsafe"
        )
    return run_root


def _existing_run_root(custody_root: Path, run_fingerprint: str) -> Path:
    candidate = custody_root.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion custody root is unsafe"
        )
    root = candidate.resolve()
    run_root = root / f"run={run_fingerprint}"
    partitions = run_root / "partitions"
    if (
        root == Path("/")
        or not root.is_dir()
        or not run_root.is_dir()
        or not partitions.is_dir()
        or root.is_symlink()
        or run_root.is_symlink()
        or partitions.is_symlink()
        or (root.stat().st_mode & 0o777) != 0o700
        or (run_root.stat().st_mode & 0o777) != 0o700
        or (partitions.stat().st_mode & 0o777) != 0o700
    ):
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion run path is invalid"
        )
    return run_root


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
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion Parquet cannot be read"
        ) from exc
    if table.schema != schema:
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion Parquet schema differs"
        )
    return table.to_pylist()


def _read(path: Path, maximum_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise ChinaAshareNormalizedExpansionPackageCorruptionError(
            "normalized expansion file size is invalid"
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


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
