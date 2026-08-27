"""Canonical tmp-only audit artifacts and formal reread for Market Regime Phase 1a."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from tip_api.contracts.analytics.v1 import (
    ExplanationLedgerEntryV1,
    MarketRegimeCompositeV1,
    OracleComparisonV1,
)
from tip_api.parameters.market_regime.v1_0_0 import (
    CALCULATION_VERSION,
    CONTRACT_VERSION,
    PARAMETER_SET_FINGERPRINT,
    PARAMETER_SET_ID,
    parameter_payload,
)
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


ARTIFACT_FILES = (
    "input-manifest.json",
    "raw-metrics.json",
    "normalized-metrics.json",
    "composite.json",
    "missingness.json",
    "explanation-ledger.json",
    "oracle-report.json",
)
AUDIT_MANIFEST = "calculation-manifest.json"
SNAPSHOT_NAMESPACE = UUID("efed7060-e698-52b6-a2a7-4296e50b63b2")


class MarketRegimeAuditError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MarketRegimeAuditContents:
    """Formally verified Phase 1a inputs exposed to a downstream append."""

    manifest: dict[str, Any]
    input_manifest: dict[str, Any]
    composites: tuple[MarketRegimeCompositeV1, ...]


def write_market_regime_audit(
    *,
    output_dir: Path,
    panel: MarketRegimeInputPanel,
    composites: tuple[MarketRegimeCompositeV1, ...],
    explanations: tuple[ExplanationLedgerEntryV1, ...],
    oracle_reports: tuple[OracleComparisonV1, ...],
    generated_at: datetime,
    elapsed_seconds: str,
    peak_memory_kib: int,
) -> dict[str, Any]:
    target = validate_tmp_output_dir(output_dir)
    target.mkdir(mode=0o700, parents=False, exist_ok=True)
    if any(target.iterdir()):
        raise MarketRegimeAuditError("existing non-empty output directory is rejected")
    universe_ids = tuple(item.universe_id for item in composites)
    snapshot_id = str(uuid5(
        SNAPSHOT_NAMESPACE,
        ":".join((
            CONTRACT_VERSION,
            CALCULATION_VERSION,
            PARAMETER_SET_ID,
            panel.as_of_session.isoformat(),
            panel.activation_pointer_fingerprint,
            panel.identity_logical_fingerprint,
            panel.eod_content_fingerprint,
        )),
    ))
    base = {
        "schema_version": "1.0",
        "contract_version": CONTRACT_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "parameter_set_id": PARAMETER_SET_ID,
        "parameter_set_fingerprint": PARAMETER_SET_FINGERPRINT,
        "snapshot_id": snapshot_id,
        "as_of_session": panel.as_of_session.isoformat(),
        "universe_ids": list(universe_ids),
    }
    input_manifest = {
        **base,
        "freshness": {
            "status": "frozen_development_baseline",
            "actual_session": panel.as_of_session.isoformat(),
            "expected_session": None,
            "lag": None,
            "calendar_id": panel.calendar_id,
            "calendar_version": panel.calendar_version,
            "reason_codes": ["freshness_not_a_phase_1a_gate"],
        },
        "history_membership_mode": "current_as_of_constituent_replay",
        "history_sessions": [item.isoformat() for item in panel.sessions],
        "history_source_fingerprint": panel.history_source_fingerprint,
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
        "activation_pointer_fingerprint": panel.activation_pointer_fingerprint,
        "identity_logical_fingerprint": panel.identity_logical_fingerprint,
        "eod_content_fingerprint": panel.eod_content_fingerprint,
        "eod_business_key_fingerprint": panel.eod_business_key_fingerprint,
        "universes": [
            {
                "universe_id": item.universe_id,
                "display_name": item.display_name,
                "catalog_order": item.catalog_order,
                "is_default": item.is_default,
                "member_count": len(item.member_ids),
                "membership_fingerprint": item.membership_fingerprint,
            }
            for item in panel.universes if item.universe_id in universe_ids
        ],
        "parameter_set": parameter_payload(),
        "warnings": ["current_as_of_constituent_replay", "notional_placeholder_not_used"],
    }
    raw_records = []
    normalized_records = []
    for composite in composites:
        for dimension in composite.dimensions:
            for metric in dimension.raw_metrics:
                identity = {
                    "universe_id": composite.universe_id,
                    "dimension_id": dimension.dimension_id,
                    "metric_id": metric.metric_id,
                    "as_of_session": metric.as_of_session.isoformat(),
                }
                raw_records.append({
                    **identity,
                    "lookback_sessions": metric.lookback_sessions,
                    "raw_value": metric.raw_value,
                    "raw_unit": metric.raw_unit,
                    "actual_observations": metric.actual_observations,
                    "minimum_observations": metric.minimum_observations,
                    "coverage_ratio": metric.coverage_ratio,
                    "missing_count": metric.missing_count,
                    "availability": metric.availability.value,
                    "missing_reason": metric.missing_reason,
                    "source_input_references": list(metric.source_input_references),
                    "reason_codes": list(metric.reason_codes),
                })
                normalized_records.append({
                    **identity,
                    "direction": metric.direction,
                    "normalization_method": metric.normalization_method,
                    "normalization_parameters": [list(item) for item in metric.normalization_parameters],
                    "normalized_value": metric.normalized_value,
                    "configured_weight": metric.configured_weight,
                    "effective_weight": metric.effective_weight,
                    "weighted_contribution": metric.weighted_contribution,
                    "availability": metric.availability.value,
                })
    payloads = {
        "input-manifest.json": input_manifest,
        "raw-metrics.json": {**base, "records": raw_records},
        "normalized-metrics.json": {**base, "records": normalized_records},
        "composite.json": {**base, "records": [item.model_dump(mode="json") for item in composites]},
        "missingness.json": {
            **base,
            "records": [
                {
                    "universe_id": item.universe_id,
                    "configured_weight_available": item.configured_weight_available,
                    "regime_score_available": item.regime_score is not None,
                    "missing_metric_ids": list(item.missing_metric_ids),
                    "unavailable_dimension_ids": list(item.unavailable_dimension_ids),
                    "reason_codes": list(item.reason_codes),
                    "warnings": list(item.warnings),
                }
                for item in composites
            ],
        },
        "explanation-ledger.json": {**base, "records": [item.model_dump(mode="json") for item in explanations]},
        "oracle-report.json": {**base, "records": [item.model_dump(mode="json") for item in oracle_reports]},
    }
    artifact_rows = []
    for name in ARTIFACT_FILES:
        payload = _with_logical_fingerprint(payloads[name])
        raw = _canonical_bytes(payload)
        path = target / name
        _write_new(path, raw)
        artifact_rows.append({
            "name": name,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "logical_content_fingerprint": payload["logical_content_fingerprint"],
        })
    logical_payload = {
        **base,
        "artifacts": artifact_rows,
        "composite_fingerprints": [item.logical_fingerprint for item in composites],
        "oracle_fingerprints": [item.oracle_fingerprint for item in oracle_reports],
        "oracle_mismatch_count": sum(item.mismatch_count for item in oracle_reports),
        "external_request_count": 0,
        "production_write_count": 0,
    }
    aggregate = _fingerprint(logical_payload)
    manifest = {
        **logical_payload,
        "logical_content_fingerprint": aggregate,
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "peak_memory_kib": peak_memory_kib,
        "completion_status": "completed",
    }
    _write_new(target / AUDIT_MANIFEST, _canonical_bytes(manifest))
    for path in target.iterdir():
        path.chmod(0o400)
    return read_market_regime_audit(target)


def read_market_regime_audit(output_dir: Path) -> dict[str, Any]:
    manifest, _, _ = _read_market_regime_audit(output_dir)
    return manifest


def read_market_regime_audit_contents(output_dir: Path) -> MarketRegimeAuditContents:
    """Reread a completed audit once and return its typed downstream inputs."""

    manifest, payloads, composites = _read_market_regime_audit(output_dir)
    return MarketRegimeAuditContents(
        manifest=manifest,
        input_manifest=payloads["input-manifest.json"],
        composites=composites,
    )


def _read_market_regime_audit(
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], tuple[MarketRegimeCompositeV1, ...]]:
    if output_dir.is_symlink():
        raise MarketRegimeAuditError("symlink audit directory is rejected")
    target = output_dir.resolve(strict=True)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.parent != Path("/tmp")
        or target.stat().st_uid != os.geteuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
    ):
        raise MarketRegimeAuditError("audit directory must be a regular direct child of /tmp")
    expected = set(ARTIFACT_FILES) | {AUDIT_MANIFEST}
    actual = {item.name for item in target.iterdir()}
    if actual != expected or any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise MarketRegimeAuditError("audit file set is incomplete or unsafe")
    manifest_path = target / AUDIT_MANIFEST
    manifest = _read_canonical_json(manifest_path)
    if manifest.get("completion_status") != "completed":
        raise MarketRegimeAuditError("audit manifest is not completed")
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "elapsed_seconds", "peak_memory_kib", "completion_status"}
    }
    if _fingerprint(logical) != manifest.get("logical_content_fingerprint"):
        raise MarketRegimeAuditError("audit logical fingerprint mismatch")
    rows = {item["name"]: item for item in manifest.get("artifacts", [])}
    if tuple(item["name"] for item in manifest.get("artifacts", [])) != ARTIFACT_FILES:
        raise MarketRegimeAuditError("audit artifact order mismatch")
    payloads: dict[str, dict[str, Any]] = {}
    for name in ARTIFACT_FILES:
        path = target / name
        raw = path.read_bytes()
        item = rows[name]
        if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise MarketRegimeAuditError(f"audit artifact hash mismatch: {name}")
        payload = _read_canonical_json(path)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if _fingerprint(payload) != fingerprint or fingerprint != item["logical_content_fingerprint"]:
            raise MarketRegimeAuditError(f"audit artifact logical fingerprint mismatch: {name}")
        payloads[name] = payload
    composites_payload = payloads["composite.json"]
    composites = tuple(MarketRegimeCompositeV1.model_validate(item) for item in composites_payload["records"])
    oracle_payload = payloads["oracle-report.json"]
    oracles = tuple(OracleComparisonV1.model_validate(item) for item in oracle_payload["records"])
    explanations_payload = payloads["explanation-ledger.json"]
    tuple(ExplanationLedgerEntryV1.model_validate(item) for item in explanations_payload["records"])
    if [item.logical_fingerprint for item in composites] != manifest["composite_fingerprints"]:
        raise MarketRegimeAuditError("composite fingerprint ledger mismatch")
    if (
        tuple(item.universe_id for item in composites) != tuple(manifest.get("universe_ids", ()))
        or any(item.as_of_session.isoformat() != manifest.get("as_of_session") for item in composites)
        or any(item.parameter_set_fingerprint != PARAMETER_SET_FINGERPRINT for item in composites)
    ):
        raise MarketRegimeAuditError("Phase 1a Composite contract binding mismatch")
    if [item.oracle_fingerprint for item in oracles] != manifest["oracle_fingerprints"]:
        raise MarketRegimeAuditError("oracle fingerprint ledger mismatch")
    if (
        manifest.get("oracle_mismatch_count") != 0
        or any(item.mismatch_count != 0 or item.mismatches for item in oracles)
    ):
        raise MarketRegimeAuditError("Phase 1a Oracle equivalence gate did not pass")
    return manifest, payloads, composites


def validate_tmp_output_dir(output_dir: Path) -> Path:
    if not output_dir.is_absolute():
        raise MarketRegimeAuditError("output directory must be absolute")
    lexical = output_dir
    if lexical.parent != Path("/tmp") or lexical.name in {"", ".", ".."}:
        raise MarketRegimeAuditError("output directory must be a direct child of /tmp")
    current = Path("/")
    for part in lexical.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise MarketRegimeAuditError("symlink output path is rejected")
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir():
            raise MarketRegimeAuditError("existing output path is unsafe")
        if any(output_dir.iterdir()):
            raise MarketRegimeAuditError("existing non-empty output directory is rejected")
        metadata = output_dir.stat()
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise MarketRegimeAuditError("existing output directory must be owned by the caller with mode 0700")
        return output_dir.resolve(strict=True)
    return output_dir


def _with_logical_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["logical_content_fingerprint"] = _fingerprint(payload)
    return value


def _canonical_bytes(value: object) -> bytes:
    normalized = _normalize_nfc(value)
    return (json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


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
        raise MarketRegimeAuditError(f"malformed audit JSON: {path.name}") from exc
    if raw != _canonical_bytes(value):
        raise MarketRegimeAuditError(f"non-canonical audit JSON: {path.name}")
    if not isinstance(value, dict):
        raise MarketRegimeAuditError("audit artifact must be an object")
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
