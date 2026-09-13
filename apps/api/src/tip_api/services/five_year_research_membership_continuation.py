"""Resumable Dell-local construction of missing research Membership sessions."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import socket
import stat
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import UniverseMembershipPartitionManifestV1
from tip_api.persistence.security_evidence import CompletedSecurityEvidenceSnapshot
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.security_evidence import (
    read_completed_security_evidence_snapshot,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.five_year_research_foundation_census import (
    RESEARCH_MEMBERSHIP_METHODOLOGY,
    _membership_publication_dates,
    _research_membership_inventory,
)
from tip_api.services.historical_universe_membership_shadow_batch import (
    HistoricalUniverseMembershipCanonicalSourceBatchResult,
    run_historical_universe_membership_canonical_source_batch,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


CONTRACT_VERSION = "five-year-research-membership-continuation/1.0"
PLAN_FILE_NAME = "continuation-plan.json"
MAXIMUM_WORKERS = 4
MAXIMUM_BATCH_SIZE = 5
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
IDENTITY_SOURCE_DATASET = "provider-identity-reference-observation"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"


class FiveYearResearchMembershipContinuationError(RuntimeError):
    """Raised when the continuation boundary or result cannot be trusted."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FiveYearResearchMembershipBatchV1(FrozenModel):
    batch_id: str = Field(pattern=r"^batch-[0-9]{4}$")
    session_dates: tuple[date, ...] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def dates_are_unique_and_ordered(self) -> "FiveYearResearchMembershipBatchV1":
        if self.session_dates != tuple(sorted(set(self.session_dates))):
            raise ValueError("continuation batch sessions must be unique and ordered")
        return self


class FiveYearResearchMembershipContinuationPlanV1(FrozenModel):
    contract_version: Literal[
        "five-year-research-membership-continuation/1.0"
    ] = CONTRACT_VERSION
    data_root: str
    candidate_root: str
    code_revision: str = Field(pattern=_REVISION_PATTERN)
    methodology_version: str
    catalog_as_of_date: date
    evaluated_at: datetime
    target_first_session: date
    target_last_session: date
    target_session_count: int = Field(ge=1)
    target_session_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    initial_research_session_count: int = Field(ge=0)
    initial_signal_session_count: int = Field(ge=0)
    initial_combined_session_count: int = Field(ge=0)
    unavailable_source_session_dates: tuple[date, ...]
    intended_session_count: int = Field(ge=0)
    batches: tuple[FiveYearResearchMembershipBatchV1, ...]
    performance_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "FiveYearResearchMembershipContinuationPlanV1":
        if normalize_utc_datetime(self.evaluated_at) != self.evaluated_at:
            raise ValueError("continuation evaluation time must be normalized UTC")
        if self.data_root != str(APPROVED_DATA_ROOT):
            raise ValueError("continuation data root differs")
        candidate = Path(self.candidate_root)
        if (
            not candidate.is_absolute()
            or candidate == Path("/tmp")
            or not candidate.is_relative_to(Path("/tmp"))
        ):
            raise ValueError("continuation candidate root must remain below /tmp")
        if self.target_first_session > self.target_last_session:
            raise ValueError("continuation target interval is inverted")
        if self.initial_combined_session_count > self.target_session_count:
            raise ValueError("continuation initial coverage exceeds target")
        batch_ids = tuple(item.batch_id for item in self.batches)
        if batch_ids != tuple(
            f"batch-{index:04d}" for index in range(1, len(self.batches) + 1)
        ):
            raise ValueError("continuation batch identifiers differ")
        intended_dates = tuple(
            session for batch in self.batches for session in batch.session_dates
        )
        if len(intended_dates) != self.intended_session_count:
            raise ValueError("continuation intended-session count differs")
        if len(set(intended_dates)) != len(intended_dates):
            raise ValueError("continuation intended sessions overlap")
        if intended_dates != tuple(sorted(intended_dates)):
            raise ValueError("continuation intended sessions are unordered")
        if set(intended_dates) & set(self.unavailable_source_session_dates):
            raise ValueError("continuation includes an unavailable source session")
        if _plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("continuation plan fingerprint differs")
        return self


class FiveYearResearchMembershipContinuationResultV1(FrozenModel):
    contract_version: Literal[
        "five-year-research-membership-continuation/1.0"
    ] = CONTRACT_VERSION
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    selected_batch_count: int = Field(ge=0)
    completed_batch_count: int = Field(ge=0)
    failed_batch_count: int = Field(ge=0)
    intended_session_count: int = Field(ge=0)
    candidate_completed_session_count: int = Field(ge=0)
    remaining_session_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    failed_batches: tuple[str, ...]
    status: Literal["completed", "partial", "completed_with_failures"]
    worker_count: int = Field(ge=0, le=4)
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    performance_authorized: Literal[False] = False
    production_authorized: Literal[False] = False


ProgressCallback = Callable[[dict[str, object]], None]


def prepare_five_year_research_membership_continuation(
    *,
    data_root: Path,
    candidate_root: Path,
    catalog_as_of_date: date,
    evaluated_at: datetime,
    code_revision: str,
    calendar: MarketSessionCalendar | None = None,
) -> FiveYearResearchMembershipContinuationPlanV1:
    """Create one immutable continuation plan or formally resume the same plan."""

    root = _validated_data_root(data_root)
    candidate = _prepare_candidate_root(candidate_root)
    plan_path = candidate / PLAN_FILE_NAME
    normalized_evaluated_at = normalize_utc_datetime(evaluated_at)
    if plan_path.exists() or plan_path.is_symlink():
        plan = _read_plan(plan_path)
        _require_matching_invocation(
            plan,
            data_root=root,
            candidate_root=candidate,
            catalog_as_of_date=catalog_as_of_date,
            evaluated_at=normalized_evaluated_at,
            code_revision=code_revision,
        )
        return plan

    session_calendar = calendar or ExchangeCalendar()
    eod_sessions = CanonicalEodReadRepository(root).list_session_index()
    if not eod_sessions:
        raise FiveYearResearchMembershipContinuationError(
            "canonical EOD session index is empty"
        )
    target_end = eod_sessions[-1]
    target_anchor = _subtract_calendar_years(target_end, 5)
    target_sessions = session_calendar.sessions_in_range(target_anchor, target_end)
    if not target_sessions or target_sessions[-1] != target_end:
        raise FiveYearResearchMembershipContinuationError(
            "rolling five-year target does not end at latest EOD"
        )
    if any(session not in set(eod_sessions) for session in target_sessions):
        raise FiveYearResearchMembershipContinuationError(
            "rolling five-year EOD target is incomplete"
        )

    research_dates = tuple(_research_membership_inventory(root)["session_dates"])
    signal_dates = _membership_publication_dates(root)
    target_set = set(target_sessions)
    initial_combined = target_set & (set(research_dates) | set(signal_dates))
    source_dates = _identity_source_session_dates(root)
    unavailable = tuple(
        session
        for session in target_sessions
        if session not in source_dates and session not in initial_combined
    )
    intended = tuple(
        session
        for session in target_sessions
        if session not in initial_combined and session in source_dates
    )
    batches = _contiguous_batches(target_sessions, intended)
    payload = {
        "contract_version": CONTRACT_VERSION,
        "data_root": str(root),
        "candidate_root": str(candidate),
        "code_revision": code_revision,
        "methodology_version": RESEARCH_MEMBERSHIP_METHODOLOGY,
        "catalog_as_of_date": catalog_as_of_date,
        "evaluated_at": normalized_evaluated_at,
        "target_first_session": target_sessions[0],
        "target_last_session": target_sessions[-1],
        "target_session_count": len(target_sessions),
        "target_session_fingerprint": _date_fingerprint(target_sessions),
        "initial_research_session_count": len(target_set & set(research_dates)),
        "initial_signal_session_count": len(target_set & set(signal_dates)),
        "initial_combined_session_count": len(initial_combined),
        "unavailable_source_session_dates": unavailable,
        "intended_session_count": len(intended),
        "batches": batches,
        "performance_authorized": False,
        "production_authorized": False,
        "external_request_count": 0,
    }
    plan = FiveYearResearchMembershipContinuationPlanV1.model_validate(
        {**payload, "logical_fingerprint": _fingerprint(payload)}
    )
    _write_plan(plan_path, plan)
    return plan


def execute_five_year_research_membership_continuation(
    plan: FiveYearResearchMembershipContinuationPlanV1,
    *,
    workers: int = MAXIMUM_WORKERS,
    batch_limit: int | None = None,
    progress: ProgressCallback | None = None,
) -> FiveYearResearchMembershipContinuationResultV1:
    """Build selected missing plan batches into tmp-only candidate custody."""

    if not 1 <= workers <= MAXIMUM_WORKERS:
        raise FiveYearResearchMembershipContinuationError(
            "continuation workers must be between one and four"
        )
    if batch_limit is not None and batch_limit < 1:
        raise FiveYearResearchMembershipContinuationError(
            "continuation batch limit must be positive"
        )
    candidate_root = _validated_candidate_root(Path(plan.candidate_root))
    completed_dates, record_count = _candidate_session_inventory(
        candidate_root,
        intended_dates={
            session for batch in plan.batches for session in batch.session_dates
        },
        methodology_version=plan.methodology_version,
    )
    selected = tuple(
        batch
        for batch in plan.batches
        if not set(batch.session_dates).issubset(completed_dates)
    )
    if batch_limit is not None:
        selected = selected[:batch_limit]
    if not selected:
        return _continuation_result(
            plan,
            selected_batch_count=0,
            completed_batch_count=0,
            failed_batches=(),
            candidate_completed_session_count=len(completed_dates),
            record_count=record_count,
            worker_count=0,
        )

    batches_root = candidate_root / "batches"
    _prepare_owner_only_directory(batches_root)
    effective_workers = min(workers, len(selected))
    jobs = tuple(
        (
            batch,
            Path(plan.data_root),
            batches_root / batch.batch_id,
            plan.catalog_as_of_date,
            plan.evaluated_at,
        )
        for batch in selected
    )
    completed_batches = 0
    failed_batches: list[str] = []
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=effective_workers,
        mp_context=context,
        initializer=_initialize_worker,
        initargs=(Path(plan.data_root), plan.catalog_as_of_date),
    ) as executor:
        futures = {executor.submit(_build_batch, job): job[0] for job in jobs}
        for future in as_completed(futures):
            batch = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failed_batches.append(batch.batch_id)
                if progress is not None:
                    progress(
                        {
                            "event": "batch_failed",
                            "batch_id": batch.batch_id,
                            "completed_batch_count": completed_batches,
                            "selected_batch_count": len(selected),
                            "error_type": type(exc).__name__,
                        }
                    )
                continue
            if result.failed_session_count:
                failed_batches.append(batch.batch_id)
            else:
                completed_batches += 1
            if progress is not None:
                progress(
                    {
                        "event": "batch_completed",
                        "batch_id": batch.batch_id,
                        "session_dates": [item.session_date for item in result.sessions],
                        "completed_batch_count": completed_batches,
                        "selected_batch_count": len(selected),
                        "failed_batch_count": len(failed_batches),
                    }
                )

    completed_dates, record_count = _candidate_session_inventory(
        candidate_root,
        intended_dates={
            session for batch in plan.batches for session in batch.session_dates
        },
        methodology_version=plan.methodology_version,
    )
    return _continuation_result(
        plan,
        selected_batch_count=len(selected),
        completed_batch_count=completed_batches,
        failed_batches=tuple(sorted(failed_batches)),
        candidate_completed_session_count=len(completed_dates),
        record_count=record_count,
        worker_count=effective_workers,
    )


_WORKER_SECURITY_SNAPSHOT: CompletedSecurityEvidenceSnapshot | None = None


def _initialize_worker(data_root: Path, catalog_as_of_date: date) -> None:
    global _WORKER_SECURITY_SNAPSHOT

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise FiveYearResearchMembershipContinuationError(
            "network access is disabled in Membership continuation workers"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
    _WORKER_SECURITY_SNAPSHOT = read_completed_security_evidence_snapshot(
        data_root,
        as_of_date=catalog_as_of_date,
    )


def _build_batch(
    job: tuple[
        FiveYearResearchMembershipBatchV1,
        Path,
        Path,
        date,
        datetime,
    ],
) -> HistoricalUniverseMembershipCanonicalSourceBatchResult:
    batch, data_root, output_root, catalog_as_of_date, evaluated_at = job
    if _WORKER_SECURITY_SNAPSHOT is None:
        raise FiveYearResearchMembershipContinuationError(
            "Membership continuation worker catalog is unavailable"
        )
    return run_historical_universe_membership_canonical_source_batch(
        data_root=data_root,
        sessions=batch.session_dates,
        catalog_as_of_date=catalog_as_of_date,
        evaluated_at=evaluated_at,
        output_root=output_root,
        security_snapshot=_WORKER_SECURITY_SNAPSHOT,
    )


def _continuation_result(
    plan: FiveYearResearchMembershipContinuationPlanV1,
    *,
    selected_batch_count: int,
    completed_batch_count: int,
    failed_batches: tuple[str, ...],
    candidate_completed_session_count: int,
    record_count: int,
    worker_count: int,
) -> FiveYearResearchMembershipContinuationResultV1:
    remaining = plan.intended_session_count - candidate_completed_session_count
    status = (
        "completed_with_failures"
        if failed_batches
        else "completed"
        if remaining == 0
        else "partial"
    )
    return FiveYearResearchMembershipContinuationResultV1(
        plan_logical_fingerprint=plan.logical_fingerprint,
        selected_batch_count=selected_batch_count,
        completed_batch_count=completed_batch_count,
        failed_batch_count=len(failed_batches),
        intended_session_count=plan.intended_session_count,
        candidate_completed_session_count=candidate_completed_session_count,
        remaining_session_count=remaining,
        record_count=record_count,
        failed_batches=failed_batches,
        status=status,
        worker_count=worker_count,
    )


def _contiguous_batches(
    target_sessions: tuple[date, ...],
    intended_sessions: tuple[date, ...],
) -> tuple[FiveYearResearchMembershipBatchV1, ...]:
    intended = set(intended_sessions)
    groups: list[list[date]] = []
    current: list[date] = []
    for session in target_sessions:
        if session not in intended:
            if current:
                groups.append(current)
                current = []
            continue
        current.append(session)
        if len(current) == MAXIMUM_BATCH_SIZE:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return tuple(
        FiveYearResearchMembershipBatchV1(
            batch_id=f"batch-{index:04d}",
            session_dates=tuple(group),
        )
        for index, group in enumerate(groups, start=1)
    )


def _identity_source_session_dates(data_root: Path) -> set[date]:
    root = (
        data_root
        / "market-data"
        / IDENTITY_SOURCE_DATASET
        / "schema_version=1"
        / f"provider={MASSIVE_PROVIDER_ID}"
    )
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise FiveYearResearchMembershipContinuationError(
            "canonical Identity source root is unavailable or unsafe"
        )
    sessions: set[date] = set()
    for partition in sorted(root.glob("as_of_date=*")):
        if partition.is_symlink() or not partition.is_dir():
            raise FiveYearResearchMembershipContinuationError(
                "canonical Identity source partition is unsafe"
            )
        try:
            session = date.fromisoformat(
                partition.name.removeprefix("as_of_date=")
            )
        except ValueError as exc:
            raise FiveYearResearchMembershipContinuationError(
                "canonical Identity source session name is malformed"
            ) from exc
        if not (partition / "manifest.json").is_file() or not (
            partition / "part-00000.parquet"
        ).is_file():
            raise FiveYearResearchMembershipContinuationError(
                "canonical Identity source partition is incomplete"
            )
        sessions.add(session)
    return sessions


def _candidate_session_inventory(
    candidate_root: Path,
    *,
    intended_dates: set[date],
    methodology_version: str,
) -> tuple[set[date], int]:
    dates: set[date] = set()
    records = 0
    for path in sorted(candidate_root.rglob("manifest.json")):
        try:
            manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
                path.read_bytes()
            )
        except Exception:
            continue
        if manifest.methodology_version != methodology_version:
            raise FiveYearResearchMembershipContinuationError(
                "candidate Membership methodology differs"
            )
        if manifest.session_date not in intended_dates:
            raise FiveYearResearchMembershipContinuationError(
                "candidate Membership session is outside the continuation plan"
            )
        if manifest.session_date in dates:
            raise FiveYearResearchMembershipContinuationError(
                "candidate Membership session is duplicated"
            )
        parquet_path = path.parent / "part-00000.parquet"
        if path.parent.is_symlink() or not parquet_path.is_file():
            raise FiveYearResearchMembershipContinuationError(
                "candidate Membership partition is incomplete"
            )
        dates.add(manifest.session_date)
        records += manifest.record_count
    return dates, records


def _prepare_candidate_root(path: Path) -> Path:
    if (
        not path.is_absolute()
        or path == Path("/tmp")
        or not path.is_relative_to(Path("/tmp"))
    ):
        raise FiveYearResearchMembershipContinuationError(
            "continuation candidate root must remain below /tmp"
        )
    if path.exists() or path.is_symlink():
        return _validated_candidate_root(path)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise FiveYearResearchMembershipContinuationError(
            "continuation candidate parent is unavailable"
        )
    path.mkdir(mode=0o700)
    return _validated_candidate_root(path)


def _validated_candidate_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
        raise FiveYearResearchMembershipContinuationError(
            "continuation candidate root is unavailable or unsafe"
        )
    metadata = path.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise FiveYearResearchMembershipContinuationError(
            "continuation candidate root must be owner-only"
        )
    for item in path.rglob("*"):
        if item.is_symlink():
            raise FiveYearResearchMembershipContinuationError(
                "continuation candidate tree contains a symlink"
            )
    return path


def _prepare_owner_only_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if (
            path.is_symlink()
            or not path.is_dir()
            or stat.S_IMODE(path.stat().st_mode) != 0o700
            or path.stat().st_uid != os.geteuid()
        ):
            raise FiveYearResearchMembershipContinuationError(
                "continuation batches root is unsafe"
            )
        return
    path.mkdir(mode=0o700)


def _validated_data_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
        raise FiveYearResearchMembershipContinuationError(
            "continuation data root is unavailable or unsafe"
        )
    if path != APPROVED_DATA_ROOT:
        raise FiveYearResearchMembershipContinuationError(
            "continuation data root is not approved"
        )
    return path


def _read_plan(path: Path) -> FiveYearResearchMembershipContinuationPlanV1:
    if path.is_symlink() or not path.is_file():
        raise FiveYearResearchMembershipContinuationError(
            "continuation plan is unavailable or unsafe"
        )
    if stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise FiveYearResearchMembershipContinuationError(
            "continuation plan must be owner-read-only"
        )
    try:
        return FiveYearResearchMembershipContinuationPlanV1.model_validate_json(
            path.read_bytes()
        )
    except Exception as exc:
        raise FiveYearResearchMembershipContinuationError(
            "continuation plan validation failed"
        ) from exc


def _write_plan(
    path: Path,
    plan: FiveYearResearchMembershipContinuationPlanV1,
) -> None:
    staging = path.parent / f".{path.name}.staging.{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise FiveYearResearchMembershipContinuationError(
            "continuation plan staging path already exists"
        )
    payload = json.dumps(
        plan.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        with staging.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        staging.chmod(0o400)
        staging.replace(path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            staging.unlink()
        raise


def _require_matching_invocation(
    plan: FiveYearResearchMembershipContinuationPlanV1,
    *,
    data_root: Path,
    candidate_root: Path,
    catalog_as_of_date: date,
    evaluated_at: datetime,
    code_revision: str,
) -> None:
    if (
        plan.data_root != str(data_root)
        or plan.candidate_root != str(candidate_root)
        or plan.catalog_as_of_date != catalog_as_of_date
        or plan.evaluated_at != evaluated_at
        or plan.code_revision != code_revision
    ):
        raise FiveYearResearchMembershipContinuationError(
            "continuation invocation differs from the immutable plan"
        )


def _plan_fingerprint(
    plan: FiveYearResearchMembershipContinuationPlanV1,
) -> str:
    return _fingerprint(
        plan.model_dump(mode="python", exclude={"logical_fingerprint"})
    )


def _date_fingerprint(sessions: tuple[date, ...]) -> str:
    return _fingerprint([session.isoformat() for session in sessions])


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"unsupported continuation fingerprint value: {type(value)!r}")


def _subtract_calendar_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)
