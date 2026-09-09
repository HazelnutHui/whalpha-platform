"""Finite execution of the independent daily Membership research sidecar."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterator

from tip_api.services.daily_eod_automation import (
    DailyEodAutomationPaths,
    plan_daily_eod_automation,
)
from tip_api.services.daily_universe_membership_continuation import (
    METHODOLOGY_VERSION,
    DailyUniverseMembershipContinuationResult,
    prepare_daily_universe_membership_candidate,
)
from tip_api.services.daily_universe_membership_sidecar import (
    APPLY_PLAN_NAME,
    CANDIDATE_ROOT_NAME,
    DailyUniverseMembershipSidecarPlan,
    MembershipSidecarAction,
    MembershipSidecarStatus,
    plan_daily_universe_membership_sidecar,
    verify_daily_universe_membership_sidecar_plan,
)
from tip_api.services.universe_membership_apply_plan import (
    UniverseMembershipApplyPlanEvidence,
    build_universe_membership_apply_plan,
)


CONTRACT_VERSION = "daily-universe-membership-bounded-run/1.0"
DEFAULT_MAXIMUM_ACTIONS = 2
MAXIMUM_ACTIONS = 2
DEFAULT_MAXIMUM_ELAPSED_SECONDS = 60 * 60
MAXIMUM_ELAPSED_SECONDS = 4 * 60 * 60


class DailyUniverseMembershipRunnerError(RuntimeError):
    """Raised when sidecar execution cannot remain exact and fail closed."""


class MembershipRunStatus(StrEnum):
    REVIEW_READY = "review_ready"
    BOUNDARY_REACHED = "boundary_reached"
    BLOCKED = "blocked"
    ACTION_FAILED = "action_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True, slots=True)
class DailyUniverseMembershipRunConfig:
    target_session: date
    data_root: Path
    catalog_as_of_date: date
    candidate_root: Path
    apply_plan_path: Path
    primary_automation_paths: DailyEodAutomationPaths


@dataclass(frozen=True, slots=True)
class MembershipRunActionEvidence:
    sequence: int
    action: str
    started_at: str
    completed_at: str
    outcome: str
    pre_plan_fingerprint: str
    post_plan_fingerprint: str | None
    artifact_fingerprint: str | None
    failure_type: str | None
    logical_content_fingerprint: str


@dataclass(frozen=True, slots=True)
class DailyUniverseMembershipRunResult:
    contract_version: str
    status: MembershipRunStatus
    target_session: str
    started_at: str
    completed_at: str
    maximum_actions: int
    maximum_elapsed_seconds: int
    action_attempt_count: int
    action_success_count: int
    action_evidence: tuple[MembershipRunActionEvidence, ...]
    final_plan_status: str
    final_next_action: str
    final_plan_fingerprint: str
    reason_codes: tuple[str, ...]
    execution_enabled: bool
    exclusive_process_lock: bool
    automatic_retry_enabled: bool
    automatic_recovery_enabled: bool
    website_pipeline_blocked: bool
    primary_pipeline_invocation_count: int
    external_request_count: int
    production_write_count: int
    canonical_membership_apply_performed: bool
    historical_coverage_authorized: bool
    research_performance_authorized: bool
    scheduler_installation_performed: bool
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))  # type: ignore[return-value]


Planner = Callable[..., DailyUniverseMembershipSidecarPlan]
CandidatePreparer = Callable[..., DailyUniverseMembershipContinuationResult]
ApplyPlanBuilder = Callable[..., UniverseMembershipApplyPlanEvidence]
Clock = Callable[[], datetime]


def run_bounded_daily_universe_membership(
    *,
    config: DailyUniverseMembershipRunConfig,
    started_at: datetime,
    execute: bool = False,
    maximum_actions: int = DEFAULT_MAXIMUM_ACTIONS,
    maximum_elapsed_seconds: int = DEFAULT_MAXIMUM_ELAPSED_SECONDS,
    planner: Planner | None = None,
    candidate_preparer: CandidatePreparer = (
        prepare_daily_universe_membership_candidate
    ),
    apply_plan_builder: ApplyPlanBuilder = build_universe_membership_apply_plan,
    clock: Clock = lambda: datetime.now(UTC),
) -> DailyUniverseMembershipRunResult:
    """Run at most two non-canonical sidecar actions and stop before Apply."""

    started = _aware_utc(started_at)
    _validate_config(
        config=config,
        maximum_actions=maximum_actions,
        maximum_elapsed_seconds=maximum_elapsed_seconds,
    )
    actual_planner = planner or _plan_sidecar
    lock = (
        _exclusive_session_lock(config.candidate_root.parent)
        if execute
        else nullcontext()
    )
    with lock:
        return _run(
            config=config,
            started_at=started,
            execute=execute,
            maximum_actions=maximum_actions,
            maximum_elapsed_seconds=maximum_elapsed_seconds,
            planner=actual_planner,
            candidate_preparer=candidate_preparer,
            apply_plan_builder=apply_plan_builder,
            clock=clock,
        )


def _run(
    *,
    config: DailyUniverseMembershipRunConfig,
    started_at: datetime,
    execute: bool,
    maximum_actions: int,
    maximum_elapsed_seconds: int,
    planner: Planner,
    candidate_preparer: CandidatePreparer,
    apply_plan_builder: ApplyPlanBuilder,
    clock: Clock,
) -> DailyUniverseMembershipRunResult:
    deadline = started_at + timedelta(seconds=maximum_elapsed_seconds)
    evidence: list[MembershipRunActionEvidence] = []
    plan = _fresh_plan(planner, config=config, checked_at=started_at)

    while True:
        observed_at = _monotonic_clock(clock, not_before=started_at)
        terminal = _terminal_status(
            plan=plan,
            execute=execute,
            action_count=len(evidence),
            observed_at=observed_at,
            deadline=deadline,
            maximum_actions=maximum_actions,
        )
        if terminal is not None:
            status, reasons = terminal
            return _result(
                status=status,
                config=config,
                started_at=started_at,
                completed_at=observed_at,
                maximum_actions=maximum_actions,
                maximum_elapsed_seconds=maximum_elapsed_seconds,
                evidence=tuple(evidence),
                final_plan=plan,
                reasons=reasons,
                execute=execute,
            )

        action = plan.next_action
        try:
            artifact_fingerprint = _execute_action(
                action=action,
                config=config,
                action_started_at=observed_at,
                candidate_preparer=candidate_preparer,
                apply_plan_builder=apply_plan_builder,
            )
        except Exception as exc:
            completed_at = _monotonic_clock(clock, not_before=observed_at)
            evidence.append(
                _action_evidence(
                    sequence=len(evidence) + 1,
                    action=action,
                    started_at=observed_at,
                    completed_at=completed_at,
                    outcome="failed",
                    pre_plan=plan,
                    post_plan=None,
                    artifact_fingerprint=None,
                    failure_type=type(exc).__name__,
                )
            )
            return _result(
                status=MembershipRunStatus.ACTION_FAILED,
                config=config,
                started_at=started_at,
                completed_at=completed_at,
                maximum_actions=maximum_actions,
                maximum_elapsed_seconds=maximum_elapsed_seconds,
                evidence=tuple(evidence),
                final_plan=plan,
                reasons=(
                    "membership_sidecar_action_failed",
                    "automatic_retry_prohibited",
                    type(exc).__name__,
                ),
                execute=execute,
            )

        completed_at = _monotonic_clock(clock, not_before=observed_at)
        try:
            post_plan = _fresh_plan(
                planner,
                config=config,
                checked_at=started_at,
            )
        except Exception as exc:
            raise DailyUniverseMembershipRunnerError(
                "sidecar action completed but its post-plan is unavailable; "
                "automatic continuation is prohibited"
            ) from exc
        if (
            post_plan.logical_content_fingerprint
            == plan.logical_content_fingerprint
            or post_plan.next_action is action
        ):
            raise DailyUniverseMembershipRunnerError(
                "sidecar action did not advance the formal plan"
            )
        evidence.append(
            _action_evidence(
                sequence=len(evidence) + 1,
                action=action,
                started_at=observed_at,
                completed_at=completed_at,
                outcome="succeeded",
                pre_plan=plan,
                post_plan=post_plan,
                artifact_fingerprint=artifact_fingerprint,
                failure_type=None,
            )
        )
        plan = post_plan


def verify_daily_universe_membership_run_result(
    result: DailyUniverseMembershipRunResult,
) -> None:
    if not isinstance(result, DailyUniverseMembershipRunResult):
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar run result is invalid"
        )
    logical = asdict(result)
    logical.pop("logical_content_fingerprint")
    try:
        date.fromisoformat(result.target_session)
        started = _parse_utc(result.started_at)
        completed = _parse_utc(result.completed_at)
        final_status = MembershipSidecarStatus(result.final_plan_status)
        MembershipSidecarAction(result.final_next_action)
    except ValueError as exc:
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar run identity is malformed"
        ) from exc
    if (
        result.contract_version != CONTRACT_VERSION
        or not isinstance(result.status, MembershipRunStatus)
        or result.logical_content_fingerprint != _fingerprint(_jsonable(logical))
        or completed < started
        or not 1 <= result.maximum_actions <= MAXIMUM_ACTIONS
        or not 1 <= result.maximum_elapsed_seconds <= MAXIMUM_ELAPSED_SECONDS
        or result.action_attempt_count != len(result.action_evidence)
        or result.action_success_count
        != sum(item.outcome == "succeeded" for item in result.action_evidence)
        or not result.reason_codes
        or not _is_fingerprint(result.final_plan_fingerprint)
        or result.exclusive_process_lock != result.execution_enabled
        or result.automatic_retry_enabled
        or result.automatic_recovery_enabled
        or result.website_pipeline_blocked
        or result.primary_pipeline_invocation_count != 0
        or result.external_request_count != 0
        or result.production_write_count != 0
        or result.canonical_membership_apply_performed
        or result.historical_coverage_authorized
        or result.research_performance_authorized
        or result.scheduler_installation_performed
    ):
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar run result exceeds its authority"
        )
    for sequence, item in enumerate(result.action_evidence, start=1):
        _verify_action_evidence(item, sequence=sequence)
    status_valid = {
        MembershipRunStatus.REVIEW_READY: (
            not result.execution_enabled
            and not result.action_evidence
            and final_status is MembershipSidecarStatus.READY
        ),
        MembershipRunStatus.BOUNDARY_REACHED: (
            final_status
            in {
                MembershipSidecarStatus.WAITING,
                MembershipSidecarStatus.REVIEW_REQUIRED,
                MembershipSidecarStatus.COMPLETE,
            }
        ),
        MembershipRunStatus.BLOCKED: (
            final_status is MembershipSidecarStatus.BLOCKED
        ),
        MembershipRunStatus.ACTION_FAILED: (
            bool(result.action_evidence)
            and result.action_evidence[-1].outcome == "failed"
        ),
        MembershipRunStatus.BUDGET_EXHAUSTED: (
            result.execution_enabled
            and final_status is MembershipSidecarStatus.READY
        ),
    }[result.status]
    if not status_valid:
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar run status conflicts with its final plan"
        )


def _plan_sidecar(
    *,
    config: DailyUniverseMembershipRunConfig,
    checked_at: datetime,
) -> DailyUniverseMembershipSidecarPlan:
    primary = plan_daily_eod_automation(
        target_session=config.target_session,
        paths=config.primary_automation_paths,
    )
    return plan_daily_universe_membership_sidecar(
        checked_at=checked_at,
        target_session=config.target_session,
        data_root=config.data_root,
        catalog_as_of_date=config.catalog_as_of_date,
        candidate_root=config.candidate_root,
        apply_plan_path=config.apply_plan_path,
        primary_automation_plan=primary,
    )


def _fresh_plan(
    planner: Planner,
    *,
    config: DailyUniverseMembershipRunConfig,
    checked_at: datetime,
) -> DailyUniverseMembershipSidecarPlan:
    plan = planner(config=config, checked_at=checked_at)
    verify_daily_universe_membership_sidecar_plan(plan)
    if plan.target_session != config.target_session.isoformat():
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar plan target differs"
        )
    return plan


def _terminal_status(
    *,
    plan: DailyUniverseMembershipSidecarPlan,
    execute: bool,
    action_count: int,
    observed_at: datetime,
    deadline: datetime,
    maximum_actions: int,
) -> tuple[MembershipRunStatus, tuple[str, ...]] | None:
    if plan.status is MembershipSidecarStatus.BLOCKED:
        return MembershipRunStatus.BLOCKED, plan.reason_codes
    if plan.status is not MembershipSidecarStatus.READY:
        return (
            MembershipRunStatus.BOUNDARY_REACHED,
            ("membership_sidecar_boundary_reached", *plan.reason_codes),
        )
    if plan.next_action not in {
        MembershipSidecarAction.PREPARE_CANDIDATE,
        MembershipSidecarAction.PREPARE_APPLY_PLAN,
    }:
        raise DailyUniverseMembershipRunnerError(
            "ready sidecar plan selected a non-executable action"
        )
    if not execute:
        return (
            MembershipRunStatus.REVIEW_READY,
            ("explicit_membership_sidecar_execution_not_enabled",),
        )
    if action_count >= maximum_actions or observed_at >= deadline:
        return (
            MembershipRunStatus.BUDGET_EXHAUSTED,
            ("membership_sidecar_budget_exhausted",),
        )
    return None


def _execute_action(
    *,
    action: MembershipSidecarAction,
    config: DailyUniverseMembershipRunConfig,
    action_started_at: datetime,
    candidate_preparer: CandidatePreparer,
    apply_plan_builder: ApplyPlanBuilder,
) -> str:
    if action is MembershipSidecarAction.PREPARE_CANDIDATE:
        candidate = candidate_preparer(
            data_root=config.data_root,
            session_date=config.target_session,
            catalog_as_of_date=config.catalog_as_of_date,
            evaluated_at=action_started_at,
            assessed_at=action_started_at,
            candidate_root=config.candidate_root,
        )
        expected_partition = str(
            Path(config.candidate_root)
            / "market-data"
            / "universe-membership"
            / "schema_version=1"
            / f"methodology_version={METHODOLOGY_VERSION}"
            / f"session_date={config.target_session.isoformat()}"
        )
        if (
            not isinstance(candidate, DailyUniverseMembershipContinuationResult)
            or candidate.status
            not in {
                "candidate_ready_for_publication_plan",
                "outcome_only_candidate",
            }
            or candidate.session_date != config.target_session.isoformat()
            or candidate.methodology_version != METHODOLOGY_VERSION
            or candidate.candidate_partition_path != expected_partition
            or candidate.record_count <= 0
            or not _is_fingerprint(candidate.membership_logical_fingerprint)
            or candidate.canonical_publication_fingerprint is not None
            or candidate.external_request_count != 0
            or candidate.canonical_data_write_count != 0
            or candidate.publication_authorized
            or candidate.historical_coverage_authorized
            or candidate.research_performance_authorized
            or candidate.scheduler_enabled
            or candidate.website_pipeline_blocked
        ):
            raise DailyUniverseMembershipRunnerError(
                "Membership candidate result differs from the planned action"
            )
        return candidate.membership_logical_fingerprint

    if action is MembershipSidecarAction.PREPARE_APPLY_PLAN:
        evidence = apply_plan_builder(
            data_root=config.data_root,
            candidate_root=config.candidate_root,
            candidate_membership_partition=Path(
                _candidate_partition(config)
            ),
            assessed_at=action_started_at,
            created_at=action_started_at,
            plan_path=config.apply_plan_path,
        )
        if not isinstance(evidence, UniverseMembershipApplyPlanEvidence):
            raise DailyUniverseMembershipRunnerError(
                "Membership Apply-plan evidence contract is invalid"
            )
        plan = evidence.plan
        if (
            evidence.plan_path != config.apply_plan_path
            or plan.publication.session_date != config.target_session
            or Path(plan.data_root) != config.data_root
            or Path(plan.candidate_root) != config.candidate_root
            or Path(plan.candidate_membership_partition)
            != Path(_candidate_partition(config))
            or not _is_fingerprint(plan.logical_fingerprint)
            or plan.external_request_count != 0
            or plan.canonical_data_write_count != 0
            or plan.apply_authorized
            or plan.historical_coverage_authorized
            or plan.research_performance_authorized
        ):
            raise DailyUniverseMembershipRunnerError(
                "Membership Apply plan differs from the planned action"
            )
        return plan.logical_fingerprint

    raise DailyUniverseMembershipRunnerError(
        "Membership sidecar action is outside the bounded runner"
    )


def _candidate_partition(config: DailyUniverseMembershipRunConfig) -> str:
    return (
        config.candidate_root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / f"methodology_version={METHODOLOGY_VERSION}"
        / f"session_date={config.target_session.isoformat()}"
    ).as_posix()


def _action_evidence(
    *,
    sequence: int,
    action: MembershipSidecarAction,
    started_at: datetime,
    completed_at: datetime,
    outcome: str,
    pre_plan: DailyUniverseMembershipSidecarPlan,
    post_plan: DailyUniverseMembershipSidecarPlan | None,
    artifact_fingerprint: str | None,
    failure_type: str | None,
) -> MembershipRunActionEvidence:
    logical = {
        "sequence": sequence,
        "action": action.value,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "outcome": outcome,
        "pre_plan_fingerprint": pre_plan.logical_content_fingerprint,
        "post_plan_fingerprint": (
            None if post_plan is None else post_plan.logical_content_fingerprint
        ),
        "artifact_fingerprint": artifact_fingerprint,
        "failure_type": failure_type,
    }
    return MembershipRunActionEvidence(
        sequence=sequence,
        action=action.value,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        outcome=outcome,
        pre_plan_fingerprint=pre_plan.logical_content_fingerprint,
        post_plan_fingerprint=(
            None if post_plan is None else post_plan.logical_content_fingerprint
        ),
        artifact_fingerprint=artifact_fingerprint,
        failure_type=failure_type,
        logical_content_fingerprint=_fingerprint(logical),
    )


def _verify_action_evidence(
    item: MembershipRunActionEvidence,
    *,
    sequence: int,
) -> None:
    logical = asdict(item)
    logical.pop("logical_content_fingerprint")
    try:
        started = _parse_utc(item.started_at)
        completed = _parse_utc(item.completed_at)
        action = MembershipSidecarAction(item.action)
    except ValueError as exc:
        raise DailyUniverseMembershipRunnerError(
            "Membership action evidence is malformed"
        ) from exc
    succeeded = item.outcome == "succeeded"
    if (
        item.sequence != sequence
        or action
        not in {
            MembershipSidecarAction.PREPARE_CANDIDATE,
            MembershipSidecarAction.PREPARE_APPLY_PLAN,
        }
        or completed < started
        or item.outcome not in {"succeeded", "failed"}
        or not _is_fingerprint(item.pre_plan_fingerprint)
        or succeeded != _is_fingerprint(item.post_plan_fingerprint)
        or succeeded != _is_fingerprint(item.artifact_fingerprint)
        or succeeded == (item.failure_type is not None)
        or item.logical_content_fingerprint != _fingerprint(logical)
    ):
        raise DailyUniverseMembershipRunnerError(
            "Membership action evidence conflicts with its outcome"
        )


def _validate_config(
    *,
    config: DailyUniverseMembershipRunConfig,
    maximum_actions: int,
    maximum_elapsed_seconds: int,
) -> None:
    if (
        not isinstance(config, DailyUniverseMembershipRunConfig)
        or not isinstance(config.primary_automation_paths, DailyEodAutomationPaths)
        or config.primary_automation_paths.data_root != config.data_root
        or config.catalog_as_of_date > config.target_session
        or config.candidate_root.name != CANDIDATE_ROOT_NAME
        or config.apply_plan_path.name != APPLY_PLAN_NAME
        or config.candidate_root.parent != config.apply_plan_path.parent
        or config.candidate_root.parent.name
        != f"session_date={config.target_session.isoformat()}"
        or type(maximum_actions) is not int
        or not 1 <= maximum_actions <= MAXIMUM_ACTIONS
        or type(maximum_elapsed_seconds) is not int
        or not 1 <= maximum_elapsed_seconds <= MAXIMUM_ELAPSED_SECONDS
    ):
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar run configuration is invalid"
        )


@contextmanager
def _exclusive_session_lock(session_root: Path) -> Iterator[None]:
    if session_root.is_symlink() or not session_root.is_dir():
        raise DailyUniverseMembershipRunnerError(
            "Membership execution requires an existing session workspace"
        )
    metadata = session_root.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise DailyUniverseMembershipRunnerError(
            "Membership session workspace must be owner-only"
        )
    descriptor = os.open(
        session_root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DailyUniverseMembershipRunnerError(
                "another Membership sidecar runner owns this session"
            ) from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _result(
    *,
    status: MembershipRunStatus,
    config: DailyUniverseMembershipRunConfig,
    started_at: datetime,
    completed_at: datetime,
    maximum_actions: int,
    maximum_elapsed_seconds: int,
    evidence: tuple[MembershipRunActionEvidence, ...],
    final_plan: DailyUniverseMembershipSidecarPlan,
    reasons: tuple[str, ...],
    execute: bool,
) -> DailyUniverseMembershipRunResult:
    logical = {
        "contract_version": CONTRACT_VERSION,
        "status": status.value,
        "target_session": config.target_session.isoformat(),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "maximum_actions": maximum_actions,
        "maximum_elapsed_seconds": maximum_elapsed_seconds,
        "action_attempt_count": len(evidence),
        "action_success_count": sum(
            item.outcome == "succeeded" for item in evidence
        ),
        "action_evidence": [_jsonable(asdict(item)) for item in evidence],
        "final_plan_status": final_plan.status.value,
        "final_next_action": final_plan.next_action.value,
        "final_plan_fingerprint": final_plan.logical_content_fingerprint,
        "reason_codes": list(reasons),
        "execution_enabled": execute,
        "exclusive_process_lock": execute,
        "automatic_retry_enabled": False,
        "automatic_recovery_enabled": False,
        "website_pipeline_blocked": False,
        "primary_pipeline_invocation_count": 0,
        "external_request_count": 0,
        "production_write_count": 0,
        "canonical_membership_apply_performed": False,
        "historical_coverage_authorized": False,
        "research_performance_authorized": False,
        "scheduler_installation_performed": False,
    }
    result = DailyUniverseMembershipRunResult(
        contract_version=CONTRACT_VERSION,
        status=status,
        target_session=config.target_session.isoformat(),
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        maximum_actions=maximum_actions,
        maximum_elapsed_seconds=maximum_elapsed_seconds,
        action_attempt_count=len(evidence),
        action_success_count=sum(
            item.outcome == "succeeded" for item in evidence
        ),
        action_evidence=evidence,
        final_plan_status=final_plan.status.value,
        final_next_action=final_plan.next_action.value,
        final_plan_fingerprint=final_plan.logical_content_fingerprint,
        reason_codes=reasons,
        execution_enabled=execute,
        exclusive_process_lock=execute,
        automatic_retry_enabled=False,
        automatic_recovery_enabled=False,
        website_pipeline_blocked=False,
        primary_pipeline_invocation_count=0,
        external_request_count=0,
        production_write_count=0,
        canonical_membership_apply_performed=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
        scheduler_installation_performed=False,
        logical_content_fingerprint=_fingerprint(logical),
    )
    verify_daily_universe_membership_run_result(result)
    return result


def _monotonic_clock(clock: Clock, *, not_before: datetime) -> datetime:
    observed = _aware_utc(clock())
    if observed < not_before:
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar clock moved backwards"
        )
    return observed


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DailyUniverseMembershipRunnerError(
            "Membership sidecar time must be timezone aware"
        )
    return value.astimezone(UTC)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp is not timezone aware")
    return parsed.astimezone(UTC)


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
