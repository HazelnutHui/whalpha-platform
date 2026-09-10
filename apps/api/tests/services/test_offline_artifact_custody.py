from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from tip_api.services.offline_artifact_custody import (
    DAILY_EOD_ACQUISITION_PACKAGE_NAME,
    DAILY_EOD_CANONICAL_APPLY_PLAN_NAME,
    DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME,
    DAILY_IDENTITY_CANONICAL_APPLY_PLAN_NAME,
    DAILY_PRICE_ACQUISITION_PACKAGE_NAME,
    DAILY_PRICE_CANONICAL_APPLY_PLAN_NAME,
    OfflineArtifactCustodyError,
    validate_daily_eod_data_artifact_location,
    validate_daily_eod_data_artifact_pair,
    validate_daily_eod_serving_bundle_location,
    validate_offline_artifact_child,
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


def _persistent_historical_session() -> tuple[Path, Path]:
    owner = Path.home() / ".local/state" / f"whalpha-custody-test-{uuid4().hex}"
    historical_base = owner / "historical-backfill"
    workspace = historical_base / "five-year-fixture"
    sessions = workspace / "sessions"
    session = sessions / "session_date=2026-08-28"
    for path in (owner, historical_base, workspace, sessions, session):
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


def test_accepts_exact_persistent_child_but_rejects_wrong_child() -> None:
    owner, session = _persistent_session()
    try:
        root = session / "market-intelligence"
        root.mkdir(mode=0o700)
        child = root / "market-intelligence.plan.artifacts"
        assert validate_offline_artifact_child(
            child,
            parent_name="market-intelligence",
            child_names={"market-intelligence.plan.artifacts"},
        ) == child
        with pytest.raises(OfflineArtifactCustodyError, match="child name"):
            validate_offline_artifact_child(
                root / "unexpected",
                parent_name="market-intelligence",
                child_names={"market-intelligence.plan.artifacts"},
            )
    finally:
        shutil.rmtree(owner)


def test_accepts_exact_persistent_daily_data_pair_bound_to_session() -> None:
    owner, session = _persistent_session()
    try:
        package = session / DAILY_EOD_ACQUISITION_PACKAGE_NAME
        plan = session / DAILY_EOD_CANONICAL_APPLY_PLAN_NAME
        expected = date(2026, 8, 28)
        assert validate_daily_eod_data_artifact_pair(
            package_path=package,
            plan_path=plan,
            expected_session=expected,
        ) == (package, plan)
        assert validate_daily_eod_data_artifact_location(
            package,
            persistent_name=DAILY_EOD_ACQUISITION_PACKAGE_NAME,
            expected_session=expected,
        ) == package
    finally:
        shutil.rmtree(owner)


def test_accepts_exact_persistent_historical_data_pair_bound_to_session() -> None:
    owner, session = _persistent_historical_session()
    try:
        package = session / DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME
        plan = session / DAILY_IDENTITY_CANONICAL_APPLY_PLAN_NAME
        assert validate_daily_eod_data_artifact_pair(
            package_path=package,
            plan_path=plan,
            expected_session=date(2026, 8, 28),
        ) == (package, plan)
    finally:
        shutil.rmtree(owner)


@pytest.mark.parametrize(
    ("package_name", "plan_name"),
    (
        (
            DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME,
            DAILY_IDENTITY_CANONICAL_APPLY_PLAN_NAME,
        ),
        (
            DAILY_PRICE_ACQUISITION_PACKAGE_NAME,
            DAILY_PRICE_CANONICAL_APPLY_PLAN_NAME,
        ),
    ),
)
def test_accepts_distinct_persistent_identity_and_eod_pairs(
    package_name: str,
    plan_name: str,
) -> None:
    owner, session = _persistent_session()
    try:
        package = session / package_name
        plan = session / plan_name
        assert validate_daily_eod_data_artifact_pair(
            package_path=package,
            plan_path=plan,
            expected_session=date(2026, 8, 28),
        ) == (package, plan)
    finally:
        shutil.rmtree(owner)


def test_rejects_cross_role_persistent_daily_data_pair() -> None:
    owner, session = _persistent_session()
    try:
        with pytest.raises(OfflineArtifactCustodyError, match="roles differ"):
            validate_daily_eod_data_artifact_pair(
                package_path=session / DAILY_IDENTITY_ACQUISITION_PACKAGE_NAME,
                plan_path=session / DAILY_PRICE_CANONICAL_APPLY_PLAN_NAME,
                expected_session=date(2026, 8, 28),
            )
    finally:
        shutil.rmtree(owner)


def test_rejects_mixed_hidden_or_wrong_session_daily_data_custody() -> None:
    owner, session = _persistent_session()
    try:
        package = session / DAILY_EOD_ACQUISITION_PACKAGE_NAME
        plan = session / DAILY_EOD_CANONICAL_APPLY_PLAN_NAME
        with pytest.raises(OfflineArtifactCustodyError, match="cannot mix"):
            validate_daily_eod_data_artifact_pair(
                package_path=package,
                plan_path=Path("/tmp/legacy-plan.json"),
                expected_session=date(2026, 8, 28),
            )
        with pytest.raises(OfflineArtifactCustodyError, match="session differs"):
            validate_daily_eod_data_artifact_location(
                plan,
                persistent_name=DAILY_EOD_CANONICAL_APPLY_PLAN_NAME,
                expected_session=date(2026, 8, 27),
            )
        with pytest.raises(OfflineArtifactCustodyError, match="hidden"):
            validate_daily_eod_data_artifact_location(
                session / ".canonical-apply-plan.json",
                persistent_name=DAILY_EOD_CANONICAL_APPLY_PLAN_NAME,
            )
    finally:
        shutil.rmtree(owner)


def test_rejects_persistent_daily_data_custody_below_data() -> None:
    path = (
        Path("/data")
        / "daily-eod"
        / "sessions"
        / "session_date=2026-08-28"
        / DAILY_EOD_ACQUISITION_PACKAGE_NAME
    )
    with pytest.raises(OfflineArtifactCustodyError, match="below /data"):
        validate_daily_eod_data_artifact_location(
            path,
            persistent_name=DAILY_EOD_ACQUISITION_PACKAGE_NAME,
        )


def test_accepts_exact_persistent_serving_bundle_release() -> None:
    owner, session = _persistent_session()
    try:
        bundle_root = session / "serving-bundle"
        bundle_root.mkdir(mode=0o700)
        bundle_root.chmod(0o700)
        release = bundle_root / "2026-08-29T120000Z-aaaaaaaaaaaa"
        release.mkdir(mode=0o700)
        assert validate_daily_eod_serving_bundle_location(
            release,
            expected_session=date(2026, 8, 28),
        ) == release
    finally:
        shutil.rmtree(owner)


def test_rejects_persistent_serving_bundle_session_or_root_custody_drift() -> None:
    owner, session = _persistent_session()
    try:
        bundle_root = session / "serving-bundle"
        bundle_root.mkdir(mode=0o700)
        bundle_root.chmod(0o700)
        release = bundle_root / "2026-08-29T120000Z-aaaaaaaaaaaa"
        release.mkdir(mode=0o700)
        with pytest.raises(OfflineArtifactCustodyError, match="session differs"):
            validate_daily_eod_serving_bundle_location(
                release,
                expected_session=date(2026, 8, 27),
            )
        bundle_root.chmod(0o755)
        with pytest.raises(OfflineArtifactCustodyError, match="root custody"):
            validate_daily_eod_serving_bundle_location(
                release,
                expected_session=date(2026, 8, 28),
            )
    finally:
        shutil.rmtree(owner)
