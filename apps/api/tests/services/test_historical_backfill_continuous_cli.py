from __future__ import annotations

import json

from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services import historical_backfill_continuous_cli as module
from tip_api.services.historical_backfill_batch_runner import (
    HistoricalBackfillBatchResultV1,
    HistoricalBackfillSessionResultV1,
)
from tip_api.services.historical_backfill_continuous_runner import (
    HistoricalBackfillContinuousResultV1,
    HistoricalBackfillContinuousStoppedError,
)


def _session(session: str, canonical_count: int) -> HistoricalBackfillSessionResultV1:
    return HistoricalBackfillSessionResultV1(
        session_date=session,
        identity_canonical_reused=False,
        identity_package_reused=False,
        identity_request_count=13,
        identity_plan_sha256="a" * 64,
        identity_status="published_and_verified",
        eod_canonical_reused=False,
        eod_package_reused=False,
        eod_request_count=1,
        eod_plan_sha256="b" * 64,
        eod_status="published_and_verified",
        canonical_session_count_after=canonical_count,
        canonical_first_session_after=session,
        provider_request_attempt_count=14,
        transient_retry_count=0,
        transient_failure_codes=(),
    )


def _batch(
    sessions: tuple[HistoricalBackfillSessionResultV1, ...],
    *,
    status: str,
    next_session: str | None,
) -> HistoricalBackfillBatchResultV1:
    return HistoricalBackfillBatchResultV1(
        contract_version="historical-research-backfill-batch-result/1.1",
        target_session_count=300,
        maximum_sessions=20,
        completed_sessions=sessions,
        status=status,
        next_session=next_session,
        external_request_count=len(sessions) * 14,
        transient_retry_count=0,
        transient_retry_delays_seconds=(30, 90),
        production_session_count=len(sessions),
        analytics_execution_count=0,
        publication_count=0,
        deployment_count=0,
    )


def _prepare(monkeypatch) -> None:
    monkeypatch.setattr(module, "_clean_revision", lambda: "c" * 40)
    monkeypatch.setattr(
        module,
        "load_massive_provider_config_from_file",
        lambda: MassiveProviderConfig(api_key=SecretStr("fixture-key")),
    )
    monkeypatch.setattr(module, "MassiveUrllibTransport", lambda: object())


def _arguments(tmp_path) -> list[str]:
    return [
        "--data-root",
        str(tmp_path / "data"),
        "--package-root",
        str(tmp_path / "packages"),
        "--execute",
    ]


def test_cli_streams_each_bounded_checkpoint_before_completion(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    _prepare(monkeypatch)
    batch = _batch(
        (_session("2026-01-29", 300),),
        status="target_complete",
        next_session=None,
    )

    def successful_run(**kwargs) -> HistoricalBackfillContinuousResultV1:
        kwargs["on_batch_complete"](1, batch)
        return HistoricalBackfillContinuousResultV1(
            contract_version="historical-research-backfill-continuous-result/1.0",
            status="target_complete",
            target_session_count=300,
            batch_size=20,
            completed_batch_count=1,
            completed_session_count=1,
            first_completed_session="2026-01-29",
            last_completed_session="2026-01-29",
            external_request_count=14,
            transient_retry_count=0,
            next_session=None,
            production_session_count=1,
            analytics_execution_count=0,
            publication_count=0,
            deployment_count=0,
        )

    monkeypatch.setattr(module, "run_historical_backfill_continuous", successful_run)

    assert module.main(_arguments(tmp_path)) == 0

    captured = capsys.readouterr()
    records = [json.loads(line) for line in captured.out.splitlines()]
    assert captured.err == ""
    assert [record["record_type"] for record in records] == [
        "bounded_batch_checkpoint",
        "continuous_completion",
    ]
    assert records[0]["batch_number"] == 1
    assert records[1]["completed_session_count"] == 1
    assert all(record["implementation_revision"] == "c" * 40 for record in records)
    assert "fixture-key" not in captured.out


def test_cli_reports_safe_continuous_stop_without_exception_text(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    _prepare(monkeypatch)

    def stopped_run(**kwargs) -> object:
        del kwargs
        raise HistoricalBackfillContinuousStoppedError(
            failed_session="2026-01-28",
            failure_code="transport_timeout",
            completed_batch_count=2,
            completed_session_count=41,
            current_batch_completed_sessions=(_session("2026-01-29", 188),),
            external_request_count=575,
            transient_retry_count=2,
            transient_failure_count=3,
        )

    monkeypatch.setattr(module, "run_historical_backfill_continuous", stopped_run)

    assert module.main(_arguments(tmp_path)) == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert captured.out == ""
    assert payload["record_type"] == "continuous_stop"
    assert payload["status"] == "stopped_transient_retries_exhausted"
    assert payload["completed_batch_count"] == 2
    assert payload["completed_session_count"] == 41
    assert payload["failed_session"] == "2026-01-28"
    assert payload["safe_resume_from_canonical"] is True
    assert payload["automatic_restart"] is False
    assert "fixture-key" not in captured.err
    assert "continuous historical backfill stopped" not in captured.err
