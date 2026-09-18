"""Owner-only immutable custody for second-stage official documents."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from tip_api.contracts.china_ashare.v1.official_event_documents import (
    ChinaAshareOfficialEventDocumentCaptureV1,
    ChinaAshareOfficialEventDocumentPlanV1,
)


PLAN_FILE = "official-event-document-plan.json"
CAPTURE_FILE = "capture.json"
RAW_FILE = "official-document.pdf"
TEXT_FILE = "extracted-text.txt"


def publish_official_event_document_plan(
    *, custody_root: Path, plan: ChinaAshareOfficialEventDocumentPlanV1
) -> Path:
    requested = custody_root.expanduser()
    if requested.is_symlink():
        raise RuntimeError("official document custody root cannot be a symlink")
    root = requested.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_directory(root, 0o700)
    target = root / f"plan={plan.logical_fingerprint}"
    if target.exists():
        if read_official_event_document_plan(plan_root=target) != plan:
            raise RuntimeError("immutable official document plan differs")
        return target
    staging = Path(tempfile.mkdtemp(prefix=".official-doc-plan-", dir=root))
    try:
        _write(staging / PLAN_FILE, _json_bytes(plan.model_dump(mode="json")))
        (staging / "documents").mkdir(mode=0o700)
        os.chmod(staging, 0o700)
        staging.rename(target)
    except BaseException:
        _remove_staging(staging)
        raise
    return target


def read_official_event_document_plan(
    *, plan_root: Path
) -> ChinaAshareOfficialEventDocumentPlanV1:
    requested = plan_root.expanduser()
    if requested.is_symlink():
        raise RuntimeError("official document plan root cannot be a symlink")
    root = requested.resolve()
    _require_directory(root, 0o700)
    if {item.name for item in root.iterdir()} != {PLAN_FILE, "documents"}:
        raise RuntimeError("official document plan closed file set differs")
    _require_directory(root / "documents", 0o700)
    plan = ChinaAshareOfficialEventDocumentPlanV1.model_validate_json(
        _read(root / PLAN_FILE)
    )
    if root.name != f"plan={plan.logical_fingerprint}":
        raise RuntimeError("official document plan path differs")
    return plan


def publish_official_event_document_capture(
    *,
    plan_root: Path,
    capture: ChinaAshareOfficialEventDocumentCaptureV1,
    raw_bytes: bytes | None,
    text_bytes: bytes | None,
) -> Path:
    plan = read_official_event_document_plan(plan_root=plan_root)
    if capture.plan_fingerprint != plan.logical_fingerprint:
        raise RuntimeError("official document capture plan binding differs")
    if capture.document_id not in {item.document_id for item in plan.documents}:
        raise RuntimeError("official document capture ID differs")
    if (raw_bytes is None) != (capture.raw_sha256 is None):
        raise RuntimeError("official document raw bytes differ")
    if (text_bytes is None) != (capture.text_sha256 is None):
        raise RuntimeError("official document text bytes differ")
    target = plan_root / "documents" / capture.document_id
    if target.exists():
        reread = read_official_event_document_capture(
            plan_root=plan_root, document_id=capture.document_id
        )
        if reread != (capture, raw_bytes, text_bytes):
            raise RuntimeError("immutable official document capture differs")
        return target
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{capture.document_id}-", dir=plan_root / "documents"
        )
    )
    try:
        if raw_bytes is not None:
            _write(staging / RAW_FILE, raw_bytes)
        if text_bytes is not None:
            _write(staging / TEXT_FILE, text_bytes)
        _write(staging / CAPTURE_FILE, _json_bytes(capture.model_dump(mode="json")))
        os.chmod(staging, 0o700)
        staging.rename(target)
    except BaseException:
        _remove_staging(staging)
        raise
    return target


def read_official_event_document_capture(
    *, plan_root: Path, document_id: str
) -> tuple[ChinaAshareOfficialEventDocumentCaptureV1, bytes | None, bytes | None]:
    target = (plan_root / "documents" / document_id).resolve()
    _require_directory(target, 0o700)
    capture = ChinaAshareOfficialEventDocumentCaptureV1.model_validate_json(
        _read(target / CAPTURE_FILE)
    )
    if capture.document_id != document_id:
        raise RuntimeError("official document capture path differs")
    raw_path = target / RAW_FILE
    text_path = target / TEXT_FILE
    raw = _read(raw_path) if raw_path.exists() else None
    text = _read(text_path) if text_path.exists() else None
    if raw is not None and (
        len(raw) != capture.raw_byte_size
        or hashlib.sha256(raw).hexdigest() != capture.raw_sha256
    ):
        raise RuntimeError("official document raw bytes changed")
    if text is not None and (
        len(text) != capture.text_byte_size
        or hashlib.sha256(text).hexdigest() != capture.text_sha256
    ):
        raise RuntimeError("official document text bytes changed")
    expected = {CAPTURE_FILE}
    if raw is not None:
        expected.add(RAW_FILE)
    if text is not None:
        expected.add(TEXT_FILE)
    if {item.name for item in target.iterdir()} != expected:
        raise RuntimeError("official document capture closed file set differs")
    return capture, raw, text


def completed_official_document_ids(*, plan_root: Path) -> tuple[str, ...]:
    plan = read_official_event_document_plan(plan_root=plan_root)
    completed = []
    for document in plan.documents:
        path = plan_root / "documents" / document.document_id
        if path.exists():
            read_official_event_document_capture(
                plan_root=plan_root, document_id=document.document_id
            )
            completed.append(document.document_id)
    return tuple(completed)


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
        raise RuntimeError("official document evidence file is invalid")
    return path.read_bytes()


def _require_directory(path: Path, mode: int) -> None:
    if (
        not path.is_dir()
        or path.is_symlink()
        or path.stat().st_mode & 0o777 != mode
    ):
        raise RuntimeError("official document evidence directory is invalid")


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
