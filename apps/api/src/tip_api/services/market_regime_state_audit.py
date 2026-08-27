"""Canonical tmp-only Phase 1b state artifacts and formal offline reader."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from tip_api.contracts.analytics.v1 import (
    MarketRegimeStateExplanationV1,
    MarketRegimeStateRecordV1,
    StateOracleComparisonV1,
)
from tip_api.parameters.market_regime.state_v1_0_1 import (
    FROZEN_PHASE1A_AUDIT_FINGERPRINT,
    PHASE1A_CALCULATION_VERSION,
    PHASE1A_PARAMETER_FINGERPRINT,
    PHASE1A_PARAMETER_SET_ID,
    STATE_CALCULATION_VERSION,
    STATE_CONTRACT_VERSION,
    STATE_PARAMETER_FINGERPRINT,
    STATE_PARAMETER_SET_ID,
    state_parameter_payload,
)
from tip_api.parameters.market_regime.state_v1_0_0 import (
    STATE_CALCULATION_VERSION as LEGACY_STATE_CALCULATION_VERSION,
    STATE_PARAMETER_FINGERPRINT as LEGACY_STATE_PARAMETER_FINGERPRINT,
    state_parameter_payload as legacy_state_parameter_payload,
)
from tip_api.services.market_regime_state import state_history_fingerprint
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


STATE_ARTIFACT_FILES = (
    "source-input-manifest.json",
    "state-parameter-contract.json",
    "state-history.json",
    "current-state-summary.json",
    "transition-ledger.json",
    "state-explanation-ledger.json",
    "state-oracle-report.json",
)
STATE_AUDIT_MANIFEST = "state-audit-manifest.json"
STATE_INCREMENTAL_VALIDATION_ARTIFACT = "incremental-validation-ledger.json"
STATE_INCREMENTAL_ARTIFACT_FILES = (*STATE_ARTIFACT_FILES, STATE_INCREMENTAL_VALIDATION_ARTIFACT)


class MarketRegimeStateAuditError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MarketRegimeStateAuditContents:
    """Formally verified cumulative Phase 1b inputs for a later append."""

    manifest: Mapping[str, Any]
    source_manifest: Mapping[str, Any]
    histories: Mapping[str, tuple[MarketRegimeStateRecordV1, ...]]
    explanations: Mapping[str, tuple[MarketRegimeStateExplanationV1, ...]]
    oracle_reports: tuple[StateOracleComparisonV1, ...]
    validation_ledger: Mapping[str, Any] | None


def write_market_regime_state_audit(
    *,
    output_dir: Path,
    panel: MarketRegimeInputPanel | None,
    phase1a_audit_manifest: Mapping[str, Any],
    histories: Mapping[str, Sequence[MarketRegimeStateRecordV1]],
    explanations: Mapping[str, Sequence[MarketRegimeStateExplanationV1]],
    oracle_reports: Sequence[StateOracleComparisonV1],
    first_calculable_session: object,
    generated_at: datetime,
    timings: Mapping[str, str],
    peak_memory_kib: int,
    phase1a_input_manifest: Mapping[str, Any] | None = None,
    incremental_validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target = _validate_tmp_output_dir(output_dir)
    target.mkdir(mode=0o700, parents=False, exist_ok=True)
    if any(target.iterdir()):
        raise MarketRegimeStateAuditError("existing non-empty output directory is rejected")
    universe_ids = tuple(histories)
    if not universe_ids or tuple(explanations) != universe_ids:
        raise MarketRegimeStateAuditError("state audit requires aligned ordered Universe histories")
    incremental = incremental_validation is not None
    if incremental == (phase1a_input_manifest is None):
        raise MarketRegimeStateAuditError(
            "incremental validation and Phase 1a input manifest must be supplied together"
        )
    if incremental and panel is not None:
        raise MarketRegimeStateAuditError("incremental state audit must consume the verified Phase 1a audit")
    if not incremental and panel is None:
        raise MarketRegimeStateAuditError("cold state audit requires the formal history panel")
    as_of_session = (
        date.fromisoformat(str(phase1a_input_manifest["as_of_session"]))
        if incremental
        else panel.as_of_session  # type: ignore[union-attr]
    )
    base = {
        "schema_version": "1.1" if incremental else "1.0",
        "contract_version": STATE_CONTRACT_VERSION,
        "calculation_version": STATE_CALCULATION_VERSION,
        "state_parameter_set_id": STATE_PARAMETER_SET_ID,
        "state_parameter_fingerprint": STATE_PARAMETER_FINGERPRINT,
        "phase1a_calculation_version": PHASE1A_CALCULATION_VERSION,
        "phase1a_parameter_set_id": PHASE1A_PARAMETER_SET_ID,
        "phase1a_parameter_fingerprint": PHASE1A_PARAMETER_FINGERPRINT,
        "as_of_session": as_of_session.isoformat(),
        "first_calculable_session": first_calculable_session.isoformat(),
        "universe_ids": list(universe_ids),
    }
    if incremental:
        base["execution_mode"] = "verified_prior_incremental"
    all_records = [item for universe_id in universe_ids for item in histories[universe_id]]
    all_explanations = [item for universe_id in universe_ids for item in explanations[universe_id]]
    history_fingerprints = {
        universe_id: state_history_fingerprint(histories[universe_id]) for universe_id in universe_ids
    }
    phase1a_fingerprint = phase1a_audit_manifest.get("logical_content_fingerprint")
    if as_of_session.isoformat() == "2026-08-21" and phase1a_fingerprint != FROZEN_PHASE1A_AUDIT_FINGERPRINT:
        raise MarketRegimeStateAuditError("frozen Phase 1a audit fingerprint mismatch")
    source_manifest = _source_manifest_payload(
        base=base,
        panel=panel,
        phase1a_audit_manifest=phase1a_audit_manifest,
        phase1a_input_manifest=phase1a_input_manifest,
        histories=histories,
        universe_ids=universe_ids,
    )
    payloads = {
        "source-input-manifest.json": source_manifest,
        "state-parameter-contract.json": {**base, "parameter_contract": state_parameter_payload()},
        "state-history.json": {
            **base,
            "history_logical_fingerprints": history_fingerprints,
            "records": [item.model_dump(mode="json") for item in all_records],
        },
        "current-state-summary.json": {
            **base,
            "records": [
                {
                    "universe_id": universe_id,
                    "history_logical_fingerprint": history_fingerprints[universe_id],
                    "history_session_count": len(histories[universe_id]),
                    "current": histories[universe_id][-1].model_dump(mode="json"),
                }
                for universe_id in universe_ids
            ],
        },
        "transition-ledger.json": {
            **base,
            "records": [
                {
                    "as_of_session": item.as_of_session.isoformat(),
                    "universe_id": item.universe_id,
                    "composite": item.composite,
                    "instantaneous_candidate_state": item.instantaneous_candidate_state.value if item.instantaneous_candidate_state else None,
                    "previous_confirmed_state": item.previous_confirmed_state.value if item.previous_confirmed_state else None,
                    "confirmed_state": item.confirmed_state.value if item.confirmed_state else None,
                    "transition_status": item.transition_status.value,
                    "transition_rule_id": item.transition_rule_id,
                    "pending_target_state": item.pending_target_state.value if item.pending_target_state else None,
                    "consecutive_confirmation_sessions": item.consecutive_confirmation_sessions,
                    "required_confirmation_sessions": item.required_confirmation_sessions,
                    "confirmation_sessions_remaining": item.confirmation_sessions_remaining,
                    "state_is_provisional": item.state_is_provisional,
                    "state_availability": item.state_availability.value,
                    "reason_codes": list(item.reason_codes),
                    "state_record_fingerprint": item.logical_fingerprint,
                }
                for item in all_records
            ],
        },
        "state-explanation-ledger.json": {
            **base,
            "records": [item.model_dump(mode="json") for item in all_explanations],
        },
        "state-oracle-report.json": {
            **base,
            "records": [item.model_dump(mode="json") for item in oracle_reports],
        },
    }
    artifact_files = STATE_ARTIFACT_FILES
    if incremental:
        validation = _validate_incremental_validation_input(
            incremental_validation,
            histories=histories,
            explanations=explanations,
            oracle_reports=oracle_reports,
            phase1a_audit_manifest=phase1a_audit_manifest,
        )
        payloads[STATE_INCREMENTAL_VALIDATION_ARTIFACT] = {**base, "record": validation}
        artifact_files = STATE_INCREMENTAL_ARTIFACT_FILES
    artifact_rows = []
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
        "history_logical_fingerprints": history_fingerprints,
        "oracle_fingerprints": [item.oracle_history_fingerprint for item in oracle_reports],
        "oracle_mismatch_count": sum(item.mismatch_count for item in oracle_reports),
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
        "timings": dict(timings),
        "peak_memory_kib": peak_memory_kib,
        "completion_status": "completed",
    }
    _write_new(target / STATE_AUDIT_MANIFEST, _canonical_bytes(manifest))
    for path in target.iterdir():
        path.chmod(0o400)
    return read_market_regime_state_audit(target)


def read_market_regime_state_audit(output_dir: Path) -> dict[str, Any]:
    manifest, _, _, _, _ = _read_market_regime_state_audit(output_dir)
    return manifest


def read_market_regime_state_audit_contents(output_dir: Path) -> MarketRegimeStateAuditContents:
    """Formally reread a Phase 1b audit and expose only verified append inputs."""

    manifest, payloads, histories, explanations, oracles = _read_market_regime_state_audit(output_dir)
    validation_payload = payloads.get(STATE_INCREMENTAL_VALIDATION_ARTIFACT)
    return MarketRegimeStateAuditContents(
        manifest=manifest,
        source_manifest=payloads["source-input-manifest.json"],
        histories=histories,
        explanations=explanations,
        oracle_reports=oracles,
        validation_ledger=None if validation_payload is None else validation_payload["record"],
    )


def _read_market_regime_state_audit(output_dir: Path):
    target = _safe_completed_directory(output_dir)
    actual = {item.name for item in target.iterdir()}
    if STATE_AUDIT_MANIFEST not in actual:
        raise MarketRegimeStateAuditError("state audit file set is incomplete or has extras")
    manifest = _read_canonical_json(target / STATE_AUDIT_MANIFEST)
    schema_version = manifest.get("schema_version")
    execution_mode = manifest.get("execution_mode")
    if schema_version == "1.0" and execution_mode is None:
        artifact_files = STATE_ARTIFACT_FILES
        incremental = False
    elif schema_version == "1.1" and execution_mode == "verified_prior_incremental":
        artifact_files = STATE_INCREMENTAL_ARTIFACT_FILES
        incremental = True
    else:
        raise MarketRegimeStateAuditError("unsupported state audit schema or execution mode")
    expected = set(artifact_files) | {STATE_AUDIT_MANIFEST}
    if actual != expected:
        raise MarketRegimeStateAuditError("state audit file set is incomplete or has extras")
    if manifest.get("completion_status") != "completed":
        raise MarketRegimeStateAuditError("state audit manifest is not completed")
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "timings", "peak_memory_kib", "completion_status"}
    }
    if _fingerprint(logical) != manifest.get("logical_content_fingerprint"):
        raise MarketRegimeStateAuditError("state audit aggregate fingerprint mismatch")
    rows = {item["name"]: item for item in manifest.get("artifacts", [])}
    if tuple(item["name"] for item in manifest.get("artifacts", [])) != artifact_files:
        raise MarketRegimeStateAuditError("state audit artifact order mismatch")
    payloads: dict[str, dict[str, Any]] = {}
    for name in artifact_files:
        raw = (target / name).read_bytes()
        expected_row = rows[name]
        if len(raw) != expected_row["bytes"] or hashlib.sha256(raw).hexdigest() != expected_row["sha256"]:
            raise MarketRegimeStateAuditError(f"state audit physical hash mismatch: {name}")
        payload = _read_canonical_json(target / name)
        content_fingerprint = payload.pop("logical_content_fingerprint", None)
        if _fingerprint(payload) != content_fingerprint or content_fingerprint != expected_row["logical_content_fingerprint"]:
            raise MarketRegimeStateAuditError(f"state audit logical hash mismatch: {name}")
        payloads[name] = payload
    parameter_payload = payloads["state-parameter-contract.json"]
    calculation_version = manifest.get("calculation_version")
    if calculation_version == STATE_CALCULATION_VERSION:
        expected_parameter_payload = state_parameter_payload()
        expected_parameter_fingerprint = STATE_PARAMETER_FINGERPRINT
    elif calculation_version == LEGACY_STATE_CALCULATION_VERSION:
        expected_parameter_payload = legacy_state_parameter_payload()
        expected_parameter_fingerprint = LEGACY_STATE_PARAMETER_FINGERPRINT
    else:
        raise MarketRegimeStateAuditError("unsupported state calculation version")
    if parameter_payload["parameter_contract"] != expected_parameter_payload:
        raise MarketRegimeStateAuditError("state parameter contract mismatch")
    if manifest.get("state_parameter_fingerprint") != expected_parameter_fingerprint:
        raise MarketRegimeStateAuditError("state parameter fingerprint mismatch")
    history_payload = payloads["state-history.json"]
    history_records = tuple(MarketRegimeStateRecordV1.model_validate(item) for item in history_payload["records"])
    by_universe: dict[str, list[MarketRegimeStateRecordV1]] = {}
    for item in history_records:
        payload = item.model_dump(mode="json", exclude={"logical_fingerprint"})
        if _fingerprint(payload) != item.logical_fingerprint:
            raise MarketRegimeStateAuditError("state row logical fingerprint mismatch")
        by_universe.setdefault(item.universe_id, []).append(item)
    for universe_id, items in by_universe.items():
        sessions = tuple(item.as_of_session for item in items)
        if tuple(sorted(sessions)) != sessions or len(set(sessions)) != len(sessions):
            raise MarketRegimeStateAuditError("state history ordering or uniqueness mismatch")
        if state_history_fingerprint(items) != history_payload["history_logical_fingerprints"][universe_id]:
            raise MarketRegimeStateAuditError("state history fingerprint mismatch")
    explanation_payload = payloads["state-explanation-ledger.json"]
    explanation_records = tuple(
        MarketRegimeStateExplanationV1.model_validate(item) for item in explanation_payload["records"]
    )
    explanations_by_universe: dict[str, list[MarketRegimeStateExplanationV1]] = {}
    for item in explanation_records:
        explanations_by_universe.setdefault(item.universe_id, []).append(item)
    oracle_payload = payloads["state-oracle-report.json"]
    oracles = tuple(StateOracleComparisonV1.model_validate(item) for item in oracle_payload["records"])
    if [item.oracle_history_fingerprint for item in oracles] != manifest["oracle_fingerprints"]:
        raise MarketRegimeStateAuditError("state oracle fingerprint ledger mismatch")
    if (
        manifest.get("oracle_mismatch_count") != 0
        or any(item.mismatch_count != 0 or item.mismatches for item in oracles)
    ):
        raise MarketRegimeStateAuditError("state Oracle equivalence gate did not pass")
    typed_histories = {key: tuple(value) for key, value in by_universe.items()}
    typed_explanations = {key: tuple(value) for key, value in explanations_by_universe.items()}
    _validate_reread_bindings(
        manifest=manifest,
        payloads=payloads,
        histories=typed_histories,
        explanations=typed_explanations,
        incremental=incremental,
    )
    return manifest, payloads, typed_histories, typed_explanations, oracles


def _source_manifest_payload(
    *,
    base: Mapping[str, Any],
    panel: MarketRegimeInputPanel | None,
    phase1a_audit_manifest: Mapping[str, Any],
    phase1a_input_manifest: Mapping[str, Any] | None,
    histories: Mapping[str, Sequence[MarketRegimeStateRecordV1]],
    universe_ids: tuple[str, ...],
) -> dict[str, Any]:
    state_sessions = [item.as_of_session.isoformat() for item in histories[universe_ids[0]]]
    warnings = [
        "current_as_of_constituent_replay",
        "short_history_not_predictive_validation",
        "state_is_research_environment_not_trade_instruction",
    ]
    if panel is not None:
        return {
            **base,
            "phase1a_audit_logical_fingerprint": phase1a_audit_manifest.get(
                "logical_content_fingerprint"
            ),
            "phase1a_current_composite_fingerprints": phase1a_audit_manifest.get(
                "composite_fingerprints"
            ),
            "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
            "identity_logical_fingerprint": panel.identity_logical_fingerprint,
            "eod_content_fingerprint": panel.eod_content_fingerprint,
            "history_source_fingerprint": panel.history_source_fingerprint,
            "history_sessions": [item.isoformat() for item in panel.sessions],
            "state_sessions": state_sessions,
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
                    "catalog_order": item.catalog_order,
                    "is_default": item.is_default,
                    "member_count": len(item.member_ids),
                    "membership_fingerprint": item.membership_fingerprint,
                }
                for item in panel.universes
                if item.universe_id in histories
            ],
            "warnings": warnings,
        }
    assert phase1a_input_manifest is not None
    return {
        **base,
        "source_custody_mode": "verified_prior_state_plus_current_phase1a_audit",
        "phase1a_audit_logical_fingerprint": phase1a_audit_manifest.get(
            "logical_content_fingerprint"
        ),
        "phase1a_current_composite_fingerprints": phase1a_audit_manifest.get(
            "composite_fingerprints"
        ),
        "activation_pointer_fingerprint": phase1a_input_manifest.get(
            "activation_pointer_fingerprint"
        ),
        "identity_logical_fingerprint": phase1a_input_manifest.get("identity_logical_fingerprint"),
        "eod_content_fingerprint": phase1a_input_manifest.get("eod_content_fingerprint"),
        "history_source_fingerprint": phase1a_input_manifest.get("history_source_fingerprint"),
        "history_sessions": phase1a_input_manifest.get("history_sessions"),
        "state_sessions": state_sessions,
        "source_sessions": phase1a_input_manifest.get("source_sessions"),
        "universes": [
            {
                "universe_id": item.get("universe_id"),
                "catalog_order": item.get("catalog_order"),
                "is_default": item.get("is_default"),
                "member_count": item.get("member_count"),
                "membership_fingerprint": item.get("membership_fingerprint"),
            }
            for item in phase1a_input_manifest.get("universes", ())
            if item.get("universe_id") in histories
        ],
        "warnings": warnings,
    }


def _validate_incremental_validation_input(
    value: Mapping[str, Any] | None,
    *,
    histories: Mapping[str, Sequence[MarketRegimeStateRecordV1]],
    explanations: Mapping[str, Sequence[MarketRegimeStateExplanationV1]],
    oracle_reports: Sequence[StateOracleComparisonV1],
    phase1a_audit_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MarketRegimeStateAuditError("incremental state validation ledger is missing")
    record = _normalize_nfc(dict(value))
    required_strings = (
        "prior_audit_logical_fingerprint",
        "prior_as_of_session",
        "current_as_of_session",
        "prior_explanation_records_fingerprint",
        "prior_source_manifest_fingerprint",
        "current_phase1a_audit_logical_fingerprint",
    )
    if any(not isinstance(record.get(name), str) or not record[name] for name in required_strings):
        raise MarketRegimeStateAuditError("incremental state validation ledger has missing bindings")
    fingerprints = (
        "prior_audit_logical_fingerprint",
        "prior_explanation_records_fingerprint",
        "prior_source_manifest_fingerprint",
        "current_phase1a_audit_logical_fingerprint",
    )
    if any(not _is_fingerprint(record[name]) for name in fingerprints):
        raise MarketRegimeStateAuditError("incremental state validation fingerprint is malformed")
    if record.get("validation_scope") != "verified_prior_plus_current_session_oracle":
        raise MarketRegimeStateAuditError("incremental state validation scope is unsupported")
    prior_session = date.fromisoformat(record["prior_as_of_session"])
    current_session = date.fromisoformat(record["current_as_of_session"])
    if phase1a_audit_manifest.get("logical_content_fingerprint") != record[
        "current_phase1a_audit_logical_fingerprint"
    ]:
        raise MarketRegimeStateAuditError("incremental current Phase 1a audit binding mismatch")
    expected_composites = phase1a_audit_manifest.get("composite_fingerprints")
    if record.get("current_phase1a_composite_fingerprints") != expected_composites:
        raise MarketRegimeStateAuditError("incremental current Composite binding mismatch")
    prior_history_fingerprints = record.get("prior_history_logical_fingerprints")
    current_oracle_fingerprints = record.get("current_session_oracle_fingerprints")
    if not isinstance(prior_history_fingerprints, dict) or not isinstance(
        current_oracle_fingerprints, list
    ):
        raise MarketRegimeStateAuditError("incremental state prefix or Oracle ledger is malformed")
    for universe_id, rows in histories.items():
        if (
            len(rows) < 2
            or rows[-1].as_of_session != current_session
            or rows[-2].as_of_session != prior_session
        ):
            raise MarketRegimeStateAuditError("incremental state history boundary mismatch")
        if state_history_fingerprint(rows[:-1]) != prior_history_fingerprints.get(universe_id):
            raise MarketRegimeStateAuditError("incremental state history prefix mismatch")
    prior_explanations = tuple(
        item.model_dump(mode="json")
        for universe_id in histories
        for item in explanations[universe_id][:-1]
    )
    if _fingerprint(prior_explanations) != record["prior_explanation_records_fingerprint"]:
        raise MarketRegimeStateAuditError("incremental explanation prefix mismatch")
    if [item.oracle_history_fingerprint for item in oracle_reports] != current_oracle_fingerprints:
        raise MarketRegimeStateAuditError("incremental current-session Oracle binding mismatch")
    if any(
        item.first_session != current_session
        or item.last_session != current_session
        or item.compared_session_count != 1
        for item in oracle_reports
    ):
        raise MarketRegimeStateAuditError("incremental Oracle scope is not exactly one session")
    reuse_checks = record.get("reuse_checks")
    if not isinstance(reuse_checks, dict) or not reuse_checks or any(
        type(item) is not bool or item is not True for item in reuse_checks.values()
    ):
        raise MarketRegimeStateAuditError("incremental state reuse checks did not pass")
    segments = record.get("validation_segments")
    if not isinstance(segments, list) or not segments or any(
        not isinstance(item, dict) for item in segments
    ):
        raise MarketRegimeStateAuditError("incremental state validation segments are malformed")
    return record  # type: ignore[return-value]


def _validate_reread_bindings(
    *, manifest, payloads, histories, explanations, incremental
) -> None:
    universe_ids = tuple(manifest.get("universe_ids", ()))
    if not universe_ids:
        raise MarketRegimeStateAuditError("state audit Universe catalog is empty")
    base_keys = (
        "schema_version",
        "contract_version",
        "calculation_version",
        "state_parameter_set_id",
        "state_parameter_fingerprint",
        "phase1a_calculation_version",
        "phase1a_parameter_set_id",
        "phase1a_parameter_fingerprint",
        "as_of_session",
        "first_calculable_session",
        "universe_ids",
    )
    if incremental:
        base_keys = (*base_keys, "execution_mode")
    if any(
        any(payload.get(key) != manifest.get(key) for key in base_keys)
        for payload in payloads.values()
    ):
        raise MarketRegimeStateAuditError("state artifact and manifest base contract mismatch")
    if tuple(histories) != universe_ids or tuple(explanations) != universe_ids:
        raise MarketRegimeStateAuditError("state audit Universe order mismatch")
    state_sessions = tuple(item.as_of_session for item in histories[universe_ids[0]])
    if not state_sessions or state_sessions[-1].isoformat() != manifest.get("as_of_session"):
        raise MarketRegimeStateAuditError("state audit current session mismatch")
    if any(tuple(item.as_of_session for item in histories[key]) != state_sessions for key in universe_ids):
        raise MarketRegimeStateAuditError("state audit Universe histories are not aligned")
    if any(
        tuple((item.as_of_session, item.universe_id) for item in explanations[key])
        != tuple((item.as_of_session, key) for item in histories[key])
        for key in universe_ids
    ):
        raise MarketRegimeStateAuditError("state explanation ledger is not aligned")
    source = payloads["source-input-manifest.json"]
    if source.get("state_sessions") != [item.isoformat() for item in state_sessions]:
        raise MarketRegimeStateAuditError("state source session ledger mismatch")
    all_records = tuple(item for key in universe_ids for item in histories[key])
    expected_transitions = [_transition_row(item) for item in all_records]
    if payloads["transition-ledger.json"].get("records") != expected_transitions:
        raise MarketRegimeStateAuditError("state transition ledger mismatch")
    summaries = payloads["current-state-summary.json"].get("records")
    expected_summaries = [
        {
            "universe_id": key,
            "history_logical_fingerprint": state_history_fingerprint(histories[key]),
            "history_session_count": len(histories[key]),
            "current": histories[key][-1].model_dump(mode="json"),
        }
        for key in universe_ids
    ]
    if summaries != expected_summaries:
        raise MarketRegimeStateAuditError("state current summary mismatch")
    if incremental:
        validation = _validate_incremental_validation_input(
            payloads[STATE_INCREMENTAL_VALIDATION_ARTIFACT].get("record"),
            histories=histories,
            explanations=explanations,
            oracle_reports=tuple(
                StateOracleComparisonV1.model_validate(item)
                for item in payloads["state-oracle-report.json"]["records"]
            ),
            phase1a_audit_manifest={
                "logical_content_fingerprint": source.get("phase1a_audit_logical_fingerprint"),
                "composite_fingerprints": source.get("phase1a_current_composite_fingerprints"),
            },
        )
        if manifest.get("prior_audit_logical_fingerprint") != validation.get(
            "prior_audit_logical_fingerprint"
        ) or manifest.get("prior_as_of_session") != validation.get("prior_as_of_session"):
            raise MarketRegimeStateAuditError("incremental state manifest binding mismatch")


def _transition_row(item: MarketRegimeStateRecordV1) -> dict[str, Any]:
    return {
        "as_of_session": item.as_of_session.isoformat(),
        "universe_id": item.universe_id,
        "composite": item.composite,
        "instantaneous_candidate_state": (
            item.instantaneous_candidate_state.value if item.instantaneous_candidate_state else None
        ),
        "previous_confirmed_state": (
            item.previous_confirmed_state.value if item.previous_confirmed_state else None
        ),
        "confirmed_state": item.confirmed_state.value if item.confirmed_state else None,
        "transition_status": item.transition_status.value,
        "transition_rule_id": item.transition_rule_id,
        "pending_target_state": item.pending_target_state.value if item.pending_target_state else None,
        "consecutive_confirmation_sessions": item.consecutive_confirmation_sessions,
        "required_confirmation_sessions": item.required_confirmation_sessions,
        "confirmation_sessions_remaining": item.confirmation_sessions_remaining,
        "state_is_provisional": item.state_is_provisional,
        "state_availability": item.state_availability.value,
        "reason_codes": list(item.reason_codes),
        "state_record_fingerprint": item.logical_fingerprint,
    }


def _is_fingerprint(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _safe_completed_directory(output_dir: Path) -> Path:
    if output_dir.is_symlink():
        raise MarketRegimeStateAuditError("symlink state audit directory is rejected")
    target = output_dir.resolve(strict=True)
    if (
        not target.is_dir()
        or target.parent != Path("/tmp")
        or target.stat().st_uid != os.geteuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
    ):
        raise MarketRegimeStateAuditError("state audit directory must be a caller-owned direct /tmp child")
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise MarketRegimeStateAuditError("state audit files must be caller-owned regular mode-0400 files")
    return target


def _validate_tmp_output_dir(output_dir: Path) -> Path:
    if not output_dir.is_absolute() or output_dir.parent != Path("/tmp") or output_dir.name in {"", ".", ".."}:
        raise MarketRegimeStateAuditError("output directory must be a direct child of /tmp")
    current = Path("/")
    for part in output_dir.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise MarketRegimeStateAuditError("symlink output path is rejected")
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise MarketRegimeStateAuditError("existing output path must be an empty safe directory")
        metadata = output_dir.stat()
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise MarketRegimeStateAuditError("existing output directory must be caller-owned mode 0700")
        return output_dir.resolve(strict=True)
    return output_dir


def _with_logical_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["logical_content_fingerprint"] = _fingerprint(payload)
    return result


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(_normalize_nfc(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _normalize_nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list | tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", str(key)): _normalize_nfc(item) for key, item in value.items()}
    return value


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise MarketRegimeStateAuditError(f"malformed state audit JSON: {path.name}") from exc
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise MarketRegimeStateAuditError(f"non-canonical state audit JSON: {path.name}")
    return value


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o400)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()
