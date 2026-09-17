"""Verify the exact normalized A-share run behind the coverage report."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    NORMALIZED_RUN_FINGERPRINT,
    ChinaAshareFullPopulationCoverageReportV1,
    china_ashare_full_population_coverage_report_v1,
)
from tip_api.contracts.china_ashare.v1.normalized_expansion import (
    ChinaAshareNormalizedExpansionPartitionManifestV1,
)
from tip_api.persistence.china_ashare_normalized_expansion_package import (
    ADJUSTMENT_FILE,
    BAR_FILE,
    MANIFEST_FILE,
    STATE_FILE,
)


class ChinaAshareFullPopulationCoverageError(RuntimeError):
    pass


def verify_china_ashare_full_population_coverage(
    *, normalized_run_root: Path
) -> ChinaAshareFullPopulationCoverageReportV1:
    root = normalized_run_root.expanduser().resolve()
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.name != f"run={NORMALIZED_RUN_FINGERPRINT}"
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion run root is invalid"
        )
    partitions_root = root / "partitions"
    if partitions_root.is_symlink() or not partitions_root.is_dir():
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partitions root is invalid"
        )
    partition_paths = tuple(
        sorted(item for item in partitions_root.iterdir() if item.is_dir())
    )
    if len(partition_paths) != 109 or tuple(item.name for item in partition_paths) != (
        tuple(f"{index:05d}" for index in range(109))
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partition set differs"
        )

    manifests = tuple(_read_partition_manifest(item) for item in partition_paths)
    report = china_ashare_full_population_coverage_report_v1()
    sums = {
        field: sum(int(getattr(item, field)) for item in manifests)
        for field in (
            "target_count",
            "resolved_target_count",
            "quarantined_target_count",
            "normalized_bar_count",
            "normalized_state_count",
            "normalized_adjustment_count",
            "suspended_state_count",
            "risk_warning_present_state_count",
        )
    }
    expected = {
        "target_count": report.target_count,
        "resolved_target_count": report.resolved_target_count,
        "quarantined_target_count": report.quarantined_target_count,
        "normalized_bar_count": report.normalized_bar_count,
        "normalized_state_count": report.normalized_state_count,
        "normalized_adjustment_count": report.normalized_adjustment_observation_count,
        "suspended_state_count": report.suspended_state_count,
        "risk_warning_present_state_count": report.risk_warning_present_unspecified_count,
    }
    if sums != expected:
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion aggregate differs from frozen coverage report"
        )

    state_files = tuple(item / STATE_FILE for item in partition_paths)
    table = ds.dataset(tuple(str(item) for item in state_files), format="parquet").to_table(
        columns=["price_limit_regime", "source_available_at"]
    )
    unknown_count = int(
        pc.sum(pc.equal(table["price_limit_regime"], "unknown")).as_py() or 0
    )
    source_null_count = table["source_available_at"].null_count
    if (
        unknown_count != report.price_limit_regime_unknown_count
        or source_null_count != report.source_available_at_null_count
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion point-in-time boundary differs"
        )
    return report


def _read_partition_manifest(
    partition_root: Path,
) -> ChinaAshareNormalizedExpansionPartitionManifestV1:
    if partition_root.is_symlink():
        raise ChinaAshareFullPopulationCoverageError("partition path is unsafe")
    manifest_path = partition_root / MANIFEST_FILE
    try:
        manifest = ChinaAshareNormalizedExpansionPartitionManifestV1.model_validate_json(
            _read(manifest_path, maximum_bytes=16 * 1024 * 1024)
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partition manifest is invalid"
        ) from exc
    if (
        manifest.run_fingerprint != NORMALIZED_RUN_FINGERPRINT
        or manifest.partition_index != int(partition_root.name)
    ):
        raise ChinaAshareFullPopulationCoverageError(
            "normalized expansion partition binding differs"
        )
    for name, expected_size, expected_hash in (
        (BAR_FILE, manifest.bar_parquet_bytes, manifest.bar_parquet_sha256),
        (STATE_FILE, manifest.state_parquet_bytes, manifest.state_parquet_sha256),
        (
            ADJUSTMENT_FILE,
            manifest.adjustment_parquet_bytes,
            manifest.adjustment_parquet_sha256,
        ),
    ):
        path = partition_root / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != expected_size
            or _file_sha256(path) != expected_hash
        ):
            raise ChinaAshareFullPopulationCoverageError(
                "normalized expansion partition payload differs"
            )
    return manifest


def _read(path: Path, *, maximum_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareFullPopulationCoverageError("coverage input is absent or unsafe")
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise ChinaAshareFullPopulationCoverageError("coverage input size is invalid")
    return path.read_bytes()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
