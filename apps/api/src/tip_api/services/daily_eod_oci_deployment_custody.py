"""Durable reservation and no-replay recovery for one OCI Dashboard deployment."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_run_journal import (
    OCI_DEPLOYMENT_START_EVENT,
    DailyEodRunEvent,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)
from tip_api.services.oci_dashboard_deployment_state import (
    MAXIMUM_INSPECTION_AGE,
    OciDashboardDeploymentBinding,
    OciDashboardDeploymentStateError,
    OciDashboardRemoteStateV1,
    read_deployment_binding,
    remote_state_is_unchanged_not_completed,
    validate_remote_postcondition,
    validate_remote_precondition,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_daily_eod_serving_bundle_location,
)


CONTRACT_VERSION = "daily-eod-oci-deployment-custody/1.0"


class DailyEodOciDeploymentCustodyError(RuntimeError):
    """Raised when one OCI deployment cannot retain exact custody."""


@dataclass(frozen=True, slots=True)
class DailyEodOciDeploymentConfig:
    target_session: date
    bundle_path: Path
    approved_bundle_logical_fingerprint: str
    expected_remote_state_fingerprint: str
    expected_current_release: str
    deployment_config_file_sha256: str
    run_root: Path
    automation_paths: DailyEodAutomationPaths


@dataclass(frozen=True, slots=True)
class OciDeploymentCustodyResult:
    outcome: str
    attempt_id: str
    event: DailyEodRunEvent
    binding: OciDashboardDeploymentBinding | None
    remote_state: OciDashboardRemoteStateV1
    reason_code: str


Clock = Callable[[], datetime]
Planner = Callable[..., DailyEodAutomationPlan]


def reserve_oci_deployment(
    *,
    config: DailyEodOciDeploymentConfig,
    checked_at: datetime,
    expected_automation_plan_fingerprint: str,
    remote_state: OciDashboardRemoteStateV1,
    clock: Clock = lambda: datetime.now(UTC),
    planner: Planner = plan_daily_eod_automation,
) -> OciDeploymentCustodyResult:
    _validate_config(config)
    observed = _aware_utc(clock())
    checked = _aware_utc(checked_at)
    if observed < checked or observed - checked > MAXIMUM_INSPECTION_AGE:
        raise DailyEodOciDeploymentCustodyError("deployment review is stale")
    binding = read_deployment_binding(
        config.bundle_path,
        expected_bundle_logical_fingerprint=config.approved_bundle_logical_fingerprint,
    )
    release = binding.bundle.deployment_manifest.release_id
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodOciDeploymentCustodyError("daily run has an unresolved attempt")
        plan = planner(target_session=config.target_session, paths=config.automation_paths)
        _validate_plan(plan, config, expected_automation_plan_fingerprint)
        try:
            validate_remote_precondition(
                remote_state,
                target_release=release,
                expected_state_fingerprint=config.expected_remote_state_fingerprint,
                expected_current_release=config.expected_current_release,
                checked_at=observed,
            )
        except OciDashboardDeploymentStateError as exc:
            raise DailyEodOciDeploymentCustodyError(
                "remote deployment precondition failed"
            ) from exc
        input_fingerprint = _fingerprint(
            {
                "automation_plan_fingerprint": plan.logical_content_fingerprint,
                "bundle_logical_fingerprint": binding.bundle.bundle_logical_fingerprint,
                "manifest_sha256": binding.manifest_sha256,
                "checksums_sha256": binding.checksums_sha256,
                "expected_remote_state_fingerprint": config.expected_remote_state_fingerprint,
                "expected_current_release": config.expected_current_release,
                "deployment_config_file_sha256": config.deployment_config_file_sha256,
            }
        )
        attempt_id = new_attempt_id(
            target_session=config.target_session,
            plan_fingerprint=input_fingerprint,
            sequence=len(events) + 1,
        )
        event = journal.append(
            event_type=OCI_DEPLOYMENT_START_EVENT,
            attempt_id=attempt_id,
            observed_at=observed,
            details={
                "custody_contract": CONTRACT_VERSION,
                "operation": "deploy_oci_dashboard",
                "automation_plan_fingerprint": plan.logical_content_fingerprint,
                "bundle_path": str(binding.bundle.path),
                "release_id": release,
                "source_revision": binding.bundle.deployment_manifest.git_commit,
                "bundle_logical_fingerprint": binding.bundle.bundle_logical_fingerprint,
                "manifest_sha256": binding.manifest_sha256,
                "checksums_sha256": binding.checksums_sha256,
                "expected_remote_state_fingerprint": config.expected_remote_state_fingerprint,
                "expected_current_release": config.expected_current_release,
                "deployment_config_file_sha256": config.deployment_config_file_sha256,
                "execution_input_fingerprint": input_fingerprint,
            },
        )
    return OciDeploymentCustodyResult(
        "reserved",
        attempt_id,
        event,
        binding,
        remote_state,
        "oci_deployment_reserved_before_remote_mutation",
    )


def record_oci_deployment_success(
    *,
    config: DailyEodOciDeploymentConfig,
    remote_state: OciDashboardRemoteStateV1,
    clock: Clock = lambda: datetime.now(UTC),
) -> OciDeploymentCustodyResult:
    _validate_config(config)
    binding = read_deployment_binding(
        config.bundle_path,
        expected_bundle_logical_fingerprint=config.approved_bundle_logical_fingerprint,
    )
    _require_fresh(remote_state, clock())
    try:
        validate_remote_postcondition(remote_state, binding=binding)
    except OciDashboardDeploymentStateError as exc:
        raise DailyEodOciDeploymentCustodyError("remote postcondition is not exact") from exc
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending(journal.read_events(), config)
        event = journal.append(
            event_type="oci_deployment_succeeded",
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "release_id": binding.bundle.deployment_manifest.release_id,
                "post_state_fingerprint": remote_state.state_fingerprint,
                "manifest_sha256": binding.manifest_sha256,
                "checksums_sha256": binding.checksums_sha256,
                "reason_code": "oci_exact_release_and_serving_boundary_proven",
            },
        )
    return OciDeploymentCustodyResult(
        "succeeded",
        pending.attempt_id,
        event,
        binding,
        remote_state,
        "oci_exact_release_and_serving_boundary_proven",
    )


def recover_oci_deployment(
    *,
    config: DailyEodOciDeploymentConfig,
    remote_state: OciDashboardRemoteStateV1,
    clock: Clock = lambda: datetime.now(UTC),
) -> OciDeploymentCustodyResult:
    """Classify one interrupted deployment from a read-only report; never Apply."""

    _validate_config(config)
    _require_fresh(remote_state, clock())
    binding: OciDashboardDeploymentBinding | None = None
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = _pending(journal.read_events(), config)
        try:
            binding = read_deployment_binding(
                config.bundle_path,
                expected_bundle_logical_fingerprint=(
                    config.approved_bundle_logical_fingerprint
                ),
            )
            validate_remote_postcondition(remote_state, binding=binding)
            outcome = "recovered_succeeded"
            event_type = "oci_deployment_recovered_succeeded"
            reason = "oci_deployment_post_state_reconciled"
        except (OciDashboardDeploymentStateError, OSError, ValueError):
            release = str(pending.details["release_id"])
            if remote_state_is_unchanged_not_completed(
                remote_state,
                target_release=release,
                expected_state_fingerprint=config.expected_remote_state_fingerprint,
                expected_current_release=config.expected_current_release,
            ):
                outcome = "recovered_not_completed"
                event_type = "oci_deployment_recovered_not_completed"
                reason = "oci_remote_state_unchanged_and_target_absent"
            else:
                outcome = "recovery_blocked"
                event_type = "oci_deployment_recovery_blocked"
                reason = "oci_remote_state_partial_changed_or_ambiguous"
        event = journal.append(
            event_type=event_type,
            attempt_id=pending.attempt_id,
            observed_at=_aware_utc(clock()),
            details={
                "release_id": pending.details["release_id"],
                "observed_remote_state_fingerprint": remote_state.state_fingerprint,
                "reason_code": reason,
                "deployment_replayed": False,
                "remote_write_count": 0,
            },
        )
    return OciDeploymentCustodyResult(
        outcome,
        pending.attempt_id,
        event,
        binding,
        remote_state,
        reason,
    )


def _validate_plan(
    plan: DailyEodAutomationPlan,
    config: DailyEodOciDeploymentConfig,
    expected_fingerprint: str,
) -> None:
    matches = tuple(
        item
        for item in plan.observations
        if item.stage == "serving_bundle"
    )
    if (
        plan.status is not PlanStatus.ANALYTICS_READY
        or plan.next_action is not NextAction.REVIEW_BUNDLE_DEPLOYMENT
        or plan.target_session != config.target_session.isoformat()
        or plan.logical_content_fingerprint != expected_fingerprint
        or len(matches) != 1
        or matches[0].path != str(config.bundle_path)
        or matches[0].logical_fingerprint
        != config.approved_bundle_logical_fingerprint
    ):
        raise DailyEodOciDeploymentCustodyError("deployment plan differs from approval")


def _pending(
    events: tuple[DailyEodRunEvent, ...],
    config: DailyEodOciDeploymentConfig,
) -> DailyEodRunEvent:
    pending = unresolved_started_event(events)
    if (
        pending is None
        or pending.event_type != OCI_DEPLOYMENT_START_EVENT
        or pending.details.get("operation") != "deploy_oci_dashboard"
        or pending.details.get("bundle_path") != str(config.bundle_path)
        or pending.details.get("bundle_logical_fingerprint")
        != config.approved_bundle_logical_fingerprint
        or pending.details.get("expected_remote_state_fingerprint")
        != config.expected_remote_state_fingerprint
        or pending.details.get("expected_current_release")
        != config.expected_current_release
        or pending.details.get("deployment_config_file_sha256")
        != config.deployment_config_file_sha256
    ):
        raise DailyEodOciDeploymentCustodyError("pending OCI deployment differs from config")
    return pending


def _validate_config(config: DailyEodOciDeploymentConfig) -> None:
    try:
        validate_daily_eod_serving_bundle_location(
            config.bundle_path,
            expected_session=config.target_session,
        )
    except OfflineArtifactCustodyError as exc:
        raise DailyEodOciDeploymentCustodyError(
            "OCI deployment config is invalid"
        ) from exc
    if (
        not config.run_root.is_absolute()
        or not all(
            _is_fingerprint(value)
            for value in (
                config.approved_bundle_logical_fingerprint,
                config.expected_remote_state_fingerprint,
                config.deployment_config_file_sha256,
            )
        )
    ):
        raise DailyEodOciDeploymentCustodyError("OCI deployment config is invalid")
    if re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}",
        config.expected_current_release,
    ) is None:
        raise DailyEodOciDeploymentCustodyError(
            "expected current release is malformed"
        )


def _require_fresh(state: OciDashboardRemoteStateV1, now: datetime) -> None:
    current = _aware_utc(now)
    inspected = _aware_utc(state.inspected_at)
    if current < inspected or current - inspected > MAXIMUM_INSPECTION_AGE:
        raise DailyEodOciDeploymentCustodyError("remote inspection is stale")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyEodOciDeploymentCustodyError("deployment timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )
