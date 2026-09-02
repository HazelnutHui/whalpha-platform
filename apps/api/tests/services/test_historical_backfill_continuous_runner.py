from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import SecretStr

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.services.historical_backfill_batch_runner import (
    HistoricalBackfillBatchResultV1,
    HistoricalBackfillBatchStoppedError,
    HistoricalBackfillSessionResultV1,
)
from tip_api.services.historical_backfill_continuous_runner import (
    HistoricalBackfillContinuousRunnerError,
    HistoricalBackfillContinuousStoppedError,
    run_historical_backfill_continuous,
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
    external_request_count: int | None = None,
    transient_retry_count: int = 0,
    production_session_count: int | None = None,
) -> HistoricalBackfillBatchResultV1:
    return HistoricalBackfillBatchResultV1(
        contract_version="historical-research-backfill-batch-result/1.1",
        target_session_count=300,
        maximum_sessions=20,
        completed_sessions=sessions,
        status=status,
        next_session=next_session,
        external_request_count=(
            external_request_count
            if external_request_count is not None
            else len(sessions) * 14
        ),
        transient_retry_count=transient_retry_count,
        transient_retry_delays_seconds=(30, 90),
        production_session_count=(
            production_session_count
            if production_session_count is not None
            else len(sessions)
        ),
        analytics_execution_count=0,
        publication_count=0,
        deployment_count=0,
    )


def _run(**overrides):
    arguments = {
        "config": MassiveProviderConfig(api_key=SecretStr("fixture-key")),
        "transport": object(),
        "data_root": Path("/fixture-data"),
        "package_root": Path("/fixture-packages"),
        "target_session_count": 300,
        "batch_size": 20,
    }
    arguments.update(overrides)
    return run_historical_backfill_continuous(**arguments)


def test_continuous_runner_chains_bounded_batches_until_target_completion() -> None:
    first = _batch(
        (_session("2026-01-29", 148), _session("2026-01-28", 149)),
        status="batch_complete",
        next_session="2026-01-27",
        external_request_count=29,
        transient_retry_count=1,
    )
    second = _batch(
        (_session("2026-01-27", 150),),
        status="target_complete",
        next_session=None,
        external_request_count=14,
    )
    responses = iter((first, second))
    calls: list[dict[str, object]] = []
    checkpoints: list[tuple[int, HistoricalBackfillBatchResultV1]] = []

    def fake_batch_runner(**kwargs) -> HistoricalBackfillBatchResultV1:
        calls.append(kwargs)
        return next(responses)

    result = _run(
        batch_runner=fake_batch_runner,
        on_batch_complete=lambda number, batch: checkpoints.append(
            (number, batch)
        ),
    )

    assert result.status == "target_complete"
    assert result.completed_batch_count == 2
    assert result.completed_session_count == 3
    assert result.first_completed_session == "2026-01-29"
    assert result.last_completed_session == "2026-01-27"
    assert result.external_request_count == 43
    assert result.transient_retry_count == 1
    assert result.next_session is None
    assert [number for number, _ in checkpoints] == [1, 2]
    assert len(calls) == 2
    assert calls[0]["rate_limiter"] is calls[1]["rate_limiter"]
    assert all(call["maximum_sessions"] == 20 for call in calls)
    assert all(call["target_session_count"] == 300 for call in calls)


def test_continuous_runner_exits_cleanly_when_target_is_already_complete() -> None:
    result = _run(
        batch_runner=lambda **kwargs: _batch(
            (), status="target_complete", next_session=None
        )
    )

    assert result.completed_batch_count == 0
    assert result.completed_session_count == 0
    assert result.first_completed_session is None
    assert result.last_completed_session is None


def test_continuous_runner_rejects_a_nonprogressing_batch() -> None:
    with pytest.raises(
        HistoricalBackfillContinuousRunnerError,
        match="no progress",
    ):
        _run(
            batch_runner=lambda **kwargs: _batch(
                (), status="batch_complete", next_session="2026-01-29"
            )
        )


def test_continuous_runner_rejects_a_mismatched_batch_contract() -> None:
    with pytest.raises(
        HistoricalBackfillContinuousRunnerError,
        match="custody contract",
    ):
        _run(
            batch_runner=lambda **kwargs: _batch(
                (_session("2026-01-29", 148),),
                status="batch_complete",
                next_session="2026-01-28",
                production_session_count=0,
            )
        )


def test_continuous_runner_preserves_prior_and_current_batch_stop_evidence() -> None:
    first = _batch(
        (_session("2026-01-29", 148),),
        status="batch_complete",
        next_session="2026-01-28",
        external_request_count=15,
        transient_retry_count=1,
    )
    calls = 0

    def stopping_batch_runner(**kwargs) -> HistoricalBackfillBatchResultV1:
        nonlocal calls
        del kwargs
        calls += 1
        if calls == 1:
            return first
        raise HistoricalBackfillBatchStoppedError(
            failed_session=date(2026, 1, 27),
            failure_code="transport_timeout",
            completed_sessions=(_session("2026-01-28", 149),),
            external_request_count=18,
            transient_retry_count=2,
            transient_failure_count=3,
        )

    with pytest.raises(HistoricalBackfillContinuousStoppedError) as raised:
        _run(batch_runner=stopping_batch_runner)

    error = raised.value
    assert error.failed_session == "2026-01-27"
    assert error.completed_batch_count == 1
    assert error.completed_session_count == 2
    assert tuple(
        item.session_date for item in error.current_batch_completed_sessions
    ) == ("2026-01-28",)
    assert error.external_request_count == 33
    assert error.transient_retry_count == 3
    assert error.transient_failure_count == 4


@pytest.mark.parametrize("batch_size", (0, 21))
def test_continuous_runner_preserves_the_twenty_session_batch_ceiling(
    batch_size: int,
) -> None:
    with pytest.raises(
        HistoricalBackfillContinuousRunnerError,
        match="between one and twenty",
    ):
        _run(batch_size=batch_size)


@pytest.mark.parametrize("target_session_count", (251, 505))
def test_continuous_runner_preserves_planner_target_bounds(
    target_session_count: int,
) -> None:
    with pytest.raises(
        HistoricalBackfillContinuousRunnerError,
        match="between 252 and 504",
    ):
        _run(target_session_count=target_session_count)
