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
from tip_api.services import canonical_split_action_candidate as module
from tip_api.services.canonical_split_action_candidate import (
    CanonicalSplitActionCandidateError,
    build_canonical_source_split_action_candidate,
    read_canonical_source_split_action_candidate,
)


START = date(2026, 8, 20)
BASIS = date(2026, 8, 22)
PUBLISHED_AT = datetime(2026, 9, 2, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 3, tzinfo=UTC)
AAA_ID = UUID("11111111-1111-4111-8111-111111111111")
BBB_ID = UUID("22222222-2222-4222-8222-222222222222")


def _split(
    source_action_id: str,
    *,
    instrument_id: UUID | None,
    ticker: str,
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
        action_type=CorporateActionType.STOCK_SPLIT,
        provider_ticker=ticker,
        instrument_resolution_status=(
            ResolutionStatus.RESOLVED if resolved else ResolutionStatus.UNRESOLVED
        ),
        instrument_id=instrument_id,
        effective_date=BASIS,
        split_ratio_from=Decimal(ratio_from),
        split_ratio_to=Decimal(ratio_to),
        knowledge_time_status=KnowledgeTimeStatus.FIRST_OBSERVED_ONLY,
        first_observed_at=datetime(2026, 9, 1, tzinfo=UTC),
        ingested_at=PUBLISHED_AT,
        quality_status=(
            QualityStatus.VALID if resolved else QualityStatus.PENDING_REVIEW
        ),
        quality_flags=(
            ("source_available_time_unavailable",)
            if resolved
            else ("source_available_time_unavailable", "unresolved_ticker")
        ),
    )


def _patch_inputs(monkeypatch, tmp_path: Path) -> dict[str, object]:
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    publication_path = data_root / "market-data" / "publication" / "manifest.json"
    publication_path.parent.mkdir(parents=True)
    records = (
        _split(
            "reciprocal-a",
            instrument_id=AAA_ID,
            ticker="AAA",
            ratio_from="3000",
            ratio_to="1",
        ),
        _split(
            "reciprocal-b",
            instrument_id=AAA_ID,
            ticker="AAA",
            ratio_from="1",
            ratio_to="3000",
        ),
        _split(
            "unresolved-one",
            instrument_id=None,
            ticker="OLD",
            ratio_from="1",
            ratio_to="2",
        ),
        _split(
            "unresolved-none",
            instrument_id=None,
            ticker="NONE",
            ratio_from="5",
            ratio_to="1",
        ),
    )
    publication = SimpleNamespace(
        start_date=START,
        end_date=BASIS,
        created_at=PUBLISHED_AT,
        logical_fingerprint="a" * 64,
        identity_evidence_path="market-data/identity-evidence/manifest.json",
        identity_evidence_sha256="b" * 64,
        identity_evidence_logical_fingerprint="c" * 64,
        identity_session_count=3,
    )
    source = SimpleNamespace(
        publication=publication,
        publication_path=publication_path,
        publication_sha256="d" * 64,
        records=records,
    )
    monkeypatch.setattr(module, "APPROVED_DATA_ROOT", data_root)
    monkeypatch.setattr(
        module,
        "read_canonical_corporate_action_source",
        lambda **_kwargs: source,
    )
    monkeypatch.setattr(
        module,
        "read_historical_ticker_candidates_bound_to_identity_evidence",
        lambda **_kwargs: {"OLD": frozenset({AAA_ID, BBB_ID}), "NONE": frozenset()},
    )
    return {
        "data_root": data_root,
        "source_publication_path": publication_path,
        "output_root": tmp_path / "candidate",
        "basis_session": BASIS,
        "calculated_at": CALCULATED_AT,
        "implementation_revision": "e" * 40,
    }


def test_builds_directly_bound_candidate_and_quarantines_multi_event(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)

    result = build_canonical_source_split_action_candidate(**inputs)  # type: ignore[arg-type]

    candidate = result.candidate
    assert result.status == "published"
    assert candidate.source_publication_logical_fingerprint == "a" * 64
    assert candidate.split_source_record_count == 4
    assert candidate.resolved_active_split_source_record_count == 2
    assert candidate.quarantined_split_source_record_count == 2
    assert candidate.resolved_event_group_count == 1
    assert candidate.clear_event_group_count == 0
    assert candidate.quarantined_event_group_count == 1
    assert candidate.possible_impact_instrument_count == 2
    assert candidate.resolved_events[0].ledger_admission_status == "quarantined"
    assert candidate.resolved_events[0].price_multiplier_to_post_event_basis == Decimal(
        "1.000000000000000000"
    )
    assert candidate.canonical_action_publication_status == "not_built"
    assert candidate.adjustment_ledger_projection_status == "not_built"
    assert result.output_root.stat().st_mode & 0o777 == 0o700
    assert (result.output_root / "candidate.json").stat().st_mode & 0o777 == 0o400
    assert read_canonical_source_split_action_candidate(
        output_root=result.output_root
    ).candidate == candidate


def test_exact_rerun_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    first = build_canonical_source_split_action_candidate(**inputs)  # type: ignore[arg-type]
    second = build_canonical_source_split_action_candidate(**inputs)  # type: ignore[arg-type]

    assert first.candidate == second.candidate
    assert second.status == "already_present"


def test_basis_must_equal_source_publication_end(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    inputs["basis_session"] = date(2026, 8, 21)

    with pytest.raises(CanonicalSplitActionCandidateError, match="basis"):
        build_canonical_source_split_action_candidate(**inputs)  # type: ignore[arg-type]


def test_tampered_candidate_stops_formal_reread(monkeypatch, tmp_path: Path) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    result = build_canonical_source_split_action_candidate(**inputs)  # type: ignore[arg-type]
    path = result.output_root / "candidate.json"
    path.chmod(0o600)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["possible_impact_instrument_count"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)

    with pytest.raises(CanonicalSplitActionCandidateError, match="contract"):
        read_canonical_source_split_action_candidate(output_root=result.output_root)


def test_resolved_non_active_action_requires_a_new_rule(
    monkeypatch, tmp_path: Path
) -> None:
    inputs = _patch_inputs(monkeypatch, tmp_path)
    source = module.read_canonical_corporate_action_source()
    corrected = source.records[0].model_copy(
        update={"record_status": CorporateActionRecordStatus.CORRECTED}
    )
    source.records = (corrected, *source.records[1:])

    with pytest.raises(CanonicalSplitActionCandidateError, match="new rule"):
        build_canonical_source_split_action_candidate(**inputs)  # type: ignore[arg-type]
