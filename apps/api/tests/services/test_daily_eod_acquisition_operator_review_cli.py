from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from tip_api.services import daily_eod_acquisition_operator_review_cli as cli


def _argv() -> list[str]:
    return [
        "--target-session",
        "2026-08-27",
        "--latest-canonical-session",
        "2026-08-26",
        "--acquisition-action",
        "prepare_eod_catchup",
        "--run-root",
        "/tmp/daily-run-root",
        "--package",
        "/tmp/daily-eod-package",
        "--purpose",
        "initial_eod_availability",
        "--disposition",
        "authorize_one_fetch_after",
        "--evidence-code",
        "provider_plan_and_release_reviewed",
        "--not-before",
        "2026-08-27T22:00:00+00:00",
        "--acknowledgement",
        cli.ACKNOWLEDGEMENT,
    ]


def test_cli_records_only_a_review_under_offline_guard(monkeypatch, capsys) -> None:
    captured = {}

    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "record_acquisition_operator_review",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(
            as_dict=lambda: {
                "contract_version": "daily-eod-acquisition-operator-review/1.0",
                "external_request_count": 0,
                "production_write_count": 0,
                "fetch_authorized_by_review": False,
            }
        ),
    )

    assert cli.main(_argv()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert captured["purpose"].value == "initial_eod_availability"
    assert captured["expected_terminal_event_fingerprint"] is None
    assert payload["external_request_count"] == 0
    assert payload["fetch_authorized_by_review"] is False


def test_cli_rejection_is_sanitized(monkeypatch, capsys) -> None:
    @contextmanager
    def guard():
        yield

    monkeypatch.setattr(cli, "_offline_socket_guard", guard)
    monkeypatch.setattr(
        cli,
        "record_acquisition_operator_review",
        lambda **kwargs: (_ for _ in ()).throw(
            cli.DailyEodAcquisitionOperatorReviewError("sensitive diagnosis")
        ),
    )

    assert cli.main(_argv()) == 1
    output = capsys.readouterr().out
    assert "sensitive" not in output
    assert json.loads(output)["external_request_count"] == 0


def test_cli_requires_exact_non_authorizing_acknowledgement() -> None:
    args = _argv()
    args[-1] = "yes"
    with pytest.raises(SystemExit):
        cli.main(args)
