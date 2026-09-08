"""Provider-neutral traditional, theme, and analytical classification contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import (
    QualityStatus,
    ensure_finite_decimal,
    normalize_optional_string,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)
from tip_api.contracts.market_data.v1.historical_research import KnowledgeTimeStatus
from tip_api.contracts.market_data.v1.provider_instrument_identity import ResolutionStatus


_SHA256 = r"^[0-9a-f]{64}$"


class ClassificationType(StrEnum):
    SECTOR = "sector"
    INDUSTRY_GROUP = "industry_group"
    INDUSTRY = "industry"
    SUB_INDUSTRY = "sub_industry"
    THEME = "theme"
    ANALYTICAL_GROUP = "analytical_group"


class ClassificationDefinitionStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class ClassificationAssignmentBasis(StrEnum):
    DIRECT_SECURITY = "direct_security"
    ISSUER_PROJECTED = "issuer_projected"
    UNRESOLVED = "unresolved"


class ClassificationIdentityEvidenceKind(StrEnum):
    PROVIDER_SECURITY_ID = "provider_security_id"
    SHARE_CLASS_FIGI = "share_class_figi"
    COMPOSITE_FIGI = "composite_figi"
    CIK_PLUS_SECURITY_EVIDENCE = "cik_plus_security_evidence"
    REVIEWED_ISSUER_PROJECTION = "reviewed_issuer_projection"


class ClassificationObservationStatus(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"
    QUARANTINED = "quarantined"


class ClassificationEligibilityScope(StrEnum):
    INELIGIBLE = "ineligible"
    CURRENT_DISPLAY_ONLY = "current_display_only"
    HISTORICAL_RESEARCH = "historical_research"


class ClassificationMembershipRole(StrEnum):
    PRIMARY = "primary"
    COMPONENT = "component"


class ClassificationReviewStatus(StrEnum):
    AUTO_RESOLVED = "auto_resolved"
    REVIEWED = "reviewed"
    QUARANTINED = "quarantined"


class ClassificationCoverageStatus(StrEnum):
    CLASSIFIED = "classified"
    NOT_COVERED = "not_covered"
    AMBIGUOUS = "ambiguous"
    EXCLUDED = "excluded"
    QUARANTINED = "quarantined"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExternalClassificationPathNodeV1(FrozenContract):
    """One ordered provider-taxonomy node without canonical authority."""

    schema_version: Literal["1.0"] = "1.0"
    level: int = Field(ge=1, le=8)
    code: str
    name: str
    level_name: str | None = None

    @field_validator("code", "name", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("level_name", mode="before")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="level_name")


class ClassificationSourceObservationV1(FrozenContract):
    """One provider taxonomy observation before canonical mapping."""

    schema_version: Literal["1.0"] = "1.0"
    source_observation_id: str
    provider: str
    as_of_date: date
    source_entity_id: str
    source_security_id: str | None = None
    instrument_id: UUID | None = None
    identity_resolution_status: ResolutionStatus
    identity_evidence: tuple[ClassificationIdentityEvidenceKind, ...] = ()
    assignment_basis: ClassificationAssignmentBasis
    external_taxonomy: str
    external_taxonomy_version: str
    external_classification_code: str
    external_classification_path: tuple[ExternalClassificationPathNodeV1, ...]
    valid_from: date
    valid_to: date | None = None
    knowledge_time_status: KnowledgeTimeStatus
    source_available_at: datetime | None = None
    provider_updated_at: datetime | None = None
    observed_at: datetime
    revision_id: str | None = None
    supersedes_source_observation_id: str | None = None
    correction_status: ClassificationObservationStatus
    permission_review_fingerprint: str = Field(pattern=_SHA256)
    eligibility_scope: ClassificationEligibilityScope
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()

    @field_validator("as_of_date", "valid_from", "valid_to", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator(
        "source_observation_id",
        "provider",
        "source_entity_id",
        "external_taxonomy",
        "external_taxonomy_version",
        "external_classification_code",
        mode="before",
    )
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator(
        "source_security_id",
        "revision_id",
        "supersedes_source_observation_id",
        mode="before",
    )
    @classmethod
    def optional_text(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name)

    @field_validator("source_available_at", "provider_updated_at", "observed_at")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_utc_datetime(value)

    @field_validator("identity_evidence", mode="before")
    @classmethod
    def identity_evidence_is_unique(cls, value: Any) -> tuple[Any, ...]:
        return tuple(sorted(_unique_tuple(value, "identity_evidence"), key=str))

    @field_validator("quality_flags", mode="before")
    @classmethod
    def quality_flags_are_normalized(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "quality_flags")

    @model_validator(mode="after")
    def reconcile(self) -> "ClassificationSourceObservationV1":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be later than valid_from")
        if self.as_of_date < self.valid_from:
            raise ValueError("as_of_date must not precede valid_from")
        if self.provider_updated_at is not None and self.provider_updated_at > self.observed_at:
            raise ValueError("provider_updated_at must not follow observed_at")

        levels = tuple(node.level for node in self.external_classification_path)
        if not levels or levels != tuple(range(1, len(levels) + 1)):
            raise ValueError("external classification path levels must be contiguous from one")
        if self.external_classification_path[-1].code != self.external_classification_code:
            raise ValueError("external classification code must match the terminal path node")

        resolved = self.identity_resolution_status is ResolutionStatus.RESOLVED
        if resolved:
            if self.instrument_id is None or not self.identity_evidence:
                raise ValueError("resolved classification requires instrument and identity evidence")
            if self.assignment_basis is ClassificationAssignmentBasis.UNRESOLVED:
                raise ValueError("resolved classification requires an assignment basis")
            if self.assignment_basis is ClassificationAssignmentBasis.DIRECT_SECURITY:
                if self.source_security_id is None:
                    raise ValueError("direct-security assignment requires source_security_id")
                direct_evidence = {
                    ClassificationIdentityEvidenceKind.PROVIDER_SECURITY_ID,
                    ClassificationIdentityEvidenceKind.SHARE_CLASS_FIGI,
                    ClassificationIdentityEvidenceKind.COMPOSITE_FIGI,
                    ClassificationIdentityEvidenceKind.CIK_PLUS_SECURITY_EVIDENCE,
                }
                if not direct_evidence.intersection(self.identity_evidence):
                    raise ValueError("direct-security assignment lacks stable security evidence")
            elif (
                ClassificationIdentityEvidenceKind.REVIEWED_ISSUER_PROJECTION
                not in self.identity_evidence
            ):
                raise ValueError("issuer projection requires reviewed projection evidence")
        else:
            if self.instrument_id is not None:
                raise ValueError("unresolved classification must not carry instrument_id")
            if self.assignment_basis is not ClassificationAssignmentBasis.UNRESOLVED:
                raise ValueError("unresolved classification must use unresolved assignment basis")
            if self.identity_evidence:
                raise ValueError("unresolved classification must not claim positive identity evidence")
            if not self.quality_flags:
                raise ValueError("unresolved classification requires quality flags")

        if self.knowledge_time_status is KnowledgeTimeStatus.SOURCE_TIMESTAMP:
            if self.source_available_at is None:
                raise ValueError("source timestamp knowledge requires source_available_at")
            if self.source_available_at > self.observed_at:
                raise ValueError("source_available_at must not follow observed_at")
        elif self.source_available_at is not None:
            raise ValueError("source_available_at requires source_timestamp knowledge")

        if self.correction_status in {
            ClassificationObservationStatus.CANCELLED,
            ClassificationObservationStatus.QUARANTINED,
        }:
            if self.eligibility_scope is not ClassificationEligibilityScope.INELIGIBLE:
                raise ValueError("cancelled or quarantined observation must be ineligible")
            if not self.quality_flags:
                raise ValueError("cancelled or quarantined observation requires quality flags")
        eligible_status = self.correction_status in {
            ClassificationObservationStatus.ACTIVE,
            ClassificationObservationStatus.CORRECTED,
        }
        eligible_quality = self.quality_status in {QualityStatus.VALID, QualityStatus.WARNING}
        if self.eligibility_scope is not ClassificationEligibilityScope.INELIGIBLE:
            if not resolved or not eligible_status or not eligible_quality:
                raise ValueError("eligible classification observation must be resolved and usable")
        if self.eligibility_scope is ClassificationEligibilityScope.HISTORICAL_RESEARCH:
            if self.knowledge_time_status is not KnowledgeTimeStatus.SOURCE_TIMESTAMP:
                raise ValueError("historical eligibility requires source timestamp knowledge")
        if self.supersedes_source_observation_id == self.source_observation_id:
            raise ValueError("classification observation cannot supersede itself")
        revision_status = self.correction_status in {
            ClassificationObservationStatus.CORRECTED,
            ClassificationObservationStatus.CANCELLED,
        }
        if revision_status:
            if self.revision_id is None or self.supersedes_source_observation_id is None:
                raise ValueError(
                    "corrected or cancelled observation requires revision and superseded ID"
                )
        elif self.supersedes_source_observation_id is not None:
            raise ValueError(
                "only corrected or cancelled observation may supersede another record"
            )
        return self


class ClassificationDefinitionV1(FrozenContract):
    """One canonical classification node for one methodology-valid interval."""

    schema_version: Literal["1.0"] = "1.0"
    classification_id: UUID
    classification_type: ClassificationType
    name: str
    description: str | None = None
    parent_classification_id: UUID | None = None
    methodology_version: str
    status: ClassificationDefinitionStatus
    valid_from: date
    valid_to: date | None = None
    source: str

    @field_validator("valid_from", "valid_to", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("name", "methodology_version", "source", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("description", mode="before")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="description")

    @model_validator(mode="after")
    def reconcile(self) -> "ClassificationDefinitionV1":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be later than valid_from")
        if self.classification_type is ClassificationType.SECTOR:
            if self.parent_classification_id is not None:
                raise ValueError("sector definition must not have a parent")
        elif self.classification_type in {
            ClassificationType.INDUSTRY_GROUP,
            ClassificationType.INDUSTRY,
            ClassificationType.SUB_INDUSTRY,
        } and self.parent_classification_id is None:
            raise ValueError("traditional child definition requires a parent")
        if self.parent_classification_id == self.classification_id:
            raise ValueError("classification definition cannot parent itself")
        return self


class ClassificationMembershipV1(FrozenContract):
    """One canonical stable-instrument membership backed by a source observation."""

    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    classification_id: UUID
    valid_from: date
    valid_to: date | None = None
    membership_role: ClassificationMembershipRole
    membership_weight: Decimal | None = None
    confidence: Decimal | None = None
    source: str
    source_reference: str | None = None
    source_observation_id: str
    assignment_basis: ClassificationAssignmentBasis
    source_available_at: datetime | None = None
    eligibility_scope: ClassificationEligibilityScope
    assigned_at: datetime
    review_status: ClassificationReviewStatus
    methodology_version: str
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()

    @field_validator("valid_from", "valid_to", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("source", "source_observation_id", "methodology_version", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("source_reference", mode="before")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="source_reference")

    @field_validator("membership_weight", "confidence", mode="before")
    @classmethod
    def reject_float_decimals(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator("membership_weight", "confidence")
    @classmethod
    def bounded_decimals(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value <= 0 or value > 1:
            raise ValueError(f"{info.field_name} must be in (0, 1]")
        return value

    @field_validator("source_available_at", "assigned_at")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_utc_datetime(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def quality_flags_are_normalized(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "quality_flags")

    @model_validator(mode="after")
    def reconcile(self) -> "ClassificationMembershipV1":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be later than valid_from")
        if self.assignment_basis is ClassificationAssignmentBasis.UNRESOLVED:
            raise ValueError("canonical membership cannot use unresolved assignment basis")
        if self.eligibility_scope is ClassificationEligibilityScope.INELIGIBLE:
            raise ValueError("ineligible evidence cannot create canonical membership")
        if self.source_available_at is not None and self.source_available_at > self.assigned_at:
            raise ValueError("source_available_at must not follow assigned_at")
        if (
            self.eligibility_scope is ClassificationEligibilityScope.HISTORICAL_RESEARCH
            and self.source_available_at is None
        ):
            raise ValueError("historical membership requires source_available_at")
        if self.review_status is ClassificationReviewStatus.QUARANTINED:
            raise ValueError("quarantined review cannot create canonical membership")
        if self.quality_status not in {QualityStatus.VALID, QualityStatus.WARNING}:
            raise ValueError("canonical membership requires usable quality status")
        return self


class ClassificationCoverageDecisionV1(FrozenContract):
    """One expected stable instrument's explicit classification disposition."""

    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    as_of_date: date
    status: ClassificationCoverageStatus
    source_observation_ids: tuple[str, ...] = ()
    classification_ids: tuple[UUID, ...] = ()
    eligibility_scope: ClassificationEligibilityScope
    reason_codes: tuple[str, ...] = ()
    evaluated_at: datetime
    quality_status: QualityStatus

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("source_observation_ids", mode="before")
    @classmethod
    def source_ids_are_unique(cls, value: Any) -> tuple[str, ...]:
        normalized = _normalized_text_tuple(value, "source_observation_ids")
        return normalized

    @field_validator("classification_ids", mode="before")
    @classmethod
    def classification_ids_are_unique(cls, value: Any) -> tuple[Any, ...]:
        return tuple(sorted(_unique_tuple(value, "classification_ids"), key=str))

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_normalized(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "reason_codes")

    @field_validator("evaluated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconcile(self) -> "ClassificationCoverageDecisionV1":
        if self.status is ClassificationCoverageStatus.CLASSIFIED:
            if not self.source_observation_ids or not self.classification_ids:
                raise ValueError("classified coverage requires source observations and classifications")
            if self.eligibility_scope is ClassificationEligibilityScope.INELIGIBLE:
                raise ValueError("classified coverage must be eligible")
            if self.quality_status not in {QualityStatus.VALID, QualityStatus.WARNING}:
                raise ValueError("classified coverage requires usable quality status")
        else:
            if self.classification_ids:
                raise ValueError("non-classified coverage cannot carry classification IDs")
            if self.eligibility_scope is not ClassificationEligibilityScope.INELIGIBLE:
                raise ValueError("non-classified coverage must be ineligible")
            if not self.reason_codes:
                raise ValueError("non-classified coverage requires reason codes")
        return self


class ClassificationCoverageSummaryV1(FrozenContract):
    status: ClassificationCoverageStatus
    count: int = Field(ge=0)


class ClassificationSnapshotManifestV1(FrozenContract):
    """Completion marker for one immutable classification snapshot."""

    contract_version: Literal["classification-snapshot/1.0"] = (
        "classification-snapshot/1.0"
    )
    dataset_name: Literal["classification-snapshot"] = "classification-snapshot"
    completion_status: Literal["completed"] = "completed"
    as_of_date: date
    methodology_version: str
    providers: tuple[str, ...]
    permission_review_fingerprints: tuple[str, ...]
    created_at: datetime
    definitions_file: Literal["definitions.parquet"] = "definitions.parquet"
    observations_file: Literal["source-observations.parquet"] = (
        "source-observations.parquet"
    )
    coverage_file: Literal["coverage.parquet"] = "coverage.parquet"
    memberships_file: Literal["memberships.parquet"] = "memberships.parquet"
    definition_count: int = Field(ge=1)
    observation_count: int = Field(ge=0)
    coverage_count: int = Field(ge=1)
    membership_count: int = Field(ge=0)
    coverage_summaries: tuple[ClassificationCoverageSummaryV1, ...]
    current_display_eligible_count: int = Field(ge=0)
    historical_research_eligible_count: int = Field(ge=0)
    definitions_logical_fingerprint: str = Field(pattern=_SHA256)
    observations_logical_fingerprint: str = Field(pattern=_SHA256)
    coverage_logical_fingerprint: str = Field(pattern=_SHA256)
    memberships_logical_fingerprint: str = Field(pattern=_SHA256)
    definitions_sha256: str = Field(pattern=_SHA256)
    observations_sha256: str = Field(pattern=_SHA256)
    coverage_sha256: str = Field(pattern=_SHA256)
    memberships_sha256: str = Field(pattern=_SHA256)
    external_request_count: int = Field(ge=0)
    live_source_accessed: bool
    production_authorized: bool
    historical_research_authorized: bool
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive datetime")
        return value

    @field_validator("methodology_version", mode="before")
    @classmethod
    def methodology_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="methodology_version")

    @field_validator("providers", mode="before")
    @classmethod
    def providers_are_normalized(cls, value: Any) -> tuple[str, ...]:
        providers = _normalized_text_tuple(value, "providers")
        if not providers or providers != tuple(sorted(providers)):
            raise ValueError("providers must be non-empty, unique, and sorted")
        return providers

    @field_validator("permission_review_fingerprints", mode="before")
    @classmethod
    def permission_fingerprints_are_sorted(cls, value: Any) -> tuple[str, ...]:
        values = _normalized_text_tuple(value, "permission_review_fingerprints")
        if not values or values != tuple(sorted(values)) or any(
            len(item) != 64 or any(char not in "0123456789abcdef" for char in item)
            for item in values
        ):
            raise ValueError(
                "permission review fingerprints must be non-empty sorted SHA-256 values"
            )
        return values

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconcile(self) -> "ClassificationSnapshotManifestV1":
        statuses = tuple(item.status for item in self.coverage_summaries)
        expected_statuses = tuple(sorted(ClassificationCoverageStatus, key=lambda item: item.value))
        if statuses != expected_statuses:
            raise ValueError("coverage summaries must contain every status in stable order")
        if sum(item.count for item in self.coverage_summaries) != self.coverage_count:
            raise ValueError("coverage summary counts do not reconcile")
        if self.current_display_eligible_count > self.coverage_count:
            raise ValueError("current-display eligible count exceeds coverage")
        if self.historical_research_eligible_count > self.current_display_eligible_count:
            raise ValueError("historical eligible count exceeds current-display eligibility")
        if self.production_authorized and self.current_display_eligible_count == 0:
            raise ValueError("Production authorization requires current-display coverage")
        if self.historical_research_authorized and self.historical_research_eligible_count == 0:
            raise ValueError("historical authorization requires research-eligible coverage")
        if self.external_request_count > 0 and not self.live_source_accessed:
            raise ValueError("external requests require live_source_accessed")
        expected = classification_fingerprint(
            self.model_dump(mode="python", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("classification snapshot logical fingerprint mismatch")
        return self


def classification_fingerprint(value: Any) -> str:
    payload = json.dumps(
        _canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _unique_tuple(value: Any, field_name: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = (value,)
    else:
        try:
            items = tuple(value)
        except TypeError as exc:
            raise ValueError(f"{field_name} must be iterable") from exc
    if len(set(items)) != len(items):
        raise ValueError(f"{field_name} must not contain duplicates")
    return items


def _normalized_text_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    items = _unique_tuple(value, field_name)
    normalized = tuple(
        normalize_required_string(item, field_name=field_name) for item in items
    )
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} must not contain normalized duplicates")
    return tuple(sorted(normalized))


def _normalized_codes(value: Any, field_name: str) -> tuple[str, ...]:
    items = _normalized_text_tuple(value, field_name)
    normalized = tuple(item.lower().replace("-", "_").replace(" ", "_") for item in items)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} must not contain normalized duplicates")
    return tuple(sorted(normalized))


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python"))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("classification fingerprint Decimal must be finite")
        return _decimal_to_string(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _decimal_to_string(value: Decimal) -> str:
    sign, raw_digits, exponent = value.as_tuple()
    digits = "".join(str(digit) for digit in raw_digits).lstrip("0")
    if not digits:
        return "-0" if sign else "0"
    trailing_zero_count = len(digits) - len(digits.rstrip("0"))
    if trailing_zero_count:
        digits = digits[:-trailing_zero_count]
        exponent += trailing_zero_count
    if exponent >= 0:
        rendered = digits + ("0" * exponent)
    else:
        point = len(digits) + exponent
        rendered = (
            digits[:point] + "." + digits[point:]
            if point > 0
            else "0." + ("0" * -point) + digits
        )
    return ("-" if sign else "") + rendered
