"""Read-only, fail-closed planning for one exact daily EOD analytics run."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Callable, Mapping

from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.market_intelligence_active import (
    MarketIntelligencePublicationError,
    MarketIntelligenceUnavailable,
    pointer_path as market_intelligence_pointer_path,
    read_active_market_intelligence,
    read_market_intelligence_approval_plan,
)
from tip_api.persistence.parquet.dashboard_snapshot_active import (
    DashboardSnapshotPublicationError,
    aggregate_sha as dashboard_snapshot_aggregate_sha,
    file_references as dashboard_snapshot_file_references,
    read_dashboard_snapshot_pointer,
    read_dashboard_snapshot_approval_plan,
)
from tip_api.providers.massive.grouped_daily_ingestion import load_identity_snapshot
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.services.candidate_entry_geometry_audit import (
    read_candidate_entry_geometry_audit,
)
from tip_api.services.candidate_strategy_channel_audit import (
    read_candidate_strategy_channel_audit,
)
from tip_api.services.etf_relationship_audit import (
    read_etf_relationship_planning_evidence,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_audit import read_market_regime_audit_contents
from tip_api.services.market_regime_preview import read_market_regime_preview_bundle
from tip_api.services.market_regime_state_audit import (
    read_market_regime_state_audit_contents,
)
from tip_api.services.opportunity_candidate_audit import (
    read_opportunity_candidate_planning_evidence,
)
from tip_api.services.oci_dashboard_serving_bundle import (
    read_oci_dashboard_serving_bundle,
)
from tip_api.services.private_dashboard_snapshot import (
    DashboardSnapshotError,
    sha256_file,
    validate_snapshot_release,
)


CONTRACT_VERSION = "daily-eod-automation-plan/1.4"


class DailyEodAutomationError(RuntimeError):
    """Raised when the planner inputs cannot define one safe daily run."""


class ArtifactStatus(StrEnum):
    COMPLETED = "completed"
    MISSING = "missing"
    INVALID = "invalid"
    NOT_INSPECTED = "not_inspected"


class PlanStatus(StrEnum):
    WAITING_FOR_AUTHORIZED_INPUT = "waiting_for_authorized_input"
    READY_FOR_OFFLINE_CALCULATION = "ready_for_offline_calculation"
    ANALYTICS_READY = "analytics_ready"
    BLOCKED = "blocked"


class NextAction(StrEnum):
    PREPARE_IDENTITY_CATCHUP = "prepare_identity_catchup"
    PREPARE_EOD_CATCHUP = "prepare_eod_catchup"
    CALCULATE_PHASE1A = "calculate_phase1a"
    CALCULATE_PHASE1B_INCREMENTAL = "calculate_phase1b_incremental"
    CALCULATE_CANDIDATE_DAILY = "calculate_candidate_daily"
    CALCULATE_ENTRY_GEOMETRY = "calculate_entry_geometry"
    CALCULATE_ETF_RELATIONSHIPS = "calculate_etf_relationships"
    BUILD_MARKET_PREVIEW = "build_market_preview"
    CALCULATE_STRATEGY_CHANNELS = "calculate_strategy_channels"
    PREPARE_MARKET_INTELLIGENCE_PLAN = "prepare_market_intelligence_plan"
    REVIEW_PUBLICATION = "review_publication"
    PREPARE_DASHBOARD_SNAPSHOT_PLAN = "prepare_dashboard_snapshot_plan"
    REVIEW_SNAPSHOT_PUBLICATION = "review_snapshot_publication"
    BUILD_SERVING_BUNDLE = "build_serving_bundle"
    REVIEW_BUNDLE_DEPLOYMENT = "review_bundle_deployment"
    OPERATOR_DIAGNOSIS = "operator_diagnosis"


@dataclass(frozen=True, slots=True)
class DailyEodAutomationPaths:
    data_root: Path
    phase1a_audit: Path
    prior_phase1b_audit: Path
    phase1b_audit: Path
    prior_candidate_audit: Path
    candidate_audit: Path
    entry_geometry_audit: Path
    phase2_audit: Path
    preview_bundle: Path
    strategy_channel_audit: Path
    market_intelligence_output_root: Path
    market_intelligence_approval_plan: Path
    snapshot_output_root: Path
    snapshot_approval_plan: Path
    serving_bundle_root: Path


@dataclass(frozen=True, slots=True)
class ArtifactObservation:
    stage: str
    status: ArtifactStatus
    path: str
    as_of_session: str | None = None
    logical_fingerprint: str | None = None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DailyEodAutomationPlan:
    contract_version: str
    target_session: str
    prior_session: str
    status: PlanStatus
    next_action: NextAction
    reason_codes: tuple[str, ...]
    observations: tuple[ArtifactObservation, ...]
    publication_authorized: bool
    deployment_authorized: bool
    scheduler_enabled: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return _jsonable(asdict(self))


@dataclass(frozen=True, slots=True)
class _CompletedProof:
    observation: ArtifactObservation
    payload: object


def plan_daily_eod_automation(
    *,
    target_session: date,
    paths: DailyEodAutomationPaths,
    calendar: ExchangeCalendar | None = None,
) -> DailyEodAutomationPlan:
    """Formally inspect one exact session and return only its next safe action."""

    _validate_paths(paths)
    session_calendar = calendar or ExchangeCalendar()
    if not session_calendar.is_session(target_session):
        raise DailyEodAutomationError("daily target must be an XNYS session")
    prior_session = session_calendar.previous_session(target_session)
    locations = _stage_locations(target_session, paths)
    observations: list[ArtifactObservation] = []

    identity = _inspect(
        stage="identity",
        path=locations["identity"],
        reader=lambda: load_identity_snapshot(
            paths.data_root,
            provider_id=MASSIVE_PROVIDER_ID,
            as_of_date=target_session,
        ),
        session=lambda value: value.as_of_date.isoformat(),
        fingerprint=lambda value: str(value.manifest["snapshot_content_sha256"]),
    )
    observations.append(identity.observation)
    if identity.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="identity",
            failed=identity.observation,
            observations=observations,
            locations=locations,
        )

    eod = _inspect(
        stage="eod",
        path=locations["eod"],
        reader=lambda: CanonicalEodReadRepository(paths.data_root).inspect_session(target_session),
        session=lambda value: value.session_date.isoformat(),
        fingerprint=lambda value: value.content_fingerprint,
    )
    observations.append(eod.observation)
    if eod.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="eod",
            failed=eod.observation,
            observations=observations,
            locations=locations,
        )
    if eod.payload.identity_snapshot_fingerprint != identity.observation.logical_fingerprint:
        return _blocked(
            target_session,
            prior_session,
            observations,
            "eod_identity_fingerprint_mismatch",
        )

    phase1a = _inspect(
        stage="phase1a",
        path=paths.phase1a_audit,
        reader=lambda: read_market_regime_audit_contents(paths.phase1a_audit),
        session=lambda value: str(value.manifest["as_of_session"]),
        fingerprint=lambda value: str(value.manifest["logical_content_fingerprint"]),
    )
    observations.append(phase1a.observation)
    if phase1a.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="phase1a",
            failed=phase1a.observation,
            observations=observations,
            locations=locations,
        )
    if phase1a.observation.as_of_session != target_session.isoformat():
        return _blocked(target_session, prior_session, observations, "phase1a_session_mismatch")
    if (
        phase1a.payload.input_manifest.get("identity_logical_fingerprint")
        != identity.observation.logical_fingerprint
        or phase1a.payload.input_manifest.get("eod_content_fingerprint")
        != eod.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "phase1a_source_fingerprint_mismatch")

    prior_phase1b = _inspect(
        stage="prior_phase1b",
        path=paths.prior_phase1b_audit,
        reader=lambda: read_market_regime_state_audit_contents(paths.prior_phase1b_audit),
        session=lambda value: str(value.manifest["as_of_session"]),
        fingerprint=lambda value: str(value.manifest["logical_content_fingerprint"]),
    )
    observations.append(prior_phase1b.observation)
    if prior_phase1b.observation.status is not ArtifactStatus.COMPLETED:
        return _blocked(target_session, prior_session, observations, "verified_prior_phase1b_unavailable")
    if prior_phase1b.observation.as_of_session != prior_session.isoformat():
        return _blocked(target_session, prior_session, observations, "prior_phase1b_session_mismatch")

    phase1b = _inspect(
        stage="phase1b",
        path=paths.phase1b_audit,
        reader=lambda: read_market_regime_state_audit_contents(paths.phase1b_audit),
        session=lambda value: str(value.manifest["as_of_session"]),
        fingerprint=lambda value: str(value.manifest["logical_content_fingerprint"]),
    )
    observations.append(phase1b.observation)
    if phase1b.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="phase1b",
            failed=phase1b.observation,
            observations=observations,
            locations=locations,
        )
    phase1b_manifest = phase1b.payload.manifest
    phase1b_source = phase1b.payload.source_manifest
    if phase1b.observation.as_of_session != target_session.isoformat():
        return _blocked(target_session, prior_session, observations, "phase1b_session_mismatch")
    if phase1b_manifest.get("execution_mode") != "verified_prior_incremental":
        return _blocked(target_session, prior_session, observations, "phase1b_not_daily_incremental")
    if (
        phase1b_manifest.get("prior_as_of_session") != prior_session.isoformat()
        or phase1b_manifest.get("prior_audit_logical_fingerprint")
        != prior_phase1b.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "phase1b_prior_binding_mismatch")
    if (
        phase1b_source.get("phase1a_audit_logical_fingerprint")
        != phase1a.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "phase1b_phase1a_binding_mismatch")

    prior_candidate = _inspect(
        stage="prior_candidate",
        path=paths.prior_candidate_audit,
        reader=lambda: read_opportunity_candidate_planning_evidence(
            paths.prior_candidate_audit
        ),
        session=lambda value: str(value.manifest["as_of_session"]),
        fingerprint=lambda value: str(value.manifest["logical_content_fingerprint"]),
    )
    observations.append(prior_candidate.observation)
    if prior_candidate.observation.status is not ArtifactStatus.COMPLETED:
        return _blocked(target_session, prior_session, observations, "verified_prior_candidate_unavailable")
    if prior_candidate.observation.as_of_session != prior_session.isoformat():
        return _blocked(target_session, prior_session, observations, "prior_candidate_session_mismatch")

    candidate = _inspect(
        stage="candidate",
        path=paths.candidate_audit,
        reader=lambda: read_opportunity_candidate_planning_evidence(
            paths.candidate_audit
        ),
        session=lambda value: str(value.manifest["as_of_session"]),
        fingerprint=lambda value: str(value.manifest["logical_content_fingerprint"]),
    )
    observations.append(candidate.observation)
    if candidate.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="candidate",
            failed=candidate.observation,
            observations=observations,
            locations=locations,
        )
    candidate_manifest = candidate.payload.manifest
    if candidate.observation.as_of_session != target_session.isoformat():
        return _blocked(target_session, prior_session, observations, "candidate_session_mismatch")
    if candidate_manifest.get("execution_mode") != "verified_prior_incremental":
        return _blocked(target_session, prior_session, observations, "candidate_not_daily_incremental")
    candidate_validation = candidate.payload.validation_ledger
    if (
        not isinstance(candidate_validation, Mapping)
        or candidate_validation.get("validation_tier") != "daily"
        or candidate_validation.get("validation_scope")
        != "verified_prior_plus_current_session_oracle"
    ):
        return _blocked(target_session, prior_session, observations, "candidate_daily_validation_missing")
    if (
        candidate_manifest.get("prior_as_of_session") != prior_session.isoformat()
        or candidate_manifest.get("prior_audit_logical_fingerprint")
        != prior_candidate.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "candidate_prior_binding_mismatch")

    entry = _inspect(
        stage="entry_geometry",
        path=paths.entry_geometry_audit,
        reader=lambda: read_candidate_entry_geometry_audit(paths.entry_geometry_audit),
        session=lambda value: str(value["as_of_session"]),
        fingerprint=lambda value: str(value["logical_content_fingerprint"]),
    )
    observations.append(entry.observation)
    if entry.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="entry_geometry",
            failed=entry.observation,
            observations=observations,
            locations=locations,
        )
    if entry.observation.as_of_session != target_session.isoformat():
        return _blocked(target_session, prior_session, observations, "entry_geometry_session_mismatch")
    if (
        entry.payload.get("source", {}).get("candidate_audit_logical_fingerprint")
        != candidate.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "entry_candidate_binding_mismatch")

    phase2 = _inspect(
        stage="phase2",
        path=paths.phase2_audit,
        reader=lambda: read_etf_relationship_planning_evidence(paths.phase2_audit),
        session=lambda value: str(value.manifest["as_of_session"]),
        fingerprint=lambda value: str(value.manifest["logical_content_fingerprint"]),
    )
    observations.append(phase2.observation)
    if phase2.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="phase2",
            failed=phase2.observation,
            observations=observations,
            locations=locations,
        )
    if phase2.observation.as_of_session != target_session.isoformat():
        return _blocked(target_session, prior_session, observations, "phase2_session_mismatch")
    if (
        phase2.payload.source_manifest.get("phase1a_audit_logical_fingerprint")
        != phase1a.observation.logical_fingerprint
        or phase2.payload.source_manifest.get("phase1b_audit_logical_fingerprint")
        != phase1b.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "phase2_source_binding_mismatch")

    preview = _inspect(
        stage="preview",
        path=paths.preview_bundle,
        reader=lambda: read_market_regime_preview_bundle(paths.preview_bundle),
        session=lambda value: value.payload.as_of_session.isoformat(),
        fingerprint=lambda value: value.payload.logical_fingerprint,
    )
    observations.append(preview.observation)
    if preview.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="preview",
            failed=preview.observation,
            observations=observations,
            locations=locations,
        )
    if preview.observation.as_of_session != target_session.isoformat():
        return _blocked(target_session, prior_session, observations, "preview_session_mismatch")
    preview_sources = preview.payload.payload.source_logical_fingerprints
    if (
        preview_sources.phase1a != phase1a.observation.logical_fingerprint
        or preview_sources.phase1b != phase1b.observation.logical_fingerprint
        or preview_sources.phase2 != phase2.observation.logical_fingerprint
    ):
        return _blocked(target_session, prior_session, observations, "preview_source_binding_mismatch")

    strategy = _inspect(
        stage="strategy_channels",
        path=paths.strategy_channel_audit,
        reader=lambda: read_candidate_strategy_channel_audit(
            paths.strategy_channel_audit
        ),
        session=lambda value: str(value["as_of_session"]),
        fingerprint=lambda value: str(value["logical_content_fingerprint"]),
    )
    observations.append(strategy.observation)
    if strategy.observation.status is not ArtifactStatus.COMPLETED:
        return _stop_before_stage(
            target_session=target_session,
            prior_session=prior_session,
            stage="strategy_channels",
            failed=strategy.observation,
            observations=observations,
            locations=locations,
        )
    if strategy.observation.as_of_session != target_session.isoformat():
        return _blocked(
            target_session,
            prior_session,
            observations,
            "strategy_channels_session_mismatch",
        )
    strategy_source = strategy.payload.get("source", {})
    if (
        strategy_source.get("candidate_audit", {}).get(
            "logical_content_fingerprint"
        )
        != candidate.observation.logical_fingerprint
        or strategy_source.get("entry_geometry_audit", {}).get(
            "logical_content_fingerprint"
        )
        != entry.observation.logical_fingerprint
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "strategy_channels_source_binding_mismatch",
        )

    publication_candidate = (
        paths.market_intelligence_output_root
        / "market-intelligence.plan.artifacts"
    )
    output_exists = _lexists(paths.market_intelligence_output_root)
    plan_exists = _lexists(paths.market_intelligence_approval_plan)
    if not output_exists and not plan_exists:
        observations.append(
            ArtifactObservation(
                stage="publication_plan",
                status=ArtifactStatus.MISSING,
                path=str(paths.market_intelligence_approval_plan),
                reason_codes=("artifact_absent",),
            )
        )
        return _build_plan(
            target_session=target_session,
            prior_session=prior_session,
            status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            next_action=NextAction.PREPARE_MARKET_INTELLIGENCE_PLAN,
            reason_codes=("publication_plan_required",),
            observations=observations,
        )
    if output_exists != plan_exists:
        observations.append(
            ArtifactObservation(
                stage="publication_plan",
                status=ArtifactStatus.INVALID,
                path=str(paths.market_intelligence_approval_plan),
                reason_codes=("partial_plan_artifacts",),
            )
        )
        return _blocked(
            target_session,
            prior_session,
            observations,
            "publication_plan_partial",
        )
    publication = _inspect(
        stage="publication_plan",
        path=paths.market_intelligence_approval_plan,
        reader=lambda: read_market_intelligence_approval_plan(
            paths.market_intelligence_approval_plan
        ),
        session=lambda value: value.analysis_session.isoformat(),
        fingerprint=lambda value: value.plan_content_fingerprint,
    )
    observations.append(publication.observation)
    if publication.observation.status is not ArtifactStatus.COMPLETED:
        return _blocked(
            target_session,
            prior_session,
            observations,
            "publication_plan_invalid",
        )
    plan = publication.payload
    if publication.observation.as_of_session != target_session.isoformat():
        return _blocked(
            target_session,
            prior_session,
            observations,
            "publication_plan_session_mismatch",
        )
    if (
        getattr(plan, "plan_version", None) != "1.2"
        or Path(plan.data_root) != paths.data_root
        or Path(plan.preview_bundle_path) != paths.preview_bundle
        or Path(plan.phase1a_audit_path) != paths.phase1a_audit
        or Path(plan.phase1b_audit_path) != paths.phase1b_audit
        or Path(plan.phase2_audit_path) != paths.phase2_audit
        or Path(plan.candidate_audit_path) != paths.candidate_audit
        or Path(plan.entry_geometry_audit_path) != paths.entry_geometry_audit
        or Path(plan.candidate_path) != publication_candidate
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "publication_plan_path_binding_mismatch",
        )
    phase_sources = plan.source.phase_logical_fingerprints
    if (
        phase_sources.phase1a != phase1a.observation.logical_fingerprint
        or phase_sources.phase1b != phase1b.observation.logical_fingerprint
        or phase_sources.phase2 != phase2.observation.logical_fingerprint
        or plan.source.preview_payload_logical_fingerprint
        != preview.observation.logical_fingerprint
        or plan.candidate_source.candidate_audit_logical_fingerprint
        != candidate.observation.logical_fingerprint
        or plan.entry_geometry_audit_logical_fingerprint
        != entry.observation.logical_fingerprint
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "publication_plan_source_binding_mismatch",
        )
    try:
        active_market_intelligence = read_active_market_intelligence(
            paths.data_root,
            validate_sources=False,
        )
    except MarketIntelligenceUnavailable:
        active_market_intelligence = None
    except (OSError, MarketIntelligencePublicationError):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "market_intelligence_active_state_invalid",
        )
    if (
        active_market_intelligence is None
        or active_market_intelligence.pointer is None
        or active_market_intelligence.payload.publication_id
        != plan.publication_id
    ):
        observations.append(
            ArtifactObservation(
                stage="market_intelligence_active",
                status=ArtifactStatus.MISSING,
                path=str(market_intelligence_pointer_path(paths.data_root)),
                reason_codes=("approved_publication_not_active",),
            )
        )
        return _build_plan(
            target_session=target_session,
            prior_session=prior_session,
            status=PlanStatus.ANALYTICS_READY,
            next_action=NextAction.REVIEW_PUBLICATION,
            reason_codes=(
                (
                    "publication_plan_ready_for_review"
                    if (
                        plan.activation_allowed
                        or plan.activation_allowed_by_review_authorization
                    )
                    else "publication_plan_freshness_blocked"
                ),
            ),
            observations=observations,
        )
    if (
        active_market_intelligence.pointer.pointer_content_fingerprint
        != plan.planned_pointer_fingerprint
        or active_market_intelligence.payload.analysis_session != target_session
        or active_market_intelligence.path != Path(plan.target_path)
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "market_intelligence_active_state_mismatch",
        )
    observations.append(
        ArtifactObservation(
            stage="market_intelligence_active",
            status=ArtifactStatus.COMPLETED,
            path=str(market_intelligence_pointer_path(paths.data_root)),
            as_of_session=target_session.isoformat(),
            logical_fingerprint=(
                active_market_intelligence.pointer.pointer_content_fingerprint
            ),
        )
    )

    snapshot_output_exists = _lexists(paths.snapshot_output_root)
    snapshot_plan_exists = _lexists(paths.snapshot_approval_plan)
    if not snapshot_output_exists and not snapshot_plan_exists:
        observations.append(
            ArtifactObservation(
                stage="snapshot_plan",
                status=ArtifactStatus.MISSING,
                path=str(paths.snapshot_approval_plan),
                reason_codes=("artifact_absent",),
            )
        )
        return _build_plan(
            target_session=target_session,
            prior_session=prior_session,
            status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            next_action=NextAction.PREPARE_DASHBOARD_SNAPSHOT_PLAN,
            reason_codes=("snapshot_plan_required",),
            observations=observations,
        )
    if snapshot_output_exists != snapshot_plan_exists:
        observations.append(
            ArtifactObservation(
                stage="snapshot_plan",
                status=ArtifactStatus.INVALID,
                path=str(paths.snapshot_approval_plan),
                reason_codes=("partial_plan_artifacts",),
            )
        )
        return _blocked(
            target_session,
            prior_session,
            observations,
            "snapshot_plan_partial",
        )
    snapshot = _inspect(
        stage="snapshot_plan",
        path=paths.snapshot_approval_plan,
        reader=lambda: read_dashboard_snapshot_approval_plan(
            paths.snapshot_approval_plan
        ),
        session=lambda value: value.analysis_session.isoformat(),
        fingerprint=lambda value: value.plan_content_fingerprint,
    )
    observations.append(snapshot.observation)
    if snapshot.observation.status is not ArtifactStatus.COMPLETED:
        return _blocked(
            target_session,
            prior_session,
            observations,
            "snapshot_plan_invalid",
        )
    snapshot_plan = snapshot.payload
    if (
        snapshot_plan.plan_version != "2.4"
        or snapshot_plan.analysis_session != target_session
        or Path(snapshot_plan.candidate_path).parent
        != paths.snapshot_output_root
        or snapshot_plan.market_intelligence_publication_id
        != plan.publication_id
        or snapshot_plan.market_intelligence_payload_sha256
        != active_market_intelligence.manifest.payload_sha256
        or snapshot_plan.market_intelligence_logical_fingerprint
        != active_market_intelligence.payload.logical_fingerprint
        or snapshot_plan.candidate_strategy_audit_logical_fingerprint
        != strategy.observation.logical_fingerprint
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "snapshot_plan_source_binding_mismatch",
        )
    try:
        snapshot_pointer = read_dashboard_snapshot_pointer(paths.data_root)
    except (OSError, DashboardSnapshotPublicationError):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "dashboard_snapshot_active_state_invalid",
        )
    if (
        snapshot_pointer is None
        or snapshot_pointer.pointer_content_fingerprint
        != snapshot_plan.planned_pointer_fingerprint
    ):
        observations.append(
            ArtifactObservation(
                stage="dashboard_snapshot_active",
                status=ArtifactStatus.MISSING,
                path=snapshot_plan.pointer_path,
                reason_codes=("approved_snapshot_not_active",),
            )
        )
        return _build_plan(
            target_session=target_session,
            prior_session=prior_session,
            status=PlanStatus.ANALYTICS_READY,
            next_action=NextAction.REVIEW_SNAPSHOT_PUBLICATION,
            reason_codes=("snapshot_plan_ready_for_review",),
            observations=observations,
        )
    active_reference = snapshot_pointer.active
    if (
        active_reference.release_id != snapshot_plan.release_id
        or active_reference.logical_path != snapshot_plan.target_logical_path
        or active_reference.snapshot_contract_version
        != snapshot_plan.snapshot_contract_version
        or active_reference.dashboard_contract_version
        != snapshot_plan.dashboard_contract_version
        or active_reference.aggregate_sha256 != snapshot_plan.aggregate_sha256
        or active_reference.manifest_sha256 != snapshot_plan.manifest_sha256
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "dashboard_snapshot_active_state_mismatch",
        )
    active_snapshot_path = Path(snapshot_plan.target_path)
    try:
        active_snapshot = validate_snapshot_release(active_snapshot_path)
        active_snapshot_files = dashboard_snapshot_file_references(
            active_snapshot_path
        )
    except (OSError, DashboardSnapshotError):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "dashboard_snapshot_active_target_invalid",
        )
    if (
        active_snapshot.release_id != snapshot_plan.release_id
        or active_snapshot.current_session_date != target_session.isoformat()
        or active_snapshot.market_intelligence_publication_id
        != snapshot_plan.market_intelligence_publication_id
        or dashboard_snapshot_aggregate_sha(active_snapshot_files)
        != snapshot_plan.aggregate_sha256
        or sha256_file(active_snapshot_path / "private-data/v1/manifest.json")
        != snapshot_plan.manifest_sha256
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "dashboard_snapshot_active_target_mismatch",
        )
    observations.append(
        ArtifactObservation(
            stage="dashboard_snapshot_active",
            status=ArtifactStatus.COMPLETED,
            path=str(active_snapshot_path),
            as_of_session=target_session.isoformat(),
            logical_fingerprint=snapshot_pointer.pointer_content_fingerprint,
        )
    )

    bundle_path = paths.serving_bundle_root / snapshot_plan.release_id
    staging_path = paths.serving_bundle_root / f".{snapshot_plan.release_id}.staging"
    if not _lexists(paths.serving_bundle_root):
        observations.append(
            ArtifactObservation(
                stage="serving_bundle",
                status=ArtifactStatus.MISSING,
                path=str(bundle_path),
                reason_codes=("artifact_absent",),
            )
        )
        return _build_plan(
            target_session=target_session,
            prior_session=prior_session,
            status=PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            next_action=NextAction.BUILD_SERVING_BUNDLE,
            reason_codes=("serving_bundle_required",),
            observations=observations,
        )
    if (
        paths.serving_bundle_root.is_symlink()
        or not paths.serving_bundle_root.is_dir()
        or _lexists(staging_path)
        or not _lexists(bundle_path)
        or {item.name for item in paths.serving_bundle_root.iterdir()}
        != {snapshot_plan.release_id}
    ):
        observations.append(
            ArtifactObservation(
                stage="serving_bundle",
                status=ArtifactStatus.INVALID,
                path=str(bundle_path),
                reason_codes=("partial_or_unexpected_bundle_artifacts",),
            )
        )
        return _blocked(
            target_session,
            prior_session,
            observations,
            "serving_bundle_partial",
        )
    bundle = _inspect(
        stage="serving_bundle",
        path=bundle_path,
        reader=lambda: read_oci_dashboard_serving_bundle(
            bundle_path,
            expected_snapshot_path=active_snapshot_path,
        ),
        session=lambda value: value.snapshot_manifest.current_session_date,
        fingerprint=lambda value: value.bundle_logical_fingerprint,
    )
    observations.append(bundle.observation)
    if bundle.observation.status is not ArtifactStatus.COMPLETED:
        return _blocked(
            target_session,
            prior_session,
            observations,
            "serving_bundle_invalid",
        )
    if (
        bundle.payload.deployment_manifest.release_id
        != snapshot_plan.release_id
        or bundle.payload.deployment_manifest.snapshot_aggregate_sha256
        != snapshot_plan.aggregate_sha256
        or bundle.payload.deployment_manifest.snapshot_manifest_sha256
        != snapshot_plan.manifest_sha256
    ):
        return _blocked(
            target_session,
            prior_session,
            observations,
            "serving_bundle_source_binding_mismatch",
        )
    return _build_plan(
        target_session=target_session,
        prior_session=prior_session,
        status=PlanStatus.ANALYTICS_READY,
        next_action=NextAction.REVIEW_BUNDLE_DEPLOYMENT,
        reason_codes=("serving_bundle_ready_for_deployment_review",),
        observations=observations,
    )


def _inspect(
    *,
    stage: str,
    path: Path,
    reader: Callable[[], object],
    session: Callable[[object], str],
    fingerprint: Callable[[object], str],
) -> _CompletedProof:
    if not _lexists(path):
        return _CompletedProof(
            ArtifactObservation(stage, ArtifactStatus.MISSING, str(path), reason_codes=("artifact_absent",)),
            None,
        )
    try:
        payload = reader()
        observation = ArtifactObservation(
            stage=stage,
            status=ArtifactStatus.COMPLETED,
            path=str(path),
            as_of_session=session(payload),
            logical_fingerprint=fingerprint(payload),
        )
        _validate_observation(observation)
        return _CompletedProof(observation, payload)
    except Exception:  # Formal readers are the fail-closed corruption boundary.
        return _CompletedProof(
            ArtifactObservation(
                stage,
                ArtifactStatus.INVALID,
                str(path),
                reason_codes=("formal_reader_failed_closed",),
            ),
            None,
        )


def _stop_before_stage(
    *,
    target_session: date,
    prior_session: date,
    stage: str,
    failed: ArtifactObservation,
    observations: list[ArtifactObservation],
    locations: Mapping[str, Path],
) -> DailyEodAutomationPlan:
    downstream = _downstream_existing(stage, locations)
    if failed.status is ArtifactStatus.INVALID:
        return _blocked(target_session, prior_session, observations, f"{stage}_invalid")
    if downstream:
        observations.extend(
            ArtifactObservation(
                item,
                ArtifactStatus.NOT_INSPECTED,
                str(locations[item]),
                reason_codes=("downstream_exists_without_verified_prerequisite",),
            )
            for item in downstream
        )
        return _blocked(
            target_session,
            prior_session,
            observations,
            "downstream_artifact_without_verified_prerequisite",
        )
    action_by_stage = {
        "identity": (PlanStatus.WAITING_FOR_AUTHORIZED_INPUT, NextAction.PREPARE_IDENTITY_CATCHUP),
        "eod": (PlanStatus.WAITING_FOR_AUTHORIZED_INPUT, NextAction.PREPARE_EOD_CATCHUP),
        "phase1a": (PlanStatus.READY_FOR_OFFLINE_CALCULATION, NextAction.CALCULATE_PHASE1A),
        "phase1b": (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_PHASE1B_INCREMENTAL,
        ),
        "candidate": (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_CANDIDATE_DAILY,
        ),
        "entry_geometry": (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_ENTRY_GEOMETRY,
        ),
        "phase2": (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_ETF_RELATIONSHIPS,
        ),
        "preview": (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.BUILD_MARKET_PREVIEW,
        ),
        "strategy_channels": (
            PlanStatus.READY_FOR_OFFLINE_CALCULATION,
            NextAction.CALCULATE_STRATEGY_CHANNELS,
        ),
    }
    status, action = action_by_stage[stage]
    return _build_plan(
        target_session=target_session,
        prior_session=prior_session,
        status=status,
        next_action=action,
        reason_codes=(f"{stage}_required",),
        observations=observations,
    )


def _blocked(
    target_session: date,
    prior_session: date,
    observations: list[ArtifactObservation],
    reason_code: str,
) -> DailyEodAutomationPlan:
    return _build_plan(
        target_session=target_session,
        prior_session=prior_session,
        status=PlanStatus.BLOCKED,
        next_action=NextAction.OPERATOR_DIAGNOSIS,
        reason_codes=(reason_code,),
        observations=observations,
    )


def _build_plan(
    *,
    target_session: date,
    prior_session: date,
    status: PlanStatus,
    next_action: NextAction,
    reason_codes: tuple[str, ...],
    observations: list[ArtifactObservation],
) -> DailyEodAutomationPlan:
    logical = {
        "contract_version": CONTRACT_VERSION,
        "target_session": target_session.isoformat(),
        "prior_session": prior_session.isoformat(),
        "status": status.value,
        "next_action": next_action.value,
        "reason_codes": list(reason_codes),
        "observations": [_jsonable(asdict(item)) for item in observations],
        "publication_authorized": False,
        "deployment_authorized": False,
        "scheduler_enabled": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return DailyEodAutomationPlan(
        contract_version=CONTRACT_VERSION,
        target_session=target_session.isoformat(),
        prior_session=prior_session.isoformat(),
        status=status,
        next_action=next_action,
        reason_codes=reason_codes,
        observations=tuple(observations),
        publication_authorized=False,
        deployment_authorized=False,
        scheduler_enabled=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(logical),
    )


def _stage_locations(target_session: date, paths: DailyEodAutomationPaths) -> dict[str, Path]:
    session = target_session.isoformat()
    return {
        "identity": paths.data_root / "market-data" / "snapshots" / "instrument-master" / f"as_of_date={session}",
        "eod": paths.data_root / "market-data" / "eod-price-bars" / "schema_version=1" / f"session_date={session}",
        "phase1a": paths.phase1a_audit,
        "phase1b": paths.phase1b_audit,
        "candidate": paths.candidate_audit,
        "entry_geometry": paths.entry_geometry_audit,
        "phase2": paths.phase2_audit,
        "preview": paths.preview_bundle,
        "strategy_channels": paths.strategy_channel_audit,
        "publication_output": paths.market_intelligence_output_root,
        "publication_plan": paths.market_intelligence_approval_plan,
        "snapshot_output": paths.snapshot_output_root,
        "snapshot_plan": paths.snapshot_approval_plan,
        "serving_bundle": paths.serving_bundle_root,
    }


def _downstream_existing(stage: str, locations: Mapping[str, Path]) -> tuple[str, ...]:
    order = (
        "identity",
        "eod",
        "phase1a",
        "phase1b",
        "candidate",
        "entry_geometry",
        "phase2",
        "preview",
        "strategy_channels",
        "publication_output",
        "publication_plan",
        "snapshot_output",
        "snapshot_plan",
        "serving_bundle",
    )
    index = order.index(stage)
    return tuple(item for item in order[index + 1 :] if _lexists(locations[item]))


def _validate_paths(paths: DailyEodAutomationPaths) -> None:
    if not paths.data_root.is_absolute():
        raise DailyEodAutomationError("data root must be absolute")
    artifacts = (
        paths.phase1a_audit,
        paths.prior_phase1b_audit,
        paths.phase1b_audit,
        paths.prior_candidate_audit,
        paths.candidate_audit,
        paths.entry_geometry_audit,
        paths.phase2_audit,
        paths.preview_bundle,
        paths.strategy_channel_audit,
        paths.market_intelligence_output_root,
        paths.market_intelligence_approval_plan,
        paths.snapshot_output_root,
        paths.snapshot_approval_plan,
        paths.serving_bundle_root,
    )
    if len(set(artifacts)) != len(artifacts):
        raise DailyEodAutomationError("daily artifact paths must be distinct")
    if any(not item.is_absolute() for item in artifacts):
        raise DailyEodAutomationError("daily artifact paths must be absolute")
    if all(item.parent == Path("/tmp") for item in artifacts):
        return
    try:
        from tip_api.services.daily_eod_workspace import (
            DailyEodWorkspaceError,
            validate_workspace_automation_paths,
        )

        validate_workspace_automation_paths(paths)
    except DailyEodWorkspaceError as exc:
        raise DailyEodAutomationError(
            "daily artifacts must be direct children of /tmp or one exact "
            "persistent workspace layout"
        ) from exc


def _validate_observation(observation: ArtifactObservation) -> None:
    if observation.as_of_session is None:
        raise DailyEodAutomationError("completed artifact session is missing")
    fingerprint = observation.logical_fingerprint
    if (
        fingerprint is None
        or len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        raise DailyEodAutomationError("completed artifact fingerprint is malformed")


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
