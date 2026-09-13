from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.market_data.v1 import ResolutionStatus
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services import historical_corporate_action_residual_evidence_census as module


EVALUATED_AT = datetime(2026, 9, 13, tzinfo=UTC)
ANCHOR = date(2026, 9, 3)


def _action(
    identifier: str,
    ticker: str,
    effective: date,
    action_type: str = "cash_dividend",
    *,
    cash_amount: Decimal | None = Decimal("0.25"),
    split_from: Decimal | None = None,
    split_to: Decimal | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        source_action_id=identifier,
        source_revision=1,
        provider_ticker=ticker,
        effective_date=effective,
        action_type=SimpleNamespace(value=action_type),
        cash_amount=cash_amount,
        split_ratio_from=split_from,
        split_ratio_to=split_to,
        quality_flags=("unresolved_ticker",),
        instrument_resolution_status=ResolutionStatus.UNRESOLVED,
    )


def _candidate(identifier: int) -> SimpleNamespace:
    return SimpleNamespace(
        instrument_id=UUID(f"00000000-0000-4000-8000-{identifier:012d}")
    )


def _lifecycle_pair(ticker: str, candidate: SimpleNamespace, index: int):
    source = SimpleNamespace(
        ticker=ticker,
        type="CS",
        source_payload_fingerprint=f"{index:064x}",
    )
    decision = SimpleNamespace(
        disposition=InactiveLifecycleDisposition.REVIEW_CANDIDATE,
        canonical_instrument_id=candidate.instrument_id,
        canonical_first_observed_date=date(2026, 1, 1),
        canonical_last_observed_date=date(2026, 1, 10),
        effective_date_candidate=date(2026, 1, 20),
        selected_identity_type=SimpleNamespace(value="share_class_figi"),
        selected_identity_value=f"FIGI{index}",
    )
    return source, decision


def _fixture(monkeypatch: pytest.MonkeyPatch):
    candidates = {
        ticker: _candidate(index)
        for index, ticker in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE"), 1)
    }
    source_rows = (
        _action("a", "AAA", date(2026, 1, 5)),
        _action(
            "b",
            "BBB",
            date(2026, 1, 15),
            "reverse_split",
            cash_amount=None,
            split_from=Decimal("10"),
            split_to=Decimal("1"),
        ),
        _action("c", "CCC", date(2025, 12, 20)),
        _action("d", "DDD", date(2026, 2, 1)),
        _action("e", "EEE", date(2026, 1, 5)),
        _action("z", "ZZZ", date(2026, 1, 5)),
    )
    census_records = tuple(
        SimpleNamespace(
            provider_ticker=ticker,
            classification="one_historical_candidate",
            candidates=(candidate,),
        )
        for ticker, candidate in candidates.items()
    ) + (
        SimpleNamespace(
            provider_ticker="ZZZ",
            classification="zero_historical_candidates",
            candidates=(),
        ),
    )
    pairs = [
        _lifecycle_pair(ticker, candidates[ticker], index)
        for index, ticker in enumerate(("AAA", "BBB", "CCC", "DDD"), 1)
    ]
    pairs.append(
        (
            SimpleNamespace(
                ticker="ZZZ", type="FUND", source_payload_fingerprint="f" * 64
            ),
            SimpleNamespace(
                disposition=InactiveLifecycleDisposition.QUARANTINED,
                selected_identity_type=SimpleNamespace(value="composite_figi"),
                selected_identity_value="FIGIZ",
            ),
        )
    )
    lifecycle = SimpleNamespace(
        source_observations=tuple(item[0] for item in pairs),
        decisions=tuple(item[1] for item in pairs),
        manifest_sha256="4" * 64,
        manifest=SimpleNamespace(
            anchor_date=ANCHOR,
            logical_fingerprint="5" * 64,
            source_artifact=SimpleNamespace(record_count=5),
            decision_artifact=SimpleNamespace(record_count=5),
        ),
    )
    shadow = SimpleNamespace(
        records=source_rows,
        manifest_sha256="1" * 64,
        manifest=SimpleNamespace(logical_fingerprint="2" * 64),
    )
    unresolved = SimpleNamespace(
        records=census_records,
        manifest_sha256="3" * 64,
        manifest=SimpleNamespace(
            logical_fingerprint="6" * 64,
            unresolved_typed_record_count=len(source_rows),
        ),
    )
    finra_rows = (
        {
            "oldSymbolCode": "AAA",
            "newSymbolCode": "AAA",
            "exDate": "2026-01-05",
            "cashAmountText": "0.25",
            "changeSymbolFlag": "Y",
        },
        {
            "oldSymbolCode": "BBB",
            "newSymbolCode": "BBB",
            "exDate": "2026-01-15",
            "reverseSplitRate": "1:10",
            "securityDeleteFlag": "Y",
        },
    )
    finra_census = SimpleNamespace(
        logical_fingerprint="7" * 64,
        package_chain_fingerprint="8" * 64,
        package_count=1,
        record_count=len(finra_rows),
    )
    monkeypatch.setattr(
        module, "read_historical_corporate_action_resolution_shadow", lambda **_: shadow
    )
    monkeypatch.setattr(
        module, "read_historical_corporate_action_unresolved_census", lambda **_: unresolved
    )
    monkeypatch.setattr(
        module,
        "read_historical_inactive_lifecycle_resolution_shadow",
        lambda **_: lifecycle,
    )
    monkeypatch.setattr(
        module,
        "_read_finra_range",
        lambda **_: (finra_rows, finra_census, "9" * 64),
    )
    return source_rows


def test_residual_census_separates_support_gaps_and_contradictions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fixture(monkeypatch)
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    result = module.build_historical_corporate_action_residual_evidence_census(
        data_root=tmp_path,
        resolution_shadow_output_root=tmp_path,
        resolution_shadow_custody_root=tmp_path,
        unresolved_census_output_root=tmp_path,
        unresolved_census_custody_root=tmp_path,
        lifecycle_shadow_root=tmp_path,
        lifecycle_shadow_custody_root=tmp_path,
        lifecycle_anchor_dates=(ANCHOR,),
        finra_custody_root=tmp_path,
        finra_range_start=date(2021, 9, 13),
        finra_range_end=date(2026, 9, 9),
        output_root=custody / "build=fixture",
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=EVALUATED_AT,
    )
    assert result.status == "published"
    assert result.manifest.residual_record_count == 6
    assert dict(result.manifest.residual_record_candidate_relation_counts) == {
        "after_delist_candidate": 1,
        "before_canonical_first_observed": 1,
        "inside_canonical_observed_span": 1,
        "mixed_anchor_boundary": 0,
        "no_lifecycle_evidence": 1,
        "unverified_terminal_gap": 1,
    }
    assert result.manifest.finra_exact_date_symbol_record_count == 2
    assert result.manifest.finra_exact_numeric_record_count == 2
    by_ticker = {item.provider_ticker: item for item in result.records}
    assert by_ticker["AAA"].lifecycle_inside_canonical_observed_span_count == 1
    assert by_ticker["BBB"].lifecycle_unverified_terminal_gap_count == 1
    assert by_ticker["CCC"].lifecycle_before_canonical_first_observed_count == 1
    assert by_ticker["DDD"].lifecycle_after_delist_candidate_count == 1
    assert by_ticker["EEE"].lifecycle_no_lifecycle_evidence_count == 1
    assert by_ticker["ZZZ"].inactive_source_state == "matched_one_stable_identity"
    assert by_ticker["ZZZ"].inactive_source_type_codes == ("FUND",)
    assert by_ticker["AAA"].finra_flag_codes == ("symbol_change",)
    assert by_ticker["BBB"].finra_flag_codes == ("security_delete",)
    assert result.manifest.stable_identity_assignment_count == 0
    assert result.output_root.stat().st_mode & 0o777 == 0o700
    assert all(item.stat().st_mode & 0o777 == 0o400 for item in result.output_root.iterdir())
    reread = module.read_historical_corporate_action_residual_evidence_census(
        output_root=result.output_root, output_custody_root=custody
    )
    assert reread.records == result.records
    assert reread.manifest == result.manifest


def test_residual_census_rejects_tampering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fixture(monkeypatch)
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    target = custody / "build=fixture"
    result = module.build_historical_corporate_action_residual_evidence_census(
        data_root=tmp_path,
        resolution_shadow_output_root=tmp_path,
        resolution_shadow_custody_root=tmp_path,
        unresolved_census_output_root=tmp_path,
        unresolved_census_custody_root=tmp_path,
        lifecycle_shadow_root=tmp_path,
        lifecycle_shadow_custody_root=tmp_path,
        lifecycle_anchor_dates=(ANCHOR,),
        finra_custody_root=tmp_path,
        finra_range_start=date(2021, 9, 13),
        finra_range_end=date(2026, 9, 9),
        output_root=target,
        output_custody_root=custody,
        implementation_revision="a" * 40,
        evaluated_at=EVALUATED_AT,
    )
    records_path = result.output_root / module.RECORDS_FILE
    records_path.chmod(0o600)
    records_path.write_bytes(records_path.read_bytes() + b"tamper")
    records_path.chmod(0o400)
    with pytest.raises(module.HistoricalCorporateActionResidualEvidenceCensusError):
        module.read_historical_corporate_action_residual_evidence_census(
            output_root=target, output_custody_root=custody
        )
