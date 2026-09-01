"""Credential-free planning for a resumable historical research foundation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum

from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


CONTRACT_VERSION = "historical-research-backfill-plan/1.0"
MINIMUM_TARGET_SESSIONS = 252
MAXIMUM_TARGET_SESSIONS = 504
DEFAULT_TARGET_SESSIONS = 300
MAXIMUM_BATCH_SIZE = 3
DEFAULT_ACTIVE_IDENTITY_PAGES_OBSERVED = 14
DEFAULT_ACTIVE_IDENTITY_PAGE_CEILING = 20
DEFAULT_SERIAL_PACE_SECONDS = 15
DEFAULT_EOD_BYTES_PER_SESSION = 1_050_391
DEFAULT_IDENTITY_BYTES_PER_SESSION = 2_235_974
REQUIRED_BLOCKER_CODES = (
    "canonical_corporate_action_coverage_absent",
    "daily_point_in_time_membership_absent",
    "equal_capability_source_permission_unresolved",
    "historical_coverage_publication_absent",
    "instrument_lifecycle_terminal_coverage_incomplete",
    "reconciled_adjustment_ledger_absent",
    "representative_historical_pilot_incomplete",
)

_SHA256 = re.compile(r"[0-9a-f]{64}")


class HistoricalBackfillPlannerError(ValueError):
    """Raised when an exact historical backfill plan cannot be formed."""


class HistoricalBackfillStatus(StrEnum):
    BLOCKED_PENDING_PILOT = "blocked_pending_pilot"


class HistoricalBackfillNextAction(StrEnum):
    RESOLVE_EXTERNAL_GATES = "resolve_external_gates_then_run_representative_pilot"


@dataclass(frozen=True, slots=True)
class HistoricalBackfillInventoryV1:
    inventory_fingerprint: str
    completed_eod_sessions: tuple[date, ...]
    completed_identity_sessions: tuple[date, ...]


@dataclass(frozen=True, slots=True)
class HistoricalBackfillRequestV1:
    target_session_count: int = DEFAULT_TARGET_SESSIONS
    batch_size: int = MAXIMUM_BATCH_SIZE
    active_identity_pages_observed_per_session: int = (
        DEFAULT_ACTIVE_IDENTITY_PAGES_OBSERVED
    )
    active_identity_page_ceiling_per_session: int = (
        DEFAULT_ACTIVE_IDENTITY_PAGE_CEILING
    )
    serial_pace_seconds: int = DEFAULT_SERIAL_PACE_SECONDS
    eod_bytes_per_session: int = DEFAULT_EOD_BYTES_PER_SESSION
    identity_bytes_per_session: int = DEFAULT_IDENTITY_BYTES_PER_SESSION
    blocker_codes: tuple[str, ...] = REQUIRED_BLOCKER_CODES


@dataclass(frozen=True, slots=True)
class HistoricalBackfillBatchV1:
    execution_sequence: int
    target_sessions: tuple[str, ...]
    missing_eod_sessions: tuple[str, ...]
    missing_identity_sessions: tuple[str, ...]
    is_representative_pilot: bool
    depends_on_prior_batch_completion: bool
    grouped_daily_request_count: int
    active_identity_request_observed_projection: int
    active_identity_request_ceiling: int
    transport_seconds_observed_projection: int
    transport_seconds_at_ceiling: int


@dataclass(frozen=True, slots=True)
class HistoricalBackfillPlanV1:
    contract_version: str
    calendar_id: str
    calendar_version: str
    inventory_fingerprint: str
    current_first_session: str
    current_last_session: str
    current_session_count: int
    target_first_session: str
    target_last_session: str
    target_session_count: int
    missing_session_count: int
    batch_size: int
    batch_count: int
    representative_pilot_sessions: tuple[str, ...]
    batches: tuple[HistoricalBackfillBatchV1, ...]
    grouped_daily_request_count: int
    active_identity_request_observed_projection: int
    active_identity_request_ceiling: int
    total_request_observed_projection: int
    total_request_ceiling: int
    serial_pace_seconds: int
    transport_seconds_observed_projection: int
    transport_seconds_at_ceiling: int
    estimated_incremental_canonical_bytes: int
    recommended_staging_reserve_bytes: int
    provider_requests_serial_only: bool
    offline_parallelism_permitted_after_source_custody: bool
    blocker_codes: tuple[str, ...]
    status: HistoricalBackfillStatus
    next_action: HistoricalBackfillNextAction
    acquisition_authorized: bool
    apply_authorized: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_authorized: bool
    performance_claims_authorized: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def plan_historical_research_backfill(
    *,
    inventory: HistoricalBackfillInventoryV1,
    request: HistoricalBackfillRequestV1 | None = None,
    calendar: MarketSessionCalendar | None = None,
) -> HistoricalBackfillPlanV1:
    """Build an exact non-authorizing plan with no filesystem or network I/O."""

    requested = request or HistoricalBackfillRequestV1()
    session_calendar = calendar or ExchangeCalendar()
    _validate_inventory(inventory, session_calendar)
    _validate_request(requested)

    current = inventory.completed_eod_sessions
    target = _target_sessions(
        end_session=current[-1],
        count=requested.target_session_count,
        calendar=session_calendar,
    )
    current_set = frozenset(current)
    identity_set = frozenset(inventory.completed_identity_sessions)
    target_set = frozenset(target)
    if not current_set.issubset(target_set):
        raise HistoricalBackfillPlannerError(
            "current inventory extends outside the requested target interval"
        )
    missing_eod = tuple(item for item in target if item not in current_set)
    missing_identity = tuple(item for item in target if item not in identity_set)
    if missing_eod != missing_identity:
        raise HistoricalBackfillPlannerError(
            "EOD and point-in-time Identity gaps must match before bulk planning"
        )
    if current and missing_eod and session_calendar.next_session(missing_eod[-1]) != current[0]:
        raise HistoricalBackfillPlannerError(
            "missing history must be one contiguous prefix adjacent to current history"
        )

    batches = _build_batches(missing_eod, requested)
    grouped_daily_requests = len(missing_eod)
    observed_identity_requests = (
        len(missing_identity) * requested.active_identity_pages_observed_per_session
    )
    ceiling_identity_requests = (
        len(missing_identity) * requested.active_identity_page_ceiling_per_session
    )
    observed_total = grouped_daily_requests + observed_identity_requests
    ceiling_total = grouped_daily_requests + ceiling_identity_requests
    canonical_bytes = (
        len(missing_eod) * requested.eod_bytes_per_session
        + len(missing_identity) * requested.identity_bytes_per_session
    )
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "calendar_id": session_calendar.calendar_id,
        "calendar_version": session_calendar.calendar_version,
        "inventory_fingerprint": inventory.inventory_fingerprint,
        "current_first_session": current[0].isoformat(),
        "current_last_session": current[-1].isoformat(),
        "current_session_count": len(current),
        "target_first_session": target[0].isoformat(),
        "target_last_session": target[-1].isoformat(),
        "target_session_count": len(target),
        "missing_session_count": len(missing_eod),
        "batch_size": requested.batch_size,
        "batch_count": len(batches),
        "representative_pilot_sessions": (
            batches[0].target_sessions if batches else ()
        ),
        "batches": [asdict(item) for item in batches],
        "grouped_daily_request_count": grouped_daily_requests,
        "active_identity_request_observed_projection": observed_identity_requests,
        "active_identity_request_ceiling": ceiling_identity_requests,
        "total_request_observed_projection": observed_total,
        "total_request_ceiling": ceiling_total,
        "serial_pace_seconds": requested.serial_pace_seconds,
        "transport_seconds_observed_projection": (
            observed_total * requested.serial_pace_seconds
        ),
        "transport_seconds_at_ceiling": ceiling_total * requested.serial_pace_seconds,
        "estimated_incremental_canonical_bytes": canonical_bytes,
        "recommended_staging_reserve_bytes": canonical_bytes * 2,
        "blocker_codes": requested.blocker_codes,
        "status": HistoricalBackfillStatus.BLOCKED_PENDING_PILOT.value,
        "next_action": HistoricalBackfillNextAction.RESOLVE_EXTERNAL_GATES.value,
        "authorization_status": "not_authorized",
    }
    fingerprint = _fingerprint(payload)
    return HistoricalBackfillPlanV1(
        contract_version=CONTRACT_VERSION,
        calendar_id=session_calendar.calendar_id,
        calendar_version=session_calendar.calendar_version,
        inventory_fingerprint=inventory.inventory_fingerprint,
        current_first_session=current[0].isoformat(),
        current_last_session=current[-1].isoformat(),
        current_session_count=len(current),
        target_first_session=target[0].isoformat(),
        target_last_session=target[-1].isoformat(),
        target_session_count=len(target),
        missing_session_count=len(missing_eod),
        batch_size=requested.batch_size,
        batch_count=len(batches),
        representative_pilot_sessions=batches[0].target_sessions if batches else (),
        batches=batches,
        grouped_daily_request_count=grouped_daily_requests,
        active_identity_request_observed_projection=observed_identity_requests,
        active_identity_request_ceiling=ceiling_identity_requests,
        total_request_observed_projection=observed_total,
        total_request_ceiling=ceiling_total,
        serial_pace_seconds=requested.serial_pace_seconds,
        transport_seconds_observed_projection=(
            observed_total * requested.serial_pace_seconds
        ),
        transport_seconds_at_ceiling=ceiling_total * requested.serial_pace_seconds,
        estimated_incremental_canonical_bytes=canonical_bytes,
        recommended_staging_reserve_bytes=canonical_bytes * 2,
        provider_requests_serial_only=True,
        offline_parallelism_permitted_after_source_custody=True,
        blocker_codes=requested.blocker_codes,
        status=HistoricalBackfillStatus.BLOCKED_PENDING_PILOT,
        next_action=HistoricalBackfillNextAction.RESOLVE_EXTERNAL_GATES,
        acquisition_authorized=False,
        apply_authorized=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_authorized=False,
        performance_claims_authorized=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=fingerprint,
    )


def _target_sessions(
    *, end_session: date, count: int, calendar: MarketSessionCalendar
) -> tuple[date, ...]:
    sessions = [end_session]
    while len(sessions) < count:
        sessions.append(calendar.previous_session(sessions[-1]))
    return tuple(reversed(sessions))


def _build_batches(
    missing_sessions: tuple[date, ...], request: HistoricalBackfillRequestV1
) -> tuple[HistoricalBackfillBatchV1, ...]:
    chunks: list[tuple[date, ...]] = []
    end = len(missing_sessions)
    while end:
        start = max(0, end - request.batch_size)
        chunks.append(missing_sessions[start:end])
        end = start
    batches: list[HistoricalBackfillBatchV1] = []
    for sequence, chunk in enumerate(chunks, start=1):
        grouped = len(chunk)
        observed_identity = (
            grouped * request.active_identity_pages_observed_per_session
        )
        ceiling_identity = grouped * request.active_identity_page_ceiling_per_session
        batches.append(
            HistoricalBackfillBatchV1(
                execution_sequence=sequence,
                target_sessions=tuple(item.isoformat() for item in chunk),
                missing_eod_sessions=tuple(item.isoformat() for item in chunk),
                missing_identity_sessions=tuple(item.isoformat() for item in chunk),
                is_representative_pilot=sequence == 1,
                depends_on_prior_batch_completion=sequence > 1,
                grouped_daily_request_count=grouped,
                active_identity_request_observed_projection=observed_identity,
                active_identity_request_ceiling=ceiling_identity,
                transport_seconds_observed_projection=(
                    (grouped + observed_identity) * request.serial_pace_seconds
                ),
                transport_seconds_at_ceiling=(
                    (grouped + ceiling_identity) * request.serial_pace_seconds
                ),
            )
        )
    return tuple(batches)


def _validate_inventory(
    inventory: HistoricalBackfillInventoryV1,
    calendar: MarketSessionCalendar,
) -> None:
    if not _SHA256.fullmatch(inventory.inventory_fingerprint):
        raise HistoricalBackfillPlannerError(
            "inventory fingerprint must be lowercase SHA-256"
        )
    _validate_contiguous_sessions(
        inventory.completed_eod_sessions, "completed EOD sessions", calendar
    )
    _validate_contiguous_sessions(
        inventory.completed_identity_sessions,
        "completed Identity sessions",
        calendar,
    )
    if inventory.completed_eod_sessions != inventory.completed_identity_sessions:
        raise HistoricalBackfillPlannerError(
            "completed EOD and point-in-time Identity sessions must match exactly"
        )


def _validate_contiguous_sessions(
    sessions: tuple[date, ...],
    name: str,
    calendar: MarketSessionCalendar,
) -> None:
    if not sessions:
        raise HistoricalBackfillPlannerError(f"{name} cannot be empty")
    if sessions != tuple(sorted(set(sessions))):
        raise HistoricalBackfillPlannerError(f"{name} must be sorted and unique")
    if any(not calendar.is_session(item) for item in sessions):
        raise HistoricalBackfillPlannerError(f"{name} must contain only XNYS sessions")
    if any(
        calendar.next_session(previous) != current
        for previous, current in zip(sessions, sessions[1:])
    ):
        raise HistoricalBackfillPlannerError(f"{name} must be contiguous")


def _validate_request(request: HistoricalBackfillRequestV1) -> None:
    if not MINIMUM_TARGET_SESSIONS <= request.target_session_count <= MAXIMUM_TARGET_SESSIONS:
        raise HistoricalBackfillPlannerError(
            "target session count must be between 252 and 504"
        )
    if not 1 <= request.batch_size <= MAXIMUM_BATCH_SIZE:
        raise HistoricalBackfillPlannerError("batch size must be between one and three")
    if not 1 <= request.active_identity_pages_observed_per_session <= request.active_identity_page_ceiling_per_session:
        raise HistoricalBackfillPlannerError(
            "observed active Identity pages must fit within the page ceiling"
        )
    if not 1 <= request.active_identity_page_ceiling_per_session <= 20:
        raise HistoricalBackfillPlannerError(
            "active Identity page ceiling must be between one and twenty"
        )
    if request.serial_pace_seconds < DEFAULT_SERIAL_PACE_SECONDS:
        raise HistoricalBackfillPlannerError(
            "provider pacing cannot be faster than fifteen seconds"
        )
    if request.eod_bytes_per_session < 1 or request.identity_bytes_per_session < 1:
        raise HistoricalBackfillPlannerError("storage estimates must be positive")
    if request.blocker_codes != REQUIRED_BLOCKER_CODES:
        raise HistoricalBackfillPlannerError(
            "historical backfill blocker codes cannot be omitted or reordered"
        )


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        _jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
