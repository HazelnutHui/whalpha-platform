"""Direct non-authoritative Candidate session segment from current run objects."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from tip_api.contracts.analytics.v1 import (
    CandidateRiskModeResultV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidateStateRecordV1,
)
from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services import opportunity_candidate_segmented_shadow as shadow
from tip_api.services.market_regime_sources import MarketRegimeInputPanel
from tip_api.services.opportunity_candidate_oracle import CandidateOracleComparisonV1


SESSION_CANDIDATE_CONTRACT = (
    "opportunity-candidate-segmented-session-candidate/1.0"
)
SESSION_PAYLOAD_CONTRACT = "opportunity-candidate-segmented-session/1.0"
SESSION_CANDIDATE_MANIFEST = "candidate-session-candidate-manifest.json"
SESSION_PAYLOAD = "candidate-session.json"
CURRENT_PROJECTION_FIELDS = (
    "source_panel",
    "candidate_batches",
    "state_records",
    "transition_records",
    "raw_facts",
    "normalization_records",
    "risk_results",
    "oracle_record",
)


class CandidateSegmentedSessionCandidateError(RuntimeError):
    """Raised when a direct current-session segment loses exact bindings."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedSessionCandidateEvidence:
    path: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str
    payload: Mapping[str, Any]
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


@dataclass(frozen=True, slots=True)
class _CandidateSegmentedParentContext:
    manifest: Mapping[str, Any]
    manifest_sha256: str
    root_shadow_contract_version: str
    session_count: int
    source_contract_fingerprint: str
    final_chain_fingerprint: str
    source_audit_logical_fingerprint: str
    universe_ids: tuple[str, ...]


def _read_parent_context(
    *,
    parent_shadow: Path,
    parent_appends: Sequence[Path],
) -> _CandidateSegmentedParentContext:
    # The local import avoids a module cycle: the append reader reuses this
    # module's typed session-payload validator.
    from tip_api.services import opportunity_candidate_segmented_append as append

    try:
        evidence = append.read_candidate_segmented_parent(
            base_shadow=parent_shadow,
            parent_appends=parent_appends,
        )
    except Exception as exc:
        raise CandidateSegmentedSessionCandidateError(
            f"direct session parent validation failed: {type(exc).__name__}"
        ) from exc
    return _CandidateSegmentedParentContext(
        manifest=evidence.manifest,
        manifest_sha256=evidence.manifest_sha256,
        root_shadow_contract_version=evidence.root_shadow_contract_version,
        session_count=evidence.session_count,
        source_contract_fingerprint=evidence.source_contract_fingerprint,
        final_chain_fingerprint=evidence.final_chain_fingerprint,
        source_audit_logical_fingerprint=(
            evidence.source_audit_logical_fingerprint
        ),
        universe_ids=evidence.universe_ids,
    )


def write_candidate_segmented_session_candidate(
    *,
    parent_shadow: Path,
    source_audit_manifest: Mapping[str, Any],
    incremental_validation: Mapping[str, Any],
    panel: MarketRegimeInputPanel | Mapping[str, Any],
    candidate_batches: Sequence[OpportunityCandidateBatchV1],
    state_records: Sequence[OpportunityCandidateStateRecordV1],
    risk_results: Sequence[CandidateRiskModeResultV1],
    oracle_comparison: CandidateOracleComparisonV1,
    raw_facts: Sequence[Mapping[str, Any]],
    normalization_records: Sequence[Mapping[str, Any]],
    output_dir: Path,
    parent_appends: Sequence[Path] = (),
) -> dict[str, Any]:
    """Persist one segment directly from the already-calculated daily objects."""

    target = _new_output_target(output_dir)
    parent = _read_parent_context(
        parent_shadow=parent_shadow,
        parent_appends=parent_appends,
    )
    source_panel = _source_panel_row(panel)
    _validate_source_binding(
        source_audit_manifest=source_audit_manifest,
        incremental_validation=incremental_validation,
        parent_manifest=parent.manifest,
        parent_chain=parent,
        parent_source_audit_logical_fingerprint=(
            parent.source_audit_logical_fingerprint
        ),
        source_panel=source_panel,
    )
    payload = _session_payload(
        source_audit_logical_fingerprint=str(
            source_audit_manifest["logical_content_fingerprint"]
        ),
        source_panel=source_panel,
        candidate_batches=candidate_batches,
        state_records=state_records,
        risk_results=risk_results,
        oracle_comparison=oracle_comparison,
        raw_facts=raw_facts,
        normalization_records=normalization_records,
    )
    projection_fingerprints = {
        field: v1._fingerprint(payload[field])
        for field in CURRENT_PROJECTION_FIELDS
    }

    if target.exists():
        evidence = read_candidate_segmented_session_candidate(
            parent_shadow=parent_shadow,
            output_dir=target,
            parent_appends=parent_appends,
        )
        manifest = _candidate_manifest(
            parent_manifest=parent.manifest,
            parent_manifest_sha256=parent.manifest_sha256,
            parent_chain=parent,
            root_shadow_contract_version=parent.root_shadow_contract_version,
            source_audit_manifest=source_audit_manifest,
            incremental_validation=incremental_validation,
            payload_descriptor=evidence.manifest["payload"],
            projection_fingerprints=projection_fingerprints,
        )
        if evidence.manifest != manifest or evidence.payload != payload:
            raise CandidateSegmentedSessionCandidateError(
                "completed session candidate differs from requested objects"
            )
        return dict(evidence.manifest)

    stage = target.with_name(f".{target.name}.staging")
    if stage.exists() or stage.is_symlink():
        evidence = _read_candidate_segmented_session_candidate_at(
            parent_shadow=parent_shadow,
            output_dir=stage,
            allow_staging=True,
            parent_appends=parent_appends,
        )
        manifest = _candidate_manifest(
            parent_manifest=parent.manifest,
            parent_manifest_sha256=parent.manifest_sha256,
            parent_chain=parent,
            root_shadow_contract_version=parent.root_shadow_contract_version,
            source_audit_manifest=source_audit_manifest,
            incremental_validation=incremental_validation,
            payload_descriptor=evidence.manifest["payload"],
            projection_fingerprints=projection_fingerprints,
        )
        if evidence.manifest != manifest or evidence.payload != payload:
            raise CandidateSegmentedSessionCandidateError(
                "staged session candidate differs from requested objects"
            )
        os.rename(stage, target)
        _fsync_directory(target.parent)
        return dict(
            read_candidate_segmented_session_candidate(
                parent_shadow=parent_shadow,
                output_dir=target,
                parent_appends=parent_appends,
            ).manifest
        )

    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    byte_count, physical_sha256 = v1._write_canonical_new(
        stage / SESSION_PAYLOAD,
        payload,
    )
    descriptor = _payload_descriptor(
        payload,
        byte_count=byte_count,
        physical_sha256=physical_sha256,
    )
    manifest = _candidate_manifest(
        parent_manifest=parent.manifest,
        parent_manifest_sha256=parent.manifest_sha256,
        parent_chain=parent,
        root_shadow_contract_version=parent.root_shadow_contract_version,
        source_audit_manifest=source_audit_manifest,
        incremental_validation=incremental_validation,
        payload_descriptor=descriptor,
        projection_fingerprints=projection_fingerprints,
    )
    manifest_bytes, manifest_sha256 = v1._write_canonical_new(
        stage / SESSION_CANDIDATE_MANIFEST,
        manifest,
    )
    _fsync_directory(stage)
    _validate_completed_physical_custody(
        output_dir=stage,
        manifest_bytes=manifest_bytes,
        manifest_sha256=manifest_sha256,
        payload_bytes=byte_count,
        payload_sha256=physical_sha256,
    )
    os.rename(stage, target)
    _fsync_directory(target.parent)
    return dict(manifest)


def read_candidate_segmented_session_candidate(
    *,
    parent_shadow: Path,
    output_dir: Path,
    parent_appends: Sequence[Path] = (),
) -> CandidateSegmentedSessionCandidateEvidence:
    """Read the direct session candidate and rebind it to the exact parent."""

    return _read_candidate_segmented_session_candidate_at(
        parent_shadow=parent_shadow,
        output_dir=output_dir,
        allow_staging=False,
        parent_appends=parent_appends,
    )


def _session_payload(
    *,
    source_audit_logical_fingerprint: str,
    source_panel: Mapping[str, Any],
    candidate_batches: Sequence[OpportunityCandidateBatchV1],
    state_records: Sequence[OpportunityCandidateStateRecordV1],
    risk_results: Sequence[CandidateRiskModeResultV1],
    oracle_comparison: CandidateOracleComparisonV1,
    raw_facts: Sequence[Mapping[str, Any]],
    normalization_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    session = str(source_panel["as_of_session"])
    universe_order = {
        str(item["universe_id"]): int(item["catalog_order"])
        for item in source_panel["universes"]
    }
    batches = tuple(
        sorted(candidate_batches, key=lambda item: universe_order[item.universe_id])
    )
    states = tuple(
        sorted(
            state_records,
            key=lambda item: (
                universe_order[item.universe_id],
                str(item.instrument_id),
            ),
        )
    )
    risk_order = {"conservative": 0, "balanced": 1, "aggressive": 2}
    risks = tuple(
        sorted(
            risk_results,
            key=lambda item: (
                universe_order[item.universe_id],
                risk_order[item.risk_mode.value],
            ),
        )
    )
    stable_raw = v1._stable_external_records(raw_facts)
    stable_normalization = v1._stable_external_records(normalization_records)
    payload = shadow._with_logical_fingerprint(
        {
            "contract_version": SESSION_PAYLOAD_CONTRACT,
            "source_audit_logical_fingerprint": source_audit_logical_fingerprint,
            "as_of_session": session,
            "universe_ids": [item.universe_id for item in batches],
            "source_panel": dict(source_panel),
            "candidate_batches": [item.model_dump(mode="json") for item in batches],
            "state_records": [item.model_dump(mode="json") for item in states],
            "transition_records": [v1._transition_row(item) for item in states],
            "raw_facts": stable_raw,
            "raw_fact_session_ordinals": list(range(len(stable_raw))),
            "normalization_records": stable_normalization,
            "risk_results": [item.model_dump(mode="json") for item in risks],
            "oracle_record": v1._jsonable(oracle_comparison),
        }
    )
    _validate_session_payload(payload)
    return payload


def _validate_source_binding(
    *,
    source_audit_manifest: Mapping[str, Any],
    incremental_validation: Mapping[str, Any],
    parent_manifest: Mapping[str, Any],
    parent_chain: _CandidateSegmentedParentContext,
    parent_source_audit_logical_fingerprint: str,
    source_panel: Mapping[str, Any],
) -> None:
    session = source_panel.get("as_of_session")
    universe_ids = tuple(
        item.get("universe_id")
        for item in source_panel.get("universes", ())
        if isinstance(item, Mapping)
    )
    if (
        source_audit_manifest.get("schema_version") != "1.1"
        or source_audit_manifest.get("execution_mode")
        != "verified_prior_incremental"
        or source_audit_manifest.get("as_of_session")
        != session
        or not shadow._is_sha256(
            source_audit_manifest.get("logical_content_fingerprint")
        )
        or tuple(source_audit_manifest.get("universe_ids", ()))
        != universe_ids
    ):
        raise CandidateSegmentedSessionCandidateError(
            "prepared source audit identity is malformed or differs"
        )
    source_contract = {
        key: source_audit_manifest.get(key) for key in shadow.SOURCE_BASE_KEYS
    }
    source_contract["execution_mode"] = source_audit_manifest.get("execution_mode")
    source_contract_fingerprint = shadow.candidate_segmented_source_contract_fingerprint(
        {
            "source_contract": source_contract,
            "universe_ids": source_audit_manifest.get("universe_ids"),
        }
    )
    if source_contract_fingerprint != parent_chain.source_contract_fingerprint:
        raise CandidateSegmentedSessionCandidateError(
            "prepared source calculation contract differs from parent chain"
        )
    reuse_checks = incremental_validation.get("reuse_checks")
    if (
        incremental_validation.get("validation_scope")
        != "verified_prior_plus_current_session_oracle"
        or incremental_validation.get("prior_audit_logical_fingerprint")
        != parent_source_audit_logical_fingerprint
        or incremental_validation.get("prior_as_of_session")
        != parent_manifest.get("as_of_session")
        or incremental_validation.get("current_as_of_session")
        != session
        or not isinstance(reuse_checks, Mapping)
        or any(value is not True for value in reuse_checks.values())
    ):
        raise CandidateSegmentedSessionCandidateError(
            "incremental validation does not bind the exact parent audit"
        )
    artifacts = {
        item.get("name"): item
        for item in source_audit_manifest.get("artifacts", ())
        if isinstance(item, Mapping)
    }
    validation_descriptor = artifacts.get(
        v1.CANDIDATE_INCREMENTAL_VALIDATION_ARTIFACT
    )
    base = {
        key: source_audit_manifest.get(key)
        for key in (*shadow.SOURCE_BASE_KEYS, "execution_mode")
    }
    expected_validation_fingerprint = v1._fingerprint(
        {**base, "record": v1._jsonable(incremental_validation)}
    )
    if (
        not isinstance(validation_descriptor, Mapping)
        or validation_descriptor.get("logical_content_fingerprint")
        != expected_validation_fingerprint
    ):
        raise CandidateSegmentedSessionCandidateError(
            "incremental validation is not bound by the prepared source audit"
        )


def _source_panel_row(
    panel: MarketRegimeInputPanel | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(panel, MarketRegimeInputPanel):
        return v1._panel_source_row(panel)
    if not isinstance(panel, Mapping):
        raise CandidateSegmentedSessionCandidateError(
            "direct session source panel is malformed"
        )
    return dict(panel)


def _validate_session_payload(payload: Mapping[str, Any]) -> None:
    session = payload.get("as_of_session")
    universe_ids = tuple(payload.get("universe_ids", ()))
    source_panel = payload.get("source_panel")
    record_fields = (
        "candidate_batches",
        "state_records",
        "transition_records",
        "raw_facts",
        "normalization_records",
        "risk_results",
    )
    if (
        payload.get("contract_version") != SESSION_PAYLOAD_CONTRACT
        or not isinstance(session, str)
        or not session
        or not universe_ids
        or len(set(universe_ids)) != len(universe_ids)
        or not isinstance(source_panel, Mapping)
        or source_panel.get("as_of_session") != session
        or not shadow._is_sha256(payload.get("source_audit_logical_fingerprint"))
        or any(
            not isinstance(payload.get(field), list)
            or any(not isinstance(item, Mapping) for item in payload[field])
            for field in record_fields
        )
        or any(
            item.get("as_of_session") != session
            for field in record_fields
            for item in payload.get(field, ())
        )
    ):
        raise CandidateSegmentedSessionCandidateError(
            "direct session payload scope differs"
        )
    panel_universes = source_panel.get("universes")
    if not isinstance(panel_universes, list) or any(
        not isinstance(item, Mapping)
        or not isinstance(item.get("universe_id"), str)
        or type(item.get("catalog_order")) is not int
        or type(item.get("member_count")) is not int
        or item["member_count"] <= 0
        for item in panel_universes
    ):
        raise CandidateSegmentedSessionCandidateError(
            "direct session source Universe scope is malformed"
        )
    ordered_panel_universes = tuple(
        sorted(panel_universes, key=lambda item: item["catalog_order"])
    )
    if (
        tuple(item["universe_id"] for item in ordered_panel_universes)
        != universe_ids
        or len({item["catalog_order"] for item in ordered_panel_universes})
        != len(ordered_panel_universes)
    ):
        raise CandidateSegmentedSessionCandidateError(
            "direct session source Universe order differs"
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
    state_universe_order = {
        universe_id: index for index, universe_id in enumerate(universe_ids)
    }
    state_keys = tuple((item.universe_id, str(item.instrument_id)) for item in states)
    expected_state_keys = tuple(
        sorted(
            state_keys,
            key=lambda item: (state_universe_order.get(item[0], len(universe_ids)), item[1]),
        )
    )
    expected_risk_keys = tuple(
        (universe_id, risk_mode)
        for universe_id in universe_ids
        for risk_mode in ("conservative", "balanced", "aggressive")
    )
    if (
        tuple(item.universe_id for item in batches) != universe_ids
        or any(
            batch.universe_member_count != panel_universe["member_count"]
            for batch, panel_universe in zip(
                batches,
                ordered_panel_universes,
                strict=True,
            )
        )
        or len(states)
        != sum(item["member_count"] for item in ordered_panel_universes)
        or state_keys != expected_state_keys
        or len(set(state_keys)) != len(state_keys)
        or any(item.universe_id not in universe_ids for item in states)
        or tuple((item.universe_id, item.risk_mode.value) for item in risks)
        != expected_risk_keys
        or payload["transition_records"]
        != [v1._transition_row(item) for item in states]
        or payload.get("raw_fact_session_ordinals")
        != list(range(len(payload.get("raw_facts", ()))))
    ):
        raise CandidateSegmentedSessionCandidateError(
            "direct session payload projections differ"
        )
    oracle = v1._oracle_from_record(payload.get("oracle_record"))
    if (
        oracle.mismatch_count != 0
        or not oracle.shared_raw_fact_match
        or not oracle.input_permutation_match
        or oracle.candidate_count != sum(len(item.candidates) for item in batches)
        or oracle.state_record_count != len(states)
        or oracle.risk_result_count != len(risks)
        or oracle.raw_fact_count != oracle.candidate_count
    ):
        raise CandidateSegmentedSessionCandidateError(
            "direct session Oracle or risk evidence differs"
        )


def _payload_descriptor(
    payload: Mapping[str, Any],
    *,
    byte_count: int,
    physical_sha256: str,
) -> dict[str, Any]:
    return {
        "relative_path": SESSION_PAYLOAD,
        "bytes": byte_count,
        "sha256": physical_sha256,
        "logical_content_fingerprint": payload["logical_content_fingerprint"],
        "candidate_batch_count": len(payload["candidate_batches"]),
        "state_record_count": len(payload["state_records"]),
        "transition_record_count": len(payload["transition_records"]),
        "raw_fact_count": len(payload["raw_facts"]),
        "normalization_record_count": len(payload["normalization_records"]),
        "risk_result_count": len(payload["risk_results"]),
        "oracle_present": payload["oracle_record"] is not None,
    }


def _candidate_manifest(
    *,
    parent_manifest: Mapping[str, Any],
    parent_manifest_sha256: str,
    parent_chain: _CandidateSegmentedParentContext,
    root_shadow_contract_version: str,
    source_audit_manifest: Mapping[str, Any],
    incremental_validation: Mapping[str, Any],
    payload_descriptor: Mapping[str, Any],
    projection_fingerprints: Mapping[str, str],
) -> dict[str, Any]:
    logical = {
        "contract_version": SESSION_CANDIDATE_CONTRACT,
        "completion_status": "completed",
        "parent": {
            "shadow_contract_version": root_shadow_contract_version,
            "manifest_sha256": parent_manifest_sha256,
            "logical_content_fingerprint": parent_manifest[
                "logical_content_fingerprint"
            ],
            "as_of_session": parent_manifest["as_of_session"],
            "session_count": parent_chain.session_count,
            "source_contract_fingerprint": parent_chain.source_contract_fingerprint,
            "final_chain_fingerprint": parent_chain.final_chain_fingerprint,
        },
        "intended_source_audit": {
            "schema_version": source_audit_manifest["schema_version"],
            "execution_mode": source_audit_manifest["execution_mode"],
            "logical_content_fingerprint": source_audit_manifest[
                "logical_content_fingerprint"
            ],
            "as_of_session": source_audit_manifest["as_of_session"],
            "physical_completion_required_before_append": True,
        },
        "incremental_validation_fingerprint": v1._fingerprint(
            incremental_validation
        ),
        "as_of_session": source_audit_manifest["as_of_session"],
        "session_ordinal": parent_chain.session_count,
        "universe_ids": list(source_audit_manifest["universe_ids"]),
        "payload": dict(payload_descriptor),
        "current_projection_fingerprints": dict(projection_fingerprints),
        "raw_fact_order": "session_local_canonical",
        "finalization_scope": "validated_write_plus_physical_custody",
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }
    return {**logical, "logical_content_fingerprint": v1._fingerprint(logical)}


def _read_candidate_segmented_session_candidate_at(
    *,
    parent_shadow: Path,
    output_dir: Path,
    allow_staging: bool,
    parent_appends: Sequence[Path] = (),
    validated_parent: _CandidateSegmentedParentContext | None = None,
) -> CandidateSegmentedSessionCandidateEvidence:
    target = _completed_output_target(output_dir, allow_staging=allow_staging)
    manifest_path = target / SESSION_CANDIDATE_MANIFEST
    payload_path = target / SESSION_PAYLOAD
    if (
        not manifest_path.is_file()
        or manifest_path.is_symlink()
        or not payload_path.is_file()
        or payload_path.is_symlink()
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate completion is unavailable"
        )
    actual_files = {item.name for item in target.iterdir() if item.is_file()}
    if actual_files != {SESSION_CANDIDATE_MANIFEST, SESSION_PAYLOAD} or any(
        item.is_dir() for item in target.iterdir()
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate file set differs"
        )
    manifest_sha256 = v1._file_sha256(manifest_path)
    manifest = shadow._read_canonical_mapping(
        manifest_path,
        physical_sha256=manifest_sha256,
    )
    manifest_fingerprint = manifest.pop("logical_content_fingerprint", None)
    if v1._fingerprint(manifest) != manifest_fingerprint:
        raise CandidateSegmentedSessionCandidateError(
            "session candidate manifest fingerprint differs"
        )
    manifest["logical_content_fingerprint"] = manifest_fingerprint
    _validate_manifest_shape(manifest)

    parent_context = validated_parent or _read_parent_context(
        parent_shadow=parent_shadow,
        parent_appends=parent_appends,
    )
    parent = manifest["parent"]
    if (
        parent.get("shadow_contract_version")
        != parent_context.root_shadow_contract_version
        or parent.get("manifest_sha256") != parent_context.manifest_sha256
        or parent.get("logical_content_fingerprint")
        != parent_context.manifest.get("logical_content_fingerprint")
        or parent.get("as_of_session") != parent_context.manifest.get("as_of_session")
        or parent.get("session_count") != parent_context.session_count
        or parent.get("source_contract_fingerprint")
        != parent_context.source_contract_fingerprint
        or parent.get("final_chain_fingerprint")
        != parent_context.final_chain_fingerprint
        or tuple(manifest.get("universe_ids", ())) != parent_context.universe_ids
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate parent chain differs"
        )

    descriptor = manifest["payload"]
    shadow._validate_file_custody(payload_path)
    if (
        payload_path.stat().st_size != descriptor.get("bytes")
        or v1._file_sha256(payload_path) != descriptor.get("sha256")
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate payload physical identity differs"
        )
    payload = shadow._read_canonical_mapping(
        payload_path,
        physical_sha256=str(descriptor["sha256"]),
    )
    payload_fingerprint = payload.pop("logical_content_fingerprint", None)
    if (
        v1._fingerprint(payload) != payload_fingerprint
        or payload_fingerprint != descriptor.get("logical_content_fingerprint")
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate payload logical identity differs"
        )
    payload["logical_content_fingerprint"] = payload_fingerprint
    _validate_session_payload(payload)
    expected_descriptor = _payload_descriptor(
        payload,
        byte_count=payload_path.stat().st_size,
        physical_sha256=str(descriptor["sha256"]),
    )
    if expected_descriptor != descriptor:
        raise CandidateSegmentedSessionCandidateError(
            "session candidate payload descriptor differs"
        )
    expected_projections = {
        field: v1._fingerprint(payload[field])
        for field in CURRENT_PROJECTION_FIELDS
    }
    if expected_projections != manifest.get("current_projection_fingerprints"):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate current projections differ"
        )
    return CandidateSegmentedSessionCandidateEvidence(
        path=target,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        payload=payload,
    )


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    parent = manifest.get("parent")
    source = manifest.get("intended_source_audit")
    descriptor = manifest.get("payload")
    if (
        manifest.get("contract_version") != SESSION_CANDIDATE_CONTRACT
        or manifest.get("completion_status") != "completed"
        or manifest.get("raw_fact_order") != "session_local_canonical"
        or manifest.get("finalization_scope")
        != "validated_write_plus_physical_custody"
        or manifest.get("external_request_count") != 0
        or manifest.get("production_write_count") != 0
        or manifest.get("publication_authorized") is not False
        or not isinstance(parent, Mapping)
        or not isinstance(source, Mapping)
        or not isinstance(descriptor, Mapping)
        or descriptor.get("relative_path") != SESSION_PAYLOAD
        or source.get("schema_version") != "1.1"
        or source.get("execution_mode") != "verified_prior_incremental"
        or source.get("physical_completion_required_before_append") is not True
        or manifest.get("as_of_session") != source.get("as_of_session")
        or type(manifest.get("session_ordinal")) is not int
        or manifest.get("session_ordinal") != parent.get("session_count")
        or not isinstance(manifest.get("universe_ids"), list)
        or not manifest["universe_ids"]
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate manifest is malformed"
        )
    fingerprints = (
        parent.get("manifest_sha256"),
        parent.get("logical_content_fingerprint"),
        parent.get("source_contract_fingerprint"),
        parent.get("final_chain_fingerprint"),
        source.get("logical_content_fingerprint"),
        manifest.get("incremental_validation_fingerprint"),
        descriptor.get("logical_content_fingerprint"),
        descriptor.get("sha256"),
    )
    if any(not shadow._is_sha256(value) for value in fingerprints):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate manifest fingerprints are malformed"
        )
    projections = manifest.get("current_projection_fingerprints")
    if (
        not isinstance(projections, Mapping)
        or set(projections) != set(CURRENT_PROJECTION_FIELDS)
        or any(not shadow._is_sha256(value) for value in projections.values())
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate projection fingerprints are malformed"
        )


def _validate_completed_physical_custody(
    *,
    output_dir: Path,
    manifest_bytes: int,
    manifest_sha256: str,
    payload_bytes: int,
    payload_sha256: str,
) -> None:
    target = _completed_output_target(output_dir, allow_staging=True)
    manifest_path = target / SESSION_CANDIDATE_MANIFEST
    payload_path = target / SESSION_PAYLOAD
    entries = tuple(target.iterdir())
    if (
        {item.name for item in entries if item.is_file()}
        != {SESSION_CANDIDATE_MANIFEST, SESSION_PAYLOAD}
        or any(item.is_dir() for item in entries)
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate physical file set differs"
        )
    for path in (manifest_path, payload_path):
        shadow._validate_file_custody(path)
    if (
        manifest_path.stat().st_size != manifest_bytes
        or v1._file_sha256(manifest_path) != manifest_sha256
        or payload_path.stat().st_size != payload_bytes
        or v1._file_sha256(payload_path) != payload_sha256
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate physical completion differs"
        )


def _new_output_target(path: Path) -> Path:
    if (
        not path.is_absolute()
        or path.parent != Path("/tmp")
        or path.name.startswith(".")
        or path.is_symlink()
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate output must be a visible direct child of /tmp"
        )
    return path


def _completed_output_target(path: Path, *, allow_staging: bool) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp"):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate must be a direct child of /tmp"
        )
    if path.name.startswith(".") and not (
        allow_staging and path.name.endswith(".staging")
    ):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate name is unsafe"
        )
    if path.is_symlink() or not path.is_dir():
        raise CandidateSegmentedSessionCandidateError(
            "session candidate directory is unsafe"
        )
    target = path.resolve(strict=True)
    metadata = target.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateSegmentedSessionCandidateError(
            "session candidate directory custody differs"
        )
    if any(item.is_symlink() for item in target.iterdir()):
        raise CandidateSegmentedSessionCandidateError(
            "session candidate contains a symlink"
        )
    return target


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
