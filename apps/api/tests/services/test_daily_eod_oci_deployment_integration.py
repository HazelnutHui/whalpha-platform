from __future__ import annotations

import shutil
from datetime import UTC, date, datetime
from pathlib import Path
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
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorConfig,
    coordinate_daily_eod_transition,
)
from tip_api.services.daily_eod_oci_deployment_capability import (
    DailyEodOciDeploymentCapability,
    DailyEodOciDeploymentCapabilityConfig,
)
from tip_api.services.daily_eod_run_journal import locked_daily_eod_run_journal
from tip_api.services.oci_dashboard_deployment_state import build_remote_state


SESSION = date(2026, 8, 28)
NOW = datetime(2026, 8, 29, 12, tzinfo=UTC)
RELEASE = "2026-08-29T120000Z-aaaaaaaaaaaa"
CURRENT = "2026-08-28T120000Z-bbbbbbbbbbbb"
BUNDLE_FP = "1" * 64
MANIFEST_SHA = "2" * 64
CHECKSUMS_SHA = "3" * 64
SOURCE_REVISION = "a" * 40
CONFIG_SHA = "4" * 64


class FakeTransport:
    def __init__(self, pre_state, post_state):
        self.states = [pre_state, post_state]
        self.calls = []

    def inspect(self, *, target_release):
        self.calls.append(("inspect", target_release))
        return self.states.pop(0)

    def apply(self, *, bundle_path, release_id, expected_current_release):
        self.calls.append(
            ("apply", bundle_path, release_id, expected_current_release)
        )


def test_complete_coordinator_deployment_uses_fake_transport_and_exact_journal(
    tmp_path,
    monkeypatch,
) -> None:
    bundle_root = Path(f"/tmp/{tmp_path.name}-integrated-serving-bundle")
    bundle_path = bundle_root / RELEASE
    bundle_path.mkdir(parents=True)
    run_root = tmp_path / "daily-run"
    run_root.mkdir(mode=0o700)
    paths = _paths(tmp_path, bundle_root)
    plan = _plan(bundle_path)
    binding = SimpleNamespace(
        manifest_sha256=MANIFEST_SHA,
        checksums_sha256=CHECKSUMS_SHA,
        bundle=SimpleNamespace(
            path=bundle_path,
            bundle_logical_fingerprint=BUNDLE_FP,
            deployment_manifest=SimpleNamespace(
                release_id=RELEASE,
                git_commit=SOURCE_REVISION,
            ),
        ),
    )
    pre = _state(
        current_release=CURRENT,
        manifest_sha="5" * 64,
        checksums_sha="6" * 64,
        bundle_fingerprint="7" * 64,
        source_revision="b" * 40,
        target_exists=False,
    )
    post = _state(
        current_release=RELEASE,
        manifest_sha=MANIFEST_SHA,
        checksums_sha=CHECKSUMS_SHA,
        bundle_fingerprint=BUNDLE_FP,
        source_revision=SOURCE_REVISION,
        target_exists=True,
    )
    transport = FakeTransport(pre, post)
    monkeypatch.setattr(
        custody,
        "read_deployment_binding",
        lambda *_args, **_kwargs: binding,
    )

    def reserve(**kwargs):
        return custody.reserve_oci_deployment(
            **kwargs,
            planner=lambda **_ignored: plan,
        )

    capability = DailyEodOciDeploymentCapability(
        config=DailyEodOciDeploymentCapabilityConfig(
            run_root=run_root,
            automation_paths=paths,
            bundle_path=bundle_path,
            approved_bundle_logical_fingerprint=BUNDLE_FP,
            expected_remote_state_fingerprint=pre.state_fingerprint,
            expected_current_release=CURRENT,
            deployment_config_file_sha256=CONFIG_SHA,
        ),
        transport=transport,
        clock=lambda: NOW,
        reserver=reserve,
        binding_reader=lambda *_args, **_kwargs: binding,
    )
    config = DailyEodCoordinatorConfig(
        target_session=SESSION,
        latest_canonical_session=SESSION,
        paths=paths,
        run_root=run_root,
        package_path=Path(f"/tmp/{tmp_path.name}-package"),
        approval_plan_path=Path(f"/tmp/{tmp_path.name}-plan.json"),
    )
    try:
        result = coordinate_daily_eod_transition(
            config=config,
            checked_at=NOW,
            deploy_oci_dashboard=True,
            deployment_capability=capability.deploy,
            planner=lambda **_ignored: plan,
        )

        assert result.status is CoordinatorStatus.TRANSITION_EXECUTED
        assert result.next_action == "deploy_oci_dashboard"
        assert result.external_request_count == 3
        assert result.production_write_count == 1
        assert transport.calls == [
            ("inspect", RELEASE),
            ("apply", bundle_path, RELEASE, CURRENT),
            ("inspect", RELEASE),
        ]
        with locked_daily_eod_run_journal(
            run_root=run_root,
            target_session=SESSION,
        ) as journal:
            events = journal.read_events()
        assert tuple(event.event_type for event in events) == (
            "oci_deployment_started",
            "oci_deployment_succeeded",
        )
        assert events[0].details["expected_remote_state_fingerprint"] == (
            pre.state_fingerprint
        )
        assert events[1].details["post_state_fingerprint"] == (
            post.state_fingerprint
        )
    finally:
        shutil.rmtree(bundle_root)


def _paths(tmp_path: Path, bundle_root: Path) -> DailyEodAutomationPaths:
    def temporary(name: str) -> Path:
        return Path(f"/tmp/{tmp_path.name}-{name}")

    return DailyEodAutomationPaths(
        data_root=tmp_path / "data",
        phase1a_audit=temporary("phase1a"),
        prior_phase1b_audit=temporary("prior-phase1b"),
        phase1b_audit=temporary("phase1b"),
        prior_candidate_audit=temporary("prior-candidate"),
        candidate_audit=temporary("candidate"),
        entry_geometry_audit=temporary("entry"),
        phase2_audit=temporary("phase2"),
        preview_bundle=temporary("preview"),
        strategy_channel_audit=temporary("strategy"),
        market_intelligence_output_root=temporary("mi-output"),
        market_intelligence_approval_plan=temporary("mi-plan"),
        snapshot_output_root=temporary("snapshot-output"),
        snapshot_approval_plan=temporary("snapshot-plan"),
        serving_bundle_root=bundle_root,
    )


def _plan(bundle_path: Path) -> DailyEodAutomationPlan:
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.5",
        target_session=SESSION.isoformat(),
        prior_session="2026-08-27",
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        reason_codes=("fixture",),
        observations=(
            ArtifactObservation(
                stage="serving_bundle",
                status=ArtifactStatus.COMPLETED,
                path=str(bundle_path),
                as_of_session=SESSION.isoformat(),
                logical_fingerprint=BUNDLE_FP,
            ),
        ),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="8" * 64,
    )


def _state(
    *,
    current_release: str,
    manifest_sha: str,
    checksums_sha: str,
    bundle_fingerprint: str,
    source_revision: str,
    target_exists: bool,
):
    return build_remote_state(
        inspected_at=NOW,
        inspected_target_release=RELEASE,
        remote_host="hui",
        remote_user="ubuntu",
        remote_base="/srv/whalpha",
        current_release_id=current_release,
        current_manifest_sha256=manifest_sha,
        current_checksums_sha256=checksums_sha,
        current_bundle_logical_fingerprint=bundle_fingerprint,
        current_source_revision=source_revision,
        target_release_exists=target_exists,
        staging_release_ids=(),
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
