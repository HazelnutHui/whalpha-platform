"""Completion census for the exact A-share raw-source expansion plan."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import normalize_utc_datetime


SOURCE_EXPANSION_COMPLETION_VERSION = "china-ashare-source-expansion-completion/1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ChinaAshareSourceExpansionCompletionReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-source-expansion-completion/1.0"
    ] = SOURCE_EXPANSION_COMPLETION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    evaluated_at: datetime
    plan_fingerprint: str
    population_package_fingerprint: str
    interval_start: date
    interval_end: date
    partition_count: int = Field(ge=1)
    target_count: int = Field(ge=1)
    resolved_target_count: int = Field(ge=0)
    quarantined_target_count: int = Field(ge=0)
    source_request_count: int = Field(ge=2)
    daily_row_count: int = Field(ge=0)
    adjustment_row_count: int = Field(ge=0)
    daily_target_with_rows_count: int = Field(ge=0)
    daily_zero_row_target_count: int = Field(ge=0)
    adjustment_target_with_rows_count: int = Field(ge=0)
    adjustment_zero_row_target_count: int = Field(ge=0)
    suspended_row_count: int = Field(ge=0)
    risk_warning_present_row_count: int = Field(ge=0)
    first_daily_session: date | None = None
    last_daily_session: date | None = None
    partition_manifest_fingerprints: tuple[str, ...] = Field(min_length=1)
    source_available_at_complete: Literal[False] = False
    capture_complete: Literal[True] = True
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "interval_start",
        "interval_end",
        "first_daily_session",
        "last_daily_session",
        mode="before",
    )
    @classmethod
    def date_values_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("source expansion completion date cannot be datetime")
        return value

    @field_validator(
        "plan_fingerprint",
        "population_package_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("partition_manifest_fingerprints", mode="before")
    @classmethod
    def manifest_hashes_are_ordered(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("partition manifest fingerprints must be ordered")
        return tuple(_sha(item, "partition_manifest_fingerprint") for item in value)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "ChinaAshareSourceExpansionCompletionReportV1":
        if self.interval_end < self.interval_start:
            raise ValueError("source expansion completion interval is reversed")
        if self.resolved_target_count + self.quarantined_target_count != (
            self.target_count
        ):
            raise ValueError("source expansion completion target partition differs")
        if self.source_request_count != self.target_count * 2:
            raise ValueError("source expansion completion request count differs")
        if self.daily_target_with_rows_count + self.daily_zero_row_target_count != (
            self.target_count
        ):
            raise ValueError("source expansion daily target coverage differs")
        if (
            self.adjustment_target_with_rows_count
            + self.adjustment_zero_row_target_count
            != self.target_count
        ):
            raise ValueError("source expansion adjustment target coverage differs")
        if len(self.partition_manifest_fingerprints) != self.partition_count:
            raise ValueError("source expansion partition manifest count differs")
        if len(set(self.partition_manifest_fingerprints)) != self.partition_count:
            raise ValueError("source expansion partition manifests are duplicated")
        if (self.first_daily_session is None) != (self.last_daily_session is None):
            raise ValueError("source expansion daily bounds are incomplete")
        if self.first_daily_session is not None:
            assert self.last_daily_session is not None
            if not (
                self.interval_start
                <= self.first_daily_session
                <= self.last_daily_session
                <= self.interval_end
            ):
                raise ValueError("source expansion daily bounds differ")
        if source_expansion_completion_report_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("source expansion completion fingerprint differs")
        return self


def build_source_expansion_completion_report(
    **values: Any,
) -> ChinaAshareSourceExpansionCompletionReportV1:
    candidate = ChinaAshareSourceExpansionCompletionReportV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareSourceExpansionCompletionReportV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": source_expansion_completion_report_fingerprint(
                candidate
            ),
        }
    )


def source_expansion_completion_report_fingerprint(
    value: ChinaAshareSourceExpansionCompletionReportV1,
) -> str:
    payload = json.dumps(
        value.model_dump(mode="json", exclude={"logical_fingerprint"}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
