from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_query_registry import (
    SecCashQualityQueryRegistryV1,
    cash_quality_query_registry_fingerprint,
    quant_research_sec_cash_quality_query_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_source_plan import (
    quant_research_sec_cash_quality_source_plan_v1,
)
from tip_api.providers.sec.fundamental_query_registry import (
    build_first_sec_fundamental_query_registry,
)


def test_cash_quality_registry_is_separate_and_bound_to_plan_and_base() -> None:
    registry = quant_research_sec_cash_quality_query_registry_v1()
    plan = quant_research_sec_cash_quality_source_plan_v1()
    base = build_first_sec_fundamental_query_registry()

    assert registry.lifecycle_state == "registered_query_contract_plan_only"
    assert registry.source_plan_fingerprint == plan.logical_fingerprint
    assert registry.immutable_base_registry_fingerprint == base.logical_fingerprint
    assert base.logical_fingerprint == (
        "ffb5e1f2be190e1f7ef7a6cde9d4b42778cf194d05a01d6cb5131037d0500ea3"
    )
    assert registry.logical_fingerprint == cash_quality_query_registry_fingerprint(
        registry
    )


def test_cash_quality_registry_freezes_exact_source_queries() -> None:
    registry = quant_research_sec_cash_quality_query_registry_v1()
    by_id = {item.query_id: item for item in registry.queries}

    assert registry.query_order == (
        "assets_fiscal_boundary_v1",
        "net_income_loss_fiscal_ytd_and_year_v1",
        "operating_cash_flow_fiscal_ytd_and_year_v1",
    )
    assert by_id["assets_fiscal_boundary_v1"].period_shape == "instant"
    assert by_id["assets_fiscal_boundary_v1"].concept_name == "Assets"
    for query_id, concept in (
        ("net_income_loss_fiscal_ytd_and_year_v1", "NetIncomeLoss"),
        (
            "operating_cash_flow_fiscal_ytd_and_year_v1",
            "NetCashProvidedByUsedInOperatingActivities",
        ),
    ):
        query = by_id[query_id]
        assert query.concept_name == concept
        assert query.period_shape == "duration"
        assert query.start_date_rule == "must_equal_fiscal_year_origin"
        assert tuple(item.fiscal_period for item in query.fiscal_basis_rules) == (
            "FY",
            "Q1",
            "Q2",
            "Q3",
        )
        assert tuple(item.required_basis for item in query.fiscal_basis_rules) == (
            "fiscal_year_duration",
            "fiscal_ytd_duration",
            "fiscal_ytd_duration",
            "fiscal_ytd_duration",
        )
    assert all(
        tuple(rule.forms for rule in query.form_period_rules)
        == (("10-K", "10-K/A"), ("10-Q", "10-Q/A"))
        for query in registry.queries
    )
    assert all(
        tuple(rule.fiscal_periods for rule in query.form_period_rules)
        == (("FY",), ("Q1", "Q2", "Q3"))
        for query in registry.queries
    )


def test_cash_quality_registry_is_default_deny() -> None:
    registry = quant_research_sec_cash_quality_query_registry_v1()

    assert registry.source_execution_authorized is False
    assert registry.external_request_authorized is False
    assert registry.occurrence_selection_authorized is False
    assert registry.ttm_derivation_authorized is False
    assert registry.feature_materialization_authorized is False
    assert registry.outcome_access_authorized is False
    assert registry.validation_access_authorized is False
    assert registry.holdout_access_authorized is False
    assert registry.trial_authorized is False
    assert registry.candidate_authorized is False
    assert registry.canonical_write_authorized is False
    assert registry.production_authorized is False


def test_cash_quality_registry_rejects_query_binding_and_authority_drift() -> None:
    source = quant_research_sec_cash_quality_query_registry_v1()

    query_drift = source.model_dump(mode="python")
    queries = list(deepcopy(query_drift["queries"]))
    queries[0]["concept_name"] = "StockholdersEquity"
    query_drift["queries"] = queries
    query_drift["logical_fingerprint"] = cash_quality_query_registry_fingerprint(
        query_drift
    )
    with pytest.raises(ValidationError):
        SecCashQualityQueryRegistryV1.model_validate(query_drift)

    binding_drift = source.model_dump(mode="python")
    binding_drift["immutable_base_registry_fingerprint"] = "f" * 64
    binding_drift["logical_fingerprint"] = cash_quality_query_registry_fingerprint(
        binding_drift
    )
    with pytest.raises(ValidationError, match="query registry differs"):
        SecCashQualityQueryRegistryV1.model_validate(binding_drift)

    authority_drift = source.model_dump(mode="python")
    authority_drift["source_execution_authorized"] = True
    with pytest.raises(ValidationError, match="Input should be False"):
        SecCashQualityQueryRegistryV1.model_validate(authority_drift)
