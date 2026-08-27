from __future__ import annotations

import hashlib
import json
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.services import daily_eod_external_preflight_cli as cli
from tip_api.services.daily_eod_email_delivery import (
    build_email_transport_config_candidate,
    canonical_email_transport_config_bytes,
)
from tip_api.services.daily_eod_host_runtime import (
    VerifiedDellRuntime,
    build_host_runtime_config_candidate,
    canonical_host_runtime_config_bytes,
)
from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_eod_standing_authorization import (
    StandingOperation,
    build_standing_authorization_candidate,
    canonical_authorization_bytes,
)


NOW = datetime(2026, 8, 27, 22, 0, tzinfo=UTC)
REVISION = "a" * 40
POLICY = DailyEodReadinessPolicy().logical_fingerprint
DATA_ROOT = Path("/data/trading-intelligence-platform")


def install_config(path: Path, raw: bytes) -> str:
    path.parent.mkdir(mode=0o700)
    path.write_bytes(raw)
    path.chmod(0o400)
    return hashlib.sha256(raw).hexdigest()


def installed_controls(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    run_root = tmp_path / "daily-run"
    alert_root = tmp_path / "daily-alert"
    authorization_path = tmp_path / "authorization" / "daily.json"
    host_path = tmp_path / "runtime" / "host.json"
    email_path = tmp_path / "email" / "smtp.json"
    massive_credential = tmp_path / "massive-secret" / "massive.env"
    smtp_credential = tmp_path / "smtp-secret" / "smtp.env"
    authorization = build_standing_authorization_candidate(
        authorization_id="daily-eod-authorization-2026q3",
        approved_at=NOW - timedelta(hours=1),
        valid_from=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(days=30),
        host="dell5820",
        data_root=DATA_ROOT,
        run_root=run_root,
        implementation_revision=REVISION,
        readiness_policy_fingerprint=POLICY,
        allowed_operations=tuple(StandingOperation),
    )
    authorization_sha = install_config(
        authorization_path,
        canonical_authorization_bytes(authorization),
    )
    host_config = build_host_runtime_config_candidate(
        config_id="dell-daily-eod-runtime-v1",
        host="dell5820",
        repository_root=repository,
        implementation_revision=REVISION,
        data_root=DATA_ROOT,
        run_root=run_root,
        authorization_root=authorization_path.parent,
        authorization_path=authorization_path,
        authorization_file_sha256=authorization_sha,
        credential_path=massive_credential,
        readiness_policy_fingerprint=POLICY,
        capabilities_enabled=True,
    )
    host_sha = install_config(
        host_path,
        canonical_host_runtime_config_bytes(host_config),
    )
    email_config = build_email_transport_config_candidate(
        config_id="daily-email-transport-v1",
        repository_root=repository,
        implementation_revision=REVISION,
        data_root=DATA_ROOT,
        run_root=run_root,
        alert_root=alert_root,
        smtp_host="smtp.example.com",
        smtp_port=465,
        transport_security="implicit_tls",
        sender_email="alerts@example.com",
        recipient_emails=("owner@example.com",),
        credential_path=smtp_credential,
        enabled=True,
    )
    email_sha = install_config(
        email_path,
        canonical_email_transport_config_bytes(email_config),
    )
    arguments = [
        "--checked-at",
        NOW.isoformat(),
        "--host-config",
        str(host_path),
        "--host-config-sha256",
        host_sha,
        "--authorization",
        str(authorization_path),
        "--authorization-sha256",
        authorization_sha,
        "--email-config",
        str(email_path),
        "--email-config-sha256",
        email_sha,
    ]
    return repository, arguments, massive_credential, smtp_credential


def verified(repository: Path) -> VerifiedDellRuntime:
    return VerifiedDellRuntime(
        host="dell5820",
        repository_root=str(repository),
        implementation_revision=REVISION,
        readiness_policy_fingerprint=POLICY,
        worktree_clean=True,
    )


def test_cli_reads_only_control_files_and_reports_no_activation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repository, arguments, massive_credential, smtp_credential = installed_controls(
        tmp_path
    )
    before = tuple(sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")))
    monkeypatch.setattr(cli, "_source_repository_root", lambda: repository)
    monkeypatch.setattr(
        cli,
        "verify_dell_runtime",
        lambda **_kwargs: verified(repository),
    )

    assert cli.main(arguments) == 0
    payload = json.loads(capsys.readouterr().out)
    after = tuple(sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")))

    assert payload["status"] == "configuration_consistent"
    assert payload["credential_file_access_count"] == 0
    assert payload["external_request_count"] == 0
    assert payload["filesystem_write_count"] == 0
    assert payload["production_write_count"] == 0
    assert payload["controlled_rehearsal_authorized"] is False
    assert payload["scheduler_enabled"] is False
    assert not massive_credential.exists()
    assert not smtp_credential.exists()
    assert after == before


def test_cli_data_only_mode_never_reads_email_config(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repository, arguments, massive_credential, smtp_credential = installed_controls(
        tmp_path
    )
    email_index = arguments.index("--email-config")
    data_only_arguments = arguments[:email_index] + ["--without-email"]
    monkeypatch.setattr(cli, "_source_repository_root", lambda: repository)
    monkeypatch.setattr(
        cli,
        "verify_dell_runtime",
        lambda **_kwargs: verified(repository),
    )
    monkeypatch.setattr(
        cli,
        "read_email_transport_config",
        lambda **_kwargs: pytest.fail("data-only mode read email config"),
    )

    assert cli.main(data_only_arguments) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["contract_version"] == "daily-eod-external-control-preflight/1.1"
    assert payload["status"] == "configuration_consistent"
    assert payload["preflight_mode"] == "daily_data_only"
    assert payload["email_config_id"] is None
    assert payload["email_config_file_sha256"] is None
    assert payload["alert_root"] is None
    assert payload["email_transport_enabled"] is False
    assert payload["credential_file_access_count"] == 0
    assert not massive_credential.exists()
    assert not smtp_credential.exists()


def test_cli_socket_guard_rejects_network_before_any_result(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repository, arguments, _, _ = installed_controls(tmp_path)
    monkeypatch.setattr(cli, "_source_repository_root", lambda: repository)

    def network_attempt(**_kwargs):
        socket.create_connection(("example.invalid", 443))
        pytest.fail("network guard did not reject the connection")

    monkeypatch.setattr(cli, "read_host_runtime_config", network_attempt)

    assert cli.main(arguments) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["reason_code"] == "external_control_preflight_rejected"
    assert payload["external_request_count"] == 0
    assert payload["controlled_rehearsal_authorized"] is False


def test_cli_rejection_does_not_emit_exception_or_secret_text(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repository, arguments, _, _ = installed_controls(tmp_path)
    monkeypatch.setattr(cli, "_source_repository_root", lambda: repository)
    monkeypatch.setattr(
        cli,
        "read_host_runtime_config",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("synthetic-secret-must-not-be-emitted")
        ),
    )

    assert cli.main(arguments) == 1
    rendered = capsys.readouterr().out
    payload = json.loads(rendered)

    assert payload["status"] == "rejected"
    assert payload["credential_file_access_count"] == 0
    assert "synthetic-secret-must-not-be-emitted" not in rendered


def test_cli_requires_absolute_paths_and_exact_sha() -> None:
    with pytest.raises(SystemExit):
        cli.main(
            [
                "--checked-at",
                NOW.isoformat(),
                "--host-config",
                "relative.json",
                "--host-config-sha256",
                "b" * 64,
                "--authorization",
                "/tmp/authorization.json",
                "--authorization-sha256",
                "c" * 64,
                "--email-config",
                "/tmp/email.json",
                "--email-config-sha256",
                "d" * 64,
            ]
        )


def test_cli_requires_explicit_email_inclusion_or_omission() -> None:
    common = [
        "--checked-at",
        NOW.isoformat(),
        "--host-config",
        "/tmp/host.json",
        "--host-config-sha256",
        "b" * 64,
        "--authorization",
        "/tmp/authorization.json",
        "--authorization-sha256",
        "c" * 64,
    ]
    with pytest.raises(SystemExit):
        cli.main(common)
    with pytest.raises(SystemExit):
        cli.main(
            common
            + [
                "--without-email",
                "--email-config",
                "/tmp/email.json",
                "--email-config-sha256",
                "d" * 64,
            ]
        )
