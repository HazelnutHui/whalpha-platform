"""Candidate-driven official-evidence budget and conservative lane census."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract


CONSERVATIVE_RECONSTRUCTION_PLAN_VERSION = (
    "china-ashare-conservative-reconstruction-plan/1.0"
)
CONSERVATIVE_RECONSTRUCTION_PARTITION_VERSION = (
    "china-ashare-conservative-reconstruction-partition/1.0"
)
CONSERVATIVE_RECONSTRUCTION_CENSUS_VERSION = (
    "china-ashare-conservative-reconstruction-census/1.0"
)
PRICE_LIMIT_SMOKE_VERSION = "china-ashare-price-limit-smoke/1.0"


class ChinaAshareOfficialEvidenceBudgetFamily(StrEnum):
    RISK_WARNING = "risk_warning"
    LIFECYCLE = "lifecycle"
    LISTING_STAGE = "listing_stage"
    CORPORATE_ACTION = "corporate_action"


OFFICIAL_EVIDENCE_PRIORITY = (
    ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
    ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
    ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
)


class ChinaAshareConservativeEvidenceCandidateV1(FrozenContract):
    source_security_id: str
    instrument_id: UUID | None = None
    partition_index: int = Field(ge=0, le=108)
    source_target_quarantined: bool
    observed_state_count: int = Field(ge=0)
    warning_present_state_count: int = Field(ge=0)
    warning_unknown_state_count: int = Field(ge=0)
    trading_status_unknown_state_count: int = Field(ge=0)
    factor_change_candidate_count: int = Field(ge=0)
    terminal_boundary_candidate: bool
    listing_stage_uncertain: bool
    requested_families: tuple[ChinaAshareOfficialEvidenceBudgetFamily, ...] = ()
    maximum_official_request_count: int = Field(ge=0)

    @field_validator("requested_families", mode="before")
    @classmethod
    def families_are_ordered(cls, value: Any):
        normalized = tuple(value)
        if normalized != tuple(sorted(set(normalized), key=lambda item: str(item))):
            raise ValueError("candidate evidence families differ")
        return normalized

    @model_validator(mode="after")
    def candidate_reconciles(self) -> "ChinaAshareConservativeEvidenceCandidateV1":
        if self.source_target_quarantined != (self.instrument_id is None):
            raise ValueError("candidate identity isolation differs")
        expected = sum(
            {
                ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING: 1,
                ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE: 4,
                ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE: 1,
                ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION: 0,
            }[item]
            for item in self.requested_families
        )
        if expected != self.maximum_official_request_count:
            raise ValueError("candidate official request budget differs")
        return self


class ChinaAshareOfficialEvidenceBudgetTierV1(FrozenContract):
    priority: int = Field(ge=1, le=3)
    family: ChinaAshareOfficialEvidenceBudgetFamily
    deduplicated_security_count: int = Field(ge=0)
    maximum_requests_per_security: int = Field(ge=1, le=4)
    maximum_request_count: int = Field(ge=0)

    @model_validator(mode="after")
    def budget_reconciles(self) -> "ChinaAshareOfficialEvidenceBudgetTierV1":
        expected = OFFICIAL_EVIDENCE_PRIORITY[self.priority - 1]
        if self.family is not expected:
            raise ValueError("official evidence budget priority differs")
        if self.maximum_request_count != (
            self.deduplicated_security_count * self.maximum_requests_per_security
        ):
            raise ValueError("official evidence tier request budget differs")
        return self


class ChinaAshareConservativeReconstructionPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-conservative-reconstruction-plan/1.0"
    ] = CONSERVATIVE_RECONSTRUCTION_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    source_expansion_plan_fingerprint: str
    population_package_fingerprint: str
    normalized_run_fingerprint: str
    normalized_partition_manifest_fingerprints: tuple[str, ...] = Field(
        min_length=109, max_length=109
    )
    market_mechanics_package_fingerprint: str
    price_limit_resolver_plan_fingerprint: str
    cninfo_sample_plan_fingerprint: str
    cninfo_sample_replay_set_fingerprint: str
    interval_start: date
    interval_end: date
    target_sessions: tuple[date, ...] = Field(min_length=1)
    official_evidence_priority: tuple[
        ChinaAshareOfficialEvidenceBudgetFamily, ...
    ] = OFFICIAL_EVIDENCE_PRIORITY
    official_confirmed_requires_all_families: Literal[True] = True
    provider_provisional_as_operated: Literal[False] = False
    provider_provisional_excludes_warning_windows: Literal[True] = True
    provider_provisional_quarantines_action_windows: Literal[True] = True
    provider_provisional_quarantines_terminal_boundaries: Literal[True] = True
    provider_provisional_quarantines_unknown_states: Literal[True] = True
    provider_provisional_reconstructs_normal_limits_from_official_mechanics: Literal[
        True
    ] = True
    provider_provisional_personal_research_candidate_only: Literal[True] = True
    maximum_requests_per_warning_candidate: Literal[1] = 1
    maximum_requests_per_lifecycle_candidate: Literal[4] = 4
    maximum_requests_per_listing_candidate: Literal[1] = 1
    maximum_requests_per_action_candidate: Literal[0] = 0
    action_candidates_remain_isolated_without_official_requests: Literal[True] = True
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "source_expansion_plan_fingerprint",
        "population_package_fingerprint",
        "normalized_run_fingerprint",
        "market_mechanics_package_fingerprint",
        "price_limit_resolver_plan_fingerprint",
        "cninfo_sample_plan_fingerprint",
        "cninfo_sample_replay_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("normalized_partition_manifest_fingerprints", mode="before")
    @classmethod
    def partitions_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        for item in normalized:
            _sha(item, "normalized_partition_manifest_fingerprints")
        return normalized

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareConservativeReconstructionPlanV1":
        if self.interval_end < self.interval_start:
            raise ValueError("conservative reconstruction interval is reversed")
        if self.target_sessions != tuple(sorted(set(self.target_sessions))):
            raise ValueError("conservative reconstruction sessions differ")
        if (
            self.target_sessions[0] != self.interval_start
            or self.target_sessions[-1] != self.interval_end
        ):
            raise ValueError("conservative reconstruction session bounds differ")
        if self.official_evidence_priority != OFFICIAL_EVIDENCE_PRIORITY:
            raise ValueError("official evidence priority differs")
        if conservative_reconstruction_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("conservative reconstruction plan fingerprint differs")
        return self


class ChinaAshareConservativePartitionCensusV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    census_version: Literal[
        "china-ashare-conservative-reconstruction-partition/1.0"
    ] = CONSERVATIVE_RECONSTRUCTION_PARTITION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    partition_index: int = Field(ge=0, le=108)
    normalized_partition_manifest_fingerprint: str
    target_count: int = Field(ge=1, le=50)
    resolved_target_count: int = Field(ge=0, le=50)
    isolated_target_count: int = Field(ge=0, le=50)
    state_count: int = Field(ge=0)
    provisional_candidate_included_state_count: int = Field(ge=0)
    provisional_candidate_excluded_state_count: int = Field(ge=0)
    provisional_quarantined_state_count: int = Field(ge=0)
    warning_present_state_count: int = Field(ge=0)
    warning_unknown_state_count: int = Field(ge=0)
    trading_status_unknown_state_count: int = Field(ge=0)
    factor_change_candidate_window_count: int = Field(ge=0)
    terminal_boundary_candidate_security_count: int = Field(ge=0, le=50)
    resolved_empty_state_target_count: int = Field(ge=0, le=50)
    warning_candidate_security_count: int = Field(ge=0, le=50)
    lifecycle_candidate_security_count: int = Field(ge=0, le=50)
    listing_stage_candidate_security_count: int = Field(ge=0, le=50)
    action_candidate_security_count: int = Field(ge=0, le=50)
    candidate_records: tuple[ChinaAshareConservativeEvidenceCandidateV1, ...] = ()
    candidate_set_fingerprint: str
    maximum_official_request_count: int = Field(ge=0)
    outcome_read_count: Literal[0] = 0
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "normalized_partition_manifest_fingerprint",
        "candidate_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def census_reconciles(self) -> "ChinaAshareConservativePartitionCensusV1":
        if self.resolved_target_count + self.isolated_target_count != self.target_count:
            raise ValueError("partition target counts differ")
        if (
            self.provisional_candidate_included_state_count
            + self.provisional_candidate_excluded_state_count
            + self.provisional_quarantined_state_count
            != self.state_count
        ):
            raise ValueError("partition provisional state counts differ")
        if (
            candidate_set_fingerprint(self.candidate_records)
            != self.candidate_set_fingerprint
        ):
            raise ValueError("partition candidate set fingerprint differs")
        if (
            sum(
                item.maximum_official_request_count
                for item in self.candidate_records
            )
            != self.maximum_official_request_count
        ):
            raise ValueError("partition official request budget differs")
        if conservative_partition_census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("partition census fingerprint differs")
        return self


class ChinaAshareConservativeReconstructionCensusV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    census_version: Literal[
        "china-ashare-conservative-reconstruction-census/1.0"
    ] = CONSERVATIVE_RECONSTRUCTION_CENSUS_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    partition_census_fingerprints: tuple[str, ...] = Field(
        min_length=109, max_length=109
    )
    target_count: int = Field(ge=1)
    resolved_target_count: int = Field(ge=0)
    isolated_target_count: int = Field(ge=0)
    state_count: int = Field(ge=0)
    provisional_candidate_included_state_count: int = Field(ge=0)
    provisional_candidate_excluded_state_count: int = Field(ge=0)
    provisional_quarantined_state_count: int = Field(ge=0)
    warning_present_state_count: int = Field(ge=0)
    warning_unknown_state_count: int = Field(ge=0)
    trading_status_unknown_state_count: int = Field(ge=0)
    factor_change_candidate_window_count: int = Field(ge=0)
    terminal_boundary_candidate_security_count: int = Field(ge=0)
    resolved_empty_state_target_count: int = Field(ge=0)
    official_confirmed_full_family_security_count: Literal[0] = 0
    warning_candidate_security_count: int = Field(ge=0)
    lifecycle_candidate_security_count: int = Field(ge=0)
    listing_stage_candidate_security_count: int = Field(ge=0)
    action_candidate_security_count: int = Field(ge=0)
    candidate_security_count: int = Field(ge=0)
    candidate_set_fingerprint: str
    official_request_budget_by_priority: tuple[
        ChinaAshareOfficialEvidenceBudgetTierV1, ...
    ] = Field(min_length=3, max_length=3)
    maximum_official_request_count: int = Field(ge=0)
    blind_baseline_request_count: int = Field(ge=1)
    avoided_request_count: int = Field(ge=0)
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "partition_census_fingerprints",
        "candidate_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: Any, info: Any):
        if isinstance(value, (tuple, list)):
            return tuple(_sha(item, info.field_name) for item in value)
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def census_reconciles(self) -> "ChinaAshareConservativeReconstructionCensusV1":
        if self.resolved_target_count + self.isolated_target_count != self.target_count:
            raise ValueError("global target counts differ")
        if (
            self.provisional_candidate_included_state_count
            + self.provisional_candidate_excluded_state_count
            + self.provisional_quarantined_state_count
            != self.state_count
        ):
            raise ValueError("global provisional state counts differ")
        if (
            self.blind_baseline_request_count
            - self.maximum_official_request_count
            != self.avoided_request_count
        ):
            raise ValueError("avoided official request count differs")
        if tuple(item.priority for item in self.official_request_budget_by_priority) != (
            1,
            2,
            3,
        ):
            raise ValueError("official evidence budget tiers differ")
        if sum(
            item.maximum_request_count
            for item in self.official_request_budget_by_priority
        ) != self.maximum_official_request_count:
            raise ValueError("official evidence budget total differs")
        if conservative_reconstruction_census_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("global census fingerprint differs")
        return self


class ChinaAsharePriceLimitSmokeV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    smoke_version: Literal[
        "china-ashare-price-limit-smoke/1.0"
    ] = PRICE_LIMIT_SMOKE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    source_security_id: Literal["sz.000001"] = "sz.000001"
    instrument_id: UUID
    cninfo_plan_fingerprint: str
    cninfo_replay_set_fingerprint: str
    normalized_partition_manifest_fingerprint: str
    price_limit_resolver_plan_fingerprint: str
    state_count: int = Field(ge=1)
    resolved_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    resolution_set_fingerprint: str
    official_zero_event_evidence: Literal[True] = True
    as_operated: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "cninfo_plan_fingerprint",
        "cninfo_replay_set_fingerprint",
        "normalized_partition_manifest_fingerprint",
        "price_limit_resolver_plan_fingerprint",
        "resolution_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def smoke_reconciles(self) -> "ChinaAsharePriceLimitSmokeV1":
        if self.resolved_count + self.quarantined_count != self.state_count:
            raise ValueError("price-limit smoke counts differ")
        if price_limit_smoke_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("price-limit smoke fingerprint differs")
        return self


def build_conservative_reconstruction_plan(**values: Any):
    return _build(
        ChinaAshareConservativeReconstructionPlanV1,
        conservative_reconstruction_plan_fingerprint,
        values,
    )


def build_conservative_partition_census(**values: Any):
    return _build(
        ChinaAshareConservativePartitionCensusV1,
        conservative_partition_census_fingerprint,
        values,
    )


def build_conservative_reconstruction_census(**values: Any):
    return _build(
        ChinaAshareConservativeReconstructionCensusV1,
        conservative_reconstruction_census_fingerprint,
        values,
    )


def build_price_limit_smoke(**values: Any):
    return _build(ChinaAsharePriceLimitSmokeV1, price_limit_smoke_fingerprint, values)


def candidate_set_fingerprint(values) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in values])


def conservative_reconstruction_plan_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def conservative_partition_census_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def conservative_reconstruction_census_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def price_limit_smoke_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _build(model, fingerprint, values):
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    payload = provisional.model_dump(mode="python")
    payload["logical_fingerprint"] = fingerprint(provisional)
    return model.model_validate(payload)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
