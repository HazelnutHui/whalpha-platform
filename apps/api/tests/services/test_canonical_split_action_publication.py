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
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    KnowledgeTimeStatus,
    ResolutionStatus,
)
from tip_api.persistence.parquet import canonical_corporate_action as persistence
from tip_api.services import canonical_split_action_candidate as candidate_module
from tip_api.services import canonical_split_action_publication_apply as apply_module
from tip_api.services import canonical_split_action_publication_plan as plan_module
from tip_api.services.canonical_split_action_candidate import (
    build_canonical_source_split_action_candidate,
)
from tip_api.services.canonical_split_action_publication_apply import (
    CanonicalSplitActionPublicationApplyError,
    apply_approved_canonical_split_action_publication_plan,
)
from tip_api.services.canonical_split_action_publication_plan import (
    CanonicalSplitActionPublicationPlanError,
    build_canonical_split_action_publication_plan,
    read_canonical_split_action_publication_plan,
)


START = date(2026, 8, 20)
BASIS = date(2026, 8, 22)
SOURCE_AT = datetime(2026, 9, 2, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 3, tzinfo=UTC)
PUBLISHED_AT = datetime(2026, 9, 4, tzinfo=UTC)
AAA_ID = UUID("11111111-1111-4111-8111-111111111111")
BBB_ID = UUID("22222222-2222-4222-8222-222222222222")


def _split(
    action_id: str,
    instrument_id: UUID,
    ticker: str,
    ratio_from: str,
    ratio_to: str,
) -> CorporateActionSourceObservationV1:
    return CorporateActionSourceObservationV1(
        provider="massive_stocks_basic",
        source_action_id=action_id,
        source_revision=1,
        record_status=CorporateActionRecordStatus.ACTIVE,
        action_type=CorporateActionType.STOCK_SPLIT,
        provider_ticker=ticker,
        instrument_resolution_status=ResolutionStatus.RESOLVED,
        instrument_id=instrument_id,
        effective_date=BASIS,
        split_ratio_from=Decimal(ratio_from),
        split_ratio_to=Decimal(ratio_to),
        knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
        first_observed_at=datetime(2026, 9, 1, tzinfo=UTC),
        ingested_at=SOURCE_AT,
        quality_status=QualityStatus.VALID,
        quality_flags=("source_available_time_unavailable",),
    )


def _unresolved_split() -> CorporateActionSourceObservationV1:
    return CorporateActionSourceObservationV1(
        provider="massive_stocks_basic",
        source_action_id="unresolved",
        source_revision=1,
        record_status=CorporateActionRecordStatus.QUARANTINED,
        action_type=CorporateActionType.STOCK_SPLIT,
        provider_ticker="OLD",
        instrument_resolution_status=ResolutionStatus.UNRESOLVED,
        instrument_id=None,
        effective_date=BASIS,
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal("2"),
        knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
        first_observed_at=datetime(2026, 9, 1, tzinfo=UTC),
        ingested_at=SOURCE_AT,
        quality_status=QualityStatus.PENDING_REVIEW,
        quality_flags=(
            "source_available_time_unavailable",
            "unresolved_ticker",
        ),
    )


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


def _inputs(monkeypatch, tmp_path: Path) -> dict[str, object]:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o755)
    source_path = data_root / "market-data" / "source" / "manifest.json"
    source_path.parent.mkdir(parents=True)
    records = (
        _split("clear", AAA_ID, "AAA", "1", "2"),
        _split("reciprocal-a", BBB_ID, "BBB", "3000", "1"),
        _split("reciprocal-b", BBB_ID, "BBB", "1", "3000"),
        _unresolved_split(),
    )
    publication = SimpleNamespace(
        start_date=START,
        end_date=BASIS,
        created_at=SOURCE_AT,
        logical_fingerprint="a" * 64,
        identity_evidence_path="market-data/identity/manifest.json",
        identity_evidence_sha256="b" * 64,
        identity_evidence_logical_fingerprint="c" * 64,
        identity_session_count=3,
    )
    source = SimpleNamespace(
        publication=publication,
        publication_path=source_path,
        publication_sha256="d" * 64,
        records=records,
    )
    monkeypatch.setattr(candidate_module, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(
        candidate_module,
        "read_canonical_corporate_action_source",
        lambda **_kwargs: source,
    )
    monkeypatch.setattr(
        candidate_module,
        "read_historical_ticker_candidates_bound_to_identity_evidence",
        lambda **_kwargs: {"OLD": frozenset({AAA_ID})},
    )
    split_candidate = build_canonical_source_split_action_candidate(
        data_root=data_root,
        source_publication_path=source_path,
        output_root=tmp_path / "split-candidate",
        basis_session=BASIS,
        calculated_at=CALCULATED_AT,
        implementation_revision="e" * 40,
    )
    monkeypatch.setattr(plan_module, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(persistence, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(apply_module, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(
        plan_module,
        "read_canonical_corporate_action_source",
        lambda **_kwargs: source,
    )
    return {
        "data_root": data_root,
        "split_candidate_root": split_candidate.output_root,
        "publication_candidate_root": tmp_path / "publication-candidate",
        "plan_path": tmp_path / "publication-plan.json",
        "source_revision": "f" * 40,
        "created_at": PUBLISHED_AT,
        "inventory_reader": _inventory,
    }


def test_plan_preserves_clear_and_quarantined_event_groups(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)

    evidence = build_canonical_split_action_publication_plan(**inputs)  # type: ignore[arg-type]

    publication = evidence.plan.publication
    assert publication.action_record_count == 3
    assert publication.active_action_record_count == 1
    assert publication.quarantined_action_record_count == 2
    assert publication.unresolved_source_action_count == 1
    assert publication.possible_impact_instrument_count == 1
    assert publication.clear_event_group_count == 1
    assert publication.quarantined_event_group_count == 1
    assert publication.adjustment_ledger_authorized is False
    assert publication.research_performance_authorized is False
    assert evidence.candidate_publication.actions[0].record_status == "active"
    assert all(
        item.record_status == "quarantined"
        for item in evidence.candidate_publication.actions[1:]
    )


def test_apply_is_atomic_and_exact_rerun_verifies_existing(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_action_publication_plan(**inputs)  # type: ignore[arg-type]
    plan = evidence.plan
    apply_values = {
        "plan_path": evidence.plan_path,
        "approved_plan_sha256": evidence.plan_sha256,
        "expected_plan_logical_fingerprint": plan.logical_fingerprint,
        "expected_current_state_fingerprint": (
            plan.expected_current_state_fingerprint
        ),
        "data_root": Path(plan.data_root),
        "inventory_reader": _inventory,
    }

    first = apply_approved_canonical_split_action_publication_plan(**apply_values)
    second = apply_approved_canonical_split_action_publication_plan(**apply_values)

    target = Path(plan.target_publication_root)
    assert first.status == "applied"
    assert first.published_file_count == 2
    assert second.status == "verified_existing"
    assert second.reused_file_count == 2
    assert target.stat().st_mode & 0o777 == 0o755
    assert {item.name for item in target.iterdir()} == {
        "actions.parquet",
        "manifest.json",
    }
    assert all(item.stat().st_mode & 0o777 == 0o644 for item in target.iterdir())


def test_inventory_change_after_plan_stops_apply(monkeypatch, tmp_path: Path) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_action_publication_plan(**inputs)  # type: ignore[arg-type]
    unrelated = Path(evidence.plan.data_root) / "unrelated.txt"
    unrelated.write_text("changed", encoding="utf-8")

    with pytest.raises(
        CanonicalSplitActionPublicationApplyError,
        match="inventory changed",
    ):
        apply_approved_canonical_split_action_publication_plan(
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
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_action_publication_plan(**inputs)  # type: ignore[arg-type]

    def interrupted_copy(_source: Path, destination: Path) -> None:
        Path(destination).write_bytes(b"partial")
        raise OSError("injected interruption")

    monkeypatch.setattr(apply_module.shutil, "copyfile", interrupted_copy)
    with pytest.raises(
        CanonicalSplitActionPublicationApplyError,
        match="atomic publication failed",
    ):
        apply_approved_canonical_split_action_publication_plan(
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
        f".{target.name}.staging."
        f"{evidence.plan.logical_fingerprint[:16]}"
    )
    assert not target.exists()
    assert not staging.exists()


def test_candidate_tamper_stops_plan_reread(monkeypatch, tmp_path: Path) -> None:
    inputs = _inputs(monkeypatch, tmp_path)
    evidence = build_canonical_split_action_publication_plan(**inputs)  # type: ignore[arg-type]
    candidate_path = Path(evidence.plan.candidate_root) / "manifest.json"
    candidate_path.chmod(0o600)
    candidate_path.write_bytes(candidate_path.read_bytes() + b"\n")
    candidate_path.chmod(0o400)

    with pytest.raises(CanonicalSplitActionPublicationPlanError):
        read_canonical_split_action_publication_plan(
            plan_path=evidence.plan_path,
            approved_plan_sha256=evidence.plan_sha256,
        )
