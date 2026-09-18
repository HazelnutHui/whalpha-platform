"""Corrected economic-endpoint SEC cash-quality TTM coverage contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_sec_cash_quality_source_readiness_census import (
    census_fingerprint,
)


CONTRACT_VERSION = "quant-research-sec-cash-quality-ttm-coverage/2.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityTtmCoveragePlanV2(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    source_selection_verification_fingerprint: str = Field(pattern=_SHA256)
    source_selection_result_fingerprint: str = Field(pattern=_SHA256)
    source_rows_logical_sha256: str = Field(pattern=_SHA256)
    source_rows_physical_sha256: str = Field(pattern=_SHA256)
    source_rows_schema_fingerprint: str = Field(pattern=_SHA256)
    source_rows_bytes: int = Field(ge=1)
    input_endpoint_count: int = Field(ge=1)
    input_query_row_count: int = Field(ge=3)
    maximum_ttm_row_count: int = Field(ge=1)
    annual_duration_days_minimum: Literal[350] = 350
    annual_duration_days_maximum: Literal[378] = 378
    economic_endpoint_rule: Literal[
        "issuer_duration_origin_fiscal_period_period_end"
    ] = "issuer_duration_origin_fiscal_period_period_end"
    cross_year_origin_rule: Literal[
        "next_origin_is_prior_fy_end_plus_one_day"
    ] = "next_origin_is_prior_fy_end_plus_one_day"
    input_package_only: Literal[True] = True
    target_index_access_authorized: Literal[False] = False
    normalized_source_access_authorized: Literal[False] = False
    network_authorized: Literal[False] = False
    security_projection_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    product_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityTtmCoveragePlanV2":
        if (
            self.input_query_row_count != self.input_endpoint_count * 3
            or self.maximum_ttm_row_count != self.input_endpoint_count
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cash-quality TTM V2 plan differs")
        return self


class SecCashQualityTtmCoverageResultV2(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    input_endpoint_count: int = Field(ge=1)
    input_query_row_count: int = Field(ge=3)
    issuer_count: int = Field(ge=1)
    ttm_ready_endpoint_count: int = Field(ge=0)
    ttm_ready_issuer_count: int = Field(ge=0)
    ttm_blocked_endpoint_count: int = Field(ge=0)
    blocker_counts: tuple[tuple[str, int], ...]
    negative_ttm_cfo_count: int = Field(ge=0)
    zero_ttm_cfo_count: int = Field(ge=0)
    negative_ttm_net_income_count: int = Field(ge=0)
    zero_ttm_net_income_count: int = Field(ge=0)
    negative_average_assets_count: int = Field(ge=0)
    earliest_knowledge_at: datetime | None = None
    latest_knowledge_at: datetime | None = None
    target_index_access_count: Literal[0] = 0
    normalized_source_access_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    security_projection_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityTtmCoverageResultV2":
        if (
            self.input_query_row_count != self.input_endpoint_count * 3
            or self.ttm_ready_endpoint_count + self.ttm_blocked_endpoint_count
            != self.input_endpoint_count
            or sum(value for _, value in self.blocker_counts)
            != self.ttm_blocked_endpoint_count
            or self.blocker_counts != tuple(sorted(self.blocker_counts))
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cash-quality TTM V2 result differs")
        return self


class SecCashQualityTtmCoverageVerificationV2(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    primary_result_fingerprint: str = Field(pattern=_SHA256)
    replay_result_fingerprint: str = Field(pattern=_SHA256)
    primary_rows_sha256: str = Field(pattern=_SHA256)
    replay_rows_sha256: str = Field(pattern=_SHA256)
    status: Literal["byte_identical"] = "byte_identical"
    downstream_authority_changed: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityTtmCoverageVerificationV2":
        if (
            self.primary_result_fingerprint != self.replay_result_fingerprint
            or self.primary_rows_sha256 != self.replay_rows_sha256
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cash-quality TTM V2 replay differs")
        return self


def build_sec_cash_quality_ttm_coverage_plan_v2(
    *, source_selection_verification_fingerprint: str,
    source_selection_result_fingerprint: str,
    source_rows_logical_sha256: str, source_rows_physical_sha256: str,
    source_rows_schema_fingerprint: str, source_rows_bytes: int,
    input_endpoint_count: int, input_query_row_count: int,
) -> SecCashQualityTtmCoveragePlanV2:
    values = {
        "source_selection_verification_fingerprint": source_selection_verification_fingerprint,
        "source_selection_result_fingerprint": source_selection_result_fingerprint,
        "source_rows_logical_sha256": source_rows_logical_sha256,
        "source_rows_physical_sha256": source_rows_physical_sha256,
        "source_rows_schema_fingerprint": source_rows_schema_fingerprint,
        "source_rows_bytes": source_rows_bytes,
        "input_endpoint_count": input_endpoint_count,
        "input_query_row_count": input_query_row_count,
        "maximum_ttm_row_count": input_endpoint_count,
    }
    provisional = SecCashQualityTtmCoveragePlanV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityTtmCoveragePlanV2.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
