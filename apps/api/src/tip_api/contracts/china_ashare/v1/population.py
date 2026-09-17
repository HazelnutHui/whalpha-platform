"""Frozen five-year SSE/SZSE population contracts for A-share expansion."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID, uuid5

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareBoard,
    ChinaAshareExchange,
    FrozenContract,
)
from tip_api.contracts.china_ashare.v1.identity_lifecycle import (
    RESEARCH_IDENTITY_NAMESPACE,
    research_identity_key,
)
from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


POPULATION_METHOD_VERSION = "china-ashare-five-year-population/1.0"
POPULATION_REPORT_VERSION = "china-ashare-five-year-population-report/1.0"
POPULATION_PACKAGE_VERSION = "china-ashare-five-year-population-package/1.0"
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz)\.[0-9]{6}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[a-z][a-z0-9_]*$")


class ChinaAsharePopulationDisposition(StrEnum):
    RESOLVED = "resolved"
    QUARANTINED = "quarantined"
    OUTSIDE_SCOPE = "outside_scope"


class ChinaAshareOfficialPopulationSourceKind(StrEnum):
    SSE_MAIN_CURRENT = "sse_main_current"
    SSE_STAR_CURRENT = "sse_star_current"
    SZSE_A_CURRENT = "szse_a_current"
    SSE_DELIST = "sse_delist"
    SZSE_DELIST = "szse_delist"


class ChinaAshareBaoStockBasicRecordV1(FrozenContract):
    source_security_id: str
    current_name: str
    listing_date: date
    out_date: date | None = None
    provider_type: str
    provider_status: str
    ingested_at: datetime
    logical_fingerprint: str

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("BaoStock basic source security ID is invalid")
        return normalized

    @field_validator("current_name", "provider_type", "provider_status", mode="before")
    @classmethod
    def text_is_present(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("listing_date", "out_date", mode="before")
    @classmethod
    def date_values_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("BaoStock basic date cannot be datetime")
        return value

    @field_validator("ingested_at")
    @classmethod
    def ingested_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("logical_fingerprint")
    @classmethod
    def fingerprint_is_sha256(cls, value: str) -> str:
        return _sha(value, "logical_fingerprint")

    @model_validator(mode="after")
    def record_reconciles(self) -> "ChinaAshareBaoStockBasicRecordV1":
        if self.out_date is not None and self.out_date < self.listing_date:
            raise ValueError("BaoStock out date precedes listing date")
        if baostock_basic_record_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("BaoStock basic fingerprint differs")
        return self


class ChinaAsharePopulationOccurrenceV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    source_security_id: str
    current_or_terminal_name: str
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    listing_date: date
    official_delist_date: date | None = None
    baostock_out_date: date | None = None
    official_source_kind: ChinaAshareOfficialPopulationSourceKind
    official_source_fingerprint: str
    baostock_basic_fingerprint: str | None = None
    disposition: ChinaAsharePopulationDisposition
    instrument_id: UUID | None = None
    research_identity_fingerprint: str | None = None
    reason_codes: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("population source security ID is invalid")
        return normalized

    @field_validator("current_or_terminal_name", mode="before")
    @classmethod
    def name_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="current_or_terminal_name")

    @field_validator("listing_date", "official_delist_date", "baostock_out_date", mode="before")
    @classmethod
    def date_values_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("population date cannot be datetime")
        return value

    @field_validator(
        "official_source_fingerprint",
        "baostock_basic_fingerprint",
        "research_identity_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def optional_hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reasons(value)

    @model_validator(mode="after")
    def occurrence_reconciles(self) -> "ChinaAsharePopulationOccurrenceV1":
        if self.official_delist_date is not None and (
            self.official_delist_date < self.listing_date
        ):
            raise ValueError("official delist date precedes listing date")
        resolved = self.disposition is ChinaAsharePopulationDisposition.RESOLVED
        if resolved:
            if self.board is ChinaAshareBoard.UNKNOWN:
                raise ValueError("resolved population occurrence requires board")
            if self.instrument_id is None or self.research_identity_fingerprint is None:
                raise ValueError("resolved occurrence requires stable research identity")
            if self.baostock_basic_fingerprint is None:
                raise ValueError("resolved occurrence requires BaoStock cross-check")
            key = research_identity_key(
                source_security_id=self.source_security_id,
                exchange=self.exchange,
                board=self.board,
                listing_date=self.listing_date,
            )
            if self.instrument_id != uuid5(RESEARCH_IDENTITY_NAMESPACE, key):
                raise ValueError("population stable identity differs from occurrence key")
            if self.research_identity_fingerprint != (
                population_research_identity_fingerprint(self)
            ):
                raise ValueError("population research identity fingerprint differs")
        elif self.instrument_id is not None or self.research_identity_fingerprint is not None:
            raise ValueError("unresolved occurrence cannot carry research identity")
        if population_occurrence_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("population occurrence fingerprint differs")
        return self


class ChinaAshareFiveYearPopulationReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-five-year-population-report/1.0"
    ] = POPULATION_REPORT_VERSION
    method_version: Literal[
        "china-ashare-five-year-population/1.0"
    ] = POPULATION_METHOD_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    evaluated_at: datetime
    interval_start: date
    interval_end: date
    official_identity_package_fingerprint: str
    baostock_basic_set_fingerprint: str
    official_candidate_count: int = Field(ge=1)
    expansion_target_count: int = Field(ge=1)
    resolved_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    outside_scope_count: int = Field(ge=0)
    current_resolved_count: int = Field(ge=0)
    delisted_resolved_count: int = Field(ge=0)
    cross_source_listing_date_conflict_count: int = Field(ge=0)
    unresolved_board_count: int = Field(ge=0)
    occurrence_set_fingerprint: str
    population_frozen: bool
    full_market_expansion_authorized: bool
    reason_codes: tuple[str, ...] = Field(min_length=1)
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "official_identity_package_fingerprint",
        "baostock_basic_set_fingerprint",
        "occurrence_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("interval_start", "interval_end", mode="before")
    @classmethod
    def interval_values_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("population interval cannot contain datetimes")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reasons(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareFiveYearPopulationReportV1":
        if self.interval_end < self.interval_start:
            raise ValueError("population interval is reversed")
        if self.official_candidate_count != (
            self.resolved_count + self.quarantined_count + self.outside_scope_count
        ):
            raise ValueError("population dispositions do not partition candidates")
        if self.current_resolved_count + self.delisted_resolved_count != self.resolved_count:
            raise ValueError("resolved population status counts differ")
        if self.expansion_target_count != self.resolved_count + self.quarantined_count:
            raise ValueError("population expansion target differs")
        frozen = self.expansion_target_count > 0
        if self.population_frozen is not frozen:
            raise ValueError("population frozen status differs")
        if self.full_market_expansion_authorized is not frozen:
            raise ValueError("population expansion authority differs")
        if five_year_population_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("population report fingerprint differs")
        return self


class ChinaAsharePopulationRawArtifactV1(FrozenContract):
    artifact_kind: ChinaAshareOfficialPopulationSourceKind
    relative_path: str
    byte_size: int = Field(ge=1)
    physical_sha256: str

    @field_validator("relative_path", mode="before")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="relative_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("population raw artifact path is unsafe")
        if not normalized.startswith("raw/official/"):
            raise ValueError("population official artifact path differs")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class ChinaAshareFiveYearPopulationPackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-five-year-population-package/1.0"
    ] = POPULATION_PACKAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    created_at: datetime
    official_identity_package_fingerprint: str
    baostock_basic_document_sha256: str
    baostock_basic_set_fingerprint: str
    occurrence_document_sha256: str
    occurrence_set_fingerprint: str
    report_document_sha256: str
    report_fingerprint: str
    official_raw_artifacts: tuple[ChinaAsharePopulationRawArtifactV1, ...]
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("created_at")
    @classmethod
    def created_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "official_identity_package_fingerprint",
        "baostock_basic_document_sha256",
        "baostock_basic_set_fingerprint",
        "occurrence_document_sha256",
        "occurrence_set_fingerprint",
        "report_document_sha256",
        "report_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "ChinaAshareFiveYearPopulationPackageManifestV1":
        keys = tuple(
            (item.artifact_kind.value, item.relative_path)
            for item in self.official_raw_artifacts
        )
        if keys != tuple(sorted(set(keys))) or len(keys) != 5:
            raise ValueError("population official artifacts differ")
        if five_year_population_package_manifest_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("population package fingerprint differs")
        return self


def build_baostock_basic_record(**values: Any) -> ChinaAshareBaoStockBasicRecordV1:
    candidate = ChinaAshareBaoStockBasicRecordV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareBaoStockBasicRecordV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": baostock_basic_record_fingerprint(candidate),
        }
    )


def build_population_occurrence(**values: Any) -> ChinaAsharePopulationOccurrenceV1:
    if ChinaAsharePopulationDisposition(values["disposition"]) is (
        ChinaAsharePopulationDisposition.RESOLVED
    ):
        key = research_identity_key(
            source_security_id=str(values["source_security_id"]).strip().lower(),
            exchange=ChinaAshareExchange(values["exchange"]),
            board=ChinaAshareBoard(values["board"]),
            listing_date=values["listing_date"],
        )
        identity_candidate = ChinaAsharePopulationOccurrenceV1.model_construct(
            **values,
            instrument_id=uuid5(RESEARCH_IDENTITY_NAMESPACE, key),
            research_identity_fingerprint="0" * 64,
            logical_fingerprint="0" * 64,
        )
        values = {
            **values,
            "instrument_id": identity_candidate.instrument_id,
            "research_identity_fingerprint": (
                population_research_identity_fingerprint(identity_candidate)
            ),
        }
    else:
        values = {
            **values,
            "instrument_id": None,
            "research_identity_fingerprint": None,
        }
    candidate = ChinaAsharePopulationOccurrenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAsharePopulationOccurrenceV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": population_occurrence_fingerprint(candidate),
        }
    )


def build_five_year_population_report(
    **values: Any,
) -> ChinaAshareFiveYearPopulationReportV1:
    candidate = ChinaAshareFiveYearPopulationReportV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFiveYearPopulationReportV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": five_year_population_report_fingerprint(candidate),
        }
    )


def build_five_year_population_package_manifest(
    **values: Any,
) -> ChinaAshareFiveYearPopulationPackageManifestV1:
    candidate = ChinaAshareFiveYearPopulationPackageManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareFiveYearPopulationPackageManifestV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": five_year_population_package_manifest_fingerprint(
                candidate
            ),
        }
    )


def baostock_basic_record_fingerprint(value: ChinaAshareBaoStockBasicRecordV1) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def baostock_basic_set_fingerprint(
    rows: tuple[ChinaAshareBaoStockBasicRecordV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in rows])


def population_occurrence_fingerprint(value: ChinaAsharePopulationOccurrenceV1) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def population_research_identity_fingerprint(
    value: ChinaAsharePopulationOccurrenceV1,
) -> str:
    return _fingerprint(
        {
            "board": value.board.value,
            "exchange": value.exchange.value,
            "instrument_id": str(value.instrument_id),
            "listing_date": value.listing_date.isoformat(),
            "market_id": MARKET_ID,
            "source_security_id": value.source_security_id,
        }
    )


def population_occurrence_set_fingerprint(
    rows: tuple[ChinaAsharePopulationOccurrenceV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in rows])


def five_year_population_report_fingerprint(
    value: ChinaAshareFiveYearPopulationReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def five_year_population_package_manifest_fingerprint(
    value: ChinaAshareFiveYearPopulationPackageManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def official_population_row_fingerprint(value: dict[str, Any]) -> str:
    return _fingerprint(value)


def _sha(value: str, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized


def _reasons(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ValueError("reason_codes must be a collection")
    normalized = tuple(sorted({str(item).strip().lower() for item in value}))
    if not normalized or any(not _REASON.fullmatch(item) for item in normalized):
        raise ValueError("reason_codes are invalid")
    return normalized


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()
