from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Rounded, localcontext
import json
from pathlib import Path
import tempfile
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateEntryReviewPosture,
    CandidateExtensionRisk,
    CandidateConfidenceV1,
    CandidateDataQualityStatus,
    CandidateMetricAvailability,
    CandidateOpportunityStage,
    CandidatePriorStateSourceV1,
    CandidatePriorStateSupportV1,
    CandidateRiskMode,
    CandidateTechnicalSetup,
    RegimeState,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_NON_BLOCKING_QUALITY_FLAGS,
    CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
    CANDIDATE_PARAMETER_FINGERPRINT,
    COMPONENT_PARAMETERS,
    parameter_payload,
)
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.opportunity_candidates import (
    OpportunityCandidateCalculationError,
    calculate_opportunity_candidate_scores,
    rank_opportunity_candidates,
)
from tip_api.services.candidate_entry_geometry import calculate_candidate_entry_geometry
from tip_api.services.candidate_entry_geometry_oracle import (
    compare_with_independent_entry_geometry_oracle,
)
from tip_api.services.candidate_entry_geometry_audit import (
    read_candidate_entry_geometry_audit,
    write_candidate_entry_geometry_audit,
)


NS = UUID("3d51d5d8-39c8-59c1-a084-01a89b96ea70")
PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"


def _id(label: str) -> UUID:
    return uuid5(NS, label)


def _panel(member_count: int = 40, adrc_count: int = 5) -> MarketRegimeInputPanel:
    sessions = tuple(date(2026, 7, 1) + timedelta(days=index) for index in range(26))
    primary_ids = tuple(_id(f"stock-{index:03d}") for index in range(member_count))
    adrc_ids = tuple(_id(f"adrc-{index:03d}") for index in range(adrc_count))
    etf_tickers = ("SPY", "QQQ", "IWM", "DIA", "XLK", "SMH")
    etf_ids = {ticker: _id(f"etf-{ticker}") for ticker in etf_tickers}
    bars: list[MarketRegimeBar] = []
    for day_index, session in enumerate(sessions):
        day = Decimal(day_index)
        for index, instrument_id in enumerate(primary_ids + adrc_ids):
            base = Decimal("35") + Decimal(index) / Decimal("3")
            slope = Decimal("0.18") + Decimal(index % 9) / Decimal("100")
            curvature = Decimal((index % 5) - 2) / Decimal("10000")
            close = base + slope * day + curvature * day * day
            volume = Decimal("2200000") + Decimal(index * 17000 + day_index * 15000)
            ticker = f"S{index:03d}" if index < member_count else f"A{index - member_count:03d}"
            bars.append(_bar(instrument_id, ticker, "common_stock", session, close, volume))
        for order, (ticker, instrument_id) in enumerate(etf_ids.items()):
            close = (
                Decimal("90")
                + Decimal(order * 7)
                + day * (Decimal("0.20") + Decimal(order) / Decimal("50"))
                + day * day * Decimal(order + 1) / Decimal("20000")
            )
            volume = Decimal("8000000") + Decimal(order * 250000 + day_index * 20000)
            bars.append(_bar(instrument_id, ticker, "etf", session, close, volume))
    sources = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"market-data/eod/session={session.isoformat()}",
            record_count=len(primary_ids) + len(adrc_ids) + len(etf_ids),
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    universes = (
        MarketRegimeUniverseSource(PRIMARY, "Common Shares", True, 0, frozenset(primary_ids), "a" * 64),
        MarketRegimeUniverseSource(
            SECONDARY,
            "Common Shares + ADRs",
            False,
            1,
            frozenset(primary_ids + adrc_ids),
            "b" * 64,
        ),
    )
    return MarketRegimeInputPanel(
        as_of_session=sessions[-1],
        calendar_id="XNYS",
        calendar_version="fixture",
        sessions=sessions,
        source_sessions=sources,
        bars=tuple(bars),
        universes=universes,
        activation_pointer_fingerprint="c" * 64,
        identity_logical_fingerprint="d" * 64,
        eod_content_fingerprint="e" * 64,
        eod_business_key_fingerprint="f" * 64,
        history_source_fingerprint="1" * 64,
    )


def _bar(instrument_id, ticker, kind, session, close, volume) -> MarketRegimeBar:
    return MarketRegimeBar(
        instrument_id=instrument_id,
        ticker=ticker,
        instrument_type=kind,
        primary_exchange="XNYS",
        session_date=session,
        open=close,
        high=close * Decimal("1.01"),
        low=close * Decimal("0.99"),
        close=close,
        volume=volume,
    )


@pytest.fixture(scope="module")
def full_panel() -> MarketRegimeInputPanel:
    return _panel()


def _calculate(panel: MarketRegimeInputPanel, universe_id: str = PRIMARY):
    universe = panel.select_universe(universe_id)
    supports = tuple(
        CandidatePriorStateSupportV1(
            instrument_id=instrument_id,
            prior_stage=CandidateOpportunityStage.WATCH,
            stage_confirmation_session_count=3,
            source_state_record_fingerprint=f"{index + 500:064x}",
        )
        for index, instrument_id in enumerate(sorted(universe.member_ids, key=str))
    )
    prior_state_source = CandidatePriorStateSourceV1(
        universe_id=universe_id,
        as_of_session=panel.as_of_session,
        bootstrap=False,
        source_state_session=panel.sessions[-2],
        state_history_fingerprint="3" * 64,
        supports=supports,
    )
    return calculate_opportunity_candidate_scores(
        panel=panel,
        universe_id=universe_id,
        regime_score=Decimal("72.5000"),
        regime_state=RegimeState.RISK_ON,
        regime_source_fingerprint="2" * 64,
        prior_state_source=prior_state_source,
    )


def _bootstrap(panel: MarketRegimeInputPanel, universe_id: str = PRIMARY) -> CandidatePriorStateSourceV1:
    return CandidatePriorStateSourceV1(
        universe_id=universe_id,
        as_of_session=panel.as_of_session,
        bootstrap=True,
        source_state_session=None,
        state_history_fingerprint=CANDIDATE_PRIOR_STATE_BOOTSTRAP_FINGERPRINT,
        supports=(),
    )


def _entry_states(batch, stage=CandidateOpportunityStage.WATCH):
    from tip_api.contracts.analytics.v1 import OpportunityCandidateStateRecordV1

    return tuple(
        OpportunityCandidateStateRecordV1.model_construct(
            as_of_session=batch.as_of_session,
            universe_id=batch.universe_id,
            instrument_id=item.instrument_id,
            final_stage=stage,
            logical_fingerprint=f"{index + 9000:064x}",
        )
        for index, item in enumerate(batch.candidates)
    )


def test_fixed_parameter_and_complete_candidate_ledger(full_panel: MarketRegimeInputPanel) -> None:
    batch = _calculate(full_panel)
    assert batch.parameter_fingerprint == CANDIDATE_PARAMETER_FINGERPRINT
    assert batch.universe_member_count == 40
    assert batch.bar_covered_member_count == 40
    assert not batch.missing_member_ids
    assert tuple(item.component_id for item in batch.candidates[0].components) == tuple(
        item.component_id for item in COMPONENT_PARAMETERS
    )
    for candidate in batch.candidates:
        assert candidate.base_score == candidate.adjusted_score
        assert candidate.regime_adjustment == "0.0000"
        assert Decimal(candidate.configured_weight_available) >= Decimal("80")
        assert sum(
            Decimal(item.contribution)
            for item in candidate.components
            if item.contribution is not None
        ).quantize(Decimal("0.0001")) == Decimal(candidate.base_score)
        proxy = next(item for item in candidate.components if item.component_id == "etf_sector_alignment")
        if proxy.score is not None:
            assert Decimal(proxy.score) <= Decimal("70")
        if candidate.primary_driver_ticker is None:
            assert candidate.primary_driver_instrument_id is None
        else:
            assert candidate.primary_driver_instrument_id is not None
        assert "candidate_score_not_success_probability" in candidate.warnings
        assert "underlying_stock_score_not_option_return" in candidate.warnings


def test_secondary_marks_only_formal_delta_as_adrc(full_panel: MarketRegimeInputPanel) -> None:
    primary = _calculate(full_panel, PRIMARY)
    secondary = _calculate(full_panel, SECONDARY)
    primary_ids = {item.instrument_id for item in primary.candidates}
    shared = [item for item in secondary.candidates if item.instrument_id in primary_ids]
    extras = [item for item in secondary.candidates if item.instrument_id not in primary_ids]
    assert all(item.security_type == "CS" for item in shared)
    assert len(extras) == 5 and all(item.security_type == "ADRC" for item in extras)


def test_missing_proxy_component_reweights_without_inventing_sector(full_panel: MarketRegimeInputPanel) -> None:
    spy_id = _id("etf-SPY")
    bars = tuple(
        replace(item, open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"))
        if item.instrument_id == spy_id
        else item
        for item in full_panel.bars
    )
    batch = _calculate(replace(full_panel, bars=bars))
    assert batch.candidates
    for candidate in batch.candidates:
        proxy = next(item for item in candidate.components if item.component_id == "etf_sector_alignment")
        if candidate.primary_driver_ticker is None:
            assert proxy.availability is CandidateMetricAvailability.UNAVAILABLE
            assert candidate.relationship_kind is None
            assert Decimal(candidate.configured_weight_available) == Decimal("87.0000")
            assert candidate.base_score is not None


def test_more_than_twenty_missing_weight_makes_score_null(full_panel: MarketRegimeInputPanel) -> None:
    target = _id("stock-000")
    bars = tuple(
        item
        for item in full_panel.bars
        if item.instrument_id != target or item.session_date == full_panel.as_of_session
    )
    batch = _calculate(replace(full_panel, bars=bars))
    candidate = next(item for item in batch.candidates if item.instrument_id == target)
    assert Decimal(candidate.configured_weight_available) < Decimal("80")
    assert candidate.base_score is None
    assert candidate.adjusted_score is None
    assert candidate.data_quality_status is CandidateDataQualityStatus.DEGRADED
    assert "candidate_score_unavailable_due_to_component_missingness" in candidate.warnings


def test_extreme_move_quarantines_and_cannot_rank(full_panel: MarketRegimeInputPanel) -> None:
    target = _id("stock-000")
    latest = full_panel.as_of_session
    original = next(item for item in full_panel.bars if item.instrument_id == target and item.session_date == latest)
    extreme_close = original.close * Decimal("2")
    extreme = replace(
        original,
        open=extreme_close,
        high=extreme_close * Decimal("1.01"),
        low=extreme_close * Decimal("0.99"),
        close=extreme_close,
    )
    bars = tuple(extreme if item.instrument_id == target and item.session_date == latest else item for item in full_panel.bars)
    batch = _calculate(replace(full_panel, bars=bars))
    candidate = next(item for item in batch.candidates if item.instrument_id == target)
    assert candidate.corporate_action_review_required
    assert candidate.data_quality_status is CandidateDataQualityStatus.QUARANTINED
    ranked = rank_opportunity_candidates(batch=batch, risk_mode=CandidateRiskMode.AGGRESSIVE)
    assessment = next(item for item in ranked.assessments if item.instrument_id == target)
    assert not assessment.eligible
    assert "candidate_quarantined" in assessment.rejection_reason_codes


@pytest.mark.parametrize(
    ("changes", "reason"),
    (
        ({"split_adjustment_factor": Decimal("2")}, "non_unit_adjustment_factor_review_required"),
        ({"quality_status": "warning"}, "source_quality_status_review_required"),
        ({"quality_flags": ("provider_warning",)}, "unknown_source_quality_flag_review_required"),
    ),
)
def test_adjustment_and_quality_evidence_quarantine(
    full_panel: MarketRegimeInputPanel,
    changes: dict[str, object],
    reason: str,
) -> None:
    target = _id("stock-000")
    latest = full_panel.as_of_session
    bars = tuple(
        replace(item, **changes)
        if item.instrument_id == target and item.session_date == latest
        else item
        for item in full_panel.bars
    )
    candidate = next(item for item in _calculate(replace(full_panel, bars=bars)).candidates if item.instrument_id == target)
    assert candidate.corporate_action_review_required
    assert candidate.data_quality_status is CandidateDataQualityStatus.QUARANTINED
    assert reason in candidate.reason_codes


@pytest.mark.parametrize("quality_flag", CANDIDATE_NON_BLOCKING_QUALITY_FLAGS)
def test_allowlisted_source_quality_flags_degrade_without_quarantine(
    full_panel: MarketRegimeInputPanel,
    quality_flag: str,
) -> None:
    target = _id("stock-000")
    latest = full_panel.as_of_session
    bars = tuple(
        replace(item, quality_flags=(quality_flag,))
        if item.instrument_id == target and item.session_date == latest
        else item
        for item in full_panel.bars
    )
    candidate = next(
        item
        for item in _calculate(replace(full_panel, bars=bars)).candidates
        if item.instrument_id == target
    )
    assert not candidate.corporate_action_review_required
    assert candidate.data_quality_status is CandidateDataQualityStatus.DEGRADED
    assert f"non_blocking_source_quality_flag:{quality_flag}" in candidate.warnings
    assert "non_blocking_source_quality_limitations_present" in candidate.warnings
    assert "corporate_action_review_required" not in candidate.reason_codes


def test_risk_modes_change_only_eligibility_and_rank(full_panel: MarketRegimeInputPanel) -> None:
    batch = _calculate(full_panel, SECONDARY)
    conservative = rank_opportunity_candidates(batch=batch, risk_mode="conservative")
    balanced = rank_opportunity_candidates(batch=batch, risk_mode="balanced")
    aggressive = rank_opportunity_candidates(batch=batch, risk_mode="aggressive")
    assert all(
        not item.eligible
        for item in conservative.assessments
        if next(candidate for candidate in batch.candidates if candidate.instrument_id == item.instrument_id).security_type == "ADRC"
    )
    assert conservative.eligible_count <= 5  # 20% of the fixed 25-row cap for one dominant proxy group.
    assert balanced.eligible_count <= 12  # 25% of 50, rounded down.
    assert aggressive.eligible_count <= 35  # 35% of 100.
    assert batch.logical_fingerprint == _calculate(full_panel, SECONDARY).logical_fingerprint


@pytest.mark.parametrize("precision", (9, 28, 50))
@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP))
def test_decimal_context_and_outer_traps_do_not_change_candidate_fingerprint(
    full_panel: MarketRegimeInputPanel, precision: int, rounding: str
) -> None:
    expected = _calculate(full_panel)
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        actual = _calculate(full_panel)
    assert actual.logical_fingerprint == expected.logical_fingerprint


def test_bad_source_binding_and_unknown_universe_fail_closed(full_panel: MarketRegimeInputPanel) -> None:
    with pytest.raises(OpportunityCandidateCalculationError, match="SHA-256"):
        calculate_opportunity_candidate_scores(
            panel=full_panel,
            universe_id=PRIMARY,
            regime_score="50",
            regime_state="balanced",
            regime_source_fingerprint="bad",
            prior_state_source=_bootstrap(full_panel),
        )
    with pytest.raises(Exception, match="unknown active Universe"):
        calculate_opportunity_candidate_scores(
            panel=full_panel,
            universe_id="legacy",
            regime_score="50",
            regime_state="balanced",
            regime_source_fingerprint="2" * 64,
            prior_state_source=_bootstrap(full_panel, "legacy"),
        )


def test_parameter_payload_binds_complete_candidate_formula() -> None:
    payload = parameter_payload()
    assert payload["confidence"]["weights"] == {
        "source_completeness": "0.40",
        "history_completeness": "0.25",
        "relationship_support": "0.20",
        "state_confirmation_support": "0.15",
    }
    assert payload["normalizers"]["sma10_to_sma20"] == ["-0.03", "0.03"]
    assert payload["quality_review"]["extreme_close_return_threshold"] == "0.50"
    assert payload["quality_review"]["non_unit_adjustment_factor_requires_review"] is True
    assert payload["quality_review"]["non_blocking_quality_flags"] == list(
        CANDIDATE_NON_BLOCKING_QUALITY_FLAGS
    )
    assert payload["quality_review"]["unknown_quality_flag_requires_review"] is True
    assert "any_quality_flag_requires_review" not in payload["quality_review"]


def test_bootstrap_is_explicit_and_confidence_is_strict(full_panel: MarketRegimeInputPanel) -> None:
    batch = calculate_opportunity_candidate_scores(
        panel=full_panel,
        universe_id=PRIMARY,
        regime_score=Decimal("72.5000"),
        regime_state=RegimeState.RISK_ON,
        regime_source_fingerprint="2" * 64,
        prior_state_source=_bootstrap(full_panel),
    )
    assert batch.prior_state_source.bootstrap
    assert all(item.confidence.confirmation_session_count == 0 for item in batch.candidates)
    assert all(item.confidence.prior_state_record_fingerprint is None for item in batch.candidates)
    with pytest.raises(ValueError, match="fixed four-term formula"):
        CandidateConfidenceV1(
            source_completeness="1.0000",
            history_completeness="1.0000",
            relationship_support="0.4000",
            state_confirmation_support="0.0000",
            confirmation_session_count=0,
            prior_state_record_fingerprint=None,
            confidence="0.9999",
        )


def test_entry_geometry_is_additive_and_source_bound(full_panel: MarketRegimeInputPanel) -> None:
    batch = _calculate(full_panel)
    result = calculate_candidate_entry_geometry(
        panel=full_panel,
        candidate_batch=batch,
        state_records=_entry_states(batch),
    )
    assert result.source_candidate_batch_fingerprint == batch.logical_fingerprint
    assert result.source_history_fingerprint == full_panel.history_source_fingerprint
    assert result.assessed_count == len(batch.candidates)
    assert result.unavailable_count == 0
    assert sum(result.extension_counts.values()) == len(batch.candidates)
    assert all(item.source_candidate_fingerprint for item in result.records)
    assert all(item.candidate_base_score is not None for item in result.records)
    assert batch == _calculate(full_panel)  # the entry layer cannot rewrite score or rank facts
    assert "shadow_only_not_candidate_rank_input" in result.warnings


def test_entry_geometry_flags_a_large_extension_instead_of_calling_it_ready(
    full_panel: MarketRegimeInputPanel,
) -> None:
    target_id = sorted(full_panel.select_universe(PRIMARY).member_ids, key=str)[0]
    bars = []
    for item in full_panel.bars:
        if item.instrument_id == target_id and item.session_date == full_panel.as_of_session:
            close = item.close * Decimal("1.20")
            bars.append(
                replace(
                    item,
                    open=item.close * Decimal("1.15"),
                    high=close * Decimal("1.01"),
                    low=item.close * Decimal("0.99"),
                    close=close,
                    volume=item.volume * Decimal("2.10"),
                )
            )
        else:
            bars.append(item)
    panel = replace(full_panel, bars=tuple(bars), history_source_fingerprint="9" * 64)
    batch = _calculate(panel)
    result = calculate_candidate_entry_geometry(
        panel=panel,
        candidate_batch=batch,
        state_records=_entry_states(batch),
    )
    target = next(item for item in result.records if item.instrument_id == target_id)
    assert target.extension_risk in {CandidateExtensionRisk.HIGH, CandidateExtensionRisk.EXTREME}
    assert target.review_posture is CandidateEntryReviewPosture.WAIT_FOR_RESET
    assert target.technical_setup in {
        CandidateTechnicalSetup.STRONG_BUT_EXTENDED,
        CandidateTechnicalSetup.NO_VIABLE_SETUP,
    }
    assert target.first_rejection_code in {"extension_risk_high", "extension_risk_extreme"}


def test_entry_geometry_fails_when_candidate_history_binding_differs(
    full_panel: MarketRegimeInputPanel,
) -> None:
    batch = _calculate(full_panel).model_copy(update={"history_source_fingerprint": "8" * 64})
    with pytest.raises(Exception, match="source history differs"):
        calculate_candidate_entry_geometry(
            panel=full_panel,
            candidate_batch=batch,
            state_records=_entry_states(batch),
        )


def test_independent_entry_geometry_oracle_matches_and_is_permutation_stable(
    full_panel: MarketRegimeInputPanel,
) -> None:
    batch = _calculate(full_panel)
    states = _entry_states(batch)
    result = calculate_candidate_entry_geometry(
        panel=full_panel,
        candidate_batch=batch,
        state_records=states,
    )
    oracle = compare_with_independent_entry_geometry_oracle(
        panel=full_panel,
        candidate_batch=batch,
        state_records=states,
        actual=result,
    )
    assert oracle.record_count == len(batch.candidates)
    assert oracle.mismatch_count == 0
    assert not oracle.mismatches
    assert oracle.input_permutation_match
    assert len(oracle.oracle_fingerprint) == 64


def test_entry_geometry_audit_writes_last_and_formally_rereads(
    full_panel: MarketRegimeInputPanel,
) -> None:
    batch = _calculate(full_panel)
    states = _entry_states(batch)
    result = calculate_candidate_entry_geometry(
        panel=full_panel,
        candidate_batch=batch,
        state_records=states,
    )
    oracle = compare_with_independent_entry_geometry_oracle(
        panel=full_panel,
        candidate_batch=batch,
        state_records=states,
        actual=result,
    )
    source_dir = Path(tempfile.mkdtemp(prefix="entry-geometry-source-", dir="/tmp"))
    output_dir = Path(tempfile.mkdtemp(prefix="entry-geometry-audit-", dir="/tmp"))
    source_manifest = {
        "logical_content_fingerprint": "4" * 64,
        "candidate_calculation_version": "market-regime-opportunity-candidate-v1.1.1",
        "candidate_parameter_fingerprint": "5" * 64,
        "candidate_state_parameter_fingerprint": "6" * 64,
        "as_of_session": full_panel.as_of_session.isoformat(),
    }
    source_path = source_dir / "candidate-audit-manifest.json"
    source_path.write_bytes((json.dumps(source_manifest, sort_keys=True, separators=(",", ":")) + "\n").encode())
    try:
        manifest = write_candidate_entry_geometry_audit(
            output_dir=output_dir,
            candidate_audit_dir=source_dir,
            candidate_audit_manifest=source_manifest,
            batches=(result,),
            oracle_reports=(oracle,),
            generated_at=datetime(2026, 8, 26, tzinfo=UTC),
        )
        assert manifest["completion_status"] == "completed"
        assert manifest["shadow_only"] is True
        assert manifest["oracle_mismatch_count"] == 0
        assert read_candidate_entry_geometry_audit(output_dir) == manifest
        assert {path.stat().st_mode & 0o777 for path in output_dir.iterdir()} == {0o400}
    finally:
        for directory in (output_dir, source_dir):
            for path in directory.iterdir():
                path.chmod(0o600)
                path.unlink()
            directory.rmdir()
