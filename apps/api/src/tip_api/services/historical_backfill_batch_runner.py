"""Resumable Dell-local execution of bounded historical EOD/Identity sessions."""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import asdict, dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal

from pydantic import SecretStr

from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import FixedIntervalRateLimiter
from tip_api.providers.massive.same_day_catchup import (
    apply_approved_plan,
    build_eod_plan,
    build_identity_plan,
    fetch_eod_package,
    fetch_identity_package,
    file_sha256,
    inventory_fingerprint,
    read_catchup_approval_plan_evidence,
    read_fetch_package_evidence,
)
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveJson,
    MassiveParams,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)
from tip_api.services.historical_backfill_planner import (
    DEFAULT_TARGET_SESSIONS,
    select_next_historical_backfill_session,
)


CONTRACT_VERSION = "historical-research-backfill-batch-result/1.1"
MAXIMUM_SESSIONS_PER_INVOCATION = 20
DEFAULT_TRANSIENT_RETRY_DELAYS_SECONDS = (30, 90)
MAXIMUM_TRANSIENT_RETRIES_PER_SESSION = 2
MAXIMUM_TRANSIENT_RETRY_DELAY_SECONDS = 5 * 60

TransientFailureCode = Literal["transport_timeout", "transport_unavailable"]


class HistoricalBackfillBatchRunnerError(RuntimeError):
    """Raised when one exact historical session cannot complete safely."""


@dataclass(frozen=True, slots=True)
class HistoricalBackfillSessionResultV1:
    session_date: str
    identity_canonical_reused: bool
    identity_package_reused: bool
    identity_request_count: int
    identity_plan_sha256: str | None
    identity_status: str
    eod_canonical_reused: bool
    eod_package_reused: bool
    eod_request_count: int
    eod_plan_sha256: str | None
    eod_status: str
    canonical_session_count_after: int
    canonical_first_session_after: str
    provider_request_attempt_count: int
    transient_retry_count: int
    transient_failure_codes: tuple[TransientFailureCode, ...]


class HistoricalBackfillBatchStoppedError(HistoricalBackfillBatchRunnerError):
    """A bounded transient retry sequence stopped with resumable evidence."""

    def __init__(
        self,
        *,
        failed_session: date,
        failure_code: TransientFailureCode,
        completed_sessions: tuple[HistoricalBackfillSessionResultV1, ...],
        external_request_count: int,
        transient_retry_count: int,
        transient_failure_count: int,
    ) -> None:
        self.failed_session = failed_session
        self.failure_code = failure_code
        self.completed_sessions = completed_sessions
        self.external_request_count = external_request_count
        self.transient_retry_count = transient_retry_count
        self.transient_failure_count = transient_failure_count
        super().__init__(
            "historical backfill stopped after bounded transient retries"
        )


@dataclass(frozen=True, slots=True)
class HistoricalBackfillBatchResultV1:
    contract_version: str
    target_session_count: int
    maximum_sessions: int
    completed_sessions: tuple[HistoricalBackfillSessionResultV1, ...]
    status: str
    next_session: str | None
    external_request_count: int
    transient_retry_count: int
    transient_retry_delays_seconds: tuple[int, ...]
    production_session_count: int
    analytics_execution_count: int
    publication_count: int
    deployment_count: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_historical_backfill_batch(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    data_root: Path,
    package_root: Path,
    maximum_sessions: int,
    target_session_count: int = DEFAULT_TARGET_SESSIONS,
    rate_limiter: FixedIntervalRateLimiter | None = None,
    transient_retry_delays_seconds: tuple[
        int, ...
    ] = DEFAULT_TRANSIENT_RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> HistoricalBackfillBatchResultV1:
    """Acquire and apply at most ``maximum_sessions`` adjacent history dates."""

    if not 1 <= maximum_sessions <= MAXIMUM_SESSIONS_PER_INVOCATION:
        raise HistoricalBackfillBatchRunnerError(
            "maximum sessions must be between one and twenty"
        )
    retry_delays = _validate_transient_retry_delays(
        transient_retry_delays_seconds
    )
    root = _validate_data_root(data_root)
    packages = _prepare_package_root(package_root)
    limiter = rate_limiter or FixedIntervalRateLimiter()
    counting_transport = _RequestCountingTransport(transport)
    completed: list[HistoricalBackfillSessionResultV1] = []
    for _ in range(maximum_sessions):
        current = CanonicalEodReadRepository(root).list_session_index()
        target = select_next_historical_backfill_session(
            completed_sessions=current,
            target_session_count=target_session_count,
        )
        if target is None:
            break
        session_request_start = counting_transport.request_count
        failure_codes: list[TransientFailureCode] = []
        for attempt_number in range(len(retry_delays) + 1):
            try:
                session_result = _process_session(
                    config=config,
                    transport=counting_transport,
                    data_root=root,
                    package_root=packages,
                    session_date=target,
                    rate_limiter=limiter,
                )
            except (
                MassiveTransportTimeoutError,
                MassiveTransportUnavailableError,
            ) as exc:
                failure_code = _transient_failure_code(exc)
                failure_codes.append(failure_code)
                if attempt_number == len(retry_delays):
                    raise HistoricalBackfillBatchStoppedError(
                        failed_session=target,
                        failure_code=failure_code,
                        completed_sessions=tuple(completed),
                        external_request_count=counting_transport.request_count,
                        transient_retry_count=(
                            sum(item.transient_retry_count for item in completed)
                            + len(failure_codes)
                            - 1
                        ),
                        transient_failure_count=(
                            sum(
                                len(item.transient_failure_codes)
                                for item in completed
                            )
                            + len(failure_codes)
                        ),
                    ) from exc
                sleep(retry_delays[attempt_number])
                continue
            break
        observed_request_attempts = (
            counting_transport.request_count - session_request_start
        )
        if observed_request_attempts == 0:
            observed_request_attempts = (
                session_result.provider_request_attempt_count
            )
        completed.append(
            replace(
                session_result,
                provider_request_attempt_count=observed_request_attempts,
                transient_retry_count=len(failure_codes),
                transient_failure_codes=tuple(failure_codes),
            )
        )
    final_sessions = CanonicalEodReadRepository(root).list_session_index()
    next_session = select_next_historical_backfill_session(
        completed_sessions=final_sessions,
        target_session_count=target_session_count,
    )
    return HistoricalBackfillBatchResultV1(
        contract_version=CONTRACT_VERSION,
        target_session_count=target_session_count,
        maximum_sessions=maximum_sessions,
        completed_sessions=tuple(completed),
        status="target_complete" if next_session is None else "batch_complete",
        next_session=next_session.isoformat() if next_session is not None else None,
        external_request_count=sum(
            item.provider_request_attempt_count for item in completed
        ),
        transient_retry_count=sum(
            item.transient_retry_count for item in completed
        ),
        transient_retry_delays_seconds=retry_delays,
        production_session_count=len(completed),
        analytics_execution_count=0,
        publication_count=0,
        deployment_count=0,
    )


def _process_session(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    data_root: Path,
    package_root: Path,
    session_date: date,
    rate_limiter: FixedIntervalRateLimiter,
) -> HistoricalBackfillSessionResultV1:
    session_root = _prepare_session_root(package_root, session_date)
    identity_exists = _identity_exists(data_root, session_date)
    identity_requests = 0
    identity_package_reused = False
    identity_plan_sha: str | None = None
    if not identity_exists:
        identity_package = session_root / "identity-package"
        if identity_package.exists():
            identity_package_reused = True
            identity_evidence = read_fetch_package_evidence(
                package_path=identity_package,
                operation="identity",
                expected_session=session_date,
            )
        else:
            fetch_identity_package(
                config=config,
                transport=transport,
                session_date=session_date,
                package_path=identity_package,
                rate_limiter=rate_limiter,
            )
            identity_evidence = read_fetch_package_evidence(
                package_path=identity_package,
                operation="identity",
                expected_session=session_date,
            )
        if not identity_package_reused:
            identity_requests = identity_evidence.request_count
        state = inventory_fingerprint(data_root)
        identity_plan = session_root / f"identity-plan-state={state}.json"
        identity_plan_sha = _ensure_plan(
            operation="identity",
            session_date=session_date,
            package_path=identity_package,
            plan_path=identity_plan,
            data_root=data_root,
            expected_state=state,
        )
        apply_approved_plan(
            plan_path=identity_plan,
            approved_plan_sha256=identity_plan_sha,
            expected_current_state_fingerprint=state,
            data_root=data_root,
            expected_operation="identity",
            expected_session=session_date,
        )
        if not _identity_exists(data_root, session_date):
            raise HistoricalBackfillBatchRunnerError(
                "Identity Apply did not create a formally readable snapshot"
            )

    eod_exists = session_date in frozenset(
        CanonicalEodReadRepository(data_root).list_session_index()
    )
    eod_requests = 0
    eod_package_reused = False
    eod_plan_sha: str | None = None
    if not eod_exists:
        eod_package = session_root / "eod-package"
        if eod_package.exists():
            eod_package_reused = True
            eod_evidence = read_fetch_package_evidence(
                package_path=eod_package,
                operation="eod",
                expected_session=session_date,
            )
        else:
            rate_limiter.wait_before_request()
            fetch_eod_package(
                config=config,
                transport=transport,
                session_date=session_date,
                package_path=eod_package,
            )
            eod_evidence = read_fetch_package_evidence(
                package_path=eod_package,
                operation="eod",
                expected_session=session_date,
            )
        if not eod_package_reused:
            eod_requests = eod_evidence.request_count
        state = inventory_fingerprint(data_root)
        eod_plan = session_root / f"eod-plan-state={state}.json"
        eod_plan_sha = _ensure_plan(
            operation="eod",
            session_date=session_date,
            package_path=eod_package,
            plan_path=eod_plan,
            data_root=data_root,
            expected_state=state,
        )
        apply_approved_plan(
            plan_path=eod_plan,
            approved_plan_sha256=eod_plan_sha,
            expected_current_state_fingerprint=state,
            data_root=data_root,
            expected_operation="eod",
            expected_session=session_date,
        )

    sessions = CanonicalEodReadRepository(data_root).list_session_index()
    if sessions[0] != session_date:
        raise HistoricalBackfillBatchRunnerError(
            "completed session did not extend the canonical left boundary"
        )
    return HistoricalBackfillSessionResultV1(
        session_date=session_date.isoformat(),
        identity_canonical_reused=identity_exists,
        identity_package_reused=identity_package_reused,
        identity_request_count=identity_requests,
        identity_plan_sha256=identity_plan_sha,
        identity_status="reused" if identity_exists else "published_and_verified",
        eod_canonical_reused=eod_exists,
        eod_package_reused=eod_package_reused,
        eod_request_count=eod_requests,
        eod_plan_sha256=eod_plan_sha,
        eod_status="reused" if eod_exists else "published_and_verified",
        canonical_session_count_after=len(sessions),
        canonical_first_session_after=sessions[0].isoformat(),
        provider_request_attempt_count=identity_requests + eod_requests,
        transient_retry_count=0,
        transient_failure_codes=(),
    )


class _RequestCountingTransport:
    """Count every provider call, including failed transient attempts."""

    def __init__(self, delegate: MassiveHttpTransport) -> None:
        self._delegate = delegate
        self.request_count = 0

    def get_json(
        self,
        path: str,
        *,
        params: MassiveParams,
        api_key: SecretStr,
        timeout_seconds: Decimal,
        base_url: str,
    ) -> MassiveJson:
        self.request_count += 1
        return self._delegate.get_json(
            path,
            params=params,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )


def _validate_transient_retry_delays(values: tuple[int, ...]) -> tuple[int, ...]:
    if (
        not isinstance(values, tuple)
        or len(values) > MAXIMUM_TRANSIENT_RETRIES_PER_SESSION
        or any(
            type(value) is not int
            or value <= 0
            or value > MAXIMUM_TRANSIENT_RETRY_DELAY_SECONDS
            for value in values
        )
    ):
        raise HistoricalBackfillBatchRunnerError(
            "transient retry delays exceed the bounded policy"
        )
    return values


def _transient_failure_code(
    error: MassiveTransportTimeoutError | MassiveTransportUnavailableError,
) -> TransientFailureCode:
    if isinstance(error, MassiveTransportTimeoutError):
        return "transport_timeout"
    return "transport_unavailable"


def _ensure_plan(
    *,
    operation: Literal["identity", "eod"],
    session_date: date,
    package_path: Path,
    plan_path: Path,
    data_root: Path,
    expected_state: str,
) -> str:
    if not plan_path.exists():
        if operation == "identity":
            build_identity_plan(
                package_path=package_path,
                plan_path=plan_path,
                data_root=data_root,
            )
        else:
            build_eod_plan(
                package_path=package_path,
                plan_path=plan_path,
                data_root=data_root,
            )
    plan_sha = file_sha256(plan_path)
    evidence = read_catchup_approval_plan_evidence(
        plan_path=plan_path,
        approved_plan_sha256=plan_sha,
        expected_operation=operation,
        expected_session=session_date,
        expected_data_root=data_root,
    )
    if evidence.expected_current_state_fingerprint != expected_state:
        raise HistoricalBackfillBatchRunnerError(
            "reused plan does not bind the current canonical inventory"
        )
    return plan_sha


def _identity_exists(data_root: Path, session_date: date) -> bool:
    logical = (
        data_root
        / "market-data"
        / "snapshots"
        / "instrument-master"
        / f"as_of_date={session_date.isoformat()}"
    )
    if not logical.exists():
        return False
    ParquetInstrumentMasterSnapshotRepository(data_root).inspect_snapshot(session_date)
    return True


def _validate_data_root(path: Path) -> Path:
    root = path.resolve()
    if root != Path("/data/trading-intelligence-platform"):
        raise HistoricalBackfillBatchRunnerError("canonical data root is not approved")
    if path.is_symlink() or not root.is_dir():
        raise HistoricalBackfillBatchRunnerError("canonical data root is unsafe")
    return root


def _prepare_package_root(path: Path) -> Path:
    if not path.is_absolute() or not path.resolve(strict=False).is_relative_to(Path("/tmp")):
        raise HistoricalBackfillBatchRunnerError("package root must be below /tmp")
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise HistoricalBackfillBatchRunnerError("package root is unsafe")
    else:
        path.mkdir(mode=0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise HistoricalBackfillBatchRunnerError("package root must be owner-only")
    return path.resolve()


def _prepare_session_root(root: Path, session_date: date) -> Path:
    path = root / f"session={session_date.isoformat()}"
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise HistoricalBackfillBatchRunnerError("session package root is unsafe")
    else:
        path.mkdir(mode=0o700)
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise HistoricalBackfillBatchRunnerError(
            "session package root must be owner-only"
        )
    return path
