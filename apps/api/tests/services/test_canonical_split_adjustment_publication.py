from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
)
from tip_api.persistence.parquet import canonical_split_adjustment as persistence
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_candidate,
    write_canonical_split_adjustment_candidate,
)
from tip_api.services import (
    canonical_split_adjustment_publication_apply as apply_module,
)
from tip_api.services import (
    canonical_split_adjustment_publication_plan as plan_module,
)
from tip_api.services.canonical_split_adjustment_publication_apply import (
    CanonicalSplitAdjustmentPublicationApplyError,
    apply_approved_canonical_split_adjustment_publication_plan,
)
from tip_api.services.canonical_split_adjustment_publication_plan import (
    CanonicalSplitAdjustmentPublicationPlanError,
    build_canonical_split_adjustment_publication_plan,
    read_canonical_split_adjustment_publication_plan,
)


FIRST = date(2026, 8, 20)
BASIS = date(2026, 8, 22)
SOURCE_AT = datetime(2026, 9, 2, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 3, tzinfo=UTC)
PLANNED_AT = datetime(2026, 9, 4, tzinfo=UTC)
AAA = UUID("11111111-1111-4111-8111-111111111111")
BBB = UUID("22222222-2222-4222-8222-222222222222")


def _inventory(root: Path, *, exclude_prefixes: tuple[Path, ...] = ()) -> str:
    excluded = tuple(path.relative_to(root) for path in exclude_prefixes)
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(relative == item or item in relative.parents for item in excluded):
            continue
        if path.is_file():
            rows.append(
                {
                    "path": relative.as_posix(),
                    "mode": path.stat().st_mode & 0o777,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _record(
    instrument_id: UUID,
    *,
    status: AdjustmentAvailabilityStatus,
) -> AdjustmentLedgerEntryV1:
    clear = status is AdjustmentAvailabilityStatus.CLEAR
    return AdjustmentLedgerEntryV1(
        instrument_id=instrument_id,
        source_session=FIRST,
        basis_session=BASIS,
        split_price_multiplier_to_basis=Decimal("0.5") if clear else None,
        split_volume_multiplier_to_basis=Decimal("2") if clear else None,
        split_adjustment_status=status,
        total_return_multiplier_to_basis=None,
        total_return_adjustment_status=AdjustmentAvailabilityStatus.UNAVAILABLE,
        source_action_set_fingerprint=("a" if clear else "b") * 64,
        calculation_methodology_version="canonical-split-ratio-to-basis-v1",
        source_data_cutoff=SOURCE_AT,
        calculated_at=CALCULATED_AT,
        revision=1,
        quality_status=QualityStatus.PENDING_REVIEW,
        quality_flags=(
            "absent_row_neutrality_unauthorized",
            "bounded_query_snapshot_only",
            "outcome_reconciliation_only",
            "sparse_affected_path_only",
            "total_return_adjustment_unavailable",
            *(() if clear else ("canonical_action_quarantined",)),
            *(("split_ratio_projection_clear",) if clear else ()),
        ),
    )


def _inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "data"
    root.mkdir(mode=0o755)
    candidate_root = tmp_path / "candidate"
    records = (
        _record(AAA, status=AdjustmentAvailabilityStatus.CLEAR),
        _record(BBB, status=AdjustmentAvailabilityStatus.QUARANTINED),
    )
    publication = write_canonical_split_adjustment_candidate(
        output_root=candidate_root,
        records=records,
        publication_values={
            "source_revision": "8" * 40,
            "basis_session": BASIS,
            "first_source_session": FIRST,
            "last_source_session": BASIS,
            "source_session_count": 3,
            "source_eod_record_count": 10,
            "canonical_action_publication_path": (
                "market-data/canonical-corporate-actions/manifest.json"
            ),
            "canonical_action_publication_sha256": "c" * 64,
            "canonical_action_publication_fingerprint": "d" * 64,
            "eod_evidence_path": "market-data/eod-evidence/manifest.json",
            "eod_evidence_sha256": "e" * 64,
            "eod_evidence_fingerprint": "f" * 64,
            "source_data_cutoff": SOURCE_AT,
            "calculated_at": CALCULATED_AT,
            "selected_instrument_count": 2,
            "selected_eod_row_count": 2,
            "selected_without_eod_count": 0,
            "record_count": 2,
            "clear_record_count": 1,
            "quarantined_record_count": 1,
            "clear_instrument_count": 1,
            "quarantined_instrument_count": 1,
            "active_action_record_count": 1,
            "quarantined_action_record_count": 1,
            "unresolved_source_action_count": 1,
            "possible_impact_instrument_count": 1,
        },
    )
    monkeypatch.setattr(plan_module, "APPROVED_DATA_ROOT", root)
    monkeypatch.setattr(persistence, "APPROVED_DATA_ROOT", root)
    monkeypatch.setattr(apply_module, "APPROVED_DATA_ROOT", root)
    def rebuild(**kwargs: object) -> SimpleNamespace:
        current = read_canonical_split_adjustment_candidate(
            output_root=Path(kwargs["output_root"])
        )
        return SimpleNamespace(status="already_present", publication=current)

    monkeypatch.setattr(
        plan_module,
        "build_canonical_split_adjustment_candidate",
        rebuild,
    )
    assert publication.root == candidate_root
    return {
        "data_root": root,
        "candidate_root": candidate_root,
        "plan_path": tmp_path / "plan.json",
        "planner_source_revision": "9" * 40,
        "created_at": PLANNED_AT,
        "inventory_reader": _inventory,
    }


def test_plan_binds_exact_candidate_and_false_authorities(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)

    evidence = build_canonical_split_adjustment_publication_plan(**inputs)  # type: ignore[arg-type]

    plan = evidence.plan
    assert plan.publication.record_count == 2
    assert plan.publication.clear_record_count == 1
    assert plan.publication.quarantined_record_count == 1
    assert plan.inventory_change_file_count == 2
    assert plan.apply_authorized is False
    assert plan.absent_row_neutrality_authorized is False
    assert plan.total_return_adjustment_authorized is False
    assert plan.full_adjustment_coverage_authorized is False
    assert plan.historical_coverage_authorized is False
    assert plan.research_performance_authorized is False


def test_apply_is_atomic_and_exact_rerun_verifies_existing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_adjustment_publication_plan(**inputs)  # type: ignore[arg-type]
    plan = evidence.plan
    values = {
        "plan_path": evidence.plan_path,
        "approved_plan_sha256": evidence.plan_sha256,
        "expected_plan_logical_fingerprint": plan.logical_fingerprint,
        "expected_current_state_fingerprint": (
            plan.expected_current_state_fingerprint
        ),
        "data_root": Path(plan.data_root),
        "inventory_reader": _inventory,
    }

    first = apply_approved_canonical_split_adjustment_publication_plan(**values)
    second = apply_approved_canonical_split_adjustment_publication_plan(**values)

    target = Path(plan.target_publication_root)
    assert first.status == "applied"
    assert first.published_file_count == 2
    assert second.status == "verified_existing"
    assert second.reused_file_count == 2
    assert target.stat().st_mode & 0o777 == 0o755
    assert {item.name for item in target.iterdir()} == {
        "part-00000.parquet",
        "manifest.json",
    }
    assert all(item.stat().st_mode & 0o777 == 0o644 for item in target.iterdir())


def test_inventory_change_after_plan_stops_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_adjustment_publication_plan(**inputs)  # type: ignore[arg-type]
    (Path(evidence.plan.data_root) / "unrelated.txt").write_text(
        "changed",
        encoding="utf-8",
    )

    with pytest.raises(
        CanonicalSplitAdjustmentPublicationApplyError,
        match="inventory changed",
    ):
        apply_approved_canonical_split_adjustment_publication_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
            expected_current_state_fingerprint=(
                evidence.plan.expected_current_state_fingerprint
            ),
            data_root=Path(evidence.plan.data_root),
            inventory_reader=_inventory,
        )


def test_interrupted_stage_leaves_no_target_or_staging(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_adjustment_publication_plan(**inputs)  # type: ignore[arg-type]

    def interrupted_copy(_source: Path, destination: Path) -> None:
        Path(destination).write_bytes(b"partial")
        raise OSError("injected interruption")

    monkeypatch.setattr(apply_module.shutil, "copyfile", interrupted_copy)
    with pytest.raises(
        CanonicalSplitAdjustmentPublicationApplyError,
        match="atomic publication failed",
    ):
        apply_approved_canonical_split_adjustment_publication_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
            expected_plan_logical_fingerprint=evidence.plan.logical_fingerprint,
            expected_current_state_fingerprint=(
                evidence.plan.expected_current_state_fingerprint
            ),
            data_root=Path(evidence.plan.data_root),
            inventory_reader=_inventory,
        )

    target = Path(evidence.plan.target_publication_root)
    staging = target.parent / (
        f".{target.name}.staging.{evidence.plan.logical_fingerprint[:16]}"
    )
    assert not target.exists()
    assert not staging.exists()


def test_candidate_tamper_stops_plan_reread(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_adjustment_publication_plan(**inputs)  # type: ignore[arg-type]
    manifest = Path(evidence.plan.candidate_root) / "manifest.json"
    manifest.chmod(0o600)
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    manifest.chmod(0o400)

    with pytest.raises(CanonicalSplitAdjustmentPublicationPlanError):
        read_canonical_split_adjustment_publication_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
        )


def test_exact_rederivation_uses_candidate_bound_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    root.mkdir()
    candidate_root = tmp_path / "candidate"
    current = SimpleNamespace(
        publication=SimpleNamespace(
            canonical_action_publication_path=(
                "market-data/canonical-actions/coverage_id=x/manifest.json"
            ),
            eod_evidence_path="market-data/eod-evidence/manifest.json",
            source_revision="8" * 40,
            calculated_at=CALCULATED_AT,
        )
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        plan_module,
        "read_canonical_split_adjustment_candidate",
        lambda **_kwargs: current,
    )

    def rebuild(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(status="already_present", publication=current)

    monkeypatch.setattr(
        plan_module,
        "build_canonical_split_adjustment_candidate",
        rebuild,
    )

    result = plan_module._read_and_rederive_candidate(root, candidate_root)

    assert result is current
    assert captured["data_root"] == root
    assert captured["canonical_action_publication_root"] == Path(
        "market-data/canonical-actions/coverage_id=x"
    )
    assert captured["eod_evidence_path"] == Path(
        "market-data/eod-evidence/manifest.json"
    )
    assert captured["source_revision"] == "8" * 40
    assert captured["calculated_at"] == CALCULATED_AT
