from __future__ import annotations

import hashlib
import shutil
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tip_api.contracts.market_data.v2.dashboard_snapshot import (
    DashboardSnapshotApprovalPlanV2_4,
)
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    DashboardSnapshotPublicationError,
)
from tip_api.services import daily_eod_dashboard_snapshot_apply_custody as custody
from tip_api.services.daily_eod_automation import (
    ArtifactObservation,
    ArtifactStatus,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_run_journal import (
    locked_daily_eod_run_journal,
    unresolved_started_event,
)


TARGET = date(2026, 8, 28)
CHECKED = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)
CURRENT_STATE = "1" * 64
ACTIVATION_STATE = "2" * 64
PLAN_FP = "3" * 64
POINTER_FP = "4" * 64


@pytest.fixture
def setup(tmp_path):
    suffix = tmp_path.name
    data_root = tmp_path / "data"
    legacy_root = tmp_path / "legacy"
    run_root = tmp_path / "run"
    for path in (data_root, legacy_root, run_root):
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    plan_path = Path(f"/tmp/{suffix}-snapshot-apply-plan.json")
    plan_path.write_bytes(b"{}")
    plan_path.chmod(0o444)
    paths = DailyEodAutomationPaths(
        data_root=data_root,
        phase1a_audit=Path(f"/tmp/{suffix}-phase1a"),
        prior_phase1b_audit=Path(f"/tmp/{suffix}-prior-phase1b"),
        phase1b_audit=Path(f"/tmp/{suffix}-phase1b"),
        prior_candidate_audit=Path(f"/tmp/{suffix}-prior-candidate"),
        candidate_audit=Path(f"/tmp/{suffix}-candidate"),
        entry_geometry_audit=Path(f"/tmp/{suffix}-entry"),
        phase2_audit=Path(f"/tmp/{suffix}-phase2"),
        preview_bundle=Path(f"/tmp/{suffix}-preview"),
        strategy_channel_audit=Path(f"/tmp/{suffix}-strategy"),
        market_intelligence_output_root=Path(f"/tmp/{suffix}-mi-output"),
        market_intelligence_approval_plan=Path(f"/tmp/{suffix}-mi-plan.json"),
        snapshot_output_root=Path(f"/tmp/{suffix}-snapshot-output"),
        snapshot_approval_plan=plan_path,
        serving_bundle_root=Path(f"/tmp/{suffix}-serving-bundle"),
    )
    release_id = "2026-08-28T210000Z-abcdef012345"
    approval = DashboardSnapshotApprovalPlanV2_4.model_construct(
        release_id=release_id,
        analysis_session=TARGET,
        expected_current_state_fingerprint=CURRENT_STATE,
        target_path=str(custody.target_path(data_root, release_id)),
        target_logical_path=str(
            custody.target_path(data_root, release_id).relative_to(data_root)
        ),
        pointer_path=str(custody.pointer_path(data_root)),
        candidate_path=str(paths.snapshot_output_root / release_id),
        activation_pointer_fingerprint=ACTIVATION_STATE,
        planned_pointer_fingerprint=POINTER_FP,
        plan_content_fingerprint=PLAN_FP,
        files=(SimpleNamespace(), SimpleNamespace()),
        normal_freshness=True,
        activation_allowed_by_review_authorization=False,
        review_deployment=None,
        snapshot_contract_version="1.9",
        dashboard_contract_version="2.6",
        aggregate_sha256="5" * 64,
        manifest_sha256="6" * 64,
    )
    automation = DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.3",
        target_session=TARGET.isoformat(),
        prior_session="2026-08-27",
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_SNAPSHOT_PUBLICATION,
        reason_codes=("fixture",),
        observations=(
            ArtifactObservation(
                stage="snapshot_plan",
                status=ArtifactStatus.COMPLETED,
                path=str(plan_path),
                as_of_session=TARGET.isoformat(),
                logical_fingerprint=PLAN_FP,
            ),
        ),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="7" * 64,
    )
    config = custody.DailyEodDashboardSnapshotApplyConfig(
        target_session=TARGET,
        approval_plan_path=plan_path,
        approved_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        expected_current_state_fingerprint=CURRENT_STATE,
        review_acknowledgement_sha256=None,
        data_root=data_root,
        legacy_root=legacy_root,
        run_root=run_root,
        automation_paths=paths,
    )
    try:
        yield config, approval, automation
    finally:
        if plan_path.exists() or plan_path.is_symlink():
            plan_path.chmod(0o600)
            plan_path.unlink()


def _reserve(monkeypatch, config, approval, automation):
    monkeypatch.setattr(
        custody,
        "validate_approved_dashboard_snapshot_freshness",
        lambda **_kwargs: None,
    )
    return custody.reserve_dashboard_snapshot_apply(
        config=config,
        checked_at=CHECKED,
        expected_automation_plan_fingerprint=(
            automation.logical_content_fingerprint
        ),
        clock=lambda: datetime(2026, 8, 28, 21, 1, tzinfo=UTC),
        planner=lambda **_kwargs: automation,
        plan_reader=lambda _path: approval,
        state_reader=lambda _root, _legacy: CURRENT_STATE,
        activation_reader=lambda _root: SimpleNamespace(
            pointer_content_fingerprint=ACTIVATION_STATE
        ),
    )


def _active(config, approval):
    return SimpleNamespace(
        pointer=SimpleNamespace(pointer_content_fingerprint=POINTER_FP),
        manifest=SimpleNamespace(
            release_id=approval.release_id,
            current_session_date=TARGET.isoformat(),
        ),
        release_path=Path(approval.target_path),
        reference=SimpleNamespace(
            release_id=approval.release_id,
            aggregate_sha256=approval.aggregate_sha256,
            manifest_sha256=approval.manifest_sha256,
            snapshot_contract_version="1.9",
            dashboard_contract_version="2.6",
        ),
    )


def test_reservation_binds_exact_review_state_without_executing_apply(
    setup,
    monkeypatch,
) -> None:
    config, approval, automation = setup

    result = _reserve(monkeypatch, config, approval, automation)

    assert result.outcome == "reserved"
    assert result.approval_plan is approval
    assert result.event.details["release_id"] == approval.release_id
    assert result.as_dict()["apply_executed_by_custody"] is False
    assert result.as_dict()["production_write_count_by_custody"] == 0


def test_reservation_rejects_changed_state_activation_or_target(
    setup,
    monkeypatch,
) -> None:
    config, approval, automation = setup
    monkeypatch.setattr(
        custody,
        "validate_approved_dashboard_snapshot_freshness",
        lambda **_kwargs: None,
    )
    with pytest.raises(
        custody.DailyEodDashboardSnapshotApplyCustodyError,
        match="state changed",
    ):
        custody.reserve_dashboard_snapshot_apply(
            config=config,
            checked_at=CHECKED,
            expected_automation_plan_fingerprint=(
                automation.logical_content_fingerprint
            ),
            clock=lambda: datetime(2026, 8, 28, 21, 1, tzinfo=UTC),
            planner=lambda **_kwargs: automation,
            plan_reader=lambda _path: approval,
            state_reader=lambda _root, _legacy: "8" * 64,
            activation_reader=lambda _root: SimpleNamespace(
                pointer_content_fingerprint=ACTIVATION_STATE
            ),
        )

    changed_config = replace(config, run_root=config.run_root.parent / "run-2")
    changed_config.run_root.mkdir(mode=0o700)
    with pytest.raises(
        custody.DailyEodDashboardSnapshotApplyCustodyError,
        match="Activation changed",
    ):
        custody.reserve_dashboard_snapshot_apply(
            config=changed_config,
            checked_at=CHECKED,
            expected_automation_plan_fingerprint=(
                automation.logical_content_fingerprint
            ),
            clock=lambda: datetime(2026, 8, 28, 21, 1, tzinfo=UTC),
            planner=lambda **_kwargs: automation,
            plan_reader=lambda _path: approval,
            state_reader=lambda _root, _legacy: CURRENT_STATE,
            activation_reader=lambda _root: SimpleNamespace(
                pointer_content_fingerprint="9" * 64
            ),
        )


def test_success_requires_exact_active_pointer_and_closes_attempt(
    setup,
    monkeypatch,
) -> None:
    config, approval, automation = setup
    _reserve(monkeypatch, config, approval, automation)

    result = custody.record_dashboard_snapshot_apply_success(
        config=config,
        clock=lambda: datetime(2026, 8, 28, 21, 2, tzinfo=UTC),
        plan_reader=lambda _path: approval,
        active_reader=lambda *_args: _active(config, approval),
    )

    assert result.outcome == "succeeded"
    assert result.event.details["inventory_change_file_count"] == 3
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=TARGET,
    ) as journal:
        assert unresolved_started_event(journal.read_events()) is None


def test_recovery_never_writes_and_blocks_partial_state(
    setup,
    monkeypatch,
) -> None:
    config, approval, automation = setup
    _reserve(monkeypatch, config, approval, automation)

    result = custody.recover_dashboard_snapshot_apply(
        config=config,
        clock=lambda: datetime(2026, 8, 28, 21, 2, tzinfo=UTC),
        plan_reader=lambda _path: approval,
        active_reader=lambda *_args: (_ for _ in ()).throw(
            DashboardSnapshotPublicationError("absent")
        ),
        state_reader=lambda _root, _legacy: CURRENT_STATE,
        activation_reader=lambda _root: SimpleNamespace(
            pointer_content_fingerprint=ACTIVATION_STATE
        ),
    )

    assert result.outcome == "recovered_not_completed"
    assert result.as_dict()["production_write_count_by_custody"] == 0

    config2 = replace(config, run_root=config.run_root.parent / "run-partial")
    config2.run_root.mkdir(mode=0o700)
    _reserve(monkeypatch, config2, approval, automation)
    Path(approval.target_path).mkdir(parents=True)
    blocked = custody.recover_dashboard_snapshot_apply(
        config=config2,
        clock=lambda: datetime(2026, 8, 28, 21, 2, tzinfo=UTC),
        plan_reader=lambda _path: approval,
        active_reader=lambda *_args: (_ for _ in ()).throw(
            DashboardSnapshotPublicationError("inactive")
        ),
        state_reader=lambda _root, _legacy: CURRENT_STATE,
        activation_reader=lambda _root: SimpleNamespace(
            pointer_content_fingerprint=ACTIVATION_STATE
        ),
    )

    assert blocked.outcome == "recovery_blocked"


def test_config_accepts_exact_persistent_session_plan(setup) -> None:
    config, _approval, _automation = setup
    owner_root = Path("/var/tmp") / f"whalpha-snapshot-plan-{uuid4().hex}"
    workspace = owner_root / "daily-eod"
    session = workspace / "sessions" / f"session_date={TARGET.isoformat()}"
    try:
        session.mkdir(parents=True, mode=0o700)
        for directory in (workspace, workspace / "sessions", session):
            directory.chmod(0o700)
        plan_path = session / "dashboard-snapshot-plan.json"
        plan_path.write_bytes(b"{}")
        plan_path.chmod(0o444)

        custody._validate_config(replace(config, approval_plan_path=plan_path))

        wrong_session = session.parent / "session_date=2026-08-27"
        wrong_session.mkdir(mode=0o700)
        wrong_session.chmod(0o700)
        wrong_plan = wrong_session / "dashboard-snapshot-plan.json"
        with pytest.raises(
            custody.DailyEodDashboardSnapshotApplyCustodyError,
            match="session differs",
        ):
            custody._validate_config(
                replace(config, approval_plan_path=wrong_plan)
            )
    finally:
        shutil.rmtree(owner_root)
