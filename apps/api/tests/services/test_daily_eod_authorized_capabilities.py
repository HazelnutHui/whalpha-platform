from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.same_day_catchup import (
    CatchupApprovalPlanEvidenceV1,
    SameDayCatchupError,
)
from tip_api.providers.massive.transport import MassiveTransportResponseError
from tip_api.services.daily_eod_acquisition_custody import (
    AcquisitionCustodyResult,
    DailyEodAcquisitionConfig,
)
from tip_api.services.daily_eod_authorized_capabilities import (
    DailyEodAuthorizedCapabilities,
    DailyEodAuthorizedCapabilityConfig,
    DailyEodAuthorizedCapabilityError,
)
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_canonical_apply_custody import (
    CanonicalApplyCustodyResult,
)
from tip_api.services.daily_eod_coordinator import AuthorizedTransitionContext
from tip_api.services.daily_eod_readiness import (
    AcquisitionAttempt,
    AttemptOutcome,
    DailyEodReadinessPolicy,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunEvent
from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
    StandingOperation,
    DailyEodStandingAuthorizationError,
    build_standing_authorization_candidate,
)


NOW = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)
TARGET = date(2026, 8, 27)
LATEST = date(2026, 8, 26)
RUN_ROOT = Path("/home/hui/.local/state/tip-test-daily-eod")
REVISION = "a" * 40
POLICY = DailyEodReadinessPolicy().logical_fingerprint
PLAN_SHA = "b" * 64
STATE_SHA = "c" * 64


def paths() -> DailyEodAutomationPaths:
    return DailyEodAutomationPaths(
        data_root=APPROVED_CANONICAL_DATA_ROOT,
        phase1a_audit=Path("/tmp/phase1a.json"),
        prior_phase1b_audit=Path("/tmp/prior-phase1b.json"),
        phase1b_audit=Path("/tmp/phase1b.json"),
        prior_candidate_audit=Path("/tmp/prior-candidate.json"),
        candidate_audit=Path("/tmp/candidate.json"),
        entry_geometry_audit=Path("/tmp/entry.json"),
    )


def capability_config(**overrides) -> DailyEodAuthorizedCapabilityConfig:
    values = {
        "authorization_path": Path("/opt/tip-authorization/daily-eod.json"),
        "authorization_root": Path("/opt/tip-authorization"),
        "repository_root": Path("/opt/trading-intelligence-platform"),
        "expected_authorization_file_sha256": "d" * 64,
        "actual_host": "dell5820",
        "implementation_revision": REVISION,
        "readiness_policy_fingerprint": POLICY,
        "data_root": APPROVED_CANONICAL_DATA_ROOT,
        "run_root": RUN_ROOT,
        "automation_paths": paths(),
        "credential_path": Path("/not-read-in-test/massive.env"),
        "approved_plan_sha256": PLAN_SHA,
        "expected_current_state_fingerprint": STATE_SHA,
    }
    values.update(overrides)
    return DailyEodAuthorizedCapabilityConfig(**values)


def authorization(*, expires_at: datetime = NOW + timedelta(days=30)):
    return build_standing_authorization_candidate(
        authorization_id="daily-eod-test-authorization",
        approved_at=NOW - timedelta(days=1),
        valid_from=NOW - timedelta(days=1),
        expires_at=expires_at,
        host="dell5820",
        data_root=APPROVED_CANONICAL_DATA_ROOT,
        run_root=RUN_ROOT,
        implementation_revision=REVISION,
        readiness_policy_fingerprint=POLICY,
        allowed_operations=tuple(StandingOperation),
    )


def automation_plan(action: NextAction) -> DailyEodAutomationPlan:
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.0",
        target_session=TARGET.isoformat(),
        prior_session=LATEST.isoformat(),
        status=PlanStatus.WAITING_FOR_AUTHORIZED_INPUT,
        next_action=action,
        reason_codes=("test",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="e" * 64,
    )


def context(*, action: NextAction, apply: bool) -> AuthorizedTransitionContext:
    attempts = (
        (
            AcquisitionAttempt(
                sequence=1,
                observed_at=datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
                outcome=AttemptOutcome.FETCH_PACKAGE_READY,
            ),
        )
        if apply
        else ()
    )
    readiness = plan_daily_eod_readiness(
        checked_at=NOW,
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=action,
        attempts=attempts,
    )
    subject = "identity" if action is NextAction.PREPARE_IDENTITY_CATCHUP else "eod"
    return AuthorizedTransitionContext(
        acquisition=DailyEodAcquisitionConfig(
            target_session=TARGET,
            latest_canonical_session=LATEST,
            acquisition_action=action,
            package_path=Path("/tmp/adapter-package"),
            run_root=RUN_ROOT,
        ),
        approval_plan_path=Path("/tmp/adapter-plan.json"),
        automation_plan=automation_plan(action),
        readiness_plan=readiness,
        operation=f"{'apply' if apply else 'fetch'}_{subject}",
    )


def event(event_type: str, *, fingerprint: str = "f" * 64) -> DailyEodRunEvent:
    return DailyEodRunEvent(
        sequence=1,
        event_type=event_type,
        target_session=TARGET.isoformat(),
        observed_at=NOW.isoformat(),
        attempt_id="1" * 64,
        previous_event_fingerprint=None,
        details={},
        event_fingerprint=fingerprint,
    )


def acquisition_reservation(**_kwargs) -> AcquisitionCustodyResult:
    started = event("acquisition_started")
    return AcquisitionCustodyResult(
        outcome="reserved",
        attempt_id=started.attempt_id,
        event=started,
        reason_code="reserved",
    )


def acquisition_recording(**kwargs) -> AcquisitionCustodyResult:
    outcome = kwargs["outcome"]
    terminal = event(
        "acquisition_package_ready"
        if outcome is AttemptOutcome.FETCH_PACKAGE_READY
        else "acquisition_rate_limited"
        if outcome is AttemptOutcome.RATE_LIMITED
        else "acquisition_permanent_failed"
    )
    return AcquisitionCustodyResult(
        outcome=outcome.value,
        attempt_id=terminal.attempt_id,
        event=terminal,
        reason_code=f"fetch_{outcome.value}",
    )


def plan_evidence() -> CatchupApprovalPlanEvidenceV1:
    return CatchupApprovalPlanEvidenceV1(
        operation="eod",
        session_date=TARGET,
        plan_path="/tmp/adapter-plan.json",
        plan_file_sha256=PLAN_SHA,
        plan_content_sha256="2" * 64,
        data_root=str(APPROVED_CANONICAL_DATA_ROOT),
        fetch_package_path="/tmp/adapter-package",
        fetch_package_manifest_sha256="3" * 64,
        fetch_package_content_sha256="4" * 64,
        expected_current_state_fingerprint=STATE_SHA,
        publication_order=(
            str(APPROVED_CANONICAL_DATA_ROOT / "market-data/eod/session=2026-08-27"),
        ),
        inventory_change_file_count=2,
        inventory_change_bytes=100,
    )


def apply_reservation(**_kwargs) -> CanonicalApplyCustodyResult:
    started = event("canonical_apply_started")
    return CanonicalApplyCustodyResult(
        outcome="reserved",
        attempt_id=started.attempt_id,
        event=started,
        plan_evidence=plan_evidence(),
        automation_plan=None,
        reason_code="reserved",
    )


def apply_recording(**_kwargs) -> CanonicalApplyCustodyResult:
    completed = event("canonical_apply_succeeded")
    return CanonicalApplyCustodyResult(
        outcome="succeeded",
        attempt_id=completed.attempt_id,
        event=completed,
        plan_evidence=None,
        automation_plan=automation_plan(NextAction.PREPARE_EOD_CATCHUP),
        reason_code="canonical_stage_completed_and_replanned",
    )


class FakeTransport:
    def get_json(self, *_args, **_kwargs):
        return {"status": "OK"}


def build_capabilities(**overrides) -> DailyEodAuthorizedCapabilities:
    values = {
        "config": capability_config(),
        "clock": lambda: NOW,
        "authorization_reader": lambda **_kwargs: authorization(),
        "credential_loader": lambda _path: MassiveProviderConfig(api_key="test-key"),
        "transport": FakeTransport(),
        "acquisition_reserver": acquisition_reservation,
        "acquisition_recorder": acquisition_recording,
        "apply_reserver": apply_reservation,
        "apply_recorder": apply_recording,
        "planner": lambda **_kwargs: automation_plan(
            NextAction.PREPARE_EOD_CATCHUP
        ),
    }
    values.update(overrides)
    return DailyEodAuthorizedCapabilities(**values)


def test_construction_performs_no_authorization_or_credential_io() -> None:
    calls: list[str] = []

    build_capabilities(
        authorization_reader=lambda **_kwargs: calls.append("authorization"),
        credential_loader=lambda _path: calls.append("credential"),
    )

    assert calls == []


def test_identity_fetch_reports_actual_bounded_http_request_count() -> None:
    recorded = []

    def fetcher(*, transport, **_kwargs):
        transport.get_json("/page-1")
        transport.get_json("/page-2")
        return SimpleNamespace(request_count=2)

    def recorder(**kwargs):
        recorded.append(kwargs)
        return acquisition_recording(**kwargs)

    result = build_capabilities(
        identity_fetcher=fetcher,
        acquisition_recorder=recorder,
    ).fetch(
        context(action=NextAction.PREPARE_IDENTITY_CATCHUP, apply=False)
    )

    assert result.outcome == "succeeded"
    assert result.external_request_count == 2
    assert recorded[0]["outcome"] is AttemptOutcome.FETCH_PACKAGE_READY
    assert len(recorded[0]["authorization_decision_fingerprint"]) == 64


def test_expired_authorization_rejects_before_reservation_or_credential_read() -> None:
    calls: list[str] = []
    capabilities = build_capabilities(
        authorization_reader=lambda **_kwargs: authorization(
            expires_at=NOW - timedelta(seconds=1)
        ),
        acquisition_reserver=lambda **_kwargs: calls.append("reserve"),
        credential_loader=lambda _path: calls.append("credential"),
    )

    with pytest.raises(DailyEodStandingAuthorizationError, match="not active"):
        capabilities.fetch(
            context(action=NextAction.PREPARE_EOD_CATCHUP, apply=False)
        )

    assert calls == []


def test_rate_limit_records_exact_request_count_and_retry_after() -> None:
    recorded = []

    def fetcher(*, transport, **_kwargs):
        transport.get_json("/eod")

    class RateLimitedTransport:
        def get_json(self, *_args, **_kwargs):
            raise MassiveTransportResponseError(429, "limited", 1200)

    def recorder(**kwargs):
        recorded.append(kwargs)
        return acquisition_recording(**kwargs)

    result = build_capabilities(
        transport=RateLimitedTransport(),
        eod_fetcher=fetcher,
        acquisition_recorder=recorder,
    ).fetch(context(action=NextAction.PREPARE_EOD_CATCHUP, apply=False))

    assert result.outcome == "waiting"
    assert result.external_request_count == 1
    assert recorded[0]["outcome"] is AttemptOutcome.RATE_LIMITED
    assert recorded[0]["retry_after_seconds"] == 1200


def test_unexpected_fetch_error_leaves_reservation_unresolved() -> None:
    calls: list[str] = []

    def fetcher(**_kwargs):
        raise RuntimeError("unexpected")

    with pytest.raises(RuntimeError, match="unexpected"):
        build_capabilities(
            eod_fetcher=fetcher,
            acquisition_recorder=lambda **_kwargs: calls.append("record"),
        ).fetch(context(action=NextAction.PREPARE_EOD_CATCHUP, apply=False))

    assert calls == []


def test_apply_binds_reservation_authorization_and_exact_executor_inputs() -> None:
    reserved = []
    executed = []
    recorded = []

    def reserver(**kwargs):
        reserved.append(kwargs)
        return apply_reservation(**kwargs)

    def executor(**kwargs):
        executed.append(kwargs)

    def recorder(**kwargs):
        recorded.append(kwargs)
        return apply_recording(**kwargs)

    result = build_capabilities(
        apply_reserver=reserver,
        apply_executor=executor,
        apply_recorder=recorder,
    ).apply(context(action=NextAction.PREPARE_EOD_CATCHUP, apply=True))

    assert result.outcome == "succeeded"
    assert result.production_write_count == 1
    assert reserved[0]["authorization_file_sha256"] == "d" * 64
    assert executed[0]["approved_plan_sha256"] == PLAN_SHA
    assert executed[0]["expected_current_state_fingerprint"] == STATE_SHA
    assert executed[0]["expected_operation"] == "eod"
    assert len(recorded[0]["authorization_decision_fingerprint"]) == 64


def test_apply_exception_never_records_success_or_replays() -> None:
    calls: list[str] = []

    def executor(**_kwargs):
        calls.append("apply")
        raise SameDayCatchupError("partial or unknown")

    with pytest.raises(SameDayCatchupError, match="partial or unknown"):
        build_capabilities(
            apply_executor=executor,
            apply_recorder=lambda **_kwargs: calls.append("record"),
        ).apply(context(action=NextAction.PREPARE_EOD_CATCHUP, apply=True))

    assert calls == ["apply"]


def test_apply_requires_exact_external_plan_bindings() -> None:
    with pytest.raises(
        DailyEodAuthorizedCapabilityError,
        match="exact approved plan",
    ):
        build_capabilities(
            config=capability_config(approved_plan_sha256=None),
        ).apply(context(action=NextAction.PREPARE_EOD_CATCHUP, apply=True))


def test_configuration_rejects_noncanonical_data_root() -> None:
    with pytest.raises(DailyEodAuthorizedCapabilityError, match="configuration"):
        build_capabilities(
            config=capability_config(
                data_root=Path("/data"),
                automation_paths=replace(paths(), data_root=Path("/data")),
            )
        )
