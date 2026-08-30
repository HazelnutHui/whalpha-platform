"""One-action offline executor for an exact daily EOD automation plan."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable, Mapping

from tip_api.contracts.analytics.v1.market_intelligence import (
    MARKET_INTELLIGENCE_REVISION,
)
from tip_api.contracts.market_data.v2.dashboard_universe_activation import (
    PUBLIC_UNIVERSE_ORDER,
)
from tip_api.persistence.parquet.market_intelligence_active import (
    read_market_intelligence_approval_plan,
)
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    read_dashboard_snapshot_approval_plan,
)
from tip_api.services import (
    candidate_entry_geometry_cli,
    candidate_strategy_channel_cli,
    candidate_visual_context_cli,
    dashboard_snapshot_v2_cli,
    etf_relationship_cli,
    market_regime_cli,
    market_regime_preview_cli,
    market_regime_state_cli,
    market_intelligence_publication_cli,
    opportunity_candidate_cli,
)
from tip_api.services.daily_eod_automation import (
    ArtifactStatus,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
    plan_daily_eod_automation,
)
from tip_api.services.daily_eod_run_journal import (
    DailyEodRunEvent,
    DailyEodRunJournalError,
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)
from tip_api.services.oci_dashboard_serving_bundle import (
    read_oci_dashboard_serving_bundle,
)


EXECUTOR_CONTRACT = "daily-eod-single-action-executor/1.5"
OFFLINE_ACTIONS = (
    NextAction.CALCULATE_PHASE1A,
    NextAction.CALCULATE_PHASE1B_INCREMENTAL,
    NextAction.CALCULATE_CANDIDATE_DAILY,
    NextAction.CALCULATE_ENTRY_GEOMETRY,
    NextAction.CALCULATE_ETF_RELATIONSHIPS,
    NextAction.BUILD_MARKET_PREVIEW,
    NextAction.CALCULATE_STRATEGY_CHANNELS,
    NextAction.CALCULATE_CANDIDATE_VISUAL_CONTEXT,
    NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN,
    NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN,
    NextAction.BUILD_SERVING_BUNDLE,
)
ACTION_STAGE = {
    NextAction.CALCULATE_PHASE1A: "phase1a",
    NextAction.CALCULATE_PHASE1B_INCREMENTAL: "phase1b",
    NextAction.CALCULATE_CANDIDATE_DAILY: "candidate",
    NextAction.CALCULATE_ENTRY_GEOMETRY: "entry_geometry",
    NextAction.CALCULATE_ETF_RELATIONSHIPS: "phase2",
    NextAction.BUILD_MARKET_PREVIEW: "preview",
    NextAction.CALCULATE_STRATEGY_CHANNELS: "strategy_channels",
    NextAction.CALCULATE_CANDIDATE_VISUAL_CONTEXT: "visual_context",
    NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN: "publication_plan",
    NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN: "snapshot_plan",
    NextAction.BUILD_SERVING_BUNDLE: "serving_bundle",
}


class DailyEodExecutorError(RuntimeError):
    """Raised when an offline action cannot preserve its exact plan boundary."""


@dataclass(frozen=True, slots=True)
class DailyEodExecutionConfig:
    target_session: date
    paths: DailyEodAutomationPaths
    run_root: Path
    panel_cache_root: Path | None = None
    candidate_work_dir: Path | None = None
    publication_created_at: datetime | None = None
    publication_expected_current_state_fingerprint: str | None = None
    snapshot_generated_at: datetime | None = None
    bundle_built_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StageExecutionEvidence:
    action: NextAction
    output_path: str
    summary_sha256: str
    summary_bytes: int


@dataclass(frozen=True, slots=True)
class DailyEodExecutionResult:
    outcome: str
    action: NextAction
    attempt_id: str
    event: DailyEodRunEvent
    pre_plan: DailyEodAutomationPlan
    post_plan: DailyEodAutomationPlan | None
    stage_evidence: StageExecutionEvidence | None
    reason_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": EXECUTOR_CONTRACT,
            "outcome": self.outcome,
            "action": self.action.value,
            "attempt_id": self.attempt_id,
            "event_fingerprint": self.event.event_fingerprint,
            "pre_plan_fingerprint": self.pre_plan.logical_content_fingerprint,
            "post_plan_fingerprint": (
                None
                if self.post_plan is None
                else self.post_plan.logical_content_fingerprint
            ),
            "post_status": None if self.post_plan is None else self.post_plan.status.value,
            "post_next_action": (
                None if self.post_plan is None else self.post_plan.next_action.value
            ),
            "stage_summary_sha256": (
                None if self.stage_evidence is None else self.stage_evidence.summary_sha256
            ),
            "reason_code": self.reason_code,
            "external_request_count": 0,
            "production_write_count": 0,
            "publication_authorized": False,
            "deployment_authorized": False,
            "scheduler_enabled": False,
        }


@dataclass(frozen=True, slots=True)
class DailyEodRecoveryResult:
    outcome: str
    action: NextAction
    attempt_id: str
    event: DailyEodRunEvent
    current_plan: DailyEodAutomationPlan
    reason_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": EXECUTOR_CONTRACT,
            "outcome": self.outcome,
            "action": self.action.value,
            "attempt_id": self.attempt_id,
            "event_fingerprint": self.event.event_fingerprint,
            "current_plan_fingerprint": self.current_plan.logical_content_fingerprint,
            "current_status": self.current_plan.status.value,
            "current_next_action": self.current_plan.next_action.value,
            "reason_code": self.reason_code,
            "action_executed": False,
            "external_request_count": 0,
            "production_write_count": 0,
        }


Planner = Callable[..., DailyEodAutomationPlan]
ActionRunner = Callable[[NextAction, DailyEodExecutionConfig], StageExecutionEvidence]


def execute_daily_eod_action(
    *,
    config: DailyEodExecutionConfig,
    expected_plan_fingerprint: str,
    expected_action: NextAction,
    planner: Planner = plan_daily_eod_automation,
    runner: ActionRunner | None = None,
) -> DailyEodExecutionResult:
    """Execute exactly one already planned offline action under durable custody."""

    _validate_execution_config(config)
    if expected_action not in OFFLINE_ACTIONS:
        raise DailyEodExecutorError("only governed offline daily actions may execute")
    if (
        expected_action is NextAction.CALCULATE_CANDIDATE_VISUAL_CONTEXT
        and config.panel_cache_root is None
    ):
        raise DailyEodExecutorError(
            "Candidate Visual Context requires the exact panel cache root"
        )
    if expected_action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN and (
        config.publication_created_at is None
        or config.publication_expected_current_state_fingerprint is None
    ):
        raise DailyEodExecutorError(
            "Market Intelligence planning requires explicit review inputs"
        )
    if (
        expected_action is NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN
        and config.snapshot_generated_at is None
    ):
        raise DailyEodExecutorError(
            "Dashboard Snapshot planning requires an explicit UTC timestamp"
        )
    if (
        expected_action is NextAction.BUILD_SERVING_BUNDLE
        and config.bundle_built_at is None
    ):
        raise DailyEodExecutorError(
            "serving bundle construction requires an explicit UTC timestamp"
        )
    if (
        expected_action is not NextAction.BUILD_SERVING_BUNDLE
        and config.bundle_built_at is not None
    ):
        raise DailyEodExecutorError(
            "serving bundle timestamp is only valid for bundle construction"
        )
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        events = journal.read_events()
        if unresolved_started_event(events) is not None:
            raise DailyEodExecutorError("daily run has an unresolved action; recover it first")
        pre_plan = planner(target_session=config.target_session, paths=config.paths)
        _validate_expected_plan(
            pre_plan,
            expected_plan_fingerprint=expected_plan_fingerprint,
            expected_action=expected_action,
        )
        attempt_id = new_attempt_id(
            target_session=config.target_session,
            plan_fingerprint=expected_plan_fingerprint,
            sequence=len(events) + 1,
        )
        journal.append(
            event_type="action_started",
            attempt_id=attempt_id,
            details={
                "executor_contract": EXECUTOR_CONTRACT,
                "action": expected_action.value,
                "action_stage": ACTION_STAGE[expected_action],
                "plan_fingerprint": pre_plan.logical_content_fingerprint,
                "plan_status": pre_plan.status.value,
                "execution_input_fingerprint": _execution_input_fingerprint(config),
            },
        )
        try:
            stage_evidence = (runner or run_offline_action)(expected_action, config)
            _validate_stage_evidence(stage_evidence, expected_action, config)
        except Exception as exc:
            event = journal.append(
                event_type="action_failed",
                attempt_id=attempt_id,
                details={
                    "action": expected_action.value,
                    "plan_fingerprint": pre_plan.logical_content_fingerprint,
                    "reason_code": "offline_action_raised",
                    "failure_type": type(exc).__name__,
                },
            )
            return DailyEodExecutionResult(
                outcome="failed",
                action=expected_action,
                attempt_id=attempt_id,
                event=event,
                pre_plan=pre_plan,
                post_plan=None,
                stage_evidence=None,
                reason_code="offline_action_raised",
            )
        post_plan = planner(target_session=config.target_session, paths=config.paths)
        stage = ACTION_STAGE[expected_action]
        if not _stage_completed(post_plan, stage) or post_plan.next_action is expected_action:
            event = journal.append(
                event_type="action_failed",
                attempt_id=attempt_id,
                details={
                    "action": expected_action.value,
                    "plan_fingerprint": pre_plan.logical_content_fingerprint,
                    "post_plan_fingerprint": post_plan.logical_content_fingerprint,
                    "post_status": post_plan.status.value,
                    "post_next_action": post_plan.next_action.value,
                    "reason_code": "offline_action_postcondition_failed",
                    "stage_summary_sha256": stage_evidence.summary_sha256,
                },
            )
            return DailyEodExecutionResult(
                outcome="failed",
                action=expected_action,
                attempt_id=attempt_id,
                event=event,
                pre_plan=pre_plan,
                post_plan=post_plan,
                stage_evidence=stage_evidence,
                reason_code="offline_action_postcondition_failed",
            )
        event = journal.append(
            event_type="action_succeeded",
            attempt_id=attempt_id,
            details={
                "action": expected_action.value,
                "plan_fingerprint": pre_plan.logical_content_fingerprint,
                "post_plan_fingerprint": post_plan.logical_content_fingerprint,
                "post_status": post_plan.status.value,
                "post_next_action": post_plan.next_action.value,
                "stage_summary_sha256": stage_evidence.summary_sha256,
                "stage_summary_bytes": stage_evidence.summary_bytes,
                "output_path": stage_evidence.output_path,
                "reason_code": "offline_action_completed_and_replanned",
            },
        )
        return DailyEodExecutionResult(
            outcome="succeeded",
            action=expected_action,
            attempt_id=attempt_id,
            event=event,
            pre_plan=pre_plan,
            post_plan=post_plan,
            stage_evidence=stage_evidence,
            reason_code="offline_action_completed_and_replanned",
        )


def recover_daily_eod_action(
    *,
    config: DailyEodExecutionConfig,
    planner: Planner = plan_daily_eod_automation,
) -> DailyEodRecoveryResult:
    """Classify an interrupted attempt from formal state without executing it again."""

    _validate_execution_config(config)
    with locked_daily_eod_run_journal(
        run_root=config.run_root,
        target_session=config.target_session,
    ) as journal:
        pending = unresolved_started_event(journal.read_events())
        if pending is None:
            raise DailyEodExecutorError("daily run has no unresolved action to recover")
        try:
            action = NextAction(str(pending.details["action"]))
            before_fingerprint = str(pending.details["plan_fingerprint"])
            started_inputs = str(pending.details["execution_input_fingerprint"])
        except (KeyError, ValueError) as exc:
            raise DailyEodRunJournalError("pending daily action identity is malformed") from exc
        if (
            action not in OFFLINE_ACTIONS
            or not _is_fingerprint(before_fingerprint)
            or not _is_fingerprint(started_inputs)
        ):
            raise DailyEodRunJournalError("pending daily action is not offline")
        if started_inputs != _execution_input_fingerprint(config):
            raise DailyEodExecutorError("daily recovery inputs differ from the started action")
        current = planner(target_session=config.target_session, paths=config.paths)
        stage = ACTION_STAGE[action]
        if _stage_completed(current, stage) and current.next_action is not action:
            event_type = "action_recovered_succeeded"
            outcome = "recovered_succeeded"
            reason = "completed_artifact_formally_reconciled"
        elif (
            current.logical_content_fingerprint == before_fingerprint
            and current.next_action is action
            and current.status is PlanStatus.READY_FOR_OFFLINE_CALCULATION
        ):
            event_type = "action_recovered_not_completed"
            outcome = "recovered_not_completed"
            reason = "no_completed_artifact_detected"
        else:
            event_type = "action_recovery_blocked"
            outcome = "recovery_blocked"
            reason = "current_state_cannot_prove_completion_or_safe_retry"
        event = journal.append(
            event_type=event_type,
            attempt_id=pending.attempt_id,
            details={
                "action": action.value,
                "started_plan_fingerprint": before_fingerprint,
                "current_plan_fingerprint": current.logical_content_fingerprint,
                "current_status": current.status.value,
                "current_next_action": current.next_action.value,
                "reason_code": reason,
                "action_executed": False,
            },
        )
        return DailyEodRecoveryResult(
            outcome=outcome,
            action=action,
            attempt_id=pending.attempt_id,
            event=event,
            current_plan=current,
            reason_code=reason,
        )


def run_offline_action(
    action: NextAction, config: DailyEodExecutionConfig
) -> StageExecutionEvidence:
    """Invoke one existing socket-guarded administrator CLI in this process."""

    session = config.target_session.isoformat()
    if action is NextAction.CALCULATE_PHASE1A:
        output = config.paths.phase1a_audit
        argv = ["--as-of-session", session]
        for universe_id in PUBLIC_UNIVERSE_ORDER:
            argv.extend(("--universe-id", universe_id))
        argv.extend(("--data-root", str(config.paths.data_root)))
        if config.panel_cache_root is not None:
            argv.extend(("--panel-cache-root", str(config.panel_cache_root)))
        argv.extend(
            (
                "--output-dir",
                str(output),
                "--sector-rotation-output-dir",
                str(_sector_rotation_output_path(config.paths.phase1a_audit)),
            )
        )
        summary = _invoke_main(market_regime_cli.main, argv)
    elif action is NextAction.CALCULATE_PHASE1B_INCREMENTAL:
        output = config.paths.phase1b_audit
        argv = ["--as-of-session", session]
        for universe_id in PUBLIC_UNIVERSE_ORDER:
            argv.extend(("--universe-id", universe_id))
        argv.extend(
            (
                "--data-root",
                str(config.paths.data_root),
                "--phase1a-audit",
                str(config.paths.phase1a_audit),
                "--prior-state-audit",
                str(config.paths.prior_phase1b_audit),
                "--output-dir",
                str(output),
            )
        )
        summary = _invoke_main(market_regime_state_cli.main, argv)
    elif action is NextAction.CALCULATE_CANDIDATE_DAILY:
        if config.candidate_work_dir is None:
            raise DailyEodExecutorError("daily Candidate execution requires a resumable work directory")
        output = config.paths.candidate_audit
        argv = [
            "--as-of-session",
            session,
            "--data-root",
            str(config.paths.data_root),
            "--phase1b-audit",
            str(config.paths.phase1b_audit),
            "--prior-candidate-audit",
            str(config.paths.prior_candidate_audit),
            "--validation-tier",
            "daily",
            "--max-workers",
            "1",
            "--audit-work-dir",
            str(config.candidate_work_dir),
            "--output-dir",
            str(output),
        ]
        if config.panel_cache_root is not None:
            argv.extend(("--panel-cache-root", str(config.panel_cache_root)))
        summary = _invoke_main(opportunity_candidate_cli.main, argv)
    elif action is NextAction.CALCULATE_ENTRY_GEOMETRY:
        output = config.paths.entry_geometry_audit
        argv = [
            "--as-of-session",
            session,
            "--data-root",
            str(config.paths.data_root),
            "--candidate-audit",
            str(config.paths.candidate_audit),
            "--output-dir",
            str(output),
        ]
        summary = _invoke_main(candidate_entry_geometry_cli.main, argv)
    elif action is NextAction.CALCULATE_ETF_RELATIONSHIPS:
        output = config.paths.phase2_audit
        argv = [
            "--as-of-session",
            session,
            "--data-root",
            str(config.paths.data_root),
            "--phase1a-audit",
            str(config.paths.phase1a_audit),
            "--phase1b-audit",
            str(config.paths.phase1b_audit),
            "--output-dir",
            str(output),
        ]
        summary = _invoke_main(etf_relationship_cli.main, argv)
    elif action is NextAction.BUILD_MARKET_PREVIEW:
        output = config.paths.preview_bundle
        argv = [
            "--as-of-session",
            session,
            "--phase1a-audit",
            str(config.paths.phase1a_audit),
            "--phase1b-audit",
            str(config.paths.phase1b_audit),
            "--phase2-audit",
            str(config.paths.phase2_audit),
            "--output-dir",
            str(output),
        ]
        summary = _invoke_main(market_regime_preview_cli.main, argv)
    elif action is NextAction.CALCULATE_STRATEGY_CHANNELS:
        output = config.paths.strategy_channel_audit
        argv = [
            "--as-of-session",
            session,
            "--candidate-audit",
            str(config.paths.candidate_audit),
            "--entry-geometry-audit",
            str(config.paths.entry_geometry_audit),
            "--output-dir",
            str(output),
        ]
        summary = _invoke_main(candidate_strategy_channel_cli.main, argv)
    elif action is NextAction.CALCULATE_CANDIDATE_VISUAL_CONTEXT:
        if config.panel_cache_root is None:
            raise DailyEodExecutorError(
                "Candidate Visual Context requires the exact panel cache root"
            )
        output = _candidate_visual_context_output_path(
            config.paths.candidate_audit
        )
        argv = [
            "--as-of-session",
            session,
            "--candidate-audit",
            str(config.paths.candidate_audit),
            "--entry-geometry-audit",
            str(config.paths.entry_geometry_audit),
            "--panel-cache-root",
            str(config.panel_cache_root),
            "--output-dir",
            str(output),
        ]
        summary = _invoke_main(candidate_visual_context_cli.main, argv)
    elif action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN:
        if (
            config.publication_created_at is None
            or config.publication_expected_current_state_fingerprint is None
        ):
            raise DailyEodExecutorError(
                "Market Intelligence planning requires timestamp and inventory binding"
            )
        output = config.paths.market_intelligence_approval_plan
        argv = [
            "--plan",
            "--data-root",
            str(config.paths.data_root),
            "--analysis-session",
            session,
            "--revision",
            MARKET_INTELLIGENCE_REVISION,
            "--preview-bundle",
            str(config.paths.preview_bundle),
            "--phase1a-audit",
            str(config.paths.phase1a_audit),
            "--phase1b-audit",
            str(config.paths.phase1b_audit),
            "--phase2-audit",
            str(config.paths.phase2_audit),
            "--candidate-audit",
            str(config.paths.candidate_audit),
            "--entry-geometry-audit",
            str(config.paths.entry_geometry_audit),
            "--sector-rotation-audit",
            str(_sector_rotation_output_path(config.paths.phase1a_audit)),
            "--output-root",
            str(config.paths.market_intelligence_output_root),
            "--approval-package",
            str(config.paths.market_intelligence_approval_plan),
            "--created-at",
            config.publication_created_at.astimezone(UTC).isoformat(),
            "--expected-current-state-fingerprint",
            config.publication_expected_current_state_fingerprint,
        ]
        summary = _invoke_main(market_intelligence_publication_cli.main, argv)
    elif action is NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN:
        if config.snapshot_generated_at is None:
            raise DailyEodExecutorError(
                "Dashboard Snapshot planning requires an explicit UTC timestamp"
            )
        market_intelligence = read_market_intelligence_approval_plan(
            config.paths.market_intelligence_approval_plan
        )
        output = config.paths.snapshot_approval_plan
        argv = [
            "--approval-package",
            str(config.paths.snapshot_approval_plan),
            "--output-root",
            str(config.paths.snapshot_output_root),
            "--generated-at",
            config.snapshot_generated_at.astimezone(UTC).isoformat(),
            "--market-intelligence-publication-id",
            market_intelligence.publication_id,
            "--candidate-strategy-audit",
            str(config.paths.strategy_channel_audit),
            "--candidate-visual-context-audit",
            str(
                _candidate_visual_context_output_path(
                    config.paths.candidate_audit
                )
            ),
            "--analysis-session",
            session,
        ]
        summary = _invoke_main(dashboard_snapshot_v2_cli.main, argv)
    elif action is NextAction.BUILD_SERVING_BUNDLE:
        if config.bundle_built_at is None:
            raise DailyEodExecutorError(
                "serving bundle construction requires an explicit UTC timestamp"
            )
        snapshot_plan = read_dashboard_snapshot_approval_plan(
            config.paths.snapshot_approval_plan
        )
        output = config.paths.serving_bundle_root / snapshot_plan.release_id
        repository_root = _source_repository_root()
        command = [
            str(repository_root / "scripts/admin/build-oci-dashboard-bundle.sh"),
            "--snapshot-path",
            snapshot_plan.target_path,
            "--market-intelligence-publication",
            snapshot_plan.market_intelligence_publication_id,
            "--bundle-release",
            snapshot_plan.release_id,
            "--bundle-root",
            str(config.paths.serving_bundle_root),
            "--build-timestamp",
            config.bundle_built_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ]
        environment = {
            name: os.environ[name]
            for name in ("HOME", "PATH", "LANG")
            if name in os.environ
        }
        environment.update(
            {
                "CI": "1",
                "npm_config_offline": "true",
            }
        )
        completed = subprocess.run(
            command,
            cwd=repository_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode != 0:
            raise DailyEodExecutorError(
                "serving bundle administrator reported failure"
            )
        bundle = read_oci_dashboard_serving_bundle(
            output,
            expected_snapshot_path=Path(snapshot_plan.target_path),
        )
        summary = json.dumps(
            {
                "status": "completed",
                "release_id": snapshot_plan.release_id,
                "bundle_logical_fingerprint": bundle.bundle_logical_fingerprint,
                "checksum_file_count": bundle.checksum_file_count,
                "deployment_authorized": False,
                "external_request_count": 0,
                "production_write_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    else:
        raise DailyEodExecutorError("unsupported offline daily action")
    raw = summary.encode("utf-8")
    return StageExecutionEvidence(
        action=action,
        output_path=str(output),
        summary_sha256=hashlib.sha256(raw).hexdigest(),
        summary_bytes=len(raw),
    )


def _invoke_main(main: Callable[[list[str] | None], int], argv: list[str]) -> str:
    capture = io.StringIO()
    try:
        with redirect_stdout(capture):
            exit_code = main(argv)
    except SystemExit as exc:
        raise DailyEodExecutorError("offline administrator argument boundary exited") from exc
    if exit_code != 0:
        raise DailyEodExecutorError("offline administrator reported failure")
    summary = capture.getvalue()
    if not summary or len(summary.encode("utf-8")) > 64 * 1024:
        raise DailyEodExecutorError("offline administrator summary is unavailable or excessive")
    return summary


def _validate_expected_plan(
    plan: DailyEodAutomationPlan,
    *,
    expected_plan_fingerprint: str,
    expected_action: NextAction,
) -> None:
    if (
        plan.logical_content_fingerprint != expected_plan_fingerprint
        or plan.status is not PlanStatus.READY_FOR_OFFLINE_CALCULATION
        or plan.next_action is not expected_action
    ):
        raise DailyEodExecutorError("daily EOD plan is stale or action differs")


def _stage_completed(plan: DailyEodAutomationPlan, stage: str) -> bool:
    return any(
        item.stage == stage and item.status is ArtifactStatus.COMPLETED
        for item in plan.observations
    )


def _validate_stage_evidence(
    evidence: StageExecutionEvidence,
    action: NextAction,
    config: DailyEodExecutionConfig,
) -> None:
    if not isinstance(evidence, StageExecutionEvidence):
        raise DailyEodExecutorError("offline action returned malformed evidence")
    if evidence.action is not action:
        raise DailyEodExecutorError("offline action evidence identifies another action")
    if evidence.output_path != str(_action_output_path(action, config)):
        raise DailyEodExecutorError("offline action evidence identifies another output")
    if not _is_fingerprint(evidence.summary_sha256):
        raise DailyEodExecutorError("offline action summary fingerprint is malformed")
    if (
        not isinstance(evidence.summary_bytes, int)
        or isinstance(evidence.summary_bytes, bool)
        or evidence.summary_bytes < 1
    ):
        raise DailyEodExecutorError("offline action summary size is malformed")


def _action_output_path(action: NextAction, config: DailyEodExecutionConfig) -> Path:
    if action is NextAction.CALCULATE_PHASE1A:
        return config.paths.phase1a_audit
    if action is NextAction.CALCULATE_PHASE1B_INCREMENTAL:
        return config.paths.phase1b_audit
    if action is NextAction.CALCULATE_CANDIDATE_DAILY:
        return config.paths.candidate_audit
    if action is NextAction.CALCULATE_ENTRY_GEOMETRY:
        return config.paths.entry_geometry_audit
    if action is NextAction.CALCULATE_ETF_RELATIONSHIPS:
        return config.paths.phase2_audit
    if action is NextAction.BUILD_MARKET_PREVIEW:
        return config.paths.preview_bundle
    if action is NextAction.CALCULATE_STRATEGY_CHANNELS:
        return config.paths.strategy_channel_audit
    if action is NextAction.CALCULATE_CANDIDATE_VISUAL_CONTEXT:
        return _candidate_visual_context_output_path(
            config.paths.candidate_audit
        )
    if action is NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN:
        return config.paths.market_intelligence_approval_plan
    if action is NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN:
        return config.paths.snapshot_approval_plan
    if action is NextAction.BUILD_SERVING_BUNDLE:
        approval = read_dashboard_snapshot_approval_plan(
            config.paths.snapshot_approval_plan
        )
        return config.paths.serving_bundle_root / approval.release_id
    raise DailyEodExecutorError("unsupported offline daily action")


def _sector_rotation_output_path(phase1a_audit: Path) -> Path:
    return phase1a_audit.with_name(f"{phase1a_audit.name}-sector-etf-rotation")


def _candidate_visual_context_output_path(candidate_audit: Path) -> Path:
    return candidate_audit.with_name(f"{candidate_audit.name}-visual-context")


def _validate_execution_config(config: DailyEodExecutionConfig) -> None:
    if not config.run_root.is_absolute():
        raise DailyEodExecutorError("daily run root must be absolute")
    if _is_within(config.run_root, config.paths.data_root):
        raise DailyEodExecutorError("daily run journal must remain outside the data root")
    if config.panel_cache_root is not None and not config.panel_cache_root.is_absolute():
        raise DailyEodExecutorError("panel cache root must be absolute")
    if config.panel_cache_root is not None and _is_within(
        config.panel_cache_root, config.paths.data_root
    ):
        raise DailyEodExecutorError("panel cache must remain outside the data root")
    if config.candidate_work_dir is not None and (
        not config.candidate_work_dir.is_absolute()
        or config.candidate_work_dir.parent != Path("/tmp")
    ):
        raise DailyEodExecutorError("Candidate work directory must be a direct child of /tmp")
    publication_values = (
        config.publication_created_at,
        config.publication_expected_current_state_fingerprint,
    )
    if any(value is not None for value in publication_values):
        if (
            config.publication_created_at is None
            or config.publication_created_at.tzinfo is None
            or config.publication_created_at.utcoffset() is None
            or config.publication_created_at.utcoffset().total_seconds() != 0
            or not _is_fingerprint(
                config.publication_expected_current_state_fingerprint
            )
        ):
            raise DailyEodExecutorError(
                "publication planning inputs must be complete UTC/fingerprint bindings"
            )
    if config.snapshot_generated_at is not None and (
        config.snapshot_generated_at.tzinfo is None
        or config.snapshot_generated_at.utcoffset() is None
        or config.snapshot_generated_at.utcoffset().total_seconds() != 0
    ):
        raise DailyEodExecutorError(
            "Snapshot planning timestamp must be explicit UTC"
        )
    if config.bundle_built_at is not None and (
        config.bundle_built_at.tzinfo is None
        or config.bundle_built_at.utcoffset() is None
        or config.bundle_built_at.utcoffset().total_seconds() != 0
    ):
        raise DailyEodExecutorError(
            "serving bundle timestamp must be explicit UTC"
        )


def _execution_input_fingerprint(config: DailyEodExecutionConfig) -> str:
    value = {
        "executor_contract": EXECUTOR_CONTRACT,
        "target_session": config.target_session.isoformat(),
        "paths": {
            "data_root": str(config.paths.data_root),
            "phase1a_audit": str(config.paths.phase1a_audit),
            "prior_phase1b_audit": str(config.paths.prior_phase1b_audit),
            "phase1b_audit": str(config.paths.phase1b_audit),
            "prior_candidate_audit": str(config.paths.prior_candidate_audit),
            "candidate_audit": str(config.paths.candidate_audit),
            "entry_geometry_audit": str(config.paths.entry_geometry_audit),
            "phase2_audit": str(config.paths.phase2_audit),
            "preview_bundle": str(config.paths.preview_bundle),
            "strategy_channel_audit": str(config.paths.strategy_channel_audit),
            "market_intelligence_output_root": str(
                config.paths.market_intelligence_output_root
            ),
            "market_intelligence_approval_plan": str(
                config.paths.market_intelligence_approval_plan
            ),
            "snapshot_output_root": str(config.paths.snapshot_output_root),
            "snapshot_approval_plan": str(config.paths.snapshot_approval_plan),
            "serving_bundle_root": str(config.paths.serving_bundle_root),
            "panel_cache_root": (
                None if config.panel_cache_root is None else str(config.panel_cache_root)
            ),
            "candidate_work_dir": (
                None if config.candidate_work_dir is None else str(config.candidate_work_dir)
            ),
            "publication_created_at": (
                None
                if config.publication_created_at is None
                else config.publication_created_at.isoformat()
            ),
            "publication_expected_current_state_fingerprint": (
                config.publication_expected_current_state_fingerprint
            ),
            "snapshot_generated_at": (
                None
                if config.snapshot_generated_at is None
                else config.snapshot_generated_at.isoformat()
            ),
            "bundle_built_at": (
                None
                if config.bundle_built_at is None
                else config.bundle_built_at.isoformat()
            ),
        },
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodExecutorError("executing source repository root is unavailable")


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
