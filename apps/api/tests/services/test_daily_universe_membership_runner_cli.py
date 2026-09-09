from __future__ import annotations

import json
import socket
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_universe_membership_runner as runner
from tip_api.services import daily_universe_membership_runner_cli as cli


SESSION = date(2026, 9, 8)
STARTED = datetime(2026, 9, 9, 8, 30, tzinfo=UTC)


def _arguments(*extra: str) -> list[str]:
    return [
        "--as-of-session",
        SESSION.isoformat(),
        "--catalog-as-of-date",
        "2026-08-14",
        "--data-root",
        "/data/trading-intelligence-platform",
        "--workspace-root",
        "/owner/work/daily-eod",
        "--started-at",
        STARTED.isoformat(),
        *extra,
    ]


def _layout() -> SimpleNamespace:
    return SimpleNamespace(
        universe_membership_candidate_root=Path(
            "/owner/work/daily-eod/sessions/session_date=2026-09-08/"
            "universe-membership-candidate"
        ),
        universe_membership_apply_plan=Path(
            "/owner/work/daily-eod/sessions/session_date=2026-09-08/"
            "universe-membership-plan.json"
        ),
        logical_content_fingerprint="a" * 64,
        as_automation_paths=lambda: SimpleNamespace(
            data_root=Path("/data/trading-intelligence-platform")
        ),
    )


def _result(status: runner.MembershipRunStatus) -> SimpleNamespace:
    return SimpleNamespace(
        status=status,
        as_dict=lambda: {
            "status": status.value,
            "execution_enabled": False,
            "external_request_count": 0,
            "production_write_count": 0,
            "canonical_membership_apply_performed": False,
        },
    )


def test_cli_defaults_to_review_only(monkeypatch, capsys) -> None:
    layout = _layout()
    monkeypatch.setattr(
        cli,
        "derive_daily_eod_workspace_layout",
        lambda **_: layout,
    )
    calls: list[dict[str, object]] = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return _result(runner.MembershipRunStatus.REVIEW_READY)

    monkeypatch.setattr(cli, "run_bounded_daily_universe_membership", fake_run)

    assert cli.main(_arguments()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls[0]["execute"] is False
    assert payload["status"] == "review_ready"
    assert payload["canonical_membership_apply_performed"] is False


def test_cli_requires_explicit_execute_and_preserves_action_budget(
    monkeypatch,
    capsys,
) -> None:
    layout = _layout()
    monkeypatch.setattr(
        cli,
        "derive_daily_eod_workspace_layout",
        lambda **_: layout,
    )
    calls: list[dict[str, object]] = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        result = _result(runner.MembershipRunStatus.BOUNDARY_REACHED)
        result.as_dict = lambda: {
            "status": result.status.value,
            "execution_enabled": True,
            "external_request_count": 0,
            "production_write_count": 0,
            "canonical_membership_apply_performed": False,
        }
        return result

    monkeypatch.setattr(cli, "run_bounded_daily_universe_membership", fake_run)

    assert cli.main(_arguments("--execute", "--maximum-actions", "1")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls[0]["execute"] is True
    assert calls[0]["maximum_actions"] == 1
    assert payload["execution_enabled"] is True


def test_cli_socket_guard_rejects_network() -> None:
    with cli._offline_socket_guard(), pytest.raises(RuntimeError, match="prohibited"):
        socket.create_connection(("127.0.0.1", 1))
