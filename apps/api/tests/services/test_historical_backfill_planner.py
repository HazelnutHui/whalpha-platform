from __future__ import annotations

from datetime import date

import pytest

from tip_api.services.historical_backfill_planner import (
    REQUIRED_BLOCKER_CODES,
    HistoricalBackfillInventoryV1,
    HistoricalBackfillPlannerError,
    HistoricalBackfillRequestV1,
    HistoricalBackfillStatus,
    plan_historical_research_backfill,
)
from tip_api.services.market_calendar import ExchangeCalendar


SHA = "a" * 64


def _sessions_ending(end: date, count: int) -> tuple[date, ...]:
    calendar = ExchangeCalendar()
    sessions = [end]
    while len(sessions) < count:
        sessions.append(calendar.previous_session(sessions[-1]))
    return tuple(reversed(sessions))


def _inventory(count: int = 32) -> HistoricalBackfillInventoryV1:
    sessions = _sessions_ending(date(2026, 8, 31), count)
    return HistoricalBackfillInventoryV1(
        inventory_fingerprint=SHA,
        completed_eod_sessions=sessions,
        completed_identity_sessions=sessions,
    )


def test_current_32_session_inventory_produces_exact_300_session_plan() -> None:
    plan = plan_historical_research_backfill(inventory=_inventory())

    assert plan.current_first_session == "2026-07-17"
    assert plan.current_last_session == "2026-08-31"
    assert plan.current_session_count == 32
    assert plan.target_first_session == "2025-06-23"
    assert plan.target_last_session == "2026-08-31"
    assert plan.target_session_count == 300
    assert plan.missing_session_count == 268
    assert plan.batch_count == 90
    assert plan.representative_pilot_sessions == (
        "2026-07-14",
        "2026-07-15",
        "2026-07-16",
    )
    assert plan.batches[0].is_representative_pilot
    assert not plan.batches[0].depends_on_prior_batch_completion
    assert plan.batches[-1].target_sessions == ("2025-06-23",)
    assert plan.batches[-1].depends_on_prior_batch_completion


def test_request_time_and_storage_projections_reconcile() -> None:
    plan = plan_historical_research_backfill(inventory=_inventory())

    assert plan.grouped_daily_request_count == 268
    assert plan.active_identity_request_observed_projection == 3_752
    assert plan.active_identity_request_ceiling == 5_360
    assert plan.total_request_observed_projection == 4_020
    assert plan.total_request_ceiling == 5_628
    assert plan.transport_seconds_observed_projection == 60_300
    assert plan.transport_seconds_at_ceiling == 84_420
    assert plan.estimated_incremental_canonical_bytes == 880_745_820
    assert plan.recommended_staging_reserve_bytes == 1_761_491_640


def test_plan_is_deterministic_and_never_authorizes() -> None:
    first = plan_historical_research_backfill(inventory=_inventory())
    second = plan_historical_research_backfill(inventory=_inventory())

    assert first == second
    assert first.logical_content_fingerprint == second.logical_content_fingerprint
    assert first.status is HistoricalBackfillStatus.BLOCKED_PENDING_PILOT
    assert first.blocker_codes == REQUIRED_BLOCKER_CODES
    assert first.provider_requests_serial_only
    assert first.offline_parallelism_permitted_after_source_custody
    assert not any(
        (
            first.acquisition_authorized,
            first.apply_authorized,
            first.publication_authorized,
            first.deployment_authorized,
            first.scheduler_authorized,
            first.performance_claims_authorized,
        )
    )
    assert first.external_request_count == 0
    assert first.production_write_count == 0
    assert first.as_dict()["status"] == "blocked_pending_pilot"


def test_target_may_extend_to_preferred_504_sessions() -> None:
    plan = plan_historical_research_backfill(
        inventory=_inventory(),
        request=HistoricalBackfillRequestV1(target_session_count=504),
    )

    assert plan.target_session_count == 504
    assert plan.missing_session_count == 472
    assert plan.batch_count == 158


@pytest.mark.parametrize(
    ("backfill_request", "message"),
    (
        (HistoricalBackfillRequestV1(target_session_count=251), "252 and 504"),
        (HistoricalBackfillRequestV1(target_session_count=505), "252 and 504"),
        (HistoricalBackfillRequestV1(batch_size=4), "one and three"),
        (HistoricalBackfillRequestV1(serial_pace_seconds=14), "fifteen"),
        (HistoricalBackfillRequestV1(blocker_codes=()), "cannot be omitted"),
    ),
)
def test_request_cannot_loosen_governed_boundaries(backfill_request, message) -> None:
    with pytest.raises(HistoricalBackfillPlannerError, match=message):
        plan_historical_research_backfill(
            inventory=_inventory(),
            request=backfill_request,
        )


def test_inventory_must_be_contiguous_and_identity_aligned() -> None:
    sessions = _sessions_ending(date(2026, 8, 31), 32)
    with pytest.raises(HistoricalBackfillPlannerError, match="match exactly"):
        plan_historical_research_backfill(
            inventory=HistoricalBackfillInventoryV1(
                inventory_fingerprint=SHA,
                completed_eod_sessions=sessions,
                completed_identity_sessions=sessions[:-1],
            )
        )
