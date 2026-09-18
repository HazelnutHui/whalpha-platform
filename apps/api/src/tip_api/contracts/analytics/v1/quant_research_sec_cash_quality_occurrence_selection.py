"""Typed local occurrence selection for the SEC cash-quality source plan."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime

from .quant_research_sec_cash_earnings_quality_query_registry import (
    quant_research_sec_cash_quality_query_registry_v1,
)


CONTRACT_VERSION = "quant-research-sec-cash-quality-occurrence-selection/1.0"
_CIK = r"^[0-9]{10}$"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCashQualityLocalSourceBindingV1(FrozenModel):
    query_registry_fingerprint: str = Field(pattern=_SHA256)
    normalized_source_manifest_fingerprint: str = Field(pattern=_SHA256)
    normalized_source_content_fingerprint: str = Field(pattern=_SHA256)
    filing_clock_manifest_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def binding_reconciles(self) -> "SecCashQualityLocalSourceBindingV1":
        if (
            self.query_registry_fingerprint
            != quant_research_sec_cash_quality_query_registry_v1().logical_fingerprint
        ):
            raise ValueError("cash-quality query registry binding differs")
        return self


class SecCashQualityEndpointRequestV1(FrozenModel):
    companyfacts_cik: str = Field(pattern=_CIK)
    fiscal_year: int = Field(ge=1900, le=2200)
    fiscal_year_origin: date
    fiscal_period: Literal["FY", "Q1", "Q2", "Q3"]
    period_end: date
    evaluated_session: date
    cutoff_at: datetime

    @field_validator("cutoff_at")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def fiscal_boundary_reconciles(self) -> "SecCashQualityEndpointRequestV1":
        if self.period_end < self.fiscal_year_origin:
            raise ValueError("cash-quality fiscal endpoint precedes its origin")
        return self


class SecCashQualityLocalOccurrenceV1(FrozenModel):
    source_occurrence_id: str = Field(pattern=_SHA256)
    companyfacts_cik: str = Field(pattern=_CIK)
    namespace: str
    concept_name: str
    unit: str
    start_date: date | None = None
    end_date: date | None = None
    value_kind: str
    value_text: str | None = None
    accession_number: str
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    form: str
    filed_date: date
    filing_clock_admission_status: str
    source_available_at: datetime | None = None
    signal_eligible_session: date | None = None
    normalization_status: str

    @field_validator("source_available_at")
    @classmethod
    def availability_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)


class SecCashQualityQueryOccurrenceSelectionV1(FrozenModel):
    query_id: Literal[
        "assets_fiscal_boundary_v1",
        "net_income_loss_fiscal_ytd_and_year_v1",
        "operating_cash_flow_fiscal_ytd_and_year_v1",
    ]
    selection_status: Literal["selected", "not_available", "quarantined"]
    reason_codes: tuple[str, ...]
    value_kind: Literal["decimal", "integer"] | None = None
    value_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source_available_at: datetime | None = None
    signal_eligible_session: date | None = None
    accession_number: str | None = None
    form: str | None = None
    filed_date: date | None = None
    source_occurrence_ids: tuple[str, ...] = ()
    exact_duplicate_redundant_occurrence_count: int = Field(ge=0)

    @field_validator("source_available_at")
    @classmethod
    def availability_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def selection_reconciles(self) -> "SecCashQualityQueryOccurrenceSelectionV1":
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("cash-quality occurrence reasons differ")
        if self.source_occurrence_ids != tuple(
            sorted(set(self.source_occurrence_ids))
        ):
            raise ValueError("cash-quality occurrence evidence differs")
        evidence = (
            self.value_kind,
            self.value_text,
            self.end_date,
            self.source_available_at,
            self.signal_eligible_session,
            self.accession_number,
            self.form,
            self.filed_date,
        )
        if self.selection_status == "selected":
            if (
                self.reason_codes
                or not all(value is not None for value in evidence)
                or not self.source_occurrence_ids
                or self.exact_duplicate_redundant_occurrence_count
                != len(self.source_occurrence_ids) - 1
            ):
                raise ValueError("selected cash-quality occurrence differs")
            if (
                self.query_id == "assets_fiscal_boundary_v1"
                and self.start_date is not None
            ) or (
                self.query_id != "assets_fiscal_boundary_v1"
                and self.start_date is None
            ):
                raise ValueError("selected cash-quality period shape differs")
        elif (
            not self.reason_codes
            or any(value is not None for value in evidence)
            or self.start_date is not None
            or self.source_occurrence_ids
            or self.exact_duplicate_redundant_occurrence_count != 0
        ):
            raise ValueError("unselected cash-quality occurrence differs")
        return self


class SecCashQualityLocalOccurrenceReadinessV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    lifecycle_state: Literal[
        "local_occurrence_readiness_only"
    ] = "local_occurrence_readiness_only"
    source_binding: SecCashQualityLocalSourceBindingV1
    request: SecCashQualityEndpointRequestV1
    selections: tuple[SecCashQualityQueryOccurrenceSelectionV1, ...]
    duration_pair_accession_coherent: bool
    readiness_status: Literal[
        "ready_for_endpoint_occurrence_use_only",
        "blocked",
    ]
    reason_codes: tuple[str, ...]
    network_request_count: Literal[0] = 0
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

    @model_validator(mode="after")
    def readiness_reconciles(self) -> "SecCashQualityLocalOccurrenceReadinessV1":
        expected_order = quant_research_sec_cash_quality_query_registry_v1().query_order
        if tuple(item.query_id for item in self.selections) != expected_order:
            raise ValueError("cash-quality occurrence selection order differs")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("cash-quality readiness reasons differ")
        all_selected = all(
            item.selection_status == "selected" for item in self.selections
        )
        selected = {item.query_id: item for item in self.selections}
        cash_flow = selected["operating_cash_flow_fiscal_ytd_and_year_v1"]
        net_income = selected["net_income_loss_fiscal_ytd_and_year_v1"]
        expected_coherence = (
            cash_flow.selection_status == "selected"
            and net_income.selection_status == "selected"
            and cash_flow.accession_number == net_income.accession_number
        )
        if self.duration_pair_accession_coherent != expected_coherence:
            raise ValueError("cash-quality duration accession coherence differs")
        if any(
            item.selection_status == "selected"
            and (
                item.end_date != self.request.period_end
                or item.source_available_at is None
                or item.source_available_at > self.request.cutoff_at
                or item.signal_eligible_session is None
                or item.signal_eligible_session > self.request.evaluated_session
            )
            for item in self.selections
        ):
            raise ValueError("cash-quality selected endpoint boundary differs")
        expected_status = (
            "ready_for_endpoint_occurrence_use_only"
            if all_selected and expected_coherence
            else "blocked"
        )
        if self.readiness_status != expected_status:
            raise ValueError("cash-quality occurrence readiness differs")
        if (expected_status == "blocked") != bool(self.reason_codes):
            raise ValueError("cash-quality readiness reason presence differs")
        if occurrence_readiness_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("cash-quality occurrence readiness fingerprint differs")
        return self


def occurrence_readiness_fingerprint(
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
