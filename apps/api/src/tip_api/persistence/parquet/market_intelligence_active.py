"""Approval-bound immutable Market Intelligence publication and active reader."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable, Mapping
from uuid import uuid4

from tip_api.contracts.analytics.v1 import (
    MarketIntelligenceActivePointerV1,
    MarketIntelligenceActivationSourceV1,
    MarketIntelligenceApprovalPlanV1,
    MarketIntelligenceApprovalPlanV1_1,
    MarketIntelligenceEodSourceV1,
    MarketIntelligenceFileReferenceV1,
    MarketIntelligenceManifestV1,
    MarketIntelligenceManifestV1_1,
    MarketIntelligencePayloadV1,
    MarketIntelligencePayloadV1_1,
    MarketIntelligenceSourceBindingV1,
    MarketIntelligenceTargetReferenceV1,
    PreviewUniverseDefinitionV1,
    ReviewDeploymentAuthorizationV1,
)
from tip_api.contracts.analytics.v1.market_intelligence import (
    MARKET_INTELLIGENCE_MANIFEST_FILE,
    MARKET_INTELLIGENCE_PAYLOAD_FILE,
    MARKET_INTELLIGENCE_REVISION,
)
from tip_api.parameters.market_regime import (
    PARAMETER_SET_FINGERPRINT,
    RELATIONSHIP_PARAMETER_FINGERPRINT,
    STATE_PARAMETER_FINGERPRINT,
)
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    _fsync_directory,
    _mkdir_parents_durable,
    _reject_symlink_chain,
    _validated_root,
    active_pointer_state_fingerprint,
    read_active_dashboard_universe_activation,
    read_dashboard_universe_activation_pointer,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.etf_relationship_audit import read_etf_relationship_audit
from tip_api.services.market_regime_audit import read_market_regime_audit
from tip_api.services.market_regime_preview import (
    CompletedPreviewBundle,
    read_market_regime_preview_bundle,
)
from tip_api.services.market_regime_sources import load_formal_market_regime_panel
from tip_api.services.market_regime_state_audit import read_market_regime_state_audit
from tip_api.services.opportunity_candidate_publication import (
    build_opportunity_candidate_publication,
)


MARKET_INTELLIGENCE_BASE = "market-data/analytics/market-intelligence"
MARKET_INTELLIGENCE_POINTER = "market-data/analytics/market-intelligence-active/active.json"
EXPECTED_FILES = (MARKET_INTELLIGENCE_PAYLOAD_FILE, MARKET_INTELLIGENCE_MANIFEST_FILE)


class MarketIntelligencePublicationError(RuntimeError):
    """Fail-closed Market Intelligence custody or publication error."""


class MarketIntelligencePublicationConflict(MarketIntelligencePublicationError):
    """Raised when an immutable target, pointer, lock, or approved state changed."""


class MarketIntelligenceUnavailable(MarketIntelligencePublicationError):
    """Raised when no active formally readable Market Intelligence publication exists."""


@dataclass(frozen=True, slots=True)
class CompletedMarketIntelligence:
    path: Path
    manifest: MarketIntelligenceManifestV1 | MarketIntelligenceManifestV1_1
    payload: MarketIntelligencePayloadV1 | MarketIntelligencePayloadV1_1
    reference: MarketIntelligenceTargetReferenceV1
    pointer: MarketIntelligenceActivePointerV1 | None = None


def target_path(root: Path, analysis_session: date, publication_id: str) -> Path:
    return (
        root
        / MARKET_INTELLIGENCE_BASE
        / "schema_version=1"
        / f"revision={MARKET_INTELLIGENCE_REVISION}"
        / f"analysis_session={analysis_session.isoformat()}"
        / f"publication_id={publication_id}"
    )


def pointer_path(root: Path) -> Path:
    return root / MARKET_INTELLIGENCE_POINTER


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            _normalize_nfc(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)[:-1]).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_market_intelligence_candidate(
    *,
    data_root: Path,
    analysis_session: date,
    publication_id: str,
    generated_at: datetime,
    preview_bundle_path: Path,
    phase1a_audit_path: Path,
    phase1b_audit_path: Path,
    phase2_audit_path: Path,
    candidate_path: Path,
    candidate_audit_path: Path | None = None,
    review_deployment: ReviewDeploymentAuthorizationV1 | None = None,
) -> CompletedMarketIntelligence:
    """Create one language-neutral candidate from explicit verified sources."""

    root = _validated_root(data_root)
    source, preview = validate_source_binding(
        data_root=root,
        analysis_session=analysis_session,
        preview_bundle_path=preview_bundle_path,
        phase1a_audit_path=phase1a_audit_path,
        phase1b_audit_path=phase1b_audit_path,
        phase2_audit_path=phase2_audit_path,
    )
    candidate_analytics = (
        build_opportunity_candidate_publication(candidate_audit_path)
        if candidate_audit_path is not None
        else None
    )
    payload_fields = {
        "publication_id": publication_id,
        "analysis_session": analysis_session,
        "generated_at": generated_at.astimezone(UTC),
        "source": source,
        "analytics": preview.payload,
        "review_deployment": review_deployment,
        "logical_fingerprint": "0" * 64,
    }
    payload_candidate = (
        MarketIntelligencePayloadV1_1(
            **payload_fields,
            candidate_source=candidate_analytics.source,
            candidate_analytics=candidate_analytics,
        )
        if candidate_analytics is not None
        else MarketIntelligencePayloadV1(**payload_fields)
    )
    payload = payload_candidate.model_copy(
        update={
            "logical_fingerprint": canonical_fingerprint(
                payload_candidate.model_dump(
                    mode="json",
                    exclude={"publication_id", "generated_at", "logical_fingerprint"},
                )
            )
        }
    )
    payload_raw = canonical_bytes(payload.model_dump(mode="json"))
    primary, secondary = source.activation.universes
    manifest_body = {
        "schema_version": "1.0",
        "contract_version": payload.contract_version,
        "revision": MARKET_INTELLIGENCE_REVISION,
        "completion_status": "completed",
        "publication_id": publication_id,
        "analysis_session": analysis_session.isoformat(),
        "generated_at": generated_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "payload_file": MARKET_INTELLIGENCE_PAYLOAD_FILE,
        "payload_bytes": len(payload_raw),
        "payload_sha256": hashlib.sha256(payload_raw).hexdigest(),
        "payload_logical_fingerprint": payload.logical_fingerprint,
        "analytics_logical_fingerprint": preview.payload.logical_fingerprint,
        "source": source.model_dump(mode="json"),
        "primary_member_count": primary.member_count,
        "secondary_member_count": secondary.member_count,
        "etf_count": len(preview.payload.etf_basket),
        "relationship_count": len(preview.payload.relationships),
        "relationship_history_count": len(preview.payload.relationship_history),
        "review_deployment": (
            review_deployment.model_dump(mode="json")
            if review_deployment is not None
            else None
        ),
        "external_request_count": 0,
        "contains_credentials": False,
        "contains_raw_provider_data": False,
    }
    if candidate_analytics is not None:
        manifest_body.update(
            {
                "candidate_source": candidate_analytics.source.model_dump(mode="json"),
                "candidate_analytics_logical_fingerprint": candidate_analytics.logical_fingerprint,
                "candidate_primary_display_count": len(candidate_analytics.universes[0].candidates),
                "candidate_secondary_display_count": len(candidate_analytics.universes[1].candidates),
            }
        )
    manifest_type = (
        MarketIntelligenceManifestV1_1
        if candidate_analytics is not None
        else MarketIntelligenceManifestV1
    )
    manifest = manifest_type.model_validate(
        {
            **manifest_body,
            "manifest_logical_fingerprint": canonical_fingerprint(
                {key: value for key, value in manifest_body.items() if key != "generated_at"}
            ),
        }
    )
    target = _safe_new_tmp_directory(candidate_path)
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        _write_new(target / MARKET_INTELLIGENCE_PAYLOAD_FILE, payload_raw, mode=0o400)
        _write_new(
            target / MARKET_INTELLIGENCE_MANIFEST_FILE,
            canonical_bytes(manifest.model_dump(mode="json")),
            mode=0o400,
        )
        _fsync_directory(target)
        completed = read_market_intelligence_release(target, validate_sources=False)
    except Exception:
        if target.exists() and not target.is_symlink():
            shutil.rmtree(target)
        raise
    return completed


def validate_source_binding(
    *,
    data_root: Path,
    analysis_session: date,
    preview_bundle_path: Path,
    phase1a_audit_path: Path,
    phase1b_audit_path: Path,
    phase2_audit_path: Path,
) -> tuple[MarketIntelligenceSourceBindingV1, CompletedPreviewBundle]:
    """Reread audit custody, parameters, EOD history, Identity, and Activation."""

    preview = read_market_regime_preview_bundle(preview_bundle_path)
    phase1a = read_market_regime_audit(phase1a_audit_path)
    phase1b = read_market_regime_state_audit(phase1b_audit_path)
    phase2 = read_etf_relationship_audit(phase2_audit_path)
    expected_phase = preview.payload.source_logical_fingerprints
    if (
        phase1a["logical_content_fingerprint"] != expected_phase.phase1a
        or phase1b["logical_content_fingerprint"] != expected_phase.phase1b
        or phase2["logical_content_fingerprint"] != expected_phase.phase2
    ):
        raise MarketIntelligencePublicationError("source audit lineage differs from preview")
    if preview.payload.as_of_session != analysis_session:
        raise MarketIntelligencePublicationError("preview as-of session differs from publication")
    if (
        preview.payload.parameter_fingerprints.phase1a != PARAMETER_SET_FINGERPRINT
        or preview.payload.parameter_fingerprints.phase1b != STATE_PARAMETER_FINGERPRINT
        or preview.payload.parameter_fingerprints.phase2 != RELATIONSHIP_PARAMETER_FINGERPRINT
    ):
        raise MarketIntelligencePublicationError("calculation parameter fingerprint changed")

    panel = load_formal_market_regime_panel(
        data_root=_validated_root(data_root), as_of_session=analysis_session
    )
    phase1a_input = _read_json(phase1a_audit_path / "input-manifest.json")
    if (
        phase1a_input.get("logical_content_fingerprint")
        != next(
            item["logical_content_fingerprint"]
            for item in phase1a["artifacts"]
            if item["name"] == "input-manifest.json"
        )
    ):
        raise MarketIntelligencePublicationError("Phase 1a input manifest identity changed")
    if (
        phase1a_input.get("history_source_fingerprint") != panel.history_source_fingerprint
        or phase1a_input.get("eod_content_fingerprint") != panel.eod_content_fingerprint
        or phase1a_input.get("eod_business_key_fingerprint")
        != panel.eod_business_key_fingerprint
        or phase1a_input.get("identity_logical_fingerprint")
        != panel.identity_logical_fingerprint
        or phase1a_input.get("activation_pointer_fingerprint")
        != panel.activation_pointer_fingerprint
    ):
        raise MarketIntelligencePublicationError("formal source panel differs from Phase 1a audit")
    source_sessions = phase1a_input.get("source_sessions")
    if not isinstance(source_sessions, list) or len(source_sessions) != len(panel.source_sessions):
        raise MarketIntelligencePublicationError("Phase 1a source-session ledger is incomplete")
    actual_session_rows = [
        {
            "session_date": item.session_date.isoformat(),
            "dataset_path": item.dataset_path,
            "record_count": item.record_count,
            "content_fingerprint": item.content_fingerprint,
            "parquet_sha256": item.parquet_sha256,
            "identity_snapshot_date": item.identity_snapshot_date.isoformat(),
            "identity_snapshot_fingerprint": item.identity_snapshot_fingerprint,
        }
        for item in panel.source_sessions
    ]
    if actual_session_rows != source_sessions:
        raise MarketIntelligencePublicationError("formal EOD history differs from approved audit")

    pointer = read_dashboard_universe_activation_pointer(data_root)
    if pointer is None:
        raise MarketIntelligencePublicationError("Activation V2 pointer is required")
    activation = read_active_dashboard_universe_activation(
        data_root, analysis_session=pointer.active.analysis_session, validate_sources=True
    )
    activation_universes = tuple(
        PreviewUniverseDefinitionV1(
            universe_id=item.universe_id,
            display_name=item.display_name,
            catalog_order=order,
            is_default=item.is_default,
            member_count=item.member_count,
            membership_fingerprint=item.membership_fingerprint,
        )
        for order, item in enumerate(activation.universes)
    )
    preview_universes = tuple(item.definition for item in preview.payload.universes)
    if activation_universes != preview_universes:
        raise MarketIntelligencePublicationError("formal Activation differs from preview Universes")
    last = panel.source_sessions[-1]
    manifest_path = data_root / last.dataset_path / "manifest.json"
    preview_payload_path = preview.path / "market-regime-opportunity-map.json"
    preview_manifest_path = preview.path / "preview-manifest.json"
    source = MarketIntelligenceSourceBindingV1(
        eod=MarketIntelligenceEodSourceV1(
            dataset_path=last.dataset_path,
            session_date=last.session_date,
            record_count=last.record_count,
            content_fingerprint=last.content_fingerprint,
            business_key_fingerprint=panel.eod_business_key_fingerprint,
            parquet_sha256=last.parquet_sha256,
            manifest_sha256=file_sha256(manifest_path),
            identity_logical_fingerprint=panel.identity_logical_fingerprint,
            history_first_session=panel.sessions[0],
            history_last_session=panel.sessions[-1],
            history_session_count=len(panel.sessions),
            history_source_fingerprint=panel.history_source_fingerprint,
        ),
        activation=MarketIntelligenceActivationSourceV1(
            pointer_fingerprint=active_pointer_state_fingerprint(data_root),
            logical_fingerprint=activation.manifest.logical_content_fingerprint,
            universes=activation_universes,
        ),
        phase_logical_fingerprints=expected_phase,
        preview_payload_logical_fingerprint=preview.payload.logical_fingerprint,
        preview_payload_sha256=file_sha256(preview_payload_path),
        preview_manifest_sha256=file_sha256(preview_manifest_path),
        preview_generated_at=preview.manifest.generated_at,
    )
    return source, preview


def read_market_intelligence_release(
    path: Path, *, validate_sources: bool = False, data_root: Path | None = None
) -> CompletedMarketIntelligence:
    target = _safe_release_directory(path)
    actual = tuple(sorted(item.name for item in target.iterdir()))
    if actual != tuple(sorted(EXPECTED_FILES)):
        raise MarketIntelligencePublicationError(
            "Market Intelligence target file set is incomplete or has extras"
        )
    for item in target.iterdir():
        metadata = item.stat()
        mode = stat.S_IMODE(metadata.st_mode)
        if (
            item.is_symlink()
            or not item.is_file()
            or metadata.st_uid != os.geteuid()
            or mode not in {0o400, 0o444}
        ):
            raise MarketIntelligencePublicationError("unsafe Market Intelligence artifact custody")
    payload_raw = (target / MARKET_INTELLIGENCE_PAYLOAD_FILE).read_bytes()
    manifest_raw = (target / MARKET_INTELLIGENCE_MANIFEST_FILE).read_bytes()
    payload_json = _read_canonical_json(payload_raw, MARKET_INTELLIGENCE_PAYLOAD_FILE)
    manifest_json = _read_canonical_json(manifest_raw, MARKET_INTELLIGENCE_MANIFEST_FILE)
    contract_version = payload_json.get("contract_version")
    if contract_version == "market-intelligence-publication/1.0":
        payload = MarketIntelligencePayloadV1.model_validate(payload_json)
        manifest = MarketIntelligenceManifestV1.model_validate(manifest_json)
    elif contract_version == "market-intelligence-publication/1.1":
        payload = MarketIntelligencePayloadV1_1.model_validate(payload_json)
        manifest = MarketIntelligenceManifestV1_1.model_validate(manifest_json)
    else:
        raise MarketIntelligencePublicationError(
            "unsupported Market Intelligence publication contract"
        )
    if (
        len(payload_raw) != manifest.payload_bytes
        or hashlib.sha256(payload_raw).hexdigest() != manifest.payload_sha256
        or payload.logical_fingerprint != manifest.payload_logical_fingerprint
        or payload.analytics.logical_fingerprint != manifest.analytics_logical_fingerprint
        or payload.source != manifest.source
        or payload.review_deployment != manifest.review_deployment
    ):
        raise MarketIntelligencePublicationError("Market Intelligence payload custody mismatch")
    if isinstance(payload, MarketIntelligencePayloadV1_1) and (
        not isinstance(manifest, MarketIntelligenceManifestV1_1)
        or payload.candidate_source != manifest.candidate_source
        or payload.candidate_analytics.logical_fingerprint
        != manifest.candidate_analytics_logical_fingerprint
        or len(payload.candidate_analytics.universes[0].candidates)
        != manifest.candidate_primary_display_count
        or len(payload.candidate_analytics.universes[1].candidates)
        != manifest.candidate_secondary_display_count
    ):
        raise MarketIntelligencePublicationError("Market Intelligence Candidate custody mismatch")
    if canonical_fingerprint(
        payload.model_dump(
            mode="json", exclude={"publication_id", "generated_at", "logical_fingerprint"}
        )
    ) != payload.logical_fingerprint:
        raise MarketIntelligencePublicationError("Market Intelligence payload logical mismatch")
    if canonical_fingerprint(
        manifest.model_dump(
            mode="json", exclude={"generated_at", "manifest_logical_fingerprint"}
        )
    ) != manifest.manifest_logical_fingerprint:
        raise MarketIntelligencePublicationError("Market Intelligence manifest logical mismatch")
    if (
        manifest.publication_id != payload.publication_id
        or manifest.analysis_session != payload.analysis_session
        or manifest.generated_at != payload.generated_at
    ):
        raise MarketIntelligencePublicationError("Market Intelligence manifest identity mismatch")
    reference = _reference(target, manifest=manifest, payload=payload)
    if validate_sources:
        if data_root is None:
            raise MarketIntelligencePublicationError("data_root is required for source validation")
        _validate_completed_source_binding(data_root, payload.source, payload.analysis_session)
    return CompletedMarketIntelligence(target, manifest, payload, reference)


def read_market_intelligence_pointer(root: Path) -> MarketIntelligenceActivePointerV1 | None:
    safe_root = _validated_root(root)
    path = pointer_path(safe_root)
    _reject_symlink_chain(safe_root, path)
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise MarketIntelligencePublicationError("Market Intelligence pointer is unsafe")
    raw = path.read_bytes()
    parsed = _read_canonical_json(raw, path.name)
    pointer = MarketIntelligenceActivePointerV1.model_validate(parsed)
    if canonical_fingerprint(
        pointer.model_dump(mode="json", exclude={"pointer_content_fingerprint"})
    ) != pointer.pointer_content_fingerprint:
        raise MarketIntelligencePublicationError("Market Intelligence pointer fingerprint mismatch")
    return pointer


def consumer_state_fingerprint(root: Path) -> str:
    pointer = read_market_intelligence_pointer(root)
    if pointer is None:
        return canonical_fingerprint({"state": "absent"})
    return pointer.pointer_content_fingerprint


def read_active_market_intelligence(
    root: Path, *, validate_sources: bool = True
) -> CompletedMarketIntelligence:
    safe_root = _validated_root(root)
    pointer = read_market_intelligence_pointer(safe_root)
    if pointer is None:
        raise MarketIntelligenceUnavailable("no active Market Intelligence publication")
    active_path = safe_root / pointer.active.logical_path
    _reject_symlink_chain(safe_root, active_path)
    completed = read_market_intelligence_release(
        active_path, validate_sources=validate_sources, data_root=safe_root
    )
    if completed.reference != pointer.active:
        raise MarketIntelligencePublicationError("active Market Intelligence reference mismatch")
    return CompletedMarketIntelligence(
        completed.path, completed.manifest, completed.payload, completed.reference, pointer
    )


def build_approval_plan(
    *,
    root: Path,
    candidate: Path,
    preview_bundle_path: Path,
    phase1a_audit_path: Path,
    phase1b_audit_path: Path,
    phase2_audit_path: Path,
    candidate_audit_path: Path | None = None,
    expected_current_state_fingerprint: str,
    expected_latest_completed_session: date | None,
    actual_latest_completed_session: date,
    freshness_status: str,
    session_lag: int | None,
    created_at: datetime,
) -> MarketIntelligenceApprovalPlanV1 | MarketIntelligenceApprovalPlanV1_1:
    safe_root = _validated_root(root)
    completed = read_market_intelligence_release(candidate, validate_sources=False)
    source, preview = validate_source_binding(
        data_root=safe_root,
        analysis_session=completed.payload.analysis_session,
        preview_bundle_path=preview_bundle_path,
        phase1a_audit_path=phase1a_audit_path,
        phase1b_audit_path=phase1b_audit_path,
        phase2_audit_path=phase2_audit_path,
    )
    if completed.payload.source != source or completed.payload.analytics != preview.payload:
        raise MarketIntelligencePublicationError("candidate source binding changed")
    candidate_analytics = None
    if isinstance(completed.payload, MarketIntelligencePayloadV1_1):
        if candidate_audit_path is None:
            raise MarketIntelligencePublicationError("MI 1.1 plan requires Candidate audit path")
        candidate_analytics = build_opportunity_candidate_publication(candidate_audit_path)
        if (
            candidate_analytics != completed.payload.candidate_analytics
            or candidate_analytics.source != completed.payload.candidate_source
        ):
            raise MarketIntelligencePublicationError("Candidate audit binding changed")
    elif candidate_audit_path is not None:
        raise MarketIntelligencePublicationError("MI 1.0 plan cannot bind a Candidate audit")
    actual_inventory = inventory_fingerprint(safe_root)
    if actual_inventory != expected_current_state_fingerprint:
        raise MarketIntelligencePublicationConflict("Production inventory differs from expected state")
    target = target_path(
        safe_root, completed.payload.analysis_session, completed.payload.publication_id
    )
    pointer_file = pointer_path(safe_root)
    _reject_symlink_chain(safe_root, target)
    _reject_symlink_chain(safe_root, pointer_file)
    _reject_target_or_staging(target)
    files = file_references(candidate)
    current_pointer = read_market_intelligence_pointer(safe_root)
    current_consumer = consumer_state_fingerprint(safe_root)
    reference = _reference(
        candidate, manifest=completed.manifest, payload=completed.payload, logical_path=target.relative_to(safe_root).as_posix()
    )
    pointer = _pointer_for(
        active=reference,
        rollback=current_pointer.active if current_pointer is not None else None,
        switched_at=created_at,
    )
    pointer_raw = canonical_bytes(pointer.model_dump(mode="json"))
    activation_allowed = (
        freshness_status == "fresh"
        and session_lag == 0
        and expected_latest_completed_session == actual_latest_completed_session
    )
    review = completed.payload.review_deployment
    review_allowed = review is not None and (
        completed.payload.analysis_session == review.approved_as_of_session
        and actual_latest_completed_session == review.approved_as_of_session
        and expected_latest_completed_session == review.expected_latest_session
        and session_lag == review.expected_lag_sessions
        and freshness_status == "stale"
    )
    payload = {
        "plan_version": "1.1" if candidate_analytics is not None else "1.0",
        "operation": "market_intelligence_publication",
        "revision": MARKET_INTELLIGENCE_REVISION,
        "publication_id": completed.payload.publication_id,
        "created_at": created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "analysis_session": completed.payload.analysis_session.isoformat(),
        "data_root": str(safe_root),
        "preview_bundle_path": str(preview_bundle_path),
        "phase1a_audit_path": str(phase1a_audit_path),
        "phase1b_audit_path": str(phase1b_audit_path),
        "phase2_audit_path": str(phase2_audit_path),
        "source": source.model_dump(mode="json"),
        "expected_current_state_fingerprint": expected_current_state_fingerprint,
        "expected_consumer_state_fingerprint": current_consumer,
        "target_path": str(target),
        "target_logical_path": target.relative_to(safe_root).as_posix(),
        "pointer_path": str(pointer_file),
        "candidate_path": str(candidate),
        "files": [item.model_dump(mode="json") for item in files],
        "aggregate_sha256": aggregate_sha256(files),
        "payload_sha256": completed.manifest.payload_sha256,
        "payload_logical_fingerprint": completed.payload.logical_fingerprint,
        "analytics_logical_fingerprint": completed.payload.analytics.logical_fingerprint,
        "manifest_sha256": file_sha256(candidate / MARKET_INTELLIGENCE_MANIFEST_FILE),
        "planned_pointer_sha256": hashlib.sha256(pointer_raw).hexdigest(),
        "planned_pointer_fingerprint": pointer.pointer_content_fingerprint,
        "rollback_target": (
            current_pointer.active.model_dump(mode="json") if current_pointer is not None else None
        ),
        "rollback_authorization_digest": pointer.pointer_content_fingerprint,
        "expected_latest_completed_session": (
            expected_latest_completed_session.isoformat()
            if expected_latest_completed_session is not None
            else None
        ),
        "actual_latest_completed_session": actual_latest_completed_session.isoformat(),
        "freshness_status": freshness_status,
        "session_lag": session_lag,
        "activation_allowed": activation_allowed,
        "review_mode": review is not None,
        "normal_freshness": activation_allowed,
        "activation_allowed_by_review_authorization": review_allowed,
        "review_deployment": review.model_dump(mode="json") if review is not None else None,
        "inventory_change_file_count": 3,
        "inventory_change_bytes": sum(item.size for item in files) + len(pointer_raw),
        "recovery_boundary": (
            "A completed target left before pointer CAS is immutable and may only be linked "
            "with this exact approved plan through verify-then-link."
        ),
        "rollback_boundary": (
            "Rollback is separately approved by the active pointer digest and can only select "
            "the formally validated prior publication; the first publication has no in-dataset rollback."
        ),
    }
    if candidate_analytics is not None:
        payload.update(
            {
                "candidate_audit_path": str(candidate_audit_path),
                "candidate_source": candidate_analytics.source.model_dump(mode="json"),
                "candidate_analytics_logical_fingerprint": candidate_analytics.logical_fingerprint,
            }
        )
    plan_type = (
        MarketIntelligenceApprovalPlanV1_1
        if candidate_analytics is not None
        else MarketIntelligenceApprovalPlanV1
    )
    return plan_type.model_validate(
        {**payload, "plan_content_fingerprint": canonical_fingerprint(payload)}
    )


def validate_plan(
    plan: MarketIntelligenceApprovalPlanV1 | MarketIntelligenceApprovalPlanV1_1,
) -> CompletedMarketIntelligence:
    if canonical_fingerprint(
        plan.model_dump(mode="json", exclude={"plan_content_fingerprint"})
    ) != plan.plan_content_fingerprint:
        raise MarketIntelligencePublicationError("Market Intelligence plan fingerprint mismatch")
    candidate = Path(plan.candidate_path)
    completed = read_market_intelligence_release(candidate, validate_sources=False)
    files = file_references(candidate)
    if (
        files != plan.files
        or aggregate_sha256(files) != plan.aggregate_sha256
        or completed.manifest.payload_sha256 != plan.payload_sha256
        or completed.payload.logical_fingerprint != plan.payload_logical_fingerprint
        or completed.payload.analytics.logical_fingerprint != plan.analytics_logical_fingerprint
        or file_sha256(candidate / MARKET_INTELLIGENCE_MANIFEST_FILE) != plan.manifest_sha256
        or completed.payload.source != plan.source
        or completed.payload.review_deployment != plan.review_deployment
    ):
        raise MarketIntelligencePublicationError("Market Intelligence candidate changed")
    if isinstance(plan, MarketIntelligenceApprovalPlanV1_1):
        if (
            not isinstance(completed.payload, MarketIntelligencePayloadV1_1)
            or completed.payload.candidate_source != plan.candidate_source
            or completed.payload.candidate_analytics.logical_fingerprint
            != plan.candidate_analytics_logical_fingerprint
        ):
            raise MarketIntelligencePublicationError("Market Intelligence Candidate plan changed")
    elif isinstance(completed.payload, MarketIntelligencePayloadV1_1):
        raise MarketIntelligencePublicationError("MI 1.1 requires a plan 1.1 Candidate binding")
    return completed


def publish_and_activate(
    *,
    root: Path,
    plan: MarketIntelligenceApprovalPlanV1,
    expected_current_state_fingerprint: str,
    freshness_validator: Callable[[], None] | None = None,
    failpoint: str | None = None,
) -> CompletedMarketIntelligence:
    safe_root = _validated_root(root)
    validate_plan(plan)
    if expected_current_state_fingerprint != plan.expected_current_state_fingerprint:
        raise MarketIntelligencePublicationConflict("approved Production state differs from plan")
    if not (plan.activation_allowed or plan.activation_allowed_by_review_authorization):
        raise MarketIntelligencePublicationConflict("approval plan is not freshness-eligible")
    with _exclusive_lock(safe_root):
        if freshness_validator is not None:
            freshness_validator()
        if inventory_fingerprint(safe_root) != expected_current_state_fingerprint:
            raise MarketIntelligencePublicationConflict("Production inventory changed after approval")
        if consumer_state_fingerprint(safe_root) != plan.expected_consumer_state_fingerprint:
            raise MarketIntelligencePublicationConflict("Market Intelligence consumer changed")
        _validate_plan_sources(safe_root, plan)
        validate_plan(plan)
        target = _approved_target(safe_root, plan)
        _reject_target_or_staging(target)
        _mkdir_parents_durable(safe_root, target.parent)
        staging = target.parent / f".{target.name}.staging-{uuid4().hex}"
        try:
            staging.mkdir(mode=0o700)
            _fsync_directory(staging)
            _fsync_directory(staging.parent)
            _copy_approved_files(plan, staging)
            _fsync_directory(staging)
            staged = read_market_intelligence_release(staging, validate_sources=False)
            if staged.reference.aggregate_sha256 != plan.aggregate_sha256:
                raise MarketIntelligencePublicationError("staged Market Intelligence aggregate differs")
            if failpoint == "before_target_rename":
                raise MarketIntelligencePublicationError("injected failure before target rename")
            os.replace(staging, target)
            _fsync_directory(target.parent)
            completed = read_market_intelligence_release(target, validate_sources=False)
            if completed.reference != _planned_reference(plan):
                raise MarketIntelligencePublicationError("completed Market Intelligence target differs")
            if failpoint == "after_target_rename":
                raise MarketIntelligencePublicationError("injected failure after target rename")
            if consumer_state_fingerprint(safe_root) != plan.expected_consumer_state_fingerprint:
                raise MarketIntelligencePublicationConflict("Market Intelligence pointer CAS failed")
            _write_pointer(safe_root, _planned_pointer(plan))
            if failpoint == "after_pointer_write":
                raise MarketIntelligencePublicationError("injected failure after pointer write")
        except Exception:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise
    return read_active_market_intelligence(safe_root, validate_sources=True)


def verify_then_link(
    *,
    root: Path,
    plan: MarketIntelligenceApprovalPlanV1,
    expected_current_state_fingerprint: str,
    freshness_validator: Callable[[], None] | None = None,
) -> CompletedMarketIntelligence:
    safe_root = _validated_root(root)
    validate_plan(plan)
    if expected_current_state_fingerprint != plan.expected_current_state_fingerprint:
        raise MarketIntelligencePublicationConflict("approved Production state differs from plan")
    if not (plan.activation_allowed or plan.activation_allowed_by_review_authorization):
        raise MarketIntelligencePublicationConflict("approval plan is not freshness-eligible")
    with _exclusive_lock(safe_root):
        if freshness_validator is not None:
            freshness_validator()
        target = _approved_target(safe_root, plan)
        if inventory_fingerprint(safe_root, exclude_prefixes=(target,)) != expected_current_state_fingerprint:
            raise MarketIntelligencePublicationConflict("Production state outside recovered target changed")
        if consumer_state_fingerprint(safe_root) != plan.expected_consumer_state_fingerprint:
            raise MarketIntelligencePublicationConflict("Market Intelligence consumer changed")
        _validate_plan_sources(safe_root, plan)
        completed = read_market_intelligence_release(target, validate_sources=False)
        if completed.reference != _planned_reference(plan):
            raise MarketIntelligencePublicationError("completed inactive target differs from plan")
        _write_pointer(safe_root, _planned_pointer(plan))
    return read_active_market_intelligence(safe_root, validate_sources=True)


def rollback(
    *, root: Path, expected_active_pointer_fingerprint: str, apply: bool = False
) -> CompletedMarketIntelligence:
    safe_root = _validated_root(root)
    pointer = read_market_intelligence_pointer(safe_root)
    if pointer is None:
        raise MarketIntelligenceUnavailable("Market Intelligence pointer is absent")
    if pointer.pointer_content_fingerprint != expected_active_pointer_fingerprint:
        raise MarketIntelligencePublicationConflict("rollback approval digest mismatch")
    if pointer.rollback is None:
        raise MarketIntelligenceUnavailable(
            "no prior formally readable Market Intelligence publication exists"
        )
    target = _read_reference(safe_root, pointer.rollback, validate_sources=True)
    if not apply:
        return target
    with _exclusive_lock(safe_root):
        current = read_market_intelligence_pointer(safe_root)
        if (
            current is None
            or current.pointer_content_fingerprint != expected_active_pointer_fingerprint
            or current.rollback != pointer.rollback
        ):
            raise MarketIntelligencePublicationConflict("pointer changed after rollback approval")
        new_pointer = _pointer_for(
            active=current.rollback,
            rollback=current.active,
            switched_at=datetime.now(UTC),
        )
        _write_pointer(safe_root, new_pointer)
    return read_active_market_intelligence(safe_root, validate_sources=True)


def file_references(path: Path) -> tuple[MarketIntelligenceFileReferenceV1, ...]:
    target = _safe_release_directory(path)
    references = tuple(
        MarketIntelligenceFileReferenceV1(
            relative_path=item.name, size=item.stat().st_size, sha256=file_sha256(item)
        )
        for item in sorted(target.iterdir(), key=lambda value: value.name)
        if item.is_file()
    )
    if tuple(item.relative_path for item in references) != tuple(sorted(EXPECTED_FILES)):
        raise MarketIntelligencePublicationError("Market Intelligence file set differs")
    return references


def aggregate_sha256(files: tuple[MarketIntelligenceFileReferenceV1, ...]) -> str:
    return canonical_fingerprint([item.model_dump(mode="json") for item in files])


def _reference(
    path: Path,
    *,
    manifest: MarketIntelligenceManifestV1 | MarketIntelligenceManifestV1_1,
    payload: MarketIntelligencePayloadV1 | MarketIntelligencePayloadV1_1,
    logical_path: str | None = None,
) -> MarketIntelligenceTargetReferenceV1:
    files = file_references(path)
    derived_logical_path = logical_path
    if derived_logical_path is None:
        if "market-data" in path.parts:
            derived_logical_path = Path(*path.parts[path.parts.index("market-data") :]).as_posix()
        else:
            derived_logical_path = f"candidate/{path.name}"
    return MarketIntelligenceTargetReferenceV1(
        publication_id=manifest.publication_id,
        analysis_session=manifest.analysis_session,
        logical_path=derived_logical_path,
        payload_sha256=manifest.payload_sha256,
        payload_logical_fingerprint=payload.logical_fingerprint,
        analytics_logical_fingerprint=payload.analytics.logical_fingerprint,
        manifest_sha256=file_sha256(path / MARKET_INTELLIGENCE_MANIFEST_FILE),
        aggregate_sha256=aggregate_sha256(files),
        review_deployment=payload.review_deployment,
    )


def _validate_completed_source_binding(
    data_root: Path, source: MarketIntelligenceSourceBindingV1, analysis_session: date
) -> None:
    panel = load_formal_market_regime_panel(
        data_root=_validated_root(data_root), as_of_session=analysis_session
    )
    last = panel.source_sessions[-1]
    pointer = read_dashboard_universe_activation_pointer(data_root)
    if pointer is None:
        raise MarketIntelligencePublicationError("Activation pointer is absent")
    activation = read_active_dashboard_universe_activation(
        data_root, analysis_session=pointer.active.analysis_session, validate_sources=True
    )
    actual_universes = tuple(
        PreviewUniverseDefinitionV1(
            universe_id=item.universe_id,
            display_name=item.display_name,
            catalog_order=index,
            is_default=item.is_default,
            member_count=item.member_count,
            membership_fingerprint=item.membership_fingerprint,
        )
        for index, item in enumerate(activation.universes)
    )
    eod = source.eod
    if (
        eod.session_date != last.session_date
        or eod.record_count != last.record_count
        or eod.content_fingerprint != panel.eod_content_fingerprint
        or eod.business_key_fingerprint != panel.eod_business_key_fingerprint
        or eod.parquet_sha256 != last.parquet_sha256
        or eod.identity_logical_fingerprint != panel.identity_logical_fingerprint
        or eod.history_first_session != panel.sessions[0]
        or eod.history_last_session != panel.sessions[-1]
        or eod.history_session_count != len(panel.sessions)
        or eod.history_source_fingerprint != panel.history_source_fingerprint
        or eod.manifest_sha256 != file_sha256(data_root / eod.dataset_path / "manifest.json")
        or source.activation.pointer_fingerprint != active_pointer_state_fingerprint(data_root)
        or source.activation.logical_fingerprint != activation.manifest.logical_content_fingerprint
        or source.activation.universes != actual_universes
    ):
        raise MarketIntelligencePublicationError("formal Market Intelligence source changed")


def _validate_plan_sources(
    root: Path,
    plan: MarketIntelligenceApprovalPlanV1 | MarketIntelligenceApprovalPlanV1_1,
) -> None:
    actual, preview = validate_source_binding(
        data_root=root,
        analysis_session=plan.analysis_session,
        preview_bundle_path=Path(plan.preview_bundle_path),
        phase1a_audit_path=Path(plan.phase1a_audit_path),
        phase1b_audit_path=Path(plan.phase1b_audit_path),
        phase2_audit_path=Path(plan.phase2_audit_path),
    )
    if actual != plan.source or preview.payload.logical_fingerprint != plan.analytics_logical_fingerprint:
        raise MarketIntelligencePublicationConflict("approved source binding changed")
    if isinstance(plan, MarketIntelligenceApprovalPlanV1_1):
        candidate = build_opportunity_candidate_publication(Path(plan.candidate_audit_path))
        if (
            candidate.source != plan.candidate_source
            or candidate.logical_fingerprint != plan.candidate_analytics_logical_fingerprint
        ):
            raise MarketIntelligencePublicationConflict("approved Candidate audit binding changed")


def _read_reference(
    root: Path,
    reference: MarketIntelligenceTargetReferenceV1,
    *,
    validate_sources: bool,
) -> CompletedMarketIntelligence:
    path = root / reference.logical_path
    _reject_symlink_chain(root, path)
    completed = read_market_intelligence_release(
        path, validate_sources=validate_sources, data_root=root
    )
    if completed.reference != reference:
        raise MarketIntelligencePublicationError("Market Intelligence target reference mismatch")
    return completed


def _pointer_for(
    *,
    active: MarketIntelligenceTargetReferenceV1,
    rollback: MarketIntelligenceTargetReferenceV1 | None,
    switched_at: datetime,
) -> MarketIntelligenceActivePointerV1:
    body = {
        "pointer_version": "1.0",
        "status": "active",
        "active": active.model_dump(mode="json"),
        "rollback": rollback.model_dump(mode="json") if rollback is not None else None,
        "switched_at": switched_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    return MarketIntelligenceActivePointerV1.model_validate(
        {**body, "pointer_content_fingerprint": canonical_fingerprint(body)}
    )


def _planned_reference(plan: MarketIntelligenceApprovalPlanV1) -> MarketIntelligenceTargetReferenceV1:
    return MarketIntelligenceTargetReferenceV1(
        publication_id=plan.publication_id,
        analysis_session=plan.analysis_session,
        logical_path=plan.target_logical_path,
        payload_sha256=plan.payload_sha256,
        payload_logical_fingerprint=plan.payload_logical_fingerprint,
        analytics_logical_fingerprint=plan.analytics_logical_fingerprint,
        manifest_sha256=plan.manifest_sha256,
        aggregate_sha256=plan.aggregate_sha256,
        review_deployment=plan.review_deployment,
    )


def _planned_pointer(plan: MarketIntelligenceApprovalPlanV1) -> MarketIntelligenceActivePointerV1:
    pointer = _pointer_for(
        active=_planned_reference(plan),
        rollback=plan.rollback_target,
        switched_at=plan.created_at,
    )
    raw = canonical_bytes(pointer.model_dump(mode="json"))
    if (
        pointer.pointer_content_fingerprint != plan.planned_pointer_fingerprint
        or hashlib.sha256(raw).hexdigest() != plan.planned_pointer_sha256
    ):
        raise MarketIntelligencePublicationError("planned pointer artifact changed")
    return pointer


def _approved_target(root: Path, plan: MarketIntelligenceApprovalPlanV1) -> Path:
    expected = target_path(root, plan.analysis_session, plan.publication_id)
    if Path(plan.target_path) != expected or Path(plan.pointer_path) != pointer_path(root):
        raise MarketIntelligencePublicationError("approved Market Intelligence path differs")
    if plan.target_logical_path != expected.relative_to(root).as_posix():
        raise MarketIntelligencePublicationError("approved logical path differs")
    return expected


def _copy_approved_files(plan: MarketIntelligenceApprovalPlanV1, staging: Path) -> None:
    for item in plan.files:
        source = Path(plan.candidate_path) / item.relative_path
        destination = staging / item.relative_path
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o400,
        )
        try:
            with source.open("rb") as input_handle, os.fdopen(
                descriptor, "wb", closefd=False
            ) as output_handle:
                shutil.copyfileobj(input_handle, output_handle)
                output_handle.flush()
                os.fsync(output_handle.fileno())
        finally:
            os.close(descriptor)
        destination.chmod(0o444)


def _write_pointer(root: Path, pointer: MarketIntelligenceActivePointerV1) -> None:
    path = pointer_path(root)
    _mkdir_parents_durable(root, path.parent)
    _reject_symlink_chain(root, path)
    staging = path.parent / f".{path.name}.staging-{uuid4().hex}"
    try:
        _write_new(staging, canonical_bytes(pointer.model_dump(mode="json")), mode=0o444)
        os.replace(staging, path)
        _fsync_directory(path.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            staging.unlink()
        raise


def _reject_target_or_staging(target: Path) -> None:
    if target.exists() or target.is_symlink():
        raise MarketIntelligencePublicationConflict("Market Intelligence target already exists")
    if target.parent.exists() and tuple(target.parent.glob(f".{target.name}.staging-*")):
        raise MarketIntelligencePublicationConflict("Market Intelligence staging residue exists")


@contextmanager
def _exclusive_lock(root: Path):
    descriptor = os.open(root, os.O_RDONLY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise MarketIntelligencePublicationConflict(
                "Production publication lock is held"
            ) from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _safe_new_tmp_directory(path: Path) -> Path:
    if not path.is_absolute() or not path.is_relative_to(Path("/tmp")):
        raise MarketIntelligencePublicationError("candidate must be under /tmp")
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise MarketIntelligencePublicationError("symlink candidate path is rejected")
    if path.exists():
        raise MarketIntelligencePublicationError("candidate path already exists")
    parent = path.parent
    if not parent.exists() or parent.is_symlink() or not parent.is_dir():
        raise MarketIntelligencePublicationError("candidate parent must already exist")
    if not parent.resolve(strict=True).is_relative_to(Path("/tmp")):
        raise MarketIntelligencePublicationError("candidate parent escapes /tmp")
    return path


def _safe_release_directory(path: Path) -> Path:
    if path.is_symlink():
        raise MarketIntelligencePublicationError("symlink Market Intelligence target rejected")
    try:
        target = path.resolve(strict=True)
    except OSError as exc:
        raise MarketIntelligencePublicationError("Market Intelligence target unavailable") from exc
    if not target.is_dir():
        raise MarketIntelligencePublicationError("Market Intelligence target is not a directory")
    return target


def _read_canonical_json(raw: bytes, name: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise MarketIntelligencePublicationError(f"malformed Market Intelligence JSON: {name}") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != raw:
        raise MarketIntelligencePublicationError(f"non-canonical Market Intelligence JSON: {name}")
    return value


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except Exception as exc:
        raise MarketIntelligencePublicationError(f"malformed source JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise MarketIntelligencePublicationError(f"source JSON is not an object: {path.name}")
    return value


def _write_new(path: Path, raw: bytes, *, mode: int) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(mode)


def _normalize_nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list | tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_nfc(item)
            for key, item in value.items()
        }
    return value
