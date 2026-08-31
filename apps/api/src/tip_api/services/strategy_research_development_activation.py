"""Review-only boundary before any real strategy-development activation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any, Literal

from tip_api.contracts.analytics.v1 import (
    RESEARCH_EXECUTION_CONTRACT_VERSION,
    RESEARCH_STATISTICS_CONTRACT_VERSION,
    CandidateStrategyResearchExperimentV1,
    StrategyResearchStage,
)
from tip_api.services.candidate_strategy_holdout_custody import (
    CONTRACT_VERSION as HOLDOUT_CUSTODY_CONTRACT_VERSION,
)
from tip_api.services.strategy_research_readiness import (
    StrategyResearchReadinessAssessment,
    StrategyResearchReadinessStatus,
    validate_strategy_research_readiness_assessment,
)


CONTRACT_VERSION = "strategy-research-development-activation-review/1.0"
INFERENCE_ORACLE_VERSION = "independent-mt19937-block-inference-oracle/1.0"


class StrategyResearchDevelopmentActivationError(RuntimeError):
    """Raised when activation review evidence is incomplete or inconsistent."""


class DevelopmentActivationReviewStatus(StrEnum):
    BLOCKED = "blocked"
    READY_FOR_EXACT_USER_AUTHORIZATION = "ready_for_exact_user_authorization"


class DevelopmentActivationNextAction(StrEnum):
    COMPLETE_RESEARCH_READINESS = "complete_research_readiness"
    REQUEST_EXACT_USER_AUTHORIZATION = "request_exact_user_authorization"


@dataclass(frozen=True, slots=True)
class ResearchDevelopmentControlEvidenceV1:
    implementation_revision: str
    experiment_fingerprint: str
    readiness_assessment_fingerprint: str
    execution_contract_version: str
    statistics_contract_version: str
    inference_oracle_version: str
    inference_oracle_audit_fingerprint: str
    holdout_custody_contract_version: str
    holdout_custody_audit_fingerprint: str
    existing_real_result_count: int
    existing_development_activation_count: int
    existing_holdout_consumption_count: int
    evidence_fingerprint: str


@dataclass(frozen=True, slots=True)
class StrategyResearchDevelopmentActivationReviewV1:
    contract_version: str
    reviewed_at: str
    experiment_id: str
    experiment_fingerprint: str
    readiness_assessment_fingerprint: str
    assessed_through_session: str | None
    historical_coverage_manifest_fingerprint: str | None
    implementation_revision: str
    control_evidence_fingerprint: str
    review_status: DevelopmentActivationReviewStatus
    next_action: DevelopmentActivationNextAction
    unresolved_gate_ids: tuple[str, ...]
    authorization_binding_fingerprint: str | None
    required_user_acknowledgement: str | None
    development_activation_authorized: Literal[False]
    real_evaluation_executed: Literal[False]
    parameter_selection_executed: Literal[False]
    holdout_accessed: Literal[False]
    performance_claims_authorized: Literal[False]
    external_request_count: Literal[0]
    production_write_count: Literal[0]
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def build_research_development_control_evidence(
    *,
    implementation_revision: str,
    experiment_fingerprint: str,
    readiness_assessment_fingerprint: str,
    inference_oracle_audit_fingerprint: str,
    holdout_custody_audit_fingerprint: str,
    existing_real_result_count: int = 0,
    existing_development_activation_count: int = 0,
    existing_holdout_consumption_count: int = 0,
) -> ResearchDevelopmentControlEvidenceV1:
    payload = {
        "implementation_revision": implementation_revision,
        "experiment_fingerprint": experiment_fingerprint,
        "readiness_assessment_fingerprint": readiness_assessment_fingerprint,
        "execution_contract_version": RESEARCH_EXECUTION_CONTRACT_VERSION,
        "statistics_contract_version": RESEARCH_STATISTICS_CONTRACT_VERSION,
        "inference_oracle_version": INFERENCE_ORACLE_VERSION,
        "inference_oracle_audit_fingerprint": inference_oracle_audit_fingerprint,
        "holdout_custody_contract_version": HOLDOUT_CUSTODY_CONTRACT_VERSION,
        "holdout_custody_audit_fingerprint": holdout_custody_audit_fingerprint,
        "existing_real_result_count": existing_real_result_count,
        "existing_development_activation_count": existing_development_activation_count,
        "existing_holdout_consumption_count": existing_holdout_consumption_count,
    }
    evidence = ResearchDevelopmentControlEvidenceV1(
        **payload,
        evidence_fingerprint=_fingerprint(payload),
    )
    _validate_control_evidence(evidence)
    return evidence


def review_strategy_research_development_activation(
    *,
    experiment: CandidateStrategyResearchExperimentV1,
    readiness: StrategyResearchReadinessAssessment,
    controls: ResearchDevelopmentControlEvidenceV1,
    reviewed_at: datetime,
) -> StrategyResearchDevelopmentActivationReviewV1:
    checked = _aware_utc(reviewed_at)
    validate_strategy_research_readiness_assessment(readiness)
    _validate_control_evidence(controls)
    if experiment.stage is not StrategyResearchStage.PREREGISTERED_DATA_BLOCKED:
        raise StrategyResearchDevelopmentActivationError(
            "development review requires the frozen preregistered experiment"
        )
    if (
        controls.experiment_fingerprint != experiment.logical_fingerprint
        or readiness.experiment_id != experiment.experiment_id
        or readiness.experiment_fingerprint != experiment.logical_fingerprint
        or readiness.evaluation_policy_fingerprint
        != experiment.evaluation_policy_fingerprint
    ):
        raise StrategyResearchDevelopmentActivationError(
            "development review experiment binding differs"
        )
    if (
        controls.readiness_assessment_fingerprint
        != readiness.logical_content_fingerprint
    ):
        raise StrategyResearchDevelopmentActivationError(
            "development review readiness binding differs"
        )
    unresolved = []
    if readiness.status is not StrategyResearchReadinessStatus.READY_FOR_DEVELOPMENT_REVIEW:
        unresolved.append("formal_research_readiness")
    if controls.existing_real_result_count != 0:
        unresolved.append("no_existing_real_result")
    if controls.existing_development_activation_count != 0:
        unresolved.append("no_existing_development_activation")
    if controls.existing_holdout_consumption_count != 0:
        unresolved.append("sealed_holdout_unconsumed")
    unresolved_gate_ids = tuple(unresolved)
    ready = not unresolved_gate_ids
    status = (
        DevelopmentActivationReviewStatus.READY_FOR_EXACT_USER_AUTHORIZATION
        if ready
        else DevelopmentActivationReviewStatus.BLOCKED
    )
    next_action = (
        DevelopmentActivationNextAction.REQUEST_EXACT_USER_AUTHORIZATION
        if ready
        else DevelopmentActivationNextAction.COMPLETE_RESEARCH_READINESS
    )
    binding_payload = {
        "contract_version": CONTRACT_VERSION,
        "experiment_id": experiment.experiment_id,
        "experiment_fingerprint": experiment.logical_fingerprint,
        "readiness_assessment_fingerprint": readiness.logical_content_fingerprint,
        "assessed_through_session": readiness.assessed_through_session,
        "historical_coverage_manifest_fingerprint": (
            readiness.historical_coverage_manifest_fingerprint
        ),
        "implementation_revision": controls.implementation_revision,
        "control_evidence_fingerprint": controls.evidence_fingerprint,
        "unresolved_gate_ids": unresolved_gate_ids,
    }
    authorization_binding = _fingerprint(binding_payload) if ready else None
    acknowledgement = (
        f"I_AUTHORIZE_STRATEGY_DEVELOPMENT_{authorization_binding}"
        if authorization_binding
        else None
    )
    payload = {
        **binding_payload,
        "reviewed_at": checked.isoformat(),
        "review_status": status.value,
        "next_action": next_action.value,
        "authorization_binding_fingerprint": authorization_binding,
        "required_user_acknowledgement": acknowledgement,
        "development_activation_authorized": False,
        "real_evaluation_executed": False,
        "parameter_selection_executed": False,
        "holdout_accessed": False,
        "performance_claims_authorized": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return StrategyResearchDevelopmentActivationReviewV1(
        contract_version=CONTRACT_VERSION,
        reviewed_at=checked.isoformat(),
        experiment_id=experiment.experiment_id,
        experiment_fingerprint=experiment.logical_fingerprint,
        readiness_assessment_fingerprint=readiness.logical_content_fingerprint,
        assessed_through_session=readiness.assessed_through_session,
        historical_coverage_manifest_fingerprint=(
            readiness.historical_coverage_manifest_fingerprint
        ),
        implementation_revision=controls.implementation_revision,
        control_evidence_fingerprint=controls.evidence_fingerprint,
        review_status=status,
        next_action=next_action,
        unresolved_gate_ids=unresolved_gate_ids,
        authorization_binding_fingerprint=authorization_binding,
        required_user_acknowledgement=acknowledgement,
        development_activation_authorized=False,
        real_evaluation_executed=False,
        parameter_selection_executed=False,
        holdout_accessed=False,
        performance_claims_authorized=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(payload),
    )


def _validate_control_evidence(
    evidence: ResearchDevelopmentControlEvidenceV1,
) -> None:
    payload = asdict(evidence)
    fingerprint = payload.pop("evidence_fingerprint")
    hashes = (
        evidence.experiment_fingerprint,
        evidence.readiness_assessment_fingerprint,
        evidence.inference_oracle_audit_fingerprint,
        evidence.holdout_custody_audit_fingerprint,
        fingerprint,
    )
    if (
        not re.fullmatch(r"[0-9a-f]{40}", evidence.implementation_revision)
        or any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in hashes)
        or evidence.execution_contract_version != RESEARCH_EXECUTION_CONTRACT_VERSION
        or evidence.statistics_contract_version != RESEARCH_STATISTICS_CONTRACT_VERSION
        or evidence.inference_oracle_version != INFERENCE_ORACLE_VERSION
        or evidence.holdout_custody_contract_version
        != HOLDOUT_CUSTODY_CONTRACT_VERSION
        or any(
            value < 0
            for value in (
                evidence.existing_real_result_count,
                evidence.existing_development_activation_count,
                evidence.existing_holdout_consumption_count,
            )
        )
        or fingerprint != _fingerprint(payload)
    ):
        raise StrategyResearchDevelopmentActivationError(
            "research development control evidence does not reconcile"
        )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise StrategyResearchDevelopmentActivationError(
            "development review time must be timezone-aware"
        )
    return value.astimezone(UTC)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            _jsonable(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
