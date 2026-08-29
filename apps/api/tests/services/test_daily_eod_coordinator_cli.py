from __future__ import annotations

import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_coordinator_cli as cli
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorResult,
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
        "--phase2-audit",
        "/tmp/phase2.json",
        "--preview-bundle",
        "/tmp/preview.json",
        "--strategy-channel-audit",
        "/tmp/strategy.json",
        "--market-intelligence-output-root",
        "/tmp/mi-output",
        "--market-intelligence-approval-plan",
        "/tmp/mi-plan.json",
        "--snapshot-output-root",
        "/tmp/snapshot-output",
        "--snapshot-approval-plan",
        "/tmp/snapshot-plan.json",
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
    monkeypatch.setattr(
        cli,
        "read_email_transport_config",
        lambda **_kwargs: pytest.fail("email config must remain unread"),
    )

    assert cli.main(arguments()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "manual_authorization_required"
    assert captured[0]["fetch_capability"] is None
    assert captured[0]["apply_capability"] is None
    assert captured[0]["recover_unresolved"] is False
    assert captured[0]["recovery_capability"] is None
    assert captured[0]["apply_market_intelligence"] is False
    assert captured[0]["publication_capability"] is None
    assert captured[0]["apply_dashboard_snapshot"] is False
    assert captured[0]["snapshot_publication_capability"] is None


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


def test_explicit_market_intelligence_apply_installs_only_one_shot_port(
    monkeypatch,
    capsys,
) -> None:
    source_root = cli._source_repository_root()
    host_config = enabled_host_config(source_root)
    captured = []

    class Capability:
        def __init__(self, *, config):
            captured.append(config)

        def apply(self, _context):
            return None

    def coordinate(**kwargs):
        captured.append(kwargs)
        assert kwargs["apply_market_intelligence"] is True
        assert kwargs["publication_capability"] is not None
        assert kwargs["fetch_capability"] is None
        assert kwargs["apply_capability"] is None
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return result(CoordinatorStatus.TRANSITION_EXECUTED)

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
    monkeypatch.setattr(
        cli,
        "DailyEodMarketIntelligenceApplyCapability",
        Capability,
    )
    monkeypatch.setattr(cli, "coordinate_daily_eod_transition", coordinate)

    invocation = arguments() + [
        "--apply-market-intelligence",
        "--host-config",
        "/etc/trading-intelligence-platform/runtime/host.json",
        "--host-config-sha256",
        "c" * 64,
        "--market-intelligence-approved-plan-sha256",
        "d" * 64,
        "--market-intelligence-expected-current-state-fingerprint",
        "e" * 64,
    ]
    assert cli.main(invocation) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "transition_executed"
    assert captured[0].approved_plan_sha256 == "d" * 64
    assert captured[0].expected_current_state_fingerprint == "e" * 64


def test_market_intelligence_apply_bindings_are_exact_and_exclusive() -> None:
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--apply-market-intelligence"])
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--market-intelligence-approved-plan-sha256",
                "d" * 64,
            ]
        )
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--apply-market-intelligence",
                "--enable-authorized-capabilities",
            ]
        )
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--apply-market-intelligence",
                "--publication-created-at",
                CHECKED,
                "--publication-expected-current-state-fingerprint",
                "e" * 64,
            ]
        )


def test_explicit_dashboard_snapshot_apply_installs_only_one_shot_port(
    monkeypatch,
    capsys,
) -> None:
    source_root = cli._source_repository_root()
    host_config = enabled_host_config(source_root)
    captured = []

    class Capability:
        def __init__(self, *, config):
            captured.append(config)

        def apply(self, _context):
            return None

    def coordinate(**kwargs):
        captured.append(kwargs)
        assert kwargs["apply_dashboard_snapshot"] is True
        assert kwargs["snapshot_publication_capability"] is not None
        assert kwargs["publication_capability"] is None
        assert kwargs["fetch_capability"] is None
        assert kwargs["apply_capability"] is None
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return result(CoordinatorStatus.TRANSITION_EXECUTED)

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
    monkeypatch.setattr(
        cli,
        "DailyEodDashboardSnapshotApplyCapability",
        Capability,
    )
    monkeypatch.setattr(cli, "coordinate_daily_eod_transition", coordinate)

    invocation = arguments() + [
        "--apply-dashboard-snapshot",
        "--host-config",
        "/etc/trading-intelligence-platform/runtime/host.json",
        "--host-config-sha256",
        "c" * 64,
        "--dashboard-snapshot-approved-plan-sha256",
        "d" * 64,
        "--dashboard-snapshot-expected-current-state-fingerprint",
        "e" * 64,
    ]
    assert cli.main(invocation) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "transition_executed"
    assert captured[0].approved_plan_sha256 == "d" * 64
    assert captured[0].expected_current_state_fingerprint == "e" * 64
    assert captured[0].legacy_root == source_root / "build/private-dashboard"


def test_dashboard_snapshot_apply_bindings_are_exact_and_exclusive() -> None:
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--apply-dashboard-snapshot"])
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--dashboard-snapshot-approved-plan-sha256",
                "d" * 64,
            ]
        )
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--apply-dashboard-snapshot",
                "--apply-market-intelligence",
            ]
        )
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--apply-dashboard-snapshot",
                "--snapshot-generated-at",
                CHECKED,
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


def test_explicit_recovery_installs_only_no_network_recovery_port(
    monkeypatch,
    capsys,
) -> None:
    captured = []

    def coordinate(**kwargs):
        captured.append(kwargs)
        assert kwargs["recover_unresolved"] is True
        assert kwargs["recovery_capability"] is cli.recover_one_daily_eod_transition
        assert kwargs["fetch_capability"] is None
        assert kwargs["apply_capability"] is None
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.create_connection(("example.invalid", 443))
        return result(CoordinatorStatus.TRANSITION_EXECUTED)

    monkeypatch.setattr(cli, "coordinate_daily_eod_transition", coordinate)

    assert cli.main(arguments() + ["--recover-unresolved"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "transition_executed"
    assert len(captured) == 1


def test_recovery_cannot_be_combined_with_execution_or_authorized_ports() -> None:
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--recover-unresolved", "--execute-offline"])
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + ["--recover-unresolved", "--enable-authorized-capabilities"]
        )


def test_explicit_alert_intent_is_emitted_without_delivery(
    monkeypatch,
    capsys,
) -> None:
    alerting = DailyEodCoordinatorResult(
        status=CoordinatorStatus.BLOCKED,
        target_session=TARGET,
        next_action="operator_diagnosis",
        reason_codes=("daily_deadline_elapsed",),
        automation_plan_fingerprint="a" * 64,
        readiness_plan_fingerprint="b" * 64,
        transition_fingerprint=None,
        external_request_count=0,
        production_write_count=0,
        alert_required=True,
        logical_content_fingerprint="c" * 64,
    )
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: alerting,
    )

    assert cli.main(arguments() + ["--emit-alert-intent"]) == 1
    payload = json.loads(capsys.readouterr().out)
    intent = payload["alert_intent"]
    assert intent["category"] == "pipeline_blocked"
    assert intent["delivery_attempted"] is False
    assert intent["external_request_count"] == 0
    assert intent["production_write_count"] == 0


def test_explicit_alert_intent_is_null_for_normal_state(monkeypatch, capsys) -> None:
    normal = DailyEodCoordinatorResult(
        status=CoordinatorStatus.WAITING,
        target_session=TARGET,
        next_action="wait",
        reason_codes=("post_close_stabilization_window",),
        automation_plan_fingerprint="a" * 64,
        readiness_plan_fingerprint="b" * 64,
        transition_fingerprint=None,
        external_request_count=0,
        production_write_count=0,
        alert_required=False,
        logical_content_fingerprint="c" * 64,
    )
    monkeypatch.setattr(
        cli,
        "coordinate_daily_eod_transition",
        lambda **_kwargs: normal,
    )

    assert cli.main(arguments() + ["--emit-alert-intent"]) == 0
    assert json.loads(capsys.readouterr().out)["alert_intent"] is None
