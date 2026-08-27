"""Canonical tmp-only Phase 1b state artifacts and formal offline reader."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from datetime import UTC, datetime
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


class MarketRegimeStateAuditError(RuntimeError):
    pass


def write_market_regime_state_audit(
    *,
    output_dir: Path,
    panel: MarketRegimeInputPanel,
    phase1a_audit_manifest: Mapping[str, Any],
    histories: Mapping[str, Sequence[MarketRegimeStateRecordV1]],
    explanations: Mapping[str, Sequence[MarketRegimeStateExplanationV1]],
    oracle_reports: Sequence[StateOracleComparisonV1],
    first_calculable_session: object,
    generated_at: datetime,
    timings: Mapping[str, str],
    peak_memory_kib: int,
) -> dict[str, Any]:
    target = _validate_tmp_output_dir(output_dir)
    target.mkdir(mode=0o700, parents=False, exist_ok=True)
    if any(target.iterdir()):
        raise MarketRegimeStateAuditError("existing non-empty output directory is rejected")
    universe_ids = tuple(histories)
    base = {
        "schema_version": "1.0",
        "contract_version": STATE_CONTRACT_VERSION,
        "calculation_version": STATE_CALCULATION_VERSION,
        "state_parameter_set_id": STATE_PARAMETER_SET_ID,
        "state_parameter_fingerprint": STATE_PARAMETER_FINGERPRINT,
        "phase1a_calculation_version": PHASE1A_CALCULATION_VERSION,
        "phase1a_parameter_set_id": PHASE1A_PARAMETER_SET_ID,
        "phase1a_parameter_fingerprint": PHASE1A_PARAMETER_FINGERPRINT,
        "as_of_session": panel.as_of_session.isoformat(),
        "first_calculable_session": first_calculable_session.isoformat(),
        "universe_ids": list(universe_ids),
    }
    all_records = [item for universe_id in universe_ids for item in histories[universe_id]]
    all_explanations = [item for universe_id in universe_ids for item in explanations[universe_id]]
    history_fingerprints = {
        universe_id: state_history_fingerprint(histories[universe_id]) for universe_id in universe_ids
    }
    phase1a_fingerprint = phase1a_audit_manifest.get("logical_content_fingerprint")
    if panel.as_of_session.isoformat() == "2026-08-21" and phase1a_fingerprint != FROZEN_PHASE1A_AUDIT_FINGERPRINT:
        raise MarketRegimeStateAuditError("frozen Phase 1a audit fingerprint mismatch")
    payloads = {
        "source-input-manifest.json": {
            **base,
            "phase1a_audit_logical_fingerprint": phase1a_fingerprint,
            "phase1a_current_composite_fingerprints": phase1a_audit_manifest.get("composite_fingerprints"),
            "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
            "identity_logical_fingerprint": panel.identity_logical_fingerprint,
            "eod_content_fingerprint": panel.eod_content_fingerprint,
            "history_source_fingerprint": panel.history_source_fingerprint,
            "history_sessions": [item.isoformat() for item in panel.sessions],
            "state_sessions": [item.as_of_session.isoformat() for item in histories[universe_ids[0]]],
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
            "warnings": [
                "current_as_of_constituent_replay",
                "short_history_not_predictive_validation",
                "state_is_research_environment_not_trade_instruction",
            ],
        },
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
    artifact_rows = []
    for name in STATE_ARTIFACT_FILES:
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
    target = _safe_completed_directory(output_dir)
    expected = set(STATE_ARTIFACT_FILES) | {STATE_AUDIT_MANIFEST}
    actual = {item.name for item in target.iterdir()}
    if actual != expected:
        raise MarketRegimeStateAuditError("state audit file set is incomplete or has extras")
    manifest = _read_canonical_json(target / STATE_AUDIT_MANIFEST)
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
    if tuple(item["name"] for item in manifest.get("artifacts", [])) != STATE_ARTIFACT_FILES:
        raise MarketRegimeStateAuditError("state audit artifact order mismatch")
    for name in STATE_ARTIFACT_FILES:
        raw = (target / name).read_bytes()
        expected_row = rows[name]
        if len(raw) != expected_row["bytes"] or hashlib.sha256(raw).hexdigest() != expected_row["sha256"]:
            raise MarketRegimeStateAuditError(f"state audit physical hash mismatch: {name}")
        payload = _read_canonical_json(target / name)
        content_fingerprint = payload.pop("logical_content_fingerprint", None)
        if _fingerprint(payload) != content_fingerprint or content_fingerprint != expected_row["logical_content_fingerprint"]:
            raise MarketRegimeStateAuditError(f"state audit logical hash mismatch: {name}")
    parameter_payload = _read_canonical_json(target / "state-parameter-contract.json")
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
    history_payload = _read_canonical_json(target / "state-history.json")
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
    explanation_payload = _read_canonical_json(target / "state-explanation-ledger.json")
    tuple(MarketRegimeStateExplanationV1.model_validate(item) for item in explanation_payload["records"])
    oracle_payload = _read_canonical_json(target / "state-oracle-report.json")
    oracles = tuple(StateOracleComparisonV1.model_validate(item) for item in oracle_payload["records"])
    if [item.oracle_history_fingerprint for item in oracles] != manifest["oracle_fingerprints"]:
        raise MarketRegimeStateAuditError("state oracle fingerprint ledger mismatch")
    return manifest


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
