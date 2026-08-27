from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from tip_api.services.daily_eod_alert_custody import (
    AlertDeliveryContext,
    DailyEodAlertCustodyConfig,
    DailyEodAlertCustodyError,
    deliver_daily_eod_alert,
)
from tip_api.services.daily_eod_alerting import plan_daily_eod_alert
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
)
from tip_api.services.daily_eod_email_delivery import (
    DailyEodEmailConfigError,
    DailyEodEmailCredentialError,
    DailyEodEmailDeliveryCapability,
    DailyEodEmailTransportError,
    SmtpCredential,
    build_email_transport_config_candidate,
    canonical_email_transport_config_bytes,
    load_smtp_credential,
    read_email_transport_config,
    render_daily_eod_email,
    send_smtp_message,
)
from tip_api.services.daily_eod_host_runtime import VerifiedDellRuntime


TARGET = date(2026, 8, 27)
NOW = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)
REVISION = "a" * 40
DATA_ROOT = Path("/data/trading-intelligence-platform")


def intent():
    value = plan_daily_eod_alert(
        target_session=TARGET,
        result=DailyEodCoordinatorResult(
            status=CoordinatorStatus.BLOCKED,
            target_session=TARGET.isoformat(),
            next_action="operator_diagnosis",
            reason_codes=("daily_deadline_elapsed", "input_not_ready"),
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


def context() -> AlertDeliveryContext:
    alert = intent()
    return AlertDeliveryContext(
        intent=alert,
        attempt_id="d" * 64,
        channel="email",
        idempotency_key=alert.deduplication_key,
    )


def custody(tmp_path: Path) -> DailyEodAlertCustodyConfig:
    alert_root = tmp_path / "alert-root"
    alert_root.mkdir(mode=0o700)
    return DailyEodAlertCustodyConfig(
        alert_root=alert_root,
        repository_root=tmp_path / "repository",
        data_root=DATA_ROOT,
        run_root=tmp_path / "run-root",
        channel="email",
    )


def transport_config(
    tmp_path: Path,
    *,
    enabled: bool = False,
    custody_config: DailyEodAlertCustodyConfig | None = None,
):
    selected = custody_config or custody(tmp_path)
    return build_email_transport_config_candidate(
        config_id="daily-email-test-20260827",
        repository_root=selected.repository_root,
        implementation_revision=REVISION,
        data_root=selected.data_root,
        run_root=selected.run_root,
        alert_root=selected.alert_root,
        smtp_host="SMTP.Example.COM",
        smtp_port=465,
        transport_security="implicit_tls",
        sender_email="Alerts@Example.COM",
        recipient_emails=("OWNER@example.com", "owner@example.com"),
        credential_path=tmp_path / "credential-root" / "smtp.env",
        enabled=enabled,
    )


def runtime(selected: DailyEodAlertCustodyConfig) -> VerifiedDellRuntime:
    return VerifiedDellRuntime(
        host="dell5820",
        repository_root=str(selected.repository_root),
        implementation_revision=REVISION,
        readiness_policy_fingerprint="e" * 64,
        worktree_clean=True,
    )


def credential() -> SmtpCredential:
    return SmtpCredential(
        username="synthetic-user-not-for-network",
        password="synthetic-secret-not-for-network",
    )


def clock():
    values = iter((NOW, NOW + timedelta(seconds=1)))
    return lambda: next(values)


def test_candidate_is_default_disabled_normalized_and_exact(tmp_path: Path) -> None:
    selected = transport_config(tmp_path)

    assert selected.enabled is False
    assert selected.smtp_host == "smtp.example.com"
    assert selected.sender_email == "alerts@example.com"
    assert selected.recipient_emails == ("owner@example.com",)
    assert selected.scheduler_enabled is False
    assert selected.publication_authorized is False
    assert selected.deployment_authorized is False
    assert len(selected.config_content_sha256) == 64


@pytest.mark.parametrize(
    ("port", "security"),
    ((587, "implicit_tls"), (465, "starttls"), (25, "starttls")),
)
def test_candidate_rejects_unapproved_tls_port_pair(port: int, security: str) -> None:
    with pytest.raises(ValidationError, match="SMTP boundary"):
        build_email_transport_config_candidate(
            config_id="daily-email-test-20260827",
            repository_root=Path("/tmp/repository"),
            implementation_revision=REVISION,
            data_root=DATA_ROOT,
            run_root=Path("/tmp/run"),
            alert_root=Path("/tmp/alert"),
            smtp_host="smtp.example.com",
            smtp_port=port,
            transport_security=security,  # type: ignore[arg-type]
            sender_email="alerts@example.com",
            recipient_emails=("owner@example.com",),
            credential_path=Path("/tmp/credential/smtp.env"),
        )


def test_sha_pinned_config_read_does_not_touch_absent_credential(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config-root"
    config_root.mkdir(mode=0o700)
    selected = transport_config(tmp_path)
    config_path = config_root / "smtp.json"
    raw = canonical_email_transport_config_bytes(selected)
    config_path.write_bytes(raw)
    config_path.chmod(0o400)

    reread = read_email_transport_config(
        config_path=config_path,
        config_root=config_root,
        repository_root=Path(selected.repository_root),
        expected_file_sha256=hashlib.sha256(raw).hexdigest(),
    )

    assert reread == selected
    assert not Path(selected.credential_path).exists()


def test_config_read_rejects_bad_sha_and_permissions(tmp_path: Path) -> None:
    config_root = tmp_path / "config-root"
    config_root.mkdir(mode=0o700)
    selected = transport_config(tmp_path)
    config_path = config_root / "smtp.json"
    raw = canonical_email_transport_config_bytes(selected)
    config_path.write_bytes(raw)
    config_path.chmod(0o400)

    with pytest.raises(DailyEodEmailConfigError, match="SHA mismatch"):
        read_email_transport_config(
            config_path=config_path,
            config_root=config_root,
            repository_root=Path(selected.repository_root),
            expected_file_sha256="f" * 64,
        )
    config_path.chmod(0o600)
    with pytest.raises(DailyEodEmailConfigError, match="custody is unsafe"):
        read_email_transport_config(
            config_path=config_path,
            config_root=config_root,
            repository_root=Path(selected.repository_root),
            expected_file_sha256=hashlib.sha256(raw).hexdigest(),
        )


def test_credential_loader_is_owner_only_minimal_and_redacted(tmp_path: Path) -> None:
    credential_root = tmp_path / "credential-root"
    credential_root.mkdir(mode=0o700)
    path = credential_root / "smtp.env"
    path.write_text(
        "TIP_SMTP_USERNAME=synthetic-user\n"
        "TIP_SMTP_PASSWORD=synthetic-secret\n",
        encoding="utf-8",
    )
    path.chmod(0o400)

    selected = load_smtp_credential(path)

    assert selected.username == "synthetic-user"
    assert selected.password == "synthetic-secret"
    assert "synthetic-user" not in repr(selected)
    assert "synthetic-secret" not in repr(selected)


def test_credential_loader_rejects_shell_syntax_and_broad_permissions(
    tmp_path: Path,
) -> None:
    credential_root = tmp_path / "credential-root"
    credential_root.mkdir(mode=0o700)
    path = credential_root / "smtp.env"
    path.write_text(
        "TIP_SMTP_USERNAME=synthetic-user\nTIP_SMTP_PASSWORD=$(unsafe)\n",
        encoding="utf-8",
    )
    path.chmod(0o400)
    with pytest.raises(DailyEodEmailCredentialError, match="entry is invalid"):
        load_smtp_credential(path)

    path.chmod(0o600)
    path.write_text(
        "TIP_SMTP_USERNAME=synthetic-user\nTIP_SMTP_PASSWORD=synthetic-secret\n",
        encoding="utf-8",
    )
    path.chmod(0o644)
    with pytest.raises(DailyEodEmailCredentialError, match="custody is unsafe"):
        load_smtp_credential(path)


def test_render_is_stable_bilingual_and_contains_no_transport_secret() -> None:
    first = render_daily_eod_email(context())
    second = render_daily_eod_email(context())
    rendered = first.get_content()

    assert first.as_bytes() == second.as_bytes()
    assert "WH Alpha daily pipeline requires attention" in rendered
    assert "WH Alpha 每日流水线需要人工关注" in rendered
    assert "daily_deadline_elapsed, input_not_ready" in rendered
    assert context().idempotency_key in rendered
    assert "synthetic-secret-not-for-network" not in rendered
    assert "From:" not in rendered
    assert "To:" not in rendered


def test_disabled_config_cannot_install_capability_or_perform_io(
    tmp_path: Path,
) -> None:
    selected_custody = custody(tmp_path)
    selected = transport_config(tmp_path, custody_config=selected_custody)
    calls: list[str] = []
    with pytest.raises(DailyEodEmailConfigError, match="transport is disabled"):
        DailyEodEmailDeliveryCapability(
            config=selected,
            custody_config=selected_custody,
            verified_runtime=runtime(selected_custody),
            credential_loader=lambda _path: calls.append("credential"),  # type: ignore[arg-type,return-value]
            smtp_sender=lambda *_args: calls.append("sender"),
        )

    assert calls == []


def test_success_is_custodied_once_and_secret_never_enters_evidence(
    tmp_path: Path,
) -> None:
    selected_custody = custody(tmp_path)
    selected = transport_config(
        tmp_path,
        enabled=True,
        custody_config=selected_custody,
    )
    messages = []

    def fake_sender(config, smtp_credential, message):
        assert config.smtp_host == "smtp.example.com"
        assert smtp_credential.password == "synthetic-secret-not-for-network"
        messages.append(message)

    capability = DailyEodEmailDeliveryCapability(
        config=selected,
        custody_config=selected_custody,
        verified_runtime=runtime(selected_custody),
        credential_loader=lambda _path: credential(),
        smtp_sender=fake_sender,
        clock=lambda: NOW,
    )
    alert = intent()
    first = deliver_daily_eod_alert(
        config=selected_custody,
        intent=alert,
        capability=capability,
        clock=clock(),
    )
    second = deliver_daily_eod_alert(
        config=selected_custody,
        intent=alert,
        capability=lambda _context: pytest.fail("duplicate SMTP delivery attempted"),
    )

    assert len(messages) == 1
    assert messages[0]["From"] == "alerts@example.com"
    assert messages[0]["To"] == "owner@example.com"
    assert messages[0]["Date"] == "Thu, 27 Aug 2026 21:00:00 +0000"
    assert first.outcome == "delivered"
    assert first.external_request_count == 1
    assert first.reason_code == "smtp_message_accepted"
    assert "synthetic-secret-not-for-network" not in repr(first.as_dict())
    assert second.outcome == "already_delivered"


def test_credential_rejection_records_known_zero_request_failure(
    tmp_path: Path,
) -> None:
    selected_custody = custody(tmp_path)
    selected = transport_config(
        tmp_path,
        enabled=True,
        custody_config=selected_custody,
    )
    capability = DailyEodEmailDeliveryCapability(
        config=selected,
        custody_config=selected_custody,
        verified_runtime=runtime(selected_custody),
        credential_loader=lambda _path: (_ for _ in ()).throw(
            DailyEodEmailCredentialError("redacted")
        ),
        smtp_sender=lambda *_args: pytest.fail("sender reached"),
    )

    result = deliver_daily_eod_alert(
        config=selected_custody,
        intent=intent(),
        capability=capability,
        clock=clock(),
    )

    assert result.outcome == "failed"
    assert result.external_request_count == 0
    assert result.reason_code == "email_credential_rejected_before_request"


def test_transport_exception_stays_unknown_and_cannot_be_replayed(
    tmp_path: Path,
) -> None:
    selected_custody = custody(tmp_path)
    selected = transport_config(
        tmp_path,
        enabled=True,
        custody_config=selected_custody,
    )
    sends = 0

    def ambiguous_sender(*_args):
        nonlocal sends
        sends += 1
        raise DailyEodEmailTransportError("unknown outcome")

    capability = DailyEodEmailDeliveryCapability(
        config=selected,
        custody_config=selected_custody,
        verified_runtime=runtime(selected_custody),
        credential_loader=lambda _path: credential(),
        smtp_sender=ambiguous_sender,
    )
    alert = intent()
    with pytest.raises(DailyEodEmailTransportError, match="unknown outcome"):
        deliver_daily_eod_alert(
            config=selected_custody,
            intent=alert,
            capability=capability,
            clock=lambda: NOW,
        )
    with pytest.raises(DailyEodAlertCustodyError, match="outcome is unknown"):
        deliver_daily_eod_alert(
            config=selected_custody,
            intent=alert,
            capability=lambda _context: pytest.fail("ambiguous SMTP replayed"),
        )
    assert sends == 1


def test_runtime_or_custody_drift_rejects_adapter_construction(
    tmp_path: Path,
) -> None:
    selected_custody = custody(tmp_path)
    selected = transport_config(tmp_path, custody_config=selected_custody)

    with pytest.raises(DailyEodEmailConfigError, match="runtime binding"):
        DailyEodEmailDeliveryCapability(
            config=selected,
            custody_config=replace(selected_custody, channel="sms"),
            verified_runtime=runtime(selected_custody),
        )


class FakeSmtpClient:
    def __init__(self, *, refused=None):
        self.refused = {} if refused is None else refused
        self.calls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, *, context):
        assert context is not None
        self.calls.append("starttls")

    def login(self, username, password):
        assert username == "synthetic-user-not-for-network"
        assert password == "synthetic-secret-not-for-network"
        self.calls.append("login")

    def send_message(self, _message):
        self.calls.append("send_message")
        return self.refused


def test_starttls_sender_uses_verified_tls_before_one_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selected_custody = custody(tmp_path)
    selected = build_email_transport_config_candidate(
        config_id="daily-email-starttls-20260827",
        repository_root=selected_custody.repository_root,
        implementation_revision=REVISION,
        data_root=selected_custody.data_root,
        run_root=selected_custody.run_root,
        alert_root=selected_custody.alert_root,
        smtp_host="smtp.example.com",
        smtp_port=587,
        transport_security="starttls",
        sender_email="alerts@example.com",
        recipient_emails=("owner@example.com",),
        credential_path=tmp_path / "credential-root" / "smtp.env",
        enabled=True,
    )
    client = FakeSmtpClient()
    monkeypatch.setattr(
        "tip_api.services.daily_eod_email_delivery.smtplib.SMTP",
        lambda *_args, **_kwargs: client,
    )

    send_smtp_message(selected, credential(), render_daily_eod_email(context()))

    assert client.calls == ["ehlo", "starttls", "ehlo", "login", "send_message"]


def test_partial_recipient_acceptance_is_ambiguous(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selected = transport_config(tmp_path, enabled=True)
    client = FakeSmtpClient(refused={"redacted-recipient": (550, b"rejected")})
    monkeypatch.setattr(
        "tip_api.services.daily_eod_email_delivery.smtplib.SMTP_SSL",
        lambda *_args, **_kwargs: client,
    )

    with pytest.raises(DailyEodEmailTransportError, match="incomplete"):
        send_smtp_message(
            selected,
            credential(),
            render_daily_eod_email(context()),
        )
