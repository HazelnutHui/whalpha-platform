from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.data_governance.v1 import (
    SHARED_CONTENT_ACCESS_POLICY_V1,
    STANDARD_DATA_FAMILY_REGISTRY_V1,
    ContentScope,
    CoverageStatus,
    DataFamilyDefinitionV1,
    DataLayer,
    EvidenceStatus,
    GovernedRecordClassificationV1,
    PointInTimeEligibility,
    RecordDisposition,
    RetentionClass,
    SharedContentAccessPolicyV1,
    StableKeyKind,
    WebServingPolicy,
    validate_governance_registry,
)


RECORD = "a" * 64
REPLACEMENT = "b" * 64
EVIDENCE = "c" * 64
AVAILABLE = datetime(2026, 8, 26, 20, 1, tzinfo=UTC)
CUTOFF = datetime(2026, 8, 26, 20, 5, tzinfo=UTC)
INGESTED = datetime(2026, 8, 26, 20, 10, tzinfo=UTC)
CLASSIFIED = datetime(2026, 8, 26, 20, 11, tzinfo=UTC)


def _record(**overrides) -> GovernedRecordClassificationV1:
    values = {
        "data_family_id": "opportunity_candidate",
        "record_fingerprint": RECORD,
        "layer": DataLayer.ANALYTIC_RESULT,
        "content_scope": ContentScope.SHARED_PRODUCT,
        "disposition": RecordDisposition.ACCEPTED,
        "evidence_status": EvidenceStatus.SUFFICIENT,
        "quality_status": QualityStatus.VALID,
        "coverage_status": CoverageStatus.COMPLETE,
        "point_in_time_eligibility": PointInTimeEligibility.SIGNAL_ELIGIBLE,
        "retention_class": RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
        "web_serving_policy": WebServingPolicy.ELIGIBLE_EQUAL_CAPABILITY,
        "source_available_at": AVAILABLE,
        "signal_cutoff_at": CUTOFF,
        "ingested_at": INGESTED,
        "classified_at": CLASSIFIED,
        "reason_codes": (),
        "evidence_fingerprints": (EVIDENCE,),
    }
    values.update(overrides)
    return GovernedRecordClassificationV1(**values)


def test_shared_access_policy_cannot_encode_guest_or_login_differences() -> None:
    assert SHARED_CONTENT_ACCESS_POLICY_V1.guest_and_credential_content_identical
    assert not SHARED_CONTENT_ACCESS_POLICY_V1.role_dependent_market_entitlements_allowed
    assert (
        SHARED_CONTENT_ACCESS_POLICY_V1.incompatible_source_handling
        == "block_for_all_shared_sessions"
    )
    assert "owner_only" not in {item.value for item in WebServingPolicy}

    with pytest.raises(ValidationError):
        SharedContentAccessPolicyV1(
            guest_and_credential_content_identical=False,
        )


def test_standard_registry_is_unique_ordered_and_covers_core_data_families() -> None:
    validate_governance_registry(STANDARD_DATA_FAMILY_REGISTRY_V1)
    ids = tuple(item.data_family_id for item in STANDARD_DATA_FAMILY_REGISTRY_V1)

    assert ids == tuple(sorted(ids))
    assert len(ids) == len(set(ids))
    assert {
        "eod_price_bar",
        "point_in_time_identity",
        "universe_membership",
        "corporate_action",
        "instrument_lifecycle",
        "adjustment_ledger",
        "historical_coverage",
        "sealed_strategy_signal",
        "matured_stock_outcome",
    }.issubset(ids)


def test_valid_shared_record_is_signal_eligible_and_equal_capability() -> None:
    record = _record(
        reason_codes=(" transparent_evidence ", "channel_scoped"),
        evidence_fingerprints=(EVIDENCE, EVIDENCE),
    )

    assert record.reason_codes == ("channel_scoped", "transparent_evidence")
    assert record.evidence_fingerprints == (EVIDENCE,)
    validate_governance_registry(
        STANDARD_DATA_FAMILY_REGISTRY_V1,
        (record,),
    )


def test_internal_source_record_can_be_retained_but_blocked_from_all_web_sessions() -> None:
    record = _record(
        data_family_id="corporate_action_source_observation",
        layer=DataLayer.SOURCE_OBSERVATION,
        content_scope=ContentScope.INTERNAL_ONLY,
        point_in_time_eligibility=PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY,
        retention_class=RetentionClass.APPEND_ONLY_EVENT_HISTORY,
        web_serving_policy=WebServingPolicy.BLOCKED_ALL_SHARED_SESSIONS,
        signal_cutoff_at=None,
    )

    validate_governance_registry(
        STANDARD_DATA_FAMILY_REGISTRY_V1,
        (record,),
    )


def test_unknown_availability_and_quarantine_remain_explicit() -> None:
    record = _record(
        data_family_id="corporate_action_source_observation",
        layer=DataLayer.SOURCE_OBSERVATION,
        content_scope=ContentScope.INTERNAL_ONLY,
        disposition=RecordDisposition.QUARANTINED,
        evidence_status=EvidenceStatus.UNKNOWN,
        quality_status=QualityStatus.PENDING_REVIEW,
        coverage_status=CoverageStatus.PARTIAL,
        point_in_time_eligibility=(
            PointInTimeEligibility.INELIGIBLE_UNKNOWN_AVAILABILITY
        ),
        retention_class=RetentionClass.APPEND_ONLY_EVENT_HISTORY,
        web_serving_policy=WebServingPolicy.BLOCKED_ALL_SHARED_SESSIONS,
        source_available_at=None,
        signal_cutoff_at=None,
        reason_codes=("source_availability_unknown",),
    )

    validate_governance_registry(
        STANDARD_DATA_FAMILY_REGISTRY_V1,
        (record,),
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        (
            {
                "disposition": RecordDisposition.QUARANTINED,
                "evidence_status": EvidenceStatus.UNKNOWN,
                "quality_status": QualityStatus.PENDING_REVIEW,
            },
            "reason codes",
        ),
        (
            {"evidence_status": EvidenceStatus.CONFLICTING},
            "unresolved evidence",
        ),
        (
            {"source_available_at": CUTOFF + timedelta(minutes=1)},
            "signal cutoff",
        ),
        (
            {"classified_at": INGESTED - timedelta(seconds=1)},
            "precede ingestion",
        ),
        (
            {"web_serving_policy": WebServingPolicy.USER_IDENTITY_REQUIRED},
            "shared content",
        ),
        (
            {
                "content_scope": ContentScope.INTERNAL_ONLY,
                "web_serving_policy": WebServingPolicy.ELIGIBLE_EQUAL_CAPABILITY,
            },
            "internal-only",
        ),
    ),
)
def test_orthogonal_dimensions_fail_closed(overrides, message) -> None:
    with pytest.raises(ValidationError, match=message):
        _record(**overrides)


def test_superseded_revision_requires_a_distinct_replacement() -> None:
    record = _record(
        disposition=RecordDisposition.SUPERSEDED,
        point_in_time_eligibility=PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY,
        signal_cutoff_at=None,
        superseded_by_record_fingerprint=REPLACEMENT,
    )
    assert record.superseded_by_record_fingerprint == REPLACEMENT

    with pytest.raises(ValidationError, match="cannot supersede itself"):
        _record(
            disposition=RecordDisposition.SUPERSEDED,
            point_in_time_eligibility=(
                PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY
            ),
            signal_cutoff_at=None,
            superseded_by_record_fingerprint=RECORD,
        )


def test_future_user_private_family_requires_identity_isolation_not_a_guest_tier() -> None:
    family = DataFamilyDefinitionV1(
        data_family_id="portfolio_position",
        layer=DataLayer.CANONICAL_FACT,
        stable_key_kind=StableKeyKind.METHODOLOGY_SCOPE,
        grain="user identity, account, instrument, observation time",
        description="Future private position record.",
        retention_class=RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
        point_in_time_required=True,
        allowed_content_scopes=(ContentScope.USER_PRIVATE,),
    )
    record = _record(
        data_family_id="portfolio_position",
        layer=DataLayer.CANONICAL_FACT,
        content_scope=ContentScope.USER_PRIVATE,
        retention_class=RetentionClass.CANONICAL_NO_AUTO_EXPIRY,
        web_serving_policy=WebServingPolicy.USER_IDENTITY_REQUIRED,
    )

    validate_governance_registry((family,), (record,))
    with pytest.raises(ValidationError, match="identity isolation"):
        _record(
            data_family_id="portfolio_position",
            layer=DataLayer.CANONICAL_FACT,
            content_scope=ContentScope.USER_PRIVATE,
            web_serving_policy=WebServingPolicy.NOT_ASSESSED,
        )


def test_registry_rejects_undefined_family_and_dimension_drift() -> None:
    with pytest.raises(ValueError, match="undefined"):
        validate_governance_registry(
            STANDARD_DATA_FAMILY_REGISTRY_V1,
            (_record(data_family_id="unknown_family"),),
        )
    with pytest.raises(ValueError, match="layer"):
        validate_governance_registry(
            STANDARD_DATA_FAMILY_REGISTRY_V1,
            (_record(layer=DataLayer.CANONICAL_FACT),),
        )
