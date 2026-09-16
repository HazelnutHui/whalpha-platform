from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from tip_api.services.quant_research_campaign_three_input_qualification import (
    CampaignThreeFactorSessionEvidence,
    CampaignThreeInputQualificationError,
    _same_side_diagnostics,
    _transform_state,
)


def test_factor_session_evidence_reconciles_ties() -> None:
    evidence = CampaignThreeFactorSessionEvidence(
        factor_id="factor",
        as_of_session=date(2026, 1, 2),
        available_instrument_count=100,
        distinct_value_count=90,
        tie_excess_count=10,
    )

    assert evidence.tie_excess_count == 10
    with pytest.raises(CampaignThreeInputQualificationError):
        CampaignThreeFactorSessionEvidence(
            factor_id="factor",
            as_of_session=date(2026, 1, 2),
            available_instrument_count=100,
            distinct_value_count=90,
            tie_excess_count=9,
        )


def test_registered_state_transforms_are_exact() -> None:
    assert _transform_state(Decimal("0.75"), "2*(share-0.5)") == Decimal("0.50")
    assert _transform_state(Decimal("-0.02"), "-1*spy_log_return_20s") == Decimal("0.02")
    assert _transform_state(Decimal("0.12"), "as_defined") == Decimal("0.12")

    with pytest.raises(CampaignThreeInputQualificationError):
        _transform_state(Decimal("1"), "hindsight_quantile")


def test_same_side_diagnostics_count_episodes_and_longest_run() -> None:
    assert _same_side_diagnostics(
        (
            Decimal("1"),
            Decimal("2"),
            Decimal("-1"),
            Decimal("-2"),
            Decimal("-3"),
            Decimal("1"),
        )
    ) == (3, 3)
