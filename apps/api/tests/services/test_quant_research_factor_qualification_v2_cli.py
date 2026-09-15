from __future__ import annotations

from uuid import UUID

import numpy as np

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
)
from tip_api.services.quant_research_factor_matrix_v2 import (
    QuantResearchFactorMatrixV2,
)
from tip_api.services.quant_research_factor_qualification_v2_cli import (
    _all_unavailable_payload,
    _merge_matrix_with_quarantines,
)


def test_v2_cli_quarantines_only_affected_stable_id() -> None:
    first = UUID("11111111-1111-4111-8111-111111111111")
    second = UUID("22222222-2222-4222-8222-222222222222")
    matrix = QuantResearchFactorMatrixV2(
        factor_values={
            factor_id: np.asarray([float(index + 1)])
            for index, factor_id in enumerate(QUANT_RESEARCH_FACTOR_V2_ORDER)
        },
        reason_codes={
            factor_id: ((),) for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
        },
        instrument_count=1,
    )

    values, reasons = _merge_matrix_with_quarantines(
        member_ids=(first, second),
        valid_ids=(second,),
        invalid_reasons={first: ("instrument_eod_unavailable",)},
        matrix=matrix,
    )

    for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
        assert np.isnan(values[factor_id][0])
        assert np.isfinite(values[factor_id][1])
        assert reasons[factor_id][0] == ("instrument_eod_unavailable",)
        assert reasons[factor_id][1] == ()


def test_v2_cli_benchmark_failure_closes_complete_session() -> None:
    values, reasons = _all_unavailable_payload(
        member_count=2,
        reasons=("benchmark_eod_unavailable",),
    )

    for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER:
        assert np.isnan(values[factor_id]).all()
        assert reasons[factor_id] == (
            ("benchmark_eod_unavailable",),
            ("benchmark_eod_unavailable",),
        )
