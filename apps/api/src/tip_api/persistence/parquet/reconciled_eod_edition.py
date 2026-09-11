"""Immutable candidate persistence for Reconciled EOD Edition V1 sessions."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import ValidationError

from tip_api.contracts.market_data.v1 import EodPriceBarV1
from tip_api.contracts.market_data.v1.reconciled_eod_edition import (
    DATASET_NAME,
    ReconciledEodDiffDisposition,
    ReconciledEodIntervalManifestV1,
    ReconciledEodIntervalSessionReferenceV1,
    ReconciledEodSessionManifestV1,
    ReconciledEodSourceProvenance,
    seal_reconciled_eod_interval_manifest,
    seal_reconciled_eod_session_manifest,
)
from tip_api.persistence.parquet.eod_bars import (
    EOD_PRICE_BAR_ARROW_SCHEMA,
    PARQUET_FILE_NAME,
    records_to_table,
)
from tip_api.persistence.parquet.manifest import (
    content_fingerprint,
    table_rows_fingerprint,
)
from tip_api.persistence.parquet.eod_bars import (
    _table_to_fingerprint_rows,
    _validate_records_for_publish,
)
from tip_api.providers.massive.mapping import MASSIVE_PROVIDER_ID
from tip_api.providers.massive.same_day_catchup import canonical_json_bytes
from tip_api.services.reconciled_eod_edition import ReconciledEodSessionCandidate


CONTRACT_VERSION_PARTITION = "1"
MANIFEST_FILE_NAME = "manifest.json"
INTERVAL_MANIFEST_FILE_NAME = "interval-manifest.json"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")


class ReconciledEodEditionPersistenceError(RuntimeError):
    """Fail-closed edition candidate persistence error."""


class ReconciledEodEditionConflictError(ReconciledEodEditionPersistenceError):
    """An immutable edition target already has different content."""


class ReconciledEodEditionCorruptionError(ReconciledEodEditionPersistenceError):
    """A completed edition artifact failed formal reread."""


@dataclass(frozen=True, slots=True)
class CompletedReconciledEodSession:
    manifest: ReconciledEodSessionManifestV1
    records: tuple[EodPriceBarV1, ...]
    partition_path: Path


@dataclass(frozen=True, slots=True)
class ReconciledEodSessionWriteResult:
    edition_id: str
    session_date: date
    record_count: int
    content_fingerprint: str
    manifest_fingerprint: str
    partition_path: Path
    status: str


@dataclass(frozen=True, slots=True)
class CompletedReconciledEodEdition:
    manifest: ReconciledEodIntervalManifestV1
    sessions: tuple[CompletedReconciledEodSession, ...]
    edition_path: Path


@dataclass(frozen=True, slots=True)
class ParquetReconciledEodEditionCandidateRepository:
    """Write edition sessions only to an isolated candidate root."""

    root: Path
    edition_id: str
    implementation_revision: str
    created_at: datetime | None = None

    def publish_session(
        self,
        candidate: ReconciledEodSessionCandidate,
    ) -> ReconciledEodSessionWriteResult:
        root = _candidate_root(self.root)
        if candidate.diff.disposition == ReconciledEodDiffDisposition.QUARANTINED:
            raise ReconciledEodEditionPersistenceError(
                "quarantined EOD candidate cannot be published"
            )
        _validate_records_for_publish(
            candidate.rebuilt_records,
            session_date=candidate.session_date,
        )
        rebuilt_fingerprint = content_fingerprint(candidate.rebuilt_records)
        if rebuilt_fingerprint != candidate.rebuilt_eod_fingerprint:
            raise ReconciledEodEditionPersistenceError(
                "candidate EOD fingerprint differs from its records"
            )
        if candidate.diff.rebuilt_record_count != len(candidate.rebuilt_records):
            raise ReconciledEodEditionPersistenceError(
                "candidate EOD diff count differs from its records"
            )

        partition = _partition_path(
            root,
            edition_id=self.edition_id,
            session_date=candidate.session_date,
        )
        if partition.exists() or partition.is_symlink():
            completed = read_reconciled_eod_session(
                root=root,
                edition_id=self.edition_id,
                session_date=candidate.session_date,
            )
            _verify_existing_candidate(
                completed,
                candidate=candidate,
                implementation_revision=self.implementation_revision,
            )
            return _write_result(completed, status="already_present")
        interval_manifest = partition.parent / INTERVAL_MANIFEST_FILE_NAME
        if interval_manifest.exists() or interval_manifest.is_symlink():
            raise ReconciledEodEditionConflictError(
                "completed EOD edition cannot accept another session"
            )

        staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise ReconciledEodEditionConflictError(
                "reconciled EOD staging path already exists"
            )
        try:
            staging.mkdir(mode=0o700)
            parquet_path = staging / PARQUET_FILE_NAME
            table = records_to_table(candidate.rebuilt_records)
            pq.write_table(table, parquet_path)
            parquet_path.chmod(0o600)
            _fsync_file(parquet_path)
            parquet_sha256 = _file_sha256(parquet_path)
            manifest = seal_reconciled_eod_session_manifest(
                {
                    "edition_id": self.edition_id,
                    "session_date": candidate.session_date,
                    "provider": MASSIVE_PROVIDER_ID,
                    "implementation_revision": self.implementation_revision,
                    "source_provenance": candidate.source_provenance,
                    "source_observed_at": candidate.source_observed_at,
                    "source_package_manifest_sha256": (
                        candidate.source_package_manifest_sha256
                    ),
                    "source_package_content_sha256": (
                        candidate.source_package_content_sha256
                    ),
                    "identity_as_of_date": candidate.session_date,
                    "identity_snapshot_fingerprint": (
                        candidate.identity_snapshot_fingerprint
                    ),
                    "identity_source_fingerprint": (
                        candidate.identity_source_fingerprint
                    ),
                    "base_eod_fingerprint": candidate.base_eod_fingerprint,
                    "rebuilt_eod_fingerprint": candidate.rebuilt_eod_fingerprint,
                    "diff": candidate.diff,
                    "quality_summary_fingerprint": (
                        candidate.quality_summary_fingerprint
                    ),
                    "quality_warnings": candidate.quality_warnings,
                    "parquet_sha256": parquet_sha256,
                    "created_at": self.created_at or datetime.now(UTC),
                }
            )
            manifest_path = staging / MANIFEST_FILE_NAME
            manifest_path.write_bytes(
                canonical_json_bytes(manifest.model_dump(mode="json"))
            )
            manifest_path.chmod(0o600)
            _fsync_file(manifest_path)
            _fsync_directory(staging)
            staging.replace(partition)
            _fsync_directory(partition.parent)
        except Exception:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise

        completed = read_reconciled_eod_session(
            root=root,
            edition_id=self.edition_id,
            session_date=candidate.session_date,
        )
        _verify_existing_candidate(
            completed,
            candidate=candidate,
            implementation_revision=self.implementation_revision,
        )
        return _write_result(completed, status="published")

    def publish_interval_manifest(
        self,
        *,
        session_dates: tuple[date, ...],
        evaluation_first_session: date,
        evaluation_last_session: date,
        warmup_first_session: date | None = None,
        warmup_last_session: date | None = None,
    ) -> CompletedReconciledEodEdition:
        """Publish the sole edition completion marker after formal reread."""

        root = _candidate_root(self.root)
        if not session_dates or session_dates != tuple(sorted(set(session_dates))):
            raise ReconciledEodEditionPersistenceError(
                "edition session dates must be non-empty, unique, and ordered"
            )
        sessions = tuple(
            read_reconciled_eod_session(
                root=root,
                edition_id=self.edition_id,
                session_date=session_date,
            )
            for session_date in session_dates
        )
        edition_path = sessions[0].partition_path.parent
        marker = edition_path / INTERVAL_MANIFEST_FILE_NAME
        declared_session_names = {
            f"session_date={session_date.isoformat()}"
            for session_date in session_dates
        }
        completed_before: CompletedReconciledEodEdition | None = None
        if marker.exists() or marker.is_symlink():
            completed_before = read_reconciled_eod_edition(
                root=root,
                edition_id=self.edition_id,
            )
            manifest_created_at = completed_before.manifest.created_at
        else:
            if {item.name for item in edition_path.iterdir()} != declared_session_names:
                raise ReconciledEodEditionPersistenceError(
                    "edition file set differs before interval completion"
                )
            manifest_created_at = self.created_at or datetime.now(UTC)
        if any(
            item.manifest.implementation_revision != self.implementation_revision
            for item in sessions
        ):
            raise ReconciledEodEditionPersistenceError(
                "edition sessions use different implementation revisions"
            )
        references = tuple(
            ReconciledEodIntervalSessionReferenceV1(
                session_date=item.manifest.session_date,
                session_manifest_fingerprint=item.manifest.logical_fingerprint,
                rebuilt_eod_fingerprint=item.manifest.rebuilt_eod_fingerprint,
                record_count=item.manifest.diff.rebuilt_record_count,
                added_record_count=item.manifest.diff.added_record_count,
                source_provenance=item.manifest.source_provenance,
                disposition=item.manifest.diff.disposition,
            )
            for item in sessions
        )
        manifest = seal_reconciled_eod_interval_manifest(
            {
                "edition_id": self.edition_id,
                "provider": MASSIVE_PROVIDER_ID,
                "implementation_revision": self.implementation_revision,
                "evaluation_first_session": evaluation_first_session,
                "evaluation_last_session": evaluation_last_session,
                "warmup_first_session": warmup_first_session,
                "warmup_last_session": warmup_last_session,
                "sessions": references,
                "retained_original_session_count": sum(
                    item.manifest.source_provenance
                    == ReconciledEodSourceProvenance.RETAINED_ORIGINAL
                    for item in sessions
                ),
                "later_reacquisition_session_count": sum(
                    item.manifest.source_provenance
                    == ReconciledEodSourceProvenance.LATER_REACQUISITION
                    for item in sessions
                ),
                "added_record_count": sum(
                    item.manifest.diff.added_record_count for item in sessions
                ),
                "created_at": manifest_created_at,
            }
        )
        if completed_before is not None:
            if completed_before.manifest != manifest:
                raise ReconciledEodEditionConflictError(
                    "existing edition interval manifest differs"
                )
            return completed_before
        temporary = edition_path / f".{INTERVAL_MANIFEST_FILE_NAME}.tmp.{os.getpid()}"
        if temporary.exists() or temporary.is_symlink():
            raise ReconciledEodEditionConflictError(
                "edition interval staging marker already exists"
            )
        try:
            temporary.write_bytes(
                canonical_json_bytes(manifest.model_dump(mode="json"))
            )
            temporary.chmod(0o600)
            _fsync_file(temporary)
            temporary.replace(marker)
            _fsync_directory(edition_path)
        except Exception:
            if temporary.is_file() and not temporary.is_symlink():
                temporary.unlink()
            raise
        return read_reconciled_eod_edition(
            root=root,
            edition_id=self.edition_id,
        )


def read_reconciled_eod_session(
    *,
    root: Path,
    edition_id: str,
    session_date: date,
) -> CompletedReconciledEodSession:
    root = _read_root(root)
    partition = _partition_path(
        root,
        edition_id=edition_id,
        session_date=session_date,
        create_parents=False,
    )
    _reject_symlink_chain(root, partition)
    if partition.is_symlink() or not partition.is_dir():
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD session partition is unavailable"
        )
    actual = {item.name for item in partition.iterdir()}
    if actual != {PARQUET_FILE_NAME, MANIFEST_FILE_NAME}:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD session file set differs"
        )
    manifest_path = partition / MANIFEST_FILE_NAME
    parquet_path = partition / PARQUET_FILE_NAME
    if any(path.is_symlink() or not path.is_file() for path in (manifest_path, parquet_path)):
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD session artifact is unavailable"
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = ReconciledEodSessionManifestV1.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD session manifest is invalid"
        ) from exc
    if manifest.edition_id != edition_id or manifest.session_date != session_date:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD session identity differs"
        )
    if manifest.parquet_sha256 != _file_sha256(parquet_path):
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD Parquet hash differs"
        )
    try:
        table = pq.ParquetFile(parquet_path).read()
    except Exception as exc:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD Parquet is unreadable"
        ) from exc
    if not table.schema.equals(EOD_PRICE_BAR_ARROW_SCHEMA, check_metadata=False):
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD Parquet schema differs"
        )
    if table.num_rows != manifest.diff.rebuilt_record_count:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD row count differs"
        )
    if table_rows_fingerprint(_table_to_fingerprint_rows(table)) != (
        manifest.rebuilt_eod_fingerprint
    ):
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD content fingerprint differs"
        )
    try:
        records = tuple(
            EodPriceBarV1.model_validate(row) for row in table.to_pylist()
        )
    except Exception as exc:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD rows violate their logical contract"
        ) from exc
    return CompletedReconciledEodSession(
        manifest=manifest,
        records=records,
        partition_path=partition,
    )


def read_reconciled_eod_edition(
    *,
    root: Path,
    edition_id: str,
) -> CompletedReconciledEodEdition:
    root = _read_root(root)
    edition_path = _edition_path(root, edition_id=edition_id)
    _reject_symlink_chain(root, edition_path)
    marker = edition_path / INTERVAL_MANIFEST_FILE_NAME
    if marker.is_symlink() or not marker.is_file():
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD interval manifest is unavailable"
        )
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        manifest = ReconciledEodIntervalManifestV1.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD interval manifest is invalid"
        ) from exc
    if manifest.edition_id != edition_id:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD interval identity differs"
        )
    expected_names = {
        INTERVAL_MANIFEST_FILE_NAME,
        *(f"session_date={item.session_date.isoformat()}" for item in manifest.sessions),
    }
    if {item.name for item in edition_path.iterdir()} != expected_names:
        raise ReconciledEodEditionCorruptionError(
            "reconciled EOD edition file set differs"
        )
    sessions = tuple(
        read_reconciled_eod_session(
            root=root,
            edition_id=edition_id,
            session_date=reference.session_date,
        )
        for reference in manifest.sessions
    )
    for reference, completed in zip(manifest.sessions, sessions, strict=True):
        session = completed.manifest
        if (
            session.logical_fingerprint != reference.session_manifest_fingerprint
            or session.rebuilt_eod_fingerprint != reference.rebuilt_eod_fingerprint
            or session.diff.rebuilt_record_count != reference.record_count
            or session.diff.added_record_count != reference.added_record_count
            or session.source_provenance != reference.source_provenance
            or session.diff.disposition != reference.disposition
            or session.implementation_revision != manifest.implementation_revision
        ):
            raise ReconciledEodEditionCorruptionError(
                "reconciled EOD interval session binding differs"
            )
    return CompletedReconciledEodEdition(
        manifest=manifest,
        sessions=sessions,
        edition_path=edition_path,
    )


def _verify_existing_candidate(
    completed: CompletedReconciledEodSession,
    *,
    candidate: ReconciledEodSessionCandidate,
    implementation_revision: str,
) -> None:
    manifest = completed.manifest
    if (
        content_fingerprint(completed.records)
        != candidate.rebuilt_eod_fingerprint
        or manifest.implementation_revision != implementation_revision
        or manifest.source_provenance != candidate.source_provenance
        or manifest.source_observed_at != candidate.source_observed_at
        or manifest.source_package_manifest_sha256
        != candidate.source_package_manifest_sha256
        or manifest.source_package_content_sha256
        != candidate.source_package_content_sha256
        or manifest.identity_snapshot_fingerprint
        != candidate.identity_snapshot_fingerprint
        or manifest.identity_source_fingerprint
        != candidate.identity_source_fingerprint
        or manifest.base_eod_fingerprint != candidate.base_eod_fingerprint
        or manifest.diff != candidate.diff
        or manifest.quality_summary_fingerprint
        != candidate.quality_summary_fingerprint
        or manifest.quality_warnings != candidate.quality_warnings
    ):
        raise ReconciledEodEditionConflictError(
            "existing reconciled EOD session differs from candidate"
        )


def _write_result(
    completed: CompletedReconciledEodSession,
    *,
    status: str,
) -> ReconciledEodSessionWriteResult:
    return ReconciledEodSessionWriteResult(
        edition_id=completed.manifest.edition_id,
        session_date=completed.manifest.session_date,
        record_count=len(completed.records),
        content_fingerprint=completed.manifest.rebuilt_eod_fingerprint,
        manifest_fingerprint=completed.manifest.logical_fingerprint,
        partition_path=completed.partition_path,
        status=status,
    )


def _candidate_root(root: Path) -> Path:
    root = _read_root(root, must_exist=False)
    temporary = Path("/tmp").resolve(strict=True)
    if temporary not in root.parents:
        raise ReconciledEodEditionPersistenceError(
            "edition candidate root must be below /tmp"
        )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink():
        raise ReconciledEodEditionPersistenceError(
            "edition candidate root must not be a symlink"
        )
    root.chmod(0o700)
    return root.resolve(strict=True)


def _read_root(root: Path, *, must_exist: bool = True) -> Path:
    if not root.is_absolute() or root.is_symlink():
        raise ReconciledEodEditionPersistenceError("edition root is invalid")
    if must_exist and not root.is_dir():
        raise ReconciledEodEditionPersistenceError("edition root is unavailable")
    resolved = root.resolve(strict=must_exist)
    temporary = Path("/tmp").resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT and temporary not in resolved.parents:
        raise ReconciledEodEditionPersistenceError(
            "edition root is outside approved boundaries"
        )
    return resolved


def _partition_path(
    root: Path,
    *,
    edition_id: str,
    session_date: date,
    create_parents: bool = True,
) -> Path:
    if not edition_id or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in edition_id
    ):
        raise ReconciledEodEditionPersistenceError("edition_id is invalid")
    partition = (
        root
        / "market-data"
        / DATASET_NAME
        / f"contract_version={CONTRACT_VERSION_PARTITION}"
        / f"edition_id={edition_id}"
        / f"session_date={session_date.isoformat()}"
    )
    if create_parents:
        partition.parent.mkdir(parents=True, exist_ok=True)
    if root not in partition.resolve(strict=False).parents:
        raise ReconciledEodEditionPersistenceError("edition path escapes root")
    return partition


def _edition_path(root: Path, *, edition_id: str) -> Path:
    sentinel = _partition_path(
        root,
        edition_id=edition_id,
        session_date=date(1970, 1, 1),
        create_parents=False,
    )
    return sentinel.parent


def _reject_symlink_chain(root: Path, path: Path) -> None:
    current = path
    while current != root:
        if current.is_symlink():
            raise ReconciledEodEditionCorruptionError(
                "reconciled EOD path contains a symlink"
            )
        if root not in current.resolve(strict=False).parents and current != root:
            raise ReconciledEodEditionCorruptionError(
                "reconciled EOD path escapes its root"
            )
        current = current.parent


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
