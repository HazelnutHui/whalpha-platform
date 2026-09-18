"""Owner-only atomic custody for corrected TTM V2 coverage."""

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
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_ttm_coverage_v2 import (
    SecCashQualityTtmCoveragePlanV2,
    SecCashQualityTtmCoverageResultV2,
    SecCashQualityTtmCoverageVerificationV2,
)
from tip_api.persistence.quant_research_sec_cash_quality_endpoint_selection import (
    SELECTED_ENDPOINT_SCHEMA,
    _schema_fingerprint,
)
from tip_api.services.quant_research_sec_cash_quality_ttm_coverage_v2 import (
    TTM_V2_ARROW_SCHEMA,
    _table_bytes,
    independently_verify_sec_cash_quality_ttm_coverage_v2,
)


PLAN_FILE = "ttm-coverage-v2-plan.json"
ROWS_FILE = "issuer-ttm-v2-rows.parquet"
RESULT_FILE = "ttm-coverage-v2-result.json"
VERIFICATION_FILE = "forward-reverse-verification.json"


class SecCashQualityTtmCoverageV2CustodyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SecCashQualityTtmCoverageV2CustodyResult:
    plan: SecCashQualityTtmCoveragePlanV2
    result: SecCashQualityTtmCoverageResultV2
    verification: SecCashQualityTtmCoverageVerificationV2
    rows: pa.Table
    package_path: Path
    status: str


def build_and_publish_sec_cash_quality_ttm_coverage_v2(
    *, source_rows_path: Path, custody_root: Path,
    plan: SecCashQualityTtmCoveragePlanV2,
) -> SecCashQualityTtmCoverageV2CustodyResult:
    path = source_rows_path.expanduser().resolve()
    if (
        path.is_symlink() or not path.is_file()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or path.stat().st_size != plan.source_rows_bytes
        or _file_sha(path) != plan.source_rows_physical_sha256
    ):
        raise SecCashQualityTtmCoverageV2CustodyError(
            "TTM V2 source physical binding differs"
        )
    source_rows = pq.ParquetFile(path).read()
    if (
        not source_rows.schema.equals(SELECTED_ENDPOINT_SCHEMA, check_metadata=False)
        or _schema_fingerprint(source_rows.schema) != plan.source_rows_schema_fingerprint
        or source_rows.num_rows != plan.input_query_row_count
        or hashlib.sha256(_selected_table_bytes(source_rows)).hexdigest()
        != plan.source_rows_logical_sha256
    ):
        raise SecCashQualityTtmCoverageV2CustodyError(
            "TTM V2 source logical binding differs"
        )
    rows, result, verification = independently_verify_sec_cash_quality_ttm_coverage_v2(
        selected_endpoints=source_rows, plan=plan
    )
    return publish_sec_cash_quality_ttm_coverage_v2(
        custody_root=custody_root, plan=plan, rows=rows,
        result=result, verification=verification,
    )


def publish_sec_cash_quality_ttm_coverage_v2(
    *, custody_root: Path, plan: SecCashQualityTtmCoveragePlanV2,
    rows: pa.Table, result: SecCashQualityTtmCoverageResultV2,
    verification: SecCashQualityTtmCoverageVerificationV2,
) -> SecCashQualityTtmCoverageV2CustodyResult:
    _validate(plan, rows, result, verification)
    root = custody_root.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    target = root / f"verification={verification.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        return replace(read_sec_cash_quality_ttm_coverage_v2(package_path=target), status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".ttm-v2-", dir=root))
    try:
        _write(staging / PLAN_FILE, canonical_census_bytes(plan) + b"\n")
        pq.write_table(rows, staging / ROWS_FILE, compression="zstd", row_group_size=65_536)
        _write(staging / RESULT_FILE, canonical_census_bytes(result) + b"\n")
        _write(staging / VERIFICATION_FILE, canonical_census_bytes(verification) + b"\n")
        staging.chmod(0o700)
        for item in staging.iterdir():
            item.chmod(0o400); _fsync_file(item)
        _fsync_directory(staging)
        staging.rename(target); _fsync_directory(root)
    except BaseException:
        if staging.exists() and not staging.is_symlink(): shutil.rmtree(staging)
        raise
    return replace(read_sec_cash_quality_ttm_coverage_v2(package_path=target), status="published")


def read_sec_cash_quality_ttm_coverage_v2(
    *, package_path: Path
) -> SecCashQualityTtmCoverageV2CustodyResult:
    root = package_path.expanduser()
    if root.is_symlink(): raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 package is unsafe")
    root = root.resolve()
    if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 custody differs")
    if {item.name for item in root.iterdir()} != {PLAN_FILE, ROWS_FILE, RESULT_FILE, VERIFICATION_FILE}:
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 inventory differs")
    plan = _read(root / PLAN_FILE, SecCashQualityTtmCoveragePlanV2)
    result = _read(root / RESULT_FILE, SecCashQualityTtmCoverageResultV2)
    verification = _read(root / VERIFICATION_FILE, SecCashQualityTtmCoverageVerificationV2)
    rows_path = root / ROWS_FILE
    if rows_path.is_symlink() or stat.S_IMODE(rows_path.stat().st_mode) != 0o400:
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 rows custody differs")
    rows = pq.ParquetFile(rows_path).read()
    _validate(plan, rows, result, verification)
    if root.name != f"verification={verification.logical_fingerprint}":
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 identity differs")
    return SecCashQualityTtmCoverageV2CustodyResult(
        plan, result, verification, rows, root, "exact_reread_complete"
    )


def _validate(plan, rows, result, verification):
    if (
        not rows.schema.equals(TTM_V2_ARROW_SCHEMA, check_metadata=False)
        or rows.num_rows != result.ttm_ready_endpoint_count
        or result.plan_fingerprint != plan.logical_fingerprint
        or verification.plan_fingerprint != plan.logical_fingerprint
        or verification.primary_result_fingerprint != result.logical_fingerprint
        or verification.primary_rows_sha256 != hashlib.sha256(_table_bytes(rows)).hexdigest()
    ):
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 binding differs")


def _selected_table_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, SELECTED_ENDPOINT_SCHEMA) as writer:
        writer.write_table(table.combine_chunks())
    return sink.getvalue().to_pybytes()


def _read(path, model):
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 JSON custody differs")
    raw = path.read_bytes(); value = model.model_validate_json(raw)
    if raw != canonical_census_bytes(value) + b"\n":
        raise SecCashQualityTtmCoverageV2CustodyError("TTM V2 JSON is not canonical")
    return value


def _file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()


def _write(path, payload):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())


def _fsync_file(path):
    descriptor = os.open(path, os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)
