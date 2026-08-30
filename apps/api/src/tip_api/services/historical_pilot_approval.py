"""Default-deny review package for one exact historical research pilot."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from tip_api.contracts.data_governance.v1 import (
    EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
    SHARED_CONTENT_ACCESS_POLICY_FINGERPRINT_V1,
    SOURCE_PERMISSION_POLICY_FINGERPRINT_V1,
    STANDARD_DATA_FAMILY_REGISTRY_FINGERPRINT_V1,
    SourcePermissionReviewV1,
    SourceUseAssessmentStatus,
    SourceUseAssessmentV1,
    assess_source_uses,
    source_permission_review_fingerprint,
)
from tip_api.services.historical_pilot_planner import (
    DEFAULT_SERIAL_PACE_SECONDS,
    GLOBAL_REQUEST_CEILING,
    HistoricalPilotPlanV1,
    PilotAuthorizationStatus,
    PilotMechanicsStatus,
    PilotRequestKind,
)


CONTRACT_VERSION = "historical-research-pilot-approval-review/1.1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{7,64}")
_SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{1,95}")


class HistoricalPilotApprovalError(ValueError):
    """Raised when an exact default-deny approval review is malformed."""


class PilotApprovalGateId(StrEnum):
    ACCOUNT_ENDPOINT_ENTITLEMENT = "account_endpoint_entitlement"
    ADJUSTMENT_INVARIANTS = "adjustment_invariants"
    DATA_GOVERNANCE_REGISTRY = "data_governance_registry"
    EQUAL_CAPABILITY_SOURCE_PERMISSION = "equal_capability_source_permission"
    EXACT_CURRENT_INVENTORY = "exact_current_inventory"
    LIFECYCLE_SOURCE_COVERAGE = "lifecycle_source_coverage"
    REQUEST_SCOPE = "request_scope"
    SYNTHETIC_ACTION_MAPPING = "synthetic_action_mapping"
    TMP_PACKAGE_APPLY_SEPARATION = "tmp_package_apply_separation"


EXTERNAL_GATE_ORDER = (
    PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT,
    PilotApprovalGateId.EXACT_CURRENT_INVENTORY,
    PilotApprovalGateId.LIFECYCLE_SOURCE_COVERAGE,
)
REQUIRED_PILOT_SOURCE_FAMILY_IDS = (
    "corporate_action_source_observation",
    "eod_price_bar",
    "point_in_time_identity",
)
ALL_GATE_ORDER = tuple(PilotApprovalGateId)
EXTERNAL_GATE_MAXIMUM_VALIDITY = {
    PilotApprovalGateId.ACCOUNT_ENDPOINT_ENTITLEMENT: timedelta(hours=24),
    PilotApprovalGateId.EXACT_CURRENT_INVENTORY: timedelta(hours=24),
    PilotApprovalGateId.LIFECYCLE_SOURCE_COVERAGE: timedelta(days=30),
}


class PilotApprovalGateState(StrEnum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNVERIFIED = "unverified"


class PilotApprovalReviewStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_EXACT_USER_AUTHORIZATION_REVIEW = (
        "ready_for_exact_user_authorization_review"
    )


class PilotApprovalNextAction(StrEnum):
    RESOLVE_REVIEW_GATES = "resolve_review_gates"
    REQUEST_EXACT_USER_AUTHORIZATION = "request_exact_user_authorization"


@dataclass(frozen=True, slots=True)
class PilotApprovalGateEvidenceV1:
    gate_id: PilotApprovalGateId
    state: PilotApprovalGateState
    evidence_fingerprint: str | None
    reason_codes: tuple[str, ...]
    observed_at: datetime | None = None
    valid_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class HistoricalPilotRepositoryEvidenceV1:
    implementation_revision: str
    synthetic_action_mapping_fingerprint: str
    adjustment_invariants_fingerprint: str


@dataclass(frozen=True, slots=True)
class HistoricalPilotRequestApprovalSummaryV1:
    kind: str
    logical_endpoint: str
    scopes: tuple[str, ...]
    request_ceiling: int
    result_limit_per_page: int | None
    required_parameters: tuple[str, ...]
    retry_count: int
    serial_only: bool


@dataclass(frozen=True, slots=True)
class HistoricalPilotApprovalReviewV1:
    contract_version: str
    reviewed_at: str
    implementation_revision: str
    plan_fingerprint: str
    inventory_fingerprint: str
    standard_data_family_registry_fingerprint: str
    shared_content_access_policy_fingerprint: str
    source_permission_policy_fingerprint: str
    source_permission_review_fingerprint: str
    source_permission_source_id: str
    source_permission_family_ids: tuple[str, ...]
    source_permission_assessment_statuses: tuple[str, ...]
    target_sessions: tuple[str, ...]
    request_summary: tuple[HistoricalPilotRequestApprovalSummaryV1, ...]
    planned_request_ceiling: int
    estimated_transport_seconds_at_ceiling: int
    temporary_package_root_requirement: str
    gate_results: tuple[PilotApprovalGateEvidenceV1, ...]
    unresolved_gate_ids: tuple[str, ...]
    review_status: PilotApprovalReviewStatus
    next_action: PilotApprovalNextAction
    authorization_binding_fingerprint: str
    required_user_acknowledgement: str | None
    acquisition_authorized: bool
    apply_authorized: bool
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_authorized: bool
    external_request_count: int
    data_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def build_historical_pilot_approval_review(
    *,
    plan: HistoricalPilotPlanV1,
    repository_evidence: HistoricalPilotRepositoryEvidenceV1,
    external_gate_evidence: tuple[PilotApprovalGateEvidenceV1, ...],
    source_permission_review: SourcePermissionReviewV1,
    source_permission_assessments: tuple[SourceUseAssessmentV1, ...],
    reviewed_at: datetime,
) -> HistoricalPilotApprovalReviewV1:
    """Build an in-memory review package; never grant or execute authority."""

    checked = _aware_utc(reviewed_at)
    _validate_plan(plan)
    _validate_repository_evidence(repository_evidence)
    external = _validate_external_gates(
        external_gate_evidence,
        inventory_fingerprint=plan.inventory.inventory_fingerprint,
        reviewed_at=checked,
    )
    by_gate = {item.gate_id: item for item in external}
    if source_permission_review.source_id != plan.provider_id:
        raise HistoricalPilotApprovalError(
            "source permission review must match the pilot provider"
        )
    permission_gate = _validate_gate(
        _source_permission_gate(
            source_permission_review,
            source_permission_assessments,
            reviewed_at=checked,
        ),
        reviewed_at=checked,
        maximum_validity=timedelta(days=90),
    )
    by_gate[permission_gate.gate_id] = permission_gate
    by_gate.update(
        _internal_gate_results(
            plan=plan,
            repository_evidence=repository_evidence,
            reviewed_at=checked,
        )
    )
    gate_results = tuple(by_gate[item] for item in ALL_GATE_ORDER)
    unresolved = tuple(
        item.gate_id.value
        for item in gate_results
        if item.state is not PilotApprovalGateState.SATISFIED
    )
    ready = not unresolved
    review_status = (
        PilotApprovalReviewStatus.READY_FOR_EXACT_USER_AUTHORIZATION_REVIEW
        if ready
        else PilotApprovalReviewStatus.BLOCKED
    )
    next_action = (
        PilotApprovalNextAction.REQUEST_EXACT_USER_AUTHORIZATION
        if ready
        else PilotApprovalNextAction.RESOLVE_REVIEW_GATES
    )
    request_summary = tuple(
        HistoricalPilotRequestApprovalSummaryV1(
            kind=item.kind.value,
            logical_endpoint=item.logical_endpoint,
            scopes=item.scopes,
            request_ceiling=item.request_ceiling,
            result_limit_per_page=item.result_limit_per_page,
            required_parameters=item.required_parameters,
            retry_count=item.retry_count,
            serial_only=item.serial_only,
        )
        for item in plan.request_lines
    )
    authorization_payload = {
        "contract_version": CONTRACT_VERSION,
        "implementation_revision": repository_evidence.implementation_revision,
        "plan_fingerprint": plan.logical_content_fingerprint,
        "inventory_fingerprint": plan.inventory.inventory_fingerprint,
        "standard_data_family_registry_fingerprint": (
            STANDARD_DATA_FAMILY_REGISTRY_FINGERPRINT_V1
        ),
        "shared_content_access_policy_fingerprint": (
            SHARED_CONTENT_ACCESS_POLICY_FINGERPRINT_V1
        ),
        "source_permission_policy_fingerprint": (
            SOURCE_PERMISSION_POLICY_FINGERPRINT_V1
        ),
        "source_permission_review_fingerprint": (
            source_permission_review_fingerprint(source_permission_review)
        ),
        "source_permission_source_id": source_permission_review.source_id,
        "source_permission_family_ids": [
            item.data_family_id for item in source_permission_assessments
        ],
        "source_permission_assessment_statuses": [
            item.status.value for item in source_permission_assessments
        ],
        "target_sessions": list(plan.target_sessions),
        "request_summary": [_jsonable(asdict(item)) for item in request_summary],
        "planned_request_ceiling": plan.planned_request_ceiling,
        "temporary_package_root_requirement": plan.temporary_package_root_requirement,
        "gate_results": [_jsonable(asdict(item)) for item in gate_results],
    }
    authorization_binding = _fingerprint(authorization_payload)
    acknowledgement = (
        f"I_AUTHORIZE_HISTORICAL_PILOT_{authorization_binding}"
        if ready
        else None
    )
    payload = {
        **authorization_payload,
        "reviewed_at": checked.isoformat(),
        "estimated_transport_seconds_at_ceiling": (
            plan.estimated_transport_seconds_at_ceiling
        ),
        "unresolved_gate_ids": list(unresolved),
        "review_status": review_status.value,
        "next_action": next_action.value,
        "authorization_binding_fingerprint": authorization_binding,
        "required_user_acknowledgement": acknowledgement,
        "acquisition_authorized": False,
        "apply_authorized": False,
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_authorized": False,
        "external_request_count": 0,
        "data_write_count": 0,
    }
    return HistoricalPilotApprovalReviewV1(
        contract_version=CONTRACT_VERSION,
        reviewed_at=checked.isoformat(),
        implementation_revision=repository_evidence.implementation_revision,
        plan_fingerprint=plan.logical_content_fingerprint,
        inventory_fingerprint=plan.inventory.inventory_fingerprint,
        standard_data_family_registry_fingerprint=(
            STANDARD_DATA_FAMILY_REGISTRY_FINGERPRINT_V1
        ),
        shared_content_access_policy_fingerprint=(
            SHARED_CONTENT_ACCESS_POLICY_FINGERPRINT_V1
        ),
        source_permission_policy_fingerprint=(
            SOURCE_PERMISSION_POLICY_FINGERPRINT_V1
        ),
        source_permission_review_fingerprint=(
            source_permission_review_fingerprint(source_permission_review)
        ),
        source_permission_source_id=source_permission_review.source_id,
        source_permission_family_ids=tuple(
            item.data_family_id for item in source_permission_assessments
        ),
        source_permission_assessment_statuses=tuple(
            item.status.value for item in source_permission_assessments
        ),
        target_sessions=plan.target_sessions,
        request_summary=request_summary,
        planned_request_ceiling=plan.planned_request_ceiling,
        estimated_transport_seconds_at_ceiling=(
            plan.estimated_transport_seconds_at_ceiling
        ),
        temporary_package_root_requirement=plan.temporary_package_root_requirement,
        gate_results=gate_results,
        unresolved_gate_ids=unresolved,
        review_status=review_status,
        next_action=next_action,
        authorization_binding_fingerprint=authorization_binding,
        required_user_acknowledgement=acknowledgement,
        acquisition_authorized=False,
        apply_authorized=False,
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_authorized=False,
        external_request_count=0,
        data_write_count=0,
        logical_content_fingerprint=_fingerprint(payload),
    )


def _validate_plan(plan: HistoricalPilotPlanV1) -> None:
    request_ceiling = sum(item.request_ceiling for item in plan.request_lines)
    if (
        plan.mechanics_status is not PilotMechanicsStatus.WITHIN_CEILING
        or plan.authorization_status is not PilotAuthorizationStatus.NOT_AUTHORIZED
        or tuple(item.kind for item in plan.request_lines) != tuple(PilotRequestKind)
        or request_ceiling != plan.planned_request_ceiling
        or plan.global_request_ceiling != GLOBAL_REQUEST_CEILING
        or plan.planned_request_ceiling > plan.global_request_ceiling
        or not plan.zero_automatic_retry
        or plan.serial_pace_seconds < DEFAULT_SERIAL_PACE_SECONDS
        or plan.estimated_transport_seconds_at_ceiling
        != plan.planned_request_ceiling * plan.serial_pace_seconds
        or plan.temporary_package_root_requirement != "/tmp"
        or any(not item.serial_only or item.retry_count != 0 for item in plan.request_lines)
        or any(
            (
                plan.acquisition_authorized,
                plan.apply_authorized,
                plan.publication_authorized,
                plan.deployment_authorized,
                plan.scheduler_enabled,
            )
        )
        or plan.external_request_count != 0
        or plan.data_write_count != 0
    ):
        raise HistoricalPilotApprovalError("pilot plan is not default-deny and bounded")
    prefix = f"historical-research-pilot/plan={plan.logical_content_fingerprint}/"
    if any(
        path.startswith("/") or not path.startswith(prefix)
        for path in plan.temporary_package_relative_paths
    ) or len(plan.temporary_package_relative_paths) != plan.planned_request_ceiling + 3:
        raise HistoricalPilotApprovalError("pilot temporary package paths are unsafe")


def _validate_repository_evidence(
    evidence: HistoricalPilotRepositoryEvidenceV1,
) -> None:
    if not _REVISION.fullmatch(evidence.implementation_revision):
        raise HistoricalPilotApprovalError("implementation revision is malformed")
    if not all(
        _SHA256.fullmatch(value)
        for value in (
            evidence.synthetic_action_mapping_fingerprint,
            evidence.adjustment_invariants_fingerprint,
        )
    ):
        raise HistoricalPilotApprovalError("repository evidence fingerprint is malformed")


def _validate_external_gates(
    values: tuple[PilotApprovalGateEvidenceV1, ...],
    *,
    inventory_fingerprint: str,
    reviewed_at: datetime,
) -> tuple[PilotApprovalGateEvidenceV1, ...]:
    if tuple(item.gate_id for item in values) != EXTERNAL_GATE_ORDER:
        raise HistoricalPilotApprovalError("external approval gates must be exact and ordered")
    normalized = tuple(
        _validate_gate(
            item,
            reviewed_at=reviewed_at,
            maximum_validity=EXTERNAL_GATE_MAXIMUM_VALIDITY[item.gate_id],
        )
        for item in values
    )
    inventory = normalized[
        EXTERNAL_GATE_ORDER.index(PilotApprovalGateId.EXACT_CURRENT_INVENTORY)
    ]
    if (
        inventory.state is PilotApprovalGateState.SATISFIED
        and inventory.evidence_fingerprint != inventory_fingerprint
    ):
        raise HistoricalPilotApprovalError("inventory gate does not bind the pilot inventory")
    return normalized


def _source_permission_gate(
    review: SourcePermissionReviewV1,
    assessments: tuple[SourceUseAssessmentV1, ...],
    *,
    reviewed_at: datetime,
) -> PilotApprovalGateEvidenceV1:
    try:
        checked_review = SourcePermissionReviewV1.model_validate(
            review.model_dump(mode="json")
        )
        checked_assessments = tuple(
            SourceUseAssessmentV1.model_validate(item.model_dump(mode="json"))
            for item in assessments
        )
    except Exception as exc:
        raise HistoricalPilotApprovalError(
            "source permission review package is malformed"
        ) from exc
    assessments = checked_assessments
    family_ids = tuple(item.data_family_id for item in assessments)
    if family_ids != REQUIRED_PILOT_SOURCE_FAMILY_IDS:
        raise HistoricalPilotApprovalError(
            "source permission assessments must cover exact pilot families in order"
        )
    if len({item.source_id for item in assessments}) != 1:
        raise HistoricalPilotApprovalError("pilot source permission must bind one source")
    expected_review_fingerprint = source_permission_review_fingerprint(checked_review)
    if (
        any(item.source_id != checked_review.source_id for item in assessments)
        or any(
            item.permission_review_fingerprint != expected_review_fingerprint
            for item in assessments
        )
    ):
        raise HistoricalPilotApprovalError(
            "pilot source permission assessments must bind one review"
        )
    if any(item.assessed_at != reviewed_at for item in assessments):
        raise HistoricalPilotApprovalError(
            "source permission assessments must be fresh at review time"
        )
    if any(
        item.required_use_cases != EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1
        for item in assessments
    ):
        raise HistoricalPilotApprovalError(
            "pilot source permission must assess every equal-capability use"
        )
    expected_assessments = tuple(
        assess_source_uses(
            checked_review,
            data_family_id=family_id,
            required_use_cases=EQUAL_CAPABILITY_MARKET_SOURCE_USES_V1,
            assessed_at=reviewed_at,
        )
        for family_id in REQUIRED_PILOT_SOURCE_FAMILY_IDS
    )
    if assessments != expected_assessments:
        raise HistoricalPilotApprovalError(
            "source permission assessments were not derived from the bound review"
        )

    evidence_fingerprint = _fingerprint(
        {
            "source_permission_policy_fingerprint": (
                SOURCE_PERMISSION_POLICY_FINGERPRINT_V1
            ),
            "assessments": [item.model_dump(mode="json") for item in assessments],
        }
    )
    statuses = tuple(item.status for item in assessments)
    if all(
        item is SourceUseAssessmentStatus.ELIGIBLE_FOR_REQUIRED_USES
        for item in statuses
    ):
        valid_until = min(item.permission_review_valid_until for item in assessments)
        valid_until = min(valid_until, reviewed_at + timedelta(days=90))
        if valid_until <= reviewed_at:
            raise HistoricalPilotApprovalError(
                "eligible source permission has no remaining validity"
            )
        return PilotApprovalGateEvidenceV1(
            gate_id=PilotApprovalGateId.EQUAL_CAPABILITY_SOURCE_PERMISSION,
            state=PilotApprovalGateState.SATISFIED,
            evidence_fingerprint=evidence_fingerprint,
            reason_codes=(),
            observed_at=reviewed_at,
            valid_until=valid_until,
        )

    state = (
        PilotApprovalGateState.UNSATISFIED
        if any(
            item is SourceUseAssessmentStatus.BLOCKED_BY_PERMISSION
            for item in statuses
        )
        else PilotApprovalGateState.UNVERIFIED
    )
    reasons = tuple(
        sorted(
            {
                f"{assessment.data_family_id}_{assessment.status.value}"
                for assessment in assessments
                if assessment.status
                is not SourceUseAssessmentStatus.ELIGIBLE_FOR_REQUIRED_USES
            }
        )
    )
    return PilotApprovalGateEvidenceV1(
        gate_id=PilotApprovalGateId.EQUAL_CAPABILITY_SOURCE_PERMISSION,
        state=state,
        evidence_fingerprint=evidence_fingerprint,
        reason_codes=reasons,
    )


def _validate_gate(
    item: PilotApprovalGateEvidenceV1,
    *,
    reviewed_at: datetime,
    maximum_validity: timedelta,
) -> PilotApprovalGateEvidenceV1:
    if (
        len(set(item.reason_codes)) != len(item.reason_codes)
        or tuple(sorted(item.reason_codes)) != item.reason_codes
        or any(not _SAFE_CODE.fullmatch(value) for value in item.reason_codes)
    ):
        raise HistoricalPilotApprovalError("approval gate reason codes are malformed")
    if item.state is PilotApprovalGateState.SATISFIED:
        if item.evidence_fingerprint is None or not _SHA256.fullmatch(
            item.evidence_fingerprint
        ):
            raise HistoricalPilotApprovalError("satisfied gate requires evidence")
        if item.observed_at is None or item.valid_until is None:
            raise HistoricalPilotApprovalError(
                "satisfied external gate requires a bounded validity window"
            )
    elif not item.reason_codes:
        raise HistoricalPilotApprovalError("unresolved gate requires a reason")
    if item.evidence_fingerprint is not None and not _SHA256.fullmatch(
        item.evidence_fingerprint
    ):
        raise HistoricalPilotApprovalError("gate evidence fingerprint is malformed")
    observed = _optional_aware_utc(item.observed_at)
    valid_until = _optional_aware_utc(item.valid_until)
    if (observed is None) != (valid_until is None):
        raise HistoricalPilotApprovalError(
            "external gate observation and validity must be paired"
        )
    if observed is not None and valid_until is not None:
        if valid_until <= observed or valid_until - observed > maximum_validity:
            raise HistoricalPilotApprovalError("external gate validity is malformed")
        if item.state is PilotApprovalGateState.SATISFIED and not (
            observed <= reviewed_at <= valid_until
        ):
            raise HistoricalPilotApprovalError("satisfied external gate is stale")
    return PilotApprovalGateEvidenceV1(
        gate_id=item.gate_id,
        state=item.state,
        evidence_fingerprint=item.evidence_fingerprint,
        reason_codes=item.reason_codes,
        observed_at=observed,
        valid_until=valid_until,
    )


def _internal_gate_results(
    *,
    plan: HistoricalPilotPlanV1,
    repository_evidence: HistoricalPilotRepositoryEvidenceV1,
    reviewed_at: datetime,
) -> dict[PilotApprovalGateId, PilotApprovalGateEvidenceV1]:
    tmp_payload = {
        "root": plan.temporary_package_root_requirement,
        "relative_paths": list(plan.temporary_package_relative_paths),
        "apply_authorized": plan.apply_authorized,
        "data_write_count": plan.data_write_count,
    }
    return {
        PilotApprovalGateId.ADJUSTMENT_INVARIANTS: _satisfied(
            PilotApprovalGateId.ADJUSTMENT_INVARIANTS,
            repository_evidence.adjustment_invariants_fingerprint,
            observed_at=reviewed_at,
        ),
        PilotApprovalGateId.DATA_GOVERNANCE_REGISTRY: _satisfied(
            PilotApprovalGateId.DATA_GOVERNANCE_REGISTRY,
            STANDARD_DATA_FAMILY_REGISTRY_FINGERPRINT_V1,
            observed_at=reviewed_at,
        ),
        PilotApprovalGateId.REQUEST_SCOPE: _satisfied(
            PilotApprovalGateId.REQUEST_SCOPE,
            plan.logical_content_fingerprint,
            observed_at=reviewed_at,
        ),
        PilotApprovalGateId.SYNTHETIC_ACTION_MAPPING: _satisfied(
            PilotApprovalGateId.SYNTHETIC_ACTION_MAPPING,
            repository_evidence.synthetic_action_mapping_fingerprint,
            observed_at=reviewed_at,
        ),
        PilotApprovalGateId.TMP_PACKAGE_APPLY_SEPARATION: _satisfied(
            PilotApprovalGateId.TMP_PACKAGE_APPLY_SEPARATION,
            _fingerprint(tmp_payload),
            observed_at=reviewed_at,
        ),
    }


def _satisfied(
    gate_id: PilotApprovalGateId,
    fingerprint: str,
    *,
    observed_at: datetime,
) -> PilotApprovalGateEvidenceV1:
    return PilotApprovalGateEvidenceV1(
        gate_id=gate_id,
        state=PilotApprovalGateState.SATISFIED,
        evidence_fingerprint=fingerprint,
        reason_codes=(),
        observed_at=observed_at,
        valid_until=None,
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HistoricalPilotApprovalError("approval review time must be timezone-aware")
    return value.astimezone(UTC)


def _optional_aware_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _aware_utc(value)


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _aware_utc(value).isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
