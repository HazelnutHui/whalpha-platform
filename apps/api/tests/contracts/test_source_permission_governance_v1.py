from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from tip_api.contracts.data_governance.v1 import (
    EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
    SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
    SourcePermissionConclusion,
    SourcePermissionReviewV1,
    SourceUseAssessmentStatus,
    SourceUseCase,
    SourceUsePermissionV1,
    assess_source_uses,
    source_permission_review_fingerprint,
)


NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)
EVIDENCE = "a" * 64


def _permission(
    use_case: SourceUseCase,
    conclusion: SourcePermissionConclusion = SourcePermissionConclusion.CLEARED,
) -> SourceUsePermissionV1:
    reasons = () if conclusion is SourcePermissionConclusion.CLEARED else ("terms_gate",)
    return SourceUsePermissionV1(
        use_case=use_case,
        conclusion=conclusion,
        reason_codes=reasons,
        evidence_fingerprints=(EVIDENCE,),
    )


def _review(**overrides) -> SourcePermissionReviewV1:
    values = {
        "source_id": "example_source",
        "source_display_name": "Example Source",
        "reviewed_at": NOW,
        "valid_until": NOW + timedelta(days=90),
        "supported_data_family_ids": ("eod_price_bar",),
        "official_evidence_urls": ("https://example.com/official-terms",),
        "permissions": tuple(_permission(item) for item in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1),
    }
    values.update(overrides)
    return SourcePermissionReviewV1(**values)


def test_fully_cleared_review_can_pass_required_equal_capability_uses() -> None:
    review = _review()
    result = assess_source_uses(
        review,
        data_family_id="eod_price_bar",
        required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
        assessed_at=NOW + timedelta(days=1),
    )

    assert result.status is SourceUseAssessmentStatus.ELIGIBLE_FOR_REQUIRED_USES
    assert result.blocking_use_cases == ()
    assert result.unresolved_use_cases == ()
    assert result.permission_review_valid_until == review.valid_until
    assert result.operational_authority == "none"
    assert result.permission_review_fingerprint == source_permission_review_fingerprint(review)
    assert len(SOURCE_PERMISSION_POLICY_FINGERPRINT_V1) == 64


def test_one_external_display_gate_blocks_the_whole_shared_source() -> None:
    permissions = tuple(
        _permission(
            item,
            SourcePermissionConclusion.BLOCKED
            if item is SourceUseCase.EQUAL_CAPABILITY_DERIVED_DISPLAY
            else SourcePermissionConclusion.CLEARED,
        )
        for item in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1
    )
    result = assess_source_uses(
        _review(permissions=permissions),
        data_family_id="eod_price_bar",
        required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
        assessed_at=NOW,
    )

    assert result.status is SourceUseAssessmentStatus.BLOCKED_BY_PERMISSION
    assert result.blocking_use_cases == (
        SourceUseCase.EQUAL_CAPABILITY_DERIVED_DISPLAY,
    )
    assert result.operational_authority == "none"


def test_separate_agreement_is_unresolved_not_implicitly_cleared() -> None:
    permissions = tuple(
        _permission(
            item,
            SourcePermissionConclusion.REQUIRES_SEPARATE_PERMISSION
            if item is SourceUseCase.EQUAL_CAPABILITY_MACHINE_DELIVERY
            else SourcePermissionConclusion.CLEARED,
        )
        for item in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1
    )
    result = assess_source_uses(
        _review(permissions=permissions),
        data_family_id="eod_price_bar",
        required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
        assessed_at=NOW,
    )

    assert result.status is SourceUseAssessmentStatus.UNRESOLVED_PERMISSION
    assert result.unresolved_use_cases == (
        SourceUseCase.EQUAL_CAPABILITY_MACHINE_DELIVERY,
    )


def test_stale_review_and_unsupported_family_fail_closed() -> None:
    review = _review(valid_until=NOW + timedelta(days=1))
    stale = assess_source_uses(
        review,
        data_family_id="eod_price_bar",
        required_use_cases=(SourceUseCase.DELL_ACQUISITION,),
        assessed_at=NOW + timedelta(days=2),
    )
    unsupported = assess_source_uses(
        _review(),
        data_family_id="corporate_action",
        required_use_cases=(SourceUseCase.DELL_ACQUISITION,),
        assessed_at=NOW,
    )

    assert stale.status is SourceUseAssessmentStatus.STALE_PERMISSION_REVIEW
    assert unsupported.status is SourceUseAssessmentStatus.UNSUPPORTED_DATA_FAMILY


def test_review_rejects_partial_permissions_and_unsafe_evidence_urls() -> None:
    with pytest.raises(ValidationError, match="every use case"):
        _review(permissions=(_permission(SourceUseCase.DELL_ACQUISITION),))
    with pytest.raises(ValidationError, match="public HTTPS"):
        _review(official_evidence_urls=("https://user:secret@example.com/terms",))


def test_non_cleared_conclusion_requires_reason_and_all_conclusions_need_evidence() -> None:
    with pytest.raises(ValidationError, match="require reason"):
        SourceUsePermissionV1(
            use_case=SourceUseCase.DELL_ACQUISITION,
            conclusion=SourcePermissionConclusion.UNRESOLVED,
            reason_codes=(),
            evidence_fingerprints=(EVIDENCE,),
        )
    with pytest.raises(ValidationError, match="requires evidence"):
        SourceUsePermissionV1(
            use_case=SourceUseCase.DELL_ACQUISITION,
            conclusion=SourcePermissionConclusion.CLEARED,
            reason_codes=(),
            evidence_fingerprints=(),
        )
