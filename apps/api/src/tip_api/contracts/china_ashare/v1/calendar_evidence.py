"""Contracts for retained official A-share calendar evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareExchange,
    FrozenContract,
)
from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


CALENDAR_EVIDENCE_PLAN_VERSION = "china-ashare-calendar-evidence-plan/1.0"
CALENDAR_EVIDENCE_PACKAGE_VERSION = "china-ashare-calendar-evidence-package/1.0"
CALENDAR_NOTICE_PARSER_VERSION = "china-ashare-official-calendar-html/1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]*$")
_ALLOWED_HOSTS = {
    ChinaAshareExchange.SSE: {"www.sse.com.cn"},
    ChinaAshareExchange.SZSE: {"www.szse.cn", "investor.szse.cn"},
}


class ChinaAshareOfficialCalendarNoticeSpecV1(FrozenContract):
    exchange: ChinaAshareExchange
    notice_year: int = Field(ge=2000, le=2100)
    source_url: str

    @field_validator("source_url", mode="before")
    @classmethod
    def source_url_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="source_url")

    @model_validator(mode="after")
    def source_is_official(self) -> "ChinaAshareOfficialCalendarNoticeSpecV1":
        if self.exchange not in _ALLOWED_HOSTS:
            raise ValueError("calendar notice exchange must be SSE or SZSE")
        parsed = urlparse(self.source_url)
        if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS[self.exchange]:
            raise ValueError("calendar notice must use an approved official HTTPS host")
        return self


class ChinaAshareOfficialCalendarEvidencePlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal["china-ashare-calendar-evidence-plan/1.0"] = (
        CALENDAR_EVIDENCE_PLAN_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    planned_at: datetime
    start_date: date
    end_date: date
    notice_specs: tuple[ChinaAshareOfficialCalendarNoticeSpecV1, ...] = Field(
        min_length=2
    )
    raw_upstream_payload_required: Literal[True] = True
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("planned_at")
    @classmethod
    def planned_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def date_fields_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("calendar evidence range must contain dates")
        return value

    @field_validator("logical_fingerprint")
    @classmethod
    def fingerprint_is_sha256(cls, value: str) -> str:
        return _sha(value, "logical_fingerprint")

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareOfficialCalendarEvidencePlanV1":
        if self.end_date < self.start_date:
            raise ValueError("calendar evidence range is reversed")
        keys = tuple((item.notice_year, item.exchange.value) for item in self.notice_specs)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("calendar notice specs must be unique and ordered")
        required_years = set(range(self.start_date.year, self.end_date.year + 1))
        expected = {
            (year, exchange.value)
            for year in required_years
            for exchange in (ChinaAshareExchange.SSE, ChinaAshareExchange.SZSE)
        }
        if set(keys) != expected:
            raise ValueError("calendar notice plan must cover SSE and SZSE for every year")
        if official_calendar_evidence_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("calendar evidence plan fingerprint differs")
        return self


class ChinaAshareOfficialCalendarClosureRangeV1(FrozenContract):
    start_date: date
    end_date: date

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def range_fields_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("closure range must contain dates")
        return value

    @model_validator(mode="after")
    def range_reconciles(self) -> "ChinaAshareOfficialCalendarClosureRangeV1":
        if self.end_date < self.start_date:
            raise ValueError("closure range is reversed")
        if (self.end_date - self.start_date).days > 31:
            raise ValueError("closure range exceeds its safety ceiling")
        return self


class ChinaAshareOfficialCalendarNoticeV1(FrozenContract):
    exchange: ChinaAshareExchange
    notice_year: int = Field(ge=2000, le=2100)
    source_url: str
    final_url: str
    retrieved_at: datetime
    http_status: Literal[200] = 200
    content_type: Literal["text/html"] = "text/html"
    raw_byte_size: int = Field(ge=1, le=4 * 1024 * 1024)
    raw_sha256: str
    parser_version: Literal["china-ashare-official-calendar-html/1.0"] = (
        CALENDAR_NOTICE_PARSER_VERSION
    )
    title: str
    closure_ranges: tuple[ChinaAshareOfficialCalendarClosureRangeV1, ...] = Field(
        min_length=1
    )
    weekday_closure_dates: tuple[date, ...] = Field(min_length=1)

    @field_validator("source_url", "final_url", "title", mode="before")
    @classmethod
    def strings_are_present(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("raw_sha256")
    @classmethod
    def raw_hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "raw_sha256")

    @field_validator("closure_ranges", mode="before")
    @classmethod
    def ranges_are_ordered(cls, value: Any) -> Any:
        if not isinstance(value, (tuple, list)):
            raise ValueError("closure_ranges must be an ordered collection")
        return value

    @field_validator("weekday_closure_dates", mode="before")
    @classmethod
    def closure_dates_are_ordered(cls, value: Any) -> tuple[date, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("weekday_closure_dates must be an ordered collection")
        if any(isinstance(item, datetime) for item in value):
            raise ValueError("weekday_closure_dates must contain dates")
        normalized = tuple(sorted(set(value)))
        if len(normalized) != len(value):
            raise ValueError("weekday_closure_dates contains duplicates")
        return normalized

    @model_validator(mode="after")
    def notice_reconciles(self) -> "ChinaAshareOfficialCalendarNoticeV1":
        spec = ChinaAshareOfficialCalendarNoticeSpecV1(
            exchange=self.exchange,
            notice_year=self.notice_year,
            source_url=self.source_url,
        )
        del spec
        parsed_final = urlparse(self.final_url)
        if (
            parsed_final.scheme != "https"
            or parsed_final.hostname not in _ALLOWED_HOSTS[self.exchange]
        ):
            raise ValueError("calendar notice redirect left the approved official host set")
        range_keys = tuple((item.start_date, item.end_date) for item in self.closure_ranges)
        if range_keys != tuple(sorted(set(range_keys))):
            raise ValueError("calendar notice closure ranges must be unique and ordered")
        if any(item.year != self.notice_year for item in self.weekday_closure_dates):
            raise ValueError("calendar notice closure date differs from notice year")
        if any(item.weekday() >= 5 for item in self.weekday_closure_dates):
            raise ValueError("weekday closure dates cannot contain weekends")
        if str(self.notice_year) not in self.title or "休市" not in self.title:
            raise ValueError("calendar notice title does not identify its year and purpose")
        return self


class ChinaAshareOfficialCalendarRawArtifactV1(FrozenContract):
    exchange: ChinaAshareExchange
    notice_year: int = Field(ge=2000, le=2100)
    relative_path: str
    byte_size: int = Field(ge=1, le=4 * 1024 * 1024)
    physical_sha256: str

    @field_validator("relative_path", mode="before")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="relative_path")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("calendar artifact path must be relative and bounded")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def physical_hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "physical_sha256")

    @model_validator(mode="after")
    def artifact_reconciles(self) -> "ChinaAshareOfficialCalendarRawArtifactV1":
        expected = f"raw/{self.exchange.value.lower()}-{self.notice_year}.html"
        if self.relative_path != expected:
            raise ValueError("calendar artifact path differs from exchange/year")
        return self


class ChinaAshareOfficialCalendarEvidenceReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    daily_package_fingerprint: str
    evaluated_at: datetime
    calendar_id: Literal["XSHG"] = "XSHG"
    calendar_version: str
    calendar_timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    start_date: date
    end_date: date
    notice_count: int = Field(ge=2)
    expected_session_count: int = Field(ge=1)
    expected_sessions_fingerprint: str
    official_weekday_closure_dates: tuple[date, ...]
    official_closure_fingerprint: str
    library_closures_missing_from_official: tuple[date, ...] = ()
    official_closures_missing_from_library: tuple[date, ...] = ()
    sse_closures_missing_from_szse: tuple[date, ...] = ()
    szse_closures_missing_from_sse: tuple[date, ...] = ()
    library_source_alignment_complete: bool
    official_exchange_notice_retained: bool
    calendar_reconciled: bool
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    reason_codes: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "daily_package_fingerprint",
        "expected_sessions_fingerprint",
        "official_closure_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("calendar_version", mode="before")
    @classmethod
    def calendar_version_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="calendar_version")

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def report_dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("calendar report range must contain dates")
        return value

    @field_validator(
        "official_weekday_closure_dates",
        "library_closures_missing_from_official",
        "official_closures_missing_from_library",
        "sse_closures_missing_from_szse",
        "szse_closures_missing_from_sse",
        mode="before",
    )
    @classmethod
    def report_date_sets_are_ordered(cls, value: Any, info: Any) -> tuple[date, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError(f"{info.field_name} must be an ordered collection")
        if any(isinstance(item, datetime) for item in value):
            raise ValueError(f"{info.field_name} must contain dates")
        normalized = tuple(sorted(set(value)))
        if len(normalized) != len(value):
            raise ValueError(f"{info.field_name} contains duplicates")
        return normalized

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("reason_codes must be an ordered collection")
        normalized = tuple(sorted(set(value)))
        if len(normalized) != len(value) or any(
            not _REASON_CODE.fullmatch(item) for item in normalized
        ):
            raise ValueError("reason_codes must be unique ordered snake-case values")
        return normalized

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareOfficialCalendarEvidenceReportV1":
        if self.end_date < self.start_date:
            raise ValueError("calendar evidence report range is reversed")
        expected_reconciled = all(
            (
                self.library_source_alignment_complete,
                self.official_exchange_notice_retained,
                not self.library_closures_missing_from_official,
                not self.official_closures_missing_from_library,
                not self.sse_closures_missing_from_szse,
                not self.szse_closures_missing_from_sse,
            )
        )
        if self.calendar_reconciled is not expected_reconciled:
            raise ValueError("calendar reconciliation status differs")
        if (
            _date_fingerprint(self.official_weekday_closure_dates)
            != self.official_closure_fingerprint
        ):
            raise ValueError("official closure fingerprint differs")
        if official_calendar_evidence_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("calendar evidence report fingerprint differs")
        return self


class ChinaAshareOfficialCalendarEvidenceManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal["china-ashare-calendar-evidence-package/1.0"] = (
        CALENDAR_EVIDENCE_PACKAGE_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    created_at: datetime
    plan_document_sha256: str
    notices_document_sha256: str
    report_document_sha256: str
    report_fingerprint: str
    raw_artifacts: tuple[ChinaAshareOfficialCalendarRawArtifactV1, ...] = Field(
        min_length=2
    )
    raw_upstream_payload_retained: Literal[True] = True
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "plan_document_sha256",
        "notices_document_sha256",
        "report_document_sha256",
        "report_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def manifest_hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def created_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAshareOfficialCalendarEvidenceManifestV1":
        keys = tuple((item.notice_year, item.exchange.value) for item in self.raw_artifacts)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("calendar raw artifacts must be unique and ordered")
        if official_calendar_evidence_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("calendar evidence manifest fingerprint differs")
        return self


def build_official_calendar_evidence_plan(
    **values: Any,
) -> ChinaAshareOfficialCalendarEvidencePlanV1:
    return _build_fingerprinted(ChinaAshareOfficialCalendarEvidencePlanV1, values)


def build_official_calendar_evidence_report(
    **values: Any,
) -> ChinaAshareOfficialCalendarEvidenceReportV1:
    return _build_fingerprinted(ChinaAshareOfficialCalendarEvidenceReportV1, values)


def build_official_calendar_evidence_manifest(
    **values: Any,
) -> ChinaAshareOfficialCalendarEvidenceManifestV1:
    return _build_fingerprinted(ChinaAshareOfficialCalendarEvidenceManifestV1, values)


def official_calendar_evidence_plan_fingerprint(
    value: ChinaAshareOfficialCalendarEvidencePlanV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def official_calendar_evidence_report_fingerprint(
    value: ChinaAshareOfficialCalendarEvidenceReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def official_calendar_evidence_manifest_fingerprint(
    value: ChinaAshareOfficialCalendarEvidenceManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _build_fingerprinted(model: Any, values: dict[str, Any]) -> Any:
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    fingerprint_function = {
        ChinaAshareOfficialCalendarEvidencePlanV1: official_calendar_evidence_plan_fingerprint,
        ChinaAshareOfficialCalendarEvidenceReportV1: official_calendar_evidence_report_fingerprint,
        ChinaAshareOfficialCalendarEvidenceManifestV1: (
            official_calendar_evidence_manifest_fingerprint
        ),
    }[model]
    return model.model_validate(
        {**values, "logical_fingerprint": fingerprint_function(provisional)}
    )


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _date_fingerprint(values: tuple[date, ...]) -> str:
    return _fingerprint(tuple(item.isoformat() for item in values))


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
