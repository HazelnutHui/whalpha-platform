"""Immutable owner-only custody for SEC cash-quality readiness evidence."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    SecCashQualitySourceReadinessCensusV1,
    SecCashQualitySourceReadinessPlanV1,
    SecCashQualitySourceReadinessVerificationV1,
    canonical_census_bytes,
)


PLAN_FILE = "plan.json"
RESULT_FILE = "result.json"
VERIFICATION_FILE = "forward-reverse-verification.json"
MAXIMUM_DOCUMENT_BYTES = 4 * 1024 * 1024


class SecCashQualitySourceReadinessCustodyError(RuntimeError):
    """Raised when readiness evidence custody cannot be proven."""


@dataclass(frozen=True, slots=True)
class SecCashQualitySourceReadinessCustodyResultV1:
    plan: SecCashQualitySourceReadinessPlanV1
    result: SecCashQualitySourceReadinessCensusV1
    verification: SecCashQualitySourceReadinessVerificationV1
    package_path: Path
    status: str


def publish_sec_cash_quality_source_readiness(
    *,
    custody_root: Path,
    plan: SecCashQualitySourceReadinessPlanV1,
    result: SecCashQualitySourceReadinessCensusV1,
    verification: SecCashQualitySourceReadinessVerificationV1,
) -> SecCashQualitySourceReadinessCustodyResultV1:
    """Atomically publish one immutable three-document evidence package."""

    _validate_bindings(plan=plan, result=result, verification=verification)
    parent = _ensure_directory(custody_root.expanduser().resolve())
    target = parent / f"verification={verification.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_sec_cash_quality_source_readiness(package_path=target)
        if (
            existing.plan != plan
            or existing.result != result
            or existing.verification != verification
        ):
            raise SecCashQualitySourceReadinessCustodyError(
                "existing cash-quality readiness package differs"
            )
        return replace(existing, status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".readiness-", dir=parent))
    try:
        _write(staging / PLAN_FILE, _canonical(plan))
        _write(staging / RESULT_FILE, _canonical(result))
        _write(staging / VERIFICATION_FILE, _canonical(verification))
        _owner_only(staging)
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_sec_cash_quality_source_readiness(package_path=target),
        status="published",
    )


def read_sec_cash_quality_source_readiness(
    *, package_path: Path
) -> SecCashQualitySourceReadinessCustodyResultV1:
    """Exactly reread one owner-only closed-set evidence package."""

    root = _validate_package(package_path)
    expected = {PLAN_FILE, RESULT_FILE, VERIFICATION_FILE}
    if {item.name for item in root.iterdir()} != expected:
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness package inventory differs"
        )
    plan = _parse(root / PLAN_FILE, SecCashQualitySourceReadinessPlanV1)
    result = _parse(root / RESULT_FILE, SecCashQualitySourceReadinessCensusV1)
    verification = _parse(
        root / VERIFICATION_FILE,
        SecCashQualitySourceReadinessVerificationV1,
    )
    _validate_bindings(plan=plan, result=result, verification=verification)
    if root.name != f"verification={verification.logical_fingerprint}":
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness package identity differs"
        )
    return SecCashQualitySourceReadinessCustodyResultV1(
        plan=plan,
        result=result,
        verification=verification,
        package_path=root,
        status="exact_reread_complete",
    )


def _validate_bindings(
    *,
    plan: SecCashQualitySourceReadinessPlanV1,
    result: SecCashQualitySourceReadinessCensusV1,
    verification: SecCashQualitySourceReadinessVerificationV1,
) -> None:
    result_sha = hashlib.sha256(canonical_census_bytes(result)).hexdigest()
    if (
        result.plan_fingerprint != plan.logical_fingerprint
        or result.normalized_manifest_fingerprint
        != plan.normalized_manifest_fingerprint
        or result.query_registry_fingerprint != plan.query_registry_fingerprint
        or verification.plan_fingerprint != plan.logical_fingerprint
        or verification.primary_result_fingerprint != result.logical_fingerprint
        or verification.replay_result_fingerprint != result.logical_fingerprint
        or verification.primary_canonical_sha256 != result_sha
        or verification.replay_canonical_sha256 != result_sha
    ):
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness evidence binding differs"
        )


def _canonical(value: object) -> bytes:
    return canonical_census_bytes(value) + b"\n"


def _parse(path: Path, model: type):
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_DOCUMENT_BYTES
    ):
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness document custody differs"
        )
    payload = path.read_bytes()
    try:
        value = model.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness document is invalid"
        ) from exc
    if payload != _canonical(value):
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness document bytes are not canonical"
        )
    return value


def _ensure_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        path.is_symlink()
        or not path.is_dir()
        or path.stat().st_uid != os.getuid()
    ):
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness custody root is invalid"
        )
    path.chmod(0o700)
    return path


def _validate_package(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness package cannot be a symlink"
        )
    root = candidate.resolve()
    if (
        not root.is_dir()
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
    ):
        raise SecCashQualitySourceReadinessCustodyError(
            "cash-quality readiness package custody differs"
        )
    return root


def _write(path: Path, payload: bytes) -> None:
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
