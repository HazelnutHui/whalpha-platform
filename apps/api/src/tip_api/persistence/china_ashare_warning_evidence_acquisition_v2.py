"""Append-only owner custody for pagination-aware warning acquisition V2."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition_v2 import (
    ChinaAshareWarningAcquisitionCensusV2,
    ChinaAshareWarningAcquisitionPlanV2,
    ChinaAshareWarningPageCaptureV2,
)


PLAN_FILE = "warning-acquisition-v2-plan.json"
CAPTURE_FILE = "capture.json"
RAW_FILE = "raw-response.bin"
MAX_BYTES = 32 * 1024 * 1024


def publish_v2_plan(*, custody_root: Path, plan: ChinaAshareWarningAcquisitionPlanV2) -> Path:
    root = _root(custody_root)
    parent = root / f"input={plan.input_reuse_package_fingerprint}"
    parent.mkdir(mode=0o700, exist_ok=True); parent.chmod(0o700)
    target = parent / f"plan={plan.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        if read_v2_plan(plan_root=target) != plan: raise RuntimeError("immutable warning V2 plan differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".warning-v2-", dir=parent))
    try:
        _write(staging / PLAN_FILE, _canonical(plan.model_dump(mode="json")))
        (staging / "captures").mkdir(mode=0o700); (staging / "censuses").mkdir(mode=0o700)
        os.chmod(staging, 0o700); _fsync_tree(staging); staging.rename(target); _fsync(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink(): shutil.rmtree(staging)
        raise
    return target


def read_v2_plan(*, plan_root: Path):
    root = _dir(plan_root)
    if {item.name for item in root.iterdir()} != {PLAN_FILE, "captures", "censuses"}: raise RuntimeError("warning V2 plan closed set differs")
    _dir(root / "captures"); _dir(root / "censuses")
    plan = ChinaAshareWarningAcquisitionPlanV2.model_validate_json(_read(root / PLAN_FILE))
    if root.name != f"plan={plan.logical_fingerprint}" or root.parent.name != f"input={plan.input_reuse_package_fingerprint}": raise RuntimeError("warning V2 plan path differs")
    return plan


def publish_v2_capture(*, plan_root: Path, capture: ChinaAshareWarningPageCaptureV2, raw_bytes: bytes | None):
    plan = read_v2_plan(plan_root=plan_root)
    if capture.plan_fingerprint != plan.logical_fingerprint: raise RuntimeError("warning V2 capture plan differs")
    if (raw_bytes is None) != (capture.raw_sha256 is None): raise RuntimeError("warning V2 raw binding differs")
    parent = plan_root / "captures" / capture.request_id / f"page={capture.page_number}"
    parent.mkdir(mode=0o700, parents=True, exist_ok=True); _chmod_dirs(plan_root / "captures", parent)
    target = parent / f"attempt={capture.attempt_number}"
    if target.exists() or target.is_symlink():
        if read_v2_capture(plan_root=plan_root, request_id=capture.request_id, page_number=capture.page_number, attempt_number=capture.attempt_number) != (capture, raw_bytes): raise RuntimeError("immutable warning V2 capture differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".attempt-", dir=parent))
    try:
        if raw_bytes is not None: _write(staging / RAW_FILE, raw_bytes)
        _write(staging / CAPTURE_FILE, _canonical(capture.model_dump(mode="json")))
        os.chmod(staging, 0o700); _fsync_tree(staging); staging.rename(target); _fsync(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink(): shutil.rmtree(staging)
        raise
    return target


def read_v2_capture(*, plan_root: Path, request_id: str, page_number: int, attempt_number: int):
    target = _dir(plan_root / "captures" / request_id / f"page={page_number}" / f"attempt={attempt_number}")
    capture = ChinaAshareWarningPageCaptureV2.model_validate_json(_read(target / CAPTURE_FILE))
    if (capture.request_id, capture.page_number, capture.attempt_number) != (request_id, page_number, attempt_number): raise RuntimeError("warning V2 capture path differs")
    raw_path = target / RAW_FILE; raw = _read(raw_path) if raw_path.exists() else None
    if raw is not None and (len(raw) != capture.raw_byte_size or hashlib.sha256(raw).hexdigest() != capture.raw_sha256): raise RuntimeError("warning V2 raw bytes changed")
    if {item.name for item in target.iterdir()} != ({CAPTURE_FILE} | ({RAW_FILE} if raw is not None else set())): raise RuntimeError("warning V2 capture closed set differs")
    return capture, raw


def read_all_v2_captures(*, plan_root: Path):
    read_v2_plan(plan_root=plan_root); captures = []
    for request_dir in sorted((plan_root / "captures").iterdir()):
        _dir(request_dir)
        for page_dir in sorted(request_dir.iterdir()):
            _dir(page_dir); page = int(page_dir.name.split("=", 1)[1])
            for attempt_dir in sorted(page_dir.iterdir()):
                attempt = int(attempt_dir.name.split("=", 1)[1])
                capture, _ = read_v2_capture(plan_root=plan_root, request_id=request_dir.name, page_number=page, attempt_number=attempt); captures.append(capture)
    return tuple(captures)


def publish_v2_census(*, plan_root: Path, census: ChinaAshareWarningAcquisitionCensusV2):
    plan = read_v2_plan(plan_root=plan_root)
    if census.plan_fingerprint != plan.logical_fingerprint: raise RuntimeError("warning V2 census plan differs")
    target = plan_root / "censuses" / f"census={census.logical_fingerprint}.json"; payload = _canonical(census.model_dump(mode="json"))
    if target.exists() or target.is_symlink():
        if _read(target) != payload: raise RuntimeError("immutable warning V2 census differs")
        return target
    _write(target, payload); _fsync(target.parent); return target


def read_v2_census(*, plan_root: Path, census_fingerprint: str):
    plan = read_v2_plan(plan_root=plan_root); census = ChinaAshareWarningAcquisitionCensusV2.model_validate_json(_read(plan_root / "censuses" / f"census={census_fingerprint}.json"))
    if census.logical_fingerprint != census_fingerprint or census.plan_fingerprint != plan.logical_fingerprint: raise RuntimeError("warning V2 census binding differs")
    return census


def _root(path):
    candidate = path.expanduser()
    if candidate.is_symlink(): raise RuntimeError("warning V2 root unsafe")
    root = candidate.resolve()
    if root == Path("/"): raise RuntimeError("warning V2 root unsafe")
    root.mkdir(mode=0o700, parents=True, exist_ok=True); root.chmod(0o700); return root


def _dir(path):
    if path.is_symlink(): raise RuntimeError("warning V2 directory unsafe")
    root = path.resolve()
    if not root.is_dir() or root.is_symlink() or root.stat().st_mode & 0o777 != 0o700: raise RuntimeError("warning V2 directory invalid")
    return root


def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o400: raise RuntimeError("warning V2 file unsafe")
    if not 0 < path.stat().st_size <= MAX_BYTES: raise RuntimeError("warning V2 file size differs")
    return path.read_bytes()


def _write(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, "wb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())


def _canonical(value): return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _chmod_dirs(root, target):
    current = target
    while True:
        os.chmod(current, 0o700)
        if current == root: break
        current = current.parent


def _fsync_tree(root):
    for directory, _, _ in os.walk(root, topdown=False): _fsync(Path(directory))


def _fsync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
