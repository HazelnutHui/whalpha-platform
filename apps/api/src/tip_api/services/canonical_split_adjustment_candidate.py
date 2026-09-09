"""Build a sparse split-adjustment candidate from canonical action and EOD evidence."""

from __future__ import annotations

import hashlib
import json
import socket
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import QualityStatus, normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CanonicalSplitActionQuarantineImpactV1,
    CanonicalSplitActionV1,
    CorporateActionRecordStatus,
    HistoricalDatasetCoverageEvidenceV1,
    HistoricalDatasetFamily,
)
from tip_api.persistence.parquet.canonical_corporate_action import (
    CanonicalSplitActionPersistenceError,
    CanonicalSplitActionPublicationRead,
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    CanonicalSplitAdjustmentPersistenceError,
    CanonicalSplitAdjustmentPublicationRead,
    read_canonical_split_adjustment_candidate as read_candidate_custody,
    write_canonical_split_adjustment_candidate,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.historical_research import (
    HistoricalResearchPersistenceError,
)
from tip_api.services.historical_split_adjustment_candidate import (
    calculate_composed_split_adjustment_multipliers,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
METHODOLOGY_VERSION = "canonical-split-ratio-to-basis-v1"
_BASE_FLAGS = frozenset(
    {
        "total_return_adjustment_unavailable",
        "sparse_affected_path_only",
        "absent_row_neutrality_unauthorized",
        "outcome_reconciliation_only",
        "bounded_query_snapshot_only",
    }
)


class CanonicalSplitAdjustmentCandidateError(RuntimeError):
    """Raised when a sparse split-adjustment candidate cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CanonicalSplitAdjustmentCandidateResult:
    output_root: Path
    publication: CanonicalSplitAdjustmentPublicationRead
    status: Literal["published", "already_present"]


def build_canonical_split_adjustment_candidate(
    *,
    data_root: Path,
    canonical_action_publication_root: Path,
    eod_evidence_path: Path,
    output_root: Path,
    source_revision: str,
    calculated_at: datetime,
) -> CanonicalSplitAdjustmentCandidateResult:
    """Project only EOD rows affected by clear or quarantine split evidence."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        target = _validated_tmp_target(output_root)
        calculated_at = normalize_utc_datetime(calculated_at)
        try:
            action_source = read_canonical_split_action_publication(
                data_root=root,
                publication_root=canonical_action_publication_root,
            )
            eod_source = ParquetHistoricalCoverageRepository(root).read_dataset_evidence(
                eod_evidence_path
            )
        except (
            CanonicalSplitActionPersistenceError,
            HistoricalResearchPersistenceError,
        ) as exc:
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment source failed formal reread"
            ) from exc
        evidence = eod_source.evidence
        _validate_source_scope(action_source, evidence, calculated_at)
        active, quarantined = _action_groups(action_source.actions)
        impacts = {
            item.instrument_id: item
            for item in action_source.publication.possible_unresolved_impacts
        }
        if len(impacts) != len(
            action_source.publication.possible_unresolved_impacts
        ):
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment possible-impact identity is duplicated"
            )
        selected = frozenset(active) | frozenset(quarantined) | frozenset(impacts)
        source_pairs = _read_selected_eod_pairs(root, evidence, selected)
        source_data_cutoff = max(
            action_source.publication.created_at,
            evidence.created_at,
        )
        if calculated_at < source_data_cutoff:
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment calculation precedes source cutoff"
            )
        records = _build_records(
            source_pairs=source_pairs,
            active=active,
            quarantined=quarantined,
            impacts=impacts,
            basis_session=evidence.sessions[-1],
            source_data_cutoff=source_data_cutoff,
            calculated_at=calculated_at,
        )
        if not records:
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment sparse projection is empty"
            )
        observed_ids = frozenset(item[0] for item in source_pairs)
        clear_ids = frozenset(
            item.instrument_id
            for item in records
            if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
        )
        quarantine_ids = frozenset(
            item.instrument_id
            for item in records
            if item.split_adjustment_status
            is AdjustmentAvailabilityStatus.QUARANTINED
        )
        action_manifest_path = action_source.root / "manifest.json"
        publication_values = {
            "source_revision": source_revision,
            "basis_session": evidence.sessions[-1],
            "first_source_session": evidence.sessions[0],
            "last_source_session": evidence.sessions[-1],
            "source_session_count": len(evidence.sessions),
            "source_eod_record_count": evidence.record_count,
            "canonical_action_publication_path": (
                action_manifest_path.relative_to(root).as_posix()
            ),
            "canonical_action_publication_sha256": action_source.manifest_sha256,
            "canonical_action_publication_fingerprint": (
                action_source.publication.logical_fingerprint
            ),
            "eod_evidence_path": eod_source.evidence_path.relative_to(root).as_posix(),
            "eod_evidence_sha256": eod_source.physical_sha256,
            "eod_evidence_fingerprint": evidence.logical_fingerprint,
            "source_data_cutoff": source_data_cutoff,
            "calculated_at": calculated_at,
            "selected_instrument_count": len(selected),
            "selected_eod_row_count": len(source_pairs),
            "selected_without_eod_count": len(selected - observed_ids),
            "record_count": len(records),
            "clear_record_count": sum(
                item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
                for item in records
            ),
            "quarantined_record_count": sum(
                item.split_adjustment_status
                is AdjustmentAvailabilityStatus.QUARANTINED
                for item in records
            ),
            "clear_instrument_count": len(clear_ids),
            "quarantined_instrument_count": len(quarantine_ids),
            "active_action_record_count": (
                action_source.publication.active_action_record_count
            ),
            "quarantined_action_record_count": (
                action_source.publication.quarantined_action_record_count
            ),
            "unresolved_source_action_count": (
                action_source.publication.unresolved_source_action_count
            ),
            "possible_impact_instrument_count": len(impacts),
        }
        existed = target.exists() or target.is_symlink()
        try:
            publication = write_canonical_split_adjustment_candidate(
                output_root=target,
                records=records,
                publication_values=publication_values,
            )
        except CanonicalSplitAdjustmentPersistenceError as exc:
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment candidate publication failed"
            ) from exc
        return CanonicalSplitAdjustmentCandidateResult(
            output_root=target,
            publication=publication,
            status="already_present" if existed else "published",
        )


def read_canonical_split_adjustment_candidate(
    *, output_root: Path
) -> CanonicalSplitAdjustmentCandidateResult:
    try:
        publication = read_candidate_custody(output_root=output_root)
    except CanonicalSplitAdjustmentPersistenceError as exc:
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment candidate failed formal reread"
        ) from exc
    return CanonicalSplitAdjustmentCandidateResult(
        output_root=publication.root,
        publication=publication,
        status="already_present",
    )


def _validate_source_scope(
    action_source: CanonicalSplitActionPublicationRead,
    evidence: HistoricalDatasetCoverageEvidenceV1,
    calculated_at: datetime,
) -> None:
    publication = action_source.publication
    if (
        evidence.family is not HistoricalDatasetFamily.EOD_PRICE_BAR
        or evidence.sessions[0] != publication.start_date
        or evidence.sessions[-1] != publication.end_date
        or publication.source_coverage_status != "bounded_query_snapshot_only"
        or publication.point_in_time_eligibility
        != "outcome_reconciliation_only"
        or publication.adjustment_ledger_authorized is not False
        or publication.full_corporate_action_coverage_authorized is not False
        or calculated_at < publication.created_at
    ):
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment source scope differs"
        )


def _action_groups(
    actions: tuple[CanonicalSplitActionV1, ...],
) -> tuple[
    dict[UUID, tuple[CanonicalSplitActionV1, ...]],
    dict[UUID, tuple[CanonicalSplitActionV1, ...]],
]:
    active: dict[UUID, list[CanonicalSplitActionV1]] = defaultdict(list)
    quarantined: dict[UUID, list[CanonicalSplitActionV1]] = defaultdict(list)
    for item in actions:
        target = (
            active
            if item.record_status is CorporateActionRecordStatus.ACTIVE
            else quarantined
        )
        target[item.instrument_id].append(item)
    return (
        {
            key: tuple(sorted(value, key=_action_sort_key))
            for key, value in active.items()
        },
        {
            key: tuple(sorted(value, key=_action_sort_key))
            for key, value in quarantined.items()
        },
    )


def _read_selected_eod_pairs(
    root: Path,
    evidence: HistoricalDatasetCoverageEvidenceV1,
    selected: frozenset[UUID],
) -> tuple[tuple[UUID, date], ...]:
    value_set = pa.array(
        [str(item) for item in sorted(selected, key=str)],
        type=pa.string(),
    )
    pairs: list[tuple[UUID, date]] = []
    for artifact in evidence.artifacts:
        references = tuple(
            item for item in artifact.payload_files if item.path.endswith(".parquet")
        )
        if len(references) != 1 or artifact.first_session != artifact.last_session:
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment EOD artifact scope differs"
            )
        path = root / references[0].path
        try:
            table = pq.ParquetFile(path).read(
                columns=["instrument_id", "session_date"]
            )
        except (pa.ArrowException, OSError) as exc:
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment EOD projection is unreadable"
            ) from exc
        if (
            table.schema.field("instrument_id").type != pa.string()
            or table.schema.field("session_date").type != pa.date32()
        ):
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment EOD projection schema differs"
            )
        filtered = table.filter(
            pc.is_in(table["instrument_id"], value_set=value_set)
        )
        session = artifact.first_session
        artifact_pairs = tuple(
            (UUID(item["instrument_id"]), item["session_date"])
            for item in filtered.to_pylist()
        )
        if any(item[1] != session for item in artifact_pairs) or len(
            {item[0] for item in artifact_pairs}
        ) != len(artifact_pairs):
            raise CanonicalSplitAdjustmentCandidateError(
                "split-adjustment selected EOD rows differ"
            )
        pairs.extend(artifact_pairs)
    ordered = tuple(sorted(pairs, key=lambda item: (str(item[0]), item[1])))
    if len(ordered) != len(set(ordered)):
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment selected EOD identity is duplicated"
        )
    return ordered


def _build_records(
    *,
    source_pairs: tuple[tuple[UUID, date], ...],
    active: dict[UUID, tuple[CanonicalSplitActionV1, ...]],
    quarantined: dict[UUID, tuple[CanonicalSplitActionV1, ...]],
    impacts: dict[UUID, CanonicalSplitActionQuarantineImpactV1],
    basis_session: date,
    source_data_cutoff: datetime,
    calculated_at: datetime,
) -> tuple[AdjustmentLedgerEntryV1, ...]:
    records = []
    for instrument_id, source_session in source_pairs:
        clear_actions = tuple(
            item
            for item in active.get(instrument_id, ())
            if source_session < item.effective_date <= basis_session
        )
        quarantine_actions = tuple(
            item
            for item in quarantined.get(instrument_id, ())
            if source_session < item.effective_date <= basis_session
        )
        impact = impacts.get(instrument_id)
        impact_applies = impact is not None and any(
            source_session < item <= basis_session
            for item in impact.effective_dates
        )
        if not clear_actions and not quarantine_actions and not impact_applies:
            continue
        flags = set(_BASE_FLAGS)
        evidence_rows: list[dict[str, object]] = [
            {
                "kind": "canonical_action",
                "corporate_action_id": str(item.corporate_action_id),
                "effective_date": item.effective_date.isoformat(),
                "source_action_set_fingerprint": (
                    item.source_action_set_fingerprint
                ),
                "record_status": item.record_status.value,
            }
            for item in (*clear_actions, *quarantine_actions)
        ]
        if impact_applies and impact is not None:
            flags.update(impact.quality_flags)
            flags.add("unresolved_split_impact_quarantined")
            evidence_rows.append(
                {
                    "kind": "unresolved_impact",
                    "instrument_id": str(impact.instrument_id),
                    "effective_dates": tuple(
                        item.isoformat() for item in impact.effective_dates
                    ),
                    "source_action_set_fingerprint": (
                        impact.source_action_set_fingerprint
                    ),
                }
            )
        if quarantine_actions:
            flags.update(
                {
                    "multiple_same_date_split_actions",
                    "canonical_action_quarantined",
                }
            )
        is_quarantined = bool(quarantine_actions or impact_applies)
        if is_quarantined:
            price_factor = None
            volume_factor = None
            split_status = AdjustmentAvailabilityStatus.QUARANTINED
        else:
            factors = calculate_composed_split_adjustment_multipliers(
                (item.split_ratio_from, item.split_ratio_to)
                for item in clear_actions
            )
            price_factor = factors.price_multiplier_to_post_event_basis
            volume_factor = factors.volume_multiplier_to_post_event_basis
            split_status = AdjustmentAvailabilityStatus.CLEAR
            flags.add("split_ratio_projection_clear")
        records.append(
            AdjustmentLedgerEntryV1(
                instrument_id=instrument_id,
                source_session=source_session,
                basis_session=basis_session,
                split_price_multiplier_to_basis=price_factor,
                split_volume_multiplier_to_basis=volume_factor,
                split_adjustment_status=split_status,
                total_return_multiplier_to_basis=None,
                total_return_adjustment_status=(
                    AdjustmentAvailabilityStatus.UNAVAILABLE
                ),
                source_action_set_fingerprint=_fingerprint(evidence_rows),
                calculation_methodology_version=METHODOLOGY_VERSION,
                source_data_cutoff=source_data_cutoff,
                calculated_at=calculated_at,
                revision=1,
                quality_status=QualityStatus.PENDING_REVIEW,
                quality_flags=tuple(flags),
            )
        )
    return tuple(records)


def _action_sort_key(item: CanonicalSplitActionV1) -> tuple[object, ...]:
    return (
        item.effective_date,
        item.source,
        item.source_action_id,
        item.source_revision,
    )


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment data root is not approved"
        )
    return resolved


def _validated_tmp_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment candidate must be below /tmp"
        )
    if (
        not target.parent.is_dir()
        or target.parent.is_symlink()
        or target.parent.resolve(strict=True) != target.parent
    ):
        raise CanonicalSplitAdjustmentCandidateError(
            "split-adjustment candidate parent is unsafe"
        )
    return target


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise CanonicalSplitAdjustmentCandidateError(
            "network is prohibited during split-adjustment construction"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
