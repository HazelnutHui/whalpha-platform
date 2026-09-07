from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
    build_universe_membership_knowledge_time_assessment,
)
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.services import universe_membership_apply_plan as plan_service
from tip_api.services.universe_membership_apply_plan import (
    UniverseMembershipApplyPlanError,
    build_universe_membership_apply_plan,
    read_universe_membership_apply_plan,
)
from tip_api.services.universe_membership_reconstruction import (
    stable_instrument_set_fingerprint,
)


SESSION = date(2026, 9, 4)
SOURCE_CUTOFF = datetime(2026, 9, 6, 11, tzinfo=UTC)
EVALUATED = datetime(2026, 9, 6, 13, tzinfo=UTC)
ASSESSED = datetime(2026, 9, 6, 14, tzinfo=UTC)
CREATED = datetime(2026, 9, 6, 14, 5, tzinfo=UTC)
SOURCE_FINGERPRINT = "c" * 64


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_root = tmp_path / "canonical"
    data_root.mkdir()
    candidate_root = tmp_path / "membership"
    candidate_root.mkdir(mode=0o700)
    candidate_root.chmod(0o700)
    instrument_id = UUID("11111111-1111-4111-8111-111111111111")
    record = UniverseMembershipDecisionV1(
        universe_id="primary",
        instrument_id=instrument_id,
        session_date=SESSION,
        methodology_version="fixture-v1",
        origin=UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME,
        disposition=UniverseMembershipDisposition.INCLUDED,
        is_member=True,
        reason_codes=("included",),
        evaluated_base_fingerprint=stable_instrument_set_fingerprint(
            frozenset({instrument_id})
        ),
        source_fingerprints=(SOURCE_FINGERPRINT,),
        source_data_cutoff=SOURCE_CUTOFF,
        evaluated_at=EVALUATED,
        quality_status=QualityStatus.VALID,
    )
    published = ParquetHistoricalResearchRepository(
        candidate_root,
        created_at=EVALUATED,
    ).publish_universe_membership(
        (record,),
        methodology_version=record.methodology_version,
        session_date=SESSION,
    )
    manifest_path = published.partition_path / "manifest.json"
    parquet_path = published.partition_path / "part-00000.parquet"
    manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
        manifest_path.read_bytes()
    )
    assessment = build_universe_membership_knowledge_time_assessment(
        membership_logical_fingerprint=manifest.logical_fingerprint,
        membership_manifest_sha256=_sha(manifest_path),
        membership_parquet_sha256=_sha(parquet_path),
        identity_source_logical_fingerprint=SOURCE_FINGERPRINT,
        identity_source_contract_version=(
            "historical-identity-source-custody/1.1"
        ),
        identity_source_point_in_time_eligibility=(
            "eligible_at_source_observed_at"
        ),
        methodology_version=manifest.methodology_version,
        session_date=SESSION,
        market_information_cutoff_at=datetime(2026, 9, 4, 20, tzinfo=UTC),
        source_data_cutoff=SOURCE_CUTOFF,
        evaluated_at=EVALUATED,
        entry_session_date=date(2026, 9, 8),
        next_session_open_at=datetime(2026, 9, 8, 13, 30, tzinfo=UTC),
        assessed_at=ASSESSED,
        calendar_id="XNYS",
        calendar_version="fixture-1",
        point_in_time_eligibility=PointInTimeEligibility.SIGNAL_ELIGIBLE,
        reason_codes=(
            "source_and_evaluation_completed_before_next_session_open",
        ),
    )
    monkeypatch.setattr(plan_service, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(
        plan_service,
        "assess_universe_membership_knowledge_time",
        lambda **_: assessment,
    )
    return data_root, candidate_root, published.partition_path, assessment


def test_plan_binds_candidate_timing_targets_and_inventory_without_data_write(
    tmp_path,
    monkeypatch,
) -> None:
    data_root, candidate_root, partition, assessment = _fixture(
        tmp_path,
        monkeypatch,
    )
    before = tuple(data_root.rglob("*"))
    plan_path = tmp_path / "membership-apply-plan.json"

    evidence = build_universe_membership_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        candidate_membership_partition=partition,
        assessed_at=ASSESSED,
        created_at=CREATED,
        plan_path=plan_path,
        inventory_reader=lambda _: "a" * 64,
    )

    assert evidence.plan.status == "ready_for_separate_review"
    assert evidence.plan.publication.knowledge_time_assessment == assessment
    assert evidence.plan.inventory_change_file_count == 3
    assert evidence.plan.target_absent_partition_count == 2
    assert evidence.plan.expected_current_state_fingerprint == "a" * 64
    assert evidence.plan.canonical_data_write_count == 0
    assert evidence.plan.apply_authorized is False
    assert plan_path.stat().st_mode & 0o777 == 0o600
    assert tuple(data_root.rglob("*")) == before

    reread = read_universe_membership_apply_plan(
        plan_path=plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        inventory_reader=lambda _: "a" * 64,
    )
    assert reread == evidence


def test_plan_rejects_outcome_only_assessment(tmp_path, monkeypatch) -> None:
    data_root, candidate_root, partition, assessment = _fixture(
        tmp_path,
        monkeypatch,
    )
    outcome_only = assessment.model_copy(
        update={
            "identity_source_contract_version": (
                "historical-identity-source-custody/1.0"
            ),
            "identity_source_point_in_time_eligibility": (
                "outcome_reconciliation_only"
            ),
            "point_in_time_eligibility": (
                PointInTimeEligibility.OUTCOME_RECONCILIATION_ONLY
            ),
            "reason_codes": ("identity_source_outcome_reconciliation_only",),
        }
    )
    monkeypatch.setattr(
        plan_service,
        "assess_universe_membership_knowledge_time",
        lambda **_: outcome_only,
    )

    with pytest.raises(
        UniverseMembershipApplyPlanError,
        match="only signal-eligible",
    ):
        build_universe_membership_apply_plan(
            data_root=data_root,
            candidate_root=candidate_root,
            candidate_membership_partition=partition,
            assessed_at=ASSESSED,
            created_at=CREATED,
            plan_path=tmp_path / "blocked-plan.json",
            inventory_reader=lambda _: "a" * 64,
        )


def test_plan_rejects_existing_membership_target(tmp_path, monkeypatch) -> None:
    data_root, candidate_root, partition, _ = _fixture(tmp_path, monkeypatch)
    target = (
        data_root
        / "market-data"
        / "universe-membership"
        / "schema_version=1"
        / "methodology_version=fixture-v1"
        / f"session_date={SESSION.isoformat()}"
    )
    target.mkdir(parents=True)

    with pytest.raises(UniverseMembershipApplyPlanError, match="no longer absent"):
        build_universe_membership_apply_plan(
            data_root=data_root,
            candidate_root=candidate_root,
            candidate_membership_partition=partition,
            assessed_at=ASSESSED,
            created_at=CREATED,
            plan_path=tmp_path / "blocked-target-plan.json",
            inventory_reader=lambda _: "a" * 64,
        )


def test_plan_reread_rejects_inventory_drift(tmp_path, monkeypatch) -> None:
    data_root, candidate_root, partition, _ = _fixture(tmp_path, monkeypatch)
    plan_path = tmp_path / "membership-apply-plan.json"
    evidence = build_universe_membership_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        candidate_membership_partition=partition,
        assessed_at=ASSESSED,
        created_at=CREATED,
        plan_path=plan_path,
        inventory_reader=lambda _: "a" * 64,
    )

    with pytest.raises(UniverseMembershipApplyPlanError, match="inventory changed"):
        read_universe_membership_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            inventory_reader=lambda _: "b" * 64,
        )


def test_plan_reread_rejects_candidate_byte_drift(tmp_path, monkeypatch) -> None:
    data_root, candidate_root, partition, _ = _fixture(tmp_path, monkeypatch)
    plan_path = tmp_path / "membership-apply-plan.json"
    evidence = build_universe_membership_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        candidate_membership_partition=partition,
        assessed_at=ASSESSED,
        created_at=CREATED,
        plan_path=plan_path,
        inventory_reader=lambda _: "a" * 64,
    )
    manifest_path = partition / "manifest.json"
    manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")

    with pytest.raises(
        UniverseMembershipApplyPlanError,
        match="candidate bytes changed",
    ):
        read_universe_membership_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            inventory_reader=lambda _: "a" * 64,
        )
