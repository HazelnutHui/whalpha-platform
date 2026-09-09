from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_universe_membership_sidecar as service
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_universe_membership_continuation import (
    DailyUniverseMembershipContinuationResult,
)


SESSION = date(2026, 9, 8)
CATALOG = date(2026, 8, 14)
CHECKED_AT = datetime(2026, 9, 9, 8, 30, tzinfo=UTC)


def _automation_plan(
    status: PlanStatus,
    action: NextAction,
    *,
    reasons: tuple[str, ...] = ("test_reason",),
) -> DailyEodAutomationPlan:
    plan = DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session=SESSION.isoformat(),
        prior_session="2026-09-04",
        status=status,
        next_action=action,
        reason_codes=reasons,
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint="",
    )
    logical = asdict(plan)
    logical.pop("logical_content_fingerprint")
    return replace(
        plan,
        logical_content_fingerprint=service._fingerprint(
            service._jsonable(logical)
        ),
    )


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    session_root = tmp_path / "sessions" / f"session_date={SESSION.isoformat()}"
    session_root.mkdir(parents=True, exist_ok=True)
    return (
        tmp_path / "canonical",
        session_root / service.CANDIDATE_ROOT_NAME,
        session_root / service.APPLY_PLAN_NAME,
    )


def _catalog(*_: object, **__: object) -> object:
    return SimpleNamespace(
        manifest=SimpleNamespace(
            as_of_date=CATALOG,
            created_at=datetime(2026, 8, 15, tzinfo=UTC),
            logical_content_sha256="c" * 64,
        )
    )


def _candidate(candidate_root: Path, *, outcome_only: bool = False):
    partition = service._candidate_partition(candidate_root, SESSION)
    return DailyUniverseMembershipContinuationResult(
        status=(
            "outcome_only_candidate"
            if outcome_only
            else "candidate_ready_for_publication_plan"
        ),
        session_date=SESSION.isoformat(),
        methodology_version=service.METHODOLOGY_VERSION,
        candidate_partition_path=str(partition),
        candidate_status="already_present",
        record_count=19_964,
        membership_logical_fingerprint="a" * 64,
        point_in_time_eligibility=(
            "outcome_reconciliation_only" if outcome_only else "signal_eligible"
        ),
        knowledge_time_assessment_fingerprint="b" * 64,
        canonical_publication_fingerprint=None,
    )


def _plan(
    tmp_path: Path,
    *,
    primary: DailyEodAutomationPlan,
    candidate_reader=None,
    apply_plan_reader=None,
    canonical_reader=None,
):
    data_root, candidate_root, apply_plan_path = _paths(tmp_path)
    data_root.mkdir(exist_ok=True)
    values = {
        "checked_at": CHECKED_AT,
        "target_session": SESSION,
        "data_root": data_root,
        "catalog_as_of_date": CATALOG,
        "candidate_root": candidate_root,
        "apply_plan_path": apply_plan_path,
        "primary_automation_plan": primary,
        "catalog_reader": _catalog,
    }
    if candidate_reader is not None:
        values["candidate_reader"] = candidate_reader
    if apply_plan_reader is not None:
        values["apply_plan_reader"] = apply_plan_reader
    if canonical_reader is not None:
        values["canonical_reader"] = canonical_reader
    return service.plan_daily_universe_membership_sidecar(**values)


def test_waits_until_same_session_canonical_inputs_exist(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.WAITING_FOR_AUTHORIZED_INPUT,
            NextAction.PREPARE_IDENTITY_CATCHUP,
        ),
    )

    assert plan.status is service.MembershipSidecarStatus.WAITING
    assert plan.next_action is service.MembershipSidecarAction.WAIT_FOR_CANONICAL_INPUT
    assert plan.website_pipeline_blocked is False


def test_reports_candidate_preparation_without_executing_it(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_PHASE1A,
        ),
        candidate_reader=lambda **_: pytest.fail("missing candidate cannot be read"),
    )

    assert plan.status is service.MembershipSidecarStatus.READY
    assert plan.next_action is service.MembershipSidecarAction.PREPARE_CANDIDATE
    assert plan.external_request_count == 0
    assert plan.production_write_count == 0


def test_candidate_waits_for_primary_final_boundary(tmp_path: Path) -> None:
    _, candidate_root, _ = _paths(tmp_path)
    service._candidate_partition(candidate_root, SESSION).mkdir(parents=True)
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_STRATEGY_CHANNELS,
        ),
        candidate_reader=lambda **_: _candidate(candidate_root),
    )

    assert plan.status is service.MembershipSidecarStatus.WAITING
    assert plan.next_action is service.MembershipSidecarAction.WAIT_FOR_PRIMARY_PIPELINE
    assert plan.record_count == 19_964


def test_final_primary_boundary_allows_apply_plan_preparation(tmp_path: Path) -> None:
    _, candidate_root, _ = _paths(tmp_path)
    service._candidate_partition(candidate_root, SESSION).mkdir(parents=True)
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.ANALYTICS_READY,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        ),
        candidate_reader=lambda **_: _candidate(candidate_root),
    )

    assert plan.status is service.MembershipSidecarStatus.READY
    assert plan.next_action is service.MembershipSidecarAction.PREPARE_APPLY_PLAN


def test_exact_apply_plan_requires_review(tmp_path: Path) -> None:
    data_root, candidate_root, apply_plan_path = _paths(tmp_path)
    candidate_partition = service._candidate_partition(candidate_root, SESSION)
    candidate_partition.mkdir(parents=True)
    apply_plan_path.touch()
    membership_plan = SimpleNamespace(
        data_root=str(data_root),
        candidate_root=str(candidate_root),
        candidate_membership_partition=str(candidate_partition),
        publication=SimpleNamespace(
            session_date=SESSION,
            membership_logical_fingerprint="a" * 64,
        ),
        logical_fingerprint="d" * 64,
    )
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.ANALYTICS_READY,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        ),
        candidate_reader=lambda **_: _candidate(candidate_root),
        apply_plan_reader=lambda **_: SimpleNamespace(
            plan=membership_plan,
            plan_path=apply_plan_path,
        ),
    )

    assert plan.status is service.MembershipSidecarStatus.REVIEW_REQUIRED
    assert plan.next_action is service.MembershipSidecarAction.REVIEW_APPLY
    assert plan.apply_plan_fingerprint == "d" * 64


def test_completed_canonical_membership_preempts_workspace(tmp_path: Path) -> None:
    data_root, _, _ = _paths(tmp_path)
    data_root.mkdir(exist_ok=True)
    membership, publication = service._canonical_targets(data_root, SESSION)
    membership.mkdir(parents=True)
    publication.mkdir(parents=True)
    canonical = SimpleNamespace(
        records=(object(), object()),
        membership_manifest=SimpleNamespace(logical_fingerprint="a" * 64),
        publication=SimpleNamespace(
            point_in_time_eligibility=SimpleNamespace(value="signal_eligible"),
            logical_fingerprint="e" * 64,
        ),
    )
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.ANALYTICS_READY,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        ),
        canonical_reader=lambda **_: canonical,
    )

    assert plan.status is service.MembershipSidecarStatus.COMPLETE
    assert plan.next_action is service.MembershipSidecarAction.NONE
    assert plan.canonical_publication_fingerprint == "e" * 64


def test_partial_canonical_membership_is_non_serving_block(tmp_path: Path) -> None:
    data_root, _, _ = _paths(tmp_path)
    data_root.mkdir(exist_ok=True)
    membership, _ = service._canonical_targets(data_root, SESSION)
    membership.mkdir(parents=True)
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.ANALYTICS_READY,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        ),
    )

    assert plan.status is service.MembershipSidecarStatus.BLOCKED
    assert plan.website_pipeline_blocked is False
    assert "partial" in plan.reason_codes[0]


def test_outcome_only_candidate_cannot_advance(tmp_path: Path) -> None:
    _, candidate_root, _ = _paths(tmp_path)
    service._candidate_partition(candidate_root, SESSION).mkdir(parents=True)
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.ANALYTICS_READY,
            NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        ),
        candidate_reader=lambda **_: _candidate(candidate_root, outcome_only=True),
    )

    assert plan.status is service.MembershipSidecarStatus.BLOCKED
    assert "outcome_only" in plan.reason_codes[0]


def test_plan_fingerprint_and_non_blocking_flag_are_enforced(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        primary=_automation_plan(
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_PHASE1A,
        ),
    )

    with pytest.raises(service.DailyUniverseMembershipSidecarError, match="fingerprint"):
        service.verify_daily_universe_membership_sidecar_plan(
            replace(plan, website_pipeline_blocked=True)
        )
