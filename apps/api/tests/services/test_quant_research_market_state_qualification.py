from __future__ import annotations

from datetime import date
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_market_state_qualification import (
    QuantResearchMarketStateQualificationStatus,
    QuantResearchMarketStateQualificationReportV1,
    QuantResearchMarketStateBenchmarkIdentityV1,
    QuantResearchMarketStateSessionV1,
    market_state_population_fingerprint,
    qualification_fingerprint,
)
from tip_api.contracts.analytics.v1.quant_research_market_state_vector import (
    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
    QuantResearchMarketStateAvailability,
    QuantResearchMarketStateMetricValueV1,
    market_state_metric_definition_fingerprint,
)
from tip_api.services.quant_research_market_state_qualification import (
    build_quant_research_market_state_qualification_v1,
)
from tip_api.services.market_calendar import ExchangeCalendar


def _sessions():
    sessions = ExchangeCalendar().sessions_in_range(
        date(2025, 6, 23),
        date(2026, 8, 12),
    )
    return tuple(
        QuantResearchMarketStateSessionV1(
            as_of_session=session,
            benchmark_identities=tuple(
                QuantResearchMarketStateBenchmarkIdentityV1(
                    ticker=ticker,
                    instrument_id=UUID(int=position + 1),
                )
                for position, ticker in enumerate(("SPY", "QQQ", "IWM", "DIA"))
            ),
            membership_logical_fingerprint=f"{index + 700:064x}",
            membership_manifest_sha256=f"{index + 1:064x}",
            declared_member_ids_fingerprint=f"{index + 288:064x}",
            declared_member_count=600,
            complete_member_count=600,
            metrics=tuple(
                QuantResearchMarketStateMetricValueV1(
                    metric_id=metric_id,
                    definition_fingerprint=(
                        market_state_metric_definition_fingerprint(metric_id)
                    ),
                    availability=QuantResearchMarketStateAvailability.AVAILABLE,
                    value=f"{(index % 20) / 10000:.10f}",
                    actual_observations=(
                        600
                        if position >= 6
                        else (20 if position == 1 else 21)
                    ),
                    expected_observations=(
                        600
                        if position >= 6
                        else (20 if position == 1 else 21)
                    ),
                    coverage_ratio="1.0000000000",
                )
                for position, metric_id in enumerate(
                    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER
                )
            ),
        )
        for index, session in enumerate(sessions)
    )


def test_market_state_qualification_builds_ready_outcome_blind_artifact() -> None:
    sessions = _sessions()
    report = build_quant_research_market_state_qualification_v1(
        source_revision="a" * 40,
        source_eod_fingerprint="1" * 64,
        source_membership_fingerprint="2" * 64,
        source_action_fingerprint="3" * 64,
        source_adjustment_fingerprint="4" * 64,
        source_census_fingerprint="5" * 64,
        source_population_fingerprint=market_state_population_fingerprint(sessions),
        calculation_code_sha256="8" * 64,
        sessions=sessions,
        limitation_codes=(
            "close_only_price_state_not_total_return",
            "daily_bars_do_not_observe_intraday_state",
            "historical_classification_unavailable",
            "reconstructed_membership_not_as_operated",
        ),
    )

    assert report.status is (
        QuantResearchMarketStateQualificationStatus.READY_FOR_CAMPAIGN_PROTOCOL_DESIGN
    )
    assert report.artifact.record_count == 287
    assert report.development_outcome_read_count == 0
    assert all(item.available_session_count == 287 for item in report.coverage)
    assert all(item.distinct_value_count == 20 for item in report.distributions)
    assert all(item.median_crossing_count >= 4 for item in report.temporal_diagnostics)
    assert len(report.pair_correlations) == 45


def test_market_state_qualification_rejects_chronology_or_source_tamper() -> None:
    sessions = _sessions()
    report = build_quant_research_market_state_qualification_v1(
        source_revision="a" * 40,
        source_eod_fingerprint="1" * 64,
        source_membership_fingerprint="2" * 64,
        source_action_fingerprint="3" * 64,
        source_adjustment_fingerprint="4" * 64,
        source_census_fingerprint="5" * 64,
        source_population_fingerprint=market_state_population_fingerprint(sessions),
        calculation_code_sha256="8" * 64,
        sessions=sessions,
        limitation_codes=(
            "close_only_price_state_not_total_return",
            "daily_bars_do_not_observe_intraday_state",
            "historical_classification_unavailable",
            "reconstructed_membership_not_as_operated",
        ),
    )
    payload = report.model_dump(mode="python")

    changed = deepcopy(payload)
    changed["sessions"][0]["as_of_session"] = date(2025, 6, 22)
    changed["logical_fingerprint"] = qualification_fingerprint(changed)
    with pytest.raises(ValidationError):
        QuantResearchMarketStateQualificationReportV1.model_validate(changed)

    changed = deepcopy(payload)
    changed["source_eod_fingerprint"] = "f" * 64
    changed["logical_fingerprint"] = qualification_fingerprint(changed)
    with pytest.raises(ValidationError):
        QuantResearchMarketStateQualificationReportV1.model_validate(changed)
