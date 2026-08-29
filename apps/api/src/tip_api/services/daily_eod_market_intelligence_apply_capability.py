"""Explicit one-shot Market Intelligence Apply capability for the Dell coordinator."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from tip_api.persistence.parquet.market_intelligence_active import publish_and_activate
from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_coordinator import (
    PublicationTransitionContext,
    PublicationTransitionEvidence,
)
from tip_api.services.daily_eod_market_intelligence_apply_custody import (
    DailyEodMarketIntelligenceApplyConfig,
    MarketIntelligenceApplyCustodyResult,
    record_market_intelligence_apply_success,
    reserve_market_intelligence_apply,
    validate_approved_market_intelligence_freshness,
)


CONTRACT_VERSION = "daily-eod-market-intelligence-apply-capability/1.0"


class DailyEodMarketIntelligenceApplyCapabilityError(RuntimeError):
    """Raised when a one-shot MI Apply invocation loses an exact binding."""


@dataclass(frozen=True, slots=True)
class DailyEodMarketIntelligenceApplyCapabilityConfig:
    data_root: Path
    run_root: Path
    automation_paths: DailyEodAutomationPaths
    approval_plan_path: Path
    approved_plan_sha256: str
    expected_current_state_fingerprint: str
    review_acknowledgement: str | None = None


Clock = Callable[[], datetime]
Planner = Callable[..., DailyEodAutomationPlan]
ApplyExecutor = Callable[..., object]
Reserver = Callable[..., MarketIntelligenceApplyCustodyResult]
Recorder = Callable[..., MarketIntelligenceApplyCustodyResult]


class DailyEodMarketIntelligenceApplyCapability:
    """Reserve, execute, and prove one exact MI publication Apply."""

    def __init__(
        self,
        *,
        config: DailyEodMarketIntelligenceApplyCapabilityConfig,
        clock: Clock = lambda: datetime.now(UTC),
        planner: Planner = plan_daily_eod_automation,
        apply_executor: ApplyExecutor = publish_and_activate,
        reserver: Reserver = reserve_market_intelligence_apply,
        recorder: Recorder = record_market_intelligence_apply_success,
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
            or context.operation != "apply_market_intelligence"
            or context.coordinator.paths != self._config.automation_paths
            or context.coordinator.run_root != self._config.run_root
            or context.coordinator.paths.data_root != self._config.data_root
            or context.coordinator.paths.market_intelligence_approval_plan
            != self._config.approval_plan_path
        ):
            raise DailyEodMarketIntelligenceApplyCapabilityError(
                "MI Apply context differs from one-shot capability bindings"
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
            raise DailyEodMarketIntelligenceApplyCapabilityError(
                "automation plan changed before MI Apply reservation"
            )
        custody_config = DailyEodMarketIntelligenceApplyConfig(
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
            or approval.publication_id != context.publication_id
            or approval.plan_content_fingerprint
            != context.approval_plan_content_fingerprint
        ):
            raise DailyEodMarketIntelligenceApplyCapabilityError(
                "MI Apply reservation evidence differs from reviewed plan"
            )
        self._apply_executor(
            root=self._config.data_root,
            plan=approval,
            expected_current_state_fingerprint=(
                self._config.expected_current_state_fingerprint
            ),
            freshness_validator=lambda: validate_approved_market_intelligence_freshness(
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
            raise DailyEodMarketIntelligenceApplyCapabilityError(
                "MI Apply completion was not formally proven"
            )
        return PublicationTransitionEvidence(
            operation="apply_market_intelligence",
            target_session=context.coordinator.target_session.isoformat(),
            precondition_fingerprint=(
                context.automation_plan.logical_content_fingerprint
            ),
            outcome="succeeded",
            event_fingerprint=completed.event.event_fingerprint,
            external_request_count=0,
            production_write_count=approval.inventory_change_file_count,
            publication_id=approval.publication_id,
            reason_code=completed.reason_code,
        )
