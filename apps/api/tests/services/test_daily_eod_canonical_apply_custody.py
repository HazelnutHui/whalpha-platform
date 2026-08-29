from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.providers.massive.same_day_catchup import (
    CatchupApprovalPlanEvidenceV1,
)
from tip_api.services.daily_eod_acquisition_custody import (
    acquisition_attempts_from_events,
    acquisition_operator_reviews_from_events,
)
from tip_api.services.daily_eod_automation import (
    ArtifactObservation,
    ArtifactStatus,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)
from tip_api.services.daily_eod_canonical_apply_custody import (
    DailyEodCanonicalApplyConfig,
    DailyEodCanonicalApplyCustodyError,
    record_canonical_apply_success,
    recover_canonical_apply,
    reserve_canonical_apply,
)
from tip_api.services.daily_eod_readiness import (
    AcquisitionOperatorReview,
    OperatorReviewDisposition,
    OperatorReviewEvidenceCode,
    OperatorReviewPurpose,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import (
    locked_daily_eod_run_journal,
    new_attempt_id,
    unresolved_started_event,
)


TARGET = date(2026, 8, 27)
LATEST = date(2026, 8, 26)
CHECKED = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)
PLAN_SHA = "1" * 64
PLAN_CONTENT_SHA = "2" * 64
CURRENT_STATE = "3" * 64
PACKAGE_MANIFEST = "4" * 64
PACKAGE_CONTENT = "5" * 64


def run_root(tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    return root


def automation_paths(tmp_path: Path) -> DailyEodAutomationPaths:
    return DailyEodAutomationPaths(
        data_root=tmp_path / "data",
        phase1a_audit=tmp_path / "phase1a",
        prior_phase1b_audit=tmp_path / "prior-phase1b",
        phase1b_audit=tmp_path / "phase1b",
        prior_candidate_audit=tmp_path / "prior-candidate",
        candidate_audit=tmp_path / "candidate",
        entry_geometry_audit=tmp_path / "entry",
        phase2_audit=tmp_path / "phase2",
        preview_bundle=tmp_path / "preview",
        strategy_channel_audit=tmp_path / "strategy",
    )


def config(tmp_path: Path, root: Path) -> DailyEodCanonicalApplyConfig:
    unique = tmp_path.name
    paths = automation_paths(tmp_path)
    paths.data_root.mkdir(exist_ok=True)
    return DailyEodCanonicalApplyConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.PREPARE_IDENTITY_CATCHUP,
        package_path=Path(f"/tmp/{unique}-package"),
        approval_plan_path=Path(f"/tmp/{unique}-plan.json"),
        approved_plan_sha256=PLAN_SHA,
        expected_current_state_fingerprint=CURRENT_STATE,
        data_root=paths.data_root,
        run_root=root,
        automation_paths=paths,
    )


def plan_evidence(
    cfg: DailyEodCanonicalApplyConfig,
    target: Path,
    **overrides,
) -> CatchupApprovalPlanEvidenceV1:
    values = {
        "operation": "identity",
        "session_date": TARGET,
        "plan_path": str(cfg.approval_plan_path),
        "plan_file_sha256": PLAN_SHA,
        "plan_content_sha256": PLAN_CONTENT_SHA,
        "data_root": str(cfg.data_root),
        "fetch_package_path": str(cfg.package_path),
        "fetch_package_manifest_sha256": PACKAGE_MANIFEST,
        "fetch_package_content_sha256": PACKAGE_CONTENT,
        "expected_current_state_fingerprint": CURRENT_STATE,
        "publication_order": (str(target),),
        "inventory_change_file_count": 2,
        "inventory_change_bytes": 100,
    }
    values.update(overrides)
    return CatchupApprovalPlanEvidenceV1.model_validate(values)


def setup_completed_acquisition(
    cfg: DailyEodCanonicalApplyConfig,
) -> tuple:
    with locked_daily_eod_run_journal(
        run_root=cfg.run_root,
        target_session=TARGET,
    ) as journal:
        attempt_id = new_attempt_id(
            target_session=TARGET,
            plan_fingerprint="6" * 64,
            sequence=1,
        )
        journal.append(
            event_type="acquisition_started",
            attempt_id=attempt_id,
            observed_at=datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
            details={
                "acquisition_action": cfg.acquisition_action.value,
                "attempt_number": 1,
                "package_path": str(cfg.package_path),
            },
        )
        journal.append(
            event_type="acquisition_package_ready",
            attempt_id=attempt_id,
            observed_at=datetime(2026, 8, 27, 20, 32, tzinfo=UTC),
            details={
                "package_manifest_sha256": PACKAGE_MANIFEST,
                "package_content_sha256": PACKAGE_CONTENT,
            },
        )
        return journal.read_events()


def readiness_fingerprint(cfg: DailyEodCanonicalApplyConfig) -> str:
    with locked_daily_eod_run_journal(
        run_root=cfg.run_root,
        target_session=TARGET,
    ) as journal:
        events = journal.read_events()
    return plan_daily_eod_readiness(
        checked_at=CHECKED,
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=cfg.acquisition_action,
        attempts=acquisition_attempts_from_events(
            events,
            target_session=TARGET,
            acquisition_action=cfg.acquisition_action,
        ),
        operator_reviews=acquisition_operator_reviews_from_events(
            events,
            target_session=TARGET,
            acquisition_action=cfg.acquisition_action,
        ),
    ).logical_content_fingerprint


def setup_reviewed_retry_completed_acquisition(
    cfg: DailyEodCanonicalApplyConfig,
) -> tuple:
    first_started_at = datetime(2026, 8, 27, 20, 31, tzinfo=UTC)
    reviewed_at = datetime(2026, 8, 27, 20, 32, tzinfo=UTC)
    retry_at = datetime(2026, 8, 27, 20, 46, tzinfo=UTC)
    with locked_daily_eod_run_journal(
        run_root=cfg.run_root,
        target_session=TARGET,
    ) as journal:
        first_attempt_id = new_attempt_id(
            target_session=TARGET,
            plan_fingerprint="a" * 64,
            sequence=1,
        )
        journal.append(
            event_type="acquisition_started",
            attempt_id=first_attempt_id,
            observed_at=first_started_at,
            details={
                "acquisition_action": cfg.acquisition_action.value,
                "attempt_number": 1,
                "package_path": str(cfg.package_path),
            },
        )
        failure = journal.append(
            event_type="acquisition_permanent_failed",
            attempt_id=first_attempt_id,
            observed_at=reviewed_at,
            details={"request_count": 1},
        )
        review = AcquisitionOperatorReview(
            purpose=OperatorReviewPurpose.TERMINAL_FAILURE_RETRY,
            acquisition_action=cfg.acquisition_action,
            attempt_sequence=1,
            reviewed_at=reviewed_at,
            not_before=retry_at,
            disposition=OperatorReviewDisposition.AUTHORIZE_ONE_FETCH_AFTER,
            evidence_code=(
                OperatorReviewEvidenceCode.LOCAL_CONFIGURATION_CORRECTED
            ),
            source_event_fingerprint=failure.event_fingerprint,
        )
        review_id = new_attempt_id(
            target_session=TARGET,
            plan_fingerprint=review.logical_fingerprint,
            sequence=3,
        )
        journal.append(
            event_type="acquisition_operator_reviewed",
            attempt_id=review_id,
            observed_at=reviewed_at,
            details={
                "acquisition_action": cfg.acquisition_action.value,
                "purpose": review.purpose.value,
                "attempt_sequence": review.attempt_sequence,
                "disposition": review.disposition.value,
                "evidence_code": review.evidence_code.value,
                "not_before": review.not_before.isoformat(),
                "source_event_fingerprint": review.source_event_fingerprint,
                "review_fingerprint": review.logical_fingerprint,
            },
        )
        second_attempt_id = new_attempt_id(
            target_session=TARGET,
            plan_fingerprint="b" * 64,
            sequence=4,
        )
        journal.append(
            event_type="acquisition_started",
            attempt_id=second_attempt_id,
            observed_at=retry_at,
            details={
                "acquisition_action": cfg.acquisition_action.value,
                "attempt_number": 2,
                "package_path": str(cfg.package_path),
            },
        )
        journal.append(
            event_type="acquisition_package_ready",
            attempt_id=second_attempt_id,
            observed_at=datetime(2026, 8, 27, 20, 47, tzinfo=UTC),
            details={
                "package_manifest_sha256": PACKAGE_MANIFEST,
                "package_content_sha256": PACKAGE_CONTENT,
            },
        )
        return journal.read_events()


def automation_plan(*, completed: bool) -> DailyEodAutomationPlan:
    observation = ArtifactObservation(
        stage="identity",
        status=ArtifactStatus.COMPLETED if completed else ArtifactStatus.MISSING,
        path="/data/identity",
        as_of_session=TARGET.isoformat() if completed else None,
        logical_fingerprint="7" * 64 if completed else None,
    )
    return DailyEodAutomationPlan(
        contract_version="daily-eod-automation-plan/1.1",
        target_session=TARGET.isoformat(),
        prior_session=LATEST.isoformat(),
        status=(
            PlanStatus.WAITING_FOR_AUTHORIZED_INPUT
            if completed
            else PlanStatus.WAITING_FOR_AUTHORIZED_INPUT
        ),
        next_action=(
            NextAction.PREPARE_EOD_CATCHUP
            if completed
            else NextAction.PREPARE_IDENTITY_CATCHUP
        ),
        reason_codes=("fixture",),
        observations=(observation,),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=("8" if completed else "9") * 64,
    )


def reserve(
    cfg: DailyEodCanonicalApplyConfig,
    evidence: CatchupApprovalPlanEvidenceV1,
    **kwargs,
):
    return reserve_canonical_apply(
        config=cfg,
        checked_at=CHECKED,
        expected_readiness_fingerprint=readiness_fingerprint(cfg),
        clock=lambda: datetime(2026, 8, 27, 21, 1, tzinfo=UTC),
        plan_reader=lambda **_kwargs: evidence,
        inventory_reader=lambda _root: CURRENT_STATE,
        **kwargs,
    )


def test_reservation_binds_completed_acquisition_plan_and_inventory(
    tmp_path: Path,
) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    evidence = plan_evidence(cfg, tmp_path / "canonical-target")

    result = reserve(
        cfg,
        evidence,
        authorization_file_sha256="a" * 64,
        authorization_content_sha256="b" * 64,
    )

    assert result.outcome == "reserved"
    assert result.plan_evidence == evidence
    assert result.as_dict()["apply_executed_by_custody"] is False
    assert result.as_dict()["production_write_count"] == 0
    assert result.event.details["authorization_file_sha256"] == "a" * 64
    assert result.event.details["authorization_content_sha256"] == "b" * 64
    with locked_daily_eod_run_journal(run_root=root, target_session=TARGET) as journal:
        assert unresolved_started_event(journal.read_events()) == result.event


def test_reservation_accepts_completed_retry_with_exact_operator_review(
    tmp_path: Path,
) -> None:
    root = run_root(tmp_path)
    cfg = replace(
        config(tmp_path, root),
        acquisition_action=NextAction.PREPARE_EOD_CATCHUP,
    )
    setup_reviewed_retry_completed_acquisition(cfg)
    evidence = plan_evidence(
        cfg,
        tmp_path / "canonical-target",
        operation="eod",
    )

    result = reserve(cfg, evidence)

    assert result.outcome == "reserved"
    assert result.plan_evidence == evidence


def test_reservation_rejects_stale_readiness_or_changed_inventory(tmp_path: Path) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    evidence = plan_evidence(cfg, tmp_path / "canonical-target")
    with pytest.raises(DailyEodCanonicalApplyCustodyError, match="stale"):
        reserve_canonical_apply(
            config=cfg,
            checked_at=CHECKED,
            expected_readiness_fingerprint="a" * 64,
            clock=lambda: datetime(2026, 8, 27, 21, 1, tzinfo=UTC),
            plan_reader=lambda **_kwargs: evidence,
            inventory_reader=lambda _root: CURRENT_STATE,
        )
    with pytest.raises(DailyEodCanonicalApplyCustodyError, match="inventory changed"):
        reserve_canonical_apply(
            config=cfg,
            checked_at=CHECKED,
            expected_readiness_fingerprint=readiness_fingerprint(cfg),
            clock=lambda: datetime(2026, 8, 27, 21, 1, tzinfo=UTC),
            plan_reader=lambda **_kwargs: evidence,
            inventory_reader=lambda _root: "b" * 64,
        )


def test_reservation_rejects_wrong_package_hash_or_existing_target(tmp_path: Path) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    target = tmp_path / "canonical-target"
    wrong = plan_evidence(
        cfg,
        target,
        fetch_package_content_sha256="c" * 64,
    )
    with pytest.raises(DailyEodCanonicalApplyCustodyError, match="differs"):
        reserve(cfg, wrong)
    target.mkdir()
    with pytest.raises(DailyEodCanonicalApplyCustodyError, match="no longer absent"):
        reserve(cfg, plan_evidence(cfg, target))


def test_success_requires_formal_stage_completion_and_closes_attempt(tmp_path: Path) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    reserve(cfg, plan_evidence(cfg, tmp_path / "canonical-target"))

    result = record_canonical_apply_success(
        config=cfg,
        authorization_decision_fingerprint="c" * 64,
        clock=lambda: datetime(2026, 8, 27, 21, 2, tzinfo=UTC),
        planner=lambda **_kwargs: automation_plan(completed=True),
    )

    assert result.outcome == "succeeded"
    assert result.automation_plan.next_action is NextAction.PREPARE_EOD_CATCHUP
    assert result.event.details["authorization_decision_fingerprint"] == "c" * 64
    with locked_daily_eod_run_journal(run_root=root, target_session=TARGET) as journal:
        assert unresolved_started_event(journal.read_events()) is None


def test_unproven_success_stays_unresolved_for_recovery(tmp_path: Path) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    reserved = reserve(cfg, plan_evidence(cfg, tmp_path / "canonical-target"))

    with pytest.raises(DailyEodCanonicalApplyCustodyError, match="recovery required"):
        record_canonical_apply_success(
            config=cfg,
            planner=lambda **_kwargs: automation_plan(completed=False),
        )
    with locked_daily_eod_run_journal(run_root=root, target_session=TARGET) as journal:
        assert unresolved_started_event(journal.read_events()) == reserved.event


def test_recovery_reconciles_formally_completed_stage(tmp_path: Path) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    reserve(cfg, plan_evidence(cfg, tmp_path / "canonical-target"))

    result = recover_canonical_apply(
        config=cfg,
        clock=lambda: datetime(2026, 8, 27, 21, 3, tzinfo=UTC),
        planner=lambda **_kwargs: automation_plan(completed=True),
    )

    assert result.outcome == "recovered_succeeded"
    assert result.as_dict()["apply_executed_by_custody"] is False


def test_recovery_allows_retry_only_when_targets_absent_and_inventory_unchanged(
    tmp_path: Path,
) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    evidence = plan_evidence(cfg, tmp_path / "canonical-target")
    reserve(cfg, evidence)

    result = recover_canonical_apply(
        config=cfg,
        clock=lambda: datetime(2026, 8, 27, 21, 3, tzinfo=UTC),
        planner=lambda **_kwargs: automation_plan(completed=False),
        plan_reader=lambda **_kwargs: evidence,
        inventory_reader=lambda _root: CURRENT_STATE,
    )

    assert result.outcome == "recovered_not_completed"
    assert result.reason_code == "no_canonical_write_detected"


@pytest.mark.parametrize("changed_inventory", (False, True))
def test_recovery_blocks_partial_or_changed_state(
    tmp_path: Path,
    changed_inventory: bool,
) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    target = tmp_path / "canonical-target"
    evidence = plan_evidence(cfg, target)
    reserve(cfg, evidence)
    if not changed_inventory:
        target.mkdir()

    result = recover_canonical_apply(
        config=cfg,
        clock=lambda: datetime(2026, 8, 27, 21, 3, tzinfo=UTC),
        planner=lambda **_kwargs: automation_plan(completed=False),
        plan_reader=lambda **_kwargs: evidence,
        inventory_reader=lambda _root: (
            "d" * 64 if changed_inventory else CURRENT_STATE
        ),
    )

    assert result.outcome == "recovery_blocked"


def test_recovery_requires_exact_reserved_inputs(tmp_path: Path) -> None:
    root = run_root(tmp_path)
    cfg = config(tmp_path, root)
    setup_completed_acquisition(cfg)
    reserve(cfg, plan_evidence(cfg, tmp_path / "canonical-target"))
    changed = replace(cfg, approved_plan_sha256="e" * 64)

    with pytest.raises(DailyEodCanonicalApplyCustodyError, match="inputs differ"):
        recover_canonical_apply(
            config=changed,
            planner=lambda **_kwargs: automation_plan(completed=False),
        )
