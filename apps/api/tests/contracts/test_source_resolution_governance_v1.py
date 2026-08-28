from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.data_governance.v1 import (
    DataFamilySourceResolutionPolicyV1,
    SourceEvidenceRole,
    SourceFactEvidenceV1,
    SourceResolutionBindingV1,
    SourceResolutionMode,
    SourceResolutionStatus,
    resolve_source_facts,
)


NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)
FACT_A = "a" * 64
FACT_B = "b" * 64


def _binding(
    source_id: str,
    role: SourceEvidenceRole,
    rank: int,
) -> SourceResolutionBindingV1:
    return SourceResolutionBindingV1(
        source_id=source_id,
        evidence_role=role,
        precedence_rank=rank,
        permission_review_fingerprint=str(rank) * 64,
    )


def _policy(**overrides) -> DataFamilySourceResolutionPolicyV1:
    values = {
        "data_family_id": "corporate_action",
        "fact_scope": "split_ratio",
        "resolution_mode": SourceResolutionMode.PRIMARY_WITH_CORROBORATION,
        "sources": (
            _binding("primary_source", SourceEvidenceRole.PRIMARY, 1),
            _binding("confirming_source", SourceEvidenceRole.CORROBORATING, 2),
            _binding("identifier_crosswalk", SourceEvidenceRole.CROSSWALK_ONLY, 3),
        ),
        "required_matching_sources": 2,
    }
    values.update(overrides)
    return DataFamilySourceResolutionPolicyV1(**values)


def _evidence(
    source_id: str,
    fact_fingerprint: str = FACT_A,
    *,
    quality_status: QualityStatus = QualityStatus.VALID,
    review_digit: str | None = None,
    **overrides,
) -> SourceFactEvidenceV1:
    source_digits = {
        "primary_source": "1",
        "confirming_source": "2",
        "identifier_crosswalk": "3",
        "authority": "1",
        "second_source": "2",
    }
    values = {
        "source_id": source_id,
        "data_family_id": "corporate_action",
        "fact_scope": "split_ratio",
        "stable_subject_id": "instrument:018f7f16-7d7f-7f4a-a277-111111111111",
        "effective_at": NOW,
        "fact_fingerprint": fact_fingerprint,
        "permission_review_fingerprint": (review_digit or source_digits[source_id]) * 64,
        "quality_status": quality_status,
    }
    values.update(overrides)
    return SourceFactEvidenceV1(**values)


def test_primary_and_corroborator_must_match_before_resolution() -> None:
    decision = resolve_source_facts(
        _policy(),
        (_evidence("primary_source"), _evidence("confirming_source")),
    )

    assert decision.status is SourceResolutionStatus.CORROBORATED
    assert decision.selected_fact_fingerprint == FACT_A
    assert decision.supporting_source_ids == ("confirming_source", "primary_source")
    assert decision.operational_authority == "none"


def test_any_resolving_source_conflict_quarantines_instead_of_voting() -> None:
    decision = resolve_source_facts(
        _policy(),
        (_evidence("primary_source"), _evidence("confirming_source", FACT_B)),
    )

    assert decision.status is SourceResolutionStatus.QUARANTINED_CONFLICT
    assert decision.selected_fact_fingerprint is None
    assert decision.conflicting_source_ids == ("confirming_source",)
    assert decision.reason_codes == ("resolving_sources_disagree",)


def test_missing_corroboration_is_unavailable_not_first_non_null() -> None:
    decision = resolve_source_facts(_policy(), (_evidence("primary_source"),))

    assert decision.status is SourceResolutionStatus.UNAVAILABLE
    assert decision.selected_fact_fingerprint is None
    assert decision.reason_codes == ("required_matching_evidence_unavailable",)


def test_crosswalk_and_unresolved_quality_cannot_resolve_a_fact() -> None:
    decision = resolve_source_facts(
        _policy(),
        (
            _evidence("primary_source"),
            _evidence("confirming_source", quality_status=QualityStatus.PENDING_REVIEW),
            _evidence("identifier_crosswalk"),
        ),
    )

    assert decision.status is SourceResolutionStatus.UNAVAILABLE
    assert decision.excluded_source_ids == ("confirming_source", "identifier_crosswalk")


def test_single_authority_resolves_without_using_lower_priority_fallback() -> None:
    policy = _policy(
        resolution_mode=SourceResolutionMode.SINGLE_AUTHORITY,
        sources=(
            _binding("authority", SourceEvidenceRole.AUTHORITATIVE, 1),
            _binding("second_source", SourceEvidenceRole.CORROBORATING, 2),
        ),
        required_matching_sources=1,
    )
    decision = resolve_source_facts(policy, (_evidence("authority"),))

    assert decision.status is SourceResolutionStatus.RESOLVED
    assert decision.selected_fact_fingerprint == FACT_A


def test_policy_and_evidence_bindings_fail_closed() -> None:
    with pytest.raises(ValidationError, match="standard data family"):
        _policy(data_family_id="unknown_family")
    with pytest.raises(ValidationError, match="contiguous precedence"):
        _policy(
            sources=(
                _binding("primary_source", SourceEvidenceRole.PRIMARY, 1),
                _binding("confirming_source", SourceEvidenceRole.CORROBORATING, 3),
            )
        )
    with pytest.raises(ValueError, match="permission review"):
        resolve_source_facts(
            _policy(),
            (_evidence("primary_source", review_digit="9"),),
        )
    with pytest.raises(ValueError, match="one exact stable-ID fact"):
        resolve_source_facts(
            _policy(),
            (
                _evidence("primary_source"),
                _evidence("confirming_source", stable_subject_id="instrument:other"),
            ),
        )


def test_policy_cannot_enable_ticker_join_or_first_non_null() -> None:
    with pytest.raises(ValidationError):
        _policy(first_non_null_allowed=True)
    with pytest.raises(ValidationError):
        _policy(ticker_join_allowed=True)
