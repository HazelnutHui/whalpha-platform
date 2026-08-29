from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_coordinator import (
    DailyEodCoordinatorConfig,
    PublicationTransitionContext,
)
from tip_api.services.daily_eod_dashboard_snapshot_apply_capability import (
    DailyEodDashboardSnapshotApplyCapability,
    DailyEodDashboardSnapshotApplyCapabilityConfig,
)
from tip_api.services.daily_eod_dashboard_snapshot_apply_custody import (
    DashboardSnapshotApplyCustodyResult,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunEvent


TARGET = date(2026, 8, 28)
NOW = datetime(2026, 8, 28, 21, 0, tzinfo=UTC)


def _paths() -> DailyEodAutomationPaths:
    return DailyEodAutomationPaths(
        data_root=Path("/data/trading-intelligence-platform"),
        phase1a_audit=Path("/tmp/phase1a"),
        prior_phase1b_audit=Path("/tmp/prior-phase1b"),
        phase1b_audit=Path("/tmp/phase1b"),
        prior_candidate_audit=Path("/tmp/prior-candidate"),
        candidate_audit=Path("/tmp/candidate"),
        entry_geometry_audit=Path("/tmp/entry"),
        phase2_audit=Path("/tmp/phase2"),
        preview_bundle=Path("/tmp/preview"),
        strategy_channel_audit=Path("/tmp/strategy"),
        market_intelligence_output_root=Path("/tmp/mi-output"),
        market_intelligence_approval_plan=Path("/tmp/mi-plan.json"),
        snapshot_output_root=Path("/tmp/snapshot-output"),
        snapshot_approval_plan=Path("/tmp/snapshot-plan.json"),
        serving_bundle_root=Path("/tmp/tip-serving-bundle"),
    )


def _plan() -> DailyEodAutomationPlan:
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.3",
        target_session=TARGET.isoformat(),
        prior_session="2026-08-27",
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_SNAPSHOT_PUBLICATION,
        reason_codes=("fixture",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="a" * 64,
    )


def _event(event_type: str) -> DailyEodRunEvent:
    return DailyEodRunEvent(
        sequence=1 if event_type.endswith("started") else 2,
        event_type=event_type,
        target_session=TARGET.isoformat(),
        observed_at=NOW.isoformat(),
        attempt_id="b" * 64,
        previous_event_fingerprint=None,
        details={},
        event_fingerprint="c" * 64,
    )


def test_capability_reserves_executes_and_records_exactly_one_plan() -> None:
    paths = _paths()
    plan = _plan()
    coordinator = DailyEodCoordinatorConfig(
        target_session=TARGET,
        latest_canonical_session=TARGET,
        paths=paths,
        run_root=Path("/var/lib/trading-intelligence-platform/daily-eod"),
        package_path=Path("/tmp/package"),
        approval_plan_path=Path("/tmp/data-plan.json"),
    )
    context = PublicationTransitionContext(
        coordinator=coordinator,
        automation_plan=plan,
        checked_at=NOW,
        operation="apply_dashboard_snapshot",
        publication_id="snapshot-1",
        approval_plan_content_fingerprint="d" * 64,
    )
    approval = SimpleNamespace(
        release_id="snapshot-1",
        plan_content_fingerprint="d" * 64,
        files=(SimpleNamespace(), SimpleNamespace()),
    )
    calls = []

    def reserve(**kwargs):
        calls.append(("reserve", kwargs))
        return DashboardSnapshotApplyCustodyResult(
            outcome="reserved",
            attempt_id="b" * 64,
            event=_event("dashboard_snapshot_apply_started"),
            approval_plan=approval,
            active_snapshot=None,
            reason_code="reserved",
        )

    def execute(**kwargs):
        calls.append(("execute", kwargs))

    def record(**kwargs):
        calls.append(("record", kwargs))
        return DashboardSnapshotApplyCustodyResult(
            outcome="succeeded",
            attempt_id="b" * 64,
            event=_event("dashboard_snapshot_apply_succeeded"),
            approval_plan=approval,
            active_snapshot=SimpleNamespace(),
            reason_code="dashboard_snapshot_active_state_formally_proven",
        )

    capability = DailyEodDashboardSnapshotApplyCapability(
        config=DailyEodDashboardSnapshotApplyCapabilityConfig(
            data_root=paths.data_root,
            legacy_root=Path("/repo/build/private-dashboard"),
            run_root=coordinator.run_root,
            automation_paths=paths,
            approval_plan_path=paths.snapshot_approval_plan,
            approved_plan_sha256="e" * 64,
            expected_current_state_fingerprint="f" * 64,
        ),
        clock=lambda: NOW,
        planner=lambda **_kwargs: plan,
        apply_executor=execute,
        reserver=reserve,
        recorder=record,
    )

    evidence = capability.apply(context)

    assert [name for name, _ in calls] == ["reserve", "execute", "record"]
    assert calls[1][1]["plan"] is approval
    assert calls[1][1]["legacy_root"] == Path("/repo/build/private-dashboard")
    assert evidence.production_write_count == 3
    assert evidence.external_request_count == 0
    assert evidence.publication_id == "snapshot-1"
