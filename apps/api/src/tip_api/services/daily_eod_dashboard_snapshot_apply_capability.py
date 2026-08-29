"""Explicit one-shot Dashboard Snapshot Apply capability for the Dell coordinator."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from tip_api.persistence.parquet.dashboard_snapshot_active import publish_and_activate
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_coordinator import (
    PublicationTransitionContext,
    PublicationTransitionEvidence,
)
from tip_api.services.daily_eod_dashboard_snapshot_apply_custody import (
    DashboardSnapshotApplyCustodyResult,
    DailyEodDashboardSnapshotApplyConfig,
    record_dashboard_snapshot_apply_success,
    reserve_dashboard_snapshot_apply,
    validate_approved_dashboard_snapshot_freshness,
)


CONTRACT_VERSION = "daily-eod-dashboard-snapshot-apply-capability/1.0"


class DailyEodDashboardSnapshotApplyCapabilityError(RuntimeError):
    """Raised when one-shot Snapshot Apply loses an exact binding."""


@dataclass(frozen=True, slots=True)
class DailyEodDashboardSnapshotApplyCapabilityConfig:
    data_root: Path
    legacy_root: Path
    run_root: Path
    automation_paths: DailyEodAutomationPaths
    approval_plan_path: Path
    approved_plan_sha256: str
    expected_current_state_fingerprint: str
    review_acknowledgement: str | None = None


Clock = Callable[[], datetime]
Planner = Callable[..., DailyEodAutomationPlan]
ApplyExecutor = Callable[..., object]
Reserver = Callable[..., DashboardSnapshotApplyCustodyResult]
Recorder = Callable[..., DashboardSnapshotApplyCustodyResult]


class DailyEodDashboardSnapshotApplyCapability:
    """Reserve, execute, and prove one exact Dashboard Snapshot Apply."""

    def __init__(
        self,
        *,
        config: DailyEodDashboardSnapshotApplyCapabilityConfig,
        clock: Clock = lambda: datetime.now(UTC),
        planner: Planner = plan_daily_eod_automation,
        apply_executor: ApplyExecutor = publish_and_activate,
        reserver: Reserver = reserve_dashboard_snapshot_apply,
        recorder: Recorder = record_dashboard_snapshot_apply_success,
    ) -> None:
        self._config = config
        self._clock = clock
        self._planner = planner
        self._apply_executor = apply_executor
        self._reserver = reserver
        self._recorder = recorder

    def apply(
        self,
        context: PublicationTransitionContext,
    ) -> PublicationTransitionEvidence:
        if (
            not isinstance(context, PublicationTransitionContext)
            or context.operation != "apply_dashboard_snapshot"
            or context.coordinator.paths != self._config.automation_paths
            or context.coordinator.run_root != self._config.run_root
            or context.coordinator.paths.data_root != self._config.data_root
            or context.coordinator.paths.snapshot_approval_plan
            != self._config.approval_plan_path
        ):
            raise DailyEodDashboardSnapshotApplyCapabilityError(
                "Snapshot Apply context differs from one-shot capability bindings"
            )
        current = self._planner(
            target_session=context.coordinator.target_session,
            paths=self._config.automation_paths,
        )
        if (
            not isinstance(current, DailyEodAutomationPlan)
            or current.logical_content_fingerprint
            != context.automation_plan.logical_content_fingerprint
        ):
            raise DailyEodDashboardSnapshotApplyCapabilityError(
                "automation plan changed before Snapshot Apply reservation"
            )
        custody_config = DailyEodDashboardSnapshotApplyConfig(
            target_session=context.coordinator.target_session,
            approval_plan_path=self._config.approval_plan_path,
            approved_plan_sha256=self._config.approved_plan_sha256,
            expected_current_state_fingerprint=(
                self._config.expected_current_state_fingerprint
            ),
            review_acknowledgement_sha256=(
                None
                if self._config.review_acknowledgement is None
                else hashlib.sha256(
                    self._config.review_acknowledgement.encode("utf-8")
                ).hexdigest()
            ),
            data_root=self._config.data_root,
            legacy_root=self._config.legacy_root,
            run_root=self._config.run_root,
            automation_paths=self._config.automation_paths,
        )
        observed = self._clock()
        reservation = self._reserver(
            config=custody_config,
            checked_at=context.checked_at,
            expected_automation_plan_fingerprint=(
                context.automation_plan.logical_content_fingerprint
            ),
            review_acknowledgement=self._config.review_acknowledgement,
            clock=lambda: observed,
            planner=self._planner,
        )
        approval = reservation.approval_plan
        if (
            reservation.outcome != "reserved"
            or approval is None
            or approval.release_id != context.publication_id
            or approval.plan_content_fingerprint
            != context.approval_plan_content_fingerprint
        ):
            raise DailyEodDashboardSnapshotApplyCapabilityError(
                "Snapshot Apply reservation evidence differs from reviewed plan"
            )
        self._apply_executor(
            root=self._config.data_root,
            legacy_root=self._config.legacy_root,
            plan=approval,
            expected_current_state_fingerprint=(
                self._config.expected_current_state_fingerprint
            ),
            freshness_validator=lambda: validate_approved_dashboard_snapshot_freshness(
                root=self._config.data_root,
                plan=approval,
                checked_at=self._clock(),
                review_acknowledgement=self._config.review_acknowledgement,
            ),
        )
        completed = self._recorder(
            config=custody_config,
            clock=self._clock,
        )
        if completed.outcome != "succeeded":
            raise DailyEodDashboardSnapshotApplyCapabilityError(
                "Snapshot Apply completion was not formally proven"
            )
        return PublicationTransitionEvidence(
            operation="apply_dashboard_snapshot",
            target_session=context.coordinator.target_session.isoformat(),
            precondition_fingerprint=(
                context.automation_plan.logical_content_fingerprint
            ),
            outcome="succeeded",
            event_fingerprint=completed.event.event_fingerprint,
            external_request_count=0,
            production_write_count=len(approval.files) + 1,
            publication_id=approval.release_id,
            reason_code=completed.reason_code,
        )
