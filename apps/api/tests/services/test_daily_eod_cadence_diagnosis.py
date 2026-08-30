from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tip_api.services import daily_eod_cadence_diagnosis as diagnosis
from tip_api.services import daily_eod_cadence_evidence as custody
from tip_api.services import daily_eod_pipeline_cadence as cadence
from tip_api.services import daily_eod_pipeline_scheduler as scheduler
from tip_api.services import daily_eod_run_journal as journal


TARGET = date(2026, 8, 28)
PRIOR = date(2026, 8, 27)
CHECKED = datetime(2026, 8, 29, 12, tzinfo=UTC)
STARTED = CHECKED + timedelta(seconds=1)


def _root(tmp_path):
    root = tmp_path / "daily-runs"
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    return root


def _plans():
    pipeline = scheduler.plan_daily_eod_pipeline_wake(
        checked_at=CHECKED,
        completed_sessions=(PRIOR,),
        review_enabled_candidate=True,
    )
    bounded = cadence.plan_bounded_pipeline_cadence(
        checked_at=CHECKED,
        cadence_started_at=CHECKED - timedelta(minutes=15),
        pipeline_plan=pipeline,
        review_enabled_candidate=True,
    )
    return pipeline, bounded


def _reserve(root):
    pipeline, bounded = _plans()
    custody.reserve_cadence_wake(
        run_root=root,
        target_session=TARGET,
        cadence_plan=bounded,
        pipeline_plan=pipeline,
        started_at=STARTED,
    )


def _events(root):
    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        return locked.read_events()


def _append_attempt(root, start_type: str, terminal_type: str | None = None):
    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        attempt_id = journal.new_attempt_id(
            target_session=TARGET,
            plan_fingerprint="d" * 64,
            sequence=len(locked.read_events()) + 1,
        )
        started = locked.append(
            event_type=start_type,
            attempt_id=attempt_id,
            details={"operation": "test"},
            observed_at=STARTED + timedelta(seconds=1),
        )
        terminal = (
            None
            if terminal_type is None
            else locked.append(
                event_type=terminal_type,
                attempt_id=attempt_id,
                details={"reason_code": "test"},
                observed_at=STARTED + timedelta(seconds=2),
            )
        )
        return started, terminal


def _diagnose(root):
    return diagnosis.diagnose_unresolved_cadence_wake(
        events=_events(root),
        target_session=TARGET,
        checked_at=STARTED + timedelta(minutes=1),
    )


def test_no_pending_wake_is_a_zero_authority_result() -> None:
    report = diagnosis.diagnose_unresolved_cadence_wake(
        events=(),
        target_session=TARGET,
        checked_at=CHECKED,
    )

    assert report.status is diagnosis.CadenceDiagnosisStatus.NO_PENDING_WAKE
    assert report.next_action == "none"
    assert report.filesystem_write_count == 0


def test_reservation_without_nested_action_remains_unknown(tmp_path) -> None:
    root = _root(tmp_path)
    _reserve(root)

    report = _diagnose(root)

    assert report.status is diagnosis.CadenceDiagnosisStatus.OUTCOME_UNKNOWN
    assert report.next_action == "operator_confirm_invocation_boundary"
    assert report.events_after_reservation == 0
    assert not report.action_replayed


@pytest.mark.parametrize(
    ("start_type", "expected_action"),
    (
        (journal.ACQUISITION_START_EVENT, "recover_acquisition_attempt"),
        (journal.CANONICAL_APPLY_START_EVENT, "recover_canonical_apply"),
        (journal.START_EVENT, "recover_offline_action"),
    ),
)
def test_unresolved_nested_action_routes_only_to_existing_no_replay_recovery(
    tmp_path,
    start_type,
    expected_action,
) -> None:
    root = _root(tmp_path)
    _reserve(root)
    started, _ = _append_attempt(root, start_type)

    report = _diagnose(root)

    assert report.status is diagnosis.CadenceDiagnosisStatus.ACTION_RECOVERY_REQUIRED
    assert report.next_action == expected_action
    assert report.nested_start_event_fingerprint == started.event_fingerprint
    assert not report.automatic_recovery_enabled


@pytest.mark.parametrize(
    ("start_type", "terminal_type", "expected"),
    (
        (
            journal.ACQUISITION_START_EVENT,
            "acquisition_package_ready",
            "advanced_candidate",
        ),
        (
            journal.ACQUISITION_START_EVENT,
            "acquisition_rate_limited",
            "no_change_candidate",
        ),
        (journal.START_EVENT, "action_failed", "failed_candidate"),
    ),
)
def test_formal_nested_terminal_is_review_ready_but_not_auto_resolved(
    tmp_path,
    start_type,
    terminal_type,
    expected,
) -> None:
    root = _root(tmp_path)
    _reserve(root)
    _, terminal = _append_attempt(root, start_type, terminal_type)

    report = _diagnose(root)

    assert report.status is diagnosis.CadenceDiagnosisStatus.KNOWN_RESULT_REVIEW_READY
    assert report.next_action == "review_no_replay_cadence_resolution"
    assert report.terminal_outcome_candidate == expected
    assert report.nested_terminal_event_fingerprint == terminal.event_fingerprint
    assert not report.automatic_resolution_enabled


def test_unexpected_standalone_event_after_reservation_is_blocked(tmp_path) -> None:
    root = _root(tmp_path)
    _reserve(root)
    with journal.locked_daily_eod_run_journal(
        run_root=root,
        target_session=TARGET,
    ) as locked:
        locked.append(
            event_type=journal.ACQUISITION_REVIEW_EVENT,
            attempt_id=journal.new_attempt_id(
                target_session=TARGET,
                plan_fingerprint="e" * 64,
                sequence=len(locked.read_events()) + 1,
            ),
            details={"review_fingerprint": "f" * 64},
            observed_at=STARTED + timedelta(seconds=1),
        )

    report = _diagnose(root)

    assert report.status is diagnosis.CadenceDiagnosisStatus.BLOCKED
    assert report.next_action == "operator_diagnosis"


def test_runtime_report_tampering_is_rejected() -> None:
    report = diagnosis.diagnose_unresolved_cadence_wake(
        events=(),
        target_session=TARGET,
        checked_at=CHECKED,
    )

    with pytest.raises(diagnosis.DailyEodCadenceDiagnosisError, match="content"):
        diagnosis.verify_daily_eod_cadence_diagnosis(
            replace(report, production_write_count=1)
        )
