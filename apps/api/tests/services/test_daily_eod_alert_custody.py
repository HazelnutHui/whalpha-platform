from __future__ import annotations

import threading
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.services.daily_eod_alert_custody import (
    AlertDeliveryEvidence,
    DailyEodAlertCustodyConfig,
    DailyEodAlertCustodyError,
    deliver_daily_eod_alert,
)
from tip_api.services.daily_eod_alerting import plan_daily_eod_alert
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
)


TARGET = date(2026, 8, 27)
NOW = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)


def intent():
    value = plan_daily_eod_alert(
        target_session=TARGET,
        result=DailyEodCoordinatorResult(
            status=CoordinatorStatus.BLOCKED,
            target_session=TARGET.isoformat(),
            next_action="operator_diagnosis",
            reason_codes=("daily_deadline_elapsed",),
            automation_plan_fingerprint="a" * 64,
            readiness_plan_fingerprint="b" * 64,
            transition_fingerprint=None,
            external_request_count=0,
            production_write_count=0,
            alert_required=True,
            logical_content_fingerprint="c" * 64,
        ),
    )
    assert value is not None
    return value


def config(tmp_path: Path, *, channel: str = "email") -> DailyEodAlertCustodyConfig:
    alert_root = tmp_path / "alert-root"
    alert_root.mkdir(mode=0o700)
    return DailyEodAlertCustodyConfig(
        alert_root=alert_root,
        repository_root=tmp_path / "repository",
        data_root=Path("/data/trading-intelligence-platform"),
        run_root=tmp_path / "daily-run",
        channel=channel,
    )


def delivered(context) -> AlertDeliveryEvidence:
    return AlertDeliveryEvidence(
        channel=context.channel,
        deduplication_key=context.idempotency_key,
        outcome="delivered",
        external_request_count=1,
        delivery_reference_fingerprint="d" * 64,
        reason_code="email_provider_accepted_message",
    )


def clock():
    values = iter((NOW, NOW + timedelta(seconds=1)))
    return lambda: next(values)


def test_delivers_once_and_rereads_as_already_delivered(tmp_path: Path) -> None:
    selected = config(tmp_path)
    alert = intent()
    calls = []

    def capability(context):
        calls.append(context)
        return delivered(context)

    first = deliver_daily_eod_alert(
        config=selected,
        intent=alert,
        capability=capability,
        clock=clock(),
    )
    second = deliver_daily_eod_alert(
        config=selected,
        intent=alert,
        capability=lambda _context: pytest.fail("duplicate delivery attempted"),
    )

    assert len(calls) == 1
    assert calls[0].idempotency_key == alert.deduplication_key
    assert first.outcome == "delivered"
    assert first.notification_delivered is True
    assert first.external_request_count == 1
    assert first.custody_event_write_count == 2
    assert first.production_write_count == 0
    assert second.outcome == "already_delivered"
    assert second.delivery_attempted_by_invocation is False
    assert second.external_request_count == 0
    assert second.custody_event_write_count == 0


def test_known_failure_is_recorded_and_never_retried_automatically(
    tmp_path: Path,
) -> None:
    selected = config(tmp_path)
    alert = intent()

    def failed(context):
        return AlertDeliveryEvidence(
            channel=context.channel,
            deduplication_key=context.idempotency_key,
            outcome="failed",
            external_request_count=0,
            delivery_reference_fingerprint=None,
            reason_code="configuration_rejected_before_request",
        )

    result = deliver_daily_eod_alert(
        config=selected,
        intent=alert,
        capability=failed,
        clock=clock(),
    )

    assert result.outcome == "failed"
    assert result.notification_delivered is False
    with pytest.raises(DailyEodAlertCustodyError, match="prior alert delivery failed"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=lambda _context: pytest.fail("retry attempted"),
        )


def test_capability_crash_leaves_unknown_outcome_and_prohibits_resend(
    tmp_path: Path,
) -> None:
    selected = config(tmp_path)
    alert = intent()

    with pytest.raises(RuntimeError, match="transport crashed"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=lambda _context: (_ for _ in ()).throw(
                RuntimeError("transport crashed")
            ),
            clock=lambda: NOW,
        )

    directory = selected.alert_root / f"alert={alert.deduplication_key}"
    assert tuple(item.name for item in directory.iterdir()) == (
        "event-000001.json",
    )
    with pytest.raises(DailyEodAlertCustodyError, match="outcome is unknown"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=lambda _context: pytest.fail("ambiguous resend attempted"),
        )


def test_invalid_evidence_fails_closed_as_unknown(tmp_path: Path) -> None:
    selected = config(tmp_path)
    alert = intent()

    with pytest.raises(DailyEodAlertCustodyError, match="evidence is invalid"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=lambda context: replace(
                delivered(context),
                deduplication_key="e" * 64,
            ),
            clock=lambda: NOW,
        )
    with pytest.raises(DailyEodAlertCustodyError, match="outcome is unknown"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=lambda _context: pytest.fail("invalid evidence retried"),
        )


def test_channel_drift_and_unsafe_root_are_rejected(tmp_path: Path) -> None:
    selected = config(tmp_path)
    alert = intent()
    deliver_daily_eod_alert(
        config=selected,
        intent=alert,
        capability=delivered,
        clock=clock(),
    )
    changed_channel = replace(selected, channel="sms")
    with pytest.raises(DailyEodAlertCustodyError, match="channel changed"):
        deliver_daily_eod_alert(
            config=changed_channel,
            intent=alert,
            capability=lambda _context: pytest.fail("channel drift delivered"),
        )

    unsafe = tmp_path / "unsafe-root"
    unsafe.mkdir(mode=0o755)
    with pytest.raises(DailyEodAlertCustodyError, match="custody is unsafe"):
        deliver_daily_eod_alert(
            config=replace(selected, alert_root=unsafe),
            intent=alert,
            capability=delivered,
        )


def test_tampered_event_permissions_and_absent_capability_are_rejected(
    tmp_path: Path,
) -> None:
    selected = config(tmp_path)
    alert = intent()
    with pytest.raises(DailyEodAlertCustodyError, match="capability is absent"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=None,  # type: ignore[arg-type]
        )

    deliver_daily_eod_alert(
        config=selected,
        intent=alert,
        capability=delivered,
        clock=clock(),
    )
    event_path = (
        selected.alert_root
        / f"alert={alert.deduplication_key}"
        / "event-000002.json"
    )
    event_path.chmod(0o600)
    with pytest.raises(DailyEodAlertCustodyError, match="custody is unsafe"):
        deliver_daily_eod_alert(
            config=selected,
            intent=alert,
            capability=lambda _context: pytest.fail("tampered alert redelivered"),
        )


def test_unexpected_root_entry_rejects_before_creating_lock(tmp_path: Path) -> None:
    selected = config(tmp_path)
    (selected.alert_root / "unexpected.txt").write_text("unsafe", encoding="utf-8")

    with pytest.raises(DailyEodAlertCustodyError, match="unsafe entry"):
        deliver_daily_eod_alert(
            config=selected,
            intent=intent(),
            capability=delivered,
        )

    assert not (selected.alert_root / ".daily-eod-alert.lock").exists()


def test_concurrent_delivery_is_rejected_by_global_lock(tmp_path: Path) -> None:
    selected = config(tmp_path)
    alert = intent()
    entered = threading.Event()
    release = threading.Event()
    failures: list[BaseException] = []

    def slow_capability(context):
        entered.set()
        assert release.wait(timeout=5)
        return delivered(context)

    def first_delivery() -> None:
        try:
            deliver_daily_eod_alert(
                config=selected,
                intent=alert,
                capability=slow_capability,
                clock=clock(),
            )
        except BaseException as exc:  # pragma: no cover - assertion handoff
            failures.append(exc)

    worker = threading.Thread(target=first_delivery)
    worker.start()
    assert entered.wait(timeout=5)
    try:
        with pytest.raises(DailyEodAlertCustodyError, match="lock is unavailable"):
            deliver_daily_eod_alert(
                config=selected,
                intent=alert,
                capability=lambda _context: pytest.fail("concurrent delivery ran"),
            )
    finally:
        release.set()
        worker.join(timeout=5)

    assert not worker.is_alive()
    assert failures == []
