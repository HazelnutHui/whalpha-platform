from __future__ import annotations

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
from tip_api.services import historical_split_adjustment_candidate as module
from tip_api.services.historical_split_adjustment_candidate import (
    HistoricalSplitAdjustmentCandidateError,
    build_historical_split_adjustment_candidate,
    read_historical_split_adjustment_candidate,
)


START = date(2026, 8, 20)
BASIS = date(2026, 8, 22)
CALCULATED_AT = datetime(2026, 9, 3, tzinfo=UTC)
AAA_ID = UUID("11111111-1111-4111-8111-111111111111")
BBB_ID = UUID("22222222-2222-4222-8222-222222222222")


def _split(
    source_action_id: str,
    *,
    instrument_id: UUID | None,
    ticker: str,
    effective_date: date,
    action_type: CorporateActionType,
    ratio_from: str,
    ratio_to: str,
) -> CorporateActionSourceObservationV1:
    resolved = instrument_id is not None
    return CorporateActionSourceObservationV1(
        provider="massive_stocks_basic",
        source_action_id=source_action_id,
        source_revision=1,
        record_status=(
            CorporateActionRecordStatus.ACTIVE
            if resolved
            else CorporateActionRecordStatus.QUARANTINED
        ),
        action_type=action_type,
        provider_ticker=ticker,
        instrument_resolution_status=(
            ResolutionStatus.RESOLVED if resolved else ResolutionStatus.UNRESOLVED
        ),
        instrument_id=instrument_id,
        effective_date=effective_date,
        split_ratio_from=Decimal(ratio_from),
        split_ratio_to=Decimal(ratio_to),
        knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
        first_observed_at=datetime(2026, 9, 1, tzinfo=UTC),
        ingested_at=datetime(2026, 9, 2, tzinfo=UTC),
        quality_status=(
            QualityStatus.VALID if resolved else QualityStatus.PENDING_REVIEW
        ),
        quality_flags=(
            ("source_available_time_unavailable",)
            if resolved
            else ("source_available_time_unavailable", "unresolved_ticker")
        ),
    )


def _records() -> tuple[CorporateActionSourceObservationV1, ...]:
    return (
        _split(
            "reciprocal-a",
            instrument_id=AAA_ID,
            ticker="AAA",
            effective_date=BASIS,
            action_type=CorporateActionType.REVERSE_SPLIT,
            ratio_from="3000",
            ratio_to="1",
        ),
        _split(
            "reciprocal-b",
            instrument_id=AAA_ID,
            ticker="AAA",
            effective_date=BASIS,
            action_type=CorporateActionType.STOCK_SPLIT,
            ratio_from="1",
            ratio_to="3000",
        ),
        _split(
            "unresolved-one",
            instrument_id=None,
            ticker="OLD",
            effective_date=date(2026, 8, 21),
            action_type=CorporateActionType.STOCK_SPLIT,
            ratio_from="1",
            ratio_to="2",
        ),
        _split(
            "unresolved-none",
            instrument_id=None,
            ticker="NONE",
            effective_date=date(2026, 8, 21),
            action_type=CorporateActionType.REVERSE_SPLIT,
            ratio_from="5",
            ratio_to="1",
        ),
    )


def _patch_inputs(monkeypatch, tmp_path: Path) -> dict[str, object]:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    records = _records()
    manifest = SimpleNamespace(
        start_date=START,
        end_date=BASIS,
        materialized_at=datetime(2026, 9, 2, tzinfo=UTC),
        split_source_record_count=len(records),
        logical_fingerprint="a" * 64,
        identity_evidence_logical_fingerprint="b" * 64,
    )
    shadow = SimpleNamespace(
        manifest=manifest,
        manifest_sha256="c" * 64,
        records=records,
    )
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(
        module,
        "read_historical_corporate_action_resolution_shadow",
        lambda **_kwargs: shadow,
    )
    monkeypatch.setattr(
        module,
        "read_historical_ticker_candidates_bound_to_resolution_shadow",
        lambda **_kwargs: {"OLD": frozenset({AAA_ID, BBB_ID}), "NONE": frozenset()},
    )
    return {
        "data_root": data_root,
        "resolution_shadow_output_root": tmp_path / "resolution-shadow",
        "resolution_shadow_custody_root": tmp_path / "resolution-shadow-custody",
        "output_root": tmp_path / "split-candidate",
        "basis_session": BASIS,
        "calculated_at": CALCULATED_AT,
    }


def test_builds_split_first_owner_only_candidate(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)

    result = build_historical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]

    assert result.status == "published"
    assert result.candidate.split_source_record_count == 4
    assert result.candidate.resolved_split_source_record_count == 2
    assert result.candidate.unresolved_split_source_record_count == 2
    assert result.candidate.resolved_event_group_count == 1
    assert result.candidate.multiple_same_date_event_group_count == 1
    assert result.candidate.unresolved_with_historical_identity_count == 1
    assert result.candidate.unresolved_without_historical_identity_count == 1
    assert result.candidate.unresolved_with_ambiguous_historical_identity_count == 1
    assert result.candidate.possible_impact_instrument_count == 2
    event = result.candidate.resolved_events[0]
    assert event.price_multiplier_to_post_event_basis == Decimal(
        "1.000000000000000000"
    )
    assert event.volume_multiplier_to_post_event_basis == Decimal(
        "1.000000000000000000"
    )
    assert event.quality_flags == ("multiple_same_date_split_actions",)
    assert result.candidate.total_return_adjustment_status == "unavailable"
    assert result.candidate.ledger_projection_status == "not_built"
    assert result.output_root.stat().st_mode & 0o777 == 0o700
    assert (
        (result.output_root / "candidate.json").stat().st_mode & 0o777 == 0o400
    )

    reread = read_historical_split_adjustment_candidate(output_root=result.output_root)
    assert reread.candidate == result.candidate
    assert reread.file_sha256 == result.file_sha256


def test_exact_rerun_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    first = build_historical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]
    second = build_historical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]

    assert first.candidate == second.candidate
    assert second.status == "already_present"


def test_basis_must_equal_resolution_end(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    inputs["basis_session"] = date(2026, 8, 21)

    with pytest.raises(HistoricalSplitAdjustmentCandidateError, match="basis"):
        build_historical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]


def test_tampered_candidate_stops_formal_reread(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    result = build_historical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]
    path = result.output_root / "candidate.json"
    path.chmod(0o600)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["possible_impact_instrument_count"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)

    with pytest.raises(HistoricalSplitAdjustmentCandidateError, match="contract"):
        read_historical_split_adjustment_candidate(output_root=result.output_root)


def test_candidate_rejects_resolved_split_after_basis(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    shadow = module.read_historical_corporate_action_resolution_shadow()
    late = _split(
        "late",
        instrument_id=AAA_ID,
        ticker="AAA",
        effective_date=date(2026, 8, 23),
        action_type=CorporateActionType.STOCK_SPLIT,
        ratio_from="1",
        ratio_to="2",
    )
    shadow.records = (*shadow.records, late)
    shadow.manifest.split_source_record_count += 1

    with pytest.raises(HistoricalSplitAdjustmentCandidateError, match="eligible"):
        build_historical_split_adjustment_candidate(**inputs)  # type: ignore[arg-type]
