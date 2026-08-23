"""Immutable Activation V2 publication and atomic active-pointer boundary."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import shutil
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterator, TypeAlias
from uuid import UUID, uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from tip_api.contracts.market_data.v1.dashboard_universe_activation import (
    DashboardUniverseActivationDatasetReferenceV1,
)
from tip_api.contracts.market_data.v2.dashboard_universe_activation import (
    DashboardUniverseActivationManifestV2,
    DashboardUniverseActivationPointerV1,
    DashboardUniverseActivationRecordV2,
    DashboardUniverseActivationTargetReferenceV1,
    PUBLIC_UNIVERSE_ORDER,
)
from tip_api.persistence.parquet.dashboard_universe_activation import (
    PUBLIC_SECONDARY_ID,
    CompletedDashboardUniverseActivation,
    DashboardUniverseActivationError,
    read_completed_dashboard_universe_activation,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.superseding_full_base import (
    REVISION_ID,
    read_completed_superseding_full_base,
    target_path as superseding_target_path,
)
from tip_api.services.full_base_liquidity import FULL_BASE_A_ID, FULL_BASE_B_ID
from tip_api.services.provider_classified_universe import CANDIDATE_A_ID
from tip_api.services.universe_pre_activation import membership_fingerprint


V2_BASE = "market-data/snapshots/dashboard-universe-activation-v2"
ACTIVE_POINTER = "market-data/snapshots/dashboard-universe-activation-active/active.json"
PARQUET_FILE = "part-00000.parquet"
MANIFEST_FILE = "manifest.json"
V1_LOGICAL_BASE = "market-data/snapshots/dashboard-universe-activation"
EXPECTED_SOURCE_FINGERPRINT = "51403e939930265ba1a273e9f8bc2113cb455f22e8437c1d2775005fd293ee97"
EXPECTED_PRIMARY_COUNT = 1718
EXPECTED_PRIMARY_FINGERPRINT = "c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978"
EXPECTED_SECONDARY_COUNT = 1831
EXPECTED_SECONDARY_FINGERPRINT = "2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295"
ABSENT_POINTER_FINGERPRINT = "absent"

V2_SCHEMA = pa.schema([
    pa.field("schema_version", pa.string(), False),
    pa.field("activation_id", pa.string(), False),
    pa.field("policy_version", pa.string(), False),
    pa.field("revision_id", pa.string(), False),
    pa.field("analysis_session", pa.date32(), False),
    pa.field("membership_evidence_as_of", pa.date32(), False),
    pa.field("activated_at", pa.timestamp("us", tz="UTC"), False),
    pa.field("universe_id", pa.string(), False),
    pa.field("display_name", pa.string(), False),
    pa.field("long_display_name", pa.string(), False),
    pa.field("description", pa.string(), False),
    pa.field("provisional", pa.bool_(), False),
    pa.field("is_default", pa.bool_(), False),
    pa.field("member_count", pa.int64(), False),
    pa.field("security_type_composition", pa.list_(pa.struct([
        pa.field("provider_type_code", pa.string(), False),
        pa.field("count", pa.int64(), False),
    ])), False),
    pa.field("membership_fingerprint", pa.string(), False),
    pa.field("source_publication_fingerprint", pa.string(), False),
    pa.field("trailing_liquidity_source_fingerprint", pa.string(), False),
    pa.field("reviewed_security_form_fingerprint", pa.string(), False),
    pa.field("current_eod_fingerprint", pa.string(), False),
    pa.field("previous_eod_fingerprint", pa.string(), False),
    pa.field("legacy_rollback_reference", pa.string(), False),
    pa.field("limitations", pa.list_(pa.string()), False),
    pa.field("status", pa.string(), False),
])


class DashboardUniverseActivationV2Error(DashboardUniverseActivationError):
    pass


class DashboardUniverseActivationV2ConflictError(DashboardUniverseActivationV2Error):
    pass


@dataclass(frozen=True, slots=True)
class CompletedDashboardUniverseActivationV2:
    manifest: DashboardUniverseActivationManifestV2
    universes: tuple[DashboardUniverseActivationRecordV2, ...]
    member_ids_by_universe: dict[str, frozenset[UUID]]

    def select(self, universe_id: str | None) -> tuple[DashboardUniverseActivationRecordV2, frozenset[UUID]]:
        selected = universe_id or self.manifest.default_universe_id
        records = {item.universe_id: item for item in self.universes}
        if selected not in records:
            raise ValueError("unknown dashboard universe")
        return records[selected], self.member_ids_by_universe[selected]


ActiveDashboardUniverseActivation: TypeAlias = CompletedDashboardUniverseActivation | CompletedDashboardUniverseActivationV2


@dataclass(frozen=True, slots=True)
class DashboardUniverseActivationV2Result:
    target_path: Path
    pointer_path: Path
    content_fingerprint: str
    parquet_sha256: str
    logical_content_fingerprint: str
    pointer_content_fingerprint: str


def v2_target_path(root: Path, analysis_session: date, *, revision_id: str = REVISION_ID) -> Path:
    return root / V2_BASE / f"revision={revision_id}" / f"analysis_session={analysis_session.isoformat()}"


def active_pointer_path(root: Path) -> Path:
    return root / ACTIVE_POINTER


def validate_activation_v2_preflight(root: Path, analysis_session: date) -> tuple[Path, Path]:
    safe_root = _validated_root(root)
    target = v2_target_path(safe_root, analysis_session)
    pointer = active_pointer_path(safe_root)
    _reject_symlink_chain(safe_root, target)
    _reject_symlink_chain(safe_root, pointer)
    if target.exists() or target.is_symlink():
        raise DashboardUniverseActivationV2ConflictError("V2 activation target already exists")
    if target.parent.exists():
        staging = tuple(target.parent.glob(f".{target.name}.staging-*"))
        if staging:
            raise DashboardUniverseActivationV2ConflictError("V2 activation staging residue exists")
    if pointer.parent.exists():
        pointer_staging = tuple(pointer.parent.glob(f".{pointer.name}.staging-*"))
        if pointer_staging:
            raise DashboardUniverseActivationV2ConflictError("active pointer staging residue exists")
    return target, pointer


def validate_activation_v2_link_preflight(
    root: Path, analysis_session: date
) -> CompletedDashboardUniverseActivationV2:
    """Validate an already completed immutable target for pointer-only recovery."""
    safe_root = _validated_root(root)
    target = v2_target_path(safe_root, analysis_session)
    pointer = active_pointer_path(safe_root)
    _reject_symlink_chain(safe_root, target)
    _reject_symlink_chain(safe_root, pointer)
    if target.parent.exists() and tuple(target.parent.glob(f".{target.name}.staging-*")):
        raise DashboardUniverseActivationV2ConflictError("V2 activation staging residue exists")
    if pointer.parent.exists() and tuple(pointer.parent.glob(f".{pointer.name}.staging-*")):
        raise DashboardUniverseActivationV2ConflictError("active pointer staging residue exists")
    return read_completed_dashboard_universe_activation_v2(
        safe_root, analysis_session=analysis_session, validate_sources=True
    )


def active_pointer_state_fingerprint(root: Path) -> str:
    """Return the exact CAS token for the current pointer bytes, or ``absent``."""
    safe_root = _validated_root(root)
    path = active_pointer_path(safe_root)
    _reject_symlink_chain(safe_root, path)
    content = _pointer_bytes(path)
    if content is None:
        return ABSENT_POINTER_FINGERPRINT
    # Parse and validate before exposing a token for authorization.
    pointer = read_dashboard_universe_activation_pointer(safe_root)
    assert pointer is not None
    return pointer.pointer_content_fingerprint


def read_dashboard_universe_activation_pointer(root: Path) -> DashboardUniverseActivationPointerV1 | None:
    safe_root = _validated_root(root)
    path = active_pointer_path(safe_root)
    _reject_symlink_chain(safe_root, path)
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise DashboardUniverseActivationV2Error("active activation pointer is unavailable")
    try:
        pointer = DashboardUniverseActivationPointerV1.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DashboardUniverseActivationV2Error("active activation pointer is malformed") from exc
    payload = pointer.model_dump(mode="json", exclude={"pointer_content_fingerprint"})
    if _json_fingerprint(payload) != pointer.pointer_content_fingerprint:
        raise DashboardUniverseActivationV2Error("active activation pointer fingerprint mismatch")
    return pointer


def read_active_dashboard_universe_activation(
    root: Path,
    *,
    analysis_session: date,
    validate_sources: bool = True,
) -> ActiveDashboardUniverseActivation:
    pointer = read_dashboard_universe_activation_pointer(root)
    if pointer is None:
        # Compatibility boundary: pre-pointer installations continue to read
        # the immutable V1 activation. A malformed pointer never falls back.
        return read_completed_dashboard_universe_activation(
            root, analysis_session=analysis_session, validate_sources=validate_sources
        )
    if pointer.active.analysis_session != analysis_session:
        raise DashboardUniverseActivationV2Error("active pointer analysis session mismatch")
    completed = _read_reference(root, pointer.active, validate_sources=validate_sources)
    if (
        completed.manifest.default_universe_id != pointer.default_universe_id
        or tuple(completed.manifest.available_universe_ids) != tuple(pointer.available_universe_ids)
    ):
        raise DashboardUniverseActivationV2Error("active pointer catalog mismatch")
    return completed


def read_completed_dashboard_universe_activation_v2(
    root: Path,
    *,
    analysis_session: date,
    validate_sources: bool = True,
    revision_id: str = REVISION_ID,
) -> CompletedDashboardUniverseActivationV2:
    safe_root = _validated_root(root)
    target = v2_target_path(safe_root, analysis_session, revision_id=revision_id)
    _reject_symlink_chain(safe_root, target)
    manifest_path = target / MANIFEST_FILE
    parquet_path = target / PARQUET_FILE
    if target.is_symlink() or not target.is_dir() or manifest_path.is_symlink() or parquet_path.is_symlink():
        raise DashboardUniverseActivationV2Error("V2 activation target is unavailable")
    if not manifest_path.is_file() or not parquet_path.is_file():
        raise DashboardUniverseActivationV2Error("V2 activation target is incomplete")
    try:
        manifest = DashboardUniverseActivationManifestV2.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DashboardUniverseActivationV2Error("V2 activation manifest is malformed") from exc
    if manifest.analysis_session != analysis_session or manifest.revision_id != revision_id:
        raise DashboardUniverseActivationV2Error("V2 activation target identity mismatch")
    payload = manifest.model_dump(
        mode="json",
        exclude={"manifest_version", "completion_status", "activated_at", "logical_content_fingerprint"},
    )
    if _json_fingerprint(payload) != manifest.logical_content_fingerprint:
        raise DashboardUniverseActivationV2Error("V2 activation logical fingerprint mismatch")
    if manifest.activation_dataset.dataset_path != target.relative_to(safe_root).as_posix():
        raise DashboardUniverseActivationV2Error("V2 activation dataset reference mismatch")
    if _file_sha256(parquet_path) != manifest.activation_dataset.parquet_sha256:
        raise DashboardUniverseActivationV2Error("V2 activation Parquet hash mismatch")
    table = pq.ParquetFile(parquet_path).read()
    if not table.schema.equals(V2_SCHEMA, check_metadata=False) or table.num_rows != 2:
        raise DashboardUniverseActivationV2Error("V2 activation Arrow schema or count mismatch")
    rows = table.to_pylist()
    if _rows_fingerprint(rows) != manifest.activation_dataset.content_fingerprint:
        raise DashboardUniverseActivationV2Error("V2 activation content fingerprint mismatch")
    try:
        parsed = tuple(DashboardUniverseActivationRecordV2.model_validate(row) for row in rows)
    except Exception as exc:
        raise DashboardUniverseActivationV2Error("V2 activation record validation failed") from exc
    records = _validate_v2_records(parsed, manifest)

    source = read_completed_superseding_full_base(safe_root, analysis_session=analysis_session)
    expected_source_path = superseding_target_path(safe_root, analysis_session).relative_to(safe_root).as_posix()
    if (
        manifest.source_publication_fingerprint != EXPECTED_SOURCE_FINGERPRINT
        or manifest.source_publication_path != expected_source_path
        or manifest.source_publication_fingerprint != source.manifest.logical_content_fingerprint
        or manifest.reviewed_security_form_fingerprint != source.manifest.reviewed_security_form_dataset.content_fingerprint
    ):
        raise DashboardUniverseActivationV2Error("V2 activation source publication mismatch")
    source_members = {
        FULL_BASE_A_ID: frozenset(item.instrument_id for item in source.memberships if item.policy_id == FULL_BASE_A_ID),
        FULL_BASE_B_ID: frozenset(item.instrument_id for item in source.memberships if item.policy_id == FULL_BASE_B_ID),
    }
    members = {
        CANDIDATE_A_ID: source_members[FULL_BASE_A_ID],
        PUBLIC_SECONDARY_ID: source_members[FULL_BASE_B_ID],
    }
    by_id = {item.universe_id: item for item in records}
    for universe_id, ids in members.items():
        record = by_id[universe_id]
        if len(ids) != record.member_count or membership_fingerprint(ids) != record.membership_fingerprint:
            raise DashboardUniverseActivationV2Error("V2 activation membership reference mismatch")
        if (
            record.source_publication_fingerprint != manifest.source_publication_fingerprint
            or record.reviewed_security_form_fingerprint != manifest.reviewed_security_form_fingerprint
        ):
            raise DashboardUniverseActivationV2Error("V2 activation record source mismatch")
    if members[CANDIDATE_A_ID] - members[PUBLIC_SECONDARY_ID]:
        raise DashboardUniverseActivationV2Error("V2 Primary is not a Secondary subset")
    secondary_types = {
        item.instrument_id: item.provider_type_code
        for item in source.memberships
        if item.policy_id == FULL_BASE_B_ID
    }
    if any(secondary_types[item] != "ADRC" for item in members[PUBLIC_SECONDARY_ID] - members[CANDIDATE_A_ID]):
        raise DashboardUniverseActivationV2Error("V2 Secondary minus Primary contains non-ADRC")
    expected_composition = {
        CANDIDATE_A_ID: Counter(
            item.provider_type_code for item in source.memberships if item.policy_id == FULL_BASE_A_ID
        ),
        PUBLIC_SECONDARY_ID: Counter(
            item.provider_type_code for item in source.memberships if item.policy_id == FULL_BASE_B_ID
        ),
    }
    for universe_id, counts in expected_composition.items():
        actual = {entry.provider_type_code: entry.count for entry in by_id[universe_id].security_type_composition}
        if actual != dict(counts):
            raise DashboardUniverseActivationV2Error("V2 activation security composition mismatch")
    if validate_sources:
        eod = CanonicalEodReadRepository(safe_root)
        current = eod.inspect_session(analysis_session)
        previous = eod.inspect_session(manifest.trailing_window_end)
        for record in records:
            if record.current_eod_fingerprint != current.content_fingerprint or record.previous_eod_fingerprint != previous.content_fingerprint:
                raise DashboardUniverseActivationV2Error("V2 activation EOD source mismatch")
        legacy = read_completed_dashboard_universe_activation(safe_root, analysis_session=analysis_session, validate_sources=True)
        if (
            legacy.manifest.legacy_member_count != manifest.legacy_member_count
            or legacy.manifest.legacy_membership_fingerprint != manifest.legacy_membership_fingerprint
        ):
            raise DashboardUniverseActivationV2Error("V2 activation Legacy rollback mismatch")
    return CompletedDashboardUniverseActivationV2(manifest, records, members)


@dataclass(frozen=True, slots=True)
class ParquetDashboardUniverseActivationV2Repository:
    root: Path

    def publish_and_activate(
        self,
        *,
        records: tuple[DashboardUniverseActivationRecordV2, ...],
        source_publication_path: str,
        source_publication_fingerprint: str,
        reviewed_security_form_fingerprint: str,
        legacy_member_count: int,
        legacy_membership_fingerprint: str,
        trailing_window_start: date,
        trailing_window_end: date,
        trailing_window_session_count: int,
        reviewed_override_count: int,
        reviewed_security_form_count: int,
        activated_at: datetime,
        expected_current_fingerprint: str,
        expected_current_pointer_fingerprint: str | None = None,
        expected_artifact_hashes: dict[str, Any] | None = None,
        failpoint: str | None = None,
    ) -> DashboardUniverseActivationV2Result:
        root = _validated_root(self.root)
        session = records[0].analysis_session if records else None
        if session is None:
            raise DashboardUniverseActivationV2Error("V2 activation records cannot be empty")
        target = v2_target_path(root, session)
        pointer_path = active_pointer_path(root)
        _reject_symlink_chain(root, target)
        _reject_symlink_chain(root, pointer_path)
        with _exclusive_activation_lock(root):
            initial_pointer_bytes = _pointer_bytes(pointer_path)
            observed_pointer = ABSENT_POINTER_FINGERPRINT if initial_pointer_bytes is None else read_dashboard_universe_activation_pointer(root).pointer_content_fingerprint
            if expected_current_pointer_fingerprint is not None and not hmac.compare_digest(observed_pointer, expected_current_pointer_fingerprint):
                raise DashboardUniverseActivationV2ConflictError("active pointer changed before publication")
            current = read_active_dashboard_universe_activation(root, analysis_session=session, validate_sources=True)
            if current.manifest.logical_content_fingerprint != expected_current_fingerprint:
                raise DashboardUniverseActivationV2ConflictError("active activation changed before publication")
            if expected_artifact_hashes is not None:
                observed_state = _json_fingerprint({
                    "current_activation_fingerprint": current.manifest.logical_content_fingerprint,
                    "current_pointer_fingerprint": observed_pointer,
                })
                if not hmac.compare_digest(
                    observed_state,
                    expected_artifact_hashes["expected_active_state_fingerprint"],
                ):
                    raise DashboardUniverseActivationV2ConflictError(
                        "approved active state changed before publication"
                    )
            rollback_reference = _reference_for_completed(root, current)
            if target.exists() or target.is_symlink():
                raise DashboardUniverseActivationV2ConflictError("V2 activation target already exists")
            records = _validate_v2_records(records, None)
            if source_publication_fingerprint != EXPECTED_SOURCE_FINGERPRINT:
                raise DashboardUniverseActivationV2Error("V2 activation source fingerprint is not approved")
            source = read_completed_superseding_full_base(root, analysis_session=session)
            expected_source_path = superseding_target_path(root, session).relative_to(root).as_posix()
            if (
                source_publication_path != expected_source_path
                or source.manifest.logical_content_fingerprint != source_publication_fingerprint
                or source.manifest.reviewed_security_form_dataset.content_fingerprint
                != reviewed_security_form_fingerprint
            ):
                raise DashboardUniverseActivationV2ConflictError(
                    "approved source publication changed before publication"
                )
            source_members = {
                FULL_BASE_A_ID: frozenset(
                    item.instrument_id for item in source.memberships
                    if item.policy_id == FULL_BASE_A_ID
                ),
                FULL_BASE_B_ID: frozenset(
                    item.instrument_id for item in source.memberships
                    if item.policy_id == FULL_BASE_B_ID
                ),
            }
            approved_members = {
                CANDIDATE_A_ID: source_members[FULL_BASE_A_ID],
                PUBLIC_SECONDARY_ID: source_members[FULL_BASE_B_ID],
            }
            by_universe = {item.universe_id: item for item in records}
            for universe_id, member_ids in approved_members.items():
                record = by_universe[universe_id]
                if (
                    record.member_count != len(member_ids)
                    or record.membership_fingerprint != membership_fingerprint(member_ids)
                ):
                    raise DashboardUniverseActivationV2ConflictError(
                        "approved source membership changed before publication"
                    )
            current_eod = CanonicalEodReadRepository(root).inspect_session(session)
            previous_eod = CanonicalEodReadRepository(root).inspect_session(trailing_window_end)
            if any(
                item.current_eod_fingerprint != current_eod.content_fingerprint
                or item.previous_eod_fingerprint != previous_eod.content_fingerprint
                for item in records
            ):
                raise DashboardUniverseActivationV2ConflictError(
                    "approved EOD source changed before publication"
                )
            created_parents = _mkdir_parents_tracking(root, target.parent)
            if failpoint == "after_target_parent_creation":
                for directory in created_parents:
                    try:
                        parent = directory.parent
                        directory.rmdir()
                        _fsync_directory(parent)
                    except OSError:
                        pass
                raise DashboardUniverseActivationV2Error(
                    "injected failure after target parent creation"
                )
            staging = target.parent / f".{target.name}.staging-{uuid4().hex}"
            _reject_symlink_chain(root, staging)
            if staging.exists() or staging.is_symlink():
                raise DashboardUniverseActivationV2ConflictError("V2 activation staging already exists")
            renamed = False
            try:
                staging.mkdir()
                rows = [_record_row(item) for item in records]
                table = pa.Table.from_pylist(rows, schema=V2_SCHEMA)
                parquet = staging / PARQUET_FILE
                pq.write_table(table, parquet)
                with parquet.open("rb") as handle:
                    os.fsync(handle.fileno())
                content_fingerprint = _rows_fingerprint(rows)
                parquet_sha256 = _file_sha256(parquet)
                if expected_artifact_hashes is not None and (content_fingerprint != expected_artifact_hashes["activation_content_fingerprint"] or parquet_sha256 != expected_artifact_hashes["parquet_sha256"]):
                    raise DashboardUniverseActivationV2ConflictError("approved activation artifact mismatch")
                reference = DashboardUniverseActivationDatasetReferenceV1(
                    dataset_path=target.relative_to(root).as_posix(),
                    record_count=2,
                    content_fingerprint=content_fingerprint,
                    parquet_sha256=parquet_sha256,
                )
                payload = {
                    "policy_version": "dashboard-universe-v2",
                    "revision_id": REVISION_ID,
                    "analysis_session": session.isoformat(),
                    "membership_evidence_as_of": records[0].membership_evidence_as_of.isoformat(),
                    "trailing_window_start": trailing_window_start.isoformat(),
                    "trailing_window_end": trailing_window_end.isoformat(),
                    "trailing_window_session_count": trailing_window_session_count,
                    "reviewed_override_count": reviewed_override_count,
                    "reviewed_security_form_count": reviewed_security_form_count,
                    "default_universe_id": CANDIDATE_A_ID,
                    "available_universe_ids": [CANDIDATE_A_ID, PUBLIC_SECONDARY_ID],
                    "activation_dataset": reference.model_dump(mode="json"),
                    "source_publication_path": source_publication_path,
                    "source_publication_fingerprint": source_publication_fingerprint,
                    "reviewed_security_form_fingerprint": reviewed_security_form_fingerprint,
                    "legacy_member_count": legacy_member_count,
                    "legacy_membership_fingerprint": legacy_membership_fingerprint,
                }
                logical_fingerprint = _json_fingerprint(payload)
                manifest = DashboardUniverseActivationManifestV2(
                    **payload,
                    activated_at=activated_at.astimezone(UTC),
                    logical_content_fingerprint=logical_fingerprint,
                )
                _write_json(staging / MANIFEST_FILE, manifest.model_dump(mode="json"))
                if expected_artifact_hashes is not None and (logical_fingerprint != expected_artifact_hashes["activation_logical_fingerprint"] or _file_sha256(staging / MANIFEST_FILE) != expected_artifact_hashes["manifest_sha256"]):
                    raise DashboardUniverseActivationV2ConflictError("approved activation manifest mismatch")
                active_reference = DashboardUniverseActivationTargetReferenceV1(
                    target_schema_version="2.0",
                    revision_id=REVISION_ID,
                    analysis_session=session,
                    logical_path=target.relative_to(root).as_posix(),
                    logical_content_fingerprint=logical_fingerprint,
                )
                pointer = _build_pointer(
                    active=active_reference,
                    rollback=rollback_reference,
                    switched_at=activated_at,
                )
                pointer_payload = pointer.model_dump(mode="json")
                pointer_sha = hashlib.sha256(
                    (json.dumps(pointer_payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
                ).hexdigest()
                if expected_artifact_hashes is not None and (
                    pointer.pointer_content_fingerprint
                    != expected_artifact_hashes["planned_active_pointer_fingerprint"]
                    or pointer_sha != expected_artifact_hashes["pointer_sha256"]
                ):
                    raise DashboardUniverseActivationV2ConflictError(
                        "approved activation pointer mismatch"
                    )
                _fsync_directory(staging)
                if failpoint == "before_target_rename":
                    raise DashboardUniverseActivationV2Error("injected failure before target rename")
                staging.replace(target)
                renamed = True
                _fsync_directory(target.parent)
                completed = read_completed_dashboard_universe_activation_v2(
                    root, analysis_session=session, validate_sources=True
                )
                if completed.manifest.logical_content_fingerprint != logical_fingerprint:
                    raise DashboardUniverseActivationV2Error("V2 target formal reread mismatch")
                if failpoint == "after_target_publish":
                    raise DashboardUniverseActivationV2Error("injected failure after target publication")
                if _pointer_bytes(pointer_path) != initial_pointer_bytes:
                    raise DashboardUniverseActivationV2ConflictError("active pointer changed concurrently")
                _atomic_write_pointer(root, pointer, failpoint=failpoint)
                if expected_artifact_hashes is not None:
                    if _file_sha256(target / PARQUET_FILE) != expected_artifact_hashes["parquet_sha256"]:
                        raise DashboardUniverseActivationV2Error("published Parquet differs from approved plan")
                    if _file_sha256(target / MANIFEST_FILE) != expected_artifact_hashes["manifest_sha256"]:
                        raise DashboardUniverseActivationV2Error("published manifest differs from approved plan")
                    if _file_sha256(pointer_path) != expected_artifact_hashes["pointer_sha256"]:
                        raise DashboardUniverseActivationV2Error("active pointer differs from approved plan")
                if failpoint == "after_pointer_switch":
                    raise DashboardUniverseActivationV2Error("injected failure after pointer switch")
                active = read_active_dashboard_universe_activation(
                    root, analysis_session=session, validate_sources=True
                )
                if active.manifest.logical_content_fingerprint != logical_fingerprint:
                    raise DashboardUniverseActivationV2Error("active V2 final reread mismatch")
                return DashboardUniverseActivationV2Result(
                    target,
                    pointer_path,
                    content_fingerprint,
                    parquet_sha256,
                    logical_fingerprint,
                    pointer.pointer_content_fingerprint,
                )
            except Exception:
                if staging.exists() and not staging.is_symlink():
                    shutil.rmtree(staging)
                # A completed immutable target is retained if failure occurs
                # after rename. It is never treated as active without pointer.
                if not renamed and target.exists() and not target.is_symlink():
                    shutil.rmtree(target)
                if not renamed:
                    for directory in created_parents:
                        try:
                            directory.rmdir()
                        except OSError:
                            pass
                raise

    def activate_existing(
        self,
        *,
        analysis_session: date,
        expected_current_pointer_fingerprint: str,
        expected_current_activation_fingerprint: str,
        expected_target_logical_fingerprint: str,
        switched_at: datetime,
        failpoint: str | None = None,
    ) -> DashboardUniverseActivationPointerV1:
        """Verify a completed immutable target and atomically link it active."""
        root = _validated_root(self.root)
        pointer_path = active_pointer_path(root)
        with _exclusive_activation_lock(root):
            initial_pointer_bytes = _pointer_bytes(pointer_path)
            observed_pointer_fingerprint = (
                ABSENT_POINTER_FINGERPRINT
                if initial_pointer_bytes is None
                else read_dashboard_universe_activation_pointer(root).pointer_content_fingerprint
            )
            if not hmac.compare_digest(
                observed_pointer_fingerprint, expected_current_pointer_fingerprint
            ):
                raise DashboardUniverseActivationV2ConflictError(
                    "active pointer changed before activate-existing"
                )
            current = read_active_dashboard_universe_activation(
                root, analysis_session=analysis_session, validate_sources=True
            )
            if not hmac.compare_digest(
                current.manifest.logical_content_fingerprint,
                expected_current_activation_fingerprint,
            ):
                raise DashboardUniverseActivationV2ConflictError(
                    "active activation changed before activate-existing"
                )
            completed = validate_activation_v2_link_preflight(root, analysis_session)
            if not hmac.compare_digest(
                completed.manifest.logical_content_fingerprint,
                expected_target_logical_fingerprint,
            ):
                raise DashboardUniverseActivationV2ConflictError(
                    "completed V2 target is not the approved target"
                )
            if isinstance(current, CompletedDashboardUniverseActivationV2):
                raise DashboardUniverseActivationV2ConflictError(
                    "completed V2 target is already active"
                )
            if _pointer_bytes(pointer_path) != initial_pointer_bytes:
                raise DashboardUniverseActivationV2ConflictError(
                    "active pointer changed concurrently"
                )
            pointer = _build_pointer(
                active=_reference_for_completed(root, completed),
                rollback=_reference_for_completed(root, current),
                switched_at=switched_at,
            )
            _atomic_write_pointer(root, pointer, failpoint=failpoint)
            active = read_active_dashboard_universe_activation(
                root, analysis_session=analysis_session, validate_sources=True
            )
            if active.manifest.logical_content_fingerprint != expected_target_logical_fingerprint:
                raise DashboardUniverseActivationV2Error(
                    "activate-existing final active reread failed"
                )
            return pointer


def rollback_active_dashboard_universe_activation(
    root: Path,
    *,
    analysis_session: date,
    expected_active_pointer_fingerprint: str,
    switched_at: datetime,
) -> DashboardUniverseActivationPointerV1:
    safe_root = _validated_root(root)
    pointer_path = active_pointer_path(safe_root)
    with _exclusive_activation_lock(safe_root):
        initial_pointer_bytes = _pointer_bytes(pointer_path)
        pointer = read_dashboard_universe_activation_pointer(safe_root)
        if pointer is None:
            raise DashboardUniverseActivationV2Error("rollback requires an explicit active pointer")
        if not hmac.compare_digest(
            pointer.pointer_content_fingerprint, expected_active_pointer_fingerprint
        ):
            raise DashboardUniverseActivationV2ConflictError("active activation changed before rollback")
        if pointer.active.analysis_session != analysis_session or pointer.rollback.analysis_session != analysis_session:
            raise DashboardUniverseActivationV2Error("rollback pointer session mismatch")
        _read_reference(safe_root, pointer.active, validate_sources=True)
        rollback_target = _read_reference(safe_root, pointer.rollback, validate_sources=True)
        replacement = _build_pointer(
            active=pointer.rollback,
            rollback=pointer.active,
            switched_at=switched_at,
        )
        if _pointer_bytes(pointer_path) != initial_pointer_bytes:
            raise DashboardUniverseActivationV2ConflictError(
                "active pointer changed concurrently before rollback"
            )
        _atomic_write_pointer(safe_root, replacement)
        reread = read_active_dashboard_universe_activation(
            safe_root, analysis_session=analysis_session, validate_sources=True
        )
        if reread.manifest.logical_content_fingerprint != rollback_target.manifest.logical_content_fingerprint:
            raise DashboardUniverseActivationV2Error("rollback final reread mismatch")
        return replacement


def _read_reference(
    root: Path,
    reference: DashboardUniverseActivationTargetReferenceV1,
    *,
    validate_sources: bool,
) -> ActiveDashboardUniverseActivation:
    if reference.target_schema_version == "1.0":
        expected_path = f"{V1_LOGICAL_BASE}/analysis_session={reference.analysis_session.isoformat()}"
        if reference.logical_path != expected_path:
            raise DashboardUniverseActivationV2Error("V1 activation pointer path mismatch")
        completed = read_completed_dashboard_universe_activation(
            root, analysis_session=reference.analysis_session, validate_sources=validate_sources
        )
    else:
        expected_path = v2_target_path(root, reference.analysis_session, revision_id=reference.revision_id or "").relative_to(root).as_posix()
        if reference.logical_path != expected_path:
            raise DashboardUniverseActivationV2Error("V2 activation pointer path mismatch")
        completed = read_completed_dashboard_universe_activation_v2(
            root,
            analysis_session=reference.analysis_session,
            validate_sources=validate_sources,
            revision_id=reference.revision_id or "",
        )
    if completed.manifest.logical_content_fingerprint != reference.logical_content_fingerprint:
        raise DashboardUniverseActivationV2Error("activation pointer target fingerprint mismatch")
    return completed


def _reference_for_completed(
    root: Path,
    completed: ActiveDashboardUniverseActivation,
) -> DashboardUniverseActivationTargetReferenceV1:
    if isinstance(completed, CompletedDashboardUniverseActivationV2):
        schema_version = "2.0"
        revision_id = completed.manifest.revision_id
        path = v2_target_path(root, completed.manifest.analysis_session, revision_id=revision_id).relative_to(root).as_posix()
    else:
        schema_version = "1.0"
        revision_id = None
        path = f"{V1_LOGICAL_BASE}/analysis_session={completed.manifest.analysis_session.isoformat()}"
    return DashboardUniverseActivationTargetReferenceV1(
        target_schema_version=schema_version,
        revision_id=revision_id,
        analysis_session=completed.manifest.analysis_session,
        logical_path=path,
        logical_content_fingerprint=completed.manifest.logical_content_fingerprint,
    )


def _build_pointer(
    *,
    active: DashboardUniverseActivationTargetReferenceV1,
    rollback: DashboardUniverseActivationTargetReferenceV1,
    switched_at: datetime,
) -> DashboardUniverseActivationPointerV1:
    payload = {
        "pointer_version": "1.0",
        "status": "active",
        "active": active.model_dump(mode="json"),
        "rollback": rollback.model_dump(mode="json"),
        "default_universe_id": CANDIDATE_A_ID,
        "available_universe_ids": [CANDIDATE_A_ID, PUBLIC_SECONDARY_ID],
        "switched_at": switched_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    return DashboardUniverseActivationPointerV1(
        **payload,
        pointer_content_fingerprint=_json_fingerprint(payload),
    )


def _atomic_write_pointer(
    root: Path,
    pointer: DashboardUniverseActivationPointerV1,
    *,
    failpoint: str | None = None,
) -> None:
    path = active_pointer_path(root)
    _reject_symlink_chain(root, path)
    created_parents = _mkdir_parents_durable(root, path.parent)
    _reject_symlink_chain(root, path)
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise DashboardUniverseActivationV2Error("active pointer path is unsafe")
    staging = path.parent / f".{path.name}.staging-{uuid4().hex}"
    if staging.exists() or staging.is_symlink():
        raise DashboardUniverseActivationV2ConflictError("active pointer staging exists")
    try:
        if failpoint == "after_pointer_parent_creation":
            raise DashboardUniverseActivationV2Error(
                "injected failure after pointer parent creation"
            )
        _write_json(staging, pointer.model_dump(mode="json"))
        os.replace(staging, path)
        _fsync_directory(path.parent)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            staging.unlink()
        for directory in created_parents:
            try:
                parent = directory.parent
                directory.rmdir()
                _fsync_directory(parent)
            except OSError:
                pass
        raise


def _validate_v2_records(
    records: tuple[DashboardUniverseActivationRecordV2, ...],
    manifest: DashboardUniverseActivationManifestV2 | None,
) -> tuple[DashboardUniverseActivationRecordV2, ...]:
    if len(records) != 2 or {item.universe_id for item in records} != {CANDIDATE_A_ID, PUBLIC_SECONDARY_ID}:
        raise DashboardUniverseActivationV2Error("V2 activation requires exactly two universes")
    if len({item.activation_id for item in records}) != 2 or len({item.analysis_session for item in records}) != 1:
        raise DashboardUniverseActivationV2Error("V2 activation record identity conflict")
    if sum(item.is_default for item in records) != 1 or not next(item for item in records if item.is_default).universe_id == CANDIDATE_A_ID:
        raise DashboardUniverseActivationV2Error("Common Shares must remain the sole default")
    by_input_id = {item.universe_id: item for item in records}
    ordered = tuple(by_input_id[universe_id] for universe_id in PUBLIC_UNIVERSE_ORDER)
    by_id = {item.universe_id: item for item in ordered}
    if (
        by_id[CANDIDATE_A_ID].member_count != EXPECTED_PRIMARY_COUNT
        or by_id[CANDIDATE_A_ID].membership_fingerprint != EXPECTED_PRIMARY_FINGERPRINT
        or by_id[PUBLIC_SECONDARY_ID].member_count != EXPECTED_SECONDARY_COUNT
        or by_id[PUBLIC_SECONDARY_ID].membership_fingerprint != EXPECTED_SECONDARY_FINGERPRINT
    ):
        raise DashboardUniverseActivationV2Error("V2 activation approved membership gate failed")
    if manifest is not None:
        if tuple(item.universe_id for item in ordered) != manifest.available_universe_ids:
            raise DashboardUniverseActivationV2Error("V2 activation manifest catalog mismatch")
        if any(item.analysis_session != manifest.analysis_session for item in ordered):
            raise DashboardUniverseActivationV2Error("V2 activation record session mismatch")
    return ordered


def _record_row(item: DashboardUniverseActivationRecordV2) -> dict[str, Any]:
    row = item.model_dump(mode="python")
    row["activation_id"] = str(item.activation_id)
    row["security_type_composition"] = [entry.model_dump(mode="python") for entry in item.security_type_composition]
    return row


def _rows_fingerprint(rows: list[dict[str, Any]]) -> str:
    normalized = []
    for row in rows:
        normalized.append({key: _canonical(value) for key, value in row.items() if key != "activated_at"})
    return _json_fingerprint(normalized)


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    return value


def _json_fingerprint(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validated_root(root: Path) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise DashboardUniverseActivationV2Error("data root must be an absolute regular directory")
    return root.resolve(strict=True)


def _mkdir_parents_durable(root: Path, directory: Path) -> tuple[Path, ...]:
    missing: list[Path] = []
    current = directory
    while current != root and not current.exists():
        missing.append(current)
        current = current.parent
    _reject_symlink_chain(root, current)
    for path in reversed(missing):
        _reject_symlink_chain(root, path.parent)
        path.mkdir()
        # Persist the new directory itself and the parent directory entry.
        _fsync_directory(path)
        _fsync_directory(path.parent)
    return tuple(missing)


# Backward-compatible private name retained for focused fault-injection tests.
_mkdir_parents_tracking = _mkdir_parents_durable


def _reject_symlink_chain(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise DashboardUniverseActivationV2Error("activation path escapes data root") from exc
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DashboardUniverseActivationV2Error("symlink activation path rejected")


def _pointer_bytes(path: Path) -> bytes | None:
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise DashboardUniverseActivationV2Error("active pointer path is unsafe")
    return path.read_bytes()


@contextmanager
def _exclusive_activation_lock(root: Path) -> Iterator[None]:
    descriptor = os.open(root, os.O_RDONLY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DashboardUniverseActivationV2ConflictError("another activation operation is in progress") from exc
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
