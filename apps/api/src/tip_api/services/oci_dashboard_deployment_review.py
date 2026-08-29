"""Write-free review of one exact external OCI deployment runtime candidate."""

from __future__ import annotations

import getpass
import hashlib
import json
import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from tip_api.services.oci_dashboard_deployment_runtime import (
    OciDashboardDeploymentRuntimeError,
    OciDashboardDeploymentRuntimeV1,
    build_deployment_runtime_candidate,
    canonical_deployment_runtime_bytes,
    verify_deployment_runtime,
)


CONTRACT_VERSION = "oci-dashboard-deployment-runtime-review/1.0"


class OciDashboardDeploymentReviewError(RuntimeError):
    """Raised when a runtime candidate cannot be reviewed without ambiguity."""


@dataclass(frozen=True, slots=True)
class OciDashboardDeploymentRuntimeReview:
    status: str
    candidate_config: dict[str, object]
    candidate_file_sha256: str
    capability_candidate_enabled: bool
    installation_performed: bool
    credential_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    deployment_authorized: bool
    rollback_authorized: bool
    scheduler_enabled: bool
    reason_code: str
    contract_version: str = CONTRACT_VERSION
    logical_content_fingerprint: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def review_deployment_runtime_candidate(
    *,
    config_id: str,
    repository_root: Path,
    run_root: Path,
    capability_enabled: bool = False,
    hostname_reader: Callable[[], str] = socket.gethostname,
    user_reader: Callable[[], str] = getpass.getuser,
    command_runner: CommandRunner = subprocess.run,
) -> OciDashboardDeploymentRuntimeReview:
    """Build and verify one in-memory candidate; never install or authorize it."""

    host = hostname_reader().split(".", 1)[0].strip().lower()
    user = user_reader()
    if host != "dell5820" or user != "hui":
        raise OciDashboardDeploymentReviewError(
            "deployment candidate review requires Dell hui"
        )
    if (
        not repository_root.is_absolute()
        or repository_root.is_symlink()
        or not repository_root.is_dir()
        or not run_root.is_absolute()
    ):
        raise OciDashboardDeploymentReviewError(
            "deployment candidate review path is invalid"
        )
    try:
        revision, branch, status = _repository_state(
            repository_root,
            command_runner=command_runner,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OciDashboardDeploymentReviewError(
            "deployment candidate repository state is unavailable"
        ) from exc
    if not _is_revision(revision) or branch != "main" or status:
        raise OciDashboardDeploymentReviewError(
            "deployment candidate requires clean main at an exact revision"
        )
    try:
        candidate = build_deployment_runtime_candidate(
            config_id=config_id,
            repository_root=repository_root,
            implementation_revision=revision,
            run_root=run_root,
            capability_enabled=capability_enabled,
        )
        verify_deployment_runtime(
            candidate,
            hostname_reader=hostname_reader,
            user_reader=user_reader,
            command_runner=command_runner,
        )
    except OciDashboardDeploymentRuntimeError as exc:
        raise OciDashboardDeploymentReviewError(
            "deployment candidate failed exact runtime verification"
        ) from exc
    raw = canonical_deployment_runtime_bytes(candidate)
    base: dict[str, object] = {
        "status": "review_ready",
        "candidate_config": candidate.model_dump(mode="json"),
        "candidate_file_sha256": hashlib.sha256(raw).hexdigest(),
        "capability_candidate_enabled": candidate.capability_enabled,
        "installation_performed": False,
        "credential_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
        "deployment_authorized": False,
        "rollback_authorized": False,
        "scheduler_enabled": False,
        "reason_code": (
            "enabled_candidate_requires_separate_installation_and_invocation_review"
            if candidate.capability_enabled
            else "disabled_candidate_ready_for_review"
        ),
        "contract_version": CONTRACT_VERSION,
    }
    return OciDashboardDeploymentRuntimeReview(
        **base,
        logical_content_fingerprint=_fingerprint(base),
    )


def candidate_from_review(
    review: OciDashboardDeploymentRuntimeReview,
) -> OciDashboardDeploymentRuntimeV1:
    """Reread the embedded candidate and its exact future-file SHA."""

    payload = review.as_dict()
    fingerprint = payload.pop("logical_content_fingerprint", None)
    if (
        fingerprint != _fingerprint(payload)
        or review.contract_version != CONTRACT_VERSION
        or review.status != "review_ready"
        or review.installation_performed
        or review.credential_access_count != 0
        or review.external_request_count != 0
        or review.filesystem_write_count != 0
        or review.production_write_count != 0
        or review.deployment_authorized
        or review.rollback_authorized
        or review.scheduler_enabled
    ):
        raise OciDashboardDeploymentReviewError(
            "deployment runtime review boundary is invalid"
        )
    try:
        candidate = OciDashboardDeploymentRuntimeV1.model_validate(
            review.candidate_config
        )
    except ValueError as exc:
        raise OciDashboardDeploymentReviewError(
            "review candidate config is invalid"
        ) from exc
    if (
        hashlib.sha256(canonical_deployment_runtime_bytes(candidate)).hexdigest()
        != review.candidate_file_sha256
        or candidate.capability_enabled != review.capability_candidate_enabled
        or review.reason_code
        != (
            "enabled_candidate_requires_separate_installation_and_invocation_review"
            if candidate.capability_enabled
            else "disabled_candidate_ready_for_review"
        )
    ):
        raise OciDashboardDeploymentReviewError(
            "review candidate identity or file SHA mismatch"
        )
    return candidate


def _repository_state(
    root: Path,
    *,
    command_runner: CommandRunner,
) -> tuple[str, str, str]:
    commands = (
        ["git", "--no-optional-locks", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        ["git", "--no-optional-locks", "-C", str(root), "branch", "--show-current"],
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "--untracked-files=normal",
        ],
    )
    results = tuple(
        command_runner(command, check=True, capture_output=True, text=True)
        for command in commands
    )
    return tuple(result.stdout.strip() for result in results)  # type: ignore[return-value]


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _is_revision(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )
