"""Closed-set custody for the listed-security applicability census."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

import pyarrow.parquet as pq
import pyarrow as pa
import pyarrow.compute as pc

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_security_applicability import (
    SecCashQualitySecurityApplicabilityPlanV1,
    SecCashQualitySecurityApplicabilityResultV1,
    SecCashQualitySecurityApplicabilityVerificationV1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import canonical_census_bytes
from tip_api.persistence.parquet.security_evidence import INSTRUMENT_EVIDENCE_SCHEMA
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.quant_research_sec_cash_quality_security_applicability import independently_verify_sec_cash_quality_security_applicability
from tip_api.services.sec_filer_security_link_decision import LINK_ARROW_SCHEMA, SecFilerSecurityLinkManifestV1


PLAN_FILE = "security-applicability-plan.json"
RESULT_FILE = "security-applicability-result.json"
VERIFICATION_FILE = "forward-reverse-verification.json"


class SecCashQualitySecurityApplicabilityCustodyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SecurityApplicabilityCustodyResult:
    plan: SecCashQualitySecurityApplicabilityPlanV1
    result: SecCashQualitySecurityApplicabilityResultV1
    verification: SecCashQualitySecurityApplicabilityVerificationV1
    package_path: Path
    status: str


def run_and_publish_sec_cash_quality_security_applicability(
    *, plan: SecCashQualitySecurityApplicabilityPlanV1,
    ttm_rows_path: Path, lineage_rows_path: Path, link_package_path: Path,
    provider_form_manifest_path: Path, provider_form_rows_path: Path,
    custody_root: Path,
) -> SecurityApplicabilityCustodyResult:
    _bind_file(ttm_rows_path, plan.ttm_rows)
    _bind_file(lineage_rows_path, plan.lineage_rows)
    _bind_file(provider_form_rows_path, plan.provider_form_rows, require_owner_only=False)
    link_manifest_path = link_package_path / "manifest.json"
    if (
        _file_sha(link_manifest_path) != plan.link_manifest_physical_sha256
        or link_manifest_path.stat().st_size != plan.link_manifest_byte_size
    ):
        raise SecCashQualitySecurityApplicabilityCustodyError("link manifest binding differs")
    manifest = SecFilerSecurityLinkManifestV1.model_validate_json(link_manifest_path.read_bytes())
    if manifest.logical_fingerprint != plan.link_manifest_logical_fingerprint:
        raise SecCashQualitySecurityApplicabilityCustodyError("link logical binding differs")
    evidence_by_date = {item.as_of_date: item for item in manifest.sessions}
    ttm_rows = pq.ParquetFile(ttm_rows_path).read()
    lineage_rows = pq.ParquetFile(lineage_rows_path).read()
    occurrence_sessions = {}
    for row in lineage_rows.select(["signal_eligible_session", "source_occurrence_ids"]).to_pylist():
        for occurrence_id in row["source_occurrence_ids"]:
            occurrence_sessions[occurrence_id] = row["signal_eligible_session"]
    target_ciks = {}
    for row in ttm_rows.select(["companyfacts_cik", "source_occurrence_ids"]).to_pylist():
        sessions = [occurrence_sessions.get(item) for item in row["source_occurrence_ids"]]
        if sessions and all(item is not None for item in sessions):
            target_ciks.setdefault(max(sessions), set()).add(row["companyfacts_cik"])
    link_tables = {}
    for binding in plan.link_sessions:
        evidence = evidence_by_date.get(binding.session_date)
        if (
            evidence is None or evidence.relative_path != binding.relative_path
            or evidence.physical_sha256 != binding.physical_sha256
            or evidence.byte_size != binding.byte_size
            or evidence.row_count != binding.row_count
            or evidence.point_in_time_eligibility != binding.point_in_time_eligibility
        ):
            raise SecCashQualitySecurityApplicabilityCustodyError("link session evidence differs")
        path = link_package_path / binding.relative_path
        _bind_file(path, binding)
        parquet = pq.ParquetFile(path)
        if not parquet.schema_arrow.equals(LINK_ARROW_SCHEMA, check_metadata=False):
            raise SecCashQualitySecurityApplicabilityCustodyError("link session schema differs")
        table = parquet.read()
        ciks = target_ciks.get(binding.session_date, set())
        link_tables[binding.session_date] = table.filter(
            pc.is_in(
                table["sec_cik"],
                value_set=pa.array(sorted(ciks), type=pa.string()),
            )
        )
    if (
        _file_sha(provider_form_manifest_path)
        != plan.provider_form_manifest_physical_sha256
    ):
        raise SecCashQualitySecurityApplicabilityCustodyError("provider form manifest differs")
    provider_rows = pq.ParquetFile(provider_form_rows_path).read()
    if not provider_rows.schema.equals(INSTRUMENT_EVIDENCE_SCHEMA, check_metadata=False):
        raise SecCashQualitySecurityApplicabilityCustodyError("provider form schema differs")
    calendar = ExchangeCalendar()
    if calendar.calendar_version != plan.calendar_version:
        raise SecCashQualitySecurityApplicabilityCustodyError("calendar version differs")
    opens = {session: calendar.session_open(session) for session in link_tables}
    result, verification = independently_verify_sec_cash_quality_security_applicability(
        ttm_rows=ttm_rows, lineage_rows=lineage_rows,
        link_rows_by_session=link_tables, provider_form_rows=provider_rows,
        session_opens=opens, plan=plan,
    )
    return publish_sec_cash_quality_security_applicability(
        custody_root=custody_root, plan=plan, result=result,
        verification=verification,
    )


def publish_sec_cash_quality_security_applicability(
    *, custody_root: Path, plan: SecCashQualitySecurityApplicabilityPlanV1,
    result: SecCashQualitySecurityApplicabilityResultV1,
    verification: SecCashQualitySecurityApplicabilityVerificationV1,
) -> SecurityApplicabilityCustodyResult:
    _validate(plan, result, verification)
    root = custody_root.expanduser().resolve(); root.mkdir(mode=0o700, parents=True, exist_ok=True); root.chmod(0o700)
    target = root / f"verification={verification.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        return replace(read_sec_cash_quality_security_applicability(package_path=target), status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".security-applicability-", dir=root))
    try:
        _write(staging / PLAN_FILE, canonical_census_bytes(plan) + b"\n")
        _write(staging / RESULT_FILE, canonical_census_bytes(result) + b"\n")
        _write(staging / VERIFICATION_FILE, canonical_census_bytes(verification) + b"\n")
        staging.chmod(0o700)
        for item in staging.iterdir(): item.chmod(0o400); _fsync_file(item)
        _fsync_directory(staging); staging.rename(target); _fsync_directory(root)
    except BaseException:
        if staging.exists() and not staging.is_symlink(): shutil.rmtree(staging)
        raise
    return replace(read_sec_cash_quality_security_applicability(package_path=target), status="published")


def read_sec_cash_quality_security_applicability(*, package_path: Path) -> SecurityApplicabilityCustodyResult:
    root = package_path.expanduser()
    if root.is_symlink(): raise SecCashQualitySecurityApplicabilityCustodyError("applicability package unsafe")
    root = root.resolve()
    if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise SecCashQualitySecurityApplicabilityCustodyError("applicability custody differs")
    if {item.name for item in root.iterdir()} != {PLAN_FILE, RESULT_FILE, VERIFICATION_FILE}:
        raise SecCashQualitySecurityApplicabilityCustodyError("applicability inventory differs")
    plan = _read(root / PLAN_FILE, SecCashQualitySecurityApplicabilityPlanV1)
    result = _read(root / RESULT_FILE, SecCashQualitySecurityApplicabilityResultV1)
    verification = _read(root / VERIFICATION_FILE, SecCashQualitySecurityApplicabilityVerificationV1)
    _validate(plan, result, verification)
    if root.name != f"verification={verification.logical_fingerprint}":
        raise SecCashQualitySecurityApplicabilityCustodyError("applicability identity differs")
    return SecurityApplicabilityCustodyResult(plan, result, verification, root, "exact_reread_complete")


def _validate(plan, result, verification):
    if (
        result.plan_fingerprint != plan.logical_fingerprint
        or verification.plan_fingerprint != plan.logical_fingerprint
        or verification.forward_result_fingerprint != result.logical_fingerprint
    ):
        raise SecCashQualitySecurityApplicabilityCustodyError("applicability binding differs")


def _bind_file(path, binding, require_owner_only=True):
    path = path.expanduser().resolve()
    if (
        path.is_symlink() or not path.is_file()
        or path.stat().st_size != binding.byte_size
        or _file_sha(path) != binding.physical_sha256
        or (require_owner_only and stat.S_IMODE(path.stat().st_mode) != 0o400)
    ):
        raise SecCashQualitySecurityApplicabilityCustodyError("applicability artifact binding differs")


def _read(path, model):
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise SecCashQualitySecurityApplicabilityCustodyError("applicability JSON custody differs")
    raw=path.read_bytes(); value=model.model_validate_json(raw)
    if raw != canonical_census_bytes(value)+b"\n": raise SecCashQualitySecurityApplicabilityCustodyError("applicability JSON noncanonical")
    return value


def _file_sha(path):
    d=hashlib.sha256()
    with path.open("rb") as stream:
        while chunk:=stream.read(1024*1024): d.update(chunk)
    return d.hexdigest()


def _write(path,payload):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    with os.fdopen(fd,"wb") as stream: stream.write(payload);stream.flush();os.fsync(stream.fileno())


def _fsync_file(path):
    fd=os.open(path,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def _fsync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
