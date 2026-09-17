"""Point-in-time daily research-Universe contracts for China A-shares."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import normalize_utc_datetime


DAILY_UNIVERSE_METHOD_VERSION = "china-ashare-daily-universe/1.0"
DAILY_UNIVERSE_REPORT_VERSION = "china-ashare-daily-universe-report/1.0"
DAILY_UNIVERSE_PACKAGE_VERSION = "china-ashare-daily-universe-package/1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[a-z][a-z0-9_]*$")


class ChinaAshareDailyUniverseReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-daily-universe-report/1.0"
    ] = DAILY_UNIVERSE_REPORT_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    methodology_version: Literal[
        "china-ashare-daily-universe/1.0"
    ] = DAILY_UNIVERSE_METHOD_VERSION
    daily_package_fingerprint: str
    identity_lifecycle_package_fingerprint: str
    evaluated_at: datetime
    interval_start: date
    interval_end: date
    instrument_count: int = Field(ge=1)
    session_count: int = Field(ge=1)
    target_decision_count: int = Field(ge=1)
    decision_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    performance_eligible_count: int = Field(ge=0)
    decision_set_fingerprint: str
    exactly_one_decision_per_instrument_session: bool
    later_retrieved_state_not_as_operated: Literal[True] = True
    daily_universe_family_complete: bool
    reason_codes: tuple[str, ...] = Field(min_length=1)
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "daily_package_fingerprint",
        "identity_lifecycle_package_fingerprint",
        "decision_set_fingerprint",
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
            raise ValueError("daily Universe interval must contain dates")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reasons(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareDailyUniverseReportV1":
        if self.interval_end < self.interval_start:
            raise ValueError("daily Universe interval is reversed")
        if self.target_decision_count != self.instrument_count * self.session_count:
            raise ValueError("daily Universe target is not the full cross product")
        if self.decision_count != (
            self.included_count + self.excluded_count + self.quarantined_count
        ):
            raise ValueError("daily Universe dispositions do not partition decisions")
        if self.performance_eligible_count > self.included_count:
            raise ValueError("performance-eligible count exceeds included decisions")
        exact = self.decision_count == self.target_decision_count
        if self.exactly_one_decision_per_instrument_session is not exact:
            raise ValueError("daily Universe exact-decision status differs")
        complete = exact and self.quarantined_count == 0
        if self.daily_universe_family_complete is not complete:
            raise ValueError("daily Universe family status differs")
        if daily_universe_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("daily Universe report fingerprint differs")
        return self


class ChinaAshareDailyUniversePackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-daily-universe-package/1.0"
    ] = DAILY_UNIVERSE_PACKAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    daily_package_fingerprint: str
    identity_lifecycle_package_fingerprint: str
    created_at: datetime
    decision_document_sha256: str
    decision_set_fingerprint: str
    report_document_sha256: str
    report_fingerprint: str
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "daily_package_fingerprint",
        "identity_lifecycle_package_fingerprint",
        "decision_document_sha256",
        "decision_set_fingerprint",
        "report_document_sha256",
        "report_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def created_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAshareDailyUniversePackageManifestV1":
        if daily_universe_package_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("daily Universe package fingerprint differs")
        return self


def build_daily_universe_report(**values: Any) -> ChinaAshareDailyUniverseReportV1:
    candidate = ChinaAshareDailyUniverseReportV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareDailyUniverseReportV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": daily_universe_report_fingerprint(candidate),
        }
    )


def build_daily_universe_package_manifest(
    **values: Any,
) -> ChinaAshareDailyUniversePackageManifestV1:
    candidate = ChinaAshareDailyUniversePackageManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareDailyUniversePackageManifestV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": daily_universe_package_manifest_fingerprint(
                candidate
            ),
        }
    )


def daily_universe_decision_set_fingerprint(rows: tuple[Any, ...]) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in rows])


def daily_universe_report_fingerprint(
    value: ChinaAshareDailyUniverseReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def daily_universe_package_manifest_fingerprint(
    value: ChinaAshareDailyUniversePackageManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


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
