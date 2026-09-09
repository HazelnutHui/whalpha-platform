from __future__ import annotations

import json
import socket
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_bounded_offline_cli as cli
from tip_api.services import daily_eod_bounded_offline_runner as runner
from tip_api.services.daily_eod_automation import (
    CONTRACT_VERSION as AUTOMATION_CONTRACT_VERSION,
    DailyEodAutomationPaths,
    DailyEodAutomationPlan,
    NextAction,
    PlanStatus,
)


TARGET = date(2026, 9, 8)
STARTED = datetime(2026, 9, 9, 1, tzinfo=UTC)


def _paths() -> DailyEodAutomationPaths:
    root = Path("/owner/work/daily-eod/sessions/session_date=2026-09-08")
    prior = Path("/owner/work/daily-eod/sessions/session_date=2026-09-04")
    return DailyEodAutomationPaths(
        data_root=Path("/data/trading-intelligence-platform"),
        phase1a_audit=root / "market-regime-phase1a",
        prior_phase1b_audit=prior / "market-regime-phase1b",
        phase1b_audit=root / "market-regime-phase1b",
        prior_candidate_audit=prior / "opportunity-candidate",
        candidate_audit=root / "opportunity-candidate",
        entry_geometry_audit=root / "entry-geometry",
        phase2_audit=root / "etf-relationships",
        preview_bundle=root / "market-preview",
        strategy_channel_audit=root / "strategy-channels",
        market_intelligence_output_root=root / "market-intelligence",
        market_intelligence_approval_plan=root / "market-intelligence-plan.json",
        snapshot_output_root=root / "dashboard-snapshot",
        snapshot_approval_plan=root / "dashboard-snapshot-plan.json",
        serving_bundle_root=root / "serving-bundle",
    )


def _plan(
    *,
    status: PlanStatus = PlanStatus.READY_FOR_OFFLINE_CALCULATION,
    action: NextAction = NextAction.CALCULATE_PHASE1A,
) -> DailyEodAutomationPlan:
    logical = {
        "contract_version": AUTOMATION_CONTRACT_VERSION,
        "target_session": TARGET.isoformat(),
        "prior_session": "2026-09-04",
        "status": status.value,
        "next_action": action.value,
        "reason_codes": ["fixture"],
        "observations": [],
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return DailyEodAutomationPlan(
        contract_version=AUTOMATION_CONTRACT_VERSION,
        target_session=TARGET.isoformat(),
        prior_session="2026-09-04",
        status=status,
        next_action=action,
        reason_codes=("fixture",),
        observations=(),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=runner._fingerprint(logical),
    )


def _layout():
    paths = _paths()
    return SimpleNamespace(
        workspace_root=Path("/owner/work/daily-eod"),
        session_root=paths.phase1a_audit.parent,
        prior_session_root=paths.prior_phase1b_audit.parent,
        run_root=Path("/owner/work/daily-eod/journal"),
        panel_cache_root=Path("/owner/work/daily-eod/cache/panels"),
        candidate_work_dir=paths.candidate_audit.with_name("candidate-work"),
        logical_content_fingerprint="a" * 64,
        as_automation_paths=lambda: paths,
    )


def _arguments(*extra: str) -> list[str]:
    return [
        "--as-of-session",
        TARGET.isoformat(),
        "--data-root",
        "/data/trading-intelligence-platform",
        "--workspace-root",
        "/owner/work/daily-eod",
        "--started-at",
        STARTED.isoformat(),
        *extra,
    ]


def test_cli_defaults_to_review_only(monkeypatch, capsys) -> None:
    layout = _layout()
    monkeypatch.setattr(cli, "derive_daily_eod_workspace_layout", lambda **kwargs: layout)
    calls: list[dict[str, object]] = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return runner._result(
            status=runner.BoundedOfflineRunStatus.REVIEW_READY,
            config=kwargs["config"],
            started_at=STARTED,
            completed_at=STARTED,
            maximum_actions=kwargs["maximum_actions"],
            maximum_elapsed_seconds=kwargs["maximum_elapsed_seconds"],
            evidence=(),
            final_plan=_plan(),
            reasons=("explicit_offline_execution_not_enabled",),
            execute=False,
        )

    monkeypatch.setattr(cli, "run_bounded_daily_eod_offline", fake_run)

    assert cli.main(_arguments()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls[0]["execute"] is False
    assert payload["status"] == "review_ready"
    assert payload["external_request_count"] == 0
    assert payload["production_write_count"] == 0


def test_cli_execute_is_explicit_and_preserves_budget(monkeypatch, capsys) -> None:
    layout = _layout()
    monkeypatch.setattr(cli, "derive_daily_eod_workspace_layout", lambda **kwargs: layout)
    monkeypatch.setattr(cli, "_validate_existing_workspace", lambda value: None)
    calls: list[dict[str, object]] = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return runner._result(
            status=runner.BoundedOfflineRunStatus.BOUNDARY_REACHED,
            config=kwargs["config"],
            started_at=STARTED,
            completed_at=STARTED,
            maximum_actions=kwargs["maximum_actions"],
            maximum_elapsed_seconds=kwargs["maximum_elapsed_seconds"],
            evidence=(),
            final_plan=_plan(
                status=PlanStatus.ANALYTICS_READY,
                action=NextAction.REVIEW_PUBLICATION,
            ),
            reasons=("fixture_boundary",),
            execute=True,
        )

    monkeypatch.setattr(cli, "run_bounded_daily_eod_offline", fake_run)

    assert cli.main(_arguments("--execute", "--maximum-actions", "3")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls[0]["execute"] is True
    assert calls[0]["maximum_actions"] == 3
    assert payload["execution_enabled"] is True


def test_offline_socket_guard_rejects_network() -> None:
    with cli._offline_socket_guard(), pytest.raises(RuntimeError, match="prohibited"):
        socket.create_connection(("127.0.0.1", 1))
