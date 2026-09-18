"""Owner-only, atomic, closed-set custody for the offline reuse census."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from tip_api.contracts.china_ashare.v1.official_evidence_reuse import (
    ChinaAshareLocalEvidenceInventoryV1,
    ChinaAshareOfficialEvidenceReuseCensusV1,
    ChinaAshareOfficialEvidenceReusePackageManifestV1,
    ChinaAshareWarningEvidenceBatchManifestV1,
    build_contract,
)


INVENTORY_FILE = "local-official-evidence-inventory.json"
CENSUS_FILE = "official-evidence-reuse-census.json"
WARNING_FILE = "warning-acquisition-batch.json"
MANIFEST_FILE = "official-evidence-reuse-manifest.json"
PAYLOAD_FILES = (CENSUS_FILE, INVENTORY_FILE, WARNING_FILE)
MAX_FILE_BYTES = 64 * 1024 * 1024


class ChinaAshareOfficialEvidenceReusePackageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareOfficialEvidenceReusePackageResultV1:
    inventory: ChinaAshareLocalEvidenceInventoryV1
    census: ChinaAshareOfficialEvidenceReuseCensusV1
    warning_batch: ChinaAshareWarningEvidenceBatchManifestV1
    manifest: ChinaAshareOfficialEvidenceReusePackageManifestV1
    package_path: Path
    manifest_physical_sha256: str
    file_count: int
    total_bytes: int
    status: str


def publish_china_ashare_official_evidence_reuse_package(*, custody_root: Path, inventory, census, warning_batch) -> ChinaAshareOfficialEvidenceReusePackageResultV1:
    root = _root(custody_root)
    parent = root / f"input={census.input_priority_plan_package_fingerprint}"
    parent.mkdir(mode=0o700, exist_ok=True)
    parent.chmod(0o700)
    payloads = {
        INVENTORY_FILE: _canonical(inventory.model_dump(mode="json")),
        CENSUS_FILE: _canonical(census.model_dump(mode="json")),
        WARNING_FILE: _canonical(warning_batch.model_dump(mode="json")),
    }
    files = tuple((name, len(payloads[name]), _sha(payloads[name])) for name in sorted(payloads))
    manifest = build_contract(
        ChinaAshareOfficialEvidenceReusePackageManifestV1,
        input_priority_plan_package_fingerprint=census.input_priority_plan_package_fingerprint,
        inventory_fingerprint=inventory.logical_fingerprint,
        census_fingerprint=census.logical_fingerprint,
        warning_batch_fingerprint=warning_batch.logical_fingerprint,
        files=files,
    )
    target = parent / f"package={manifest.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_china_ashare_official_evidence_reuse_package(package_path=target)
        if (existing.inventory, existing.census, existing.warning_batch, existing.manifest) != (inventory, census, warning_batch, manifest):
            raise ChinaAshareOfficialEvidenceReusePackageError("existing reuse package differs")
        return replace(existing, status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".official-evidence-reuse-", dir=parent))
    try:
        for name, payload in payloads.items():
            _write(staging / name, payload)
        _write(staging / MANIFEST_FILE, _canonical(manifest.model_dump(mode="json")))
        _owner_only(staging)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(read_china_ashare_official_evidence_reuse_package(package_path=target), status="published")


def read_china_ashare_official_evidence_reuse_package(*, package_path: Path) -> ChinaAshareOfficialEvidenceReusePackageResultV1:
    root = _package(package_path)
    actual = {item.relative_to(root).as_posix() for item in root.rglob("*") if item.is_file()}
    expected = set(PAYLOAD_FILES) | {MANIFEST_FILE}
    if actual != expected or any(item.is_symlink() for item in root.rglob("*")):
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse package closed file set differs")
    raw = {name: _read(root / name) for name in expected}
    inventory = ChinaAshareLocalEvidenceInventoryV1.model_validate_json(raw[INVENTORY_FILE])
    census = ChinaAshareOfficialEvidenceReuseCensusV1.model_validate_json(raw[CENSUS_FILE])
    warning = ChinaAshareWarningEvidenceBatchManifestV1.model_validate_json(raw[WARNING_FILE])
    manifest = ChinaAshareOfficialEvidenceReusePackageManifestV1.model_validate_json(raw[MANIFEST_FILE])
    files = tuple((name, len(raw[name]), _sha(raw[name])) for name in sorted(PAYLOAD_FILES))
    if (
        root.name != f"package={manifest.logical_fingerprint}"
        or root.parent.name != f"input={census.input_priority_plan_package_fingerprint}"
        or manifest.input_priority_plan_package_fingerprint != census.input_priority_plan_package_fingerprint
        or manifest.inventory_fingerprint != inventory.logical_fingerprint
        or manifest.census_fingerprint != census.logical_fingerprint
        or manifest.warning_batch_fingerprint != warning.logical_fingerprint
        or census.local_evidence_inventory_fingerprint != inventory.logical_fingerprint
        or warning.input_reuse_census_fingerprint != census.logical_fingerprint
        or manifest.files != files
        or any(raw[name] != _canonical(obj.model_dump(mode="json")) for name, obj in (
            (INVENTORY_FILE, inventory), (CENSUS_FILE, census), (WARNING_FILE, warning), (MANIFEST_FILE, manifest)
        ))
    ):
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse package binding differs")
    return ChinaAshareOfficialEvidenceReusePackageResultV1(
        inventory=inventory, census=census, warning_batch=warning, manifest=manifest,
        package_path=root, manifest_physical_sha256=_sha(raw[MANIFEST_FILE]),
        file_count=4, total_bytes=sum(len(item) for item in raw.values()), status="exact_reread_complete",
    )


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse custody root is unsafe")
    root = candidate.resolve()
    if root == Path("/"):
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse custody root is unsafe")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    return root


def _package(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse package is unsafe")
    root = candidate.resolve()
    if not root.is_dir() or root.is_symlink() or root.stat().st_mode & 0o777 != 0o700:
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse package is invalid")
    return root


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o400:
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse file is unsafe")
    size = path.stat().st_size
    if size <= 0 or size > MAX_FILE_BYTES:
        raise ChinaAshareOfficialEvidenceReusePackageError("reuse file size is invalid")
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, "wb") as stream:
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
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
