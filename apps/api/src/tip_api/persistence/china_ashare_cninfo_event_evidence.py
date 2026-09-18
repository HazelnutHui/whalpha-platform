"""Owner-only immutable custody for the bounded CNINFO event sample."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from tip_api.contracts.china_ashare.v1.cninfo_event_evidence import (
    ChinaAshareCninfoCaptureV1,
    ChinaAshareCninfoEventPlanV1,
)


PLAN_FILE = "cninfo-event-plan.json"
CAPTURE_FILE = "capture.json"
RAW_FILE = "raw-response.bin"


def publish_cninfo_event_plan(
    *, custody_root: Path, plan: ChinaAshareCninfoEventPlanV1
) -> Path:
    requested = custody_root.expanduser()
    if requested.is_symlink():
        raise RuntimeError("CNINFO custody root cannot be a symlink")
    root = requested.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_directory(root, 0o700)
    target = root / f"plan={plan.logical_fingerprint}"
    if target.exists():
        if read_cninfo_event_plan(plan_root=target) != plan:
            raise RuntimeError("immutable CNINFO event plan differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".cninfo-plan-", dir=root))
    try:
        _write(staging / PLAN_FILE, _json_bytes(plan.model_dump(mode="json")))
        (staging / "captures").mkdir(mode=0o700)
        os.chmod(staging, 0o700)
        staging.rename(target)
    except BaseException:
        _remove_staging(staging)
        raise
    return target


def read_cninfo_event_plan(*, plan_root: Path) -> ChinaAshareCninfoEventPlanV1:
    root = plan_root.expanduser()
    if root.is_symlink():
        raise RuntimeError("CNINFO plan root cannot be a symlink")
    root = root.resolve()
    _require_directory(root, 0o700)
    if {item.name for item in root.iterdir()} != {PLAN_FILE, "captures"}:
        raise RuntimeError("CNINFO plan closed file set differs")
    _require_directory(root / "captures", 0o700)
    plan = ChinaAshareCninfoEventPlanV1.model_validate_json(_read(root / PLAN_FILE))
    if root.name != f"plan={plan.logical_fingerprint}":
        raise RuntimeError("CNINFO plan path differs")
    return plan


def publish_cninfo_event_capture(
    *, plan_root: Path, capture: ChinaAshareCninfoCaptureV1, raw_bytes: bytes | None
) -> Path:
    plan = read_cninfo_event_plan(plan_root=plan_root)
    if capture.plan_fingerprint != plan.logical_fingerprint:
        raise RuntimeError("CNINFO capture plan binding differs")
    if capture.query_id not in {item.query_id for item in plan.queries}:
        raise RuntimeError("CNINFO capture query differs")
    if (raw_bytes is None) != (capture.raw_sha256 is None):
        raise RuntimeError("CNINFO raw bytes differ")
    target = plan_root / "captures" / capture.query_id
    if target.exists():
        if read_cninfo_event_capture(
            plan_root=plan_root, query_id=capture.query_id
        ) != (capture, raw_bytes):
            raise RuntimeError("immutable CNINFO capture differs")
        return target
    staging = Path(
        tempfile.mkdtemp(prefix=f".{capture.query_id}-", dir=plan_root / "captures")
    )
    try:
        if raw_bytes is not None:
            _write(staging / RAW_FILE, raw_bytes)
        _write(staging / CAPTURE_FILE, _json_bytes(capture.model_dump(mode="json")))
        os.chmod(staging, 0o700)
        staging.rename(target)
    except BaseException:
        _remove_staging(staging)
        raise
    return target


def read_cninfo_event_capture(
    *, plan_root: Path, query_id: str
) -> tuple[ChinaAshareCninfoCaptureV1, bytes | None]:
    target = (plan_root / "captures" / query_id).resolve()
    _require_directory(target, 0o700)
    capture = ChinaAshareCninfoCaptureV1.model_validate_json(
        _read(target / CAPTURE_FILE)
    )
    if capture.query_id != query_id:
        raise RuntimeError("CNINFO capture path differs")
    raw_path = target / RAW_FILE
    raw = _read(raw_path) if raw_path.exists() else None
    if raw is not None and (
        len(raw) != capture.raw_byte_size
        or hashlib.sha256(raw).hexdigest() != capture.raw_sha256
    ):
        raise RuntimeError("CNINFO raw bytes changed")
    expected = {CAPTURE_FILE} | ({RAW_FILE} if raw is not None else set())
    if {item.name for item in target.iterdir()} != expected:
        raise RuntimeError("CNINFO capture closed file set differs")
    return capture, raw


def _write(path: Path, payload: bytes) -> None:
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _read(path: Path) -> bytes:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_mode & 0o777 != 0o400
    ):
        raise RuntimeError("CNINFO evidence file is invalid")
    return path.read_bytes()


def _require_directory(path: Path, mode: int) -> None:
    if (
        not path.is_dir()
        or path.is_symlink()
        or path.stat().st_mode & 0o777 != mode
    ):
        raise RuntimeError("CNINFO evidence directory is invalid")


def _remove_staging(path: Path) -> None:
    if not path.exists():
        return
    for item in sorted(path.rglob("*"), reverse=True):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    path.rmdir()


def _json_bytes(value) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        + "\n"
    ).encode()
