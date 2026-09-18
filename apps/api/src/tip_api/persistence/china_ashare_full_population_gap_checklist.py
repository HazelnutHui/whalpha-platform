"""Owner-only custody for the A-share dynamic gap checklist."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_gaps import (
    ChinaAshareFullPopulationGapChecklistV1,
)


CHECKLIST_FILE = "gap-admission-checklist.json"
MAXIMUM_FILE_BYTES = 4 * 1024 * 1024


class ChinaAshareFullPopulationGapChecklistError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationGapChecklistResultV1:
    checklist: ChinaAshareFullPopulationGapChecklistV1
    package_path: Path
    checklist_path: Path
    physical_sha256: str
    total_bytes: int
    status: str


def publish_china_ashare_full_population_gap_checklist(
    *, custody_root: Path, checklist: ChinaAshareFullPopulationGapChecklistV1
) -> ChinaAshareFullPopulationGapChecklistResultV1:
    parent = _ensure_directory(_custody_root(custody_root) / "checklists")
    target = parent / f"checklist={checklist.logical_fingerprint}"
    if target.exists() or target.is_symlink():
        existing = read_china_ashare_full_population_gap_checklist(
            package_path=target
        )
        if existing.checklist != checklist:
            raise ChinaAshareFullPopulationGapChecklistError(
                "existing dynamic gap checklist differs"
            )
        return replace(existing, status="already_present")
    staging = Path(tempfile.mkdtemp(prefix=".checklist-", dir=parent))
    try:
        _write(staging / CHECKLIST_FILE, _canonical(checklist))
        staging.chmod(0o700)
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(parent)
    except BaseException:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return replace(
        read_china_ashare_full_population_gap_checklist(package_path=target),
        status="published",
    )


def read_china_ashare_full_population_gap_checklist(
    *, package_path: Path
) -> ChinaAshareFullPopulationGapChecklistResultV1:
    candidate = package_path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist path cannot be a symlink"
        )
    root = candidate.resolve()
    if not root.is_dir() or (root.stat().st_mode & 0o777) != 0o700:
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist package is invalid"
        )
    entries = tuple(root.rglob("*"))
    if (
        {item.relative_to(root).as_posix() for item in entries} != {CHECKLIST_FILE}
        or any(item.is_symlink() for item in entries)
        or any((item.stat().st_mode & 0o777) != 0o400 for item in entries)
    ):
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist custody differs"
        )
    payload = _read(root / CHECKLIST_FILE)
    try:
        checklist = ChinaAshareFullPopulationGapChecklistV1.model_validate_json(
            payload
        )
    except (ValidationError, ValueError) as exc:
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist document is invalid"
        ) from exc
    if (
        root.name != f"checklist={checklist.logical_fingerprint}"
        or root.parent.name != "checklists"
        or payload != _canonical(checklist)
    ):
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist identity differs"
        )
    return ChinaAshareFullPopulationGapChecklistResultV1(
        checklist=checklist,
        package_path=root,
        checklist_path=root / CHECKLIST_FILE,
        physical_sha256=_sha(payload),
        total_bytes=len(payload),
        status="exact_reread_complete",
    )


def _custody_root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap custody root cannot be a symlink"
        )
    return _ensure_directory(candidate.resolve())


def _ensure_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap custody directory is invalid"
        )
    path.chmod(0o700)
    return path


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist file is absent or unsafe"
        )
    size = path.stat().st_size
    if size <= 0 or size > MAXIMUM_FILE_BYTES:
        raise ChinaAshareFullPopulationGapChecklistError(
            "dynamic gap checklist file size is invalid"
        )
    return path.read_bytes()


def _canonical(checklist: ChinaAshareFullPopulationGapChecklistV1) -> bytes:
    return (
        json.dumps(
            checklist.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode()


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
