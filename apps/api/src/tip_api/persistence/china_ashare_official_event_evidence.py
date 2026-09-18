"""Owner-only immutable restart checkpoints for official-event evidence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from tip_api.contracts.china_ashare.v1.official_event_evidence import (
    ChinaAshareOfficialEventCaptureV1,
    ChinaAshareOfficialEventEvidencePlanV1,
)


PLAN_FILE = "official-event-evidence-plan.json"
CAPTURE_FILE = "capture.json"
RAW_FILE = "raw-response.bin"


def publish_official_event_evidence_plan(*, custody_root: Path, plan: ChinaAshareOfficialEventEvidencePlanV1) -> Path:
    requested = custody_root.expanduser()
    if requested.is_symlink():
        raise RuntimeError("official-event custody root cannot be a symlink")
    root = requested.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_directory(root, 0o700)
    target = root / f"plan={plan.logical_fingerprint}"
    if target.exists():
        reread = read_official_event_evidence_plan(plan_root=target)
        if reread != plan:
            raise RuntimeError("immutable official-event plan differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".official-event-plan-", dir=root))
    try:
        _write(staging / PLAN_FILE, _json_bytes(plan.model_dump(mode="json")))
        (staging / "captures").mkdir(mode=0o700)
        os.chmod(staging, 0o700)
        staging.rename(target)
    except BaseException:
        if staging.exists():
            for item in sorted(staging.rglob("*"), reverse=True):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            staging.rmdir()
        raise
    return target


def read_official_event_evidence_plan(*, plan_root: Path) -> ChinaAshareOfficialEventEvidencePlanV1:
    requested = plan_root.expanduser()
    if requested.is_symlink():
        raise RuntimeError("official-event plan root cannot be a symlink")
    root = requested.resolve()
    _require_directory(root, 0o700)
    if {item.name for item in root.iterdir()} != {PLAN_FILE, "captures"}:
        raise RuntimeError("official-event plan closed file set differs")
    _require_directory(root / "captures", 0o700)
    plan = ChinaAshareOfficialEventEvidencePlanV1.model_validate_json(_read(root / PLAN_FILE))
    if root.name != f"plan={plan.logical_fingerprint}":
        raise RuntimeError("official-event plan path differs")
    return plan


def completed_official_event_query_ids(*, plan_root: Path) -> tuple[str, ...]:
    plan = read_official_event_evidence_plan(plan_root=plan_root)
    completed = []
    for query in plan.queries:
        path = plan_root / "captures" / query.query_id
        if path.exists():
            read_official_event_capture(plan_root=plan_root, query_id=query.query_id)
            completed.append(query.query_id)
    return tuple(completed)


def publish_official_event_capture(*, plan_root: Path, capture: ChinaAshareOfficialEventCaptureV1, raw_bytes: bytes | None) -> Path:
    plan = read_official_event_evidence_plan(plan_root=plan_root)
    if capture.plan_fingerprint != plan.logical_fingerprint:
        raise RuntimeError("official-event capture plan binding differs")
    if capture.query_id not in {item.query_id for item in plan.queries}:
        raise RuntimeError("official-event capture query differs")
    if (raw_bytes is None) != (capture.raw_sha256 is None):
        raise RuntimeError("official-event raw bytes differ")
    target = plan_root / "captures" / capture.query_id
    if target.exists():
        reread, existing_raw = read_official_event_capture(plan_root=plan_root, query_id=capture.query_id)
        if reread != capture or existing_raw != raw_bytes:
            raise RuntimeError("immutable official-event capture differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=f".{capture.query_id}-", dir=plan_root / "captures"))
    try:
        if raw_bytes is not None:
            _write(staging / RAW_FILE, raw_bytes)
        _write(staging / CAPTURE_FILE, _json_bytes(capture.model_dump(mode="json")))
        os.chmod(staging, 0o700)
        staging.rename(target)
    except BaseException:
        for item in staging.iterdir():
            item.unlink()
        staging.rmdir()
        raise
    return target


def read_official_event_capture(*, plan_root: Path, query_id: str) -> tuple[ChinaAshareOfficialEventCaptureV1, bytes | None]:
    target = (plan_root / "captures" / query_id).resolve()
    _require_directory(target, 0o700)
    capture = ChinaAshareOfficialEventCaptureV1.model_validate_json(_read(target / CAPTURE_FILE))
    if capture.query_id != query_id:
        raise RuntimeError("official-event capture path differs")
    raw_path = target / RAW_FILE
    raw = _read(raw_path) if raw_path.exists() else None
    if raw is not None:
        import hashlib
        if hashlib.sha256(raw).hexdigest() != capture.raw_sha256 or len(raw) != capture.raw_byte_size:
            raise RuntimeError("official-event raw bytes changed")
    expected = {CAPTURE_FILE} | ({RAW_FILE} if raw is not None else set())
    if {item.name for item in target.iterdir()} != expected:
        raise RuntimeError("official-event closed file set differs")
    return capture, raw


def _write(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _read(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o777 != 0o400:
        raise RuntimeError("official-event evidence file is invalid")
    return path.read_bytes()


def _require_directory(path: Path, mode: int) -> None:
    if not path.is_dir() or path.is_symlink() or path.stat().st_mode & 0o777 != mode:
        raise RuntimeError("official-event evidence directory is invalid")


def _json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
