"""Exact SEC source-query registry for the cash-earnings-quality plan."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.providers.sec.fundamental_query_registry import (
    SecFormPeriodRuleV1,
    build_first_sec_fundamental_query_registry,
)

from .quant_research_sec_cash_earnings_quality_source_plan import (
    quant_research_sec_cash_quality_source_plan_v1,
)


CONTRACT_VERSION = "quant-research-sec-cash-quality-query-registry/1.0"
REGISTRY_ID = "sec-cash-earnings-quality-exact-source-queries-v1"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityFiscalBasisV1(FrozenModel):
    fiscal_period: Literal["FY", "Q1", "Q2", "Q3"]
    required_basis: Literal["fiscal_year_duration", "fiscal_ytd_duration"]


class SecCashQualitySourceQueryV1(FrozenModel):
    query_id: Literal[
        "assets_fiscal_boundary_v1",
        "net_income_loss_fiscal_ytd_and_year_v1",
        "operating_cash_flow_fiscal_ytd_and_year_v1",
    ]
    component_role: Literal[
        "total_assets_boundary",
        "net_income_cumulative",
        "operating_cash_flow_cumulative",
    ]
    economic_grain: Literal["issuer"] = "issuer"
    namespace: Literal["us-gaap"] = "us-gaap"
    concept_name: Literal[
        "Assets",
        "NetIncomeLoss",
        "NetCashProvidedByUsedInOperatingActivities",
    ]
    unit: Literal["USD"] = "USD"
    accepted_value_kinds: tuple[Literal["decimal", "integer"], ...] = (
        "decimal",
        "integer",
    )
    period_shape: Literal["duration", "instant"]
    start_date_rule: Literal[
        "must_be_null",
        "must_equal_fiscal_year_origin",
    ]
    form_period_rules: tuple[SecFormPeriodRuleV1, ...]
    fiscal_basis_rules: tuple[SecCashQualityFiscalBasisV1, ...]
    period_end_rule: Literal["must_equal_reported_fiscal_period_end"] = (
        "must_equal_reported_fiscal_period_end"
    )
    availability_rule: Literal[
        "sec_acceptance_then_first_xnys_open_strictly_after"
    ] = "sec_acceptance_then_first_xnys_open_strictly_after"
    revision_rule: Literal[
        "later_clean_amendment_applies_only_from_its_own_availability"
    ] = "later_clean_amendment_applies_only_from_its_own_availability"
    exact_duplicate_rule: Literal["collapse_identical_within_accession"] = (
        "collapse_identical_within_accession"
    )
    conflict_rule: Literal["quarantine_no_value_selection"] = (
        "quarantine_no_value_selection"
    )
    concept_fallback_authorized: Literal[False] = False
    currency_conversion_authorized: Literal[False] = False
    missing_value_fill_authorized: Literal[False] = False

    @model_validator(mode="after")
    def query_reconciles(self) -> "SecCashQualitySourceQueryV1":
        expected = _QUERY_PAYLOADS_BY_ID[self.query_id]
        if self.model_dump(mode="python") != expected:
            raise ValueError("SEC cash-quality source query differs")
        return self


class SecCashQualityQueryRegistryV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    registry_id: Literal[REGISTRY_ID] = REGISTRY_ID
    lifecycle_state: Literal[
        "registered_query_contract_plan_only"
    ] = "registered_query_contract_plan_only"
    provider_id: Literal["sec_edgar_companyfacts"] = "sec_edgar_companyfacts"
    source_plan_fingerprint: str = Field(pattern=_SHA256)
    immutable_base_registry_fingerprint: str = Field(pattern=_SHA256)
    query_order: tuple[str, ...]
    queries: tuple[SecCashQualitySourceQueryV1, ...]
    duration_pair_accession_rule: Literal[
        "cfo_and_net_income_same_fiscal_endpoint_require_same_clean_accession"
    ] = "cfo_and_net_income_same_fiscal_endpoint_require_same_clean_accession"
    assets_boundary_rule: Literal[
        "opening_and_closing_instants_required_no_interpolation"
    ] = "opening_and_closing_instants_required_no_interpolation"
    source_execution_authorized: Literal[False] = False
    external_request_authorized: Literal[False] = False
    occurrence_selection_authorized: Literal[False] = False
    ttm_derivation_authorized: Literal[False] = False
    feature_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    trial_authorized: Literal[False] = False
    candidate_authorized: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def registry_reconciles(self) -> "SecCashQualityQueryRegistryV1":
        query_ids = tuple(item.query_id for item in self.queries)
        plan = quant_research_sec_cash_quality_source_plan_v1()
        base = build_first_sec_fundamental_query_registry()
        if (
            self.source_plan_fingerprint != plan.logical_fingerprint
            or self.immutable_base_registry_fingerprint != base.logical_fingerprint
            or self.query_order != query_ids
            or query_ids != _QUERY_ORDER
            or self.queries != _queries()
            or cash_quality_query_registry_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("SEC cash-quality query registry differs")
        return self


def cash_quality_query_registry_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def quant_research_sec_cash_quality_query_registry_v1() -> (
    SecCashQualityQueryRegistryV1
):
    values: dict[str, object] = {
        "source_plan_fingerprint": (
            quant_research_sec_cash_quality_source_plan_v1().logical_fingerprint
        ),
        "immutable_base_registry_fingerprint": (
            build_first_sec_fundamental_query_registry().logical_fingerprint
        ),
        "query_order": _QUERY_ORDER,
        "queries": _queries(),
    }
    provisional = SecCashQualityQueryRegistryV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityQueryRegistryV1.model_validate(
        {
            **values,
            "logical_fingerprint": cash_quality_query_registry_fingerprint(
                provisional
            ),
        }
    )


@lru_cache(maxsize=1)
def _queries() -> tuple[SecCashQualitySourceQueryV1, ...]:
    return tuple(
        SecCashQualitySourceQueryV1.model_validate(_QUERY_PAYLOADS_BY_ID[query_id])
        for query_id in _QUERY_ORDER
    )


_ANNUAL_AND_QUARTERLY_RULES = (
    {
        "forms": ("10-K", "10-K/A"),
        "fiscal_periods": ("FY",),
    },
    {
        "forms": ("10-Q", "10-Q/A"),
        "fiscal_periods": ("Q1", "Q2", "Q3"),
    },
)
_DURATION_BASIS_RULES = (
    {"fiscal_period": "FY", "required_basis": "fiscal_year_duration"},
    {"fiscal_period": "Q1", "required_basis": "fiscal_ytd_duration"},
    {"fiscal_period": "Q2", "required_basis": "fiscal_ytd_duration"},
    {"fiscal_period": "Q3", "required_basis": "fiscal_ytd_duration"},
)
_QUERY_PAYLOADS_BY_ID: dict[str, dict[str, object]] = {
    "assets_fiscal_boundary_v1": {
        "query_id": "assets_fiscal_boundary_v1",
        "component_role": "total_assets_boundary",
        "economic_grain": "issuer",
        "namespace": "us-gaap",
        "concept_name": "Assets",
        "unit": "USD",
        "accepted_value_kinds": ("decimal", "integer"),
        "period_shape": "instant",
        "start_date_rule": "must_be_null",
        "form_period_rules": _ANNUAL_AND_QUARTERLY_RULES,
        "fiscal_basis_rules": (),
        "period_end_rule": "must_equal_reported_fiscal_period_end",
        "availability_rule": "sec_acceptance_then_first_xnys_open_strictly_after",
        "revision_rule": (
            "later_clean_amendment_applies_only_from_its_own_availability"
        ),
        "exact_duplicate_rule": "collapse_identical_within_accession",
        "conflict_rule": "quarantine_no_value_selection",
        "concept_fallback_authorized": False,
        "currency_conversion_authorized": False,
        "missing_value_fill_authorized": False,
    },
    "net_income_loss_fiscal_ytd_and_year_v1": {
        "query_id": "net_income_loss_fiscal_ytd_and_year_v1",
        "component_role": "net_income_cumulative",
        "economic_grain": "issuer",
        "namespace": "us-gaap",
        "concept_name": "NetIncomeLoss",
        "unit": "USD",
        "accepted_value_kinds": ("decimal", "integer"),
        "period_shape": "duration",
        "start_date_rule": "must_equal_fiscal_year_origin",
        "form_period_rules": _ANNUAL_AND_QUARTERLY_RULES,
        "fiscal_basis_rules": _DURATION_BASIS_RULES,
        "period_end_rule": "must_equal_reported_fiscal_period_end",
        "availability_rule": "sec_acceptance_then_first_xnys_open_strictly_after",
        "revision_rule": (
            "later_clean_amendment_applies_only_from_its_own_availability"
        ),
        "exact_duplicate_rule": "collapse_identical_within_accession",
        "conflict_rule": "quarantine_no_value_selection",
        "concept_fallback_authorized": False,
        "currency_conversion_authorized": False,
        "missing_value_fill_authorized": False,
    },
    "operating_cash_flow_fiscal_ytd_and_year_v1": {
        "query_id": "operating_cash_flow_fiscal_ytd_and_year_v1",
        "component_role": "operating_cash_flow_cumulative",
        "economic_grain": "issuer",
        "namespace": "us-gaap",
        "concept_name": "NetCashProvidedByUsedInOperatingActivities",
        "unit": "USD",
        "accepted_value_kinds": ("decimal", "integer"),
        "period_shape": "duration",
        "start_date_rule": "must_equal_fiscal_year_origin",
        "form_period_rules": _ANNUAL_AND_QUARTERLY_RULES,
        "fiscal_basis_rules": _DURATION_BASIS_RULES,
        "period_end_rule": "must_equal_reported_fiscal_period_end",
        "availability_rule": "sec_acceptance_then_first_xnys_open_strictly_after",
        "revision_rule": (
            "later_clean_amendment_applies_only_from_its_own_availability"
        ),
        "exact_duplicate_rule": "collapse_identical_within_accession",
        "conflict_rule": "quarantine_no_value_selection",
        "concept_fallback_authorized": False,
        "currency_conversion_authorized": False,
        "missing_value_fill_authorized": False,
    },
}
_QUERY_ORDER = tuple(sorted(_QUERY_PAYLOADS_BY_ID))
