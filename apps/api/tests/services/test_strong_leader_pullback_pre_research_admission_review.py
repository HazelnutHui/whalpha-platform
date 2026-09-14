from __future__ import annotations

from tip_api.services import strong_leader_pullback_pre_research_admission_review as service


def test_gate_has_finite_registered_blockers() -> None:
    codes = service._blocker_codes()

    assert codes == tuple(sorted(set(codes)))
    assert "terminal_reference_gaps_present" in codes
    assert "corporate_action_absence_neutrality_unproven" in codes
    assert "minimum_252_complete_sessions_not_met" in codes


def test_acquisition_request_is_capability_scoped() -> None:
    capabilities = service._required_external_capabilities()

    assert capabilities == tuple(sorted(set(capabilities)))
    assert len(capabilities) == 3
    assert all("vendor" not in item for item in capabilities)


def test_limitations_keep_price_returns_distinct() -> None:
    assert "cash_dividends_are_event_context_not_total_return" in (
        service._limitation_codes()
    )
