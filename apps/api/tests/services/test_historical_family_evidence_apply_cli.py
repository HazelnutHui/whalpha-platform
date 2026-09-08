from __future__ import annotations

import json

from tip_api.services import historical_family_evidence_apply_cli as cli
from tip_api.services.historical_family_evidence_apply import (
    HistoricalFamilyEvidenceApplyResult,
)


def _result() -> HistoricalFamilyEvidenceApplyResult:
    return HistoricalFamilyEvidenceApplyResult(
        status="applied",
        plan_sha256="a" * 64,
        plan_logical_fingerprint="b" * 64,
        family_set_fingerprint="c" * 64,
        pre_apply_outside_inventory_fingerprint="d" * 64,
        post_apply_outside_inventory_fingerprint="d" * 64,
        post_state_fingerprint="e" * 64,
        published_families=("eod_price_bar", "point_in_time_identity"),
        reused_families=(),
        published_file_count=2,
        published_bytes=500,
        formal_reread_family_count=2,
    )


def _arguments() -> list[str]:
    return [
        "--plan-path",
        "/tmp/plan.json",
        "--approved-plan-sha256",
        "a" * 64,
        "--expected-plan-logical-fingerprint",
        "b" * 64,
        "--expected-family-set-fingerprint",
        "c" * 64,
        "--data-root",
        "/data/trading-intelligence-platform",
    ]


def test_cli_passes_every_exact_binding_and_reports_compact_result(
    monkeypatch,
    capsys,
) -> None:
    observed = {}

    def apply(**kwargs):
        observed.update(kwargs)
        return _result()

    monkeypatch.setattr(
        cli,
        "apply_approved_current_historical_family_evidence_plan",
        apply,
    )

    exit_code = cli.main([*_arguments(), "--verify-then-complete"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "applied"
    assert payload["published_families"] == [
        "eod_price_bar",
        "point_in_time_identity",
    ]
    assert payload["external_request_count"] == 0
    assert observed["approved_plan_sha256"] == "a" * 64
    assert observed["expected_plan_logical_fingerprint"] == "b" * 64
    assert observed["expected_family_set_fingerprint"] == "c" * 64
    assert observed["verify_then_complete"] is True


def test_cli_rejection_is_fail_closed_and_hides_local_detail(
    monkeypatch,
    capsys,
) -> None:
    def rejected(**_kwargs):
        raise RuntimeError("sensitive local detail")

    monkeypatch.setattr(
        cli,
        "apply_approved_current_historical_family_evidence_plan",
        rejected,
    )

    exit_code = cli.main(_arguments())
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 1
    assert payload == {
        "deleted_partition_count": 0,
        "error_type": "RuntimeError",
        "external_request_count": 0,
        "historical_coverage_authorized": False,
        "overwritten_partition_count": 0,
        "reason_code": "historical_family_evidence_apply_rejected",
        "research_development_authorized": False,
        "research_performance_authorized": False,
        "status": "rejected",
    }
    assert "sensitive" not in output
