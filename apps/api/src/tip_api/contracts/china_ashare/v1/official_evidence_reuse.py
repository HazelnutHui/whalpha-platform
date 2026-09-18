"""Offline official-evidence reuse census and bounded warning batch contracts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareOfficialEvidenceBudgetFamily,
)
from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    EXPECTED_FIELDS_BY_PURPOSE,
    ChinaAshareOfficialEvidenceAuthority,
    ChinaAshareOfficialEvidenceRequestPurpose,
)
from tip_api.contracts.common import normalize_utc_datetime


REUSE_CENSUS_VERSION = "china-ashare-local-official-evidence-reuse-census/1.0"
WARNING_BATCH_VERSION = "china-ashare-warning-evidence-acquisition-batch/1.0"
REUSE_PACKAGE_VERSION = "china-ashare-local-official-evidence-reuse-package/1.0"


class ChinaAshareLocalEvidenceKind(StrEnum):
    OFFICIAL_SEARCH_CAPTURE = "official_search_capture"
    OFFICIAL_DOCUMENT_CAPTURE = "official_document_capture"
    CNINFO_CAPTURE = "cninfo_capture"


class ChinaAshareReuseDisposition(StrEnum):
    REUSABLE = "reusable"
    NETWORK_REQUIRED = "network_required"


class ChinaAshareWarningCaptureStatus(StrEnum):
    CAPTURED_PENDING_ADJUDICATION = "captured_pending_adjudication"
    TRANSPORT_BLOCKED = "transport_blocked"
    HTTP_BLOCKED = "http_blocked"
    CHALLENGE_BLOCKED = "challenge_blocked"
    SCHEMA_BLOCKED = "schema_blocked"


class ChinaAshareLocalEvidenceDescriptorV1(FrozenContract):
    evidence_id: str
    evidence_kind: ChinaAshareLocalEvidenceKind
    authority: ChinaAshareOfficialEvidenceAuthority
    source_package_fingerprint: str
    source_capture_fingerprint: str
    source_security_id: str | None = None
    stable_subject_id: str | None = None
    exact_security_binding: bool = False
    raw_sha256: str | None = None
    publication_clock: datetime | None = None
    publication_clock_observed: bool = False
    effective_from: date | None = None
    effective_to: date | None = None
    structured_fields: tuple[str, ...] = ()
    parse_status: str
    positive_evidence_eligible: bool = False

    @field_validator("evidence_id", "source_package_fingerprint", "source_capture_fingerprint", "raw_sha256")
    @classmethod
    def hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        if value is not None and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
            raise ValueError(f"{info.field_name} must be lowercase sha256")
        return value

    @field_validator("publication_clock")
    @classmethod
    def publication_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("structured_fields", mode="before")
    @classmethod
    def fields_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item) for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("structured evidence fields differ")
        return normalized

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "ChinaAshareLocalEvidenceDescriptorV1":
        complete = all((
            self.stable_subject_id,
            self.exact_security_binding,
            self.raw_sha256,
            self.publication_clock,
            self.publication_clock_observed,
            self.effective_from,
            self.effective_to,
            self.structured_fields,
        ))
        if self.positive_evidence_eligible != bool(complete):
            raise ValueError("positive evidence eligibility differs")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("local evidence interval is reversed")
        return self


class ChinaAshareLocalEvidenceInventoryV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    source_package_fingerprints: tuple[str, ...]
    evidence: tuple[ChinaAshareLocalEvidenceDescriptorV1, ...]
    evidence_count: int = Field(ge=0)
    positive_evidence_eligible_count: int = Field(ge=0)
    logical_fingerprint: str

    @model_validator(mode="after")
    def inventory_reconciles(self) -> "ChinaAshareLocalEvidenceInventoryV1":
        ids = tuple(item.evidence_id for item in self.evidence)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("local evidence order differs")
        if self.source_package_fingerprints != tuple(sorted(set(self.source_package_fingerprints))):
            raise ValueError("local evidence package fingerprints differ")
        if self.evidence_count != len(self.evidence):
            raise ValueError("local evidence count differs")
        if self.positive_evidence_eligible_count != sum(item.positive_evidence_eligible for item in self.evidence):
            raise ValueError("positive evidence count differs")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("local evidence inventory fingerprint differs")
        return self


class ChinaAshareOfficialEvidenceReuseDecisionV1(FrozenContract):
    request_id: str
    stable_subject_id: str
    source_security_id: str
    family: ChinaAshareOfficialEvidenceBudgetFamily
    purpose: ChinaAshareOfficialEvidenceRequestPurpose
    disposition: ChinaAshareReuseDisposition
    candidate_evidence_ids: tuple[str, ...] = ()
    reused_evidence_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...]

    @field_validator("request_id")
    @classmethod
    def request_id_is_sha256(cls, value: str) -> str:
        return _sha(value, "request_id")

    @model_validator(mode="after")
    def decision_reconciles(self) -> "ChinaAshareOfficialEvidenceReuseDecisionV1":
        for values in (self.candidate_evidence_ids, self.reused_evidence_ids, self.reason_codes):
            if values != tuple(sorted(set(values))):
                raise ValueError("reuse decision sequence differs")
        reusable = self.disposition is ChinaAshareReuseDisposition.REUSABLE
        if reusable != bool(self.reused_evidence_ids):
            raise ValueError("reuse decision disposition differs")
        if not self.reason_codes:
            raise ValueError("reuse decision lacks reason")
        return self


class ChinaAshareOfficialEvidenceReuseCensusV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    census_version: Literal["china-ashare-local-official-evidence-reuse-census/1.0"] = REUSE_CENSUS_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    input_priority_plan_package_fingerprint: str
    input_priority_plan_fingerprint: str
    local_evidence_inventory_fingerprint: str
    decisions: tuple[ChinaAshareOfficialEvidenceReuseDecisionV1, ...]
    request_count: int = Field(ge=0, le=2294)
    reusable_request_count: int = Field(ge=0)
    network_required_request_count: int = Field(ge=0)
    counts_by_family: tuple[tuple[str, int], ...]
    network_execution_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @model_validator(mode="after")
    def census_reconciles(self) -> "ChinaAshareOfficialEvidenceReuseCensusV1":
        ids = tuple(item.request_id for item in self.decisions)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("reuse census request order differs")
        reusable = sum(item.disposition is ChinaAshareReuseDisposition.REUSABLE for item in self.decisions)
        if (self.request_count != len(self.decisions) or self.reusable_request_count != reusable
                or self.network_required_request_count != self.request_count - reusable):
            raise ValueError("reuse census counts differ")
        expected = tuple(sorted(Counter(str(item.family) for item in self.decisions).items()))
        if self.counts_by_family != expected:
            raise ValueError("reuse census family counts differ")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("reuse census fingerprint differs")
        return self


class ChinaAshareWarningBatchRequestV1(FrozenContract):
    ordinal: int = Field(ge=1, le=492)
    request_id: str
    stable_subject_id: str
    source_security_id: str
    authority: ChinaAshareOfficialEvidenceAuthority
    purpose: Literal["risk_warning_transition_history"] = "risk_warning_transition_history"
    effective_from: date
    effective_to: date
    expected_fields: tuple[str, ...]
    maximum_response_bytes: Literal[16777216] = 16 * 1024 * 1024

    @field_validator("request_id")
    @classmethod
    def request_id_is_sha256(cls, value: str) -> str:
        return _sha(value, "request_id")

    @model_validator(mode="after")
    def request_reconciles(self) -> "ChinaAshareWarningBatchRequestV1":
        purpose = ChinaAshareOfficialEvidenceRequestPurpose.RISK_WARNING_TRANSITION_HISTORY
        if self.expected_fields != EXPECTED_FIELDS_BY_PURPOSE[purpose]:
            raise ValueError("warning expected fields differ")
        if self.effective_to < self.effective_from:
            raise ValueError("warning request interval is reversed")
        return self


class ChinaAshareWarningEvidenceBatchManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    batch_version: Literal["china-ashare-warning-evidence-acquisition-batch/1.0"] = WARNING_BATCH_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    input_priority_plan_package_fingerprint: str
    input_reuse_census_fingerprint: str
    requests: tuple[ChinaAshareWarningBatchRequestV1, ...]
    logical_request_limit: Literal[492] = 492
    maximum_retry_count_per_request: Literal[1] = 1
    maximum_http_attempts_per_request: Literal[2] = 2
    maximum_total_http_attempts: Literal[984] = 984
    minimum_request_interval_milliseconds: Literal[1000] = 1000
    sequential_execution_required: Literal[True] = True
    credentials_required: Literal[False] = False
    challenge_markers: tuple[str, ...] = ("acw_sc__v2", "document.cookie", "enable javascript")
    challenge_is_terminal: Literal[True] = True
    network_execution_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @model_validator(mode="after")
    def batch_reconciles(self) -> "ChinaAshareWarningEvidenceBatchManifestV1":
        if len(self.requests) != 492:
            raise ValueError("warning batch must contain all 492 logical requests")
        ids = tuple(item.request_id for item in self.requests)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("warning batch request order differs")
        if tuple(item.ordinal for item in self.requests) != tuple(range(1, 493)):
            raise ValueError("warning batch ordinals differ")
        for item in self.requests:
            expected = ChinaAshareOfficialEvidenceAuthority.SSE if item.source_security_id.startswith("sh.") else ChinaAshareOfficialEvidenceAuthority.CNINFO
            if item.authority is not expected:
                raise ValueError("warning batch authority route differs")
        if self.challenge_markers != tuple(sorted(set(self.challenge_markers))):
            raise ValueError("challenge marker order differs")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning batch fingerprint differs")
        return self


class ChinaAshareWarningRawCaptureV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    batch_fingerprint: str
    request_id: str
    attempt_number: int = Field(ge=1, le=2)
    authority: ChinaAshareOfficialEvidenceAuthority
    requested_url: str
    final_url: str | None = None
    retrieved_at: datetime
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    raw_byte_size: int | None = Field(default=None, ge=1, le=16 * 1024 * 1024)
    raw_sha256: str | None = None
    status: ChinaAshareWarningCaptureStatus
    blocker_code: str | None = None
    detected_challenge_marker: str | None = None
    positive_evidence_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0

    @field_validator("batch_fingerprint", "request_id", "raw_sha256")
    @classmethod
    def hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha(value, info.field_name)

    @field_validator("retrieved_at")
    @classmethod
    def retrieval_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def capture_reconciles(self) -> "ChinaAshareWarningRawCaptureV1":
        captured = self.raw_sha256 is not None
        if captured != all(v is not None for v in (self.final_url, self.http_status, self.content_type, self.raw_byte_size)):
            raise ValueError("warning raw metadata differs")
        if self.status is ChinaAshareWarningCaptureStatus.CHALLENGE_BLOCKED and not self.detected_challenge_marker:
            raise ValueError("challenge capture lacks marker")
        return self


class ChinaAshareWarningAdjudicationInputV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    stable_subject_id: str
    source_security_id: str
    authority: ChinaAshareOfficialEvidenceAuthority
    search_raw_sha256: str
    document_id: str
    document_url: str
    document_raw_sha256: str
    published_at: datetime
    publication_clock_observed: Literal[True] = True
    effective_from: date
    effective_to: date
    event_kind: str
    warning_subtype: str
    exact_security_binding: Literal[True] = True
    ticker_only_evidence_authorized: Literal[False] = False
    body_heuristic_evidence_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0

    @field_validator("request_id", "search_raw_sha256", "document_raw_sha256")
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("published_at")
    @classmethod
    def publication_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def adjudication_reconciles(self) -> "ChinaAshareWarningAdjudicationInputV1":
        if self.effective_to < self.effective_from:
            raise ValueError("warning adjudication interval is reversed")
        return self


class ChinaAshareOfficialEvidenceReusePackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal["china-ashare-local-official-evidence-reuse-package/1.0"] = REUSE_PACKAGE_VERSION
    input_priority_plan_package_fingerprint: str
    inventory_fingerprint: str
    census_fingerprint: str
    warning_batch_fingerprint: str
    files: tuple[tuple[str, int, str], ...]
    logical_fingerprint: str

    @model_validator(mode="after")
    def package_reconciles(self) -> "ChinaAshareOfficialEvidenceReusePackageManifestV1":
        if tuple(path for path, _, _ in self.files) != tuple(sorted({path for path, _, _ in self.files})):
            raise ValueError("reuse package files differ")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("reuse package fingerprint differs")
        return self


def build_contract(contract_type: type[FrozenContract], **values: Any) -> Any:
    provisional = contract_type.model_construct(**values, logical_fingerprint="0" * 64)
    payload = provisional.model_dump(mode="python")
    payload["logical_fingerprint"] = logical_fingerprint(provisional)
    return contract_type.model_validate(payload)


def logical_fingerprint(value: FrozenContract) -> str:
    payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must be lowercase sha256")
    return normalized
