"""Read-only readiness assessment for one preregistered strategy experiment."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum, StrEnum
from typing import Any

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyResearchExperimentV1,
    StrategyResearchStage,
)
from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageManifestV1,
    HistoricalDatasetFamily,
    HistoricalReadinessStatus,
    RESEARCH_REQUIRED_DATASET_FAMILIES,
)
from tip_api.read_models.eod import EodSessionDescriptor


CONTRACT_VERSION = "strategy-research-readiness/1.0"


class StrategyResearchReadinessError(RuntimeError):
    """Raised when readiness evidence is malformed or internally inconsistent."""


class StrategyResearchReadinessStatus(StrEnum):
    DATA_BLOCKED = "data_blocked"
    READY_FOR_DEVELOPMENT_REVIEW = "ready_for_development_review"


class StrategyResearchReadinessNextAction(StrEnum):
    COMPLETE_HISTORICAL_FOUNDATION = "complete_historical_foundation"
    REVIEW_DEVELOPMENT_ACTIVATION = "review_development_activation"


class ResearchRequirementState(StrEnum):
    SATISFIED = "satisfied"
    MECHANICS_ONLY = "mechanics_only"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CanonicalEodIdentityEvidence:
    sessions: tuple[date, ...]
    identity_bound_session_count: int
    record_count: int
    logical_fingerprint: str


@dataclass(frozen=True, slots=True)
class StrategyResearchRequirementObservation:
    requirement_id: str
    state: ResearchRequirementState
    required_for_development: bool
    dataset_family: str | None
    expected_session_count: int | None
    observed_session_count: int | None
    source_fingerprint: str | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyResearchReadinessAssessment:
    contract_version: str
    experiment_id: str
    experiment_fingerprint: str
    evaluation_policy_fingerprint: str
    assessed_through_session: str | None
    canonical_eod_identity_fingerprint: str
    historical_coverage_manifest_fingerprint: str | None
    status: StrategyResearchReadinessStatus
    next_action: StrategyResearchReadinessNextAction
    reason_codes: tuple[str, ...]
    observations: tuple[StrategyResearchRequirementObservation, ...]
    development_authorized: bool
    performance_claims_authorized: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


def canonical_eod_identity_evidence(
    descriptors: tuple[EodSessionDescriptor, ...],
) -> CanonicalEodIdentityEvidence:
    sessions = tuple(item.session_date for item in descriptors)
    if sessions != tuple(sorted(set(sessions))):
        raise StrategyResearchReadinessError(
            "canonical EOD descriptors must be unique and ordered"
        )
    if any(item.identity_as_of_date > item.session_date for item in descriptors):
        raise StrategyResearchReadinessError(
            "canonical EOD descriptor references future Identity"
        )
    if any(item.completion_status != "completed" for item in descriptors):
        raise StrategyResearchReadinessError(
            "canonical EOD descriptor is not completed"
        )
    if any(item.record_count <= 0 for item in descriptors):
        raise StrategyResearchReadinessError(
            "canonical EOD descriptor has no records"
        )
    payload = {
        "sessions": [item.isoformat() for item in sessions],
        "schema_versions": [item.schema_version for item in descriptors],
        "identity_sessions": [
            item.identity_as_of_date.isoformat() for item in descriptors
        ],
        "record_counts": [item.record_count for item in descriptors],
        "completion_statuses": [item.completion_status for item in descriptors],
        "available_at": [item.available_at.isoformat() for item in descriptors],
        "quality_warning_counts": [
            item.quality_warning_count for item in descriptors
        ],
    }
    return CanonicalEodIdentityEvidence(
        sessions=sessions,
        identity_bound_session_count=len(descriptors),
        record_count=sum(item.record_count for item in descriptors),
        logical_fingerprint=_fingerprint(payload),
    )


def assess_strategy_research_readiness(
    *,
    experiment: CandidateStrategyResearchExperimentV1,
    canonical_evidence: CanonicalEodIdentityEvidence,
    coverage_manifest: HistoricalCoverageManifestV1 | None = None,
) -> StrategyResearchReadinessAssessment:
    if experiment.stage is not StrategyResearchStage.PREREGISTERED_DATA_BLOCKED:
        raise StrategyResearchReadinessError(
            "readiness assessment requires the frozen preregistered experiment"
        )
    _validate_hash(canonical_evidence.logical_fingerprint, "canonical evidence")
    if canonical_evidence.identity_bound_session_count != len(
        canonical_evidence.sessions
    ):
        raise StrategyResearchReadinessError(
            "every canonical EOD session must bind validated Identity"
        )
    if canonical_evidence.sessions != tuple(
        sorted(set(canonical_evidence.sessions))
    ):
        raise StrategyResearchReadinessError(
            "canonical evidence sessions must be unique and ordered"
        )

    observations = _observations(experiment, canonical_evidence, coverage_manifest)
    blockers = tuple(
        item.requirement_id
        for item in observations
        if item.required_for_development
        and item.state is not ResearchRequirementState.SATISFIED
    )
    ready = not blockers
    status = (
        StrategyResearchReadinessStatus.READY_FOR_DEVELOPMENT_REVIEW
        if ready
        else StrategyResearchReadinessStatus.DATA_BLOCKED
    )
    next_action = (
        StrategyResearchReadinessNextAction.REVIEW_DEVELOPMENT_ACTIVATION
        if ready
        else StrategyResearchReadinessNextAction.COMPLETE_HISTORICAL_FOUNDATION
    )
    reason_codes = (
        ("separate_development_activation_review_required",)
        if ready
        else tuple(f"requirement_not_satisfied:{item}" for item in blockers)
    )
    manifest_fingerprint = (
        None if coverage_manifest is None else coverage_manifest.logical_fingerprint
    )
    assessed_through_session = (
        canonical_evidence.sessions[-1].isoformat()
        if canonical_evidence.sessions
        else None
    )
    payload = {
        "contract_version": CONTRACT_VERSION,
        "experiment_id": experiment.experiment_id,
        "experiment_fingerprint": experiment.logical_fingerprint,
        "evaluation_policy_fingerprint": experiment.evaluation_policy_fingerprint,
        "assessed_through_session": assessed_through_session,
        "canonical_eod_identity_fingerprint": canonical_evidence.logical_fingerprint,
        "historical_coverage_manifest_fingerprint": manifest_fingerprint,
        "status": status.value,
        "next_action": next_action.value,
        "reason_codes": reason_codes,
        "observations": [_jsonable(asdict(item)) for item in observations],
        "development_authorized": False,
        "performance_claims_authorized": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return StrategyResearchReadinessAssessment(
        contract_version=CONTRACT_VERSION,
        experiment_id=experiment.experiment_id,
        experiment_fingerprint=experiment.logical_fingerprint,
        evaluation_policy_fingerprint=experiment.evaluation_policy_fingerprint,
        assessed_through_session=assessed_through_session,
        canonical_eod_identity_fingerprint=canonical_evidence.logical_fingerprint,
        historical_coverage_manifest_fingerprint=manifest_fingerprint,
        status=status,
        next_action=next_action,
        reason_codes=reason_codes,
        observations=observations,
        development_authorized=False,
        performance_claims_authorized=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(payload),
    )


def validate_strategy_research_readiness_assessment(
    assessment: StrategyResearchReadinessAssessment,
) -> None:
    """Formally recheck one in-memory readiness result before downstream review."""

    required = tuple(
        item for item in assessment.observations if item.required_for_development
    )
    ready = bool(required) and all(
        item.state is ResearchRequirementState.SATISFIED for item in required
    )
    expected_status = (
        StrategyResearchReadinessStatus.READY_FOR_DEVELOPMENT_REVIEW
        if ready
        else StrategyResearchReadinessStatus.DATA_BLOCKED
    )
    expected_next = (
        StrategyResearchReadinessNextAction.REVIEW_DEVELOPMENT_ACTIVATION
        if ready
        else StrategyResearchReadinessNextAction.COMPLETE_HISTORICAL_FOUNDATION
    )
    expected_reasons = (
        ("separate_development_activation_review_required",)
        if ready
        else tuple(
            f"requirement_not_satisfied:{item.requirement_id}"
            for item in assessment.observations
            if item.required_for_development
            and item.state is not ResearchRequirementState.SATISFIED
        )
    )
    payload = assessment.as_dict()
    actual_fingerprint = payload.pop("logical_content_fingerprint")
    if (
        assessment.contract_version != CONTRACT_VERSION
        or assessment.status is not expected_status
        or assessment.next_action is not expected_next
        or assessment.reason_codes != expected_reasons
        or assessment.development_authorized
        or assessment.performance_claims_authorized
        or assessment.external_request_count != 0
        or assessment.production_write_count != 0
        or actual_fingerprint != _fingerprint(payload)
    ):
        raise StrategyResearchReadinessError(
            "strategy research readiness assessment does not formally reconcile"
        )


def _observations(
    experiment: CandidateStrategyResearchExperimentV1,
    canonical: CanonicalEodIdentityEvidence,
    manifest: HistoricalCoverageManifestV1 | None,
) -> tuple[StrategyResearchRequirementObservation, ...]:
    manifest_datasets = {
        item.family: item for item in (() if manifest is None else manifest.datasets)
    }
    manifest_ready = (
        manifest is not None
        and manifest.readiness_status is HistoricalReadinessStatus.RESEARCH_READY
    )
    if manifest is not None:
        if not set(manifest.sessions).issubset(set(canonical.sessions)):
            raise StrategyResearchReadinessError(
                "historical coverage sessions are absent from canonical EOD evidence"
            )
        if manifest.maximum_outcome_horizon_sessions < max(
            experiment.target_holding_sessions
        ):
            raise StrategyResearchReadinessError(
                "historical coverage outcome horizon is shorter than the experiment"
            )
        maximum_feature_lookback = max(
            item.minimum_lookback_sessions for item in experiment.feature_requirements
        )
        if manifest.feature_warmup_sessions < maximum_feature_lookback:
            raise StrategyResearchReadinessError(
                "historical coverage warmup is shorter than the experiment"
            )

    history_state = (
        ResearchRequirementState.SATISFIED
        if manifest_ready
        and manifest is not None
        and len(manifest.sessions) >= experiment.minimum_research_history_sessions
        else ResearchRequirementState.MECHANICS_ONLY
        if canonical.sessions
        else ResearchRequirementState.BLOCKED
    )
    history_reasons = (
        ()
        if history_state is ResearchRequirementState.SATISFIED
        else (
            f"observed_{len(canonical.sessions)}_of_"
            f"{experiment.minimum_research_history_sessions}_required_sessions",
        )
    )
    rows: list[StrategyResearchRequirementObservation] = [
        StrategyResearchRequirementObservation(
            requirement_id="canonical_history_depth",
            state=history_state,
            required_for_development=True,
            dataset_family=HistoricalDatasetFamily.EOD_PRICE_BAR.value,
            expected_session_count=experiment.minimum_research_history_sessions,
            observed_session_count=len(canonical.sessions),
            source_fingerprint=canonical.logical_fingerprint,
            reason_codes=history_reasons,
        ),
        StrategyResearchRequirementObservation(
            requirement_id="experiment_preregistration",
            state=ResearchRequirementState.SATISFIED,
            required_for_development=True,
            dataset_family=None,
            expected_session_count=None,
            observed_session_count=None,
            source_fingerprint=experiment.logical_fingerprint,
            reason_codes=(),
        ),
    ]
    requirement_by_family = {
        HistoricalDatasetFamily.EOD_PRICE_BAR: "eod_price_bar_coverage",
        HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY: (
            "point_in_time_identity_coverage"
        ),
        HistoricalDatasetFamily.UNIVERSE_MEMBERSHIP: (
            "daily_point_in_time_membership"
        ),
        HistoricalDatasetFamily.CORPORATE_ACTION: "corporate_action_coverage",
        HistoricalDatasetFamily.INSTRUMENT_LIFECYCLE: (
            "instrument_lifecycle_coverage"
        ),
        HistoricalDatasetFamily.ADJUSTMENT_LEDGER: (
            "adjustment_ledger_reconciliation"
        ),
    }
    for family in sorted(
        RESEARCH_REQUIRED_DATASET_FAMILIES,
        key=lambda item: item.value,
    ):
        dataset = manifest_datasets.get(family)
        satisfied = (
            manifest_ready
            and dataset is not None
            and dataset.completed
            and manifest is not None
            and dataset.first_session <= manifest.sessions[0]
            and dataset.last_session >= manifest.sessions[-1]
        )
        mechanics = (
            family
            in {
                HistoricalDatasetFamily.EOD_PRICE_BAR,
                HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY,
            }
            and bool(canonical.sessions)
        )
        state = (
            ResearchRequirementState.SATISFIED
            if satisfied
            else ResearchRequirementState.MECHANICS_ONLY
            if mechanics
            else ResearchRequirementState.BLOCKED
        )
        reasons = (
            ()
            if satisfied
            else ("research_ready_coverage_manifest_absent",)
            if manifest is None
            else (f"family_not_research_ready:{family.value}",)
        )
        rows.append(
            StrategyResearchRequirementObservation(
                requirement_id=requirement_by_family[family],
                state=state,
                required_for_development=True,
                dataset_family=family.value,
                expected_session_count=experiment.minimum_research_history_sessions,
                observed_session_count=(
                    len(canonical.sessions)
                    if dataset is None
                    and family
                    in {
                        HistoricalDatasetFamily.EOD_PRICE_BAR,
                        HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY,
                    }
                    else None if dataset is None else len(manifest.sessions)
                ),
                source_fingerprint=(
                    canonical.logical_fingerprint
                    if dataset is None and mechanics
                    else None if dataset is None else dataset.logical_fingerprint
                ),
                reason_codes=reasons,
            )
        )
    matured = manifest is not None and manifest.matured_signal_session_count > 0
    rows.append(
        StrategyResearchRequirementObservation(
            requirement_id="matured_signal_window",
            state=(
                ResearchRequirementState.SATISFIED
                if manifest_ready and matured
                else ResearchRequirementState.BLOCKED
            ),
            required_for_development=True,
            dataset_family=None,
            expected_session_count=1,
            observed_session_count=(
                0 if manifest is None else manifest.matured_signal_session_count
            ),
            source_fingerprint=(
                None if manifest is None else manifest.logical_fingerprint
            ),
            reason_codes=(
                ()
                if manifest_ready and matured
                else ("matured_signal_window_not_research_ready",)
            ),
        )
    )
    return tuple(sorted(rows, key=lambda item: item.requirement_id))


def _validate_hash(value: str, field_name: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise StrategyResearchReadinessError(f"{field_name} fingerprint is malformed")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
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
