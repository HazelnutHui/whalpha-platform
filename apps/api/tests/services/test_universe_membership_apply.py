from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
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
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services import universe_membership_apply as apply_service
from tip_api.services import universe_membership_apply_plan as plan_service
from tip_api.services import universe_membership_canonical as canonical_service
from tip_api.services.universe_membership_reconstruction import (
    stable_instrument_set_fingerprint,
)


SESSION = date(2026, 9, 4)
ASSESSED = datetime(2026, 9, 6, 14, tzinfo=UTC)
CREATED = datetime(2026, 9, 6, 14, 5, tzinfo=UTC)
SOURCE_CUTOFF = datetime(2026, 9, 6, 11, tzinfo=UTC)
EVALUATED = datetime(2026, 9, 6, 13, tzinfo=UTC)
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
        identity_source_contract_version="historical-identity-source-custody/1.1",
        identity_source_point_in_time_eligibility="eligible_at_source_observed_at",
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
    monkeypatch.setattr(apply_service, "APPROVED_DATA_ROOT", data_root.resolve())
    monkeypatch.setattr(
        canonical_service,
        "APPROVED_DATA_ROOT",
        data_root.resolve(),
    )
    monkeypatch.setattr(
        plan_service,
        "assess_universe_membership_knowledge_time",
        lambda **_: assessment,
    )
    source = SimpleNamespace(
        manifest=SimpleNamespace(
            as_of_date=SESSION,
            logical_fingerprint=SOURCE_FINGERPRINT,
            contract_version="historical-identity-source-custody/1.1",
            point_in_time_eligibility="eligible_at_source_observed_at",
            source_package_fetched_at=SOURCE_CUTOFF,
        )
    )
    monkeypatch.setattr(
        canonical_service,
        "read_historical_identity_source_custody",
        lambda **_: source,
    )
    plan_path = tmp_path / "membership-apply-plan.json"
    evidence = plan_service.build_universe_membership_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        candidate_membership_partition=published.partition_path,
        assessed_at=ASSESSED,
        created_at=CREATED,
        plan_path=plan_path,
    )
    return data_root, plan_path, evidence


def _apply(data_root: Path, plan_path: Path, evidence, **kwargs):
    return apply_service.apply_approved_universe_membership_plan(
        plan_path=plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
        expected_current_state_fingerprint=(
            evidence.plan.expected_current_state_fingerprint
        ),
        data_root=data_root,
        **kwargs,
    )


def test_apply_publishes_physical_first_marker_last_and_formally_rereads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    publish_marker = apply_service._publish_publication_marker

    def marker_last(**kwargs) -> None:
        assert Path(evidence.plan.target_membership_partition).is_dir()
        assert not Path(evidence.plan.target_publication_partition).exists()
        publish_marker(**kwargs)

    monkeypatch.setattr(
        apply_service,
        "_publish_publication_marker",
        marker_last,
    )
    result = _apply(data_root, plan_path, evidence)

    assert result.status == "applied"
    assert result.membership_partition_published is True
    assert result.publication_marker_published is True
    assert result.membership_partition_reused is False
    assert result.publication_marker_reused is False
    assert result.published_file_count == 3
    assert result.published_bytes == evidence.plan.inventory_change_bytes
    assert result.formal_reread_record_count == 1
    assert result.overwritten_partition_count == 0
    assert result.deleted_partition_count == 0
    assert result.external_request_count == 0
    assert result.post_state_fingerprint == inventory_fingerprint(data_root)


def test_physical_only_state_is_not_canonical_and_can_be_completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    publish_physical = apply_service._publish_membership_partition

    def interrupt_after_physical(**kwargs) -> None:
        publish_physical(**kwargs)
        raise apply_service.UniverseMembershipApplyError("injected interruption")

    with monkeypatch.context() as fault:
        fault.setattr(
            apply_service,
            "_publish_membership_partition",
            interrupt_after_physical,
        )
        with pytest.raises(
            apply_service.UniverseMembershipApplyError,
            match="injected interruption",
        ):
            _apply(data_root, plan_path, evidence)

    assert Path(evidence.plan.target_membership_partition).is_dir()
    assert not Path(evidence.plan.target_publication_partition).exists()
    with pytest.raises(
        canonical_service.CanonicalUniverseMembershipError,
        match="partition is missing",
    ):
        canonical_service.read_canonical_universe_membership(
            data_root=data_root,
            methodology_version="fixture-v1",
            session_date=SESSION,
        )

    recovered = _apply(
        data_root,
        plan_path,
        evidence,
        verify_then_complete=True,
    )
    assert recovered.status == "verified_then_completed"
    assert recovered.membership_partition_reused is True
    assert recovered.publication_marker_published is True
    assert recovered.published_file_count == 1
    assert recovered.published_bytes == evidence.plan.publication_manifest_bytes


def test_completed_apply_can_be_proven_without_rewriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    _apply(data_root, plan_path, evidence)

    recovered = _apply(
        data_root,
        plan_path,
        evidence,
        verify_then_complete=True,
    )
    assert recovered.membership_partition_reused is True
    assert recovered.publication_marker_reused is True
    assert recovered.membership_partition_published is False
    assert recovered.publication_marker_published is False
    assert recovered.published_file_count == 0
    assert recovered.published_bytes == 0


def test_recovery_without_any_completed_target_refuses_to_start_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)

    with pytest.raises(
        apply_service.UniverseMembershipApplyError,
        match="found no completed target",
    ):
        _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )
    assert not Path(evidence.plan.target_membership_partition).exists()
    assert not Path(evidence.plan.target_publication_partition).exists()


def test_apply_rejects_unrelated_inventory_drift_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    (data_root / "unrelated.txt").write_text("changed", encoding="utf-8")

    with pytest.raises(
        apply_service.UniverseMembershipApplyError,
        match="failed formal reread",
    ):
        _apply(data_root, plan_path, evidence)
    assert not Path(evidence.plan.target_membership_partition).exists()
    assert not Path(evidence.plan.target_publication_partition).exists()


def test_recovery_blocks_corrupt_physical_target_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    publish_physical = apply_service._publish_membership_partition

    def interrupt_after_physical(**kwargs) -> None:
        publish_physical(**kwargs)
        raise apply_service.UniverseMembershipApplyError("injected interruption")

    with monkeypatch.context() as fault:
        fault.setattr(
            apply_service,
            "_publish_membership_partition",
            interrupt_after_physical,
        )
        with pytest.raises(apply_service.UniverseMembershipApplyError):
            _apply(data_root, plan_path, evidence)
    manifest = Path(evidence.plan.target_membership_partition) / "manifest.json"
    manifest.write_bytes(manifest.read_bytes() + b"\n")

    with pytest.raises(
        apply_service.UniverseMembershipApplyError,
        match="physical artifact differs",
    ):
        _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )
    assert manifest.read_bytes().endswith(b"\n\n")
    assert not Path(evidence.plan.target_publication_partition).exists()


def test_recovery_blocks_owned_staging_residue_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    target = Path(evidence.plan.target_membership_partition)
    staging = target.parent / (
        f".{target.name}.staging.{evidence.plan.logical_fingerprint[:16]}"
    )
    staging.mkdir(parents=True, mode=0o755)

    with pytest.raises(
        apply_service.UniverseMembershipApplyError,
        match="staging path already exists",
    ):
        _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )
    assert staging.is_dir()


def test_recovery_rejects_marker_without_physical_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    marker = Path(evidence.plan.target_publication_partition)
    marker.mkdir(parents=True, mode=0o755)

    with pytest.raises(
        apply_service.UniverseMembershipApplyError,
        match="failed formal reread",
    ):
        _apply(
            data_root,
            plan_path,
            evidence,
            verify_then_complete=True,
        )
    assert marker.is_dir()
    assert not Path(evidence.plan.target_membership_partition).exists()


def test_canonical_reader_rejects_identity_source_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, plan_path, evidence = _fixture(tmp_path, monkeypatch)
    _apply(data_root, plan_path, evidence)
    monkeypatch.setattr(
        canonical_service,
        "read_historical_identity_source_custody",
        lambda **_: SimpleNamespace(
            manifest=SimpleNamespace(
                as_of_date=SESSION,
                logical_fingerprint="d" * 64,
                contract_version="historical-identity-source-custody/1.1",
                point_in_time_eligibility="eligible_at_source_observed_at",
                source_package_fetched_at=SOURCE_CUTOFF,
            )
        ),
    )

    with pytest.raises(
        canonical_service.CanonicalUniverseMembershipError,
        match="Identity source binding differs",
    ):
        canonical_service.read_canonical_universe_membership(
            data_root=data_root,
            methodology_version="fixture-v1",
            session_date=SESSION,
        )
