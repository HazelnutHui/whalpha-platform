from __future__ import annotations

from datetime import date

import pytest

from tip_api.services.historical_pilot_planner import (
    DEFAULT_SOURCE_GAPS,
    HistoricalPilotInventoryV1,
    HistoricalPilotPlannerError,
    HistoricalPilotRequestV1,
    PilotAuthorizationStatus,
    PilotMechanicsStatus,
    PilotNextAction,
    PilotRequestKind,
    plan_historical_research_pilot,
)


SHA = "a" * 64
TARGETS = (date(2026, 8, 24), date(2026, 8, 25), date(2026, 8, 26))
ANCHORS = (date(2026, 6, 30), date(2026, 7, 31), date(2026, 8, 26))
TICKERS = ("AAPL", "BRK.B", "SNDK", "SPY", "XYZ")


def _inventory(
    *,
    eod: tuple[date, ...] = (),
    identity: tuple[date, ...] = (),
) -> HistoricalPilotInventoryV1:
    return HistoricalPilotInventoryV1(
        source_report_id="caller-inventory-v1",
        inventory_fingerprint=SHA,
        completed_eod_sessions=eod,
        completed_identity_sessions=identity,
        provider_action_partition_count=1,
        lifecycle_partition_count=2,
        membership_partition_count=3,
        adjustment_partition_count=4,
        coverage_manifest_count=5,
    )


def _request(**overrides) -> HistoricalPilotRequestV1:
    values = {
        "target_sessions": TARGETS,
        "inactive_identity_anchor_dates": ANCHORS,
        "targeted_ticker_event_scopes": TICKERS,
    }
    values.update(overrides)
    return HistoricalPilotRequestV1(**values)


def test_maximum_plan_is_exactly_eighty_serial_requests_and_never_authorizes() -> None:
    plan = plan_historical_research_pilot(
        inventory=_inventory(),
        request=_request(),
    )

    by_kind = {item.kind: item for item in plan.request_lines}
    assert by_kind[PilotRequestKind.GROUPED_DAILY].request_ceiling == 3
    assert by_kind[PilotRequestKind.ACTIVE_ALL_TICKERS].request_ceiling == 60
    assert by_kind[PilotRequestKind.INACTIVE_ALL_TICKERS].request_ceiling == 6
    assert by_kind[PilotRequestKind.SPLITS].request_ceiling == 2
    assert by_kind[PilotRequestKind.DIVIDENDS].request_ceiling == 4
    assert by_kind[PilotRequestKind.TICKER_EVENTS_EXPERIMENTAL].request_ceiling == 5
    assert by_kind[PilotRequestKind.GROUPED_DAILY].required_parameters == (
        "adjusted=false",
    )
    assert by_kind[PilotRequestKind.ACTIVE_ALL_TICKERS].result_limit_per_page == 1_000
    assert by_kind[PilotRequestKind.SPLITS].result_limit_per_page == 5_000
    assert plan.planned_request_ceiling == plan.global_request_ceiling == 80
    assert plan.estimated_transport_seconds_at_ceiling == 1_200
    assert plan.mechanics_status is PilotMechanicsStatus.WITHIN_CEILING
    assert plan.authorization_status is PilotAuthorizationStatus.NOT_AUTHORIZED
    assert plan.next_action is PilotNextAction.REVIEW_PLAN_ONLY
    assert plan.source_gap_codes == DEFAULT_SOURCE_GAPS
    assert "equal_capability_source_permission_unresolved" in plan.source_gap_codes
    assert all("product_posture" not in code for code in plan.source_gap_codes)
    assert not any(
        (
            plan.acquisition_authorized,
            plan.apply_authorized,
            plan.publication_authorized,
            plan.deployment_authorized,
            plan.scheduler_enabled,
        )
    )
    assert plan.external_request_count == 0
    assert plan.data_write_count == 0


def test_caller_inventory_removes_only_completed_session_requests() -> None:
    plan = plan_historical_research_pilot(
        inventory=_inventory(eod=TARGETS[:2], identity=TARGETS[:1]),
        request=_request(targeted_ticker_event_scopes=()),
    )
    by_kind = {item.kind: item for item in plan.request_lines}

    assert plan.missing_eod_sessions == ("2026-08-26",)
    assert plan.missing_identity_sessions == ("2026-08-25", "2026-08-26")
    assert plan.inventory.matched_target_eod_sessions == (
        "2026-08-24",
        "2026-08-25",
    )
    assert plan.inventory.matched_target_identity_sessions == ("2026-08-24",)
    assert by_kind[PilotRequestKind.GROUPED_DAILY].request_ceiling == 1
    assert by_kind[PilotRequestKind.ACTIVE_ALL_TICKERS].request_ceiling == 40
    assert plan.planned_request_ceiling == 53


def test_plan_fingerprint_and_paths_are_deterministic_and_tmp_bounded() -> None:
    first = plan_historical_research_pilot(
        inventory=_inventory(),
        request=_request(),
    )
    second = plan_historical_research_pilot(
        inventory=_inventory(),
        request=_request(),
    )

    assert first == second
    assert first.logical_content_fingerprint == second.logical_content_fingerprint
    prefix = (
        "historical-research-pilot/"
        f"plan={first.logical_content_fingerprint}/"
    )
    assert first.temporary_package_root_requirement == "/tmp"
    assert all(path.startswith(prefix) for path in first.temporary_package_relative_paths)
    assert all(not path.startswith("/") for path in first.temporary_package_relative_paths)
    assert len(first.temporary_package_relative_paths) == 83
    assert first.as_dict()["authorization_status"] == "not_authorized"
    assert first.as_dict()["request_lines"][0]["kind"] == "grouped_daily"


def test_proposed_canonical_paths_do_not_invent_action_year_or_coverage_id() -> None:
    plan = plan_historical_research_pilot(
        inventory=_inventory(),
        request=_request(),
    )

    assert len(plan.proposed_canonical_partition_candidates) == 7
    assert plan.proposed_canonical_partition_candidates[-1].endswith(
        "basis_session=2026-08-26"
    )
    assert any(
        "<validated-event-year>" in path
        for path in plan.unresolved_canonical_path_templates
    )
    assert any(
        "<derived-after-formal-reread>" in path
        for path in plan.unresolved_canonical_path_templates
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"target_sessions": TARGETS + (date(2026, 8, 27),)}, "bounded maximum"),
        ({"target_sessions": (date(2026, 8, 23),)}, "XNYS"),
        ({"target_sessions": tuple(reversed(TARGETS))}, "sorted and unique"),
        ({"active_identity_page_ceiling_per_session": 21}, "between 1 and 20"),
        ({"inactive_identity_pages_per_anchor": 3}, "exceed six"),
        ({"split_page_ceiling": 3}, "zero and two"),
        ({"dividend_page_ceiling": 5}, "zero and four"),
        ({"targeted_ticker_event_scopes": ("BAD/TICKER",)}, "safe tickers"),
        ({"serial_pace_seconds": 14}, "faster than 15"),
        ({"source_gap_codes": ()}, "source gaps"),
        ({"source_gap_codes": ("exact_live_pilot_authorization_absent",)}, "cannot be omitted"),
    ),
)
def test_request_scope_cannot_loosen_reviewed_boundaries(overrides, message) -> None:
    with pytest.raises(HistoricalPilotPlannerError, match=message):
        plan_historical_research_pilot(
            inventory=_inventory(),
            request=_request(**overrides),
        )


@pytest.mark.parametrize(
    "inventory",
    (
        HistoricalPilotInventoryV1(
            source_report_id="unsafe/report",
            inventory_fingerprint=SHA,
            completed_eod_sessions=(),
            completed_identity_sessions=(),
        ),
        HistoricalPilotInventoryV1(
            source_report_id="safe",
            inventory_fingerprint="not-a-hash",
            completed_eod_sessions=(),
            completed_identity_sessions=(),
        ),
        HistoricalPilotInventoryV1(
            source_report_id="safe",
            inventory_fingerprint=SHA,
            completed_eod_sessions=(date(2026, 8, 23),),
            completed_identity_sessions=(),
        ),
        HistoricalPilotInventoryV1(
            source_report_id="safe",
            inventory_fingerprint=SHA,
            completed_eod_sessions=(),
            completed_identity_sessions=(),
            membership_partition_count=-1,
        ),
    ),
)
def test_inventory_is_untrusted_and_validated_without_scanning_storage(inventory) -> None:
    with pytest.raises(HistoricalPilotPlannerError):
        plan_historical_research_pilot(inventory=inventory, request=_request())
