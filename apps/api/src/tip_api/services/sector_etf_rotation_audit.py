"""Atomic, tmp-only custody for Sector ETF Rotation V1."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from tip_api.contracts.analytics.v1.sector_etf_rotation import (
    SectorEtfRotationSnapshotV1,
    SectorRotationOracleComparisonV1,
)
from tip_api.services.market_regime_audit import read_market_regime_audit_contents
from tip_api.services.market_regime_sources import MarketRegimeInputPanel


AUDIT_CONTRACT_VERSION = "sector-etf-rotation-audit/1.0"
AUDIT_FILES = (
    "source-input-manifest.json",
    "sector-rotation-product.json",
    "sector-rotation-oracle-report.json",
)
AUDIT_MANIFEST = "sector-rotation-audit-manifest.json"


class SectorEtfRotationAuditError(RuntimeError):
    """Raised when Sector ETF Rotation audit custody or lineage is invalid."""


@dataclass(frozen=True, slots=True)
class SectorEtfRotationAuditContents:
    """Typed, formally reread inputs for downstream publication consumers."""

    manifest: dict[str, Any]
    product: SectorEtfRotationSnapshotV1
    oracle_report: SectorRotationOracleComparisonV1


def write_sector_etf_rotation_audit(
    *,
    output_dir: Path,
    phase1a_audit_dir: Path,
    panel: MarketRegimeInputPanel,
    product: SectorEtfRotationSnapshotV1,
    oracle_report: SectorRotationOracleComparisonV1,
    generated_at: datetime,
    timings: Mapping[str, str],
) -> dict[str, Any]:
    target = _validate_new_tmp_dir(output_dir)
    source = read_market_regime_audit_contents(phase1a_audit_dir)
    phase1a_input_file = _read_canonical_json(phase1a_audit_dir / "input-manifest.json")
    _validate_lineage(
        panel=panel,
        product=product,
        oracle_report=oracle_report,
        phase1a_manifest=source.manifest,
        phase1a_input=source.input_manifest,
    )
    source_binding = {
        "phase1a_audit_logical_fingerprint": source.manifest["logical_content_fingerprint"],
        "phase1a_manifest_sha256": _sha(phase1a_audit_dir / "calculation-manifest.json"),
        "phase1a_input_logical_fingerprint": phase1a_input_file["logical_content_fingerprint"],
        "phase1a_input_sha256": _sha(phase1a_audit_dir / "input-manifest.json"),
        "history_source_fingerprint": panel.history_source_fingerprint,
        "source_panel_supplied_by_caller": True,
        "canonical_rescan_performed_by_audit_writer": False,
    }
    base = {
        "schema_version": "1.0",
        "audit_contract_version": AUDIT_CONTRACT_VERSION,
        "product_contract_version": product.contract_version,
        "calculation_version": product.calculation_version,
        "parameter_fingerprint": product.parameter_fingerprint,
        "as_of_session": product.as_of_session.isoformat(),
        "source": source_binding,
        "shadow_only": True,
        "market_intelligence_input": False,
        "snapshot_input": False,
        "production_write_count": 0,
        "external_request_count": 0,
    }
    payloads = {
        "source-input-manifest.json": {
            **base,
            "input_first_session": product.input_first_session.isoformat(),
            "input_last_session": product.input_last_session.isoformat(),
            "input_session_count": product.input_session_count,
            "phase1a_source_session_count": len(panel.source_sessions),
        },
        "sector-rotation-product.json": {
            **base,
            "record": product.model_dump(mode="json"),
        },
        "sector-rotation-oracle-report.json": {
            **base,
            "record": oracle_report.model_dump(mode="json"),
        },
    }
    staging = target.with_name(f".{target.name}.partial-{uuid4().hex}")
    staging.mkdir(mode=0o700)
    try:
        artifacts = []
        for name in AUDIT_FILES:
            payload = {**payloads[name], "logical_content_fingerprint": _fingerprint(payloads[name])}
            raw = _canonical_bytes(payload)
            _write_new(staging / name, raw)
            artifacts.append(
                {
                    "name": name,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "logical_content_fingerprint": payload["logical_content_fingerprint"],
                }
            )
        logical = {
            **base,
            "artifacts": artifacts,
            "product_logical_fingerprint": product.logical_fingerprint,
            "record_fingerprints": [item.logical_fingerprint for item in product.records],
            "oracle_mismatch_count": oracle_report.mismatch_count,
            "record_count": len(product.records),
            "theme_status": product.theme_status,
        }
        manifest = {
            **logical,
            "logical_content_fingerprint": _fingerprint(logical),
            "generated_at": generated_at.astimezone(UTC).isoformat(),
            "timings": dict(sorted(timings.items())),
            "completion_status": "completed",
        }
        _write_new(staging / AUDIT_MANIFEST, _canonical_bytes(manifest))
        for path in staging.iterdir():
            path.chmod(0o400)
        _fsync_directory(staging)
        os.rename(staging, target)
        _fsync_directory(target.parent)
    except BaseException:
        if staging.exists():
            for path in staging.iterdir():
                path.chmod(0o600)
                path.unlink()
            staging.rmdir()
        raise
    return read_sector_etf_rotation_audit(target)


def read_sector_etf_rotation_audit(output_dir: Path) -> dict[str, Any]:
    return read_sector_etf_rotation_audit_contents(output_dir).manifest


def read_sector_etf_rotation_audit_contents(
    output_dir: Path,
) -> SectorEtfRotationAuditContents:
    """Reread complete custody once and return only validated typed records."""

    target = _safe_completed_dir(output_dir)
    expected = set(AUDIT_FILES) | {AUDIT_MANIFEST}
    if {item.name for item in target.iterdir()} != expected:
        raise SectorEtfRotationAuditError("sector rotation audit file set differs")
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise SectorEtfRotationAuditError("unsafe sector rotation audit artifact")
    manifest = _read_canonical_json(target / AUDIT_MANIFEST)
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "timings", "completion_status"}
    }
    if (
        manifest.get("completion_status") != "completed"
        or manifest.get("logical_content_fingerprint") != _fingerprint(logical)
        or manifest.get("audit_contract_version") != AUDIT_CONTRACT_VERSION
        or manifest.get("shadow_only") is not True
        or manifest.get("market_intelligence_input") is not False
        or manifest.get("snapshot_input") is not False
        or manifest.get("production_write_count") != 0
        or manifest.get("external_request_count") != 0
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("record_count") != 11
        or manifest.get("theme_status") != "unavailable_no_governed_membership"
    ):
        raise SectorEtfRotationAuditError("sector rotation audit manifest differs")
    artifacts = manifest.get("artifacts", ())
    if tuple(item.get("name") for item in artifacts) != AUDIT_FILES:
        raise SectorEtfRotationAuditError("sector rotation audit artifact order differs")
    payloads: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        name = artifact["name"]
        raw = (target / name).read_bytes()
        if len(raw) != artifact.get("bytes") or hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
            raise SectorEtfRotationAuditError(f"sector rotation artifact custody mismatch: {name}")
        payload = _read_canonical_json(target / name)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if fingerprint != artifact.get("logical_content_fingerprint") or fingerprint != _fingerprint(payload):
            raise SectorEtfRotationAuditError(f"sector rotation artifact fingerprint mismatch: {name}")
        payloads[name] = payload
    product = SectorEtfRotationSnapshotV1.model_validate(
        payloads["sector-rotation-product.json"].get("record")
    )
    oracle = SectorRotationOracleComparisonV1.model_validate(
        payloads["sector-rotation-oracle-report.json"].get("record")
    )
    if (
        product.logical_fingerprint != manifest.get("product_logical_fingerprint")
        or [item.logical_fingerprint for item in product.records] != manifest.get("record_fingerprints")
        or oracle.source_product_fingerprint != product.logical_fingerprint
        or oracle.mismatch_count != 0
        or oracle.mismatches
        or product.source_history_fingerprint
        != manifest.get("source", {}).get("history_source_fingerprint")
    ):
        raise SectorEtfRotationAuditError("sector rotation typed product or Oracle differs")
    return SectorEtfRotationAuditContents(
        manifest=manifest,
        product=product,
        oracle_report=oracle,
    )


def _validate_lineage(*, panel, product, oracle_report, phase1a_manifest, phase1a_input):
    as_of = panel.as_of_session.isoformat()
    if (
        phase1a_manifest.get("completion_status") != "completed"
        or phase1a_manifest.get("oracle_mismatch_count") != 0
        or phase1a_manifest.get("as_of_session") != as_of
        or phase1a_input.get("as_of_session") != as_of
        or phase1a_input.get("history_source_fingerprint") != panel.history_source_fingerprint
        or tuple(phase1a_input.get("history_sessions", ()))
        != tuple(item.isoformat() for item in panel.sessions)
        or product.as_of_session != panel.as_of_session
        or product.input_session_count != len(panel.sessions)
        or product.source_history_fingerprint != panel.history_source_fingerprint
        or oracle_report.source_product_fingerprint != product.logical_fingerprint
        or oracle_report.mismatch_count != 0
        or oracle_report.mismatches
    ):
        raise SectorEtfRotationAuditError("sector rotation Phase 1a or Oracle lineage differs")


def _validate_new_tmp_dir(path: Path) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp") or path.name in {"", ".", ".."}:
        raise SectorEtfRotationAuditError("sector rotation output must be a new direct child of /tmp")
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise SectorEtfRotationAuditError("sector rotation output symlink is rejected")
    if path.exists():
        raise SectorEtfRotationAuditError("sector rotation output already exists")
    return path


def _safe_completed_dir(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise SectorEtfRotationAuditError("sector rotation audit path is unsafe")
    target = path.resolve(strict=True)
    metadata = target.stat()
    if (
        not target.is_dir()
        or target.parent != Path("/tmp")
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise SectorEtfRotationAuditError("sector rotation audit directory custody differs")
    return target


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SectorEtfRotationAuditError("malformed sector rotation audit JSON") from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise SectorEtfRotationAuditError("sector rotation audit JSON is not canonical")
    return payload


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value).rstrip(b"\n")).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
