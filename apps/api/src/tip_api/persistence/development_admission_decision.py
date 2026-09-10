"""Owner-only persistence for a development-admission decision."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from uuid import uuid4

from tip_api.contracts.analytics.v1.candidate_strategy_development_admission import (
    StrongLeaderPullbackDevelopmentAdmissionDecisionV1,
)


DECISION_FILE = "decision.json"
OUTPUT_PREFIX = "whalpha-strong-leader-pullback-development-admission-"
MAXIMUM_DECISION_BYTES = 256 * 1024


class DevelopmentAdmissionDecisionPersistenceError(RuntimeError):
    """Raised when owner-only admission-decision custody cannot be trusted."""


def write_development_admission_decision(
    *,
    output_root: Path,
    decision: StrongLeaderPullbackDevelopmentAdmissionDecisionV1,
) -> Path:
    target = _validate_new_output_root(output_root)
    staging = target.parent / f"{target.name}-staging-{uuid4().hex}"
    try:
        staging.mkdir(mode=0o700)
        _write_exclusive(
            staging / DECISION_FILE,
            development_admission_decision_bytes(decision),
        )
        if read_development_admission_decision(output_root=staging) != decision:
            raise DevelopmentAdmissionDecisionPersistenceError(
                "development admission decision formal reread differs"
            )
        _fsync_directory(staging)
        staging.rename(target)
        _fsync_directory(target.parent)
    except Exception as exc:
        _cleanup_staging(staging)
        if isinstance(exc, DevelopmentAdmissionDecisionPersistenceError):
            raise
        raise DevelopmentAdmissionDecisionPersistenceError(
            "development admission decision write failed"
        ) from exc
    if read_development_admission_decision(output_root=target) != decision:
        raise DevelopmentAdmissionDecisionPersistenceError(
            "development admission decision final reread differs"
        )
    return target / DECISION_FILE


def read_development_admission_decision(
    *, output_root: Path
) -> StrongLeaderPullbackDevelopmentAdmissionDecisionV1:
    root = output_root.absolute()
    temporary_root = Path("/tmp").resolve(strict=True)
    if (
        root.parent != temporary_root
        or not root.name.startswith(OUTPUT_PREFIX)
        or root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or {item.name for item in root.iterdir()} != {DECISION_FILE}
    ):
        raise DevelopmentAdmissionDecisionPersistenceError(
            "development admission decision directory custody differs"
        )
    path = root / DECISION_FILE
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not 0 < path.stat().st_size <= MAXIMUM_DECISION_BYTES
    ):
        raise DevelopmentAdmissionDecisionPersistenceError(
            "development admission decision file custody differs"
        )
    raw = path.read_bytes()
    try:
        decision = (
            StrongLeaderPullbackDevelopmentAdmissionDecisionV1.model_validate_json(
                raw
            )
        )
    except Exception as exc:
        raise DevelopmentAdmissionDecisionPersistenceError(
            "development admission decision is invalid"
        ) from exc
    if raw != development_admission_decision_bytes(decision):
        raise DevelopmentAdmissionDecisionPersistenceError(
            "development admission decision bytes are not canonical"
        )
    return decision


def development_admission_decision_bytes(
    decision: StrongLeaderPullbackDevelopmentAdmissionDecisionV1,
) -> bytes:
    return (
        json.dumps(
            decision.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_new_output_root(output_root: Path) -> Path:
    target = output_root.absolute()
    temporary_root = Path("/tmp").resolve(strict=True)
    if (
        target.parent != temporary_root
        or not target.name.startswith(OUTPUT_PREFIX)
        or target.exists()
        or target.is_symlink()
    ):
        raise DevelopmentAdmissionDecisionPersistenceError(
            "output root must be one new direct /tmp admission directory"
        )
    return target


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _cleanup_staging(staging: Path) -> None:
    if staging.is_symlink() or not staging.exists():
        return
    path = staging / DECISION_FILE
    if path.exists() and not path.is_symlink():
        path.unlink()
    try:
        staging.rmdir()
    except OSError:
        pass


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
