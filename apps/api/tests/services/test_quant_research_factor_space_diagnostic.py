from __future__ import annotations

import numpy as np
import pytest

from tip_api.contracts.analytics.v1.quant_research_factor_space_diagnostic import (
    FactorSpacePanelKind,
    FactorSpaceVifStatus,
)
from tip_api.services.quant_research_factor_space_diagnostic import (
    FactorSpaceDiagnosticError,
    build_factor_space_panel,
)


def test_cross_section_reports_redundancy_without_filling_missing_values() -> None:
    rng = np.random.default_rng(7)
    groups = tuple(f"s{index // 12}" for index in range(120))
    base = rng.normal(size=120)
    values = np.column_stack(
        (base, 2.0 * base + rng.normal(scale=0.02, size=120), rng.normal(size=120))
    )
    values[3, 2] = np.nan

    report = build_factor_space_panel(
        panel=FactorSpacePanelKind.SECURITY_CROSS_SECTION,
        input_ids=("momentum_a", "momentum_b", "volatility"),
        economic_families=("momentum", "momentum", "risk"),
        values=values,
        group_keys=groups,
    )

    assert report.row_count == 120
    assert report.complete_case_count == 119
    assert report.scales[2].available_count == 119
    assert len(report.cluster_merges) == 2
    assert report.cluster_merges[0].merged_members == ("momentum_a", "momentum_b")
    assert report.components[0].loadings[0].loading[0] != "-"


def test_market_state_uses_mad_and_is_deterministic() -> None:
    x = np.arange(1.0, 31.0)
    values = np.column_stack((x, np.sqrt(x), (-1.0) ** x))
    first = build_factor_space_panel(
        panel=FactorSpacePanelKind.MARKET_STATE_TIME_SERIES,
        input_ids=("trend", "breadth", "risk"),
        economic_families=("market", "market", "risk"),
        values=values,
    )
    second = build_factor_space_panel(
        panel=FactorSpacePanelKind.MARKET_STATE_TIME_SERIES,
        input_ids=("trend", "breadth", "risk"),
        economic_families=("market", "market", "risk"),
        values=values,
    )

    assert first == second
    assert all(item.method == "development_median_mad" for item in first.scales)
    assert first.dimension.components_95 <= 3


def test_singular_panel_reports_no_vif_or_condition_number() -> None:
    x = np.arange(1.0, 41.0)
    values = np.column_stack((x, x, np.sin(x)))
    report = build_factor_space_panel(
        panel=FactorSpacePanelKind.MARKET_STATE_TIME_SERIES,
        input_ids=("same_a", "same_b", "different"),
        economic_families=("same", "same", "other"),
        values=values,
    )

    assert report.dimension.condition_status == "singular"
    assert report.dimension.condition_number is None
    assert all(item.status is FactorSpaceVifStatus.SINGULAR for item in report.vifs)


def test_cross_section_requires_groups_and_never_accepts_infinity() -> None:
    values = np.asarray([[1.0, 2.0], [2.0, np.inf], [3.0, 4.0]])
    with pytest.raises(FactorSpaceDiagnosticError):
        build_factor_space_panel(
            panel=FactorSpacePanelKind.SECURITY_CROSS_SECTION,
            input_ids=("a", "b"),
            economic_families=("x", "y"),
            values=values,
        )
