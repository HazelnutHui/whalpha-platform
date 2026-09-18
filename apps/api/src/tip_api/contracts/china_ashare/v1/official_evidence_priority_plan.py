"""Offline-only priority plan for bounded official A-share evidence work."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
    OFFICIAL_EVIDENCE_PRIORITY,
)
from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract


OFFICIAL_EVIDENCE_PRIORITY_PLAN_VERSION = (
    "china-ashare-official-evidence-priority-plan/1.0"
)
OFFICIAL_EVIDENCE_PRIORITY_PACKAGE_VERSION = (
    "china-ashare-official-evidence-priority-package/1.0"
)


class ChinaAshareOfficialEvidenceAuthority(StrEnum):
    SSE = "sse"
    SZSE = "szse"
    CNINFO = "cninfo"


class ChinaAshareOfficialEvidenceRequestPurpose(StrEnum):
    RISK_WARNING_TRANSITION_HISTORY = "risk_warning_transition_history"
    LISTING_STATUS_INTERVAL_HISTORY = "listing_status_interval_history"
    RELISTING_OR_RESUMPTION_HISTORY = "relisting_or_resumption_history"
    TERMINATION_DECISION_HISTORY = "termination_decision_history"
    DELISTING_PERIOD_AND_LAST_TRADING_DAY = (
        "delisting_period_and_last_trading_day"
    )
    ORIGINAL_LISTING_STAGE_HISTORY = "original_listing_stage_history"


PURPOSE_BY_FAMILY = {
    ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING: (
        ChinaAshareOfficialEvidenceRequestPurpose.RISK_WARNING_TRANSITION_HISTORY,
    ),
    ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE: tuple(
        sorted(
            (
                ChinaAshareOfficialEvidenceRequestPurpose.LISTING_STATUS_INTERVAL_HISTORY,
                ChinaAshareOfficialEvidenceRequestPurpose.RELISTING_OR_RESUMPTION_HISTORY,
                ChinaAshareOfficialEvidenceRequestPurpose.TERMINATION_DECISION_HISTORY,
                ChinaAshareOfficialEvidenceRequestPurpose.DELISTING_PERIOD_AND_LAST_TRADING_DAY,
            ),
            key=str,
        )
    ),
    ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE: (
        ChinaAshareOfficialEvidenceRequestPurpose.ORIGINAL_LISTING_STAGE_HISTORY,
    ),
}

EXPECTED_FIELDS_BY_PURPOSE = {
    ChinaAshareOfficialEvidenceRequestPurpose.RISK_WARNING_TRANSITION_HISTORY: (
        "document_id",
        "document_url",
        "effective_from",
        "effective_to",
        "event_kind",
        "published_at",
        "raw_sha256",
        "warning_subtype",
    ),
    ChinaAshareOfficialEvidenceRequestPurpose.LISTING_STATUS_INTERVAL_HISTORY: (
        "document_id",
        "document_url",
        "effective_from",
        "effective_to",
        "listing_status",
        "published_at",
        "raw_sha256",
    ),
    ChinaAshareOfficialEvidenceRequestPurpose.RELISTING_OR_RESUMPTION_HISTORY: (
        "document_id",
        "document_url",
        "effective_from",
        "event_kind",
        "published_at",
        "raw_sha256",
    ),
    ChinaAshareOfficialEvidenceRequestPurpose.TERMINATION_DECISION_HISTORY: (
        "document_id",
        "document_url",
        "published_at",
        "raw_sha256",
        "termination_decision_date",
        "termination_effective_date",
    ),
    ChinaAshareOfficialEvidenceRequestPurpose.DELISTING_PERIOD_AND_LAST_TRADING_DAY: (
        "delisting_period_end",
        "delisting_period_start",
        "document_id",
        "document_url",
        "last_trading_day",
        "published_at",
        "raw_sha256",
    ),
    ChinaAshareOfficialEvidenceRequestPurpose.ORIGINAL_LISTING_STAGE_HISTORY: (
        "board",
        "document_id",
        "document_url",
        "ipo_special_stage_end",
        "ipo_special_stage_start",
        "original_listing_date",
        "published_at",
        "raw_sha256",
        "special_price_limit_regime",
    ),
}


class ChinaAshareOfficialEvidenceAuthoritySpecV1(FrozenContract):
    authority: ChinaAshareOfficialEvidenceAuthority
    official_base_url: str
    credentials_required: Literal[False] = False
    aggregate_source: Literal[False] = False

    @model_validator(mode="after")
    def authority_reconciles(self) -> "ChinaAshareOfficialEvidenceAuthoritySpecV1":
        expected = {
            ChinaAshareOfficialEvidenceAuthority.SSE: "https://www.sse.com.cn/",
            ChinaAshareOfficialEvidenceAuthority.SZSE: "https://www.szse.cn/",
            ChinaAshareOfficialEvidenceAuthority.CNINFO: "https://www.cninfo.com.cn/",
        }[self.authority]
        if self.official_base_url != expected:
            raise ValueError("official authority base URL differs")
        return self


class ChinaAshareOfficialEvidencePriorityRequestV1(FrozenContract):
    request_id: str
    stable_subject_id: str
    source_security_id: str = Field(pattern=r"^(?:sh|sz)\.[0-9]{6}$")
    instrument_id: UUID | None = None
    partition_index: int = Field(ge=0, le=108)
    family: ChinaAshareOfficialEvidenceBudgetFamily
    purpose: ChinaAshareOfficialEvidenceRequestPurpose
    effective_from: date
    effective_to: date
    candidate_authorities: tuple[ChinaAshareOfficialEvidenceAuthority, ...] = Field(
        min_length=2, max_length=2
    )
    expected_fields: tuple[str, ...] = Field(min_length=1)
    maximum_acquisition_attempt_count: Literal[1] = 1
    failure_disposition: Literal["quarantine_unchanged"] = "quarantine_unchanged"
    source_available_at_must_be_observed: Literal[True] = True
    evidence_may_be_reused_by_bound_adjudications: Literal[True] = True

    @field_validator("request_id")
    @classmethod
    def request_id_is_sha256(cls, value: str) -> str:
        return _sha(value, "request_id")

    @field_validator("candidate_authorities", "expected_fields", mode="before")
    @classmethod
    def sequences_are_unique(cls, value: Any) -> tuple[Any, ...]:
        normalized = tuple(value)
        if len(normalized) != len(set(normalized)):
            raise ValueError("official evidence request sequence differs")
        return normalized

    @model_validator(mode="after")
    def request_reconciles(self) -> "ChinaAshareOfficialEvidencePriorityRequestV1":
        if self.family is ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION:
            raise ValueError("corporate-action requests are not authorized")
        if self.purpose not in PURPOSE_BY_FAMILY[self.family]:
            raise ValueError("official evidence request purpose differs")
        if self.expected_fields != EXPECTED_FIELDS_BY_PURPOSE[self.purpose]:
            raise ValueError("official evidence expected fields differ")
        if self.effective_to < self.effective_from:
            raise ValueError("official evidence request interval is reversed")
        allowed = (
            (
                ChinaAshareOfficialEvidenceAuthority.SSE,
                ChinaAshareOfficialEvidenceAuthority.CNINFO,
            )
            if self.source_security_id.startswith("sh.")
            else (
                ChinaAshareOfficialEvidenceAuthority.SZSE,
                ChinaAshareOfficialEvidenceAuthority.CNINFO,
            )
        )
        if self.candidate_authorities != allowed:
            raise ValueError("official evidence candidate authorities differ")
        expected_subject = (
            f"instrument:{self.instrument_id}"
            if self.instrument_id is not None
            else f"quarantined-source-security:{self.source_security_id}"
        )
        if self.stable_subject_id != expected_subject:
            raise ValueError("official evidence stable subject differs")
        expected_id = official_evidence_request_id(
            stable_subject_id=self.stable_subject_id,
            family=self.family,
            purpose=self.purpose,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
        )
        if self.request_id != expected_id:
            raise ValueError("official evidence stable request ID differs")
        return self


class ChinaAshareOfficialEvidencePriorityTierV1(FrozenContract):
    priority: int = Field(ge=1, le=3)
    family: ChinaAshareOfficialEvidenceBudgetFamily
    deduplicated_security_count: int = Field(ge=0)
    requests_per_security: int = Field(ge=1, le=4)
    maximum_request_count: int = Field(ge=0)

    @model_validator(mode="after")
    def tier_reconciles(self) -> "ChinaAshareOfficialEvidencePriorityTierV1":
        if self.family is not OFFICIAL_EVIDENCE_PRIORITY[self.priority - 1]:
            raise ValueError("official evidence tier priority differs")
        if self.maximum_request_count != (
            self.deduplicated_security_count * self.requests_per_security
        ):
            raise ValueError("official evidence tier budget differs")
        return self


class ChinaAshareOfficialEvidencePriorityPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-official-evidence-priority-plan/1.0"
    ] = OFFICIAL_EVIDENCE_PRIORITY_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    input_package_fingerprint: str
    input_manifest_physical_sha256: str
    input_plan_fingerprint: str
    input_global_census_fingerprint: str
    input_candidate_set_fingerprint: str
    interval_start: date
    interval_end: date
    authority_registry: tuple[ChinaAshareOfficialEvidenceAuthoritySpecV1, ...] = Field(
        min_length=3, max_length=3
    )
    tiers: tuple[ChinaAshareOfficialEvidencePriorityTierV1, ...] = Field(
        min_length=3, max_length=3
    )
    requests: tuple[ChinaAshareOfficialEvidencePriorityRequestV1, ...]
    maximum_official_request_count: int = Field(ge=0, le=2294)
    corporate_action_candidate_security_count: int = Field(ge=0)
    corporate_action_candidate_window_count: int = Field(ge=0)
    corporate_action_request_count: Literal[0] = 0
    corporate_action_disposition: Literal["quarantine_unchanged"] = (
        "quarantine_unchanged"
    )
    network_execution_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "input_package_fingerprint",
        "input_manifest_physical_sha256",
        "input_plan_fingerprint",
        "input_global_census_fingerprint",
        "input_candidate_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareOfficialEvidencePriorityPlanV1":
        if self.interval_end < self.interval_start:
            raise ValueError("official evidence priority interval is reversed")
        if tuple(item.authority for item in self.authority_registry) != (
            ChinaAshareOfficialEvidenceAuthority.SSE,
            ChinaAshareOfficialEvidenceAuthority.SZSE,
            ChinaAshareOfficialEvidenceAuthority.CNINFO,
        ):
            raise ValueError("official evidence authority registry differs")
        if tuple(item.priority for item in self.tiers) != (1, 2, 3):
            raise ValueError("official evidence priority tiers differ")
        keys = tuple(_request_sort_key(item) for item in self.requests)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("official evidence requests differ")
        if len({item.request_id for item in self.requests}) != len(self.requests):
            raise ValueError("official evidence stable request IDs differ")
        if any(
            item.effective_from != self.interval_start
            or item.effective_to != self.interval_end
            for item in self.requests
        ):
            raise ValueError("official evidence request interval differs")
        family_counts = Counter(item.family for item in self.requests)
        if tuple(family_counts[item.family] for item in self.tiers) != tuple(
            item.maximum_request_count for item in self.tiers
        ):
            raise ValueError("official evidence family request counts differ")
        security_counts = {
            family: len(
                {
                    item.source_security_id
                    for item in self.requests
                    if item.family is family
                }
            )
            for family in OFFICIAL_EVIDENCE_PRIORITY
        }
        if tuple(security_counts[item.family] for item in self.tiers) != tuple(
            item.deduplicated_security_count for item in self.tiers
        ):
            raise ValueError("official evidence security counts differ")
        if len(self.requests) != self.maximum_official_request_count or sum(
            item.maximum_request_count for item in self.tiers
        ) != self.maximum_official_request_count:
            raise ValueError("official evidence maximum request budget differs")
        if official_evidence_priority_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("official evidence priority plan fingerprint differs")
        return self


class ChinaAshareOfficialEvidencePriorityPackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-official-evidence-priority-package/1.0"
    ] = OFFICIAL_EVIDENCE_PRIORITY_PACKAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    input_package_fingerprint: str
    plan_fingerprint: str
    plan_byte_size: int = Field(ge=1)
    plan_physical_sha256: str
    request_count: int = Field(ge=0, le=2294)
    network_execution_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "input_package_fingerprint",
        "plan_fingerprint",
        "plan_physical_sha256",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAshareOfficialEvidencePriorityPackageManifestV1":
        if official_evidence_priority_package_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("official evidence priority package fingerprint differs")
        return self


def build_official_evidence_priority_plan(**values: Any):
    return _build(
        ChinaAshareOfficialEvidencePriorityPlanV1,
        official_evidence_priority_plan_fingerprint,
        values,
    )


def build_official_evidence_priority_package_manifest(**values: Any):
    return _build(
        ChinaAshareOfficialEvidencePriorityPackageManifestV1,
        official_evidence_priority_package_fingerprint,
        values,
    )


def official_evidence_request_id(
    *, stable_subject_id, family, purpose, effective_from, effective_to
) -> str:
    return _fingerprint(
        {
            "request_definition_version": OFFICIAL_EVIDENCE_PRIORITY_PLAN_VERSION,
            "stable_subject_id": stable_subject_id,
            "family": str(family),
            "purpose": str(purpose),
            "effective_from": effective_from,
            "effective_to": effective_to,
        }
    )


def official_evidence_priority_plan_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def official_evidence_priority_package_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _request_sort_key(item) -> tuple[int, str, str]:
    return (
        OFFICIAL_EVIDENCE_PRIORITY.index(item.family),
        item.source_security_id,
        str(item.purpose),
    )


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
