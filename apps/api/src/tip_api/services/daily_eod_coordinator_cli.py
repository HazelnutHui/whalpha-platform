"""Default-disabled CLI for exactly one Dell daily EOD transition."""

from __future__ import annotations

import argparse
import json
import socket
from functools import partial
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from tip_api.services.daily_eod_authorized_capabilities import (
    DailyEodAuthorizedCapabilities,
    DailyEodAuthorizedCapabilityConfig,
    DailyEodAuthorizedCapabilityError,
)
from tip_api.services.daily_eod_alerting import (
    DailyEodAlertingError,
    plan_daily_eod_alert,
)
from tip_api.services.daily_eod_alert_custody import (
    DailyEodAlertCustodyConfig,
    DailyEodAlertCustodyError,
    deliver_daily_eod_alert,
)
from tip_api.services.daily_eod_automation import DailyEodAutomationPaths
from tip_api.services.daily_eod_coordinator import (
    CoordinatorStatus,
    DailyEodCoordinatorConfig,
    DailyEodCoordinatorError,
    coordinate_daily_eod_transition,
)
from tip_api.services.daily_eod_email_delivery import (
    DailyEodEmailConfigError,
    DailyEodEmailDeliveryCapability,
    read_email_transport_config,
)
from tip_api.services.daily_eod_dashboard_snapshot_apply_capability import (
    DailyEodDashboardSnapshotApplyCapability,
    DailyEodDashboardSnapshotApplyCapabilityConfig,
    DailyEodDashboardSnapshotApplyCapabilityError,
)
from tip_api.services.daily_eod_dashboard_snapshot_apply_custody import (
    DailyEodDashboardSnapshotApplyCustodyError,
)
from tip_api.services.daily_eod_host_runtime import (
    DailyEodHostRuntimeError,
    read_host_runtime_config,
    verify_dell_runtime,
)
from tip_api.services.daily_eod_market_intelligence_apply_capability import (
    DailyEodMarketIntelligenceApplyCapability,
    DailyEodMarketIntelligenceApplyCapabilityConfig,
    DailyEodMarketIntelligenceApplyCapabilityError,
)
from tip_api.services.daily_eod_market_intelligence_apply_custody import (
    DailyEodMarketIntelligenceApplyCustodyError,
)
from tip_api.services.daily_eod_oci_deployment_capability import (
    DailyEodOciDeploymentCapability,
    DailyEodOciDeploymentCapabilityConfig,
    DailyEodOciDeploymentCapabilityError,
    ReviewedShellOciDeploymentTransport,
)
from tip_api.services.daily_eod_oci_deployment_custody import (
    DailyEodOciDeploymentCustodyError,
)
from tip_api.services.oci_dashboard_deployment_runtime import (
    OciDashboardDeploymentRuntimeError,
    read_deployment_runtime,
    verify_deployment_runtime,
)
from tip_api.services.oci_dashboard_deployment_state import (
    OciDashboardDeploymentStateError,
)
from tip_api.services.daily_eod_recovery_router import (
    DailyEodRecoveryRouterError,
    recover_one_daily_eod_transition,
)
from tip_api.services.daily_eod_readiness import (
    DailyEodReadinessPolicy,
    ProviderRecencyProfile,
)
from tip_api.services.daily_eod_run_journal import DailyEodRunJournalError


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_arguments(parser, args)
    readiness_policy = DailyEodReadinessPolicy(
        provider_recency_profile=ProviderRecencyProfile(
            args.provider_recency_profile
        )
    )
    automation_paths = DailyEodAutomationPaths(
        data_root=args.data_root,
        phase1a_audit=args.phase1a_audit,
        prior_phase1b_audit=args.prior_phase1b_audit,
        phase1b_audit=args.phase1b_audit,
        prior_candidate_audit=args.prior_candidate_audit,
        candidate_audit=args.candidate_audit,
        entry_geometry_audit=args.entry_geometry_audit,
        phase2_audit=args.phase2_audit,
        preview_bundle=args.preview_bundle,
        strategy_channel_audit=args.strategy_channel_audit,
        market_intelligence_output_root=args.market_intelligence_output_root,
        market_intelligence_approval_plan=args.market_intelligence_approval_plan,
        snapshot_output_root=args.snapshot_output_root,
        snapshot_approval_plan=args.snapshot_approval_plan,
        serving_bundle_root=args.serving_bundle_root,
    )
    coordinator_config = DailyEodCoordinatorConfig(
        target_session=args.target_session,
        latest_canonical_session=args.latest_canonical_session,
        paths=automation_paths,
        run_root=args.run_root,
        package_path=args.package,
        approval_plan_path=args.approval_plan,
        panel_cache_root=args.panel_cache_root,
        candidate_work_dir=args.candidate_work_dir,
        publication_created_at=args.publication_created_at,
        publication_expected_current_state_fingerprint=(
            args.publication_expected_current_state_fingerprint
        ),
        snapshot_generated_at=args.snapshot_generated_at,
        bundle_built_at=args.bundle_built_at,
        readiness_policy=readiness_policy,
    )
    result = None
    try:
        capabilities = (
            _load_authorized_capabilities(
                args, automation_paths, readiness_policy
            )
            if args.enable_authorized_capabilities
            else None
        )
        publication_capability = (
            _load_market_intelligence_apply_capability(
                args, automation_paths, readiness_policy
            )
            if args.apply_market_intelligence
            else None
        )
        snapshot_publication_capability = (
            _load_dashboard_snapshot_apply_capability(
                args, automation_paths, readiness_policy
            )
            if args.apply_dashboard_snapshot
            else None
        )
        deployment = (
            _load_oci_deployment(args, automation_paths)
            if args.deploy_oci_dashboard
            else None
        )
        recovery_transport = (
            _load_oci_recovery_transport(args)
            if args.recover_unresolved and args.deployment_config is not None
            else None
        )
        email_delivery = (
            _load_email_delivery(args, readiness_policy)
            if args.deliver_alert_email
            else None
        )
        with _network_boundary(
            enabled=(
                capabilities is not None
                or deployment is not None
                or recovery_transport is not None
            )
        ):
            recovery_capability = None
            if args.recover_unresolved:
                recovery_capability = (
                    recover_one_daily_eod_transition
                    if recovery_transport is None
                    else partial(
                        recover_one_daily_eod_transition,
                        oci_state_inspector=recovery_transport.inspect,
                        oci_deployment_config_file_sha256=(
                            args.deployment_config_sha256
                        ),
                    )
                )
            result = coordinate_daily_eod_transition(
                config=coordinator_config,
                checked_at=args.checked_at,
                execute_offline=args.execute_offline,
                recover_unresolved=args.recover_unresolved,
                apply_market_intelligence=args.apply_market_intelligence,
                apply_dashboard_snapshot=args.apply_dashboard_snapshot,
                deploy_oci_dashboard=args.deploy_oci_dashboard,
                fetch_capability=(None if capabilities is None else capabilities.fetch),
                apply_capability=(None if capabilities is None else capabilities.apply),
                recovery_capability=recovery_capability,
                publication_capability=(
                    None
                    if publication_capability is None
                    else publication_capability.apply
                ),
                snapshot_publication_capability=(
                    None
                    if snapshot_publication_capability is None
                    else snapshot_publication_capability.apply
                ),
                deployment_capability=(
                    None if deployment is None else deployment.deploy
                ),
            )
            payload = result.as_dict()
            if args.emit_alert_intent:
                intent = plan_daily_eod_alert(
                    target_session=args.target_session,
                    result=result,
                )
                payload["alert_intent"] = (
                    None if intent is None else intent.as_dict()
                )
        alert_delivery = None
        if email_delivery is not None and intent is not None:
            custody_config, capability = email_delivery
            alert_delivery = deliver_daily_eod_alert(
                config=custody_config,
                intent=intent,
                capability=capability,
            )
        if args.deliver_alert_email:
            payload["alert_delivery"] = (
                None if alert_delivery is None else alert_delivery.as_dict()
            )
    except (
        DailyEodAuthorizedCapabilityError,
        DailyEodAlertCustodyError,
        DailyEodAlertingError,
        DailyEodCoordinatorError,
        DailyEodEmailConfigError,
        DailyEodHostRuntimeError,
        DailyEodDashboardSnapshotApplyCapabilityError,
        DailyEodDashboardSnapshotApplyCustodyError,
        DailyEodMarketIntelligenceApplyCapabilityError,
        DailyEodMarketIntelligenceApplyCustodyError,
        DailyEodOciDeploymentCapabilityError,
        DailyEodOciDeploymentCustodyError,
        DailyEodRecoveryRouterError,
        DailyEodRunJournalError,
        OciDashboardDeploymentRuntimeError,
        OciDashboardDeploymentStateError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        transition_known = result is not None
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "daily_eod_one_transition_rejected",
                    "error_type": type(exc).__name__,
                    "coordinator_status": (
                        None if result is None else result.status.value
                    ),
                    "external_request_count": (
                        None if result is None else result.external_request_count
                    ),
                    "production_write_count": (
                        None if result is None else result.production_write_count
                    ),
                    "transition_outcome_formally_known": transition_known,
                    "alert_delivery_outcome_formally_known": False,
                    "publication_authorized": False,
                    "deployment_authorized": False,
                    "scheduler_enabled": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return (
        1
        if (
            result.status
            in {CoordinatorStatus.BLOCKED, CoordinatorStatus.RECOVERY_REQUIRED}
            or (
                alert_delivery is not None
                and alert_delivery.outcome == "failed"
            )
        )
        else 0
    )


def _load_authorized_capabilities(
    args: argparse.Namespace,
    automation_paths: DailyEodAutomationPaths,
    readiness_policy: DailyEodReadinessPolicy,
) -> DailyEodAuthorizedCapabilities:
    source_root = _source_repository_root()
    host_config = read_host_runtime_config(
        config_path=args.host_config,
        config_root=args.host_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.host_config_sha256,
    )
    if not host_config.capabilities_enabled:
        raise DailyEodHostRuntimeError(
            "host runtime capabilities are disabled"
        )
    verified = verify_dell_runtime(
        config=host_config,
        source_repository_root=source_root,
        readiness_policy=readiness_policy,
    )
    if (
        Path(host_config.data_root) != args.data_root
        or Path(host_config.run_root) != args.run_root
    ):
        raise DailyEodHostRuntimeError(
            "CLI data or run root differs from host runtime config"
        )
    return DailyEodAuthorizedCapabilities(
        config=DailyEodAuthorizedCapabilityConfig(
            authorization_path=Path(host_config.authorization_path),
            authorization_root=Path(host_config.authorization_root),
            repository_root=Path(host_config.repository_root),
            expected_authorization_file_sha256=(
                host_config.authorization_file_sha256
            ),
            actual_host=verified.host,
            implementation_revision=verified.implementation_revision,
            readiness_policy_fingerprint=verified.readiness_policy_fingerprint,
            data_root=Path(host_config.data_root),
            run_root=Path(host_config.run_root),
            automation_paths=automation_paths,
            credential_path=Path(host_config.credential_path),
            approved_plan_sha256=args.approved_plan_sha256,
            expected_current_state_fingerprint=(
                args.expected_current_state_fingerprint
            ),
        )
    )


def _load_email_delivery(
    args: argparse.Namespace,
    readiness_policy: DailyEodReadinessPolicy,
) -> tuple[DailyEodAlertCustodyConfig, DailyEodEmailDeliveryCapability]:
    source_root = _source_repository_root()
    host_config = read_host_runtime_config(
        config_path=args.host_config,
        config_root=args.host_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.host_config_sha256,
    )
    verified = verify_dell_runtime(
        config=host_config,
        source_repository_root=source_root,
        readiness_policy=readiness_policy,
    )
    if (
        Path(host_config.data_root) != args.data_root
        or Path(host_config.run_root) != args.run_root
        or _paths_overlap(args.host_config.parent, args.email_config.parent)
    ):
        raise DailyEodHostRuntimeError(
            "email delivery CLI paths differ from host runtime config"
        )
    email_config = read_email_transport_config(
        config_path=args.email_config,
        config_root=args.email_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.email_config_sha256,
    )
    if _paths_overlap(
        Path(host_config.credential_path).parent,
        Path(email_config.credential_path).parent,
    ):
        raise DailyEodEmailConfigError(
            "provider and email credentials require separate custody"
        )
    custody_config = DailyEodAlertCustodyConfig(
        alert_root=Path(email_config.alert_root),
        repository_root=Path(host_config.repository_root),
        data_root=Path(host_config.data_root),
        run_root=Path(host_config.run_root),
        channel="email",
    )
    capability = DailyEodEmailDeliveryCapability(
        config=email_config,
        custody_config=custody_config,
        verified_runtime=verified,
    )
    return custody_config, capability


def _load_market_intelligence_apply_capability(
    args: argparse.Namespace,
    automation_paths: DailyEodAutomationPaths,
    readiness_policy: DailyEodReadinessPolicy,
) -> DailyEodMarketIntelligenceApplyCapability:
    source_root = _source_repository_root()
    host_config = read_host_runtime_config(
        config_path=args.host_config,
        config_root=args.host_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.host_config_sha256,
    )
    if not host_config.capabilities_enabled:
        raise DailyEodHostRuntimeError(
            "host runtime capabilities are disabled"
        )
    verify_dell_runtime(
        config=host_config,
        source_repository_root=source_root,
        readiness_policy=readiness_policy,
    )
    if (
        Path(host_config.data_root) != args.data_root
        or Path(host_config.run_root) != args.run_root
    ):
        raise DailyEodHostRuntimeError(
            "MI Apply CLI paths differ from host runtime config"
        )
    return DailyEodMarketIntelligenceApplyCapability(
        config=DailyEodMarketIntelligenceApplyCapabilityConfig(
            data_root=args.data_root,
            run_root=args.run_root,
            automation_paths=automation_paths,
            approval_plan_path=args.market_intelligence_approval_plan,
            approved_plan_sha256=(
                args.market_intelligence_approved_plan_sha256
            ),
            expected_current_state_fingerprint=(
                args.market_intelligence_expected_current_state_fingerprint
            ),
            review_acknowledgement=(
                args.market_intelligence_review_acknowledgement
            ),
        )
    )


def _load_dashboard_snapshot_apply_capability(
    args: argparse.Namespace,
    automation_paths: DailyEodAutomationPaths,
    readiness_policy: DailyEodReadinessPolicy,
) -> DailyEodDashboardSnapshotApplyCapability:
    source_root = _source_repository_root()
    host_config = read_host_runtime_config(
        config_path=args.host_config,
        config_root=args.host_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.host_config_sha256,
    )
    if not host_config.capabilities_enabled:
        raise DailyEodHostRuntimeError(
            "host runtime capabilities are disabled"
        )
    verify_dell_runtime(
        config=host_config,
        source_repository_root=source_root,
        readiness_policy=readiness_policy,
    )
    if (
        Path(host_config.data_root) != args.data_root
        or Path(host_config.run_root) != args.run_root
    ):
        raise DailyEodHostRuntimeError(
            "Snapshot Apply CLI paths differ from host runtime config"
        )
    return DailyEodDashboardSnapshotApplyCapability(
        config=DailyEodDashboardSnapshotApplyCapabilityConfig(
            data_root=args.data_root,
            legacy_root=source_root / "build/private-dashboard",
            run_root=args.run_root,
            automation_paths=automation_paths,
            approval_plan_path=args.snapshot_approval_plan,
            approved_plan_sha256=(
                args.dashboard_snapshot_approved_plan_sha256
            ),
            expected_current_state_fingerprint=(
                args.dashboard_snapshot_expected_current_state_fingerprint
            ),
            review_acknowledgement=(
                args.dashboard_snapshot_review_acknowledgement
            ),
        )
    )


def _load_oci_runtime(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    source_root = _source_repository_root()
    config = read_deployment_runtime(
        config_path=args.deployment_config,
        config_root=args.deployment_config.parent,
        repository_root=source_root,
        expected_file_sha256=args.deployment_config_sha256,
    )
    if not config.capability_enabled:
        raise OciDashboardDeploymentRuntimeError(
            "OCI deployment capability is disabled"
        )
    if Path(config.run_root) != args.run_root:
        raise OciDashboardDeploymentRuntimeError(
            "OCI deployment run root differs from coordinator"
        )
    return verify_deployment_runtime(config)


def _load_oci_deployment(
    args: argparse.Namespace,
    automation_paths: DailyEodAutomationPaths,
) -> DailyEodOciDeploymentCapability:
    runtime = _load_oci_runtime(args)
    transport = ReviewedShellOciDeploymentTransport(runtime)
    return DailyEodOciDeploymentCapability(
        config=DailyEodOciDeploymentCapabilityConfig(
            run_root=args.run_root,
            automation_paths=automation_paths,
            bundle_path=args.approved_serving_bundle_path,
            approved_bundle_logical_fingerprint=(
                args.approved_serving_bundle_logical_fingerprint
            ),
            expected_remote_state_fingerprint=(
                args.expected_oci_remote_state_fingerprint
            ),
            expected_current_release=args.expected_current_oci_release,
            deployment_config_file_sha256=args.deployment_config_sha256,
        ),
        transport=transport,
    )


def _load_oci_recovery_transport(
    args: argparse.Namespace,
) -> ReviewedShellOciDeploymentTransport:
    return ReviewedShellOciDeploymentTransport(_load_oci_runtime(args))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coordinate exactly one Dell daily EOD transition without looping."
    )
    parser.add_argument("--target-session", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--latest-canonical-session", required=True, type=date.fromisoformat
    )
    parser.add_argument("--checked-at", required=True, type=datetime.fromisoformat)
    parser.add_argument(
        "--provider-recency-profile",
        choices=tuple(item.value for item in ProviderRecencyProfile),
        default=ProviderRecencyProfile.MASSIVE_STOCKS_BASIC_END_OF_DAY.value,
    )
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--approval-plan", required=True, type=Path)
    parser.add_argument("--phase1a-audit", required=True, type=Path)
    parser.add_argument("--prior-phase1b-audit", required=True, type=Path)
    parser.add_argument("--phase1b-audit", required=True, type=Path)
    parser.add_argument("--prior-candidate-audit", required=True, type=Path)
    parser.add_argument("--candidate-audit", required=True, type=Path)
    parser.add_argument("--entry-geometry-audit", required=True, type=Path)
    parser.add_argument("--phase2-audit", required=True, type=Path)
    parser.add_argument("--preview-bundle", required=True, type=Path)
    parser.add_argument("--strategy-channel-audit", required=True, type=Path)
    parser.add_argument("--market-intelligence-output-root", required=True, type=Path)
    parser.add_argument("--market-intelligence-approval-plan", required=True, type=Path)
    parser.add_argument("--snapshot-output-root", required=True, type=Path)
    parser.add_argument("--snapshot-approval-plan", required=True, type=Path)
    parser.add_argument("--serving-bundle-root", required=True, type=Path)
    parser.add_argument("--publication-created-at", type=datetime.fromisoformat)
    parser.add_argument("--publication-expected-current-state-fingerprint")
    parser.add_argument("--snapshot-generated-at", type=datetime.fromisoformat)
    parser.add_argument("--bundle-built-at", type=datetime.fromisoformat)
    parser.add_argument("--panel-cache-root", type=Path)
    parser.add_argument("--candidate-work-dir", type=Path)
    parser.add_argument("--execute-offline", action="store_true")
    parser.add_argument("--recover-unresolved", action="store_true")
    parser.add_argument("--apply-market-intelligence", action="store_true")
    parser.add_argument("--apply-dashboard-snapshot", action="store_true")
    parser.add_argument("--deploy-oci-dashboard", action="store_true")
    parser.add_argument("--emit-alert-intent", action="store_true")
    parser.add_argument("--deliver-alert-email", action="store_true")
    parser.add_argument("--enable-authorized-capabilities", action="store_true")
    parser.add_argument("--host-config", type=Path)
    parser.add_argument("--host-config-sha256")
    parser.add_argument("--email-config", type=Path)
    parser.add_argument("--email-config-sha256")
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--expected-current-state-fingerprint")
    parser.add_argument("--market-intelligence-approved-plan-sha256")
    parser.add_argument(
        "--market-intelligence-expected-current-state-fingerprint"
    )
    parser.add_argument("--market-intelligence-review-acknowledgement")
    parser.add_argument("--dashboard-snapshot-approved-plan-sha256")
    parser.add_argument(
        "--dashboard-snapshot-expected-current-state-fingerprint"
    )
    parser.add_argument("--dashboard-snapshot-review-acknowledgement")
    parser.add_argument("--deployment-config", type=Path)
    parser.add_argument("--deployment-config-sha256")
    parser.add_argument("--approved-serving-bundle-path", type=Path)
    parser.add_argument("--approved-serving-bundle-logical-fingerprint")
    parser.add_argument("--expected-oci-remote-state-fingerprint")
    parser.add_argument("--expected-current-oci-release")
    return parser


def _validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    path_names = (
        "data_root",
        "run_root",
        "package",
        "approval_plan",
        "phase1a_audit",
        "prior_phase1b_audit",
        "phase1b_audit",
        "prior_candidate_audit",
        "candidate_audit",
        "entry_geometry_audit",
        "phase2_audit",
        "preview_bundle",
        "strategy_channel_audit",
        "market_intelligence_output_root",
        "market_intelligence_approval_plan",
        "snapshot_output_root",
        "snapshot_approval_plan",
        "serving_bundle_root",
        "panel_cache_root",
        "candidate_work_dir",
        "deployment_config",
        "approved_serving_bundle_path",
    )
    for name in path_names:
        value = getattr(args, name)
        if value is not None and not value.is_absolute():
            parser.error(f"--{name.replace('_', '-')} must be absolute")
    if args.recover_unresolved and args.enable_authorized_capabilities:
        parser.error(
            "--recover-unresolved cannot be combined with authorized capabilities"
        )
    if args.recover_unresolved and args.execute_offline:
        parser.error("--recover-unresolved cannot be combined with --execute-offline")
    if args.apply_market_intelligence and (
        args.recover_unresolved
        or args.execute_offline
        or args.enable_authorized_capabilities
        or args.deliver_alert_email
        or args.apply_dashboard_snapshot
    ):
        parser.error(
            "--apply-market-intelligence cannot be combined with another execution mode"
        )
    if args.apply_dashboard_snapshot and (
        args.recover_unresolved
        or args.execute_offline
        or args.enable_authorized_capabilities
        or args.deliver_alert_email
    ):
        parser.error(
            "--apply-dashboard-snapshot cannot be combined with another execution mode"
        )
    if args.deploy_oci_dashboard and (
        args.recover_unresolved
        or args.execute_offline
        or args.enable_authorized_capabilities
        or args.deliver_alert_email
        or args.apply_market_intelligence
        or args.apply_dashboard_snapshot
    ):
        parser.error(
            "--deploy-oci-dashboard cannot be combined with another execution mode"
        )
    publication_values = (
        args.publication_created_at,
        args.publication_expected_current_state_fingerprint,
    )
    if (
        args.apply_market_intelligence
        or args.apply_dashboard_snapshot
        or args.deploy_oci_dashboard
    ) and any(value is not None for value in publication_values):
        parser.error(
            "publication Apply cannot accept MI Plan preparation bindings"
        )
    if (
        args.apply_market_intelligence
        or args.apply_dashboard_snapshot
        or args.deploy_oci_dashboard
    ) and args.snapshot_generated_at is not None:
        parser.error(
            "publication Apply cannot accept Snapshot Plan preparation bindings"
        )
    if (
        args.apply_market_intelligence
        or args.apply_dashboard_snapshot
        or args.deploy_oci_dashboard
    ) and args.bundle_built_at is not None:
        parser.error(
            "publication Apply cannot accept serving-bundle build bindings"
        )
    if any(value is not None for value in publication_values) and not all(
        value is not None for value in publication_values
    ):
        parser.error("publication planning bindings must be supplied together")
    if (
        args.publication_expected_current_state_fingerprint is not None
        and not _is_fingerprint(
            args.publication_expected_current_state_fingerprint
        )
    ):
        parser.error("publication current-state binding must be SHA-256")
    host_values = (args.host_config, args.host_config_sha256)
    host_required = (
        args.enable_authorized_capabilities
        or args.deliver_alert_email
        or args.apply_market_intelligence
        or args.apply_dashboard_snapshot
    )
    if host_required:
        if args.host_config is None or not _is_fingerprint(args.host_config_sha256):
            parser.error(
                "authorized capabilities or email delivery require an absolute "
                "--host-config and --host-config-sha256"
            )
        if not args.host_config.is_absolute():
            parser.error("--host-config must be absolute")
    elif any(value is not None for value in host_values):
        parser.error(
            "host runtime arguments require an explicitly enabled capability"
        )
    email_values = (args.email_config, args.email_config_sha256)
    if args.deliver_alert_email:
        if not args.emit_alert_intent:
            parser.error("--deliver-alert-email requires --emit-alert-intent")
        if (
            args.email_config is None
            or not args.email_config.is_absolute()
            or not _is_fingerprint(args.email_config_sha256)
        ):
            parser.error(
                "--deliver-alert-email requires an absolute --email-config "
                "and --email-config-sha256"
            )
    elif any(value is not None for value in email_values):
        parser.error("email config arguments require --deliver-alert-email")
    apply_values = (
        args.approved_plan_sha256,
        args.expected_current_state_fingerprint,
    )
    if any(value is not None for value in apply_values) and not all(
        _is_fingerprint(value) for value in apply_values
    ):
        parser.error(
            "approved Apply inputs must be supplied together as SHA-256 fingerprints"
        )
    if any(value is not None for value in apply_values) and not args.enable_authorized_capabilities:
        parser.error(
            "approved Apply inputs require --enable-authorized-capabilities"
        )
    mi_apply_values = (
        args.market_intelligence_approved_plan_sha256,
        args.market_intelligence_expected_current_state_fingerprint,
    )
    if args.apply_market_intelligence:
        if not all(_is_fingerprint(value) for value in mi_apply_values):
            parser.error(
                "MI Apply requires the exact plan SHA-256 and current-state fingerprint"
            )
    elif any(value is not None for value in mi_apply_values) or (
        args.market_intelligence_review_acknowledgement is not None
    ):
        parser.error(
            "MI Apply bindings require --apply-market-intelligence"
        )
    snapshot_apply_values = (
        args.dashboard_snapshot_approved_plan_sha256,
        args.dashboard_snapshot_expected_current_state_fingerprint,
    )
    if args.apply_dashboard_snapshot:
        if not all(_is_fingerprint(value) for value in snapshot_apply_values):
            parser.error(
                "Snapshot Apply requires the exact plan SHA-256 and current-state fingerprint"
            )
    elif any(value is not None for value in snapshot_apply_values) or (
        args.dashboard_snapshot_review_acknowledgement is not None
    ):
        parser.error(
            "Snapshot Apply bindings require --apply-dashboard-snapshot"
        )
    deployment_config_values = (
        args.deployment_config,
        args.deployment_config_sha256,
    )
    deployment_config_required = args.deploy_oci_dashboard or (
        args.recover_unresolved and args.deployment_config is not None
    )
    if deployment_config_required:
        if (
            args.deployment_config is None
            or not args.deployment_config.is_absolute()
            or not _is_fingerprint(args.deployment_config_sha256)
        ):
            parser.error(
                "OCI deployment or its recovery inspection requires an absolute "
                "--deployment-config and exact --deployment-config-sha256"
            )
    elif any(value is not None for value in deployment_config_values):
        parser.error(
            "deployment config arguments require OCI deployment or explicit recovery"
        )
    deployment_values = (
        args.approved_serving_bundle_path,
        args.approved_serving_bundle_logical_fingerprint,
        args.expected_oci_remote_state_fingerprint,
        args.expected_current_oci_release,
    )
    if args.deploy_oci_dashboard:
        if (
            args.approved_serving_bundle_path is None
            or not args.approved_serving_bundle_path.is_absolute()
            or not all(
                _is_fingerprint(value)
                for value in (
                    args.approved_serving_bundle_logical_fingerprint,
                    args.expected_oci_remote_state_fingerprint,
                )
            )
            or not isinstance(args.expected_current_oci_release, str)
        ):
            parser.error("OCI deployment requires all exact bundle and remote bindings")
    elif any(value is not None for value in deployment_values):
        parser.error("OCI deployment bindings require --deploy-oci-dashboard")


def _source_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise DailyEodHostRuntimeError("executing source repository root is unavailable")


@contextmanager
def _network_boundary(*, enabled: bool):
    if enabled:
        yield
        return
    original_socket = socket.socket
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    class GuardedSocket(original_socket):
        def connect(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited without authorized capabilities")

        def connect_ex(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("network is prohibited without authorized capabilities")

    def rejected(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("network is prohibited without authorized capabilities")

    socket.socket = GuardedSocket
    socket.create_connection = rejected
    socket.getaddrinfo = rejected
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _paths_overlap(left: Path, right: Path) -> bool:
    try:
        left.absolute().relative_to(right.absolute())
        return True
    except ValueError:
        pass
    try:
        right.absolute().relative_to(left.absolute())
        return True
    except ValueError:
        return False


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
