"""Build an inventory-bound plan for canonical split-action publication."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator
from uuid import UUID, uuid5

from tip_api.contracts.common import QualityStatus, normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    CanonicalSplitActionApplyPlanV1,
    CanonicalSplitActionPlanArtifactV1,
    CanonicalSplitActionQuarantineImpactV1,
    CanonicalSplitActionV1,
    CorporateActionRecordStatus,
    KnowledgeTimeStatus,
    build_canonical_split_action_apply_plan,
)
from tip_api.persistence.parquet.canonical_corporate_action import (
    ACTIONS_FILE,
    MANIFEST_FILE,
    CanonicalSplitActionPersistenceError,
    CanonicalSplitActionPublicationRead,
    read_canonical_split_action_publication_candidate,
    write_canonical_split_action_publication_candidate,
)
from tip_api.providers.massive.same_day_catchup import inventory_fingerprint
from tip_api.services.canonical_split_action_candidate import (
    CanonicalSourceSplitActionCandidateResult,
    CanonicalSplitActionCandidateError,
    read_canonical_source_split_action_candidate,
)
from tip_api.services.corporate_action_source_canonical import (
    CanonicalCorporateActionSource,
    CanonicalCorporateActionSourceError,
    read_canonical_corporate_action_source,
)


CONTRACT_VERSION = "canonical-split-action-apply-plan/1.0"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
ACTION_NAMESPACE = UUID("c82708f1-ddd1-5d8e-9a7c-7596a3f0f4b8")
MAXIMUM_PLAN_BYTES = 16 * 1024 * 1024


class CanonicalSplitActionPublicationPlanError(RuntimeError):
    """Raised when the split-action publication plan cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitActionPublicationPlanEvidence:
    plan_path: Path
    plan: CanonicalSplitActionApplyPlanV1
    plan_sha256: str
    candidate_publication: CanonicalSplitActionPublicationRead


InventoryReader = Callable[[Path], str]


def build_canonical_split_action_publication_plan(
    *,
    data_root: Path,
    split_candidate_root: Path,
    publication_candidate_root: Path,
    plan_path: Path,
    source_revision: str,
    created_at: datetime,
    inventory_reader: InventoryReader = inventory_fingerprint,
) -> CanonicalSplitActionPublicationPlanEvidence:
    """Build exact `/tmp` publication bytes and a no-authority Apply plan."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        created_at = normalize_utc_datetime(created_at)
        candidate_target = _validated_tmp_target(publication_candidate_root)
        plan_target = _validated_tmp_file_target(plan_path)
        try:
            candidate = read_canonical_source_split_action_candidate(
                output_root=split_candidate_root
            )
            source = read_canonical_corporate_action_source(
                data_root=root,
                publication_path=root / candidate.candidate.source_publication_path,
            )
        except (
            CanonicalSplitActionCandidateError,
            CanonicalCorporateActionSourceError,
        ) as exc:
            raise CanonicalSplitActionPublicationPlanError(
                "split-action plan input failed formal reread"
            ) from exc
        _validate_candidate_source(candidate, source, created_at)
        actions = _build_actions(candidate, source, created_at)
        impacts = _build_impacts(candidate)
        publication_values = {
            "manifest_version": "canonical-split-action-publication/1.0",
            "completion_status": "completed",
            "dataset_name": "canonical-corporate-action",
            "action_scope": "split_only",
            "source_revision": source_revision,
            "source_publication_path": candidate.candidate.source_publication_path,
            "source_publication_sha256": candidate.candidate.source_publication_sha256,
            "source_publication_logical_fingerprint": (
                candidate.candidate.source_publication_logical_fingerprint
            ),
            "candidate_file_sha256": candidate.file_sha256,
            "candidate_logical_fingerprint": candidate.candidate.logical_fingerprint,
            "start_date": candidate.candidate.start_date,
            "end_date": candidate.candidate.basis_session,
            "source_data_cutoff": candidate.candidate.source_data_cutoff,
            "action_file": ACTIONS_FILE,
            "action_record_count": len(actions),
            "active_action_record_count": sum(
                item.record_status is CorporateActionRecordStatus.ACTIVE
                for item in actions
            ),
            "quarantined_action_record_count": sum(
                item.record_status is CorporateActionRecordStatus.QUARANTINED
                for item in actions
            ),
            "event_group_count": candidate.candidate.resolved_event_group_count,
            "clear_event_group_count": candidate.candidate.clear_event_group_count,
            "quarantined_event_group_count": (
                candidate.candidate.quarantined_event_group_count
            ),
            "unresolved_source_action_count": (
                candidate.candidate.quarantined_split_source_record_count
            ),
            "possible_impact_instrument_count": len(impacts),
            "possible_unresolved_impacts": impacts,
            "source_coverage_status": "bounded_query_snapshot_only",
            "point_in_time_eligibility": "outcome_reconciliation_only",
            "canonical_split_action_scope_published": True,
            "full_corporate_action_coverage_authorized": False,
            "neutral_factor_inference_authorized": False,
            "adjustment_ledger_authorized": False,
            "historical_coverage_authorized": False,
            "research_performance_authorized": False,
            "created_at": created_at,
        }
        try:
            publication = write_canonical_split_action_publication_candidate(
                output_root=candidate_target,
                actions=actions,
                publication_values=publication_values,
            )
        except CanonicalSplitActionPersistenceError as exc:
            raise CanonicalSplitActionPublicationPlanError(
                "split-action publication candidate failed"
            ) from exc
        target_root = (
            root
            / "market-data"
            / "canonical-corporate-actions"
            / "schema_version=1"
            / "action_scope=split"
            / f"coverage_id={publication.publication.logical_fingerprint}"
        )
        if os.path.lexists(target_root):
            raise CanonicalSplitActionPublicationPlanError(
                "canonical split-action target already exists"
            )
        artifacts = tuple(
            CanonicalSplitActionPlanArtifactV1(
                file_name=file_name,
                source_path=str(candidate_target / file_name),
                target_path=str(target_root / file_name),
                size=(candidate_target / file_name).stat().st_size,
                sha256=_file_sha256(candidate_target / file_name),
            )
            for file_name in (ACTIONS_FILE, MANIFEST_FILE)
        )
        values = {
            "contract_version": CONTRACT_VERSION,
            "operation": "publish_canonical_split_actions",
            "status": "ready_for_separate_review",
            "source_revision": source_revision,
            "created_at": created_at,
            "data_root": str(root),
            "split_candidate_root": str(split_candidate_root.absolute()),
            "candidate_root": str(candidate_target),
            "target_publication_root": str(target_root),
            "expected_current_state_fingerprint": inventory_reader(root),
            "artifacts": artifacts,
            "publication": publication.publication,
            "inventory_change_file_count": 2,
            "inventory_change_bytes": sum(item.size for item in artifacts),
            "target_absent_count": 1,
            "external_request_count": 0,
            "overwritten_file_count": 0,
            "deleted_file_count": 0,
            "apply_authorized": False,
            "adjustment_ledger_authorized": False,
            "historical_coverage_authorized": False,
            "research_performance_authorized": False,
        }
        plan = build_canonical_split_action_apply_plan(**values)
        _write_plan(plan_target, plan)
        return read_canonical_split_action_publication_plan(
            plan_path=plan_target,
            approved_plan_sha256=_file_sha256(plan_target),
        )


def read_canonical_split_action_publication_plan(
    *,
    plan_path: Path,
    approved_plan_sha256: str,
) -> CanonicalSplitActionPublicationPlanEvidence:
    path = _validated_existing_tmp_file(plan_path)
    raw = path.read_bytes()
    if (
        len(raw) < 1
        or len(raw) > MAXIMUM_PLAN_BYTES
        or hashlib.sha256(raw).hexdigest() != approved_plan_sha256
    ):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan bytes differ"
        )
    try:
        plan = CanonicalSplitActionApplyPlanV1.model_validate_json(raw)
    except Exception as exc:
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan contract is invalid"
        ) from exc
    if raw != _pretty_json(plan.model_dump(mode="json")):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan is not canonical JSON"
        )
    try:
        publication = read_canonical_split_action_publication_candidate(
            output_root=Path(plan.candidate_root)
        )
    except CanonicalSplitActionPersistenceError as exc:
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan candidate failed formal reread"
        ) from exc
    if publication.publication != plan.publication:
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan publication differs"
        )
    try:
        candidate = read_canonical_source_split_action_candidate(
            output_root=Path(plan.split_candidate_root)
        )
        source = read_canonical_corporate_action_source(
            data_root=Path(plan.data_root),
            publication_path=(
                Path(plan.data_root) / candidate.candidate.source_publication_path
            ),
        )
    except (
        CanonicalSplitActionCandidateError,
        CanonicalCorporateActionSourceError,
    ) as exc:
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan source failed formal reread"
        ) from exc
    _validate_candidate_source(candidate, source, plan.created_at)
    expected_actions = _build_actions(candidate, source, plan.created_at)
    expected_impacts = _build_impacts(candidate)
    if (
        publication.actions != expected_actions
        or plan.publication.candidate_file_sha256 != candidate.file_sha256
        or plan.publication.candidate_logical_fingerprint
        != candidate.candidate.logical_fingerprint
        or plan.publication.possible_unresolved_impacts != expected_impacts
    ):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan derivation differs"
        )
    for artifact in plan.artifacts:
        source = Path(artifact.source_path)
        if (
            source.is_symlink()
            or not source.is_file()
            or stat.S_IMODE(source.stat().st_mode) != 0o400
            or source.stat().st_size != artifact.size
            or _file_sha256(source) != artifact.sha256
        ):
            raise CanonicalSplitActionPublicationPlanError(
                "canonical split-action plan artifact differs"
            )
    return CanonicalSplitActionPublicationPlanEvidence(
        plan_path=path,
        plan=plan,
        plan_sha256=approved_plan_sha256,
        candidate_publication=publication,
    )


def _validate_candidate_source(
    candidate: CanonicalSourceSplitActionCandidateResult,
    source: CanonicalCorporateActionSource,
    created_at: datetime,
) -> None:
    candidate_value = candidate.candidate
    publication = source.publication
    if (
        source.publication_sha256 != candidate_value.source_publication_sha256
        or publication.logical_fingerprint
        != candidate_value.source_publication_logical_fingerprint
        or publication.start_date != candidate_value.start_date
        or publication.end_date != candidate_value.basis_session
        or publication.created_at != candidate_value.source_data_cutoff
        or source.publication_path
        != Path(APPROVED_DATA_ROOT) / candidate_value.source_publication_path
        or created_at < candidate_value.calculated_at
    ):
        raise CanonicalSplitActionPublicationPlanError(
            "split candidate and canonical source binding differ"
        )


def _build_actions(
    candidate: CanonicalSourceSplitActionCandidateResult,
    source: CanonicalCorporateActionSource,
    created_at: datetime,
) -> tuple[CanonicalSplitActionV1, ...]:
    candidate_value = candidate.candidate
    source_pairs = tuple(
        ((item.source_action_id, item.source_revision), item)
        for item in source.records
    )
    source_by_key = dict(source_pairs)
    if len(source_by_key) != len(source_pairs):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical source has duplicate source-action identity"
        )
    rows: list[CanonicalSplitActionV1] = []
    used: set[tuple[str, int]] = set()
    for event in candidate_value.resolved_events:
        group_quarantined = event.ledger_admission_status == "quarantined"
        for action in event.source_actions:
            key = (action.source_action_id, action.source_revision)
            source_row = source_by_key.get(key)
            if (
                source_row is None
                or source_row.instrument_id != event.instrument_id
                or source_row.effective_date != event.effective_date
                or source_row.action_type is not action.action_type
                or source_row.split_ratio_from != action.split_ratio_from
                or source_row.split_ratio_to != action.split_ratio_to
                or source_row.knowledge_time_status
                is not KnowledgeTimeStatus.FIRST_OBSERVED_ONLY
                or source_row.source_available_at is not None
                or key in used
            ):
                raise CanonicalSplitActionPublicationPlanError(
                    "split candidate action differs from canonical source"
                )
            used.add(key)
            flags = set(source_row.quality_flags)
            flags.add("outcome_reconciliation_only")
            if group_quarantined:
                flags.update(
                    {
                        "multiple_same_date_split_actions",
                        "ledger_admission_quarantined",
                    }
                )
            rows.append(
                CanonicalSplitActionV1(
                    corporate_action_id=uuid5(
                        ACTION_NAMESPACE,
                        f"{source_row.provider}|{source_row.source_action_id}",
                    ),
                    instrument_id=event.instrument_id,
                    action_type=source_row.action_type,
                    effective_date=event.effective_date,
                    split_ratio_from=source_row.split_ratio_from,
                    split_ratio_to=source_row.split_ratio_to,
                    source=source_row.provider,
                    source_action_id=source_row.source_action_id,
                    source_revision=source_row.source_revision,
                    canonical_revision=1,
                    source_action_set_fingerprint=(
                        event.source_action_set_fingerprint
                    ),
                    source_publication_fingerprint=(
                        candidate_value.source_publication_logical_fingerprint
                    ),
                    event_group_size=len(event.source_actions),
                    record_status=(
                        CorporateActionRecordStatus.QUARANTINED
                        if group_quarantined
                        else CorporateActionRecordStatus.ACTIVE
                    ),
                    first_observed_at=source_row.first_observed_at,
                    ingested_at=created_at,
                    quality_status=(
                        QualityStatus.PENDING_REVIEW
                        if group_quarantined
                        else QualityStatus.VALID
                    ),
                    quality_flags=tuple(flags),
                )
            )
    expected_keys = {
        (item.source_action_id, item.source_revision)
        for item in source.records
        if item.action_type.value
        in {"stock_split", "reverse_split", "stock_dividend"}
        and item.record_status is CorporateActionRecordStatus.ACTIVE
        and item.instrument_resolution_status.value == "resolved"
        and item.instrument_id is not None
    }
    if (
        len(used) != candidate_value.resolved_active_split_source_record_count
        or used != expected_keys
    ):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action source coverage differs"
        )
    return tuple(rows)


def _build_impacts(
    candidate: CanonicalSourceSplitActionCandidateResult,
) -> tuple[CanonicalSplitActionQuarantineImpactV1, ...]:
    source_fingerprint = (
        candidate.candidate.source_publication_logical_fingerprint
    )
    return tuple(
        CanonicalSplitActionQuarantineImpactV1(
            instrument_id=item.instrument_id,
            provider_tickers=item.provider_tickers,
            effective_dates=item.effective_dates,
            source_action_ids=item.source_action_ids,
            source_action_set_fingerprint=item.source_action_set_fingerprint,
            source_publication_fingerprint=source_fingerprint,
            impact_status="quarantined",
            assignment_authorized=False,
            quality_flags=item.quality_flags,
        )
        for item in candidate.candidate.possible_unresolved_impacts
    )


def _write_plan(path: Path, plan: CanonicalSplitActionApplyPlanV1) -> None:
    payload = _pretty_json(plan.model_dump(mode="json"))
    if path.exists() or path.is_symlink():
        if (
            path.is_symlink()
            or not path.is_file()
            or stat.S_IMODE(path.stat().st_mode) != 0o400
            or path.read_bytes() != payload
        ):
            raise CanonicalSplitActionPublicationPlanError(
                "existing canonical split-action plan differs"
            )
        return
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}"
    descriptor = os.open(
        temporary,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise CanonicalSplitActionPublicationPlanError(
                    "canonical split-action plan write was incomplete"
                )
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(path)
    _fsync_directory(path.parent)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action data root is not approved"
        )
    return resolved


def _validated_tmp_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise CanonicalSplitActionPublicationPlanError(
            "split-action publication candidate must be below /tmp"
        )
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise CanonicalSplitActionPublicationPlanError(
            "split-action publication candidate parent is unsafe"
        )
    return target


def _validated_tmp_file_target(path: Path) -> Path:
    target = _validated_tmp_target(path)
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan target is unsafe"
        )
    return target


def _validated_existing_tmp_file(path: Path) -> Path:
    target = _validated_tmp_file_target(path)
    if (
        target.is_symlink()
        or not target.is_file()
        or stat.S_IMODE(target.stat().st_mode) != 0o400
    ):
        raise CanonicalSplitActionPublicationPlanError(
            "canonical split-action plan is unavailable"
        )
    return target


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CanonicalSplitActionPublicationPlanError(
            "network is prohibited while planning canonical split actions"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
