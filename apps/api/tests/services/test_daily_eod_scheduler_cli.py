from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_scheduler_cli as cli


CHECKED_AT = "2026-08-29T12:00:00+00:00"
DATA_ROOT = Path("/data/trading-intelligence-platform")


def test_default_cli_reviews_disabled_candidate_without_writes(
    monkeypatch,
    capsys,
) -> None:
    class Repository:
        def __init__(self, root: Path):
            assert root == DATA_ROOT

        def list_session_index(self):
            return (date(2026, 8, 27), date(2026, 8, 28))

        def inspect_session(self, session_date: date):
            return SimpleNamespace(session_date=session_date)

    monkeypatch.setattr(cli, "CanonicalEodReadRepository", Repository)

    assert cli.main(["--checked-at", CHECKED_AT, "--data-root", str(DATA_ROOT)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "up_to_date"
    assert payload["scheduler_candidate_enabled"] is False
    assert payload["scheduler_installation_performed"] is False
    assert "scheduler_installed" not in payload
    assert payload["coordinator_invocation_count"] == 0
    assert payload["credential_access_count"] == 0
    assert payload["external_request_count"] == 0
    assert payload["filesystem_write_count"] == 0
    assert payload["production_write_count"] == 0
    assert payload["checked_at_source"] == "explicit_argument"


def test_cli_uses_system_utc_clock_when_checked_at_is_omitted(
    monkeypatch,
    capsys,
) -> None:
    class Repository:
        def __init__(self, _root: Path):
            pass

        def list_session_index(self):
            return (date(2026, 8, 27), date(2026, 8, 28))

        def inspect_session(self, session_date: date):
            return SimpleNamespace(session_date=session_date)

    monkeypatch.setattr(cli, "CanonicalEodReadRepository", Repository)
    monkeypatch.setattr(
        cli,
        "_utc_now",
        lambda: datetime(2026, 8, 29, 12, tzinfo=UTC),
    )

    assert cli.main(["--data-root", str(DATA_ROOT)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["checked_at"] == CHECKED_AT
    assert payload["checked_at_source"] == "system_utc_clock"


def test_enabled_review_changes_candidate_only(monkeypatch, capsys) -> None:
    class Repository:
        def __init__(self, _root: Path):
            pass

        def list_session_index(self):
            return (date(2026, 8, 27),)

        def inspect_session(self, session_date: date):
            return SimpleNamespace(session_date=session_date)

    monkeypatch.setattr(cli, "CanonicalEodReadRepository", Repository)

    assert (
        cli.main(
            [
                "--checked-at",
                "2026-08-28T21:00:00+00:00",
                "--data-root",
                str(DATA_ROOT),
                "--review-enabled-candidate",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_action"] == "invoke_one_transition"
    assert payload["scheduler_candidate_enabled"] is True
    assert payload["scheduler_installation_performed"] is False
    assert payload["coordinator_invocation_count"] == 0


def test_cli_fails_closed_on_unavailable_canonical_state(monkeypatch, capsys) -> None:
    class Repository:
        def __init__(self, _root: Path):
            pass

        def list_session_index(self):
            return ()

        def inspect_session(self, _session_date: date):
            raise AssertionError("empty index must not inspect a session")

    monkeypatch.setattr(cli, "CanonicalEodReadRepository", Repository)

    assert cli.main(["--checked-at", CHECKED_AT, "--data-root", str(DATA_ROOT)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["scheduler_installation_performed"] is False
    assert payload["external_request_count"] == 0
    assert payload["production_write_count"] == 0


def test_cli_fails_closed_when_latest_formal_read_differs_from_index(
    monkeypatch,
    capsys,
) -> None:
    class Repository:
        def __init__(self, _root: Path):
            pass

        def list_session_index(self):
            return (date(2026, 8, 28),)

        def inspect_session(self, _session_date: date):
            return SimpleNamespace(session_date=date(2026, 8, 27))

    monkeypatch.setattr(cli, "CanonicalEodReadRepository", Repository)

    assert cli.main(["--checked-at", CHECKED_AT, "--data-root", str(DATA_ROOT)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["scheduler_installation_performed"] is False
    assert payload["coordinator_invocation_count"] == 0


def test_cli_rejects_relative_data_root() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--checked-at", CHECKED_AT, "--data-root", "relative"])


def test_runtime_verification_requires_paired_exact_revision() -> None:
    revision = "a" * 40
    python = str(Path(sys.executable).resolve())
    with pytest.raises(SystemExit):
        cli.main(["--data-root", str(DATA_ROOT), "--verify-dell-runtime"])
    with pytest.raises(SystemExit):
        cli.main(
            [
                "--data-root",
                str(DATA_ROOT),
                "--expected-revision",
                "not-a-revision",
            ]
        )
    with pytest.raises(SystemExit):
        cli.main(
            ["--data-root", str(DATA_ROOT), "--expected-revision", revision]
        )
    with pytest.raises(SystemExit):
        cli.main(
            ["--data-root", str(DATA_ROOT), "--expected-python-executable", python]
        )


def test_runtime_verification_requires_clean_dell_main(monkeypatch, tmp_path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    monkeypatch.setattr(cli, "_source_repository_root", lambda: repository)
    monkeypatch.setattr(cli.socket, "gethostname", lambda: "dell5820.example")
    monkeypatch.setattr(
        cli.pwd,
        "getpwuid",
        lambda _uid: SimpleNamespace(pw_name="hui"),
    )
    revision = "a" * 40

    def runner(command, **_kwargs):
        output = revision if "rev-parse" in command else (
            "main" if "branch" in command else ""
        )
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    cli._verify_dell_runtime(
        expected_revision=revision,
        expected_python_executable=Path(sys.executable).resolve(),
        command_runner=runner,
    )
    with pytest.raises(cli.DailyEodSchedulerError, match="host identity"):
        cli._verify_dell_runtime(
            expected_revision=revision,
            expected_python_executable=Path("/bin/false"),
            command_runner=runner,
        )

    def dirty_runner(command, **_kwargs):
        output = revision if "rev-parse" in command else (
            "main" if "branch" in command else " M changed.py"
        )
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    with pytest.raises(cli.DailyEodSchedulerError, match="clean pinned main"):
        cli._verify_dell_runtime(
            expected_revision=revision,
            expected_python_executable=Path(sys.executable).resolve(),
            command_runner=dirty_runner,
        )
