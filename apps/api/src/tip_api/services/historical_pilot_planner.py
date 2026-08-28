"""Pure, credential-free planning for one bounded historical research pilot."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum

from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


CONTRACT_VERSION = "historical-research-pilot-plan/1.0"
GLOBAL_REQUEST_CEILING = 80
MAX_TARGET_SESSIONS = 3
MAX_ACTIVE_IDENTITY_PAGES_PER_SESSION = 20
MAX_INACTIVE_IDENTITY_REQUESTS = 6
MAX_SPLIT_PAGES = 2
MAX_DIVIDEND_PAGES = 4
MAX_TICKER_EVENT_REQUESTS = 5
DEFAULT_SERIAL_PACE_SECONDS = 15
DEFAULT_SOURCE_GAPS = (
    "account_endpoint_entitlement_unverified",
    "exact_live_pilot_authorization_absent",
    "guest_friend_product_posture_conflict_unresolved",
    "merger_successor_terminal_source_incomplete",
    "provider_permission_review_incomplete",
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_SAFE_TICKER = re.compile(r"[A-Z0-9][A-Z0-9.-]{0,14}")


class HistoricalPilotPlannerError(ValueError):
    """Raised when a bounded, deterministic pilot cannot be planned."""


class PilotMechanicsStatus(StrEnum):
    WITHIN_CEILING = "within_ceiling"


class PilotAuthorizationStatus(StrEnum):
    NOT_AUTHORIZED = "not_authorized"


class PilotNextAction(StrEnum):
    REVIEW_PLAN_ONLY = "review_plan_only"


class PilotRequestKind(StrEnum):
    GROUPED_DAILY = "grouped_daily"
    ACTIVE_ALL_TICKERS = "active_all_tickers"
    INACTIVE_ALL_TICKERS = "inactive_all_tickers"
    SPLITS = "splits"
    DIVIDENDS = "dividends"
    TICKER_EVENTS_EXPERIMENTAL = "ticker_events_experimental"


@dataclass(frozen=True, slots=True)
class HistoricalPilotInventoryV1:
    """Caller-supplied inventory evidence; the planner never scans storage."""

    source_report_id: str
    inventory_fingerprint: str
    completed_eod_sessions: tuple[date, ...]
    completed_identity_sessions: tuple[date, ...]
    provider_action_partition_count: int = 0
    lifecycle_partition_count: int = 0
    membership_partition_count: int = 0
    adjustment_partition_count: int = 0
    coverage_manifest_count: int = 0


@dataclass(frozen=True, slots=True)
class HistoricalPilotRequestV1:
    """Exact pilot scope, limited to the previously reviewed hard ceilings."""

    target_sessions: tuple[date, ...]
    inactive_identity_anchor_dates: tuple[date, ...] = ()
    targeted_ticker_event_scopes: tuple[str, ...] = ()
    provider_id: str = "massive"
    methodology_version: str = "historical-research-pilot-v1"
    active_identity_page_ceiling_per_session: int = 20
    inactive_identity_pages_per_anchor: int = 2
    split_page_ceiling: int = 2
    dividend_page_ceiling: int = 4
    serial_pace_seconds: int = DEFAULT_SERIAL_PACE_SECONDS
    source_gap_codes: tuple[str, ...] = DEFAULT_SOURCE_GAPS


@dataclass(frozen=True, slots=True)
class HistoricalPilotInventorySummaryV1:
    source_report_id: str
    inventory_fingerprint: str
    completed_eod_session_count: int
    completed_identity_session_count: int
    matched_target_eod_sessions: tuple[str, ...]
    matched_target_identity_sessions: tuple[str, ...]
    provider_action_partition_count: int
    lifecycle_partition_count: int
    membership_partition_count: int
    adjustment_partition_count: int
    coverage_manifest_count: int


@dataclass(frozen=True, slots=True)
class HistoricalPilotRequestLineV1:
    kind: PilotRequestKind
    logical_endpoint: str
    scopes: tuple[str, ...]
    request_ceiling: int
    page_ceiling_per_scope: int | None
    result_limit_per_page: int | None
    required_parameters: tuple[str, ...]
    retry_count: int
    serial_only: bool
    purpose: str


@dataclass(frozen=True, slots=True)
class HistoricalPilotPlanV1:
    contract_version: str
    calendar_id: str
    calendar_version: str
    provider_id: str
    methodology_version: str
    target_sessions: tuple[str, ...]
    missing_eod_sessions: tuple[str, ...]
    missing_identity_sessions: tuple[str, ...]
    inventory: HistoricalPilotInventorySummaryV1
    request_lines: tuple[HistoricalPilotRequestLineV1, ...]
    global_request_ceiling: int
    planned_request_ceiling: int
    zero_automatic_retry: bool
    serial_pace_seconds: int
    estimated_transport_seconds_at_ceiling: int
    temporary_package_root_requirement: str
    temporary_package_relative_paths: tuple[str, ...]
    proposed_canonical_partition_candidates: tuple[str, ...]
    unresolved_canonical_path_templates: tuple[str, ...]
    source_gap_codes: tuple[str, ...]
    mechanics_status: PilotMechanicsStatus
    authorization_status: PilotAuthorizationStatus
    next_action: PilotNextAction
    acquisition_authorized: bool
    apply_authorized: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_enabled: bool
    external_request_count: int
    data_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def plan_historical_research_pilot(
    *,
    inventory: HistoricalPilotInventoryV1,
    request: HistoricalPilotRequestV1,
    calendar: MarketSessionCalendar | None = None,
) -> HistoricalPilotPlanV1:
    """Calculate one default-deny pilot plan without filesystem or network I/O."""

    session_calendar = calendar or ExchangeCalendar()
    _validate_inventory(inventory, session_calendar)
    _validate_request(request, session_calendar)

    target = request.target_sessions
    completed_eod = frozenset(inventory.completed_eod_sessions)
    completed_identity = frozenset(inventory.completed_identity_sessions)
    missing_eod = tuple(item for item in target if item not in completed_eod)
    missing_identity = tuple(item for item in target if item not in completed_identity)
    matched_eod = tuple(item for item in target if item in completed_eod)
    matched_identity = tuple(item for item in target if item in completed_identity)

    request_lines = _request_lines(
        request=request,
        missing_eod=missing_eod,
        missing_identity=missing_identity,
    )
    planned_ceiling = sum(item.request_ceiling for item in request_lines)
    if planned_ceiling > GLOBAL_REQUEST_CEILING:  # defense in depth
        raise HistoricalPilotPlannerError("planned requests exceed the global pilot ceiling")

    inventory_summary = HistoricalPilotInventorySummaryV1(
        source_report_id=inventory.source_report_id,
        inventory_fingerprint=inventory.inventory_fingerprint,
        completed_eod_session_count=len(inventory.completed_eod_sessions),
        completed_identity_session_count=len(inventory.completed_identity_sessions),
        matched_target_eod_sessions=_dates(matched_eod),
        matched_target_identity_sessions=_dates(matched_identity),
        provider_action_partition_count=inventory.provider_action_partition_count,
        lifecycle_partition_count=inventory.lifecycle_partition_count,
        membership_partition_count=inventory.membership_partition_count,
        adjustment_partition_count=inventory.adjustment_partition_count,
        coverage_manifest_count=inventory.coverage_manifest_count,
    )
    payload = {
        "contract_version": CONTRACT_VERSION,
        "calendar_id": session_calendar.calendar_id,
        "calendar_version": session_calendar.calendar_version,
        "provider_id": request.provider_id,
        "methodology_version": request.methodology_version,
        "target_sessions": _dates(target),
        "missing_eod_sessions": _dates(missing_eod),
        "missing_identity_sessions": _dates(missing_identity),
        "inventory": _jsonable(asdict(inventory_summary)),
        "request_lines": [_jsonable(asdict(item)) for item in request_lines],
        "global_request_ceiling": GLOBAL_REQUEST_CEILING,
        "planned_request_ceiling": planned_ceiling,
        "serial_pace_seconds": request.serial_pace_seconds,
        "source_gap_codes": list(request.source_gap_codes),
        "authorization_status": PilotAuthorizationStatus.NOT_AUTHORIZED.value,
    }
    fingerprint = _fingerprint(payload)
    return HistoricalPilotPlanV1(
        contract_version=CONTRACT_VERSION,
        calendar_id=session_calendar.calendar_id,
        calendar_version=session_calendar.calendar_version,
        provider_id=request.provider_id,
        methodology_version=request.methodology_version,
        target_sessions=_dates(target),
        missing_eod_sessions=_dates(missing_eod),
        missing_identity_sessions=_dates(missing_identity),
        inventory=inventory_summary,
        request_lines=request_lines,
        global_request_ceiling=GLOBAL_REQUEST_CEILING,
        planned_request_ceiling=planned_ceiling,
        zero_automatic_retry=True,
        serial_pace_seconds=request.serial_pace_seconds,
        estimated_transport_seconds_at_ceiling=(
            planned_ceiling * request.serial_pace_seconds
        ),
        temporary_package_root_requirement="/tmp",
        temporary_package_relative_paths=_temporary_paths(
            fingerprint=fingerprint,
            request=request,
            missing_eod=missing_eod,
            missing_identity=missing_identity,
        ),
        proposed_canonical_partition_candidates=_canonical_candidates(request),
        unresolved_canonical_path_templates=(
            "market-data/provider-corporate-action-observation/"
            f"provider_id={request.provider_id}/schema_version=1/event_year=<validated-event-year>",
            "market-data/corporate-actions/schema_version=1/"
            "event_year=<validated-event-year>",
            "market-data/historical-coverage/schema_version=1/"
            "coverage_id=<derived-after-formal-reread>",
        ),
        source_gap_codes=request.source_gap_codes,
        mechanics_status=PilotMechanicsStatus.WITHIN_CEILING,
        authorization_status=PilotAuthorizationStatus.NOT_AUTHORIZED,
        next_action=PilotNextAction.REVIEW_PLAN_ONLY,
        acquisition_authorized=False,
        apply_authorized=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        data_write_count=0,
        logical_content_fingerprint=fingerprint,
    )


def _request_lines(
    *,
    request: HistoricalPilotRequestV1,
    missing_eod: tuple[date, ...],
    missing_identity: tuple[date, ...],
) -> tuple[HistoricalPilotRequestLineV1, ...]:
    return (
        HistoricalPilotRequestLineV1(
            kind=PilotRequestKind.GROUPED_DAILY,
            logical_endpoint="stocks_grouped_daily_unadjusted",
            scopes=_dates(missing_eod),
            request_ceiling=len(missing_eod),
            page_ceiling_per_scope=1,
            result_limit_per_page=None,
            required_parameters=("adjusted=false",),
            retry_count=0,
            serial_only=True,
            purpose="unadjusted full-market EOD bars for exact missing sessions",
        ),
        HistoricalPilotRequestLineV1(
            kind=PilotRequestKind.ACTIVE_ALL_TICKERS,
            logical_endpoint="stocks_reference_all_tickers_active_point_in_time",
            scopes=_dates(missing_identity),
            request_ceiling=(
                len(missing_identity)
                * request.active_identity_page_ceiling_per_session
            ),
            page_ceiling_per_scope=request.active_identity_page_ceiling_per_session,
            result_limit_per_page=1_000,
            required_parameters=("active=true", "date=<scope>", "limit=1000"),
            retry_count=0,
            serial_only=True,
            purpose="same-session active point-in-time identity evidence",
        ),
        HistoricalPilotRequestLineV1(
            kind=PilotRequestKind.INACTIVE_ALL_TICKERS,
            logical_endpoint="stocks_reference_all_tickers_inactive_point_in_time",
            scopes=_dates(request.inactive_identity_anchor_dates),
            request_ceiling=(
                len(request.inactive_identity_anchor_dates)
                * request.inactive_identity_pages_per_anchor
            ),
            page_ceiling_per_scope=request.inactive_identity_pages_per_anchor,
            result_limit_per_page=1_000,
            required_parameters=("active=false", "date=<scope>", "limit=1000"),
            retry_count=0,
            serial_only=True,
            purpose="bounded inactive/lifecycle discovery evidence",
        ),
        HistoricalPilotRequestLineV1(
            kind=PilotRequestKind.SPLITS,
            logical_endpoint="stocks_v1_splits",
            scopes=("bounded_paginated_collection",),
            request_ceiling=request.split_page_ceiling,
            page_ceiling_per_scope=request.split_page_ceiling,
            result_limit_per_page=5_000,
            required_parameters=("limit=5000",),
            retry_count=0,
            serial_only=True,
            purpose="split and reverse-split source observations",
        ),
        HistoricalPilotRequestLineV1(
            kind=PilotRequestKind.DIVIDENDS,
            logical_endpoint="stocks_v1_dividends",
            scopes=("bounded_paginated_collection",),
            request_ceiling=request.dividend_page_ceiling,
            page_ceiling_per_scope=request.dividend_page_ceiling,
            result_limit_per_page=5_000,
            required_parameters=("limit=5000",),
            retry_count=0,
            serial_only=True,
            purpose="cash and stock distribution source observations",
        ),
        HistoricalPilotRequestLineV1(
            kind=PilotRequestKind.TICKER_EVENTS_EXPERIMENTAL,
            logical_endpoint="stocks_reference_ticker_events_experimental",
            scopes=request.targeted_ticker_event_scopes,
            request_ceiling=len(request.targeted_ticker_event_scopes),
            page_ceiling_per_scope=1,
            result_limit_per_page=None,
            required_parameters=("ticker=<scope>",),
            retry_count=0,
            serial_only=True,
            purpose="targeted unresolved lifecycle evidence only",
        ),
    )


def _temporary_paths(
    *,
    fingerprint: str,
    request: HistoricalPilotRequestV1,
    missing_eod: tuple[date, ...],
    missing_identity: tuple[date, ...],
) -> tuple[str, ...]:
    prefix = f"historical-research-pilot/plan={fingerprint}"
    paths = [
        f"{prefix}/manifests/inventory-source.json",
        f"{prefix}/manifests/request-plan.json",
    ]
    paths.extend(
        f"{prefix}/staged/grouped-daily/session={session.isoformat()}/request=001.json"
        for session in missing_eod
    )
    for session in missing_identity:
        paths.extend(
            f"{prefix}/staged/active-all-tickers/session={session.isoformat()}/"
            f"page={page:03d}.json"
            for page in range(1, request.active_identity_page_ceiling_per_session + 1)
        )
    for anchor in request.inactive_identity_anchor_dates:
        paths.extend(
            f"{prefix}/staged/inactive-all-tickers/anchor={anchor.isoformat()}/"
            f"page={page:03d}.json"
            for page in range(1, request.inactive_identity_pages_per_anchor + 1)
        )
    paths.extend(
        f"{prefix}/staged/splits/page={page:03d}.json"
        for page in range(1, request.split_page_ceiling + 1)
    )
    paths.extend(
        f"{prefix}/staged/dividends/page={page:03d}.json"
        for page in range(1, request.dividend_page_ceiling + 1)
    )
    paths.extend(
        f"{prefix}/staged/ticker-events/request-scope={ticker}.json"
        for ticker in request.targeted_ticker_event_scopes
    )
    paths.append(f"{prefix}/manifests/formal-reread-result.json")
    return tuple(paths)


def _canonical_candidates(request: HistoricalPilotRequestV1) -> tuple[str, ...]:
    paths: list[str] = []
    for session in request.target_sessions:
        value = session.isoformat()
        paths.extend(
            (
                "market-data/instrument-lifecycle/schema_version=1/"
                f"as_of_date={value}",
                "market-data/universe-membership/schema_version=1/"
                f"methodology_version={request.methodology_version}/session_date={value}",
            )
        )
    paths.append(
        "market-data/adjustment-ledger/schema_version=1/"
        f"methodology_version={request.methodology_version}/"
        f"basis_session={request.target_sessions[-1].isoformat()}"
    )
    return tuple(paths)


def _validate_inventory(
    inventory: HistoricalPilotInventoryV1,
    calendar: MarketSessionCalendar,
) -> None:
    if not _SAFE_ID.fullmatch(inventory.source_report_id):
        raise HistoricalPilotPlannerError("inventory source report ID is unsafe")
    if not _SHA256.fullmatch(inventory.inventory_fingerprint):
        raise HistoricalPilotPlannerError("inventory fingerprint must be lowercase SHA-256")
    _validate_sessions(
        inventory.completed_eod_sessions,
        name="completed EOD sessions",
        calendar=calendar,
        allow_empty=True,
    )
    _validate_sessions(
        inventory.completed_identity_sessions,
        name="completed Identity sessions",
        calendar=calendar,
        allow_empty=True,
    )
    counts = (
        inventory.provider_action_partition_count,
        inventory.lifecycle_partition_count,
        inventory.membership_partition_count,
        inventory.adjustment_partition_count,
        inventory.coverage_manifest_count,
    )
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in counts
    ):
        raise HistoricalPilotPlannerError("inventory counts must be non-negative integers")


def _validate_request(
    request: HistoricalPilotRequestV1,
    calendar: MarketSessionCalendar,
) -> None:
    if not _SAFE_ID.fullmatch(request.provider_id):
        raise HistoricalPilotPlannerError("provider ID is unsafe")
    if not _SAFE_ID.fullmatch(request.methodology_version):
        raise HistoricalPilotPlannerError("methodology version is unsafe")
    _validate_sessions(
        request.target_sessions,
        name="target sessions",
        calendar=calendar,
        allow_empty=False,
        maximum=MAX_TARGET_SESSIONS,
    )
    _validate_sessions(
        request.inactive_identity_anchor_dates,
        name="inactive Identity anchor dates",
        calendar=calendar,
        allow_empty=True,
        maximum=MAX_INACTIVE_IDENTITY_REQUESTS,
    )
    if (
        not isinstance(request.active_identity_page_ceiling_per_session, int)
        or isinstance(request.active_identity_page_ceiling_per_session, bool)
        or not 1
        <= request.active_identity_page_ceiling_per_session
        <= MAX_ACTIVE_IDENTITY_PAGES_PER_SESSION
    ):
        raise HistoricalPilotPlannerError("active Identity page ceiling must be between 1 and 20")
    if (
        not isinstance(request.inactive_identity_pages_per_anchor, int)
        or isinstance(request.inactive_identity_pages_per_anchor, bool)
        or not 1
        <= request.inactive_identity_pages_per_anchor
        <= MAX_INACTIVE_IDENTITY_REQUESTS
    ):
        raise HistoricalPilotPlannerError(
            "inactive Identity pages per anchor must be between 1 and 6"
        )
    inactive_count = (
        len(request.inactive_identity_anchor_dates)
        * request.inactive_identity_pages_per_anchor
    )
    if inactive_count > MAX_INACTIVE_IDENTITY_REQUESTS:
        raise HistoricalPilotPlannerError("inactive Identity requests exceed six")
    if (
        not isinstance(request.split_page_ceiling, int)
        or isinstance(request.split_page_ceiling, bool)
        or not 0 <= request.split_page_ceiling <= MAX_SPLIT_PAGES
    ):
        raise HistoricalPilotPlannerError("split page ceiling must be between zero and two")
    if (
        not isinstance(request.dividend_page_ceiling, int)
        or isinstance(request.dividend_page_ceiling, bool)
        or not 0 <= request.dividend_page_ceiling <= MAX_DIVIDEND_PAGES
    ):
        raise HistoricalPilotPlannerError("dividend page ceiling must be between zero and four")
    if (
        len(request.targeted_ticker_event_scopes) > MAX_TICKER_EVENT_REQUESTS
        or len(set(request.targeted_ticker_event_scopes))
        != len(request.targeted_ticker_event_scopes)
        or tuple(sorted(request.targeted_ticker_event_scopes))
        != request.targeted_ticker_event_scopes
        or any(not _SAFE_TICKER.fullmatch(value) for value in request.targeted_ticker_event_scopes)
    ):
        raise HistoricalPilotPlannerError(
            "ticker-event scopes must be sorted unique safe tickers, maximum five"
        )
    if (
        not isinstance(request.serial_pace_seconds, int)
        or isinstance(request.serial_pace_seconds, bool)
        or request.serial_pace_seconds < DEFAULT_SERIAL_PACE_SECONDS
    ):
        raise HistoricalPilotPlannerError("pilot serial pace cannot be faster than 15 seconds")
    if (
        not request.source_gap_codes
        or len(set(request.source_gap_codes)) != len(request.source_gap_codes)
        or tuple(sorted(request.source_gap_codes)) != request.source_gap_codes
        or any(not _SAFE_ID.fullmatch(value) for value in request.source_gap_codes)
    ):
        raise HistoricalPilotPlannerError("source gaps must be sorted unique safe codes")
    if not set(DEFAULT_SOURCE_GAPS).issubset(request.source_gap_codes):
        raise HistoricalPilotPlannerError("current source gaps cannot be omitted")


def _validate_sessions(
    sessions: tuple[date, ...],
    *,
    name: str,
    calendar: MarketSessionCalendar,
    allow_empty: bool,
    maximum: int | None = None,
) -> None:
    if not allow_empty and not sessions:
        raise HistoricalPilotPlannerError(f"{name} cannot be empty")
    if maximum is not None and len(sessions) > maximum:
        raise HistoricalPilotPlannerError(f"{name} exceed the bounded maximum")
    if any(not isinstance(item, date) for item in sessions):
        raise HistoricalPilotPlannerError(f"{name} must contain dates")
    if tuple(sorted(sessions)) != sessions or len(set(sessions)) != len(sessions):
        raise HistoricalPilotPlannerError(f"{name} must be sorted and unique")
    if any(not calendar.is_session(item) for item in sessions):
        raise HistoricalPilotPlannerError(f"{name} must contain only XNYS sessions")


def _dates(values: tuple[date, ...]) -> tuple[str, ...]:
    return tuple(item.isoformat() for item in values)


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
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
