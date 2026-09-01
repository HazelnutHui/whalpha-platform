"""Write-free plan for an immutable Dell daily-scheduler runtime checkout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "daily-eod-scheduler-runtime-plan/1.0"
APPROVED_SOURCE_REPOSITORY = Path(
    "/home/hui/projects/trading-intelligence-platform"
)
APPROVED_RUNTIME_PARENT = Path(
    "/home/hui/.local/share/trading-intelligence-platform/daily-eod-scheduler-runtime"
)
APPROVED_PYTHON_LAUNCHER = APPROVED_SOURCE_REPOSITORY / ".venv/bin/python"


class DailyEodSchedulerRuntimePlanError(RuntimeError):
    """Raised when the immutable-runtime boundary is not exact and safe."""


class DailyEodSchedulerRuntimePlanV1(BaseModel):
    """Exact proposed checkout; this model performs and authorizes no write."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["daily-eod-scheduler-runtime-plan/1.0"] = (
        CONTRACT_VERSION
    )
    host: Literal["dell5820"]
    user: Literal["hui"]
    source_repository: str
    implementation_revision: str
    checkout_mode: Literal["detached_git_worktree"]
    runtime_parent: str
    runtime_root: str
    runtime_entrypoint: str
    runtime_package_root: str
    python_launcher: str
    expected_python_executable: str
    required_runtime_checks: tuple[str, ...]
    creation_command: tuple[str, ...]
    network_authorized: Literal[False]
    credential_access_authorized: Literal[False]
    data_read_authorized: Literal[False]
    filesystem_write_authorized: Literal[False]
    production_write_authorized: Literal[False]
    systemd_change_authorized: Literal[False]
    creation_performed: Literal[False]
    installation_performed: Literal[False]
    logical_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_exact_plan(self) -> "DailyEodSchedulerRuntimePlanV1":
        source = Path(self.source_repository)
        runtime_parent = Path(self.runtime_parent)
        runtime_root = Path(self.runtime_root)
        revision = self.implementation_revision
        expected_root = APPROVED_RUNTIME_PARENT / f"revision={revision}"
        if (
            source != APPROVED_SOURCE_REPOSITORY
            or runtime_parent != APPROVED_RUNTIME_PARENT
            or runtime_root != expected_root
            or Path(self.runtime_entrypoint)
            != expected_root / "scripts/admin/plan-daily-eod-scheduler.sh"
            or Path(self.runtime_package_root) != expected_root / "apps/api/src"
            or Path(self.python_launcher) != APPROVED_PYTHON_LAUNCHER
            or not Path(self.expected_python_executable).is_absolute()
            or not _is_revision(revision)
            or self.creation_command
            != (
                "/usr/bin/git",
                "-C",
                str(APPROVED_SOURCE_REPOSITORY),
                "worktree",
                "add",
                "--detach",
                str(expected_root),
                revision,
            )
            or self.required_runtime_checks != _required_runtime_checks()
        ):
            raise ValueError("daily scheduler runtime plan boundary is invalid")
        expected_fingerprint = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_content_fingerprint"})
        )
        if self.logical_content_fingerprint != expected_fingerprint:
            raise ValueError("daily scheduler runtime plan fingerprint mismatch")
        return self


def build_daily_eod_scheduler_runtime_plan(
    *,
    implementation_revision: str,
    expected_python_executable: Path,
) -> DailyEodSchedulerRuntimePlanV1:
    """Build a deterministic plan without inspecting or changing host state."""

    if not _is_revision(implementation_revision):
        raise DailyEodSchedulerRuntimePlanError(
            "implementation revision must be an exact 40-character commit"
        )
    if not expected_python_executable.is_absolute():
        raise DailyEodSchedulerRuntimePlanError(
            "expected Python executable must be absolute"
        )
    runtime_root = APPROVED_RUNTIME_PARENT / (
        f"revision={implementation_revision}"
    )
    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "host": "dell5820",
        "user": "hui",
        "source_repository": str(APPROVED_SOURCE_REPOSITORY),
        "implementation_revision": implementation_revision,
        "checkout_mode": "detached_git_worktree",
        "runtime_parent": str(APPROVED_RUNTIME_PARENT),
        "runtime_root": str(runtime_root),
        "runtime_entrypoint": str(
            runtime_root / "scripts/admin/plan-daily-eod-scheduler.sh"
        ),
        "runtime_package_root": str(runtime_root / "apps/api/src"),
        "python_launcher": str(APPROVED_PYTHON_LAUNCHER),
        "expected_python_executable": str(expected_python_executable),
        "required_runtime_checks": _required_runtime_checks(),
        "creation_command": (
            "/usr/bin/git",
            "-C",
            str(APPROVED_SOURCE_REPOSITORY),
            "worktree",
            "add",
            "--detach",
            str(runtime_root),
            implementation_revision,
        ),
        "network_authorized": False,
        "credential_access_authorized": False,
        "data_read_authorized": False,
        "filesystem_write_authorized": False,
        "production_write_authorized": False,
        "systemd_change_authorized": False,
        "creation_performed": False,
        "installation_performed": False,
    }
    return DailyEodSchedulerRuntimePlanV1.model_validate(
        {**base, "logical_content_fingerprint": _fingerprint(base)}
    )


def _required_runtime_checks() -> tuple[str, ...]:
    return (
        "runtime_root_is_exact_non_symlink_directory",
        "git_head_equals_implementation_revision",
        "git_checkout_is_detached",
        "git_worktree_is_clean",
        "runtime_entrypoint_is_regular_executable_file",
        "python_launcher_resolves_to_expected_python_executable",
        "runtime_imports_resolve_from_runtime_package_root",
        "scheduler_verify_dell_runtime_passes_exact_revision",
    )


def _is_revision(value: str) -> bool:
    return len(value) == 40 and all(
        character in "0123456789abcdef" for character in value
    )


def _fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
