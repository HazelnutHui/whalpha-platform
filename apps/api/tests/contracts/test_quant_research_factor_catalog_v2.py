from __future__ import annotations

from copy import deepcopy
from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_discovery_trial_ledger import (
    quant_research_discovery_trial_ledger_v1,
)
from tip_api.contracts.analytics.v1.quant_research_factor_catalog_v2 import (
    QUANT_RESEARCH_FACTOR_V2_ORDER,
    QuantResearchFactorCatalogV2,
    QuantResearchFactorAvailabilityV2,
    QuantResearchFactorValueV2,
    QuantResearchFactorRoleV2,
    build_quant_research_factor_observation_v2,
    factor_catalog_v2_fingerprint,
    factor_definition_v2_fingerprint,
    quant_research_factor_catalog_v2,
)


def test_v2_catalog_is_finite_deterministic_adaptive_and_outcome_blind() -> None:
    first = quant_research_factor_catalog_v2()
    second = quant_research_factor_catalog_v2()

    assert first == second
    assert tuple(item.factor_id for item in first.definitions) == QUANT_RESEARCH_FACTOR_V2_ORDER
    assert len(first.definitions) == 8
    assert first.candidate_alpha_count == 4
    assert first.setup_conditioner_count == 1
    assert first.applicability_input_count == 1
    assert first.risk_guard_count == 2
    assert first.prior_discovery_ledger_fingerprint == (
        quant_research_discovery_trial_ledger_v1().logical_fingerprint
    )
    assert first.adaptive_to_consumed_development_evidence is True
    assert first.contains_forward_outcomes is False
    assert first.development_outcome_read_authorized is False
    assert first.validation_authorized is False
    assert first.holdout_access_authorized is False
    assert first.logical_fingerprint == factor_catalog_v2_fingerprint(first)


def test_v2_catalog_roles_and_consumed_trial_links_are_explicit() -> None:
    catalog = quant_research_factor_catalog_v2()
    assert sum(
        item.role is QuantResearchFactorRoleV2.CANDIDATE_ALPHA
        for item in catalog.definitions
    ) == 4
    linked = {
        item.factor_id: item.consumed_trial_links
        for item in catalog.definitions
        if item.consumed_trial_links
    }
    assert "medium_term_relative_momentum_126s_skip5" in linked
    assert "single_index_residual_volatility_60s" in linked


def test_v2_catalog_rejects_formula_drift_even_with_recomputed_outer_hash() -> None:
    payload = quant_research_factor_catalog_v2().model_dump(mode="python")
    definitions = deepcopy(payload["definitions"])
    definitions[0]["exact_formula"] = "post_hoc_formula"
    definitions[0]["logical_fingerprint"] = "0" * 64
    payload["definitions"] = definitions
    payload["logical_fingerprint"] = factor_catalog_v2_fingerprint(payload)

    with pytest.raises(ValidationError, match="immutable V2 catalog"):
        QuantResearchFactorCatalogV2.model_validate(payload)


def test_v2_observation_binds_stable_id_source_window_and_zero_authority() -> None:
    catalog = quant_research_factor_catalog_v2()
    values = tuple(
        QuantResearchFactorValueV2(
            factor_id=factor_id,
            factor_definition_fingerprint=factor_definition_v2_fingerprint(
                factor_id
            ),
            availability=QuantResearchFactorAvailabilityV2.AVAILABLE,
            value="0.0000000000",
        )
        for factor_id in QUANT_RESEARCH_FACTOR_V2_ORDER
    )
    observation = build_quant_research_factor_observation_v2(
        catalog_fingerprint=catalog.logical_fingerprint,
        as_of_session=date(2026, 1, 7),
        instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
        display_ticker="TEST",
        source_min_session=date(2025, 7, 7),
        source_max_session=date(2026, 1, 7),
        source_eod_fingerprint="1" * 64,
        source_adjustment_fingerprint="2" * 64,
        factor_values=values,
    )

    assert observation.instrument_id == UUID(
        "11111111-1111-4111-8111-111111111111"
    )
    assert observation.factor_screening_authorized is False
    assert observation.model_construction_authorized is False
