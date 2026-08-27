from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.services.daily_eod_email_delivery import (
    build_email_transport_config_candidate,
)
from tip_api.services.daily_eod_external_preflight import (
    DailyEodExternalPreflightError,
    preflight_external_controls,
)
from tip_api.services.daily_eod_host_runtime import (
    VerifiedDellRuntime,
    build_host_runtime_config_candidate,
)
from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_eod_standing_authorization import (
    StandingOperation,
    build_standing_authorization_candidate,
)


NOW = datetime(2026, 8, 27, 22, 0, tzinfo=UTC)
REVISION = "a" * 40
POLICY = DailyEodReadinessPolicy().logical_fingerprint
REPOSITORY = Path("/opt/trading-intelligence-platform")
DATA_ROOT = Path("/data/trading-intelligence-platform")
RUN_ROOT = Path("/var/lib/trading-intelligence-platform/daily-eod")
ALERT_ROOT = Path("/var/lib/trading-intelligence-platform/daily-alert")
HOST_PATH = Path("/etc/trading-intelligence-platform/runtime/host.json")
AUTH_PATH = Path("/etc/trading-intelligence-platform/authorization/daily.json")
EMAIL_PATH = Path("/etc/trading-intelligence-platform/email/smtp.json")
MASSIVE_CREDENTIAL = Path("/etc/trading-intelligence-platform/provider/massive.env")
SMTP_CREDENTIAL = Path("/etc/trading-intelligence-platform/smtp-secret/smtp.env")
HOST_SHA = "b" * 64
AUTH_SHA = "c" * 64
EMAIL_SHA = "d" * 64


def authorization(**overrides):
    values = {
        "authorization_id": "daily-eod-authorization-2026q3",
        "approved_at": NOW - timedelta(hours=1),
        "valid_from": NOW - timedelta(hours=1),
        "expires_at": NOW + timedelta(days=30),
        "host": "dell5820",
        "data_root": DATA_ROOT,
        "run_root": RUN_ROOT,
        "implementation_revision": REVISION,
        "readiness_policy_fingerprint": POLICY,
        "allowed_operations": tuple(StandingOperation),
    }
    values.update(overrides)
    return build_standing_authorization_candidate(**values)


def host_config(**overrides):
    values = {
        "config_id": "dell-daily-eod-runtime-v1",
        "host": "dell5820",
        "repository_root": REPOSITORY,
        "implementation_revision": REVISION,
        "data_root": DATA_ROOT,
        "run_root": RUN_ROOT,
        "authorization_root": AUTH_PATH.parent,
        "authorization_path": AUTH_PATH,
        "authorization_file_sha256": AUTH_SHA,
        "credential_path": MASSIVE_CREDENTIAL,
        "readiness_policy_fingerprint": POLICY,
        "capabilities_enabled": True,
    }
    values.update(overrides)
    return build_host_runtime_config_candidate(**values)


def email_config(**overrides):
    values = {
        "config_id": "daily-email-transport-v1",
        "repository_root": REPOSITORY,
        "implementation_revision": REVISION,
        "data_root": DATA_ROOT,
        "run_root": RUN_ROOT,
        "alert_root": ALERT_ROOT,
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "transport_security": "implicit_tls",
        "sender_email": "alerts@example.com",
        "recipient_emails": ("owner@example.com",),
        "credential_path": SMTP_CREDENTIAL,
        "enabled": True,
    }
    values.update(overrides)
    return build_email_transport_config_candidate(**values)


def verified(**overrides):
    values = {
        "host": "dell5820",
        "repository_root": str(REPOSITORY),
        "implementation_revision": REVISION,
        "readiness_policy_fingerprint": POLICY,
        "worktree_clean": True,
    }
    values.update(overrides)
    return VerifiedDellRuntime(**values)


def preflight(**overrides):
    values = {
        "host_config": host_config(),
        "authorization": authorization(),
        "email_config": email_config(),
        "verified_runtime": verified(),
        "checked_at": NOW,
        "host_config_path": HOST_PATH,
        "host_config_file_sha256": HOST_SHA,
        "authorization_path": AUTH_PATH,
        "authorization_file_sha256": AUTH_SHA,
        "email_config_path": EMAIL_PATH,
        "email_config_file_sha256": EMAIL_SHA,
    }
    values.update(overrides)
    return preflight_external_controls(**values)


def test_consistent_controls_report_zero_authority_and_zero_io() -> None:
    result = preflight()
    payload = result.as_dict()

    assert result.status == "configuration_consistent"
    assert result.configuration_consistent is True
    assert result.allowed_operations == tuple(item.value for item in StandingOperation)
    assert result.credential_paths_distinct is True
    assert result.credential_file_access_count == 0
    assert result.external_request_count == 0
    assert result.filesystem_write_count == 0
    assert result.production_write_count == 0
    assert result.controlled_rehearsal_authorized is False
    assert result.publication_authorized is False
    assert result.deployment_authorized is False
    assert result.scheduler_enabled is False
    assert len(result.logical_content_fingerprint) == 64
    assert "credential_path" not in payload
    assert str(MASSIVE_CREDENTIAL) not in repr(payload)
    assert str(SMTP_CREDENTIAL) not in repr(payload)


@pytest.mark.parametrize(
    "override",
    (
        {"host_config": host_config(capabilities_enabled=False)},
        {"email_config": email_config(enabled=False)},
        {
            "authorization": authorization(
                allowed_operations=(StandingOperation.FETCH_IDENTITY,)
            )
        },
    ),
)
def test_incomplete_or_disabled_scope_is_not_preflight_ready(override) -> None:
    with pytest.raises(DailyEodExternalPreflightError, match="complete daily scope"):
        preflight(**override)


@pytest.mark.parametrize(
    "override",
    (
        {"email_config": email_config(implementation_revision="e" * 40)},
        {"email_config": email_config(run_root=Path("/var/lib/other-run"))},
        {"verified_runtime": verified(readiness_policy_fingerprint="f" * 64)},
    ),
)
def test_runtime_revision_root_or_policy_drift_is_rejected(override) -> None:
    with pytest.raises(DailyEodExternalPreflightError, match="runtime binding"):
        preflight(**override)


def test_host_authorization_path_and_sha_must_match_independent_inputs() -> None:
    with pytest.raises(DailyEodExternalPreflightError, match="artifact binding"):
        preflight(authorization_file_sha256="9" * 64)
    with pytest.raises(DailyEodExternalPreflightError, match="artifact binding"):
        preflight(authorization_path=Path("/etc/other/daily.json"))


def test_each_control_artifact_requires_a_distinct_parent_directory() -> None:
    with pytest.raises(DailyEodExternalPreflightError, match="custody identity"):
        preflight(email_config_path=HOST_PATH.parent / "smtp.json")
    with pytest.raises(DailyEodExternalPreflightError, match="custody identity"):
        preflight(email_config_path=HOST_PATH.parent / "nested" / "smtp.json")


def test_provider_and_email_credentials_require_separate_custody_roots() -> None:
    selected = email_config(
        credential_path=MASSIVE_CREDENTIAL.parent / "smtp.env"
    )

    with pytest.raises(DailyEodExternalPreflightError, match="independently"):
        preflight(email_config=selected)
    nested = email_config(
        credential_path=HOST_PATH.parent / "secrets" / "smtp.env"
    )
    with pytest.raises(DailyEodExternalPreflightError, match="independently"):
        preflight(email_config=nested)


def test_expired_authorization_is_not_configuration_ready() -> None:
    expired = authorization(
        approved_at=NOW - timedelta(days=3),
        valid_from=NOW - timedelta(days=3),
        expires_at=NOW - timedelta(days=1),
    )

    with pytest.raises(DailyEodExternalPreflightError, match="not active"):
        preflight(authorization=expired)


def test_dirty_runtime_is_rejected_before_claiming_consistency() -> None:
    with pytest.raises(DailyEodExternalPreflightError, match="custody identity"):
        preflight(verified_runtime=verified(worktree_clean=False))
