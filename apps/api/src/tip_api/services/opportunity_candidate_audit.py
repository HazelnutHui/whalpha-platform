"""Canonical, tmp-only Phase 5C opportunity-candidate audit artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
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
CANDIDATE_INCREMENTAL_ARTIFACT_FILES = (
    *CANDIDATE_ARTIFACT_FILES,
    CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT,
)
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
) -> dict[str, Any]:
    """Write a completed immutable audit and formally reread it before return."""

    target = validate_tmp_output_dir(output_dir)
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

    artifact_rows: list[dict[str, Any]] = []
    for name in artifact_files:
        payload = _with_logical_fingerprint(payloads[name])
        raw = _canonical_bytes(payload)
        _write_new(target / name, raw)
        artifact_rows.append(
            {
                "name": name,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "logical_content_fingerprint": payload["logical_content_fingerprint"],
            }
        )

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
    manifest = {
        **logical,
        "logical_content_fingerprint": _fingerprint(logical),
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "timings": dict(sorted(timings.items())),
        "peak_memory_kib": peak_memory_kib,
        "runtime_metrics": dict(sorted((runtime_metrics or {}).items())),
        "completion_status": "completed",
    }
    # The completion marker is deliberately created only after every artifact.
    _write_new(target / CANDIDATE_AUDIT_MANIFEST, _canonical_bytes(manifest))
    for path in target.iterdir():
        path.chmod(0o400)
    return read_opportunity_candidate_audit(target)


def read_opportunity_candidate_audit(output_dir: Path) -> dict[str, Any]:
    """Verify custody, canonical encoding, hashes, contracts, and Oracle gates."""

    manifest, _, _, _, _, _ = _read_opportunity_candidate_audit(output_dir)
    return manifest


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


def _read_opportunity_candidate_audit(output_dir: Path):
    """Internal verified reread that retains canonical artifact payloads."""

    target = _safe_completed_directory(output_dir)
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
        raw = (target / name).read_bytes()
        if len(raw) != row.get("bytes") or hashlib.sha256(raw).hexdigest() != row.get("sha256"):
            raise OpportunityCandidateAuditError(f"audit artifact custody mismatch: {name}")
        payload = _read_canonical_json(target / name)
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


def validate_tmp_output_dir(output_dir: Path) -> Path:
    if not output_dir.is_absolute() or output_dir.parent != Path("/tmp") or output_dir.name in {"", ".", ".."}:
        raise OpportunityCandidateAuditError("output directory must be a direct child of /tmp")
    current = Path("/")
    for part in output_dir.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise OpportunityCandidateAuditError("symlink output path is rejected")
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


def _safe_completed_directory(path: Path) -> Path:
    if path.is_symlink():
        raise OpportunityCandidateAuditError("symlink audit directory is rejected")
    target = path.resolve(strict=True)
    metadata = target.stat()
    if (
        not target.is_dir()
        or target.parent != Path("/tmp")
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
        return {str(key): _jsonable(item) for key, item in value.items()}
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
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise OpportunityCandidateAuditError(f"unsupported audit value type: {type(value).__name__}")


def _with_logical_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {**payload, "logical_content_fingerprint": _fingerprint(payload)}


def _canonical_bytes(value: object) -> bytes:
    normalized = _normalize_nfc(value)
    try:
        encoded = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OpportunityCandidateAuditError("audit value is not canonical-JSON serializable") from exc
    return (encoded + "\n").encode("utf-8")


def _normalize_nfc(value: object) -> object:
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


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise OpportunityCandidateAuditError(f"malformed audit JSON: {path.name}") from exc
    if raw != _canonical_bytes(value):
        raise OpportunityCandidateAuditError(f"non-canonical audit JSON: {path.name}")
    if not isinstance(value, dict):
        raise OpportunityCandidateAuditError("audit artifact must be an object")
    return value


def _write_new(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o400)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()


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
