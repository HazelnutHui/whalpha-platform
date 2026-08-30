"""Provider-neutral custody contract for one temporary historical source package."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalSourceRequestKind(StrEnum):
    GROUPED_DAILY = "grouped_daily"
    ACTIVE_ALL_TICKERS = "active_all_tickers"
    INACTIVE_ALL_TICKERS = "inactive_all_tickers"
    SPLITS = "splits"
    DIVIDENDS = "dividends"
    TICKER_EVENTS_EXPERIMENTAL = "ticker_events_experimental"


class HistoricalSourceArtifactV1(FrozenContract):
    request_kind: HistoricalSourceRequestKind
    logical_endpoint: str
    scope: str
    sequence: int = Field(ge=1)
    relative_path: str
    media_type: Literal["application/json"] = "application/json"
    canonical_json: Literal[True] = True
    byte_size: int = Field(ge=1)
    physical_sha256: str

    @field_validator("logical_endpoint", "scope", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("relative_path", mode="before")
    @classmethod
    def normalized_relative_path(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="relative_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("relative_path must be normalized and relative")
        if not normalized.startswith("staged/") or not normalized.endswith(".json"):
            raise ValueError("source artifacts must use the staged JSON boundary")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class HistoricalSourceScopeReceiptV1(FrozenContract):
    request_kind: HistoricalSourceRequestKind
    logical_endpoint: str
    scope: str
    completed: Literal[True] = True
    request_count: int = Field(ge=1)
    request_ceiling: int = Field(ge=1)
    artifacts: tuple[HistoricalSourceArtifactV1, ...] = Field(min_length=1)

    @field_validator("logical_endpoint", "scope", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @model_validator(mode="after")
    def receipt_reconciles(self) -> "HistoricalSourceScopeReceiptV1":
        if self.request_count != len(self.artifacts):
            raise ValueError("scope request count does not match artifact count")
        if self.request_count > self.request_ceiling:
            raise ValueError("scope request count exceeds its reviewed ceiling")
        if tuple(item.sequence for item in self.artifacts) != tuple(
            range(1, self.request_count + 1)
        ):
            raise ValueError("scope artifact sequence must be contiguous")
        if any(
            item.request_kind is not self.request_kind
            or item.logical_endpoint != self.logical_endpoint
            or item.scope != self.scope
            for item in self.artifacts
        ):
            raise ValueError("scope artifacts do not match their receipt")
        return self


class HistoricalSourcePackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal["historical-source-package/1.0"] = (
        "historical-source-package/1.0"
    )
    provider_id: str
    pilot_plan_fingerprint: str
    source_permission_review_fingerprint: str
    account_entitlement_evidence_fingerprint: str
    lifecycle_coverage_review_fingerprint: str
    exact_authorization_acknowledgement_fingerprint: str
    acquired_at: datetime
    serial_pace_seconds: int = Field(ge=15)
    zero_automatic_retry: Literal[True] = True
    request_plan_document_sha256: str
    inventory_document_sha256: str
    scope_receipts: tuple[HistoricalSourceScopeReceiptV1, ...] = Field(min_length=1)
    total_request_count: int = Field(ge=1)
    planned_request_ceiling: int = Field(ge=1)
    source_payload_retention: Literal["temporary_package_only"] = (
        "temporary_package_only"
    )
    canonical_apply_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    scheduler_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("provider_id", mode="before")
    @classmethod
    def safe_provider(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="provider_id").lower()
        if not _SAFE_ID.fullmatch(normalized):
            raise ValueError("provider_id is unsafe")
        return normalized

    @field_validator("acquired_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "pilot_plan_fingerprint",
        "source_permission_review_fingerprint",
        "account_entitlement_evidence_fingerprint",
        "lifecycle_coverage_review_fingerprint",
        "exact_authorization_acknowledgement_fingerprint",
        "request_plan_document_sha256",
        "inventory_document_sha256",
        "logical_fingerprint",
    )
    @classmethod
    def valid_hashes(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "HistoricalSourcePackageManifestV1":
        keys = tuple(
            (item.request_kind.value, item.logical_endpoint, item.scope)
            for item in self.scope_receipts
        )
        if keys != tuple(sorted(set(keys))):
            raise ValueError("scope receipts must be unique and sorted")
        paths = tuple(
            artifact.relative_path
            for receipt in self.scope_receipts
            for artifact in receipt.artifacts
        )
        if len(paths) != len(set(paths)):
            raise ValueError("source artifact paths must be unique")
        if self.total_request_count != sum(
            item.request_count for item in self.scope_receipts
        ):
            raise ValueError("package request count does not reconcile")
        if self.total_request_count > self.planned_request_ceiling:
            raise ValueError("package exceeds the reviewed request ceiling")
        if historical_source_package_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("historical source package fingerprint mismatch")
        return self


def build_historical_source_package_manifest(
    **values: Any,
) -> HistoricalSourcePackageManifestV1:
    provisional = HistoricalSourcePackageManifestV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return HistoricalSourcePackageManifestV1.model_validate(
        {
            **values,
            "logical_fingerprint": historical_source_package_fingerprint(provisional),
        }
    )


def historical_source_package_fingerprint(
    manifest: HistoricalSourcePackageManifestV1,
) -> str:
    payload = manifest.model_dump(mode="json", exclude={"logical_fingerprint"})
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized
