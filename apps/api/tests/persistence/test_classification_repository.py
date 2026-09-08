from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    ClassificationAssignmentBasis,
    ClassificationCoverageDecisionV1,
    ClassificationCoverageStatus,
    ClassificationDefinitionStatus,
    ClassificationDefinitionV1,
    ClassificationEligibilityScope,
    ClassificationIdentityEvidenceKind,
    ClassificationMembershipRole,
    ClassificationMembershipV1,
    ClassificationObservationStatus,
    ClassificationReviewStatus,
    ClassificationSourceObservationV1,
    ClassificationType,
    ExternalClassificationPathNodeV1,
    KnowledgeTimeStatus,
    ResolutionStatus,
)
from tip_api.persistence.classification import (
    ClassificationConflictError,
    ClassificationCorruptionError,
    ClassificationPersistenceError,
)
from tip_api.persistence.parquet.classification import (
    COVERAGE_FILE,
    DEFINITION_SCHEMA,
    DEFINITIONS_FILE,
    MEMBERSHIPS_FILE,
    OBSERVATIONS_FILE,
    ParquetClassificationRepository,
)


AS_OF = date(2026, 9, 4)
CREATED_AT = datetime(2026, 9, 8, 20, 0, tzinfo=UTC)
AVAILABLE_AT = CREATED_AT - timedelta(hours=1)
METHOD = "whalpha-traditional-v1"
PROVIDER = "sp-global"
PERMISSION = "a" * 64
INSTRUMENT_1 = UUID("11111111-1111-4111-8111-111111111111")
INSTRUMENT_2 = UUID("22222222-2222-4222-8222-222222222222")
SECTOR_ID = UUID("33333333-3333-4333-8333-333333333333")
GROUP_ID = UUID("44444444-4444-4444-8444-444444444444")
SECOND_SECTOR_ID = UUID("55555555-5555-4555-8555-555555555555")
OBSERVATION_ID = "gics-company-1-revision-7"


def definitions() -> tuple[ClassificationDefinitionV1, ...]:
    return (
        ClassificationDefinitionV1(
            classification_id=GROUP_ID,
            classification_type=ClassificationType.INDUSTRY_GROUP,
            name="Software & Services",
            parent_classification_id=SECTOR_ID,
            methodology_version=METHOD,
            status=ClassificationDefinitionStatus.ACTIVE,
            valid_from=date(2024, 1, 1),
            source="whalpha",
        ),
        ClassificationDefinitionV1(
            classification_id=SECTOR_ID,
            classification_type=ClassificationType.SECTOR,
            name="Information Technology",
            methodology_version=METHOD,
            status=ClassificationDefinitionStatus.ACTIVE,
            valid_from=date(2024, 1, 1),
            source="whalpha",
        ),
    )


def observation(
    *,
    scope: ClassificationEligibilityScope = ClassificationEligibilityScope.HISTORICAL_RESEARCH,
) -> ClassificationSourceObservationV1:
    return ClassificationSourceObservationV1(
        source_observation_id=OBSERVATION_ID,
        provider=PROVIDER,
        as_of_date=AS_OF,
        source_entity_id="company-1",
        source_security_id="security-1",
        instrument_id=INSTRUMENT_1,
        identity_resolution_status=ResolutionStatus.RESOLVED,
        identity_evidence=(ClassificationIdentityEvidenceKind.SHARE_CLASS_FIGI,),
        assignment_basis=ClassificationAssignmentBasis.DIRECT_SECURITY,
        external_taxonomy="GICS",
        external_taxonomy_version="2026",
        external_classification_code="4510",
        external_classification_path=(
            ExternalClassificationPathNodeV1(
                level=1,
                code="45",
                name="Information Technology",
                level_name="sector",
            ),
            ExternalClassificationPathNodeV1(
                level=2,
                code="4510",
                name="Software & Services",
                level_name="industry_group",
            ),
        ),
        valid_from=date(2024, 1, 1),
        knowledge_time_status=KnowledgeTimeStatus.SOURCE_TIMESTAMP,
        source_available_at=AVAILABLE_AT,
        provider_updated_at=AVAILABLE_AT,
        observed_at=CREATED_AT,
        revision_id="7",
        correction_status=ClassificationObservationStatus.ACTIVE,
        permission_review_fingerprint=PERMISSION,
        eligibility_scope=scope,
        quality_status=QualityStatus.VALID,
    )


def membership(
    classification_id: UUID,
    *,
    scope: ClassificationEligibilityScope = ClassificationEligibilityScope.HISTORICAL_RESEARCH,
) -> ClassificationMembershipV1:
    return ClassificationMembershipV1(
        instrument_id=INSTRUMENT_1,
        classification_id=classification_id,
        valid_from=date(2024, 1, 1),
        membership_role=ClassificationMembershipRole.PRIMARY,
        confidence=Decimal("1"),
        source=PROVIDER,
        source_observation_id=OBSERVATION_ID,
        assignment_basis=ClassificationAssignmentBasis.DIRECT_SECURITY,
        source_available_at=AVAILABLE_AT,
        eligibility_scope=scope,
        assigned_at=CREATED_AT,
        review_status=ClassificationReviewStatus.AUTO_RESOLVED,
        methodology_version=METHOD,
        quality_status=QualityStatus.VALID,
    )


def coverage(
    *,
    missing_reason: str = "source_not_covered",
    scope: ClassificationEligibilityScope = ClassificationEligibilityScope.HISTORICAL_RESEARCH,
) -> tuple[ClassificationCoverageDecisionV1, ...]:
    return (
        ClassificationCoverageDecisionV1(
            instrument_id=INSTRUMENT_2,
            as_of_date=AS_OF,
            status=ClassificationCoverageStatus.NOT_COVERED,
            eligibility_scope=ClassificationEligibilityScope.INELIGIBLE,
            reason_codes=(missing_reason,),
            evaluated_at=CREATED_AT,
            quality_status=QualityStatus.PENDING_REVIEW,
        ),
        ClassificationCoverageDecisionV1(
            instrument_id=INSTRUMENT_1,
            as_of_date=AS_OF,
            status=ClassificationCoverageStatus.CLASSIFIED,
            source_observation_ids=(OBSERVATION_ID,),
            classification_ids=(SECTOR_ID, GROUP_ID),
            eligibility_scope=scope,
            evaluated_at=CREATED_AT,
            quality_status=QualityStatus.VALID,
        ),
    )


def publish(
    repository: ParquetClassificationRepository,
    *,
    definition_records: tuple[ClassificationDefinitionV1, ...] | None = None,
    observation_records: tuple[ClassificationSourceObservationV1, ...] | None = None,
    coverage_records: tuple[ClassificationCoverageDecisionV1, ...] | None = None,
    membership_records: tuple[ClassificationMembershipV1, ...] | None = None,
    permission_review_fingerprints: tuple[str, ...] = (PERMISSION,),
):
    return repository.publish_snapshot(
        definitions=definition_records or definitions(),
        observations=observation_records or (observation(),),
        coverage=coverage_records or coverage(),
        memberships=membership_records or (membership(SECTOR_ID), membership(GROUP_ID)),
        as_of_date=AS_OF,
        methodology_version=METHOD,
        providers=(PROVIDER,),
        permission_review_fingerprints=permission_review_fingerprints,
        created_at=CREATED_AT,
    )


def test_snapshot_round_trip_is_atomic_sorted_and_idempotent(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)

    result = publish(repository)
    completed = repository.read_snapshot(as_of_date=AS_OF, methodology_version=METHOD)
    again = publish(repository)

    assert result.status == "published"
    assert again.status == "already_present"
    assert tuple(item.classification_id for item in completed.definitions) == (
        SECTOR_ID,
        GROUP_ID,
    )
    assert tuple(item.instrument_id for item in completed.coverage) == (
        INSTRUMENT_1,
        INSTRUMENT_2,
    )
    assert completed.manifest.coverage_count == 2
    assert completed.manifest.membership_count == 2
    assert completed.manifest.current_display_eligible_count == 1
    assert completed.manifest.historical_research_eligible_count == 1
    summaries = {
        item.status: item.count for item in completed.manifest.coverage_summaries
    }
    assert summaries[ClassificationCoverageStatus.CLASSIFIED] == 1
    assert summaries[ClassificationCoverageStatus.NOT_COVERED] == 1
    assert {item.name for item in result.partition_path.iterdir()} == {
        "manifest.json",
        DEFINITIONS_FILE,
        OBSERVATIONS_FILE,
        COVERAGE_FILE,
        MEMBERSHIPS_FILE,
    }


def test_conflicting_immutable_rerun_is_rejected(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)
    publish(repository)

    with pytest.raises(ClassificationConflictError, match="conflicts"):
        publish(repository, coverage_records=coverage(missing_reason="vendor_not_covered"))


def test_missing_parent_membership_is_rejected_before_filesystem_write(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)

    with pytest.raises(ClassificationPersistenceError, match="covering parent"):
        publish(
            repository,
            membership_records=(membership(GROUP_ID),),
            coverage_records=(
                coverage()[0],
                coverage()[1].model_copy(update={"classification_ids": (GROUP_ID,)}),
            ),
        )

    assert tuple(tmp_path.iterdir()) == ()


def test_permission_review_is_required_before_filesystem_write(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)

    with pytest.raises(ClassificationPersistenceError, match="non-empty SHA-256"):
        publish(repository, permission_review_fingerprints=())

    assert tuple(tmp_path.iterdir()) == ()


def test_membership_cannot_exceed_observation_eligibility(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)

    with pytest.raises(ClassificationPersistenceError, match="eligibility exceeds"):
        publish(
            repository,
            observation_records=(
                observation(scope=ClassificationEligibilityScope.CURRENT_DISPLAY_ONLY),
            ),
        )


def test_revision_target_must_exist_before_filesystem_write(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)
    revised = ClassificationSourceObservationV1.model_validate(
        {
            **observation().model_dump(mode="python"),
            "source_observation_id": "gics-company-1-revision-8",
            "revision_id": "8",
            "correction_status": ClassificationObservationStatus.CORRECTED,
            "supersedes_source_observation_id": "missing-revision-7",
            "observed_at": CREATED_AT + timedelta(minutes=1),
        }
    )

    with pytest.raises(ClassificationPersistenceError, match="references unknown"):
        publish(repository, observation_records=(revised,))

    assert tuple(tmp_path.iterdir()) == ()


def test_membership_cannot_reference_superseded_observation(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)
    revised = ClassificationSourceObservationV1.model_validate(
        {
            **observation().model_dump(mode="python"),
            "source_observation_id": "gics-company-1-revision-8",
            "revision_id": "8",
            "correction_status": ClassificationObservationStatus.CORRECTED,
            "supersedes_source_observation_id": OBSERVATION_ID,
            "observed_at": CREATED_AT + timedelta(minutes=1),
        }
    )

    with pytest.raises(ClassificationPersistenceError, match="superseded"):
        publish(repository, observation_records=(observation(), revised))

    assert tuple(tmp_path.iterdir()) == ()


def test_same_type_overlapping_traditional_memberships_are_rejected(tmp_path) -> None:
    second_sector = ClassificationDefinitionV1(
        classification_id=SECOND_SECTOR_ID,
        classification_type=ClassificationType.SECTOR,
        name="Industrials",
        methodology_version=METHOD,
        status=ClassificationDefinitionStatus.ACTIVE,
        valid_from=date(2024, 1, 1),
        source="whalpha",
    )
    decision = coverage()[1].model_copy(
        update={"classification_ids": (SECTOR_ID, GROUP_ID, SECOND_SECTOR_ID)}
    )
    repository = ParquetClassificationRepository(tmp_path)

    with pytest.raises(ClassificationPersistenceError, match="intervals overlap"):
        publish(
            repository,
            definition_records=definitions() + (second_sector,),
            coverage_records=(coverage()[0], decision),
            membership_records=(
                membership(SECTOR_ID),
                membership(GROUP_ID),
                membership(SECOND_SECTOR_ID),
            ),
        )


def test_reader_rejects_parquet_drift(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)
    result = publish(repository)
    path = result.partition_path / COVERAGE_FILE
    payload = path.read_bytes()
    path.write_bytes(payload + b"drift")

    with pytest.raises(ClassificationCorruptionError, match="physical hash"):
        repository.read_snapshot(as_of_date=AS_OF, methodology_version=METHOD)


def test_reader_rejects_manifest_count_drift(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)
    result = publish(repository)
    manifest_path = result.manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["coverage_count"] = 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ClassificationCorruptionError, match="manifest is invalid"):
        repository.read_snapshot(as_of_date=AS_OF, methodology_version=METHOD)


def test_reader_rejects_extra_snapshot_file(tmp_path) -> None:
    repository = ParquetClassificationRepository(tmp_path)
    result = publish(repository)
    (result.partition_path / "unexpected.txt").write_text("unexpected", encoding="utf-8")

    with pytest.raises(ClassificationCorruptionError, match="file set differs"):
        repository.read_snapshot(as_of_date=AS_OF, methodology_version=METHOD)


def test_definition_schema_is_explicit() -> None:
    assert DEFINITION_SCHEMA.names == [
        "schema_version",
        "classification_id",
        "classification_type",
        "name",
        "description",
        "parent_classification_id",
        "methodology_version",
        "status",
        "valid_from",
        "valid_to",
        "source",
    ]
