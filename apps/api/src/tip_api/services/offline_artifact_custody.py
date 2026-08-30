"""Shared lexical custody for tmp-only and exact persistent daily artifacts."""

from __future__ import annotations

import os
import stat
from datetime import date
from pathlib import Path
from typing import Collection


class OfflineArtifactCustodyError(RuntimeError):
    """Raised when an offline artifact path is outside governed custody."""


def validate_offline_artifact_location(
    path: Path,
    *,
    persistent_names: Collection[str],
) -> Path:
    """Accept one direct /tmp child or one exact persistent session child."""

    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise OfflineArtifactCustodyError("offline artifact path must be absolute")
    _reject_existing_symlink_components(path)
    if path.parent == Path("/tmp"):
        return path
    if path.name not in persistent_names:
        raise OfflineArtifactCustodyError(
            "persistent offline artifact name is not governed"
        )
    session_root = path.parent
    sessions_root = session_root.parent
    workspace_root = sessions_root.parent
    if (
        sessions_root.name != "sessions"
        or workspace_root.name != "daily-eod"
        or workspace_root == Path("/")
        or workspace_root == Path("/tmp")
        or Path("/tmp") in workspace_root.parents
        or _inside_git_repository(workspace_root)
    ):
        raise OfflineArtifactCustodyError(
            "persistent offline artifact layout differs"
        )
    try:
        date.fromisoformat(session_root.name.removeprefix("session_date="))
    except ValueError as exc:
        raise OfflineArtifactCustodyError(
            "persistent offline artifact session is malformed"
        ) from exc
    if not session_root.name.startswith("session_date="):
        raise OfflineArtifactCustodyError(
            "persistent offline artifact session is malformed"
        )
    for directory in (workspace_root, sessions_root, session_root):
        if directory.is_symlink() or not directory.is_dir():
            raise OfflineArtifactCustodyError(
                "persistent offline artifact parent is unavailable"
            )
        metadata = directory.stat()
        if (
            metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise OfflineArtifactCustodyError(
                "persistent offline artifact parent custody differs"
            )
    return path


def _reject_existing_symlink_components(path: Path) -> None:
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise OfflineArtifactCustodyError(
                "offline artifact symlink component is rejected"
            )


def _inside_git_repository(path: Path) -> bool:
    return any(
        (candidate / ".git").exists()
        for candidate in (path, *path.parents)
    )
