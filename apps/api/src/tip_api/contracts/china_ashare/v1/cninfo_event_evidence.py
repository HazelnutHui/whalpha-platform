"""Minimal immutable CNINFO event-search evidence for one SZSE sample."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import normalize_utc_datetime


CNINFO_EVENT_PLAN_VERSION = "china-ashare-cninfo-event-plan/1.0"
CNINFO_EVENT_CAPTURE_VERSION = "china-ashare-cninfo-event-capture/1.0"


class ChinaAshareCninfoRequestKind(StrEnum):
    SECURITY_MAP = "security_map"
    ANNOUNCEMENT_QUERY = "announcement_query"


class ChinaAshareCninfoParseStatus(StrEnum):
    PARSED = "parsed"
    TRANSPORT_BLOCKED = "transport_blocked"
    SCHEMA_BLOCKED = "schema_blocked"
    ANTIBOT_BLOCKED = "antibot_blocked"


class ChinaAshareCninfoQueryV1(FrozenContract):
    query_id: str
    request_kind: ChinaAshareCninfoRequestKind
    keyword: str | None = None
    maximum_response_bytes: int = Field(ge=1, le=16 * 1024 * 1024)
    maximum_attempts: Literal[1] = 1


class ChinaAshareCninfoEventPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-cninfo-event-plan/1.0"
    ] = CNINFO_EVENT_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    source_expansion_plan_fingerprint: str
    source_partition_manifest_fingerprint: str
    partition_index: Literal[47] = 47
    source_security_id: Literal["sz.000001"] = "sz.000001"
    interval_start: date
    interval_end: date
    security_map_url: Literal[
        "https://www.cninfo.com.cn/new/data/szse_stock.json"
    ] = "https://www.cninfo.com.cn/new/data/szse_stock.json"
    announcement_query_url: Literal[
        "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    ] = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    queries: tuple[ChinaAshareCninfoQueryV1, ...] = Field(min_length=6, max_length=6)
    minimum_request_interval_milliseconds: int = Field(ge=500, le=60_000)
    credentials_required: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    as_operated_claim_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
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

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareCninfoEventPlanV1":
        if self.interval_end < self.interval_start:
            raise ValueError("CNINFO event interval is reversed")
        query_ids = tuple(item.query_id for item in self.queries)
        if query_ids != tuple(sorted(set(query_ids))):
            raise ValueError("CNINFO query IDs differ")
        if sum(
            item.request_kind is ChinaAshareCninfoRequestKind.SECURITY_MAP
            for item in self.queries
        ) != 1:
            raise ValueError("CNINFO security-map query differs")
        if cninfo_event_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("CNINFO event plan fingerprint differs")
        return self


class ChinaAshareCninfoAnnouncementV1(FrozenContract):
    announcement_id: str
    source_security_id: Literal["sz.000001"] = "sz.000001"
    title: str
    published_at: datetime
    document_url: str

    @field_validator("published_at")
    @classmethod
    def published_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class ChinaAshareCninfoCaptureV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    capture_version: Literal[
        "china-ashare-cninfo-event-capture/1.0"
    ] = CNINFO_EVENT_CAPTURE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    query_id: str
    requested_url: str
    http_method: Literal["GET", "POST"]
    request_parameters: tuple[tuple[str, str], ...] = ()
    final_url: str | None = None
    retrieved_at: datetime
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    raw_byte_size: int | None = Field(default=None, ge=1)
    raw_sha256: str | None = None
    parse_status: ChinaAshareCninfoParseStatus
    resolved_org_id: str | None = None
    announcements: tuple[ChinaAshareCninfoAnnouncementV1, ...] = ()
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

    @field_validator("request_parameters", mode="before")
    @classmethod
    def parameters_are_ordered(cls, value: Any) -> tuple[tuple[str, str], ...]:
        normalized = tuple((str(key), str(item)) for key, item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("CNINFO request parameters differ")
        return normalized

    @field_validator("conflict_codes", mode="before")
    @classmethod
    def conflicts_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("CNINFO conflicts differ")
        return normalized

    @model_validator(mode="after")
    def capture_reconciles(self) -> "ChinaAshareCninfoCaptureV1":
        captured = self.raw_sha256 is not None
        if captured != all(
            item is not None
            for item in (
                self.final_url,
                self.http_status,
                self.content_type,
                self.raw_byte_size,
            )
        ):
            raise ValueError("CNINFO raw evidence metadata differs")
        if not captured and self.parse_status is not ChinaAshareCninfoParseStatus.TRANSPORT_BLOCKED:
            raise ValueError("missing CNINFO evidence must be transport-blocked")
        if cninfo_event_capture_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("CNINFO capture fingerprint differs")
        return self


def build_cninfo_event_plan(**values: Any) -> ChinaAshareCninfoEventPlanV1:
    return _build(ChinaAshareCninfoEventPlanV1, cninfo_event_plan_fingerprint, values)


def build_cninfo_event_capture(**values: Any) -> ChinaAshareCninfoCaptureV1:
    return _build(
        ChinaAshareCninfoCaptureV1, cninfo_event_capture_fingerprint, values
    )


def cninfo_event_plan_fingerprint(value: ChinaAshareCninfoEventPlanV1) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def cninfo_event_capture_fingerprint(value: ChinaAshareCninfoCaptureV1) -> str:
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
