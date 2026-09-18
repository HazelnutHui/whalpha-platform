"""Contracts for a reusable SEC cash-quality occurrence/endpoint package."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime

from .quant_research_sec_cash_quality_source_readiness_census import (
    SecCashQualitySourceReadinessCensusV1,
    SecCashQualitySourceReadinessPlanV1,
    SecCashQualitySourceReadinessVerificationV1,
    census_fingerprint,
)


CONTRACT_VERSION = "quant-research-sec-cash-quality-endpoint-selection-package/1.0"
PLAN_VERSION = "whalpha.sec-cash-quality-endpoint-selection-package/1.0.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityEndpointSelectionBudgetV1(FrozenModel):
    maximum_source_occurrence_count: int = Field(ge=1)
    maximum_target_index_row_count: int = Field(ge=1)
    maximum_ready_endpoint_count: int = Field(ge=1)
    maximum_selected_query_row_count: int = Field(ge=3)
    batch_size: Literal[65536] = 65_536
    process_count: Literal[1] = 1


class SecCashQualityEndpointSelectionPlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_version: Literal[PLAN_VERSION] = PLAN_VERSION
    readiness_plan_fingerprint: str = Field(pattern=_SHA256)
    readiness_result_fingerprint: str = Field(pattern=_SHA256)
    readiness_verification_fingerprint: str = Field(pattern=_SHA256)
    normalized_manifest_fingerprint: str = Field(pattern=_SHA256)
    normalized_content_fingerprint: str = Field(pattern=_SHA256)
    filing_clock_manifest_fingerprint: str = Field(pattern=_SHA256)
    occurrence_schema_fingerprint: str = Field(pattern=_SHA256)
    source_occurrence_count: int = Field(ge=1)
    target_occurrence_count: int = Field(ge=1)
    admitted_ready_endpoint_count: int = Field(ge=1)
    knowledge_cutoff_at: datetime
    evaluated_session: date
    budget: SecCashQualityEndpointSelectionBudgetV1
    source_scan_rule: Literal[
        "one_formal_reader_scan_then_reuse_owner_only_target_index"
    ] = "one_formal_reader_scan_then_reuse_owner_only_target_index"
    endpoint_admission_rule: Literal[
        "readiness_census_ready_endpoints_only"
    ] = "readiness_census_ready_endpoints_only"
    retains_value_accession_knowledge_time_occurrence_ids: Literal[True] = True
    security_projection_authorized: Literal[False] = False
    ttm_derivation_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("knowledge_cutoff_at")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "SecCashQualityEndpointSelectionPlanV1":
        if (
            self.budget.maximum_source_occurrence_count
            != self.source_occurrence_count
            or self.budget.maximum_target_index_row_count
            != self.target_occurrence_count
            or self.budget.maximum_ready_endpoint_count
            != self.admitted_ready_endpoint_count
            or self.budget.maximum_selected_query_row_count
            != self.admitted_ready_endpoint_count * 3
        ):
            raise ValueError("cash-quality endpoint selection budget differs")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality endpoint selection plan fingerprint differs")
        return self


class SecCashQualityEndpointSelectionPackageManifestV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    built_at: datetime
    target_index_schema_fingerprint: str = Field(pattern=_SHA256)
    target_index_row_count: int = Field(ge=1)
    target_index_bytes: int = Field(ge=1)
    target_index_sha256: str = Field(pattern=_SHA256)
    selected_endpoint_schema_fingerprint: str = Field(pattern=_SHA256)
    selected_endpoint_count: int = Field(ge=1)
    selected_query_row_count: int = Field(ge=3)
    selected_endpoint_bytes: int = Field(ge=1)
    selected_endpoint_sha256: str = Field(pattern=_SHA256)
    source_scan_count: Literal[1] = 1
    network_request_count: Literal[0] = 0
    security_projection_count: Literal[0] = 0
    ttm_derivation_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("built_at")
    @classmethod
    def built_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "SecCashQualityEndpointSelectionPackageManifestV1":
        if self.selected_query_row_count != self.selected_endpoint_count * 3:
            raise ValueError("cash-quality selected query row count differs")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality endpoint package fingerprint differs")
        return self


class SecCashQualityTtmFeasibilityPlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    endpoint_selection_plan_fingerprint: str = Field(pattern=_SHA256)
    endpoint_selection_package_fingerprint: str = Field(pattern=_SHA256)
    admitted_endpoint_count: int = Field(ge=1)
    feasibility_rule: Literal[
        "four_consecutive_discrete_quarters_plus_opening_and_closing_assets"
    ] = "four_consecutive_discrete_quarters_plus_opening_and_closing_assets"
    plan_only: Literal[True] = True
    ttm_derivation_authorized: Literal[False] = False
    security_projection_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "SecCashQualityTtmFeasibilityPlanV1":
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality TTM feasibility plan fingerprint differs")
        return self


def build_sec_cash_quality_endpoint_selection_plan_v1(
    *,
    readiness_plan: SecCashQualitySourceReadinessPlanV1,
    readiness_result: SecCashQualitySourceReadinessCensusV1,
    readiness_verification: SecCashQualitySourceReadinessVerificationV1,
) -> SecCashQualityEndpointSelectionPlanV1:
    if (
        readiness_result.plan_fingerprint != readiness_plan.logical_fingerprint
        or readiness_verification.plan_fingerprint != readiness_plan.logical_fingerprint
        or readiness_verification.primary_result_fingerprint
        != readiness_result.logical_fingerprint
    ):
        raise ValueError("cash-quality readiness evidence binding differs")
    values = {
        "readiness_plan_fingerprint": readiness_plan.logical_fingerprint,
        "readiness_result_fingerprint": readiness_result.logical_fingerprint,
        "readiness_verification_fingerprint": readiness_verification.logical_fingerprint,
        "normalized_manifest_fingerprint": (
            readiness_plan.normalized_manifest_fingerprint
        ),
        "normalized_content_fingerprint": readiness_plan.normalized_content_fingerprint,
        "filing_clock_manifest_fingerprint": (
            readiness_plan.filing_clock_manifest_fingerprint
        ),
        "occurrence_schema_fingerprint": readiness_plan.occurrence_schema_fingerprint,
        "source_occurrence_count": readiness_plan.source_occurrence_count,
        "target_occurrence_count": readiness_result.target_occurrence_count,
        "admitted_ready_endpoint_count": readiness_result.ready_endpoint_count,
        "knowledge_cutoff_at": readiness_plan.knowledge_cutoff_at,
        "evaluated_session": readiness_plan.evaluated_session,
        "budget": SecCashQualityEndpointSelectionBudgetV1(
            maximum_source_occurrence_count=readiness_plan.source_occurrence_count,
            maximum_target_index_row_count=readiness_result.target_occurrence_count,
            maximum_ready_endpoint_count=readiness_result.ready_endpoint_count,
            maximum_selected_query_row_count=readiness_result.ready_endpoint_count * 3,
        ),
    }
    provisional = SecCashQualityEndpointSelectionPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityEndpointSelectionPlanV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def build_sec_cash_quality_ttm_feasibility_plan_v1(
    *,
    selection_plan: SecCashQualityEndpointSelectionPlanV1,
    package_manifest: SecCashQualityEndpointSelectionPackageManifestV1,
) -> SecCashQualityTtmFeasibilityPlanV1:
    if (
        package_manifest.plan_fingerprint != selection_plan.logical_fingerprint
        or package_manifest.selected_endpoint_count
        != selection_plan.admitted_ready_endpoint_count
    ):
        raise ValueError("cash-quality endpoint package binding differs")
    values: Mapping[str, object] = {
        "endpoint_selection_plan_fingerprint": selection_plan.logical_fingerprint,
        "endpoint_selection_package_fingerprint": package_manifest.logical_fingerprint,
        "admitted_endpoint_count": package_manifest.selected_endpoint_count,
    }
    provisional = SecCashQualityTtmFeasibilityPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityTtmFeasibilityPlanV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
