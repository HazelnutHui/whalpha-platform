from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from tip_api.services import daily_universe_membership_sidecar_cli as cli
from tip_api.services.daily_universe_membership_sidecar import (
    MembershipSidecarStatus,
)


ARGS = [
    "--checked-at",
    "2026-09-09T08:30:00+00:00",
    "--as-of-session",
    "2026-09-08",
    "--catalog-as-of-date",
    "2026-08-14",
    "--data-root",
    "/data/trading-intelligence-platform",
    "--workspace-root",
    "/home/hui/.local/share/trading-intelligence-platform/daily-eod",
    "--repository-root",
    "/home/hui/projects/trading-intelligence-platform",
]


def _layout() -> object:
    return SimpleNamespace(
        universe_membership_candidate_root=Path(
            "/tmp/universe-membership-candidate"
        ),
        universe_membership_apply_plan=Path(
            "/tmp/universe-membership-plan.json"
        ),
        as_automation_paths=lambda: object(),
    )


def test_cli_reports_non_blocking_sidecar_plan(monkeypatch, capsys) -> None:
    primary = object()
    plan = SimpleNamespace(
        status=MembershipSidecarStatus.READY,
        as_dict=lambda: {
            "status": "ready",
            "next_action": "prepare_candidate",
            "website_pipeline_blocked": False,
            "apply_authorized": False,
            "scheduler_enabled": False,
            "external_request_count": 0,
            "production_write_count": 0,
        },
    )
    monkeypatch.setattr(
        cli,
        "derive_daily_eod_workspace_layout",
        lambda **_: _layout(),
    )
    monkeypatch.setattr(cli, "plan_daily_eod_automation", lambda **_: primary)

    def sidecar(**values):
        assert values["primary_automation_plan"] is primary
        assert values["target_session"] == date(2026, 9, 8)
        return plan

    monkeypatch.setattr(cli, "plan_daily_universe_membership_sidecar", sidecar)

    assert cli.main(ARGS) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_action"] == "prepare_candidate"
    assert payload["website_pipeline_blocked"] is False
    assert payload["checked_at_source"] == "explicit_argument"


def test_cli_fails_closed_without_error_body(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "derive_daily_eod_workspace_layout",
        lambda **_: (_ for _ in ()).throw(RuntimeError("sensitive detail")),
    )

    assert cli.main(ARGS) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["website_pipeline_blocked"] is False
    assert payload["production_write_count"] == 0
    assert "sensitive detail" not in str(payload)
