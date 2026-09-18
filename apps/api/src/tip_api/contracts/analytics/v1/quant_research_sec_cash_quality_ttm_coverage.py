"""Issuer-level four-quarter TTM derivation and coverage contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime

from .quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


CONTRACT_VERSION = "quant-research-sec-cash-quality-ttm-coverage/1.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityTtmCoveragePlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    endpoint_package_fingerprint: str = Field(pattern=_SHA256)
    endpoint_plan_fingerprint: str = Field(pattern=_SHA256)
    input_endpoint_count: int = Field(ge=1)
    maximum_ttm_row_count: int = Field(ge=1)
    annual_duration_days_minimum: Literal[350] = 350
    annual_duration_days_maximum: Literal[378] = 378
    cross_year_origin_rule: Literal[
        "next_fiscal_origin_is_prior_fy_end_plus_one_day"
    ] = "next_fiscal_origin_is_prior_fy_end_plus_one_day"
    negative_flow_values_admitted: Literal[True] = True
    zero_flow_values_admitted: Literal[True] = True
    zero_average_assets_admitted: Literal[False] = False
    issuer_level_only: Literal[True] = True
    security_projection_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    product_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityTtmCoveragePlanV1":
        if self.maximum_ttm_row_count != self.input_endpoint_count:
            raise ValueError("cash-quality TTM budget differs")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality TTM plan fingerprint differs")
        return self


class SecCashQualityTtmCoverageResultV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    input_endpoint_count: int = Field(ge=1)
    ttm_ready_endpoint_count: int = Field(ge=0)
    ttm_blocked_endpoint_count: int = Field(ge=0)
    issuer_count: int = Field(ge=1)
    ttm_ready_issuer_count: int = Field(ge=0)
    blocker_counts: tuple[tuple[str, int], ...]
    negative_ttm_cfo_count: int = Field(ge=0)
    zero_ttm_cfo_count: int = Field(ge=0)
    negative_ttm_net_income_count: int = Field(ge=0)
    zero_ttm_net_income_count: int = Field(ge=0)
    negative_average_assets_count: int = Field(ge=0)
    earliest_knowledge_at: datetime | None = None
    latest_knowledge_at: datetime | None = None
    network_request_count: Literal[0] = 0
    security_projection_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("earliest_knowledge_at", "latest_knowledge_at")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityTtmCoverageResultV1":
        if self.ttm_ready_endpoint_count + self.ttm_blocked_endpoint_count != self.input_endpoint_count:
            raise ValueError("cash-quality TTM endpoint counts differ")
        if self.blocker_counts != tuple(sorted(self.blocker_counts)) or sum(
            value for _, value in self.blocker_counts
        ) != self.ttm_blocked_endpoint_count:
            raise ValueError("cash-quality TTM blockers differ")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality TTM result fingerprint differs")
        return self


class SecCashQualityTtmCoverageVerificationV1(FrozenModel):
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
    def reconciles(self) -> "SecCashQualityTtmCoverageVerificationV1":
        if (
            self.primary_result_fingerprint != self.replay_result_fingerprint
            or self.primary_rows_sha256 != self.replay_rows_sha256
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cash-quality TTM replay differs")
        return self


def build_sec_cash_quality_ttm_coverage_plan_v1(
    *, endpoint_package_fingerprint: str, endpoint_plan_fingerprint: str, endpoint_count: int
) -> SecCashQualityTtmCoveragePlanV1:
    values = {
        "endpoint_package_fingerprint": endpoint_package_fingerprint,
        "endpoint_plan_fingerprint": endpoint_plan_fingerprint,
        "input_endpoint_count": endpoint_count,
        "maximum_ttm_row_count": endpoint_count,
    }
    provisional = SecCashQualityTtmCoveragePlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityTtmCoveragePlanV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
