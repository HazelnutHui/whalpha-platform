"""Typed manifest for normalized A-share source-expansion partitions."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import normalize_utc_datetime


NORMALIZED_EXPANSION_METHOD_VERSION = "china-ashare-normalized-expansion/1.0"
NORMALIZED_EXPANSION_PARTITION_VERSION = (
    "china-ashare-normalized-expansion-partition/1.0"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz)\.[0-9]{6}$")


class ChinaAshareNormalizedExpansionPartitionManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    partition_version: Literal[
        "china-ashare-normalized-expansion-partition/1.0"
    ] = NORMALIZED_EXPANSION_PARTITION_VERSION
    method_version: Literal[
        "china-ashare-normalized-expansion/1.0"
    ] = NORMALIZED_EXPANSION_METHOD_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    run_fingerprint: str
    plan_fingerprint: str
    population_package_fingerprint: str
    source_partition_manifest_fingerprint: str
    partition_index: int = Field(ge=0)
    normalized_at: datetime
    target_count: int = Field(ge=1)
    resolved_target_count: int = Field(ge=0)
    quarantined_target_count: int = Field(ge=0)
    source_daily_row_count: int = Field(ge=0)
    source_adjustment_row_count: int = Field(ge=0)
    normalized_bar_count: int = Field(ge=0)
    normalized_state_count: int = Field(ge=0)
    normalized_adjustment_count: int = Field(ge=0)
    suspended_state_count: int = Field(ge=0)
    unknown_trading_state_count: int = Field(ge=0)
    risk_warning_present_state_count: int = Field(ge=0)
    quarantined_daily_row_count: int = Field(ge=0)
    quarantined_adjustment_row_count: int = Field(ge=0)
    quarantined_target_ids: tuple[str, ...]
    bar_parquet_bytes: int = Field(ge=1)
    bar_parquet_sha256: str
    state_parquet_bytes: int = Field(ge=1)
    state_parquet_sha256: str
    adjustment_parquet_bytes: int = Field(ge=1)
    adjustment_parquet_sha256: str
    source_available_at_complete: Literal[False] = False
    normalized_source_observation_layer_only: Literal[True] = True
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("normalized_at")
    @classmethod
    def normalized_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "run_fingerprint",
        "plan_fingerprint",
        "population_package_fingerprint",
        "source_partition_manifest_fingerprint",
        "bar_parquet_sha256",
        "state_parquet_sha256",
        "adjustment_parquet_sha256",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("quarantined_target_ids", mode="before")
    @classmethod
    def quarantined_ids_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("quarantined target IDs must be a collection")
        normalized = tuple(sorted({str(item).strip().lower() for item in value}))
        if any(not _SOURCE_SECURITY_ID.fullmatch(item) for item in normalized):
            raise ValueError("quarantined target ID is invalid")
        return normalized

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "ChinaAshareNormalizedExpansionPartitionManifestV1":
        if self.resolved_target_count + self.quarantined_target_count != (
            self.target_count
        ):
            raise ValueError("normalized expansion target partition differs")
        if len(self.quarantined_target_ids) != self.quarantined_target_count:
            raise ValueError("normalized expansion quarantine target count differs")
        if self.normalized_state_count + self.quarantined_daily_row_count != (
            self.source_daily_row_count
        ):
            raise ValueError("normalized expansion daily row partition differs")
        if (
            self.normalized_adjustment_count
            + self.quarantined_adjustment_row_count
            != self.source_adjustment_row_count
        ):
            raise ValueError("normalized expansion adjustment row partition differs")
        if self.normalized_bar_count > self.normalized_state_count:
            raise ValueError("normalized bars exceed daily states")
        if self.suspended_state_count + self.normalized_bar_count > (
            self.normalized_state_count
        ):
            raise ValueError("normalized trading-state counts differ")
        if self.unknown_trading_state_count > self.normalized_state_count:
            raise ValueError("unknown trading states exceed daily states")
        if self.risk_warning_present_state_count > self.normalized_state_count:
            raise ValueError("risk-warning states exceed daily states")
        if normalized_expansion_partition_manifest_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("normalized expansion manifest fingerprint differs")
        return self


def build_normalized_expansion_partition_manifest(
    **values: Any,
) -> ChinaAshareNormalizedExpansionPartitionManifestV1:
    candidate = ChinaAshareNormalizedExpansionPartitionManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareNormalizedExpansionPartitionManifestV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": (
                normalized_expansion_partition_manifest_fingerprint(candidate)
            ),
        }
    )


def normalized_expansion_run_fingerprint(
    *, plan_fingerprint: str, population_package_fingerprint: str
) -> str:
    payload = json.dumps(
        {
            "method_version": NORMALIZED_EXPANSION_METHOD_VERSION,
            "plan_fingerprint": _sha(plan_fingerprint, "plan_fingerprint"),
            "population_package_fingerprint": _sha(
                population_package_fingerprint,
                "population_package_fingerprint",
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def normalized_expansion_partition_manifest_fingerprint(
    value: ChinaAshareNormalizedExpansionPartitionManifestV1,
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
