"""Formal reader for bounded canonical corporate-action source observations."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tip_api.contracts.market_data.v1 import (
    CorporateActionSourceObservationV1,
    CorporateActionSourcePublicationV1,
    corporate_action_source_publication_bytes,
)
from tip_api.persistence.parquet.historical_coverage import (
    ParquetHistoricalCoverageRepository,
)
from tip_api.persistence.parquet.historical_research import (
    MANIFEST_FILE_NAME,
    PARQUET_FILE_NAME,
    ParquetHistoricalResearchRepository,
)


APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
PUBLICATION_DIRECTORY = "provider-corporate-action-observation-publications"
PUBLICATION_FILE_NAME = "manifest.json"
MAXIMUM_PUBLICATION_BYTES = 16 * 1024 * 1024


class CanonicalCorporateActionSourceError(RuntimeError):
    """Raised when canonical source-observation evidence does not reconcile."""


@dataclass(frozen=True, slots=True)
class CanonicalCorporateActionSource:
    publication: CorporateActionSourcePublicationV1
    publication_path: Path
    publication_sha256: str
    records: tuple[CorporateActionSourceObservationV1, ...]


def read_canonical_corporate_action_source(
    *, data_root: Path, publication_path: Path
) -> CanonicalCorporateActionSource:
    """Transitively validate one marker and every referenced canonical byte."""

    root = _validated_data_root(data_root)
    path = publication_path if publication_path.is_absolute() else root / publication_path
    _regular_file(root, path, expected_mode=0o644)
    if {item.name for item in path.parent.iterdir()} != {PUBLICATION_FILE_NAME}:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication file set differs"
        )
    raw = path.read_bytes()
    if len(raw) > MAXIMUM_PUBLICATION_BYTES:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication exceeds its byte ceiling"
        )
    try:
        publication = CorporateActionSourcePublicationV1.model_validate_json(raw)
    except Exception as exc:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication contract is invalid"
        ) from exc
    if raw != corporate_action_source_publication_bytes(publication):
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication bytes are not canonical"
        )
    expected_path = (
        root
        / "market-data"
        / PUBLICATION_DIRECTORY
        / "schema_version=1"
        / f"provider_id={publication.provider_id}"
        / f"coverage_id={publication.logical_fingerprint}"
        / PUBLICATION_FILE_NAME
    )
    if path != expected_path:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication path differs"
        )
    identity = ParquetHistoricalCoverageRepository(root).read_dataset_evidence(
        root / publication.identity_evidence_path
    )
    if (
        identity.physical_sha256 != publication.identity_evidence_sha256
        or identity.evidence.logical_fingerprint
        != publication.identity_evidence_logical_fingerprint
        or len(identity.evidence.sessions) != publication.identity_session_count
        or identity.evidence.sessions[0] != publication.start_date
        or identity.evidence.sessions[-1] != publication.end_date
    ):
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication Identity evidence differs"
        )

    repository = ParquetHistoricalResearchRepository(root)
    records: list[CorporateActionSourceObservationV1] = []
    for artifact in publication.artifacts:
        partition = root / PurePosixPath(artifact.partition_path)
        _directory(root, partition, expected_mode=0o755)
        if {item.name for item in partition.iterdir()} != {
            MANIFEST_FILE_NAME,
            PARQUET_FILE_NAME,
        }:
            raise CanonicalCorporateActionSourceError(
                "corporate-action partition file set differs"
            )
        manifest_path = partition / MANIFEST_FILE_NAME
        parquet_path = partition / PARQUET_FILE_NAME
        _regular_file(root, manifest_path, expected_mode=0o644)
        _regular_file(root, parquet_path, expected_mode=0o644)
        try:
            part = repository.read_corporate_action_observations(partition)
        except Exception as exc:
            raise CanonicalCorporateActionSourceError(
                "corporate-action partition failed formal reread"
            ) from exc
        if (
            len(part) != artifact.record_count
            or _file_sha256(manifest_path) != artifact.manifest_sha256
            or manifest_path.stat().st_size != artifact.manifest_bytes
            or _file_sha256(parquet_path) != artifact.parquet_sha256
            or parquet_path.stat().st_size != artifact.parquet_bytes
            or any(item.effective_date.year != artifact.event_year for item in part)
            or _partition_logical_fingerprint(manifest_path)
            != artifact.logical_fingerprint
        ):
            raise CanonicalCorporateActionSourceError(
                "corporate-action partition binding differs"
            )
        records.extend(part)
    ordered = tuple(
        sorted(
            records,
            key=lambda item: (
                item.provider,
                item.source_action_id,
                item.source_revision,
            ),
        )
    )
    if len(ordered) != publication.source_record_count:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication record count differs"
        )
    resolved = sum(item.instrument_id is not None for item in ordered)
    quarantined = sum(item.record_status.value == "quarantined" for item in ordered)
    if (
        resolved != publication.resolved_record_count
        or quarantined != publication.quarantined_record_count
        or resolved + quarantined != len(ordered)
        or any(
            item.knowledge_time_status.value != "first_observed_only"
            or item.source_available_at is not None
            or item.source_revision != 1
            for item in ordered
        )
    ):
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication semantics differ"
        )
    return CanonicalCorporateActionSource(
        publication=publication,
        publication_path=path,
        publication_sha256=_bytes_sha256(raw),
        records=ordered,
    )


def _partition_logical_fingerprint(path: Path) -> str:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise CanonicalCorporateActionSourceError(
            "corporate-action partition manifest is invalid"
        ) from exc
    fingerprint = value.get("logical_fingerprint")
    if not isinstance(fingerprint, str):
        raise CanonicalCorporateActionSourceError(
            "corporate-action partition fingerprint is missing"
        )
    return fingerprint


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CanonicalCorporateActionSourceError(
            "corporate-action canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != path or resolved != APPROVED_DATA_ROOT:
        raise CanonicalCorporateActionSourceError(
            "corporate-action data root is not the approved Dell root"
        )
    return resolved


def _directory(root: Path, path: Path, *, expected_mode: int) -> None:
    _inside_root(root, path)
    if path.is_symlink() or not path.is_dir():
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication directory is unavailable"
        )
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != expected_mode:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication directory custody differs"
        )


def _regular_file(root: Path, path: Path, *, expected_mode: int) -> None:
    _inside_root(root, path)
    if path.is_symlink() or not path.is_file():
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication file is unavailable"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != expected_mode
    ):
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication file custody differs"
        )


def _inside_root(root: Path, path: Path) -> None:
    if path != root and root not in path.parents:
        raise CanonicalCorporateActionSourceError(
            "corporate-action publication path escaped the data root"
        )
    current = path
    while current != root:
        if current.is_symlink():
            raise CanonicalCorporateActionSourceError(
                "corporate-action publication path contains a symlink"
            )
        current = current.parent


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
