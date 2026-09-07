from __future__ import annotations

import json
from types import SimpleNamespace

from tip_api.services import universe_membership_apply_plan_cli as cli


def test_cli_reports_bounded_no_write_plan(monkeypatch, capsys) -> None:
    plan = SimpleNamespace(
        status="ready_for_separate_review",
        logical_fingerprint="a" * 64,
        expected_current_state_fingerprint="b" * 64,
        publication=SimpleNamespace(
            session_date=SimpleNamespace(isoformat=lambda: "2026-09-04"),
            membership_logical_fingerprint="c" * 64,
            knowledge_time_assessment=SimpleNamespace(logical_fingerprint="d" * 64),
            point_in_time_eligibility=SimpleNamespace(value="signal_eligible"),
        ),
        inventory_change_file_count=3,
        inventory_change_bytes=100,
        target_membership_partition="/data/membership",
        target_publication_partition="/data/publication",
        apply_authorized=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
    )
    monkeypatch.setattr(
        cli,
        "build_universe_membership_apply_plan",
        lambda **_: SimpleNamespace(
            plan=plan,
            plan_path="/tmp/plan.json",
            plan_sha256="e" * 64,
        ),
    )

    result = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--candidate-root",
            "/tmp/candidate",
            "--candidate-membership-partition",
            "/tmp/candidate/partition",
            "--assessed-at",
            "2026-09-06T14:00:00+00:00",
            "--created-at",
            "2026-09-06T14:10:00+00:00",
            "--plan-path",
            "/tmp/plan.json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["status"] == "ready_for_separate_review"
    assert payload["inventory_change_file_count"] == 3
    assert payload["apply_authorized"] is False
    assert payload["canonical_data_write_count"] == 0


def test_cli_rejection_does_not_echo_failure_detail(monkeypatch, capsys) -> None:
    def rejected(**_):
        raise RuntimeError("sensitive failure detail")

    monkeypatch.setattr(cli, "build_universe_membership_apply_plan", rejected)
    result = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--candidate-root",
            "/tmp/candidate",
            "--candidate-membership-partition",
            "/tmp/candidate/partition",
            "--assessed-at",
            "2026-09-06T14:00:00+00:00",
            "--created-at",
            "2026-09-06T14:10:00+00:00",
            "--plan-path",
            "/tmp/plan.json",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert result == 1
    assert payload["status"] == "rejected"
    assert payload["error_type"] == "RuntimeError"
    assert "sensitive" not in output
