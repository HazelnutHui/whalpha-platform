"""Outcome-blind source-gap disposition for listed-security applicability."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


CONTRACT_VERSION = "quant-research-sec-cash-quality-source-gap/1.0"
BASELINE_APPLICABILITY_RESULT_FINGERPRINT = (
    "da67ce358fef0bb533875125d658ee6f2e365c435f17c08036d9b03d12fa578e"
)
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceLane(StrEnum):
    INSTRUMENT_CIK = "effective_dated_instrument_cik"
    SECURITY_FORM = "effective_dated_security_form"
    LISTING_AND_ALIASES = "listing_interval_and_ticker_aliases"
    ISSUER_SECURITY_STRUCTURE = "issuer_security_structure"
    MULTI_COMMON = "multi_common_policy"


class SourceClass(StrEnum):
    LOCAL_RETAINED = "local_retained"
    FREE_OFFICIAL = "free_official"
    OPEN_IDENTIFIER = "open_identifier"
    MASSIVE_STARTER = "massive_starter"
    OPTIONAL_COMMERCIAL = "optional_commercial"


class LocalQualification(StrEnum):
    VERIFIED_INSUFFICIENT = "verified_insufficient"
    CORROBORATOR_ONLY = "corroborator_only"
    REQUIRES_BOUNDED_SAMPLE = "requires_bounded_sample"
    QUALIFIED = "qualified"


class SourceCapabilityV1(FrozenModel):
    source_id: str = Field(min_length=1)
    source_class: SourceClass
    lane: EvidenceLane
    local_qualification: LocalQualification
    stable_key_supported: bool
    effective_interval_supported: bool
    source_knowledge_time_supported: bool
    positive_admission_supported: bool
    additional_acquisition_requires_network: bool
    additional_acquisition_requires_credentials_or_agreement: bool
    evidence_references: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def fail_closed(self) -> "SourceCapabilityV1":
        if self.evidence_references != tuple(sorted(set(self.evidence_references))):
            raise ValueError("source evidence references must be unique and sorted")
        if self.limitations != tuple(sorted(set(self.limitations))):
            raise ValueError("source limitations must be unique and sorted")
        complete = (
            self.stable_key_supported
            and self.effective_interval_supported
            and self.source_knowledge_time_supported
        )
        if self.positive_admission_supported != (
            self.local_qualification is LocalQualification.QUALIFIED and complete
        ):
            raise ValueError("positive admission requires locally qualified complete evidence")
        return self


class SourceGapV1(FrozenModel):
    lane: EvidenceLane
    blocked_observation_count: int = Field(ge=0)
    denominator_name: str = Field(min_length=1)
    required_proof: tuple[str, ...] = Field(min_length=1)
    current_disposition: Literal["blocked"] = "blocked"

    @model_validator(mode="after")
    def canonical(self) -> "SourceGapV1":
        if self.required_proof != tuple(sorted(set(self.required_proof))):
            raise ValueError("required proof must be unique and sorted")
        return self


class ConservativeFirstBatchPolicyV1(FrozenModel):
    policy_id: Literal["prospective-single-common-core-v1"] = (
        "prospective-single-common-core-v1"
    )
    activation_rule: Literal[
        "first_xnys_session_after_all_five_lanes_are_qualified_and_frozen"
    ] = "first_xnys_session_after_all_five_lanes_are_qualified_and_frozen"
    denominator_rule: Literal[
        "all_ttm_ready_issuer_observations_on_or_after_the_frozen_activation_session"
    ] = "all_ttm_ready_issuer_observations_on_or_after_the_frozen_activation_session"
    security_selection_rule: Literal[
        "exactly_one_qualified_common_security_per_cik_at_signal_cutoff"
    ] = "exactly_one_qualified_common_security_per_cik_at_signal_cutoff"
    multi_common_disposition: Literal["quarantine"] = "quarantine"
    adr_ads_disposition: Literal["quarantine"] = "quarantine"
    foreign_ordinary_disposition: Literal["quarantine"] = "quarantine"
    preferred_fund_unit_warrant_right_disposition: Literal["exclude"] = "exclude"
    unknown_or_conflicting_disposition: Literal["quarantine"] = "quarantine"
    historical_backfill_from_future_observation_allowed: Literal[False] = False
    selection_may_use_outcomes: Literal[False] = False
    currently_activated: Literal[False] = False


class SecCashQualitySourceGapPlanV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    applicability_result_fingerprint: Literal[
        BASELINE_APPLICABILITY_RESULT_FINGERPRINT
    ] = BASELINE_APPLICABILITY_RESULT_FINGERPRINT
    historical_ttm_denominator_count: Literal[75391] = 75391
    historical_fully_applicable_count: Literal[0] = 0
    historical_identity_known_by_signal_open_count: Literal[0] = 0
    unique_common_observation_count: Literal[56542] = 56542
    multiple_common_observation_count: Literal[577] = 577
    gaps: tuple[SourceGapV1, ...]
    capabilities: tuple[SourceCapabilityV1, ...]
    prospective_policy: ConservativeFirstBatchPolicyV1
    forbidden_positive_proxies: tuple[
        Literal[
            "current_provider_snapshot_backcast",
            "sec_filer_identity_only",
            "ticker_or_name",
        ],
        ...,
    ] = (
        "current_provider_snapshot_backcast",
        "sec_filer_identity_only",
        "ticker_or_name",
    )
    network_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
    canonical_write_count: Literal[0] = 0
    outcome_access_count: Literal[0] = 0
    security_projection_authorized: Literal[False] = False
    factor_materialization_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    product_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualitySourceGapPlanV1":
        lane_order = tuple(EvidenceLane)
        if tuple(gap.lane for gap in self.gaps) != lane_order:
            raise ValueError("source gaps must cover every lane in canonical order")
        keys = tuple((item.lane.value, item.source_id) for item in self.capabilities)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("source capabilities must be unique and sorted")
        if self.forbidden_positive_proxies != tuple(
            sorted(self.forbidden_positive_proxies)
        ):
            raise ValueError("forbidden positive proxies differ")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("source-gap plan fingerprint differs")
        return self


class SecCashQualitySourceGapEvaluationV1(FrozenModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    plan_fingerprint: str = Field(pattern=_SHA256)
    qualified_lanes: tuple[EvidenceLane, ...]
    blocked_lanes: tuple[EvidenceLane, ...]
    prioritized_gaps: tuple[tuple[EvidenceLane, int], ...]
    historical_status: Literal["blocked_zero_applicable"] = "blocked_zero_applicable"
    historical_admitted_count: Literal[0] = 0
    prospective_status: Literal["registerable_not_activated"] = (
        "registerable_not_activated"
    )
    denominator_is_outcome_blind: Literal[True] = True
    downstream_authority_changed: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @model_validator(mode="after")
    def reconciles(self) -> "SecCashQualitySourceGapEvaluationV1":
        if set(self.qualified_lanes) & set(self.blocked_lanes):
            raise ValueError("source-gap lane cannot be both qualified and blocked")
        if set(self.qualified_lanes) | set(self.blocked_lanes) != set(EvidenceLane):
            raise ValueError("source-gap evaluation must cover every lane")
        if census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("source-gap evaluation fingerprint differs")
        return self
