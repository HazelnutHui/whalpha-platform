"""Atomic owner-only custody for partitioned conservative A-share candidates."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareConservativePartitionCensusV1,
    ChinaAshareConservativeReconstructionCensusV1,
    ChinaAshareConservativeReconstructionPlanV1,
    ChinaAsharePriceLimitSmokeV1,
)
from tip_api.contracts.china_ashare.v1.conservative_reconstructed_universe import (
    ChinaAshareConservativeUniverseArtifactV1,
    ChinaAshareConservativeUniverseDisposition,
    ChinaAshareConservativeUniversePackageManifestV1,
    ChinaAshareConservativeUniversePartitionManifestV1,
    ChinaAshareConservativeUniverseRowV1,
    build_universe_package_manifest,
    build_universe_partition_manifest,
    universe_row_set_fingerprint,
)


PLAN_FILE = "reconstruction-plan.json"
CENSUS_FILE = "global-census.json"
SMOKE_FILE = "price-limit-smoke.json"
PACKAGE_MANIFEST_FILE = "package-manifest.json"
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
MAXIMUM_PARQUET_BYTES = 256 * 1024 * 1024

ROW_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("market_id", pa.string(), nullable=False),
        pa.field("partition_index", pa.int16(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("source_security_id", pa.string(), nullable=False),
        pa.field("session_date", pa.date32(), nullable=False),
        pa.field("knowledge_session_date", pa.date32(), nullable=True),
        pa.field("exchange", pa.string(), nullable=False),
        pa.field("board", pa.string(), nullable=False),
        pa.field("trading_status", pa.string(), nullable=False),
        pa.field("risk_warning_status", pa.string(), nullable=False),
        pa.field("disposition", pa.string(), nullable=False),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("input_partition_manifest_fingerprint", pa.string(), nullable=False),
        pa.field("as_operated", pa.bool_(), nullable=False),
        pa.field("research_authorized", pa.bool_(), nullable=False),
        pa.field("return_construction_authorized", pa.bool_(), nullable=False),
        pa.field("research_backtest_authorized", pa.bool_(), nullable=False),
    ]
)


class ChinaAshareConservativeReconstructionPackageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareConservativeReconstructionPackageResultV1:
    manifest: ChinaAshareConservativeUniversePackageManifestV1
    plan: ChinaAshareConservativeReconstructionPlanV1
    census: ChinaAshareConservativeReconstructionCensusV1
    smoke: ChinaAsharePriceLimitSmokeV1
    partition_censuses: tuple[ChinaAshareConservativePartitionCensusV1, ...]
    partition_manifests: tuple[ChinaAshareConservativeUniversePartitionManifestV1, ...]
    package_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_conservative_reconstruction_package(
    *, custody_root: Path, plan, census, smoke,
    partition_payloads: Iterable[tuple[ChinaAshareConservativePartitionCensusV1, tuple[ChinaAshareConservativeUniverseRowV1, ...]]],
) -> ChinaAshareConservativeReconstructionPackageResultV1:
    if census.plan_fingerprint != plan.logical_fingerprint:
        raise ChinaAshareConservativeReconstructionPackageError("global census plan differs")
    root = _root(custody_root)
    staging = Path(tempfile.mkdtemp(prefix=".conservative-reconstruction-", dir=root))
    try:
        artifacts = []
        for relative, value in (
            (PLAN_FILE, plan),
            (CENSUS_FILE, census),
            (SMOKE_FILE, smoke),
        ):
            payload = _canonical(value.model_dump(mode="json"))
            _write(staging / relative, payload)
            artifacts.append(_artifact(relative, payload))
        partition_manifests = []
        for expected_index, (partition_census, rows) in enumerate(partition_payloads):
            if (
                expected_index > 108
                or partition_census.partition_index != expected_index
                or census.partition_census_fingerprints[expected_index]
                != partition_census.logical_fingerprint
            ):
                raise ChinaAshareConservativeReconstructionPackageError(
                    "partition payload order differs"
                )
            prefix = f"partitions/partition-{expected_index:03d}"
            census_path = f"{prefix}/partition-census.json"
            parquet_path = f"{prefix}/daily-universe.parquet"
            manifest_path = f"{prefix}/partition-manifest.json"
            census_payload = _canonical(partition_census.model_dump(mode="json"))
            parquet_payload = _parquet_bytes(rows)
            counts = Counter(item.disposition for item in rows)
            partition_manifest = build_universe_partition_manifest(
                plan_fingerprint=plan.logical_fingerprint,
                global_census_fingerprint=census.logical_fingerprint,
                partition_census_fingerprint=partition_census.logical_fingerprint,
                normalized_partition_manifest_fingerprint=(
                    partition_census.normalized_partition_manifest_fingerprint
                ),
                partition_index=expected_index,
                row_count=len(rows),
                provisional_include_count=counts[
                    ChinaAshareConservativeUniverseDisposition.PROVISIONAL_INCLUDE
                ],
                warning_exclude_count=counts[
                    ChinaAshareConservativeUniverseDisposition.WARNING_EXCLUDE
                ],
                quarantine_count=counts[
                    ChinaAshareConservativeUniverseDisposition.QUARANTINE
                ],
                parquet_bytes=len(parquet_payload),
                parquet_physical_sha256=_sha(parquet_payload),
                logical_row_set_fingerprint=universe_row_set_fingerprint(rows),
                as_operated=False,
                source_available_at_observed=False,
                research_authorized=False,
                return_construction_authorized=False,
                research_backtest_authorized=False,
            )
            manifest_payload = _canonical(partition_manifest.model_dump(mode="json"))
            for relative, payload in (
                (census_path, census_payload),
                (parquet_path, parquet_payload),
                (manifest_path, manifest_payload),
            ):
                path = staging / relative
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                _write(path, payload)
                artifacts.append(_artifact(relative, payload))
            partition_manifests.append(partition_manifest)
        if len(partition_manifests) != 109:
            raise ChinaAshareConservativeReconstructionPackageError(
                "partition payload set differs"
            )
        manifest = build_universe_package_manifest(
            plan_fingerprint=plan.logical_fingerprint,
            global_census_fingerprint=census.logical_fingerprint,
            candidate_set_fingerprint=census.candidate_set_fingerprint,
            price_limit_smoke_fingerprint=smoke.logical_fingerprint,
            partition_manifest_fingerprints=tuple(
                item.logical_fingerprint for item in partition_manifests
            ),
            partition_count=109,
            row_count=census.state_count,
            provisional_include_count=census.provisional_candidate_included_state_count,
            warning_exclude_count=census.provisional_candidate_excluded_state_count,
            quarantine_count=census.provisional_quarantined_state_count,
            artifacts=tuple(sorted(artifacts, key=lambda item: item.relative_path)),
            as_operated=False,
            research_authorized=False,
            return_construction_authorized=False,
            historical_coverage_authorized=False,
            research_backtest_authorized=False,
            product_publication_authorized=False,
        )
        _write(staging / PACKAGE_MANIFEST_FILE, _canonical(manifest.model_dump(mode="json")))
        _owner_only(staging)
        _fsync_tree(staging)
        target = root / f"package={manifest.logical_fingerprint}"
        if target.exists() or target.is_symlink():
            existing = read_china_ashare_conservative_reconstruction_package(
                package_path=target
            )
            if existing.manifest != manifest:
                raise ChinaAshareConservativeReconstructionPackageError(
                    "existing conservative reconstruction package differs"
                )
            shutil.rmtree(staging)
            return replace(existing, status="already_present")
        staging.rename(target)
        _fsync_directory(root)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_conservative_reconstruction_package(package_path=target),
        status="published",
    )


def read_china_ashare_conservative_reconstruction_package(
    *, package_path: Path,
) -> ChinaAshareConservativeReconstructionPackageResultV1:
    root = _package(package_path)
    manifest_payload = _read(root / PACKAGE_MANIFEST_FILE, MAXIMUM_JSON_BYTES)
    try:
        manifest = ChinaAshareConservativeUniversePackageManifestV1.model_validate_json(
            manifest_payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareConservativeReconstructionPackageError(
            "conservative reconstruction manifest is invalid"
        ) from exc
    if root.name != f"package={manifest.logical_fingerprint}":
        raise ChinaAshareConservativeReconstructionPackageError(
            "conservative reconstruction path identity differs"
        )
    expected = {PACKAGE_MANIFEST_FILE, *(item.relative_path for item in manifest.artifacts)}
    actual = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
        if item.is_file()
    }
    if actual != expected or any(item.is_symlink() for item in root.rglob("*")):
        raise ChinaAshareConservativeReconstructionPackageError(
            "conservative reconstruction closed file set differs"
        )
    payload_by_path = {}
    for artifact in manifest.artifacts:
        maximum = MAXIMUM_PARQUET_BYTES if artifact.relative_path.endswith(".parquet") else MAXIMUM_JSON_BYTES
        payload = _read(root / artifact.relative_path, maximum)
        if len(payload) != artifact.byte_size or _sha(payload) != artifact.physical_sha256:
            raise ChinaAshareConservativeReconstructionPackageError(
                "conservative reconstruction artifact bytes differ"
            )
        payload_by_path[artifact.relative_path] = payload
    try:
        plan = ChinaAshareConservativeReconstructionPlanV1.model_validate_json(payload_by_path[PLAN_FILE])
        census = ChinaAshareConservativeReconstructionCensusV1.model_validate_json(payload_by_path[CENSUS_FILE])
        smoke = ChinaAsharePriceLimitSmokeV1.model_validate_json(payload_by_path[SMOKE_FILE])
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareConservativeReconstructionPackageError(
            "conservative reconstruction root document is invalid"
        ) from exc
    partition_censuses = []
    partition_manifests = []
    total_counts = Counter()
    for index in range(109):
        prefix = f"partitions/partition-{index:03d}"
        try:
            partition_census = ChinaAshareConservativePartitionCensusV1.model_validate_json(
                payload_by_path[f"{prefix}/partition-census.json"]
            )
            partition_manifest = ChinaAshareConservativeUniversePartitionManifestV1.model_validate_json(
                payload_by_path[f"{prefix}/partition-manifest.json"]
            )
            rows = _parquet_rows(payload_by_path[f"{prefix}/daily-universe.parquet"])
        except (ValidationError, ValueError, pa.ArrowException, OSError) as exc:
            raise ChinaAshareConservativeReconstructionPackageError(
                "conservative reconstruction partition is invalid"
            ) from exc
        counts = Counter(item.disposition for item in rows)
        if (
            partition_census.logical_fingerprint
            != census.partition_census_fingerprints[index]
            or partition_manifest.partition_index != index
            or partition_manifest.partition_census_fingerprint
            != partition_census.logical_fingerprint
            or partition_manifest.logical_fingerprint
            != manifest.partition_manifest_fingerprints[index]
            or partition_manifest.row_count != len(rows)
            or partition_manifest.logical_row_set_fingerprint
            != universe_row_set_fingerprint(rows)
            or partition_manifest.provisional_include_count
            != counts[ChinaAshareConservativeUniverseDisposition.PROVISIONAL_INCLUDE]
            or partition_manifest.warning_exclude_count
            != counts[ChinaAshareConservativeUniverseDisposition.WARNING_EXCLUDE]
            or partition_manifest.quarantine_count
            != counts[ChinaAshareConservativeUniverseDisposition.QUARANTINE]
        ):
            raise ChinaAshareConservativeReconstructionPackageError(
                "conservative reconstruction partition binding differs"
            )
        total_counts.update(counts)
        partition_censuses.append(partition_census)
        partition_manifests.append(partition_manifest)
    if (
        manifest.plan_fingerprint != plan.logical_fingerprint
        or manifest.global_census_fingerprint != census.logical_fingerprint
        or manifest.price_limit_smoke_fingerprint != smoke.logical_fingerprint
        or manifest.candidate_set_fingerprint != census.candidate_set_fingerprint
        or manifest.row_count != sum(total_counts.values())
        or manifest.provisional_include_count
        != total_counts[ChinaAshareConservativeUniverseDisposition.PROVISIONAL_INCLUDE]
        or manifest.warning_exclude_count
        != total_counts[ChinaAshareConservativeUniverseDisposition.WARNING_EXCLUDE]
        or manifest.quarantine_count
        != total_counts[ChinaAshareConservativeUniverseDisposition.QUARANTINE]
    ):
        raise ChinaAshareConservativeReconstructionPackageError(
            "conservative reconstruction package binding differs"
        )
    files = tuple(item for item in root.rglob("*") if item.is_file())
    return ChinaAshareConservativeReconstructionPackageResultV1(
        manifest=manifest,
        plan=plan,
        census=census,
        smoke=smoke,
        partition_censuses=tuple(partition_censuses),
        partition_manifests=tuple(partition_manifests),
        package_path=root,
        manifest_physical_sha256=_sha(manifest_payload),
        file_count=len(files),
        total_bytes=sum(item.stat().st_size for item in files),
        status="exact_reread_complete",
    )


def _parquet_bytes(rows) -> bytes:
    values = [item.model_dump(mode="python") for item in rows]
    for item in values:
        item["instrument_id"] = str(item["instrument_id"])
    table = pa.Table.from_pylist(values, schema=ROW_SCHEMA)
    stream = BytesIO()
    pq.write_table(
        table, stream, compression="zstd", compression_level=9,
        use_dictionary=True, write_statistics=True, version="2.6",
    )
    return stream.getvalue()


def _parquet_rows(payload: bytes) -> tuple[ChinaAshareConservativeUniverseRowV1, ...]:
    table = pq.read_table(pa.BufferReader(payload))
    if table.schema != ROW_SCHEMA:
        raise ValueError("conservative Universe Parquet schema differs")
    rows = tuple(ChinaAshareConservativeUniverseRowV1.model_validate(item) for item in table.to_pylist())
    keys = tuple((str(item.instrument_id), item.session_date) for item in rows)
    if keys != tuple(sorted(set(keys))):
        raise ValueError("conservative Universe Parquet keys differ")
    return rows


def _artifact(relative_path: str, payload: bytes):
    return ChinaAshareConservativeUniverseArtifactV1(
        relative_path=relative_path, byte_size=len(payload), physical_sha256=_sha(payload)
    )


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareConservativeReconstructionPackageError("custody root is unsafe")
    root = candidate.resolve()
    if root == Path("/"):
        raise ChinaAshareConservativeReconstructionPackageError("custody root is unsafe")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    return root


def _package(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareConservativeReconstructionPackageError("package path is unsafe")
    root = candidate.resolve()
    if not root.is_dir() or root.is_symlink() or (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareConservativeReconstructionPackageError("package path is invalid")
    return root


def _read(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file() or (path.stat().st_mode & 0o777) != 0o400:
        raise ChinaAshareConservativeReconstructionPackageError("artifact path is unsafe")
    size = path.stat().st_size
    if size <= 0 or size > maximum:
        raise ChinaAshareConservativeReconstructionPackageError("artifact size is invalid")
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _owner_only(root: Path) -> None:
    for item in root.rglob("*"):
        os.chmod(item, 0o700 if item.is_dir() else 0o400)
    os.chmod(root, 0o700)


def _fsync_tree(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        _fsync_directory(Path(directory))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
