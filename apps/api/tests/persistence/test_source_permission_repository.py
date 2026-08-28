from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tip_api.contracts.data_governance.v1 import (
    EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
    SourcePermissionConclusion,
    SourcePermissionReviewV1,
    SourceUsePermissionV1,
    assess_source_uses,
)
from tip_api.persistence.source_permission import (
    SourcePermissionRepositoryError,
    SourcePermissionReviewRepository,
    read_completed_source_permission_review,
)


NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)
EVIDENCE = "a" * 64
FAMILIES = (
    "corporate_action_source_observation",
    "eod_price_bar",
    "point_in_time_identity",
)


def _review() -> SourcePermissionReviewV1:
    return SourcePermissionReviewV1(
        source_id="fixture_source",
        source_display_name="Fixture Source",
        reviewed_at=NOW,
        valid_until=NOW + timedelta(days=30),
        supported_data_family_ids=FAMILIES,
        official_evidence_urls=("https://example.com/official-terms",),
        permissions=tuple(
            SourceUsePermissionV1(
                use_case=item,
                conclusion=SourcePermissionConclusion.CLEARED,
                reason_codes=(),
                evidence_fingerprints=(EVIDENCE,),
            )
            for item in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1
        ),
    )


def _assessments(review: SourcePermissionReviewV1):
    return tuple(
        assess_source_uses(
            review,
            data_family_id=family_id,
            required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
            assessed_at=NOW,
        )
        for family_id in FAMILIES
    )


def test_atomic_round_trip_and_identical_rerun(tmp_path: Path) -> None:
    review = _review()
    repo = SourcePermissionReviewRepository(tmp_path)
    first = repo.publish(
        review=review,
        assessments=_assessments(review),
        created_at=NOW,
    )
    second = repo.publish(
        review=review,
        assessments=_assessments(review),
        created_at=NOW + timedelta(minutes=1),
    )
    completed = read_completed_source_permission_review(
        tmp_path,
        source_id=review.source_id,
        review_fingerprint=first.manifest.review_fingerprint,
    )

    assert first.status == "published"
    assert second.status == "already_present"
    assert completed.review == review
    assert completed.assessments == _assessments(review)
    assert completed.manifest.assessment_count == 3
    assert not list(tmp_path.rglob(".staging-*"))


def test_conflicting_assessments_and_cross_review_bindings_fail(tmp_path: Path) -> None:
    review = _review()
    assessments = _assessments(review)
    repo = SourcePermissionReviewRepository(tmp_path)
    repo.publish(review=review, assessments=assessments, created_at=NOW)

    tampered = list(assessments)
    tampered[1] = tampered[1].model_copy(
        update={"assessed_at": NOW + timedelta(minutes=1)}
    )
    with pytest.raises(SourcePermissionRepositoryError, match="conflicts"):
        repo.publish(review=review, assessments=tuple(tampered), created_at=NOW)

    other_review = review.model_copy(
        update={"official_evidence_urls": ("https://example.com/revised-terms",)}
    )
    with pytest.raises(SourcePermissionRepositoryError, match="bind the review"):
        SourcePermissionReviewRepository(tmp_path / "other").publish(
            review=other_review,
            assessments=assessments,
            created_at=NOW,
        )


def test_corruption_partial_target_and_symlink_root_fail_closed(tmp_path: Path) -> None:
    review = _review()
    result = SourcePermissionReviewRepository(tmp_path).publish(
        review=review,
        assessments=_assessments(review),
        created_at=NOW,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest["assessment_count"] = 99
    result.manifest_path.write_text(
        json.dumps(manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SourcePermissionRepositoryError, match="reconcile"):
        read_completed_source_permission_review(
            tmp_path,
            source_id=review.source_id,
            review_fingerprint=result.manifest.review_fingerprint,
        )

    partial_root = tmp_path / "partial"
    partial = (
        partial_root
        / "governance/source-permission-reviews/schema_version=1"
        / f"source={review.source_id}"
        / f"review={result.manifest.review_fingerprint}"
    )
    partial.mkdir(parents=True)
    with pytest.raises(SourcePermissionRepositoryError, match="incomplete"):
        SourcePermissionReviewRepository(partial_root).publish(
            review=review,
            assessments=_assessments(review),
            created_at=NOW,
        )

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(SourcePermissionRepositoryError, match="symlink"):
        SourcePermissionReviewRepository(link)
    with pytest.raises(SourcePermissionRepositoryError, match="filesystem root"):
        SourcePermissionReviewRepository(Path("/"))
