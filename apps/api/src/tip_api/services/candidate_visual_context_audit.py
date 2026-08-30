"""Atomic, tmp-only audit for Candidate Visual Context 1.0."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from tip_api.contracts.analytics.v1 import (
    CandidateVisualContextBatchV1,
    VISUAL_CONTEXT_CALCULATION_VERSION,
    VISUAL_CONTEXT_CONTRACT_VERSION,
)
from tip_api.services.candidate_visual_context_oracle import (
    CandidateVisualContextOracleComparisonV1,
)


VISUAL_CONTEXT_AUDIT_CONTRACT_VERSION = "candidate-visual-context-audit/1.0"
VISUAL_CONTEXT_AUDIT_FILES = (
    "visual-context-batches.json",
    "visual-context-oracle-reports.json",
)
VISUAL_CONTEXT_AUDIT_MANIFEST = "visual-context-audit-manifest.json"
COMMON_FIELDS = (
    "schema_version",
    "audit_contract_version",
    "contract_version",
    "calculation_version",
    "as_of_session",
    "universe_ids",
    "source",
    "shadow_only",
    "strategy_score_input",
    "outcome_or_performance_claim",
    "production_write_count",
    "external_request_count",
)


class CandidateVisualContextAuditError(RuntimeError):
    """Raised when visual-context audit custody or reconciliation fails."""


def write_candidate_visual_context_audit(
    *,
    output_dir: Path,
    candidate_audit_dir: Path,
    candidate_audit_manifest: Mapping[str, Any],
    entry_geometry_audit_dir: Path,
    entry_geometry_audit_manifest: Mapping[str, Any],
    panel_cache_entry_dir: Path,
    panel_cache_manifest: Mapping[str, Any],
    batches: Sequence[CandidateVisualContextBatchV1],
    oracle_reports: Sequence[CandidateVisualContextOracleComparisonV1],
    generated_at: datetime,
) -> dict[str, Any]:
    target = validate_visual_context_tmp_output_dir(output_dir)
    batches = tuple(batches)
    reports = tuple(oracle_reports)
    if not batches or len(batches) != len(reports):
        raise CandidateVisualContextAuditError(
            "one visual-context Oracle report is required per batch"
        )
    if any(
        report.mismatch_count
        or report.mismatches
        or not report.input_permutation_match
        or report.production_calculator_imported
        for report in reports
    ):
        raise CandidateVisualContextAuditError(
            "visual-context Oracle gates must pass before audit write"
        )
    universe_ids = tuple(batch.universe_id for batch in batches)
    if len(set(universe_ids)) != len(universe_ids) or len({batch.as_of_session for batch in batches}) != 1:
        raise CandidateVisualContextAuditError(
            "visual-context batches require unique Universes and one session"
        )
    candidate_source = _source_binding(
        directory=candidate_audit_dir,
        filename="candidate-audit-manifest.json",
        supplied=candidate_audit_manifest,
        label="Candidate",
    )
    entry_source = _source_binding(
        directory=entry_geometry_audit_dir,
        filename="entry-geometry-audit-manifest.json",
        supplied=entry_geometry_audit_manifest,
        label="Entry Geometry",
    )
    panel_source = _source_binding(
        directory=panel_cache_entry_dir,
        filename="manifest.json",
        supplied=panel_cache_manifest,
        label="panel cache",
    )
    as_of = batches[0].as_of_session.isoformat()
    if (
        candidate_audit_manifest.get("as_of_session") != as_of
        or entry_geometry_audit_manifest.get("as_of_session") != as_of
        or tuple(candidate_audit_manifest.get("universe_ids", ())) != universe_ids
        or tuple(entry_geometry_audit_manifest.get("universe_ids", ())) != universe_ids
        or tuple(candidate_audit_manifest.get("candidate_batch_fingerprints", ())[-len(batches):])
        != tuple(batch.source_candidate_batch_fingerprint for batch in batches)
        or tuple(entry_geometry_audit_manifest.get("batch_fingerprints", ()))
        != tuple(batch.source_entry_geometry_batch_fingerprint for batch in batches)
    ):
        raise CandidateVisualContextAuditError(
            "visual-context Candidate or Entry source binding differs"
        )
    boundary = panel_cache_manifest.get("source_boundary")
    boundary_universes = boundary.get("universes", ()) if isinstance(boundary, Mapping) else ()
    if (
        not isinstance(boundary, Mapping)
        or boundary.get("as_of_session") != as_of
        or tuple(
            item.get("universe_id")
            for item in boundary_universes
            if isinstance(item, Mapping)
        )
        != universe_ids
        or any(
            batch.source_history_fingerprint != boundary.get("history_source_fingerprint")
            for batch in batches
        )
    ):
        raise CandidateVisualContextAuditError(
            "visual-context panel-cache source binding differs"
        )
    base = {
        "schema_version": "1.0",
        "audit_contract_version": VISUAL_CONTEXT_AUDIT_CONTRACT_VERSION,
        "contract_version": VISUAL_CONTEXT_CONTRACT_VERSION,
        "calculation_version": VISUAL_CONTEXT_CALCULATION_VERSION,
        "as_of_session": as_of,
        "universe_ids": list(universe_ids),
        "source": {
            "candidate_audit": candidate_source,
            "entry_geometry_audit": entry_source,
            "panel_cache": panel_source,
        },
        "shadow_only": True,
        "strategy_score_input": False,
        "outcome_or_performance_claim": False,
        "production_write_count": 0,
        "external_request_count": 0,
    }
    payloads = {
        "visual-context-batches.json": {
            **base,
            "records": [batch.model_dump(mode="json") for batch in batches],
        },
        "visual-context-oracle-reports.json": {
            **base,
            "records": [asdict(report) for report in reports],
        },
    }
    staging = target.with_name(f".{target.name}.partial-{uuid4().hex}")
    staging.mkdir(mode=0o700)
    try:
        artifacts = []
        for name in VISUAL_CONTEXT_AUDIT_FILES:
            payload = payloads[name]
            payload["logical_content_fingerprint"] = _fingerprint(payload)
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
            "batch_fingerprints": [batch.logical_fingerprint for batch in batches],
            "state_history_fingerprints": [batch.source_state_history_fingerprint for batch in batches],
            "oracle_fingerprints": [report.oracle_fingerprint for report in reports],
            "oracle_mismatch_count": 0,
            "input_permutation_match": True,
            "production_calculator_imported_by_oracle": False,
            "record_count": sum(batch.record_count for batch in batches),
            "price_path_availability_counts": _sum_counts(
                batch.price_path_availability_counts for batch in batches
            ),
            "state_age_availability_counts": _sum_counts(
                batch.state_age_availability_counts for batch in batches
            ),
            "artifacts": artifacts,
        }
        manifest = {
            **logical,
            "logical_content_fingerprint": _fingerprint(logical),
            "generated_at": generated_at.astimezone(UTC).isoformat(),
            "completion_status": "completed",
        }
        _write_new(staging / VISUAL_CONTEXT_AUDIT_MANIFEST, _canonical_bytes(manifest))
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
    return read_candidate_visual_context_audit(target)


def read_candidate_visual_context_audit(output_dir: Path) -> dict[str, Any]:
    target = _safe_completed_directory(output_dir)
    expected = set(VISUAL_CONTEXT_AUDIT_FILES) | {VISUAL_CONTEXT_AUDIT_MANIFEST}
    if {item.name for item in target.iterdir()} != expected:
        raise CandidateVisualContextAuditError(
            "visual-context audit file set is incomplete or contains extras"
        )
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise CandidateVisualContextAuditError("unsafe visual-context audit artifact")
    manifest = _read_canonical_json(target / VISUAL_CONTEXT_AUDIT_MANIFEST)
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "completion_status"}
    }
    if (
        manifest.get("completion_status") != "completed"
        or manifest.get("logical_content_fingerprint") != _fingerprint(logical)
        or manifest.get("audit_contract_version") != VISUAL_CONTEXT_AUDIT_CONTRACT_VERSION
        or manifest.get("contract_version") != VISUAL_CONTEXT_CONTRACT_VERSION
        or manifest.get("calculation_version") != VISUAL_CONTEXT_CALCULATION_VERSION
        or manifest.get("shadow_only") is not True
        or manifest.get("strategy_score_input") is not False
        or manifest.get("outcome_or_performance_claim") is not False
        or manifest.get("production_write_count") != 0
        or manifest.get("external_request_count") != 0
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("input_permutation_match") is not True
        or manifest.get("production_calculator_imported_by_oracle") is not False
    ):
        raise CandidateVisualContextAuditError(
            "visual-context manifest or safety gate differs"
        )
    artifacts = manifest.get("artifacts", ())
    if tuple(item.get("name") for item in artifacts) != VISUAL_CONTEXT_AUDIT_FILES:
        raise CandidateVisualContextAuditError("visual-context artifact order differs")
    payloads = {}
    for artifact in artifacts:
        name = artifact["name"]
        raw = (target / name).read_bytes()
        if len(raw) != artifact.get("bytes") or hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
            raise CandidateVisualContextAuditError(
                f"visual-context artifact custody mismatch: {name}"
            )
        payload = _read_canonical_json(target / name)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if (
            _fingerprint(payload) != fingerprint
            or fingerprint != artifact.get("logical_content_fingerprint")
            or any(payload.get(field) != manifest.get(field) for field in COMMON_FIELDS)
        ):
            raise CandidateVisualContextAuditError(
                f"visual-context artifact fingerprint mismatch: {name}"
            )
        payloads[name] = payload
    batches = tuple(
        CandidateVisualContextBatchV1.model_validate(item)
        for item in payloads["visual-context-batches.json"].get("records", ())
    )
    reports = payloads["visual-context-oracle-reports.json"].get("records", ())
    if (
        [batch.logical_fingerprint for batch in batches] != manifest.get("batch_fingerprints")
        or [batch.source_state_history_fingerprint for batch in batches]
        != manifest.get("state_history_fingerprints")
        or tuple(batch.universe_id for batch in batches) != tuple(manifest.get("universe_ids", ()))
        or any(batch.as_of_session.isoformat() != manifest.get("as_of_session") for batch in batches)
        or sum(batch.record_count for batch in batches) != manifest.get("record_count")
        or _sum_counts(batch.price_path_availability_counts for batch in batches)
        != manifest.get("price_path_availability_counts")
        or _sum_counts(batch.state_age_availability_counts for batch in batches)
        != manifest.get("state_age_availability_counts")
        or not isinstance(reports, list)
        or len(reports) != len(batches)
        or any(
            report.get("mismatch_count") != 0
            or report.get("mismatches")
            or report.get("input_permutation_match") is not True
            or report.get("production_calculator_imported") is not False
            or report.get("record_count") != batch.record_count
            for report, batch in zip(reports, batches, strict=True)
        )
        or [report.get("oracle_fingerprint") for report in reports]
        != manifest.get("oracle_fingerprints")
    ):
        raise CandidateVisualContextAuditError(
            "visual-context typed batch or Oracle ledger differs"
        )
    return manifest


def validate_visual_context_tmp_output_dir(output_dir: Path) -> Path:
    if not output_dir.is_absolute() or output_dir.parent != Path("/tmp") or output_dir.name in {"", ".", ".."}:
        raise CandidateVisualContextAuditError(
            "visual-context output directory must be a direct child of /tmp"
        )
    current = Path("/")
    for part in output_dir.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise CandidateVisualContextAuditError("symlink output path is rejected")
    if output_dir.exists():
        raise CandidateVisualContextAuditError(
            "visual-context audit output path must not already exist"
        )
    return output_dir


def _sum_counts(values):
    result: dict[str, int] = {}
    for counts in values:
        for key, value in counts.items():
            result[key] = result.get(key, 0) + value
    return dict(sorted(result.items()))


def _source_binding(*, directory, filename, supplied, label):
    path = directory / filename
    if path.is_symlink() or not path.is_file():
        raise CandidateVisualContextAuditError(f"{label} manifest source is unsafe")
    raw = path.read_bytes()
    try:
        on_disk = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateVisualContextAuditError(f"{label} manifest source is malformed") from exc
    if on_disk != dict(supplied):
        raise CandidateVisualContextAuditError(
            f"{label} manifest argument differs from source file"
        )
    return {
        "logical_content_fingerprint": supplied["logical_content_fingerprint"],
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _safe_completed_directory(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise CandidateVisualContextAuditError(
            "visual-context audit directory must be absolute and not a symlink"
        )
    target = path.resolve(strict=True)
    metadata = target.stat()
    if not target.is_dir() or metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateVisualContextAuditError("unsafe visual-context audit directory")
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
        raise CandidateVisualContextAuditError("malformed visual-context audit JSON") from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise CandidateVisualContextAuditError(
            "visual-context audit JSON is not canonically encoded"
        )
    return payload


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value).rstrip(b"\n")).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
