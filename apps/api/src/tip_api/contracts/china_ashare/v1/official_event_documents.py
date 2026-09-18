"""Immutable second-stage official announcement document evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import normalize_utc_datetime


OFFICIAL_EVENT_DOCUMENT_PLAN_VERSION = (
    "china-ashare-official-event-document-plan/1.0"
)
OFFICIAL_EVENT_DOCUMENT_CAPTURE_VERSION = (
    "china-ashare-official-event-document-capture/1.0"
)


class ChinaAshareOfficialDocumentProvider(StrEnum):
    SSE = "sse"
    CNINFO = "cninfo"


class ChinaAshareOfficialDocumentParseStatus(StrEnum):
    PARSED = "parsed"
    CAPTURED_UNPARSED = "captured_unparsed"
    TRANSPORT_BLOCKED = "transport_blocked"
    SCHEMA_BLOCKED = "schema_blocked"
    ANTIBOT_BLOCKED = "antibot_blocked"


class ChinaAshareRiskWarningEventKind(StrEnum):
    WARNING_EXPECTED = "warning_expected"
    WARNING_IMPLEMENTED = "warning_implemented"
    WARNING_REMOVED = "warning_removed"
    WARNING_CHANGED = "warning_changed"


class ChinaAshareRiskWarningSubtype(StrEnum):
    ST = "st"
    STAR_ST = "star_st"
    OTHER_RISK_WARNING = "other_risk_warning"
    COMBINED = "combined"
    UNKNOWN = "unknown"


class ChinaAshareOfficialDocumentSpecV1(FrozenContract):
    document_id: str
    provider: ChinaAshareOfficialDocumentProvider
    source_security_id: str
    title: str
    published_on: date
    document_url: str
    maximum_response_bytes: int = Field(ge=1, le=32 * 1024 * 1024)
    maximum_attempts: Literal[1] = 1


class ChinaAshareOfficialEventDocumentPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-official-event-document-plan/1.0"
    ] = OFFICIAL_EVENT_DOCUMENT_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    provider: ChinaAshareOfficialDocumentProvider
    source_security_id: str
    parent_evidence_plan_fingerprint: str
    parent_query_id: str
    parent_capture_fingerprint: str
    parent_raw_sha256: str
    documents: tuple[ChinaAshareOfficialDocumentSpecV1, ...] = Field(
        min_length=1, max_length=10
    )
    minimum_request_interval_milliseconds: int = Field(ge=500, le=60_000)
    credentials_required: Literal[False] = False
    outcome_read_count: Literal[0] = 0
    as_operated_claim_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "parent_evidence_plan_fingerprint",
        "parent_capture_fingerprint",
        "parent_raw_sha256",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareOfficialEventDocumentPlanV1":
        document_ids = tuple(item.document_id for item in self.documents)
        if document_ids != tuple(sorted(set(document_ids))):
            raise ValueError("official document IDs differ")
        if any(
            item.provider is not self.provider
            or item.source_security_id != self.source_security_id
            for item in self.documents
        ):
            raise ValueError("official document scope differs")
        if official_event_document_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("official document plan fingerprint differs")
        return self


class ChinaAshareRiskWarningEventV1(FrozenContract):
    document_id: str
    source_security_id: str
    event_kind: ChinaAshareRiskWarningEventKind
    subtype: ChinaAshareRiskWarningSubtype
    published_on: date
    effective_from: date | None = None
    effective_to: date | None = None
    publication_clock_time_known: Literal[False] = False
    evidence_markers: tuple[str, ...] = ()

    @field_validator("evidence_markers", mode="before")
    @classmethod
    def markers_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip() for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("risk-warning evidence markers differ")
        return normalized

    @model_validator(mode="after")
    def event_dates_reconcile(self) -> "ChinaAshareRiskWarningEventV1":
        if self.effective_to is not None and self.effective_from is None:
            raise ValueError("risk-warning end lacks start")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("risk-warning interval is reversed")
        return self


class ChinaAshareOfficialEventDocumentCaptureV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    capture_version: Literal[
        "china-ashare-official-event-document-capture/1.0"
    ] = OFFICIAL_EVENT_DOCUMENT_CAPTURE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    document_id: str
    requested_url: str
    final_url: str | None = None
    retrieved_at: datetime
    http_status: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    raw_byte_size: int | None = Field(default=None, ge=1)
    raw_sha256: str | None = None
    text_byte_size: int | None = Field(default=None, ge=1)
    text_sha256: str | None = None
    parse_status: ChinaAshareOfficialDocumentParseStatus
    risk_warning_events: tuple[ChinaAshareRiskWarningEventV1, ...] = ()
    conflict_codes: tuple[str, ...] = ()
    blocker_code: str | None = None
    attempt_count: Literal[1] = 1
    outcome_read_count: Literal[0] = 0
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint", "raw_sha256", "text_sha256", "logical_fingerprint"
    )
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
            raise ValueError("official document conflicts differ")
        return normalized

    @model_validator(mode="after")
    def capture_reconciles(self) -> "ChinaAshareOfficialEventDocumentCaptureV1":
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
            raise ValueError("official document raw metadata differs")
        text_captured = self.text_sha256 is not None
        if text_captured != (self.text_byte_size is not None):
            raise ValueError("official document text metadata differs")
        if (
            not captured
            and self.parse_status
            is not ChinaAshareOfficialDocumentParseStatus.TRANSPORT_BLOCKED
        ):
            raise ValueError("missing document must be transport-blocked")
        if self.parse_status is ChinaAshareOfficialDocumentParseStatus.PARSED:
            if not text_captured or not self.risk_warning_events:
                raise ValueError("parsed document lacks text or events")
        elif self.risk_warning_events:
            raise ValueError("unparsed document cannot carry events")
        if official_event_document_capture_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("official document capture fingerprint differs")
        return self


def build_official_event_document_plan(
    **values: Any,
) -> ChinaAshareOfficialEventDocumentPlanV1:
    return _build(
        ChinaAshareOfficialEventDocumentPlanV1,
        official_event_document_plan_fingerprint,
        values,
    )


def build_official_event_document_capture(
    **values: Any,
) -> ChinaAshareOfficialEventDocumentCaptureV1:
    return _build(
        ChinaAshareOfficialEventDocumentCaptureV1,
        official_event_document_capture_fingerprint,
        values,
    )


def official_event_document_plan_fingerprint(
    value: ChinaAshareOfficialEventDocumentPlanV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def official_event_document_capture_fingerprint(
    value: ChinaAshareOfficialEventDocumentCaptureV1,
) -> str:
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
