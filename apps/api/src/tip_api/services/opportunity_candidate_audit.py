"""Canonical governed Phase 5C opportunity-candidate audit artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import stat
import time
import unicodedata
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import UUID

from pydantic import BaseModel

from tip_api.contracts.analytics.v1 import (
    CandidateRiskModeResultV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import (
    CANDIDATE_CALCULATION_VERSION,
    CANDIDATE_CONTRACT_VERSION,
    CANDIDATE_PARAMETER_FINGERPRINT,
    CANDIDATE_PARAMETER_SET_ID,
    CANDIDATE_STATE_CALCULATION_VERSION,
    CANDIDATE_STATE_CONTRACT_VERSION,
    CANDIDATE_STATE_PARAMETER_FINGERPRINT,
    CANDIDATE_STATE_PARAMETER_SET_ID,
    candidate_state_parameter_payload,
    parameter_payload,
)
from tip_api.services.market_regime_sources import MarketRegimeInputPanel
from tip_api.services.opportunity_candidate_oracle import CandidateOracleComparisonV1
from tip_api.services.opportunity_candidate_state import opportunity_candidate_state_history_fingerprint
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


CANDIDATE_ARTIFACT_FILES = (
    "source-input-manifest.json",
    "candidate-parameter-contract.json",
    "raw-candidate-facts.json",
    "cross-section-normalization-ledger.json",
    "candidate-score-history.json",
    "candidate-state-history.json",
    "candidate-transition-ledger.json",
    "current-risk-mode-results.json",
    "candidate-oracle-report.json",
)
CANDIDATE_AUDIT_MANIFEST = "candidate-audit-manifest.json"
CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT = "incremental-validation-ledger.json"
CANDIDATE_AUDIT_RESUME_CONTRACT = "opportunity-candidate-audit-resume/1.0"
CANDIDATE_AUDIT_RESUME_FILE = "candidate-audit-resume.json"
CANDIDATE_AUDIT_PENDING_MANIFEST = f"{CANDIDATE_AUDIT_MANIFEST}.partial"
CANDIDATE_FINALIZATION_FULL = "full_semantic_reread"
CANDIDATE_FINALIZATION_DAILY = "validated_write_plus_physical_custody"
CANDIDATE_FINALIZATION_SCOPES = {
    CANDIDATE_FINALIZATION_FULL,
    CANDIDATE_FINALIZATION_DAILY,
}
CANDIDATE_INCREMENTAL_ARTIFACT_FILES = (
    *CANDIDATE_ARTIFACT_FILES,
    CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT,
)
CANDIDATE_PERIODIC_BUSINESS_PROJECTIONS = {
    "source-input-manifest.json": ("panels",),
    "candidate-parameter-contract.json": (
        "candidate_parameter_contract",
        "candidate_state_parameter_contract",
    ),
    "raw-candidate-facts.json": ("records",),
    "cross-section-normalization-ledger.json": ("records",),
    "candidate-score-history.json": ("records",),
    "candidate-state-history.json": ("records",),
    "candidate-transition-ledger.json": ("records",),
    "current-risk-mode-results.json": ("records",),
}
REQUIRED_EQUIVALENCE_FLAGS = (
    "append_full_replay_match",
    "restart_replay_match",
    "future_prefix_stable",
)
REQUIRED_INCREMENTAL_EQUIVALENCE_FLAGS = (
    "prior_prefix_preserved",
    "incremental_restart_match",
    "future_prefix_stable",
)


@dataclass(frozen=True, slots=True)
class OpportunityCandidateAuditContents:
    """Formally verified cumulative Candidate inputs for a subsequent append."""

    manifest: Mapping[str, Any]
    source_panels: tuple[Mapping[str, Any], ...]
    candidate_batches: tuple[OpportunityCandidateBatchV1, ...]
    state_history: tuple[OpportunityCandidateStateRecordV1, ...]
    risk_results: tuple[CandidateRiskModeResultV1, ...]
    raw_facts: tuple[Mapping[str, Any], ...]
    normalization_ledger: tuple[Mapping[str, Any], ...]
    validation_ledger: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class OpportunityCandidatePublicationEvidence:
    """Hash-verified audit custody suitable for an already-built publication."""

    path: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class OpportunityCandidatePlanningEvidence:
    """Hash-verified completion and bounded lineage evidence for daily planning."""

    path: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str
    validation_ledger: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class OpportunityCandidateCurrentBatchEvidence:
    """Hash-verified current Candidate batches without historical row replay."""

    manifest: Mapping[str, Any]
    manifest_sha256: str
    source_panel: Mapping[str, Any]
    candidate_batches: tuple[OpportunityCandidateBatchV1, ...]


class OpportunityCandidateAuditError(RuntimeError):
    """Raised when a Candidate audit cannot preserve its custody boundary."""


def write_opportunity_candidate_audit(
    *,
    output_dir: Path,
    panels: Sequence[MarketRegimeInputPanel],
    candidate_batches: Sequence[OpportunityCandidateBatchV1],
    state_history: Sequence[OpportunityCandidateStateRecordV1],
    risk_results: Sequence[CandidateRiskModeResultV1],
    oracle_comparison: CandidateOracleComparisonV1,
    equivalence_flags: Mapping[str, bool],
    raw_facts: Mapping[Any, Any] | Sequence[Any],
    normalization_ledger: Mapping[Any, Any] | Sequence[Any],
    generated_at: datetime,
    timings: Mapping[str, str],
    peak_memory_kib: int,
    runtime_metrics: Mapping[str, int] | None = None,
    prior_source_panels: Sequence[Mapping[str, Any]] = (),
    incremental_validation: Mapping[str, Any] | None = None,
    work_dir: Path | None = None,
    defer_finalization: bool = False,
) -> dict[str, Any]:
    """Stream a completed immutable audit, optionally resuming verified artifact stages."""

    final_target = validate_tmp_output_dir(output_dir)
    resumable = work_dir is not None
    if defer_finalization and not resumable:
        raise OpportunityCandidateAuditError("deferred finalization requires a resumable work directory")
    if resumable:
        if final_target.exists():
            raise OpportunityCandidateAuditError("resumable output directory must not already exist")
        target = _prepare_candidate_audit_work_dir(work_dir, final_target=final_target)
    else:
        target = final_target
        target.mkdir(mode=0o700, parents=False, exist_ok=True)
        target.chmod(0o700)
        if any(target.iterdir()):
            raise OpportunityCandidateAuditError("existing non-empty output directory is rejected")

    current_panels = tuple(panels)
    if not current_panels:
        raise OpportunityCandidateAuditError("candidate audit requires at least one source panel")
    if tuple(item.as_of_session for item in current_panels) != tuple(
        sorted({item.as_of_session for item in current_panels})
    ):
        raise OpportunityCandidateAuditError("candidate source panels must be unique and ascending")
    incremental = incremental_validation is not None
    if bool(prior_source_panels) != incremental:
        raise OpportunityCandidateAuditError("incremental source prefix and validation ledger must be supplied together")
    source_panel_rows = tuple(_jsonable(item) for item in prior_source_panels) + tuple(
        _panel_source_row(item) for item in current_panels
    )
    if tuple(item.get("as_of_session") for item in source_panel_rows) != tuple(
        sorted({item.get("as_of_session") for item in source_panel_rows})
    ):
        raise OpportunityCandidateAuditError("candidate source panel ledger must be unique and ascending")
    current_panel = current_panels[-1]
    universe_order = {
        item.universe_id: index
        for index, item in enumerate(sorted(current_panel.universes, key=lambda row: row.catalog_order))
    }
    batches = tuple(
        sorted(
            candidate_batches,
            key=lambda item: (item.as_of_session, universe_order.get(item.universe_id, len(universe_order))),
        )
    )
    states = tuple(
        sorted(
            state_history,
            key=lambda item: (
                item.as_of_session,
                universe_order.get(item.universe_id, len(universe_order)),
                str(item.instrument_id),
            ),
        )
    )
    risk_mode_order = {"conservative": 0, "balanced": 1, "aggressive": 2}
    risks = tuple(
        sorted(
            risk_results,
            key=lambda item: (
                item.as_of_session,
                universe_order.get(item.universe_id, len(universe_order)),
                risk_mode_order.get(item.risk_mode.value, len(risk_mode_order)),
            ),
        )
    )
    flags = _validate_equivalence_flags(
        equivalence_flags,
        oracle_comparison,
        incremental=incremental,
    )
    _validate_inputs(
        source_panels=source_panel_rows,
        current_panel=current_panel,
        batches=batches,
        states=states,
        risks=risks,
        oracle=oracle_comparison,
    )

    batch_records = [item.model_dump(mode="json") for item in batches]
    state_records = [item.model_dump(mode="json") for item in states]
    risk_records = [item.model_dump(mode="json") for item in risks]
    stable_raw_facts = _stable_external_records(raw_facts)
    stable_normalization_ledger = _stable_external_records(normalization_ledger)
    history_fingerprint = _fingerprint(batch_records)
    state_fingerprint = opportunity_candidate_state_history_fingerprint(states)
    risk_fingerprint = _fingerprint(risk_records)
    oracle_record = _jsonable(oracle_comparison)
    oracle_fingerprint = str(oracle_record["oracle_fingerprint"])
    universe_ids = tuple(
        item.universe_id for item in sorted(current_panel.universes, key=lambda row: row.catalog_order)
    )
    base = {
        "schema_version": "1.1" if incremental else "1.0",
        "candidate_contract_version": CANDIDATE_CONTRACT_VERSION,
        "candidate_calculation_version": CANDIDATE_CALCULATION_VERSION,
        "candidate_parameter_set_id": CANDIDATE_PARAMETER_SET_ID,
        "candidate_parameter_fingerprint": CANDIDATE_PARAMETER_FINGERPRINT,
        "candidate_state_contract_version": CANDIDATE_STATE_CONTRACT_VERSION,
        "candidate_state_calculation_version": CANDIDATE_STATE_CALCULATION_VERSION,
        "candidate_state_parameter_set_id": CANDIDATE_STATE_PARAMETER_SET_ID,
        "candidate_state_parameter_fingerprint": CANDIDATE_STATE_PARAMETER_FINGERPRINT,
        "as_of_session": current_panel.as_of_session.isoformat(),
        "universe_ids": list(universe_ids),
    }
    if incremental:
        base["execution_mode"] = "verified_prior_incremental"
    payloads = {
        "source-input-manifest.json": {
            **base,
            "panels": list(source_panel_rows),
            "warnings": [
                "current_as_of_constituent_replay",
                "underlying_stock_opportunity_not_option_return",
                "audit_artifacts_not_production_publication",
            ],
        },
        "candidate-parameter-contract.json": {
            **base,
            "candidate_parameter_contract": parameter_payload(),
            "candidate_state_parameter_contract": candidate_state_parameter_payload(),
        },
        "raw-candidate-facts.json": {**base, "records": stable_raw_facts},
        "cross-section-normalization-ledger.json": {
            **base,
            "records": stable_normalization_ledger,
        },
        "candidate-score-history.json": {
            **base,
            "candidate_history_fingerprint": history_fingerprint,
            "records": batch_records,
        },
        "candidate-state-history.json": {
            **base,
            "candidate_state_history_fingerprint": state_fingerprint,
            "records": state_records,
        },
        "candidate-transition-ledger.json": {
            **base,
            "candidate_state_history_fingerprint": state_fingerprint,
            "records": [_transition_row(item) for item in states],
        },
        "current-risk-mode-results.json": {
            **base,
            "risk_results_fingerprint": risk_fingerprint,
            "records": risk_records,
        },
        "candidate-oracle-report.json": {**base, "record": oracle_record},
    }
    artifact_files = CANDIDATE_ARTIFACT_FILES
    if incremental:
        validation = _validate_incremental_validation_input(
            incremental_validation,
            source_panels=source_panel_rows,
            batches=batches,
            states=states,
            risks=risks,
            oracle=oracle_comparison,
            raw_facts=stable_raw_facts,
            normalization_ledger=stable_normalization_ledger,
        )
        payloads[CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT] = {
            **base,
            "record": validation,
        }
        artifact_files = CANDIDATE_INCREMENTAL_ARTIFACT_FILES

    prepared_payloads = {
        name: _with_logical_fingerprint(payloads[name])
        for name in artifact_files
    }
    resume_identity = _fingerprint(
        {
            "contract_version": CANDIDATE_AUDIT_RESUME_CONTRACT,
            "final_output_dir": str(final_target),
            "base": base,
            "artifacts": [
                {
                    "name": name,
                    "logical_content_fingerprint": prepared_payloads[name][
                        "logical_content_fingerprint"
                    ],
                }
                for name in artifact_files
            ],
            "candidate_batch_fingerprints": [item.logical_fingerprint for item in batches],
            "candidate_state_record_fingerprints": [item.logical_fingerprint for item in states],
            "risk_result_fingerprints": [item.logical_fingerprint for item in risks],
            "oracle_fingerprint": oracle_fingerprint,
            "equivalence_flags": flags,
            "prior_audit_logical_fingerprint": (
                None if not incremental else validation["prior_audit_logical_fingerprint"]
            ),
        }
    )
    resume_journal = None
    if resumable:
        resume_journal = _load_or_create_resume_journal(
            target,
            final_target=final_target,
            resume_identity=resume_identity,
            artifact_files=artifact_files,
        )

    writer_wall_started = time.monotonic()
    writer_cpu_started = time.process_time()
    artifact_rows: list[dict[str, Any]] = []
    reused_artifact_count = 0
    for name in artifact_files:
        payload = prepared_payloads[name]
        if resume_journal is None:
            byte_count, physical_sha256 = _write_canonical_new(target / name, payload)
            artifact = _artifact_row(
                name=name,
                byte_count=byte_count,
                physical_sha256=physical_sha256,
                logical_fingerprint=payload["logical_content_fingerprint"],
            )
        else:
            artifact, reused = _write_or_reuse_resumable_artifact(
                target,
                name=name,
                payload=payload,
                resume_journal=resume_journal,
                artifact_files=artifact_files,
            )
            reused_artifact_count += int(reused)
        artifact_rows.append(artifact)

    logical = {
        **base,
        "artifacts": artifact_rows,
        "candidate_history_fingerprint": history_fingerprint,
        "candidate_batch_fingerprints": [item.logical_fingerprint for item in batches],
        "candidate_state_history_fingerprint": state_fingerprint,
        "candidate_state_record_fingerprints": [item.logical_fingerprint for item in states],
        "risk_results_fingerprint": risk_fingerprint,
        "risk_result_fingerprints": [item.logical_fingerprint for item in risks],
        "oracle_fingerprint": oracle_fingerprint,
        "oracle_mismatch_count": oracle_comparison.mismatch_count,
        "shared_raw_fact_match": oracle_comparison.shared_raw_fact_match,
        "input_permutation_match": oracle_comparison.input_permutation_match,
        "equivalence_flags": flags,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    if incremental:
        logical["prior_audit_logical_fingerprint"] = validation["prior_audit_logical_fingerprint"]
        logical["prior_as_of_session"] = validation["prior_as_of_session"]
    writer_wall_seconds = time.monotonic() - writer_wall_started
    writer_cpu_seconds = time.process_time() - writer_cpu_started
    final_timings = {
        **timings,
        "audit_artifact_stream_write_wall_seconds": f"{writer_wall_seconds:.6f}",
        "audit_artifact_stream_write_cpu_seconds": f"{writer_cpu_seconds:.6f}",
    }
    final_runtime_metrics = {
        **(runtime_metrics or {}),
        "audit_artifact_stream_write_count": len(artifact_files) - reused_artifact_count,
        "audit_artifact_resume_reuse_count": reused_artifact_count,
        "audit_streaming_writer_enabled": 1,
        "audit_resumable_work_dir_enabled": int(resumable),
    }
    manifest = {
        **logical,
        "logical_content_fingerprint": _fingerprint(logical),
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "timings": dict(sorted(final_timings.items())),
        "peak_memory_kib": max(peak_memory_kib, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "runtime_metrics": dict(sorted(final_runtime_metrics.items())),
        "completion_status": "completed",
    }
    if resumable:
        _prepare_resumable_candidate_audit_manifest(
            target,
            manifest=manifest,
            resume_identity=resume_identity,
        )
        if defer_finalization:
            return manifest
        completed = finalize_resumable_candidate_audit(target, final_target)
        if completed is None:
            raise OpportunityCandidateAuditError("completed Candidate work directory did not finalize")
        return completed
    else:
        # The completion marker is deliberately created only after every artifact.
        _write_canonical_new(target / CANDIDATE_AUDIT_MANIFEST, manifest)
        for path in target.iterdir():
            path.chmod(0o400)
    return read_opportunity_candidate_audit(target)


def read_opportunity_candidate_audit(output_dir: Path) -> dict[str, Any]:
    """Verify custody, canonical encoding, hashes, contracts, and Oracle gates."""

    manifest, _, _, _, _, _ = _read_opportunity_candidate_audit(output_dir)
    return manifest


def read_opportunity_candidate_publication_evidence(
    output_dir: Path,
) -> OpportunityCandidatePublicationEvidence:
    """Verify immutable audit bytes without reparsing historical business rows.

    A publication must first have been built by the full audit reader. This
    lighter reread is only for proving that the exact approved artifact set has
    not changed between publication construction, planning, and Apply.
    """

    return _read_opportunity_candidate_completion_evidence(output_dir)


def _read_opportunity_candidate_completion_evidence(
    output_dir: Path,
    *,
    persistent_names: frozenset[str] | set[str] = frozenset(
        {"opportunity-candidate"}
    ),
) -> OpportunityCandidatePublicationEvidence:
    """Verify completed physical custody and manifest gates without history replay."""

    target = _safe_completed_directory(
        output_dir,
        persistent_names=persistent_names,
    )
    names = {item.name for item in target.iterdir()}
    if CANDIDATE_AUDIT_MANIFEST not in names:
        raise OpportunityCandidateAuditError("audit file set is incomplete or contains extras")
    manifest_path = target / CANDIDATE_AUDIT_MANIFEST
    manifest_sha256 = _file_sha256(manifest_path)
    manifest = _read_canonical_json(
        manifest_path,
        physical_sha256=manifest_sha256,
    )
    artifact_files = _artifact_files_for_manifest(manifest)
    expected = set(artifact_files) | {CANDIDATE_AUDIT_MANIFEST}
    if names != expected:
        raise OpportunityCandidateAuditError("audit file set is incomplete or contains extras")
    _validate_pending_manifest(
        manifest,
        artifact_files=artifact_files,
        artifacts=manifest.get("artifacts", ()),
    )
    for descriptor, name in zip(manifest["artifacts"], artifact_files, strict=True):
        path = target / name
        metadata = path.stat()
        if (
            descriptor.get("name") != name
            or path.is_symlink()
            or not path.is_file()
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size != descriptor.get("bytes")
            or _file_sha256(path) != descriptor.get("sha256")
        ):
            raise OpportunityCandidateAuditError(
                f"audit artifact custody mismatch: {name}"
            )
    _validate_parameter_contract(target, manifest)
    required_flags = (
        REQUIRED_INCREMENTAL_EQUIVALENCE_FLAGS
        if manifest.get("schema_version") == "1.1"
        else REQUIRED_EQUIVALENCE_FLAGS
    )
    flags = manifest.get("equivalence_flags")
    if (
        not isinstance(flags, Mapping)
        or any(flags.get(name) is not True for name in required_flags)
        or any(type(value) is not bool or value is not True for value in flags.values())
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("shared_raw_fact_match") is not True
        or manifest.get("input_permutation_match") is not True
    ):
        raise OpportunityCandidateAuditError(
            "Candidate publication evidence gates did not pass"
        )
    try:
        date.fromisoformat(str(manifest["as_of_session"]))
    except (KeyError, ValueError) as exc:
        raise OpportunityCandidateAuditError(
            "Candidate publication evidence session is malformed"
        ) from exc
    universe_ids = manifest.get("universe_ids")
    if (
        not isinstance(universe_ids, list)
        or len(universe_ids) != 2
        or len(set(universe_ids)) != 2
    ):
        raise OpportunityCandidateAuditError(
            "Candidate publication evidence Universe order is malformed"
        )
    return OpportunityCandidatePublicationEvidence(
        path=target,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
    )


def read_opportunity_candidate_planning_evidence(
    output_dir: Path,
) -> OpportunityCandidatePlanningEvidence:
    """Verify completed custody and only the lineage needed by the daily planner.

    Candidate calculation remains responsible for fully reconstructing a prior
    append input. Planning only proves that an already finalized audit is the
    same immutable, zero-Oracle artifact and, for incremental output, that its
    small validation ledger is bound to the completion manifest.
    """

    evidence = read_opportunity_candidate_publication_evidence(output_dir)
    manifest = evidence.manifest
    validation: Mapping[str, Any] | None = None
    if manifest.get("schema_version") == "1.1":
        descriptors = {
            item.get("name"): item
            for item in manifest.get("artifacts", ())
            if isinstance(item, Mapping)
        }
        descriptor = descriptors.get(CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT)
        if not isinstance(descriptor, Mapping):
            raise OpportunityCandidateAuditError(
                "Candidate planning validation descriptor is missing"
            )
        payload = _read_canonical_json(
            evidence.path / CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT,
            physical_sha256=str(descriptor.get("sha256")),
        )
        logical_fingerprint = payload.pop("logical_content_fingerprint", None)
        if (
            _fingerprint(payload) != logical_fingerprint
            or logical_fingerprint != descriptor.get("logical_content_fingerprint")
        ):
            raise OpportunityCandidateAuditError(
                "Candidate planning validation logical fingerprint mismatch"
            )
        base_keys = (
            "schema_version",
            "candidate_contract_version",
            "candidate_calculation_version",
            "candidate_parameter_set_id",
            "candidate_parameter_fingerprint",
            "candidate_state_contract_version",
            "candidate_state_calculation_version",
            "candidate_state_parameter_set_id",
            "candidate_state_parameter_fingerprint",
            "as_of_session",
            "universe_ids",
            "execution_mode",
        )
        if any(payload.get(key) != manifest.get(key) for key in base_keys):
            raise OpportunityCandidateAuditError(
                "Candidate planning validation contract differs from manifest"
            )
        record = payload.get("record")
        if not isinstance(record, Mapping):
            raise OpportunityCandidateAuditError(
                "Candidate planning validation ledger is malformed"
            )
        _validate_planning_validation_record(record, manifest=manifest)
        validation = record
    return OpportunityCandidatePlanningEvidence(
        path=evidence.path,
        manifest=manifest,
        manifest_sha256=evidence.manifest_sha256,
        validation_ledger=validation,
    )


def read_opportunity_candidate_audit_contents(output_dir: Path) -> OpportunityCandidateAuditContents:
    """Formally reread an audit and return the cumulative append inputs."""

    manifest, payloads, batches, states, risks, _ = _read_opportunity_candidate_audit(output_dir)
    raw = payloads["raw-candidate-facts.json"].get("records")
    normalization = payloads["cross-section-normalization-ledger.json"].get("records")
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise OpportunityCandidateAuditError("candidate raw-fact ledger is malformed")
    if not isinstance(normalization, list) or not all(isinstance(item, dict) for item in normalization):
        raise OpportunityCandidateAuditError("candidate normalization ledger is malformed")
    validation_payload = payloads.get(CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT)
    return OpportunityCandidateAuditContents(
        manifest=manifest,
        source_panels=tuple(payloads["source-input-manifest.json"]["panels"]),
        candidate_batches=batches,
        state_history=states,
        risk_results=risks,
        raw_facts=tuple(raw),
        normalization_ledger=tuple(normalization),
        validation_ledger=(None if validation_payload is None else validation_payload["record"]),
    )


def read_opportunity_candidate_incremental_source(
    output_dir: Path,
) -> OpportunityCandidateAuditContents:
    """Load a finalized prior audit for the next verified daily append.

    The audit was fully reconstructed before finalization.  At this later
    boundary, publication evidence first rehashes the immutable manifest and
    every exact artifact.  We can therefore parse the hash-verified bytes once
    without repeating canonical JSON serialization and every finalized
    historical fingerprint derivation for hundreds of megabytes.  Typed
    contracts, manifest record ledgers, session/Universe bindings, Oracle
    gates, and the finalized incremental lineage binding remain mandatory.
    """

    evidence = read_opportunity_candidate_publication_evidence(output_dir)
    manifest = evidence.manifest
    target = evidence.path
    artifact_files = _artifact_files_for_manifest(manifest)
    descriptors = {
        item.get("name"): item
        for item in manifest.get("artifacts", ())
        if isinstance(item, Mapping)
    }
    payloads: dict[str, dict[str, Any]] = {}
    for name in artifact_files:
        if name in {
            "candidate-parameter-contract.json",
            "candidate-transition-ledger.json",
        }:
            continue
        payload = _read_custodied_json(
            target / name,
            label=f"Candidate incremental source {name}",
        )
        descriptor = descriptors.get(name)
        embedded_fingerprint = payload.pop("logical_content_fingerprint", None)
        if (
            not isinstance(descriptor, Mapping)
            or embedded_fingerprint != descriptor.get("logical_content_fingerprint")
        ):
            raise OpportunityCandidateAuditError(
                f"Candidate incremental source fingerprint binding differs: {name}"
            )
        payloads[name] = payload

    base_keys = (
        "schema_version",
        "candidate_contract_version",
        "candidate_calculation_version",
        "candidate_parameter_set_id",
        "candidate_parameter_fingerprint",
        "candidate_state_contract_version",
        "candidate_state_calculation_version",
        "candidate_state_parameter_set_id",
        "candidate_state_parameter_fingerprint",
        "as_of_session",
        "universe_ids",
    )
    if manifest.get("schema_version") == "1.1":
        base_keys = (*base_keys, "execution_mode")
    if any(
        any(payload.get(key) != manifest.get(key) for key in base_keys)
        for payload in payloads.values()
    ):
        raise OpportunityCandidateAuditError(
            "Candidate incremental source contract differs from manifest"
        )

    source_panels = payloads["source-input-manifest.json"].get("panels")
    raw = payloads["raw-candidate-facts.json"].get("records")
    normalization = payloads["cross-section-normalization-ledger.json"].get(
        "records"
    )
    if (
        not isinstance(source_panels, list)
        or not source_panels
        or not all(isinstance(item, dict) for item in source_panels)
        or not isinstance(raw, list)
        or not all(isinstance(item, dict) for item in raw)
        or not isinstance(normalization, list)
        or not all(isinstance(item, dict) for item in normalization)
    ):
        raise OpportunityCandidateAuditError(
            "Candidate incremental source ledgers are malformed"
        )
    source_sessions = [item.get("as_of_session") for item in source_panels]
    if source_sessions != sorted(source_sessions) or len(source_sessions) != len(
        set(source_sessions)
    ):
        raise OpportunityCandidateAuditError(
            "Candidate incremental source panels are not unique and ascending"
        )
    if [
        item.get("universe_id") for item in source_panels[-1].get("universes", [])
    ] != manifest.get("universe_ids"):
        raise OpportunityCandidateAuditError(
            "Candidate incremental source Universe order differs"
        )

    batch_payload = payloads["candidate-score-history.json"]
    state_payload = payloads["candidate-state-history.json"]
    risk_payload = payloads["current-risk-mode-results.json"]
    batches = tuple(
        OpportunityCandidateBatchV1.model_validate(item)
        for item in batch_payload.get("records", ())
    )
    states = tuple(
        OpportunityCandidateStateRecordV1.model_validate(item)
        for item in state_payload.get("records", ())
    )
    risks = tuple(
        CandidateRiskModeResultV1.model_validate(item)
        for item in risk_payload.get("records", ())
    )
    oracle = _oracle_from_record(payloads["candidate-oracle-report.json"]["record"])

    _require_equal(
        batch_payload.get("candidate_history_fingerprint"),
        manifest.get("candidate_history_fingerprint"),
        "candidate incremental source artifact history",
    )
    _require_equal(
        state_payload.get("candidate_state_history_fingerprint"),
        manifest.get("candidate_state_history_fingerprint"),
        "candidate incremental source state artifact history",
    )
    _require_equal(
        risk_payload.get("risk_results_fingerprint"),
        manifest.get("risk_results_fingerprint"),
        "candidate incremental source risk artifact results",
    )
    _require_equal(
        [item.logical_fingerprint for item in batches],
        manifest.get("candidate_batch_fingerprints"),
        "candidate incremental source batch ledger",
    )
    _require_equal(
        [item.logical_fingerprint for item in states],
        manifest.get("candidate_state_record_fingerprints"),
        "candidate incremental source state ledger",
    )
    _require_equal(
        [item.logical_fingerprint for item in risks],
        manifest.get("risk_result_fingerprints"),
        "candidate incremental source risk ledger",
    )
    _require_equal(
        oracle.oracle_fingerprint,
        manifest.get("oracle_fingerprint"),
        "candidate incremental source Oracle",
    )
    _validate_reread_session_and_universe_bindings(
        manifest=manifest,
        source_panels=source_panels,
        batches=batches,
        states=states,
        risks=risks,
    )
    flags = manifest.get("equivalence_flags")
    required_flags = (
        REQUIRED_INCREMENTAL_EQUIVALENCE_FLAGS
        if manifest.get("schema_version") == "1.1"
        else REQUIRED_EQUIVALENCE_FLAGS
    )
    if (
        not isinstance(flags, dict)
        or any(flags.get(name) is not True for name in required_flags)
        or any(type(value) is not bool or value is not True for value in flags.values())
        or oracle.mismatch_count != 0
        or oracle.mismatches
        or not oracle.shared_raw_fact_match
        or not oracle.input_permutation_match
    ):
        raise OpportunityCandidateAuditError(
            "Candidate incremental source equivalence gates did not pass"
        )

    validation_payload = payloads.get(CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT)
    validation: Mapping[str, Any] | None = None
    if validation_payload is not None:
        validation = validation_payload.get("record")
        if not isinstance(validation, Mapping):
            raise OpportunityCandidateAuditError(
                "Candidate incremental source validation ledger is malformed"
            )
        _validate_planning_validation_record(validation, manifest=manifest)
        _require_equal(
            manifest.get("prior_audit_logical_fingerprint"),
            validation.get("prior_audit_logical_fingerprint"),
            "candidate incremental source prior audit",
        )
        _require_equal(
            manifest.get("prior_as_of_session"),
            validation.get("prior_as_of_session"),
            "candidate incremental source prior session",
        )

    return OpportunityCandidateAuditContents(
        manifest=manifest,
        source_panels=tuple(source_panels),
        candidate_batches=batches,
        state_history=states,
        risk_results=risks,
        raw_facts=tuple(raw),
        normalization_ledger=tuple(normalization),
        validation_ledger=validation,
    )


def _validate_planning_validation_record(
    record: Mapping[str, Any], *, manifest: Mapping[str, Any]
) -> None:
    if (
        record.get("validation_tier") not in {None, "daily"}
        or record.get("validation_scope")
        != "verified_prior_plus_current_session_oracle"
        or record.get("current_as_of_session") != manifest.get("as_of_session")
        or record.get("prior_as_of_session") != manifest.get("prior_as_of_session")
        or record.get("prior_audit_logical_fingerprint")
        != manifest.get("prior_audit_logical_fingerprint")
    ):
        raise OpportunityCandidateAuditError(
            "Candidate planning validation lineage is incompatible"
        )
    oracle_fingerprint = record.get("current_session_oracle_fingerprint")
    if (
        not isinstance(oracle_fingerprint, str)
        or len(oracle_fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in oracle_fingerprint)
    ):
        raise OpportunityCandidateAuditError(
            "Candidate planning validation Oracle fingerprint is malformed"
        )
    reuse_checks = record.get("reuse_checks")
    if not isinstance(reuse_checks, Mapping) or not reuse_checks or any(
        type(value) is not bool or value is not True for value in reuse_checks.values()
    ):
        raise OpportunityCandidateAuditError(
            "Candidate planning validation reuse gates did not pass"
        )
    segments = record.get("validation_segments")
    current_segments = (
        [
            item
            for item in segments
            if isinstance(item, Mapping)
            and item.get("session") == manifest.get("as_of_session")
        ]
        if isinstance(segments, list)
        else []
    )
    if (
        len(current_segments) != 1
        or current_segments[0].get("scope")
        != "current_session_independent_oracle"
        or current_segments[0].get("oracle_fingerprint") != oracle_fingerprint
        or current_segments[0].get("oracle_mismatch_count") != 0
    ):
        raise OpportunityCandidateAuditError(
            "Candidate planning validation current-session Oracle binding differs"
        )


def read_opportunity_candidate_current_batches(
    output_dir: Path,
    *,
    as_of_session: date,
) -> OpportunityCandidateCurrentBatchEvidence:
    """Read only the exact current batches after rehashing completed custody.

    This projection deliberately avoids reconstructing raw facts, state history,
    transitions, normalization rows, and risk results. It is suitable only for
    downstream work that binds the immutable completed Candidate audit.
    """

    evidence = read_opportunity_candidate_publication_evidence(output_dir)
    manifest = evidence.manifest
    if manifest.get("as_of_session") != as_of_session.isoformat():
        raise OpportunityCandidateAuditError(
            "current Candidate projection requires the audit as-of session"
        )
    target = evidence.path
    # Publication evidence immediately above already verifies the immutable
    # manifest, exact file set, owner/mode, byte counts, and physical hashes.
    # Re-encoding the 196 MB score history only to prove canonical bytes again
    # adds no new custody evidence at this downstream projection boundary.
    score_payload = _read_custodied_json(
        target / "candidate-score-history.json",
        label="Candidate score history",
    )
    source_payload = _read_custodied_json(
        target / "source-input-manifest.json",
        label="Candidate source manifest",
    )
    score_rows = score_payload.get("records")
    source_rows = source_payload.get("panels")
    if (
        not isinstance(score_rows, list)
        or not all(isinstance(item, dict) for item in score_rows)
        or not isinstance(source_rows, list)
        or not all(isinstance(item, dict) for item in source_rows)
    ):
        raise OpportunityCandidateAuditError(
            "current Candidate projection source payload is malformed"
        )
    batches = tuple(
        OpportunityCandidateBatchV1.model_validate(item)
        for item in score_rows
        if item.get("as_of_session") == as_of_session.isoformat()
    )
    universe_ids = tuple(manifest.get("universe_ids", ()))
    if (
        not batches
        or tuple(item.universe_id for item in batches) != universe_ids
        or tuple(manifest.get("candidate_batch_fingerprints", ())[-len(batches) :])
        != tuple(item.logical_fingerprint for item in batches)
    ):
        raise OpportunityCandidateAuditError(
            "current Candidate projection batch ledger differs"
        )
    _validate_typed_fingerprints(batches=batches, states=(), risks=())
    matching_panels = tuple(
        item
        for item in source_rows
        if item.get("as_of_session") == as_of_session.isoformat()
    )
    panel_universes = (
        matching_panels[0].get("universes", ()) if len(matching_panels) == 1 else ()
    )
    panel_universe_by_id = {
        item.get("universe_id"): item
        for item in panel_universes
        if isinstance(item, Mapping)
    }
    if len(matching_panels) != 1 or any(
        batch.history_source_fingerprint
        != matching_panels[0].get("history_source_fingerprint")
        or batch.membership_fingerprint
        != panel_universe_by_id.get(batch.universe_id, {}).get(
            "membership_fingerprint"
        )
        or batch.universe_member_count
        != panel_universe_by_id.get(batch.universe_id, {}).get("member_count")
        for batch in batches
    ):
        raise OpportunityCandidateAuditError(
            "current Candidate projection panel lineage differs"
        )
    return OpportunityCandidateCurrentBatchEvidence(
        manifest=manifest,
        manifest_sha256=evidence.manifest_sha256,
        source_panel=matching_panels[0],
        candidate_batches=batches,
    )


def read_opportunity_candidate_state_history(
    output_dir: Path,
) -> tuple[OpportunityCandidateStateRecordV1, ...]:
    """Read the cumulative typed state ledger after completed custody validation."""

    evidence = read_opportunity_candidate_publication_evidence(output_dir)
    payload = _read_custodied_json(
        evidence.path / "candidate-state-history.json",
        label="Candidate state history",
    )
    rows = payload.get("records")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        raise OpportunityCandidateAuditError(
            "Candidate state-history projection source is malformed"
        )
    states = tuple(OpportunityCandidateStateRecordV1.model_validate(item) for item in rows)
    manifest = evidence.manifest
    if (
        opportunity_candidate_state_history_fingerprint(states)
        != manifest.get("candidate_state_history_fingerprint")
        or [item.logical_fingerprint for item in states]
        != manifest.get("candidate_state_record_fingerprints")
    ):
        raise OpportunityCandidateAuditError(
            "Candidate state-history projection fingerprint differs"
        )
    _validate_typed_fingerprints(batches=(), states=states, risks=())
    return states


def read_opportunity_candidate_business_fingerprints(
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Formally reread an audit and fingerprint schema-neutral business projections."""

    manifest, payloads, _, _, _, _ = _read_opportunity_candidate_audit(output_dir)
    projections: dict[str, str] = {}
    for name, keys in CANDIDATE_PERIODIC_BUSINESS_PROJECTIONS.items():
        payload = payloads.get(name)
        if not isinstance(payload, Mapping) or any(key not in payload for key in keys):
            raise OpportunityCandidateAuditError(
                f"Candidate periodic business projection is malformed: {name}"
            )
        projections[name] = _fingerprint({key: payload[key] for key in keys})
    return manifest, projections


def finalize_resumable_candidate_audit(
    work_dir: Path,
    output_dir: Path,
    *,
    validation_scope: str = CANDIDATE_FINALIZATION_FULL,
) -> dict[str, Any] | None:
    """Finalize a fully written work directory without rerunning Candidate calculation."""

    if validation_scope not in CANDIDATE_FINALIZATION_SCOPES:
        raise OpportunityCandidateAuditError(
            "Candidate finalization validation scope is unsupported"
        )
    final_target = validate_tmp_output_dir(output_dir)
    if final_target.exists():
        raise OpportunityCandidateAuditError("resumable output directory must not already exist")
    if not work_dir.exists():
        return None
    target = _safe_candidate_audit_work_dir(work_dir, final_target=final_target)
    names = {item.name for item in target.iterdir()}
    if CANDIDATE_AUDIT_RESUME_FILE in names:
        journal = _read_resume_journal(target / CANDIDATE_AUDIT_RESUME_FILE)
        if journal.get("final_output_dir") != str(final_target):
            raise OpportunityCandidateAuditError("Candidate recovery journal output binding mismatch")
        if journal.get("next_artifact") is not None:
            return None
        if CANDIDATE_AUDIT_PENDING_MANIFEST not in names:
            return None
        completed = journal.get("completed_artifacts", ())
        artifact_files = tuple(journal.get("artifact_order", ()))
        if tuple(item.get("name") for item in completed) != artifact_files:
            raise OpportunityCandidateAuditError("completed Candidate recovery journal is malformed")
        if names != set(artifact_files) | {
            CANDIDATE_AUDIT_RESUME_FILE,
            CANDIDATE_AUDIT_PENDING_MANIFEST,
        }:
            raise OpportunityCandidateAuditError("completed Candidate work directory contains extras")
        pending_manifest = _read_canonical_json(target / CANDIDATE_AUDIT_PENDING_MANIFEST)
        _validate_pending_manifest(pending_manifest, artifact_files=artifact_files, artifacts=completed)
        (target / CANDIDATE_AUDIT_RESUME_FILE).unlink()
        _fsync_directory(target)
        os.rename(
            target / CANDIDATE_AUDIT_PENDING_MANIFEST,
            target / CANDIDATE_AUDIT_MANIFEST,
        )
        _fsync_directory(target)
        names = {item.name for item in target.iterdir()}
    if CANDIDATE_AUDIT_PENDING_MANIFEST in names:
        pending = _read_canonical_json(target / CANDIDATE_AUDIT_PENDING_MANIFEST)
        artifact_files = _artifact_files_for_manifest(pending)
        if names != set(artifact_files) | {CANDIDATE_AUDIT_PENDING_MANIFEST}:
            raise OpportunityCandidateAuditError("resumable pending audit file set is unsafe")
        _validate_pending_manifest(
            pending,
            artifact_files=artifact_files,
            artifacts=pending.get("artifacts", ()),
        )
        os.rename(
            target / CANDIDATE_AUDIT_PENDING_MANIFEST,
            target / CANDIDATE_AUDIT_MANIFEST,
        )
        _fsync_directory(target)
        names = {item.name for item in target.iterdir()}
    if CANDIDATE_AUDIT_MANIFEST not in names:
        if names:
            raise OpportunityCandidateAuditError("resumable work directory lost its recovery journal")
        return None
    if validation_scope == CANDIDATE_FINALIZATION_FULL:
        manifest, _, _, _, _, _ = _read_opportunity_candidate_audit(
            target,
            persistent_names={"candidate-work"},
        )
    else:
        manifest = _read_opportunity_candidate_completion_evidence(
            target,
            persistent_names={"candidate-work"},
        ).manifest
    os.rename(target, final_target)
    _fsync_directory(final_target.parent)
    return manifest


def _read_opportunity_candidate_audit(
    output_dir: Path,
    *,
    persistent_names: frozenset[str] | set[str] = frozenset(
        {"opportunity-candidate"}
    ),
):
    """Internal verified reread that retains canonical artifact payloads."""

    target = _safe_completed_directory(
        output_dir,
        persistent_names=persistent_names,
    )
    names = {item.name for item in target.iterdir()}
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise OpportunityCandidateAuditError("unsafe audit artifact")
    if CANDIDATE_AUDIT_MANIFEST not in names:
        raise OpportunityCandidateAuditError("audit file set is incomplete or contains extras")

    manifest = _read_canonical_json(target / CANDIDATE_AUDIT_MANIFEST)
    schema_version = manifest.get("schema_version")
    execution_mode = manifest.get("execution_mode")
    if schema_version == "1.0" and execution_mode is None:
        artifact_files = CANDIDATE_ARTIFACT_FILES
        incremental = False
    elif schema_version == "1.1" and execution_mode == "verified_prior_incremental":
        artifact_files = CANDIDATE_INCREMENTAL_ARTIFACT_FILES
        incremental = True
    else:
        raise OpportunityCandidateAuditError("unsupported Candidate audit schema or execution mode")
    expected = set(artifact_files) | {CANDIDATE_AUDIT_MANIFEST}
    if names != expected:
        raise OpportunityCandidateAuditError("audit file set is incomplete or contains extras")
    logical = {
        key: value
        for key, value in manifest.items()
        if key
        not in {
            "logical_content_fingerprint",
            "generated_at",
            "timings",
            "peak_memory_kib",
            "runtime_metrics",
            "completion_status",
        }
    }
    if manifest.get("completion_status") != "completed" or _fingerprint(logical) != manifest.get(
        "logical_content_fingerprint"
    ):
        raise OpportunityCandidateAuditError("audit manifest fingerprint mismatch")
    if tuple(item.get("name") for item in manifest.get("artifacts", ())) != artifact_files:
        raise OpportunityCandidateAuditError("audit artifact order mismatch")

    artifact_payloads: dict[str, dict[str, Any]] = {}
    for row in manifest["artifacts"]:
        name = row["name"]
        path = target / name
        physical_sha256 = _file_sha256(path)
        if path.stat().st_size != row.get("bytes") or physical_sha256 != row.get("sha256"):
            raise OpportunityCandidateAuditError(f"audit artifact custody mismatch: {name}")
        payload = _read_canonical_json(path, physical_sha256=physical_sha256)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if _fingerprint(payload) != fingerprint or fingerprint != row.get("logical_content_fingerprint"):
            raise OpportunityCandidateAuditError(f"audit artifact logical fingerprint mismatch: {name}")
        artifact_payloads[name] = payload

    base_keys = (
        "schema_version",
        "candidate_contract_version",
        "candidate_calculation_version",
        "candidate_parameter_set_id",
        "candidate_parameter_fingerprint",
        "candidate_state_contract_version",
        "candidate_state_calculation_version",
        "candidate_state_parameter_set_id",
        "candidate_state_parameter_fingerprint",
        "as_of_session",
        "universe_ids",
    )
    if incremental:
        base_keys = (*base_keys, "execution_mode")
    if any(
        any(payload.get(key) != manifest.get(key) for key in base_keys)
        for payload in artifact_payloads.values()
    ):
        raise OpportunityCandidateAuditError("artifact and manifest base contract mismatch")
    source_payload = artifact_payloads["source-input-manifest.json"]
    source_panels = source_payload.get("panels")
    if not isinstance(source_panels, list) or not source_panels:
        raise OpportunityCandidateAuditError("source panel custody ledger is missing")
    source_sessions = [item.get("as_of_session") for item in source_panels if isinstance(item, dict)]
    if source_sessions != sorted(source_sessions) or len(source_sessions) != len(set(source_sessions)):
        raise OpportunityCandidateAuditError("source panels must be unique and ascending")
    source_universe_ids = [item.get("universe_id") for item in source_panels[-1].get("universes", [])]
    if source_universe_ids != manifest.get("universe_ids"):
        raise OpportunityCandidateAuditError("source panel and manifest Universe order mismatch")

    _validate_parameter_contract(target, manifest)
    batch_payload = artifact_payloads["candidate-score-history.json"]
    batches = tuple(OpportunityCandidateBatchV1.model_validate(item) for item in batch_payload["records"])
    state_payload = artifact_payloads["candidate-state-history.json"]
    states = tuple(OpportunityCandidateStateRecordV1.model_validate(item) for item in state_payload["records"])
    risk_payload = artifact_payloads["current-risk-mode-results.json"]
    risks = tuple(CandidateRiskModeResultV1.model_validate(item) for item in risk_payload["records"])
    oracle_payload = artifact_payloads["candidate-oracle-report.json"]
    oracle = _oracle_from_record(oracle_payload["record"])

    batch_records = [item.model_dump(mode="json") for item in batches]
    state_records = [item.model_dump(mode="json") for item in states]
    risk_records = [item.model_dump(mode="json") for item in risks]
    _require_equal(_fingerprint(batch_records), manifest.get("candidate_history_fingerprint"), "candidate history")
    _require_equal(
        batch_payload.get("candidate_history_fingerprint"),
        manifest.get("candidate_history_fingerprint"),
        "candidate artifact history fingerprint",
    )
    _require_equal(
        opportunity_candidate_state_history_fingerprint(states),
        manifest.get("candidate_state_history_fingerprint"),
        "candidate state history",
    )
    _require_equal(
        state_payload.get("candidate_state_history_fingerprint"),
        manifest.get("candidate_state_history_fingerprint"),
        "candidate state artifact history fingerprint",
    )
    _require_equal(_fingerprint(risk_records), manifest.get("risk_results_fingerprint"), "risk results")
    _require_equal(
        risk_payload.get("risk_results_fingerprint"),
        manifest.get("risk_results_fingerprint"),
        "risk artifact results fingerprint",
    )
    _require_equal(
        [item.logical_fingerprint for item in batches],
        manifest.get("candidate_batch_fingerprints"),
        "candidate batch fingerprint ledger",
    )
    _require_equal(
        [item.logical_fingerprint for item in states],
        manifest.get("candidate_state_record_fingerprints"),
        "candidate state fingerprint ledger",
    )
    _require_equal(
        [item.logical_fingerprint for item in risks],
        manifest.get("risk_result_fingerprints"),
        "risk fingerprint ledger",
    )
    _require_equal(oracle.oracle_fingerprint, manifest.get("oracle_fingerprint"), "Oracle fingerprint")
    _validate_typed_fingerprints(batches=batches, states=states, risks=risks)
    _validate_reread_session_and_universe_bindings(
        manifest=manifest,
        source_panels=source_panels,
        batches=batches,
        states=states,
        risks=risks,
    )
    transition_payload = artifact_payloads["candidate-transition-ledger.json"]
    _require_equal(transition_payload.get("records"), [_transition_row(item) for item in states], "transition ledger")
    flags = manifest.get("equivalence_flags")
    required_flags = REQUIRED_INCREMENTAL_EQUIVALENCE_FLAGS if incremental else REQUIRED_EQUIVALENCE_FLAGS
    if (
        not isinstance(flags, dict)
        or any(flags.get(name) is not True for name in required_flags)
        or any(type(value) is not bool or value is not True for value in flags.values())
    ):
        raise OpportunityCandidateAuditError("Candidate replay equivalence gates did not pass")
    if "input_permutation_match" in flags and flags["input_permutation_match"] is not oracle.input_permutation_match:
        raise OpportunityCandidateAuditError("Candidate input-permutation gates disagree")
    if (
        oracle.mismatch_count != 0
        or oracle.mismatches
        or not oracle.shared_raw_fact_match
        or not oracle.input_permutation_match
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("shared_raw_fact_match") is not True
        or manifest.get("input_permutation_match") is not True
    ):
        raise OpportunityCandidateAuditError("Candidate Oracle equivalence gates did not pass")
    if incremental:
        validation = _validate_incremental_validation_input(
            artifact_payloads[CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT].get("record"),
            source_panels=tuple(source_panels),
            batches=batches,
            states=states,
            risks=risks,
            oracle=oracle,
            raw_facts=artifact_payloads["raw-candidate-facts.json"].get("records"),
            normalization_ledger=artifact_payloads["cross-section-normalization-ledger.json"].get("records"),
        )
        _require_equal(
            manifest.get("prior_audit_logical_fingerprint"),
            validation.get("prior_audit_logical_fingerprint"),
            "incremental prior audit fingerprint",
        )
        _require_equal(
            manifest.get("prior_as_of_session"),
            validation.get("prior_as_of_session"),
            "incremental prior as-of session",
        )
    return manifest, artifact_payloads, batches, states, risks, oracle


def _artifact_files_for_manifest(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    if manifest.get("schema_version") == "1.0" and manifest.get("execution_mode") is None:
        return CANDIDATE_ARTIFACT_FILES
    if (
        manifest.get("schema_version") == "1.1"
        and manifest.get("execution_mode") == "verified_prior_incremental"
    ):
        return CANDIDATE_INCREMENTAL_ARTIFACT_FILES
    raise OpportunityCandidateAuditError("unsupported resumable Candidate audit schema")


def _validate_pending_manifest(
    manifest: Mapping[str, Any],
    *,
    artifact_files: tuple[str, ...],
    artifacts: Sequence[Mapping[str, Any]],
) -> None:
    logical = {
        key: value
        for key, value in manifest.items()
        if key
        not in {
            "logical_content_fingerprint",
            "generated_at",
            "timings",
            "peak_memory_kib",
            "runtime_metrics",
            "completion_status",
        }
    }
    if (
        manifest.get("completion_status") != "completed"
        or _fingerprint(logical) != manifest.get("logical_content_fingerprint")
        or tuple(item.get("name") for item in manifest.get("artifacts", ())) != artifact_files
        or list(manifest.get("artifacts", ())) != [dict(item) for item in artifacts]
    ):
        raise OpportunityCandidateAuditError("pending Candidate audit manifest is malformed")


def _prepare_candidate_audit_work_dir(work_dir: Path | None, *, final_target: Path) -> Path:
    if work_dir is None:
        raise OpportunityCandidateAuditError("resumable Candidate audit requires a work directory")
    if work_dir == final_target:
        raise OpportunityCandidateAuditError("Candidate audit work and output directories must differ")
    if not work_dir.exists():
        _validate_direct_tmp_path(work_dir, label="work directory")
        work_dir.mkdir(mode=0o700, parents=False)
        work_dir.chmod(0o700)
    return _safe_candidate_audit_work_dir(work_dir, final_target=final_target)


def _safe_candidate_audit_work_dir(work_dir: Path, *, final_target: Path) -> Path:
    _validate_direct_tmp_path(work_dir, label="work directory")
    if work_dir == final_target or work_dir.is_symlink():
        raise OpportunityCandidateAuditError("Candidate audit work directory is unsafe")
    target = work_dir.resolve(strict=True)
    metadata = target.stat()
    if (
        not target.is_dir()
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise OpportunityCandidateAuditError("Candidate audit work directory custody mismatch")
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise OpportunityCandidateAuditError("unsafe resumable Candidate artifact")
    return target


def _load_or_create_resume_journal(
    target: Path,
    *,
    final_target: Path,
    resume_identity: str,
    artifact_files: tuple[str, ...],
) -> dict[str, Any]:
    journal_path = target / CANDIDATE_AUDIT_RESUME_FILE
    if not any(target.iterdir()):
        journal = _resume_journal_payload(
            final_target=final_target,
            resume_identity=resume_identity,
            artifact_files=artifact_files,
            completed_artifacts=(),
        )
        _write_canonical_new(journal_path, journal)
        _fsync_directory(target)
        return journal
    if not journal_path.is_file():
        raise OpportunityCandidateAuditError("resumable Candidate audit is missing its recovery journal")
    journal_pending = target / f"{CANDIDATE_AUDIT_RESUME_FILE}.partial"
    if journal_pending.exists():
        _unlink_verified_partial(journal_pending)
    journal = _read_resume_journal(journal_path)
    if (
        journal.get("contract_version") != CANDIDATE_AUDIT_RESUME_CONTRACT
        or journal.get("resume_identity") != resume_identity
        or journal.get("final_output_dir") != str(final_target)
        or tuple(journal.get("artifact_order", ())) != artifact_files
        or journal.get("status") != "writing_artifacts"
    ):
        raise OpportunityCandidateAuditError("Candidate recovery journal input binding mismatch")
    completed = journal.get("completed_artifacts")
    if not isinstance(completed, list) or tuple(item.get("name") for item in completed) != artifact_files[: len(completed)]:
        raise OpportunityCandidateAuditError("Candidate recovery journal artifact prefix is malformed")
    allowed = {CANDIDATE_AUDIT_RESUME_FILE, *(item["name"] for item in completed)}
    next_name = artifact_files[len(completed)] if len(completed) < len(artifact_files) else None
    if next_name is not None:
        allowed.update({next_name, f"{next_name}.partial"})
    names = {item.name for item in target.iterdir()}
    if not names <= allowed:
        raise OpportunityCandidateAuditError("resumable Candidate audit contains unexpected files")
    for item in completed:
        _validate_resumable_artifact(target / item["name"], item)
    return journal


def _read_resume_journal(path: Path) -> dict[str, Any]:
    journal = _read_canonical_json(path)
    logical_fingerprint = journal.pop("logical_content_fingerprint", None)
    if _fingerprint(journal) != logical_fingerprint:
        raise OpportunityCandidateAuditError("Candidate recovery journal fingerprint mismatch")
    journal["logical_content_fingerprint"] = logical_fingerprint
    if journal.get("contract_version") != CANDIDATE_AUDIT_RESUME_CONTRACT:
        raise OpportunityCandidateAuditError("Candidate recovery journal contract mismatch")
    return journal


def _resume_journal_payload(
    *,
    final_target: Path,
    resume_identity: str,
    artifact_files: tuple[str, ...],
    completed_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    logical = {
        "schema_version": "1.0",
        "contract_version": CANDIDATE_AUDIT_RESUME_CONTRACT,
        "resume_identity": resume_identity,
        "final_output_dir": str(final_target),
        "artifact_order": list(artifact_files),
        "completed_artifacts": [dict(item) for item in completed_artifacts],
        "next_artifact": (
            None if len(completed_artifacts) == len(artifact_files) else artifact_files[len(completed_artifacts)]
        ),
        "status": "writing_artifacts",
    }
    return {**logical, "logical_content_fingerprint": _fingerprint(logical)}


def _write_or_reuse_resumable_artifact(
    target: Path,
    *,
    name: str,
    payload: Mapping[str, Any],
    resume_journal: dict[str, Any],
    artifact_files: tuple[str, ...],
) -> tuple[dict[str, Any], bool]:
    completed = resume_journal["completed_artifacts"]
    expected_logical = payload["logical_content_fingerprint"]
    if len(completed) < artifact_files.index(name):
        raise OpportunityCandidateAuditError("Candidate recovery journal skipped an artifact stage")
    if len(completed) > artifact_files.index(name):
        artifact = dict(completed[artifact_files.index(name)])
        if artifact.get("logical_content_fingerprint") != expected_logical:
            raise OpportunityCandidateAuditError("resumed Candidate artifact logical identity changed")
        _validate_resumable_artifact(target / name, artifact)
        return artifact, True

    path = target / name
    partial = target / f"{name}.partial"
    reused = False
    if path.exists():
        artifact = _artifact_row_from_existing(path, name=name, expected_logical=expected_logical)
        reused = True
        if partial.exists():
            _unlink_verified_partial(partial)
    else:
        if partial.exists():
            try:
                artifact = _artifact_row_from_existing(
                    partial,
                    name=name,
                    expected_logical=expected_logical,
                )
                os.rename(partial, path)
                _fsync_directory(target)
                reused = True
            except OpportunityCandidateAuditError:
                _unlink_verified_partial(partial)
        if not path.exists():
            byte_count, physical_sha256 = _write_canonical_new(partial, payload)
            artifact = _artifact_row(
                name=name,
                byte_count=byte_count,
                physical_sha256=physical_sha256,
                logical_fingerprint=expected_logical,
            )
            os.rename(partial, path)
            _fsync_directory(target)
    completed.append(artifact)
    updated = _resume_journal_payload(
        final_target=Path(resume_journal["final_output_dir"]),
        resume_identity=resume_journal["resume_identity"],
        artifact_files=artifact_files,
        completed_artifacts=completed,
    )
    _replace_resume_journal(target, updated)
    resume_journal.clear()
    resume_journal.update(updated)
    return artifact, reused


def _artifact_row_from_existing(path: Path, *, name: str, expected_logical: str) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.geteuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
    ):
        raise OpportunityCandidateAuditError("resumable Candidate artifact custody mismatch")
    physical_sha256 = _file_sha256(path)
    payload = _read_canonical_json(path, physical_sha256=physical_sha256)
    logical_fingerprint = payload.pop("logical_content_fingerprint", None)
    if _fingerprint(payload) != logical_fingerprint or logical_fingerprint != expected_logical:
        raise OpportunityCandidateAuditError("resumable Candidate artifact logical fingerprint mismatch")
    return _artifact_row(
        name=name,
        byte_count=path.stat().st_size,
        physical_sha256=physical_sha256,
        logical_fingerprint=logical_fingerprint,
    )


def _validate_resumable_artifact(path: Path, artifact: Mapping[str, Any]) -> None:
    actual = _artifact_row_from_existing(
        path,
        name=str(artifact.get("name")),
        expected_logical=str(artifact.get("logical_content_fingerprint")),
    )
    if actual != artifact:
        raise OpportunityCandidateAuditError("resumable Candidate artifact descriptor mismatch")


def _artifact_row(
    *, name: str, byte_count: int, physical_sha256: str, logical_fingerprint: str
) -> dict[str, Any]:
    return {
        "name": name,
        "bytes": byte_count,
        "sha256": physical_sha256,
        "logical_content_fingerprint": logical_fingerprint,
    }


def _replace_resume_journal(target: Path, journal: Mapping[str, Any]) -> None:
    path = target / CANDIDATE_AUDIT_RESUME_FILE
    pending = target / f"{CANDIDATE_AUDIT_RESUME_FILE}.partial"
    if pending.exists():
        _unlink_verified_partial(pending)
    _write_canonical_new(pending, journal)
    os.replace(pending, path)
    _fsync_directory(target)


def _unlink_verified_partial(path: Path) -> None:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_uid != os.geteuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o400
        or not path.name.endswith(".partial")
    ):
        raise OpportunityCandidateAuditError("unsafe Candidate partial artifact")
    path.unlink()


def _prepare_resumable_candidate_audit_manifest(
    target: Path,
    *,
    manifest: Mapping[str, Any],
    resume_identity: str,
) -> None:
    journal = _read_resume_journal(target / CANDIDATE_AUDIT_RESUME_FILE)
    if journal.get("resume_identity") != resume_identity or journal.get("next_artifact") is not None:
        raise OpportunityCandidateAuditError("Candidate recovery journal is not ready for completion")
    pending = target / CANDIDATE_AUDIT_PENDING_MANIFEST
    if pending.exists():
        _unlink_verified_partial(pending)
    _write_canonical_new(pending, manifest)
    _fsync_directory(target)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_direct_tmp_path(path: Path, *, label: str) -> None:
    try:
        validate_offline_artifact_location(
            path,
            persistent_names={"candidate-work"},
        )
    except OfflineArtifactCustodyError as exc:
        raise OpportunityCandidateAuditError(
            f"{label} custody differs: {exc}"
        ) from exc


def validate_tmp_output_dir(output_dir: Path) -> Path:
    try:
        validate_offline_artifact_location(
            output_dir,
            persistent_names={"opportunity-candidate"},
        )
    except OfflineArtifactCustodyError as exc:
        raise OpportunityCandidateAuditError(
            f"output directory custody differs: {exc}"
        ) from exc
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise OpportunityCandidateAuditError("existing output path is unsafe or non-empty")
        metadata = output_dir.stat()
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise OpportunityCandidateAuditError("existing output directory custody mismatch")
    return output_dir


def _validate_inputs(*, source_panels, current_panel, batches, states, risks, oracle) -> None:
    if not batches:
        raise OpportunityCandidateAuditError("candidate audit requires at least one typed batch")
    panel_sessions = tuple(date.fromisoformat(item["as_of_session"]) for item in source_panels)
    if panel_sessions != tuple(sorted(set(panel_sessions))):
        raise OpportunityCandidateAuditError("candidate source panels must be unique and ascending")
    universe_ids = tuple(
        item.universe_id for item in sorted(current_panel.universes, key=lambda row: row.catalog_order)
    )
    if len(universe_ids) != len(set(universe_ids)):
        raise OpportunityCandidateAuditError("candidate source panel Universes must be unique")
    if any(
        tuple(item.get("universe_id") for item in panel.get("universes", ())) != universe_ids
        for panel in source_panels
    ):
        raise OpportunityCandidateAuditError("candidate source panel Universe catalogs do not match")
    if current_panel.as_of_session != max(item.as_of_session for item in batches):
        raise OpportunityCandidateAuditError("candidate audit panel and batch as-of sessions do not match")
    batches_by_session: dict[date, list[OpportunityCandidateBatchV1]] = {}
    for batch in batches:
        batches_by_session.setdefault(batch.as_of_session, []).append(batch)
    if tuple(batches_by_session) != panel_sessions:
        raise OpportunityCandidateAuditError("every candidate batch session requires exactly one source panel")
    if any(tuple(item.universe_id for item in rows) != universe_ids for rows in batches_by_session.values()):
        raise OpportunityCandidateAuditError("every candidate session requires one Primary-first Universe batch set")
    if any(item.parameter_fingerprint != CANDIDATE_PARAMETER_FINGERPRINT for item in batches):
        raise OpportunityCandidateAuditError("candidate batch parameter fingerprint mismatch")
    if any(item.parameter_fingerprint != CANDIDATE_STATE_PARAMETER_FINGERPRINT for item in states):
        raise OpportunityCandidateAuditError("candidate state parameter fingerprint mismatch")
    if any(item.parameter_fingerprint != CANDIDATE_PARAMETER_FINGERPRINT for item in risks):
        raise OpportunityCandidateAuditError("candidate risk parameter fingerprint mismatch")
    current_batch_universes = {
        item.universe_id for item in batches if item.as_of_session == current_panel.as_of_session
    }
    risk_keys = tuple((item.universe_id, item.risk_mode.value) for item in risks)
    if len(risk_keys) != len(set(risk_keys)) or any(
        item.as_of_session != current_panel.as_of_session or item.universe_id not in current_batch_universes
        for item in risks
    ):
        raise OpportunityCandidateAuditError("risk results must uniquely belong to current as-of candidate batches")
    if any(item.as_of_session > current_panel.as_of_session for item in states):
        raise OpportunityCandidateAuditError("candidate state history cannot be later than the current as-of session")
    if any(item.universe_id not in universe_ids for item in states):
        raise OpportunityCandidateAuditError("candidate state history cites an unknown Universe")
    if oracle.mismatch_count or oracle.mismatches or not oracle.shared_raw_fact_match or not oracle.input_permutation_match:
        raise OpportunityCandidateAuditError("Candidate Oracle equivalence gates must pass before audit write")
    if len(oracle.oracle_fingerprint) != 64 or any(character not in "0123456789abcdef" for character in oracle.oracle_fingerprint):
        raise OpportunityCandidateAuditError("Candidate Oracle fingerprint is malformed")


def _validate_equivalence_flags(
    flags: Mapping[str, bool], oracle: CandidateOracleComparisonV1, *, incremental: bool = False
) -> dict[str, bool]:
    required = REQUIRED_INCREMENTAL_EQUIVALENCE_FLAGS if incremental else REQUIRED_EQUIVALENCE_FLAGS
    if not isinstance(flags, Mapping) or any(name not in flags for name in required):
        raise OpportunityCandidateAuditError("required Candidate replay equivalence flags are missing")
    if any(type(value) is not bool or value is not True for value in flags.values()):
        raise OpportunityCandidateAuditError("Candidate replay equivalence gates must all pass")
    if "input_permutation_match" in flags and flags["input_permutation_match"] is not oracle.input_permutation_match:
        raise OpportunityCandidateAuditError("Candidate input-permutation gates disagree")
    return dict(sorted(flags.items()))


def _validate_incremental_validation_input(
    value: Mapping[str, Any] | None,
    *,
    source_panels: Sequence[Mapping[str, Any]],
    batches: Sequence[OpportunityCandidateBatchV1],
    states: Sequence[OpportunityCandidateStateRecordV1],
    risks: Sequence[CandidateRiskModeResultV1],
    oracle: CandidateOracleComparisonV1,
    raw_facts: Sequence[Mapping[str, Any]],
    normalization_ledger: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OpportunityCandidateAuditError("incremental validation ledger is missing")
    record = _jsonable(value)
    required_strings = (
        "prior_audit_logical_fingerprint",
        "prior_as_of_session",
        "current_as_of_session",
        "prior_candidate_history_fingerprint",
        "prior_candidate_state_history_fingerprint",
        "prior_raw_facts_records_fingerprint",
        "prior_normalization_records_fingerprint",
        "current_session_oracle_fingerprint",
    )
    if any(not isinstance(record.get(name), str) or not record[name] for name in required_strings):
        raise OpportunityCandidateAuditError("incremental validation ledger has missing bindings")
    fingerprint_fields = (
        "prior_audit_logical_fingerprint",
        "prior_candidate_history_fingerprint",
        "prior_candidate_state_history_fingerprint",
        "prior_raw_facts_records_fingerprint",
        "prior_normalization_records_fingerprint",
        "current_session_oracle_fingerprint",
    )
    if any(len(record[name]) != 64 or any(character not in "0123456789abcdef" for character in record[name]) for name in fingerprint_fields):
        raise OpportunityCandidateAuditError("incremental validation ledger has malformed fingerprints")
    if record.get("validation_scope") != "verified_prior_plus_current_session_oracle":
        raise OpportunityCandidateAuditError("incremental validation scope is unsupported")
    if record.get("validation_tier") not in {None, "daily"}:
        raise OpportunityCandidateAuditError("incremental Candidate validation tier is unsupported")
    cache_status = record.get("current_panel_stage_cache_status")
    cache_fingerprint = record.get("current_panel_stage_logical_fingerprint")
    if cache_status is not None or cache_fingerprint is not None:
        if cache_status not in {"disabled", "populated", "hit"}:
            raise OpportunityCandidateAuditError("incremental panel-stage cache status is invalid")
        if cache_status == "disabled":
            if cache_fingerprint is not None:
                raise OpportunityCandidateAuditError("disabled panel-stage cache has a fingerprint")
        elif (
            not isinstance(cache_fingerprint, str)
            or len(cache_fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in cache_fingerprint)
        ):
            raise OpportunityCandidateAuditError("incremental panel-stage cache fingerprint is malformed")
    reuse_checks = record.get("reuse_checks")
    if not isinstance(reuse_checks, Mapping) or not reuse_checks or any(
        type(result) is not bool or result is not True for result in reuse_checks.values()
    ):
        raise OpportunityCandidateAuditError("incremental reuse checks did not pass")
    prior_session = date.fromisoformat(record["prior_as_of_session"])
    current_session = date.fromisoformat(record["current_as_of_session"])
    panel_sessions = tuple(date.fromisoformat(item["as_of_session"]) for item in source_panels)
    if len(panel_sessions) < 2 or panel_sessions[-2:] != (prior_session, current_session):
        raise OpportunityCandidateAuditError("incremental source panel boundary mismatch")
    batch_sessions = tuple(sorted({item.as_of_session for item in batches}))
    if batch_sessions != panel_sessions:
        raise OpportunityCandidateAuditError("incremental Candidate session ledger mismatch")
    if oracle.oracle_fingerprint != record["current_session_oracle_fingerprint"]:
        raise OpportunityCandidateAuditError("incremental current-session Oracle binding mismatch")
    if any(item.as_of_session != current_session for item in risks):
        raise OpportunityCandidateAuditError("incremental risk results are not current-session results")
    prior_batches = tuple(item for item in batches if item.as_of_session <= prior_session)
    prior_states = tuple(item for item in states if item.as_of_session <= prior_session)
    if _fingerprint([item.model_dump(mode="json") for item in prior_batches]) != record[
        "prior_candidate_history_fingerprint"
    ]:
        raise OpportunityCandidateAuditError("incremental Candidate prefix fingerprint mismatch")
    if opportunity_candidate_state_history_fingerprint(prior_states) != record[
        "prior_candidate_state_history_fingerprint"
    ]:
        raise OpportunityCandidateAuditError("incremental state prefix fingerprint mismatch")
    if not isinstance(raw_facts, Sequence) or not isinstance(normalization_ledger, Sequence):
        raise OpportunityCandidateAuditError("incremental external ledgers are malformed")
    prior_raw = tuple(item for item in raw_facts if date.fromisoformat(item["as_of_session"]) <= prior_session)
    prior_normalization = tuple(
        item for item in normalization_ledger if date.fromisoformat(item["as_of_session"]) <= prior_session
    )
    if _fingerprint(prior_raw) != record["prior_raw_facts_records_fingerprint"]:
        raise OpportunityCandidateAuditError("incremental raw-fact prefix fingerprint mismatch")
    if _fingerprint(prior_normalization) != record["prior_normalization_records_fingerprint"]:
        raise OpportunityCandidateAuditError("incremental normalization prefix fingerprint mismatch")
    return record


def _validate_parameter_contract(target: Path, manifest: Mapping[str, Any]) -> None:
    payload = _read_canonical_json(target / "candidate-parameter-contract.json")
    if payload.get("candidate_parameter_contract") != _jsonable(parameter_payload()):
        raise OpportunityCandidateAuditError("candidate parameter contract mismatch")
    if payload.get("candidate_state_parameter_contract") != _jsonable(candidate_state_parameter_payload()):
        raise OpportunityCandidateAuditError("candidate state parameter contract mismatch")
    if manifest.get("candidate_parameter_fingerprint") != CANDIDATE_PARAMETER_FINGERPRINT:
        raise OpportunityCandidateAuditError("candidate manifest parameter fingerprint mismatch")
    if manifest.get("candidate_state_parameter_fingerprint") != CANDIDATE_STATE_PARAMETER_FINGERPRINT:
        raise OpportunityCandidateAuditError("candidate state manifest parameter fingerprint mismatch")


def _validate_typed_fingerprints(*, batches, states, risks) -> None:
    for batch in batches:
        if batch.parameter_fingerprint != CANDIDATE_PARAMETER_FINGERPRINT:
            raise OpportunityCandidateAuditError("candidate batch parameter fingerprint mismatch")
        for candidate in batch.candidates:
            if candidate.parameter_fingerprint != CANDIDATE_PARAMETER_FINGERPRINT:
                raise OpportunityCandidateAuditError("candidate score parameter fingerprint mismatch")
            expected = _candidate_model_fingerprint(
                candidate.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
            _require_equal(expected, candidate.logical_fingerprint, "candidate score logical fingerprint")
        expected = _candidate_model_fingerprint(batch.model_dump(mode="json", exclude={"logical_fingerprint"}))
        _require_equal(expected, batch.logical_fingerprint, "candidate batch logical fingerprint")
    for state_record in states:
        if state_record.parameter_fingerprint != CANDIDATE_STATE_PARAMETER_FINGERPRINT:
            raise OpportunityCandidateAuditError("candidate state parameter fingerprint mismatch")
        expected = _state_model_fingerprint(
            state_record.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        _require_equal(expected, state_record.logical_fingerprint, "candidate state logical fingerprint")
    for risk in risks:
        if risk.parameter_fingerprint != CANDIDATE_PARAMETER_FINGERPRINT:
            raise OpportunityCandidateAuditError("candidate risk parameter fingerprint mismatch")
        expected = _candidate_model_fingerprint(risk.model_dump(mode="json", exclude={"logical_fingerprint"}))
        _require_equal(expected, risk.logical_fingerprint, "candidate risk logical fingerprint")


def _validate_reread_session_and_universe_bindings(*, manifest, source_panels, batches, states, risks) -> None:
    universe_ids = tuple(manifest.get("universe_ids", ()))
    universe_order = {universe_id: index for index, universe_id in enumerate(universe_ids)}
    risk_mode_order = {"conservative": 0, "balanced": 1, "aggressive": 2}
    panel_sessions = tuple(item.get("as_of_session") for item in source_panels)
    if manifest.get("as_of_session") != panel_sessions[-1]:
        raise OpportunityCandidateAuditError("current source panel and manifest as-of sessions do not match")
    for panel in source_panels:
        if [item.get("universe_id") for item in panel.get("universes", ())] != list(universe_ids):
            raise OpportunityCandidateAuditError("historical source panel Universe order mismatch")
        history_sessions = panel.get("history_sessions")
        source_sessions = panel.get("source_sessions")
        if (
            not isinstance(history_sessions, list)
            or not history_sessions
            or history_sessions != sorted(history_sessions)
            or len(history_sessions) != len(set(history_sessions))
            or not isinstance(source_sessions, list)
            or [item.get("session_date") for item in source_sessions] != history_sessions
            or panel.get("as_of_session") != history_sessions[-1]
        ):
            raise OpportunityCandidateAuditError("historical source panel session custody mismatch")
    batch_groups: dict[str, list[OpportunityCandidateBatchV1]] = {}
    for batch in batches:
        batch_groups.setdefault(batch.as_of_session.isoformat(), []).append(batch)
    if tuple(batch_groups) != panel_sessions:
        raise OpportunityCandidateAuditError("candidate score sessions and source panels do not match")
    panel_by_session = {item["as_of_session"]: item for item in source_panels}
    for session, rows in batch_groups.items():
        if tuple(item.universe_id for item in rows) != universe_ids:
            raise OpportunityCandidateAuditError("candidate batch history is not Primary-first and complete")
        membership = {
            item["universe_id"]: item["membership_fingerprint"]
            for item in panel_by_session[session]["universes"]
        }
        if any(item.membership_fingerprint != membership[item.universe_id] for item in rows):
            raise OpportunityCandidateAuditError("candidate batch and source panel membership mismatch")
        if any(
            item.history_source_fingerprint != panel_by_session[session]["history_source_fingerprint"]
            for item in rows
        ):
            raise OpportunityCandidateAuditError("candidate batch and source history fingerprint mismatch")
    if tuple(states) != tuple(
        sorted(
            states,
            key=lambda item: (
                item.as_of_session,
                universe_order.get(item.universe_id, len(universe_order)),
                str(item.instrument_id),
            ),
        )
    ):
        raise OpportunityCandidateAuditError("candidate state history order mismatch")
    current_session = date.fromisoformat(manifest["as_of_session"])
    if any(item.as_of_session > current_session for item in states):
        raise OpportunityCandidateAuditError("candidate state history exceeds current as-of session")
    current_universes = {item.universe_id for item in batch_groups[manifest["as_of_session"]]}
    risk_keys = tuple((item.universe_id, item.risk_mode.value) for item in risks)
    if (
        tuple(risks)
        != tuple(
            sorted(
                risks,
                key=lambda item: (
                    item.as_of_session,
                    universe_order.get(item.universe_id, len(universe_order)),
                    risk_mode_order.get(item.risk_mode.value, len(risk_mode_order)),
                ),
            )
        )
        or len(risk_keys) != len(set(risk_keys))
        or any(item.as_of_session != current_session or item.universe_id not in current_universes for item in risks)
    ):
        raise OpportunityCandidateAuditError("risk results are not uniquely bound to current candidate batches")


def _panel_source_row(panel: MarketRegimeInputPanel) -> dict[str, Any]:
    return {
        "as_of_session": panel.as_of_session.isoformat(),
        "calendar_id": panel.calendar_id,
        "calendar_version": panel.calendar_version,
        "history_sessions": [item.isoformat() for item in panel.sessions],
        "history_source_fingerprint": panel.history_source_fingerprint,
        "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
        "identity_logical_fingerprint": panel.identity_logical_fingerprint,
        "eod_content_fingerprint": panel.eod_content_fingerprint,
        "eod_business_key_fingerprint": panel.eod_business_key_fingerprint,
        "source_sessions": [
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
        ],
        "universes": [
            {
                "universe_id": item.universe_id,
                "display_name": item.display_name,
                "catalog_order": item.catalog_order,
                "is_default": item.is_default,
                "member_count": len(item.member_ids),
                "membership_fingerprint": item.membership_fingerprint,
            }
            for item in sorted(panel.universes, key=lambda row: row.catalog_order)
        ],
    }


def _oracle_from_record(record: Mapping[str, Any]) -> CandidateOracleComparisonV1:
    try:
        integer_fields = (
            "candidate_count",
            "risk_result_count",
            "state_record_count",
            "raw_fact_count",
            "mismatch_count",
        )
        if any(type(record[name]) is not int or record[name] < 0 for name in integer_fields):
            raise ValueError("Oracle counts must be nonnegative integers")
        if type(record["shared_raw_fact_match"]) is not bool or type(record["input_permutation_match"]) is not bool:
            raise ValueError("Oracle gates must be booleans")
        if not isinstance(record["mismatches"], list) or not all(
            isinstance(item, str) for item in record["mismatches"]
        ):
            raise ValueError("Oracle mismatches must be a string array")
        fingerprint = record["oracle_fingerprint"]
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in fingerprint
        ):
            raise ValueError("Oracle fingerprint is malformed")
        return CandidateOracleComparisonV1(
            candidate_count=record["candidate_count"],
            risk_result_count=record["risk_result_count"],
            state_record_count=record["state_record_count"],
            raw_fact_count=record["raw_fact_count"],
            mismatch_count=record["mismatch_count"],
            mismatches=tuple(record["mismatches"]),
            shared_raw_fact_match=record["shared_raw_fact_match"],
            input_permutation_match=record["input_permutation_match"],
            oracle_fingerprint=fingerprint,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OpportunityCandidateAuditError("malformed Candidate Oracle report") from exc


def _transition_row(item: OpportunityCandidateStateRecordV1) -> dict[str, Any]:
    return {
        "as_of_session": item.as_of_session.isoformat(),
        "universe_id": item.universe_id,
        "instrument_id": str(item.instrument_id),
        "ticker": item.ticker,
        "prior_stage": None if item.prior_stage is None else item.prior_stage.value,
        "proposed_stage": None if item.proposed_stage is None else item.proposed_stage.value,
        "final_stage": None if item.final_stage is None else item.final_stage.value,
        "transition_status": item.transition_status.value,
        "transition_rule_id": item.transition_rule_id,
        "pending_target_stage": None if item.pending_target_stage is None else item.pending_target_stage.value,
        "confirmation_count_before": item.confirmation_count_before,
        "confirmation_count_after": item.confirmation_count_after,
        "required_confirmation_sessions": item.required_confirmation_sessions,
        "stage_confirmation_count_before": item.stage_confirmation_count_before,
        "stage_confirmation_count_after": item.stage_confirmation_count_after,
        "state_availability": item.state_availability.value,
        "source_state_record_fingerprint": item.logical_fingerprint,
    }


def _safe_completed_directory(
    path: Path,
    *,
    persistent_names: frozenset[str] | set[str] = frozenset(
        {"opportunity-candidate"}
    ),
) -> Path:
    try:
        validate_offline_artifact_location(
            path,
            persistent_names=persistent_names,
        )
    except OfflineArtifactCustodyError as exc:
        raise OpportunityCandidateAuditError(
            f"audit directory custody mismatch: {exc}"
        ) from exc
    target = path.resolve(strict=True)
    metadata = target.stat()
    if (
        not target.is_dir()
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise OpportunityCandidateAuditError("audit directory custody mismatch")
    return target


def _stable_external_records(value: Mapping[Any, Any] | Sequence[Any]) -> Any:
    normalized = _jsonable(value)
    if isinstance(normalized, list):
        return sorted(normalized, key=_canonical_bytes)
    return normalized


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): _jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OpportunityCandidateAuditError("non-finite decimal cannot enter an audit artifact")
        return str(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    raise OpportunityCandidateAuditError(f"unsupported audit value type: {type(value).__name__}")


def _with_logical_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {**payload, "logical_content_fingerprint": _fingerprint(payload)}


def _canonical_bytes(value: object) -> bytes:
    try:
        return b"".join(
            _canonical_byte_chunks(_normalize_nfc(value), trailing_newline=True)
        )
    except (TypeError, ValueError) as exc:
        raise OpportunityCandidateAuditError("audit value is not canonical-JSON serializable") from exc


def _canonical_byte_chunks(value: object, *, trailing_newline: bool = False):
    """Yield canonical JSON without materializing a second complete payload."""

    _require_nfc(value)
    encoder = json.JSONEncoder(
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    for chunk in encoder.iterencode(value):
        yield chunk.encode("utf-8")
    if trailing_newline:
        yield b"\n"


def _require_nfc(value: object) -> None:
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            if not unicodedata.is_normalized("NFC", item):
                raise OpportunityCandidateAuditError("audit strings must use canonical NFC")
        elif isinstance(item, Mapping):
            for key, nested in item.items():
                if not isinstance(key, str) or not unicodedata.is_normalized("NFC", key):
                    raise OpportunityCandidateAuditError("audit object keys must be canonical NFC strings")
                stack.append(nested)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)


def _normalize_nfc(value: object) -> object:
    """Retain the model-fingerprint normalization contract used by state rows."""

    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_nfc(item)
            for key, item in value.items()
        }
    return value


def _read_canonical_json(path: Path, *, physical_sha256: str | None = None) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except Exception as exc:
        raise OpportunityCandidateAuditError(f"malformed audit JSON: {path.name}") from exc
    actual_sha256 = physical_sha256 or _file_sha256(path)
    if actual_sha256 != _canonical_sha256(value, trailing_newline=True):
        raise OpportunityCandidateAuditError(f"non-canonical audit JSON: {path.name}")
    if not isinstance(value, dict):
        raise OpportunityCandidateAuditError("audit artifact must be an object")
    return value


def _read_custodied_json(path: Path, *, label: str) -> dict[str, Any]:
    """Parse bytes whose exact physical hash was just verified by the caller."""

    try:
        value = json.loads(path.read_bytes())
    except Exception as exc:
        raise OpportunityCandidateAuditError(f"{label} is malformed") from exc
    if not isinstance(value, dict):
        raise OpportunityCandidateAuditError(f"{label} must be an object")
    return value


def _write_canonical_new(path: Path, value: object) -> tuple[int, str]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o400)
    digest = hashlib.sha256()
    byte_count = 0
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            buffer = bytearray()
            for chunk in _canonical_byte_chunks(value, trailing_newline=True):
                byte_count += len(chunk)
                buffer.extend(chunk)
                if len(buffer) >= 1024 * 1024:
                    handle.write(buffer)
                    digest.update(buffer)
                    buffer.clear()
            if buffer:
                handle.write(buffer)
                digest.update(buffer)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    return byte_count, digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: object, *, trailing_newline: bool) -> str:
    digest = hashlib.sha256()
    try:
        buffer = bytearray()
        for chunk in _canonical_byte_chunks(value, trailing_newline=trailing_newline):
            buffer.extend(chunk)
            if len(buffer) >= 1024 * 1024:
                digest.update(buffer)
                buffer.clear()
        if buffer:
            digest.update(buffer)
    except (TypeError, ValueError) as exc:
        raise OpportunityCandidateAuditError("audit value is not canonical-JSON serializable") from exc
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return _canonical_sha256(value, trailing_newline=False)


def _candidate_model_fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _state_model_fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            _normalize_nfc(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise OpportunityCandidateAuditError(f"{label} mismatch")
