"""Registered issuer-level SEC fundamental source queries."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import to_jsonable_python


CONTRACT_VERSION = "sec-fundamental-query-registry/1.0"
REGISTRY_ID = "sec-issuer-fundamentals-first-set-v1"
_SHA256 = r"^[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecFormPeriodRuleV1(_FrozenModel):
    forms: tuple[str, ...]
    fiscal_periods: tuple[str, ...]

    @model_validator(mode="after")
    def values_are_unique_and_ordered(self) -> "SecFormPeriodRuleV1":
        if not self.forms or self.forms != tuple(sorted(set(self.forms))):
            raise ValueError("SEC form rule forms are not unique and ordered")
        if not self.fiscal_periods or self.fiscal_periods != tuple(
            sorted(set(self.fiscal_periods))
        ):
            raise ValueError("SEC form rule fiscal periods are not unique and ordered")
        return self


class SecFundamentalQueryV1(_FrozenModel):
    query_id: str = Field(pattern=r"^[a-z0-9_]+_v1$")
    display_name: str = Field(min_length=1)
    economic_grain: Literal["issuer"] = "issuer"
    statement_role: Literal["balance_sheet_stock", "annual_income_statement_flow"]
    namespace: Literal["us-gaap"] = "us-gaap"
    concept_name: str = Field(min_length=1)
    unit: Literal["USD"] = "USD"
    accepted_value_kinds: tuple[Literal["decimal", "integer"], ...] = (
        "decimal",
        "integer",
    )
    period_shape: Literal["instant", "duration"]
    start_date_rule: Literal["must_be_null", "must_be_present"]
    minimum_duration_days: int | None = Field(default=None, ge=1)
    maximum_duration_days: int | None = Field(default=None, ge=1)
    form_period_rules: tuple[SecFormPeriodRuleV1, ...]
    availability_policy: Literal["source_available_at_not_after_caller_cutoff"] = (
        "source_available_at_not_after_caller_cutoff"
    )
    period_end_policy: Literal["period_end_not_after_caller_cutoff"] = (
        "period_end_not_after_caller_cutoff"
    )
    revision_policy: Literal[
        "latest_available_clean_accession_for_latest_period_end"
    ] = "latest_available_clean_accession_for_latest_period_end"
    exact_duplicate_policy: Literal["collapse_identical_within_accession"] = (
        "collapse_identical_within_accession"
    )
    conflict_policy: Literal["quarantine_no_value_selection"] = (
        "quarantine_no_value_selection"
    )
    projection_class: Literal["single_common_security_per_cik_v1"] = (
        "single_common_security_per_cik_v1"
    )
    permitted_evidence_tiers: tuple[
        Literal[
            "as_operated_next_open",
            "reconstructed_latest_vintage_development_only",
        ],
        ...,
    ] = (
        "as_operated_next_open",
        "reconstructed_latest_vintage_development_only",
    )
    missing_behavior: Literal["quarantine"] = "quarantine"
    concept_fallback_authorized: Literal[False] = False

    @model_validator(mode="after")
    def semantics_reconcile(self) -> "SecFundamentalQueryV1":
        if self.accepted_value_kinds != ("decimal", "integer"):
            raise ValueError("fundamental query value kinds differ")
        if self.permitted_evidence_tiers != (
            "as_operated_next_open",
            "reconstructed_latest_vintage_development_only",
        ):
            raise ValueError("fundamental query evidence tiers differ")
        if not self.form_period_rules:
            raise ValueError("fundamental query has no form-period rule")
        forms = tuple(
            form for rule in self.form_period_rules for form in rule.forms
        )
        if len(forms) != len(set(forms)):
            raise ValueError("fundamental query form appears in multiple rules")
        if self.period_shape == "instant":
            if (
                self.statement_role != "balance_sheet_stock"
                or self.start_date_rule != "must_be_null"
                or self.minimum_duration_days is not None
                or self.maximum_duration_days is not None
            ):
                raise ValueError("instant fundamental query semantics differ")
        else:
            if (
                self.statement_role != "annual_income_statement_flow"
                or self.start_date_rule != "must_be_present"
                or self.minimum_duration_days is None
                or self.maximum_duration_days is None
                or self.minimum_duration_days > self.maximum_duration_days
            ):
                raise ValueError("duration fundamental query semantics differ")
        return self


class SecFundamentalQueryRegistryV1(_FrozenModel):
    contract_version: Literal[
        "sec-fundamental-query-registry/1.0"
    ] = CONTRACT_VERSION
    registry_id: Literal[
        "sec-issuer-fundamentals-first-set-v1"
    ] = REGISTRY_ID
    lifecycle_state: Literal["registered_source_query_only"] = (
        "registered_source_query_only"
    )
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    query_order: tuple[str, ...]
    queries: tuple[SecFundamentalQueryV1, ...]
    daily_cartesian_panel_authorized: Literal[False] = False
    security_feature_materialization_authorized: Literal[False] = False
    strategy_outcome_access_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    candidate_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def registry_reconciles(self) -> "SecFundamentalQueryRegistryV1":
        query_ids = tuple(item.query_id for item in self.queries)
        if self.query_order != query_ids or query_ids != tuple(sorted(set(query_ids))):
            raise ValueError("fundamental query registry order differs")
        if query_ids != (
            "assets_latest_reported_v1",
            "net_income_loss_fiscal_year_v1",
            "operating_income_loss_fiscal_year_v1",
            "stockholders_equity_latest_reported_v1",
        ):
            raise ValueError("fundamental query registry membership differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("fundamental query registry fingerprint differs")
        return self


def build_first_sec_fundamental_query_registry() -> SecFundamentalQueryRegistryV1:
    """Return the immutable first SEC issuer-query registry."""

    quarterly_and_annual = (
        SecFormPeriodRuleV1(forms=("10-K", "10-K/A"), fiscal_periods=("FY",)),
        SecFormPeriodRuleV1(
            forms=("10-Q", "10-Q/A"),
            fiscal_periods=("Q1", "Q2", "Q3"),
        ),
    )
    annual = (
        SecFormPeriodRuleV1(forms=("10-K", "10-K/A"), fiscal_periods=("FY",)),
    )
    queries = tuple(
        sorted(
            (
                SecFundamentalQueryV1(
                    query_id="assets_latest_reported_v1",
                    display_name="Latest reported assets",
                    statement_role="balance_sheet_stock",
                    concept_name="Assets",
                    period_shape="instant",
                    start_date_rule="must_be_null",
                    form_period_rules=quarterly_and_annual,
                ),
                SecFundamentalQueryV1(
                    query_id="stockholders_equity_latest_reported_v1",
                    display_name="Latest reported stockholders' equity",
                    statement_role="balance_sheet_stock",
                    concept_name="StockholdersEquity",
                    period_shape="instant",
                    start_date_rule="must_be_null",
                    form_period_rules=quarterly_and_annual,
                ),
                SecFundamentalQueryV1(
                    query_id="net_income_loss_fiscal_year_v1",
                    display_name="Fiscal-year net income or loss",
                    statement_role="annual_income_statement_flow",
                    concept_name="NetIncomeLoss",
                    period_shape="duration",
                    start_date_rule="must_be_present",
                    minimum_duration_days=330,
                    maximum_duration_days=400,
                    form_period_rules=annual,
                ),
                SecFundamentalQueryV1(
                    query_id="operating_income_loss_fiscal_year_v1",
                    display_name="Fiscal-year operating income or loss",
                    statement_role="annual_income_statement_flow",
                    concept_name="OperatingIncomeLoss",
                    period_shape="duration",
                    start_date_rule="must_be_present",
                    minimum_duration_days=330,
                    maximum_duration_days=400,
                    form_period_rules=annual,
                ),
            ),
            key=lambda item: item.query_id,
        )
    )
    values = {
        "contract_version": CONTRACT_VERSION,
        "registry_id": REGISTRY_ID,
        "lifecycle_state": "registered_source_query_only",
        "provider_id": "sec_edgar",
        "query_order": tuple(item.query_id for item in queries),
        "queries": queries,
        "daily_cartesian_panel_authorized": False,
        "security_feature_materialization_authorized": False,
        "strategy_outcome_access_authorized": False,
        "research_performance_authorized": False,
        "candidate_authorized": False,
        "production_authorized": False,
    }
    return SecFundamentalQueryRegistryV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _fingerprint(value: object) -> str:
    raw = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
