from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "admin" / "configure-sec-user-agent.sh"
SENTINEL = "trading-intelligence-platform fixture-contact@invalid.example"


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_script_syntax_help_and_default_dry_run() -> None:
    assert subprocess.run(["bash", "-n", str(SCRIPT)], check=False).returncode == 0
    help_result = run("--help")
    assert help_result.returncode == 0 and "--apply" in help_result.stdout
    dry_run = run()
    assert dry_run.returncode == 0
    assert "mode=dry-run" in dry_run.stdout and "apply_required=true" in dry_run.stdout


def test_unknown_and_extra_arguments_return_two() -> None:
    assert run("--unknown").returncode == 2
    assert run("--help", "extra").returncode == 2


def test_apply_rejects_non_tty_without_reading_input() -> None:
    result = run("--apply")
    assert result.returncode != 0
    assert "interactive terminal" in result.stderr


def test_environment_user_agent_is_rejected_without_exposure() -> None:
    env = dict(os.environ)
    env["TIP_SEC_USER_AGENT"] = SENTINEL
    result = run(env=env)
    assert result.returncode != 0
    assert SENTINEL not in result.stdout + result.stderr


def test_root_execution_is_rejected(tmp_path: Path) -> None:
    fake_id = tmp_path / "id"
    fake_id.write_text(
        "#!/usr/bin/env bash\nif [[ \"$1\" == \"-un\" ]]; then echo hui; else echo 0; fi\n",
        encoding="utf-8",
    )
    fake_id.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    result = run(env=env)
    assert result.returncode != 0 and "must not run as root" in result.stderr


def test_script_contains_no_real_or_fixture_contact_value() -> None:
    content = SCRIPT.read_text(encoding="utf-8")
    assert SENTINEL not in content
    assert "@invalid.example" not in content
