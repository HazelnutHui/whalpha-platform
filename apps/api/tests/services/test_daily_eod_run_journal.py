from __future__ import annotations

import fcntl
import json
import os
from datetime import UTC, date, datetime

import pytest

from tip_api.services import daily_eod_run_journal as journal


SESSION = date(2026, 8, 27)
PLAN_FP = "a" * 64


def _root(tmp_path):
    root = tmp_path / "daily-runs"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    return root


def test_append_only_events_formally_reread_and_chain(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION) as locked:
        attempt = journal.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PLAN_FP,
            sequence=1,
        )
        started = locked.append(
            event_type="action_started",
            attempt_id=attempt,
            details={"action": "calculate_phase1a", "plan_fingerprint": PLAN_FP},
            observed_at=datetime(2026, 8, 27, 1, tzinfo=UTC),
        )
        completed = locked.append(
            event_type="action_succeeded",
            attempt_id=attempt,
            details={"action": "calculate_phase1a", "reason_code": "completed"},
            observed_at=datetime(2026, 8, 27, 2, tzinfo=UTC),
        )
        events = locked.read_events()
    assert events == (started, completed)
    assert completed.previous_event_fingerprint == started.event_fingerprint
    assert journal.unresolved_started_event(events) is None
    assert (root / "session=2026-08-27" / "event-000001.json").stat().st_mode & 0o777 == 0o400


def test_unresolved_start_rejects_another_start_but_accepts_matching_terminal(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION) as locked:
        attempt = journal.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PLAN_FP,
            sequence=1,
        )
        started = locked.append(
            event_type="action_started",
            attempt_id=attempt,
            details={"action": "calculate_phase1a"},
        )
        assert journal.unresolved_started_event(locked.read_events()) == started
        with pytest.raises(journal.DailyEodRunJournalError, match="unresolved"):
            locked.append(
                event_type="action_started",
                attempt_id="b" * 64,
                details={"action": "calculate_phase1b_incremental"},
            )
        with pytest.raises(journal.DailyEodRunJournalError, match="does not match"):
            locked.append(
                event_type="action_failed",
                attempt_id="b" * 64,
                details={"reason_code": "wrong"},
            )
        locked.append(
            event_type="action_recovered_not_completed",
            attempt_id=attempt,
            details={"reason_code": "safe_retry"},
        )


def test_tampered_event_fails_closed(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION) as locked:
        attempt = journal.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PLAN_FP,
            sequence=1,
        )
        locked.append(
            event_type="action_started",
            attempt_id=attempt,
            details={"action": "calculate_phase1a"},
        )
    event_path = root / "session=2026-08-27" / "event-000001.json"
    event_path.chmod(0o600)
    payload = json.loads(event_path.read_bytes())
    payload["details"]["action"] = "calculate_candidate_daily"
    event_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    event_path.chmod(0o400)
    with pytest.raises(journal.DailyEodRunJournalError, match="fingerprint"):
        with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION):
            pass


def test_unknown_root_entry_and_unsafe_permissions_fail_closed(tmp_path) -> None:
    root = _root(tmp_path)
    (root / "unknown").write_text("x")
    with pytest.raises(journal.DailyEodRunJournalError, match="unknown"):
        with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION):
            pass
    (root / "unknown").unlink()
    root.chmod(0o755)
    with pytest.raises(journal.DailyEodRunJournalError, match="custody"):
        with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION):
            pass


def test_exclusive_lock_rejects_a_second_executor(tmp_path) -> None:
    root = _root(tmp_path)
    lock_path = root / journal.LOCK_FILE
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(journal.DailyEodRunJournalError, match="unavailable"):
            with journal.locked_daily_eod_run_journal(
                run_root=root,
                target_session=SESSION,
            ):
                pass
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def test_run_root_must_be_preprovisioned_and_symlink_free(tmp_path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(journal.DailyEodRunJournalError, match="provisioned"):
        with journal.locked_daily_eod_run_journal(run_root=missing, target_session=SESSION):
            pass
    root = _root(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(journal.DailyEodRunJournalError, match="symlink"):
        with journal.locked_daily_eod_run_journal(run_root=alias, target_session=SESSION):
            pass


def test_corrupt_prior_session_blocks_a_new_session(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION) as locked:
        attempt = journal.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PLAN_FP,
            sequence=1,
        )
        locked.append(
            event_type="action_started",
            attempt_id=attempt,
            details={"action": "calculate_phase1a"},
        )
    event_path = root / "session=2026-08-27" / "event-000001.json"
    event_path.chmod(0o600)
    event_path.write_text("{}\n")
    event_path.chmod(0o400)
    with pytest.raises(journal.DailyEodRunJournalError):
        with journal.locked_daily_eod_run_journal(
            run_root=root,
            target_session=date(2026, 8, 28),
        ):
            pass


def test_unresolved_prior_session_blocks_a_new_session(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION) as locked:
        attempt = journal.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PLAN_FP,
            sequence=1,
        )
        locked.append(
            event_type="action_started",
            attempt_id=attempt,
            details={"action": "calculate_phase1a"},
        )
    with pytest.raises(journal.DailyEodRunJournalError, match="earlier"):
        with journal.locked_daily_eod_run_journal(
            run_root=root,
            target_session=date(2026, 8, 28),
        ):
            pass


def test_first_event_of_new_session_chains_to_prior_session(tmp_path) -> None:
    root = _root(tmp_path)
    with journal.locked_daily_eod_run_journal(run_root=root, target_session=SESSION) as locked:
        first_attempt = journal.new_attempt_id(
            target_session=SESSION,
            plan_fingerprint=PLAN_FP,
            sequence=1,
        )
        locked.append(
            event_type="action_started",
            attempt_id=first_attempt,
            details={"action": "calculate_phase1a"},
        )
        prior_terminal = locked.append(
            event_type="action_failed",
            attempt_id=first_attempt,
            details={"reason_code": "test"},
        )
    next_session = date(2026, 8, 28)
    with journal.locked_daily_eod_run_journal(
        run_root=root, target_session=next_session
    ) as locked:
        next_attempt = journal.new_attempt_id(
            target_session=next_session,
            plan_fingerprint="b" * 64,
            sequence=1,
        )
        next_started = locked.append(
            event_type="action_started",
            attempt_id=next_attempt,
            details={"action": "calculate_phase1a"},
        )
        locked.append(
            event_type="action_failed",
            attempt_id=next_attempt,
            details={"reason_code": "test"},
        )
    assert next_started.previous_event_fingerprint == prior_terminal.event_fingerprint

    prior_path = root / "session=2026-08-27" / "event-000002.json"
    prior_path.chmod(0o600)
    payload = json.loads(prior_path.read_bytes())
    payload["details"]["reason_code"] = "rewritten"
    logical = {key: value for key, value in payload.items() if key != "event_fingerprint"}
    payload["event_fingerprint"] = journal._fingerprint(logical)
    prior_path.write_bytes(journal._canonical_bytes(payload))
    prior_path.chmod(0o400)
    with pytest.raises(journal.DailyEodRunJournalError, match="hash chain"):
        with journal.locked_daily_eod_run_journal(
            run_root=root,
            target_session=next_session,
        ):
            pass


def test_cannot_append_a_session_before_existing_later_custody(tmp_path) -> None:
    root = _root(tmp_path)
    later_session = date(2026, 8, 28)
    with journal.locked_daily_eod_run_journal(
        run_root=root, target_session=later_session
    ):
        pass
    with pytest.raises(journal.DailyEodRunJournalError, match="later session"):
        with journal.locked_daily_eod_run_journal(
            run_root=root,
            target_session=SESSION,
        ):
            pass
