"""Owner-only restartable custody for the frozen warning acquisition batch."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import (
    ChinaAshareWarningAcquisitionCaptureV1,
    ChinaAshareWarningAcquisitionCensusV1,
    ChinaAshareWarningAcquisitionPlanV1,
)


PLAN_FILE = "warning-acquisition-plan.json"
CAPTURE_FILE = "capture.json"
RAW_FILE = "raw-response.bin"
MAX_FILE_BYTES = 32 * 1024 * 1024


def publish_warning_acquisition_plan(*, custody_root: Path, plan: ChinaAshareWarningAcquisitionPlanV1) -> Path:
    root = _root(custody_root)
    parent = root / f"input={plan.input_reuse_package_fingerprint}" / f"batch={plan.input_warning_batch_fingerprint}"
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _owner_parent_chain(root, parent)
    target = parent / f"plan={plan.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        if read_warning_acquisition_plan(plan_root=target) != plan:
            raise RuntimeError("immutable warning acquisition plan differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".warning-acquisition-", dir=parent))
    try:
        _write(staging / PLAN_FILE, _canonical(plan.model_dump(mode="json")))
        (staging / "captures").mkdir(mode=0o700)
        (staging / "censuses").mkdir(mode=0o700)
        os.chmod(staging, 0o700)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return target


def read_warning_acquisition_plan(*, plan_root: Path) -> ChinaAshareWarningAcquisitionPlanV1:
    root = _directory(plan_root, 0o700)
    if {item.name for item in root.iterdir()} != {PLAN_FILE, "captures", "censuses"}:
        raise RuntimeError("warning acquisition plan closed set differs")
    _directory(root / "captures", 0o700)
    _directory(root / "censuses", 0o700)
    plan = ChinaAshareWarningAcquisitionPlanV1.model_validate_json(_read(root / PLAN_FILE))
    if root.name != f"plan={plan.logical_fingerprint}" or root.parent.name != f"batch={plan.input_warning_batch_fingerprint}" or root.parent.parent.name != f"input={plan.input_reuse_package_fingerprint}":
        raise RuntimeError("warning acquisition plan path differs")
    return plan


def publish_warning_acquisition_capture(*, plan_root: Path, capture: ChinaAshareWarningAcquisitionCaptureV1, raw_bytes: bytes | None) -> Path:
    plan = read_warning_acquisition_plan(plan_root=plan_root)
    if capture.plan_fingerprint != plan.logical_fingerprint or capture.warning_batch_fingerprint != plan.input_warning_batch_fingerprint:
        raise RuntimeError("warning capture plan binding differs")
    if (raw_bytes is None) != (capture.raw_sha256 is None):
        raise RuntimeError("warning capture raw binding differs")
    target_parent = plan_root / "captures" / capture.request_id
    target_parent.mkdir(mode=0o700, exist_ok=True)
    os.chmod(target_parent, 0o700)
    target = target_parent / f"attempt={capture.attempt_number}"
    if target.exists() or target.is_symlink():
        if read_warning_acquisition_capture(plan_root=plan_root, request_id=capture.request_id, attempt_number=capture.attempt_number) != (capture, raw_bytes):
            raise RuntimeError("immutable warning capture differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".attempt-", dir=target_parent))
    try:
        if raw_bytes is not None:
            _write(staging / RAW_FILE, raw_bytes)
        _write(staging / CAPTURE_FILE, _canonical(capture.model_dump(mode="json")))
        os.chmod(staging, 0o700)
        _fsync_tree(staging)
        staging.rename(target)
        _fsync_directory(target_parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return target


def read_warning_acquisition_capture(*, plan_root: Path, request_id: str, attempt_number: int):
    target = _directory(plan_root / "captures" / request_id / f"attempt={attempt_number}", 0o700)
    capture = ChinaAshareWarningAcquisitionCaptureV1.model_validate_json(_read(target / CAPTURE_FILE))
    if capture.request_id != request_id or capture.attempt_number != attempt_number:
        raise RuntimeError("warning capture path differs")
    raw_path = target / RAW_FILE
    raw = _read(raw_path) if raw_path.exists() else None
    if raw is not None and (len(raw) != capture.raw_byte_size or hashlib.sha256(raw).hexdigest() != capture.raw_sha256):
        raise RuntimeError("warning capture raw bytes changed")
    expected = {CAPTURE_FILE} | ({RAW_FILE} if raw is not None else set())
    if {item.name for item in target.iterdir()} != expected:
        raise RuntimeError("warning capture closed set differs")
    return capture, raw


def read_all_warning_acquisition_captures(*, plan_root: Path):
    plan = read_warning_acquisition_plan(plan_root=plan_root)
    captures = []
    root = plan_root / "captures"
    for request_dir in sorted(root.iterdir(), key=lambda item: item.name):
        _directory(request_dir, 0o700)
        for attempt_dir in sorted(request_dir.iterdir(), key=lambda item: item.name):
            if not attempt_dir.name.startswith("attempt="):
                raise RuntimeError("warning attempt path differs")
            attempt = int(attempt_dir.name.split("=", 1)[1])
            capture, _ = read_warning_acquisition_capture(plan_root=plan_root, request_id=request_dir.name, attempt_number=attempt)
            if capture.plan_fingerprint != plan.logical_fingerprint:
                raise RuntimeError("warning capture collection differs")
            captures.append(capture)
    return tuple(captures)


def publish_warning_acquisition_census(*, plan_root: Path, census: ChinaAshareWarningAcquisitionCensusV1) -> Path:
    plan = read_warning_acquisition_plan(plan_root=plan_root)
    if census.plan_fingerprint != plan.logical_fingerprint:
        raise RuntimeError("warning census plan binding differs")
    target = plan_root / "censuses" / f"census={census.logical_fingerprint}.json"
    payload = _canonical(census.model_dump(mode="json"))
    if target.exists() or target.is_symlink():
        if _read(target) != payload:
            raise RuntimeError("immutable warning census differs")
        return target
    _write(target, payload)
    _fsync_directory(target.parent)
    return target


def read_warning_acquisition_census(*, plan_root: Path, census_fingerprint: str):
    plan = read_warning_acquisition_plan(plan_root=plan_root)
    path = plan_root / "censuses" / f"census={census_fingerprint}.json"
    census = ChinaAshareWarningAcquisitionCensusV1.model_validate_json(_read(path))
    if census.logical_fingerprint != census_fingerprint or census.plan_fingerprint != plan.logical_fingerprint:
        raise RuntimeError("warning census binding differs")
    return census


def _root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise RuntimeError("warning acquisition custody root is unsafe")
    root = candidate.resolve()
    if root == Path("/"):
        raise RuntimeError("warning acquisition custody root is unsafe")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


def _directory(path: Path, mode: int) -> Path:
    if path.is_symlink():
        raise RuntimeError("warning acquisition directory is unsafe")
    root = path.resolve()
    if not root.is_dir() or root.is_symlink() or root.stat().st_mode & 0o777 != mode:
        raise RuntimeError("warning acquisition directory is invalid")
    return root


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o400:
        raise RuntimeError("warning acquisition file is unsafe")
    size = path.stat().st_size
    if size <= 0 or size > MAX_FILE_BYTES:
        raise RuntimeError("warning acquisition file size differs")
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _owner_parent_chain(root: Path, target: Path) -> None:
    current = target
    while current != root.parent:
        os.chmod(current, 0o700)
        if current == root:
            break
        current = current.parent


def _fsync_tree(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        _fsync_directory(Path(directory))


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
