from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from tip_api.services import quant_research_campaign_three_development_access_cli as access_cli
from tip_api.services import quant_research_campaign_three_screening_cli as screening_cli


REVISION = "1" * 40


def _custody(tmp_path, name):
    path = tmp_path / name
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def test_access_cli_creates_exact_request_then_bound_grant(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(access_cli, "_validate_repository_revision", lambda _: None)
    request_custody = _custody(tmp_path, "requests")
    grant_custody = _custody(tmp_path, "grants")
    request_root = request_custody / "request=test"
    grant_root = grant_custody / "grant=test"

    assert access_cli.main(
        [
            "request",
            "--implementation-revision",
            REVISION,
            "--output-root",
            str(request_root),
            "--output-custody-root",
            str(request_custody),
        ]
    ) == 0
    request_output = json.loads(capsys.readouterr().out)
    assert request_output["development_outcome_access_authorized"] is False

    assert access_cli.main(
        [
            "grant",
            "--implementation-revision",
            REVISION,
            "--request-root",
            str(request_root),
            "--request-custody-root",
            str(request_custody),
            "--output-root",
            str(grant_root),
            "--output-custody-root",
            str(grant_custody),
            "--authorization-phrase",
            request_output["exact_authorization_phrase"],
            "--granted-at",
            "2026-09-16T01:00:00Z",
        ]
    ) == 0
    grant_output = json.loads(capsys.readouterr().out)
    assert grant_output["authorized_execution_count"] == 2
    assert grant_output["validation_access_authorized"] is False
    assert grant_output["holdout_access_authorized"] is False


def test_campaign_three_run_identity_requires_exact_utc() -> None:
    screening_cli._validate_run_identity(
        datetime(2026, 9, 16, tzinfo=timezone.utc), REVISION
    )
    with pytest.raises(screening_cli.CampaignThreeScreeningCliError, match="UTC"):
        screening_cli._validate_run_identity(
            datetime(
                2026,
                9,
                16,
                tzinfo=timezone(timedelta(hours=-6)),
            ),
            REVISION,
        )


def test_campaign_three_evaluator_hash_is_stable() -> None:
    first = screening_cli._evaluator_code_sha256()
    second = screening_cli._evaluator_code_sha256()

    assert first == second
    assert len(first) == 64
