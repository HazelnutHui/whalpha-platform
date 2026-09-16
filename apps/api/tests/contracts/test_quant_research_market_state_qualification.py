from __future__ import annotations

from copy import deepcopy
import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    QuantResearchMarketStateQualificationProtocolV1,
    qualification_fingerprint,
    quant_research_market_state_qualification_protocol_v1,
)


def test_market_state_qualification_protocol_keeps_outcomes_closed() -> None:
    value = quant_research_market_state_qualification_protocol_v1()

    assert value.expected_signal_session_count == 287
    assert value.thresholds_select_data_quality_not_market_states is True
    assert value.state_thresholds_selected is False
    assert value.interactions_registered is False
    assert value.campaign_three_registered is False
    assert value.development_outcome_read_authorized is False


def test_market_state_qualification_protocol_rejects_authority_tamper() -> None:
    payload = quant_research_market_state_qualification_protocol_v1().model_dump(
        mode="python"
    )
    changed = deepcopy(payload)
    changed["development_outcome_read_authorized"] = True
    changed["logical_fingerprint"] = qualification_fingerprint(changed)

    with pytest.raises(ValidationError):
        QuantResearchMarketStateQualificationProtocolV1.model_validate(changed)
