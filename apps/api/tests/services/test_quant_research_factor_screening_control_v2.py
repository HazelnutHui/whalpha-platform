from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from tip_api.services.quant_research_factor_screening_control_v2 import (
    QuantResearchFactorScreeningControlV2Error,
    build_quant_research_factor_screening_control_v2,
)
from tip_api.services.quant_research_factor_values import QuantResearchFactorBar


def _series(*, excess_step: Decimal) -> tuple[QuantResearchFactorBar, ...]:
    start = date(2025, 7, 1)
    return tuple(
        QuantResearchFactorBar(
            session=start + timedelta(days=index),
            open=Decimal("100") + excess_step * index,
            high=Decimal("101") + excess_step * index,
            low=Decimal("99") + excess_step * index,
            close=Decimal("100") + excess_step * index,
            volume=Decimal("1000000"),
        )
        for index in range(21)
    )


def test_v2_control_reuses_registered_v1_relative_return_without_outcomes() -> None:
    stock = _series(excess_step=Decimal("1"))
    benchmark = _series(excess_step=Decimal("0.5"))
    control = build_quant_research_factor_screening_control_v2(
        observation_fingerprint="1" * 64,
        signal_session=stock[-1].session,
        instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
        source_min_session=stock[0].session,
        source_eod_fingerprint="2" * 64,
        source_action_fingerprint="3" * 64,
        source_adjustment_fingerprint="4" * 64,
        stock_series=stock,
        benchmark_series=benchmark,
    )

    assert control.available is True
    assert Decimal(control.value) > 0
    assert control.contains_forward_outcomes is False


def test_v2_control_rejects_series_attached_to_an_unavailable_record() -> None:
    stock = _series(excess_step=Decimal("1"))
    with pytest.raises(
        QuantResearchFactorScreeningControlV2Error,
        match="cannot carry price series",
    ):
        build_quant_research_factor_screening_control_v2(
            observation_fingerprint="1" * 64,
            signal_session=stock[-1].session,
            instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
            source_min_session=stock[0].session,
            source_eod_fingerprint="2" * 64,
            source_action_fingerprint="3" * 64,
            source_adjustment_fingerprint="4" * 64,
            stock_series=stock,
            unavailable_reason_codes=("control_source_unavailable",),
        )
