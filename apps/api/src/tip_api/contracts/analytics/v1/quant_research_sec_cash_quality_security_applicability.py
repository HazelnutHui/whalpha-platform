"""Outcome-blind listed-security applicability census contracts."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


CONTRACT_VERSION = "quant-research-sec-cash-quality-security-applicability/1.0"
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ApplicabilityArtifactBindingV1(FrozenModel):
    relative_path: str = Field(min_length=1)
    physical_sha256: str = Field(pattern=_SHA256)
    byte_size: int = Field(ge=1)
    row_count: int = Field(ge=1)


class ApplicabilityLinkSessionBindingV1(ApplicabilityArtifactBindingV1):
    session_date: date
    point_in_time_eligibility: str


class SecCashQualitySecurityApplicabilityPlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    ttm_verification_fingerprint: str = Field(pattern=_SHA256)
    ttm_result_fingerprint: str = Field(pattern=_SHA256)
    ttm_rows: ApplicabilityArtifactBindingV1
    lineage_selection_verification_fingerprint: str = Field(pattern=_SHA256)
    lineage_rows: ApplicabilityArtifactBindingV1
    link_manifest_logical_fingerprint: str = Field(pattern=_SHA256)
    link_manifest_physical_sha256: str = Field(pattern=_SHA256)
    link_manifest_byte_size: int = Field(ge=1)
    link_sessions: tuple[ApplicabilityLinkSessionBindingV1, ...]
    provider_form_manifest_physical_sha256: str = Field(pattern=_SHA256)
    provider_form_rows: ApplicabilityArtifactBindingV1
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str = Field(min_length=1)
    expected_ttm_endpoint_count: int = Field(ge=1)
    security_form_evidence_is_effective_dated: Literal[False] = False
    issuer_structure_evidence_available: Literal[False] = False
    sec_filer_identity_is_security_proof: Literal[False] = False
    security_projection_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_authorized: Literal[False] = False
    product_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualitySecurityApplicabilityPlanV1":
        dates = tuple(item.session_date for item in self.link_sessions)
        if (
            dates != tuple(sorted(set(dates)))
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("security applicability plan differs")
        return self


class SecCashQualitySecurityApplicabilityResultV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    ttm_endpoint_count: int = Field(ge=1)
    lineage_session_recovered_count: int = Field(ge=0)
    distinct_signal_session_count: int = Field(ge=0)
    link_session_in_range_count: int = Field(ge=0)
    cik_linked_endpoint_count: int = Field(ge=0)
    unique_common_security_endpoint_count: int = Field(ge=0)
    multiple_security_issuer_endpoint_count: int = Field(ge=0)
    multiple_common_security_endpoint_count: int = Field(ge=0)
    identity_known_by_signal_open_count: int = Field(ge=0)
    observed_provider_form_counts: tuple[tuple[str, int], ...]
    stable_instrument_count: int = Field(ge=0)
    stable_instrument_ticker_change_count: int = Field(ge=0)
    effective_dated_security_form_eligible_count: Literal[0] = 0
    authoritative_issuer_structure_eligible_count: Literal[0] = 0
    fully_applicable_endpoint_count: Literal[0] = 0
    primary_blocker_counts: tuple[tuple[str, int], ...]
    evidence_gap_counts: tuple[tuple[str, int], ...]
    network_request_count: Literal[0] = 0
    security_projection_count: Literal[0] = 0
    factor_materialization_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    validation_access_count: Literal[0] = 0
    holdout_access_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualitySecurityApplicabilityResultV1":
        if (
            sum(value for _, value in self.primary_blocker_counts)
            != self.ttm_endpoint_count
            or self.primary_blocker_counts != tuple(sorted(self.primary_blocker_counts))
            or self.observed_provider_form_counts
            != tuple(sorted(self.observed_provider_form_counts))
            or self.evidence_gap_counts != tuple(sorted(self.evidence_gap_counts))
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("security applicability result differs")
        return self


class SecCashQualitySecurityApplicabilityVerificationV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    forward_result_fingerprint: str = Field(pattern=_SHA256)
    reverse_result_fingerprint: str = Field(pattern=_SHA256)
    status: Literal["identical"] = "identical"
    downstream_authority_changed: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualitySecurityApplicabilityVerificationV1":
        if (
            self.forward_result_fingerprint != self.reverse_result_fingerprint
            or census_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("security applicability replay differs")
        return self
