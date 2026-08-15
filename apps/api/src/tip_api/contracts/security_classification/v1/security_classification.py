"""Effective-dated Security Classification V1 contract."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tip_api.contracts.common import normalize_optional_string, normalize_required_string, normalize_utc_datetime


class SecurityForm(StrEnum):
    COMMON_SHARE = "common_share"
    ORDINARY_SHARE = "ordinary_share"
    ADR_ADS = "adr_ads"
    PREFERRED_SHARE = "preferred_share"
    DEPOSITARY_PREFERRED = "depositary_preferred"
    FUND_SHARE = "fund_share"
    TRUST_UNIT = "trust_unit"
    PARTNERSHIP_UNIT = "partnership_unit"
    UNIT = "unit"
    WARRANT = "warrant"
    RIGHT = "right"
    DEBT = "debt"
    STRUCTURED_PRODUCT = "structured_product"
    OTHER = "other"
    UNKNOWN = "unknown"


class IssuerStructure(StrEnum):
    OPERATING_COMPANY = "operating_company"
    EQUITY_REIT = "equity_reit"
    MORTGAGE_REIT = "mortgage_reit"
    BUSINESS_DEVELOPMENT_COMPANY = "business_development_company"
    SPAC_BLANK_CHECK = "spac_blank_check"
    ETF = "etf"
    ETN = "etn"
    CLOSED_END_FUND = "closed_end_fund"
    OPEN_END_FUND = "open_end_fund"
    PARTNERSHIP = "partnership"
    ROYALTY_TRUST = "royalty_trust"
    STRUCTURED_PRODUCT_VEHICLE = "structured_product_vehicle"
    OTHER = "other"
    UNKNOWN = "unknown"


class ListingScope(StrEnum):
    US_DOMESTIC_PRIMARY = "us_domestic_primary"
    US_LISTED_FOREIGN = "us_listed_foreign"
    DEPOSITARY_RECEIPT = "depositary_receipt"
    OTHER = "other"
    UNKNOWN = "unknown"


class ClassificationStatus(StrEnum):
    RESOLVED = "resolved"
    EXCLUDED_RESOLVED = "excluded_resolved"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    MALFORMED = "malformed"


class UniverseDisposition(StrEnum):
    CANDIDATE_CORE = "candidate_core"
    CANDIDATE_US_LISTED_INTERNATIONAL = "candidate_us_listed_international"
    EXCLUDED = "excluded"
    QUARANTINE = "quarantine"


class EvidenceGrade(StrEnum):
    AUTHORITATIVE = "authoritative"
    PROVIDER_EXPLICIT = "provider_explicit"
    REVIEWED_OVERRIDE = "reviewed_override"
    HEURISTIC_FLAG_ONLY = "heuristic_flag_only"
    INSUFFICIENT = "insufficient"


class ClassificationMethod(StrEnum):
    AUTHORITATIVE_OVERRIDE = "authoritative_override"
    PROVIDER_EXPLICIT = "provider_explicit"
    REVIEWED_OVERRIDE = "reviewed_override"
    HEURISTIC_REVIEW_FLAG = "heuristic_review_flag"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ProviderStableIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier_type: str
    value: str

    @field_validator("identifier_type", "value", mode="before")
    @classmethod
    def normalize_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)


class SecurityClassificationV1(BaseModel):
    """One provider-neutral classification valid over a half-open date interval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    taxonomy_version: str
    ruleset_version: str
    instrument_id: UUID
    issuer_id: UUID | None = None
    listing_id: UUID | None = None
    provider: str
    provider_stable_identifiers: tuple[ProviderStableIdentifier, ...] = ()
    as_of_date: date
    effective_from: date
    effective_to: date | None = None
    security_form: SecurityForm
    issuer_structure: IssuerStructure
    listing_scope: ListingScope
    primary_exchange: str
    listing_country: str
    issuer_domicile_country: str
    incorporation_country: str
    is_us_listed: bool
    is_us_domiciled: bool | None
    classification_status: ClassificationStatus
    universe_disposition: UniverseDisposition
    decision_reason_codes: tuple[str, ...]
    classification_method: ClassificationMethod
    evidence_grade: EvidenceGrade
    evidence_ids: tuple[str, ...]
    quality_flags: tuple[str, ...]
    observed_at: datetime
    reviewed_at: datetime
    ingested_at: datetime

    @field_validator("as_of_date", "effective_from", "effective_to", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("taxonomy_version", "ruleset_version", "provider", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("primary_exchange", mode="before")
    @classmethod
    def normalize_exchange(cls, value: str) -> str:
        return normalize_required_string(value, field_name="primary_exchange", uppercase=True)

    @field_validator("listing_country", "issuer_domicile_country", "incorporation_country", mode="before")
    @classmethod
    def normalize_country(cls, value: str, info: Any) -> str:
        normalized = normalize_required_string(value, field_name=info.field_name, uppercase=True)
        if normalized != "UNKNOWN" and (len(normalized) != 2 or not normalized.isalpha()):
            raise ValueError(f"{info.field_name} must be an ISO alpha-2 code or UNKNOWN")
        return normalized

    @field_validator("decision_reason_codes", "evidence_ids", "quality_flags", mode="before")
    @classmethod
    def normalize_string_sets(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError(f"{info.field_name} must be a collection")
        return tuple(sorted({normalize_required_string(item, field_name=info.field_name) for item in value}))

    @field_validator("provider_stable_identifiers", mode="after")
    @classmethod
    def normalize_identifiers(
        cls, value: tuple[ProviderStableIdentifier, ...]
    ) -> tuple[ProviderStableIdentifier, ...]:
        keys = [(item.identifier_type, item.value) for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("provider_stable_identifiers must be unique")
        return tuple(sorted(value, key=lambda item: (item.identifier_type, item.value)))

    @field_validator("observed_at", "reviewed_at", "ingested_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_semantics(self) -> SecurityClassificationV1:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if not self.is_effective_on(self.as_of_date):
            raise ValueError("as_of_date must fall within the effective interval")
        if self.reviewed_at < self.observed_at or self.ingested_at < self.observed_at:
            raise ValueError("reviewed_at and ingested_at must not precede observed_at")
        if self.classification_status in {
            ClassificationStatus.UNKNOWN,
            ClassificationStatus.AMBIGUOUS,
            ClassificationStatus.MALFORMED,
        } and self.universe_disposition is not UniverseDisposition.QUARANTINE:
            raise ValueError("unresolved classifications must be quarantined")
        if self.evidence_grade in {EvidenceGrade.HEURISTIC_FLAG_ONLY, EvidenceGrade.INSUFFICIENT} and self.universe_disposition in {
            UniverseDisposition.CANDIDATE_CORE,
            UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL,
        }:
            raise ValueError("heuristic or insufficient evidence cannot create a candidate")
        if self.universe_disposition is UniverseDisposition.CANDIDATE_CORE:
            if not (
                self.classification_status is ClassificationStatus.RESOLVED
                and self.security_form is SecurityForm.COMMON_SHARE
                and self.issuer_structure in {IssuerStructure.OPERATING_COMPANY, IssuerStructure.EQUITY_REIT}
                and self.listing_scope is ListingScope.US_DOMESTIC_PRIMARY
                and self.is_us_listed
                and self.is_us_domiciled is True
            ):
                raise ValueError("candidate_core classification is inconsistent")
        if self.universe_disposition is UniverseDisposition.CANDIDATE_US_LISTED_INTERNATIONAL:
            if not (
                self.classification_status is ClassificationStatus.RESOLVED
                and self.security_form in {SecurityForm.ORDINARY_SHARE, SecurityForm.ADR_ADS}
                and self.issuer_structure is IssuerStructure.OPERATING_COMPANY
                and self.listing_scope in {ListingScope.US_LISTED_FOREIGN, ListingScope.DEPOSITARY_RECEIPT}
                and self.is_us_listed
                and self.is_us_domiciled is False
            ):
                raise ValueError("candidate_us_listed_international classification is inconsistent")
        return self

    def is_effective_on(self, session_date: date) -> bool:
        return self.effective_from <= session_date and (
            self.effective_to is None or session_date < self.effective_to
        )


def validate_non_overlapping_classifications(records: tuple[SecurityClassificationV1, ...]) -> None:
    """Hard-fail overlapping effective periods for a stable instrument identity."""

    by_instrument: dict[UUID, list[SecurityClassificationV1]] = {}
    for record in records:
        by_instrument.setdefault(record.instrument_id, []).append(record)
    for instrument_records in by_instrument.values():
        ordered = sorted(instrument_records, key=lambda item: item.effective_from)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.effective_to is None or current.effective_from < previous.effective_to:
                raise ValueError("classification effective periods overlap")
