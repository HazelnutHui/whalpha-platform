"""Immutable, non-authoritative one-session append proof for Candidate segments."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services import opportunity_candidate_segmented_shadow as shadow


APPEND_CONTRACT = "opportunity-candidate-segmented-append/1.0"
APPEND_SESSION_CONTRACT = "opportunity-candidate-segmented-append-session/1.0"
APPEND_MANIFEST = "candidate-segmented-append-manifest.json"
APPEND_SEGMENT = "candidate-session-segment.json"
PREFIX_FIELDS = (
    "source_panel",
    "candidate_batches",
    "state_records",
    "transition_records",
    "raw_facts",
    "normalization_records",
)
CURRENT_FIELDS = (
    *PREFIX_FIELDS,
    "risk_results",
    "oracle_record",
)


class CandidateSegmentedAppendError(RuntimeError):
    """Raised when an append package cannot preserve exact segmented evidence."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedAppendEvidence:
    path: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str
    segment: Mapping[str, Any]
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


@dataclass(frozen=True, slots=True)
class CandidateSegmentedAppendColdEquivalence:
    parent_session_count: int
    appended_session_count: int
    as_of_session: str
    source_audit_logical_fingerprint: str
    final_chain_fingerprint: str
    prefix_projection_fingerprints: Mapping[str, str]
    current_projection_fingerprints: Mapping[str, str]
    logical_content_fingerprint: str
    mismatch_count: int = 0
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


@dataclass(frozen=True, slots=True)
class _PreparedAppend:
    parent_manifest: Mapping[str, Any]
    parent_manifest_sha256: str
    parent_chain: shadow.CandidateSegmentedChainIdentity
    source_manifest: Mapping[str, Any]
    source_manifest_sha256: str
    segment: Mapping[str, Any]
    segment_descriptor: Mapping[str, Any]
    prefix_projection_fingerprints: Mapping[str, str]
    current_projection_fingerprints: Mapping[str, str]
    incremental_prior_binding: str
    final_chain_fingerprint: str


def write_candidate_segmented_append(
    *,
    parent_shadow: Path,
    source_audit: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Write one atomic append package while leaving every parent byte unchanged."""

    target = _new_output_target(output_dir)
    prepared = _prepare_append(parent_shadow=parent_shadow, source_audit=source_audit)
    if target.exists():
        evidence = read_candidate_segmented_append(
            parent_shadow=parent_shadow,
            output_dir=target,
        )
        _require_expected_append(evidence.manifest, prepared)
        return dict(evidence.manifest)

    stage = target.with_name(f".{target.name}.staging")
    if stage.exists() or stage.is_symlink():
        evidence = _read_candidate_segmented_append_at(
            parent_shadow=parent_shadow,
            output_dir=stage,
            allow_staging=True,
        )
        _require_expected_append(evidence.manifest, prepared)
        os.rename(stage, target)
        _fsync_directory(target.parent)
        return dict(
            read_candidate_segmented_append(
                parent_shadow=parent_shadow,
                output_dir=target,
            ).manifest
        )

    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        segment_bytes, segment_sha256 = v1._write_canonical_new(
            stage / APPEND_SEGMENT,
            prepared.segment,
        )
        descriptor = dict(prepared.segment_descriptor)
        descriptor.update(bytes=segment_bytes, sha256=segment_sha256)
        expected_chain = shadow.candidate_segmented_chain_node_fingerprint(
            session_ordinal=prepared.parent_chain.session_count,
            as_of_session=str(prepared.source_manifest["as_of_session"]),
            prior_chain_fingerprint=prepared.parent_chain.final_chain_fingerprint,
            source_contract_fingerprint=prepared.parent_chain.source_contract_fingerprint,
            source_audit_logical_fingerprint=str(
                prepared.source_manifest["logical_content_fingerprint"]
            ),
            segment_descriptor=descriptor,
        )
        if expected_chain != prepared.final_chain_fingerprint:
            raise CandidateSegmentedAppendError(
                "append segment physical identity changed the prepared chain"
            )
        logical = _append_manifest_logical(prepared, descriptor=descriptor)
        manifest = {
            **logical,
            "logical_content_fingerprint": v1._fingerprint(logical),
        }
        v1._write_canonical_new(stage / APPEND_MANIFEST, manifest)
        _fsync_directory(stage)
        os.rename(stage, target)
        _fsync_directory(target.parent)
    except Exception:
        # A completed deterministic staging directory is retained for exact
        # verify-then-complete recovery. Ambiguous partial evidence is not deleted.
        raise
    return dict(
        read_candidate_segmented_append(
            parent_shadow=parent_shadow,
            output_dir=target,
        ).manifest
    )


def read_candidate_segmented_append(
    *,
    parent_shadow: Path,
    output_dir: Path,
) -> CandidateSegmentedAppendEvidence:
    """Formally read a completed append package and its exact parent chain."""

    return _read_candidate_segmented_append_at(
        parent_shadow=parent_shadow,
        output_dir=output_dir,
        allow_staging=False,
    )


def verify_candidate_segmented_append_cold_equivalence(
    *,
    parent_shadow: Path,
    source_audit: Path,
    output_dir: Path,
) -> CandidateSegmentedAppendColdEquivalence:
    """Rebuild exact per-session projections from the cold V1 source."""

    prepared = _prepare_append(parent_shadow=parent_shadow, source_audit=source_audit)
    evidence = read_candidate_segmented_append(
        parent_shadow=parent_shadow,
        output_dir=output_dir,
    )
    _require_expected_append(evidence.manifest, prepared)
    logical = {
        "contract_version": APPEND_CONTRACT,
        "parent_session_count": prepared.parent_chain.session_count,
        "appended_session_count": prepared.parent_chain.session_count + 1,
        "as_of_session": prepared.source_manifest["as_of_session"],
        "source_audit_logical_fingerprint": prepared.source_manifest[
            "logical_content_fingerprint"
        ],
        "final_chain_fingerprint": prepared.final_chain_fingerprint,
        "prefix_projection_fingerprints": dict(
            prepared.prefix_projection_fingerprints
        ),
        "current_projection_fingerprints": dict(
            prepared.current_projection_fingerprints
        ),
        "mismatch_count": 0,
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }
    return CandidateSegmentedAppendColdEquivalence(
        parent_session_count=prepared.parent_chain.session_count,
        appended_session_count=prepared.parent_chain.session_count + 1,
        as_of_session=str(prepared.source_manifest["as_of_session"]),
        source_audit_logical_fingerprint=str(
            prepared.source_manifest["logical_content_fingerprint"]
        ),
        final_chain_fingerprint=prepared.final_chain_fingerprint,
        prefix_projection_fingerprints=prepared.prefix_projection_fingerprints,
        current_projection_fingerprints=prepared.current_projection_fingerprints,
        logical_content_fingerprint=v1._fingerprint(logical),
    )


def _prepare_append(*, parent_shadow: Path, source_audit: Path) -> _PreparedAppend:
    try:
        parent_current = shadow.read_candidate_segmented_shadow_current(parent_shadow)
        parent_chain = shadow._chain_identity_from_validated_manifest(
            parent_current.manifest
        )
        (
            source_manifest,
            payloads,
            batches,
            states,
            risks,
            oracle,
        ) = v1._read_opportunity_candidate_audit(source_audit)
    except Exception as exc:
        raise CandidateSegmentedAppendError(
            f"append source validation failed: {type(exc).__name__}"
        ) from exc

    source = source_audit.resolve(strict=True)
    sessions = shadow._source_sessions(payloads)
    parent_sessions = list(parent_current.manifest["sessions"])
    if (
        len(sessions) != len(parent_sessions) + 1
        or sessions[:-1] != parent_sessions
        or source_manifest.get("as_of_session") != sessions[-1]
    ):
        raise CandidateSegmentedAppendError(
            "append source must extend the parent by exactly one ordered session"
        )
    source_contract = {
        key: source_manifest.get(key) for key in shadow.SOURCE_BASE_KEYS
    }
    if source_manifest.get("schema_version") == "1.1":
        source_contract["execution_mode"] = source_manifest.get("execution_mode")
    source_contract_fingerprint = shadow.candidate_segmented_source_contract_fingerprint(
        {
            "source_contract": source_contract,
            "universe_ids": source_manifest.get("universe_ids"),
        }
    )
    if source_contract_fingerprint != parent_chain.source_contract_fingerprint:
        raise CandidateSegmentedAppendError(
            "append source calculation contract differs from parent chain"
        )

    record_sets = {
        "candidate_batches": [item.model_dump(mode="json") for item in batches],
        "state_records": [item.model_dump(mode="json") for item in states],
        "transition_records": list(
            payloads["candidate-transition-ledger.json"]["records"]
        ),
        "raw_facts": list(payloads["raw-candidate-facts.json"]["records"]),
        "normalization_records": list(
            payloads["cross-section-normalization-ledger.json"]["records"]
        ),
    }
    grouped = {
        key: shadow._group_records_by_session(value, sessions=sessions, label=key)
        for key, value in record_sets.items()
    }
    prefix_values: dict[str, list[Any]] = {key: [] for key in PREFIX_FIELDS}
    parent_target, parent_manifest, parent_manifest_sha256 = shadow._read_shadow_manifest(
        parent_shadow
    )
    for index, descriptor in enumerate(parent_manifest["segments"]):
        session = parent_sessions[index]
        payload = shadow._read_segment(parent_target, descriptor)
        shadow._validate_segment_records(
            payload,
            session=session,
            is_current=index == len(parent_sessions) - 1,
            oracle_fingerprint=str(parent_manifest["oracle_fingerprint"]),
            source_audit_logical_fingerprint=str(
                parent_manifest["source_audit_logical_fingerprint"]
            ),
            universe_ids=tuple(parent_manifest["universe_ids"]),
        )
        expected = {
            "source_panel": shadow._panel_for_session(payloads, session),
            **{key: grouped[key][session] for key in grouped},
        }
        for field in PREFIX_FIELDS:
            if payload[field] != expected[field]:
                raise CandidateSegmentedAppendError(
                    f"append source prefix differs in {field} for {session}"
                )
            if field == "source_panel":
                prefix_values[field].append(payload[field])
            else:
                prefix_values[field].extend(payload[field])

    current_session = sessions[-1]
    risk_records = [item.model_dump(mode="json") for item in risks]
    raw_ordinals = [
        ordinal
        for ordinal, item in enumerate(record_sets["raw_facts"])
        if item.get("as_of_session") == current_session
    ]
    segment = shadow._with_logical_fingerprint(
        {
            "contract_version": APPEND_SESSION_CONTRACT,
            "source_audit_logical_fingerprint": source_manifest[
                "logical_content_fingerprint"
            ],
            "as_of_session": current_session,
            "universe_ids": list(source_manifest["universe_ids"]),
            "source_panel": shadow._panel_for_session(payloads, current_session),
            "candidate_batches": grouped["candidate_batches"][current_session],
            "state_records": grouped["state_records"][current_session],
            "transition_records": grouped["transition_records"][current_session],
            "raw_facts": grouped["raw_facts"][current_session],
            "raw_fact_source_ordinals": raw_ordinals,
            "normalization_records": grouped["normalization_records"][current_session],
            "risk_results": risk_records,
            "oracle_record": payloads["candidate-oracle-report.json"]["record"],
        }
    )
    segment_descriptor = _segment_descriptor(segment)
    final_chain_fingerprint = shadow.candidate_segmented_chain_node_fingerprint(
        session_ordinal=parent_chain.session_count,
        as_of_session=current_session,
        prior_chain_fingerprint=parent_chain.final_chain_fingerprint,
        source_contract_fingerprint=parent_chain.source_contract_fingerprint,
        source_audit_logical_fingerprint=str(
            source_manifest["logical_content_fingerprint"]
        ),
        segment_descriptor=segment_descriptor,
    )
    incremental_prior_binding = _incremental_prior_binding(
        payloads=payloads,
        parent_manifest=parent_manifest,
        current_session=current_session,
    )
    prefix_fingerprints = {
        field: v1._fingerprint(prefix_values[field]) for field in PREFIX_FIELDS
    }
    current_fingerprints = {
        field: v1._fingerprint(segment[field]) for field in CURRENT_FIELDS
    }
    return _PreparedAppend(
        parent_manifest=parent_manifest,
        parent_manifest_sha256=parent_manifest_sha256,
        parent_chain=parent_chain,
        source_manifest=source_manifest,
        source_manifest_sha256=v1._file_sha256(
            source / v1.CANDIDATE_AUDIT_MANIFEST
        ),
        segment=segment,
        segment_descriptor=segment_descriptor,
        prefix_projection_fingerprints=prefix_fingerprints,
        current_projection_fingerprints=current_fingerprints,
        incremental_prior_binding=incremental_prior_binding,
        final_chain_fingerprint=final_chain_fingerprint,
    )


def _incremental_prior_binding(
    *,
    payloads: Mapping[str, Mapping[str, Any]],
    parent_manifest: Mapping[str, Any],
    current_session: str,
) -> str:
    validation = payloads.get(v1.CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT)
    if validation is None:
        return "not_present_full_semantic_prefix_exact"
    record = validation.get("record")
    if (
        not isinstance(record, Mapping)
        or record.get("prior_audit_logical_fingerprint")
        != parent_manifest.get("source_audit_logical_fingerprint")
        or record.get("prior_as_of_session") != parent_manifest.get("as_of_session")
        or record.get("current_as_of_session") != current_session
        or not isinstance(record.get("reuse_checks"), Mapping)
        or any(value is not True for value in record["reuse_checks"].values())
    ):
        raise CandidateSegmentedAppendError(
            "incremental source does not bind the exact parent Candidate audit"
        )
    return "exact_prior_audit_and_semantic_prefix"


def _segment_descriptor(segment: Mapping[str, Any]) -> dict[str, Any]:
    canonical = v1._canonical_bytes(segment)
    return {
        "relative_path": APPEND_SEGMENT,
        "bytes": len(canonical),
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "logical_content_fingerprint": segment["logical_content_fingerprint"],
        "candidate_batch_count": len(segment["candidate_batches"]),
        "state_record_count": len(segment["state_records"]),
        "transition_record_count": len(segment["transition_records"]),
        "raw_fact_count": len(segment["raw_facts"]),
        "normalization_record_count": len(segment["normalization_records"]),
        "risk_result_count": len(segment["risk_results"]),
        "oracle_present": segment["oracle_record"] is not None,
    }


def _append_manifest_logical(
    prepared: _PreparedAppend,
    *,
    descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": APPEND_CONTRACT,
        "completion_status": "completed",
        "parent": {
            "shadow_contract_version": prepared.parent_manifest["contract_version"],
            "manifest_sha256": prepared.parent_manifest_sha256,
            "logical_content_fingerprint": prepared.parent_manifest[
                "logical_content_fingerprint"
            ],
            "as_of_session": prepared.parent_manifest["as_of_session"],
            "session_count": prepared.parent_chain.session_count,
            "source_contract_fingerprint": (
                prepared.parent_chain.source_contract_fingerprint
            ),
            "final_chain_fingerprint": prepared.parent_chain.final_chain_fingerprint,
        },
        "source_audit": {
            "manifest_sha256": prepared.source_manifest_sha256,
            "logical_content_fingerprint": prepared.source_manifest[
                "logical_content_fingerprint"
            ],
            "as_of_session": prepared.source_manifest["as_of_session"],
            "incremental_prior_binding": prepared.incremental_prior_binding,
        },
        "as_of_session": prepared.source_manifest["as_of_session"],
        "session_ordinal": prepared.parent_chain.session_count,
        "universe_ids": list(prepared.source_manifest["universe_ids"]),
        "segment": dict(descriptor),
        "chain_node": {
            "contract_version": shadow.CHAIN_IDENTITY_CONTRACT,
            "prior_chain_fingerprint": prepared.parent_chain.final_chain_fingerprint,
            "chain_fingerprint": prepared.final_chain_fingerprint,
        },
        "prefix_projection_fingerprints": dict(
            prepared.prefix_projection_fingerprints
        ),
        "current_projection_fingerprints": dict(
            prepared.current_projection_fingerprints
        ),
        "prefix_semantic_match": True,
        "current_segment_match": True,
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }


def _read_candidate_segmented_append_at(
    *,
    parent_shadow: Path,
    output_dir: Path,
    allow_staging: bool,
) -> CandidateSegmentedAppendEvidence:
    target = _completed_output_target(output_dir, allow_staging=allow_staging)
    manifest_path = target / APPEND_MANIFEST
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise CandidateSegmentedAppendError("append completion manifest is unavailable")
    manifest_sha256 = v1._file_sha256(manifest_path)
    manifest = shadow._read_canonical_mapping(
        manifest_path,
        physical_sha256=manifest_sha256,
    )
    logical_fingerprint = manifest.pop("logical_content_fingerprint", None)
    if v1._fingerprint(manifest) != logical_fingerprint:
        raise CandidateSegmentedAppendError(
            "append manifest logical fingerprint differs"
        )
    manifest["logical_content_fingerprint"] = logical_fingerprint
    _validate_append_manifest_shape(manifest)
    actual_files = {item.name for item in target.iterdir() if item.is_file()}
    actual_directories = {item.name for item in target.iterdir() if item.is_dir()}
    if actual_files != {APPEND_MANIFEST, APPEND_SEGMENT} or actual_directories:
        raise CandidateSegmentedAppendError(
            "append package file set is incomplete or contains extras"
        )

    parent_current = shadow.read_candidate_segmented_shadow_current(parent_shadow)
    parent_chain = shadow._chain_identity_from_validated_manifest(
        parent_current.manifest
    )
    parent = manifest["parent"]
    if (
        parent.get("manifest_sha256") != parent_current.manifest_sha256
        or parent.get("logical_content_fingerprint")
        != parent_current.manifest.get("logical_content_fingerprint")
        or parent.get("as_of_session") != parent_current.manifest.get("as_of_session")
        or parent.get("session_count") != parent_chain.session_count
        or parent.get("source_contract_fingerprint")
        != parent_chain.source_contract_fingerprint
        or parent.get("final_chain_fingerprint")
        != parent_chain.final_chain_fingerprint
    ):
        raise CandidateSegmentedAppendError("append parent chain identity differs")

    descriptor = manifest["segment"]
    segment_path = target / APPEND_SEGMENT
    shadow._validate_file_custody(segment_path)
    if (
        segment_path.stat().st_size != descriptor.get("bytes")
        or v1._file_sha256(segment_path) != descriptor.get("sha256")
    ):
        raise CandidateSegmentedAppendError(
            "append segment physical descriptor differs"
        )
    segment = shadow._read_canonical_mapping(
        segment_path,
        physical_sha256=str(descriptor["sha256"]),
    )
    segment_logical = segment.pop("logical_content_fingerprint", None)
    if (
        v1._fingerprint(segment) != segment_logical
        or segment_logical != descriptor.get("logical_content_fingerprint")
    ):
        raise CandidateSegmentedAppendError(
            "append segment logical fingerprint differs"
        )
    segment["logical_content_fingerprint"] = segment_logical
    expected_counts = _segment_descriptor(segment)
    if any(
        expected_counts.get(key) != descriptor.get(key)
        for key in expected_counts
        if key not in {"bytes", "sha256"}
    ):
        raise CandidateSegmentedAppendError("append segment counts differ")
    shadow._validate_segment_records(
        segment,
        session=str(manifest["as_of_session"]),
        is_current=True,
        oracle_fingerprint=str(segment["oracle_record"]["oracle_fingerprint"]),
        source_audit_logical_fingerprint=str(
            manifest["source_audit"]["logical_content_fingerprint"]
        ),
        universe_ids=tuple(manifest["universe_ids"]),
        expected_contract=APPEND_SESSION_CONTRACT,
    )
    expected_chain = shadow.candidate_segmented_chain_node_fingerprint(
        session_ordinal=int(manifest["session_ordinal"]),
        as_of_session=str(manifest["as_of_session"]),
        prior_chain_fingerprint=str(
            manifest["chain_node"]["prior_chain_fingerprint"]
        ),
        source_contract_fingerprint=str(parent["source_contract_fingerprint"]),
        source_audit_logical_fingerprint=str(
            manifest["source_audit"]["logical_content_fingerprint"]
        ),
        segment_descriptor=descriptor,
    )
    if expected_chain != manifest["chain_node"].get("chain_fingerprint"):
        raise CandidateSegmentedAppendError("append chain node identity differs")
    return CandidateSegmentedAppendEvidence(
        path=target,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        segment=segment,
    )


def _validate_append_manifest_shape(manifest: Mapping[str, Any]) -> None:
    parent = manifest.get("parent")
    source = manifest.get("source_audit")
    segment = manifest.get("segment")
    chain = manifest.get("chain_node")
    if (
        manifest.get("contract_version") != APPEND_CONTRACT
        or manifest.get("completion_status") != "completed"
        or manifest.get("prefix_semantic_match") is not True
        or manifest.get("current_segment_match") is not True
        or manifest.get("external_request_count") != 0
        or manifest.get("production_write_count") != 0
        or manifest.get("publication_authorized") is not False
        or not isinstance(parent, Mapping)
        or not isinstance(source, Mapping)
        or not isinstance(segment, Mapping)
        or not isinstance(chain, Mapping)
        or segment.get("relative_path") != APPEND_SEGMENT
        or chain.get("contract_version") != shadow.CHAIN_IDENTITY_CONTRACT
        or manifest.get("session_ordinal") != parent.get("session_count")
        or type(manifest.get("session_ordinal")) is not int
        or manifest["session_ordinal"] < 1
        or manifest.get("as_of_session") != source.get("as_of_session")
        or not isinstance(manifest.get("universe_ids"), list)
        or not manifest["universe_ids"]
        or source.get("incremental_prior_binding")
        not in {
            "exact_prior_audit_and_semantic_prefix",
            "not_present_full_semantic_prefix_exact",
        }
    ):
        raise CandidateSegmentedAppendError("append manifest is malformed")
    fingerprints = (
        parent.get("manifest_sha256"),
        parent.get("logical_content_fingerprint"),
        parent.get("source_contract_fingerprint"),
        parent.get("final_chain_fingerprint"),
        source.get("manifest_sha256"),
        source.get("logical_content_fingerprint"),
        segment.get("logical_content_fingerprint"),
        segment.get("sha256"),
        chain.get("prior_chain_fingerprint"),
        chain.get("chain_fingerprint"),
    )
    if any(not shadow._is_sha256(value) for value in fingerprints):
        raise CandidateSegmentedAppendError(
            "append manifest fingerprints are malformed"
        )
    for name, fields in (
        ("prefix", PREFIX_FIELDS),
        ("current", CURRENT_FIELDS),
    ):
        values = manifest.get(f"{name}_projection_fingerprints")
        if (
            not isinstance(values, Mapping)
            or set(values) != set(fields)
            or any(not shadow._is_sha256(value) for value in values.values())
        ):
            raise CandidateSegmentedAppendError(
                f"append {name} projection fingerprints are malformed"
            )


def _require_expected_append(
    manifest: Mapping[str, Any],
    prepared: _PreparedAppend,
) -> None:
    descriptor = manifest.get("segment")
    if not isinstance(descriptor, Mapping):
        raise CandidateSegmentedAppendError("append descriptor is missing")
    expected_logical = _append_manifest_logical(prepared, descriptor=descriptor)
    if any(
        manifest.get(key) != value for key, value in expected_logical.items()
    ):
        raise CandidateSegmentedAppendError(
            "completed append does not match the requested parent and source"
        )


def _new_output_target(path: Path) -> Path:
    if (
        not path.is_absolute()
        or path.parent != Path("/tmp")
        or path.name.startswith(".")
    ):
        raise CandidateSegmentedAppendError(
            "append output must be a visible direct child of /tmp"
        )
    if path.is_symlink():
        raise CandidateSegmentedAppendError("append output symlink is unsafe")
    return path


def _completed_output_target(path: Path, *, allow_staging: bool) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp"):
        raise CandidateSegmentedAppendError(
            "append package must be a direct child of /tmp"
        )
    if path.name.startswith(".") and not (
        allow_staging and path.name.endswith(".staging")
    ):
        raise CandidateSegmentedAppendError("append package name is unsafe")
    if path.is_symlink() or not path.is_dir():
        raise CandidateSegmentedAppendError("append package directory is unsafe")
    target = path.resolve(strict=True)
    metadata = target.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateSegmentedAppendError(
            "append package directory custody differs"
        )
    if any(item.is_symlink() for item in target.iterdir()):
        raise CandidateSegmentedAppendError("append package contains a symlink")
    return target


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
