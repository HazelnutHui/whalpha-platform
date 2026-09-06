from __future__ import annotations

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

from tip_api.services import universe_membership_knowledge_time_cli as cli


def test_cli_emits_assessment_without_network_or_writes(monkeypatch, capsys) -> None:
    report = SimpleNamespace(
        model_dump=lambda **_: {
            "schema_version": "1.0",
            "session_date": date(2026, 9, 4).isoformat(),
            "point_in_time_eligibility": "signal_eligible",
            "logical_fingerprint": "a" * 64,
        }
    )
    monkeypatch.setattr(
        cli,
        "assess_universe_membership_knowledge_time",
        lambda **_: report,
    )

    result = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--membership-root",
            "/tmp/membership",
            "--membership-partition",
            "/tmp/membership/partition",
            "--assessed-at",
            datetime(2026, 9, 6, 14, tzinfo=UTC).isoformat(),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["status"] == "assessed"
    assert payload["point_in_time_eligibility"] == "signal_eligible"
    assert payload["external_request_count"] == 0
    assert payload["canonical_data_write_count"] == 0


def test_cli_failure_is_safe_and_does_not_echo_exception(monkeypatch, capsys) -> None:
    def rejected(**_):
        raise RuntimeError("sensitive failure detail")

    monkeypatch.setattr(
        cli,
        "assess_universe_membership_knowledge_time",
        rejected,
    )

    result = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--membership-root",
            "/tmp/membership",
            "--membership-partition",
            "/tmp/membership/partition",
            "--assessed-at",
            "2026-09-06T14:00:00+00:00",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert result == 1
    assert payload["status"] == "rejected"
    assert payload["error_type"] == "RuntimeError"
    assert "sensitive" not in output
