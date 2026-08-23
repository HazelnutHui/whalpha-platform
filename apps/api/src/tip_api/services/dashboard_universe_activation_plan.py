"""Canonical cryptographic approval plan for Dashboard Activation V2."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1.dashboard_universe_activation import DashboardUniverseActivationDatasetReferenceV1
from tip_api.contracts.market_data.v2.dashboard_universe_activation import DashboardUniverseActivationManifestV2, DashboardUniverseActivationTargetReferenceV1
from tip_api.persistence.parquet.dashboard_universe_activation_active import (
    ACTIVE_POINTER, MANIFEST_FILE, PARQUET_FILE, V2_SCHEMA, _build_pointer,
    _file_sha256, _json_fingerprint, _record_row, _reference_for_completed,
    _rows_fingerprint, active_pointer_state_fingerprint,
    read_active_dashboard_universe_activation, v2_target_path,
)
from tip_api.persistence.parquet.superseding_full_base import REVISION_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID

PLAN_SCHEMA_VERSION = "1.0"
PLAN_FIELDS = frozenset({
    "schema_version", "revision_id", "analysis_session", "source_publication_id",
    "source_publication_path", "source_publication_fingerprint",
    "reviewed_security_form_fingerprint", "expected_current_pointer_fingerprint",
    "expected_current_activation_fingerprint", "expected_active_state_fingerprint",
    "activated_at", "activation_ids", "universes", "target_path", "parquet_path",
    "manifest_path", "pointer_path", "activation_content_fingerprint",
    "activation_logical_fingerprint", "parquet_sha256", "manifest_sha256",
    "planned_active_pointer_fingerprint", "pointer_sha256", "rollback_target",
    "rollback_authorization_digest", "planned_inventory_change", "plan_sha256",
})


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def plan_sha256(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "plan_sha256"}
    return hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()


def build_activation_approval_plan(root: Path, plan: Any) -> dict[str, Any]:
    root = root.resolve(strict=True)
    target = v2_target_path(root, plan.records[0].analysis_session)
    pointer_path = root / ACTIVE_POINTER
    current = read_active_dashboard_universe_activation(
        root, analysis_session=plan.records[0].analysis_session, validate_sources=True
    )
    rows = [_record_row(item) for item in plan.records]
    content_fingerprint = _rows_fingerprint(rows)
    with tempfile.TemporaryDirectory(prefix="tip-activation-plan-", dir="/tmp") as temp:
        parquet = Path(temp) / PARQUET_FILE
        pq.write_table(pa.Table.from_pylist(rows, schema=V2_SCHEMA), parquet)
        parquet_sha = _file_sha256(parquet)
    reference = DashboardUniverseActivationDatasetReferenceV1(
        dataset_path=target.relative_to(root).as_posix(), record_count=2,
        content_fingerprint=content_fingerprint, parquet_sha256=parquet_sha,
    )
    manifest_payload = {
        "policy_version": "dashboard-universe-v2", "revision_id": REVISION_ID,
        "analysis_session": plan.records[0].analysis_session.isoformat(),
        "membership_evidence_as_of": plan.records[0].membership_evidence_as_of.isoformat(),
        "trailing_window_start": "2026-07-22", "trailing_window_end": "2026-08-18",
        "trailing_window_session_count": 20,
        "reviewed_override_count": plan.reviewed_override_count,
        "reviewed_security_form_count": plan.reviewed_security_form_count,
        "default_universe_id": CANDIDATE_A_ID,
        "available_universe_ids": [item.universe_id for item in plan.records],
        "activation_dataset": reference.model_dump(mode="json"),
        "source_publication_path": plan.source_path,
        "source_publication_fingerprint": plan.source_fingerprint,
        "reviewed_security_form_fingerprint": plan.reviewed_security_form_fingerprint,
        "legacy_member_count": plan.legacy_count,
        "legacy_membership_fingerprint": plan.legacy_fingerprint,
    }
    logical = _json_fingerprint(manifest_payload)
    manifest = DashboardUniverseActivationManifestV2(
        **manifest_payload, activated_at=plan.activated_at,
        logical_content_fingerprint=logical,
    )
    manifest_bytes = canonical_json_bytes(manifest.model_dump(mode="json"))
    active_reference = DashboardUniverseActivationTargetReferenceV1(
        target_schema_version="2.0", revision_id=REVISION_ID,
        analysis_session=plan.records[0].analysis_session,
        logical_path=target.relative_to(root).as_posix(),
        logical_content_fingerprint=logical,
    )
    rollback_reference = _reference_for_completed(root, current)
    pointer = _build_pointer(active=active_reference, rollback=rollback_reference, switched_at=plan.activated_at)
    pointer_bytes = canonical_json_bytes(pointer.model_dump(mode="json"))
    pointer_state = active_pointer_state_fingerprint(root)
    active_state = _json_fingerprint({
        "current_activation_fingerprint": plan.current_fingerprint,
        "current_pointer_fingerprint": pointer_state,
    })
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "revision_id": REVISION_ID,
        "analysis_session": plan.records[0].analysis_session.isoformat(),
        "source_publication_id": plan.source_fingerprint,
        "source_publication_path": str((root / plan.source_path).resolve(strict=True)),
        "source_publication_fingerprint": plan.source_fingerprint,
        "reviewed_security_form_fingerprint": plan.reviewed_security_form_fingerprint,
        "expected_current_pointer_fingerprint": pointer_state,
        "expected_current_activation_fingerprint": plan.current_fingerprint,
        "expected_active_state_fingerprint": active_state,
        "activated_at": plan.activated_at.isoformat().replace("+00:00", "Z"),
        "activation_ids": [str(item.activation_id) for item in plan.records],
        "universes": [{
            "universe_id": item.universe_id, "member_count": item.member_count,
            "composition": {entry.provider_type_code: entry.count for entry in item.security_type_composition},
            "membership_fingerprint": item.membership_fingerprint,
        } for item in plan.records],
        "target_path": str(target), "parquet_path": str(target / PARQUET_FILE),
        "manifest_path": str(target / MANIFEST_FILE), "pointer_path": str(pointer_path),
        "activation_content_fingerprint": content_fingerprint,
        "activation_logical_fingerprint": logical,
        "parquet_sha256": parquet_sha,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "planned_active_pointer_fingerprint": pointer.pointer_content_fingerprint,
        "pointer_sha256": hashlib.sha256(pointer_bytes).hexdigest(),
        "rollback_target": rollback_reference.model_dump(mode="json"),
        "rollback_authorization_digest": pointer.pointer_content_fingerprint,
        "planned_inventory_change": {"new_files": 3, "modified_files": 0},
    }
    payload["plan_sha256"] = plan_sha256(payload)
    return payload


def load_approved_plan(path: Path, approved_sha256: str) -> dict[str, Any]:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RuntimeError("approved plan must be an absolute regular non-symlink file")
    if not path.resolve().is_relative_to(Path("/tmp")):
        raise RuntimeError("approved plan must be located under /tmp")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise RuntimeError("approved plan contract is invalid")
    if frozenset(value) != PLAN_FIELDS:
        raise RuntimeError("approved plan fields are incomplete or contain extras")
    actual = plan_sha256(value)
    if value.get("plan_sha256") != actual or approved_sha256 != actual:
        raise RuntimeError("approved plan SHA-256 mismatch")
    return value
