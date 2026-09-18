"""Pagination-aware continuation contracts for official warning evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.china_ashare.v1.official_evidence_priority_plan import ChinaAshareOfficialEvidenceAuthority
from tip_api.contracts.china_ashare.v1.warning_evidence_acquisition import ChinaAshareWarningAnnouncementLocatorV1
from tip_api.contracts.common import normalize_utc_datetime


PLAN_VERSION = "china-ashare-warning-evidence-acquisition-plan/2.0"
PAGE_VERSION = "china-ashare-warning-evidence-page-capture/2.0"
CENSUS_VERSION = "china-ashare-warning-evidence-acquisition-census/2.0"


class ChinaAshareWarningPageStatus(StrEnum):
    PARSED = "parsed"
    TRANSPORT_BLOCKED = "transport_blocked"
    HTTP_BLOCKED = "http_blocked"
    CHALLENGE_BLOCKED = "challenge_blocked"
    SCHEMA_BLOCKED = "schema_blocked"
    TOTAL_DRIFT_BLOCKED = "total_drift_blocked"
    EMPTY_PAGE_BLOCKED = "empty_page_blocked"
    DUPLICATE_CONFLICT_BLOCKED = "duplicate_conflict_blocked"
    MAX_PAGES_BLOCKED = "max_pages_blocked"
    SECURITY_BINDING_BLOCKED = "security_binding_blocked"


class ChinaAshareWarningV2UnitV1(FrozenContract):
    ordinal: int = Field(ge=1, le=492)
    request_id: str
    source_security_id: str
    stable_subject_id: str
    authority: ChinaAshareOfficialEvidenceAuthority
    page_size: int
    maximum_pages: int
    imported_page1_capture_fingerprint: str | None = None
    imported_page1_raw_sha256: str | None = None
    imported_page1_total: int | None = Field(default=None, ge=0)
    imported_page1_locator_count: int | None = Field(default=None, ge=0)
    required_page_count: int | None = Field(default=None, ge=1)

    @field_validator("request_id", "imported_page1_capture_fingerprint", "imported_page1_raw_sha256")
    @classmethod
    def hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha(value, info.field_name)

    @model_validator(mode="after")
    def unit_reconciles(self) -> "ChinaAshareWarningV2UnitV1":
        expected_size, expected_max = ((100, 2) if self.authority is ChinaAshareOfficialEvidenceAuthority.SSE else (30, 4))
        if (self.page_size, self.maximum_pages) != (expected_size, expected_max):
            raise ValueError("warning V2 authority page policy differs")
        imported = self.imported_page1_capture_fingerprint is not None
        if imported != all(value is not None for value in (
            self.imported_page1_raw_sha256, self.imported_page1_total,
            self.imported_page1_locator_count, self.required_page_count,
        )):
            raise ValueError("warning V2 imported page binding differs")
        if imported:
            expected_pages = max(1, (self.imported_page1_total + self.page_size - 1) // self.page_size)
            if self.required_page_count != expected_pages:
                raise ValueError("warning V2 required pages differ")
            if expected_pages > self.maximum_pages:
                raise ValueError("warning V2 imported total exceeds page limit")
        return self


class ChinaAshareWarningAcquisitionPlanV2(FrozenContract):
    schema_version: Literal["2.0"] = "2.0"
    plan_version: Literal["china-ashare-warning-evidence-acquisition-plan/2.0"] = PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    input_reuse_package_fingerprint: str
    input_warning_batch_fingerprint: str
    input_v1_plan_fingerprint: str
    input_v1_partial_census_fingerprint: str
    input_v1_capture_set_fingerprint: str
    cninfo_route_map_raw_sha256: str
    units: tuple[ChinaAshareWarningV2UnitV1, ...]
    logical_unit_count: Literal[492] = 492
    imported_logical_unit_count: Literal[38] = 38
    imported_http_attempt_count: Literal[39] = 39
    maximum_pages_per_sse_unit: Literal[2] = 2
    maximum_pages_per_cninfo_unit: Literal[4] = 4
    theoretical_maximum_new_page_request_count: Literal[1405] = 1405
    maximum_new_page_request_count: Literal[580] = 580
    maximum_new_http_attempt_count: Literal[1160] = 1160
    maximum_total_http_attempt_count: Literal[1199] = 1199
    minimum_request_interval_milliseconds: Literal[1000] = 1000
    maximum_retry_count_per_page: Literal[1] = 1
    retryable_http_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)
    credentials_required: Literal[False] = False
    network_execution_authorized: Literal[True] = True
    outcome_read_count: Literal[0] = 0
    return_construction_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "input_reuse_package_fingerprint", "input_warning_batch_fingerprint",
        "input_v1_plan_fingerprint", "input_v1_partial_census_fingerprint",
        "input_v1_capture_set_fingerprint", "cninfo_route_map_raw_sha256", "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareWarningAcquisitionPlanV2":
        if tuple(item.ordinal for item in self.units) != tuple(range(1, 493)):
            raise ValueError("warning V2 unit order differs")
        if len({item.request_id for item in self.units}) != 492:
            raise ValueError("warning V2 request IDs differ")
        if sum(item.imported_page1_capture_fingerprint is not None for item in self.units) != 38:
            raise ValueError("warning V2 imported unit count differs")
        if self.retryable_http_statuses != tuple(sorted(set(self.retryable_http_statuses))):
            raise ValueError("warning V2 retry statuses differ")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning V2 plan fingerprint differs")
        return self


class ChinaAshareWarningPageCaptureV2(FrozenContract):
    schema_version: Literal["2.0"] = "2.0"
    capture_version: Literal["china-ashare-warning-evidence-page-capture/2.0"] = PAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    request_id: str
    source_security_id: str
    authority: ChinaAshareOfficialEvidenceAuthority
    page_number: int = Field(ge=1, le=4)
    page_size: int
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
    status: ChinaAshareWarningPageStatus
    blocker_code: str | None = None
    detected_challenge_marker: str | None = None
    reported_total: int | None = Field(default=None, ge=0)
    required_page_count: int | None = Field(default=None, ge=1)
    locators: tuple[ChinaAshareWarningAnnouncementLocatorV1, ...] = ()
    zero_results_prove_no_event: Literal[False] = False
    positive_event_evidence_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    logical_fingerprint: str

    @field_validator("plan_fingerprint", "request_id", "raw_sha256", "logical_fingerprint")
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
            raise ValueError("warning V2 params differ")
        return normalized

    @model_validator(mode="after")
    def capture_reconciles(self) -> "ChinaAshareWarningPageCaptureV2":
        captured = self.raw_sha256 is not None
        if captured != all(v is not None for v in (self.final_url, self.http_status, self.content_type, self.raw_byte_size)):
            raise ValueError("warning V2 raw metadata differs")
        if self.status is ChinaAshareWarningPageStatus.PARSED:
            if not captured or self.reported_total is None or self.required_page_count is None:
                raise ValueError("warning V2 parsed page differs")
            if self.reported_total > 0 and not self.locators:
                raise ValueError("warning V2 nonempty page lacks locators")
        if self.locators != tuple(sorted(self.locators, key=lambda item: (item.published_at, item.document_id))):
            raise ValueError("warning V2 locator order differs")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning V2 capture fingerprint differs")
        return self


class ChinaAshareWarningAcquisitionCensusV2(FrozenContract):
    schema_version: Literal["2.0"] = "2.0"
    census_version: Literal["china-ashare-warning-evidence-acquisition-census/2.0"] = CENSUS_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    completed_unit_count: int = Field(ge=0, le=492)
    imported_attempt_count: Literal[39] = 39
    new_attempt_count: int = Field(ge=0, le=1160)
    total_attempt_count: int = Field(ge=39, le=1199)
    new_page_request_count: int = Field(ge=0, le=580)
    deduplicated_locator_count: int = Field(ge=0)
    observed_publication_clock_count: int = Field(ge=0)
    adjudication_ready_unit_count: Literal[0] = 0
    stopped_early: bool
    stop_code: str | None = None
    logical_fingerprint: str

    @model_validator(mode="after")
    def census_reconciles(self) -> "ChinaAshareWarningAcquisitionCensusV2":
        if self.total_attempt_count != self.imported_attempt_count + self.new_attempt_count:
            raise ValueError("warning V2 total attempts differ")
        if self.stopped_early != (self.stop_code is not None):
            raise ValueError("warning V2 stop state differs")
        if logical_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("warning V2 census fingerprint differs")
        return self


def build_contract(contract_type: type[FrozenContract], **values: Any) -> Any:
    provisional = contract_type.model_construct(**values, logical_fingerprint="0" * 64)
    payload = provisional.model_dump(mode="python")
    payload["logical_fingerprint"] = logical_fingerprint(provisional)
    return contract_type.model_validate(payload)


def logical_fingerprint(value: FrozenContract) -> str:
    payload = value.model_dump(mode="json", exclude={"logical_fingerprint"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def capture_set_fingerprint(values: tuple[str, ...]) -> str:
    return hashlib.sha256(json.dumps(tuple(sorted(values)), separators=(",", ":")).encode()).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
        raise ValueError(f"{field_name} must be lowercase sha256")
    return normalized
