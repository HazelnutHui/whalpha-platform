from __future__ import annotations

from datetime import date
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_factor_screening_result_v2 import (
    QuantResearchFactorScreeningControlV2,
    build_factor_screening_control_v2,
    factor_screening_v2_result_fingerprint,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    quant_research_factor_screening_protocol_v2,
)


def test_v2_incremental_control_is_factor_bound_and_outcome_free() -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    control = build_factor_screening_control_v2(
        protocol_fingerprint=protocol.logical_fingerprint,
        observation_fingerprint="1" * 64,
        signal_session=date(2025, 8, 1),
        instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
        factor_definition_fingerprint=(
            protocol.incremental_baseline_definition_fingerprint
        ),
        available=True,
        value="0.0123456789",
        source_min_session=date(2025, 7, 3),
        source_max_session=date(2025, 8, 1),
        source_eod_fingerprint="2" * 64,
        source_action_fingerprint="3" * 64,
        source_adjustment_fingerprint="4" * 64,
    )

    assert control.factor_id == "relative_return_spy_20s"
    assert control.contains_forward_outcomes is False
    assert control.logical_fingerprint == factor_screening_v2_result_fingerprint(
        control
    )


def test_v2_incremental_control_rejects_silent_missing_value() -> None:
    protocol = quant_research_factor_screening_protocol_v2()
    payload = build_factor_screening_control_v2(
        protocol_fingerprint=protocol.logical_fingerprint,
        observation_fingerprint="1" * 64,
        signal_session=date(2025, 8, 1),
        instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
        factor_definition_fingerprint=(
            protocol.incremental_baseline_definition_fingerprint
        ),
        available=False,
        reason_codes=("control_source_unavailable",),
        source_min_session=date(2025, 7, 3),
        source_max_session=date(2025, 8, 1),
        source_eod_fingerprint="2" * 64,
        source_action_fingerprint="3" * 64,
        source_adjustment_fingerprint="4" * 64,
    ).model_dump(mode="python")
    changed = deepcopy(payload)
    changed["reason_codes"] = ()
    changed["logical_fingerprint"] = factor_screening_v2_result_fingerprint(changed)

    with pytest.raises(ValidationError, match="control differs"):
        QuantResearchFactorScreeningControlV2.model_validate(changed)
