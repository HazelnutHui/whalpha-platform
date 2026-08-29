from __future__ import annotations

import json
from datetime import date
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
    assert payload["scheduler_installed"] is False
    assert payload["coordinator_invocation_count"] == 0
    assert payload["credential_access_count"] == 0
    assert payload["external_request_count"] == 0
    assert payload["filesystem_write_count"] == 0
    assert payload["production_write_count"] == 0


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
    assert payload["scheduler_installed"] is False
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
    assert payload["scheduler_installed"] is False
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
    assert payload["scheduler_installed"] is False
    assert payload["coordinator_invocation_count"] == 0


def test_cli_rejects_relative_data_root() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--checked-at", CHECKED_AT, "--data-root", "relative"])
