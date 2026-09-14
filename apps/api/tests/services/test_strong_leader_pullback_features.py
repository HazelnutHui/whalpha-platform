from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.services.strong_leader_pullback_features import (
    StrongLeaderPullbackFeatureBar,
    StrongLeaderPullbackFeatureError,
    calculate_strong_leader_pullback_features,
)


ALPHA_ID = UUID("11111111-1111-4111-8111-111111111111")
BETA_ID = UUID("22222222-2222-4222-8222-222222222222")
GAMMA_ID = UUID("33333333-3333-4333-8333-333333333333")
SPY_ID = UUID("99999999-9999-4999-8999-999999999999")


def _series(*, daily_step: str, spread: str = "1"):
    start = date(2026, 1, 2)
    step = Decimal(daily_step)
    half_spread = Decimal(spread)
    return tuple(
        StrongLeaderPullbackFeatureBar(
            session=start + timedelta(days=index),
            open=Decimal("100") + step * index,
            high=Decimal("100") + step * index + half_spread,
            low=Decimal("100") + step * index - half_spread,
            close=Decimal("100") + step * index,
            volume=Decimal("1000000"),
        )
        for index in range(21)
    )


def test_calculates_average_rank_ties_and_stable_instrument_order():
    panel = calculate_strong_leader_pullback_features(
        member_ids=frozenset((GAMMA_ID, ALPHA_ID, BETA_ID)),
        benchmark_instrument_id=SPY_ID,
        series_by_instrument={
            GAMMA_ID: _series(daily_step="0"),
            BETA_ID: _series(daily_step="1"),
            SPY_ID: _series(daily_step="0.25"),
            ALPHA_ID: _series(daily_step="1"),
        },
    )

    assert tuple(item.instrument_id for item in panel.features) == (
        ALPHA_ID,
        BETA_ID,
        GAMMA_ID,
    )
    assert tuple(
        item.relative_strength_20s_percentile for item in panel.features
    ) == ("0.7500", "0.7500", "0.0000")


def test_rejects_a_panel_that_is_not_exactly_21_aligned_sessions():
    series = _series(daily_step="1")

    with pytest.raises(
        StrongLeaderPullbackFeatureError,
        match="incomplete or invalid",
    ):
        calculate_strong_leader_pullback_features(
            member_ids=frozenset((ALPHA_ID,)),
            benchmark_instrument_id=SPY_ID,
            series_by_instrument={
                ALPHA_ID: series[:-1],
                SPY_ID: series,
            },
        )


def test_rejects_a_non_positive_atr_instead_of_manufacturing_a_score():
    flat = _series(daily_step="0", spread="0")

    with pytest.raises(StrongLeaderPullbackFeatureError, match="non-positive ATR"):
        calculate_strong_leader_pullback_features(
            member_ids=frozenset((ALPHA_ID,)),
            benchmark_instrument_id=SPY_ID,
            series_by_instrument={ALPHA_ID: flat, SPY_ID: flat},
        )
