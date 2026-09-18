"""Bounded source-readiness census contracts for SEC cash quality."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_normalized_source import (
    SecCompanyfactsNormalizedSourceManifestV1,
)

from .quant_research_sec_cash_earnings_quality_query_registry import (
    quant_research_sec_cash_quality_query_registry_v1,
)


CONTRACT_VERSION = "quant-research-sec-cash-quality-source-readiness-census/1.0"
PLAN_VERSION = "whalpha.sec-cash-quality-source-readiness-census/1.0.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityCensusArtifactV1(FrozenModel):
    relative_path: str
    row_count: int = Field(ge=1)
    physical_sha256: str = Field(pattern=_SHA256)
    logical_fingerprint: str = Field(pattern=_SHA256)


class SecCashQualitySourceReadinessBudgetV1(FrozenModel):
    maximum_scanned_occurrence_count: int = Field(ge=1)
    maximum_target_occurrence_count: int = Field(ge=1)
    maximum_observed_endpoint_count: int = Field(ge=1)
    maximum_rows_retained_per_worker: int = Field(ge=1)
    batch_size: Literal[65536] = 65_536
    worker_count: int = Field(ge=1, le=16)
    process_count: Literal[1] = 1


class SecCashQualitySourceReadinessPlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_version: Literal[PLAN_VERSION] = PLAN_VERSION
    lifecycle_state: Literal[
        "bounded_local_source_readiness_only"
    ] = "bounded_local_source_readiness_only"
    query_registry_fingerprint: str = Field(pattern=_SHA256)
    normalized_manifest_fingerprint: str = Field(pattern=_SHA256)
    normalized_content_fingerprint: str = Field(pattern=_SHA256)
    filing_clock_manifest_fingerprint: str = Field(pattern=_SHA256)
    occurrence_schema_fingerprint: str = Field(pattern=_SHA256)
    source_range_start: date
    source_range_end: date
    knowledge_cutoff_at: datetime
    evaluated_session: date
    source_occurrence_count: int = Field(ge=1)
    occurrence_artifacts: tuple[SecCashQualityCensusArtifactV1, ...]
    budget: SecCashQualitySourceReadinessBudgetV1
    target_query_order: tuple[str, ...]
    denominator_rule: Literal[
        "observed_target_concept_issuer_fiscal_endpoints_only"
    ] = "observed_target_concept_issuer_fiscal_endpoints_only"
    traversal_rule: Literal[
        "stream_every_bound_occurrence_artifact_without_source_panel_materialization"
    ] = "stream_every_bound_occurrence_artifact_without_source_panel_materialization"
    result_values_retained: Literal[False] = False
    network_request_authorized: Literal[False] = False
    security_projection_authorized: Literal[False] = False
    applicability_adjudication_authorized: Literal[False] = False
    ttm_derivation_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    trial_authorized: Literal[False] = False
    candidate_authorized: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    production_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("knowledge_cutoff_at")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "SecCashQualitySourceReadinessPlanV1":
        registry = quant_research_sec_cash_quality_query_registry_v1()
        if self.query_registry_fingerprint != registry.logical_fingerprint:
            raise ValueError("cash-quality census query registry binding differs")
        if self.target_query_order != registry.query_order:
            raise ValueError("cash-quality census query order differs")
        if self.source_range_end < self.source_range_start:
            raise ValueError("cash-quality census source range is reversed")
        if self.occurrence_artifacts != tuple(
            sorted(self.occurrence_artifacts, key=lambda item: item.relative_path)
        ):
            raise ValueError("cash-quality census artifacts are unordered")
        if sum(item.row_count for item in self.occurrence_artifacts) != (
            self.source_occurrence_count
        ):
            raise ValueError("cash-quality census source denominator differs")
        if (
            self.budget.maximum_scanned_occurrence_count
            != self.source_occurrence_count
            or self.budget.worker_count
            != len(
                {
                    item.relative_path.split("/", 1)[0]
                    for item in self.occurrence_artifacts
                }
            )
        ):
            raise ValueError("cash-quality census budget differs")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality census plan fingerprint differs")
        return self


class SecCashQualityQueryCensusResultV1(FrozenModel):
    query_id: str
    target_occurrence_count: int = Field(ge=0)
    occurrence_disposition_counts: tuple[tuple[str, int], ...]
    selected_endpoint_count: int = Field(ge=0)
    not_available_endpoint_count: int = Field(ge=0)
    quarantined_endpoint_count: int = Field(ge=0)
    endpoint_reason_counts: tuple[tuple[str, int], ...]

    @model_validator(mode="after")
    def counts_reconcile(self) -> "SecCashQualityQueryCensusResultV1":
        if self.occurrence_disposition_counts != tuple(
            sorted(self.occurrence_disposition_counts)
        ) or any(
            value <= 0 for _, value in self.occurrence_disposition_counts
        ) or len({key for key, _ in self.occurrence_disposition_counts}) != len(
            self.occurrence_disposition_counts
        ) or sum(
            value for _, value in self.occurrence_disposition_counts
        ) != self.target_occurrence_count:
            raise ValueError("cash-quality query occurrence counts differ")
        if self.endpoint_reason_counts != tuple(
            sorted(self.endpoint_reason_counts)
        ) or any(
            value <= 0 for _, value in self.endpoint_reason_counts
        ) or len({key for key, _ in self.endpoint_reason_counts}) != len(
            self.endpoint_reason_counts
        ):
            raise ValueError("cash-quality query endpoint reasons differ")
        return self


class SecCashQualitySourceReadinessCensusV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    completion_status: Literal["completed_source_readiness_only"] = (
        "completed_source_readiness_only"
    )
    plan_fingerprint: str = Field(pattern=_SHA256)
    normalized_manifest_fingerprint: str = Field(pattern=_SHA256)
    query_registry_fingerprint: str = Field(pattern=_SHA256)
    source_range_start: date
    source_range_end: date
    knowledge_cutoff_at: datetime
    evaluated_session: date
    scanned_occurrence_count: int = Field(ge=1)
    target_occurrence_count: int = Field(ge=0)
    observed_issuer_count: int = Field(ge=0)
    observed_endpoint_count: int = Field(ge=0)
    ready_endpoint_count: int = Field(ge=0)
    blocked_endpoint_count: int = Field(ge=0)
    fiscal_period_endpoint_counts: tuple[tuple[str, int], ...]
    readiness_reason_counts: tuple[tuple[str, int], ...]
    query_results: tuple[SecCashQualityQueryCensusResultV1, ...]
    earliest_target_source_available_at: datetime | None = None
    latest_target_source_available_at: datetime | None = None
    positive_evidence_denominator_only: Literal[True] = True
    absent_issuer_endpoints_measured: Literal[False] = False
    result_values_retained: Literal[False] = False
    network_request_count: Literal[0] = 0
    security_projection_count: Literal[0] = 0
    ttm_derivation_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    canonical_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator(
        "knowledge_cutoff_at",
        "earliest_target_source_available_at",
        "latest_target_source_available_at",
    )
    @classmethod
    def datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def census_reconciles(self) -> "SecCashQualitySourceReadinessCensusV1":
        if self.source_range_end < self.source_range_start:
            raise ValueError("cash-quality census source range is reversed")
        if self.target_occurrence_count > self.scanned_occurrence_count:
            raise ValueError("cash-quality census target denominator differs")
        if self.observed_issuer_count > self.observed_endpoint_count:
            raise ValueError("cash-quality census issuer denominator differs")
        if self.ready_endpoint_count + self.blocked_endpoint_count != (
            self.observed_endpoint_count
        ):
            raise ValueError("cash-quality census endpoint counts differ")
        if self.fiscal_period_endpoint_counts != tuple(
            sorted(self.fiscal_period_endpoint_counts)
        ) or any(
            value <= 0 for _, value in self.fiscal_period_endpoint_counts
        ) or len({key for key, _ in self.fiscal_period_endpoint_counts}) != len(
            self.fiscal_period_endpoint_counts
        ) or sum(
            value for _, value in self.fiscal_period_endpoint_counts
        ) != self.observed_endpoint_count:
            raise ValueError("cash-quality census fiscal-period counts differ")
        if self.readiness_reason_counts != tuple(
            sorted(self.readiness_reason_counts)
        ) or any(
            value <= 0 for _, value in self.readiness_reason_counts
        ) or len({key for key, _ in self.readiness_reason_counts}) != len(
            self.readiness_reason_counts
        ):
            raise ValueError("cash-quality census reasons differ")
        if tuple(item.query_id for item in self.query_results) != (
            quant_research_sec_cash_quality_query_registry_v1().query_order
        ):
            raise ValueError("cash-quality census query results differ")
        if sum(
            item.target_occurrence_count for item in self.query_results
        ) != self.target_occurrence_count:
            raise ValueError("cash-quality census query target counts differ")
        if any(
            item.selected_endpoint_count
            + item.not_available_endpoint_count
            + item.quarantined_endpoint_count
            != self.observed_endpoint_count
            for item in self.query_results
        ):
            raise ValueError("cash-quality census query endpoint counts differ")
        if (self.earliest_target_source_available_at is None) != (
            self.latest_target_source_available_at is None
        ):
            raise ValueError("cash-quality census availability bounds differ")
        if (
            self.earliest_target_source_available_at is not None
            and self.latest_target_source_available_at is not None
            and self.latest_target_source_available_at
            < self.earliest_target_source_available_at
        ):
            raise ValueError("cash-quality census availability range is reversed")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality census fingerprint differs")
        return self


class SecCashQualitySourceReadinessVerificationV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    primary_result_fingerprint: str = Field(pattern=_SHA256)
    replay_result_fingerprint: str = Field(pattern=_SHA256)
    primary_canonical_sha256: str = Field(pattern=_SHA256)
    replay_canonical_sha256: str = Field(pattern=_SHA256)
    verification_status: Literal["byte_identical"] = "byte_identical"
    downstream_authority_changed: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def verification_reconciles(self) -> "SecCashQualitySourceReadinessVerificationV1":
        if (
            self.primary_result_fingerprint != self.replay_result_fingerprint
            or self.primary_canonical_sha256 != self.replay_canonical_sha256
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("cash-quality census replay differs")
        return self


def build_sec_cash_quality_source_readiness_plan_v1(
    manifest: SecCompanyfactsNormalizedSourceManifestV1,
) -> SecCashQualitySourceReadinessPlanV1:
    artifacts = tuple(
        SecCashQualityCensusArtifactV1(
            relative_path=item.relative_path,
            row_count=item.row_count,
            physical_sha256=item.physical_sha256,
            logical_fingerprint=item.logical_fingerprint,
        )
        for item in manifest.artifacts
        if item.artifact_kind == "occurrence"
    )
    registry = quant_research_sec_cash_quality_query_registry_v1()
    values = {
        "query_registry_fingerprint": registry.logical_fingerprint,
        "normalized_manifest_fingerprint": manifest.logical_fingerprint,
        "normalized_content_fingerprint": manifest.content_fingerprint,
        "filing_clock_manifest_fingerprint": (
            manifest.filing_clock_manifest_fingerprint
        ),
        "occurrence_schema_fingerprint": manifest.occurrence_schema_fingerprint,
        "source_range_start": manifest.range_start,
        "source_range_end": manifest.range_end,
        "knowledge_cutoff_at": manifest.built_at,
        "evaluated_session": manifest.built_at.date(),
        "source_occurrence_count": manifest.occurrence_count,
        "occurrence_artifacts": artifacts,
        "budget": SecCashQualitySourceReadinessBudgetV1(
            maximum_scanned_occurrence_count=manifest.occurrence_count,
            maximum_target_occurrence_count=2_000_000,
            maximum_observed_endpoint_count=1_000_000,
            maximum_rows_retained_per_worker=300_000,
            worker_count=manifest.worker_count,
        ),
        "target_query_order": registry.query_order,
    }
    provisional = SecCashQualitySourceReadinessPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualitySourceReadinessPlanV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def census_fingerprint(value: BaseModel | Mapping[str, object]) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(canonical_census_bytes(payload)).hexdigest()


def canonical_census_bytes(value: BaseModel | Mapping[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
