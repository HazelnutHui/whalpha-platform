"""Externally pinned, default-disabled Dell runtime configuration."""

from __future__ import annotations

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
from pydantic_core import to_jsonable_python

from tip_api.services.daily_eod_readiness import DailyEodReadinessPolicy
from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
)


CONTRACT_VERSION = "daily-eod-host-runtime-config/1.0"
MAXIMUM_CONFIG_BYTES = 64 * 1024


class DailyEodHostRuntimeError(RuntimeError):
    """Raised when the host runtime identity or config is not exact and safe."""


class DailyEodHostRuntimeConfigV1(BaseModel):
    """External host-owned installation candidate; absence means disabled."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["daily-eod-host-runtime-config/1.0"] = (
        CONTRACT_VERSION
    )
    config_id: str = Field(
        min_length=16,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_.:-]+$",
    )
    host: Literal["dell5820"]
    repository_root: str
    implementation_revision: str
    data_root: str
    run_root: str
    authorization_root: str
    authorization_path: str
    authorization_file_sha256: str
    credential_path: str
    readiness_policy_fingerprint: str
    capabilities_enabled: bool
    one_transition_per_invocation: Literal[True] = True
    scheduler_enabled: Literal[False] = False
    publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    config_content_sha256: str

    @model_validator(mode="after")
    def validate_exact_boundaries(self) -> "DailyEodHostRuntimeConfigV1":
        repository_root = Path(self.repository_root)
        data_root = Path(self.data_root)
        run_root = Path(self.run_root)
        authorization_root = Path(self.authorization_root)
        authorization_path = Path(self.authorization_path)
        credential_path = Path(self.credential_path)
        if (
            not repository_root.is_absolute()
            or data_root != APPROVED_CANONICAL_DATA_ROOT
            or not run_root.is_absolute()
            or _is_within(run_root, Path("/data"))
            or _is_within(run_root, repository_root)
            or not authorization_root.is_absolute()
            or _is_within(authorization_root, Path("/data"))
            or _is_within(authorization_root, repository_root)
            or authorization_path.parent != authorization_root
            or authorization_path.name.startswith(".")
            or authorization_path.suffix != ".json"
            or not credential_path.is_absolute()
            or _is_within(credential_path, Path("/data"))
            or _is_within(credential_path, repository_root)
        ):
            raise ValueError("host runtime path boundary is invalid")
        if not _is_revision(self.implementation_revision):
            raise ValueError("host runtime implementation revision is malformed")
        if not _is_fingerprint(self.authorization_file_sha256) or not _is_fingerprint(
            self.readiness_policy_fingerprint
        ):
            raise ValueError("host runtime fingerprint is malformed")
        if not _is_fingerprint(self.config_content_sha256):
            raise ValueError("host runtime content fingerprint is malformed")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"config_content_sha256"})
        )
        if self.config_content_sha256 != expected:
            raise ValueError("host runtime content fingerprint mismatch")
        return self


@dataclass(frozen=True, slots=True)
class VerifiedDellRuntime:
    host: str
    repository_root: str
    implementation_revision: str
    readiness_policy_fingerprint: str
    worktree_clean: bool


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
HostnameReader = Callable[[], str]


def build_host_runtime_config_candidate(
    *,
    config_id: str,
    host: Literal["dell5820"],
    repository_root: Path,
    implementation_revision: str,
    data_root: Path,
    run_root: Path,
    authorization_root: Path,
    authorization_path: Path,
    authorization_file_sha256: str,
    credential_path: Path,
    readiness_policy_fingerprint: str,
    capabilities_enabled: bool = False,
) -> DailyEodHostRuntimeConfigV1:
    """Build an in-memory review candidate without installing or writing it."""

    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "config_id": config_id,
        "host": host,
        "repository_root": str(repository_root),
        "implementation_revision": implementation_revision,
        "data_root": str(data_root),
        "run_root": str(run_root),
        "authorization_root": str(authorization_root),
        "authorization_path": str(authorization_path),
        "authorization_file_sha256": authorization_file_sha256,
        "credential_path": str(credential_path),
        "readiness_policy_fingerprint": readiness_policy_fingerprint,
        "capabilities_enabled": capabilities_enabled,
        "one_transition_per_invocation": True,
        "scheduler_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
    }
    return DailyEodHostRuntimeConfigV1.model_validate(
        {**base, "config_content_sha256": _fingerprint(base)}
    )


def canonical_host_runtime_config_bytes(
    config: DailyEodHostRuntimeConfigV1,
) -> bytes:
    return _canonical_bytes(config.model_dump(mode="json"))


def read_host_runtime_config(
    *,
    config_path: Path,
    config_root: Path,
    repository_root: Path,
    expected_file_sha256: str,
) -> DailyEodHostRuntimeConfigV1:
    """Read one externally provisioned config under owner-only SHA custody."""

    if not _is_fingerprint(expected_file_sha256):
        raise DailyEodHostRuntimeError("host runtime file SHA is malformed")
    if (
        not config_root.is_absolute()
        or not repository_root.is_absolute()
        or config_path.parent != config_root
        or config_path.name.startswith(".")
        or config_path.suffix != ".json"
        or _is_within(config_root, Path("/data"))
        or _is_within(config_root, repository_root)
    ):
        raise DailyEodHostRuntimeError("host runtime config path boundary is invalid")
    try:
        root_metadata = config_root.lstat()
        file_metadata = config_path.lstat()
    except OSError as exc:
        raise DailyEodHostRuntimeError("host runtime config custody is unavailable") from exc
    if (
        config_root.resolve() != config_root
        or stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or root_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(root_metadata.st_mode) != 0o700
        or stat.S_ISLNK(file_metadata.st_mode)
        or not stat.S_ISREG(file_metadata.st_mode)
        or file_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(file_metadata.st_mode) != 0o400
        or not 0 < file_metadata.st_size <= MAXIMUM_CONFIG_BYTES
    ):
        raise DailyEodHostRuntimeError("host runtime config custody is unsafe")
    try:
        raw = config_path.read_bytes()
        config = DailyEodHostRuntimeConfigV1.model_validate(json.loads(raw))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise DailyEodHostRuntimeError("host runtime config is invalid") from exc
    if hashlib.sha256(raw).hexdigest() != expected_file_sha256:
        raise DailyEodHostRuntimeError("host runtime config file SHA mismatch")
    if raw != canonical_host_runtime_config_bytes(config):
        raise DailyEodHostRuntimeError("host runtime config is not canonical")
    if (
        Path(config.repository_root) != repository_root
        or config_root == Path(config.authorization_root)
    ):
        raise DailyEodHostRuntimeError("host runtime config identity mismatch")
    return config


def verify_dell_runtime(
    *,
    config: DailyEodHostRuntimeConfigV1,
    source_repository_root: Path,
    readiness_policy: DailyEodReadinessPolicy | None = None,
    hostname_reader: HostnameReader = socket.gethostname,
    command_runner: CommandRunner = subprocess.run,
) -> VerifiedDellRuntime:
    """Prove actual host, source checkout, clean HEAD, and policy revision."""

    repository_root = Path(config.repository_root)
    if (
        not source_repository_root.is_absolute()
        or source_repository_root.resolve() != repository_root.resolve()
        or not repository_root.is_dir()
        or repository_root.is_symlink()
    ):
        raise DailyEodHostRuntimeError("executing source repository differs from host config")
    actual_host = hostname_reader().split(".", 1)[0].strip().lower()
    if actual_host != config.host:
        raise DailyEodHostRuntimeError("actual host differs from host runtime config")
    try:
        revision_result = command_runner(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(repository_root),
                "rev-parse",
                "--verify",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        status_result = command_runner(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(repository_root),
                "status",
                "--porcelain=v1",
                "--untracked-files=normal",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DailyEodHostRuntimeError("repository runtime identity is unavailable") from exc
    revision = revision_result.stdout.strip()
    if not _is_revision(revision) or revision != config.implementation_revision:
        raise DailyEodHostRuntimeError("repository revision differs from host runtime config")
    if status_result.stdout:
        raise DailyEodHostRuntimeError("repository worktree is not clean")
    selected_policy = readiness_policy or DailyEodReadinessPolicy()
    if not isinstance(selected_policy, DailyEodReadinessPolicy):
        raise DailyEodHostRuntimeError("readiness policy is invalid")
    policy = selected_policy.logical_fingerprint
    if policy != config.readiness_policy_fingerprint:
        raise DailyEodHostRuntimeError("readiness policy differs from host runtime config")
    return VerifiedDellRuntime(
        host=actual_host,
        repository_root=str(repository_root),
        implementation_revision=revision,
        readiness_policy_fingerprint=policy,
        worktree_clean=True,
    )


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
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
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_revision(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )
