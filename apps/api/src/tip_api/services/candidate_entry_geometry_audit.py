"""Canonical governed audit for the Candidate entry-geometry shadow layer."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from tip_api.contracts.analytics.v1 import CandidateEntryGeometryBatchV1
from tip_api.parameters.market_regime.candidate_entry_v1_0_0 import (
    ENTRY_GEOMETRY_CALCULATION_VERSION,
    ENTRY_GEOMETRY_CONTRACT_VERSION,
    ENTRY_GEOMETRY_PARAMETER_FINGERPRINT,
    ENTRY_GEOMETRY_PARAMETER_SET_ID,
    entry_geometry_parameter_payload,
)
from tip_api.services.candidate_entry_geometry_oracle import (
    CandidateEntryGeometryOracleComparisonV1,
)
from tip_api.services.offline_artifact_custody import (
    OfflineArtifactCustodyError,
    validate_offline_artifact_location,
)


ENTRY_GEOMETRY_ARTIFACT_FILES = (
    "entry-geometry-parameter-contract.json",
    "entry-geometry-batches.json",
    "entry-geometry-oracle-report.json",
)
ENTRY_GEOMETRY_AUDIT_MANIFEST = "entry-geometry-audit-manifest.json"


class CandidateEntryGeometryAuditError(RuntimeError):
    """Raised when the shadow audit cannot preserve its custody boundary."""


def write_candidate_entry_geometry_audit(
    *,
    output_dir: Path,
    candidate_audit_dir: Path,
    candidate_audit_manifest: Mapping[str, Any],
    batches: Sequence[CandidateEntryGeometryBatchV1],
    oracle_reports: Sequence[CandidateEntryGeometryOracleComparisonV1],
    generated_at: datetime,
) -> dict[str, Any]:
    target = validate_entry_geometry_tmp_output_dir(output_dir)
    target.mkdir(mode=0o700, parents=False, exist_ok=True)
    target.chmod(0o700)
    if any(target.iterdir()):
        raise CandidateEntryGeometryAuditError("existing non-empty output directory is rejected")
    ordered_batches = tuple(batches)
    ordered_oracles = tuple(oracle_reports)
    if not ordered_batches or len(ordered_batches) != len(ordered_oracles):
        raise CandidateEntryGeometryAuditError("one Oracle report is required per entry-geometry batch")
    if any(item.mismatch_count or item.mismatches or not item.input_permutation_match for item in ordered_oracles):
        raise CandidateEntryGeometryAuditError("entry-geometry Oracle gates must pass before audit write")
    if len({item.universe_id for item in ordered_batches}) != len(ordered_batches):
        raise CandidateEntryGeometryAuditError("entry-geometry audit Universe batches must be unique")
    if len({item.as_of_session for item in ordered_batches}) != 1:
        raise CandidateEntryGeometryAuditError("entry-geometry audit batches must share one as-of session")
    candidate_manifest_path = candidate_audit_dir / "candidate-audit-manifest.json"
    if not candidate_manifest_path.is_file() or candidate_manifest_path.is_symlink():
        raise CandidateEntryGeometryAuditError("Candidate audit manifest source is unsafe")
    candidate_manifest_raw = candidate_manifest_path.read_bytes()
    try:
        candidate_manifest_on_disk = json.loads(candidate_manifest_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateEntryGeometryAuditError("Candidate audit manifest source is malformed") from exc
    if candidate_manifest_on_disk != dict(candidate_audit_manifest):
        raise CandidateEntryGeometryAuditError("Candidate audit manifest argument differs from its source file")
    candidate_manifest_sha = hashlib.sha256(candidate_manifest_raw).hexdigest()
    source = {
        "candidate_audit_logical_fingerprint": candidate_audit_manifest["logical_content_fingerprint"],
        "candidate_audit_manifest_sha256": candidate_manifest_sha,
        "candidate_calculation_version": candidate_audit_manifest["candidate_calculation_version"],
        "candidate_parameter_fingerprint": candidate_audit_manifest["candidate_parameter_fingerprint"],
        "candidate_state_parameter_fingerprint": candidate_audit_manifest["candidate_state_parameter_fingerprint"],
        "candidate_audit_as_of_session": candidate_audit_manifest["as_of_session"],
    }
    base = {
        "schema_version": "1.0",
        "contract_version": ENTRY_GEOMETRY_CONTRACT_VERSION,
        "calculation_version": ENTRY_GEOMETRY_CALCULATION_VERSION,
        "parameter_set_id": ENTRY_GEOMETRY_PARAMETER_SET_ID,
        "parameter_fingerprint": ENTRY_GEOMETRY_PARAMETER_FINGERPRINT,
        "as_of_session": ordered_batches[0].as_of_session.isoformat(),
        "universe_ids": [item.universe_id for item in ordered_batches],
        "source": source,
        "shadow_only": True,
        "production_write_count": 0,
        "external_request_count": 0,
    }
    payloads = {
        "entry-geometry-parameter-contract.json": {
            **base,
            "parameter_contract": entry_geometry_parameter_payload(),
        },
        "entry-geometry-batches.json": {
            **base,
            "records": [item.model_dump(mode="json") for item in ordered_batches],
        },
        "entry-geometry-oracle-report.json": {
            **base,
            "records": [asdict(item) for item in ordered_oracles],
        },
    }
    artifacts = []
    for name in ENTRY_GEOMETRY_ARTIFACT_FILES:
        payload = payloads[name]
        payload["logical_content_fingerprint"] = _fingerprint(payload)
        raw = _canonical_bytes(payload)
        _write_new(target / name, raw)
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
        "batch_fingerprints": [item.logical_fingerprint for item in ordered_batches],
        "oracle_fingerprints": [item.oracle_fingerprint for item in ordered_oracles],
        "oracle_mismatch_count": sum(item.mismatch_count for item in ordered_oracles),
        "input_permutation_match": all(item.input_permutation_match for item in ordered_oracles),
        "artifacts": artifacts,
    }
    manifest = {
        **logical,
        "logical_content_fingerprint": _fingerprint(logical),
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "completion_status": "completed",
    }
    _write_new(target / ENTRY_GEOMETRY_AUDIT_MANIFEST, _canonical_bytes(manifest))
    for path in target.iterdir():
        path.chmod(0o400)
    return read_candidate_entry_geometry_audit(target)


def read_candidate_entry_geometry_audit(output_dir: Path) -> dict[str, Any]:
    target = _safe_completed_directory(output_dir)
    expected = set(ENTRY_GEOMETRY_ARTIFACT_FILES) | {ENTRY_GEOMETRY_AUDIT_MANIFEST}
    if {item.name for item in target.iterdir()} != expected:
        raise CandidateEntryGeometryAuditError("entry-geometry audit file set is incomplete or contains extras")
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise CandidateEntryGeometryAuditError("unsafe entry-geometry audit artifact")
    manifest = _read_canonical_json(target / ENTRY_GEOMETRY_AUDIT_MANIFEST)
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "completion_status"}
    }
    if manifest.get("completion_status") != "completed" or _fingerprint(logical) != manifest.get(
        "logical_content_fingerprint"
    ):
        raise CandidateEntryGeometryAuditError("entry-geometry manifest fingerprint mismatch")
    if manifest.get("shadow_only") is not True or manifest.get("production_write_count") != 0:
        raise CandidateEntryGeometryAuditError("entry-geometry audit escaped its shadow-only boundary")
    if manifest.get("parameter_fingerprint") != ENTRY_GEOMETRY_PARAMETER_FINGERPRINT:
        raise CandidateEntryGeometryAuditError("entry-geometry parameter fingerprint mismatch")
    payloads = {}
    for artifact in manifest.get("artifacts", ()):
        name = artifact.get("name")
        if name not in ENTRY_GEOMETRY_ARTIFACT_FILES:
            raise CandidateEntryGeometryAuditError("entry-geometry manifest artifact order differs")
        raw = (target / name).read_bytes()
        if len(raw) != artifact.get("bytes") or hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
            raise CandidateEntryGeometryAuditError(f"entry-geometry artifact custody mismatch: {name}")
        payload = _read_canonical_json(target / name)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if _fingerprint(payload) != fingerprint or fingerprint != artifact.get("logical_content_fingerprint"):
            raise CandidateEntryGeometryAuditError(f"entry-geometry artifact fingerprint mismatch: {name}")
        payloads[name] = payload
    if tuple(item.get("name") for item in manifest.get("artifacts", ())) != ENTRY_GEOMETRY_ARTIFACT_FILES:
        raise CandidateEntryGeometryAuditError("entry-geometry artifact order mismatch")
    if payloads["entry-geometry-parameter-contract.json"].get("parameter_contract") != entry_geometry_parameter_payload():
        raise CandidateEntryGeometryAuditError("entry-geometry parameter contract differs")
    batches = tuple(
        CandidateEntryGeometryBatchV1.model_validate(item)
        for item in payloads["entry-geometry-batches.json"].get("records", ())
    )
    if [item.logical_fingerprint for item in batches] != manifest.get("batch_fingerprints"):
        raise CandidateEntryGeometryAuditError("entry-geometry typed batch fingerprints differ")
    for batch in batches:
        for record in batch.records:
            expected_record = _fingerprint(record.model_dump(mode="json", exclude={"logical_fingerprint"}))
            if expected_record != record.logical_fingerprint:
                raise CandidateEntryGeometryAuditError("entry-geometry record fingerprint differs")
        expected_batch = _fingerprint(batch.model_dump(mode="json", exclude={"logical_fingerprint"}))
        if expected_batch != batch.logical_fingerprint:
            raise CandidateEntryGeometryAuditError("entry-geometry batch fingerprint differs")
    oracle_rows = payloads["entry-geometry-oracle-report.json"].get("records", ())
    if (
        not isinstance(oracle_rows, list)
        or len(oracle_rows) != len(batches)
        or any(item.get("mismatch_count") != 0 or item.get("mismatches") or item.get("input_permutation_match") is not True for item in oracle_rows)
        or [item.get("oracle_fingerprint") for item in oracle_rows] != manifest.get("oracle_fingerprints")
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("input_permutation_match") is not True
    ):
        raise CandidateEntryGeometryAuditError("entry-geometry Oracle gates did not pass")
    return manifest


def validate_entry_geometry_tmp_output_dir(output_dir: Path) -> Path:
    try:
        validate_offline_artifact_location(
            output_dir,
            persistent_names={"entry-geometry"},
        )
    except OfflineArtifactCustodyError as exc:
        raise CandidateEntryGeometryAuditError(
            f"output directory custody differs: {exc}"
        ) from exc
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise CandidateEntryGeometryAuditError("existing output path is unsafe or non-empty")
        metadata = output_dir.stat()
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise CandidateEntryGeometryAuditError("existing output directory custody mismatch")
    return output_dir


def _safe_completed_directory(path: Path) -> Path:
    try:
        validate_offline_artifact_location(
            path,
            persistent_names={"entry-geometry"},
        )
    except OfflineArtifactCustodyError as exc:
        raise CandidateEntryGeometryAuditError(
            f"audit directory custody differs: {exc}"
        ) from exc
    target = path.resolve(strict=True)
    metadata = target.stat()
    if not target.is_dir() or metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateEntryGeometryAuditError("unsafe entry-geometry audit directory")
    return target


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
        raise CandidateEntryGeometryAuditError("malformed entry-geometry JSON") from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise CandidateEntryGeometryAuditError("entry-geometry JSON is not canonically encoded")
    return payload


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
