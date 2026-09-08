"""Atomic immutable Parquet snapshot persistence for Classification V1."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ValidationError

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    ClassificationAssignmentBasis,
    ClassificationCoverageDecisionV1,
    ClassificationCoverageStatus,
    ClassificationCoverageSummaryV1,
    ClassificationDefinitionV1,
    ClassificationEligibilityScope,
    ClassificationMembershipV1,
    ClassificationSnapshotManifestV1,
    ClassificationSourceObservationV1,
    ClassificationType,
    classification_fingerprint,
)
from tip_api.persistence.classification import (
    ClassificationConflictError,
    ClassificationCorruptionError,
    ClassificationPersistenceError,
    ClassificationSnapshotWriteResult,
    CompletedClassificationSnapshot,
)


SCHEMA_PARTITION = "1"
SNAPSHOT_DIRECTORY = "market-data/classification-snapshots"
MANIFEST_FILE = "manifest.json"
DEFINITIONS_FILE = "definitions.parquet"
OBSERVATIONS_FILE = "source-observations.parquet"
COVERAGE_FILE = "coverage.parquet"
MEMBERSHIPS_FILE = "memberships.parquet"
EXPECTED_FILES = {
    MANIFEST_FILE,
    DEFINITIONS_FILE,
    OBSERVATIONS_FILE,
    COVERAGE_FILE,
    MEMBERSHIPS_FILE,
}

PATH_NODE_TYPE = pa.struct(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("level", pa.int32(), nullable=False),
        pa.field("code", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("level_name", pa.string(), nullable=True),
    ]
)

DEFINITION_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("classification_id", pa.string(), nullable=False),
        pa.field("classification_type", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("description", pa.string(), nullable=True),
        pa.field("parent_classification_id", pa.string(), nullable=True),
        pa.field("methodology_version", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("valid_from", pa.date32(), nullable=False),
        pa.field("valid_to", pa.date32(), nullable=True),
        pa.field("source", pa.string(), nullable=False),
    ]
)

OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("source_observation_id", pa.string(), nullable=False),
        pa.field("provider", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("source_entity_id", pa.string(), nullable=False),
        pa.field("source_security_id", pa.string(), nullable=True),
        pa.field("instrument_id", pa.string(), nullable=True),
        pa.field("identity_resolution_status", pa.string(), nullable=False),
        pa.field("identity_evidence", pa.list_(pa.string()), nullable=False),
        pa.field("assignment_basis", pa.string(), nullable=False),
        pa.field("external_taxonomy", pa.string(), nullable=False),
        pa.field("external_taxonomy_version", pa.string(), nullable=False),
        pa.field("external_classification_code", pa.string(), nullable=False),
        pa.field("external_classification_path", pa.list_(PATH_NODE_TYPE), nullable=False),
        pa.field("valid_from", pa.date32(), nullable=False),
        pa.field("valid_to", pa.date32(), nullable=True),
        pa.field("knowledge_time_status", pa.string(), nullable=False),
        pa.field("source_available_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("provider_updated_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("revision_id", pa.string(), nullable=True),
        pa.field("supersedes_source_observation_id", pa.string(), nullable=True),
        pa.field("correction_status", pa.string(), nullable=False),
        pa.field("permission_review_fingerprint", pa.string(), nullable=False),
        pa.field("eligibility_scope", pa.string(), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)

COVERAGE_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("as_of_date", pa.date32(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("source_observation_ids", pa.list_(pa.string()), nullable=False),
        pa.field("classification_ids", pa.list_(pa.string()), nullable=False),
        pa.field("eligibility_scope", pa.string(), nullable=False),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("evaluated_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
    ]
)

MEMBERSHIP_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("classification_id", pa.string(), nullable=False),
        pa.field("valid_from", pa.date32(), nullable=False),
        pa.field("valid_to", pa.date32(), nullable=True),
        pa.field("membership_role", pa.string(), nullable=False),
        pa.field("membership_weight", pa.decimal128(38, 18), nullable=True),
        pa.field("confidence", pa.decimal128(38, 18), nullable=True),
        pa.field("source", pa.string(), nullable=False),
        pa.field("source_reference", pa.string(), nullable=True),
        pa.field("source_observation_id", pa.string(), nullable=False),
        pa.field("assignment_basis", pa.string(), nullable=False),
        pa.field("source_available_at", pa.timestamp("us", tz="UTC"), nullable=True),
        pa.field("eligibility_scope", pa.string(), nullable=False),
        pa.field("assigned_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("review_status", pa.string(), nullable=False),
        pa.field("methodology_version", pa.string(), nullable=False),
        pa.field("quality_status", pa.string(), nullable=False),
        pa.field("quality_flags", pa.list_(pa.string()), nullable=False),
    ]
)

RecordT = TypeVar("RecordT", bound=BaseModel)


class ParquetClassificationRepository:
    """Publish and formally reread one complete classification snapshot."""

    def __init__(self, root: Path):
        self.root = root

    def publish_snapshot(
        self,
        *,
        definitions: tuple[ClassificationDefinitionV1, ...],
        observations: tuple[ClassificationSourceObservationV1, ...],
        coverage: tuple[ClassificationCoverageDecisionV1, ...],
        memberships: tuple[ClassificationMembershipV1, ...],
        as_of_date: date,
        methodology_version: str,
        providers: tuple[str, ...],
        permission_review_fingerprints: tuple[str, ...],
        created_at: datetime,
        external_request_count: int = 0,
        live_source_accessed: bool = False,
        production_authorized: bool = False,
        historical_research_authorized: bool = False,
    ) -> ClassificationSnapshotWriteResult:
        created_at = normalize_utc_datetime(created_at)
        _validate_publication_controls(
            as_of_date=as_of_date,
            providers=providers,
            permission_review_fingerprints=permission_review_fingerprints,
            external_request_count=external_request_count,
            live_source_accessed=live_source_accessed,
            production_authorized=production_authorized,
            historical_research_authorized=historical_research_authorized,
        )
        ordered = _validate_and_order(
            definitions=definitions,
            observations=observations,
            coverage=coverage,
            memberships=memberships,
            as_of_date=as_of_date,
            methodology_version=methodology_version,
            providers=providers,
            permission_review_fingerprints=permission_review_fingerprints,
        )
        root = _prepare_root(self.root)
        partition = _snapshot_path(root, as_of_date, methodology_version)
        identity = _snapshot_identity(
            ordered=ordered,
            as_of_date=as_of_date,
            methodology_version=methodology_version,
            providers=providers,
            permission_review_fingerprints=permission_review_fingerprints,
            external_request_count=external_request_count,
            live_source_accessed=live_source_accessed,
            production_authorized=production_authorized,
            historical_research_authorized=historical_research_authorized,
        )
        if partition.exists() or partition.is_symlink():
            completed = _read_snapshot(root, partition)
            if _completed_identity(completed) != identity:
                raise ClassificationConflictError(
                    "existing classification snapshot conflicts with requested content"
                )
            return _write_result(completed.manifest, partition, "already_present")

        _reject_existing_symlinks(root, partition.parent)
        partition.parent.mkdir(parents=True, exist_ok=True)
        staging = partition.parent / f".{partition.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise ClassificationConflictError("classification staging path already exists")
        try:
            staging.mkdir()
            file_specs = (
                (DEFINITIONS_FILE, DEFINITION_SCHEMA, ordered.definitions),
                (OBSERVATIONS_FILE, OBSERVATION_SCHEMA, ordered.observations),
                (COVERAGE_FILE, COVERAGE_SCHEMA, ordered.coverage),
                (MEMBERSHIPS_FILE, MEMBERSHIP_SCHEMA, ordered.memberships),
            )
            physical_hashes: dict[str, str] = {}
            for file_name, schema, records in file_specs:
                path = staging / file_name
                table = _records_to_table(records, schema)
                pq.write_table(table, path, compression="zstd")
                _fsync_file(path)
                _validate_table_file(
                    path,
                    schema=schema,
                    model=_model_for_file(file_name),
                    ordered_records=records,
                )
                physical_hashes[file_name] = _file_sha256(path)

            manifest = _build_manifest(
                ordered=ordered,
                as_of_date=as_of_date,
                methodology_version=methodology_version,
                providers=providers,
                permission_review_fingerprints=permission_review_fingerprints,
                created_at=created_at,
                physical_hashes=physical_hashes,
                external_request_count=external_request_count,
                live_source_accessed=live_source_accessed,
                production_authorized=production_authorized,
                historical_research_authorized=historical_research_authorized,
            )
            _write_json(staging / MANIFEST_FILE, manifest.model_dump(mode="json"))
            _fsync_directory(staging)
            staging.replace(partition)
            _fsync_directory(partition.parent)
            completed = _read_snapshot(root, partition)
            return _write_result(completed.manifest, partition, "published")
        except ClassificationPersistenceError:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise
        except Exception as exc:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise ClassificationPersistenceError(
                "classification snapshot publication failed"
            ) from exc

    def read_snapshot(
        self,
        *,
        as_of_date: date,
        methodology_version: str,
    ) -> CompletedClassificationSnapshot:
        root = _require_root(self.root)
        return _read_snapshot(root, _snapshot_path(root, as_of_date, methodology_version))


@dataclass(frozen=True, slots=True)
class _OrderedSnapshot:
    definitions: tuple[ClassificationDefinitionV1, ...]
    observations: tuple[ClassificationSourceObservationV1, ...]
    coverage: tuple[ClassificationCoverageDecisionV1, ...]
    memberships: tuple[ClassificationMembershipV1, ...]


def _validate_and_order(
    *,
    definitions: tuple[ClassificationDefinitionV1, ...],
    observations: tuple[ClassificationSourceObservationV1, ...],
    coverage: tuple[ClassificationCoverageDecisionV1, ...],
    memberships: tuple[ClassificationMembershipV1, ...],
    as_of_date: date,
    methodology_version: str,
    providers: tuple[str, ...],
    permission_review_fingerprints: tuple[str, ...],
) -> _OrderedSnapshot:
    if not definitions or not coverage:
        raise ClassificationPersistenceError(
            "classification snapshot requires definitions and explicit coverage"
        )
    if not isinstance(methodology_version, str) or not methodology_version.strip():
        raise ClassificationPersistenceError("methodology_version is required")
    if providers != tuple(sorted(set(providers))) or not providers:
        raise ClassificationPersistenceError("providers must be non-empty, unique, and sorted")
    if permission_review_fingerprints != tuple(sorted(set(permission_review_fingerprints))):
        raise ClassificationPersistenceError(
            "permission review fingerprints must be unique and sorted"
        )

    ordered = _OrderedSnapshot(
        definitions=tuple(sorted(definitions, key=lambda item: str(item.classification_id))),
        observations=tuple(sorted(observations, key=lambda item: item.source_observation_id)),
        coverage=tuple(sorted(coverage, key=lambda item: str(item.instrument_id))),
        memberships=tuple(
            sorted(
                memberships,
                key=lambda item: (
                    str(item.instrument_id),
                    str(item.classification_id),
                    item.valid_from,
                ),
            )
        ),
    )

    _reject_duplicate(
        (item.classification_id for item in ordered.definitions),
        "classification definition ID",
    )
    _reject_duplicate(
        (item.source_observation_id for item in ordered.observations),
        "classification source observation ID",
    )
    _reject_duplicate(
        (item.instrument_id for item in ordered.coverage),
        "classification coverage instrument",
    )
    _reject_duplicate(
        (
            (item.instrument_id, item.classification_id, item.valid_from)
            for item in ordered.memberships
        ),
        "classification membership business key",
    )

    definitions_by_id = {item.classification_id: item for item in ordered.definitions}
    observations_by_id = {
        item.source_observation_id: item for item in ordered.observations
    }
    coverage_by_instrument = {item.instrument_id: item for item in ordered.coverage}
    memberships_by_instrument: dict[UUID, list[ClassificationMembershipV1]] = {}

    for definition in ordered.definitions:
        if definition.methodology_version != methodology_version:
            raise ClassificationPersistenceError("definition methodology differs")
        _validate_definition_parent(definition, definitions_by_id)
    for observation in ordered.observations:
        if observation.as_of_date != as_of_date:
            raise ClassificationPersistenceError("observation as_of_date differs")
        if observation.provider not in providers:
            raise ClassificationPersistenceError("observation provider is undeclared")
        if observation.permission_review_fingerprint not in permission_review_fingerprints:
            raise ClassificationPersistenceError(
                "observation permission review fingerprint is undeclared"
            )
    superseded_observation_ids = _validate_observation_revisions(
        ordered.observations,
        observations_by_id,
    )
    for decision in ordered.coverage:
        if decision.as_of_date != as_of_date:
            raise ClassificationPersistenceError("coverage as_of_date differs")

    for membership in ordered.memberships:
        if membership.methodology_version != methodology_version:
            raise ClassificationPersistenceError("membership methodology differs")
        definition = definitions_by_id.get(membership.classification_id)
        observation = observations_by_id.get(membership.source_observation_id)
        if definition is None or observation is None:
            raise ClassificationPersistenceError(
                "membership references unknown definition or source observation"
            )
        if membership.source_observation_id in superseded_observation_ids:
            raise ClassificationPersistenceError(
                "membership references a superseded source observation"
            )
        if observation.instrument_id != membership.instrument_id:
            raise ClassificationPersistenceError("membership stable identity differs")
        if membership.source != observation.provider:
            raise ClassificationPersistenceError("membership source differs")
        if membership.assignment_basis is not observation.assignment_basis:
            raise ClassificationPersistenceError("membership assignment basis differs")
        if membership.source_available_at != observation.source_available_at:
            raise ClassificationPersistenceError("membership source availability differs")
        if not _interval_contains(
            observation.valid_from,
            observation.valid_to,
            membership.valid_from,
            membership.valid_to,
        ):
            raise ClassificationPersistenceError(
                "membership interval escapes source observation"
            )
        if _scope_rank(membership.eligibility_scope) > _scope_rank(
            observation.eligibility_scope
        ):
            raise ClassificationPersistenceError(
                "membership eligibility exceeds source observation"
            )
        memberships_by_instrument.setdefault(membership.instrument_id, []).append(
            membership
        )

    for instrument_id, decision in coverage_by_instrument.items():
        instrument_memberships = memberships_by_instrument.get(instrument_id, [])
        membership_classification_ids = tuple(
            sorted({item.classification_id for item in instrument_memberships}, key=str)
        )
        membership_observation_ids = tuple(
            sorted({item.source_observation_id for item in instrument_memberships})
        )
        if decision.status is ClassificationCoverageStatus.CLASSIFIED:
            if tuple(sorted(decision.classification_ids, key=str)) != membership_classification_ids:
                raise ClassificationPersistenceError(
                    "classified coverage differs from canonical memberships"
                )
            if tuple(sorted(decision.source_observation_ids)) != membership_observation_ids:
                raise ClassificationPersistenceError(
                    "classified coverage differs from source observations"
                )
            membership_scopes = {item.eligibility_scope for item in instrument_memberships}
            if len(membership_scopes) != 1 or decision.eligibility_scope not in membership_scopes:
                raise ClassificationPersistenceError(
                    "classified coverage eligibility differs from memberships"
                )
        elif instrument_memberships:
            raise ClassificationPersistenceError(
                "non-classified coverage cannot have canonical memberships"
            )
        for source_id in decision.source_observation_ids:
            observation = observations_by_id.get(source_id)
            if observation is None:
                raise ClassificationPersistenceError(
                    "coverage references unknown source observation"
                )
            if observation.instrument_id not in {None, instrument_id}:
                raise ClassificationPersistenceError(
                    "coverage source observation resolves to another instrument"
                )

    if set(memberships_by_instrument) - set(coverage_by_instrument):
        raise ClassificationPersistenceError("membership instrument lacks coverage decision")

    _validate_traditional_membership_paths(ordered.memberships, definitions_by_id)
    return ordered


def _validate_observation_revisions(
    observations: tuple[ClassificationSourceObservationV1, ...],
    observations_by_id: dict[str, ClassificationSourceObservationV1],
) -> set[str]:
    superseded_ids: set[str] = set()
    for observation in observations:
        superseded_id = observation.supersedes_source_observation_id
        if superseded_id is None:
            continue
        previous = observations_by_id.get(superseded_id)
        if previous is None:
            raise ClassificationPersistenceError(
                "classification revision references unknown source observation"
            )
        if (
            previous.provider != observation.provider
            or previous.source_entity_id != observation.source_entity_id
            or previous.external_taxonomy != observation.external_taxonomy
        ):
            raise ClassificationPersistenceError(
                "classification revision crosses source evidence identity"
            )
        if previous.observed_at >= observation.observed_at:
            raise ClassificationPersistenceError(
                "classification revision must follow the superseded observation"
            )
        superseded_ids.add(superseded_id)
    return superseded_ids


def _validate_publication_controls(
    *,
    as_of_date: date,
    providers: tuple[str, ...],
    permission_review_fingerprints: tuple[str, ...],
    external_request_count: int,
    live_source_accessed: bool,
    production_authorized: bool,
    historical_research_authorized: bool,
) -> None:
    if type(as_of_date) is not date:
        raise ClassificationPersistenceError("as_of_date must be a date")
    if any(not isinstance(item, str) or not item.strip() for item in providers):
        raise ClassificationPersistenceError("providers must contain non-empty text")
    if any(
        not isinstance(item, str)
        or len(item) != 64
        or any(character not in "0123456789abcdef" for character in item)
        for item in permission_review_fingerprints
    ) or not permission_review_fingerprints:
        raise ClassificationPersistenceError(
            "permission review fingerprints must be non-empty SHA-256 values"
        )
    if type(external_request_count) is not int or external_request_count < 0:
        raise ClassificationPersistenceError("external_request_count is invalid")
    if external_request_count > 0 and live_source_accessed is not True:
        raise ClassificationPersistenceError(
            "external requests require live source access disclosure"
        )
    if any(
        type(value) is not bool
        for value in (
            live_source_accessed,
            production_authorized,
            historical_research_authorized,
        )
    ):
        raise ClassificationPersistenceError("classification authorization flags must be boolean")


def _validate_definition_parent(
    definition: ClassificationDefinitionV1,
    definitions_by_id: dict[UUID, ClassificationDefinitionV1],
) -> None:
    expected_parent_type = {
        ClassificationType.INDUSTRY_GROUP: ClassificationType.SECTOR,
        ClassificationType.INDUSTRY: ClassificationType.INDUSTRY_GROUP,
        ClassificationType.SUB_INDUSTRY: ClassificationType.INDUSTRY,
    }.get(definition.classification_type)
    if expected_parent_type is None:
        return
    parent = definitions_by_id.get(definition.parent_classification_id)
    if parent is None or parent.classification_type is not expected_parent_type:
        raise ClassificationPersistenceError("classification definition parent differs")
    if not _interval_contains(
        parent.valid_from,
        parent.valid_to,
        definition.valid_from,
        definition.valid_to,
    ):
        raise ClassificationPersistenceError(
            "classification definition interval escapes its parent"
        )


def _validate_traditional_membership_paths(
    memberships: tuple[ClassificationMembershipV1, ...],
    definitions_by_id: dict[UUID, ClassificationDefinitionV1],
) -> None:
    by_instrument: dict[UUID, list[ClassificationMembershipV1]] = {}
    for membership in memberships:
        by_instrument.setdefault(membership.instrument_id, []).append(membership)
    traditional = {
        ClassificationType.SECTOR,
        ClassificationType.INDUSTRY_GROUP,
        ClassificationType.INDUSTRY,
        ClassificationType.SUB_INDUSTRY,
    }
    for instrument_memberships in by_instrument.values():
        by_type: dict[ClassificationType, list[ClassificationMembershipV1]] = {}
        by_classification: dict[UUID, list[ClassificationMembershipV1]] = {}
        for membership in instrument_memberships:
            definition = definitions_by_id[membership.classification_id]
            by_classification.setdefault(membership.classification_id, []).append(membership)
            if definition.classification_type in traditional:
                by_type.setdefault(definition.classification_type, []).append(membership)
        for type_memberships in by_type.values():
            ordered = sorted(type_memberships, key=lambda item: item.valid_from)
            for previous, current in zip(ordered, ordered[1:], strict=False):
                if previous.valid_to is None or current.valid_from < previous.valid_to:
                    raise ClassificationPersistenceError(
                        "traditional classification intervals overlap"
                    )
        for membership in instrument_memberships:
            definition = definitions_by_id[membership.classification_id]
            if definition.classification_type not in {
                ClassificationType.INDUSTRY_GROUP,
                ClassificationType.INDUSTRY,
                ClassificationType.SUB_INDUSTRY,
            }:
                continue
            parents = by_classification.get(definition.parent_classification_id, [])
            if not any(
                _interval_contains(
                    parent.valid_from,
                    parent.valid_to,
                    membership.valid_from,
                    membership.valid_to,
                )
                for parent in parents
            ):
                raise ClassificationPersistenceError(
                    "traditional membership lacks a covering parent"
                )


def _read_snapshot(root: Path, partition: Path) -> CompletedClassificationSnapshot:
    _require_within_root(root, partition)
    if not partition.is_dir() or partition.is_symlink():
        raise ClassificationCorruptionError(
            "classification snapshot directory is missing or unsafe"
        )
    if {item.name for item in partition.iterdir()} != EXPECTED_FILES:
        raise ClassificationCorruptionError("classification snapshot file set differs")
    manifest_path = partition / MANIFEST_FILE
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ClassificationCorruptionError("classification manifest is unavailable")
    try:
        manifest = ClassificationSnapshotManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except (ValidationError, ValueError, OSError) as exc:
        raise ClassificationCorruptionError("classification manifest is invalid") from exc
    if partition != _snapshot_path(root, manifest.as_of_date, manifest.methodology_version):
        raise ClassificationCorruptionError("classification snapshot path differs")

    definitions = _read_records(
        partition / DEFINITIONS_FILE,
        DEFINITION_SCHEMA,
        ClassificationDefinitionV1,
        manifest.definition_count,
        manifest.definitions_sha256,
        manifest.definitions_logical_fingerprint,
        lambda item: str(item.classification_id),
    )
    observations = _read_records(
        partition / OBSERVATIONS_FILE,
        OBSERVATION_SCHEMA,
        ClassificationSourceObservationV1,
        manifest.observation_count,
        manifest.observations_sha256,
        manifest.observations_logical_fingerprint,
        lambda item: item.source_observation_id,
    )
    coverage = _read_records(
        partition / COVERAGE_FILE,
        COVERAGE_SCHEMA,
        ClassificationCoverageDecisionV1,
        manifest.coverage_count,
        manifest.coverage_sha256,
        manifest.coverage_logical_fingerprint,
        lambda item: str(item.instrument_id),
    )
    memberships = _read_records(
        partition / MEMBERSHIPS_FILE,
        MEMBERSHIP_SCHEMA,
        ClassificationMembershipV1,
        manifest.membership_count,
        manifest.memberships_sha256,
        manifest.memberships_logical_fingerprint,
        lambda item: (
            str(item.instrument_id),
            str(item.classification_id),
            item.valid_from,
        ),
    )
    ordered = _validate_and_order(
        definitions=definitions,
        observations=observations,
        coverage=coverage,
        memberships=memberships,
        as_of_date=manifest.as_of_date,
        methodology_version=manifest.methodology_version,
        providers=manifest.providers,
        permission_review_fingerprints=manifest.permission_review_fingerprints,
    )
    expected = _build_manifest(
        ordered=ordered,
        as_of_date=manifest.as_of_date,
        methodology_version=manifest.methodology_version,
        providers=manifest.providers,
        permission_review_fingerprints=manifest.permission_review_fingerprints,
        created_at=manifest.created_at,
        physical_hashes={
            DEFINITIONS_FILE: manifest.definitions_sha256,
            OBSERVATIONS_FILE: manifest.observations_sha256,
            COVERAGE_FILE: manifest.coverage_sha256,
            MEMBERSHIPS_FILE: manifest.memberships_sha256,
        },
        external_request_count=manifest.external_request_count,
        live_source_accessed=manifest.live_source_accessed,
        production_authorized=manifest.production_authorized,
        historical_research_authorized=manifest.historical_research_authorized,
    )
    if expected != manifest:
        raise ClassificationCorruptionError(
            "classification manifest does not reconcile with rows"
        )
    return CompletedClassificationSnapshot(
        manifest=manifest,
        definitions=definitions,
        observations=observations,
        coverage=coverage,
        memberships=memberships,
    )


def _read_records(
    path: Path,
    schema: pa.Schema,
    model: type[RecordT],
    count: int,
    physical_sha256: str,
    logical_fingerprint: str,
    sort_key: Callable[[RecordT], Any],
) -> tuple[RecordT, ...]:
    if path.is_symlink() or not path.is_file():
        raise ClassificationCorruptionError("classification Parquet file is unavailable")
    if _file_sha256(path) != physical_sha256:
        raise ClassificationCorruptionError("classification Parquet physical hash differs")
    try:
        table = pq.ParquetFile(path).read()
    except (pa.ArrowException, OSError) as exc:
        raise ClassificationCorruptionError("classification Parquet cannot be read") from exc
    if not table.schema.equals(schema, check_metadata=False) or table.num_rows != count:
        raise ClassificationCorruptionError("classification Parquet schema or count differs")
    try:
        records = tuple(model.model_validate(row) for row in table.to_pylist())
    except (ValidationError, ValueError, TypeError) as exc:
        raise ClassificationCorruptionError("classification Parquet row is invalid") from exc
    if records != tuple(sorted(records, key=sort_key)):
        raise ClassificationCorruptionError("classification Parquet ordering differs")
    if classification_fingerprint(records) != logical_fingerprint:
        raise ClassificationCorruptionError("classification Parquet logical hash differs")
    return records


def _validate_table_file(
    path: Path,
    *,
    schema: pa.Schema,
    model: type[RecordT],
    ordered_records: tuple[RecordT, ...],
) -> None:
    try:
        table = pq.ParquetFile(path).read()
        records = tuple(model.model_validate(row) for row in table.to_pylist())
    except (pa.ArrowException, OSError, ValidationError, ValueError, TypeError) as exc:
        raise ClassificationCorruptionError(
            "staged classification Parquet failed reread"
        ) from exc
    if not table.schema.equals(schema, check_metadata=False):
        raise ClassificationCorruptionError("staged classification schema differs")
    if records != ordered_records:
        raise ClassificationCorruptionError("staged classification rows differ")


def _build_manifest(
    *,
    ordered: _OrderedSnapshot,
    as_of_date: date,
    methodology_version: str,
    providers: tuple[str, ...],
    permission_review_fingerprints: tuple[str, ...],
    created_at: datetime,
    physical_hashes: dict[str, str],
    external_request_count: int,
    live_source_accessed: bool,
    production_authorized: bool,
    historical_research_authorized: bool,
) -> ClassificationSnapshotManifestV1:
    summaries = tuple(
        ClassificationCoverageSummaryV1(
            status=status,
            count=sum(item.status is status for item in ordered.coverage),
        )
        for status in sorted(ClassificationCoverageStatus, key=lambda item: item.value)
    )
    current_eligible = sum(
        item.status is ClassificationCoverageStatus.CLASSIFIED
        and item.eligibility_scope
        in {
            ClassificationEligibilityScope.CURRENT_DISPLAY_ONLY,
            ClassificationEligibilityScope.HISTORICAL_RESEARCH,
        }
        for item in ordered.coverage
    )
    historical_eligible = sum(
        item.status is ClassificationCoverageStatus.CLASSIFIED
        and item.eligibility_scope is ClassificationEligibilityScope.HISTORICAL_RESEARCH
        for item in ordered.coverage
    )
    payload = {
        "contract_version": "classification-snapshot/1.0",
        "dataset_name": "classification-snapshot",
        "completion_status": "completed",
        "as_of_date": as_of_date,
        "methodology_version": methodology_version,
        "providers": providers,
        "permission_review_fingerprints": permission_review_fingerprints,
        "created_at": created_at,
        "definitions_file": DEFINITIONS_FILE,
        "observations_file": OBSERVATIONS_FILE,
        "coverage_file": COVERAGE_FILE,
        "memberships_file": MEMBERSHIPS_FILE,
        "definition_count": len(ordered.definitions),
        "observation_count": len(ordered.observations),
        "coverage_count": len(ordered.coverage),
        "membership_count": len(ordered.memberships),
        "coverage_summaries": summaries,
        "current_display_eligible_count": current_eligible,
        "historical_research_eligible_count": historical_eligible,
        "definitions_logical_fingerprint": classification_fingerprint(
            ordered.definitions
        ),
        "observations_logical_fingerprint": classification_fingerprint(
            ordered.observations
        ),
        "coverage_logical_fingerprint": classification_fingerprint(ordered.coverage),
        "memberships_logical_fingerprint": classification_fingerprint(
            ordered.memberships
        ),
        "definitions_sha256": physical_hashes[DEFINITIONS_FILE],
        "observations_sha256": physical_hashes[OBSERVATIONS_FILE],
        "coverage_sha256": physical_hashes[COVERAGE_FILE],
        "memberships_sha256": physical_hashes[MEMBERSHIPS_FILE],
        "external_request_count": external_request_count,
        "live_source_accessed": live_source_accessed,
        "production_authorized": production_authorized,
        "historical_research_authorized": historical_research_authorized,
    }
    return ClassificationSnapshotManifestV1.model_validate(
        {**payload, "logical_fingerprint": classification_fingerprint(payload)}
    )


def _snapshot_identity(
    *,
    ordered: _OrderedSnapshot,
    as_of_date: date,
    methodology_version: str,
    providers: tuple[str, ...],
    permission_review_fingerprints: tuple[str, ...],
    external_request_count: int,
    live_source_accessed: bool,
    production_authorized: bool,
    historical_research_authorized: bool,
) -> dict[str, Any]:
    return {
        "as_of_date": as_of_date,
        "methodology_version": methodology_version,
        "providers": providers,
        "permission_review_fingerprints": permission_review_fingerprints,
        "definitions": classification_fingerprint(ordered.definitions),
        "observations": classification_fingerprint(ordered.observations),
        "coverage": classification_fingerprint(ordered.coverage),
        "memberships": classification_fingerprint(ordered.memberships),
        "external_request_count": external_request_count,
        "live_source_accessed": live_source_accessed,
        "production_authorized": production_authorized,
        "historical_research_authorized": historical_research_authorized,
    }


def _completed_identity(completed: CompletedClassificationSnapshot) -> dict[str, Any]:
    manifest = completed.manifest
    ordered = _OrderedSnapshot(
        completed.definitions,
        completed.observations,
        completed.coverage,
        completed.memberships,
    )
    return _snapshot_identity(
        ordered=ordered,
        as_of_date=manifest.as_of_date,
        methodology_version=manifest.methodology_version,
        providers=manifest.providers,
        permission_review_fingerprints=manifest.permission_review_fingerprints,
        external_request_count=manifest.external_request_count,
        live_source_accessed=manifest.live_source_accessed,
        production_authorized=manifest.production_authorized,
        historical_research_authorized=manifest.historical_research_authorized,
    )


def _records_to_table(records: tuple[BaseModel, ...], schema: pa.Schema) -> pa.Table:
    try:
        return pa.Table.from_pylist(
            [_arrow_value(record.model_dump(mode="python")) for record in records],
            schema=schema,
        )
    except (pa.ArrowException, OverflowError, ValueError) as exc:
        raise ClassificationPersistenceError(
            "classification record cannot be represented by Arrow schema"
        ) from exc


def _arrow_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _arrow_value(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {key: _arrow_value(item) for key, item in value.items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, tuple):
        return [_arrow_value(item) for item in value]
    return value


def _model_for_file(file_name: str) -> type[BaseModel]:
    return {
        DEFINITIONS_FILE: ClassificationDefinitionV1,
        OBSERVATIONS_FILE: ClassificationSourceObservationV1,
        COVERAGE_FILE: ClassificationCoverageDecisionV1,
        MEMBERSHIPS_FILE: ClassificationMembershipV1,
    }[file_name]


def _interval_contains(
    outer_from: date,
    outer_to: date | None,
    inner_from: date,
    inner_to: date | None,
) -> bool:
    if inner_from < outer_from:
        return False
    if outer_to is None:
        return True
    return inner_to is not None and inner_to <= outer_to


def _scope_rank(scope: ClassificationEligibilityScope) -> int:
    return {
        ClassificationEligibilityScope.INELIGIBLE: 0,
        ClassificationEligibilityScope.CURRENT_DISPLAY_ONLY: 1,
        ClassificationEligibilityScope.HISTORICAL_RESEARCH: 2,
    }[scope]


def _reject_duplicate(values: Any, name: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ClassificationConflictError(f"duplicate {name}")


def _snapshot_path(root: Path, as_of_date: date, methodology_version: str) -> Path:
    return (
        root
        / SNAPSHOT_DIRECTORY
        / f"schema_version={SCHEMA_PARTITION}"
        / f"as_of_date={as_of_date.isoformat()}"
        / f"methodology_version={_safe_segment(methodology_version)}"
    )


def _safe_segment(value: str) -> str:
    if not isinstance(value, str):
        raise ClassificationPersistenceError("classification path segment must be text")
    normalized = value.strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if (
        not normalized
        or normalized in {".", ".."}
        or any(character not in allowed for character in normalized)
    ):
        raise ClassificationPersistenceError("classification path segment is unsafe")
    return normalized


def _prepare_root(root: Path) -> Path:
    if root.exists() and (not root.is_dir() or root.is_symlink()):
        raise ClassificationPersistenceError(
            "classification root must be a non-symlink directory"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root.absolute()


def _require_root(root: Path) -> Path:
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ClassificationPersistenceError("classification root is unavailable")
    return root.absolute()


def _require_within_root(root: Path, path: Path) -> None:
    if root == path or root not in path.parents:
        raise ClassificationPersistenceError("classification path escapes root")
    _reject_existing_symlinks(root, path)


def _reject_existing_symlinks(root: Path, path: Path) -> None:
    current = path
    while current != root:
        if current.exists() and current.is_symlink():
            raise ClassificationPersistenceError(
                "classification path contains a symlink"
            )
        if root not in current.parents:
            raise ClassificationPersistenceError("classification path escapes root")
        current = current.parent


def _write_result(
    manifest: ClassificationSnapshotManifestV1,
    partition: Path,
    status: str,
) -> ClassificationSnapshotWriteResult:
    return ClassificationSnapshotWriteResult(
        partition_path=partition,
        manifest_path=partition / MANIFEST_FILE,
        logical_fingerprint=manifest.logical_fingerprint,
        definition_count=manifest.definition_count,
        observation_count=manifest.observation_count,
        coverage_count=manifest.coverage_count,
        membership_count=manifest.membership_count,
        status=status,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    _fsync_file(temporary)
    temporary.replace(path)
    _fsync_file(path)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
