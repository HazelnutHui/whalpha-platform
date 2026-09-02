from __future__ import annotations

import json
from datetime import date

from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services import historical_backfill_batch_cli as module
from tip_api.services.historical_backfill_batch_runner import (
    HistoricalBackfillBatchStoppedError,
    HistoricalBackfillSessionResultV1,
)


def test_cli_reports_safe_resume_evidence_when_transient_retries_are_exhausted(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    completed = HistoricalBackfillSessionResultV1(
        session_date="2026-07-13",
        identity_canonical_reused=False,
        identity_package_reused=False,
        identity_request_count=14,
        identity_plan_sha256="a" * 64,
        identity_status="published_and_verified",
        eod_canonical_reused=False,
        eod_package_reused=False,
        eod_request_count=1,
        eod_plan_sha256="b" * 64,
        eod_status="published_and_verified",
        canonical_session_count_after=36,
        canonical_first_session_after="2026-07-13",
        provider_request_attempt_count=15,
        transient_retry_count=0,
        transient_failure_codes=(),
    )

    def stopped_batch(**kwargs) -> object:
        del kwargs
        raise HistoricalBackfillBatchStoppedError(
            failed_session=date(2026, 7, 10),
            failure_code="transport_timeout",
            completed_sessions=(completed,),
            external_request_count=18,
            transient_retry_count=2,
            transient_failure_count=3,
        )

    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "load_massive_provider_config_from_file",
        lambda: MassiveProviderConfig(api_key=SecretStr("fixture-key")),
    )
    monkeypatch.setattr(module, "run_historical_backfill_batch", stopped_batch)

    return_code = module.main(
        [
            "--data-root",
            str(tmp_path / "data"),
            "--package-root",
            str(tmp_path / "packages"),
            "--maximum-sessions",
            "20",
            "--execute",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert return_code == 1
    assert captured.out == ""
    assert payload == {
        "analytics_execution_count": 0,
        "automatic_retry": False,
        "completed_session_count": 1,
        "completed_sessions": [
            {
                "canonical_first_session_after": "2026-07-13",
                "canonical_session_count_after": 36,
                "eod_canonical_reused": False,
                "eod_package_reused": False,
                "eod_plan_sha256": "b" * 64,
                "eod_request_count": 1,
                "eod_status": "published_and_verified",
                "identity_canonical_reused": False,
                "identity_package_reused": False,
                "identity_plan_sha256": "a" * 64,
                "identity_request_count": 14,
                "identity_status": "published_and_verified",
                "provider_request_attempt_count": 15,
                "session_date": "2026-07-13",
                "transient_failure_codes": [],
                "transient_retry_count": 0,
            }
        ],
        "contract_version": "historical-research-backfill-batch-result/1.1",
        "deployment_count": 0,
        "external_request_count": 18,
        "failed_session": "2026-07-10",
        "failure_code": "transport_timeout",
        "implementation_revision": "c" * 40,
        "publication_count": 0,
        "safe_resume_from_canonical": True,
        "status": "stopped_transient_retries_exhausted",
        "transient_failure_count": 3,
        "transient_retry_count": 2,
    }
    assert "fixture-key" not in captured.err
    assert "fixture timeout" not in captured.err
