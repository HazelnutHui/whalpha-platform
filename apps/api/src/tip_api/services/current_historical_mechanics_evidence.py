"""Adapt current canonical EOD and Identity into unpublished coverage evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from tip_api.contracts.market_data.v1 import (
    HistoricalCoverageArtifactEvidenceV1,
    HistoricalCoverageFileReferenceV1,
    HistoricalDatasetCoverageEvidenceV1,
    HistoricalDatasetFamily,
    build_historical_dataset_coverage_evidence,
)
from tip_api.persistence.instrument_master import InstrumentMasterSnapshotReadResult
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.historical_coverage import (
    HistoricalDatasetEvidenceValidationResult,
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.instrument_master_snapshot import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    ParquetInstrumentMasterSnapshotRepository,
)
from tip_api.read_models.eod import EodSessionDescriptor


CONTRACT_VERSION = "current-historical-mechanics-evidence/1.0"
MINIMUM_RESEARCH_HISTORY_SESSIONS = 252
MAXIMUM_JSON_BYTES = 16 * 1024 * 1024


class CurrentHistoricalMechanicsEvidenceError(RuntimeError):
    """Raised when canonical mechanics evidence cannot be reconciled."""


@dataclass(frozen=True, slots=True)
class CurrentHistoricalFamilyEvidenceObservation:
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
class CurrentHistoricalMechanicsEvidenceReport:
    contract_version: str
    status: str
    observed_session_count: int
    required_session_count: int
    missing_history_session_count: int
    first_session: str
    last_session: str
    families: tuple[CurrentHistoricalFamilyEvidenceObservation, ...]
    blocker_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    evidence_publication_performed: bool
    historical_coverage_publication_performed: bool
    external_request_count: int
    production_write_count: int
    logical_content_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_current_historical_mechanics_evidence(
    data_root: Path,
) -> CurrentHistoricalMechanicsEvidenceReport:
    """Formally validate current bytes and propose, but never publish, evidence."""

    validated = validate_current_historical_family_evidence(data_root)
    sessions = validated[0].evidence.sessions
    if any(item.evidence.sessions != sessions for item in validated[1:]):
        raise CurrentHistoricalMechanicsEvidenceError(
            "current historical family session coverage differs"
        )
    observations = tuple(
        _observation(data_root, item)
        for item in sorted(validated, key=lambda value: value.evidence.family.value)
    )
    missing = max(0, MINIMUM_RESEARCH_HISTORY_SESSIONS - len(sessions))
    blocker_codes = tuple(
        code
        for condition, code in (
            (missing > 0, "canonical_252_session_history_absent"),
            (True, "daily_point_in_time_membership_absent"),
            (True, "canonical_corporate_action_coverage_absent"),
            (True, "instrument_lifecycle_coverage_absent"),
            (True, "adjustment_ledger_reconciliation_absent"),
            (True, "historical_coverage_publication_absent"),
        )
        if condition
    )
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "status": "mechanics_only",
        "observed_session_count": len(sessions),
        "required_session_count": MINIMUM_RESEARCH_HISTORY_SESSIONS,
        "missing_history_session_count": missing,
        "first_session": sessions[0].isoformat(),
        "last_session": sessions[-1].isoformat(),
        "families": [asdict(item) for item in observations],
        "blocker_codes": blocker_codes,
        "limitation_codes": (
            "canonical_rows_only_source_exclusions_not_counted",
            "family_evidence_validated_but_not_published",
            "no_research_or_performance_claim_authorized",
        ),
        "evidence_publication_performed": False,
        "historical_coverage_publication_performed": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    return CurrentHistoricalMechanicsEvidenceReport(
        contract_version=CONTRACT_VERSION,
        status="mechanics_only",
        observed_session_count=len(sessions),
        required_session_count=MINIMUM_RESEARCH_HISTORY_SESSIONS,
        missing_history_session_count=missing,
        first_session=sessions[0].isoformat(),
        last_session=sessions[-1].isoformat(),
        families=observations,
        blocker_codes=blocker_codes,
        limitation_codes=(
            "canonical_rows_only_source_exclusions_not_counted",
            "family_evidence_validated_but_not_published",
            "no_research_or_performance_claim_authorized",
        ),
        evidence_publication_performed=False,
        historical_coverage_publication_performed=False,
        external_request_count=0,
        production_write_count=0,
        logical_content_fingerprint=_fingerprint(payload),
    )


def validate_current_historical_family_evidence(
    data_root: Path,
) -> tuple[HistoricalDatasetEvidenceValidationResult, ...]:
    """Return exact, transitively validated EOD and Identity evidence candidates."""

    descriptors = CanonicalEodReadRepository(data_root).list_sessions()
    if not descriptors:
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical EOD contains no completed sessions"
        )
    sessions = tuple(item.session_date for item in descriptors)
    if sessions != tuple(sorted(set(sessions))):
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical EOD sessions are not unique and ordered"
        )
    identity_repository = ParquetInstrumentMasterSnapshotRepository(data_root)
    snapshots = {
        as_of_date: identity_repository.inspect_snapshot(as_of_date)
        for as_of_date in sorted({item.identity_as_of_date for item in descriptors})
    }
    eod_evidence = _build_eod_evidence(data_root, descriptors)
    identity_evidence = _build_identity_evidence(data_root, descriptors, snapshots)
    coverage_repository = ParquetHistoricalCoverageRepository(data_root)
    return (
        coverage_repository.validate_dataset_evidence(eod_evidence),
        coverage_repository.validate_dataset_evidence(identity_evidence),
    )


def _build_eod_evidence(
    root: Path,
    descriptors: tuple[EodSessionDescriptor, ...],
) -> HistoricalDatasetCoverageEvidenceV1:
    artifacts: list[HistoricalCoverageArtifactEvidenceV1] = []
    created_at: list[datetime] = []
    for descriptor in descriptors:
        partition = (
            root
            / "market-data"
            / "eod-price-bars"
            / "schema_version=1"
            / f"session_date={descriptor.session_date.isoformat()}"
        )
        manifest_path = partition / MANIFEST_FILE_NAME
        parquet_path = partition / PARQUET_FILE_NAME
        manifest = _read_json(manifest_path)
        logical = _required_sha(manifest, "content_sha256")
        manifest_created_at = _required_utc_datetime(manifest, "created_at")
        if (
            manifest.get("record_count") != descriptor.record_count
            or manifest_created_at != descriptor.available_at.astimezone(UTC)
        ):
            raise CurrentHistoricalMechanicsEvidenceError(
                "EOD descriptor differs from its completion manifest"
            )
        created_at.append(manifest_created_at)
        artifacts.append(
            HistoricalCoverageArtifactEvidenceV1(
                completion_manifest=_file_reference(root, manifest_path),
                payload_files=(_file_reference(root, parquet_path),),
                first_session=descriptor.session_date,
                last_session=descriptor.session_date,
                record_count=descriptor.record_count,
                logical_fingerprint=logical,
            )
        )
    return build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.EOD_PRICE_BAR,
        sessions=tuple(item.session_date for item in descriptors),
        artifacts=tuple(artifacts),
        record_count=sum(item.record_count for item in descriptors),
        quarantined_record_count=0,
        created_at=max(created_at),
    )


def _build_identity_evidence(
    root: Path,
    descriptors: tuple[EodSessionDescriptor, ...],
    snapshots: dict[date, InstrumentMasterSnapshotReadResult],
) -> HistoricalDatasetCoverageEvidenceV1:
    bound_sessions: dict[date, list[date]] = {}
    for descriptor in descriptors:
        bound_sessions.setdefault(descriptor.identity_as_of_date, []).append(
            descriptor.session_date
        )
    artifacts: list[HistoricalCoverageArtifactEvidenceV1] = []
    for as_of_date, sessions in sorted(bound_sessions.items()):
        snapshot = snapshots[as_of_date]
        payload_paths = tuple(
            sorted(
                (
                    partition / MANIFEST_FILE_NAME,
                    partition / PARQUET_FILE_NAME,
                )
                for partition in (
                    snapshot.instrument_partition_path,
                    snapshot.identity_partition_path,
                    snapshot.resolver_partition_path,
                )
            )
        )
        flattened = tuple(path for pair in payload_paths for path in pair)
        artifacts.append(
            HistoricalCoverageArtifactEvidenceV1(
                completion_manifest=_file_reference(
                    root, snapshot.snapshot_manifest_path
                ),
                payload_files=tuple(
                    sorted(
                        (_file_reference(root, path) for path in flattened),
                        key=lambda item: item.path,
                    )
                ),
                first_session=min(sessions),
                last_session=max(sessions),
                record_count=snapshot.instrument_count,
                logical_fingerprint=snapshot.snapshot_content_sha256,
            )
        )
    artifacts.sort(key=lambda item: item.completion_manifest.path)
    return build_historical_dataset_coverage_evidence(
        family=HistoricalDatasetFamily.POINT_IN_TIME_IDENTITY,
        sessions=tuple(item.session_date for item in descriptors),
        artifacts=tuple(artifacts),
        record_count=sum(item.record_count for item in artifacts),
        quarantined_record_count=0,
        created_at=max(item.created_at for item in snapshots.values()),
    )


def _observation(
    root: Path,
    validation: HistoricalDatasetEvidenceValidationResult,
) -> CurrentHistoricalFamilyEvidenceObservation:
    evidence = validation.evidence
    return CurrentHistoricalFamilyEvidenceObservation(
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


def _file_reference(root: Path, path: Path) -> HistoricalCoverageFileReferenceV1:
    return HistoricalCoverageFileReferenceV1(
        path=_relative_path(root, path),
        physical_sha256=_file_sha256(path),
    )


def _relative_path(root: Path, path: Path) -> str:
    absolute_root = root.absolute()
    absolute_path = path.absolute()
    if absolute_root not in absolute_path.parents:
        raise CurrentHistoricalMechanicsEvidenceError(
            "evidence path escaped the canonical data root"
        )
    current = absolute_path
    while current != absolute_root:
        if current.exists() and current.is_symlink():
            raise CurrentHistoricalMechanicsEvidenceError(
                "evidence path contains a symlink"
            )
        current = current.parent
    return absolute_path.relative_to(absolute_root).as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size <= 0 or path.stat().st_size > MAXIMUM_JSON_BYTES:
            raise ValueError("invalid JSON size")
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical completion manifest cannot be read"
        ) from exc
    if not isinstance(value, dict):
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical completion manifest is not an object"
        )
    return value


def _required_sha(manifest: dict[str, Any], field: str) -> str:
    value = manifest.get(field)
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical completion fingerprint is invalid"
        )
    return value


def _required_utc_datetime(manifest: dict[str, Any], field: str) -> datetime:
    value = manifest.get(field)
    if not isinstance(value, str):
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical completion timestamp is invalid"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical completion timestamp is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CurrentHistoricalMechanicsEvidenceError(
            "canonical completion timestamp is invalid"
        )
    return parsed.astimezone(UTC)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()
