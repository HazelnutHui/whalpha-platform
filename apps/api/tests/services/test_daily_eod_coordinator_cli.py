from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_coordinator_cli as cli
from tip_api.services.daily_eod_coordinator import CoordinatorStatus
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
REVISION = "a" * 40
POLICY = DailyEodReadinessPolicy().logical_fingerprint
RUN_ROOT = Path("/var/lib/trading-intelligence-platform/daily-eod")


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


def result(status: CoordinatorStatus = CoordinatorStatus.MANUAL_AUTHORIZATION_REQUIRED):
    payload = {
        "status": status.value,
        "next_action": "review_fetch_authorization",
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
    }
    return SimpleNamespace(status=status, as_dict=lambda: payload)


def enabled_host_config(repository_root: Path):
    auth_root = Path("/etc/trading-intelligence-platform/authorization")
    return build_host_runtime_config_candidate(
        config_id="enabled-dell-runtime-v1",
        host="dell5820",
        repository_root=repository_root,
        implementation_revision=REVISION,
        data_root=APPROVED_CANONICAL_DATA_ROOT,
        run_root=RUN_ROOT,
        authorization_root=auth_root,
        authorization_path=auth_root / "daily-eod.json",
        authorization_file_sha256="b" * 64,
        credential_path=Path("/etc/trading-intelligence-platform/massive.env"),
        readiness_policy_fingerprint=POLICY,
        capabilities_enabled=True,
    )


def test_default_invocation_does_not_read_host_config_or_install_capabilities(
    monkeypatch,
    capsys,
) -> None:
    captured = []

    def coordinate(**kwargs):
        captured.append(kwargs)
        return result()

    monkeypatch.setattr(cli, "coordinate_daily_eod_transition", coordinate)
    monkeypatch.setattr(
        cli,
        "read_host_runtime_config",
        lambda **_kwargs: pytest.fail("host config must remain unread"),
    )

    assert cli.main(arguments()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "manual_authorization_required"
    assert captured[0]["fetch_capability"] is None
    assert captured[0]["apply_capability"] is None


def test_capability_enablement_requires_external_config_and_sha() -> None:
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--enable-authorized-capabilities"])


def test_explicit_enabled_config_installs_both_capability_ports(
    monkeypatch,
    capsys,
) -> None:
    source_root = cli._source_repository_root()
    host_config = enabled_host_config(source_root)
    captured = []

    class Capabilities:
        def __init__(self, *, config):
            captured.append(config)

        def fetch(self, _context):
            return None

        def apply(self, _context):
            return None

    def coordinate(**kwargs):
        captured.append(kwargs)
        return result()

    monkeypatch.setattr(cli, "read_host_runtime_config", lambda **_kwargs: host_config)
    monkeypatch.setattr(
        cli,
        "verify_dell_runtime",
        lambda **_kwargs: VerifiedDellRuntime(
            host="dell5820",
            repository_root=str(source_root),
            implementation_revision=REVISION,
            readiness_policy_fingerprint=POLICY,
            worktree_clean=True,
        ),
    )
    monkeypatch.setattr(cli, "DailyEodAuthorizedCapabilities", Capabilities)
    monkeypatch.setattr(cli, "coordinate_daily_eod_transition", coordinate)

    invocation = arguments() + [
        "--enable-authorized-capabilities",
        "--host-config",
        "/etc/trading-intelligence-platform/runtime/host.json",
        "--host-config-sha256",
        "c" * 64,
    ]
    assert cli.main(invocation) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["external_request_count"] == 0
    coordinator_call = captured[1]
    assert coordinator_call["fetch_capability"] is not None
    assert coordinator_call["apply_capability"] is not None
    assert captured[0].implementation_revision == REVISION


def test_external_config_disabled_rejects_without_runtime_verification(
    monkeypatch,
    capsys,
) -> None:
    source_root = cli._source_repository_root()
    disabled = enabled_host_config(source_root).model_copy(
        update={"capabilities_enabled": False}
    )
    monkeypatch.setattr(cli, "read_host_runtime_config", lambda **_kwargs: disabled)
    monkeypatch.setattr(
        cli,
        "verify_dell_runtime",
        lambda **_kwargs: pytest.fail("disabled config must stop before verification"),
    )

    code = cli.main(
        arguments()
        + [
            "--enable-authorized-capabilities",
            "--host-config",
            "/etc/trading-intelligence-platform/runtime/host.json",
            "--host-config-sha256",
            "c" * 64,
        ]
    )

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["external_request_count"] is None
    assert payload["production_write_count"] is None
    assert payload["transition_outcome_formally_known"] is False


def test_apply_bindings_must_be_complete_and_capabilities_enabled() -> None:
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--approved-plan-sha256", "d" * 64])
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--approved-plan-sha256",
                "d" * 64,
                "--expected-current-state-fingerprint",
                "e" * 64,
            ]
        )


def test_recovery_required_returns_nonzero(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: result(CoordinatorStatus.RECOVERY_REQUIRED),
    )

    assert cli.main(arguments()) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "recovery_required"
