"""Atomic, tmp-only audit for descriptive Candidate continuation facts."""

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

from tip_api.contracts.analytics.v1 import CandidateContinuationFactsBatchV1
from tip_api.parameters.market_regime.candidate_continuation_facts_v1_1_0 import (
    CONTINUATION_FACTS_CALCULATION_VERSION,
    CONTINUATION_FACTS_CONTRACT_VERSION,
    CONTINUATION_FACTS_PARAMETER_FINGERPRINT,
    CONTINUATION_FACTS_PARAMETER_SET_ID,
    continuation_facts_parameter_payload,
)
from tip_api.services.candidate_continuation_facts_oracle import (
    CandidateContinuationFactsOracleComparisonV1,
)


CONTINUATION_FACTS_AUDIT_CONTRACT_VERSION = "candidate-continuation-facts-audit/1.0"
CONTINUATION_FACTS_AUDIT_FILES = (
    "continuation-facts-parameter-contract.json",
    "continuation-facts-batches.json",
    "continuation-facts-oracle-reports.json",
)
CONTINUATION_FACTS_AUDIT_MANIFEST = "continuation-facts-audit-manifest.json"
CONTINUATION_FACTS_COMMON_FIELDS = (
    "schema_version",
    "audit_contract_version",
    "contract_version",
    "calculation_version",
    "parameter_set_id",
    "parameter_fingerprint",
    "as_of_session",
    "universe_ids",
    "source",
    "shadow_only",
    "strategy_score_input",
    "outcome_or_performance_claim",
    "production_write_count",
    "external_request_count",
)


class CandidateContinuationFactsAuditError(RuntimeError):
    """Raised when continuation-fact audit custody or reconciliation fails."""


def write_candidate_continuation_facts_audit(
    *,
    output_dir: Path,
    candidate_audit_dir: Path,
    candidate_audit_manifest: Mapping[str, Any],
    entry_geometry_audit_dir: Path,
    entry_geometry_audit_manifest: Mapping[str, Any],
    panel_cache_entry_dir: Path,
    panel_cache_manifest: Mapping[str, Any],
    batches: Sequence[CandidateContinuationFactsBatchV1],
    oracle_reports: Sequence[CandidateContinuationFactsOracleComparisonV1],
    generated_at: datetime,
) -> dict[str, Any]:
    """Write one complete shadow audit atomically, then formally reread it."""

    target = validate_continuation_facts_tmp_output_dir(output_dir)
    ordered_batches = tuple(batches)
    ordered_oracles = tuple(oracle_reports)
    if not ordered_batches or len(ordered_batches) != len(ordered_oracles):
        raise CandidateContinuationFactsAuditError(
            "one Oracle report is required per continuation-fact batch"
        )
    if any(
        item.mismatch_count
        or item.mismatches
        or not item.input_permutation_match
        or item.production_calculator_imported
        for item in ordered_oracles
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact Oracle gates must pass before audit write"
        )
    universe_ids = tuple(item.universe_id for item in ordered_batches)
    if len(set(universe_ids)) != len(universe_ids):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact audit Universes must be unique"
        )
    if len({item.as_of_session for item in ordered_batches}) != 1:
        raise CandidateContinuationFactsAuditError(
            "continuation-fact batches must share one session"
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
    as_of = ordered_batches[0].as_of_session.isoformat()
    if (
        candidate_audit_manifest.get("as_of_session") != as_of
        or entry_geometry_audit_manifest.get("as_of_session") != as_of
        or tuple(candidate_audit_manifest.get("universe_ids", ())) != universe_ids
        or tuple(entry_geometry_audit_manifest.get("universe_ids", ()))
        != universe_ids
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact source session or Universe order differs"
        )
    candidate_fingerprints = tuple(
        item.source_candidate_batch_fingerprint for item in ordered_batches
    )
    entry_fingerprints = tuple(
        item.source_entry_geometry_batch_fingerprint for item in ordered_batches
    )
    if (
        tuple(candidate_audit_manifest.get("candidate_batch_fingerprints", ()))
        [-len(candidate_fingerprints) :]
        != candidate_fingerprints
        or tuple(entry_geometry_audit_manifest.get("batch_fingerprints", ()))
        != entry_fingerprints
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact batch fingerprints differ from source manifests"
        )
    boundary = panel_cache_manifest.get("source_boundary")
    if not isinstance(boundary, Mapping) or (
        boundary.get("as_of_session") != as_of
        or any(
            item.source_history_fingerprint
            != boundary.get("history_source_fingerprint")
            for item in ordered_batches
        )
        or tuple(
            row.get("universe_id")
            for row in boundary.get("universes", ())
            if isinstance(row, Mapping)
        )
        != universe_ids
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact panel-cache lineage differs"
        )

    base = {
        "schema_version": "1.0",
        "audit_contract_version": CONTINUATION_FACTS_AUDIT_CONTRACT_VERSION,
        "contract_version": CONTINUATION_FACTS_CONTRACT_VERSION,
        "calculation_version": CONTINUATION_FACTS_CALCULATION_VERSION,
        "parameter_set_id": CONTINUATION_FACTS_PARAMETER_SET_ID,
        "parameter_fingerprint": CONTINUATION_FACTS_PARAMETER_FINGERPRINT,
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
        "continuation-facts-parameter-contract.json": {
            **base,
            "parameter_contract": continuation_facts_parameter_payload(),
        },
        "continuation-facts-batches.json": {
            **base,
            "records": [item.model_dump(mode="json") for item in ordered_batches],
        },
        "continuation-facts-oracle-reports.json": {
            **base,
            "records": [asdict(item) for item in ordered_oracles],
        },
    }
    staging = target.with_name(f".{target.name}.partial-{uuid4().hex}")
    staging.mkdir(mode=0o700)
    try:
        artifacts = []
        for name in CONTINUATION_FACTS_AUDIT_FILES:
            payload = payloads[name]
            payload["logical_content_fingerprint"] = _fingerprint(payload)
            raw = _canonical_bytes(payload)
            _write_new(staging / name, raw)
            artifacts.append(
                {
                    "name": name,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "logical_content_fingerprint": payload[
                        "logical_content_fingerprint"
                    ],
                }
            )
        logical = {
            **base,
            "batch_fingerprints": [
                item.logical_fingerprint for item in ordered_batches
            ],
            "oracle_fingerprints": [
                item.oracle_fingerprint for item in ordered_oracles
            ],
            "oracle_mismatch_count": sum(
                item.mismatch_count for item in ordered_oracles
            ),
            "input_permutation_match": all(
                item.input_permutation_match for item in ordered_oracles
            ),
            "production_calculator_imported_by_oracle": any(
                item.production_calculator_imported for item in ordered_oracles
            ),
            "assessed_count": sum(item.assessed_count for item in ordered_batches),
            "unavailable_count": sum(
                item.unavailable_count for item in ordered_batches
            ),
            "artifacts": artifacts,
        }
        manifest = {
            **logical,
            "logical_content_fingerprint": _fingerprint(logical),
            "generated_at": generated_at.astimezone(UTC).isoformat(),
            "completion_status": "completed",
        }
        _write_new(
            staging / CONTINUATION_FACTS_AUDIT_MANIFEST,
            _canonical_bytes(manifest),
        )
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
    return read_candidate_continuation_facts_audit(target)


def read_candidate_continuation_facts_audit(output_dir: Path) -> dict[str, Any]:
    """Verify completed files, custody hashes, typed batches, and Oracle gates."""

    target = _safe_completed_directory(output_dir)
    expected = set(CONTINUATION_FACTS_AUDIT_FILES) | {
        CONTINUATION_FACTS_AUDIT_MANIFEST
    }
    if {item.name for item in target.iterdir()} != expected:
        raise CandidateContinuationFactsAuditError(
            "continuation-fact audit file set is incomplete or contains extras"
        )
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise CandidateContinuationFactsAuditError(
            "unsafe continuation-fact audit artifact"
        )
    manifest = _read_canonical_json(target / CONTINUATION_FACTS_AUDIT_MANIFEST)
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "completion_status"}
    }
    if (
        manifest.get("completion_status") != "completed"
        or _fingerprint(logical) != manifest.get("logical_content_fingerprint")
        or manifest.get("shadow_only") is not True
        or manifest.get("strategy_score_input") is not False
        or manifest.get("outcome_or_performance_claim") is not False
        or manifest.get("production_write_count") != 0
        or manifest.get("external_request_count") != 0
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("input_permutation_match") is not True
        or manifest.get("production_calculator_imported_by_oracle") is not False
        or manifest.get("audit_contract_version")
        != CONTINUATION_FACTS_AUDIT_CONTRACT_VERSION
        or manifest.get("contract_version") != CONTINUATION_FACTS_CONTRACT_VERSION
        or manifest.get("calculation_version")
        != CONTINUATION_FACTS_CALCULATION_VERSION
        or manifest.get("parameter_set_id") != CONTINUATION_FACTS_PARAMETER_SET_ID
        or manifest.get("parameter_fingerprint")
        != CONTINUATION_FACTS_PARAMETER_FINGERPRINT
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact manifest or safety gate differs"
        )

    artifacts = manifest.get("artifacts", ())
    if tuple(item.get("name") for item in artifacts) != CONTINUATION_FACTS_AUDIT_FILES:
        raise CandidateContinuationFactsAuditError(
            "continuation-fact artifact order differs"
        )
    payloads = {}
    for artifact in artifacts:
        name = artifact["name"]
        raw = (target / name).read_bytes()
        if (
            len(raw) != artifact.get("bytes")
            or hashlib.sha256(raw).hexdigest() != artifact.get("sha256")
        ):
            raise CandidateContinuationFactsAuditError(
                f"continuation-fact artifact custody mismatch: {name}"
            )
        payload = _read_canonical_json(target / name)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if (
            _fingerprint(payload) != fingerprint
            or fingerprint != artifact.get("logical_content_fingerprint")
            or any(
                payload.get(field) != manifest.get(field)
                for field in CONTINUATION_FACTS_COMMON_FIELDS
            )
        ):
            raise CandidateContinuationFactsAuditError(
                f"continuation-fact artifact fingerprint mismatch: {name}"
            )
        payloads[name] = payload
    if (
        payloads["continuation-facts-parameter-contract.json"].get(
            "parameter_contract"
        )
        != continuation_facts_parameter_payload()
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact parameter contract differs"
        )
    batches = tuple(
        CandidateContinuationFactsBatchV1.model_validate(item)
        for item in payloads["continuation-facts-batches.json"].get("records", ())
    )
    if (
        [item.logical_fingerprint for item in batches]
        != manifest.get("batch_fingerprints")
        or tuple(item.universe_id for item in batches)
        != tuple(manifest.get("universe_ids", ()))
        or any(
            item.as_of_session.isoformat() != manifest.get("as_of_session")
            for item in batches
        )
        or sum(item.assessed_count for item in batches)
        != manifest.get("assessed_count")
        or sum(item.unavailable_count for item in batches)
        != manifest.get("unavailable_count")
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact typed batch ledger differs"
        )
    oracle_rows = payloads["continuation-facts-oracle-reports.json"].get(
        "records", ()
    )
    if (
        not isinstance(oracle_rows, list)
        or len(oracle_rows) != len(batches)
        or any(
            item.get("mismatch_count") != 0
            or item.get("mismatches")
            or item.get("input_permutation_match") is not True
            or item.get("production_calculator_imported") is not False
            or item.get("record_count") != len(batch.records)
            for item, batch in zip(oracle_rows, batches, strict=True)
        )
        or [item.get("oracle_fingerprint") for item in oracle_rows]
        != manifest.get("oracle_fingerprints")
    ):
        raise CandidateContinuationFactsAuditError(
            "continuation-fact Oracle gates did not pass"
        )
    return manifest


def validate_continuation_facts_tmp_output_dir(output_dir: Path) -> Path:
    if (
        not output_dir.is_absolute()
        or output_dir.parent != Path("/tmp")
        or output_dir.name in {"", ".", ".."}
    ):
        raise CandidateContinuationFactsAuditError(
            "output directory must be a direct child of /tmp"
        )
    current = Path("/")
    for part in output_dir.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise CandidateContinuationFactsAuditError(
                "symlink output path is rejected"
            )
    if output_dir.exists():
        raise CandidateContinuationFactsAuditError(
            "continuation-fact audit output path must not already exist"
        )
    return output_dir


def _source_binding(*, directory, filename, supplied, label):
    path = directory / filename
    if path.is_symlink() or not path.is_file():
        raise CandidateContinuationFactsAuditError(f"{label} manifest source is unsafe")
    raw = path.read_bytes()
    try:
        on_disk = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateContinuationFactsAuditError(
            f"{label} manifest source is malformed"
        ) from exc
    if on_disk != dict(supplied):
        raise CandidateContinuationFactsAuditError(
            f"{label} manifest argument differs from source file"
        )
    return {
        "logical_content_fingerprint": supplied["logical_content_fingerprint"],
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _safe_completed_directory(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise CandidateContinuationFactsAuditError(
            "continuation-fact audit directory must be absolute and not a symlink"
        )
    target = path.resolve(strict=True)
    metadata = target.stat()
    if (
        not target.is_dir()
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise CandidateContinuationFactsAuditError(
            "unsafe continuation-fact audit directory"
        )
    return target


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateContinuationFactsAuditError(
            "malformed continuation-fact audit JSON"
        ) from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise CandidateContinuationFactsAuditError(
            "continuation-fact audit JSON is not canonically encoded"
        )
    return payload


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
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
