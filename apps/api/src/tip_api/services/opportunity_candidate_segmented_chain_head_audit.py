"""Zero-write periodic audit of a segmented Candidate chain head."""

from __future__ import annotations

import hashlib
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal, Mapping, Sequence

from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services import opportunity_candidate_segmented_append as append
from tip_api.services import opportunity_candidate_segmented_chain_head as head
from tip_api.services import (
    opportunity_candidate_segmented_chain_head_publication as publication,
)
from tip_api.services import opportunity_candidate_segmented_shadow as shadow


FULL_LINEAGE_AUDIT_CONTRACT = (
    "opportunity-candidate-segmented-chain-head-full-lineage-audit/1.0"
)
AUDIT_STATUS = "exact_match"
VALIDATION_TIER = "periodic"
VALIDATION_SCOPE = "cold_base_plus_all_appends_to_current_active_head"


class CandidateSegmentedChainHeadAuditError(RuntimeError):
    """Raised when a periodic full-lineage audit cannot prove exact identity."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainHeadFullLineageAudit:
    contract_version: str
    status: Literal["exact_match"]
    validation_tier: Literal["periodic"]
    validation_scope: str
    current_family_inventory_fingerprint: str
    current_pointer_state_fingerprint: str
    active_chain_head_logical_fingerprint: str
    active_chain_head_manifest_sha256: str
    cold_chain_head_logical_fingerprint: str
    cold_chain_head_manifest_sha256: str
    lineage_fingerprint: str
    base_manifest_sha256: str
    base_manifest_logical_fingerprint: str
    source_contract_fingerprint: str
    source_audit_logical_fingerprint: str
    as_of_session: str
    base_session_count: int
    session_count: int
    append_count: int
    universe_ids: tuple[str, ...]
    current_state_reread_count: int
    full_lineage_reread_count: int
    manifest_byte_match: bool
    parent_identity_match: bool
    mismatch_count: int
    logical_content_fingerprint: str
    external_request_count: int = 0
    filesystem_write_count: int = 0
    canonical_write_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False
    cutover_authorized: bool = False
    code_change_validation_complete: bool = False


def audit_candidate_segmented_chain_head_full_lineage(
    *,
    canonical_root: Path,
    base_shadow: Path,
    parent_appends: Sequence[Path],
    expected_current_family_inventory_fingerprint: str,
    expected_current_pointer_state_fingerprint: str,
    expected_active_chain_head_logical_fingerprint: str,
    expected_active_chain_head_manifest_sha256: str,
) -> CandidateSegmentedChainHeadFullLineageAudit:
    """Cold-read the complete lineage and compare it with one trusted head."""

    if canonical_root == publication.APPROVED_DATA_ROOT:
        raise CandidateSegmentedChainHeadAuditError(
            "full-lineage audit refuses the production data root"
        )
    for value, label in (
        (
            expected_current_family_inventory_fingerprint,
            "expected family inventory fingerprint",
        ),
        (
            expected_current_pointer_state_fingerprint,
            "expected pointer state fingerprint",
        ),
        (
            expected_active_chain_head_logical_fingerprint,
            "expected active chain-head logical fingerprint",
        ),
        (
            expected_active_chain_head_manifest_sha256,
            "expected active chain-head manifest SHA-256",
        ),
    ):
        if not shadow._is_sha256(value):
            raise CandidateSegmentedChainHeadAuditError(f"{label} is malformed")
    try:
        root = publication._validated_canonical_root(canonical_root)
    except Exception as exc:
        raise CandidateSegmentedChainHeadAuditError(
            f"full-lineage audit root is invalid: {type(exc).__name__}"
        ) from exc
    if root == publication.APPROVED_DATA_ROOT:
        raise CandidateSegmentedChainHeadAuditError(
            "full-lineage audit refuses the production data root"
        )

    with _network_prohibited():
        before = _read_expected_current_state(
            canonical_root=root,
            expected_family_inventory_fingerprint=(
                expected_current_family_inventory_fingerprint
            ),
            expected_pointer_state_fingerprint=(
                expected_current_pointer_state_fingerprint
            ),
            expected_active_logical_fingerprint=(
                expected_active_chain_head_logical_fingerprint
            ),
            expected_active_manifest_sha256=(
                expected_active_chain_head_manifest_sha256
            ),
        )
        try:
            cold_parent = append.read_candidate_segmented_parent(
                base_shadow=base_shadow,
                parent_appends=parent_appends,
            )
        except Exception as exc:
            raise CandidateSegmentedChainHeadAuditError(
                f"full Candidate lineage validation failed: {type(exc).__name__}"
            ) from exc
        active_manifest = before.active_manifest
        if active_manifest is None:
            raise CandidateSegmentedChainHeadAuditError(
                "active chain-head manifest is unavailable"
            )
        try:
            active_parent = head._validate_chain_head_manifest(
                manifest=active_manifest,
                base_shadow_path=cold_parent.base_shadow_path,
            )
        except Exception as exc:
            raise CandidateSegmentedChainHeadAuditError(
                f"active chain-head validation failed: {type(exc).__name__}"
            ) from exc
        cold_manifest = _cold_manifest(cold_parent)
        cold_manifest_bytes = v1._canonical_bytes(cold_manifest)
        cold_manifest_sha256 = hashlib.sha256(cold_manifest_bytes).hexdigest()
        if active_parent != cold_parent or active_manifest != cold_manifest:
            raise CandidateSegmentedChainHeadAuditError(
                "cold reconstructed chain head differs from the active head"
            )
        if (
            cold_manifest_sha256
            != expected_active_chain_head_manifest_sha256
        ):
            raise CandidateSegmentedChainHeadAuditError(
                "cold reconstructed chain-head physical identity differs"
            )
        after = _read_expected_current_state(
            canonical_root=root,
            expected_family_inventory_fingerprint=(
                expected_current_family_inventory_fingerprint
            ),
            expected_pointer_state_fingerprint=(
                expected_current_pointer_state_fingerprint
            ),
            expected_active_logical_fingerprint=(
                expected_active_chain_head_logical_fingerprint
            ),
            expected_active_manifest_sha256=(
                expected_active_chain_head_manifest_sha256
            ),
        )
        if after != before:
            raise CandidateSegmentedChainHeadAuditError(
                "chain-head current state changed during full-lineage audit"
            )

    logical: dict[str, object] = {
        "contract_version": FULL_LINEAGE_AUDIT_CONTRACT,
        "status": AUDIT_STATUS,
        "validation_tier": VALIDATION_TIER,
        "validation_scope": VALIDATION_SCOPE,
        "current_family_inventory_fingerprint": (
            before.family_inventory_fingerprint
        ),
        "current_pointer_state_fingerprint": (
            before.current_pointer_state_fingerprint
        ),
        "active_chain_head_logical_fingerprint": (
            expected_active_chain_head_logical_fingerprint
        ),
        "active_chain_head_manifest_sha256": (
            expected_active_chain_head_manifest_sha256
        ),
        "cold_chain_head_logical_fingerprint": cold_manifest[
            "logical_content_fingerprint"
        ],
        "cold_chain_head_manifest_sha256": cold_manifest_sha256,
        "lineage_fingerprint": cold_parent.lineage_fingerprint,
        "base_manifest_sha256": cold_parent.base_manifest_sha256,
        "base_manifest_logical_fingerprint": (
            cold_parent.base_manifest_logical_fingerprint
        ),
        "source_contract_fingerprint": (
            cold_parent.source_contract_fingerprint
        ),
        "source_audit_logical_fingerprint": (
            cold_parent.source_audit_logical_fingerprint
        ),
        "as_of_session": cold_parent.as_of_session,
        "base_session_count": cold_parent.base_session_count,
        "session_count": cold_parent.session_count,
        "append_count": cold_parent.append_count,
        "universe_ids": list(cold_parent.universe_ids),
        "current_state_reread_count": 2,
        "full_lineage_reread_count": 1,
        "manifest_byte_match": True,
        "parent_identity_match": True,
        "mismatch_count": 0,
        "external_request_count": 0,
        "filesystem_write_count": 0,
        "canonical_write_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
        "cutover_authorized": False,
        "code_change_validation_complete": False,
    }
    return CandidateSegmentedChainHeadFullLineageAudit(
        contract_version=FULL_LINEAGE_AUDIT_CONTRACT,
        status="exact_match",
        validation_tier="periodic",
        validation_scope=VALIDATION_SCOPE,
        current_family_inventory_fingerprint=(
            before.family_inventory_fingerprint
        ),
        current_pointer_state_fingerprint=(
            before.current_pointer_state_fingerprint
        ),
        active_chain_head_logical_fingerprint=(
            expected_active_chain_head_logical_fingerprint
        ),
        active_chain_head_manifest_sha256=(
            expected_active_chain_head_manifest_sha256
        ),
        cold_chain_head_logical_fingerprint=str(
            cold_manifest["logical_content_fingerprint"]
        ),
        cold_chain_head_manifest_sha256=cold_manifest_sha256,
        lineage_fingerprint=cold_parent.lineage_fingerprint,
        base_manifest_sha256=cold_parent.base_manifest_sha256,
        base_manifest_logical_fingerprint=(
            cold_parent.base_manifest_logical_fingerprint
        ),
        source_contract_fingerprint=cold_parent.source_contract_fingerprint,
        source_audit_logical_fingerprint=(
            cold_parent.source_audit_logical_fingerprint
        ),
        as_of_session=cold_parent.as_of_session,
        base_session_count=cold_parent.base_session_count,
        session_count=cold_parent.session_count,
        append_count=cold_parent.append_count,
        universe_ids=cold_parent.universe_ids,
        current_state_reread_count=2,
        full_lineage_reread_count=1,
        manifest_byte_match=True,
        parent_identity_match=True,
        mismatch_count=0,
        logical_content_fingerprint=v1._fingerprint(logical),
    )


def _read_expected_current_state(
    *,
    canonical_root: Path,
    expected_family_inventory_fingerprint: str,
    expected_pointer_state_fingerprint: str,
    expected_active_logical_fingerprint: str,
    expected_active_manifest_sha256: str,
) -> publication.CandidateSegmentedChainHeadCurrentState:
    try:
        current = publication.read_candidate_segmented_chain_head_current_state(
            canonical_root=canonical_root,
        )
    except Exception as exc:
        raise CandidateSegmentedChainHeadAuditError(
            f"chain-head current state is invalid: {type(exc).__name__}"
        ) from exc
    pointer = current.pointer
    if pointer is None or current.active_manifest is None:
        raise CandidateSegmentedChainHeadAuditError(
            "chain-head current state has no active release"
        )
    active = pointer["active"]
    if (
        current.family_inventory_fingerprint
        != expected_family_inventory_fingerprint
        or current.current_pointer_state_fingerprint
        != expected_pointer_state_fingerprint
        or active["chain_head_logical_content_fingerprint"]
        != expected_active_logical_fingerprint
        or active["chain_head_manifest_sha256"]
        != expected_active_manifest_sha256
    ):
        raise CandidateSegmentedChainHeadAuditError(
            "chain-head current state differs from expected audit bindings"
        )
    return current


def _cold_manifest(
    parent: append.CandidateSegmentedParentEvidence,
) -> Mapping[str, object]:
    logical = head._chain_head_manifest_logical(parent)
    return {
        **logical,
        "logical_content_fingerprint": v1._fingerprint(logical),
    }


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CandidateSegmentedChainHeadAuditError(
            "network access is disabled during full-lineage audit"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
