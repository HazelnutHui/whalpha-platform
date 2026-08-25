from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Rounded, localcontext
from pathlib import Path
import shutil
import tempfile
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.analytics.v1 import AvailabilityStatus
from tip_api.parameters.market_regime.v1_0_0 import DIMENSION_PARAMETERS
from tip_api.services.market_regime import (
    MarketRegimeCalculationError,
    _normalize,
    calculate_market_regime,
)
from tip_api.services.market_regime_audit import (
    MarketRegimeAuditError,
    read_market_regime_audit,
    validate_tmp_output_dir,
    write_market_regime_audit,
)
from tip_api.services.market_regime_oracle import compare_with_independent_oracle
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)


NS = UUID("c5b0e883-7b08-5cf9-ac73-a6ee888cc12e")
PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"


def _id(label: str) -> UUID:
    return uuid5(NS, label)


def _panel(member_count: int = 600) -> MarketRegimeInputPanel:
    sessions = tuple(date(2026, 7, 17) + timedelta(days=index) for index in range(26))
    primary_ids = tuple(_id(f"stock-{index:04d}") for index in range(member_count))
    secondary_extra = tuple(_id(f"adrc-{index:03d}") for index in range(10))
    benchmarks = {ticker: _id(f"etf-{ticker}") for ticker in ("SPY", "QQQ", "IWM", "DIA")}
    bars = []
    for day_index, session in enumerate(sessions):
        for index, instrument_id in enumerate(primary_ids + secondary_extra):
            base = Decimal("10") + Decimal(index) / Decimal("100")
            close = base + Decimal(day_index) * (Decimal("0.03") + Decimal(index % 7) / Decimal("1000"))
            volume = Decimal("1000000.0001") + Decimal(index * 100 + day_index * 1000)
            bars.append(_bar(instrument_id, f"S{index:04d}", "common_stock", session, close, volume))
        for order, (ticker, instrument_id) in enumerate(benchmarks.items()):
            close = Decimal("100") + Decimal(order * 10) + Decimal(day_index) * Decimal(order + 1) / Decimal("2")
            volume = Decimal("5000000") + Decimal(order * 100000 + day_index * 10000)
            bars.append(_bar(instrument_id, ticker, "etf", session, close, volume))
    sources = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"market-data/eod/session={session.isoformat()}",
            record_count=member_count + 14,
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    universes = (
        MarketRegimeUniverseSource(PRIMARY, "Common Shares", True, 0, frozenset(primary_ids), "a" * 64),
        MarketRegimeUniverseSource(SECONDARY, "Common Shares + ADRs", False, 1, frozenset(primary_ids + secondary_extra), "b" * 64),
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
        high=close,
        low=close,
        close=close,
        volume=volume,
    )


@pytest.fixture(scope="module")
def full_panel() -> MarketRegimeInputPanel:
    return _panel()


def test_full_five_dimension_ledger_and_independent_oracle(full_panel: MarketRegimeInputPanel) -> None:
    result, explanations = calculate_market_regime(panel=full_panel, universe_id=PRIMARY)
    oracle = compare_with_independent_oracle(panel=full_panel, result=result)
    assert tuple(item.dimension_id for item in result.dimensions) == (
        "trend", "breadth", "volatility", "liquidity_participation", "leadership_dispersion"
    )
    assert all(item.availability is AvailabilityStatus.AVAILABLE for item in result.dimensions)
    assert len([metric for item in result.dimensions for metric in item.raw_metrics]) == 18
    assert result.regime_score is not None and result.regime_state is None
    assert result.state_classification_status == "deferred_phase_1a"
    assert result.regime_adjustment == "0.0000"
    assert len(explanations) == 6
    assert oracle.mismatch_count == 0
    assert oracle.input_permutation_fingerprint_match
    assert oracle.future_session_reference_count == 0
    assert oracle.wrong_universe_reference_count == 0


def test_primary_and_secondary_are_isolated(full_panel: MarketRegimeInputPanel) -> None:
    primary, _ = calculate_market_regime(panel=full_panel, universe_id=PRIMARY)
    secondary, _ = calculate_market_regime(panel=full_panel, universe_id=SECONDARY)
    assert primary.membership_fingerprint != secondary.membership_fingerprint
    assert primary.universe_member_count == 600 and secondary.universe_member_count == 610
    assert all(
        f"activation:{PRIMARY}:" in reference
        for dimension in primary.dimensions
        for metric in dimension.raw_metrics
        for reference in metric.source_input_references
        if reference.startswith("activation:")
    )


def test_single_noncritical_metric_missing_reweights_only_inside_dimension() -> None:
    panel = _panel(499)
    result, _ = calculate_market_regime(panel=panel, universe_id=PRIMARY)
    breadth = next(item for item in result.dimensions if item.dimension_id == "breadth")
    advancer = next(item for item in breadth.raw_metrics if item.metric_id == "advancer_share_1")
    assert advancer.availability is AvailabilityStatus.UNAVAILABLE
    assert advancer.missing_reason == "insufficient_observations"
    assert breadth.availability is AvailabilityStatus.AVAILABLE
    assert breadth.internal_configured_weight_available == "75.0000"
    assert "internal_weight_redistributed" in breadth.reason_codes
    assert sum(
        Decimal(item.effective_weight)
        for item in breadth.raw_metrics if item.availability is AvailabilityStatus.AVAILABLE
    ) == Decimal("100.0000")


def test_whole_required_dimension_missing_makes_composite_unavailable(full_panel: MarketRegimeInputPanel) -> None:
    spy = _id("etf-SPY")
    bars = tuple(item for item in full_panel.bars if item.instrument_id != spy or item.session_date == full_panel.as_of_session)
    panel = replace(full_panel, bars=bars)
    result, _ = calculate_market_regime(panel=panel, universe_id=PRIMARY)
    assert next(item for item in result.dimensions if item.dimension_id == "trend").availability is AvailabilityStatus.UNAVAILABLE
    assert next(item for item in result.dimensions if item.dimension_id == "volatility").availability is AvailabilityStatus.UNAVAILABLE
    assert result.regime_score is None
    assert "composite_unavailable" in result.reason_codes


def test_session_gap_duplicate_and_illegal_inputs_fail_closed(full_panel: MarketRegimeInputPanel) -> None:
    missing_session = full_panel.sessions[10]
    with pytest.raises(MarketRegimeCalculationError, match="session gap"):
        calculate_market_regime(
            panel=replace(full_panel, bars=tuple(item for item in full_panel.bars if item.session_date != missing_session)),
            universe_id=PRIMARY,
        )
    duplicate = replace(full_panel, bars=full_panel.bars + (full_panel.bars[0],))
    with pytest.raises(MarketRegimeCalculationError, match="duplicate"):
        calculate_market_regime(panel=duplicate, universe_id=PRIMARY)
    bad = replace(full_panel.bars[0], close=Decimal("NaN"))
    with pytest.raises(MarketRegimeCalculationError, match="non-finite"):
        calculate_market_regime(panel=replace(full_panel, bars=(bad,) + full_panel.bars[1:]), universe_id=PRIMARY)


def test_insufficient_history_and_all_zero_volume_are_not_zero_filled(full_panel: MarketRegimeInputPanel) -> None:
    shortened_sessions = full_panel.sessions[-20:]
    shortened = replace(
        full_panel,
        sessions=shortened_sessions,
        source_sessions=full_panel.source_sessions[-20:],
        bars=tuple(item for item in full_panel.bars if item.session_date in shortened_sessions),
    )
    with pytest.raises(MarketRegimeCalculationError, match="at least 21"):
        calculate_market_regime(panel=shortened, universe_id=PRIMARY)

    member_ids = full_panel.select_universe(PRIMARY).member_ids
    zero_bars = tuple(
        replace(item, volume=Decimal(0)) if item.instrument_id in member_ids else item
        for item in full_panel.bars
    )
    result, _ = calculate_market_regime(panel=replace(full_panel, bars=zero_bars), universe_id=PRIMARY)
    participation = next(item for item in result.dimensions if item.dimension_id == "liquidity_participation")
    aggregate = next(item for item in participation.raw_metrics if item.metric_id == "aggregate_participation_ratio")
    up_share = next(item for item in participation.raw_metrics if item.metric_id == "up_participation_share")
    assert aggregate.raw_value is None and aggregate.missing_reason == "zero_denominator"
    assert up_share.raw_value is None and up_share.missing_reason == "zero_denominator"
    assert participation.availability is AvailabilityStatus.UNAVAILABLE


@pytest.mark.parametrize("precision", (9, 28, 50))
@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP))
def test_decimal_context_and_outer_traps_cannot_change_core(
    full_panel: MarketRegimeInputPanel, precision: int, rounding: str
) -> None:
    expected, _ = calculate_market_regime(panel=full_panel, universe_id=PRIMARY)
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        actual, _ = calculate_market_regime(panel=full_panel, universe_id=PRIMARY)
        oracle = compare_with_independent_oracle(panel=full_panel, result=actual)
    assert actual.logical_fingerprint == expected.logical_fingerprint
    assert oracle.mismatch_count == 0


def test_fixed_normalizer_threshold_boundaries() -> None:
    metrics = {item.metric_id: item for dim in DIMENSION_PARAMETERS for item in dim.metrics}
    rising = metrics["broad_return_5"]
    declining = metrics["spy_realized_volatility_10"]
    triangular = metrics["return_dispersion_5"]
    assert _normalize(Decimal("-0.03"), rising) == 0
    assert _normalize(Decimal("0.03"), rising) == 100
    assert _normalize(Decimal("0.10"), declining) == 100
    assert _normalize(Decimal("0.35"), declining) == 0
    assert _normalize(Decimal("0.005"), triangular) == 0
    assert _normalize(Decimal("0.025"), triangular) == 100
    assert _normalize(Decimal("0.08"), triangular) == 0


def test_oracle_reports_a_perturbed_ledger(full_panel: MarketRegimeInputPanel) -> None:
    result, _ = calculate_market_regime(panel=full_panel, universe_id=PRIMARY)
    trend = result.dimensions[0]
    metric = trend.raw_metrics[0].model_copy(update={"normalized_value": "0.0000"})
    bad_trend = trend.model_copy(update={"raw_metrics": (metric,) + trend.raw_metrics[1:]})
    perturbed = result.model_copy(update={"dimensions": (bad_trend,) + result.dimensions[1:]})
    oracle = compare_with_independent_oracle(panel=full_panel, result=perturbed)
    assert oracle.mismatch_count > 0
    assert any("broad_return_20.normalized_value" in item for item in oracle.mismatches)


def test_audit_artifacts_are_canonical_rereadable_and_logically_deterministic(
    tmp_path: Path, full_panel: MarketRegimeInputPanel
) -> None:
    result, explanations = calculate_market_regime(panel=full_panel, universe_id=PRIMARY)
    oracle = compare_with_independent_oracle(panel=full_panel, result=result)
    first = Path(tempfile.mkdtemp(prefix="mrom-test-a-", dir="/tmp"))
    second = Path(tempfile.mkdtemp(prefix="mrom-test-b-", dir="/tmp"))
    try:
        for output, generated in ((first, datetime(2026, 8, 25, tzinfo=UTC)), (second, datetime(2026, 8, 26, tzinfo=UTC))):
            write_market_regime_audit(
                output_dir=output,
                panel=full_panel,
                composites=(result,),
                explanations=explanations,
                oracle_reports=(oracle,),
                generated_at=generated,
                elapsed_seconds="1.000000",
                peak_memory_kib=123,
            )
        a, b = read_market_regime_audit(first), read_market_regime_audit(second)
        assert a["logical_content_fingerprint"] == b["logical_content_fingerprint"]
        assert a["composite_fingerprints"] == b["composite_fingerprints"]
        assert a["generated_at"] != b["generated_at"]
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)


def test_output_path_rejects_production_repo_symlink_and_nonempty(tmp_path: Path) -> None:
    with pytest.raises(MarketRegimeAuditError):
        validate_tmp_output_dir(Path("/data/market-regime"))
    with pytest.raises(MarketRegimeAuditError):
        validate_tmp_output_dir(Path("/home/hui/projects/trading-intelligence-platform/audit"))
    nonempty = Path(tempfile.mkdtemp(prefix="mrom-nonempty-", dir="/tmp"))
    symlink = Path(str(nonempty) + "-link")
    try:
        (nonempty / "x").write_text("x")
        with pytest.raises(MarketRegimeAuditError):
            validate_tmp_output_dir(nonempty)
        symlink.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(MarketRegimeAuditError):
            validate_tmp_output_dir(symlink)
    finally:
        shutil.rmtree(nonempty, ignore_errors=True)
        symlink.unlink(missing_ok=True)
