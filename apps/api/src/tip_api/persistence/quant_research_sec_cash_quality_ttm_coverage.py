"""Owner-only atomic custody for issuer-level cash-quality TTM coverage."""

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

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import canonical_census_bytes
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_ttm_coverage import (
    SecCashQualityTtmCoveragePlanV1,
    SecCashQualityTtmCoverageResultV1,
    SecCashQualityTtmCoverageVerificationV1,
)
from tip_api.services.quant_research_sec_cash_quality_ttm_coverage import (
    TTM_ARROW_SCHEMA,
    _table_bytes,
)


PLAN_FILE = "ttm-coverage-plan.json"
ROWS_FILE = "issuer-ttm-rows.parquet"
RESULT_FILE = "ttm-coverage-result.json"
VERIFICATION_FILE = "forward-reverse-verification.json"


class SecCashQualityTtmCoverageCustodyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SecCashQualityTtmCoverageCustodyResultV1:
    plan: SecCashQualityTtmCoveragePlanV1
    result: SecCashQualityTtmCoverageResultV1
    verification: SecCashQualityTtmCoverageVerificationV1
    rows: pa.Table
    package_path: Path
    status: str


def publish_sec_cash_quality_ttm_coverage(
    *, custody_root: Path, plan: SecCashQualityTtmCoveragePlanV1,
    rows: pa.Table, result: SecCashQualityTtmCoverageResultV1,
    verification: SecCashQualityTtmCoverageVerificationV1,
) -> SecCashQualityTtmCoverageCustodyResultV1:
    _validate(plan, rows, result, verification)
    root = custody_root.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    target = root / f"verification={verification.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        return replace(read_sec_cash_quality_ttm_coverage(package_path=target), status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".ttm-coverage-", dir=root))
    try:
        _write(staging / PLAN_FILE, canonical_census_bytes(plan) + b"\n")
        pq.write_table(rows, staging / ROWS_FILE, compression="zstd", row_group_size=65_536)
        _write(staging / RESULT_FILE, canonical_census_bytes(result) + b"\n")
        _write(staging / VERIFICATION_FILE, canonical_census_bytes(verification) + b"\n")
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
    return replace(read_sec_cash_quality_ttm_coverage(package_path=target), status="published")


def read_sec_cash_quality_ttm_coverage(
    *, package_path: Path
) -> SecCashQualityTtmCoverageCustodyResultV1:
    root = package_path.expanduser()
    if root.is_symlink():
        raise SecCashQualityTtmCoverageCustodyError("TTM coverage package is unsafe")
    root = root.resolve()
    if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise SecCashQualityTtmCoverageCustodyError("TTM coverage package custody differs")
    if {item.name for item in root.iterdir()} != {PLAN_FILE, ROWS_FILE, RESULT_FILE, VERIFICATION_FILE}:
        raise SecCashQualityTtmCoverageCustodyError("TTM coverage package inventory differs")
    plan = _read(root / PLAN_FILE, SecCashQualityTtmCoveragePlanV1)
    result = _read(root / RESULT_FILE, SecCashQualityTtmCoverageResultV1)
    verification = _read(root / VERIFICATION_FILE, SecCashQualityTtmCoverageVerificationV1)
    rows_path = root / ROWS_FILE
    if rows_path.is_symlink() or stat.S_IMODE(rows_path.stat().st_mode) != 0o400:
        raise SecCashQualityTtmCoverageCustodyError("TTM row custody differs")
    rows = pq.ParquetFile(rows_path).read()
    _validate(plan, rows, result, verification)
    if root.name != f"verification={verification.logical_fingerprint}":
        raise SecCashQualityTtmCoverageCustodyError("TTM package identity differs")
    return SecCashQualityTtmCoverageCustodyResultV1(
        plan=plan, result=result, verification=verification, rows=rows,
        package_path=root, status="exact_reread_complete"
    )


def _validate(plan, rows, result, verification) -> None:
    row_sha = hashlib.sha256(_table_bytes(rows)).hexdigest()
    if (
        not rows.schema.equals(TTM_ARROW_SCHEMA, check_metadata=False)
        or rows.num_rows != result.ttm_ready_endpoint_count
        or result.plan_fingerprint != plan.logical_fingerprint
        or verification.plan_fingerprint != plan.logical_fingerprint
        or verification.primary_result_fingerprint != result.logical_fingerprint
        or verification.primary_rows_sha256 != row_sha
    ):
        raise SecCashQualityTtmCoverageCustodyError("TTM coverage binding differs")


def _read(path: Path, model: type):
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise SecCashQualityTtmCoverageCustodyError("TTM JSON custody differs")
    raw = path.read_bytes()
    value = model.model_validate_json(raw)
    if raw != canonical_census_bytes(value) + b"\n":
        raise SecCashQualityTtmCoverageCustodyError("TTM JSON is not canonical")
    return value


def _write(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
