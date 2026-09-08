"""No-write publication planning for segmented Candidate chain heads."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services import opportunity_candidate_segmented_append as append
from tip_api.services import opportunity_candidate_segmented_chain_head as head
from tip_api.services import opportunity_candidate_segmented_shadow as shadow


PUBLICATION_PLAN_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-publication-plan/1.0"
)
CURRENT_POINTER_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-current-pointer/1.0"
)
CURRENT_STATE_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-current-state/1.0"
)
FAMILY_INVENTORY_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-family-inventory/1.0"
)
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
FAMILY_RELATIVE_PATH = PurePosixPath(
    "analytics/opportunity-candidate/segmented-chain-head"
)
RELEASES_DIRECTORY = "releases"
CURRENT_POINTER_FILE = "current.json"
PLAN_STATUS = "review_ready"
ABSENT_POINTER_STATE_FINGERPRINT = v1._fingerprint(
    {
        "contract_version": CURRENT_STATE_CONTRACT,
        "status": "absent",
    }
)


class CandidateSegmentedChainHeadPublicationError(RuntimeError):
    """Raised when a chain-head publication plan is not exactly provable."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainHeadCurrentState:
    canonical_root: Path
    family_root: Path
    family_inventory_fingerprint: str
    current_pointer_state_fingerprint: str
    pointer: Mapping[str, Any] | None
    pointer_sha256: str | None
    active_manifest: Mapping[str, Any] | None
    rollback_manifest: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainHeadPublicationPlanEvidence:
    path: Path
    plan: Mapping[str, Any]
    plan_sha256: str
    source: head.CandidateSegmentedChainHeadEvidence
    current_state: CandidateSegmentedChainHeadCurrentState
    external_request_count: int = 0
    canonical_write_count: int = 0
    apply_authorized: bool = False


def build_candidate_segmented_chain_head_publication_plan(
    *,
    canonical_root: Path,
    base_shadow: Path,
    source_chain_head: Path,
    expected_source_logical_fingerprint: str,
    created_at: datetime,
    plan_path: Path,
) -> CandidateSegmentedChainHeadPublicationPlanEvidence:
    """Build and formally reread one immutable-release/pointer plan."""

    root = _validated_canonical_root(canonical_root)
    source = _read_source(
        base_shadow=base_shadow,
        source_chain_head=source_chain_head,
        expected_source_logical_fingerprint=(
            expected_source_logical_fingerprint
        ),
    )
    current = read_candidate_segmented_chain_head_current_state(
        canonical_root=root,
    )
    _require_immediate_successor(source=source, current=current)
    plan = _build_plan(
        canonical_root=root,
        source=source,
        current=current,
        created_at=normalize_utc_datetime(created_at),
    )
    target = _write_plan(plan=plan, plan_path=plan_path)
    return read_candidate_segmented_chain_head_publication_plan(
        plan_path=target,
        expected_plan_sha256=v1._file_sha256(target),
        expected_plan_logical_fingerprint=str(
            plan["logical_content_fingerprint"]
        ),
        expected_source_logical_fingerprint=(
            expected_source_logical_fingerprint
        ),
    )


def read_candidate_segmented_chain_head_publication_plan(
    *,
    plan_path: Path,
    expected_plan_sha256: str,
    expected_plan_logical_fingerprint: str,
    expected_source_logical_fingerprint: str,
) -> CandidateSegmentedChainHeadPublicationPlanEvidence:
    """Reread source, target absence, current pointer, and family CAS state."""

    for value, label in (
        (expected_plan_sha256, "expected plan SHA-256"),
        (expected_plan_logical_fingerprint, "expected plan logical fingerprint"),
        (
            expected_source_logical_fingerprint,
            "expected source logical fingerprint",
        ),
    ):
        if not shadow._is_sha256(value):
            raise CandidateSegmentedChainHeadPublicationError(
                f"{label} is malformed"
            )
    path = _validated_plan_file(plan_path)
    plan_sha256 = v1._file_sha256(path)
    if plan_sha256 != expected_plan_sha256:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication plan SHA-256 differs"
        )
    plan = _read_canonical_mapping(path, expected_sha256=plan_sha256)
    logical_fingerprint = plan.pop("logical_content_fingerprint", None)
    if (
        v1._fingerprint(plan) != logical_fingerprint
        or logical_fingerprint != expected_plan_logical_fingerprint
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication plan logical identity differs"
        )
    plan["logical_content_fingerprint"] = logical_fingerprint
    _validate_plan_shape(plan)

    root = _validated_canonical_root(Path(str(plan["canonical_root"])))
    source_section = plan["source"]
    source = _read_source(
        base_shadow=Path(str(source_section["base_shadow_path"])),
        source_chain_head=Path(str(source_section["package_path"])),
        expected_source_logical_fingerprint=(
            expected_source_logical_fingerprint
        ),
    )
    expected_target = _release_reference(
        source=source,
        canonical_root=root,
    )
    target_section = plan["target"]
    if (
        source_section != _source_descriptor(source)
        or target_section
        != _target_descriptor_for_source(source, root)
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head plan source or target identity changed"
        )
    _require_absent_release_target(
        canonical_root=root,
        release_relative_path=str(expected_target["release_relative_path"]),
    )

    current = read_candidate_segmented_chain_head_current_state(
        canonical_root=root,
    )
    expected_state = plan["expected_current_state"]
    if expected_state != _state_descriptor(current):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head current state changed after planning"
        )
    _require_immediate_successor(source=source, current=current)
    expected_plan = _build_plan(
        canonical_root=root,
        source=source,
        current=current,
        created_at=_parse_created_at(plan["created_at"]),
    )
    if expected_plan != plan:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication plan content changed"
        )
    return CandidateSegmentedChainHeadPublicationPlanEvidence(
        path=path,
        plan=plan,
        plan_sha256=plan_sha256,
        source=source,
        current_state=current,
    )


def read_candidate_segmented_chain_head_current_state(
    *,
    canonical_root: Path,
) -> CandidateSegmentedChainHeadCurrentState:
    """Read the bounded family inventory and exact active/rollback references."""

    root = _validated_canonical_root(canonical_root)
    family_root = root.joinpath(*FAMILY_RELATIVE_PATH.parts)
    inventory_fingerprint = _family_inventory_fingerprint(
        canonical_root=root,
    )
    pointer_path = family_root / CURRENT_POINTER_FILE
    if not os.path.lexists(pointer_path):
        return CandidateSegmentedChainHeadCurrentState(
            canonical_root=root,
            family_root=family_root,
            family_inventory_fingerprint=inventory_fingerprint,
            current_pointer_state_fingerprint=(
                ABSENT_POINTER_STATE_FINGERPRINT
            ),
            pointer=None,
            pointer_sha256=None,
            active_manifest=None,
            rollback_manifest=None,
        )
    _validate_canonical_file(pointer_path)
    pointer_sha256 = v1._file_sha256(pointer_path)
    pointer = _read_canonical_mapping(
        pointer_path,
        expected_sha256=pointer_sha256,
    )
    _validate_pointer_shape(pointer)
    releases = _read_release_sequence(
        canonical_root=root,
        family_root=family_root,
    )
    expected_active_reference, active_manifest = releases[-1]
    expected_rollback_reference = (
        None if len(releases) == 1 else releases[-2][0]
    )
    rollback_manifest = None if len(releases) == 1 else releases[-2][1]
    rollback_reference = pointer["rollback"]
    if (
        pointer["active"] != expected_active_reference
        or rollback_reference != expected_rollback_reference
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head pointer does not select the retained lineage tip"
        )
    pointer_state_fingerprint = v1._fingerprint(
        {
            "contract_version": CURRENT_STATE_CONTRACT,
            "status": "present",
            "pointer_sha256": pointer_sha256,
            "pointer_logical_content_fingerprint": pointer[
                "logical_content_fingerprint"
            ],
            "active_chain_head_logical_fingerprint": pointer["active"][
                "chain_head_logical_content_fingerprint"
            ],
            "active_chain_head_manifest_sha256": pointer["active"][
                "chain_head_manifest_sha256"
            ],
            "rollback_chain_head_logical_fingerprint": (
                None
                if rollback_reference is None
                else rollback_reference[
                    "chain_head_logical_content_fingerprint"
                ]
            ),
        }
    )
    return CandidateSegmentedChainHeadCurrentState(
        canonical_root=root,
        family_root=family_root,
        family_inventory_fingerprint=inventory_fingerprint,
        current_pointer_state_fingerprint=pointer_state_fingerprint,
        pointer=pointer,
        pointer_sha256=pointer_sha256,
        active_manifest=active_manifest,
        rollback_manifest=rollback_manifest,
    )


def _build_plan(
    *,
    canonical_root: Path,
    source: head.CandidateSegmentedChainHeadEvidence,
    current: CandidateSegmentedChainHeadCurrentState,
    created_at: datetime,
) -> dict[str, Any]:
    active = _release_reference(source=source, canonical_root=canonical_root)
    rollback = None if current.pointer is None else current.pointer["active"]
    pointer = _build_pointer(
        active=active,
        rollback=rollback,
        prior_pointer_state_fingerprint=(
            current.current_pointer_state_fingerprint
        ),
    )
    pointer_bytes = v1._canonical_bytes(pointer)
    source_bytes = source.path.joinpath(head.CHAIN_HEAD_MANIFEST).stat().st_size
    pointer_exists = current.pointer is not None
    logical: dict[str, Any] = {
        "contract_version": PUBLICATION_PLAN_CONTRACT,
        "status": PLAN_STATUS,
        "created_at": _format_utc(created_at),
        "canonical_root": str(canonical_root),
        "family_relative_path": FAMILY_RELATIVE_PATH.as_posix(),
        "source": _source_descriptor(source),
        "target": _target_descriptor_for_source(source, canonical_root),
        "expected_current_state": _state_descriptor(current),
        "planned_pointer": pointer,
        "planned_pointer_sha256": hashlib.sha256(pointer_bytes).hexdigest(),
        "planned_pointer_bytes": len(pointer_bytes),
        "inventory_change": {
            "new_files": 1 + (0 if pointer_exists else 1),
            "modified_files": 1 if pointer_exists else 0,
            "new_immutable_bytes": source_bytes,
            "pointer_bytes": len(pointer_bytes),
        },
        "apply_order": [
            "immutable_release_first",
            "current_pointer_last",
        ],
        "recovery_policy": {
            "neither_target_present": "not_started",
            "exact_release_only": "pointer_completion_requires_fresh_cas",
            "exact_pointer_active": "complete",
            "other_state": "block_for_diagnosis",
        },
        "rollback_policy": {
            "reference": rollback,
            "automatic_rollback_authorized": False,
            "separate_exact_pointer_cas_required": True,
        },
        "retention_policy": {
            "immutable_releases": "retain_all",
            "automatic_pruning_authorized": False,
            "rationale": "bounded_chain_head_evidence",
        },
        "source_formal_read_complete": True,
        "target_absence_verified": True,
        "current_family_state_bound": True,
        "current_pointer_state_bound": True,
        "immediate_successor_verified": True,
        "external_request_count": 0,
        "canonical_write_count": 0,
        "production_write_count": 0,
        "apply_authorized": False,
        "rollback_authorized": False,
        "executor_authorized": False,
        "scheduler_authorized": False,
        "production_consumer_authorized": False,
    }
    return {
        **logical,
        "logical_content_fingerprint": v1._fingerprint(logical),
    }


def _read_source(
    *,
    base_shadow: Path,
    source_chain_head: Path,
    expected_source_logical_fingerprint: str,
) -> head.CandidateSegmentedChainHeadEvidence:
    try:
        return head.read_candidate_segmented_chain_head(
            base_shadow=base_shadow,
            output_dir=source_chain_head,
            expected_logical_fingerprint=expected_source_logical_fingerprint,
        )
    except Exception as exc:
        raise CandidateSegmentedChainHeadPublicationError(
            f"chain-head publication source is invalid: {type(exc).__name__}"
        ) from exc


def _source_descriptor(
    source: head.CandidateSegmentedChainHeadEvidence,
) -> dict[str, Any]:
    manifest = source.manifest
    parent = source.parent
    return {
        "base_shadow_path": str(parent.base_shadow_path),
        "package_path": str(source.path),
        "manifest_file": head.CHAIN_HEAD_MANIFEST,
        "manifest_bytes": source.path.joinpath(
            head.CHAIN_HEAD_MANIFEST
        ).stat().st_size,
        "manifest_sha256": source.manifest_sha256,
        "logical_content_fingerprint": manifest[
            "logical_content_fingerprint"
        ],
        "lineage_fingerprint": manifest["lineage_fingerprint"],
        "as_of_session": parent.as_of_session,
        "session_count": parent.session_count,
        "append_count": parent.append_count,
        "source_contract_fingerprint": (
            parent.source_contract_fingerprint
        ),
        "source_audit_logical_fingerprint": (
            parent.source_audit_logical_fingerprint
        ),
        "lineage_tip_manifest_sha256": parent.manifest_sha256,
        "lineage_tip_logical_content_fingerprint": parent.manifest[
            "logical_content_fingerprint"
        ],
        "final_chain_fingerprint": parent.final_chain_fingerprint,
        "universe_ids": list(parent.universe_ids),
    }


def _release_reference(
    *,
    source: head.CandidateSegmentedChainHeadEvidence,
    canonical_root: Path,
) -> dict[str, Any]:
    descriptor = _source_descriptor(source)
    release_relative = (
        FAMILY_RELATIVE_PATH
        / RELEASES_DIRECTORY
        / str(descriptor["logical_content_fingerprint"])
    )
    manifest_relative = release_relative / head.CHAIN_HEAD_MANIFEST
    _resolve_relative(canonical_root, manifest_relative.as_posix())
    return {
        "release_relative_path": release_relative.as_posix(),
        "manifest_relative_path": manifest_relative.as_posix(),
        "chain_head_contract_version": head.CHAIN_HEAD_CONTRACT,
        "chain_head_manifest_sha256": descriptor["manifest_sha256"],
        "chain_head_logical_content_fingerprint": descriptor[
            "logical_content_fingerprint"
        ],
        "lineage_fingerprint": descriptor["lineage_fingerprint"],
        "as_of_session": descriptor["as_of_session"],
        "session_count": descriptor["session_count"],
        "append_count": descriptor["append_count"],
        "source_contract_fingerprint": descriptor[
            "source_contract_fingerprint"
        ],
        "source_audit_logical_fingerprint": descriptor[
            "source_audit_logical_fingerprint"
        ],
        "lineage_tip_manifest_sha256": descriptor[
            "lineage_tip_manifest_sha256"
        ],
        "lineage_tip_logical_content_fingerprint": descriptor[
            "lineage_tip_logical_content_fingerprint"
        ],
        "final_chain_fingerprint": descriptor["final_chain_fingerprint"],
        "universe_ids": descriptor["universe_ids"],
    }


def _target_descriptor(reference: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "release_relative_path": reference["release_relative_path"],
        "manifest_relative_path": reference["manifest_relative_path"],
        "manifest_bytes": None,
        "manifest_sha256": reference["chain_head_manifest_sha256"],
        "logical_content_fingerprint": reference[
            "chain_head_logical_content_fingerprint"
        ],
        "required_absent": True,
    }


def _build_pointer(
    *,
    active: Mapping[str, Any],
    rollback: Mapping[str, Any] | None,
    prior_pointer_state_fingerprint: str,
) -> dict[str, Any]:
    logical = {
        "contract_version": CURRENT_POINTER_CONTRACT,
        "status": "active",
        "active": dict(active),
        "rollback": None if rollback is None else dict(rollback),
        "prior_pointer_state_fingerprint": (
            prior_pointer_state_fingerprint
        ),
    }
    return {
        **logical,
        "logical_content_fingerprint": v1._fingerprint(logical),
    }


def _state_descriptor(
    state: CandidateSegmentedChainHeadCurrentState,
) -> dict[str, Any]:
    return {
        "family_inventory_fingerprint": (
            state.family_inventory_fingerprint
        ),
        "current_pointer_state_fingerprint": (
            state.current_pointer_state_fingerprint
        ),
        "current_pointer_sha256": state.pointer_sha256,
        "active": None if state.pointer is None else state.pointer["active"],
        "rollback": (
            None if state.pointer is None else state.pointer["rollback"]
        ),
    }


def _require_immediate_successor(
    *,
    source: head.CandidateSegmentedChainHeadEvidence,
    current: CandidateSegmentedChainHeadCurrentState,
) -> None:
    if current.pointer is None:
        return
    active = current.pointer["active"]
    manifest = source.manifest
    parent = source.parent
    embedded = manifest["head"]["manifest"]
    embedded_parent = embedded.get("parent")
    active_manifest = current.active_manifest
    if (
        parent.append_count != int(active["append_count"]) + 1
        or parent.session_count != int(active["session_count"]) + 1
        or parent.as_of_session <= str(active["as_of_session"])
        or manifest["base"] != active_manifest["base"]
        or embedded.get("contract_version")
        not in {append.APPEND_CONTRACT, append.COMPOSED_APPEND_CONTRACT}
        or not isinstance(embedded_parent, Mapping)
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head candidate is not the immediate current successor"
        )
    expected_lineage = append.candidate_segmented_lineage_append_fingerprint(
        prior_lineage_fingerprint=str(active["lineage_fingerprint"]),
        append_manifest=embedded,
        append_manifest_sha256=parent.manifest_sha256,
    )
    if (
        embedded_parent.get("manifest_sha256")
        != active["lineage_tip_manifest_sha256"]
        or embedded_parent.get("logical_content_fingerprint")
        != active["lineage_tip_logical_content_fingerprint"]
        or embedded_parent.get("final_chain_fingerprint")
        != active["final_chain_fingerprint"]
        or embedded_parent.get("session_count") != active["session_count"]
        or embedded["chain_node"].get("prior_chain_fingerprint")
        != active["final_chain_fingerprint"]
        or manifest["lineage_fingerprint"] != expected_lineage
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head candidate is not the immediate current successor"
        )


def _family_inventory_fingerprint(*, canonical_root: Path) -> str:
    family_root = canonical_root.joinpath(*FAMILY_RELATIVE_PATH.parts)
    if not os.path.lexists(family_root):
        entries: list[dict[str, Any]] = []
    else:
        _validate_directory(family_root)
        entries = []
        for path in sorted(family_root.rglob("*")):
            if path.is_symlink():
                raise CandidateSegmentedChainHeadPublicationError(
                    "chain-head family contains a symlink"
                )
            relative = path.relative_to(family_root).as_posix()
            metadata = path.stat()
            if path.is_dir():
                _validate_directory(path)
                entries.append(
                    {
                        "relative_path": relative,
                        "type": "directory",
                        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                    }
                )
            elif path.is_file():
                _validate_canonical_file(path)
                entries.append(
                    {
                        "relative_path": relative,
                        "type": "file",
                        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                        "bytes": metadata.st_size,
                        "sha256": v1._file_sha256(path),
                    }
                )
            else:
                raise CandidateSegmentedChainHeadPublicationError(
                    "chain-head family contains a special file"
                )
        _validate_family_layout(entries)
    return v1._fingerprint(
        {
            "contract_version": FAMILY_INVENTORY_CONTRACT,
            "entries": entries,
        }
    )


def _read_release_sequence(
    *,
    canonical_root: Path,
    family_root: Path,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    releases_root = family_root / RELEASES_DIRECTORY
    result: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for release in sorted(releases_root.iterdir()):
        path = release / head.CHAIN_HEAD_MANIFEST
        physical_sha256 = v1._file_sha256(path)
        manifest = _read_canonical_mapping(
            path,
            expected_sha256=physical_sha256,
        )
        logical_fingerprint = manifest.get("logical_content_fingerprint")
        logical = dict(manifest)
        logical.pop("logical_content_fingerprint", None)
        if (
            v1._fingerprint(logical) != logical_fingerprint
            or release.name != logical_fingerprint
        ):
            raise CandidateSegmentedChainHeadPublicationError(
                "stored chain-head release identity differs from its path"
            )
        try:
            parent = head._validate_chain_head_manifest(
                manifest=manifest,
                base_shadow_path=Path("/tmp/canonical-release-anchor"),
            )
        except Exception as exc:
            raise CandidateSegmentedChainHeadPublicationError(
                f"stored chain-head release is invalid: {type(exc).__name__}"
            ) from exc
        reference = _reference_from_manifest(
            manifest=manifest,
            manifest_sha256=physical_sha256,
            parent=parent,
            release_relative_path=release.relative_to(
                canonical_root
            ).as_posix(),
        )
        _validate_reference_shape(reference)
        result.append((reference, manifest))
    result.sort(key=lambda item: int(item[0]["append_count"]))
    if not result:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head current pointer has no immutable release"
        )
    for (prior_reference, prior_manifest), (
        next_reference,
        next_manifest,
    ) in zip(result, result[1:], strict=False):
        _require_reference_successor(
            successor_reference=next_reference,
            successor_manifest=next_manifest,
            predecessor_reference=prior_reference,
            predecessor_manifest=prior_manifest,
        )
    return result


def _validate_family_layout(entries: list[dict[str, Any]]) -> None:
    paths = {str(item["relative_path"]): item for item in entries}
    allowed_files = {CURRENT_POINTER_FILE}
    for path, item in paths.items():
        pure = PurePosixPath(path)
        if item["type"] == "directory":
            if path == RELEASES_DIRECTORY:
                continue
            if (
                len(pure.parts) == 2
                and pure.parts[0] == RELEASES_DIRECTORY
                and shadow._is_sha256(pure.parts[1])
            ):
                continue
            raise CandidateSegmentedChainHeadPublicationError(
                "chain-head family contains an unexpected directory"
            )
        if path in allowed_files:
            continue
        if (
            len(pure.parts) == 3
            and pure.parts[0] == RELEASES_DIRECTORY
            and shadow._is_sha256(pure.parts[1])
            and pure.parts[2] == head.CHAIN_HEAD_MANIFEST
            and str(paths.get(PurePosixPath(*pure.parts[:2]).as_posix(), {}).get("type"))
            == "directory"
        ):
            continue
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head family contains an unexpected file"
        )
    release_dirs = {
        path
        for path, item in paths.items()
        if item["type"] == "directory"
        and len(PurePosixPath(path).parts) == 2
    }
    for release_dir in release_dirs:
        expected = f"{release_dir}/{head.CHAIN_HEAD_MANIFEST}"
        if expected not in paths:
            raise CandidateSegmentedChainHeadPublicationError(
                "chain-head immutable release is incomplete"
            )
    has_pointer = CURRENT_POINTER_FILE in paths
    has_release = bool(release_dirs)
    if has_pointer != has_release:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head pointer and immutable releases are inconsistent"
        )


def _require_reference_successor(
    *,
    successor_reference: Mapping[str, Any],
    successor_manifest: Mapping[str, Any],
    predecessor_reference: Mapping[str, Any],
    predecessor_manifest: Mapping[str, Any] | None,
) -> None:
    embedded = successor_manifest["head"]["manifest"]
    embedded_parent = embedded.get("parent")
    if (
        predecessor_manifest is None
        or successor_manifest["base"] != predecessor_manifest["base"]
        or successor_reference["append_count"]
        != predecessor_reference["append_count"] + 1
        or successor_reference["session_count"]
        != predecessor_reference["session_count"] + 1
        or successor_reference["as_of_session"]
        <= predecessor_reference["as_of_session"]
        or embedded.get("contract_version")
        not in {append.APPEND_CONTRACT, append.COMPOSED_APPEND_CONTRACT}
        or not isinstance(embedded_parent, Mapping)
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head active and rollback lineage differs"
        )
    expected_lineage = append.candidate_segmented_lineage_append_fingerprint(
        prior_lineage_fingerprint=str(
            predecessor_reference["lineage_fingerprint"]
        ),
        append_manifest=embedded,
        append_manifest_sha256=str(
            successor_reference["lineage_tip_manifest_sha256"]
        ),
    )
    if (
        embedded_parent.get("manifest_sha256")
        != predecessor_reference["lineage_tip_manifest_sha256"]
        or embedded_parent.get("logical_content_fingerprint")
        != predecessor_reference[
            "lineage_tip_logical_content_fingerprint"
        ]
        or embedded_parent.get("final_chain_fingerprint")
        != predecessor_reference["final_chain_fingerprint"]
        or embedded_parent.get("session_count")
        != predecessor_reference["session_count"]
        or embedded["chain_node"].get("prior_chain_fingerprint")
        != predecessor_reference["final_chain_fingerprint"]
        or successor_manifest["lineage_fingerprint"] != expected_lineage
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head active and rollback lineage differs"
        )


def _reference_from_manifest(
    *,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    parent: append.CandidateSegmentedParentEvidence,
    release_relative_path: str,
) -> dict[str, Any]:
    manifest_relative_path = (
        PurePosixPath(release_relative_path) / head.CHAIN_HEAD_MANIFEST
    ).as_posix()
    return {
        "release_relative_path": release_relative_path,
        "manifest_relative_path": manifest_relative_path,
        "chain_head_contract_version": head.CHAIN_HEAD_CONTRACT,
        "chain_head_manifest_sha256": manifest_sha256,
        "chain_head_logical_content_fingerprint": manifest[
            "logical_content_fingerprint"
        ],
        "lineage_fingerprint": manifest["lineage_fingerprint"],
        "as_of_session": parent.as_of_session,
        "session_count": parent.session_count,
        "append_count": parent.append_count,
        "source_contract_fingerprint": parent.source_contract_fingerprint,
        "source_audit_logical_fingerprint": (
            parent.source_audit_logical_fingerprint
        ),
        "lineage_tip_manifest_sha256": parent.manifest_sha256,
        "lineage_tip_logical_content_fingerprint": parent.manifest[
            "logical_content_fingerprint"
        ],
        "final_chain_fingerprint": parent.final_chain_fingerprint,
        "universe_ids": list(parent.universe_ids),
    }


def _validate_pointer_shape(pointer: Mapping[str, Any]) -> None:
    required = {
        "contract_version",
        "status",
        "active",
        "rollback",
        "prior_pointer_state_fingerprint",
        "logical_content_fingerprint",
    }
    logical = dict(pointer)
    logical_fingerprint = logical.pop("logical_content_fingerprint", None)
    if (
        set(pointer) != required
        or pointer.get("contract_version") != CURRENT_POINTER_CONTRACT
        or pointer.get("status") != "active"
        or not isinstance(pointer.get("active"), Mapping)
        or (
            pointer.get("rollback") is not None
            and not isinstance(pointer.get("rollback"), Mapping)
        )
        or not shadow._is_sha256(
            pointer.get("prior_pointer_state_fingerprint")
        )
        or not shadow._is_sha256(logical_fingerprint)
        or v1._fingerprint(logical) != logical_fingerprint
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head current pointer is malformed"
        )
    _validate_reference_shape(pointer["active"])
    if pointer["rollback"] is not None:
        _validate_reference_shape(pointer["rollback"])
        if pointer["active"] == pointer["rollback"]:
            raise CandidateSegmentedChainHeadPublicationError(
                "chain-head active and rollback references are identical"
            )


def _validate_reference_shape(reference: Mapping[str, Any]) -> None:
    required = {
        "release_relative_path",
        "manifest_relative_path",
        "chain_head_contract_version",
        "chain_head_manifest_sha256",
        "chain_head_logical_content_fingerprint",
        "lineage_fingerprint",
        "as_of_session",
        "session_count",
        "append_count",
        "source_contract_fingerprint",
        "source_audit_logical_fingerprint",
        "lineage_tip_manifest_sha256",
        "lineage_tip_logical_content_fingerprint",
        "final_chain_fingerprint",
        "universe_ids",
    }
    release = PurePosixPath(str(reference.get("release_relative_path")))
    manifest = PurePosixPath(str(reference.get("manifest_relative_path")))
    fingerprints = (
        reference.get("chain_head_manifest_sha256"),
        reference.get("chain_head_logical_content_fingerprint"),
        reference.get("lineage_fingerprint"),
        reference.get("source_contract_fingerprint"),
        reference.get("source_audit_logical_fingerprint"),
        reference.get("lineage_tip_manifest_sha256"),
        reference.get("lineage_tip_logical_content_fingerprint"),
        reference.get("final_chain_fingerprint"),
    )
    if (
        set(reference) != required
        or release.parent
        != FAMILY_RELATIVE_PATH / RELEASES_DIRECTORY
        or not shadow._is_sha256(release.name)
        or release.name
        != reference.get("chain_head_logical_content_fingerprint")
        or manifest != release / head.CHAIN_HEAD_MANIFEST
        or reference.get("chain_head_contract_version")
        != head.CHAIN_HEAD_CONTRACT
        or any(not shadow._is_sha256(item) for item in fingerprints)
        or type(reference.get("session_count")) is not int
        or int(reference["session_count"]) < 1
        or type(reference.get("append_count")) is not int
        or int(reference["append_count"]) < 0
        or not isinstance(reference.get("as_of_session"), str)
        or not isinstance(reference.get("universe_ids"), list)
        or not reference["universe_ids"]
        or not all(isinstance(item, str) for item in reference["universe_ids"])
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head release reference is malformed"
        )


def _validate_plan_shape(plan: Mapping[str, Any]) -> None:
    required = {
        "contract_version",
        "status",
        "created_at",
        "canonical_root",
        "family_relative_path",
        "source",
        "target",
        "expected_current_state",
        "planned_pointer",
        "planned_pointer_sha256",
        "planned_pointer_bytes",
        "inventory_change",
        "apply_order",
        "recovery_policy",
        "rollback_policy",
        "retention_policy",
        "source_formal_read_complete",
        "target_absence_verified",
        "current_family_state_bound",
        "current_pointer_state_bound",
        "immediate_successor_verified",
        "external_request_count",
        "canonical_write_count",
        "production_write_count",
        "apply_authorized",
        "rollback_authorized",
        "executor_authorized",
        "scheduler_authorized",
        "production_consumer_authorized",
        "logical_content_fingerprint",
    }
    if (
        set(plan) != required
        or plan.get("contract_version") != PUBLICATION_PLAN_CONTRACT
        or plan.get("status") != PLAN_STATUS
        or plan.get("family_relative_path") != FAMILY_RELATIVE_PATH.as_posix()
        or plan.get("apply_order")
        != ["immutable_release_first", "current_pointer_last"]
        or any(
            plan.get(field) is not True
            for field in (
                "source_formal_read_complete",
                "target_absence_verified",
                "current_family_state_bound",
                "current_pointer_state_bound",
                "immediate_successor_verified",
            )
        )
        or any(
            plan.get(field) is not False
            for field in (
                "apply_authorized",
                "rollback_authorized",
                "executor_authorized",
                "scheduler_authorized",
                "production_consumer_authorized",
            )
        )
        or plan.get("external_request_count") != 0
        or plan.get("canonical_write_count") != 0
        or plan.get("production_write_count") != 0
        or not shadow._is_sha256(plan.get("planned_pointer_sha256"))
        or not shadow._is_sha256(plan.get("logical_content_fingerprint"))
        or not isinstance(plan.get("source"), Mapping)
        or not isinstance(plan.get("target"), Mapping)
        or not isinstance(plan.get("expected_current_state"), Mapping)
        or not isinstance(plan.get("planned_pointer"), Mapping)
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication plan contract is malformed"
        )
    _validate_pointer_shape(plan["planned_pointer"])
    _parse_created_at(plan["created_at"])


def _target_descriptor_for_source(
    source: head.CandidateSegmentedChainHeadEvidence,
    canonical_root: Path,
) -> dict[str, Any]:
    value = _target_descriptor(
        _release_reference(source=source, canonical_root=canonical_root)
    )
    value["manifest_bytes"] = source.path.joinpath(
        head.CHAIN_HEAD_MANIFEST
    ).stat().st_size
    return value


def _require_absent_release_target(
    *,
    canonical_root: Path,
    release_relative_path: str,
) -> None:
    target = _resolve_relative(canonical_root, release_relative_path)
    staging = target.with_name(f".{target.name}.staging")
    for path in (target, staging):
        _reject_symlink_chain(canonical_root, path)
        if os.path.lexists(path):
            raise CandidateSegmentedChainHeadPublicationError(
                "chain-head immutable release target is no longer absent"
            )


def _validated_canonical_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical root path differs"
        )
    if resolved != APPROVED_DATA_ROOT and not resolved.is_relative_to(
        Path("/tmp")
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical root is outside approved or simulated custody"
        )
    if resolved != APPROVED_DATA_ROOT:
        metadata = resolved.stat()
        if (
            metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise CandidateSegmentedChainHeadPublicationError(
                "simulated chain-head canonical root custody differs"
            )
    return resolved


def _validate_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head family directory is unsafe"
        )
    metadata = path.stat()
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head family directory custody differs"
        )


def _validate_canonical_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical file is unsafe"
        )
    metadata = path.stat()
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o400
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical file custody differs"
        )


def _validated_plan_file(path: Path) -> Path:
    _validate_plan_path(path)
    staging = path.with_name(f".{path.name}.staging")
    if os.path.lexists(staging):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication-plan staging residue requires diagnosis"
        )
    _validate_canonical_file(path)
    return path


def _validate_plan_path(path: Path) -> None:
    if (
        not path.is_absolute()
        or path.parent != Path("/tmp")
        or path.name.startswith(".")
        or path.is_symlink()
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication plan must be a visible direct child of /tmp"
        )


def _write_plan(*, plan: Mapping[str, Any], plan_path: Path) -> Path:
    _validate_plan_path(plan_path)
    if os.path.lexists(plan_path):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication plan must use a new path"
        )
    staging = plan_path.with_name(f".{plan_path.name}.staging")
    if os.path.lexists(staging):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head publication-plan staging residue requires diagnosis"
        )
    v1._write_canonical_new(staging, plan)
    os.link(staging, plan_path, follow_symlinks=False)
    os.unlink(staging)
    head._fsync_directory(plan_path.parent)
    return plan_path


def _read_canonical_mapping(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except Exception as exc:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical JSON is malformed"
        ) from exc
    if (
        not isinstance(value, dict)
        or v1._file_sha256(path) != expected_sha256
        or v1._canonical_bytes(value) != path.read_bytes()
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head canonical JSON bytes differ"
        )
    return value


def _resolve_relative(root: Path, value: str) -> Path:
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or pure.as_posix() != value
    ):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head relative path is unsafe"
        )
    path = root.joinpath(*pure.parts)
    _reject_symlink_chain(root, path)
    return path


def _reject_symlink_chain(root: Path, path: Path) -> None:
    if path != root and root not in path.parents:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head path escaped canonical root"
        )
    current = path
    while True:
        if current.is_symlink():
            raise CandidateSegmentedChainHeadPublicationError(
                "chain-head path contains a symlink"
            )
        if current == root:
            return
        current = current.parent


def _parse_created_at(value: Any) -> datetime:
    if not isinstance(value, str):
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head plan creation time is malformed"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return normalize_utc_datetime(parsed)
    except Exception as exc:
        raise CandidateSegmentedChainHeadPublicationError(
            "chain-head plan creation time is malformed"
        ) from exc


def _format_utc(value: datetime) -> str:
    return normalize_utc_datetime(value).isoformat().replace("+00:00", "Z")
