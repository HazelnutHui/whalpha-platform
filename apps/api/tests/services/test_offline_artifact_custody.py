from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


def _persistent_session() -> tuple[Path, Path]:
    owner = Path.home() / ".local/state" / f"whalpha-custody-test-{uuid4().hex}"
    workspace = owner / "daily-eod"
    sessions = workspace / "sessions"
    session = sessions / "session_date=2026-08-28"
    for path in (owner, workspace, sessions, session):
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    return owner, session


def test_accepts_direct_tmp_and_exact_persistent_session_child() -> None:
    direct = Path("/tmp/arbitrary-reviewed-audit")
    assert validate_offline_artifact_location(
        direct,
        persistent_names={"market-regime-phase1a"},
    ) == direct
    owner, session = _persistent_session()
    try:
        persistent = session / "market-regime-phase1a"
        assert validate_offline_artifact_location(
            persistent,
            persistent_names={"market-regime-phase1a"},
        ) == persistent
    finally:
        shutil.rmtree(owner)


def test_rejects_ungoverned_name_or_parent_custody() -> None:
    owner, session = _persistent_session()
    try:
        with pytest.raises(OfflineArtifactCustodyError, match="name"):
            validate_offline_artifact_location(
                session / "unexpected",
                persistent_names={"market-regime-phase1a"},
            )
        session.chmod(0o755)
        with pytest.raises(OfflineArtifactCustodyError, match="custody"):
            validate_offline_artifact_location(
                session / "market-regime-phase1a",
                persistent_names={"market-regime-phase1a"},
            )
    finally:
        shutil.rmtree(owner)


def test_rejects_dangling_symlink_and_git_workspace() -> None:
    dangling = Path("/tmp") / f"whalpha-custody-dangling-{uuid4().hex}"
    dangling.symlink_to(dangling.with_name(f"{dangling.name}-missing"))
    try:
        with pytest.raises(OfflineArtifactCustodyError, match="symlink"):
            validate_offline_artifact_location(
                dangling,
                persistent_names={"market-regime-phase1a"},
            )
    finally:
        dangling.unlink(missing_ok=True)

    owner, session = _persistent_session()
    try:
        (owner / ".git").write_text("gitdir: unavailable\n", encoding="utf-8")
        with pytest.raises(OfflineArtifactCustodyError, match="layout"):
            validate_offline_artifact_location(
                session / "market-regime-phase1a",
                persistent_names={"market-regime-phase1a"},
            )
    finally:
        shutil.rmtree(owner)
