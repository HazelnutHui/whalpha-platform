from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from tip_api.contracts.china_ashare.v1.full_population_coverage import (
    ChinaAshareFullPopulationDiagnosticPlanV1,
    ChinaAshareFullPopulationCoverageReportV1,
    CoverageDisposition,
    build_full_population_diagnostic_plan,
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


def test_diagnostic_plan_rejects_partition_or_authority_drift() -> None:
    plan = build_full_population_diagnostic_plan(
        registered_at=datetime(2026, 9, 17, tzinfo=UTC),
        interval_start=date(2021, 9, 16),
        interval_end=date(2026, 9, 16),
        target_session_count=1211,
        target_count=5409,
        population_package_fingerprint="1" * 64,
        source_plan_fingerprint="2" * 64,
        source_completion_fingerprint="3" * 64,
        normalized_run_fingerprint="4" * 64,
        source_partition_manifest_fingerprints=("5" * 64,),
        normalized_partition_manifest_fingerprints=("6" * 64,),
    )
    drifted = plan.model_dump(mode="python")
    drifted["normalized_partition_manifest_fingerprints"] = (
        "6" * 64,
        "7" * 64,
    )
    with pytest.raises(ValidationError, match="partition sets differ"):
        ChinaAshareFullPopulationDiagnosticPlanV1.model_validate(drifted)

    authority = plan.model_dump(mode="python")
    authority["research_backtest_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        ChinaAshareFullPopulationDiagnosticPlanV1.model_validate(authority)
