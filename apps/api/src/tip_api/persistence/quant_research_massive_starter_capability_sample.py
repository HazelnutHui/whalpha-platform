"""Atomic owner-only custody for the Massive Starter capability sample."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1.quant_research_massive_starter_capability_sample import (
    MassiveStarterCapabilitySamplePlanV1,
    MassiveStarterCapabilitySampleResultV1,
    MassiveStarterCapabilitySampleVerificationV1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


class MassiveStarterCapabilitySampleCustodyError(RuntimeError):
    pass


@dataclass(frozen=True)
class MassiveStarterCapabilitySamplePackage:
    package_path: Path
    plan: MassiveStarterCapabilitySamplePlanV1
    result: MassiveStarterCapabilitySampleResultV1
    verification: MassiveStarterCapabilitySampleVerificationV1


def publish_massive_starter_capability_sample(
    *,
    custody_root: Path,
    plan: MassiveStarterCapabilitySamplePlanV1,
    result: MassiveStarterCapabilitySampleResultV1,
    sanitized_responses: dict[int, object],
) -> MassiveStarterCapabilitySamplePackage:
    if result.plan_fingerprint != plan.logical_fingerprint:
        raise MassiveStarterCapabilitySampleCustodyError("sample plan/result binding differs")
    root = custody_root.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    staging = root / f".staging-{uuid4().hex}"
    staging.mkdir(mode=0o700)
    try:
        _write_json(staging / "sample-plan.json", plan.model_dump(mode="json"))
        _write_json(staging / "sample-result.json", result.model_dump(mode="json"))
        raw = staging / "raw"
        raw.mkdir(mode=0o700)
        for sequence, response in sorted(sanitized_responses.items()):
            _write_json(raw / f"request-{sequence:02d}.json", response)
        schemas = {
            f"request-{item.sequence:02d}": list(item.schema_paths)
            for item in result.request_outcomes
        }
        _write_json(staging / "response-schemas.json", schemas)
        bound = tuple(sorted(path for path in staging.rglob("*") if path.is_file()))
        values = {
            "plan_fingerprint": plan.logical_fingerprint,
            "result_fingerprint": result.logical_fingerprint,
            "retained_file_count": len(bound),
            "retained_byte_count": sum(path.stat().st_size for path in bound),
        }
        provisional = MassiveStarterCapabilitySampleVerificationV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
        verification = MassiveStarterCapabilitySampleVerificationV1.model_validate(
            {**values, "logical_fingerprint": census_fingerprint(provisional)}
        )
        _write_json(
            staging / "exact-reread-verification.json",
            verification.model_dump(mode="json"),
        )
        _make_owner_only(staging)
        target = root / f"verification={verification.logical_fingerprint}"
        if target.exists():
            raise MassiveStarterCapabilitySampleCustodyError("sample package already exists")
        os.replace(staging, target)
        _fsync_directory(root)
        return read_massive_starter_capability_sample(package_path=target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def read_massive_starter_capability_sample(
    *, package_path: Path
) -> MassiveStarterCapabilitySamplePackage:
    path = package_path.expanduser().resolve()
    _require_owner_only(path)
    plan = MassiveStarterCapabilitySamplePlanV1.model_validate(_read_json(path / "sample-plan.json"))
    result = MassiveStarterCapabilitySampleResultV1.model_validate(_read_json(path / "sample-result.json"))
    verification = MassiveStarterCapabilitySampleVerificationV1.model_validate(
        _read_json(path / "exact-reread-verification.json")
    )
    if path.name != f"verification={verification.logical_fingerprint}":
        raise MassiveStarterCapabilitySampleCustodyError("sample package path differs")
    if verification.plan_fingerprint != plan.logical_fingerprint or verification.result_fingerprint != result.logical_fingerprint:
        raise MassiveStarterCapabilitySampleCustodyError("sample verification bindings differ")
    bound = tuple(
        sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and item.name != "exact-reread-verification.json"
        )
    )
    if len(bound) != verification.retained_file_count or sum(item.stat().st_size for item in bound) != verification.retained_byte_count:
        raise MassiveStarterCapabilitySampleCustodyError("sample retained inventory differs")
    schemas = _read_json(path / "response-schemas.json")
    for outcome in result.request_outcomes:
        raw_path = path / "raw" / f"request-{outcome.sequence:02d}.json"
        payload = _read_json(raw_path)
        encoded = _canonical_bytes(payload)
        if hashlib.sha256(encoded).hexdigest() != outcome.sanitized_response_sha256 or len(encoded) != outcome.sanitized_response_byte_size:
            raise MassiveStarterCapabilitySampleCustodyError("sample raw response differs")
        if schemas.get(f"request-{outcome.sequence:02d}") != list(outcome.schema_paths):
            raise MassiveStarterCapabilitySampleCustodyError("sample response schema differs")
    return MassiveStarterCapabilitySamplePackage(
        package_path=path,
        plan=plan,
        result=result,
        verification=verification,
    )


def _write_json(path: Path, value: object) -> None:
    encoded = _canonical_bytes(value)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_bytes())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise MassiveStarterCapabilitySampleCustodyError("sample JSON is unavailable") from exc
    if not isinstance(value, dict):
        raise MassiveStarterCapabilitySampleCustodyError("sample JSON is not an object")
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _make_owner_only(path: Path) -> None:
    for item in path.rglob("*"):
        item.chmod(0o700 if item.is_dir() else 0o600)
    path.chmod(0o700)


def _require_owner_only(path: Path) -> None:
    if not path.is_dir() or path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise MassiveStarterCapabilitySampleCustodyError("sample package is not owner-only")
    for item in path.rglob("*"):
        if item.is_symlink() or item.stat().st_uid != os.getuid() or item.stat().st_mode & 0o077:
            raise MassiveStarterCapabilitySampleCustodyError("sample member is not owner-only")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
