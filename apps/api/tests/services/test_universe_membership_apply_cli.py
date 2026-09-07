from __future__ import annotations

import json

from tip_api.services import universe_membership_apply_cli as cli
from tip_api.services.universe_membership_apply import (
    UniverseMembershipApplyResult,
)


def test_apply_cli_reports_exact_result(monkeypatch, capsys) -> None:
    result = UniverseMembershipApplyResult(
        status="applied",
        plan_sha256="a" * 64,
        plan_logical_fingerprint="b" * 64,
        expected_current_state_fingerprint="c" * 64,
        post_state_fingerprint="d" * 64,
        membership_partition_published=True,
        membership_partition_reused=False,
        publication_marker_published=True,
        publication_marker_reused=False,
        published_file_count=3,
        published_bytes=100,
        formal_reread_record_count=1,
        publication_fingerprint="e" * 64,
        publication_sha256="f" * 64,
        external_request_count=0,
        overwritten_partition_count=0,
        deleted_partition_count=0,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
    )
    monkeypatch.setattr(
        cli,
        "apply_approved_universe_membership_plan",
        lambda **_: result,
    )

    exit_code = cli.main(
        [
            "--plan-path",
            "/tmp/plan.json",
            "--approved-plan-sha256",
            "a" * 64,
            "--expected-plan-logical-fingerprint",
            "b" * 64,
            "--expected-current-state-fingerprint",
            "c" * 64,
            "--data-root",
            "/data/trading-intelligence-platform",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "applied"
    assert payload["published_file_count"] == 3
    assert payload["external_request_count"] == 0


def test_apply_cli_rejection_hides_failure_detail(monkeypatch, capsys) -> None:
    def rejected(**_):
        raise RuntimeError("sensitive failure detail")

    monkeypatch.setattr(
        cli,
        "apply_approved_universe_membership_plan",
        rejected,
    )
    exit_code = cli.main(
        [
            "--plan-path",
            "/tmp/plan.json",
            "--approved-plan-sha256",
            "a" * 64,
            "--expected-plan-logical-fingerprint",
            "b" * 64,
            "--expected-current-state-fingerprint",
            "c" * 64,
            "--data-root",
            "/data/trading-intelligence-platform",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 1
    assert payload["status"] == "rejected"
    assert "sensitive" not in output
