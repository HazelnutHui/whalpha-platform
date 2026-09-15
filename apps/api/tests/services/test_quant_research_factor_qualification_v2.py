from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
)
from tip_api.services.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationAccumulatorV2,
    QuantResearchFactorQualificationV2Error,
    _average_ranks,
    _pearson,
)


def test_average_ranks_are_stable_and_tie_aware() -> None:
    values = np.asarray([3.0, 1.0, 1.0, 2.0])
    assert _average_ranks(values).tolist() == [4.0, 1.5, 1.5, 3.0]


def test_rank_pearson_detects_exact_inverse_order() -> None:
    left = _average_ranks(np.asarray([1.0, 2.0, 3.0, 4.0]))
    right = _average_ranks(np.asarray([4.0, 3.0, 2.0, 1.0]))
    assert _pearson(left, right) == pytest.approx(-1.0)


def test_accumulator_rejects_unordered_stable_ids() -> None:
    accumulator = QuantResearchFactorQualificationAccumulatorV2(
        chronological_plan_fingerprint="1" * 64,
        source_population_fingerprint="2" * 64,
        source_eod_fingerprint="3" * 64,
        source_membership_fingerprint="4" * 64,
        source_action_fingerprint="5" * 64,
        source_adjustment_fingerprint="6" * 64,
        calculation_code_sha256="7" * 64,
        diagnostic_code_sha256="8" * 64,
        first_source_session=date(2025, 1, 1),
        limitation_codes=("test_limitation",),
    )
    values = {
        factor_id: np.asarray([1.0, 2.0])
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
    }
    reasons = {
        factor_id: ((), ()) for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
    }

    with pytest.raises(
        QuantResearchFactorQualificationV2Error,
        match="stable-ID ordered",
    ):
        accumulator.add_session(
            as_of_session=date(2026, 1, 1) + timedelta(days=1),
            instrument_ids=("b", "a"),
            factor_values=values,
            reason_codes=reasons,
        )
