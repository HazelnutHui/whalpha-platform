from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.reconstructed_lane import (
    ChinaAshareReconstructedDisposition,
)
from tip_api.services.china_ashare_reconstructed_lane import (
    ChinaAshareReconstructedLaneError,
    build_china_ashare_reconstructed_partition,
    plan_china_ashare_reconstructed_lane,
)


def test_reconstructed_lane_uses_next_session_and_fails_closed() -> None:
    sessions = (
        date(2026, 9, 14),
        date(2026, 9, 15),
        date(2026, 9, 16),
    )
    diagnostic, gaps = _inputs(target_session_count=3)
    plan = plan_china_ashare_reconstructed_lane(
        diagnostic=diagnostic,
        gap_checklist=gaps,
        target_sessions=sessions,
    )
    first = UUID("00000000-0000-0000-0000-000000000001")
    second = UUID("00000000-0000-0000-0000-000000000002")
    states = (
        _state(first, sessions[0]),
        _state(
            first,
            sessions[1],
            warning=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
        ),
        _state(first, sessions[2]),
        _state(second, sessions[0]),
    )
    adjustments = (
        _adjustment(first, sessions[0], "1"),
        _adjustment(first, sessions[1], "0.9"),
    )
    partition = SimpleNamespace(
        manifest=SimpleNamespace(partition_index=0, logical_fingerprint="6" * 64),
        normalized=SimpleNamespace(states=states, adjustments=adjustments),
    )

    decisions, aggregate = build_china_ashare_reconstructed_partition(
        plan=plan,
        partition=partition,
    )

    assert len(decisions) == 4
    assert decisions[0].knowledge_session_date == sessions[1]
    assert decisions[2].knowledge_session_date is None
    assert all(item.source_available_at is None for item in decisions)
    assert all(item.as_operated is False for item in decisions)
    assert all(item.research_eligible is False for item in decisions)
    assert all(
        item.disposition is ChinaAshareReconstructedDisposition.QUARANTINED
        for item in decisions
    )
    assert aggregate.next_session_mapped_count == 3
    assert aggregate.no_next_session_count == 1
    assert aggregate.unknown_price_limit_count == 4
    assert aggregate.risk_warning_exclusion_candidate_count == 1
    assert aggregate.factor_change_candidate_window_count == 1
    assert aggregate.terminal_boundary_candidate_count == 1
    assert aggregate.research_backtest_authorized is False


def test_reconstructed_lane_rejects_observed_source_clock_replacement() -> None:
    diagnostic, gaps = _inputs(target_session_count=2)
    plan = plan_china_ashare_reconstructed_lane(
        diagnostic=diagnostic,
        gap_checklist=gaps,
        target_sessions=(date(2026, 9, 15), date(2026, 9, 16)),
    )
    partition = SimpleNamespace(
        manifest=SimpleNamespace(partition_index=0, logical_fingerprint="6" * 64),
        normalized=SimpleNamespace(
            states=(
                SimpleNamespace(
                    instrument_id=UUID("00000000-0000-0000-0000-000000000001"),
                    session_date=date(2026, 9, 15),
                    trading_status=ChinaAshareTradingStatus.TRADING,
                    risk_warning_status=ChinaAshareRiskWarningStatus.NONE,
                    price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
                    source_available_at=object(),
                ),
            ),
            adjustments=(),
        ),
    )
    with pytest.raises(ChinaAshareReconstructedLaneError, match="source clocks"):
        build_china_ashare_reconstructed_partition(plan=plan, partition=partition)


def _inputs(*, target_session_count: int):
    plan = SimpleNamespace(
        logical_fingerprint="1" * 64,
        normalized_run_fingerprint="4" * 64,
        normalized_partition_manifest_fingerprints=("6" * 64,),
        target_session_count=target_session_count,
    )
    streaming = SimpleNamespace(logical_fingerprint="2" * 64)
    manifest = SimpleNamespace(logical_fingerprint="3" * 64)
    diagnostic = SimpleNamespace(plan=plan, streaming=streaming, manifest=manifest)
    gaps = SimpleNamespace(
        diagnostic_plan_fingerprint=plan.logical_fingerprint,
        diagnostic_package_fingerprint=manifest.logical_fingerprint,
        streaming_aggregate_fingerprint=streaming.logical_fingerprint,
        logical_fingerprint="5" * 64,
    )
    return diagnostic, gaps


def _state(instrument_id, session_date, *, warning=ChinaAshareRiskWarningStatus.NONE):
    return SimpleNamespace(
        instrument_id=instrument_id,
        session_date=session_date,
        trading_status=ChinaAshareTradingStatus.TRADING,
        risk_warning_status=warning,
        price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
        source_available_at=None,
    )


def _adjustment(instrument_id, session_date, factor):
    value = Decimal(factor)
    return SimpleNamespace(
        instrument_id=instrument_id,
        session_date=session_date,
        provider_factor=value,
        fore_adjust_factor=value,
        back_adjust_factor=value,
    )
