"""Owner-only custody for V2 direct-origin endpoint selection."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_direct_origin_selection import (
    SecCashQualityDirectOriginSelectionPlanV2,
    SecCashQualityDirectOriginSelectionResultV2,
    SecCashQualityDirectOriginSelectionVerificationV2,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    canonical_census_bytes,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    SELECTED_ENDPOINT_SCHEMA,
    TARGET_INDEX_SCHEMA,
    _schema_fingerprint,
)
from tip_api.services.quant_research_sec_cash_quality_direct_origin_selection import (
    _table_bytes,
    independently_verify_sec_cash_quality_direct_origin_selection_v2,
)


PLAN_FILE = "direct-origin-selection-plan.json"
ROWS_FILE = "canonical-endpoint-selections.parquet"
RESULT_FILE = "direct-origin-selection-result.json"
VERIFICATION_FILE = "forward-reverse-verification.json"


class SecCashQualityDirectOriginSelectionCustodyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SecCashQualityDirectOriginSelectionCustodyResultV2:
    plan: SecCashQualityDirectOriginSelectionPlanV2
    result: SecCashQualityDirectOriginSelectionResultV2
    verification: SecCashQualityDirectOriginSelectionVerificationV2
    rows: pa.Table
    package_path: Path
    status: str


def build_and_publish_sec_cash_quality_direct_origin_selection_v2(
    *, target_index_path: Path, custody_root: Path,
    plan: SecCashQualityDirectOriginSelectionPlanV2,
) -> SecCashQualityDirectOriginSelectionCustodyResultV2:
    path = target_index_path.expanduser().resolve()
    if (
        path.is_symlink() or not path.is_file()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or path.stat().st_size != plan.target_index_bytes
        or _file_sha(path) != plan.target_index_physical_sha256
    ):
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin target index physical binding differs"
        )
    rows = pq.ParquetFile(path).read()
    if (
        not rows.schema.equals(TARGET_INDEX_SCHEMA, check_metadata=False)
        or _schema_fingerprint(rows.schema) != plan.target_index_schema_fingerprint
        or rows.num_rows != plan.target_index_row_count
    ):
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin target index logical binding differs"
        )
    selected, result, verification = (
        independently_verify_sec_cash_quality_direct_origin_selection_v2(
            target_index=rows, plan=plan
        )
    )
    return publish_sec_cash_quality_direct_origin_selection_v2(
        custody_root=custody_root, plan=plan, rows=selected,
        result=result, verification=verification,
    )


def publish_sec_cash_quality_direct_origin_selection_v2(
    *, custody_root: Path, plan: SecCashQualityDirectOriginSelectionPlanV2,
    rows: pa.Table, result: SecCashQualityDirectOriginSelectionResultV2,
    verification: SecCashQualityDirectOriginSelectionVerificationV2,
) -> SecCashQualityDirectOriginSelectionCustodyResultV2:
    _validate(plan, rows, result, verification)
    root = custody_root.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    target = root / f"verification={verification.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        return replace(
            read_sec_cash_quality_direct_origin_selection_v2(package_path=target),
            status="already_present",
        )
    staging = Path(tempfile.mkdtemp(prefix=".direct-origin-v2-", dir=root))
    try:
        _write(staging / PLAN_FILE, canonical_census_bytes(plan) + b"\n")
        pq.write_table(
            rows, staging / ROWS_FILE, compression="zstd", row_group_size=65_536
        )
        _write(staging / RESULT_FILE, canonical_census_bytes(result) + b"\n")
        _write(
            staging / VERIFICATION_FILE,
            canonical_census_bytes(verification) + b"\n",
        )
        staging.chmod(0o700)
        for item in staging.iterdir():
            item.chmod(0o400)
            _fsync_file(item)
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(root)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_sec_cash_quality_direct_origin_selection_v2(package_path=target),
        status="published",
    )


def read_sec_cash_quality_direct_origin_selection_v2(
    *, package_path: Path
) -> SecCashQualityDirectOriginSelectionCustodyResultV2:
    root = package_path.expanduser()
    if root.is_symlink():
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin package is unsafe"
        )
    root = root.resolve()
    if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin package custody differs"
        )
    if {item.name for item in root.iterdir()} != {
        PLAN_FILE, ROWS_FILE, RESULT_FILE, VERIFICATION_FILE,
    }:
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin package inventory differs"
        )
    plan = _read(root / PLAN_FILE, SecCashQualityDirectOriginSelectionPlanV2)
    result = _read(root / RESULT_FILE, SecCashQualityDirectOriginSelectionResultV2)
    verification = _read(
        root / VERIFICATION_FILE,
        SecCashQualityDirectOriginSelectionVerificationV2,
    )
    rows_path = root / ROWS_FILE
    if rows_path.is_symlink() or stat.S_IMODE(rows_path.stat().st_mode) != 0o400:
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin row custody differs"
        )
    rows = pq.ParquetFile(rows_path).read()
    _validate(plan, rows, result, verification)
    if root.name != f"verification={verification.logical_fingerprint}":
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin package identity differs"
        )
    return SecCashQualityDirectOriginSelectionCustodyResultV2(
        plan=plan, result=result, verification=verification, rows=rows,
        package_path=root, status="exact_reread_complete",
    )


def _validate(plan, rows, result, verification) -> None:
    row_sha = hashlib.sha256(_table_bytes(rows)).hexdigest()
    if (
        not rows.schema.equals(SELECTED_ENDPOINT_SCHEMA, check_metadata=False)
        or rows.num_rows != result.output_query_row_count
        or result.plan_fingerprint != plan.logical_fingerprint
        or verification.plan_fingerprint != plan.logical_fingerprint
        or verification.primary_result_fingerprint != result.logical_fingerprint
        or verification.primary_rows_sha256 != row_sha
    ):
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin custody binding differs"
        )


def _read(path: Path, model: type):
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin JSON custody differs"
        )
    raw = path.read_bytes()
    value = model.model_validate_json(raw)
    if raw != canonical_census_bytes(value) + b"\n":
        raise SecCashQualityDirectOriginSelectionCustodyError(
            "direct-origin JSON is not canonical"
        )
    return value


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
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
