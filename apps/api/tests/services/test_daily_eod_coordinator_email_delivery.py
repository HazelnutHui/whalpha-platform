from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tip_api.services import daily_eod_coordinator_cli as cli
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
)
from tip_api.services.daily_eod_email_delivery import (
    DailyEodEmailCredentialError,
    DailyEodEmailDeliveryCapability,
    DailyEodEmailTransportError,
    SmtpCredential,
    build_email_transport_config_candidate,
)
from tip_api.services.daily_eod_host_runtime import (
    VerifiedDellRuntime,
    build_host_runtime_config_candidate,
)
from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
)


TARGET = "2026-08-27"
LATEST = "2026-08-26"
CHECKED = "2026-08-27T21:00:00+00:00"
NOW = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)
REVISION = "a" * 40
POLICY = DailyEodReadinessPolicy().logical_fingerprint
RUN_ROOT = Path("/var/lib/trading-intelligence-platform/daily-eod")
HOST_PATH = Path("/etc/trading-intelligence-platform/runtime/host.json")
EMAIL_PATH = Path("/etc/trading-intelligence-platform/email/smtp.json")


def arguments() -> list[str]:
    return [
        "--target-session",
        TARGET,
        "--latest-canonical-session",
        LATEST,
        "--checked-at",
        CHECKED,
        "--data-root",
        str(APPROVED_CANONICAL_DATA_ROOT),
        "--run-root",
        str(RUN_ROOT),
        "--package",
        "/tmp/daily-package",
        "--approval-plan",
        "/tmp/daily-plan.json",
        "--phase1a-audit",
        "/tmp/phase1a.json",
        "--prior-phase1b-audit",
        "/tmp/prior-phase1b.json",
        "--phase1b-audit",
        "/tmp/phase1b.json",
        "--prior-candidate-audit",
        "/tmp/prior-candidate.json",
        "--candidate-audit",
        "/tmp/candidate.json",
        "--entry-geometry-audit",
        "/tmp/entry.json",
    ]


def email_arguments() -> list[str]:
    return arguments() + [
        "--emit-alert-intent",
        "--deliver-alert-email",
        "--host-config",
        str(HOST_PATH),
        "--host-config-sha256",
        "b" * 64,
        "--email-config",
        str(EMAIL_PATH),
        "--email-config-sha256",
        "c" * 64,
    ]


def coordinator_result(
    status: CoordinatorStatus = CoordinatorStatus.BLOCKED,
) -> DailyEodCoordinatorResult:
    alert_required = status in {
        CoordinatorStatus.BLOCKED,
        CoordinatorStatus.RECOVERY_REQUIRED,
        CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED,
    }
    return DailyEodCoordinatorResult(
        status=status,
        target_session=TARGET,
        next_action=(
            "operator_diagnosis"
            if status is CoordinatorStatus.BLOCKED
            else "review_fetch_authorization"
            if status is CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED
            else "wait"
        ),
        reason_codes=("daily_deadline_elapsed",) if alert_required else ("wait",),
        automation_plan_fingerprint="d" * 64,
        readiness_plan_fingerprint="e" * 64,
        transition_fingerprint=None,
        external_request_count=0,
        production_write_count=0,
        alert_required=alert_required,
        logical_content_fingerprint="f" * 64,
    )


def host_config(repository_root: Path):
    authorization_root = Path("/etc/trading-intelligence-platform/authorization")
    return build_host_runtime_config_candidate(
        config_id="dell-daily-eod-runtime-v1",
        host="dell5820",
        repository_root=repository_root,
        implementation_revision=REVISION,
        data_root=APPROVED_CANONICAL_DATA_ROOT,
        run_root=RUN_ROOT,
        authorization_root=authorization_root,
        authorization_path=authorization_root / "daily.json",
        authorization_file_sha256="1" * 64,
        credential_path=Path(
            "/etc/trading-intelligence-platform/provider/massive.env"
        ),
        readiness_policy_fingerprint=POLICY,
        capabilities_enabled=False,
    )


def email_config(repository_root: Path, alert_root: Path, *, enabled: bool = True):
    return build_email_transport_config_candidate(
        config_id="daily-email-transport-v1",
        repository_root=repository_root,
        implementation_revision=REVISION,
        data_root=APPROVED_CANONICAL_DATA_ROOT,
        run_root=RUN_ROOT,
        alert_root=alert_root,
        smtp_host="smtp.example.com",
        smtp_port=465,
        transport_security="implicit_tls",
        sender_email="alerts@example.com",
        recipient_emails=("owner@example.com",),
        credential_path=Path(
            "/etc/trading-intelligence-platform/smtp-secret/smtp.env"
        ),
        enabled=enabled,
    )


def verified(repository_root: Path) -> VerifiedDellRuntime:
    return VerifiedDellRuntime(
        host="dell5820",
        repository_root=str(repository_root),
        implementation_revision=REVISION,
        readiness_policy_fingerprint=POLICY,
        worktree_clean=True,
    )


def install_email_boundary(
    tmp_path: Path,
    monkeypatch,
    *,
    credential_loader,
    smtp_sender,
    enabled: bool = True,
):
    source_root = cli._source_repository_root()
    alert_root = tmp_path / "alert-root"
    alert_root.mkdir(mode=0o700)
    selected_host = host_config(source_root)
    selected_email = email_config(source_root, alert_root, enabled=enabled)
    monkeypatch.setattr(
        cli,
        "read_host_runtime_config",
        lambda **_kwargs: selected_host,
    )
    monkeypatch.setattr(
        cli,
        "verify_dell_runtime",
        lambda **_kwargs: verified(source_root),
    )
    monkeypatch.setattr(
        cli,
        "read_email_transport_config",
        lambda **_kwargs: selected_email,
    )
    original = DailyEodEmailDeliveryCapability

    def capability_factory(**kwargs):
        return original(
            **kwargs,
            credential_loader=credential_loader,
            smtp_sender=smtp_sender,
            clock=lambda: NOW,
        )

    monkeypatch.setattr(cli, "DailyEodEmailDeliveryCapability", capability_factory)
    return alert_root


def credential() -> SmtpCredential:
    return SmtpCredential(
        username="synthetic-user-not-for-network",
        password="synthetic-secret-not-for-network",
    )


def test_explicit_email_delivery_is_custodied_and_deduplicated(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    sends = []
    install_email_boundary(
        tmp_path,
        monkeypatch,
        credential_loader=lambda _path: credential(),
        smtp_sender=lambda _config, _credential, message: sends.append(message),
    )

    def coordinate(**_kwargs):
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return coordinator_result()

    monkeypatch.setattr(cli, "coordinate_daily_eod_transition", coordinate)

    assert cli.main(email_arguments()) == 1
    first = json.loads(capsys.readouterr().out)
    assert cli.main(email_arguments()) == 1
    second = json.loads(capsys.readouterr().out)

    assert len(sends) == 1
    assert first["alert_delivery"]["outcome"] == "delivered"
    assert first["alert_delivery"]["external_request_count"] == 1
    assert first["alert_delivery"]["production_write_count"] == 0
    assert second["alert_delivery"]["outcome"] == "already_delivered"
    assert second["alert_delivery"]["external_request_count"] == 0
    assert "synthetic-secret-not-for-network" not in repr(first)


def test_normal_state_loads_no_credential_and_sends_no_email(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    calls = []
    install_email_boundary(
        tmp_path,
        monkeypatch,
        credential_loader=lambda _path: calls.append("credential"),  # type: ignore[arg-type,return-value]
        smtp_sender=lambda *_args: calls.append("sender"),
    )
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: coordinator_result(CoordinatorStatus.WAITING),
    )

    assert cli.main(email_arguments()) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["alert_intent"] is None
    assert payload["alert_delivery"] is None
    assert calls == []


def test_known_credential_failure_is_reported_and_returns_nonzero(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    install_email_boundary(
        tmp_path,
        monkeypatch,
        credential_loader=lambda _path: (_ for _ in ()).throw(
            DailyEodEmailCredentialError("redacted")
        ),
        smtp_sender=lambda *_args: pytest.fail("SMTP sender reached"),
    )
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: coordinator_result(
            CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED
        ),
    )

    assert cli.main(email_arguments()) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "manual_authorization_required"
    assert payload["alert_delivery"]["outcome"] == "failed"
    assert payload["alert_delivery"]["external_request_count"] == 0
    assert payload["alert_delivery"]["reason_code"] == (
        "email_credential_rejected_before_request"
    )


def test_ambiguous_transport_exception_returns_redacted_unknown_outcome(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    alert_root = install_email_boundary(
        tmp_path,
        monkeypatch,
        credential_loader=lambda _path: credential(),
        smtp_sender=lambda *_args: (_ for _ in ()).throw(
            DailyEodEmailTransportError("synthetic transport detail")
        ),
    )
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: coordinator_result(),
    )

    assert cli.main(email_arguments()) == 1
    rendered = capsys.readouterr().out
    payload = json.loads(rendered)

    assert payload["status"] == "rejected"
    assert payload["coordinator_status"] == "blocked"
    assert payload["transition_outcome_formally_known"] is True
    assert payload["external_request_count"] == 0
    assert payload["production_write_count"] == 0
    assert payload["alert_delivery_outcome_formally_known"] is False
    assert "synthetic transport detail" not in rendered
    event_files = tuple(alert_root.rglob("event-*.json"))
    assert len(event_files) == 1
    assert event_files[0].name == "event-000001.json"


def test_disabled_email_config_rejects_before_coordinator_or_credential(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    calls = []
    install_email_boundary(
        tmp_path,
        monkeypatch,
        credential_loader=lambda _path: calls.append("credential"),  # type: ignore[arg-type,return-value]
        smtp_sender=lambda *_args: calls.append("sender"),
        enabled=False,
    )
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: pytest.fail("disabled email reached coordinator"),
    )

    assert cli.main(email_arguments()) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "rejected"
    assert payload["error_type"] == "DailyEodEmailConfigError"
    assert calls == []


def test_email_delivery_arguments_are_explicit_and_complete() -> None:
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--deliver-alert-email"])
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--emit-alert-intent",
                "--email-config",
                str(EMAIL_PATH),
                "--email-config-sha256",
                "c" * 64,
            ]
        )
