"""Owner-only custody for reusable cash-quality target and endpoint indexes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_query_registry import (
    quant_research_sec_cash_quality_query_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_endpoint_selection_package import (
    SecCashQualityEndpointSelectionPackageManifestV1,
    SecCashQualityEndpointSelectionPlanV1,
    SecCashQualityTtmFeasibilityPlanV1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    canonical_census_bytes,
    census_fingerprint,
)


PLAN_FILE = "selection-plan.json"
TARGET_INDEX_FILE = "target-occurrence-index.parquet"
SELECTED_FILE = "ready-endpoint-selections.parquet"
MANIFEST_FILE = "package-manifest.json"
TTM_PLAN_FILE = "ttm-feasibility-plan.json"
MAXIMUM_JSON_BYTES = 4 * 1024 * 1024

TARGET_INDEX_SCHEMA = pa.schema(
    [
        pa.field("source_occurrence_id", pa.string(), nullable=False),
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("namespace", pa.string(), nullable=False),
        pa.field("concept_name", pa.string(), nullable=False),
        pa.field("unit", pa.string(), nullable=False),
        pa.field("start_date", pa.date32(), nullable=True),
        pa.field("end_date", pa.date32(), nullable=True),
        pa.field("value_kind", pa.string(), nullable=False),
        pa.field("value_text", pa.string(), nullable=True),
        pa.field("accession_number", pa.string(), nullable=False),
        pa.field("fiscal_year", pa.int32(), nullable=True),
        pa.field("fiscal_period", pa.string(), nullable=True),
        pa.field("form", pa.string(), nullable=False),
        pa.field("filed_date", pa.date32(), nullable=False),
        pa.field("source_available_at_utc", pa.timestamp("ms", tz="UTC"), nullable=True),
        pa.field("signal_eligible_session", pa.date32(), nullable=True),
        pa.field("filing_clock_admission_status", pa.string(), nullable=False),
        pa.field("normalization_status", pa.string(), nullable=False),
        pa.field("occurrence_disposition", pa.string(), nullable=False),
    ]
)

SELECTED_ENDPOINT_SCHEMA = pa.schema(
    [
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("fiscal_year", pa.int32(), nullable=False),
        pa.field("fiscal_year_origin", pa.date32(), nullable=False),
        pa.field("fiscal_period", pa.string(), nullable=False),
        pa.field("period_end", pa.date32(), nullable=False),
        pa.field("query_id", pa.string(), nullable=False),
        pa.field("concept_name", pa.string(), nullable=False),
        pa.field("value_kind", pa.string(), nullable=False),
        pa.field("value_text", pa.string(), nullable=False),
        pa.field("accession_number", pa.string(), nullable=False),
        pa.field("source_available_at_utc", pa.timestamp("ms", tz="UTC"), nullable=False),
        pa.field("signal_eligible_session", pa.date32(), nullable=False),
        pa.field("source_occurrence_ids", pa.list_(pa.string()), nullable=False),
    ]
)


class SecCashQualityEndpointSelectionCustodyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SecCashQualityEndpointSelectionPackageResultV1:
    plan: SecCashQualityEndpointSelectionPlanV1
    manifest: SecCashQualityEndpointSelectionPackageManifestV1
    package_path: Path
    status: str


@dataclass(frozen=True, slots=True)
class SecCashQualityTtmFeasibilityPlanResultV1:
    plan: SecCashQualityTtmFeasibilityPlanV1
    package_path: Path
    status: str


def publish_sec_cash_quality_endpoint_selection_package(
    *,
    custody_root: Path,
    plan: SecCashQualityEndpointSelectionPlanV1,
    target_index: pa.Table,
    selected_endpoints: pa.Table,
    built_at: datetime,
) -> SecCashQualityEndpointSelectionPackageResultV1:
    """Atomically publish one bounded target index and ready-only selection set."""

    _validate_tables(plan, target_index, selected_endpoints)
    parent = _ensure_directory(custody_root.expanduser().resolve())
    staging = Path(tempfile.mkdtemp(prefix=".selection-", dir=parent))
    try:
        _write_json(staging / PLAN_FILE, _canonical(plan))
        pq.write_table(
            target_index,
            staging / TARGET_INDEX_FILE,
            compression="zstd",
            row_group_size=65_536,
        )
        pq.write_table(
            selected_endpoints,
            staging / SELECTED_FILE,
            compression="zstd",
            row_group_size=65_536,
        )
        target_path = staging / TARGET_INDEX_FILE
        selected_path = staging / SELECTED_FILE
        values = {
            "plan_fingerprint": plan.logical_fingerprint,
            "built_at": built_at,
            "target_index_schema_fingerprint": _schema_fingerprint(
                TARGET_INDEX_SCHEMA
            ),
            "target_index_row_count": target_index.num_rows,
            "target_index_bytes": target_path.stat().st_size,
            "target_index_sha256": _file_sha(target_path),
            "selected_endpoint_schema_fingerprint": _schema_fingerprint(
                SELECTED_ENDPOINT_SCHEMA
            ),
            "selected_endpoint_count": plan.admitted_ready_endpoint_count,
            "selected_query_row_count": selected_endpoints.num_rows,
            "selected_endpoint_bytes": selected_path.stat().st_size,
            "selected_endpoint_sha256": _file_sha(selected_path),
        }
        provisional = SecCashQualityEndpointSelectionPackageManifestV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
        manifest = SecCashQualityEndpointSelectionPackageManifestV1.model_validate(
            {**values, "logical_fingerprint": census_fingerprint(provisional)}
        )
        _write_json(staging / MANIFEST_FILE, _canonical(manifest))
        _owner_only(staging)
        _fsync_tree(staging)
        target = parent / f"package={manifest.logical_fingerprint}"
        if target.exists() or target.is_symlink():
            existing = read_sec_cash_quality_endpoint_selection_package(
                package_path=target
            )
            if existing.plan != plan or existing.manifest != manifest:
                raise SecCashQualityEndpointSelectionCustodyError(
                    "existing cash-quality endpoint package differs"
                )
            shutil.rmtree(staging)
            return replace(existing, status="already_present")
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_sec_cash_quality_endpoint_selection_package(package_path=target),
        status="published",
    )


def read_sec_cash_quality_endpoint_selection_package(
    *, package_path: Path
) -> SecCashQualityEndpointSelectionPackageResultV1:
    root = _validate_package(package_path)
    if {item.name for item in root.iterdir()} != {
        PLAN_FILE,
        TARGET_INDEX_FILE,
        SELECTED_FILE,
        MANIFEST_FILE,
    }:
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint package inventory differs"
        )
    plan = _read_json(root / PLAN_FILE, SecCashQualityEndpointSelectionPlanV1)
    manifest = _read_json(
        root / MANIFEST_FILE,
        SecCashQualityEndpointSelectionPackageManifestV1,
    )
    target_path = root / TARGET_INDEX_FILE
    selected_path = root / SELECTED_FILE
    for path in (target_path, selected_path):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_uid != os.getuid()
            or stat.S_IMODE(path.stat().st_mode) != 0o400
        ):
            raise SecCashQualityEndpointSelectionCustodyError(
                "cash-quality endpoint Parquet custody differs"
            )
    target = pq.ParquetFile(target_path).read()
    selected = pq.ParquetFile(selected_path).read()
    if (
        root.name != f"package={manifest.logical_fingerprint}"
        or manifest.plan_fingerprint != plan.logical_fingerprint
        or manifest.target_index_schema_fingerprint
        != _schema_fingerprint(TARGET_INDEX_SCHEMA)
        or manifest.target_index_row_count != target.num_rows
        or manifest.target_index_bytes != target_path.stat().st_size
        or manifest.target_index_sha256 != _file_sha(target_path)
        or manifest.selected_endpoint_schema_fingerprint
        != _schema_fingerprint(SELECTED_ENDPOINT_SCHEMA)
        or manifest.selected_endpoint_count
        != plan.admitted_ready_endpoint_count
        or manifest.selected_query_row_count != selected.num_rows
        or manifest.selected_endpoint_bytes != selected_path.stat().st_size
        or manifest.selected_endpoint_sha256 != _file_sha(selected_path)
    ):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint package binding differs"
        )
    _validate_tables(plan, target, selected)
    return SecCashQualityEndpointSelectionPackageResultV1(
        plan=plan,
        manifest=manifest,
        package_path=root,
        status="exact_reread_complete",
    )


def publish_sec_cash_quality_ttm_feasibility_plan(
    *,
    custody_root: Path,
    plan: SecCashQualityTtmFeasibilityPlanV1,
) -> SecCashQualityTtmFeasibilityPlanResultV1:
    """Atomically persist one plan-only, zero-execution TTM feasibility object."""

    parent = _ensure_directory(custody_root.expanduser().resolve())
    target = parent / f"ttm-plan={plan.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_sec_cash_quality_ttm_feasibility_plan(package_path=target)
        if existing.plan != plan:
            raise SecCashQualityEndpointSelectionCustodyError(
                "existing cash-quality TTM feasibility plan differs"
            )
        return replace(existing, status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".ttm-plan-", dir=parent))
    try:
        _write_json(staging / TTM_PLAN_FILE, _canonical(plan))
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_sec_cash_quality_ttm_feasibility_plan(package_path=target),
        status="published",
    )


def read_sec_cash_quality_ttm_feasibility_plan(
    *, package_path: Path
) -> SecCashQualityTtmFeasibilityPlanResultV1:
    root = _validate_package(package_path)
    if {item.name for item in root.iterdir()} != {TTM_PLAN_FILE}:
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality TTM feasibility plan inventory differs"
        )
    plan = _read_json(root / TTM_PLAN_FILE, SecCashQualityTtmFeasibilityPlanV1)
    if root.name != f"ttm-plan={plan.logical_fingerprint}":
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality TTM feasibility plan identity differs"
        )
    return SecCashQualityTtmFeasibilityPlanResultV1(
        plan=plan,
        package_path=root,
        status="exact_reread_complete",
    )


def _validate_tables(
    plan: SecCashQualityEndpointSelectionPlanV1,
    target: pa.Table,
    selected: pa.Table,
) -> None:
    if not target.schema.equals(
        TARGET_INDEX_SCHEMA, check_metadata=False
    ) or not selected.schema.equals(
        SELECTED_ENDPOINT_SCHEMA, check_metadata=False
    ):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint package schema differs"
        )
    if (
        target.num_rows != plan.target_occurrence_count
        or selected.num_rows != plan.admitted_ready_endpoint_count * 3
    ):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint package row count differs"
        )
    query_ids = set(quant_research_sec_cash_quality_query_registry_v1().query_order)
    groups: dict[tuple[object, ...], set[str]] = {}
    accessions: dict[tuple[object, ...], dict[str, str]] = {}
    for row in selected.to_pylist():
        key = (
            row["companyfacts_cik"],
            row["fiscal_year"],
            row["fiscal_year_origin"],
            row["fiscal_period"],
            row["period_end"],
        )
        groups.setdefault(key, set()).add(row["query_id"])
        accessions.setdefault(key, {})[row["query_id"]] = row["accession_number"]
        if not row["source_occurrence_ids"]:
            raise SecCashQualityEndpointSelectionCustodyError(
                "cash-quality selected occurrence lineage is empty"
            )
    if len(groups) != plan.admitted_ready_endpoint_count or any(
        ids != query_ids for ids in groups.values()
    ):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality selected endpoint membership differs"
        )
    for values in accessions.values():
        if values["operating_cash_flow_fiscal_ytd_and_year_v1"] != values[
            "net_income_loss_fiscal_ytd_and_year_v1"
        ]:
            raise SecCashQualityEndpointSelectionCustodyError(
                "cash-quality duration accession coherence differs"
            )


def _canonical(value: object) -> bytes:
    return canonical_census_bytes(value) + b"\n"


def _read_json(path: Path, model: type):
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_JSON_BYTES
    ):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint JSON custody differs"
        )
    payload = path.read_bytes()
    try:
        value = model.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint JSON is invalid"
        ) from exc
    if payload != _canonical(value):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint JSON is not canonical"
        )
    return value


def _schema_fingerprint(schema: pa.Schema) -> str:
    return hashlib.sha256(schema.serialize().to_pybytes()).hexdigest()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.stat().st_uid != os.getuid():
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint custody root is invalid"
        )
    path.chmod(0o700)
    return path


def _validate_package(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint package cannot be a symlink"
        )
    root = candidate.resolve()
    if (
        not root.is_dir()
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
    ):
        raise SecCashQualityEndpointSelectionCustodyError(
            "cash-quality endpoint package custody differs"
        )
    return root


def _write_json(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _owner_only(root: Path) -> None:
    root.chmod(0o700)
    for item in root.iterdir():
        item.chmod(0o400)


def _fsync_tree(root: Path) -> None:
    for item in root.iterdir():
        descriptor = os.open(item, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    _fsync_directory(root)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
