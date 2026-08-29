from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_scheduler_systemd as systemd


REVISION = "a" * 40


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    entrypoint = root / "scripts/admin/plan-daily-eod-scheduler.sh"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    entrypoint.chmod(0o755)
    python_launcher = root / ".venv/bin/python"
    python_launcher.parent.mkdir(parents=True)
    python_launcher.symlink_to(Path(sys.executable).resolve())
    return root


def runner(*, linger: str = "no", status: str = ""):
    def run(command, **_kwargs):
        if command[0] == "/usr/bin/git":
            if "rev-parse" in command:
                output = REVISION
            elif "branch" in command:
                output = "main"
            else:
                output = status
        elif command[:2] == ["/usr/bin/systemd", "--version"]:
            output = "systemd 255 (test)\n"
        elif command[:3] == [
            "/usr/bin/systemctl",
            "--user",
            "is-system-running",
        ]:
            output = "running\n"
        elif command[0] == "/usr/bin/loginctl":
            output = linger + "\n"
        elif command[:2] == ["/usr/bin/systemd-analyze", "calendar"]:
            output = "Normalized form: test\n"
        else:  # pragma: no cover - guards the exact command set
            raise AssertionError(command)
        return SimpleNamespace(stdout=output)

    return run


def test_candidate_is_exact_read_only_and_default_disabled(tmp_path) -> None:
    root = repository(tmp_path)
    candidate = systemd.build_scheduler_systemd_candidate(
        config_id="dell-systemd-candidate-1",
        repository_root=root,
        implementation_revision=REVISION,
        python_executable=Path(sys.executable).resolve(),
    )
    service = systemd.render_service_unit(candidate)
    timer = systemd.render_timer_unit(candidate)

    assert candidate.activation_candidate_enabled is False
    assert candidate.wake_mode == "read_only_plan"
    assert candidate.coordinator_invocation_enabled is False
    assert candidate.authorized_capabilities_enabled is False
    assert "--verify-dell-runtime" in service
    assert f"--expected-revision {REVISION}" in service
    assert "Environment=PYTHONPATH=" in service
    assert f"Environment=TIP_PYTHON_BIN={root}/.venv/bin/python" in service
    assert (
        f"--expected-python-executable {Path(sys.executable).resolve()}" in service
    )
    assert "--review-enabled-candidate" not in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectSystem=strict" in service
    assert "ProtectHome=read-only" in service
    assert "RestrictAddressFamilies=AF_UNIX" in service
    assert "PrivateNetwork=" not in service
    assert "PrivateDevices=" not in service
    assert "CapabilityBoundingSet=" not in service
    assert "OnCalendar=Mon..Fri *-*-* 13:30:00 America/New_York" in timer
    assert "OnCalendar=Mon..Fri *-*-* 16:30:00 America/New_York" in timer
    assert "Persistent=true" in timer


@pytest.mark.skipif(
    shutil.which("systemd-analyze") is None,
    reason="systemd-analyze is unavailable",
)
def test_rendered_units_pass_systemd_parser(tmp_path) -> None:
    candidate = systemd.build_scheduler_systemd_candidate(
        config_id="dell-systemd-candidate-parser",
        repository_root=repository(tmp_path),
        implementation_revision=REVISION,
        python_executable=Path(sys.executable).resolve(),
    )
    service_path = tmp_path / systemd.SERVICE_UNIT_NAME
    timer_path = tmp_path / systemd.TIMER_UNIT_NAME
    service_path.write_text(systemd.render_service_unit(candidate), encoding="utf-8")
    timer_path.write_text(systemd.render_timer_unit(candidate), encoding="utf-8")

    result = subprocess.run(
        [
            "systemd-analyze",
            "--user",
            "verify",
            str(service_path),
            str(timer_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_enabled_review_reports_missing_linger_without_installing(tmp_path) -> None:
    root = repository(tmp_path)
    before = inventory(tmp_path)
    review = systemd.review_scheduler_systemd_candidate(
        config_id="dell-systemd-candidate-2",
        repository_root=root,
        activation_candidate_enabled=True,
        hostname_reader=lambda: "dell5820.example",
        user_reader=lambda: "hui",
        command_runner=runner(linger="no"),
    )
    candidate = systemd.candidate_from_review(review)

    assert candidate.activation_candidate_enabled is True
    assert review.status == "review_ready_prerequisite_missing"
    assert review.user_manager_running is True
    assert review.linger_enabled is False
    assert review.installation_prerequisites_satisfied is False
    assert review.installation_performed is False
    assert review.activation_performed is False
    assert "scheduler_installed" not in review.as_dict()
    assert review.coordinator_invocation_count == 0
    assert review.credential_access_count == 0
    assert review.external_request_count == 0
    assert review.filesystem_write_count == 0
    assert review.production_write_count == 0
    assert inventory(tmp_path) == before


def test_linger_ready_candidate_still_requires_separate_installation(tmp_path) -> None:
    review = systemd.review_scheduler_systemd_candidate(
        config_id="dell-systemd-candidate-3",
        repository_root=repository(tmp_path),
        activation_candidate_enabled=True,
        hostname_reader=lambda: "dell5820",
        user_reader=lambda: "hui",
        command_runner=runner(linger="yes"),
    )

    assert review.status == "review_ready"
    assert review.installation_prerequisites_satisfied is True
    assert review.installation_performed is False
    assert review.reason_code == (
        "enabled_candidate_requires_separate_installation_review"
    )


def test_review_rejects_dirty_tree_or_wrong_host(tmp_path) -> None:
    root = repository(tmp_path)
    with pytest.raises(systemd.DailyEodSchedulerSystemdError, match="clean pinned"):
        systemd.review_scheduler_systemd_candidate(
            config_id="dell-systemd-candidate-4",
            repository_root=root,
            hostname_reader=lambda: "dell5820",
            user_reader=lambda: "hui",
            command_runner=runner(status=" M changed.py"),
        )
    with pytest.raises(systemd.DailyEodSchedulerSystemdError, match="Dell hui"):
        systemd.review_scheduler_systemd_candidate(
            config_id="dell-systemd-candidate-5",
            repository_root=root,
            hostname_reader=lambda: "windows",
            user_reader=lambda: "hui",
            command_runner=lambda *_args, **_kwargs: pytest.fail("must not run"),
        )

    python_launcher = root / ".venv/bin/python"
    python_launcher.unlink()
    python_launcher.symlink_to(Path("/bin/false"))
    with pytest.raises(
        systemd.DailyEodSchedulerSystemdError,
        match="entrypoint custody",
    ):
        systemd.review_scheduler_systemd_candidate(
            config_id="dell-systemd-candidate-7",
            repository_root=root,
            hostname_reader=lambda: "dell5820",
            user_reader=lambda: "hui",
            command_runner=runner(),
        )


def test_review_tamper_is_rejected(tmp_path) -> None:
    review = systemd.review_scheduler_systemd_candidate(
        config_id="dell-systemd-candidate-6",
        repository_root=repository(tmp_path),
        hostname_reader=lambda: "dell5820",
        user_reader=lambda: "hui",
        command_runner=runner(),
    )
    with pytest.raises(systemd.DailyEodSchedulerSystemdError, match="boundary"):
        systemd.candidate_from_review(replace(review, installation_performed=True))

    changed = replace(
        review,
        service_unit=review.service_unit + "# changed\n",
        logical_content_fingerprint="",
    )
    payload = changed.as_dict()
    payload.pop("logical_content_fingerprint")
    changed = replace(
        changed,
        logical_content_fingerprint=systemd._fingerprint(payload),
    )
    with pytest.raises(systemd.DailyEodSchedulerSystemdError, match="identity"):
        systemd.candidate_from_review(changed)


def inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }
