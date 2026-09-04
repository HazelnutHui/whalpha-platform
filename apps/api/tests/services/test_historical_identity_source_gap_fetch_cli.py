from __future__ import annotations

import json

from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services import historical_identity_source_gap_fetch_cli as module
from tip_api.services.historical_identity_source_gap_fetch import (
    HistoricalIdentitySourceGapFetchStoppedError,
)


def test_cli_never_emits_exception_or_credential_text(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "load_massive_provider_config_from_file",
        lambda: MassiveProviderConfig(api_key=SecretStr("fixture-secret")),
    )

    def stopped(**kwargs) -> object:
        del kwargs
        error = HistoricalIdentitySourceGapFetchStoppedError(
            failed_session=module.date(2026, 7, 17),
            failure_code="transport_timeout",
            completed_items=(),
            provider_request_attempt_count=3,
            transient_retry_count=2,
            transient_failure_count=3,
        )
        error.__cause__ = RuntimeError("fixture-secret response body")
        raise error

    monkeypatch.setattr(
        module,
        "run_historical_identity_source_gap_fetch",
        stopped,
    )
    code = module.main(
        [
            "--data-root",
            str(tmp_path / "data"),
            "--package-root",
            str(tmp_path / "packages"),
            "--session-date",
            "2026-07-17",
            "--execute",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 1
    assert captured.out == ""
    assert payload["status"] == "stopped_transient_retries_exhausted"
    assert payload["safe_resume_from_package_custody"] is True
    assert "fixture-secret" not in captured.err
    assert "response body" not in captured.err
