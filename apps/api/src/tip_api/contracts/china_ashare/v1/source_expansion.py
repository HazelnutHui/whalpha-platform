"""Restartable raw-source expansion contracts for the A-share foundation."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


SOURCE_EXPANSION_PLAN_VERSION = "china-ashare-source-expansion-plan/1.0"
SOURCE_EXPANSION_PARTITION_VERSION = "china-ashare-source-expansion-partition/1.0"
SOURCE_EXPANSION_PROVIDER_ID = "baostock_ashare"
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz)\.[0-9]{6}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ChinaAshareSourceExpansionTargetV1(FrozenContract):
    source_security_id: str
    listing_date: date
    disposition: ChinaAsharePopulationDisposition
    population_occurrence_fingerprint: str

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source expansion security ID is invalid")
        return normalized

    @field_validator("listing_date", mode="before")
    @classmethod
    def listing_value_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("source expansion listing date cannot be datetime")
        return value

    @field_validator("population_occurrence_fingerprint")
    @classmethod
    def fingerprint_is_sha256(cls, value: str) -> str:
        return _sha(value, "population_occurrence_fingerprint")

    @model_validator(mode="after")
    def target_is_in_scope(self) -> "ChinaAshareSourceExpansionTargetV1":
        if self.disposition is ChinaAsharePopulationDisposition.OUTSIDE_SCOPE:
            raise ValueError("outside-scope occurrence cannot be an expansion target")
        return self


class ChinaAshareSourceExpansionPartitionSpecV1(FrozenContract):
    partition_index: int = Field(ge=0)
    targets: tuple[ChinaAshareSourceExpansionTargetV1, ...] = Field(min_length=1)
    logical_fingerprint: str

    @field_validator("logical_fingerprint")
    @classmethod
    def fingerprint_is_sha256(cls, value: str) -> str:
        return _sha(value, "logical_fingerprint")

    @model_validator(mode="after")
    def partition_reconciles(self) -> "ChinaAshareSourceExpansionPartitionSpecV1":
        keys = tuple(item.source_security_id for item in self.targets)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("source expansion targets must be unique and sorted")
        if source_expansion_partition_spec_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("source expansion partition fingerprint differs")
        return self


class ChinaAshareSourceExpansionPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-source-expansion-plan/1.0"
    ] = SOURCE_EXPANSION_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    provider_id: Literal["baostock_ashare"] = SOURCE_EXPANSION_PROVIDER_ID
    registered_at: datetime
    population_package_fingerprint: str
    population_occurrence_set_fingerprint: str
    interval_start: date
    interval_end: date
    partition_size: int = Field(ge=1, le=250)
    partitions: tuple[ChinaAshareSourceExpansionPartitionSpecV1, ...] = Field(
        min_length=1
    )
    target_count: int = Field(ge=1)
    expected_source_request_count: int = Field(ge=2)
    raw_source_layer_only: Literal[True] = True
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("registered_at")
    @classmethod
    def registered_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("interval_start", "interval_end", mode="before")
    @classmethod
    def interval_values_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("source expansion interval cannot contain datetimes")
        return value

    @field_validator(
        "population_package_fingerprint",
        "population_occurrence_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareSourceExpansionPlanV1":
        if self.interval_end < self.interval_start:
            raise ValueError("source expansion interval is reversed")
        indices = tuple(item.partition_index for item in self.partitions)
        if indices != tuple(range(len(self.partitions))):
            raise ValueError("source expansion partition indices are not contiguous")
        targets = tuple(target for item in self.partitions for target in item.targets)
        keys = tuple(item.source_security_id for item in targets)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("source expansion plan targets differ")
        if any(len(item.targets) > self.partition_size for item in self.partitions):
            raise ValueError("source expansion partition exceeds its ceiling")
        if self.target_count != len(targets):
            raise ValueError("source expansion target count differs")
        if self.expected_source_request_count != self.target_count * 2:
            raise ValueError("source expansion request count differs")
        if source_expansion_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("source expansion plan fingerprint differs")
        return self


class ChinaAshareRawDailySourceRowV1(FrozenContract):
    source_security_id: str
    session_date: date
    open: str
    high: str
    low: str
    close: str
    pre_close: str
    volume: str
    amount: str
    provider_trade_status: str
    provider_risk_warning: str
    ingested_at: datetime

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("raw daily source security ID is invalid")
        return normalized

    @field_validator("session_date", mode="before")
    @classmethod
    def session_value_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("raw daily session cannot be datetime")
        return value

    @field_validator(
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "volume",
        "amount",
        "provider_trade_status",
        "provider_risk_warning",
        mode="before",
    )
    @classmethod
    def source_values_are_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("ingested_at")
    @classmethod
    def ingested_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class ChinaAshareRawAdjustmentSourceRowV1(FrozenContract):
    source_security_id: str
    session_date: date
    provider_factor: str
    fore_adjust_factor: str
    back_adjust_factor: str
    ingested_at: datetime

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("raw adjustment source security ID is invalid")
        return normalized

    @field_validator("session_date", mode="before")
    @classmethod
    def session_value_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("raw adjustment session cannot be datetime")
        return value

    @field_validator(
        "provider_factor", "fore_adjust_factor", "back_adjust_factor", mode="before"
    )
    @classmethod
    def factors_are_positive_decimal_strings(cls, value: object) -> str:
        normalized = str(value or "").strip()
        try:
            number = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError("raw adjustment factor is invalid") from exc
        if not number.is_finite() or number <= 0:
            raise ValueError("raw adjustment factor must be positive")
        return normalized

    @field_validator("ingested_at")
    @classmethod
    def ingested_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class ChinaAshareSourceExpansionPartitionManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    partition_version: Literal[
        "china-ashare-source-expansion-partition/1.0"
    ] = SOURCE_EXPANSION_PARTITION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    provider_id: Literal["baostock_ashare"] = SOURCE_EXPANSION_PROVIDER_ID
    plan_fingerprint: str
    partition_fingerprint: str
    partition_index: int = Field(ge=0)
    captured_at: datetime
    target_count: int = Field(ge=1)
    source_request_count: int = Field(ge=2)
    daily_row_count: int = Field(ge=0)
    adjustment_row_count: int = Field(ge=0)
    daily_zero_row_ids: tuple[str, ...]
    adjustment_zero_row_ids: tuple[str, ...]
    daily_parquet_bytes: int = Field(ge=1)
    daily_parquet_sha256: str
    adjustment_parquet_bytes: int = Field(ge=1)
    adjustment_parquet_sha256: str
    source_available_at_complete: Literal[False] = False
    raw_source_layer_only: Literal[True] = True
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("captured_at")
    @classmethod
    def captured_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "plan_fingerprint",
        "partition_fingerprint",
        "daily_parquet_sha256",
        "adjustment_parquet_sha256",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("daily_zero_row_ids", "adjustment_zero_row_ids", mode="before")
    @classmethod
    def source_id_sets_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("zero-row IDs must be a collection")
        normalized = tuple(sorted({str(item).strip().lower() for item in value}))
        if any(not _SOURCE_SECURITY_ID.fullmatch(item) for item in normalized):
            raise ValueError("zero-row source security ID is invalid")
        return normalized

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "ChinaAshareSourceExpansionPartitionManifestV1":
        if self.source_request_count != self.target_count * 2:
            raise ValueError("source expansion partition request count differs")
        if source_expansion_partition_manifest_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("source expansion partition manifest differs")
        return self


def build_source_expansion_target(**values: Any) -> ChinaAshareSourceExpansionTargetV1:
    return ChinaAshareSourceExpansionTargetV1.model_validate(values)


def build_source_expansion_partition_spec(
    **values: Any,
) -> ChinaAshareSourceExpansionPartitionSpecV1:
    candidate = ChinaAshareSourceExpansionPartitionSpecV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareSourceExpansionPartitionSpecV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": source_expansion_partition_spec_fingerprint(
                candidate
            ),
        }
    )


def build_source_expansion_plan(**values: Any) -> ChinaAshareSourceExpansionPlanV1:
    candidate = ChinaAshareSourceExpansionPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareSourceExpansionPlanV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": source_expansion_plan_fingerprint(candidate),
        }
    )


def build_source_expansion_partition_manifest(
    **values: Any,
) -> ChinaAshareSourceExpansionPartitionManifestV1:
    candidate = ChinaAshareSourceExpansionPartitionManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareSourceExpansionPartitionManifestV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": source_expansion_partition_manifest_fingerprint(
                candidate
            ),
        }
    )


def source_expansion_partition_spec_fingerprint(
    value: ChinaAshareSourceExpansionPartitionSpecV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def source_expansion_plan_fingerprint(value: ChinaAshareSourceExpansionPlanV1) -> str:
    return _fingerprint(
        value.model_dump(
            mode="json", exclude={"logical_fingerprint", "registered_at"}
        )
    )


def source_expansion_partition_manifest_fingerprint(
    value: ChinaAshareSourceExpansionPartitionManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _sha(value: str, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()
