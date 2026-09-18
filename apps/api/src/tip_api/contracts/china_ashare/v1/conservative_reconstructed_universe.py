"""Fail-closed, partitioned candidate artifact for reconstructed A-share sessions."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
    FrozenContract,
)


UNIVERSE_PARTITION_VERSION = "china-ashare-conservative-universe-partition/1.0"
UNIVERSE_PACKAGE_VERSION = "china-ashare-conservative-universe-package/1.0"


class ChinaAshareConservativeUniverseDisposition(StrEnum):
    PROVISIONAL_INCLUDE = "provisional_include"
    WARNING_EXCLUDE = "warning_exclude"
    QUARANTINE = "quarantine"


class ChinaAshareConservativeUniverseRowV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    partition_index: int = Field(ge=0, le=108)
    instrument_id: UUID
    source_security_id: str = Field(pattern=r"^(?:sh|sz|bj)\.[0-9]{6}$")
    session_date: date
    knowledge_session_date: date | None
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    trading_status: ChinaAshareTradingStatus
    risk_warning_status: ChinaAshareRiskWarningStatus
    disposition: ChinaAshareConservativeUniverseDisposition
    reason_codes: tuple[str, ...] = Field(min_length=2)
    input_partition_manifest_fingerprint: str
    as_operated: Literal[False] = False
    research_authorized: Literal[False] = False
    return_construction_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False

    @field_validator("input_partition_manifest_fingerprint")
    @classmethod
    def hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "input_partition_manifest_fingerprint")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(sorted(set(str(item) for item in value)))
        if not normalized or any(not item.replace("_", "").isalnum() for item in normalized):
            raise ValueError("conservative Universe reason codes differ")
        return normalized

    @model_validator(mode="after")
    def knowledge_clock_is_forward(self) -> "ChinaAshareConservativeUniverseRowV1":
        if (
            self.knowledge_session_date is not None
            and self.knowledge_session_date <= self.session_date
        ):
            raise ValueError("reconstructed knowledge clock is not next-session")
        if self.disposition is ChinaAshareConservativeUniverseDisposition.PROVISIONAL_INCLUDE:
            if self.knowledge_session_date is None:
                raise ValueError("provisional inclusion lacks next-session clock")
        return self


class ChinaAshareConservativeUniverseArtifactV1(FrozenContract):
    relative_path: str
    byte_size: int = Field(ge=1)
    physical_sha256: str

    @field_validator("relative_path")
    @classmethod
    def path_is_safe(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or str(path) != value:
            raise ValueError("conservative Universe artifact path is unsafe")
        return value

    @field_validator("physical_sha256")
    @classmethod
    def hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class ChinaAshareConservativeUniversePartitionManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    partition_version: Literal[
        "china-ashare-conservative-universe-partition/1.0"
    ] = UNIVERSE_PARTITION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    global_census_fingerprint: str
    partition_census_fingerprint: str
    normalized_partition_manifest_fingerprint: str
    partition_index: int = Field(ge=0, le=108)
    row_count: int = Field(ge=0)
    provisional_include_count: int = Field(ge=0)
    warning_exclude_count: int = Field(ge=0)
    quarantine_count: int = Field(ge=0)
    parquet_bytes: int = Field(ge=1)
    parquet_physical_sha256: str
    logical_row_set_fingerprint: str
    as_operated: Literal[False] = False
    source_available_at_observed: Literal[False] = False
    research_authorized: Literal[False] = False
    return_construction_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "global_census_fingerprint",
        "partition_census_fingerprint",
        "normalized_partition_manifest_fingerprint",
        "parquet_physical_sha256",
        "logical_row_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAshareConservativeUniversePartitionManifestV1":
        if self.provisional_include_count + self.warning_exclude_count + self.quarantine_count != self.row_count:
            raise ValueError("conservative Universe partition counts differ")
        if universe_partition_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("conservative Universe partition fingerprint differs")
        return self


class ChinaAshareConservativeUniversePackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-conservative-universe-package/1.0"
    ] = UNIVERSE_PACKAGE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    global_census_fingerprint: str
    candidate_set_fingerprint: str
    price_limit_smoke_fingerprint: str
    partition_manifest_fingerprints: tuple[str, ...] = Field(
        min_length=109, max_length=109
    )
    partition_count: Literal[109] = 109
    row_count: int = Field(ge=0)
    provisional_include_count: int = Field(ge=0)
    warning_exclude_count: int = Field(ge=0)
    quarantine_count: int = Field(ge=0)
    artifacts: tuple[ChinaAshareConservativeUniverseArtifactV1, ...]
    as_operated: Literal[False] = False
    research_authorized: Literal[False] = False
    return_construction_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "global_census_fingerprint",
        "candidate_set_fingerprint",
        "price_limit_smoke_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("partition_manifest_fingerprints", mode="before")
    @classmethod
    def partition_hashes_are_sha256(cls, value: Any) -> tuple[str, ...]:
        return tuple(_sha(item, "partition_manifest_fingerprints") for item in value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAshareConservativeUniversePackageManifestV1":
        if self.provisional_include_count + self.warning_exclude_count + self.quarantine_count != self.row_count:
            raise ValueError("conservative Universe package counts differ")
        paths = tuple(item.relative_path for item in self.artifacts)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("conservative Universe artifact set differs")
        if universe_package_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("conservative Universe package fingerprint differs")
        return self


def build_universe_partition_manifest(**values: Any):
    return _build(
        ChinaAshareConservativeUniversePartitionManifestV1,
        universe_partition_manifest_fingerprint,
        values,
    )


def build_universe_package_manifest(**values: Any):
    return _build(
        ChinaAshareConservativeUniversePackageManifestV1,
        universe_package_manifest_fingerprint,
        values,
    )


def universe_row_set_fingerprint(rows) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in rows])


def universe_partition_manifest_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def universe_package_manifest_fingerprint(value) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _build(model, fingerprint, values):
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    payload = provisional.model_dump(mode="python")
    payload["logical_fingerprint"] = fingerprint(provisional)
    return model.model_validate(payload)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(item not in "0123456789abcdef" for item in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
