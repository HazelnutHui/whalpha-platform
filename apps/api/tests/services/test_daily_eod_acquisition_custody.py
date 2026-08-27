from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tip_api.providers.massive.same_day_catchup import FetchPackageEvidenceV1
from tip_api.services import daily_eod_acquisition_custody as custody
from tip_api.services.daily_eod_automation import NextAction
from tip_api.services.daily_eod_readiness import (
    AcquisitionAttempt,
    AttemptOutcome,
    plan_daily_eod_readiness,
)
from tip_api.services.daily_eod_run_journal import locked_daily_eod_run_journal


TARGET = date(2026, 8, 27)
LATEST = date(2026, 8, 26)
CHECKED = datetime(2026, 8, 27, 20, 30, tzinfo=UTC)
ACTION = NextAction.PREPARE_IDENTITY_CATCHUP


def _config(tmp_path: Path, *, name: str = "identity-fetch") -> custody.DailyEodAcquisitionConfig:
    root = tmp_path / "run-root"
    if not root.exists():
        root.mkdir(mode=0o700)
        root.chmod(0o700)
    return custody.DailyEodAcquisitionConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=ACTION,
        package_path=Path(f"/tmp/{tmp_path.parent.name}-{tmp_path.name}-{name}"),
        run_root=root,
    )


def _readiness(attempts=(), *, checked=CHECKED):
    return plan_daily_eod_readiness(
        checked_at=checked,
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=ACTION,
        attempts=attempts,
    )


def _reserve(config, *, checked=CHECKED, attempts=(), **kwargs):
    plan = _readiness(attempts, checked=checked)
    return custody.reserve_acquisition_attempt(
        config=config,
        checked_at=checked,
        expected_readiness_fingerprint=plan.logical_content_fingerprint,
        clock=lambda: checked,
        **kwargs,
    )


def _package_evidence(config) -> FetchPackageEvidenceV1:
    return FetchPackageEvidenceV1(
        operation="identity",
        session_date=TARGET,
        package_path=str(config.package_path),
        package_type="identity_reference",
        request_count=3,
        fetched_at=datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
        package_manifest_sha256="a" * 64,
        package_content_sha256="b" * 64,
    )


def test_reserves_without_executing_provider_request(tmp_path) -> None:
    config = _config(tmp_path)
    result = _reserve(
        config,
        authorization_file_sha256="c" * 64,
        authorization_content_sha256="d" * 64,
    )
    assert result.outcome == "reserved"
    assert result.as_dict()["provider_request_executed_by_custody"] is False
    assert result.as_dict()["credential_access_count"] == 0
    with locked_daily_eod_run_journal(
        run_root=config.run_root, target_session=TARGET
    ) as journal:
        events = journal.read_events()
    assert [item.event_type for item in events] == ["acquisition_started"]
    assert events[0].details["attempt_number"] == 1
    assert events[0].details["authorization_file_sha256"] == "c" * 64
    assert events[0].details["authorization_content_sha256"] == "d" * 64


def test_stale_readiness_or_unresolved_attempt_rejects_duplicate(tmp_path) -> None:
    config = _config(tmp_path)
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="stale"):
        custody.reserve_acquisition_attempt(
            config=config,
            checked_at=CHECKED,
            expected_readiness_fingerprint="f" * 64,
            clock=lambda: CHECKED,
        )
    _reserve(config)
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="unresolved"):
        _reserve(config)


def test_nonready_outcome_becomes_bounded_readiness_history(tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    finished = custody.record_acquisition_outcome(
        config=config,
        outcome=AttemptOutcome.NOT_READY,
        authorization_decision_fingerprint="e" * 64,
        clock=lambda: datetime(2026, 8, 27, 20, 32, tzinfo=UTC),
    )
    assert finished.outcome == "not_ready"
    assert finished.readiness_plan is not None
    assert finished.readiness_plan.next_check_at == "2026-08-27T20:45:00+00:00"
    assert finished.event.details["authorization_decision_fingerprint"] == "e" * 64
    with locked_daily_eod_run_journal(
        run_root=config.run_root, target_session=TARGET
    ) as journal:
        attempts = custody.acquisition_attempts_from_events(
            journal.read_events(),
            target_session=TARGET,
            acquisition_action=ACTION,
        )
    assert len(attempts) == 1
    assert attempts[0].sequence == 1
    assert attempts[0].observed_at == CHECKED
    assert attempts[0].outcome is AttemptOutcome.NOT_READY
    assert attempts[0].retry_after_seconds is None
    assert attempts[0].terminal_event_fingerprint == finished.event.event_fingerprint
    retry_checked = datetime(2026, 8, 27, 20, 45, tzinfo=UTC)
    waiting = _readiness(
        attempts, checked=datetime(2026, 8, 27, 20, 44, tzinfo=UTC)
    )
    assert waiting.next_check_at == "2026-08-27T20:45:00+00:00"
    second = _config(tmp_path, name="identity-fetch-2")
    _reserve(second, checked=retry_checked, attempts=attempts)


def test_rate_limit_requires_bounded_retry_after(tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="retry-after"):
        custody.record_acquisition_outcome(
            config=config,
            outcome=AttemptOutcome.NOT_READY,
            retry_after_seconds=10,
        )
    result = custody.record_acquisition_outcome(
        config=config,
        outcome=AttemptOutcome.RATE_LIMITED,
        retry_after_seconds=1800,
        clock=lambda: datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
    )
    assert result.event.details["retry_after_seconds"] == 1800


def test_nonpackage_http_failure_retains_only_safe_provider_evidence(tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)

    result = custody.record_acquisition_outcome(
        config=config,
        outcome=AttemptOutcome.PERMANENT_FAILURE,
        request_count=1,
        provider_http_status_code=403,
        clock=lambda: datetime(2026, 8, 27, 20, 31, tzinfo=UTC),
    )

    assert result.event.details["request_count"] == 1
    assert result.event.details["provider_http_status_code"] == 403
    assert "response" not in result.event.details


@pytest.mark.parametrize(
    ("outcome", "request_count", "status_code"),
    (
        (AttemptOutcome.PERMANENT_FAILURE, 0, 403),
        (AttemptOutcome.PERMANENT_FAILURE, 21, 403),
        (AttemptOutcome.PERMANENT_FAILURE, 1, 404),
        (AttemptOutcome.NOT_READY, 1, 403),
        (AttemptOutcome.RATE_LIMITED, 1, 403),
    ),
)
def test_provider_http_evidence_must_match_scope_and_outcome(
    tmp_path,
    outcome,
    request_count,
    status_code,
) -> None:
    config = _config(tmp_path)
    _reserve(config)

    with pytest.raises(
        custody.DailyEodAcquisitionCustodyError,
        match="provider|HTTP",
    ):
        custody.record_acquisition_outcome(
            config=config,
            outcome=outcome,
            request_count=request_count,
            provider_http_status_code=status_code,
        )


def test_package_ready_requires_formal_exact_package_evidence(monkeypatch, tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    config.package_path.mkdir(mode=0o700)
    monkeypatch.setattr(
        custody,
        "read_fetch_package_evidence",
        lambda **kwargs: _package_evidence(config),
    )
    result = custody.record_acquisition_outcome(
        config=config,
        outcome=AttemptOutcome.FETCH_PACKAGE_READY,
        clock=lambda: datetime(2026, 8, 27, 20, 32, tzinfo=UTC),
    )
    assert result.package_evidence == _package_evidence(config)
    assert result.event.event_type == "acquisition_package_ready"
    assert result.as_dict()["apply_authorized"] is False
    assert result.readiness_plan is not None
    assert result.readiness_plan.next_action.value == "review_apply_authorization"
    config.package_path.rmdir()


def test_mismatched_package_evidence_cannot_close_reservation(monkeypatch, tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    config.package_path.mkdir(mode=0o700)
    wrong = _package_evidence(config).model_copy(
        update={"package_path": "/tmp/unrelated-package"}
    )
    monkeypatch.setattr(
        custody,
        "read_fetch_package_evidence",
        lambda **kwargs: wrong,
    )
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="reserved"):
        custody.record_acquisition_outcome(
            config=config,
            outcome=AttemptOutcome.FETCH_PACKAGE_READY,
            clock=lambda: datetime(2026, 8, 27, 20, 32, tzinfo=UTC),
        )
    with locked_daily_eod_run_journal(
        run_root=config.run_root, target_session=TARGET
    ) as journal:
        assert journal.read_events()[-1].event_type == "acquisition_started"
    config.package_path.rmdir()


def test_failure_outcome_rejects_package_or_staging_residue(tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    config.package_path.mkdir(mode=0o700)
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="custody"):
        custody.record_acquisition_outcome(
            config=config,
            outcome=AttemptOutcome.TRANSIENT_FAILURE,
        )
    config.package_path.rmdir()


def test_recovery_classifies_absent_package_without_reexecution(tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    result = custody.recover_acquisition_attempt(
        config=config,
        clock=lambda: datetime(2026, 8, 27, 20, 35, tzinfo=UTC),
    )
    assert result.outcome == "recovered_not_completed"
    assert result.as_dict()["provider_request_executed_by_custody"] is False
    with locked_daily_eod_run_journal(
        run_root=config.run_root, target_session=TARGET
    ) as journal:
        attempts = custody.acquisition_attempts_from_events(
            journal.read_events(),
            target_session=TARGET,
            acquisition_action=ACTION,
        )
    assert attempts[0].outcome is AttemptOutcome.TRANSIENT_FAILURE


def test_recovery_formally_recognizes_completed_package(monkeypatch, tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    config.package_path.mkdir(mode=0o700)
    monkeypatch.setattr(
        custody,
        "read_fetch_package_evidence",
        lambda **kwargs: _package_evidence(config),
    )
    result = custody.recover_acquisition_attempt(
        config=config,
        clock=lambda: datetime(2026, 8, 27, 20, 35, tzinfo=UTC),
    )
    assert result.outcome == "recovered_package_ready"
    assert result.event.event_type == "acquisition_recovered_package_ready"
    config.package_path.rmdir()


def test_recovery_blocks_staging_or_invalid_completed_package(monkeypatch, tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    staging = custody._staging_path(config.package_path)
    staging.mkdir(mode=0o700)
    result = custody.recover_acquisition_attempt(
        config=config,
        clock=lambda: datetime(2026, 8, 27, 20, 35, tzinfo=UTC),
    )
    assert result.outcome == "recovery_blocked"
    assert result.event.event_type == "acquisition_recovery_blocked"
    staging.rmdir()


def test_recovery_records_invalid_completed_package_as_blocked(monkeypatch, tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    config.package_path.mkdir(mode=0o700)
    monkeypatch.setattr(
        custody,
        "read_fetch_package_evidence",
        lambda **kwargs: (_ for _ in ()).throw(
            custody.SameDayCatchupError("invalid fixture package")
        ),
    )
    result = custody.recover_acquisition_attempt(
        config=config,
        clock=lambda: datetime(2026, 8, 27, 20, 35, tzinfo=UTC),
    )
    assert result.outcome == "recovery_blocked"
    assert result.reason_code == "package_present_but_not_formally_valid"
    config.package_path.rmdir()


def test_outcome_and_recovery_require_exact_reserved_inputs(tmp_path) -> None:
    config = _config(tmp_path)
    _reserve(config)
    changed = custody.DailyEodAcquisitionConfig(
        target_session=config.target_session,
        latest_canonical_session=config.latest_canonical_session,
        acquisition_action=config.acquisition_action,
        package_path=Path(f"/tmp/{tmp_path.name}-changed"),
        run_root=config.run_root,
    )
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="differ"):
        custody.recover_acquisition_attempt(config=changed)


def test_reservation_rejects_old_plan_unsafe_package_and_offline_action(tmp_path) -> None:
    config = _config(tmp_path)
    plan = _readiness()
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="age"):
        custody.reserve_acquisition_attempt(
            config=config,
            checked_at=CHECKED,
            expected_readiness_fingerprint=plan.logical_content_fingerprint,
            clock=lambda: datetime(2026, 8, 27, 20, 36, tzinfo=UTC),
        )
    unsafe = custody.DailyEodAcquisitionConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=ACTION,
        package_path=tmp_path / "not-tmp-direct",
        run_root=config.run_root,
    )
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="/tmp"):
        _reserve(unsafe)
    offline = custody.DailyEodAcquisitionConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=NextAction.CALCULATE_PHASE1A,
        package_path=config.package_path,
        run_root=config.run_root,
    )
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="only acquisition"):
        _reserve(offline)
    data_root_custody = custody.DailyEodAcquisitionConfig(
        target_session=TARGET,
        latest_canonical_session=LATEST,
        acquisition_action=ACTION,
        package_path=config.package_path,
        run_root=Path("/data/unsafe-daily-run-root"),
    )
    with pytest.raises(custody.DailyEodAcquisitionCustodyError, match="outside"):
        _reserve(data_root_custody)
