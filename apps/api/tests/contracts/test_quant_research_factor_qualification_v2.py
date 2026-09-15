from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    quant_research_factor_catalog_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_qualification_v2 import (
    QuantResearchFactorQualificationProtocolV2,
    factor_qualification_v2_fingerprint,
    quant_research_factor_qualification_protocol_v2,
)


def test_v2_qualification_protocol_is_frozen_outcome_blind_and_local() -> None:
    first = quant_research_factor_qualification_protocol_v2()
    second = quant_research_factor_qualification_protocol_v2()

    assert first == second
    assert first.catalog_fingerprint == quant_research_factor_catalog_v2().logical_fingerprint
    assert first.expected_signal_session_count == 287
    assert first.expected_signal_path_count == 437402
    assert first.source_window_sessions == 127
    assert first.instrument_failure_rule == (
        "quarantine_only_affected_stable_instrument_id"
    )
    assert first.real_factor_values_not_read_before_protocol is True
    assert first.development_outcome_read_authorized is False
    assert first.validation_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == factor_qualification_v2_fingerprint(first)


def test_v2_qualification_protocol_rejects_post_registration_gate_drift() -> None:
    payload = quant_research_factor_qualification_protocol_v2().model_dump(
        mode="python"
    )
    payload["minimum_factor_availability_rate"] = "0.8000000000"
    payload["logical_fingerprint"] = factor_qualification_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchFactorQualificationProtocolV2.model_validate(payload)


def test_v2_qualification_protocol_rejects_instrument_quarantine_drift() -> None:
    payload = quant_research_factor_qualification_protocol_v2().model_dump(
        mode="python"
    )
    payload = deepcopy(payload)
    payload["instrument_failure_rule"] = "exclude_complete_signal_session"
    payload["logical_fingerprint"] = factor_qualification_v2_fingerprint(payload)

    with pytest.raises(ValidationError):
        QuantResearchFactorQualificationProtocolV2.model_validate(payload)
