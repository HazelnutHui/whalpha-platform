"""Canonical governed Phase 2 ETF relationship artifacts and formal reread."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Sequence

from tip_api.contracts.analytics.v1.etf_relationship import (
    EtfRelationshipExplanationV1,
    EtfRelationshipOracleComparisonV1,
    EtfRelationshipRecordV1,
    MarketRegimeRelationshipComparisonV1,
)
from tip_api.parameters.market_regime.relationship_v1_0_0 import (
    ETF_BASKET,
    ETF_PAIRS,
    RELATIONSHIP_CALCULATION_VERSION,
    RELATIONSHIP_CONTRACT_VERSION,
    RELATIONSHIP_PARAMETER_FINGERPRINT,
    RELATIONSHIP_PARAMETER_SET_ID,
    parameter_payload,
)
from tip_api.services.etf_relationships import relationship_history_fingerprint
from tip_api.services.market_regime_sources import MarketRegimeInputPanel
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


RELATIONSHIP_ARTIFACT_FILES = (
    "pair-registry.json",
    "source-input-manifest.json",
    "relationship-metrics.json",
    "current-relationship-summary.json",
    "relationship-explanation-ledger.json",
    "historical-relationship-states.json",
    "market-regime-relationship-comparison.json",
    "relationship-oracle-report.json",
)
RELATIONSHIP_AUDIT_MANIFEST = "relationship-audit-manifest.json"


class EtfRelationshipAuditError(RuntimeError):
    pass


class EtfRelationshipPlanningEvidence(NamedTuple):
    manifest: Mapping[str, Any]
    source_manifest: Mapping[str, Any]


def write_etf_relationship_audit(
    *, output_dir: Path, panel: MarketRegimeInputPanel,
    phase1a_manifest: Mapping[str, Any], phase1b_manifest: Mapping[str, Any],
    history: Sequence[EtfRelationshipRecordV1], current: Sequence[EtfRelationshipRecordV1],
    explanations: Sequence[EtfRelationshipExplanationV1],
    regime_comparisons: Sequence[MarketRegimeRelationshipComparisonV1],
    oracle_report: EtfRelationshipOracleComparisonV1,
    first_available_sessions: Mapping[str, str], generated_at: datetime,
    timings: Mapping[str, str], peak_memory_kib: int,
) -> dict[str, Any]:
    target = validate_tmp_output_dir(output_dir)
    target.mkdir(mode=0o700, parents=False, exist_ok=True)
    if any(target.iterdir()):
        raise EtfRelationshipAuditError("existing non-empty output directory is rejected")
    base = {
        "schema_version": "1.0", "contract_version": RELATIONSHIP_CONTRACT_VERSION,
        "calculation_version": RELATIONSHIP_CALCULATION_VERSION,
        "parameter_set_id": RELATIONSHIP_PARAMETER_SET_ID,
        "parameter_fingerprint": RELATIONSHIP_PARAMETER_FINGERPRINT,
        "as_of_session": panel.as_of_session.isoformat(),
    }
    history_fp = relationship_history_fingerprint(history)
    payloads = {
        "pair-registry.json": {
            **base, "basket": [item.__dict__ if hasattr(item, "__dict__") else {name: getattr(item,name) for name in item.__slots__} for item in ETF_BASKET],
            "pairs": [{name: list(getattr(item,name)) if name == "applicable_windows" else getattr(item,name) for name in item.__slots__} for item in ETF_PAIRS],
            "parameter_contract": parameter_payload(),
        },
        "source-input-manifest.json": {
            **base, "input_session_range": [panel.sessions[0].isoformat(), panel.sessions[-1].isoformat()],
            "input_session_count": len(panel.sessions), "calendar_id": panel.calendar_id,
            "calendar_version": panel.calendar_version, "history_source_fingerprint": panel.history_source_fingerprint,
            "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
            "identity_logical_fingerprint": panel.identity_logical_fingerprint,
            "eod_content_fingerprint": panel.eod_content_fingerprint,
            "eod_business_key_fingerprint": panel.eod_business_key_fingerprint,
            "phase1a_audit_logical_fingerprint": phase1a_manifest.get("logical_content_fingerprint"),
            "phase1a_composite_fingerprints": phase1a_manifest.get("composite_fingerprints"),
            "phase1b_audit_logical_fingerprint": phase1b_manifest.get("logical_content_fingerprint"),
            "phase1b_history_logical_fingerprints": phase1b_manifest.get("history_logical_fingerprints"),
            "source_sessions": [
                {"session_date": item.session_date.isoformat(), "dataset_path": item.dataset_path,
                 "record_count": item.record_count, "content_fingerprint": item.content_fingerprint,
                 "parquet_sha256": item.parquet_sha256, "identity_snapshot_date": item.identity_snapshot_date.isoformat(),
                 "identity_snapshot_fingerprint": item.identity_snapshot_fingerprint}
                for item in panel.source_sessions
            ],
            "first_available_sessions": dict(first_available_sessions),
            "warnings": ["short_history_not_predictive_validation", "current_relationships_not_trade_instructions", "notional_placeholder_not_used"],
        },
        "relationship-metrics.json": {**base, "history_logical_fingerprint": history_fp, "records": [item.model_dump(mode="json") for item in history]},
        "current-relationship-summary.json": {**base, "history_logical_fingerprint": history_fp, "records": [item.model_dump(mode="json") for item in current]},
        "relationship-explanation-ledger.json": {**base, "records": [item.model_dump(mode="json") for item in explanations]},
        "historical-relationship-states.json": {
            **base, "history_logical_fingerprint": history_fp,
            "records": [
                {"as_of_session": item.as_of_session.isoformat(), "pair_id": item.pair_id,
                 "relationship_state": item.relationship_state.value, "previous_relationship_state": item.previous_relationship_state.value if item.previous_relationship_state else None,
                 "availability": item.availability.value, "confidence": item.confidence.value,
                 "reason_codes": list(item.reason_codes), "record_logical_fingerprint": item.logical_fingerprint}
                for item in history
            ],
        },
        "market-regime-relationship-comparison.json": {**base, "records": [item.model_dump(mode="json") for item in regime_comparisons]},
        "relationship-oracle-report.json": {**base, "record": oracle_report.model_dump(mode="json")},
    }
    artifacts = []
    for name in RELATIONSHIP_ARTIFACT_FILES:
        payload = _with_logical_fingerprint(payloads[name])
        raw = _canonical_bytes(payload)
        _write_new(target / name, raw)
        artifacts.append({"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "logical_content_fingerprint": payload["logical_content_fingerprint"]})
    logical = {
        **base, "artifacts": artifacts, "history_logical_fingerprint": history_fp,
        "current_record_fingerprints": [item.logical_fingerprint for item in current],
        "oracle_history_fingerprint": oracle_report.oracle_history_fingerprint,
        "oracle_mismatch_count": oracle_report.mismatch_count,
        "append_full_replay_match": oracle_report.append_full_replay_match,
        "input_permutation_match": oracle_report.input_permutation_match,
        "future_prefix_stable": oracle_report.future_prefix_stable,
        "external_request_count": 0, "production_write_count": 0,
    }
    manifest = {**logical, "logical_content_fingerprint": _fingerprint(logical),
                "generated_at": generated_at.astimezone(UTC).isoformat(), "timings": dict(timings),
                "peak_memory_kib": peak_memory_kib, "completion_status": "completed"}
    _write_new(target / RELATIONSHIP_AUDIT_MANIFEST, _canonical_bytes(manifest))
    for path in target.iterdir(): path.chmod(0o400)
    return read_etf_relationship_audit(target)


def read_etf_relationship_audit(output_dir: Path) -> dict[str, Any]:
    target = _safe_completed_directory(output_dir)
    expected = set(RELATIONSHIP_ARTIFACT_FILES) | {RELATIONSHIP_AUDIT_MANIFEST}
    if {item.name for item in target.iterdir()} != expected:
        raise EtfRelationshipAuditError("audit file set is incomplete")
    if any(item.is_symlink() or not item.is_file() or item.stat().st_uid != os.geteuid() or stat.S_IMODE(item.stat().st_mode) != 0o400 for item in target.iterdir()):
        raise EtfRelationshipAuditError("unsafe audit artifact")
    manifest = _read_canonical_json(target / RELATIONSHIP_AUDIT_MANIFEST)
    logical = {key: value for key,value in manifest.items() if key not in {"logical_content_fingerprint","generated_at","timings","peak_memory_kib","completion_status"}}
    if manifest.get("completion_status") != "completed" or _fingerprint(logical) != manifest.get("logical_content_fingerprint"):
        raise EtfRelationshipAuditError("audit manifest fingerprint mismatch")
    if tuple(item["name"] for item in manifest.get("artifacts",())) != RELATIONSHIP_ARTIFACT_FILES:
        raise EtfRelationshipAuditError("artifact order mismatch")
    for row in manifest["artifacts"]:
        raw=(target/row["name"]).read_bytes()
        if len(raw)!=row["bytes"] or hashlib.sha256(raw).hexdigest()!=row["sha256"]:
            raise EtfRelationshipAuditError(f"artifact custody mismatch: {row['name']}")
        payload=_read_canonical_json(target/row["name"]); fingerprint=payload.pop("logical_content_fingerprint",None)
        if _fingerprint(payload)!=fingerprint or fingerprint!=row["logical_content_fingerprint"]:
            raise EtfRelationshipAuditError(f"artifact logical fingerprint mismatch: {row['name']}")
    current_payload=_read_canonical_json(target/"current-relationship-summary.json")
    current=tuple(EtfRelationshipRecordV1.model_validate(item) for item in current_payload["records"])
    if [item.logical_fingerprint for item in current] != manifest["current_record_fingerprints"]:
        raise EtfRelationshipAuditError("current relationship fingerprint ledger mismatch")
    explanations=_read_canonical_json(target/"relationship-explanation-ledger.json")
    tuple(EtfRelationshipExplanationV1.model_validate(item) for item in explanations["records"])
    comparisons=_read_canonical_json(target/"market-regime-relationship-comparison.json")
    tuple(MarketRegimeRelationshipComparisonV1.model_validate(item) for item in comparisons["records"])
    oracle=_read_canonical_json(target/"relationship-oracle-report.json")
    EtfRelationshipOracleComparisonV1.model_validate(oracle["record"])
    return manifest


def read_etf_relationship_planning_evidence(
    output_dir: Path,
) -> EtfRelationshipPlanningEvidence:
    """Return the completed manifest plus its hash-verified source binding."""

    manifest = read_etf_relationship_audit(output_dir)
    source_manifest = _read_canonical_json(output_dir / "source-input-manifest.json")
    return EtfRelationshipPlanningEvidence(
        manifest=manifest,
        source_manifest=source_manifest,
    )


def validate_tmp_output_dir(output_dir: Path) -> Path:
    try:
        validate_offline_artifact_location(
            output_dir,
            persistent_names={"etf-relationships"},
        )
    except OfflineArtifactCustodyError as exc:
        raise EtfRelationshipAuditError(
            f"output directory custody differs: {exc}"
        ) from exc
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise EtfRelationshipAuditError("existing output path is unsafe or non-empty")
        meta=output_dir.stat()
        if meta.st_uid!=os.geteuid() or stat.S_IMODE(meta.st_mode)!=0o700:
            raise EtfRelationshipAuditError("existing output directory custody mismatch")
    return output_dir


def _safe_completed_directory(path: Path) -> Path:
    try:
        validate_offline_artifact_location(
            path,
            persistent_names={"etf-relationships"},
        )
    except OfflineArtifactCustodyError as exc:
        raise EtfRelationshipAuditError(
            f"audit directory custody differs: {exc}"
        ) from exc
    target=path.resolve(strict=True); meta=target.stat()
    if not target.is_dir() or meta.st_uid!=os.geteuid() or stat.S_IMODE(meta.st_mode)!=0o700:
        raise EtfRelationshipAuditError("audit directory custody mismatch")
    return target


def _with_logical_fingerprint(payload): return {**payload,"logical_content_fingerprint":_fingerprint(payload)}
def _fingerprint(value): return hashlib.sha256(_canonical_bytes(value)).hexdigest()
def _canonical_bytes(value): return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)+"\n").encode()
def _write_new(path, raw):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    with os.fdopen(descriptor,"wb") as handle: handle.write(raw); handle.flush(); os.fsync(handle.fileno())
def _read_canonical_json(path):
    raw=path.read_bytes(); parsed=json.loads(raw)
    if _canonical_bytes(parsed)!=raw: raise EtfRelationshipAuditError(f"non-canonical artifact: {path.name}")
    return parsed
