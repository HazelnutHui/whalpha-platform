from __future__ import annotations

import json
from pathlib import Path

from tip_api.services import daily_universe_membership_continuation_cli as cli
from tip_api.services.daily_universe_membership_continuation import (
    DailyUniverseMembershipContinuationResult,
)


def test_cli_reports_candidate_without_canonical_authority(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        cli,
        "prepare_daily_universe_membership_candidate",
        lambda **_: DailyUniverseMembershipContinuationResult(
            status="candidate_ready_for_publication_plan",
            session_date="2026-09-04",
            methodology_version="method-v1",
            candidate_partition_path="/tmp/candidate/partition",
            candidate_status="published",
            record_count=2,
            membership_logical_fingerprint="a" * 64,
            point_in_time_eligibility="signal_eligible",
            knowledge_time_assessment_fingerprint="b" * 64,
            canonical_publication_fingerprint=None,
        ),
    )

    result = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--session-date",
            "2026-09-04",
            "--catalog-as-of-date",
            "2026-08-14",
            "--evaluated-at",
            "2026-09-06T13:15:00+00:00",
            "--assessed-at",
            "2026-09-06T13:20:00+00:00",
            "--candidate-root",
            "/tmp/candidate",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "candidate_ready_for_publication_plan"
    assert payload["canonical_data_write_count"] == 0
    assert payload["publication_authorized"] is False
    assert payload["scheduler_enabled"] is False


def test_cli_fails_closed_without_error_body(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "prepare_daily_universe_membership_candidate",
        lambda **_: (_ for _ in ()).throw(RuntimeError("sensitive detail")),
    )

    result = cli.main(
        [
            "--data-root",
            "/data/trading-intelligence-platform",
            "--session-date",
            "2026-09-04",
            "--catalog-as-of-date",
            "2026-08-14",
            "--evaluated-at",
            "2026-09-06T13:15:00+00:00",
            "--assessed-at",
            "2026-09-06T13:20:00+00:00",
            "--candidate-root",
            str(Path("/tmp/candidate")),
        ]
    )

    assert result == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["error_type"] == "RuntimeError"
    assert "sensitive detail" not in str(payload)
