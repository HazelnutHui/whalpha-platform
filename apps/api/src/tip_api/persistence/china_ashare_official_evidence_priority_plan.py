"""Owner-only immutable custody for an offline official-evidence priority plan."""

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

from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidencePriorityPackageManifestV1,
    ChinaAshareOfficialEvidencePriorityPlanV1,
    build_official_evidence_priority_package_manifest,
)


PLAN_FILE = "official-evidence-priority-plan.json"
MANIFEST_FILE = "official-evidence-priority-manifest.json"
MAXIMUM_FILE_BYTES = 32 * 1024 * 1024


class ChinaAshareOfficialEvidencePriorityPackageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareOfficialEvidencePriorityPackageResultV1:
    manifest: ChinaAshareOfficialEvidencePriorityPackageManifestV1
    plan: ChinaAshareOfficialEvidencePriorityPlanV1
    package_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_official_evidence_priority_plan(
    *, custody_root: Path, plan: ChinaAshareOfficialEvidencePriorityPlanV1
) -> ChinaAshareOfficialEvidencePriorityPackageResultV1:
    root = _root(custody_root)
    parent = root / f"input={plan.input_package_fingerprint}"
    parent.mkdir(mode=0o700, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority input scope is unsafe"
        )
    parent.chmod(0o700)
    plan_payload = _canonical(plan.model_dump(mode="json"))
    manifest = build_official_evidence_priority_package_manifest(
        input_package_fingerprint=plan.input_package_fingerprint,
        plan_fingerprint=plan.logical_fingerprint,
        plan_byte_size=len(plan_payload),
        plan_physical_sha256=_sha(plan_payload),
        request_count=len(plan.requests),
        network_execution_authorized=False,
        outcome_read_count=0,
        research_backtest_authorized=False,
        product_publication_authorized=False,
    )
    target = parent / f"plan={manifest.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_china_ashare_official_evidence_priority_plan(
            package_path=target
        )
        if existing.plan != plan or existing.manifest != manifest:
            raise ChinaAshareOfficialEvidencePriorityPackageError(
                "existing official evidence priority package differs"
            )
        return replace(existing, status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".official-evidence-priority-", dir=parent))
    try:
        _write(staging / PLAN_FILE, plan_payload)
        _write(staging / MANIFEST_FILE, _canonical(manifest.model_dump(mode="json")))
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_official_evidence_priority_plan(package_path=target),
        status="published",
    )


def read_china_ashare_official_evidence_priority_plan(
    *, package_path: Path
) -> ChinaAshareOfficialEvidencePriorityPackageResultV1:
    root = _package(package_path)
    plan_payload = _read(root / PLAN_FILE)
    manifest_payload = _read(root / MANIFEST_FILE)
    try:
        plan = ChinaAshareOfficialEvidencePriorityPlanV1.model_validate_json(
            plan_payload
        )
        manifest = (
            ChinaAshareOfficialEvidencePriorityPackageManifestV1.model_validate_json(
                manifest_payload
            )
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority package is invalid"
        ) from exc
    if (
        root.name != f"plan={manifest.logical_fingerprint}"
        or root.parent.name != f"input={plan.input_package_fingerprint}"
        or manifest.input_package_fingerprint != plan.input_package_fingerprint
        or manifest.plan_fingerprint != plan.logical_fingerprint
        or manifest.plan_byte_size != len(plan_payload)
        or manifest.plan_physical_sha256 != _sha(plan_payload)
        or manifest.request_count != len(plan.requests)
        or plan_payload != _canonical(plan.model_dump(mode="json"))
        or manifest_payload != _canonical(manifest.model_dump(mode="json"))
    ):
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority package binding differs"
        )
    actual = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
        if item.is_file()
    }
    if actual != {PLAN_FILE, MANIFEST_FILE} or any(
        item.is_symlink() for item in root.rglob("*")
    ):
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority closed file set differs"
        )
    return ChinaAshareOfficialEvidencePriorityPackageResultV1(
        manifest=manifest,
        plan=plan,
        package_path=root,
        manifest_physical_sha256=_sha(manifest_payload),
        file_count=2,
        total_bytes=len(plan_payload) + len(manifest_payload),
        status="exact_reread_complete",
    )


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority custody root is unsafe"
        )
    root = candidate.resolve()
    if root == Path("/"):
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority custody root is unsafe"
        )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    return root


def _package(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority package path is unsafe"
        )
    root = candidate.resolve()
    if (
        not root.is_dir()
        or root.is_symlink()
        or (root.stat().st_mode & 0o777) != 0o700
    ):
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority package path is invalid"
        )
    return root


def _read(path: Path) -> bytes:
    if (
        path.is_symlink()
        or not path.is_file()
        or (path.stat().st_mode & 0o777) != 0o400
    ):
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority file is unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAshareOfficialEvidencePriorityPackageError(
            "official evidence priority file size is invalid"
        )
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
