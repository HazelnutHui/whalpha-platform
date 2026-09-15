from __future__ import annotations

from copy import deepcopy
from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_factor_catalog import (
    QUANT_RESEARCH_FACTOR_ORDER,
    QuantResearchFactorAvailability,
    QuantResearchFactorCatalogV1,
    QuantResearchFactorValueV1,
    build_quant_research_factor_observation,
    factor_catalog_fingerprint,
    factor_definition_fingerprint,
    quant_research_factor_catalog_v1,
)


def test_catalog_is_deterministic_exact_and_outcome_blind() -> None:
    first = quant_research_factor_catalog_v1()
    second = quant_research_factor_catalog_v1()

    assert first == second
    assert tuple(item.factor_id for item in first.definitions) == QUANT_RESEARCH_FACTOR_ORDER
    assert len(first.definitions) == 12
    assert first.family_count == 5
    assert first.candidate_alpha_count == 5
    assert first.setup_conditioner_count == 4
    assert first.risk_guard_count == 3
    assert first.contains_forward_outcomes is False
    assert first.factor_screening_authorized is False
    assert first.logical_fingerprint == factor_catalog_fingerprint(first)


def test_catalog_rejects_formula_drift_even_if_fingerprint_is_recomputed() -> None:
    payload = quant_research_factor_catalog_v1().model_dump(mode="json")
    definitions = deepcopy(payload["definitions"])
    definitions[0]["exact_formula"] = "close[t] / close[t-20]"
    definitions[0]["logical_fingerprint"] = "0" * 64
    payload["definitions"] = definitions
    payload["logical_fingerprint"] = factor_catalog_fingerprint(payload)

    with pytest.raises(ValidationError, match="immutable V1 catalog"):
        QuantResearchFactorCatalogV1.model_validate(payload)


def test_factor_value_requires_exact_definition_identity_and_missingness_shape() -> None:
    factor_id = QUANT_RESEARCH_FACTOR_ORDER[0]
    available = QuantResearchFactorValueV1(
        factor_id=factor_id,
        factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
        availability=QuantResearchFactorAvailability.AVAILABLE,
        value="0.1234567890",
    )
    assert available.value == "0.1234567890"

    with pytest.raises(ValidationError, match="reasons and no value"):
        QuantResearchFactorValueV1(
            factor_id=factor_id,
            factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
            availability=QuantResearchFactorAvailability.UNAVAILABLE,
        )


def test_observation_is_fingerprinted_and_contains_no_outcome_authority() -> None:
    catalog = quant_research_factor_catalog_v1()
    values = tuple(
        QuantResearchFactorValueV1(
            factor_id=factor_id,
            factor_definition_fingerprint=factor_definition_fingerprint(factor_id),
            availability=QuantResearchFactorAvailability.AVAILABLE,
            value="0.0000000000",
        )
        for factor_id in QUANT_RESEARCH_FACTOR_ORDER
    )
    observation = build_quant_research_factor_observation(
        catalog_fingerprint=catalog.logical_fingerprint,
        calculation_version=catalog.calculation_version,
        as_of_session=date(2026, 9, 11),
        instrument_id=UUID("11111111-1111-4111-8111-111111111111"),
        display_ticker="TEST",
        membership_tier="reconstructed_latest_vintage_research_only",
        source_max_session=date(2026, 9, 11),
        source_eod_fingerprint="1" * 64,
        source_adjustment_fingerprint="2" * 64,
        factor_values=values,
        contains_forward_outcomes=False,
        factor_screening_authorized=False,
        model_construction_authorized=False,
        candidate_activation_authorized=False,
    )

    assert observation.contains_forward_outcomes is False
    assert observation.factor_screening_authorized is False
    assert observation.logical_fingerprint != "0" * 64
