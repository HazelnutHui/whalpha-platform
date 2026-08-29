"""Exact, non-installed user-systemd candidate for read-only wake planning."""

from __future__ import annotations

import hashlib
import json
import os
import pwd
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.services.daily_eod_standing_authorization import (
    APPROVED_CANONICAL_DATA_ROOT,
)


CONTRACT_VERSION = "daily-eod-scheduler-systemd-candidate/1.0"
REVIEW_CONTRACT_VERSION = "daily-eod-scheduler-systemd-review/1.1"
SERVICE_UNIT_NAME = "whalpha-daily-eod-wake-review.service"
TIMER_UNIT_NAME = "whalpha-daily-eod-wake-review.timer"
CALENDAR_EXPRESSIONS = (
    "Mon..Fri *-*-* 13:30:00 America/New_York",
    "Mon..Fri *-*-* 16:30:00 America/New_York",
)
MINIMUM_SYSTEMD_VERSION = 255


class DailyEodSchedulerSystemdError(RuntimeError):
    """Raised when the proposed timer boundary is not exact and write-free."""


class DailyEodSchedulerSystemdCandidateV1(BaseModel):
    """Exact future user-unit bytes; this object grants no installation authority."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["daily-eod-scheduler-systemd-candidate/1.0"] = (
        CONTRACT_VERSION
    )
    config_id: str = Field(
        min_length=16,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_.:-]+$",
    )
    host: Literal["dell5820"]
    user: Literal["hui"]
    repository_root: str
    branch: Literal["main"]
    implementation_revision: str
    data_root: str
    entrypoint: str
    python_launcher: str
    python_executable: str
    installation_scope: Literal["user"]
    user_unit_root: str
    service_unit_name: Literal["whalpha-daily-eod-wake-review.service"]
    timer_unit_name: Literal["whalpha-daily-eod-wake-review.timer"]
    calendar_expressions: tuple[str, ...]
    persistent: Literal[True]
    linger_required: Literal[True]
    wake_mode: Literal["read_only_plan"]
    activation_candidate_enabled: bool
    coordinator_invocation_enabled: Literal[False]
    authorized_capabilities_enabled: Literal[False]
    publication_authorized: Literal[False]
    deployment_authorized: Literal[False]
    service_unit_sha256: str
    timer_unit_sha256: str
    config_content_sha256: str

    @model_validator(mode="after")
    def validate_exact_candidate(self) -> "DailyEodSchedulerSystemdCandidateV1":
        repository = Path(self.repository_root)
        data_root = Path(self.data_root)
        entrypoint = Path(self.entrypoint)
        python_launcher = Path(self.python_launcher)
        python_executable = Path(self.python_executable)
        unit_root = Path(self.user_unit_root)
        if (
            not repository.is_absolute()
            or data_root != APPROVED_CANONICAL_DATA_ROOT
            or entrypoint
            != repository / "scripts/admin/plan-daily-eod-scheduler.sh"
            or python_launcher != repository / ".venv/bin/python"
            or not python_executable.is_absolute()
            or unit_root != Path("/home/hui/.config/systemd/user")
            or not _is_safe_unit_path(repository)
            or not _is_safe_unit_path(entrypoint)
            or not _is_safe_unit_path(python_launcher)
            or not _is_safe_unit_path(python_executable)
            or not _is_revision(self.implementation_revision)
            or self.calendar_expressions != CALENDAR_EXPRESSIONS
            or not _is_fingerprint(self.service_unit_sha256)
            or not _is_fingerprint(self.timer_unit_sha256)
            or not _is_fingerprint(self.config_content_sha256)
        ):
            raise ValueError("scheduler systemd candidate boundary is invalid")
        if self.service_unit_sha256 != hashlib.sha256(
            render_service_unit(self).encode("utf-8")
        ).hexdigest() or self.timer_unit_sha256 != hashlib.sha256(
            render_timer_unit(self).encode("utf-8")
        ).hexdigest():
            raise ValueError("scheduler systemd unit content SHA mismatch")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"config_content_sha256"})
        )
        if self.config_content_sha256 != expected:
            raise ValueError("scheduler systemd candidate content fingerprint mismatch")
        return self


@dataclass(frozen=True, slots=True)
class DailyEodSchedulerSystemdReview:
    status: str
    candidate_config: dict[str, object]
    service_unit: str
    timer_unit: str
    service_unit_sha256: str
    timer_unit_sha256: str
    systemd_version: int
    user_manager_running: bool
    linger_enabled: bool
    installation_prerequisites_satisfied: bool
    activation_candidate_enabled: bool
    installation_performed: bool
    activation_performed: bool
    coordinator_invocation_count: int
    credential_access_count: int
    external_request_count: int
    filesystem_write_count: int
    production_write_count: int
    publication_authorized: bool
    deployment_authorized: bool
    reason_code: str
    contract_version: str = REVIEW_CONTRACT_VERSION
    logical_content_fingerprint: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def build_scheduler_systemd_candidate(
    *,
    config_id: str,
    repository_root: Path,
    implementation_revision: str,
    python_executable: Path,
    activation_candidate_enabled: bool = False,
) -> DailyEodSchedulerSystemdCandidateV1:
    base: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "config_id": config_id,
        "host": "dell5820",
        "user": "hui",
        "repository_root": str(repository_root),
        "branch": "main",
        "implementation_revision": implementation_revision,
        "data_root": str(APPROVED_CANONICAL_DATA_ROOT),
        "entrypoint": str(
            repository_root / "scripts/admin/plan-daily-eod-scheduler.sh"
        ),
        "python_launcher": str(repository_root / ".venv/bin/python"),
        "python_executable": str(python_executable),
        "installation_scope": "user",
        "user_unit_root": "/home/hui/.config/systemd/user",
        "service_unit_name": SERVICE_UNIT_NAME,
        "timer_unit_name": TIMER_UNIT_NAME,
        "calendar_expressions": CALENDAR_EXPRESSIONS,
        "persistent": True,
        "linger_required": True,
        "wake_mode": "read_only_plan",
        "activation_candidate_enabled": activation_candidate_enabled,
        "coordinator_invocation_enabled": False,
        "authorized_capabilities_enabled": False,
        "publication_authorized": False,
        "deployment_authorized": False,
    }
    service_sha = hashlib.sha256(_service_unit(base).encode("utf-8")).hexdigest()
    timer_sha = hashlib.sha256(_timer_unit(base).encode("utf-8")).hexdigest()
    with_unit_shas = {
        **base,
        "service_unit_sha256": service_sha,
        "timer_unit_sha256": timer_sha,
    }
    return DailyEodSchedulerSystemdCandidateV1.model_validate(
        {
            **with_unit_shas,
            "config_content_sha256": _fingerprint(with_unit_shas),
        }
    )


def render_service_unit(candidate: DailyEodSchedulerSystemdCandidateV1) -> str:
    return _service_unit(candidate.model_dump(mode="json"))


def render_timer_unit(candidate: DailyEodSchedulerSystemdCandidateV1) -> str:
    return _timer_unit(candidate.model_dump(mode="json"))


def review_scheduler_systemd_candidate(
    *,
    config_id: str,
    repository_root: Path,
    activation_candidate_enabled: bool = False,
    hostname_reader: Callable[[], str] = socket.gethostname,
    user_reader: Callable[[], str] = lambda: pwd.getpwuid(os.geteuid()).pw_name,
    command_runner: CommandRunner = subprocess.run,
) -> DailyEodSchedulerSystemdReview:
    """Review exact unit bytes and live prerequisites without writing or installing."""

    if (
        hostname_reader().split(".", 1)[0].strip().lower() != "dell5820"
        or user_reader() != "hui"
        or not repository_root.is_absolute()
        or repository_root.is_symlink()
        or repository_root.resolve() != repository_root
        or not repository_root.is_dir()
    ):
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd review requires the Dell hui source repository"
        )
    revision, branch, status = _repository_state(
        repository_root,
        command_runner=command_runner,
    )
    if not _is_revision(revision) or branch != "main" or status:
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd review requires clean pinned main"
        )
    entrypoint = repository_root / "scripts/admin/plan-daily-eod-scheduler.sh"
    python_launcher = repository_root / ".venv/bin/python"
    python_executable = Path(sys.executable).resolve()
    if (
        entrypoint.is_symlink()
        or not entrypoint.is_file()
        or not entrypoint.stat().st_mode & 0o111
        or not python_launcher.is_file()
        or not os.access(python_launcher, os.X_OK)
        or not python_executable.is_file()
        or not os.access(python_executable, os.X_OK)
        or python_launcher.resolve() != python_executable
    ):
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd entrypoint custody is invalid"
        )
    version = _systemd_version(command_runner=command_runner)
    manager_running = _user_manager_running(command_runner=command_runner)
    linger = _linger_enabled(command_runner=command_runner)
    if version < MINIMUM_SYSTEMD_VERSION or not manager_running:
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd runtime prerequisites are unavailable"
        )
    for expression in CALENDAR_EXPRESSIONS:
        _verify_calendar(expression, command_runner=command_runner)
    candidate = build_scheduler_systemd_candidate(
        config_id=config_id,
        repository_root=repository_root,
        implementation_revision=revision,
        python_executable=python_executable,
        activation_candidate_enabled=activation_candidate_enabled,
    )
    service = render_service_unit(candidate)
    timer = render_timer_unit(candidate)
    prerequisites = manager_running and linger
    reason = (
        "disabled_candidate_ready_for_review"
        if not activation_candidate_enabled
        else (
            "enabled_candidate_requires_linger_and_separate_installation_review"
            if not prerequisites
            else "enabled_candidate_requires_separate_installation_review"
        )
    )
    base: dict[str, object] = {
        "status": (
            "review_ready_prerequisite_missing"
            if activation_candidate_enabled and not prerequisites
            else "review_ready"
        ),
        "candidate_config": candidate.model_dump(mode="json"),
        "service_unit": service,
        "timer_unit": timer,
        "service_unit_sha256": hashlib.sha256(service.encode("utf-8")).hexdigest(),
        "timer_unit_sha256": hashlib.sha256(timer.encode("utf-8")).hexdigest(),
        "systemd_version": version,
        "user_manager_running": manager_running,
        "linger_enabled": linger,
        "installation_prerequisites_satisfied": prerequisites,
        "activation_candidate_enabled": activation_candidate_enabled,
        "installation_performed": False,
        "activation_performed": False,
        "coordinator_invocation_count": 0,
        "credential_access_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
        "deployment_authorized": False,
        "reason_code": reason,
        "contract_version": REVIEW_CONTRACT_VERSION,
    }
    return DailyEodSchedulerSystemdReview(
        **base,
        logical_content_fingerprint=_fingerprint(base),
    )


def candidate_from_review(
    review: DailyEodSchedulerSystemdReview,
) -> DailyEodSchedulerSystemdCandidateV1:
    payload = review.as_dict()
    fingerprint = payload.pop("logical_content_fingerprint", None)
    if (
        fingerprint != _fingerprint(payload)
        or review.contract_version != REVIEW_CONTRACT_VERSION
        or review.installation_performed
        or review.activation_performed
        or review.coordinator_invocation_count != 0
        or review.credential_access_count != 0
        or review.external_request_count != 0
        or review.filesystem_write_count != 0
        or review.production_write_count != 0
        or review.publication_authorized
        or review.deployment_authorized
    ):
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd review boundary is invalid"
        )
    try:
        candidate = DailyEodSchedulerSystemdCandidateV1.model_validate(
            review.candidate_config
        )
    except ValueError as exc:
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd candidate config is invalid"
        ) from exc
    expected_reason = (
        "disabled_candidate_ready_for_review"
        if not candidate.activation_candidate_enabled
        else (
            "enabled_candidate_requires_linger_and_separate_installation_review"
            if not review.installation_prerequisites_satisfied
            else "enabled_candidate_requires_separate_installation_review"
        )
    )
    expected_status = (
        "review_ready_prerequisite_missing"
        if candidate.activation_candidate_enabled
        and not review.installation_prerequisites_satisfied
        else "review_ready"
    )
    if (
        render_service_unit(candidate) != review.service_unit
        or render_timer_unit(candidate) != review.timer_unit
        or candidate.service_unit_sha256 != review.service_unit_sha256
        or candidate.timer_unit_sha256 != review.timer_unit_sha256
        or candidate.activation_candidate_enabled
        != review.activation_candidate_enabled
        or review.installation_prerequisites_satisfied
        != (review.user_manager_running and review.linger_enabled)
        or review.systemd_version < MINIMUM_SYSTEMD_VERSION
        or not review.user_manager_running
        or review.status != expected_status
        or review.reason_code != expected_reason
    ):
        raise DailyEodSchedulerSystemdError(
            "scheduler systemd review identity mismatch"
        )
    return candidate


def _service_unit(values: dict[str, object]) -> str:
    return "\n".join(
        (
            "[Unit]",
            "Description=WH Alpha read-only daily EOD wake review",
            "After=local-fs.target",
            f"ConditionPathIsDirectory={values['repository_root']}",
            "",
            "[Service]",
            "Type=oneshot",
            f"WorkingDirectory={values['repository_root']}",
            "Environment=PATH=/usr/bin:/bin",
            "Environment=PYTHONPATH=",
            "Environment=PYTHONHOME=",
            f"Environment=TIP_PYTHON_BIN={values['python_launcher']}",
            "ExecStart="
            f"{values['entrypoint']} --data-root {values['data_root']} "
            "--verify-dell-runtime "
            f"--expected-revision {values['implementation_revision']} "
            f"--expected-python-executable {values['python_executable']}",
            "Environment=PYTHONDONTWRITEBYTECODE=1",
            "UMask=0077",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectHome=read-only",
            "RestrictAddressFamilies=AF_UNIX",
            "LockPersonality=true",
            "RestrictSUIDSGID=true",
            "TimeoutStartSec=120",
            "StandardOutput=journal",
            "StandardError=journal",
            "",
        )
    )


def _timer_unit(values: dict[str, object]) -> str:
    lines = [
        "[Unit]",
        "Description=WH Alpha read-only daily EOD wake review timer",
        "",
        "[Timer]",
    ]
    lines.extend(
        f"OnCalendar={expression}" for expression in values["calendar_expressions"]
    )
    lines.extend(
        (
            "Persistent=true",
            "AccuracySec=1min",
            "RandomizedDelaySec=0",
            "WakeSystem=false",
            f"Unit={values['service_unit_name']}",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        )
    )
    return "\n".join(lines)


def _repository_state(
    root: Path,
    *,
    command_runner: CommandRunner,
) -> tuple[str, str, str]:
    commands = (
        ["/usr/bin/git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD"],
        [
            "/usr/bin/git",
            "--no-optional-locks",
            "-C",
            str(root),
            "branch",
            "--show-current",
        ],
        [
            "/usr/bin/git",
            "--no-optional-locks",
            "-C",
            str(root),
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
        raise DailyEodSchedulerSystemdError(
            "scheduler repository identity is unavailable"
        ) from exc
    return tuple(result.stdout.strip() for result in results)  # type: ignore[return-value]


def _systemd_version(*, command_runner: CommandRunner) -> int:
    try:
        first_line = command_runner(
            ["/usr/bin/systemd", "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()[0]
        return int(first_line.split()[1])
    except (IndexError, OSError, subprocess.SubprocessError, ValueError) as exc:
        raise DailyEodSchedulerSystemdError("systemd version is unavailable") from exc


def _user_manager_running(*, command_runner: CommandRunner) -> bool:
    try:
        value = command_runner(
            ["/usr/bin/systemctl", "--user", "is-system-running"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise DailyEodSchedulerSystemdError(
            "user systemd manager is unavailable"
        ) from exc
    return value == "running"


def _linger_enabled(*, command_runner: CommandRunner) -> bool:
    try:
        value = command_runner(
            ["/usr/bin/loginctl", "show-user", "hui", "-p", "Linger", "--value"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise DailyEodSchedulerSystemdError("linger state is unavailable") from exc
    if value not in {"yes", "no"}:
        raise DailyEodSchedulerSystemdError("linger state is invalid")
    return value == "yes"


def _verify_calendar(expression: str, *, command_runner: CommandRunner) -> None:
    try:
        command_runner(
            [
                "/usr/bin/systemd-analyze",
                "calendar",
                expression,
                "--iterations=1",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DailyEodSchedulerSystemdError(
            "scheduler calendar expression is invalid"
        ) from exc


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


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


def _is_safe_unit_path(path: Path) -> bool:
    return path.is_absolute() and all(
        character.isalnum() or character in "/._-" for character in str(path)
    )
