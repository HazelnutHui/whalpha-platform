"""Coverage-bound reacquisition of missing Reconciled EOD source packages."""

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

from tip_api.contracts.market_data.v1.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageDisposition,
    ReconciledEodSourceCoverageV1,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.providers.massive.config import MassiveProviderConfig
from tip_api.providers.massive.instrument_master_snapshot import (
    FixedIntervalRateLimiter,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import (
    fetch_eod_package,
    read_fetch_package_evidence,
)
from tip_api.providers.massive.transport import (
    MassiveHttpTransport,
    MassiveJson,
    MassiveParams,
    MassiveTransportTimeoutError,
    MassiveTransportUnavailableError,
)
from tip_api.services.historical_identity_source_custody import (
    read_identity_source_custody_at_data_root,
)
from tip_api.services.reconciled_eod_source_coverage import (
    APPROVED_DATA_ROOT,
    LATER_REACQUISITION_SESSIONS_ROOT,
)


CONTRACT_VERSION = "reconciled-eod-source-reacquisition-result/1.0"
APPROVED_PACKAGE_ROOT = LATER_REACQUISITION_SESSIONS_ROOT.parent
MAXIMUM_SESSIONS_PER_INVOCATION = 40
DEFAULT_REQUEST_INTERVAL_SECONDS = Decimal("0.25")
DEFAULT_TRANSIENT_RETRY_DELAYS_SECONDS = (30, 90)
MAXIMUM_TRANSIENT_RETRIES_PER_SESSION = 2
MAXIMUM_TRANSIENT_RETRY_DELAY_SECONDS = 5 * 60

TransientFailureCode = Literal["transport_timeout", "transport_unavailable"]
ProgressCallback = Callable[[int, int, "ReconciledEodSourceReacquisitionItem"], None]


class ReconciledEodSourceReacquisitionError(RuntimeError):
    """Fail-closed error at the later-source acquisition boundary."""


@dataclass(frozen=True, slots=True)
class ReconciledEodSourceReacquisitionItem:
    session_date: str
    package_reused: bool
    package_request_count: int
    provider_request_attempt_count: int
    transient_retry_count: int
    transient_failure_codes: tuple[TransientFailureCode, ...]
    package_manifest_sha256: str
    package_content_sha256: str
    source_observed_at: str
    source_provenance: Literal["later_reacquisition"] = "later_reacquisition"
    status: str = "fetched_and_verified"


class ReconciledEodSourceReacquisitionStoppedError(
    ReconciledEodSourceReacquisitionError
):
    """A bounded transient retry sequence stopped with resumable evidence."""

    def __init__(
        self,
        *,
        failed_session: date,
        failure_code: TransientFailureCode,
        completed_items: tuple[ReconciledEodSourceReacquisitionItem, ...],
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
            "Reconciled EOD source reacquisition stopped after bounded retries"
        )


@dataclass(frozen=True, slots=True)
class ReconciledEodSourceReacquisitionResult:
    contract_version: str
    status: Literal["complete"]
    requested_session_count: int
    completed_session_count: int
    reused_package_count: int
    fetched_package_count: int
    package_request_count: int
    provider_request_attempt_count: int
    transient_retry_count: int
    transient_retry_delays_seconds: tuple[int, ...]
    items: tuple[ReconciledEodSourceReacquisitionItem, ...]
    canonical_data_write_count: Literal[0] = 0
    source_package_write_count: int = 0
    universe_membership_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    production_authority: Literal[False] = False
    research_performance_authorized: Literal[False] = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_reconciled_eod_source_reacquisition(
    *,
    config: MassiveProviderConfig,
    transport: MassiveHttpTransport,
    data_root: Path,
    package_root: Path,
    coverage: ReconciledEodSourceCoverageV1,
    session_dates: tuple[date, ...],
    rate_limiter: FixedIntervalRateLimiter | None = None,
    transient_retry_delays_seconds: tuple[
        int, ...
    ] = DEFAULT_TRANSIENT_RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    progress: ProgressCallback | None = None,
) -> ReconciledEodSourceReacquisitionResult:
    """Fetch only exact missing packages named by one sealed coverage artifact."""

    sessions = _validate_session_dates(session_dates)
    retry_delays = _validate_transient_retry_delays(
        transient_retry_delays_seconds
    )
    canonical_root = _validate_data_root(data_root)
    packages = _prepare_package_root(package_root)
    _validate_sessions_against_coverage(
        data_root=canonical_root,
        coverage=coverage,
        session_dates=sessions,
    )

    limiter = rate_limiter or FixedIntervalRateLimiter(
        interval_seconds=DEFAULT_REQUEST_INTERVAL_SECONDS
    )
    counting_transport = _RequestCountingTransport(transport)
    completed: list[ReconciledEodSourceReacquisitionItem] = []
    total_retries = 0
    total_failures = 0
    for index, session in enumerate(sessions, start=1):
        session_root = _prepare_session_root(packages, session)
        package_path = session_root / "eod-acquisition-package"
        package_reused = os.path.lexists(package_path)
        failure_codes: list[TransientFailureCode] = []
        request_start = counting_transport.request_count
        if not package_reused:
            for attempt_number in range(len(retry_delays) + 1):
                limiter.wait_before_request()
                try:
                    fetch_eod_package(
                        config=config,
                        transport=counting_transport,
                        session_date=session,
                        package_path=package_path,
                    )
                except (
                    MassiveTransportTimeoutError,
                    MassiveTransportUnavailableError,
                ) as exc:
                    failure_code = _transient_failure_code(exc)
                    failure_codes.append(failure_code)
                    total_failures += 1
                    if attempt_number == len(retry_delays):
                        raise ReconciledEodSourceReacquisitionStoppedError(
                            failed_session=session,
                            failure_code=failure_code,
                            completed_items=tuple(completed),
                            provider_request_attempt_count=(
                                counting_transport.request_count
                            ),
                            transient_retry_count=total_retries,
                            transient_failure_count=total_failures,
                        ) from exc
                    total_retries += 1
                    sleep(retry_delays[attempt_number])
                    continue
                break
        evidence = read_fetch_package_evidence(
            package_path=package_path,
            operation="eod",
            expected_session=session,
        )
        request_attempts = counting_transport.request_count - request_start
        item = ReconciledEodSourceReacquisitionItem(
            session_date=session.isoformat(),
            package_reused=package_reused,
            package_request_count=evidence.request_count,
            provider_request_attempt_count=request_attempts,
            transient_retry_count=len(failure_codes),
            transient_failure_codes=tuple(failure_codes),
            package_manifest_sha256=evidence.package_manifest_sha256,
            package_content_sha256=evidence.package_content_sha256,
            source_observed_at=evidence.fetched_at.isoformat(),
            status=(
                "reused_and_verified"
                if package_reused
                else "fetched_and_verified"
            ),
        )
        completed.append(item)
        if progress is not None:
            progress(index, len(sessions), item)

    return ReconciledEodSourceReacquisitionResult(
        contract_version=CONTRACT_VERSION,
        status="complete",
        requested_session_count=len(sessions),
        completed_session_count=len(completed),
        reused_package_count=sum(item.package_reused for item in completed),
        fetched_package_count=sum(not item.package_reused for item in completed),
        package_request_count=sum(item.package_request_count for item in completed),
        provider_request_attempt_count=counting_transport.request_count,
        transient_retry_count=total_retries,
        transient_retry_delays_seconds=retry_delays,
        items=tuple(completed),
        source_package_write_count=sum(not item.package_reused for item in completed),
    )


class _RequestCountingTransport:
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
        or values != tuple(sorted(set(values)))
    ):
        raise ReconciledEodSourceReacquisitionError(
            "sessions must be 1–40 unique ordered dates"
        )
    return values


def _validate_sessions_against_coverage(
    *,
    data_root: Path,
    coverage: ReconciledEodSourceCoverageV1,
    session_dates: tuple[date, ...],
) -> None:
    evidence_by_date = {item.session_date: item for item in coverage.sessions}
    repository = CanonicalEodReadRepository(data_root)
    for session in session_dates:
        evidence = evidence_by_date.get(session)
        ordinary_source_gap = (
            evidence is not None
            and evidence.disposition
            == ReconciledEodSourceCoverageDisposition.MISSING
            and evidence.reason_codes
            == ("grouped_daily_source_package_missing",)
        )
        identity_blocked_source_gap = (
            evidence is not None
            and evidence.disposition
            == ReconciledEodSourceCoverageDisposition.INVALID
            and evidence.reason_codes
            == (
                "grouped_daily_source_package_missing",
                "identity_source_custody_unavailable",
            )
        )
        if (
            evidence is None
            or not (ordinary_source_gap or identity_blocked_source_gap)
            or evidence.canonical_eod_fingerprint is None
            or evidence.canonical_identity_fingerprint is None
        ):
            raise ReconciledEodSourceReacquisitionError(
                "session is not one exact Grouped Daily gap in sealed coverage"
            )
        current = repository.inspect_session(session)
        if (
            current.content_fingerprint != evidence.canonical_eod_fingerprint
            or current.identity_snapshot_fingerprint
            != evidence.canonical_identity_fingerprint
        ):
            raise ReconciledEodSourceReacquisitionError(
                "canonical source-gap binding changed after coverage sealing"
            )
        if ordinary_source_gap:
            identity_source = read_identity_source_custody_at_data_root(
                data_root=data_root,
                provider=MASSIVE_PROVIDER_ID,
                session_date=session,
            )
            if (
                identity_source.manifest.canonical_snapshot_fingerprint
                != evidence.canonical_identity_fingerprint
            ):
                raise ReconciledEodSourceReacquisitionError(
                    "canonical source-gap binding changed after coverage sealing"
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
        raise ReconciledEodSourceReacquisitionError(
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
        raise ReconciledEodSourceReacquisitionError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT.resolve(strict=True):
        raise ReconciledEodSourceReacquisitionError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _prepare_package_root(path: Path) -> Path:
    if path != APPROVED_PACKAGE_ROOT or not path.is_absolute():
        raise ReconciledEodSourceReacquisitionError(
            "source package root is not the approved Dell custody"
        )
    _owner_only_directory(path.parent)
    if os.path.lexists(path):
        _owner_only_directory(path)
    else:
        path.mkdir(mode=0o700)
        _fsync_directory(path.parent)
    root = _owner_only_directory(path)
    sessions = root / "sessions"
    if not sessions.exists():
        sessions.mkdir(mode=0o700)
        _fsync_directory(root)
    return _owner_only_directory(sessions)


def _prepare_session_root(root: Path, session_date: date) -> Path:
    path = root / f"session_date={session_date.isoformat()}"
    if os.path.lexists(path):
        _owner_only_directory(path)
    else:
        path.mkdir(mode=0o700)
        _fsync_directory(root)
    return _owner_only_directory(path)


def _owner_only_directory(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ReconciledEodSourceReacquisitionError(
            "source package directory is unavailable"
        )
    resolved = path.resolve(strict=True)
    metadata = resolved.stat()
    if (
        resolved != path
        or metadata.st_uid != os.geteuid()
        or not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ReconciledEodSourceReacquisitionError(
            "source package directory custody differs"
        )
    return resolved


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
