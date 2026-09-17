from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    ChinaAshareFullPopulationCoverageReportV1,
    CoverageDisposition,
    china_ashare_full_population_coverage_report_v1,
    full_population_coverage_fingerprint,
)


def test_full_population_coverage_is_ordered_bounded_and_closed() -> None:
    report = china_ashare_full_population_coverage_report_v1()

    assert report.partition_count == 109
    assert report.resolved_target_count + report.quarantined_target_count == 5409
    assert report.normalized_bar_count + report.suspended_state_count == report.normalized_state_count
    assert tuple(item.ordinal for item in report.families) == tuple(range(1, 14))
    assert len({item.family_id for item in report.families}) == 13
    assert sum(item.disposition is CoverageDisposition.SOURCE_COMPLETE for item in report.families) == 1
    assert report.historical_coverage_admitted is False
    assert report.research_backtest_authorized is False
    assert report.factor_discovery_authorized is False
    assert all(item.authorizes_backtest is False for item in report.families)
    assert report.logical_fingerprint == full_population_coverage_fingerprint(report)


def test_full_population_coverage_preserves_known_quarantine_and_unknowns() -> None:
    report = china_ashare_full_population_coverage_report_v1()

    assert report.quarantined_target_count == 113
    assert report.price_limit_regime_unknown_count == report.normalized_state_count
    assert report.source_available_at_null_count == report.normalized_state_count
    assert report.terminal_boundary_occurrence_gap_count == 22
    assert report.terminal_boundary_session_gap_count == 23


def test_full_population_coverage_rejects_authority_or_family_drift() -> None:
    source = china_ashare_full_population_coverage_report_v1()
    authority = source.model_dump(mode="python")
    authority["research_backtest_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        ChinaAshareFullPopulationCoverageReportV1.model_validate(authority)

    family = source.model_dump(mode="python")
    families = list(deepcopy(family["families"]))
    families[0]["current_evidence"] = "heuristic identity accepted"
    family["families"] = families
    family["logical_fingerprint"] = full_population_coverage_fingerprint(family)
    with pytest.raises(ValidationError, match="coverage report differs"):
        ChinaAshareFullPopulationCoverageReportV1.model_validate(family)
