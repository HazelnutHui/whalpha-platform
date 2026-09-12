"""Adapt one reconciled EOD edition and exact Identity into coverage evidence."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageFileReferenceV1,
    HistoricalDatasetCoverageEvidenceV1,
    HistoricalDatasetFamily,
    build_historical_dataset_coverage_evidence,
)
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotReadResult
from tip_api.persistence.parquet.historical_coverage import (
    HistoricalDatasetEvidenceValidationResult,
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.persistence.parquet.reconciled_eod_edition import (
    INTERVAL_MANIFEST_FILE_NAME,
    ValidatedReconciledEodEdition,
    validate_reconciled_eod_edition,
)


CONTRACT_VERSION = "reconciled-eod-historical-mechanics-evidence/1.0"
DEFAULT_VALIDATION_WORKERS = min(8, os.cpu_count() or 1)


class ReconciledEodHistoricalMechanicsEvidenceError(RuntimeError):
    """Raised when an edition cannot be represented by exact family evidence."""


@dataclass(frozen=True, slots=True)
class ReconciledEodHistoricalFamilyEvidenceObservation:
    family: str
    session_count: int
    artifact_count: int
    record_count: int
    first_session: str
    last_session: str
    logical_fingerprint: str
    proposed_evidence_path: str
    evidence_physical_sha256: str
    validation_status: str
    publication_exists: bool


@dataclass(frozen=True, slots=True)
class ReconciledEodHistoricalMechanicsEvidenceReport:
    contract_version: str
    status: str
    edition_id: str
    interval_manifest_fingerprint: str
    validation_worker_count: int
    observed_session_count: int
    first_session: str
    last_session: str
    families: tuple[ReconciledEodHistoricalFamilyEvidenceObservation, ...]
    blocker_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    evidence_publication_performed: bool
    historical_coverage_publication_performed: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_reconciled_eod_historical_mechanics_evidence(
    *,
    data_root: Path,
    edition_id: str,
    expected_interval_manifest_fingerprint: str,
    max_workers: int = DEFAULT_VALIDATION_WORKERS,
) -> ReconciledEodHistoricalMechanicsEvidenceReport:
    """Formally validate exact edition/Identity bytes without publishing them."""

    edition, validated = validate_reconciled_eod_historical_family_evidence(
        data_root=data_root,
        edition_id=edition_id,
        expected_interval_manifest_fingerprint=(
            expected_interval_manifest_fingerprint
        ),
        max_workers=max_workers,
    )
    sessions = validated[0].evidence.sessions
    if any(item.evidence.sessions != sessions for item in validated[1:]):
        raise ReconciledEodHistoricalMechanicsEvidenceError(
            "reconciled historical family session coverage differs"
        )
    observations = tuple(
        _observation(data_root, item)
        for item in sorted(validated, key=lambda value: value.evidence.family.value)
    )
    blocker_codes = (
        "daily_point_in_time_membership_absent",
        "canonical_corporate_action_coverage_absent",
        "instrument_lifecycle_coverage_absent",
        "adjustment_ledger_reconciliation_absent",
        "historical_coverage_publication_absent",
    )
    limitation_codes = (
        "edition_ends_before_unresolved_identity_source_gap",
        "family_evidence_validated_but_not_published",
        "no_research_or_performance_claim_authorized",
    )
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "status": "price_identity_mechanics_only",
        "edition_id": edition.manifest.edition_id,
        "interval_manifest_fingerprint": edition.manifest.logical_fingerprint,
        "validation_worker_count": min(max_workers, len(sessions)),
        "observed_session_count": len(sessions),
        "first_session": sessions[0].isoformat(),
        "last_session": sessions[-1].isoformat(),
        "families": [asdict(item) for item in observations],
        "blocker_codes": blocker_codes,
        "limitation_codes": limitation_codes,
        "evidence_publication_performed": False,
        "historical_coverage_publication_performed": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return ReconciledEodHistoricalMechanicsEvidenceReport(
        contract_version=CONTRACT_VERSION,
        status="price_identity_mechanics_only",
        edition_id=edition.manifest.edition_id,
        interval_manifest_fingerprint=edition.manifest.logical_fingerprint,
        validation_worker_count=min(max_workers, len(sessions)),
        observed_session_count=len(sessions),
        first_session=sessions[0].isoformat(),
        last_session=sessions[-1].isoformat(),
        families=observations,
        blocker_codes=blocker_codes,
        limitation_codes=limitation_codes,
        evidence_publication_performed=False,
        historical_coverage_publication_performed=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(payload),
    )


def validate_reconciled_eod_historical_family_evidence(
    *,
    data_root: Path,
    edition_id: str,
    expected_interval_manifest_fingerprint: str,
    max_workers: int = DEFAULT_VALIDATION_WORKERS,
) -> tuple[
    ValidatedReconciledEodEdition,
    tuple[HistoricalDatasetEvidenceValidationResult, ...],
]:
    """Return exact, transitively validated edition and Identity evidence."""

    _require_sha(expected_interval_manifest_fingerprint)
    _require_worker_count(max_workers)
    edition = validate_reconciled_eod_edition(
        root=data_root,
        edition_id=edition_id,
        max_workers=max_workers,
    )
    if (
        edition.manifest.logical_fingerprint
        != expected_interval_manifest_fingerprint
    ):
        raise ReconciledEodHistoricalMechanicsEvidenceError(
            "reconciled EOD interval fingerprint differs from the expected value"
        )
    worker_count = min(max_workers, len(edition.session_manifests))
    arguments = tuple(
        (data_root, session.identity_as_of_date)
        for session in edition.session_manifests
    )
    if worker_count == 1:
        inspected = tuple(_inspect_identity_snapshot(item) for item in arguments)
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            inspected = tuple(
                executor.map(_inspect_identity_snapshot, arguments, chunksize=1)
            )
    snapshots: dict[date, InstrumentMasterSnapshotReadResult] = {}
    for session, snapshot in zip(
        edition.session_manifests,
        inspected,
        strict=True,
    ):
        if (
            snapshot.as_of_date != session.session_date
            or snapshot.provider_id != session.provider
            or snapshot.snapshot_content_sha256
            != session.identity_snapshot_fingerprint
        ):
            raise ReconciledEodHistoricalMechanicsEvidenceError(
                "reconciled EOD Identity snapshot binding differs"
            )
        snapshots[session.session_date] = snapshot
    eod_evidence = _build_reconciled_eod_evidence(data_root, edition)
    identity_evidence = _build_identity_evidence(
        data_root,
        edition,
        snapshots,
    )
    repository = ParquetHistoricalCoverageRepository(data_root)
    return edition, (
        repository.validate_dataset_evidence(eod_evidence),
        repository.validate_dataset_evidence(identity_evidence),
    )


def _inspect_identity_snapshot(
    argument: tuple[Path, date],
) -> InstrumentMasterSnapshotReadResult:
    root, as_of_date = argument
    return ParquetInstrumentMasterSnapshotRepository(root).inspect_snapshot(
        as_of_date
    )


def _build_reconciled_eod_evidence(
    root: Path,
    edition: ValidatedReconciledEodEdition,
) -> HistoricalDatasetCoverageEvidenceV1:
    interval = edition.manifest
    completion = edition.edition_path / INTERVAL_MANIFEST_FILE_NAME
    payload_files: list[HistoricalCoverageFileReferenceV1] = []
    for session in edition.session_manifests:
        partition = (
            edition.edition_path
            / f"session_date={session.session_date.isoformat()}"
        )
        payload_files.extend(
            (
                _file_reference(root, partition / "manifest.json"),
                _file_reference(
                    root,
                    partition / "part-00000.parquet",
                    physical_sha256=session.parquet_sha256,
                ),
            )
        )
    ordered_payload_files = tuple(
        sorted(payload_files, key=lambda item: item.path)
    )
    artifact = HistoricalCoverageArtifactEvidenceV1(
        completion_manifest=_file_reference(root, completion),
        payload_files=ordered_payload_files,
        first_session=interval.sessions[0].session_date,
        last_session=interval.sessions[-1].session_date,
        record_count=sum(item.record_count for item in interval.sessions),
        logical_fingerprint=interval.logical_fingerprint,
    )
    return build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.EOD_PRICE_BAR,
        sessions=tuple(item.session_date for item in interval.sessions),
        artifacts=(artifact,),
        record_count=artifact.record_count,
        quarantined_record_count=0,
        created_at=interval.created_at,
    )


def _build_identity_evidence(
    root: Path,
    edition: ValidatedReconciledEodEdition,
    snapshots: dict[date, InstrumentMasterSnapshotReadResult],
) -> HistoricalDatasetCoverageEvidenceV1:
    artifacts: list[HistoricalCoverageArtifactEvidenceV1] = []
    for session in edition.session_manifests:
        snapshot = snapshots[session.session_date]
        payload_paths = tuple(
            sorted(
                path
                for partition in (
                    snapshot.instrument_partition_path,
                    snapshot.identity_partition_path,
                    snapshot.resolver_partition_path,
                )
                for path in (
                    partition / MANIFEST_FILE_NAME,
                    partition / PARQUET_FILE_NAME,
                )
            )
        )
        artifacts.append(
            HistoricalCoverageArtifactEvidenceV1(
                completion_manifest=_file_reference(
                    root,
                    snapshot.snapshot_manifest_path,
                ),
                payload_files=tuple(
                    _file_reference(root, path) for path in payload_paths
                ),
                first_session=session.session_date,
                last_session=session.session_date,
                record_count=snapshot.instrument_count,
                logical_fingerprint=snapshot.snapshot_content_sha256,
            )
        )
    artifacts.sort(key=lambda item: item.completion_manifest.path)
    return build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY,
        sessions=tuple(item.session_date for item in edition.session_manifests),
        artifacts=tuple(artifacts),
        record_count=sum(item.record_count for item in artifacts),
        quarantined_record_count=0,
        created_at=max(item.created_at for item in snapshots.values()),
    )


def _observation(
    root: Path,
    validation: HistoricalDatasetEvidenceValidationResult,
) -> ReconciledEodHistoricalFamilyEvidenceObservation:
    evidence = validation.evidence
    return ReconciledEodHistoricalFamilyEvidenceObservation(
        family=evidence.family.value,
        session_count=len(evidence.sessions),
        artifact_count=len(evidence.artifacts),
        record_count=evidence.record_count,
        first_session=evidence.sessions[0].isoformat(),
        last_session=evidence.sessions[-1].isoformat(),
        logical_fingerprint=evidence.logical_fingerprint,
        proposed_evidence_path=_relative_path(root, validation.proposed_evidence_path),
        evidence_physical_sha256=validation.physical_sha256,
        validation_status=validation.status,
        publication_exists=validation.publication_exists,
    )


def _file_reference(
    root: Path,
    path: Path,
    *,
    physical_sha256: str | None = None,
) -> HistoricalCoverageFileReferenceV1:
    return HistoricalCoverageFileReferenceV1(
        path=_relative_path(root, path),
        physical_sha256=physical_sha256 or _file_sha256(path),
    )


def _relative_path(root: Path, path: Path) -> str:
    absolute_root = root.absolute()
    absolute_path = path.absolute()
    if absolute_root not in absolute_path.parents:
        raise ReconciledEodHistoricalMechanicsEvidenceError(
            "evidence path escaped the canonical data root"
        )
    current = absolute_path
    while current != absolute_root:
        if current.is_symlink():
            raise ReconciledEodHistoricalMechanicsEvidenceError(
                "evidence path contains a symlink"
            )
        current = current.parent
    return absolute_path.relative_to(absolute_root).as_posix()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ReconciledEodHistoricalMechanicsEvidenceError(
            "expected interval fingerprint is invalid"
        )


def _require_worker_count(value: int) -> None:
    if isinstance(value, bool) or not 1 <= value <= 32:
        raise ReconciledEodHistoricalMechanicsEvidenceError(
            "validation worker count is invalid"
        )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
