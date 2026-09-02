"""Finite continuous orchestration over bounded Historical Backfill batches."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import FixedIntervalRateLimiter
from tip_api.providers.massive.transport import MassiveHttpTransport
from tip_api.services.historical_backfill_batch_runner import (
    CONTRACT_VERSION as BATCH_CONTRACT_VERSION,
    MAXIMUM_SESSIONS_PER_INVOCATION,
    HistoricalBackfillBatchResultV1,
    HistoricalBackfillBatchStoppedError,
    HistoricalBackfillSessionResultV1,
    TransientFailureCode,
    run_historical_backfill_batch,
)
from tip_api.services.historical_backfill_planner import (
    DEFAULT_TARGET_SESSIONS,
    MAXIMUM_TARGET_SESSIONS,
    MINIMUM_TARGET_SESSIONS,
)


CONTRACT_VERSION = "historical-research-backfill-continuous-result/1.0"
DEFAULT_BATCH_SIZE = MAXIMUM_SESSIONS_PER_INVOCATION

BatchRunner = Callable[..., HistoricalBackfillBatchResultV1]
BatchCheckpoint = Callable[[int, HistoricalBackfillBatchResultV1], None]


class HistoricalBackfillContinuousRunnerError(RuntimeError):
    """Raised when finite continuous execution cannot advance safely."""


class HistoricalBackfillContinuousStoppedError(
    HistoricalBackfillContinuousRunnerError
):
    """A batch stopped after prior checkpoints with safe resume evidence."""

    def __init__(
        self,
        *,
        failed_session: str,
        failure_code: TransientFailureCode,
        completed_batch_count: int,
        completed_session_count: int,
        current_batch_completed_sessions: tuple[
            HistoricalBackfillSessionResultV1, ...
        ],
        external_request_count: int,
        transient_retry_count: int,
        transient_failure_count: int,
    ) -> None:
        self.failed_session = failed_session
        self.failure_code = failure_code
        self.completed_batch_count = completed_batch_count
        self.completed_session_count = completed_session_count
        self.current_batch_completed_sessions = current_batch_completed_sessions
        self.external_request_count = external_request_count
        self.transient_retry_count = transient_retry_count
        self.transient_failure_count = transient_failure_count
        super().__init__(
            "continuous historical backfill stopped at a bounded batch"
        )


@dataclass(frozen=True, slots=True)
class HistoricalBackfillContinuousResultV1:
    contract_version: str
    status: str
    target_session_count: int
    batch_size: int
    completed_batch_count: int
    completed_session_count: int
    first_completed_session: str | None
    last_completed_session: str | None
    external_request_count: int
    transient_retry_count: int
    next_session: str | None
    production_session_count: int
    analytics_execution_count: int
    publication_count: int
    deployment_count: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_historical_backfill_continuous(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    data_root: Path,
    package_root: Path,
    target_session_count: int = DEFAULT_TARGET_SESSIONS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    rate_limiter: FixedIntervalRateLimiter | None = None,
    batch_runner: BatchRunner = run_historical_backfill_batch,
    on_batch_complete: BatchCheckpoint | None = None,
) -> HistoricalBackfillContinuousResultV1:
    """Run finite bounded batches until the exact target is complete."""

    if not 1 <= batch_size <= MAXIMUM_SESSIONS_PER_INVOCATION:
        raise HistoricalBackfillContinuousRunnerError(
            "batch size must be between one and twenty"
        )
    if not (
        MINIMUM_TARGET_SESSIONS
        <= target_session_count
        <= MAXIMUM_TARGET_SESSIONS
    ):
        raise HistoricalBackfillContinuousRunnerError(
            "target session count must be between 252 and 504"
        )
    limiter = rate_limiter or FixedIntervalRateLimiter()
    completed_batches = 0
    completed_sessions = 0
    first_completed_session: str | None = None
    last_completed_session: str | None = None
    external_requests = 0
    transient_retries = 0

    for _ in range(target_session_count + 1):
        try:
            batch = batch_runner(
                config=config,
                transport=transport,
                data_root=data_root,
                package_root=package_root,
                maximum_sessions=batch_size,
                target_session_count=target_session_count,
                rate_limiter=limiter,
            )
        except HistoricalBackfillBatchStoppedError as exc:
            raise HistoricalBackfillContinuousStoppedError(
                failed_session=exc.failed_session.isoformat(),
                failure_code=exc.failure_code,
                completed_batch_count=completed_batches,
                completed_session_count=(
                    completed_sessions + len(exc.completed_sessions)
                ),
                current_batch_completed_sessions=exc.completed_sessions,
                external_request_count=(
                    external_requests + exc.external_request_count
                ),
                transient_retry_count=(
                    transient_retries + exc.transient_retry_count
                ),
                transient_failure_count=(
                    transient_retries + exc.transient_failure_count
                ),
            ) from exc

        _validate_batch_result(
            batch,
            expected_target_session_count=target_session_count,
            expected_batch_size=batch_size,
        )
        batch_session_count = len(batch.completed_sessions)
        if batch_session_count == 0:
            if batch.status != "target_complete":
                raise HistoricalBackfillContinuousRunnerError(
                    "bounded batch returned no progress before target completion"
                )
            return _result(
                target_session_count=target_session_count,
                batch_size=batch_size,
                completed_batch_count=completed_batches,
                completed_session_count=completed_sessions,
                first_completed_session=first_completed_session,
                last_completed_session=last_completed_session,
                external_request_count=external_requests,
                transient_retry_count=transient_retries,
            )

        completed_batches += 1
        completed_sessions += batch_session_count
        external_requests += batch.external_request_count
        transient_retries += batch.transient_retry_count
        if first_completed_session is None:
            first_completed_session = batch.completed_sessions[0].session_date
        last_completed_session = batch.completed_sessions[-1].session_date
        if on_batch_complete is not None:
            on_batch_complete(completed_batches, batch)
        if batch.status == "target_complete":
            return _result(
                target_session_count=target_session_count,
                batch_size=batch_size,
                completed_batch_count=completed_batches,
                completed_session_count=completed_sessions,
                first_completed_session=first_completed_session,
                last_completed_session=last_completed_session,
                external_request_count=external_requests,
                transient_retry_count=transient_retries,
            )

    raise HistoricalBackfillContinuousRunnerError(
        "continuous backfill exceeded its finite progress bound"
    )


def _validate_batch_result(
    batch: HistoricalBackfillBatchResultV1,
    *,
    expected_target_session_count: int,
    expected_batch_size: int,
) -> None:
    if (
        batch.contract_version != BATCH_CONTRACT_VERSION
        or batch.target_session_count != expected_target_session_count
        or batch.maximum_sessions != expected_batch_size
        or batch.production_session_count != len(batch.completed_sessions)
        or len(batch.completed_sessions) > expected_batch_size
        or batch.analytics_execution_count != 0
        or batch.publication_count != 0
        or batch.deployment_count != 0
    ):
        raise HistoricalBackfillContinuousRunnerError(
            "bounded batch result violated the continuous custody contract"
        )
    if batch.status not in {"batch_complete", "target_complete"}:
        raise HistoricalBackfillContinuousRunnerError(
            "bounded batch returned an unknown status"
        )


def _result(
    *,
    target_session_count: int,
    batch_size: int,
    completed_batch_count: int,
    completed_session_count: int,
    first_completed_session: str | None,
    last_completed_session: str | None,
    external_request_count: int,
    transient_retry_count: int,
) -> HistoricalBackfillContinuousResultV1:
    return HistoricalBackfillContinuousResultV1(
        contract_version=CONTRACT_VERSION,
        status="target_complete",
        target_session_count=target_session_count,
        batch_size=batch_size,
        completed_batch_count=completed_batch_count,
        completed_session_count=completed_session_count,
        first_completed_session=first_completed_session,
        last_completed_session=last_completed_session,
        external_request_count=external_request_count,
        transient_retry_count=transient_retry_count,
        next_session=None,
        production_session_count=completed_session_count,
        analytics_execution_count=0,
        publication_count=0,
        deployment_count=0,
    )
