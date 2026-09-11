from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.services import reconciled_eod_edition_apply_cli as cli


def test_plan_command_emits_approval_bindings(monkeypatch, capsys) -> None:
    plan = SimpleNamespace(
        status="ready_for_separate_apply",
        logical_fingerprint="a" * 64,
        expected_current_state_fingerprint="b" * 64,
        edition_id="massive-exact-symbol-v1",
        candidate_session_count=1255,
        candidate_record_count=12_000_000,
        inventory_change_file_count=2511,
        inventory_change_bytes=4_700_000_000,
        apply_authorized=False,
        production_authority=False,
        research_performance_authorized=False,
    )
    evidence = SimpleNamespace(
        plan=plan,
        plan_path=Path("/tmp/candidate/apply-plan.json"),
        plan_sha256="c" * 64,
    )
    monkeypatch.setattr(
        cli,
        "build_reconciled_eod_edition_apply_plan",
        lambda **_values: evidence,
    )

    assert (
        cli.main(
            [
                "plan",
                "--data-root",
                "/data/trading-intelligence-platform",
                "--candidate-root",
                "/tmp/candidate",
                "--plan-path",
                "/tmp/candidate/apply-plan.json",
                "--edition-id",
                "massive-exact-symbol-v1",
                "--planner-revision",
                "d" * 40,
                "--created-at",
                "2026-09-11T00:00:00+00:00",
            ]
        )
        == 0
    )
    assert '"apply_authorized": false' in capsys.readouterr().out


def test_apply_command_requires_execute(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "apply_approved_reconciled_eod_edition_plan",
        lambda **_values: pytest.fail("Apply must not be called"),
    )
    with pytest.raises(SystemExit):
        cli.main(
            [
                "apply",
                "--data-root",
                "/data/trading-intelligence-platform",
                "--plan-path",
                "/tmp/candidate/apply-plan.json",
                "--approved-plan-sha256",
                "a" * 64,
                "--expected-plan-logical-fingerprint",
                "b" * 64,
                "--expected-current-state-fingerprint",
                "c" * 64,
            ]
        )


def test_apply_command_passes_all_exact_approval_values(monkeypatch, capsys) -> None:
    observed: dict[str, object] = {}
    result = SimpleNamespace(
        status="applied",
        plan_sha256="a" * 64,
        plan_logical_fingerprint="b" * 64,
        edition_id="massive-exact-symbol-v1",
        interval_manifest_fingerprint="d" * 64,
        edition_published=True,
        edition_reused=False,
        published_file_count=2511,
        published_bytes=4_700_000_000,
        formal_reread_session_count=1255,
        formal_reread_record_count=12_000_000,
        external_request_count=0,
        production_authority=False,
        research_performance_authorized=False,
    )

    def apply(**values):
        observed.update(values)
        return result

    monkeypatch.setattr(
        cli,
        "apply_approved_reconciled_eod_edition_plan",
        apply,
    )
    assert (
        cli.main(
            [
                "apply",
                "--data-root",
                "/data/trading-intelligence-platform",
                "--plan-path",
                "/tmp/candidate/apply-plan.json",
                "--approved-plan-sha256",
                "a" * 64,
                "--expected-plan-logical-fingerprint",
                "b" * 64,
                "--expected-current-state-fingerprint",
                "c" * 64,
                "--verify-then-complete",
                "--execute",
            ]
        )
        == 0
    )
    assert observed["approved_plan_sha256"] == "a" * 64
    assert observed["verify_then_complete"] is True
    assert '"production_authority": false' in capsys.readouterr().out
