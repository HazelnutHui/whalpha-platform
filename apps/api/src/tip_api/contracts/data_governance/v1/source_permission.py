"""Provider-neutral source permission reviews and default-deny assessments."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.data_governance.v1.record_classification import (
    STANDARD_DATA_FAMILY_REGISTRY_V1,
)


_SOURCE_ID = re.compile(r"[a-z][a-z0-9_]{1,63}")
_FAMILY_IDS = frozenset(
    item.data_family_id for item in STANDARD_DATA_FAMILY_REGISTRY_V1
)


class SourceUseCase(StrEnum):
    DELL_ACQUISITION = "dell_acquisition"
    DELL_RAW_RETENTION = "dell_raw_retention"
    DELL_DERIVED_ANALYSIS = "dell_derived_analysis"
    EQUAL_CAPABILITY_RAW_DISPLAY = "equal_capability_raw_display"
    EQUAL_CAPABILITY_DERIVED_DISPLAY = "equal_capability_derived_display"
    EQUAL_CAPABILITY_MACHINE_DELIVERY = "equal_capability_machine_delivery"


class SourcePermissionConclusion(StrEnum):
    CLEARED = "cleared"
    BLOCKED = "blocked"
    REQUIRES_SEPARATE_PERMISSION = "requires_separate_permission"
    UNRESOLVED = "unresolved"
    NOT_APPLICABLE = "not_applicable"


class SourceUseAssessmentStatus(StrEnum):
    ELIGIBLE_FOR_REQUIRED_USES = "eligible_for_required_uses"
    BLOCKED_BY_PERMISSION = "blocked_by_permission"
    UNRESOLVED_PERMISSION = "unresolved_permission"
    STALE_PERMISSION_REVIEW = "stale_permission_review"
    UNSUPPORTED_DATA_FAMILY = "unsupported_data_family"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceUsePermissionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    use_case: SourceUseCase
    conclusion: SourcePermissionConclusion
    reason_codes: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...]

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_strings(value, field_name="reason_codes")

    @field_validator("evidence_fingerprints", mode="before")
    @classmethod
    def evidence_is_canonical(cls, value: Any) -> tuple[str, ...]:
        normalized = _canonical_strings(value, field_name="evidence_fingerprints")
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in normalized):
            raise ValueError("evidence_fingerprints must contain SHA-256 values")
        return normalized

    @model_validator(mode="after")
    def conclusion_has_evidence(self) -> "SourceUsePermissionV1":
        if not self.evidence_fingerprints:
            raise ValueError("every permission conclusion requires evidence")
        if self.conclusion is not SourcePermissionConclusion.CLEARED and not self.reason_codes:
            raise ValueError("non-cleared permission conclusions require reason codes")
        return self


class SourcePermissionReviewV1(FrozenContract):
    """One effective-dated review; this never grants acquisition authority."""

    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal["source-permission-governance-v1"] = (
        "source-permission-governance-v1"
    )
    source_id: str
    source_display_name: str
    reviewed_at: datetime
    valid_until: datetime
    supported_data_family_ids: tuple[str, ...]
    official_evidence_urls: tuple[str, ...]
    permissions: tuple[SourceUsePermissionV1, ...]
    operational_authority: Literal["none"] = "none"

    @field_validator("source_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="source_id")
        if not _SOURCE_ID.fullmatch(normalized):
            raise ValueError("source_id must be lower snake case")
        return normalized

    @field_validator("source_display_name", mode="before")
    @classmethod
    def display_name_is_required(cls, value: str) -> str:
        return normalize_required_string(value, field_name="source_display_name")

    @field_validator("reviewed_at", "valid_until")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("supported_data_family_ids", mode="before")
    @classmethod
    def families_are_known_and_canonical(cls, value: Any) -> tuple[str, ...]:
        normalized = _canonical_strings(value, field_name="supported_data_family_ids")
        if not normalized:
            raise ValueError("a source review requires at least one data family")
        unknown = tuple(item for item in normalized if item not in _FAMILY_IDS)
        if unknown:
            raise ValueError(f"unknown standard data families: {unknown}")
        return normalized

    @field_validator("official_evidence_urls", mode="before")
    @classmethod
    def urls_are_public_https(cls, value: Any) -> tuple[str, ...]:
        normalized = _canonical_strings(value, field_name="official_evidence_urls")
        if not normalized:
            raise ValueError("a source review requires official evidence URLs")
        for item in normalized:
            parsed = urlsplit(item)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "official evidence URLs must be public HTTPS URLs without credentials, query, or fragment"
                )
        return normalized

    @field_validator("permissions")
    @classmethod
    def permissions_are_complete_and_canonical(
        cls,
        value: tuple[SourceUsePermissionV1, ...],
    ) -> tuple[SourceUsePermissionV1, ...]:
        use_cases = tuple(item.use_case.value for item in value)
        expected = tuple(sorted(item.value for item in SourceUseCase))
        if use_cases != expected:
            raise ValueError("permissions must contain every use case exactly once in canonical order")
        return value

    @model_validator(mode="after")
    def review_window_is_valid(self) -> "SourcePermissionReviewV1":
        if self.valid_until < self.reviewed_at:
            raise ValueError("permission review cannot expire before it was reviewed")
        return self


class SourceUseAssessmentV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal["source-permission-governance-v1"] = (
        "source-permission-governance-v1"
    )
    source_id: str
    data_family_id: str
    assessed_at: datetime
    permission_review_valid_until: datetime
    required_use_cases: tuple[SourceUseCase, ...]
    status: SourceUseAssessmentStatus
    blocking_use_cases: tuple[SourceUseCase, ...]
    unresolved_use_cases: tuple[SourceUseCase, ...]
    reason_codes: tuple[str, ...]
    permission_review_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operational_authority: Literal["none"] = "none"

    @field_validator("source_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="source_id")
        if not _SOURCE_ID.fullmatch(normalized):
            raise ValueError("source_id must be lower snake case")
        return normalized

    @field_validator("data_family_id", mode="before")
    @classmethod
    def family_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="data_family_id")
        if not _SOURCE_ID.fullmatch(normalized):
            raise ValueError("data_family_id must be lower snake case")
        return normalized

    @field_validator("assessed_at", "permission_review_valid_until")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "required_use_cases",
        "blocking_use_cases",
        "unresolved_use_cases",
    )
    @classmethod
    def use_cases_are_canonical(
        cls,
        value: tuple[SourceUseCase, ...],
        info: Any,
    ) -> tuple[SourceUseCase, ...]:
        keys = tuple(item.value for item in value)
        if keys != tuple(sorted(set(keys))):
            raise ValueError(f"{info.field_name} must be sorted and unique")
        if info.field_name == "required_use_cases" and not value:
            raise ValueError("required_use_cases cannot be empty")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_strings(value, field_name="reason_codes")

    @model_validator(mode="after")
    def status_reconciles(self) -> "SourceUseAssessmentV1":
        required = set(self.required_use_cases)
        blocking = set(self.blocking_use_cases)
        unresolved = set(self.unresolved_use_cases)
        if not blocking.issubset(required) or not unresolved.issubset(required):
            raise ValueError("blocking and unresolved uses must be required uses")
        if blocking & unresolved:
            raise ValueError("one required use cannot be both blocked and unresolved")
        review_is_stale = self.assessed_at > self.permission_review_valid_until
        if (
            self.status is SourceUseAssessmentStatus.STALE_PERMISSION_REVIEW
        ) is not review_is_stale:
            raise ValueError("stale status must match the permission review validity")
        if self.status is SourceUseAssessmentStatus.ELIGIBLE_FOR_REQUIRED_USES:
            if blocking or unresolved or self.reason_codes:
                raise ValueError("eligible assessment cannot carry unresolved state")
        elif self.status is SourceUseAssessmentStatus.BLOCKED_BY_PERMISSION:
            if not blocking or not self.reason_codes:
                raise ValueError("blocked assessment requires blocked uses and reasons")
        elif self.status is SourceUseAssessmentStatus.UNRESOLVED_PERMISSION:
            if blocking or not unresolved or not self.reason_codes:
                raise ValueError("unresolved assessment requires unresolved uses and reasons")
        elif blocking or unresolved or not self.reason_codes:
            raise ValueError("stale and unsupported assessments require only reason codes")
        return self


EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1 = tuple(
    sorted(SourceUseCase, key=lambda item: item.value)
)
SOURCE_PERMISSION_POLICY_FINGERPRINT_V1 = hashlib.sha256(
    json.dumps(
        {
            "policy_version": "source-permission-governance-v1",
            "equal_capability_market_source_uses": [
                item.value for item in EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1
            ],
            "permission_conclusions": sorted(
                item.value for item in SourcePermissionConclusion
            ),
            "assessment_statuses": sorted(
                item.value for item in SourceUseAssessmentStatus
            ),
            "operational_authority": "none",
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()


def source_permission_review_fingerprint(review: SourcePermissionReviewV1) -> str:
    return hashlib.sha256(
        json.dumps(
            review.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def assess_source_uses(
    review: SourcePermissionReviewV1,
    *,
    data_family_id: str,
    required_use_cases: tuple[SourceUseCase, ...],
    assessed_at: datetime,
) -> SourceUseAssessmentV1:
    """Assess documented permission only; never contact or authorize a source."""

    normalized_family = normalize_required_string(
        data_family_id,
        field_name="data_family_id",
    )
    normalized_assessed_at = normalize_utc_datetime(assessed_at)
    ordered_required = tuple(sorted(set(required_use_cases), key=lambda item: item.value))
    if not ordered_required:
        raise ValueError("at least one source use case is required")

    reason_codes: list[str] = []
    status: SourceUseAssessmentStatus
    blocking: tuple[SourceUseCase, ...] = ()
    unresolved: tuple[SourceUseCase, ...] = ()

    if normalized_assessed_at > review.valid_until:
        status = SourceUseAssessmentStatus.STALE_PERMISSION_REVIEW
        reason_codes.append("permission_review_expired")
    elif normalized_family not in review.supported_data_family_ids:
        status = SourceUseAssessmentStatus.UNSUPPORTED_DATA_FAMILY
        reason_codes.append("data_family_not_covered_by_source_review")
    else:
        by_use = {item.use_case: item for item in review.permissions}
        blocking = tuple(
            item
            for item in ordered_required
            if by_use[item].conclusion
            in {
                SourcePermissionConclusion.BLOCKED,
                SourcePermissionConclusion.NOT_APPLICABLE,
            }
        )
        unresolved = tuple(
            item
            for item in ordered_required
            if by_use[item].conclusion
            in {
                SourcePermissionConclusion.REQUIRES_SEPARATE_PERMISSION,
                SourcePermissionConclusion.UNRESOLVED,
            }
        )
        if blocking:
            status = SourceUseAssessmentStatus.BLOCKED_BY_PERMISSION
            reason_codes.append("required_source_use_blocked")
        elif unresolved:
            status = SourceUseAssessmentStatus.UNRESOLVED_PERMISSION
            reason_codes.append("required_source_use_unresolved")
        else:
            status = SourceUseAssessmentStatus.ELIGIBLE_FOR_REQUIRED_USES

    return SourceUseAssessmentV1(
        source_id=review.source_id,
        data_family_id=normalized_family,
        assessed_at=normalized_assessed_at,
        permission_review_valid_until=review.valid_until,
        required_use_cases=ordered_required,
        status=status,
        blocking_use_cases=blocking,
        unresolved_use_cases=unresolved,
        reason_codes=tuple(reason_codes),
        permission_review_fingerprint=source_permission_review_fingerprint(review),
    )


def _canonical_strings(value: Any, *, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str) or value is None:
        raise ValueError(f"{field_name} must be a sequence")
    normalized = tuple(
        normalize_required_string(item, field_name=field_name) for item in value
    )
    canonical = tuple(sorted(set(normalized)))
    if normalized != canonical:
        raise ValueError(f"{field_name} must be sorted and unique")
    return canonical
