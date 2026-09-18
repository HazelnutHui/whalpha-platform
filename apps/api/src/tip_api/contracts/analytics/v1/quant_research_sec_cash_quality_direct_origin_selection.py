"""Versioned direct-origin SEC cash-quality endpoint selection contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_sec_cash_quality_source_readiness_census import (
    census_fingerprint,
)


CONTRACT_VERSION = "quant-research-sec-cash-quality-direct-origin-selection/2.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityDirectOriginSelectionPlanV2(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    source_endpoint_package_fingerprint: str = Field(pattern=_SHA256)
    source_selection_plan_fingerprint: str = Field(pattern=_SHA256)
    target_index_physical_sha256: str = Field(pattern=_SHA256)
    target_index_schema_fingerprint: str = Field(pattern=_SHA256)
    target_index_row_count: int = Field(ge=1)
    target_index_bytes: int = Field(ge=1)
    maximum_endpoint_coordinate_count: int = Field(ge=1)
    maximum_selected_endpoint_variant_count: int = Field(ge=1)
    query_count_per_endpoint: Literal[3] = 3
    q2_q3_origin_rule: Literal[
        "unique_complete_accession_coherent_duration_start_date"
    ] = "unique_complete_accession_coherent_duration_start_date"
    comparative_variant_rule: Literal[
        "unique_componentwise_latest_complete_variant"
    ] = "unique_componentwise_latest_complete_variant"
    local_target_index_only: Literal[True] = True
    source_rescan_authorized: Literal[False] = False
    network_authorized: Literal[False] = False
    ttm_derivation_authorized: Literal[False] = False
    security_projection_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    product_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityDirectOriginSelectionPlanV2":
        if (
            self.maximum_endpoint_coordinate_count > self.target_index_row_count
            or self.maximum_selected_endpoint_variant_count
            > self.maximum_endpoint_coordinate_count
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("direct-origin selection plan differs")
        return self


class SecCashQualityDirectOriginSelectionResultV2(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    target_index_row_count: int = Field(ge=1)
    query_candidate_occurrence_count: int = Field(ge=1)
    observed_issuer_count: int = Field(ge=1)
    observed_endpoint_coordinate_count: int = Field(ge=1)
    selected_endpoint_variant_count: int = Field(ge=0)
    selector_blocked_endpoint_coordinate_count: int = Field(ge=0)
    selector_blocker_counts: tuple[tuple[str, int], ...]
    canonical_endpoint_count: int = Field(ge=0)
    superseded_comparative_variant_count: int = Field(ge=0)
    canonicalization_blocked_variant_count: int = Field(ge=0)
    canonicalization_blocker_counts: tuple[tuple[str, int], ...]
    fiscal_period_canonical_endpoint_counts: tuple[tuple[str, int], ...]
    earliest_source_available_at: datetime | None = None
    latest_source_available_at: datetime | None = None
    output_query_row_count: int = Field(ge=0)
    source_scan_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    ttm_derivation_count: Literal[0] = 0
    security_projection_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualityDirectOriginSelectionResultV2":
        if (
            self.selected_endpoint_variant_count
            + self.selector_blocked_endpoint_coordinate_count
            != self.observed_endpoint_coordinate_count
            or sum(value for _, value in self.selector_blocker_counts)
            != self.selector_blocked_endpoint_coordinate_count
            or self.canonical_endpoint_count
            + self.superseded_comparative_variant_count
            + self.canonicalization_blocked_variant_count
            != self.selected_endpoint_variant_count
            or sum(value for _, value in self.canonicalization_blocker_counts)
            != self.canonicalization_blocked_variant_count
            or sum(value for _, value in self.fiscal_period_canonical_endpoint_counts)
            != self.canonical_endpoint_count
            or self.output_query_row_count != self.canonical_endpoint_count * 3
            or self.selector_blocker_counts != tuple(sorted(self.selector_blocker_counts))
            or self.canonicalization_blocker_counts
            != tuple(sorted(self.canonicalization_blocker_counts))
            or self.fiscal_period_canonical_endpoint_counts
            != tuple(sorted(self.fiscal_period_canonical_endpoint_counts))
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("direct-origin selection result differs")
        return self


class SecCashQualityDirectOriginSelectionVerificationV2(FrozenModel):
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
    def reconciles(self) -> "SecCashQualityDirectOriginSelectionVerificationV2":
        if (
            self.primary_result_fingerprint != self.replay_result_fingerprint
            or self.primary_rows_sha256 != self.replay_rows_sha256
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("direct-origin selection replay differs")
        return self


def build_sec_cash_quality_direct_origin_selection_plan_v2(
    *,
    source_endpoint_package_fingerprint: str,
    source_selection_plan_fingerprint: str,
    target_index_physical_sha256: str,
    target_index_schema_fingerprint: str,
    target_index_row_count: int,
    target_index_bytes: int,
) -> SecCashQualityDirectOriginSelectionPlanV2:
    values = {
        "source_endpoint_package_fingerprint": source_endpoint_package_fingerprint,
        "source_selection_plan_fingerprint": source_selection_plan_fingerprint,
        "target_index_physical_sha256": target_index_physical_sha256,
        "target_index_schema_fingerprint": target_index_schema_fingerprint,
        "target_index_row_count": target_index_row_count,
        "target_index_bytes": target_index_bytes,
        "maximum_endpoint_coordinate_count": target_index_row_count,
        "maximum_selected_endpoint_variant_count": target_index_row_count,
    }
    provisional = SecCashQualityDirectOriginSelectionPlanV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualityDirectOriginSelectionPlanV2.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
