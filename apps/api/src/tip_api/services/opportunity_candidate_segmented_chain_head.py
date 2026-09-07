"""Immutable non-authoritative checkpoints for a segmented Candidate lineage."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from tip_api.services import opportunity_candidate_audit as v1
from tip_api.services import opportunity_candidate_segmented_append as append
from tip_api.services import opportunity_candidate_segmented_shadow as shadow


CHAIN_HEAD_CONTRACT = "opportunity-candidate-segmented-chain-head/1.0"
CHAIN_HEAD_MANIFEST = "candidate-segmented-chain-head.json"


class CandidateSegmentedChainHeadError(RuntimeError):
    """Raised when a Candidate chain-head checkpoint loses exact identity."""


@dataclass(frozen=True, slots=True)
class CandidateSegmentedChainHeadEvidence:
    path: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str
    parent: append.CandidateSegmentedParentEvidence
    external_request_count: int = 0
    production_write_count: int = 0
    publication_authorized: bool = False


def write_candidate_segmented_chain_head(
    *,
    base_shadow: Path,
    parent_appends: Sequence[Path] = (),
    output_dir: Path,
) -> dict[str, Any]:
    """Cold-build one checkpoint after fully validating the supplied lineage."""

    try:
        parent = append.read_candidate_segmented_parent(
            base_shadow=base_shadow,
            parent_appends=parent_appends,
        )
    except Exception as exc:
        raise CandidateSegmentedChainHeadError(
            f"chain-head lineage validation failed: {type(exc).__name__}"
        ) from exc
    return _write_chain_head(parent=parent, output_dir=output_dir)


def advance_candidate_segmented_chain_head(
    *,
    base_shadow: Path,
    prior_chain_head: Path,
    expected_prior_logical_fingerprint: str,
    append_package: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Advance one expected checkpoint by fully validating only the new append."""

    prior = read_candidate_segmented_chain_head(
        base_shadow=base_shadow,
        output_dir=prior_chain_head,
        expected_logical_fingerprint=expected_prior_logical_fingerprint,
    )
    try:
        appended = append._read_candidate_segmented_append_at(
            parent=prior.parent,
            output_dir=append_package,
            allow_staging=False,
        )
        parent = append._parent_evidence_from_append(
            parent=prior.parent,
            evidence=appended,
        )
    except Exception as exc:
        raise CandidateSegmentedChainHeadError(
            f"chain-head successor validation failed: {type(exc).__name__}"
        ) from exc
    return _write_chain_head(parent=parent, output_dir=output_dir)


def read_candidate_segmented_chain_head(
    *,
    base_shadow: Path,
    output_dir: Path,
    expected_logical_fingerprint: str,
) -> CandidateSegmentedChainHeadEvidence:
    """Read a small checkpoint only when its exact identity is already expected."""

    if not shadow._is_sha256(expected_logical_fingerprint):
        raise CandidateSegmentedChainHeadError(
            "expected chain-head logical fingerprint is malformed"
        )
    base_path = _operational_base_path(base_shadow)
    return _read_chain_head_at(
        base_shadow_path=base_path,
        output_dir=output_dir,
        expected_logical_fingerprint=expected_logical_fingerprint,
        allow_staging=False,
    )


def _write_chain_head(
    *,
    parent: append.CandidateSegmentedParentEvidence,
    output_dir: Path,
) -> dict[str, Any]:
    target = _new_output_target(output_dir)
    logical = _chain_head_manifest_logical(parent)
    manifest = {
        **logical,
        "logical_content_fingerprint": v1._fingerprint(logical),
    }
    expected_fingerprint = str(manifest["logical_content_fingerprint"])
    if target.exists():
        evidence = read_candidate_segmented_chain_head(
            base_shadow=parent.base_shadow_path,
            output_dir=target,
            expected_logical_fingerprint=expected_fingerprint,
        )
        if evidence.manifest != manifest:
            raise CandidateSegmentedChainHeadError(
                "completed chain head differs from the requested lineage"
            )
        return dict(evidence.manifest)

    stage = target.with_name(f".{target.name}.staging")
    if stage.exists() or stage.is_symlink():
        evidence = _read_chain_head_at(
            base_shadow_path=parent.base_shadow_path,
            output_dir=stage,
            expected_logical_fingerprint=expected_fingerprint,
            allow_staging=True,
        )
        if evidence.manifest != manifest:
            raise CandidateSegmentedChainHeadError(
                "staged chain head differs from the requested lineage"
            )
        os.rename(stage, target)
        _fsync_directory(target.parent)
        return dict(
            read_candidate_segmented_chain_head(
                base_shadow=parent.base_shadow_path,
                output_dir=target,
                expected_logical_fingerprint=expected_fingerprint,
            ).manifest
        )

    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    byte_count, physical_sha256 = v1._write_canonical_new(
        stage / CHAIN_HEAD_MANIFEST,
        manifest,
    )
    _fsync_directory(stage)
    _validate_physical_completion(
        output_dir=stage,
        byte_count=byte_count,
        physical_sha256=physical_sha256,
    )
    os.rename(stage, target)
    _fsync_directory(target.parent)
    return dict(manifest)


def _chain_head_manifest_logical(
    parent: append.CandidateSegmentedParentEvidence,
) -> dict[str, Any]:
    return {
        "contract_version": CHAIN_HEAD_CONTRACT,
        "completion_status": "completed",
        "lineage_identity_contract_version": append.LINEAGE_IDENTITY_CONTRACT,
        "base": {
            "shadow_contract_version": parent.root_shadow_contract_version,
            "manifest_sha256": parent.base_manifest_sha256,
            "logical_content_fingerprint": (
                parent.base_manifest_logical_fingerprint
            ),
            "as_of_session": parent.base_as_of_session,
            "session_count": parent.base_session_count,
            "source_contract_fingerprint": parent.source_contract_fingerprint,
            "final_chain_fingerprint": parent.base_final_chain_fingerprint,
            "universe_ids": list(parent.universe_ids),
        },
        "head": {
            "manifest": dict(parent.manifest),
            "manifest_sha256": parent.manifest_sha256,
            "as_of_session": parent.as_of_session,
            "session_count": parent.session_count,
            "append_count": parent.append_count,
            "source_contract_fingerprint": parent.source_contract_fingerprint,
            "source_audit_logical_fingerprint": (
                parent.source_audit_logical_fingerprint
            ),
            "final_chain_fingerprint": parent.final_chain_fingerprint,
            "universe_ids": list(parent.universe_ids),
        },
        "lineage_fingerprint": parent.lineage_fingerprint,
        "validation_scope": "expected_identity_checkpoint",
        "external_request_count": 0,
        "production_write_count": 0,
        "publication_authorized": False,
    }


def _read_chain_head_at(
    *,
    base_shadow_path: Path,
    output_dir: Path,
    expected_logical_fingerprint: str,
    allow_staging: bool,
) -> CandidateSegmentedChainHeadEvidence:
    target = _completed_output_target(output_dir, allow_staging=allow_staging)
    manifest_path = target / CHAIN_HEAD_MANIFEST
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise CandidateSegmentedChainHeadError(
            "chain-head completion manifest is unavailable"
        )
    entries = tuple(target.iterdir())
    if (
        {item.name for item in entries if item.is_file()} != {CHAIN_HEAD_MANIFEST}
        or any(item.is_dir() for item in entries)
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head package file set differs"
        )
    shadow._validate_file_custody(manifest_path)
    manifest_sha256 = v1._file_sha256(manifest_path)
    manifest = shadow._read_canonical_mapping(
        manifest_path,
        physical_sha256=manifest_sha256,
    )
    logical_fingerprint = manifest.pop("logical_content_fingerprint", None)
    if (
        v1._fingerprint(manifest) != logical_fingerprint
        or logical_fingerprint != expected_logical_fingerprint
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head logical identity differs from the expected checkpoint"
        )
    manifest["logical_content_fingerprint"] = logical_fingerprint
    parent = _validate_chain_head_manifest(
        manifest=manifest,
        base_shadow_path=base_shadow_path,
    )
    return CandidateSegmentedChainHeadEvidence(
        path=target,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        parent=parent,
    )


def _validate_chain_head_manifest(
    *,
    manifest: Mapping[str, Any],
    base_shadow_path: Path,
) -> append.CandidateSegmentedParentEvidence:
    base = manifest.get("base")
    head = manifest.get("head")
    if (
        manifest.get("contract_version") != CHAIN_HEAD_CONTRACT
        or manifest.get("completion_status") != "completed"
        or manifest.get("lineage_identity_contract_version")
        != append.LINEAGE_IDENTITY_CONTRACT
        or manifest.get("validation_scope") != "expected_identity_checkpoint"
        or manifest.get("external_request_count") != 0
        or manifest.get("production_write_count") != 0
        or manifest.get("publication_authorized") is not False
        or not isinstance(base, Mapping)
        or not isinstance(head, Mapping)
    ):
        raise CandidateSegmentedChainHeadError("chain-head manifest is malformed")
    parent_manifest = head.get("manifest")
    if not isinstance(parent_manifest, Mapping):
        raise CandidateSegmentedChainHeadError(
            "chain-head embedded parent manifest is malformed"
        )
    parent_manifest = dict(parent_manifest)
    parent_logical_fingerprint = parent_manifest.get(
        "logical_content_fingerprint"
    )
    parent_logical = dict(parent_manifest)
    parent_logical.pop("logical_content_fingerprint", None)
    parent_manifest_sha256 = hashlib.sha256(
        v1._canonical_bytes(parent_manifest)
    ).hexdigest()
    fingerprints = (
        manifest.get("logical_content_fingerprint"),
        manifest.get("lineage_fingerprint"),
        base.get("manifest_sha256"),
        base.get("logical_content_fingerprint"),
        base.get("source_contract_fingerprint"),
        base.get("final_chain_fingerprint"),
        head.get("manifest_sha256"),
        head.get("source_contract_fingerprint"),
        head.get("source_audit_logical_fingerprint"),
        head.get("final_chain_fingerprint"),
        parent_logical_fingerprint,
    )
    if (
        any(not shadow._is_sha256(value) for value in fingerprints)
        or v1._fingerprint(parent_logical) != parent_logical_fingerprint
        or parent_manifest_sha256 != head.get("manifest_sha256")
        or base.get("shadow_contract_version") != shadow.SHADOW_CONTRACT
        or type(base.get("session_count")) is not int
        or base["session_count"] < 1
        or type(head.get("session_count")) is not int
        or type(head.get("append_count")) is not int
        or head["append_count"] < 0
        or head["session_count"]
        != base["session_count"] + head["append_count"]
        or head.get("source_contract_fingerprint")
        != base.get("source_contract_fingerprint")
        or head.get("universe_ids") != base.get("universe_ids")
        or not isinstance(head.get("universe_ids"), list)
        or not head["universe_ids"]
        or head.get("as_of_session") != parent_manifest.get("as_of_session")
        or head.get("universe_ids") != parent_manifest.get("universe_ids")
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head identity fields differ"
        )
    if head["append_count"] == 0:
        try:
            shadow._validate_manifest_shape(parent_manifest)
            chain = shadow._chain_identity_from_validated_manifest(
                parent_manifest
            )
        except Exception as exc:
            raise CandidateSegmentedChainHeadError(
                f"chain-head base manifest validation failed: {type(exc).__name__}"
            ) from exc
        base_lineage_fingerprint = append.candidate_segmented_lineage_base_fingerprint(
            root_shadow_contract_version=str(base["shadow_contract_version"]),
            base_manifest_sha256=str(base["manifest_sha256"]),
            base_manifest_logical_fingerprint=str(
                base["logical_content_fingerprint"]
            ),
            base_as_of_session=str(base["as_of_session"]),
            base_session_count=int(base["session_count"]),
            source_contract_fingerprint=str(
                base["source_contract_fingerprint"]
            ),
            base_final_chain_fingerprint=str(base["final_chain_fingerprint"]),
            universe_ids=tuple(base["universe_ids"]),
        )
        if (
            parent_manifest_sha256 != base.get("manifest_sha256")
            or parent_logical_fingerprint
            != base.get("logical_content_fingerprint")
            or head.get("as_of_session") != base.get("as_of_session")
            or head.get("session_count") != base.get("session_count")
            or head.get("final_chain_fingerprint")
            != base.get("final_chain_fingerprint")
            or chain.source_contract_fingerprint
            != base.get("source_contract_fingerprint")
            or chain.final_chain_fingerprint
            != base.get("final_chain_fingerprint")
            or manifest.get("lineage_fingerprint") != base_lineage_fingerprint
        ):
            raise CandidateSegmentedChainHeadError(
                "chain-head base identity differs"
            )
        source_audit_logical_fingerprint = str(
            parent_manifest["source_audit_logical_fingerprint"]
        )
    else:
        try:
            append._validate_append_manifest_shape(parent_manifest)
        except Exception as exc:
            raise CandidateSegmentedChainHeadError(
                f"chain-head append manifest validation failed: {type(exc).__name__}"
            ) from exc
        if (
            parent_manifest["parent"].get("shadow_contract_version")
            != base.get("shadow_contract_version")
            or head.get("session_count")
            != int(parent_manifest["session_ordinal"]) + 1
            or head.get("source_contract_fingerprint")
            != parent_manifest["parent"].get("source_contract_fingerprint")
            or head.get("source_audit_logical_fingerprint")
            != parent_manifest["source_audit"].get(
                "logical_content_fingerprint"
            )
            or head.get("final_chain_fingerprint")
            != parent_manifest["chain_node"].get("chain_fingerprint")
        ):
            raise CandidateSegmentedChainHeadError(
                "chain-head append identity differs"
            )
        source_audit_logical_fingerprint = str(
            head["source_audit_logical_fingerprint"]
        )
    return append.CandidateSegmentedParentEvidence(
        base_shadow_path=base_shadow_path,
        root_shadow_contract_version=str(base["shadow_contract_version"]),
        manifest=parent_manifest,
        manifest_sha256=str(head["manifest_sha256"]),
        as_of_session=str(head["as_of_session"]),
        session_count=int(head["session_count"]),
        source_contract_fingerprint=str(head["source_contract_fingerprint"]),
        final_chain_fingerprint=str(head["final_chain_fingerprint"]),
        source_audit_logical_fingerprint=source_audit_logical_fingerprint,
        universe_ids=tuple(head["universe_ids"]),
        append_count=int(head["append_count"]),
        base_manifest_sha256=str(base["manifest_sha256"]),
        base_manifest_logical_fingerprint=str(
            base["logical_content_fingerprint"]
        ),
        base_as_of_session=str(base["as_of_session"]),
        base_session_count=int(base["session_count"]),
        base_final_chain_fingerprint=str(base["final_chain_fingerprint"]),
        lineage_fingerprint=str(manifest["lineage_fingerprint"]),
    )


def _validate_physical_completion(
    *,
    output_dir: Path,
    byte_count: int,
    physical_sha256: str,
) -> None:
    target = _completed_output_target(output_dir, allow_staging=True)
    path = target / CHAIN_HEAD_MANIFEST
    entries = tuple(target.iterdir())
    if (
        {item.name for item in entries if item.is_file()} != {CHAIN_HEAD_MANIFEST}
        or any(item.is_dir() for item in entries)
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head physical file set differs"
        )
    shadow._validate_file_custody(path)
    if (
        path.stat().st_size != byte_count
        or v1._file_sha256(path) != physical_sha256
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head physical completion differs"
        )


def _operational_base_path(path: Path) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp") or path.is_symlink():
        raise CandidateSegmentedChainHeadError(
            "chain-head base must be a non-symlink direct child of /tmp"
        )
    return path


def _new_output_target(path: Path) -> Path:
    if (
        not path.is_absolute()
        or path.parent != Path("/tmp")
        or path.name.startswith(".")
        or path.is_symlink()
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head output must be a visible direct child of /tmp"
        )
    return path


def _completed_output_target(path: Path, *, allow_staging: bool) -> Path:
    if not path.is_absolute() or path.parent != Path("/tmp"):
        raise CandidateSegmentedChainHeadError(
            "chain-head package must be a direct child of /tmp"
        )
    if path.name.startswith(".") and not (
        allow_staging and path.name.endswith(".staging")
    ):
        raise CandidateSegmentedChainHeadError(
            "chain-head package name is unsafe"
        )
    if path.is_symlink() or not path.is_dir():
        raise CandidateSegmentedChainHeadError(
            "chain-head package directory is unsafe"
        )
    target = path.resolve(strict=True)
    metadata = target.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CandidateSegmentedChainHeadError(
            "chain-head package directory custody differs"
        )
    if any(item.is_symlink() for item in target.iterdir()):
        raise CandidateSegmentedChainHeadError(
            "chain-head package contains a symlink"
        )
    return target


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
