"""Pure outcome-free nuisance-control builder for the V2 factor screen."""

from __future__ import annotations

from datetime import date

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QuantResearchFactorAvailability,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_result_v2 import (
    QuantResearchFactorScreeningControlV2,
    build_factor_screening_control_v2,
)
from tip_api.contracts.analytics.v1.quant_research_factor_screening_v2 import (
    QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID,
    quant_research_factor_screening_protocol_v2,
)
from tip_api.services.quant_research_factor_values import (
    QuantResearchFactorBar,
    calculate_quant_research_factor_values,
)


class QuantResearchFactorScreeningControlV2Error(ValueError):
    """Raised when the registered V1 nuisance control cannot be reproduced."""


def build_quant_research_factor_screening_control_v2(
    *,
    observation_fingerprint: str,
    signal_session: date,
    instrument_id,
    source_min_session: date,
    source_eod_fingerprint: str,
    source_action_fingerprint: str,
    source_adjustment_fingerprint: str,
    stock_series: tuple[QuantResearchFactorBar, ...] | None = None,
    benchmark_series: tuple[QuantResearchFactorBar, ...] | None = None,
    unavailable_reason_codes: tuple[str, ...] = (),
) -> QuantResearchFactorScreeningControlV2:
    """Build the exact 20-session relative-return control without outcomes."""

    protocol = quant_research_factor_screening_protocol_v2()
    common = {
        "protocol_fingerprint": protocol.logical_fingerprint,
        "observation_fingerprint": observation_fingerprint,
        "signal_session": signal_session,
        "instrument_id": instrument_id,
        "factor_definition_fingerprint": (
            protocol.incremental_baseline_definition_fingerprint
        ),
        "source_min_session": source_min_session,
        "source_max_session": signal_session,
        "source_eod_fingerprint": source_eod_fingerprint,
        "source_action_fingerprint": source_action_fingerprint,
        "source_adjustment_fingerprint": source_adjustment_fingerprint,
    }
    reasons = tuple(sorted(set(unavailable_reason_codes)))
    if reasons:
        if stock_series is not None or benchmark_series is not None:
            raise QuantResearchFactorScreeningControlV2Error(
                "unavailable V2 control cannot carry price series"
            )
        return build_factor_screening_control_v2(
            **common,
            available=False,
            reason_codes=reasons,
        )
    if stock_series is None or benchmark_series is None:
        raise QuantResearchFactorScreeningControlV2Error(
            "available V2 control requires stock and benchmark series"
        )
    if (
        len(stock_series) != 21
        or len(benchmark_series) != 21
        or tuple(item.session for item in stock_series)
        != tuple(item.session for item in benchmark_series)
        or stock_series[0].session != source_min_session
        or stock_series[-1].session != signal_session
    ):
        raise QuantResearchFactorScreeningControlV2Error(
            "V2 control source window differs"
        )
    values = calculate_quant_research_factor_values(
        stock_series=stock_series,
        benchmark_series=benchmark_series,
    )
    control = next(
        (
            item
            for item in values
            if item.factor_id == QUANT_RESEARCH_FACTOR_SCREENING_V2_BASELINE_FACTOR_ID
        ),
        None,
    )
    if control is None:
        raise QuantResearchFactorScreeningControlV2Error(
            "registered V2 nuisance control is absent"
        )
    if control.availability is not QuantResearchFactorAvailability.AVAILABLE:
        return build_factor_screening_control_v2(
            **common,
            available=False,
            reason_codes=tuple(
                sorted(f"control_{reason}" for reason in control.reason_codes)
            ),
        )
    return build_factor_screening_control_v2(
        **common,
        available=True,
        value=control.value,
    )
