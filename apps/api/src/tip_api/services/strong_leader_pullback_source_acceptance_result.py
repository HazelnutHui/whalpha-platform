"""Pure provider-neutral evaluation of a first-strategy source sample."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    ACTION_REQUIRED_FIELDS,
    LIFECYCLE_REQUIRED_FIELDS,
    ActionSourceAcceptanceCaseV1,
    LifecycleSourceAcceptanceCaseV1,
    StrongLeaderPullbackSourceAcceptanceSampleV1,
)


CONTRACT_VERSION = "strong-leader-pullback-source-acceptance-result/1.0"
ASSESSMENT_CONTRACT_VERSION = (
    "strong-leader-pullback-provider-sample-assessment/1.0"
)
EXPECTED_ASSESSED_FIELD_COUNT = 20 * len(ACTION_REQUIRED_FIELDS) + 64 * len(
    LIFECYCLE_REQUIRED_FIELDS
)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SAFE_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,127}$"

_ACTION_POSITIVE_REQUIRED_FIELDS = frozenset(
    {
        "action_status_and_type",
        "announcement_effective_ex_record_pay_dates_as_applicable",
        "exact_ratio_or_consideration",
        "provider_event_id_and_revision_chain",
        "source_availability_time",
        "stable_security_and_listing_identifiers",
    }
)
_LIFECYCLE_POSITIVE_REQUIRED_FIELDS = frozenset(
    {
        "first_and_last_tradable_dates",
        "source_availability_time_and_revision_history",
        "stable_security_and_listing_identifiers",
        "suspension_and_delisting_status_effective_dates",
        "termination_reason",
    }
)


class SourceResultState(StrEnum):
    MATCHED = "matched"
    ABSENT = "absent"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting"


class SourceFieldState(StrEnum):
    PROVIDED = "provided"
    EXPLICIT_NOT_APPLICABLE = "explicit_not_applicable"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting"


class StableIdentityState(StrEnum):
    VERIFIED = "verified"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"


class SourceQualification(StrEnum):
    SOLE_PRIMARY_CANDIDATE = "sole_primary_candidate"
    CORROBORATOR_ONLY = "corroborator_only"
    REJECTED = "rejected"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourcePermissionAssessmentV1(_FrozenModel):
    permission_review_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    production_representative_sample: bool
    private_research_permitted: bool
    local_evidence_retention_permitted: bool
    stable_identifier_use_permitted: bool
    public_derived_metric_display_permitted: bool
    termination_obligations_documented: bool
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def ordered_codes(cls, value: object) -> tuple[str, ...]:
        return _ordered_codes(value, "permission")


class SourceFieldAssessmentV1(_FrozenModel):
    field_name: str
    state: SourceFieldState
    evidence_fingerprint: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("field_name")
    @classmethod
    def field_name_is_clean(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("source field name is invalid")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def ordered_codes(cls, value: object) -> tuple[str, ...]:
        return _ordered_codes(value, "field")

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "SourceFieldAssessmentV1":
        evidence_states = {
            SourceFieldState.PROVIDED,
            SourceFieldState.EXPLICIT_NOT_APPLICABLE,
            SourceFieldState.CONFLICTING,
        }
        if (self.state in evidence_states) != (self.evidence_fingerprint is not None):
            raise ValueError("source field evidence fingerprint differs from state")
        return self


class ActionCaseAssessmentV1(_FrozenModel):
    source_action_id: str
    source_revision: int = Field(ge=1)
    candidate_instrument_id: UUID
    result_state: SourceResultState
    result_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    stable_identity_state: StableIdentityState
    field_assessments: tuple[SourceFieldAssessmentV1, ...]
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def ordered_codes(cls, value: object) -> tuple[str, ...]:
        return _ordered_codes(value, "action case")


class LifecycleCaseAssessmentV1(_FrozenModel):
    instrument_id: UUID
    result_state: SourceResultState
    result_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    stable_identity_state: StableIdentityState
    field_assessments: tuple[SourceFieldAssessmentV1, ...]
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def ordered_codes(cls, value: object) -> tuple[str, ...]:
        return _ordered_codes(value, "lifecycle case")


class ProviderSampleAssessmentV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-provider-sample-assessment/1.0"
    ] = ASSESSMENT_CONTRACT_VERSION
    provider_id: str = Field(pattern=_SAFE_ID_PATTERN)
    product_id: str = Field(pattern=_SAFE_ID_PATTERN)
    sample_id: str = Field(pattern=_SAFE_ID_PATTERN)
    assessed_at: datetime
    source_schema_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_sample_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    acceptance_sample_sha256: str = Field(pattern=_SHA256_PATTERN)
    acceptance_sample_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    permission: SourcePermissionAssessmentV1
    action_cases: tuple[ActionCaseAssessmentV1, ...]
    lifecycle_cases: tuple[LifecycleCaseAssessmentV1, ...]
    raw_provider_body_included: Literal[False] = False
    credential_material_included: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("assessed_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def fingerprint_reconciles(self) -> "ProviderSampleAssessmentV1":
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("provider sample assessment fingerprint differs")
        return self


class StrongLeaderPullbackSourceAcceptanceResultV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-source-acceptance-result/1.0"
    ] = CONTRACT_VERSION
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    provider_id: str
    product_id: str
    sample_id: str
    acceptance_sample_sha256: str = Field(pattern=_SHA256_PATTERN)
    acceptance_sample_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    provider_assessment_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    action_case_count: Literal[20] = 20
    lifecycle_case_count: Literal[64] = 64
    action_matched_count: int = Field(ge=0, le=20)
    lifecycle_matched_count: int = Field(ge=0, le=64)
    action_complete_count: int = Field(ge=0, le=20)
    lifecycle_complete_count: int = Field(ge=0, le=64)
    assessed_field_count: Literal[672] = EXPECTED_ASSESSED_FIELD_COUNT
    provided_field_count: int = Field(ge=0, le=EXPECTED_ASSESSED_FIELD_COUNT)
    stable_identity_verified_case_count: int = Field(ge=0, le=84)
    conflicting_case_count: int = Field(ge=0, le=84)
    permission_gate_passed: bool
    complete_semantic_gate_passed: bool
    qualification: SourceQualification
    blocker_codes: tuple[str, ...]
    sole_primary_source_selected: Literal[False] = False
    canonical_promotion_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    performance_admission_authorized: Literal[False] = False
    true_return_labels_authorized: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    evaluator_network_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("blocker_codes", mode="before")
    @classmethod
    def ordered_codes(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))) or any(not item for item in values):
            raise ValueError("result blockers are not ordered and unique")
        return values

    @model_validator(mode="after")
    def result_reconciles(self) -> "StrongLeaderPullbackSourceAcceptanceResultV1":
        if (
            self.action_complete_count > self.action_matched_count
            or self.lifecycle_complete_count > self.lifecycle_matched_count
        ):
            raise ValueError("complete source cases exceed matched cases")
        semantic_gate = (
            self.action_complete_count == self.action_case_count
            and self.lifecycle_complete_count == self.lifecycle_case_count
        )
        if self.complete_semantic_gate_passed != semantic_gate:
            raise ValueError("source semantic gate differs from case counts")
        permission_blockers = {
            "sample_not_production_representative",
            "private_research_permission_absent",
            "local_evidence_retention_permission_absent",
            "stable_identifier_permission_absent",
            "public_derived_metric_display_permission_absent",
            "termination_obligations_undocumented",
        }
        if self.permission_gate_passed != (
            not bool(permission_blockers & set(self.blocker_codes))
        ):
            raise ValueError("source permission gate differs from blockers")
        blocker_reconciliation = (
            (
                "action_cases_incomplete" in self.blocker_codes
            )
            == (self.action_complete_count != self.action_case_count),
            (
                "lifecycle_cases_incomplete" in self.blocker_codes
            )
            == (self.lifecycle_complete_count != self.lifecycle_case_count),
            (
                "stable_identity_cases_incomplete" in self.blocker_codes
            )
            == (
                self.stable_identity_verified_case_count
                != self.action_case_count + self.lifecycle_case_count
            ),
            ("source_conflicts_present" in self.blocker_codes)
            == bool(self.conflicting_case_count),
        )
        if not all(blocker_reconciliation):
            raise ValueError("source blockers differ from measured counts")
        sole = (
            self.permission_gate_passed
            and self.complete_semantic_gate_passed
            and self.action_complete_count == self.action_case_count
            and self.lifecycle_complete_count == self.lifecycle_case_count
            and self.stable_identity_verified_case_count
            == self.action_case_count + self.lifecycle_case_count
            and self.conflicting_case_count == 0
            and not self.blocker_codes
        )
        if (self.qualification is SourceQualification.SOLE_PRIMARY_CANDIDATE) != sole:
            raise ValueError("source qualification differs from measured gates")
        corroborator = (
            not sole
            and self.provided_field_count > 0
            and self.action_matched_count + self.lifecycle_matched_count > 0
        )
        if corroborator:
            disqualifying_permission_blockers = {
                "sample_not_production_representative",
                "private_research_permission_absent",
                "local_evidence_retention_permission_absent",
                "stable_identifier_permission_absent",
                "termination_obligations_undocumented",
            }
            corroborator = not bool(
                disqualifying_permission_blockers & set(self.blocker_codes)
            )
        if (
            self.qualification is SourceQualification.CORROBORATOR_ONLY
        ) != corroborator:
            raise ValueError("source corroborator qualification differs")
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("source acceptance result fingerprint differs")
        return self


def build_provider_sample_assessment(**values: object) -> ProviderSampleAssessmentV1:
    """Build one self-fingerprinted provider assessment from non-secret facts."""

    payload = to_jsonable_python(
        {
            "contract_version": ASSESSMENT_CONTRACT_VERSION,
            "raw_provider_body_included": False,
            "credential_material_included": False,
            **values,
        }
    )
    return ProviderSampleAssessmentV1.model_validate(
        {**payload, "logical_fingerprint": _fingerprint(payload)}
    )


def evaluate_strong_leader_pullback_source_sample(
    *,
    sample: StrongLeaderPullbackSourceAcceptanceSampleV1,
    sample_sha256: str,
    assessment: ProviderSampleAssessmentV1,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSourceAcceptanceResultV1:
    """Evaluate an exact sample without transport, canonical writes, or outcomes."""

    if re.fullmatch(_SHA256_PATTERN, sample_sha256) is None:
        raise ValueError("acceptance sample SHA-256 is invalid")
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise ValueError("implementation revision is invalid")
    verified_sample = StrongLeaderPullbackSourceAcceptanceSampleV1.model_validate(
        sample.model_dump(mode="python")
    )
    verified_assessment = ProviderSampleAssessmentV1.model_validate(
        assessment.model_dump(mode="python")
    )
    if (
        verified_assessment.acceptance_sample_sha256 != sample_sha256
        or verified_assessment.acceptance_sample_logical_fingerprint
        != verified_sample.logical_fingerprint
    ):
        raise ValueError("provider assessment does not bind the acceptance sample")

    action_pairs = _pair_action_cases(
        verified_sample.action_cases, verified_assessment.action_cases
    )
    lifecycle_pairs = _pair_lifecycle_cases(
        verified_sample.lifecycle_cases, verified_assessment.lifecycle_cases
    )
    action_complete = tuple(
        _case_is_complete(
            assessment_item,
            required_fields=ACTION_REQUIRED_FIELDS,
            positive_required_fields=_ACTION_POSITIVE_REQUIRED_FIELDS,
        )
        for _, assessment_item in action_pairs
    )
    lifecycle_complete = tuple(
        _case_is_complete(
            assessment_item,
            required_fields=LIFECYCLE_REQUIRED_FIELDS,
            positive_required_fields=_LIFECYCLE_POSITIVE_REQUIRED_FIELDS,
        )
        for _, assessment_item in lifecycle_pairs
    )
    all_cases = tuple(item for _, item in (*action_pairs, *lifecycle_pairs))
    permission_gate = _permission_gate(verified_assessment.permission)
    complete_semantic_gate = all(action_complete) and all(lifecycle_complete)
    conflict_count = sum(
        item.result_state is SourceResultState.CONFLICTING
        or item.stable_identity_state is StableIdentityState.CONFLICTING
        or any(
            field.state is SourceFieldState.CONFLICTING
            for field in item.field_assessments
        )
        for item in all_cases
    )
    identity_count = sum(
        item.stable_identity_state is StableIdentityState.VERIFIED
        for item in all_cases
    )
    assessed_field_count = sum(len(item.field_assessments) for item in all_cases)
    provided_field_count = sum(
        field.state is SourceFieldState.PROVIDED
        for item in all_cases
        for field in item.field_assessments
    )
    blocker_codes = _blocker_codes(
        permission=verified_assessment.permission,
        action_complete_count=sum(action_complete),
        lifecycle_complete_count=sum(lifecycle_complete),
        stable_identity_verified_case_count=identity_count,
        conflicting_case_count=conflict_count,
    )
    matched_case_count = sum(
        item.result_state is SourceResultState.MATCHED for item in all_cases
    )
    if not blocker_codes:
        qualification = SourceQualification.SOLE_PRIMARY_CANDIDATE
    elif (
        matched_case_count
        and provided_field_count
        and _corroborator_permission_gate(verified_assessment.permission)
    ):
        qualification = SourceQualification.CORROBORATOR_ONLY
    else:
        qualification = SourceQualification.REJECTED
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "provider_id": verified_assessment.provider_id,
        "product_id": verified_assessment.product_id,
        "sample_id": verified_assessment.sample_id,
        "acceptance_sample_sha256": sample_sha256,
        "acceptance_sample_logical_fingerprint": verified_sample.logical_fingerprint,
        "provider_assessment_fingerprint": verified_assessment.logical_fingerprint,
        "action_matched_count": sum(
            item.result_state is SourceResultState.MATCHED
            for item in verified_assessment.action_cases
        ),
        "lifecycle_matched_count": sum(
            item.result_state is SourceResultState.MATCHED
            for item in verified_assessment.lifecycle_cases
        ),
        "action_complete_count": sum(action_complete),
        "lifecycle_complete_count": sum(lifecycle_complete),
        "assessed_field_count": assessed_field_count,
        "provided_field_count": provided_field_count,
        "stable_identity_verified_case_count": identity_count,
        "conflicting_case_count": conflict_count,
        "permission_gate_passed": permission_gate,
        "complete_semantic_gate_passed": complete_semantic_gate,
        "qualification": qualification,
        "blocker_codes": blocker_codes,
    }
    provisional = StrongLeaderPullbackSourceAcceptanceResultV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    payload = provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
    return StrongLeaderPullbackSourceAcceptanceResultV1.model_validate(
        {**payload, "logical_fingerprint": _fingerprint(payload)}
    )


def _pair_action_cases(
    sample_cases: tuple[ActionSourceAcceptanceCaseV1, ...],
    assessment_cases: tuple[ActionCaseAssessmentV1, ...],
) -> tuple[tuple[ActionSourceAcceptanceCaseV1, ActionCaseAssessmentV1], ...]:
    sample_keys = tuple(_action_key(item) for item in sample_cases)
    assessment_keys = tuple(_action_key(item) for item in assessment_cases)
    if assessment_keys != sample_keys:
        raise ValueError("provider action assessment population differs")
    return tuple(zip(sample_cases, assessment_cases, strict=True))


def _pair_lifecycle_cases(
    sample_cases: tuple[LifecycleSourceAcceptanceCaseV1, ...],
    assessment_cases: tuple[LifecycleCaseAssessmentV1, ...],
) -> tuple[tuple[LifecycleSourceAcceptanceCaseV1, LifecycleCaseAssessmentV1], ...]:
    sample_keys = tuple(item.instrument_id for item in sample_cases)
    assessment_keys = tuple(item.instrument_id for item in assessment_cases)
    if assessment_keys != sample_keys:
        raise ValueError("provider lifecycle assessment population differs")
    return tuple(zip(sample_cases, assessment_cases, strict=True))


def _action_key(item: object) -> tuple[str, int, UUID]:
    return (
        getattr(item, "source_action_id"),
        getattr(item, "source_revision"),
        getattr(item, "candidate_instrument_id"),
    )


def _case_is_complete(
    assessment: ActionCaseAssessmentV1 | LifecycleCaseAssessmentV1,
    *,
    required_fields: tuple[str, ...],
    positive_required_fields: frozenset[str],
) -> bool:
    fields = tuple(item.field_name for item in assessment.field_assessments)
    if fields != required_fields:
        raise ValueError("provider case field population differs")
    if (
        assessment.result_state is not SourceResultState.MATCHED
        or assessment.stable_identity_state is not StableIdentityState.VERIFIED
    ):
        return False
    for field in assessment.field_assessments:
        if field.state is SourceFieldState.PROVIDED:
            continue
        if (
            field.state is SourceFieldState.EXPLICIT_NOT_APPLICABLE
            and field.field_name not in positive_required_fields
        ):
            continue
        return False
    return True


def _permission_gate(permission: SourcePermissionAssessmentV1) -> bool:
    return all(
        (
            permission.production_representative_sample,
            permission.private_research_permitted,
            permission.local_evidence_retention_permitted,
            permission.stable_identifier_use_permitted,
            permission.public_derived_metric_display_permitted,
            permission.termination_obligations_documented,
        )
    )


def _corroborator_permission_gate(permission: SourcePermissionAssessmentV1) -> bool:
    return all(
        (
            permission.production_representative_sample,
            permission.private_research_permitted,
            permission.local_evidence_retention_permitted,
            permission.stable_identifier_use_permitted,
            permission.termination_obligations_documented,
        )
    )


def _blocker_codes(
    *,
    permission: SourcePermissionAssessmentV1,
    action_complete_count: int,
    lifecycle_complete_count: int,
    stable_identity_verified_case_count: int,
    conflicting_case_count: int,
) -> tuple[str, ...]:
    blockers = set()
    if not permission.production_representative_sample:
        blockers.add("sample_not_production_representative")
    if not permission.private_research_permitted:
        blockers.add("private_research_permission_absent")
    if not permission.local_evidence_retention_permitted:
        blockers.add("local_evidence_retention_permission_absent")
    if not permission.stable_identifier_use_permitted:
        blockers.add("stable_identifier_permission_absent")
    if not permission.public_derived_metric_display_permitted:
        blockers.add("public_derived_metric_display_permission_absent")
    if not permission.termination_obligations_documented:
        blockers.add("termination_obligations_undocumented")
    if action_complete_count != 20:
        blockers.add("action_cases_incomplete")
    if lifecycle_complete_count != 64:
        blockers.add("lifecycle_cases_incomplete")
    if stable_identity_verified_case_count != 84:
        blockers.add("stable_identity_cases_incomplete")
    if conflicting_case_count:
        blockers.add("source_conflicts_present")
    return tuple(sorted(blockers))


def _ordered_codes(value: object, label: str) -> tuple[str, ...]:
    values = tuple(value)  # type: ignore[arg-type]
    if values != tuple(sorted(set(values))) or any(
        not item or item != item.strip() for item in values
    ):
        raise ValueError(f"{label} codes are not ordered and unique")
    return values


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
