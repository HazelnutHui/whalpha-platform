"""Explicit one-shot OCI deployment capability and reviewed shell transport."""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

from tip_api.services.daily_eod_coordinator import (
    DeploymentTransitionContext,
    DeploymentTransitionEvidence,
)
from tip_api.services.daily_eod_automation import DailyEodAutomationPaths
from tip_api.services.daily_eod_oci_deployment_custody import (
    DailyEodOciDeploymentConfig,
    OciDeploymentCustodyResult,
    record_oci_deployment_success,
    reserve_oci_deployment,
)
from tip_api.services.oci_dashboard_deployment_runtime import (
    VerifiedOciDeploymentRuntime,
)
from tip_api.services.oci_dashboard_deployment_state import (
    OciDashboardDeploymentStateError,
    OciDashboardDeploymentBinding,
    OciDashboardRemoteStateV1,
    parse_remote_state_json,
    read_deployment_binding,
)


CONTRACT_VERSION = "daily-eod-oci-deployment-capability/1.0"


class DailyEodOciDeploymentCapabilityError(RuntimeError):
    """Raised when the exact one-shot remote transition cannot be proven."""


class OciDeploymentTransport(Protocol):
    def inspect(self, *, target_release: str) -> OciDashboardRemoteStateV1: ...

    def apply(
        self,
        *,
        bundle_path: Path,
        release_id: str,
        expected_current_release: str,
    ) -> None: ...


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class ReviewedShellOciDeploymentTransport:
    """Invoke only the two fixed reviewed scripts; never a shell command string."""

    def __init__(
        self,
        runtime: VerifiedOciDeploymentRuntime,
        *,
        command_runner: CommandRunner = subprocess.run,
    ) -> None:
        self._runtime = runtime
        self._run = command_runner

    def inspect(self, *, target_release: str) -> OciDashboardRemoteStateV1:
        try:
            result = self._run(
                [str(self._runtime.inspect_script), "--target-release", target_release],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            return parse_remote_state_json(result.stdout)
        except (
            OSError,
            subprocess.SubprocessError,
            OciDashboardDeploymentStateError,
        ) as exc:
            raise DailyEodOciDeploymentCapabilityError(
                "read-only OCI state inspection failed"
            ) from exc

    def apply(
        self,
        *,
        bundle_path: Path,
        release_id: str,
        expected_current_release: str,
    ) -> None:
        try:
            self._run(
                [
                    str(self._runtime.deploy_script),
                    "--bundle-release",
                    release_id,
                    "--bundle-path",
                    str(bundle_path),
                    "--expected-current-release",
                    expected_current_release,
                    "--apply",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=900,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DailyEodOciDeploymentCapabilityError(
                "OCI Apply outcome requires read-only recovery inspection"
            ) from exc


@dataclass(frozen=True, slots=True)
class DailyEodOciDeploymentCapabilityConfig:
    run_root: Path
    automation_paths: DailyEodAutomationPaths
    bundle_path: Path
    approved_bundle_logical_fingerprint: str
    expected_remote_state_fingerprint: str
    expected_current_release: str
    deployment_config_file_sha256: str


Clock = Callable[[], datetime]
Reserver = Callable[..., OciDeploymentCustodyResult]
Recorder = Callable[..., OciDeploymentCustodyResult]
BindingReader = Callable[..., OciDashboardDeploymentBinding]


class DailyEodOciDeploymentCapability:
    def __init__(
        self,
        *,
        config: DailyEodOciDeploymentCapabilityConfig,
        transport: OciDeploymentTransport,
        clock: Clock = lambda: datetime.now(UTC),
        reserver: Reserver = reserve_oci_deployment,
        recorder: Recorder = record_oci_deployment_success,
        binding_reader: BindingReader = read_deployment_binding,
    ) -> None:
        self._config = config
        self._transport = transport
        self._clock = clock
        self._reserver = reserver
        self._recorder = recorder
        self._binding_reader = binding_reader

    def deploy(self, context: DeploymentTransitionContext) -> DeploymentTransitionEvidence:
        if (
            not isinstance(context, DeploymentTransitionContext)
            or context.operation != "deploy_oci_dashboard"
            or context.coordinator.run_root != self._config.run_root
            or context.coordinator.paths != self._config.automation_paths
            or context.bundle_path != self._config.bundle_path
            or context.bundle_logical_fingerprint
            != self._config.approved_bundle_logical_fingerprint
        ):
            raise DailyEodOciDeploymentCapabilityError(
                "deployment context differs from one-shot bindings"
            )
        _validate_local_approval(self._config, context)
        try:
            local_binding = self._binding_reader(
                self._config.bundle_path,
                expected_bundle_logical_fingerprint=(
                    self._config.approved_bundle_logical_fingerprint
                ),
            )
        except OciDashboardDeploymentStateError as exc:
            raise DailyEodOciDeploymentCapabilityError(
                "local Serving Bundle approval is invalid"
            ) from exc
        if local_binding.bundle.deployment_manifest.release_id != context.release_id:
            raise DailyEodOciDeploymentCapabilityError(
                "local Serving Bundle release differs from coordinator evidence"
            )
        custody = DailyEodOciDeploymentConfig(
            target_session=context.coordinator.target_session,
            bundle_path=self._config.bundle_path,
            approved_bundle_logical_fingerprint=(
                self._config.approved_bundle_logical_fingerprint
            ),
            expected_remote_state_fingerprint=(
                self._config.expected_remote_state_fingerprint
            ),
            expected_current_release=self._config.expected_current_release,
            deployment_config_file_sha256=(
                self._config.deployment_config_file_sha256
            ),
            run_root=self._config.run_root,
            automation_paths=context.coordinator.paths,
        )
        pre_state = self._transport.inspect(target_release=context.release_id)
        reservation = self._reserver(
            config=custody,
            checked_at=context.checked_at,
            expected_automation_plan_fingerprint=(
                context.automation_plan.logical_content_fingerprint
            ),
            remote_state=pre_state,
            clock=self._clock,
        )
        if reservation.outcome != "reserved" or reservation.binding is None:
            raise DailyEodOciDeploymentCapabilityError(
                "OCI deployment was not durably reserved"
            )
        binding = reservation.binding
        if binding.bundle.deployment_manifest.release_id != context.release_id:
            raise DailyEodOciDeploymentCapabilityError(
                "reserved release differs from coordinator evidence"
            )
        self._transport.apply(
            bundle_path=binding.bundle.path,
            release_id=context.release_id,
            expected_current_release=self._config.expected_current_release,
        )
        post_state = self._transport.inspect(target_release=context.release_id)
        completed = self._recorder(
            config=custody,
            remote_state=post_state,
            clock=self._clock,
        )
        if completed.outcome != "succeeded":
            raise DailyEodOciDeploymentCapabilityError(
                "OCI deployment post-state was not formally proven"
            )
        return DeploymentTransitionEvidence(
            operation="deploy_oci_dashboard",
            target_session=context.coordinator.target_session.isoformat(),
            precondition_fingerprint=context.automation_plan.logical_content_fingerprint,
            outcome="succeeded",
            event_fingerprint=completed.event.event_fingerprint,
            external_request_count=3,
            production_write_count=1,
            release_id=context.release_id,
            reason_code=completed.reason_code,
        )


def _validate_local_approval(
    config: DailyEodOciDeploymentCapabilityConfig,
    context: DeploymentTransitionContext,
) -> None:
    if (
        not config.bundle_path.is_absolute()
        or config.bundle_path.parent.parent != Path("/tmp")
        or config.bundle_path.name != context.release_id
        or not config.run_root.is_absolute()
        or not all(
            _is_fingerprint(value)
            for value in (
                config.approved_bundle_logical_fingerprint,
                config.expected_remote_state_fingerprint,
                config.deployment_config_file_sha256,
            )
        )
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[0-9a-f]{7,40}",
            config.expected_current_release,
        )
        is None
    ):
        raise DailyEodOciDeploymentCapabilityError(
            "local OCI deployment approval binding is invalid"
        )


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
