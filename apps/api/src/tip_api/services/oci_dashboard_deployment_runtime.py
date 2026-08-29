"""Owner-pinned, default-disabled runtime configuration for one OCI deployment."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import socket
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "oci-dashboard-deployment-runtime/1.0"
MAXIMUM_CONFIG_BYTES = 32 * 1024


class OciDashboardDeploymentRuntimeError(RuntimeError):
    """Raised when external deployment authority or Dell identity is unsafe."""


class OciDashboardDeploymentRuntimeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["oci-dashboard-deployment-runtime/1.0"] = CONTRACT_VERSION
    config_id: str = Field(min_length=16, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$")
    host: Literal["dell5820"]
    user: Literal["hui"]
    repository_root: str
    branch: Literal["main"]
    implementation_revision: str
    run_root: str
    remote_alias: Literal["whalpha-oci"]
    remote_host: Literal["hui"]
    remote_user: Literal["ubuntu"]
    deploy_script: str
    inspect_script: str
    capability_enabled: bool
    one_shot: Literal[True] = True
    scheduler_enabled: Literal[False] = False
    rollback_authorized: Literal[False] = False
    password_access_authorized: Literal[False] = False
    config_content_sha256: str

    @model_validator(mode="after")
    def exact_boundary(self) -> "OciDashboardDeploymentRuntimeV1":
        repo = Path(self.repository_root)
        run_root = Path(self.run_root)
        deploy = Path(self.deploy_script)
        inspect = Path(self.inspect_script)
        if (
            not repo.is_absolute()
            or not run_root.is_absolute()
            or _is_within(run_root, repo)
            or _is_within(run_root, Path("/data"))
            or deploy != repo / "scripts/admin/deploy-private-dashboard-oci.sh"
            or inspect != repo / "scripts/admin/inspect-private-dashboard-oci.sh"
            or not _is_revision(self.implementation_revision)
            or not _is_fingerprint(self.config_content_sha256)
        ):
            raise ValueError("deployment runtime boundary is invalid")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"config_content_sha256"})
        )
        if self.config_content_sha256 != expected:
            raise ValueError("deployment runtime content fingerprint mismatch")
        return self


@dataclass(frozen=True, slots=True)
class VerifiedOciDeploymentRuntime:
    repository_root: Path
    implementation_revision: str
    deploy_script: Path
    inspect_script: Path


def build_deployment_runtime_candidate(
    *,
    config_id: str,
    repository_root: Path,
    implementation_revision: str,
    run_root: Path,
    capability_enabled: bool = False,
) -> OciDashboardDeploymentRuntimeV1:
    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "config_id": config_id,
        "host": "dell5820",
        "user": "hui",
        "repository_root": str(repository_root),
        "branch": "main",
        "implementation_revision": implementation_revision,
        "run_root": str(run_root),
        "remote_alias": "whalpha-oci",
        "remote_host": "hui",
        "remote_user": "ubuntu",
        "deploy_script": str(repository_root / "scripts/admin/deploy-private-dashboard-oci.sh"),
        "inspect_script": str(repository_root / "scripts/admin/inspect-private-dashboard-oci.sh"),
        "capability_enabled": capability_enabled,
        "one_shot": True,
        "scheduler_enabled": False,
        "rollback_authorized": False,
        "password_access_authorized": False,
    }
    return OciDashboardDeploymentRuntimeV1.model_validate(
        {**base, "config_content_sha256": _fingerprint(base)}
    )


def read_deployment_runtime(
    *,
    config_path: Path,
    config_root: Path,
    repository_root: Path,
    expected_file_sha256: str,
) -> OciDashboardDeploymentRuntimeV1:
    if (
        not _is_fingerprint(expected_file_sha256)
        or not config_root.is_absolute()
        or config_path.parent != config_root
        or config_path.suffix != ".json"
        or config_path.name.startswith(".")
        or _is_within(config_root, repository_root)
        or _is_within(config_root, Path("/data"))
    ):
        raise OciDashboardDeploymentRuntimeError("deployment config path boundary is invalid")
    try:
        root_meta = config_root.lstat()
        file_meta = config_path.lstat()
        raw = config_path.read_bytes()
    except OSError as exc:
        raise OciDashboardDeploymentRuntimeError(
            "deployment config custody is unavailable"
        ) from exc
    if (
        config_root.resolve() != config_root
        or stat.S_ISLNK(root_meta.st_mode)
        or not stat.S_ISDIR(root_meta.st_mode)
        or root_meta.st_uid != os.geteuid()
        or stat.S_IMODE(root_meta.st_mode) != 0o700
        or stat.S_ISLNK(file_meta.st_mode)
        or not stat.S_ISREG(file_meta.st_mode)
        or file_meta.st_uid != os.geteuid()
        or stat.S_IMODE(file_meta.st_mode) != 0o400
        or not 0 < len(raw) <= MAXIMUM_CONFIG_BYTES
        or hashlib.sha256(raw).hexdigest() != expected_file_sha256
    ):
        raise OciDashboardDeploymentRuntimeError("deployment config custody is unsafe")
    try:
        config = OciDashboardDeploymentRuntimeV1.model_validate_json(raw)
    except ValueError as exc:
        raise OciDashboardDeploymentRuntimeError("deployment config is invalid") from exc
    canonical = _canonical_bytes(config.model_dump(mode="json"))
    if raw != canonical or Path(config.repository_root) != repository_root:
        raise OciDashboardDeploymentRuntimeError("deployment config identity mismatch")
    return config


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def verify_deployment_runtime(
    config: OciDashboardDeploymentRuntimeV1,
    *,
    hostname_reader: Callable[[], str] = socket.gethostname,
    user_reader: Callable[[], str] = getpass.getuser,
    command_runner: CommandRunner = subprocess.run,
) -> VerifiedOciDeploymentRuntime:
    repo = Path(config.repository_root)
    if (
        hostname_reader().split(".", 1)[0].lower() != config.host
        or user_reader() != config.user
        or repo.is_symlink()
        or not repo.is_dir()
    ):
        raise OciDashboardDeploymentRuntimeError("deployment host identity mismatch")
    commands = (
        ["git", "--no-optional-locks", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
        ["git", "--no-optional-locks", "-C", str(repo), "branch", "--show-current"],
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(repo),
            "status",
            "--porcelain=v1",
            "--untracked-files=normal",
        ],
    )
    try:
        results = tuple(
            command_runner(command, check=True, capture_output=True, text=True)
            for command in commands
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OciDashboardDeploymentRuntimeError(
            "deployment repository identity unavailable"
        ) from exc
    if (
        results[0].stdout.strip() != config.implementation_revision
        or results[1].stdout.strip() != config.branch
        or results[2].stdout
    ):
        raise OciDashboardDeploymentRuntimeError("deployment repository state changed")
    deploy = Path(config.deploy_script)
    inspect = Path(config.inspect_script)
    for path in (deploy, inspect):
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise OciDashboardDeploymentRuntimeError("deployment script custody mismatch")
    return VerifiedOciDeploymentRuntime(repo, config.implementation_revision, deploy, inspect)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _is_revision(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(c in "0123456789abcdef" for c in value)
    )
