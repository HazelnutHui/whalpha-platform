"""Family-specific canonical source resolution with fail-closed conflicts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import (
    QualityStatus,
    normalize_required_string,
    normalize_utc_datetime,
)
from tip_api.contracts.data_governance.v1.record_classification import (
    STANDARD_DATA_FAMILY_REGISTRY_V1,
)


_CANONICAL_ID = re.compile(r"[a-z][a-z0-9_]{1,63}")
_FAMILY_IDS = frozenset(
    item.data_family_id for item in STANDARD_DATA_FAMILY_REGISTRY_V1
)


class SourceResolutionMode(StrEnum):
    SINGLE_AUTHORITY = "single_authority"
    PRIMARY_WITH_CORROBORATION = "primary_with_corroboration"
    UNANIMOUS_EVIDENCE = "unanimous_evidence"


class SourceEvidenceRole(StrEnum):
    AUTHORITATIVE = "authoritative"
    PRIMARY = "primary"
    CORROBORATING = "corroborating"
    CROSSWALK_ONLY = "crosswalk_only"


class SourceResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    CORROBORATED = "corroborated"
    QUARANTINED_CONFLICT = "quarantined_conflict"
    UNAVAILABLE = "unavailable"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceResolutionBindingV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    source_id: str
    evidence_role: SourceEvidenceRole
    precedence_rank: int = Field(ge=1)
    permission_review_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("source_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        return _canonical_id(value, field_name="source_id")


class DataFamilySourceResolutionPolicyV1(FrozenContract):
    """One exact fact scope; this is policy only and grants no operation."""

    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal["data-family-source-resolution-v1"] = (
        "data-family-source-resolution-v1"
    )
    data_family_id: str
    fact_scope: str
    resolution_mode: SourceResolutionMode
    sources: tuple[SourceResolutionBindingV1, ...]
    required_matching_sources: int = Field(ge=1)
    first_non_null_allowed: Literal[False] = False
    ticker_join_allowed: Literal[False] = False
    unresolved_conflict_action: Literal["quarantine"] = "quarantine"
    missing_required_evidence_action: Literal["unavailable"] = "unavailable"
    operational_authority: Literal["none"] = "none"

    @field_validator("data_family_id", mode="before")
    @classmethod
    def family_is_known(cls, value: str) -> str:
        normalized = _canonical_id(value, field_name="data_family_id")
        if normalized not in _FAMILY_IDS:
            raise ValueError("source-resolution policy requires a standard data family")
        return normalized

    @field_validator("fact_scope", mode="before")
    @classmethod
    def scope_is_canonical(cls, value: str) -> str:
        return _canonical_id(value, field_name="fact_scope")

    @model_validator(mode="after")
    def composition_is_valid(self) -> "DataFamilySourceResolutionPolicyV1":
        if not self.sources:
            raise ValueError("source-resolution policy requires sources")
        ranks = tuple(item.precedence_rank for item in self.sources)
        source_ids = tuple(item.source_id for item in self.sources)
        if ranks != tuple(range(1, len(self.sources) + 1)):
            raise ValueError("sources must use unique contiguous precedence ranks")
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source-resolution policy sources must be unique")

        eligible = tuple(
            item
            for item in self.sources
            if item.evidence_role is not SourceEvidenceRole.CROSSWALK_ONLY
        )
        authorities = tuple(
            item for item in eligible if item.evidence_role is SourceEvidenceRole.AUTHORITATIVE
        )
        primaries = tuple(
            item for item in eligible if item.evidence_role is SourceEvidenceRole.PRIMARY
        )
        corroborators = tuple(
            item
            for item in eligible
            if item.evidence_role is SourceEvidenceRole.CORROBORATING
        )

        if self.resolution_mode is SourceResolutionMode.SINGLE_AUTHORITY:
            if len(authorities) != 1 or primaries:
                raise ValueError(
                    "single-authority mode requires exactly one authority and no primary"
                )
            if self.required_matching_sources != 1:
                raise ValueError("single-authority mode requires one matching source")
        elif self.resolution_mode is SourceResolutionMode.PRIMARY_WITH_CORROBORATION:
            if authorities or len(primaries) != 1 or not corroborators:
                raise ValueError(
                    "primary-with-corroboration requires one primary and at least one corroborator"
                )
            if not 2 <= self.required_matching_sources <= len(eligible):
                raise ValueError("corroboration threshold must include primary and corroborator")
        else:
            if authorities or primaries or len(corroborators) < 2:
                raise ValueError("unanimous mode requires at least two corroborating sources")
            if self.required_matching_sources != len(eligible):
                raise ValueError("unanimous mode requires every resolving source")
        return self


class SourceFactEvidenceV1(FrozenContract):
    """Normalized fact identity only; the fact body remains in its domain contract."""

    schema_version: Literal["1.0"] = "1.0"
    source_id: str
    data_family_id: str
    fact_scope: str
    stable_subject_id: str
    effective_at: datetime
    fact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    permission_review_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_status: QualityStatus

    @field_validator("source_id", "data_family_id", "fact_scope", mode="before")
    @classmethod
    def canonical_ids(cls, value: str, info: Any) -> str:
        return _canonical_id(value, field_name=info.field_name)

    @field_validator("stable_subject_id", mode="before")
    @classmethod
    def subject_is_required(cls, value: str) -> str:
        return normalize_required_string(value, field_name="stable_subject_id")

    @field_validator("effective_at")
    @classmethod
    def effective_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class SourceResolutionDecisionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    data_family_id: str
    fact_scope: str
    stable_subject_id: str
    effective_at: datetime
    status: SourceResolutionStatus
    selected_fact_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    supporting_source_ids: tuple[str, ...]
    conflicting_source_ids: tuple[str, ...]
    excluded_source_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    operational_authority: Literal["none"] = "none"

    @field_validator("effective_at")
    @classmethod
    def effective_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "supporting_source_ids",
        "conflicting_source_ids",
        "excluded_source_ids",
        "reason_codes",
        mode="before",
    )
    @classmethod
    def strings_are_canonical(cls, value: Any, info: Any) -> tuple[str, ...]:
        if isinstance(value, str) or value is None:
            raise ValueError(f"{info.field_name} must be a sequence")
        normalized = tuple(
            normalize_required_string(item, field_name=info.field_name)
            for item in value
        )
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError(f"{info.field_name} must be sorted and unique")
        return normalized

    @model_validator(mode="after")
    def decision_is_consistent(self) -> "SourceResolutionDecisionV1":
        source_sets = (
            set(self.supporting_source_ids),
            set(self.conflicting_source_ids),
            set(self.excluded_source_ids),
        )
        overlaps = any(
            source_sets[index] & source_sets[other]
            for index in range(3)
            for other in range(index + 1, 3)
        )
        if overlaps:
            raise ValueError("source decision sets must be disjoint")
        resolved = self.status in {
            SourceResolutionStatus.RESOLVED,
            SourceResolutionStatus.CORROBORATED,
        }
        if resolved:
            if self.selected_fact_fingerprint is None or not self.supporting_source_ids:
                raise ValueError("resolved decisions require a selected fact and support")
            if self.conflicting_source_ids or self.reason_codes:
                raise ValueError("resolved decisions cannot retain conflict or failure reasons")
            if (
                self.status is SourceResolutionStatus.RESOLVED
                and len(self.supporting_source_ids) != 1
            ):
                raise ValueError("resolved status represents exactly one supporting source")
            if (
                self.status is SourceResolutionStatus.CORROBORATED
                and len(self.supporting_source_ids) < 2
            ):
                raise ValueError("corroborated status requires multiple supporting sources")
        else:
            if self.selected_fact_fingerprint is not None or not self.reason_codes:
                raise ValueError("unresolved decisions require reasons and no selected fact")
            if (
                self.status is SourceResolutionStatus.QUARANTINED_CONFLICT
                and not self.conflicting_source_ids
            ):
                raise ValueError("conflict quarantine requires conflicting sources")
            if (
                self.status is SourceResolutionStatus.UNAVAILABLE
                and self.conflicting_source_ids
            ):
                raise ValueError("unavailable status cannot contain source conflicts")
        return self


def source_resolution_policy_fingerprint(
    policy: DataFamilySourceResolutionPolicyV1,
) -> str:
    return hashlib.sha256(
        json.dumps(
            policy.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def resolve_source_facts(
    policy: DataFamilySourceResolutionPolicyV1,
    evidence: tuple[SourceFactEvidenceV1, ...],
) -> SourceResolutionDecisionV1:
    """Resolve fingerprints mechanically; never fetch, persist, or publish data."""

    if not evidence:
        raise ValueError("source resolution requires at least one evidence record")
    first = evidence[0]
    expected_key = (
        policy.data_family_id,
        policy.fact_scope,
        first.stable_subject_id,
        first.effective_at,
    )
    by_source = {item.source_id: item for item in policy.sources}
    seen: set[str] = set()
    for item in evidence:
        key = (
            item.data_family_id,
            item.fact_scope,
            item.stable_subject_id,
            item.effective_at,
        )
        if key != expected_key:
            raise ValueError("all source evidence must describe one exact stable-ID fact")
        binding = by_source.get(item.source_id)
        if binding is None:
            raise ValueError("source evidence is not bound by the resolution policy")
        if item.source_id in seen:
            raise ValueError("one source may contribute only one fact revision per decision")
        seen.add(item.source_id)
        if item.permission_review_fingerprint != binding.permission_review_fingerprint:
            raise ValueError("source evidence permission review does not match policy")

    ordered = tuple(
        sorted(evidence, key=lambda item: by_source[item.source_id].precedence_rank)
    )
    usable: list[SourceFactEvidenceV1] = []
    excluded: list[str] = []
    for item in ordered:
        binding = by_source[item.source_id]
        if (
            binding.evidence_role is SourceEvidenceRole.CROSSWALK_ONLY
            or item.quality_status in {QualityStatus.REJECTED, QualityStatus.PENDING_REVIEW}
        ):
            excluded.append(item.source_id)
        else:
            usable.append(item)

    anchor: SourceFactEvidenceV1 | None = None
    if policy.resolution_mode is SourceResolutionMode.SINGLE_AUTHORITY:
        anchor = next(
            (
                item
                for item in usable
                if by_source[item.source_id].evidence_role
                is SourceEvidenceRole.AUTHORITATIVE
            ),
            None,
        )
    elif policy.resolution_mode is SourceResolutionMode.PRIMARY_WITH_CORROBORATION:
        anchor = next(
            (
                item
                for item in usable
                if by_source[item.source_id].evidence_role is SourceEvidenceRole.PRIMARY
            ),
            None,
        )
    elif usable:
        anchor = usable[0]

    base = {
        "policy_fingerprint": source_resolution_policy_fingerprint(policy),
        "data_family_id": policy.data_family_id,
        "fact_scope": policy.fact_scope,
        "stable_subject_id": first.stable_subject_id,
        "effective_at": first.effective_at,
        "excluded_source_ids": tuple(sorted(excluded)),
    }
    if anchor is None:
        return SourceResolutionDecisionV1(
            **base,
            status=SourceResolutionStatus.UNAVAILABLE,
            supporting_source_ids=(),
            conflicting_source_ids=(),
            reason_codes=("required_anchor_evidence_unavailable",),
        )

    supporting = tuple(
        sorted(
            item.source_id
            for item in usable
            if item.fact_fingerprint == anchor.fact_fingerprint
        )
    )
    conflicting = tuple(
        sorted(
            item.source_id
            for item in usable
            if item.fact_fingerprint != anchor.fact_fingerprint
        )
    )
    if conflicting:
        return SourceResolutionDecisionV1(
            **base,
            status=SourceResolutionStatus.QUARANTINED_CONFLICT,
            supporting_source_ids=supporting,
            conflicting_source_ids=conflicting,
            reason_codes=("resolving_sources_disagree",),
        )
    if len(supporting) < policy.required_matching_sources:
        return SourceResolutionDecisionV1(
            **base,
            status=SourceResolutionStatus.UNAVAILABLE,
            supporting_source_ids=supporting,
            conflicting_source_ids=(),
            reason_codes=("required_matching_evidence_unavailable",),
        )
    status = (
        SourceResolutionStatus.CORROBORATED
        if len(supporting) > 1
        else SourceResolutionStatus.RESOLVED
    )
    return SourceResolutionDecisionV1(
        **base,
        status=status,
        selected_fact_fingerprint=anchor.fact_fingerprint,
        supporting_source_ids=supporting,
        conflicting_source_ids=(),
        reason_codes=(),
    )


def _canonical_id(value: str, *, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name)
    if not _CANONICAL_ID.fullmatch(normalized):
        raise ValueError(f"{field_name} must be lower snake case")
    return normalized
