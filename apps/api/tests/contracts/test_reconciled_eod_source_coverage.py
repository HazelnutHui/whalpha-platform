from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
)
from tip_api.contracts.market_data.v1.reconciled_eod_source_coverage import (
    ReconciledEodSourceCoverageDisposition,
    ReconciledEodSourceCoverageSessionV1,
    ReconciledEodSourceCoverageV1,
    ReconciledEodSourceOrigin,
    seal_reconciled_eod_source_coverage,
)


SESSION = date(2026, 9, 9)
NOW = datetime(2026, 9, 11, 1, tzinfo=UTC)


def selected_original() -> ReconciledEodSourceCoverageSessionV1:
    return ReconciledEodSourceCoverageSessionV1(
        session_date=SESSION,
        disposition=(
            ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
        ),
        observed_candidate_count=1,
        observed_candidate_origins=(
            ReconciledEodSourceOrigin.HISTORICAL_BACKFILL,
        ),
        canonical_eod_fingerprint="1" * 64,
        canonical_identity_fingerprint="2" * 64,
        selected_source_origin=ReconciledEodSourceOrigin.HISTORICAL_BACKFILL,
        selected_source_provenance=(
            ReconciledEodSourceProvenance.RETAINED_ORIGINAL
        ),
        selected_source_observed_at=NOW,
        selected_package_manifest_sha256="3" * 64,
        selected_package_content_sha256="4" * 64,
        selected_binding_plan_sha256="5" * 64,
    )


def coverage(
    session: ReconciledEodSourceCoverageSessionV1,
) -> ReconciledEodSourceCoverageV1:
    counts = {
        "retained_original_session_count": int(
            session.disposition
            == ReconciledEodSourceCoverageDisposition.SELECTED_RETAINED_ORIGINAL
        ),
        "later_reacquisition_session_count": int(
            session.disposition
            == ReconciledEodSourceCoverageDisposition.SELECTED_LATER_REACQUISITION
        ),
        "missing_session_count": int(
            session.disposition == ReconciledEodSourceCoverageDisposition.MISSING
        ),
        "invalid_session_count": int(
            session.disposition == ReconciledEodSourceCoverageDisposition.INVALID
        ),
        "conflict_session_count": int(
            session.disposition == ReconciledEodSourceCoverageDisposition.CONFLICT
        ),
    }
    incomplete = (
        counts["missing_session_count"]
        + counts["invalid_session_count"]
        + counts["conflict_session_count"]
    )
    return seal_reconciled_eod_source_coverage(
        {
            "status": "incomplete" if incomplete else "ready_for_candidate_build",
            "evaluation_first_session": SESSION,
            "evaluation_last_session": SESSION,
            "sessions": (session,),
            "target_session_count": 1,
            **counts,
            "created_at": NOW,
        }
    )


def test_seals_ready_source_coverage_without_persisting_paths() -> None:
    sealed = coverage(selected_original())

    assert sealed.status == "ready_for_candidate_build"
    assert sealed.retained_original_session_count == 1
    assert sealed.external_request_count == 0
    assert sealed.canonical_data_write_count == 0
    assert sealed.source_selection_authorized is False
    assert "/home/" not in sealed.model_dump_json()


def test_missing_session_requires_a_reason_and_keeps_selection_empty() -> None:
    missing = ReconciledEodSourceCoverageSessionV1(
        session_date=SESSION,
        disposition=ReconciledEodSourceCoverageDisposition.MISSING,
        observed_candidate_count=0,
        reason_codes=("grouped_daily_source_package_missing",),
    )
    sealed = coverage(missing)

    assert sealed.status == "incomplete"
    assert sealed.missing_session_count == 1
    assert sealed.sessions[0].selected_source_origin is None


def test_selected_original_requires_a_binding_plan() -> None:
    values = selected_original().model_dump()
    values["selected_binding_plan_sha256"] = None

    with pytest.raises(ValidationError, match="retained-original"):
        ReconciledEodSourceCoverageSessionV1.model_validate(values)


def test_coverage_rejects_incorrect_disposition_counts() -> None:
    sealed = coverage(selected_original())
    values = sealed.model_dump()
    values["retained_original_session_count"] = 0

    with pytest.raises(ValidationError, match="counts differ"):
        ReconciledEodSourceCoverageV1.model_validate(values)


def test_coverage_keeps_warmup_separate_from_evaluation_interval() -> None:
    warmup_session = selected_original().model_copy(
        update={"session_date": date(2026, 9, 8)}
    )
    evaluation_session = selected_original()
    sealed = seal_reconciled_eod_source_coverage(
        {
            "status": "ready_for_candidate_build",
            "evaluation_first_session": SESSION,
            "evaluation_last_session": SESSION,
            "warmup_first_session": date(2026, 9, 8),
            "warmup_last_session": date(2026, 9, 8),
            "sessions": (warmup_session, evaluation_session),
            "target_session_count": 2,
            "retained_original_session_count": 2,
            "later_reacquisition_session_count": 0,
            "missing_session_count": 0,
            "invalid_session_count": 0,
            "conflict_session_count": 0,
            "created_at": NOW,
        }
    )

    assert sealed.warmup_first_session == date(2026, 9, 8)
    assert sealed.evaluation_first_session == SESSION
    assert tuple(item.session_date for item in sealed.sessions) == (
        date(2026, 9, 8),
        SESSION,
    )


def test_coverage_rejects_partial_warmup_bounds() -> None:
    sealed = coverage(selected_original())
    values = sealed.model_dump()
    values["warmup_first_session"] = date(2026, 9, 8)

    with pytest.raises(ValidationError, match="both"):
        ReconciledEodSourceCoverageV1.model_validate(values)
