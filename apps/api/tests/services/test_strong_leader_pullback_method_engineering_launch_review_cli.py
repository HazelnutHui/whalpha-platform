from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tip_api.services import strong_leader_pullback_method_engineering_launch_review_cli as cli


def _args() -> list[str]:
    return [
        "--pre-research-review", "/private/pre/review=v2",
        "--pre-research-review-custody-root", "/private/pre",
        "--output-root", "/private/launch/review=v1",
        "--output-custody-root", "/private/launch",
        "--reviewed-at", "2026-09-14T12:00:00Z",
        "--execute",
    ]


def test_cli_reports_narrow_launch_boundary(monkeypatch, capsys) -> None:
    report = SimpleNamespace(
        contract_version=cli.service.CONTRACT_VERSION,
        decision_status="ready_for_outcome_blind_method_engineering",
        formal_data_gate_status="rejected_data_blocked",
        signal_session_count=287,
        included_path_count=437402,
        unresolved_formal_blocker_codes=("still_blocked",),
        next_action=(
            "implement_first_strategy_and_lab_method_surface_without_opening_outcomes"
        ),
        logical_fingerprint="1" * 64,
    )
    monkeypatch.setattr(cli, "_clean_revision", lambda: "2" * 40)
    monkeypatch.setattr(
        cli.service,
        "build_strong_leader_pullback_method_engineering_launch_review",
        lambda **_: SimpleNamespace(
            report=report,
            report_sha256="3" * 64,
            status="published",
        ),
    )

    assert cli.main(_args()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision_status"] == (
        "ready_for_outcome_blind_method_engineering"
    )
    assert payload["formal_data_gate_status"] == "rejected_data_blocked"
    assert payload["method_engineering_authorized"] is True
    assert payload["true_return_labels_authorized"] is False
    assert payload["performance_claims_authorized"] is False
    assert payload["canonical_data_write_count"] == 0
    assert payload["network_request_count"] == 0


def test_cli_fails_closed(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_clean_revision", lambda: "2" * 40)

    def stop(**_: Path) -> object:
        raise cli.service.StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "stopped"
        )

    monkeypatch.setattr(
        cli.service,
        "build_strong_leader_pullback_method_engineering_launch_review",
        stop,
    )

    assert cli.main(_args()) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "stopped"
    assert payload["method_engineering_authorized"] is False
    assert payload["true_return_labels_authorized"] is False
    assert payload["canonical_data_write_count"] == 0
    assert payload["network_request_count"] == 0
