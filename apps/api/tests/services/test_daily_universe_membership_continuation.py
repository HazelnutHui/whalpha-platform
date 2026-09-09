from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.services import daily_universe_membership_continuation as service
from tip_api.services.daily_universe_membership_continuation import (
    DailyUniverseMembershipContinuationError,
    prepare_daily_universe_membership_candidate,
    read_daily_universe_membership_candidate,
)


SESSION = date(2026, 9, 4)
CATALOG = date(2026, 8, 14)
EVALUATED = datetime(2026, 9, 6, 13, 15, tzinfo=UTC)
ASSESSED = datetime(2026, 9, 6, 13, 20, tzinfo=UTC)


def _manifest():
    return SimpleNamespace(
        session_date=SESSION,
        methodology_version=service.METHODOLOGY_VERSION,
        record_count=2,
        logical_fingerprint="a" * 64,
    )


def _assessment(eligibility=PointInTimeEligibility.SIGNAL_ELIGIBLE):
    return SimpleNamespace(
        point_in_time_eligibility=eligibility,
        logical_fingerprint="b" * 64,
    )


def test_builds_one_candidate_and_reports_signal_eligible_without_canonical_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    candidate_root = tmp_path / "candidate"
    batch = SimpleNamespace(
        status="completed",
        completed_session_count=1,
        failed_session_count=0,
        sessions=(
            SimpleNamespace(
                status="published",
                logical_fingerprint="a" * 64,
                failure_code=None,
            ),
        ),
    )
    monkeypatch.setattr(
        service,
        "run_historical_universe_membership_canonical_source_batch",
        lambda **_: batch,
    )
    monkeypatch.setattr(
        service,
        "_read_candidate",
        lambda **_: ((object(), object()), _manifest()),
    )
    monkeypatch.setattr(
        service,
        "assess_universe_membership_knowledge_time",
        lambda **_: _assessment(),
    )

    result = prepare_daily_universe_membership_candidate(
        data_root=data_root,
        session_date=SESSION,
        catalog_as_of_date=CATALOG,
        evaluated_at=EVALUATED,
        assessed_at=ASSESSED,
        candidate_root=candidate_root,
    )

    assert result.status == "candidate_ready_for_publication_plan"
    assert result.candidate_status == "published"
    assert result.record_count == 2
    assert result.point_in_time_eligibility == "signal_eligible"
    assert result.canonical_data_write_count == 0
    assert result.publication_authorized is False
    assert result.website_pipeline_blocked is False


def test_reuses_completed_candidate_and_preserves_outcome_only_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    candidate_root = tmp_path / "candidate"
    partition = service._candidate_partition(
        candidate_root=candidate_root,
        session_date=SESSION,
    )
    partition.mkdir(parents=True)
    monkeypatch.setattr(
        service,
        "run_historical_universe_membership_canonical_source_batch",
        lambda **_: pytest.fail("completed candidate must be reused"),
    )
    monkeypatch.setattr(
        service,
        "_read_candidate",
        lambda **_: ((object(), object()), _manifest()),
    )
    monkeypatch.setattr(
        service,
        "assess_universe_membership_knowledge_time",
        lambda **_: _assessment(
            PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY
        ),
    )

    result = prepare_daily_universe_membership_candidate(
        data_root=data_root,
        session_date=SESSION,
        catalog_as_of_date=CATALOG,
        evaluated_at=EVALUATED,
        assessed_at=ASSESSED,
        candidate_root=candidate_root,
    )

    assert result.status == "outcome_only_candidate"
    assert result.candidate_status == "already_present"
    assert result.point_in_time_eligibility == "outcome_reconciliation_only"


def test_reuses_canonical_completion_before_touching_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    membership, publication = service._canonical_targets(
        data_root=data_root,
        session_date=SESSION,
    )
    membership.mkdir(parents=True)
    publication.mkdir(parents=True)
    canonical = SimpleNamespace(
        records=(object(), object()),
        membership_manifest=SimpleNamespace(logical_fingerprint="a" * 64),
        publication=SimpleNamespace(
            point_in_time_eligibility=PointInTimeEligibility.SIGNAL_ELIGIBLE,
            logical_fingerprint="c" * 64,
            knowledge_time_assessment=SimpleNamespace(
                logical_fingerprint="b" * 64
            ),
        ),
    )
    monkeypatch.setattr(
        service,
        "read_canonical_universe_membership",
        lambda **_: canonical,
    )
    monkeypatch.setattr(
        service,
        "run_historical_universe_membership_canonical_source_batch",
        lambda **_: pytest.fail("canonical completion must be reused"),
    )

    result = prepare_daily_universe_membership_candidate(
        data_root=data_root,
        session_date=SESSION,
        catalog_as_of_date=CATALOG,
        evaluated_at=EVALUATED,
        assessed_at=ASSESSED,
        candidate_root=tmp_path / "candidate",
    )

    assert result.status == "canonical_already_complete"
    assert result.candidate_partition_path is None
    assert result.canonical_publication_fingerprint == "c" * 64


def test_partial_canonical_state_requires_exact_plan_recovery(tmp_path: Path) -> None:
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    membership, _ = service._canonical_targets(
        data_root=data_root,
        session_date=SESSION,
    )
    membership.mkdir(parents=True)

    with pytest.raises(
        DailyUniverseMembershipContinuationError,
        match="exact-plan recovery",
    ):
        prepare_daily_universe_membership_candidate(
            data_root=data_root,
            session_date=SESSION,
            catalog_as_of_date=CATALOG,
            evaluated_at=EVALUATED,
            assessed_at=ASSESSED,
            candidate_root=tmp_path / "candidate",
        )


def test_assessment_cannot_precede_evaluation(tmp_path: Path) -> None:
    with pytest.raises(
        DailyUniverseMembershipContinuationError,
        match="cannot precede evaluation",
    ):
        prepare_daily_universe_membership_candidate(
            data_root=tmp_path / "canonical",
            session_date=SESSION,
            catalog_as_of_date=CATALOG,
            evaluated_at=ASSESSED,
            assessed_at=EVALUATED,
            candidate_root=tmp_path / "candidate",
        )


def test_read_existing_candidate_has_no_build_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    candidate_root = tmp_path / "candidate"
    partition = service._candidate_partition(
        candidate_root=candidate_root,
        session_date=SESSION,
    )
    partition.mkdir(parents=True)
    monkeypatch.setattr(
        service,
        "run_historical_universe_membership_canonical_source_batch",
        lambda **_: pytest.fail("read-only candidate path cannot build"),
    )
    monkeypatch.setattr(
        service,
        "_read_candidate",
        lambda **_: ((object(), object()), _manifest()),
    )
    monkeypatch.setattr(
        service,
        "assess_universe_membership_knowledge_time",
        lambda **_: _assessment(),
    )

    result = read_daily_universe_membership_candidate(
        data_root=data_root,
        session_date=SESSION,
        assessed_at=ASSESSED,
        candidate_root=candidate_root,
    )

    assert result.status == "candidate_ready_for_publication_plan"
    assert result.candidate_status == "already_present"
    assert result.record_count == 2
    assert result.canonical_data_write_count == 0
