from __future__ import annotations

import json

import pytest

from tip_api.services import daily_eod_scheduler_rehearsal_cli as cli
from tip_api.services.daily_eod_scheduler_rehearsal import (
    review_daily_eod_scheduler_rehearsal,
)


def test_rehearsal_covers_five_separate_bounded_wakes() -> None:
    report = review_daily_eod_scheduler_rehearsal()
    by_name = {item.name: item for item in report.scenarios}

    assert set(by_name) == {
        "current",
        "oldest_missing",
        "retry_wait",
        "unresolved_interruption",
        "alert_required",
    }
    assert report.scenario_count == 5
    assert report.total_coordinator_invocation_count == 4
    assert report.maximum_coordinator_invocations_per_wake == 1
    assert by_name["current"].coordinator_invocation_count == 0
    assert by_name["unresolved_interruption"].coordinator_status == "recovery_required"
    assert by_name["unresolved_interruption"].recovery_attempted is False
    assert by_name["alert_required"].alert_required is True
    assert by_name["alert_required"].alert_delivery_attempted is False
    assert all(not item.automatic_retry_enabled for item in report.scenarios)
    assert all(not item.automatic_recovery_enabled for item in report.scenarios)
    assert report.synthetic_coordinator_results is True
    assert report.scheduler_installation_performed is False
    assert report.credential_access_count == 0
    assert report.external_request_count == 0
    assert report.filesystem_write_count == 0
    assert report.production_write_count == 0
    assert report.publication_authorized is False
    assert report.deployment_authorized is False


def test_rehearsal_cli_emits_canonical_report(capsys) -> None:
    assert cli.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contract_version"] == "daily-eod-scheduler-rehearsal/1.1"
    assert payload["scenario_count"] == 5
    assert payload["maximum_coordinator_invocations_per_wake"] == 1
    assert payload["scheduler_installation_performed"] is False
    assert "scheduler_installed" not in payload


def test_rehearsal_cli_rejects_arguments() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--unexpected"])
