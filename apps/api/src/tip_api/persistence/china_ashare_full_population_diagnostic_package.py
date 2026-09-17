"""Owner-only custody for bounded A-share diagnostic plans and aggregates."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    ChinaAshareFullPopulationDiagnosticPackageManifestV1,
    ChinaAshareFullPopulationDiagnosticPlanV1,
    ChinaAshareFullPopulationPartitionAggregateV1,
    ChinaAshareFullPopulationStreamingAggregateV1,
    build_full_population_diagnostic_package_manifest,
)


PLAN_FILE = "diagnostic-plan.json"
PARTITIONS_FILE = "partition-aggregates.json"
STREAMING_FILE = "streaming-aggregate.json"
MANIFEST_FILE = "diagnostic-package-manifest.json"
MAXIMUM_FILE_BYTES = 16 * 1024 * 1024


class ChinaAshareFullPopulationDiagnosticPackageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationDiagnosticPlanResultV1:
    plan: ChinaAshareFullPopulationDiagnosticPlanV1
    package_path: Path
    plan_path: Path
    plan_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationDiagnosticAggregateResultV1:
    manifest: ChinaAshareFullPopulationDiagnosticPackageManifestV1
    plan: ChinaAshareFullPopulationDiagnosticPlanV1
    partitions: tuple[ChinaAshareFullPopulationPartitionAggregateV1, ...]
    streaming: ChinaAshareFullPopulationStreamingAggregateV1
    package_path: Path
    manifest_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_full_population_diagnostic_plan(
    *, custody_root: Path, plan: ChinaAshareFullPopulationDiagnosticPlanV1
) -> ChinaAshareFullPopulationDiagnosticPlanResultV1:
    parent = _ensure_directory(_custody_root(custody_root) / "plans")
    target = parent / f"plan={plan.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_china_ashare_full_population_diagnostic_plan(
            package_path=target
        )
        if existing.plan != plan:
            raise ChinaAshareFullPopulationDiagnosticPackageError(
                "existing diagnostic plan differs"
            )
        return replace(existing, status="already_present")
    temporary = Path(tempfile.mkdtemp(prefix=".plan-", dir=parent))
    try:
        _write(temporary / PLAN_FILE, _canonical(plan.model_dump(mode="json")))
        _owner_only(temporary)
        _fsync_tree(temporary)
        temporary.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if temporary.exists() and not temporary.is_symlink():
            shutil.rmtree(temporary)
        raise
    return replace(
        read_china_ashare_full_population_diagnostic_plan(package_path=target),
        status="published",
    )


def read_china_ashare_full_population_diagnostic_plan(
    *, package_path: Path
) -> ChinaAshareFullPopulationDiagnosticPlanResultV1:
    root = _validate_package(package_path)
    payload = _read(root / PLAN_FILE)
    try:
        plan = ChinaAshareFullPopulationDiagnosticPlanV1.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic plan is invalid"
        ) from exc
    if (
        root.name != f"plan={plan.logical_fingerprint}"
        or root.parent.name != "plans"
        or payload != _canonical(plan.model_dump(mode="json"))
    ):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic plan identity differs"
        )
    _validate_inventory(root, {PLAN_FILE})
    return ChinaAshareFullPopulationDiagnosticPlanResultV1(
        plan=plan,
        package_path=root,
        plan_path=root / PLAN_FILE,
        plan_physical_sha256=_sha(payload),
        file_count=1,
        total_bytes=len(payload),
        status="exact_reread_complete",
    )


def publish_china_ashare_full_population_diagnostic_aggregate(
    *,
    custody_root: Path,
    plan_result: ChinaAshareFullPopulationDiagnosticPlanResultV1,
    partitions: tuple[ChinaAshareFullPopulationPartitionAggregateV1, ...],
    streaming: ChinaAshareFullPopulationStreamingAggregateV1,
) -> ChinaAshareFullPopulationDiagnosticAggregateResultV1:
    _validate_aggregate_inputs(
        plan=plan_result.plan,
        partitions=partitions,
        streaming=streaming,
    )
    partition_payload = _canonical(
        {
            "schema_version": "1.0",
            "rows": [item.model_dump(mode="json") for item in partitions],
        }
    )
    streaming_payload = _canonical(streaming.model_dump(mode="json"))
    manifest = build_full_population_diagnostic_package_manifest(
        plan_fingerprint=plan_result.plan.logical_fingerprint,
        created_at=plan_result.plan.registered_at,
        partition_count=len(partitions),
        partition_document_bytes=len(partition_payload),
        partition_document_sha256=_sha(partition_payload),
        streaming_aggregate_fingerprint=streaming.logical_fingerprint,
        streaming_document_bytes=len(streaming_payload),
        streaming_document_sha256=_sha(streaming_payload),
        full_universe_rows_materialized=False,
        future_return_read_count=0,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
    )
    root = _ensure_directory(_custody_root(custody_root) / "aggregates")
    plan_parent = _ensure_directory(
        root / f"plan={plan_result.plan.logical_fingerprint}"
    )
    target = plan_parent / f"aggregate={manifest.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=target,
        )
        if existing.manifest != manifest:
            raise ChinaAshareFullPopulationDiagnosticPackageError(
                "existing diagnostic aggregate differs"
            )
        return replace(existing, status="already_present")
    temporary = Path(tempfile.mkdtemp(prefix=".aggregate-", dir=plan_parent))
    try:
        _write(temporary / PARTITIONS_FILE, partition_payload)
        _write(temporary / STREAMING_FILE, streaming_payload)
        _write(
            temporary / MANIFEST_FILE,
            _canonical(manifest.model_dump(mode="json")),
        )
        _owner_only(temporary)
        _fsync_tree(temporary)
        temporary.rename(target)
        _fsync_directory(plan_parent)
    except BaseException:
        if temporary.exists() and not temporary.is_symlink():
            shutil.rmtree(temporary)
        raise
    return replace(
        read_china_ashare_full_population_diagnostic_aggregate(
            plan_result=plan_result,
            package_path=target,
        ),
        status="published",
    )


def read_china_ashare_full_population_diagnostic_aggregate(
    *,
    plan_result: ChinaAshareFullPopulationDiagnosticPlanResultV1,
    package_path: Path,
) -> ChinaAshareFullPopulationDiagnosticAggregateResultV1:
    root = _validate_package(package_path)
    manifest_payload = _read(root / MANIFEST_FILE)
    partition_payload = _read(root / PARTITIONS_FILE)
    streaming_payload = _read(root / STREAMING_FILE)
    try:
        manifest = (
            ChinaAshareFullPopulationDiagnosticPackageManifestV1.model_validate_json(
                manifest_payload
            )
        )
        document = json.loads(partition_payload)
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != "1.0"
            or not isinstance(document.get("rows"), list)
        ):
            raise ValueError("partition aggregate document shape differs")
        partitions = tuple(
            ChinaAshareFullPopulationPartitionAggregateV1.model_validate(item)
            for item in document["rows"]
        )
        streaming = ChinaAshareFullPopulationStreamingAggregateV1.model_validate_json(
            streaming_payload
        )
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic aggregate document is invalid"
        ) from exc
    if (
        root.name != f"aggregate={manifest.logical_fingerprint}"
        or root.parent.name != f"plan={plan_result.plan.logical_fingerprint}"
        or root.parent.parent.name != "aggregates"
        or manifest.plan_fingerprint != plan_result.plan.logical_fingerprint
        or manifest.partition_count != len(partitions)
        or manifest.partition_document_bytes != len(partition_payload)
        or manifest.partition_document_sha256 != _sha(partition_payload)
        or manifest.streaming_document_bytes != len(streaming_payload)
        or manifest.streaming_document_sha256 != _sha(streaming_payload)
        or manifest.streaming_aggregate_fingerprint != streaming.logical_fingerprint
    ):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic aggregate binding differs"
        )
    if (
        partition_payload
        != _canonical(
            {
                "schema_version": "1.0",
                "rows": [item.model_dump(mode="json") for item in partitions],
            }
        )
        or streaming_payload != _canonical(streaming.model_dump(mode="json"))
        or manifest_payload != _canonical(manifest.model_dump(mode="json"))
    ):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic aggregate canonical bytes differ"
        )
    _validate_aggregate_inputs(
        plan=plan_result.plan,
        partitions=partitions,
        streaming=streaming,
    )
    _validate_inventory(root, {PARTITIONS_FILE, STREAMING_FILE, MANIFEST_FILE})
    return ChinaAshareFullPopulationDiagnosticAggregateResultV1(
        manifest=manifest,
        plan=plan_result.plan,
        partitions=partitions,
        streaming=streaming,
        package_path=root,
        manifest_path=root / MANIFEST_FILE,
        manifest_physical_sha256=_sha(manifest_payload),
        file_count=3,
        total_bytes=(
            len(manifest_payload) + len(partition_payload) + len(streaming_payload)
        ),
        status="exact_reread_complete",
    )


def _validate_aggregate_inputs(
    *,
    plan: ChinaAshareFullPopulationDiagnosticPlanV1,
    partitions: tuple[ChinaAshareFullPopulationPartitionAggregateV1, ...],
    streaming: ChinaAshareFullPopulationStreamingAggregateV1,
) -> None:
    if streaming.plan_fingerprint != plan.logical_fingerprint:
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic aggregate plan differs"
        )
    if tuple(item.partition_index for item in partitions) != tuple(
        range(len(partitions))
    ):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic partition aggregates are not complete and ordered"
        )
    if tuple(item.logical_fingerprint for item in partitions) != (
        streaming.partition_aggregate_fingerprints
    ):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic partition aggregate set differs"
        )
    if len(partitions) != len(plan.normalized_partition_manifest_fingerprints):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic partition count differs from plan"
        )
    for index, item in enumerate(partitions):
        if (
            item.source_partition_manifest_fingerprint
            != plan.source_partition_manifest_fingerprints[index]
            or item.normalized_partition_manifest_fingerprint
            != plan.normalized_partition_manifest_fingerprints[index]
        ):
            raise ChinaAshareFullPopulationDiagnosticPackageError(
                "diagnostic partition input binding differs"
            )


def _ensure_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic custody directory is invalid"
        )
    path.chmod(0o700)
    return path


def _custody_root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic custody root cannot be a symlink"
        )
    return _ensure_directory(candidate.resolve())


def _validate_package(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic package path cannot be a symlink"
        )
    root = candidate.resolve()
    if (
        root.is_symlink()
        or not root.is_dir()
        or (root.stat().st_mode & 0o777) != 0o700
    ):
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic package path is invalid"
        )
    return root


def _validate_inventory(root: Path, expected: set[str]) -> None:
    actual = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
    }
    if actual != expected:
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic package file set differs"
        )
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ChinaAshareFullPopulationDiagnosticPackageError(
                "diagnostic package contains a symlink"
            )
        expected_mode = 0o400 if item.is_file() else 0o700
        if item.stat().st_mode & 0o777 != expected_mode:
            raise ChinaAshareFullPopulationDiagnosticPackageError(
                "diagnostic package permissions differ"
            )


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic package file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAshareFullPopulationDiagnosticPackageError(
            "diagnostic package file size is invalid"
        )
    return path.read_bytes()


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
        item.chmod(0o700 if item.is_dir() else 0o400)
    root.chmod(0o700)


def _fsync_tree(root: Path) -> None:
    for directory in sorted(
        (item for item in root.rglob("*") if item.is_dir()), reverse=True
    ):
        _fsync_directory(directory)
    _fsync_directory(root)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
