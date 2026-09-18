"""Bounded live acquisition contracts for the frozen A-share warning batch."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import (
    ChinaAshareOfficialEvidenceAuthority,
)
from tip_api.contracts.common import normalize_utc_datetime


WARNING_ACQUISITION_PLAN_VERSION = "china-ashare-warning-evidence-acquisition-plan/1.0"
WARNING_ACQUISITION_CAPTURE_VERSION = "china-ashare-warning-evidence-acquisition-capture/1.0"
WARNING_ACQUISITION_CENSUS_VERSION = "china-ashare-warning-evidence-acquisition-census/1.0"


class ChinaAshareWarningAcquisitionStatus(StrEnum):
    PARSED_PENDING_ADJUDICATION = "parsed_pending_adjudication"
    PARSED_ZERO_RESULTS = "parsed_zero_results"
    TRANSPORT_BLOCKED = "transport_blocked"
    HTTP_BLOCKED = "http_blocked"
    CHALLENGE_BLOCKED = "challenge_blocked"
    SCHEMA_BLOCKED = "schema_blocked"
    SEMANTIC_BLOCKED = "semantic_blocked"


class ChinaAshareWarningAnnouncementLocatorV1(FrozenContract):
    document_id: str
    source_security_id: str
    document_url: str
    published_at: datetime
    publication_clock_observed: bool

    @field_validator("published_at")
    @classmethod
    def publication_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class ChinaAshareWarningAcquisitionPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal["china-ashare-warning-evidence-acquisition-plan/1.0"] = WARNING_ACQUISITION_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    input_reuse_package_fingerprint: str
    input_warning_batch_fingerprint: str
    cninfo_route_map_raw_sha256: str
    cninfo_route_map_capture_fingerprint: str
    logical_request_count: Literal[492] = 492
    sse_request_count: Literal[225] = 225
    cninfo_request_count: Literal[267] = 267
    minimum_request_interval_milliseconds: Literal[1000] = 1000
    maximum_retry_count_per_request: Literal[1] = 1
    maximum_http_attempts_per_request: Literal[2] = 2
    maximum_total_http_attempts: Literal[984] = 984
    retryable_http_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)
    challenge_is_terminal: Literal[True] = True
    alternative_authority_fallback_authorized: Literal[False] = False
    credentials_required: Literal[False] = False
    network_execution_authorized: Literal[True] = True
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("input_reuse_package_fingerprint", "input_warning_batch_fingerprint", "cninfo_route_map_raw_sha256", "cninfo_route_map_capture_fingerprint", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareWarningAcquisitionPlanV1":
        if self.retryable_http_statuses != tuple(sorted(set(self.retryable_http_statuses))):
            raise ValueError("warning retry statuses differ")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning acquisition plan fingerprint differs")
        return self


class ChinaAshareWarningAcquisitionCaptureV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    capture_version: Literal["china-ashare-warning-evidence-acquisition-capture/1.0"] = WARNING_ACQUISITION_CAPTURE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    warning_batch_fingerprint: str
    request_id: str
    stable_subject_id: str
    source_security_id: str
    authority: ChinaAshareOfficialEvidenceAuthority
    attempt_number: int = Field(ge=1, le=2)
    requested_url: str
    http_method: Literal["GET", "POST"]
    request_parameters: tuple[tuple[str, str], ...]
    retrieved_at: datetime
    final_url: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    raw_byte_size: int | None = Field(default=None, ge=1, le=16 * 1024 * 1024)
    raw_sha256: str | None = None
    status: ChinaAshareWarningAcquisitionStatus
    blocker_code: str | None = None
    detected_challenge_marker: str | None = None
    result_total: int | None = Field(default=None, ge=0)
    locators: tuple[ChinaAshareWarningAnnouncementLocatorV1, ...] = ()
    zero_results_prove_no_event: Literal[False] = False
    positive_event_evidence_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    logical_fingerprint: str

    @field_validator("plan_fingerprint", "warning_batch_fingerprint", "request_id", "raw_sha256", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha(value, info.field_name)

    @field_validator("retrieved_at")
    @classmethod
    def retrieval_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("request_parameters", mode="before")
    @classmethod
    def params_are_ordered(cls, value: Any) -> tuple[tuple[str, str], ...]:
        normalized = tuple((str(k), str(v)) for k, v in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("warning request parameters differ")
        return normalized

    @model_validator(mode="after")
    def capture_reconciles(self) -> "ChinaAshareWarningAcquisitionCaptureV1":
        captured = self.raw_sha256 is not None
        if captured != all(v is not None for v in (self.final_url, self.http_status, self.content_type, self.raw_byte_size)):
            raise ValueError("warning capture raw metadata differs")
        if self.status is ChinaAshareWarningAcquisitionStatus.TRANSPORT_BLOCKED and captured:
            raise ValueError("transport-blocked warning capture has bytes")
        if self.status is not ChinaAshareWarningAcquisitionStatus.TRANSPORT_BLOCKED and not captured:
            raise ValueError("non-transport warning capture lacks bytes")
        if self.status is ChinaAshareWarningAcquisitionStatus.CHALLENGE_BLOCKED and not self.detected_challenge_marker:
            raise ValueError("warning challenge capture lacks marker")
        if self.status is ChinaAshareWarningAcquisitionStatus.PARSED_ZERO_RESULTS:
            if self.result_total != 0 or self.locators:
                raise ValueError("warning zero-result capture differs")
        if self.status is ChinaAshareWarningAcquisitionStatus.PARSED_PENDING_ADJUDICATION and not self.locators:
            raise ValueError("warning parsed capture lacks locators")
        if self.locators != tuple(sorted(self.locators, key=lambda item: (item.published_at, item.document_id))):
            raise ValueError("warning locator order differs")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning capture fingerprint differs")
        return self


class ChinaAshareWarningAcquisitionCensusV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    census_version: Literal["china-ashare-warning-evidence-acquisition-census/1.0"] = WARNING_ACQUISITION_CENSUS_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    warning_batch_fingerprint: str
    capture_fingerprints: tuple[str, ...]
    completed_logical_unit_count: int = Field(ge=0, le=492)
    http_attempt_count: int = Field(ge=0, le=984)
    counts_by_status: tuple[tuple[str, int], ...]
    announcement_locator_count: int = Field(ge=0)
    observed_publication_clock_count: int = Field(ge=0)
    adjudication_ready_unit_count: int = Field(ge=0)
    zero_result_unit_count: int = Field(ge=0)
    stopped_early: bool
    stop_code: str | None = None
    outcome_read_count: Literal[0] = 0
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("plan_fingerprint", "warning_batch_fingerprint", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("capture_fingerprints", mode="before")
    @classmethod
    def captures_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item) for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("warning census captures differ")
        return normalized

    @model_validator(mode="after")
    def census_reconciles(self) -> "ChinaAshareWarningAcquisitionCensusV1":
        if self.stopped_early != (self.stop_code is not None):
            raise ValueError("warning census stop state differs")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning census fingerprint differs")
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
    if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
        raise ValueError(f"{field_name} must be lowercase sha256")
    return normalized
