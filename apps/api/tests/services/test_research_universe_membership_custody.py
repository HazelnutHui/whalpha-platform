from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    RESEARCH_UNIVERSE_MEMBERSHIP_PERMITTED_USES,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.services import research_universe_membership_apply as apply_service
from tip_api.services import (
    research_universe_membership_apply_plan as plan_service,
)
from tip_api.services import research_universe_membership_canonical as reader_service
from tip_api.services.research_universe_membership_apply import (
    apply_research_universe_membership_plan,
)
from tip_api.services.research_universe_membership_apply_plan import (
    ResearchUniverseMembershipApplyPlanError,
    build_research_universe_membership_apply_plan,
    read_research_universe_membership_apply_plan,
)
from tip_api.services.research_universe_membership_archive import (
    archive_research_universe_membership_candidates,
)
from tip_api.services.research_universe_membership_canonical import (
    read_canonical_research_universe_membership,
)
from tip_api.services.universe_membership_reconstruction import (
    stable_instrument_set_fingerprint,
)


SESSION = date(2025, 1, 2)
SESSION_CLOSE = datetime(2025, 1, 2, 21, tzinfo=UTC)
SOURCE_CUTOFF = datetime(2026, 9, 1, 12, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 9, 1, 13, tzinfo=UTC)
CREATED_AT = datetime(2026, 9, 10, 9, tzinfo=UTC)
SOURCE_FINGERPRINT = "a" * 64


class _Calendar:
    def session_close(self, session_date: date) -> datetime:
        assert session_date == SESSION
        return SESSION_CLOSE


def _fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    origin: UniverseMembershipOrigin = (
        UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME
    ),
):
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir(mode=0o700)
    candidate_root.chmod(0o700)
    instrument_id = UUID("11111111-1111-4111-8111-111111111111")
    record = UniverseMembershipDecisionV1(
        universe_id="primary",
        instrument_id=instrument_id,
        session_date=SESSION,
        methodology_version="fixture-v1",
        origin=origin,
        disposition=UniverseMembershipDisposition.INCLUDED,
        is_member=True,
        reason_codes=("included",),
        evaluated_base_fingerprint=stable_instrument_set_fingerprint(
            frozenset({instrument_id})
        ),
        source_fingerprints=(SOURCE_FINGERPRINT,),
        source_data_cutoff=SOURCE_CUTOFF,
        evaluated_at=EVALUATED_AT,
        quality_status=QualityStatus.VALID,
    )
    published = ParquetHistoricalResearchRepository(
        candidate_root,
        created_at=EVALUATED_AT,
    ).publish_universe_membership(
        (record,),
        methodology_version=record.methodology_version,
        session_date=SESSION,
    )
    approved = data_root.resolve()
    monkeypatch.setattr(plan_service, "APPROVED_DATA_ROOT", approved)
    monkeypatch.setattr(apply_service, "APPROVED_DATA_ROOT", approved)
    monkeypatch.setattr(reader_service, "APPROVED_DATA_ROOT", approved)
    return data_root, published.partition_path


def _plan(
    tmp_path: Path,
    data_root: Path,
    candidate: Path,
):
    return build_research_universe_membership_apply_plan(
        data_root=data_root,
        candidate_membership_partition=candidate,
        created_at=CREATED_AT,
        plan_path=tmp_path / "research-membership-apply-plan.json",
        calendar=_Calendar(),
    )


def test_plan_and_apply_preserve_research_only_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, candidate = _fixture(tmp_path, monkeypatch)
    evidence = _plan(tmp_path, data_root, candidate)

    assert evidence.plan.custody.knowledge_time_status == "not_as_operated"
    assert evidence.plan.custody.permitted_uses == (
        RESEARCH_UNIVERSE_MEMBERSHIP_PERMITTED_USES
    )
    assert evidence.plan.custody.signal_authorized is False
    assert evidence.plan.custody.development_authorized is False
    assert evidence.plan.custody.performance_authorized is False
    assert evidence.plan.custody.production_authorized is False
    assert evidence.plan.overwritten_partition_count == 0
    assert evidence.plan.deleted_partition_count == 0

    result = apply_research_universe_membership_plan(
        plan_path=evidence.plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
        data_root=data_root,
    )
    assert result.status == "applied"
    assert result.published_file_count == 3
    assert result.formal_reread_record_count == 1
    assert not (data_root / "market-data/universe-membership").exists()

    reread = read_canonical_research_universe_membership(
        data_root=data_root,
        methodology_version="fixture-v1",
        session_date=SESSION,
        expected_custody_fingerprint=evidence.plan.custody.logical_fingerprint,
    )
    assert reread.records[0].instrument_id == UUID(
        "11111111-1111-4111-8111-111111111111"
    )


def test_apply_is_idempotent_only_for_exact_completed_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, candidate = _fixture(tmp_path, monkeypatch)
    evidence = _plan(tmp_path, data_root, candidate)
    kwargs = {
        "plan_path": evidence.plan_path,
        "approved_plan_sha256": evidence.plan_sha256,
        "expected_plan_logical_fingerprint": evidence.plan.logical_fingerprint,
        "data_root": data_root,
    }
    apply_research_universe_membership_plan(**kwargs)
    repeated = apply_research_universe_membership_plan(**kwargs)

    assert repeated.status == "already_present"
    assert repeated.membership_partition_reused is True
    assert repeated.published_file_count == 0
    assert repeated.published_bytes == 0


def test_plan_rejects_as_operated_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, candidate = _fixture(
        tmp_path,
        monkeypatch,
        origin=UniverseMembershipOrigin.AS_OPERATED,
    )
    with pytest.raises(
        ResearchUniverseMembershipApplyPlanError,
        match="reconstructed origin",
    ):
        _plan(tmp_path, data_root, candidate)


def test_plan_reread_rejects_candidate_byte_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, candidate = _fixture(tmp_path, monkeypatch)
    evidence = _plan(tmp_path, data_root, candidate)
    parquet = candidate / "part-00000.parquet"
    parquet.chmod(0o600)
    with parquet.open("ab") as handle:
        handle.write(b"drift")

    with pytest.raises(
        ResearchUniverseMembershipApplyPlanError,
        match="candidate bytes changed",
    ):
        read_research_universe_membership_apply_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
        )


def test_archive_inspects_then_executes_without_signal_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, candidate = _fixture(tmp_path, monkeypatch)
    candidate_root = candidate.parents[4]
    workspace = tmp_path / "workspace"

    preview = archive_research_universe_membership_candidates(
        data_root=data_root,
        candidate_root=candidate_root,
        workspace_root=workspace,
        created_at=CREATED_AT,
        execute=False,
    )
    assert preview.status == "inspection_complete"
    assert preview.planned_only_session_count == 1
    assert not (data_root / "market-data").exists()

    completed = archive_research_universe_membership_candidates(
        data_root=data_root,
        candidate_root=candidate_root,
        workspace_root=workspace,
        created_at=CREATED_AT,
        execute=True,
    )
    assert completed.status == "completed"
    assert completed.applied_session_count == 1
    assert completed.failed_session_count == 0
    assert completed.performance_authorized is False
    assert completed.production_authorized is False
    assert not (data_root / "market-data/universe-membership").exists()
