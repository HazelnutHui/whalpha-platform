"""Contracts for the disconnected inactive-lifecycle resolution shadow."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.provider_instrument_identity import (
    ResolutionStatus,
)


SOURCE_ROW_CONTRACT_VERSION = "historical-inactive-lifecycle-source-observation/1.0"
DECISION_ROW_CONTRACT_VERSION = "historical-inactive-lifecycle-resolution-decision/1.0"
MANIFEST_CONTRACT_VERSION = "historical-inactive-lifecycle-resolution-shadow/1.0"
DATASET_NAME = "historical-inactive-lifecycle-resolution-shadow"
SOURCE_FIELD_NAMES = (
    "active",
    "cik",
    "composite_figi",
    "currency_name",
    "delisted_utc",
    "last_updated_utc",
    "locale",
    "market",
    "name",
    "primary_exchange",
    "share_class_figi",
    "ticker",
    "type",
)
REVIEW_LIMITATION_CODES = (
    "last_tradable_date_unverified",
    "provider_delisted_date_candidate_only",
    "source_availability_unverified",
    "successor_unverified",
    "terminal_reason_unverified",
)
QUARANTINE_REASON_CODES = frozenset(
    {
        "canonical_instrument_seen_after_delisted_date",
        "delisted_date_after_anchor",
        "delisted_date_malformed",
        "delisted_date_missing",
        "missing_stable_security_identifier",
        "source_ticker_absent_from_canonical_history",
        "stable_identifier_absent_from_canonical_history",
        "stable_identifier_collision",
    }
)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class InactiveLifecycleDisposition(StrEnum):
    """Disposition at the review-only shadow boundary."""

    REVIEW_CANDIDATE = "review_candidate"
    QUARANTINED = "quarantined"


class InactiveLifecycleIdentityType(StrEnum):
    """Stable identifiers present in the reviewed source."""

    SHARE_CLASS_FIGI = "share_class_figi"
    COMPOSITE_FIGI = "composite_figi"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalInactiveLifecycleSourceObservationV1(_FrozenModel):
    """One lossless, located occurrence from an inactive source page."""

    schema_version: Literal[
        "historical-inactive-lifecycle-source-observation/1.0"
    ] = SOURCE_ROW_CONTRACT_VERSION
    provider: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    anchor_date: date
    source_observed_at: datetime
    source_page_sequence: int = Field(ge=1)
    source_row_sequence: int = Field(ge=1)
    active: Literal[False] = False
    cik: str | None = None
    composite_figi: str | None = None
    currency_name: str | None = None
    delisted_utc: str | None = None
    last_updated_utc: str | None = None
    locale: str | None = None
    market: str | None = None
    name: str | None = None
    primary_exchange: str | None = None
    share_class_figi: str | None = None
    ticker: str | None = None
    type: str | None = None
    source_payload_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_observation_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def fingerprints_reconcile(self) -> "HistoricalInactiveLifecycleSourceObservationV1":
        payload = {field: getattr(self, field) for field in SOURCE_FIELD_NAMES}
        if self.source_payload_fingerprint != inactive_lifecycle_fingerprint(payload):
            raise ValueError("inactive lifecycle source payload fingerprint differs")
        occurrence = {
            "anchor_date": self.anchor_date,
            "source_page_sequence": self.source_page_sequence,
            "source_row_sequence": self.source_row_sequence,
            "source_payload_fingerprint": self.source_payload_fingerprint,
        }
        if self.source_observation_fingerprint != inactive_lifecycle_fingerprint(
            occurrence
        ):
            raise ValueError("inactive lifecycle source occurrence fingerprint differs")
        return self


class HistoricalInactiveLifecycleResolutionDecisionV1(_FrozenModel):
    """One fail-closed identity and lifecycle decision for one source occurrence."""

    schema_version: Literal[
        "historical-inactive-lifecycle-resolution-decision/1.0"
    ] = DECISION_ROW_CONTRACT_VERSION
    provider: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    anchor_date: date
    source_observation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_payload_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_page_sequence: int = Field(ge=1)
    source_row_sequence: int = Field(ge=1)
    selected_identity_type: InactiveLifecycleIdentityType | None = None
    selected_identity_value: str | None = None
    identity_resolution_status: ResolutionStatus
    canonical_instrument_id: UUID | None = None
    canonical_first_observed_date: date | None = None
    canonical_last_observed_date: date | None = None
    effective_date_candidate: date | None = None
    ticker_seen_in_canonical_history: bool | None = None
    disposition: InactiveLifecycleDisposition
    reason_codes: tuple[str, ...] = Field(min_length=1)
    source_package_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_instrument_history_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    evaluated_at: datetime

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("selected_identity_value", mode="before")
    @classmethod
    def normalize_identity_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("selected identity value is empty")
        return normalized

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            value = (value,)
        try:
            codes = tuple(value)
        except TypeError as exc:
            raise ValueError("reason codes must be iterable") from exc
        if any(not isinstance(item, str) or not item for item in codes):
            raise ValueError("reason codes must be non-empty strings")
        if codes != tuple(sorted(set(codes))):
            raise ValueError("reason codes must be sorted and unique")
        return codes

    @model_validator(mode="after")
    def decision_reconciles(self) -> "HistoricalInactiveLifecycleResolutionDecisionV1":
        if (self.selected_identity_type is None) != (
            self.selected_identity_value is None
        ):
            raise ValueError("selected identity fields are incomplete")
        canonical_values = (
            self.canonical_instrument_id,
            self.canonical_first_observed_date,
            self.canonical_last_observed_date,
        )
        if any(value is not None for value in canonical_values) and not all(
            value is not None for value in canonical_values
        ):
            raise ValueError("canonical history fields are incomplete")
        if (
            self.canonical_first_observed_date is not None
            and self.canonical_last_observed_date is not None
            and self.canonical_last_observed_date
            < self.canonical_first_observed_date
        ):
            raise ValueError("canonical history bounds are reversed")
        if self.identity_resolution_status is ResolutionStatus.RESOLVED:
            if self.canonical_instrument_id is None or self.selected_identity_type is None:
                raise ValueError("resolved decision requires canonical identity")
        elif self.canonical_instrument_id is not None:
            raise ValueError("non-resolved decision carries canonical identity")
        codes = set(self.reason_codes)
        if self.disposition is InactiveLifecycleDisposition.REVIEW_CANDIDATE:
            if self.identity_resolution_status is not ResolutionStatus.RESOLVED:
                raise ValueError("review candidate identity is not resolved")
            if self.effective_date_candidate is None:
                raise ValueError("review candidate lacks an effective-date candidate")
            if self.effective_date_candidate > self.anchor_date:
                raise ValueError("review candidate effective date exceeds anchor")
            if self.ticker_seen_in_canonical_history is not True:
                raise ValueError("review candidate ticker evidence differs")
            if (
                self.canonical_last_observed_date is None
                or self.canonical_last_observed_date > self.effective_date_candidate
            ):
                raise ValueError("review candidate has a temporal contradiction")
            if codes != set(REVIEW_LIMITATION_CODES):
                raise ValueError("review candidate limitations differ")
        elif not codes or not codes.issubset(QUARANTINE_REASON_CODES):
            raise ValueError("quarantine reasons are unsupported")
        return self


class InactiveLifecycleShadowArtifactV1(_FrozenModel):
    file_name: str
    row_contract_version: str
    record_count: int = Field(ge=1)
    byte_size: int = Field(ge=1)
    content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)


class HistoricalInactiveLifecycleResolutionShadowManifestV1(_FrozenModel):
    """Sealed, disconnected shadow manifest."""

    contract_version: Literal[
        "historical-inactive-lifecycle-resolution-shadow/1.0"
    ] = MANIFEST_CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "historical-inactive-lifecycle-resolution-shadow"
    ] = DATASET_NAME
    provider: Literal["massive_stocks_basic"] = "massive_stocks_basic"
    anchor_date: date
    materialized_at: datetime
    source_package_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_package_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_package_record_count: int = Field(ge=1)
    canonical_history_first_date: date
    canonical_history_last_date: date
    canonical_history_session_count: int = Field(ge=1)
    canonical_history_record_count: int = Field(ge=1)
    canonical_history_unique_instrument_count: int = Field(ge=1)
    canonical_instrument_history_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_artifact: InactiveLifecycleShadowArtifactV1
    decision_artifact: InactiveLifecycleShadowArtifactV1
    disposition_counts: tuple[tuple[str, int], ...]
    resolution_status_counts: tuple[tuple[str, int], ...]
    reason_counts: tuple[tuple[str, int], ...]
    source_decision_one_to_one: Literal[True] = True
    ticker_positive_resolution_count: Literal[0] = 0
    cik_positive_resolution_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("materialized_at")
    @classmethod
    def materialized_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("disposition_counts", "resolution_status_counts", "reason_counts")
    @classmethod
    def counts_are_canonical(
        cls, value: tuple[tuple[str, int], ...]
    ) -> tuple[tuple[str, int], ...]:
        if value != tuple(sorted(value)) or len(value) != len(dict(value)):
            raise ValueError("manifest counts must be sorted and unique")
        if any(not key or count < 0 for key, count in value):
            raise ValueError("manifest counts are invalid")
        return value

    @model_validator(mode="after")
    def manifest_reconciles(
        self,
    ) -> "HistoricalInactiveLifecycleResolutionShadowManifestV1":
        if self.canonical_history_last_date > self.anchor_date:
            raise ValueError("canonical history exceeds source anchor")
        if self.canonical_history_last_date < self.canonical_history_first_date:
            raise ValueError("canonical history bounds are reversed")
        for artifact in (self.source_artifact, self.decision_artifact):
            if artifact.record_count != self.source_package_record_count:
                raise ValueError("shadow artifact count differs from source")
        if (
            self.source_artifact.file_name != "source-observations.parquet"
            or self.source_artifact.row_contract_version
            != SOURCE_ROW_CONTRACT_VERSION
            or self.decision_artifact.file_name != "resolution-decisions.parquet"
            or self.decision_artifact.row_contract_version
            != DECISION_ROW_CONTRACT_VERSION
        ):
            raise ValueError("shadow artifact identity differs")
        if sum(dict(self.disposition_counts).values()) != self.source_package_record_count:
            raise ValueError("disposition counts differ from source")
        if sum(dict(self.resolution_status_counts).values()) != self.source_package_record_count:
            raise ValueError("resolution counts differ from source")
        expected = inactive_lifecycle_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("shadow manifest fingerprint differs")
        return self


def inactive_lifecycle_fingerprint(value: Any) -> str:
    """Return the canonical SHA-256 fingerprint for a contract value."""

    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def inactive_lifecycle_rows_fingerprint(rows: tuple[BaseModel, ...]) -> str:
    """Fingerprint a contract-ordered row collection."""

    return inactive_lifecycle_fingerprint(
        [row.model_dump(mode="json") for row in rows]
    )
