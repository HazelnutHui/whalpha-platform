from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from tip_api.contracts.analytics.v1.quant_research_factor_screening_result import (
    QuantResearchFactorScreeningLabelState,
)
from tip_api.services.quant_research_factor_screening_labels_v2 import (
    build_quant_research_factor_screening_label_v2,
)
from tip_api.services.strong_leader_pullback_development_labels import (
    ReconstructedOutcomeBarV1,
)


def test_v2_screening_label_is_factor_bound_and_not_an_option_return() -> None:
    session = date(2026, 1, 5)
    path = (date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 8))
    instrument_bars = tuple(
        ReconstructedOutcomeBarV1(
            session=item,
            open=Decimal("10"),
            high=Decimal("12"),
            low=Decimal("9"),
            close=Decimal("11"),
        )
        for item in path
    )
    benchmark_bars = tuple(
        ReconstructedOutcomeBarV1(
            session=item,
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
        )
        for item in path
    )

    label = build_quant_research_factor_screening_label_v2(
        observation_fingerprint="1" * 64,
        signal_session=session,
        instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
        display_ticker="TEST",
        expected_path_sessions=path,
        split_basis_session=date(2026, 1, 8),
        instrument_bars=instrument_bars,
        benchmark_bars=benchmark_bars,
        source_eod_fingerprint="2" * 64,
        source_action_fingerprint="4" * 64,
        source_adjustment_fingerprint="3" * 64,
    )

    assert label.state is QuantResearchFactorScreeningLabelState.OBSERVED_EOD_EXACT
    assert label.underlying_price_return_lower == "0.1000000000"
    assert label.maximum_adverse_excursion == "-0.1000000000"
    assert label.prior_strategy_outcome_reused is False
    assert label.underlying_stock_result_not_option_return is True
