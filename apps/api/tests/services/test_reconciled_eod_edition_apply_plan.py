from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import EodPriceBarV1, QualityStatus
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    ReconciledEodSourceProvenance,
    reconciled_eod_fingerprint,
)
from tip_api.persistence.parquet import reconciled_eod_edition as persistence
from tip_api.persistence.parquet.manifest import content_fingerprint
from tip_api.persistence.parquet.reconciled_eod_edition import (
    ParquetReconciledEodEditionCandidateRepository,
)
from tip_api.services import reconciled_eod_edition_apply_plan as service
from tip_api.services import reconciled_eod_edition_apply as apply_service
from tip_api.services.reconciled_eod_edition import (
    ReconciledEodSessionCandidate,
    compare_reconciled_eod_records,
)


SESSION = date(2022, 10, 7)
NOW = datetime(2026, 9, 11, tzinfo=UTC)
REVISION = "a" * 40
EDITION_ID = "massive-exact-symbol-v1"
ID1 = UUID("00000000-0000-0000-0000-000000000001")
ID2 = UUID("00000000-0000-0000-0000-000000000002")


def _bar(instrument_id: UUID) -> EodPriceBarV1:
    return EodPriceBarV1(
        instrument_id=instrument_id,
        session_date=SESSION,
        open=Decimal("10"),
        high=Decimal("12"),
        low=Decimal("9"),
        close=Decimal("11"),
        volume=Decimal("1000"),
        vwap=Decimal("10.5"),
        trade_count=25,
        notional=Decimal("11000"),
        currency="USD",
        split_adjustment_factor=Decimal("1"),
        dividend_adjustment_factor=Decimal("1"),
        total_return_adjustment_factor=Decimal("1"),
        adjusted_close=Decimal("11"),
        source="massive_stocks_basic",
        ingested_at=NOW,
        revision=1,
        is_latest_revision=True,
        quality_status=QualityStatus.VALID,
    )


def _candidate() -> ReconciledEodSessionCandidate:
    base = (_bar(ID1),)
    rebuilt = (_bar(ID1), _bar(ID2))
    return ReconciledEodSessionCandidate(
        session_date=SESSION,
        rebuilt_records=rebuilt,
        diff=compare_reconciled_eod_records(
            base_records=base,
            rebuilt_records=rebuilt,
            expected_added_instrument_ids=frozenset({ID2}),
            source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        ),
        source_provenance=ReconciledEodSourceProvenance.RETAINED_ORIGINAL,
        source_observed_at=NOW,
        source_package_manifest_sha256="1" * 64,
        source_package_content_sha256="2" * 64,
        identity_snapshot_fingerprint="3" * 64,
        identity_source_fingerprint="4" * 64,
        base_eod_fingerprint=content_fingerprint(base),
        rebuilt_eod_fingerprint=content_fingerprint(rebuilt),
        quality_summary_fingerprint=reconciled_eod_fingerprint(("valid",)),
        quality_warnings=("case_sensitive_provider_tickers_present",),
    )


def _arrange(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o755)
    candidate_root = tmp_path / "candidate"
    repository = ParquetReconciledEodEditionCandidateRepository(
        root=candidate_root,
        edition_id=EDITION_ID,
        implementation_revision=REVISION,
        created_at=NOW,
    )
    repository.publish_session(_candidate())
    repository.publish_interval_manifest(
        session_dates=(SESSION,),
        evaluation_first_session=SESSION,
        evaluation_last_session=SESSION,
    )
    monkeypatch.setattr(service, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(persistence, "APPROVED_DATA_ROOT", data_root)
    return data_root, candidate_root, candidate_root / service.PLAN_FILE_NAME


def test_builds_and_formally_rereads_exact_whole_edition_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, candidate_root, plan_path = _arrange(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )

    evidence = service.build_reconciled_eod_edition_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        plan_path=plan_path,
        edition_id=EDITION_ID,
        planner_revision="b" * 40,
        created_at=NOW,
        inventory_reader=lambda _root: "c" * 64,
    )

    assert evidence.plan.candidate_session_count == 1
    assert evidence.plan.candidate_record_count == 2
    assert evidence.plan.inventory_change_file_count == 3
    assert evidence.plan.artifacts[-1].relative_path == "interval-manifest.json"
    assert plan_path.stat().st_mode & 0o777 == 0o400
    assert evidence.plan.apply_authorized is False
    assert evidence.plan.production_authority is False

    reread = service.read_reconciled_eod_edition_apply_plan(
        plan_path=plan_path,
        approved_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
    )
    assert reread.plan == evidence.plan


def test_plan_reread_rejects_byte_and_candidate_tampering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, candidate_root, plan_path = _arrange(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    evidence = service.build_reconciled_eod_edition_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        plan_path=plan_path,
        edition_id=EDITION_ID,
        planner_revision="b" * 40,
        created_at=NOW,
        inventory_reader=lambda _root: "c" * 64,
    )

    with pytest.raises(service.ReconciledEodEditionApplyPlanError, match="bytes"):
        service.read_reconciled_eod_edition_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256="0" * 64,
        )

    source = (
        evidence.candidate.edition_path
        / evidence.plan.artifacts[0].relative_path
    )
    source.chmod(0o600)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["quality_warnings"] = []
    source.write_text(json.dumps(payload), encoding="utf-8")
    source.chmod(0o600)
    with pytest.raises(
        service.ReconciledEodEditionApplyPlanError,
        match="formal reread",
    ):
        service.read_reconciled_eod_edition_apply_plan(
            plan_path=plan_path,
            approved_plan_sha256=evidence.plan_sha256,
        )


def test_plan_rejects_existing_target_and_non_owner_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, candidate_root, plan_path = _arrange(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    target = service._edition_path(data_root, edition_id=EDITION_ID)
    target.mkdir(parents=True)
    with pytest.raises(
        service.ReconciledEodEditionApplyPlanError,
        match="already exists",
    ):
        service.build_reconciled_eod_edition_apply_plan(
            data_root=data_root,
            candidate_root=candidate_root,
            plan_path=plan_path,
            edition_id=EDITION_ID,
            planner_revision="b" * 40,
            created_at=NOW,
            inventory_reader=lambda _root: "c" * 64,
        )

    target.rmdir()
    candidate_root.chmod(0o755)
    with pytest.raises(
        service.ReconciledEodEditionApplyPlanError,
        match="owner-only",
    ):
        service.build_reconciled_eod_edition_apply_plan(
            data_root=data_root,
            candidate_root=candidate_root,
            plan_path=plan_path,
            edition_id=EDITION_ID,
            planner_revision="b" * 40,
            created_at=NOW,
            inventory_reader=lambda _root: "c" * 64,
        )


def _build_plan(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    data_root, candidate_root, plan_path = _arrange(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    monkeypatch.setattr(apply_service, "APPROVED_DATA_ROOT", data_root)
    evidence = service.build_reconciled_eod_edition_apply_plan(
        data_root=data_root,
        candidate_root=candidate_root,
        plan_path=plan_path,
        edition_id=EDITION_ID,
        planner_revision="b" * 40,
        created_at=NOW,
        inventory_reader=lambda _root: "c" * 64,
    )
    return data_root, evidence


def test_apply_publishes_one_atomic_edition_and_formally_rereads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, evidence = _build_plan(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    observed_inventory_calls: list[tuple[Path, ...]] = []

    def outside(_root: Path, exclusions: tuple[Path, ...]) -> str:
        observed_inventory_calls.append(exclusions)
        return "c" * 64

    result = apply_service.apply_approved_reconciled_eod_edition_plan(
        plan_path=evidence.plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
        expected_current_state_fingerprint=(
            evidence.plan.expected_current_state_fingerprint
        ),
        data_root=data_root,
        outside_inventory_reader=outside,
    )

    target = Path(evidence.plan.target_edition_path)
    assert result.status == "applied"
    assert result.edition_published is True
    assert result.published_file_count == 3
    assert result.formal_reread_session_count == 1
    assert result.formal_reread_record_count == 2
    assert len(observed_inventory_calls) == 2
    assert target.is_dir()
    assert target.stat().st_mode & 0o777 == 0o755
    assert all(
        path.stat().st_mode & 0o777 == 0o644
        for path in target.rglob("*")
        if path.is_file()
    )

    repeated = apply_service.apply_approved_reconciled_eod_edition_plan(
        plan_path=evidence.plan_path,
        approved_plan_sha256=evidence.plan_sha256,
        expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
        expected_current_state_fingerprint=(
            evidence.plan.expected_current_state_fingerprint
        ),
        data_root=data_root,
        verify_then_complete=True,
        outside_inventory_reader=lambda _root, _exclusions: "c" * 64,
    )
    assert repeated.status == "verified_then_completed"
    assert repeated.edition_reused is True
    assert repeated.published_file_count == 0


def test_apply_rejects_inventory_drift_without_writing_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, evidence = _build_plan(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )

    with pytest.raises(
        apply_service.ReconciledEodEditionApplyError,
        match="changed after",
    ):
        apply_service.apply_approved_reconciled_eod_edition_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
            expected_current_state_fingerprint=(
                evidence.plan.expected_current_state_fingerprint
            ),
            data_root=data_root,
            outside_inventory_reader=lambda _root, _exclusions: "d" * 64,
        )

    assert not Path(evidence.plan.target_edition_path).exists()


def test_apply_rejects_preexisting_staging_without_removing_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, evidence = _build_plan(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    target = Path(evidence.plan.target_edition_path)
    target.parent.mkdir(parents=True)
    staging = apply_service._staging_path(
        target,
        evidence.plan.logical_fingerprint,
    )
    staging.mkdir()

    with pytest.raises(
        apply_service.ReconciledEodEditionApplyError,
        match="target or staging",
    ):
        apply_service.apply_approved_reconciled_eod_edition_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
            expected_current_state_fingerprint=(
                evidence.plan.expected_current_state_fingerprint
            ),
            data_root=data_root,
            outside_inventory_reader=lambda _root, _exclusions: "c" * 64,
        )

    assert staging.is_dir()
    assert not target.exists()


def test_apply_removes_only_its_owned_staging_after_copy_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_root, evidence = _build_plan(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
    )
    target = Path(evidence.plan.target_edition_path)
    staging = apply_service._staging_path(
        target,
        evidence.plan.logical_fingerprint,
    )

    def fail_copy(**_values) -> None:
        raise apply_service.ReconciledEodEditionApplyError("injected copy failure")

    monkeypatch.setattr(apply_service, "_copy_verified_artifact", fail_copy)
    with pytest.raises(
        apply_service.ReconciledEodEditionApplyError,
        match="injected copy failure",
    ):
        apply_service.apply_approved_reconciled_eod_edition_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
            expected_current_state_fingerprint=(
                evidence.plan.expected_current_state_fingerprint
            ),
            data_root=data_root,
            outside_inventory_reader=lambda _root, _exclusions: "c" * 64,
        )

    assert not staging.exists()
    assert not target.exists()
