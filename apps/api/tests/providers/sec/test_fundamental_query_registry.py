from __future__ import annotations

import pytest
from pydantic import ValidationError

from tip_api.providers.sec.fundamental_query_registry import (
    SecFundamentalQueryRegistryV1,
    build_first_sec_fundamental_query_registry,
)


def test_first_registry_is_stable_and_default_deny() -> None:
    registry = build_first_sec_fundamental_query_registry()

    assert registry.query_order == (
        "assets_latest_reported_v1",
        "net_income_loss_fiscal_year_v1",
        "operating_income_loss_fiscal_year_v1",
        "stockholders_equity_latest_reported_v1",
    )
    assert all(query.economic_grain == "issuer" for query in registry.queries)
    assert all(not query.concept_fallback_authorized for query in registry.queries)
    assert not registry.daily_cartesian_panel_authorized
    assert not registry.security_feature_materialization_authorized
    assert not registry.strategy_outcome_access_authorized
    assert not registry.research_performance_authorized
    assert not registry.candidate_authorized
    assert not registry.production_authorized
    assert len(registry.logical_fingerprint) == 64


def test_first_registry_separates_instant_and_annual_duration_semantics() -> None:
    registry = build_first_sec_fundamental_query_registry()
    by_id = {query.query_id: query for query in registry.queries}

    assets = by_id["assets_latest_reported_v1"]
    assert assets.period_shape == "instant"
    assert assets.start_date_rule == "must_be_null"
    assert assets.minimum_duration_days is None
    assert assets.maximum_duration_days is None

    net_income = by_id["net_income_loss_fiscal_year_v1"]
    assert net_income.period_shape == "duration"
    assert net_income.start_date_rule == "must_be_present"
    assert net_income.minimum_duration_days == 330
    assert net_income.maximum_duration_days == 400
    assert net_income.form_period_rules[0].forms == ("10-K", "10-K/A")
    assert net_income.form_period_rules[0].fiscal_periods == ("FY",)


def test_registry_rejects_fingerprint_or_membership_drift() -> None:
    registry = build_first_sec_fundamental_query_registry()
    values = registry.model_dump(mode="json")
    values["logical_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="fingerprint differs"):
        SecFundamentalQueryRegistryV1.model_validate(values)

    values = registry.model_dump(mode="json")
    values["queries"] = values["queries"][:-1]
    values["query_order"] = values["query_order"][:-1]
    with pytest.raises(ValidationError, match="membership differs"):
        SecFundamentalQueryRegistryV1.model_validate(values)
