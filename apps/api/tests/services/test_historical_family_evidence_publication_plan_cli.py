from __future__ import annotations

import json
import socket
from types import SimpleNamespace

import pytest

from tip_api.services import historical_family_evidence_publication_plan_cli as cli


def _evidence():
    family = SimpleNamespace(
        value="eod_price_bar",
    )
    item = SimpleNamespace(
        family=family,
        record_count=100,
        source_artifact_count=1,
        source_file_count=2,
        evidence=SimpleNamespace(logical_fingerprint="a" * 64),
        evidence_manifest_sha256="b" * 64,
        target_path="market-data/evidence/manifest.json",
        expected_target_state="absent",
    )
    plan = SimpleNamespace(
        logical_fingerprint="c" * 64,
        family_set_fingerprint="d" * 64,
        first_session=SimpleNamespace(isoformat=lambda: "2026-09-03"),
        last_session=SimpleNamespace(isoformat=lambda: "2026-09-04"),
        session_count=2,
        inventory_change_file_count=2,
        inventory_change_bytes=500,
        target_absent_count=2,
        families=(item,),
        external_request_count=0,
        canonical_data_write_count=0,
        apply_authorized=False,
        historical_coverage_authorized=False,
        research_development_authorized=False,
        research_performance_authorized=False,
    )
    return SimpleNamespace(
        plan=plan,
        plan_path="/tmp/plan.json",
        plan_sha256="e" * 64,
    )


def test_build_cli_reports_compact_no_write_plan(monkeypatch, capsys) -> None:
    observed = {}

    def build(**kwargs):
        observed.update(kwargs)
        return _evidence()

    monkeypatch.setattr(
        cli,
        "build_current_historical_family_evidence_publication_plan",
        build,
    )

    result = cli.main(
        [
            "build",
            "--data-root",
            "/data/trading-intelligence-platform",
            "--plan-path",
            "/tmp/plan.json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["status"] == "plan_created"
    assert payload["canonical_data_write_count"] == 0
    assert payload["apply_authorized"] is False
    assert payload["families"][0]["family"] == "eod_price_bar"
    assert observed["data_root"].as_posix() == "/data/trading-intelligence-platform"


def test_verify_cli_requires_and_passes_exact_plan_sha(monkeypatch, capsys) -> None:
    observed = {}

    def read(**kwargs):
        observed.update(kwargs)
        return _evidence()

    monkeypatch.setattr(
        cli,
        "read_current_historical_family_evidence_publication_plan",
        read,
    )

    result = cli.main(
        [
            "verify",
            "--plan-path",
            "/tmp/plan.json",
            "--approved-plan-sha256",
            "e" * 64,
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["status"] == "plan_revalidated"
    assert observed["approved_plan_sha256"] == "e" * 64


def test_cli_rejection_hides_failure_detail(monkeypatch, capsys) -> None:
    def rejected(**_):
        raise RuntimeError("sensitive local detail")

    monkeypatch.setattr(
        cli,
        "build_current_historical_family_evidence_publication_plan",
        rejected,
    )

    result = cli.main(
        [
            "build",
            "--data-root",
            "/data/trading-intelligence-platform",
            "--plan-path",
            "/tmp/plan.json",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert result == 1
    assert payload["status"] == "rejected"
    assert payload["canonical_data_write_count"] == 0
    assert "sensitive" not in output


def test_cli_socket_guard_blocks_and_restores() -> None:
    original = socket.socket
    with cli._offline_socket_guard():
        with pytest.raises(RuntimeError, match="network is prohibited"):
            socket.getaddrinfo("localhost", 80)
        guarded = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(RuntimeError, match="network is prohibited"):
            guarded.connect(("127.0.0.1", 9))
        guarded.close()
    assert socket.socket is original
