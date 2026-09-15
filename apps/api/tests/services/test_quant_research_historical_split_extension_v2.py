from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    CorporateActionRecordStatus,
    CorporateActionType,
)
from tip_api.services.historical_split_adjustment_candidate import (
    SplitAdjustmentEventCandidateV1,
    SplitAdjustmentSourceActionV1,
    _fingerprint,
)
from tip_api.services.quant_research_historical_split_extension_v2 import (
    build_quant_research_historical_split_evidence_v2,
)


INSTRUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSIONS = (date(2026, 8, 20), date(2026, 8, 21), date(2026, 8, 22))


def _event() -> SplitAdjustmentEventCandidateV1:
    action = SplitAdjustmentSourceActionV1(
        source_action_id="split-one",
        source_revision=1,
        action_type=CorporateActionType.STOCK_SPLIT,
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal("2"),
    )
    return SplitAdjustmentEventCandidateV1(
        instrument_id=INSTRUMENT_ID,
        effective_date=SESSIONS[1],
        source_actions=(action,),
        source_action_set_fingerprint=_fingerprint(
            (action.model_dump(mode="json"),)
        ),
        price_multiplier_to_post_event_basis=Decimal("0.5"),
        volume_multiplier_to_post_event_basis=Decimal("2"),
    )


def _inputs(*, canonical_ratio_to: str = "2") -> dict[str, object]:
    event = _event()
    candidate = SimpleNamespace(
        start_date=date(2021, 8, 11),
        basis_session=SESSIONS[-1],
        point_in_time_eligibility="outcome_reconciliation_only",
        ledger_projection_status="not_built",
        total_return_adjustment_status="unavailable",
        resolved_events=(event,),
        possible_unresolved_impacts=(),
        logical_fingerprint="a" * 64,
    )
    canonical_action = SimpleNamespace(
        instrument_id=INSTRUMENT_ID,
        effective_date=SESSIONS[1],
        action_type=CorporateActionType.STOCK_SPLIT,
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal(canonical_ratio_to),
        record_status=CorporateActionRecordStatus.ACTIVE,
    )
    action_publication = SimpleNamespace(
        point_in_time_eligibility="outcome_reconciliation_only",
        full_corporate_action_coverage_authorized=False,
        research_performance_authorized=False,
        possible_unresolved_impacts=(),
        logical_fingerprint="b" * 64,
    )
    canonical_adjustment = SimpleNamespace(
        instrument_id=INSTRUMENT_ID,
        source_session=SESSIONS[0],
        split_adjustment_status=AdjustmentAvailabilityStatus.CLEAR,
        split_price_multiplier_to_basis=Decimal("0.5"),
        split_volume_multiplier_to_basis=Decimal("2"),
    )
    adjustment_publication = SimpleNamespace(
        basis_session=SESSIONS[-1],
        total_return_adjustment_authorized=False,
        absent_row_neutrality_authorized=False,
        historical_coverage_authorized=False,
        research_performance_authorized=False,
        logical_fingerprint="c" * 64,
    )
    return {
        "candidate": candidate,
        "candidate_file_sha256": "d" * 64,
        "canonical_action_source": SimpleNamespace(
            actions=(canonical_action,), publication=action_publication
        ),
        "canonical_adjustment_source": SimpleNamespace(
            records=(canonical_adjustment,), publication=adjustment_publication
        ),
        "source_sessions": SESSIONS,
        "required_ids": frozenset({INSTRUMENT_ID}),
    }


def test_builds_clear_outcome_blind_extension() -> None:
    result = build_quant_research_historical_split_evidence_v2(**_inputs())

    key = (INSTRUMENT_ID, SESSIONS[0])
    assert result.active_action_keys == frozenset({(INSTRUMENT_ID, SESSIONS[1])})
    assert result.quarantined_action_keys == frozenset()
    assert result.clear_adjustments[key].split_price_multiplier_to_basis == Decimal(
        "0.5"
    )
    assert result.clear_adjustments[key].split_volume_multiplier_to_basis == Decimal(
        "2"
    )
    assert result.conflict_event_count == 0
    assert result.conflict_adjustment_count == 0


def test_conflicting_prior_action_is_quarantined() -> None:
    result = build_quant_research_historical_split_evidence_v2(
        **_inputs(canonical_ratio_to="3")
    )

    assert result.active_action_keys == frozenset()
    assert result.quarantined_action_keys == frozenset(
        {(INSTRUMENT_ID, SESSIONS[1])}
    )
    assert result.conflict_event_count == 1
    assert result.conflict_adjustment_count == 1
