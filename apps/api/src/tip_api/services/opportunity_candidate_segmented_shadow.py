"""Lossless, non-authoritative per-session shadow of Candidate Audit V1."""

from __future__ import annotations

import os
import shutil
import stat
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from tip_api.contracts.analytics.v1 import (
    CandidateRiskModeResultV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.services import opportunity_candidate_audit as v1


SHADOW_CONTRACT = "opportunity-candidate-segmented-shadow/1.0"
CHAIN_IDENTITY_CONTRACT = "opportunity-candidate-segmented-chain-identity/1.0"
SHADOW_MANIFEST = "candidate-segmented-shadow-manifest.json"
SHADOW_SEGMENT_DIR = "segments"
BUSINESS_PROJECTIONS = v1.CANDIDATE_PERIODIC_BUSINESS_PROJECTIONS
SOURCE_BASE_KEYS = (
    "schema_version",
    "candidate_contract_version",
    "candidate_calculation_version",
    "candidate_parameter_set_id",
    "candidate_parameter_fingerprint",
    "candidate_state_contract_version",
    "candidate_state_calculation_version",
    "candidate_state_parameter_set_id",
    "candidate_state_parameter_fingerprint",
    "as_of_session",
    "universe_ids",
)


class CandidateSegmentedShadowError(RuntimeError):
    """Raised when segmented shadow custody or equivalence differs."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedShadowContents:
    manifest: Mapping[str, Any]
    manifest_sha256: str
    business_projection_fingerprints: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class CandidateSegmentedShadowCurrentEvidence:
    manifest: Mapping[str, Any]
    manifest_sha256: str
    source_panel: Mapping[str, Any]
    candidate_batches: tuple[OpportunityCandidateBatchV1, ...]
    state_records: tuple[OpportunityCandidateStateRecordV1, ...]
    risk_results: tuple[CandidateRiskModeResultV1, ...]


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainNodeIdentity:
    as_of_session: str
    session_ordinal: int
    prior_chain_fingerprint: str | None
    segment_logical_fingerprint: str
    segment_physical_sha256: str
    source_audit_logical_fingerprint: str
    chain_fingerprint: str


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainIdentity:
    contract_version: str
    source_shadow_logical_fingerprint: str
    source_contract_fingerprint: str
    session_count: int
    nodes: tuple[CandidateSegmentedChainNodeIdentity, ...]
    final_chain_fingerprint: str
    logical_content_fingerprint: str
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


def write_candidate_segmented_shadow(
    *,
    source_audit: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Convert one formally validated V1 audit into immutable session segments."""

    target = _new_direct_tmp_target(output_dir)
    source = source_audit.resolve(strict=True)
    try:
        manifest, payloads, batches, states, risks, oracle = (
            v1._read_opportunity_candidate_audit(source_audit)
        )
    except Exception as exc:
        raise CandidateSegmentedShadowError(
            f"source Candidate audit validation failed: {type(exc).__name__}"
        ) from exc

    sessions = _source_sessions(payloads)
    as_of_session = str(manifest.get("as_of_session"))
    if not sessions or sessions[-1] != as_of_session:
        raise CandidateSegmentedShadowError(
            "source Candidate session ledger does not end at as-of"
        )
    source_base = {key: manifest.get(key) for key in SOURCE_BASE_KEYS}
    if manifest.get("schema_version") == "1.1":
        source_base["execution_mode"] = manifest.get("execution_mode")

    records = {
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
        key: _group_records_by_session(value, sessions=sessions, label=key)
        for key, value in records.items()
    }
    raw_fact_ordinals = {session: [] for session in sessions}
    for ordinal, item in enumerate(records["raw_facts"]):
        raw_fact_ordinals[str(item["as_of_session"])].append(ordinal)
    risk_records = [item.model_dump(mode="json") for item in risks]
    if any(item.get("as_of_session") != as_of_session for item in risk_records):
        raise CandidateSegmentedShadowError(
            "source Candidate risk results are not current-session only"
        )

    source_business = _business_projection_fingerprints(payloads)
    stage = target.with_name(f".{target.name}.staging-{uuid4().hex}")
    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    segment_root = stage / SHADOW_SEGMENT_DIR
    segment_root.mkdir(mode=0o700)
    descriptors: list[dict[str, Any]] = []
    try:
        for session in sessions:
            is_current = session == as_of_session
            payload = _with_logical_fingerprint(
                {
                    "contract_version": SHADOW_CONTRACT,
                    "source_audit_logical_fingerprint": manifest[
                        "logical_content_fingerprint"
                    ],
                    "as_of_session": session,
                    "universe_ids": list(manifest["universe_ids"]),
                    "source_panel": _panel_for_session(payloads, session),
                    "candidate_batches": grouped["candidate_batches"][session],
                    "state_records": grouped["state_records"][session],
                    "transition_records": grouped["transition_records"][session],
                    "raw_facts": grouped["raw_facts"][session],
                    "raw_fact_source_ordinals": raw_fact_ordinals[session],
                    "normalization_records": grouped["normalization_records"][session],
                    "risk_results": risk_records if is_current else [],
                    "oracle_record": (
                        payloads["candidate-oracle-report.json"]["record"]
                        if is_current
                        else None
                    ),
                }
            )
            relative_path = f"{SHADOW_SEGMENT_DIR}/session={session}.json"
            path = stage / relative_path
            byte_count, physical_sha256 = v1._write_canonical_new(path, payload)
            descriptors.append(
                {
                    "as_of_session": session,
                    "relative_path": relative_path,
                    "bytes": byte_count,
                    "sha256": physical_sha256,
                    "logical_content_fingerprint": payload[
                        "logical_content_fingerprint"
                    ],
                    "candidate_batch_count": len(payload["candidate_batches"]),
                    "state_record_count": len(payload["state_records"]),
                    "transition_record_count": len(payload["transition_records"]),
                    "raw_fact_count": len(payload["raw_facts"]),
                    "normalization_record_count": len(
                        payload["normalization_records"]
                    ),
                    "risk_result_count": len(payload["risk_results"]),
                    "oracle_present": payload["oracle_record"] is not None,
                }
            )

        validation_payload = payloads.get(
            v1.CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT
        )
        logical = {
            "contract_version": SHADOW_CONTRACT,
            "completion_status": "completed",
            "source_manifest_sha256": v1._file_sha256(
                source / v1.CANDIDATE_AUDIT_MANIFEST
            ),
            "source_audit_logical_fingerprint": manifest[
                "logical_content_fingerprint"
            ],
            "source_contract": source_base,
            "as_of_session": as_of_session,
            "universe_ids": list(manifest["universe_ids"]),
            "sessions": sessions,
            "session_count": len(sessions),
            "segments": descriptors,
            "source_business_projection_fingerprints": source_business,
            "candidate_parameter_contract": payloads[
                "candidate-parameter-contract.json"
            ]["candidate_parameter_contract"],
            "candidate_state_parameter_contract": payloads[
                "candidate-parameter-contract.json"
            ]["candidate_state_parameter_contract"],
            "source_warnings": list(
                payloads["source-input-manifest.json"].get("warnings", ())
            ),
            "incremental_validation_record": (
                None
                if validation_payload is None
                else validation_payload.get("record")
            ),
            "oracle_fingerprint": oracle.oracle_fingerprint,
            "oracle_mismatch_count": oracle.mismatch_count,
            "shared_raw_fact_match": oracle.shared_raw_fact_match,
            "input_permutation_match": oracle.input_permutation_match,
            "equivalence_flags": dict(manifest["equivalence_flags"]),
            "external_request_count": 0,
            "production_write_count": 0,
            "publication_authorized": False,
        }
        shadow_manifest = {
            **logical,
            "logical_content_fingerprint": v1._fingerprint(logical),
        }
        v1._write_canonical_new(stage / SHADOW_MANIFEST, shadow_manifest)
        _fsync_directory(segment_root)
        _fsync_directory(stage)
        os.rename(stage, target)
        _fsync_directory(target.parent)
    except Exception:
        if stage.exists() and stage.is_dir() and not stage.is_symlink():
            shutil.rmtree(stage)
        raise

    return dict(read_candidate_segmented_shadow(target).manifest)


def read_candidate_segmented_shadow(
    output_dir: Path,
) -> CandidateSegmentedShadowContents:
    """Formally validate custody and lossless V1 business reconstruction."""

    target, manifest, manifest_sha256 = _read_shadow_manifest(output_dir)
    descriptors = manifest["segments"]

    reconstructed: dict[str, list[Mapping[str, Any]]] = {
        "panels": [],
        "candidate_batches": [],
        "state_records": [],
        "transition_records": [],
        "raw_facts": [],
        "normalization_records": [],
        "risk_results": [],
    }
    raw_fact_pairs: list[tuple[int, Mapping[str, Any]]] = []
    for index, descriptor in enumerate(descriptors):
        payload = _read_segment(target, descriptor)
        session = manifest["sessions"][index]
        if payload.get("as_of_session") != session:
            raise CandidateSegmentedShadowError(
                "segmented shadow descriptor session differs"
            )
        reconstructed["panels"].append(payload["source_panel"])
        for key in (
            "candidate_batches",
            "state_records",
            "transition_records",
            "normalization_records",
            "risk_results",
        ):
            reconstructed[key].extend(payload[key])
        raw_fact_pairs.extend(
            zip(
                payload["raw_fact_source_ordinals"],
                payload["raw_facts"],
                strict=True,
            )
        )
        _validate_segment_records(
            payload,
            session=session,
            is_current=index == len(descriptors) - 1,
            oracle_fingerprint=str(manifest["oracle_fingerprint"]),
            source_audit_logical_fingerprint=str(
                manifest["source_audit_logical_fingerprint"]
            ),
            universe_ids=tuple(manifest["universe_ids"]),
        )

    if sorted(ordinal for ordinal, _ in raw_fact_pairs) != list(
        range(len(raw_fact_pairs))
    ):
        raise CandidateSegmentedShadowError(
            "segmented shadow raw-fact source order is malformed"
        )
    reconstructed["raw_facts"] = [
        item for _, item in sorted(raw_fact_pairs, key=lambda pair: pair[0])
    ]

    projection_payloads = {
        "source-input-manifest.json": {"panels": reconstructed["panels"]},
        "candidate-parameter-contract.json": {
            "candidate_parameter_contract": manifest[
                "candidate_parameter_contract"
            ],
            "candidate_state_parameter_contract": manifest[
                "candidate_state_parameter_contract"
            ],
        },
        "raw-candidate-facts.json": {"records": reconstructed["raw_facts"]},
        "cross-section-normalization-ledger.json": {
            "records": reconstructed["normalization_records"]
        },
        "candidate-score-history.json": {
            "records": reconstructed["candidate_batches"]
        },
        "candidate-state-history.json": {
            "records": reconstructed["state_records"]
        },
        "candidate-transition-ledger.json": {
            "records": reconstructed["transition_records"]
        },
        "current-risk-mode-results.json": {
            "records": reconstructed["risk_results"]
        },
    }
    actual_business = _business_projection_fingerprints(projection_payloads)
    expected_business = manifest["source_business_projection_fingerprints"]
    mismatches = tuple(
        name
        for name in BUSINESS_PROJECTIONS
        if actual_business.get(name) != expected_business.get(name)
    )
    if mismatches:
        raise CandidateSegmentedShadowError(
            "segmented shadow business reconstruction differs from V1: "
            + ", ".join(mismatches)
        )
    return CandidateSegmentedShadowContents(
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        business_projection_fingerprints=actual_business,
    )


def read_candidate_segmented_shadow_current(
    output_dir: Path,
) -> CandidateSegmentedShadowCurrentEvidence:
    """Hash the whole shadow custody while parsing only its current checkpoint."""

    target, manifest, manifest_sha256 = _read_shadow_manifest(output_dir)
    descriptors = manifest["segments"]
    for descriptor in descriptors[:-1]:
        _validate_segment_physical(target, descriptor)
    current = _read_segment(target, descriptors[-1])
    session = str(manifest["as_of_session"])
    batches, states, risks = _validate_segment_records(
        current,
        session=session,
        is_current=True,
        oracle_fingerprint=str(manifest["oracle_fingerprint"]),
        source_audit_logical_fingerprint=str(
            manifest["source_audit_logical_fingerprint"]
        ),
        universe_ids=tuple(manifest["universe_ids"]),
    )
    return CandidateSegmentedShadowCurrentEvidence(
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        source_panel=current["source_panel"],
        candidate_batches=batches,
        state_records=states,
        risk_results=risks,
    )


def build_candidate_segmented_chain_identity(
    output_dir: Path,
) -> CandidateSegmentedChainIdentity:
    """Assign a versioned hash-chain identity without reusing V1 history hashes."""

    current = read_candidate_segmented_shadow_current(output_dir)
    manifest = current.manifest
    source_contract = {
        key: manifest["source_contract"].get(key)
        for key in (
            "candidate_contract_version",
            "candidate_calculation_version",
            "candidate_parameter_set_id",
            "candidate_parameter_fingerprint",
            "candidate_state_contract_version",
            "candidate_state_calculation_version",
            "candidate_state_parameter_set_id",
            "candidate_state_parameter_fingerprint",
            "universe_ids",
        )
    }
    if source_contract["universe_ids"] != manifest.get("universe_ids"):
        raise CandidateSegmentedShadowError(
            "segmented chain source Universe identity differs"
        )
    source_contract_fingerprint = v1._fingerprint(source_contract)
    prior: str | None = None
    nodes: list[CandidateSegmentedChainNodeIdentity] = []
    for ordinal, descriptor in enumerate(manifest["segments"]):
        session = str(descriptor["as_of_session"])
        segment_logical = str(descriptor["logical_content_fingerprint"])
        segment_physical = str(descriptor["sha256"])
        node_logical = {
            "contract_version": CHAIN_IDENTITY_CONTRACT,
            "session_ordinal": ordinal,
            "as_of_session": session,
            "prior_chain_fingerprint": prior,
            "source_contract_fingerprint": source_contract_fingerprint,
            "source_audit_logical_fingerprint": manifest[
                "source_audit_logical_fingerprint"
            ],
            "segment": {
                key: descriptor[key]
                for key in (
                    "logical_content_fingerprint",
                    "sha256",
                    "candidate_batch_count",
                    "state_record_count",
                    "transition_record_count",
                    "raw_fact_count",
                    "normalization_record_count",
                    "risk_result_count",
                    "oracle_present",
                )
            },
        }
        chain_fingerprint = v1._fingerprint(node_logical)
        nodes.append(
            CandidateSegmentedChainNodeIdentity(
                as_of_session=session,
                session_ordinal=ordinal,
                prior_chain_fingerprint=prior,
                segment_logical_fingerprint=segment_logical,
                segment_physical_sha256=segment_physical,
                source_audit_logical_fingerprint=str(
                    manifest["source_audit_logical_fingerprint"]
                ),
                chain_fingerprint=chain_fingerprint,
            )
        )
        prior = chain_fingerprint
    if prior is None:
        raise CandidateSegmentedShadowError("segmented chain contains no sessions")
    logical = {
        "contract_version": CHAIN_IDENTITY_CONTRACT,
        "source_shadow_logical_fingerprint": manifest[
            "logical_content_fingerprint"
        ],
        "source_contract_fingerprint": source_contract_fingerprint,
        "session_count": len(nodes),
        "nodes": [
            {
                "as_of_session": item.as_of_session,
                "session_ordinal": item.session_ordinal,
                "prior_chain_fingerprint": item.prior_chain_fingerprint,
                "segment_logical_fingerprint": item.segment_logical_fingerprint,
                "segment_physical_sha256": item.segment_physical_sha256,
                "source_audit_logical_fingerprint": (
                    item.source_audit_logical_fingerprint
                ),
                "chain_fingerprint": item.chain_fingerprint,
            }
            for item in nodes
        ],
        "final_chain_fingerprint": prior,
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }
    return CandidateSegmentedChainIdentity(
        contract_version=CHAIN_IDENTITY_CONTRACT,
        source_shadow_logical_fingerprint=str(
            manifest["logical_content_fingerprint"]
        ),
        source_contract_fingerprint=source_contract_fingerprint,
        session_count=len(nodes),
        nodes=tuple(nodes),
        final_chain_fingerprint=prior,
        logical_content_fingerprint=v1._fingerprint(logical),
    )


def _source_sessions(payloads: Mapping[str, Mapping[str, Any]]) -> list[str]:
    panels = payloads["source-input-manifest.json"].get("panels")
    if not isinstance(panels, list) or not all(
        isinstance(item, Mapping) for item in panels
    ):
        raise CandidateSegmentedShadowError("source Candidate panels are malformed")
    sessions = [str(item.get("as_of_session")) for item in panels]
    if sessions != sorted(set(sessions)):
        raise CandidateSegmentedShadowError(
            "source Candidate sessions are not unique and ascending"
        )
    return sessions


def _group_records_by_session(
    records: Sequence[Mapping[str, Any]],
    *,
    sessions: Sequence[str],
    label: str,
) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in records:
        if not isinstance(item, Mapping):
            raise CandidateSegmentedShadowError(f"source {label} row is malformed")
        session = item.get("as_of_session")
        if session not in sessions:
            raise CandidateSegmentedShadowError(
                f"source {label} row is outside the session ledger"
            )
        grouped[str(session)].append(item)
    return {session: grouped[session] for session in sessions}


def _panel_for_session(
    payloads: Mapping[str, Mapping[str, Any]], session: str
) -> Mapping[str, Any]:
    matches = [
        item
        for item in payloads["source-input-manifest.json"]["panels"]
        if item.get("as_of_session") == session
    ]
    if len(matches) != 1:
        raise CandidateSegmentedShadowError(
            "source Candidate panel session is missing or duplicated"
        )
    return matches[0]


def _business_projection_fingerprints(
    payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, keys in BUSINESS_PROJECTIONS.items():
        payload = payloads.get(name)
        if not isinstance(payload, Mapping) or any(key not in payload for key in keys):
            raise CandidateSegmentedShadowError(
                f"Candidate business projection is malformed: {name}"
            )
        result[name] = v1._fingerprint({key: payload[key] for key in keys})
    return result


def _with_logical_fingerprint(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    return {**value, "logical_content_fingerprint": v1._fingerprint(value)}


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    sessions = manifest.get("sessions")
    descriptors = manifest.get("segments")
    if (
        manifest.get("contract_version") != SHADOW_CONTRACT
        or manifest.get("completion_status") != "completed"
        or manifest.get("publication_authorized") is not False
        or manifest.get("external_request_count") != 0
        or manifest.get("production_write_count") != 0
        or not isinstance(sessions, list)
        or sessions != sorted(set(sessions))
        or manifest.get("session_count") != len(sessions)
        or not sessions
        or manifest.get("as_of_session") != sessions[-1]
        or not isinstance(descriptors, list)
        or len(descriptors) != len(sessions)
        or [item.get("as_of_session") for item in descriptors] != sessions
        or manifest.get("oracle_mismatch_count") != 0
        or manifest.get("shared_raw_fact_match") is not True
        or manifest.get("input_permutation_match") is not True
    ):
        raise CandidateSegmentedShadowError("segmented shadow manifest is malformed")
    flags = manifest.get("equivalence_flags")
    business = manifest.get("source_business_projection_fingerprints")
    if (
        not isinstance(flags, Mapping)
        or not flags
        or any(value is not True for value in flags.values())
        or not isinstance(business, Mapping)
        or set(business) != set(BUSINESS_PROJECTIONS)
        or any(not _is_sha256(value) for value in business.values())
        or not _is_sha256(manifest.get("source_manifest_sha256"))
        or not _is_sha256(manifest.get("source_audit_logical_fingerprint"))
        or not _is_sha256(manifest.get("oracle_fingerprint"))
    ):
        raise CandidateSegmentedShadowError(
            "segmented shadow source bindings are malformed"
        )


def _read_segment(
    target: Path,
    descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    path = _validate_segment_physical(target, descriptor)
    payload = _read_canonical_mapping(path, physical_sha256=str(descriptor["sha256"]))
    fingerprint = payload.pop("logical_content_fingerprint", None)
    if (
        v1._fingerprint(payload) != fingerprint
        or fingerprint != descriptor.get("logical_content_fingerprint")
    ):
        raise CandidateSegmentedShadowError(
            "segmented shadow segment logical fingerprint differs"
        )
    payload["logical_content_fingerprint"] = fingerprint
    count_fields = {
        "candidate_batches": "candidate_batch_count",
        "state_records": "state_record_count",
        "transition_records": "transition_record_count",
        "raw_facts": "raw_fact_count",
        "normalization_records": "normalization_record_count",
        "risk_results": "risk_result_count",
    }
    if any(
        not isinstance(payload.get(key), list)
        or len(payload[key]) != descriptor.get(count_key)
        for key, count_key in count_fields.items()
    ) or (
        not isinstance(payload.get("raw_fact_source_ordinals"), list)
        or len(payload["raw_fact_source_ordinals"]) != len(payload["raw_facts"])
        or any(
            type(ordinal) is not int or ordinal < 0
            for ordinal in payload["raw_fact_source_ordinals"]
        )
        or (payload.get("oracle_record") is not None)
        != descriptor.get("oracle_present")
    ):
        raise CandidateSegmentedShadowError("segmented shadow counts differ")
    return payload


def _validate_segment_records(
    payload: Mapping[str, Any],
    *,
    session: str,
    is_current: bool,
    oracle_fingerprint: str,
    source_audit_logical_fingerprint: str,
    universe_ids: tuple[str, ...],
) -> tuple[
    tuple[OpportunityCandidateBatchV1, ...],
    tuple[OpportunityCandidateStateRecordV1, ...],
    tuple[CandidateRiskModeResultV1, ...],
]:
    if (
        payload.get("contract_version") != SHADOW_CONTRACT
        or payload.get("source_audit_logical_fingerprint")
        != source_audit_logical_fingerprint
        or tuple(payload.get("universe_ids", ())) != universe_ids
        or payload.get("as_of_session") != session
        or payload.get("source_panel", {}).get("as_of_session") != session
        or any(
            item.get("as_of_session") != session
            for key in (
                "candidate_batches",
                "state_records",
                "transition_records",
                "raw_facts",
                "normalization_records",
                "risk_results",
            )
            for item in payload[key]
        )
    ):
        raise CandidateSegmentedShadowError(
            "segmented shadow record session differs"
        )
    batches = tuple(
        OpportunityCandidateBatchV1.model_validate(item)
        for item in payload["candidate_batches"]
    )
    states = tuple(
        OpportunityCandidateStateRecordV1.model_validate(item)
        for item in payload["state_records"]
    )
    risks = tuple(
        CandidateRiskModeResultV1.model_validate(item)
        for item in payload["risk_results"]
    )
    v1._validate_typed_fingerprints(batches=batches, states=states, risks=risks)
    if payload["transition_records"] != [v1._transition_row(item) for item in states]:
        raise CandidateSegmentedShadowError(
            "segmented shadow transition projection differs"
        )
    if tuple(item.universe_id for item in batches) != universe_ids:
        raise CandidateSegmentedShadowError(
            "segmented shadow Candidate Universe order differs"
        )
    if is_current:
        oracle = v1._oracle_from_record(payload.get("oracle_record"))
        if (
            oracle.oracle_fingerprint != oracle_fingerprint
            or oracle.mismatch_count != 0
            or not oracle.shared_raw_fact_match
            or not oracle.input_permutation_match
            or len(risks) != len(universe_ids) * 3
        ):
            raise CandidateSegmentedShadowError(
                "segmented shadow current Oracle or risk result differs"
            )
    elif risks or payload.get("oracle_record") is not None:
        raise CandidateSegmentedShadowError(
            "segmented shadow historical segment contains current-only evidence"
        )
    return batches, states, risks


def _read_shadow_manifest(
    output_dir: Path,
) -> tuple[Path, dict[str, Any], str]:
    target = _completed_direct_tmp_target(output_dir)
    manifest_path = target / SHADOW_MANIFEST
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise CandidateSegmentedShadowError("segmented shadow manifest is unavailable")
    manifest_sha256 = v1._file_sha256(manifest_path)
    manifest = _read_canonical_mapping(
        manifest_path,
        physical_sha256=manifest_sha256,
    )
    logical_fingerprint = manifest.pop("logical_content_fingerprint", None)
    if v1._fingerprint(manifest) != logical_fingerprint:
        raise CandidateSegmentedShadowError(
            "segmented shadow manifest logical fingerprint differs"
        )
    manifest["logical_content_fingerprint"] = logical_fingerprint
    _validate_manifest_shape(manifest)
    descriptors = manifest["segments"]
    expected_files = {SHADOW_MANIFEST} | {
        str(item["relative_path"]) for item in descriptors
    }
    actual_files = {
        item.relative_to(target).as_posix()
        for item in target.rglob("*")
        if item.is_file()
    }
    actual_directories = {
        item.relative_to(target).as_posix()
        for item in target.rglob("*")
        if item.is_dir()
    }
    if actual_files != expected_files or actual_directories != {SHADOW_SEGMENT_DIR}:
        raise CandidateSegmentedShadowError(
            "segmented shadow file set is incomplete or contains extras"
        )
    return target, manifest, manifest_sha256


def _validate_segment_physical(
    target: Path,
    descriptor: Mapping[str, Any],
) -> Path:
    relative = descriptor.get("relative_path")
    if not isinstance(relative, str):
        raise CandidateSegmentedShadowError("segmented shadow path is malformed")
    expected = f"{SHADOW_SEGMENT_DIR}/session={descriptor.get('as_of_session')}.json"
    if relative != expected:
        raise CandidateSegmentedShadowError("segmented shadow path differs")
    path = target / relative
    _validate_file_custody(path)
    if (
        path.stat().st_size != descriptor.get("bytes")
        or v1._file_sha256(path) != descriptor.get("sha256")
    ):
        raise CandidateSegmentedShadowError(
            "segmented shadow physical descriptor differs"
        )
    return path


def _read_canonical_mapping(path: Path, *, physical_sha256: str) -> dict[str, Any]:
    _validate_file_custody(path)
    try:
        return v1._read_canonical_json(path, physical_sha256=physical_sha256)
    except Exception as exc:
        raise CandidateSegmentedShadowError(
            f"segmented shadow JSON is malformed: {path.name}"
        ) from exc


def _new_direct_tmp_target(path: Path) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp") or path.name.startswith("."):
        raise CandidateSegmentedShadowError(
            "segmented shadow output must be a visible direct child of /tmp"
        )
    if path.exists() or path.is_symlink():
        raise CandidateSegmentedShadowError("segmented shadow output must be new")
    return path


def _completed_direct_tmp_target(path: Path) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp"):
        raise CandidateSegmentedShadowError(
            "segmented shadow must be a direct child of /tmp"
        )
    if path.is_symlink() or not path.is_dir():
        raise CandidateSegmentedShadowError("segmented shadow directory is unsafe")
    target = path.resolve(strict=True)
    metadata = target.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateSegmentedShadowError(
            "segmented shadow directory custody differs"
        )
    segment_root = target / SHADOW_SEGMENT_DIR
    if segment_root.is_symlink() or not segment_root.is_dir():
        raise CandidateSegmentedShadowError(
            "segmented shadow segment directory is unsafe"
        )
    segment_metadata = segment_root.stat()
    if (
        segment_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(segment_metadata.st_mode) != 0o700
    ):
        raise CandidateSegmentedShadowError(
            "segmented shadow segment-directory custody differs"
        )
    return target


def _validate_file_custody(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise CandidateSegmentedShadowError("segmented shadow file is unsafe")
    metadata = path.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise CandidateSegmentedShadowError("segmented shadow file custody differs")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
