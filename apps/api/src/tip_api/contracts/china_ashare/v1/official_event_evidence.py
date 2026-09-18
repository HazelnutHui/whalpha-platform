"""Bounded official-event evidence plan and checkpoint contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import normalize_utc_datetime


OFFICIAL_EVENT_EVIDENCE_PLAN_VERSION = "china-ashare-official-event-evidence-plan/1.0"
OFFICIAL_EVENT_CAPTURE_VERSION = "china-ashare-official-event-capture/1.0"


class ChinaAshareOfficialEventFamily(StrEnum):
    RISK_WARNING = "risk_warning"
    RELISTING_OR_RESUMPTION = "relisting_or_resumption"
    TERMINATION_OR_DELISTING_PERIOD = "termination_or_delisting_period"
    LEGACY_IPO_RULE = "legacy_ipo_rule"


class ChinaAshareOfficialEventParseStatus(StrEnum):
    PARSED = "parsed"
    CAPTURED_UNPARSED = "captured_unparsed"
    TRANSPORT_BLOCKED = "transport_blocked"
    SCHEMA_BLOCKED = "schema_blocked"


class ChinaAshareOfficialEventQueryV1(FrozenContract):
    query_id: str
    event_family: ChinaAshareOfficialEventFamily
    source_security_id: str | None = None
    source_url: str
    http_method: Literal["GET"] = "GET"
    request_parameters: tuple[tuple[str, str], ...]
    title_keyword: str | None = None
    maximum_response_bytes: int = Field(ge=1, le=16 * 1024 * 1024)
    maximum_attempts: Literal[1] = 1

    @field_validator("request_parameters", mode="before")
    @classmethod
    def parameters_are_ordered(cls, value: Any) -> tuple[tuple[str, str], ...]:
        normalized = tuple((str(key), str(item)) for key, item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("official-event query parameters differ")
        return normalized


class ChinaAshareOfficialEventEvidencePlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-official-event-evidence-plan/1.0"
    ] = OFFICIAL_EVENT_EVIDENCE_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    source_expansion_plan_fingerprint: str
    source_partition_manifest_fingerprint: str
    partition_index: Literal[0] = 0
    interval_start: date
    interval_end: date
    target_source_security_ids: tuple[str, ...] = Field(min_length=1, max_length=50)
    queries: tuple[ChinaAshareOfficialEventQueryV1, ...] = Field(min_length=1)
    minimum_request_interval_milliseconds: int = Field(ge=500, le=60_000)
    credentials_required: Literal[False] = False
    aggregate_sources_authorized: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    as_operated_claim_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "source_expansion_plan_fingerprint",
        "source_partition_manifest_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("target_source_security_ids", mode="before")
    @classmethod
    def targets_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("official-event target IDs differ")
        return normalized

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareOfficialEventEvidencePlanV1":
        if self.interval_end < self.interval_start:
            raise ValueError("official-event interval is reversed")
        query_ids = tuple(item.query_id for item in self.queries)
        if query_ids != tuple(sorted(set(query_ids))):
            raise ValueError("official-event query IDs differ")
        scoped = {
            item.source_security_id
            for item in self.queries
            if item.source_security_id is not None
        }
        if scoped != set(self.target_source_security_ids):
            raise ValueError("official-event query scope differs")
        if official_event_evidence_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("official-event plan fingerprint differs")
        return self


class ChinaAshareOfficialEventAnnouncementV1(FrozenContract):
    announcement_id: str
    source_security_id: str
    title: str
    disclosed_at: datetime
    document_url: str

    @field_validator("disclosed_at")
    @classmethod
    def disclosed_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class ChinaAshareOfficialEventCaptureV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    capture_version: Literal[
        "china-ashare-official-event-capture/1.0"
    ] = OFFICIAL_EVENT_CAPTURE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    query_id: str
    requested_url: str
    final_url: str | None = None
    retrieved_at: datetime
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    raw_byte_size: int | None = Field(default=None, ge=1)
    raw_sha256: str | None = None
    parse_status: ChinaAshareOfficialEventParseStatus
    announcements: tuple[ChinaAshareOfficialEventAnnouncementV1, ...] = ()
    conflict_codes: tuple[str, ...] = ()
    blocker_code: str | None = None
    attempt_count: Literal[1] = 1
    outcome_read_count: Literal[0] = 0
    logical_fingerprint: str

    @field_validator("plan_fingerprint", "raw_sha256", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha(value, info.field_name)

    @field_validator("retrieved_at")
    @classmethod
    def retrieval_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("conflict_codes", mode="before")
    @classmethod
    def conflicts_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("official-event conflicts differ")
        return normalized

    @model_validator(mode="after")
    def capture_reconciles(self) -> "ChinaAshareOfficialEventCaptureV1":
        captured = self.raw_sha256 is not None
        if captured != all(
            item is not None
            for item in (self.final_url, self.http_status, self.content_type, self.raw_byte_size)
        ):
            raise ValueError("official-event raw evidence metadata differs")
        if not captured and self.parse_status is not ChinaAshareOfficialEventParseStatus.TRANSPORT_BLOCKED:
            raise ValueError("missing raw evidence must be transport-blocked")
        if captured and self.blocker_code == "transport_blocked":
            raise ValueError("captured evidence cannot be transport-blocked")
        if official_event_capture_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("official-event capture fingerprint differs")
        return self


def build_official_event_evidence_plan(**values: Any) -> ChinaAshareOfficialEventEvidencePlanV1:
    return _build(ChinaAshareOfficialEventEvidencePlanV1, official_event_evidence_plan_fingerprint, values)


def build_official_event_capture(**values: Any) -> ChinaAshareOfficialEventCaptureV1:
    return _build(ChinaAshareOfficialEventCaptureV1, official_event_capture_fingerprint, values)


def official_event_evidence_plan_fingerprint(value: ChinaAshareOfficialEventEvidencePlanV1) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def official_event_capture_fingerprint(value: ChinaAshareOfficialEventCaptureV1) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _build(model, fingerprint, values):
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate({**provisional.model_dump(mode="python"), "logical_fingerprint": fingerprint(provisional)})


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
