from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.services.daily_eod_acquisition_custody import AcquisitionCustodyResult
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_coordinator import (
    DailyEodCoordinatorConfig,
    RecoveryTransitionContext,
)
from tip_api.services.daily_eod_canonical_apply_custody import (
    CanonicalApplyCustodyResult,
)
from tip_api.services.daily_eod_executor import DailyEodRecoveryResult
from tip_api.services.daily_eod_recovery_router import (
    DailyEodRecoveryRouterError,
    recover_one_daily_eod_transition,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunEvent


TARGET = date(2026, 8, 27)
NOW = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)


def paths() -> DailyEodAutomationPaths:
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
    )


def config() -> DailyEodCoordinatorConfig:
    return DailyEodCoordinatorConfig(
        target_session=TARGET,
        latest_canonical_session=date(2026, 8, 26),
        paths=paths(),
        run_root=Path("/tmp/daily-run-root"),
        package_path=Path("/tmp/daily-package"),
        approval_plan_path=Path("/tmp/daily-plan.json"),
        panel_cache_root=Path("/tmp/panel-cache"),
        candidate_work_dir=Path("/tmp/candidate-work"),
    )


def plan() -> DailyEodAutomationPlan:
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.1",
        target_session=TARGET.isoformat(),
        prior_session="2026-08-26",
        status=PlanStatus.WAITING_FOR_AUTHORIZED_INPUT,
        next_action=NextAction.PREPARE_EOD_CATCHUP,
        reason_codes=("fixture",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="a" * 64,
    )


def event(event_type: str, details: dict[str, object]) -> DailyEodRunEvent:
    return DailyEodRunEvent(
        sequence=1,
        event_type=event_type,
        target_session=TARGET.isoformat(),
        observed_at="2026-08-27T20:30:00+00:00",
        attempt_id="b" * 64,
        previous_event_fingerprint=None,
        details=details,
        event_fingerprint="c" * 64,
    )


def terminal(event_type: str) -> DailyEodRunEvent:
    return DailyEodRunEvent(
        sequence=2,
        event_type=event_type,
        target_session=TARGET.isoformat(),
        observed_at="2026-08-27T21:00:00+00:00",
        attempt_id="b" * 64,
        previous_event_fingerprint="c" * 64,
        details={},
        event_fingerprint="d" * 64,
    )


def context(pending: DailyEodRunEvent, action: str) -> RecoveryTransitionContext:
    return RecoveryTransitionContext(
        coordinator=config(),
        pending_event=pending,
        automation_plan=plan(),
        recovery_action=action,
    )


def journal(pending: DailyEodRunEvent):
    return lambda _root, _session: (pending,)


def test_routes_acquisition_recovery_without_provider_request() -> None:
    pending = event(
        "acquisition_started",
        {"acquisition_action": NextAction.PREPARE_EOD_CATCHUP.value},
    )
    calls = []

    def recoverer(**kwargs):
        calls.append(kwargs)
        return AcquisitionCustodyResult(
            outcome="recovered_package_ready",
            attempt_id=pending.attempt_id,
            event=terminal("acquisition_recovered_package_ready"),
            readiness_plan=None,
            package_evidence=None,
            reason_code="completed_package_formally_reconciled",
        )

    evidence = recover_one_daily_eod_transition(
        context(pending, "recover_acquisition_attempt"),
        clock=lambda: NOW,
        journal_reader=journal(pending),
        acquisition_recoverer=recoverer,
    )

    assert len(calls) == 1
    assert calls[0]["config"].package_path == Path("/tmp/daily-package")
    assert evidence.outcome == "recovered_package_ready"
    assert evidence.external_request_count == 0
    assert evidence.production_write_count == 0
    assert evidence.action_replayed is False


def test_routes_canonical_apply_using_only_immutable_start_bindings() -> None:
    pending = event(
        "canonical_apply_started",
        {
            "acquisition_action": NextAction.PREPARE_IDENTITY_CATCHUP.value,
            "operation": "apply_identity",
            "approval_plan_sha256": "e" * 64,
            "expected_current_state_fingerprint": "f" * 64,
        },
    )
    calls = []

    def recoverer(**kwargs):
        calls.append(kwargs)
        return CanonicalApplyCustodyResult(
            outcome="recovered_not_completed",
            attempt_id=pending.attempt_id,
            event=terminal("canonical_apply_recovered_not_completed"),
            plan_evidence=None,
            automation_plan=plan(),
            reason_code="no_canonical_write_detected",
        )

    evidence = recover_one_daily_eod_transition(
        context(pending, "recover_canonical_apply"),
        journal_reader=journal(pending),
        apply_recoverer=recoverer,
    )

    recovery_config = calls[0]["config"]
    assert recovery_config.approved_plan_sha256 == "e" * 64
    assert recovery_config.expected_current_state_fingerprint == "f" * 64
    assert recovery_config.data_root == Path("/data/trading-intelligence-platform")
    assert evidence.outcome == "recovered_not_completed"


def test_routes_offline_recovery_without_replaying_action() -> None:
    pending = event(
        "action_started",
        {
            "action": NextAction.CALCULATE_PHASE1A.value,
            "plan_fingerprint": "e" * 64,
            "execution_input_fingerprint": "f" * 64,
        },
    )
    calls = []

    def recoverer(**kwargs):
        calls.append(kwargs)
        return DailyEodRecoveryResult(
            outcome="recovered_succeeded",
            action=NextAction.CALCULATE_PHASE1A,
            attempt_id=pending.attempt_id,
            event=terminal("action_recovered_succeeded"),
            current_plan=plan(),
            reason_code="completed_artifact_formally_reconciled",
        )

    evidence = recover_one_daily_eod_transition(
        context(pending, "recover_offline_action"),
        journal_reader=journal(pending),
        offline_recoverer=recoverer,
    )

    assert len(calls) == 1
    assert calls[0]["config"].panel_cache_root == Path("/tmp/panel-cache")
    assert evidence.action_replayed is False


def test_rejects_changed_pending_event_before_calling_recovery() -> None:
    pending = event(
        "acquisition_started",
        {"acquisition_action": NextAction.PREPARE_EOD_CATCHUP.value},
    )
    changed = replace(pending, event_fingerprint="9" * 64)

    with pytest.raises(DailyEodRecoveryRouterError, match="changed"):
        recover_one_daily_eod_transition(
            context(pending, "recover_acquisition_attempt"),
            journal_reader=journal(changed),
            acquisition_recoverer=lambda **_kwargs: pytest.fail(
                "recovery must not run"
            ),
        )


def test_rejects_wrong_family_result_and_malformed_apply_binding() -> None:
    pending = event(
        "canonical_apply_started",
        {
            "acquisition_action": NextAction.PREPARE_EOD_CATCHUP.value,
            "operation": "apply_eod",
            "approval_plan_sha256": "not-a-fingerprint",
            "expected_current_state_fingerprint": "f" * 64,
        },
    )
    with pytest.raises(DailyEodRecoveryRouterError, match="malformed"):
        recover_one_daily_eod_transition(
            context(pending, "recover_canonical_apply"),
            journal_reader=journal(pending),
        )

    acquisition = event(
        "acquisition_started",
        {"acquisition_action": NextAction.PREPARE_EOD_CATCHUP.value},
    )
    with pytest.raises(DailyEodRecoveryRouterError, match="inconsistent"):
        recover_one_daily_eod_transition(
            context(acquisition, "recover_acquisition_attempt"),
            journal_reader=journal(acquisition),
            acquisition_recoverer=lambda **_kwargs: AcquisitionCustodyResult(
                outcome="recovered_not_completed",
                attempt_id=acquisition.attempt_id,
                event=terminal("action_recovered_not_completed"),
                readiness_plan=None,
                package_evidence=None,
                reason_code="wrong_family",
            ),
        )
