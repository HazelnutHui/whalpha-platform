"""Bounded, resumable acquisition of missing historical Identity source packages."""

from __future__ import annotations

import os
import stat
import time
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal

from pydantic import SecretStr

from tip_api.contracts.market_data.v1.historical_identity_source_custody import (
    DATASET_NAME,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.instrument_master_snapshot import (
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import (
    FixedIntervalRateLimiter,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import (
    fetch_identity_package,
    read_fetch_package_evidence,
)
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveJson,
    MassiveParams,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)


CONTRACT_VERSION = "historical-identity-source-gap-fetch-result/1.0"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
MAXIMUM_SESSIONS_PER_INVOCATION = 24
DEFAULT_TRANSIENT_RETRY_DELAYS_SECONDS = (30, 90)
MAXIMUM_TRANSIENT_RETRIES_PER_SESSION = 2
MAXIMUM_TRANSIENT_RETRY_DELAY_SECONDS = 5 * 60

TransientFailureCode = Literal["transport_timeout", "transport_unavailable"]
ProgressCallback = Callable[[int, int, "HistoricalIdentitySourceGapFetchItem"], None]


class HistoricalIdentitySourceGapFetchError(RuntimeError):
    """Raised when an exact source-gap fetch cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceGapFetchItem:
    session_date: str
    package_reused: bool
    package_request_count: int
    provider_request_attempt_count: int
    transient_retry_count: int
    transient_failure_codes: tuple[TransientFailureCode, ...]
    package_manifest_sha256: str
    package_content_sha256: str
    status: str


class HistoricalIdentitySourceGapFetchStoppedError(
    HistoricalIdentitySourceGapFetchError
):
    """A bounded transient retry sequence stopped with resumable evidence."""

    def __init__(
        self,
        *,
        failed_session: date,
        failure_code: TransientFailureCode,
        completed_items: tuple[HistoricalIdentitySourceGapFetchItem, ...],
        provider_request_attempt_count: int,
        transient_retry_count: int,
        transient_failure_count: int,
    ) -> None:
        self.failed_session = failed_session
        self.failure_code = failure_code
        self.completed_items = completed_items
        self.provider_request_attempt_count = provider_request_attempt_count
        self.transient_retry_count = transient_retry_count
        self.transient_failure_count = transient_failure_count
        super().__init__(
            "historical Identity source-gap fetch stopped after bounded retries"
        )


@dataclass(frozen=True, slots=True)
class HistoricalIdentitySourceGapFetchResult:
    contract_version: str
    status: str
    requested_session_count: int
    completed_session_count: int
    reused_package_count: int
    fetched_package_count: int
    package_request_count: int
    provider_request_attempt_count: int
    transient_retry_count: int
    transient_retry_delays_seconds: tuple[int, ...]
    items: tuple[HistoricalIdentitySourceGapFetchItem, ...]
    canonical_data_write_count: int = 0
    canonical_source_custody_write_count: int = 0
    universe_membership_write_count: int = 0
    analytics_execution_count: int = 0
    publication_count: int = 0
    deployment_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_historical_identity_source_gap_fetch(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    data_root: Path,
    package_root: Path,
    session_dates: tuple[date, ...],
    rate_limiter: FixedIntervalRateLimiter | None = None,
    transient_retry_delays_seconds: tuple[
        int, ...
    ] = DEFAULT_TRANSIENT_RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    progress: ProgressCallback | None = None,
) -> HistoricalIdentitySourceGapFetchResult:
    """Fetch exact canonical source gaps into owner-only temporary custody."""

    sessions = _validate_session_dates(session_dates)
    retry_delays = _validate_transient_retry_delays(
        transient_retry_delays_seconds
    )
    canonical_root = _validate_data_root(data_root)
    packages = _prepare_package_root(package_root)
    canonical_eod_sessions = frozenset(
        CanonicalEodReadRepository(canonical_root).list_session_index()
    )
    for session in sessions:
        _validate_gap_session(
            data_root=canonical_root,
            canonical_eod_sessions=canonical_eod_sessions,
            session_date=session,
        )

    limiter = rate_limiter or FixedIntervalRateLimiter()
    counting_transport = _RequestCountingTransport(transport)
    completed: list[HistoricalIdentitySourceGapFetchItem] = []
    total_failures = 0
    for index, session in enumerate(sessions, start=1):
        session_root = _prepare_session_root(packages, session)
        package_path = session_root / "identity-package"
        package_reused = package_path.exists()
        failure_codes: list[TransientFailureCode] = []
        request_start = counting_transport.request_count
        if not package_reused:
            for attempt_number in range(len(retry_delays) + 1):
                try:
                    fetch_identity_package(
                        config=config,
                        transport=counting_transport,
                        session_date=session,
                        package_path=package_path,
                        rate_limiter=limiter,
                    )
                except (
                    MassiveTransportTimeoutError,
                    MassiveTransportUnavailableError,
                ) as exc:
                    failure_code = _transient_failure_code(exc)
                    failure_codes.append(failure_code)
                    total_failures += 1
                    if attempt_number == len(retry_delays):
                        raise HistoricalIdentitySourceGapFetchStoppedError(
                            failed_session=session,
                            failure_code=failure_code,
                            completed_items=tuple(completed),
                            provider_request_attempt_count=(
                                counting_transport.request_count
                            ),
                            transient_retry_count=total_failures - 1,
                            transient_failure_count=total_failures,
                        ) from exc
                    sleep(retry_delays[attempt_number])
                    continue
                break
        evidence = read_fetch_package_evidence(
            package_path=package_path,
            operation="identity",
            expected_session=session,
        )
        request_attempts = counting_transport.request_count - request_start
        item = HistoricalIdentitySourceGapFetchItem(
            session_date=session.isoformat(),
            package_reused=package_reused,
            package_request_count=evidence.request_count,
            provider_request_attempt_count=request_attempts,
            transient_retry_count=len(failure_codes),
            transient_failure_codes=tuple(failure_codes),
            package_manifest_sha256=evidence.package_manifest_sha256,
            package_content_sha256=evidence.package_content_sha256,
            status="reused_and_verified" if package_reused else "fetched_and_verified",
        )
        completed.append(item)
        if progress is not None:
            progress(index, len(sessions), item)

    return HistoricalIdentitySourceGapFetchResult(
        contract_version=CONTRACT_VERSION,
        status="complete",
        requested_session_count=len(sessions),
        completed_session_count=len(completed),
        reused_package_count=sum(item.package_reused for item in completed),
        fetched_package_count=sum(not item.package_reused for item in completed),
        package_request_count=sum(item.package_request_count for item in completed),
        provider_request_attempt_count=counting_transport.request_count,
        transient_retry_count=sum(item.transient_retry_count for item in completed),
        transient_retry_delays_seconds=retry_delays,
        items=tuple(completed),
    )


class _RequestCountingTransport:
    """Count every provider call without exposing request or response content."""

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


def _validate_session_dates(values: tuple[date, ...]) -> tuple[date, ...]:
    if (
        not values
        or len(values) > MAXIMUM_SESSIONS_PER_INVOCATION
        or values != tuple(sorted(values))
        or len(values) != len(set(values))
        or any(value >= date.today() for value in values)
    ):
        raise HistoricalIdentitySourceGapFetchError(
            "session dates must be one to twenty-four unique ordered historical dates"
        )
    return values


def _validate_gap_session(
    *,
    data_root: Path,
    canonical_eod_sessions: frozenset[date],
    session_date: date,
) -> None:
    if session_date not in canonical_eod_sessions:
        raise HistoricalIdentitySourceGapFetchError(
            "source-gap session is absent from canonical EOD"
        )
    ParquetInstrumentMasterSnapshotRepository(data_root).inspect_snapshot(
        session_date
    )
    source_partition = (
        data_root
        / "market-data"
        / DATASET_NAME
        / "schema_version=1"
        / f"provider={MASSIVE_PROVIDER_ID}"
        / f"as_of_date={session_date.isoformat()}"
    )
    if os.path.lexists(source_partition):
        raise HistoricalIdentitySourceGapFetchError(
            "source-gap session already has canonical source custody"
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
        raise HistoricalIdentitySourceGapFetchError(
            "transient retry delays exceed the bounded policy"
        )
    return values


def _transient_failure_code(
    error: MassiveTransportTimeoutError | MassiveTransportUnavailableError,
) -> TransientFailureCode:
    if isinstance(error, MassiveTransportTimeoutError):
        return "transport_timeout"
    return "transport_unavailable"


def _validate_data_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise HistoricalIdentitySourceGapFetchError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT:
        raise HistoricalIdentitySourceGapFetchError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _prepare_package_root(path: Path) -> Path:
    if (
        not path.is_absolute()
        or not path.resolve(strict=False).is_relative_to(Path("/tmp"))
    ):
        raise HistoricalIdentitySourceGapFetchError(
            "package root must be below /tmp"
        )
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise HistoricalIdentitySourceGapFetchError("package root is unsafe")
    else:
        path.mkdir(mode=0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise HistoricalIdentitySourceGapFetchError(
            "package root must be owner-only"
        )
    return path.resolve()


def _prepare_session_root(root: Path, session_date: date) -> Path:
    path = root / f"session={session_date.isoformat()}"
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise HistoricalIdentitySourceGapFetchError(
                "session package root is unsafe"
            )
    else:
        path.mkdir(mode=0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise HistoricalIdentitySourceGapFetchError(
            "session package root must be owner-only"
        )
    return path
