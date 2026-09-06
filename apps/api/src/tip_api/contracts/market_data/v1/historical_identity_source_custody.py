"""Normalized durable custody for historical Identity reference observations."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime


CONTRACT_VERSION = "historical-identity-source-custody/1.0"
DAILY_CONTRACT_VERSION = "historical-identity-source-custody/1.1"
ROW_CONTRACT_VERSION = "historical-identity-reference-observation/1.0"
DATASET_NAME = "provider-identity-reference-observation"
SOURCE_FIELD_NAMES = (
    "active",
    "cik",
    "composite_figi",
    "currency_name",
    "last_updated_utc",
    "locale",
    "market",
    "name",
    "primary_exchange",
    "share_class_figi",
    "ticker",
    "type",
)
_SHA256 = r"^[0-9a-f]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalIdentityReferenceObservationV1(FrozenModel):
    """One complete provider result occurrence, without response-envelope data."""

    schema_version: Literal["historical-identity-reference-observation/1.0"] = (
        ROW_CONTRACT_VERSION
    )
    provider: str
    as_of_date: date
    source_observed_at: datetime
    source_page_sequence: int = Field(ge=1)
    source_row_sequence: int = Field(ge=1)
    active: bool | None = None
    cik: str | None = None
    composite_figi: str | None = None
    currency_name: str | None = None
    last_updated_utc: str | None = None
    locale: str | None = None
    market: str | None = None
    name: str | None = None
    primary_exchange: str | None = None
    share_class_figi: str | None = None
    ticker: str | None = None
    type: str | None = None
    source_record_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("provider")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider is required")
        return value.strip()

    @field_validator(*SOURCE_FIELD_NAMES)
    @classmethod
    def source_string_types_are_preserved(
        cls,
        value: Any,
        info: Any,
    ) -> Any:
        if info.field_name == "active":
            if value is not None and not isinstance(value, bool):
                raise ValueError("active must be boolean or null")
            return value
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string or null")
        return value

    @field_validator("source_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def record_fingerprint_reconciles(
        self,
    ) -> "HistoricalIdentityReferenceObservationV1":
        expected = historical_identity_source_fingerprint(
            self.model_dump(mode="json", exclude={"source_record_fingerprint"})
        )
        if self.source_record_fingerprint != expected:
            raise ValueError("historical Identity source-record fingerprint mismatch")
        return self

    def source_payload(self) -> dict[str, object]:
        """Return the complete audited provider result field set."""

        return {name: getattr(self, name) for name in SOURCE_FIELD_NAMES}


class HistoricalIdentitySourceArtifactV1(FrozenModel):
    sequence: int = Field(ge=1)
    source_response_sha256: str = Field(pattern=_SHA256)
    source_response_bytes: int = Field(ge=1)
    row_count: int = Field(ge=0)
    reported_count: int | None = Field(default=None, ge=0)
    reported_status: str | None = None
    pagination_continues: bool

    @field_validator("reported_status")
    @classmethod
    def reported_status_is_bounded(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip() or len(value) > 64:
            raise ValueError("reported status must be a bounded string")
        return value.strip()


class HistoricalIdentitySourceCustodyManifestV1(FrozenModel):
    contract_version: Literal["historical-identity-source-custody/1.0"] = (
        CONTRACT_VERSION
    )
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["provider-identity-reference-observation"] = DATASET_NAME
    data_family_id: Literal["point_in_time_identity"] = "point_in_time_identity"
    data_layer: Literal["source_observation"] = "source_observation"
    content_scope: Literal["internal_only"] = "internal_only"
    retention_class: Literal["canonical_no_auto_expiry"] = (
        "canonical_no_auto_expiry"
    )
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    provider: str
    as_of_date: date
    materialized_at: datetime
    source_package_fetched_at: datetime
    source_locator_sha256: str = Field(pattern=_SHA256)
    source_package_manifest_sha256: str = Field(pattern=_SHA256)
    source_package_content_sha256: str = Field(pattern=_SHA256)
    source_request_count: int = Field(ge=1)
    source_artifacts: tuple[HistoricalIdentitySourceArtifactV1, ...]
    source_field_names: tuple[str, ...]
    identity_rebuild_profile: Literal["current_v1", "pre_etv_governance_v1"]
    identity_profile_map_fingerprint: str = Field(pattern=_SHA256)
    identity_profile_binding_fingerprint: str = Field(pattern=_SHA256)
    canonical_snapshot_fingerprint: str = Field(pattern=_SHA256)
    canonical_instrument_fingerprint: str = Field(pattern=_SHA256)
    canonical_identity_fingerprint: str = Field(pattern=_SHA256)
    canonical_resolver_fingerprint: str = Field(pattern=_SHA256)
    parquet_file: Literal["part-00000.parquet"] = "part-00000.parquet"
    record_count: int = Field(ge=1)
    content_fingerprint: str = Field(pattern=_SHA256)
    parquet_sha256: str = Field(pattern=_SHA256)
    raw_response_retained: Literal[False] = False
    response_url_retained: Literal[False] = False
    request_identifier_retained: Literal[False] = False
    credential_material_retained: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    universe_membership_write_count: Literal[0] = 0
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("provider")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider is required")
        return value.strip()

    @field_validator("materialized_at", "source_package_fetched_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "HistoricalIdentitySourceCustodyManifestV1":
        sequences = tuple(item.sequence for item in self.source_artifacts)
        if sequences != tuple(range(1, len(self.source_artifacts) + 1)):
            raise ValueError("source artifact sequence is not contiguous")
        if self.source_request_count != len(self.source_artifacts):
            raise ValueError("source request count differs from artifacts")
        if sum(item.row_count for item in self.source_artifacts) != self.record_count:
            raise ValueError("source artifact rows differ from record count")
        if self.source_field_names != SOURCE_FIELD_NAMES:
            raise ValueError("historical Identity retained field contract differs")
        expected = historical_identity_source_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("historical Identity source-custody fingerprint mismatch")
        return self


class SameDayIdentitySourceCustodyManifestV1(FrozenModel):
    """Directly bound daily source custody without a historical profile map."""

    contract_version: Literal["historical-identity-source-custody/1.1"] = (
        DAILY_CONTRACT_VERSION
    )
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal["provider-identity-reference-observation"] = DATASET_NAME
    data_family_id: Literal["point_in_time_identity"] = "point_in_time_identity"
    data_layer: Literal["source_observation"] = "source_observation"
    content_scope: Literal["internal_only"] = "internal_only"
    retention_class: Literal["canonical_no_auto_expiry"] = (
        "canonical_no_auto_expiry"
    )
    point_in_time_eligibility: Literal["eligible_at_source_observed_at"] = (
        "eligible_at_source_observed_at"
    )
    binding_origin: Literal["same_day_identity_plan"] = "same_day_identity_plan"
    provider: str
    as_of_date: date
    materialized_at: datetime
    source_package_fetched_at: datetime
    source_locator_sha256: str = Field(pattern=_SHA256)
    source_package_manifest_sha256: str = Field(pattern=_SHA256)
    source_package_content_sha256: str = Field(pattern=_SHA256)
    source_request_count: int = Field(ge=1)
    source_artifacts: tuple[HistoricalIdentitySourceArtifactV1, ...]
    source_field_names: tuple[str, ...]
    identity_rebuild_profile: Literal["current_v1"] = "current_v1"
    source_binding_fingerprint: str = Field(pattern=_SHA256)
    canonical_snapshot_fingerprint: str = Field(pattern=_SHA256)
    canonical_instrument_fingerprint: str = Field(pattern=_SHA256)
    canonical_identity_fingerprint: str = Field(pattern=_SHA256)
    canonical_resolver_fingerprint: str = Field(pattern=_SHA256)
    parquet_file: Literal["part-00000.parquet"] = "part-00000.parquet"
    record_count: int = Field(ge=1)
    content_fingerprint: str = Field(pattern=_SHA256)
    parquet_sha256: str = Field(pattern=_SHA256)
    raw_response_retained: Literal[False] = False
    response_url_retained: Literal[False] = False
    request_identifier_retained: Literal[False] = False
    credential_material_retained: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    universe_membership_write_count: Literal[0] = 0
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("provider")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider is required")
        return value.strip()

    @field_validator("materialized_at", "source_package_fetched_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "SameDayIdentitySourceCustodyManifestV1":
        sequences = tuple(item.sequence for item in self.source_artifacts)
        if sequences != tuple(range(1, len(self.source_artifacts) + 1)):
            raise ValueError("source artifact sequence is not contiguous")
        if self.source_request_count != len(self.source_artifacts):
            raise ValueError("source request count differs from artifacts")
        if sum(item.row_count for item in self.source_artifacts) != self.record_count:
            raise ValueError("source artifact rows differ from record count")
        if self.source_field_names != SOURCE_FIELD_NAMES:
            raise ValueError("daily Identity retained field contract differs")
        expected_binding = historical_identity_source_fingerprint(
            self.model_dump(
                mode="json",
                include={
                    "binding_origin",
                    "provider",
                    "as_of_date",
                    "source_package_fetched_at",
                    "source_locator_sha256",
                    "source_package_manifest_sha256",
                    "source_package_content_sha256",
                    "identity_rebuild_profile",
                    "canonical_snapshot_fingerprint",
                    "canonical_instrument_fingerprint",
                    "canonical_identity_fingerprint",
                    "canonical_resolver_fingerprint",
                },
            )
        )
        if self.source_binding_fingerprint != expected_binding:
            raise ValueError("daily Identity direct-binding fingerprint mismatch")
        expected = historical_identity_source_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("daily Identity source-custody fingerprint mismatch")
        return self


IdentitySourceCustodyManifest = (
    HistoricalIdentitySourceCustodyManifestV1
    | SameDayIdentitySourceCustodyManifestV1
)


def parse_identity_source_custody_manifest(
    value: bytes | str | dict[str, object],
) -> IdentitySourceCustodyManifest:
    """Parse either immutable manifest variant by its explicit version."""

    raw: object
    if isinstance(value, bytes):
        raw = json.loads(value)
    elif isinstance(value, str):
        raw = json.loads(value)
    else:
        raw = value
    if not isinstance(raw, dict):
        raise ValueError("Identity source-custody manifest must be an object")
    version = raw.get("contract_version")
    if version == CONTRACT_VERSION:
        return HistoricalIdentitySourceCustodyManifestV1.model_validate(raw)
    if version == DAILY_CONTRACT_VERSION:
        return SameDayIdentitySourceCustodyManifestV1.model_validate(raw)
    raise ValueError("unsupported Identity source-custody contract version")


def identity_source_binding_fingerprint(
    manifest: IdentitySourceCustodyManifest,
) -> str:
    """Return the origin-appropriate immutable binding fingerprint."""

    if isinstance(manifest, HistoricalIdentitySourceCustodyManifestV1):
        return manifest.identity_profile_binding_fingerprint
    return manifest.source_binding_fingerprint


def build_historical_identity_reference_observation(
    *,
    provider: str,
    as_of_date: date,
    source_observed_at: datetime,
    source_page_sequence: int,
    source_row_sequence: int,
    source_payload: dict[str, object],
) -> HistoricalIdentityReferenceObservationV1:
    values = {
        "schema_version": ROW_CONTRACT_VERSION,
        "provider": provider,
        "as_of_date": as_of_date,
        "source_observed_at": normalize_utc_datetime(source_observed_at),
        "source_page_sequence": source_page_sequence,
        "source_row_sequence": source_row_sequence,
        **{name: source_payload.get(name) for name in SOURCE_FIELD_NAMES},
    }
    return HistoricalIdentityReferenceObservationV1.model_validate(
        {
            **values,
            "source_record_fingerprint": historical_identity_source_fingerprint(
                _json_ready(values)
            ),
        }
    )


def historical_identity_source_fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def historical_identity_source_content_fingerprint(
    records: tuple[HistoricalIdentityReferenceObservationV1, ...],
) -> str:
    return historical_identity_source_fingerprint(
        [item.model_dump(mode="json") for item in records]
    )


def _json_ready(value: object) -> object:
    return to_jsonable_python(value)
