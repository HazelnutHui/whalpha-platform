"""Shared lexical custody for tmp-only and exact persistent daily artifacts."""

from __future__ import annotations

import os
import stat
from datetime import date
from pathlib import Path
from typing import Collection


DAILY_EOD_ACQUISITION_PACKAGE_NAME = "acquisition-package"
DAILY_EOD_CANONICAL_APPLY_PLAN_NAME = "canonical-apply-plan.json"
DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME = "identity-acquisition-package"
DAILY_IDENTITY_CANONICAL_APPLY_PLAN_NAME = (
    "identity-canonical-apply-plan.json"
)
DAILY_PRICE_ACQUISITION_PACKAGE_NAME = "eod-acquisition-package"
DAILY_PRICE_CANONICAL_APPLY_PLAN_NAME = "eod-canonical-apply-plan.json"
RESEARCH_MEMBERSHIP_APPLY_PLAN_NAME = "research-membership-apply-plan.json"
DAILY_EOD_SERVING_BUNDLE_ROOT_NAME = "serving-bundle"
RECONCILED_EOD_SOURCE_WORKSPACE_NAME = "reconciled-eod-source-reacquisition"
RECONCILED_EOD_SOURCE_PACKAGE_NAME = "eod-acquisition-package"

_DAILY_DATA_PACKAGE_NAMES = frozenset(
    {
        DAILY_EOD_ACQUISITION_PACKAGE_NAME,
        DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME,
        DAILY_PRICE_ACQUISITION_PACKAGE_NAME,
    }
)
_DAILY_DATA_PLAN_NAMES = frozenset(
    {
        DAILY_EOD_CANONICAL_APPLY_PLAN_NAME,
        DAILY_IDENTITY_CANONICAL_APPLY_PLAN_NAME,
        DAILY_PRICE_CANONICAL_APPLY_PLAN_NAME,
    }
)
_DAILY_DATA_PERSISTENT_PAIRS = {
    DAILY_EOD_ACQUISITION_PACKAGE_NAME: DAILY_EOD_CANONICAL_APPLY_PLAN_NAME,
    DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME: (
        DAILY_IDENTITY_CANONICAL_APPLY_PLAN_NAME
    ),
    DAILY_PRICE_ACQUISITION_PACKAGE_NAME: DAILY_PRICE_CANONICAL_APPLY_PLAN_NAME,
}


class OfflineArtifactCustodyError(RuntimeError):
    """Raised when an offline artifact path is outside governed custody."""


def validate_offline_artifact_location(
    path: Path,
    *,
    persistent_names: Collection[str],
    allow_tmp_descendants: bool = False,
) -> Path:
    """Accept one direct /tmp child or one exact persistent session child."""

    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise OfflineArtifactCustodyError("offline artifact path must be absolute")
    _reject_existing_symlink_components(path)
    if path.parent == Path("/tmp") or (
        allow_tmp_descendants and path.is_relative_to(Path("/tmp"))
    ):
        return path
    if path.name not in persistent_names:
        raise OfflineArtifactCustodyError(
            "persistent offline artifact name is not governed"
        )
    session_root = path.parent
    sessions_root = session_root.parent
    workspace_root = sessions_root.parent
    daily_layout = (
        sessions_root.name == "sessions"
        and workspace_root.name == "daily-eod"
        and workspace_root not in {Path("/"), Path("/tmp")}
        and Path("/tmp") not in workspace_root.parents
        and not _inside_git_repository(workspace_root)
    )
    historical_base = workspace_root.parent
    historical_layout = (
        sessions_root.name == "sessions"
        and historical_base.name == "historical-backfill"
        and workspace_root not in {Path("/"), Path("/tmp")}
        and Path("/tmp") not in workspace_root.parents
        and not _inside_git_repository(workspace_root)
    )
    if not daily_layout and not historical_layout:
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
    governed_directories = (workspace_root, sessions_root, session_root)
    if historical_layout:
        governed_directories = (historical_base, *governed_directories)
    for directory in governed_directories:
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


def validate_offline_artifact_child(
    path: Path,
    *,
    parent_name: str,
    child_names: Collection[str],
) -> Path:
    """Accept one exact child of a governed tmp or persistent artifact root."""

    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise OfflineArtifactCustodyError("offline artifact child must be absolute")
    _reject_existing_symlink_components(path)
    if path.is_relative_to(Path("/tmp")):
        return path
    if path.name not in child_names:
        raise OfflineArtifactCustodyError(
            "offline artifact child name is not governed"
        )
    validate_offline_artifact_location(
        path.parent,
        persistent_names={parent_name},
        allow_tmp_descendants=True,
    )
    return path


def validate_daily_eod_data_artifact_location(
    path: Path,
    *,
    persistent_name: str,
    expected_session: date | None = None,
    allow_tmp_descendants: bool = False,
) -> Path:
    """Accept legacy temporary custody or one exact persistent data path."""

    if persistent_name in _DAILY_DATA_PACKAGE_NAMES:
        governed_names = _DAILY_DATA_PACKAGE_NAMES
    elif persistent_name in _DAILY_DATA_PLAN_NAMES:
        governed_names = _DAILY_DATA_PLAN_NAMES
    else:
        raise OfflineArtifactCustodyError(
            "daily EOD data artifact role is not governed"
        )
    if path.name.startswith("."):
        raise OfflineArtifactCustodyError(
            "daily EOD data artifact cannot be hidden"
        )
    temporary = path.parent == Path("/tmp") or (
        allow_tmp_descendants and path.is_relative_to(Path("/tmp"))
    )
    if not temporary and path.is_relative_to(Path("/data")):
        raise OfflineArtifactCustodyError(
            "persistent daily EOD data artifact cannot be below /data"
        )
    target = validate_offline_artifact_location(
        path,
        persistent_names=governed_names,
        allow_tmp_descendants=allow_tmp_descendants,
    )
    if temporary:
        return target
    if expected_session is not None and path.parent.name != (
        f"session_date={expected_session.isoformat()}"
    ):
        raise OfflineArtifactCustodyError(
            "persistent daily EOD data artifact session differs"
        )
    return target


def validate_daily_eod_data_artifact_pair(
    *,
    package_path: Path,
    plan_path: Path,
    expected_session: date | None = None,
    allow_tmp_descendants: bool = False,
) -> tuple[Path, Path]:
    """Validate one package/plan pair without mixing custody modes or sessions."""

    package = validate_daily_eod_data_artifact_location(
        package_path,
        persistent_name=DAILY_EOD_ACQUISITION_PACKAGE_NAME,
        expected_session=expected_session,
        allow_tmp_descendants=allow_tmp_descendants,
    )
    plan = validate_daily_eod_data_artifact_location(
        plan_path,
        persistent_name=DAILY_EOD_CANONICAL_APPLY_PLAN_NAME,
        expected_session=expected_session,
        allow_tmp_descendants=allow_tmp_descendants,
    )
    package_temporary = package.parent == Path("/tmp") or (
        allow_tmp_descendants and package.is_relative_to(Path("/tmp"))
    )
    plan_temporary = plan.parent == Path("/tmp") or (
        allow_tmp_descendants and plan.is_relative_to(Path("/tmp"))
    )
    if package_temporary != plan_temporary:
        raise OfflineArtifactCustodyError(
            "daily EOD package and plan cannot mix custody modes"
        )
    if not package_temporary and package.parent != plan.parent:
        raise OfflineArtifactCustodyError(
            "persistent daily EOD package and plan sessions differ"
        )
    if (
        not package_temporary
        and _DAILY_DATA_PERSISTENT_PAIRS.get(package.name) != plan.name
    ):
        raise OfflineArtifactCustodyError(
            "persistent daily EOD package and plan roles differ"
        )
    if package == plan:
        raise OfflineArtifactCustodyError(
            "daily EOD package and plan paths must differ"
        )
    return package, plan


def validate_reconciled_eod_source_package_location(
    path: Path,
    *,
    expected_session: date,
) -> Path:
    """Accept one exact later-reacquisition Grouped Daily package path."""

    if (
        not path.is_absolute()
        or path.name != RECONCILED_EOD_SOURCE_PACKAGE_NAME
        or path.is_relative_to(Path("/tmp"))
        or path.is_relative_to(Path("/data"))
    ):
        raise OfflineArtifactCustodyError(
            "reconciled EOD source package path is not governed"
        )
    _reject_existing_symlink_components(path)
    session_root = path.parent
    sessions_root = session_root.parent
    workspace_root = sessions_root.parent
    if (
        session_root.name != f"session_date={expected_session.isoformat()}"
        or sessions_root.name != "sessions"
        or workspace_root.name != RECONCILED_EOD_SOURCE_WORKSPACE_NAME
        or workspace_root in {Path("/"), Path("/tmp")}
        or Path("/tmp") in workspace_root.parents
        or _inside_git_repository(workspace_root)
    ):
        raise OfflineArtifactCustodyError(
            "reconciled EOD source package layout differs"
        )
    for directory in (workspace_root, sessions_root, session_root):
        if directory.is_symlink() or not directory.is_dir():
            raise OfflineArtifactCustodyError(
                "reconciled EOD source package parent is unavailable"
            )
        metadata = directory.stat()
        if (
            metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise OfflineArtifactCustodyError(
                "reconciled EOD source package parent custody differs"
            )
    return path


def validate_daily_eod_serving_bundle_location(
    path: Path,
    *,
    expected_session: date | None = None,
) -> Path:
    """Accept a legacy tmp bundle release or one exact persistent session release."""

    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise OfflineArtifactCustodyError(
            "daily EOD serving bundle path must be absolute"
        )
    _reject_existing_symlink_components(path)
    if path.parent.parent == Path("/tmp"):
        return path
    if path.is_relative_to(Path("/data")):
        raise OfflineArtifactCustodyError(
            "persistent daily EOD serving bundle cannot be below /data"
        )
    bundle_root = path.parent
    validate_offline_artifact_location(
        bundle_root,
        persistent_names={DAILY_EOD_SERVING_BUNDLE_ROOT_NAME},
    )
    if bundle_root.is_symlink() or not bundle_root.is_dir():
        raise OfflineArtifactCustodyError(
            "persistent daily EOD serving bundle root is unavailable"
        )
    metadata = bundle_root.stat()
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise OfflineArtifactCustodyError(
            "persistent daily EOD serving bundle root custody differs"
        )
    if expected_session is not None and bundle_root.parent.name != (
        f"session_date={expected_session.isoformat()}"
    ):
        raise OfflineArtifactCustodyError(
            "persistent daily EOD serving bundle session differs"
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
