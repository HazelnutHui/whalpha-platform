from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import shutil
from types import SimpleNamespace

from tip_api.services import daily_eod_oci_deployment_custody as custody
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
from tip_api.services.oci_dashboard_deployment_state import build_remote_state


TARGET_SESSION = date(2026, 8, 28)
RELEASE = "2026-08-29T120000Z-aaaaaaaaaaaa"
CURRENT = "2026-08-28T120000Z-bbbbbbbbbbbb"
NOW = datetime(2026, 8, 29, 12, tzinfo=UTC)
BUNDLE_FP = "1" * 64
CONFIG_SHA = "2" * 64


def _paths(bundle_path: Path, tmp_path: Path) -> DailyEodAutomationPaths:
    def p(name: str) -> Path:
        return Path(f"/tmp/{tmp_path.name}-{name}")

    return DailyEodAutomationPaths(
        data_root=tmp_path / "data",
        phase1a_audit=p("phase1a"),
        prior_phase1b_audit=p("prior-phase1b"),
        phase1b_audit=p("phase1b"),
        prior_candidate_audit=p("prior-candidate"),
        candidate_audit=p("candidate"),
        entry_geometry_audit=p("entry"),
        phase2_audit=p("phase2"),
        preview_bundle=p("preview"),
        strategy_channel_audit=p("strategy"),
        market_intelligence_output_root=p("mi"),
        market_intelligence_approval_plan=p("mi-plan"),
        snapshot_output_root=p("snapshot"),
        snapshot_approval_plan=p("snapshot-plan"),
        serving_bundle_root=bundle_path.parent,
    )


def _fixture(tmp_path):
    root = Path(f"/tmp/{tmp_path.name}-bundle")
    bundle_path = root / RELEASE
    bundle_path.mkdir(parents=True)
    run_root = tmp_path / "run"
    run_root.mkdir(mode=0o700)
    paths = _paths(bundle_path, tmp_path)
    plan = DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.4",
        target_session=TARGET_SESSION.isoformat(),
        prior_session="2026-08-27",
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        reason_codes=("fixture",),
        observations=(
            ArtifactObservation(
                stage="serving_bundle",
                status=ArtifactStatus.COMPLETED,
                path=str(bundle_path),
                as_of_session=TARGET_SESSION.isoformat(),
                logical_fingerprint=BUNDLE_FP,
            ),
        ),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="3" * 64,
    )
    config = custody.DailyEodOciDeploymentConfig(
        target_session=TARGET_SESSION,
        bundle_path=bundle_path,
        approved_bundle_logical_fingerprint=BUNDLE_FP,
        expected_remote_state_fingerprint="4" * 64,
        expected_current_release=CURRENT,
        deployment_config_file_sha256=CONFIG_SHA,
        run_root=run_root,
        automation_paths=paths,
    )
    binding = SimpleNamespace(
        manifest_sha256="5" * 64,
        checksums_sha256="6" * 64,
        bundle=SimpleNamespace(
            path=bundle_path,
            bundle_logical_fingerprint=BUNDLE_FP,
            deployment_manifest=SimpleNamespace(
                release_id=RELEASE,
                git_commit="a" * 40,
            ),
        ),
    )
    pre = _state(current=CURRENT, target=False)
    config = replace(config, expected_remote_state_fingerprint=pre.state_fingerprint)
    post = _state(current=RELEASE, target=True, binding=binding)
    return root, config, plan, binding, pre, post


def _state(*, current: str, target: bool, binding=None, staging=()):
    deployed = current == RELEASE and binding is not None
    return build_remote_state(
        inspected_at=NOW,
        inspected_target_release=RELEASE,
        remote_host="hui",
        remote_user="ubuntu",
        remote_base="/srv/whalpha",
        current_release_id=current,
        current_manifest_sha256=(binding.manifest_sha256 if deployed else "7" * 64),
        current_checksums_sha256=(binding.checksums_sha256 if deployed else "8" * 64),
        current_bundle_logical_fingerprint=(BUNDLE_FP if deployed else "9" * 64),
        current_source_revision=("a" * 40 if deployed else "b" * 40),
        target_release_exists=target,
        staging_release_ids=staging,
        failed_release_ids=(),
        nginx_active=True,
        nginx_enabled=True,
        auth_service_active=True,
        auth_service_enabled=True,
        auth_listener_localhost_only=True,
        unexpected_private_listener=False,
        protected_routes_verified=True,
        guest_session_verified=True,
        guest_and_credential_route_policy_identical=True,
        credential_login_tested=False,
        failed_system_unit_count=0,
    )


def _reserve(monkeypatch, config, plan, binding, pre):
    monkeypatch.setattr(custody, "read_deployment_binding", lambda *_a, **_k: binding)
    return custody.reserve_oci_deployment(
        config=config,
        checked_at=NOW,
        expected_automation_plan_fingerprint=plan.logical_content_fingerprint,
        remote_state=pre,
        clock=lambda: NOW,
        planner=lambda **_kwargs: plan,
    )


def test_reserve_then_independent_postcondition_closes_exact_attempt(tmp_path, monkeypatch):
    root, config, plan, binding, pre, post = _fixture(tmp_path)
    try:
        reserved = _reserve(monkeypatch, config, plan, binding, pre)
        assert reserved.outcome == "reserved"
        assert reserved.event.details["manifest_sha256"] == binding.manifest_sha256
        completed = custody.record_oci_deployment_success(
            config=config,
            remote_state=post,
            clock=lambda: NOW,
        )
        assert completed.outcome == "succeeded"
        with locked_daily_eod_run_journal(
            run_root=config.run_root, target_session=TARGET_SESSION
        ) as journal:
            assert unresolved_started_event(journal.read_events()) is None
    finally:
        shutil.rmtree(root)


def test_recovery_never_replays_and_distinguishes_unchanged_from_partial(tmp_path, monkeypatch):
    root, config, plan, binding, pre, _post = _fixture(tmp_path)
    try:
        _reserve(monkeypatch, config, plan, binding, pre)
        result = custody.recover_oci_deployment(
            config=config,
            remote_state=pre,
            clock=lambda: NOW,
        )
        assert result.outcome == "recovered_not_completed"
        assert result.event.details["deployment_replayed"] is False

        run2 = tmp_path / "run2"
        run2.mkdir(mode=0o700)
        config2 = replace(config, run_root=run2)
        _reserve(monkeypatch, config2, plan, binding, pre)
        partial = _state(current=CURRENT, target=False, staging=(RELEASE,))
        blocked = custody.recover_oci_deployment(
            config=config2,
            remote_state=partial,
            clock=lambda: NOW,
        )
        assert blocked.outcome == "recovery_blocked"
    finally:
        shutil.rmtree(root)
