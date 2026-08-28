"""Atomic, tmp-only audit for the Candidate strategy-channel shadow preview."""

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
    CandidateStrategyChannelBatchV1,
    CandidateStrategyChannelConsumerV1,
)
from tip_api.parameters.market_regime.candidate_strategy_preview_v1_0_0 import (
    STRATEGY_CHANNEL_CALCULATION_VERSION,
    STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
    STRATEGY_CHANNEL_CONTRACT_VERSION,
    STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
    STRATEGY_CHANNEL_PARAMETER_SET_ID,
    strategy_channel_parameter_payload,
)
from tip_api.services.candidate_strategy_channels_oracle import (
    CandidateStrategyChannelOracleComparisonV1,
)


STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION = "candidate-strategy-channel-audit/1.0"
STRATEGY_CHANNEL_ARTIFACT_FILES = (
    "strategy-channel-parameter-contract.json",
    "strategy-channel-batches.json",
    "strategy-channel-consumers.json",
    "strategy-channel-oracle-reports.json",
)
STRATEGY_CHANNEL_AUDIT_MANIFEST = "strategy-channel-audit-manifest.json"


class CandidateStrategyChannelAuditError(RuntimeError):
    """Raised when strategy-channel audit custody or reconciliation fails."""


def write_candidate_strategy_channel_audit(
    *,
    output_dir: Path,
    candidate_audit_dir: Path,
    candidate_audit_manifest: Mapping[str, Any],
    entry_geometry_audit_dir: Path,
    entry_geometry_audit_manifest: Mapping[str, Any],
    batches: Sequence[CandidateStrategyChannelBatchV1],
    consumers: Sequence[CandidateStrategyChannelConsumerV1],
    oracle_reports: Sequence[CandidateStrategyChannelOracleComparisonV1],
    generated_at: datetime,
) -> dict[str, Any]:
    """Write a complete audit by atomic directory rename, then formally reread it."""

    target = validate_strategy_channel_tmp_output_dir(output_dir)
    ordered_batches = tuple(batches)
    ordered_consumers = tuple(consumers)
    ordered_oracles = tuple(oracle_reports)
    if not ordered_batches or not (
        len(ordered_batches) == len(ordered_consumers) == len(ordered_oracles)
    ):
        raise CandidateStrategyChannelAuditError(
            "one consumer and Oracle report are required per strategy batch"
        )
    if any(
        item.mismatch_count
        or item.mismatches
        or not item.input_permutation_match
        or item.production_calculator_imported
        for item in ordered_oracles
    ):
        raise CandidateStrategyChannelAuditError(
            "strategy-channel Oracle gates must pass before audit write"
        )
    universe_ids = tuple(item.universe_id for item in ordered_batches)
    if len(set(universe_ids)) != len(universe_ids):
        raise CandidateStrategyChannelAuditError("strategy audit Universes must be unique")
    if len({item.as_of_session for item in ordered_batches}) != 1:
        raise CandidateStrategyChannelAuditError("strategy batches must share one session")
    for batch, consumer in zip(ordered_batches, ordered_consumers, strict=True):
        if (
            consumer.as_of_session != batch.as_of_session
            or consumer.universe_id != batch.universe_id
            or consumer.source_batch_logical_fingerprint != batch.logical_fingerprint
        ):
            raise CandidateStrategyChannelAuditError(
                "strategy consumer is not bound to its full batch"
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
        label="entry geometry",
    )
    as_of = ordered_batches[0].as_of_session.isoformat()
    if (
        candidate_audit_manifest.get("as_of_session") != as_of
        or entry_geometry_audit_manifest.get("as_of_session") != as_of
        or tuple(candidate_audit_manifest.get("universe_ids", ())) != universe_ids
        or tuple(entry_geometry_audit_manifest.get("universe_ids", ())) != universe_ids
    ):
        raise CandidateStrategyChannelAuditError(
            "strategy audit source session or Universe order differs"
        )
    source_candidate_fingerprints = tuple(
        item.source_candidate_batch_fingerprint for item in ordered_batches
    )
    source_entry_fingerprints = tuple(
        item.source_entry_geometry_batch_fingerprint for item in ordered_batches
    )
    candidate_history_fingerprints = tuple(
        candidate_audit_manifest.get("candidate_batch_fingerprints", ())
    )
    if (
        candidate_history_fingerprints[-len(source_candidate_fingerprints) :]
        != source_candidate_fingerprints
        or tuple(entry_geometry_audit_manifest.get("batch_fingerprints", ()))
        != source_entry_fingerprints
    ):
        raise CandidateStrategyChannelAuditError(
            "strategy batch fingerprints differ from formal source manifests"
        )

    base = {
        "schema_version": "1.0",
        "audit_contract_version": STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION,
        "contract_version": STRATEGY_CHANNEL_CONTRACT_VERSION,
        "consumer_contract_version": STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
        "calculation_version": STRATEGY_CHANNEL_CALCULATION_VERSION,
        "parameter_set_id": STRATEGY_CHANNEL_PARAMETER_SET_ID,
        "parameter_fingerprint": STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
        "as_of_session": as_of,
        "universe_ids": list(universe_ids),
        "source": {
            "candidate_audit": candidate_source,
            "entry_geometry_audit": entry_source,
        },
        "shadow_only": True,
        "production_write_count": 0,
        "external_request_count": 0,
    }
    payloads = {
        "strategy-channel-parameter-contract.json": {
            **base,
            "parameter_contract": strategy_channel_parameter_payload(),
        },
        "strategy-channel-batches.json": {
            **base,
            "records": [item.model_dump(mode="json") for item in ordered_batches],
        },
        "strategy-channel-consumers.json": {
            **base,
            "records": [item.model_dump(mode="json") for item in ordered_consumers],
        },
        "strategy-channel-oracle-reports.json": {
            **base,
            "records": [asdict(item) for item in ordered_oracles],
        },
    }
    staging = target.with_name(f".{target.name}.partial-{uuid4().hex}")
    staging.mkdir(mode=0o700)
    try:
        artifacts = []
        for name in STRATEGY_CHANNEL_ARTIFACT_FILES:
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
            "batch_fingerprints": [item.logical_fingerprint for item in ordered_batches],
            "consumer_fingerprints": [
                item.logical_fingerprint for item in ordered_consumers
            ],
            "oracle_fingerprints": [item.oracle_fingerprint for item in ordered_oracles],
            "oracle_mismatch_count": sum(item.mismatch_count for item in ordered_oracles),
            "input_permutation_match": all(
                item.input_permutation_match for item in ordered_oracles
            ),
            "production_calculator_imported_by_oracle": any(
                item.production_calculator_imported for item in ordered_oracles
            ),
            "artifacts": artifacts,
        }
        manifest = {
            **logical,
            "logical_content_fingerprint": _fingerprint(logical),
            "generated_at": generated_at.astimezone(UTC).isoformat(),
            "completion_status": "completed",
        }
        _write_new(staging / STRATEGY_CHANNEL_AUDIT_MANIFEST, _canonical_bytes(manifest))
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
    return read_candidate_strategy_channel_audit(target)


def read_candidate_strategy_channel_audit(output_dir: Path) -> dict[str, Any]:
    """Verify the completed file set, custody hashes, typed contracts, and gates."""

    target = _safe_completed_directory(output_dir)
    expected = set(STRATEGY_CHANNEL_ARTIFACT_FILES) | {
        STRATEGY_CHANNEL_AUDIT_MANIFEST
    }
    if {item.name for item in target.iterdir()} != expected:
        raise CandidateStrategyChannelAuditError(
            "strategy audit file set is incomplete or contains extras"
        )
    if any(
        item.is_symlink()
        or not item.is_file()
        or item.stat().st_uid != os.geteuid()
        or stat.S_IMODE(item.stat().st_mode) != 0o400
        for item in target.iterdir()
    ):
        raise CandidateStrategyChannelAuditError("unsafe strategy audit artifact")
    manifest = _read_canonical_json(target / STRATEGY_CHANNEL_AUDIT_MANIFEST)
    logical = {
        key: value
        for key, value in manifest.items()
        if key not in {"logical_content_fingerprint", "generated_at", "completion_status"}
    }
    if (
        manifest.get("completion_status") != "completed"
        or _fingerprint(logical) != manifest.get("logical_content_fingerprint")
        or manifest.get("shadow_only") is not True
        or manifest.get("production_write_count") != 0
        or manifest.get("external_request_count") != 0
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("input_permutation_match") is not True
        or manifest.get("production_calculator_imported_by_oracle") is not False
        or manifest.get("audit_contract_version")
        != STRATEGY_CHANNEL_AUDIT_CONTRACT_VERSION
        or manifest.get("contract_version") != STRATEGY_CHANNEL_CONTRACT_VERSION
        or manifest.get("consumer_contract_version")
        != STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION
        or manifest.get("calculation_version")
        != STRATEGY_CHANNEL_CALCULATION_VERSION
        or manifest.get("parameter_set_id") != STRATEGY_CHANNEL_PARAMETER_SET_ID
        or manifest.get("parameter_fingerprint")
        != STRATEGY_CHANNEL_PARAMETER_FINGERPRINT
    ):
        raise CandidateStrategyChannelAuditError(
            "strategy manifest fingerprint or safety gate differs"
        )

    payloads = {}
    artifacts = manifest.get("artifacts", ())
    if tuple(item.get("name") for item in artifacts) != STRATEGY_CHANNEL_ARTIFACT_FILES:
        raise CandidateStrategyChannelAuditError("strategy artifact order differs")
    for artifact in artifacts:
        name = artifact["name"]
        raw = (target / name).read_bytes()
        if (
            len(raw) != artifact.get("bytes")
            or hashlib.sha256(raw).hexdigest() != artifact.get("sha256")
        ):
            raise CandidateStrategyChannelAuditError(
                f"strategy artifact custody mismatch: {name}"
            )
        payload = _read_canonical_json(target / name)
        fingerprint = payload.pop("logical_content_fingerprint", None)
        if (
            _fingerprint(payload) != fingerprint
            or fingerprint != artifact.get("logical_content_fingerprint")
        ):
            raise CandidateStrategyChannelAuditError(
                f"strategy artifact fingerprint mismatch: {name}"
            )
        payloads[name] = payload
    if (
        _canonical_bytes(
            payloads["strategy-channel-parameter-contract.json"].get(
                "parameter_contract"
            )
        )
        != _canonical_bytes(strategy_channel_parameter_payload())
    ):
        raise CandidateStrategyChannelAuditError("strategy parameter contract differs")

    batches = tuple(
        CandidateStrategyChannelBatchV1.model_validate(item)
        for item in payloads["strategy-channel-batches.json"].get("records", ())
    )
    consumers = tuple(
        CandidateStrategyChannelConsumerV1.model_validate(item)
        for item in payloads["strategy-channel-consumers.json"].get("records", ())
    )
    if (
        [item.logical_fingerprint for item in batches]
        != manifest.get("batch_fingerprints")
        or [item.logical_fingerprint for item in consumers]
        != manifest.get("consumer_fingerprints")
        or len(batches) != len(consumers)
        or tuple(item.universe_id for item in batches)
        != tuple(manifest.get("universe_ids", ()))
        or any(
            item.as_of_session.isoformat() != manifest.get("as_of_session")
            for item in batches
        )
        or any(
            consumer.source_batch_logical_fingerprint != batch.logical_fingerprint
            for batch, consumer in zip(batches, consumers, strict=True)
        )
    ):
        raise CandidateStrategyChannelAuditError(
            "strategy typed batch or consumer fingerprints differ"
        )
    oracle_rows = payloads["strategy-channel-oracle-reports.json"].get(
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
        raise CandidateStrategyChannelAuditError("strategy Oracle gates did not pass")
    return manifest


def validate_strategy_channel_tmp_output_dir(output_dir: Path) -> Path:
    if (
        not output_dir.is_absolute()
        or output_dir.parent != Path("/tmp")
        or output_dir.name in {"", ".", ".."}
    ):
        raise CandidateStrategyChannelAuditError(
            "output directory must be a direct child of /tmp"
        )
    current = Path("/")
    for part in output_dir.parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise CandidateStrategyChannelAuditError("symlink output path is rejected")
    if output_dir.exists():
        raise CandidateStrategyChannelAuditError(
            "strategy audit output path must not already exist"
        )
    return output_dir


def _source_binding(*, directory, filename, supplied, label):
    path = directory / filename
    if path.is_symlink() or not path.is_file():
        raise CandidateStrategyChannelAuditError(f"{label} manifest source is unsafe")
    raw = path.read_bytes()
    try:
        on_disk = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateStrategyChannelAuditError(
            f"{label} manifest source is malformed"
        ) from exc
    if on_disk != dict(supplied):
        raise CandidateStrategyChannelAuditError(
            f"{label} manifest argument differs from source file"
        )
    return {
        "logical_content_fingerprint": supplied["logical_content_fingerprint"],
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _safe_completed_directory(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise CandidateStrategyChannelAuditError(
            "strategy audit directory must be absolute and not a symlink"
        )
    target = path.resolve(strict=True)
    metadata = target.stat()
    if (
        not target.is_dir()
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise CandidateStrategyChannelAuditError("unsafe strategy audit directory")
    return target


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
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
        raise CandidateStrategyChannelAuditError("malformed strategy audit JSON") from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise CandidateStrategyChannelAuditError(
            "strategy audit JSON is not canonically encoded"
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
