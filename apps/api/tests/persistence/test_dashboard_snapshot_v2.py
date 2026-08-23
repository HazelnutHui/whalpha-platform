from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.persistence.parquet import dashboard_snapshot_active as repo
from tip_api.persistence.parquet import dashboard_universe_activation_active as durable
from tip_api.services import dashboard_snapshot_v2_cli as cli
from tip_api.services import private_dashboard_snapshot as snapshot
from tip_api.services.dashboard_overview import DashboardUniverseFunnelStage
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID

from tests.services.test_private_dashboard_snapshot import FakeOverviewService, fake_overview

ACTIVATION_POINTER = "a" * 64
ACTIVATION_LOGICAL = "b" * 64
AT = datetime(2026, 8, 20, 12, tzinfo=UTC)


class FormalOverviewService(FakeOverviewService):
    def get_latest_overview(self, *, checked_at=None):
        overview = fake_overview()
        funnels = []
        for universe, policy in zip(overview.universes, (FULL_BASE_A_ID, FULL_BASE_B_ID), strict=True):
            remaining = universe.definition.member_count
            stages = tuple(
                DashboardUniverseFunnelStage(
                    universe_id=universe.definition.universe_id,
                    stage_index=index,
                    stage_id=f"stage_{index}",
                    display_label=f"Stage {index}",
                    input_count=(3 if index == 1 else remaining),
                    excluded_count=((3 - remaining) if index == 1 else 0),
                    remaining_count=remaining,
                    source_revision="authoritative-security-form-v2",
                    source_session=overview.current_session_date,
                    source_fingerprint=ACTIVATION_LOGICAL,
                )
                for index in range(1, 11)
            )
            funnels.append(replace(universe, funnel=stages))
        return replace(
            overview,
            contract_version="2.1",
            activation_fingerprint=ACTIVATION_LOGICAL,
            freshness_status="fresh",
            expected_latest_completed_session=overview.current_session_date,
            actual_latest_completed_session=overview.current_session_date,
            session_lag=0,
            universes=tuple(funnels),
        )


class StaleFormalOverviewService(FormalOverviewService):
    def get_latest_overview(self, *, checked_at=None):
        overview = super().get_latest_overview(checked_at=checked_at)
        return replace(
            overview,
            freshness_status="stale",
            expected_latest_completed_session=overview.current_session_date.replace(day=14),
            session_lag=1,
        )


def _release(monkeypatch, root: Path, release_id: str, *, formal: bool) -> Path:
    monkeypatch.setattr(
        snapshot,
        "DashboardOverviewService",
        FormalOverviewService if formal else FakeOverviewService,
    )
    result = snapshot.build_private_dashboard_snapshot(
        data_root=root,
        output_root=root,
        allowed_output_root=root,
        release_id=release_id,
        generated_at=AT,
        dashboard_activation=object(),
    )
    return result.output_dir


def _setup(monkeypatch, tmp_path):
    root = tmp_path / "data"
    legacy = tmp_path / "legacy"
    candidate_root = tmp_path / "candidate"
    root.mkdir(); legacy.mkdir(); candidate_root.mkdir()
    _release(monkeypatch, legacy, repo.LEGACY_RELEASE_ID, formal=False)
    candidate = _release(monkeypatch, candidate_root, "2026-08-20T120000Z-abcdef0", formal=True)
    pointer = SimpleNamespace(pointer_content_fingerprint=ACTIVATION_POINTER)
    monkeypatch.setattr(repo, "read_dashboard_universe_activation_pointer", lambda root: pointer)
    plan = repo.build_approval_plan(
        root=root,
        legacy_root=legacy,
        candidate=candidate,
        activation_logical_fingerprint=ACTIVATION_LOGICAL,
        generated_at=AT,
    )
    return root, legacy, candidate, plan


def test_v1_pointer_absent_compatibility(monkeypatch, tmp_path):
    root, legacy, _, _ = _setup(monkeypatch, tmp_path)
    active = repo.read_active_dashboard_snapshot(root, legacy)
    assert active.pointer is None
    assert active.manifest.snapshot_contract_version == "1.3"


def test_plan_is_deterministic_and_binds_fresh_funnel(monkeypatch, tmp_path):
    root, legacy, candidate, plan = _setup(monkeypatch, tmp_path)
    again = repo.build_approval_plan(
        root=root, legacy_root=legacy, candidate=candidate,
        activation_logical_fingerprint=ACTIVATION_LOGICAL, generated_at=AT,
    )
    assert again == plan
    assert len(plan.files) == 6
    assert plan.expected_latest_completed_session == plan.actual_latest_completed_session
    assert plan.freshness_status == "fresh"


def test_atomic_publish_formal_reread_and_replay_rejected(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    result = repo.publish_and_activate(
        root=root, legacy_root=legacy, plan=plan,
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        freshness_validator=lambda: None,
    )
    assert result.manifest.snapshot_contract_version == "1.4"
    assert result.pointer.pointer_content_fingerprint == plan.planned_pointer_fingerprint
    assert not tuple(root.rglob("*staging*"))
    with pytest.raises(repo.DashboardSnapshotPublicationConflict, match="state changed|exists"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        )


def test_completed_target_before_pointer_recovers_without_overwrite(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    with pytest.raises(repo.DashboardSnapshotPublicationError, match="after target"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            failpoint="after_target_rename",
        )
    target = root / plan.target_path
    before = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    result = repo.verify_then_link(
        root=root, legacy_root=legacy, plan=plan,
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        freshness_validator=lambda: None,
    )
    after = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    assert before == after
    assert result.pointer.pointer_content_fingerprint == plan.planned_pointer_fingerprint


def test_freshness_rechecked_inside_lock_before_write(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    def stale():
        raise repo.DashboardSnapshotPublicationError("stale")
    with pytest.raises(repo.DashboardSnapshotPublicationError, match="stale"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            freshness_validator=stale,
        )
    assert not (root / plan.target_path).exists()
    assert repo.read_dashboard_snapshot_pointer(root) is None


def test_stale_candidate_cannot_create_approval_plan(monkeypatch, tmp_path):
    root, legacy, _, _ = _setup(monkeypatch, tmp_path)
    candidate_root = tmp_path / "stale"
    candidate_root.mkdir()
    monkeypatch.setattr(snapshot, "DashboardOverviewService", StaleFormalOverviewService)
    candidate = snapshot.build_private_dashboard_snapshot(
        data_root=root, output_root=candidate_root, allowed_output_root=candidate_root,
        release_id="2026-08-20T130000Z-abcdef0", generated_at=AT,
        dashboard_activation=object(),
    ).output_dir
    with pytest.raises(repo.DashboardSnapshotPublicationError, match="stale snapshot"):
        repo.build_approval_plan(
            root=root, legacy_root=legacy, candidate=candidate,
            activation_logical_fingerprint=ACTIVATION_LOGICAL, generated_at=AT,
        )


def test_rollback_requires_explicit_digest_and_restores_v1(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    published = repo.publish_and_activate(
        root=root, legacy_root=legacy, plan=plan,
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
    )
    approved = published.pointer.pointer_content_fingerprint
    with pytest.raises(repo.DashboardSnapshotPublicationConflict, match="approval digest"):
        repo.rollback(root=root, legacy_root=legacy, expected_pointer_fingerprint="f" * 64, apply=True)
    result = repo.rollback(root=root, legacy_root=legacy, expected_pointer_fingerprint=approved, apply=True)
    assert result.manifest.snapshot_contract_version == "1.3"
    assert result.pointer.active.storage_kind == "legacy_repo_build"


def test_symlink_and_partial_target_fail_closed(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    target = root / plan.target_path
    target.parent.mkdir(parents=True)
    target.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(Exception, match="symlink"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        )


def test_crash_boundaries_and_lock_are_unambiguous(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    with pytest.raises(repo.DashboardSnapshotPublicationError, match="before target"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            failpoint="before_target_rename",
        )
    assert not Path(plan.target_path).exists()
    assert repo.read_dashboard_snapshot_pointer(root) is None
    with repo._lock(root):
        with pytest.raises(repo.DashboardSnapshotPublicationConflict, match="locked"):
            repo.publish_and_activate(
                root=root, legacy_root=legacy, plan=plan,
                expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            )


def test_crash_after_pointer_is_formally_active(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    with pytest.raises(repo.DashboardSnapshotPublicationError, match="after pointer"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
            failpoint="after_pointer_write",
        )
    active = repo.read_active_dashboard_snapshot(root, legacy)
    assert active.pointer.pointer_content_fingerprint == plan.planned_pointer_fingerprint


def test_plan_tamper_and_state_change_are_zero_write_rejections(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    tampered = plan.model_copy(update={"aggregate_sha256": "f" * 64})
    with pytest.raises(repo.DashboardSnapshotPublicationError, match="plan fingerprint"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=tampered,
            expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
        )
    with pytest.raises(repo.DashboardSnapshotPublicationConflict, match="approved current"):
        repo.publish_and_activate(
            root=root, legacy_root=legacy, plan=plan,
            expected_current_state_fingerprint="e" * 64,
        )
    assert not Path(plan.target_path).exists()


def test_first_directory_entries_and_artifacts_are_fsynced(monkeypatch, tmp_path):
    root, legacy, _, plan = _setup(monkeypatch, tmp_path)
    calls = []
    original = repo._fsync_directory
    durable_original = durable._fsync_directory
    monkeypatch.setattr(repo, "_fsync_directory", lambda path: (calls.append(path), original(path))[1])
    monkeypatch.setattr(durable, "_fsync_directory", lambda path: (calls.append(path), durable_original(path))[1])
    repo.publish_and_activate(
        root=root, legacy_root=legacy, plan=plan,
        expected_current_state_fingerprint=plan.expected_current_state_fingerprint,
    )
    target = Path(plan.target_path)
    pointer_parent = Path(plan.pointer_path).parent
    assert target.parent in calls
    assert pointer_parent in calls
    assert root in calls


def test_cli_rejects_naked_apply_and_approval_arguments(capsys):
    for args in (
        ["--apply"],
        ["--verify-then-link"],
        ["--approved-plan", "/tmp/plan.json"],
    ):
        with pytest.raises(SystemExit) as error:
            cli.main(args)
        assert error.value.code == 2


def test_cli_current_freshness_cannot_be_spoofed_by_generated_at(monkeypatch, tmp_path, capsys):
    root, legacy, candidate, _ = _setup(monkeypatch, tmp_path)
    manifest = snapshot.validate_snapshot_release(candidate)
    stale = SimpleNamespace(
        freshness_status=SimpleNamespace(value="stale"), session_lag=2,
        expected_latest_completed_session=date(2026, 8, 15),
        actual_latest_completed_session=date.fromisoformat(manifest.current_session_date),
    )
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(cli, "LEGACY_ROOT", legacy)
    monkeypatch.setattr(cli, "_formal_freshness", lambda: stale)
    monkeypatch.setattr(cli, "read_active_dashboard_universe_activation", lambda *a, **k: object())
    monkeypatch.setattr(
        cli, "build_private_dashboard_snapshot",
        lambda **kwargs: SimpleNamespace(output_dir=candidate, manifest=manifest),
    )
    monkeypatch.setattr(
        cli, "build_approval_plan",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("stale state reached plan builder")),
    )
    assert cli.main([
        "--output-root", str(tmp_path / "output"),
        "--release-id", "2026-08-19T120000Z-abcdef0",
        "--generated-at", "2026-08-19T12:00:00Z",
    ]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["status"] == "stale_blocked"
    assert payload["session_lag"] == 2
