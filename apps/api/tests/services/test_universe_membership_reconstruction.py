from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    FullBaseDecisionV1,
    FullBaseDisposition,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
)
from tip_api.services.universe_membership_reconstruction import (
    reconstruct_daily_universe_membership,
    stable_instrument_set_fingerprint,
)

SESSION = date(2026, 8, 19)
NOW = datetime(2026, 8, 28, 22, 0, tzinfo=UTC)
ID1 = UUID("11111111-1111-4111-8111-111111111111")
ID2 = UUID("22222222-2222-4222-8222-222222222222")


def source_decision(
    policy_id: str,
    instrument_id: UUID,
    disposition: FullBaseDisposition,
) -> FullBaseDecisionV1:
    return FullBaseDecisionV1(
        analysis_session=SESSION,
        membership_evidence_as_of_date=date(2026, 8, 14),
        policy_id=policy_id,
        instrument_id=instrument_id,
        provider_type_code="CS" if instrument_id == ID1 else "ADRC",
        disposition=disposition,
        included=disposition is FullBaseDisposition.INCLUDED,
        stage_id=disposition.value,
        reason_codes=(disposition.value,),
        reviewed_override_decision=None,
        calculated_at=NOW - timedelta(days=1),
    )


def test_reconstruction_preserves_explicit_exclusion_and_quarantines_missing_input() -> None:
    decisions = (
        source_decision("a", ID1, FullBaseDisposition.INCLUDED),
        source_decision("a", ID2, FullBaseDisposition.TARGET_SECURITY_FORM),
        source_decision("b", ID1, FullBaseDisposition.INCLUDED),
        source_decision("b", ID2, FullBaseDisposition.INSUFFICIENT_HISTORY),
    )

    result = reconstruct_daily_universe_membership(
        session_date=SESSION,
        source_decisions=decisions,
        evaluated_base_ids=frozenset({ID1, ID2}),
        source_policy_to_universe={"a": "primary", "b": "secondary"},
        source_fingerprints=("b" * 64, "a" * 64),
        source_data_cutoff=NOW - timedelta(hours=1),
        evaluated_at=NOW,
    )

    by_key = {(item.universe_id, item.instrument_id): item for item in result.records}
    assert len(by_key) == 4
    assert by_key[("primary", ID1)].disposition is UniverseMembershipDisposition.INCLUDED
    assert by_key[("primary", ID2)].disposition is UniverseMembershipDisposition.EXCLUDED
    assert by_key[("primary", ID2)].is_member is False
    assert by_key[("primary", ID2)].quality_status is QualityStatus.WARNING
    assert "reconstruction_source_cutoff_after_session" in by_key[("primary", ID2)].reason_codes
    assert by_key[("secondary", ID2)].disposition is UniverseMembershipDisposition.QUARANTINED
    assert by_key[("secondary", ID2)].is_member is None
    assert by_key[("secondary", ID2)].quality_status is QualityStatus.PENDING_REVIEW
    assert all(item.origin is UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME for item in result.records)
    assert result.evaluated_base_fingerprint == stable_instrument_set_fingerprint(frozenset({ID1, ID2}))
    assert result.source_fingerprints == ("a" * 64, "b" * 64)
    assert result.included_counts == (("primary", 1), ("secondary", 1))
    assert result.excluded_counts == (("primary", 1), ("secondary", 0))
    assert result.quarantined_counts == (("primary", 0), ("secondary", 1))


def test_reconstruction_rejects_omission_instead_of_treating_it_as_exclusion() -> None:
    decisions = (
        source_decision("a", ID1, FullBaseDisposition.INCLUDED),
        source_decision("a", ID2, FullBaseDisposition.TARGET_SECURITY_FORM),
        source_decision("b", ID1, FullBaseDisposition.INCLUDED),
    )

    with pytest.raises(ValueError, match="missing=1"):
        reconstruct_daily_universe_membership(
            session_date=SESSION,
            source_decisions=decisions,
            evaluated_base_ids=frozenset({ID1, ID2}),
            source_policy_to_universe={"a": "primary", "b": "secondary"},
            source_fingerprints=("a" * 64,),
            source_data_cutoff=NOW - timedelta(hours=1),
            evaluated_at=NOW,
        )


def test_reconstruction_rejects_future_cutoff() -> None:
    decisions = (source_decision("a", ID1, FullBaseDisposition.INCLUDED),)
    with pytest.raises(ValueError, match="must not follow"):
        reconstruct_daily_universe_membership(
            session_date=SESSION,
            source_decisions=decisions,
            evaluated_base_ids=frozenset({ID1}),
            source_policy_to_universe={"a": "primary"},
            source_fingerprints=("a" * 64,),
            source_data_cutoff=NOW + timedelta(seconds=1),
            evaluated_at=NOW,
        )


def test_reconstruction_rejects_future_dated_membership_evidence() -> None:
    decision = source_decision("a", ID1, FullBaseDisposition.INCLUDED).model_copy(
        update={"membership_evidence_as_of_date": SESSION + timedelta(days=1)}
    )
    with pytest.raises(ValueError, match="future-dated membership evidence"):
        reconstruct_daily_universe_membership(
            session_date=SESSION,
            source_decisions=(decision,),
            evaluated_base_ids=frozenset({ID1}),
            source_policy_to_universe={"a": "primary"},
            source_fingerprints=("a" * 64,),
            source_data_cutoff=NOW - timedelta(hours=1),
            evaluated_at=NOW,
        )


def test_same_session_source_cutoff_does_not_create_later_known_warning() -> None:
    decision = source_decision("a", ID1, FullBaseDisposition.INCLUDED)
    result = reconstruct_daily_universe_membership(
        session_date=SESSION,
        source_decisions=(decision,),
        evaluated_base_ids=frozenset({ID1}),
        source_policy_to_universe={"a": "primary"},
        source_fingerprints=("a" * 64,),
        source_data_cutoff=datetime(2026, 8, 19, 23, 0, tzinfo=UTC),
        evaluated_at=NOW,
    )

    assert result.records[0].quality_status is QualityStatus.VALID
    assert "reconstruction_source_cutoff_after_session" not in result.records[0].reason_codes
