"""Normalize every in-range SEC Company Facts occurrence into Parquet."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import stat
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal, Protocol

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_payload_census import (
    SecCompanyfactsPayloadCensusV1,
    read_sealed_sec_companyfacts_payload_census,
)
from tip_api.providers.sec.companyfacts_source import (
    ARCHIVE_FILE,
    SecCompanyfactsSourceManifestV1,
    read_sec_companyfacts_source_package,
)
from tip_api.providers.sec.filing_clock_ledger import (
    MANIFEST_FILE as FILING_CLOCK_MANIFEST_FILE,
    PARQUET_FILE as FILING_CLOCK_PARQUET_FILE,
    SecFilingClockLedgerManifestV1,
    read_sec_filing_clock_package,
)


CONTRACT_VERSION = "sec-companyfacts-normalized-source/1.0"
MANIFEST_FILE = "manifest.json"
ENTITY_FILE = "entities.parquet"
CONCEPT_FILE = "concepts.parquet"
OCCURRENCE_FILE_TEMPLATE = "occurrences-filed-year={year}.parquet"
MAXIMUM_WORKERS = 16
FACT_BUFFER_ROWS = 25_000
MAXIMUM_MANIFEST_BYTES = 4 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_CIK_MEMBER = re.compile(r"CIK(?P<cik>[0-9]{10})\.json\Z")
_ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")


ENTITY_ARROW_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("source_member_name", pa.string(), nullable=False),
        pa.field("entity_name", pa.string(), nullable=False),
    ]
)

CONCEPT_ARROW_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("concept_key", pa.string(), nullable=False),
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("source_member_name", pa.string(), nullable=False),
        pa.field("namespace", pa.string(), nullable=False),
        pa.field("concept_name", pa.string(), nullable=False),
        pa.field("label", pa.string(), nullable=True),
        pa.field("description", pa.string(), nullable=True),
    ]
)

OCCURRENCE_ARROW_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("source_occurrence_id", pa.string(), nullable=False),
        pa.field("raw_fact_fingerprint", pa.string(), nullable=False),
        pa.field("companyfacts_cik", pa.string(), nullable=False),
        pa.field("source_member_name", pa.string(), nullable=False),
        pa.field("concept_key", pa.string(), nullable=False),
        pa.field("namespace", pa.string(), nullable=False),
        pa.field("concept_name", pa.string(), nullable=False),
        pa.field("unit", pa.string(), nullable=False),
        pa.field("unit_occurrence_ordinal", pa.int32(), nullable=False),
        pa.field("start_raw", pa.string(), nullable=True),
        pa.field("start_date", pa.date32(), nullable=True),
        pa.field("end_raw", pa.string(), nullable=True),
        pa.field("end_date", pa.date32(), nullable=True),
        pa.field("value_kind", pa.string(), nullable=False),
        pa.field("value_text", pa.string(), nullable=True),
        pa.field("accession_number", pa.string(), nullable=False),
        pa.field("fiscal_year_raw", pa.string(), nullable=True),
        pa.field("fiscal_year", pa.int32(), nullable=True),
        pa.field("fiscal_period", pa.string(), nullable=True),
        pa.field("form", pa.string(), nullable=False),
        pa.field("filed_date", pa.date32(), nullable=False),
        pa.field("frame", pa.string(), nullable=True),
        pa.field("filing_clock_admission_status", pa.string(), nullable=False),
        pa.field(
            "source_available_at_utc",
            pa.timestamp("ms", tz="UTC"),
            nullable=True,
        ),
        pa.field("signal_eligible_session", pa.date32(), nullable=True),
        pa.field("clock_reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("normalization_status", pa.string(), nullable=False),
        pa.field("normalization_reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("instrument_resolution_status", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=True),
    ]
)


class SecCompanyfactsNormalizedSourceError(RuntimeError):
    """Raised when normalized Company Facts custody cannot be proven."""


class _Digest(Protocol):
    def update(self, value: bytes) -> None: ...

    def hexdigest(self) -> str: ...


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NormalizedArtifactV1(_FrozenModel):
    artifact_kind: Literal["entity", "concept", "occurrence"]
    worker_index: int = Field(ge=0, lt=MAXIMUM_WORKERS)
    filed_year: int | None = Field(default=None, ge=1900, le=2200)
    relative_path: str
    row_count: int = Field(ge=1)
    byte_size: int = Field(ge=1)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    schema_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def artifact_identity_reconciles(self) -> "NormalizedArtifactV1":
        worker = f"worker={self.worker_index:02d}"
        expected_file = (
            ENTITY_FILE
            if self.artifact_kind == "entity"
            else CONCEPT_FILE
            if self.artifact_kind == "concept"
            else OCCURRENCE_FILE_TEMPLATE.format(year=self.filed_year)
        )
        if self.artifact_kind == "occurrence" and self.filed_year is None:
            raise ValueError("occurrence artifact lacks filed year")
        if self.artifact_kind != "occurrence" and self.filed_year is not None:
            raise ValueError("catalog artifact has filed year")
        if self.relative_path != f"{worker}/{expected_file}":
            raise ValueError("normalized artifact path differs")
        return self


class WorkerMemberPartitionV1(_FrozenModel):
    worker_index: int = Field(ge=0, lt=MAXIMUM_WORKERS)
    member_count: int = Field(ge=1)
    member_name_fingerprint: str = Field(pattern=_SHA256_PATTERN)


class SecCompanyfactsNormalizedSourceManifestV1(_FrozenModel):
    contract_version: Literal[
        "sec-companyfacts-normalized-source/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    built_at: datetime
    range_start: date
    range_end: date
    companyfacts_snapshot_date: date
    companyfacts_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    companyfacts_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    companyfacts_payload_census_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    companyfacts_payload_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    filing_clock_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    filing_clock_manifest_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    filing_clock_content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    worker_count: int = Field(ge=1, le=MAXIMUM_WORKERS)
    worker_partitions: tuple[WorkerMemberPartitionV1, ...]
    artifacts: tuple[NormalizedArtifactV1, ...]
    entity_count: int = Field(ge=1)
    concept_count: int = Field(ge=1)
    occurrence_count: int = Field(ge=1)
    clock_admitted_occurrence_count: int = Field(ge=0)
    clock_quarantined_occurrence_count: int = Field(ge=0)
    normalization_admitted_occurrence_count: int = Field(ge=0)
    normalization_quarantined_occurrence_count: int = Field(ge=0)
    invalid_normalized_field_occurrence_count: int = Field(ge=0)
    value_kind_counts: tuple[tuple[str, int], ...]
    namespace_occurrence_counts: tuple[tuple[str, int], ...]
    form_occurrence_counts: tuple[tuple[str, int], ...]
    filed_year_occurrence_counts: tuple[tuple[str, int], ...]
    entity_schema_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    concept_schema_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    occurrence_schema_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    stable_instrument_resolution_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("built_at")
    @classmethod
    def built_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "SecCompanyfactsNormalizedSourceManifestV1":
        if self.range_end < self.range_start:
            raise ValueError("normalized Company Facts range is reversed")
        if len(self.worker_partitions) != self.worker_count:
            raise ValueError("normalized worker partition count differs")
        if tuple(item.worker_index for item in self.worker_partitions) != tuple(
            range(self.worker_count)
        ):
            raise ValueError("normalized worker partition order differs")
        if self.artifacts != tuple(
            sorted(self.artifacts, key=lambda item: item.relative_path)
        ):
            raise ValueError("normalized artifacts are unordered")
        if len({item.relative_path for item in self.artifacts}) != len(self.artifacts):
            raise ValueError("normalized artifact path is duplicated")
        artifact_entity_count = sum(
            item.row_count for item in self.artifacts if item.artifact_kind == "entity"
        )
        artifact_concept_count = sum(
            item.row_count for item in self.artifacts if item.artifact_kind == "concept"
        )
        artifact_occurrence_count = sum(
            item.row_count
            for item in self.artifacts
            if item.artifact_kind == "occurrence"
        )
        if (artifact_entity_count, artifact_concept_count, artifact_occurrence_count) != (
            self.entity_count,
            self.concept_count,
            self.occurrence_count,
        ):
            raise ValueError("normalized artifact row counts differ")
        if (
            self.clock_admitted_occurrence_count
            + self.clock_quarantined_occurrence_count
            != self.occurrence_count
        ):
            raise ValueError("normalized clock counts differ")
        if (
            self.normalization_admitted_occurrence_count
            + self.normalization_quarantined_occurrence_count
            != self.occurrence_count
        ):
            raise ValueError("normalized occurrence states differ")
        for counts in (
            self.value_kind_counts,
            self.namespace_occurrence_counts,
            self.form_occurrence_counts,
            self.filed_year_occurrence_counts,
        ):
            if counts != tuple(sorted(counts)) or sum(value for _, value in counts) != self.occurrence_count:
                raise ValueError("normalized ordered counts differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("normalized manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecCompanyfactsNormalizedSourceResult:
    package_path: Path
    manifest: SecCompanyfactsNormalizedSourceManifestV1


@dataclass(frozen=True, slots=True)
class _Clock:
    admission_status: str
    source_available_at: datetime | None
    signal_eligible_session: date | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _WorkerResult:
    worker_index: int
    member_count: int
    member_name_fingerprint: str
    populated_count: int
    empty_object_count: int
    empty_facts_count: int
    quarantined_member_count: int
    entity_count: int
    concept_count: int
    occurrence_count: int
    clock_admitted_count: int
    clock_quarantined_count: int
    normalization_admitted_count: int
    normalization_quarantined_count: int
    invalid_normalized_field_count: int
    value_kinds: Counter[str]
    namespaces: Counter[str]
    forms: Counter[str]
    filed_years: Counter[str]
    artifacts: tuple[NormalizedArtifactV1, ...]


def build_sec_companyfacts_normalized_source(
    *,
    companyfacts_package_path: Path,
    companyfacts_custody_root: Path,
    companyfacts_census_root: Path,
    filing_clock_package_path: Path,
    output_package_path: Path,
    range_start: date,
    range_end: date,
    worker_count: int,
    implementation_revision: str,
    built_at: datetime | None = None,
) -> SecCompanyfactsNormalizedSourceResult:
    """Build one immutable, source-normalized Company Facts package."""

    if range_end < range_start:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts range is reversed"
        )
    if worker_count < 1 or worker_count > MAXIMUM_WORKERS:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts worker count is invalid"
        )
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts revision is invalid"
        )
    target, partial = _validate_output_target(output_package_path)
    source = read_sec_companyfacts_source_package(
        package_path=companyfacts_package_path,
        approved_custody_root=companyfacts_custody_root,
    )
    census = read_sealed_sec_companyfacts_payload_census(
        output_root=companyfacts_census_root,
        source_snapshot_date=source.remote.last_modified.date(),
        range_start=range_start,
        range_end=range_end,
    )
    _validate_source_census_binding(source, census)
    clock_result = read_sec_filing_clock_package(
        package_path=filing_clock_package_path
    )
    clock_manifest = clock_result.manifest
    if clock_manifest.range_start != range_start or clock_manifest.range_end != range_end:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts clock range differs"
        )
    if (
        clock_manifest.companyfacts_source_fingerprint != source.logical_fingerprint
        or clock_manifest.companyfacts_payload_census_fingerprint
        != census.logical_fingerprint
    ):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts clock lineage differs"
        )
    clocks = _read_filing_clocks(filing_clock_package_path, clock_manifest)
    archive_path = companyfacts_package_path / ARCHIVE_FILE
    with zipfile.ZipFile(archive_path) as archive:
        names = tuple(sorted(item.filename for item in archive.infolist()))
    if len(names) != source.member_count or _fingerprint(names) != source.member_name_fingerprint:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts member binding differs"
        )
    partitions = tuple(names[index::worker_count] for index in range(worker_count))
    if any(not partition for partition in partitions):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts worker partition is empty"
        )
    os.mkdir(partial, mode=0o700)
    arguments = tuple(
        (
            str(archive_path),
            partition,
            str(partial),
            index,
            range_start,
            range_end,
            clocks,
        )
        for index, partition in enumerate(partitions)
    )
    if worker_count == 1:
        results = tuple(_normalize_worker(argument) for argument in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            results = tuple(executor.map(_normalize_worker, arguments))
    ordered_results = tuple(sorted(results, key=lambda item: item.worker_index))
    _validate_worker_results(
        results=ordered_results,
        partitions=partitions,
        census=census,
    )
    artifacts = tuple(
        sorted(
            (artifact for result in ordered_results for artifact in result.artifacts),
            key=lambda item: item.relative_path,
        )
    )
    manifest = _build_manifest(
        source=source,
        census=census,
        source_manifest_sha256=_sha256_file(companyfacts_package_path / "package.json"),
        census_sha256=_sha256_file(
            _census_path(
                companyfacts_census_root,
                source.remote.last_modified.date(),
                range_start,
                range_end,
            )
        ),
        filing_clock_package_path=filing_clock_package_path,
        clock_manifest=clock_manifest,
        results=ordered_results,
        artifacts=artifacts,
        implementation_revision=implementation_revision,
        built_at=normalize_utc_datetime(built_at or datetime.now(UTC)),
        range_start=range_start,
        range_end=range_end,
        worker_count=worker_count,
    )
    _write_exclusive_json(partial / MANIFEST_FILE, manifest.model_dump(mode="json"))
    _fsync_directory(partial)
    os.rename(partial, target)
    _fsync_directory(target.parent)
    return read_sec_companyfacts_normalized_source(package_path=target)


def read_sec_companyfacts_normalized_source(
    *,
    package_path: Path,
    occurrence_concept_filter: frozenset[str] | None = None,
    occurrence_batch_consumer: Callable[
        [NormalizedArtifactV1, pa.RecordBatch], None
    ] | None = None,
) -> SecCompanyfactsNormalizedSourceResult:
    """Formally reread every normalized artifact and aggregate invariant."""

    if (occurrence_concept_filter is None) != (occurrence_batch_consumer is None):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts occurrence filter is incomplete"
        )
    if occurrence_concept_filter is not None and not occurrence_concept_filter:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts occurrence filter is empty"
        )

    package = _validate_completed_package(package_path)
    manifest_path = package / MANIFEST_FILE
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts manifest is unavailable"
        )
    _require_mode(manifest_path, 0o400)
    if manifest_path.stat().st_size > MAXIMUM_MANIFEST_BYTES:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts manifest exceeds byte ceiling"
        )
    try:
        manifest = SecCompanyfactsNormalizedSourceManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts manifest is invalid"
        ) from exc
    expected_workers = {f"worker={index:02d}" for index in range(manifest.worker_count)}
    root_members = {item.name for item in package.iterdir()}
    if root_members != {MANIFEST_FILE, *expected_workers}:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts package members differ"
        )
    expected_by_worker: dict[int, set[str]] = {
        index: set() for index in range(manifest.worker_count)
    }
    for artifact in manifest.artifacts:
        expected_by_worker[artifact.worker_index].add(Path(artifact.relative_path).name)
    counters: dict[str, Counter[str]] = {
        name: Counter()
        for name in ("value_kinds", "namespaces", "forms", "filed_years")
    }
    state_counts: Counter[str] = Counter()
    invalid_field_occurrences = 0
    entity_count = concept_count = occurrence_count = 0
    for index in range(manifest.worker_count):
        worker_path = package / f"worker={index:02d}"
        if worker_path.is_symlink() or not worker_path.is_dir():
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts worker directory is unavailable"
            )
        _require_mode(worker_path, 0o700)
        if {item.name for item in worker_path.iterdir()} != expected_by_worker[index]:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts worker artifacts differ"
            )
    for artifact in manifest.artifacts:
        path = package / artifact.relative_path
        if path.is_symlink() or not path.is_file():
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts artifact is unavailable"
            )
        _require_mode(path, 0o400)
        if path.stat().st_size != artifact.byte_size or _sha256_file(path) != artifact.physical_sha256:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts artifact identity differs"
            )
        parquet = pq.ParquetFile(path)
        expected_schema = _schema_for_kind(artifact.artifact_kind)
        if parquet.schema_arrow != expected_schema:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts Arrow schema differs"
            )
        if _schema_fingerprint(expected_schema) != artifact.schema_fingerprint:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts schema fingerprint differs"
            )
        digest = hashlib.sha256()
        row_count = 0
        last_key: tuple[object, ...] | None = None
        for batch in parquet.iter_batches(batch_size=65_536):
            if (
                artifact.artifact_kind == "occurrence"
                and occurrence_concept_filter is not None
                and occurrence_batch_consumer is not None
            ):
                concept_column = batch.column(
                    batch.schema.get_field_index("concept_name")
                )
                filtered = batch.filter(
                    pc.is_in(
                        concept_column,
                        value_set=pa.array(sorted(occurrence_concept_filter)),
                    )
                )
                if filtered.num_rows:
                    occurrence_batch_consumer(artifact, filtered)
            for row in pa.Table.from_batches([batch]).to_pylist():
                digest.update(_json_bytes(row))
                digest.update(b"\n")
                key = _validate_normalized_row(row, artifact, counters, state_counts)
                if last_key is not None and key <= last_key:
                    raise SecCompanyfactsNormalizedSourceError(
                        "normalized Company Facts row order differs"
                    )
                last_key = key
                if artifact.artifact_kind == "occurrence" and any(
                    reason != "missing_filing_clock"
                    for reason in row["normalization_reason_codes"]
                ):
                    invalid_field_occurrences += 1
                row_count += 1
        if row_count != artifact.row_count or digest.hexdigest() != artifact.logical_fingerprint:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts artifact content differs"
            )
        if artifact.artifact_kind == "entity":
            entity_count += row_count
        elif artifact.artifact_kind == "concept":
            concept_count += row_count
        else:
            occurrence_count += row_count
    observed = {
        "entity_count": entity_count,
        "concept_count": concept_count,
        "occurrence_count": occurrence_count,
        "clock_admitted_occurrence_count": state_counts["clock_admitted"],
        "clock_quarantined_occurrence_count": state_counts["clock_quarantined"],
        "normalization_admitted_occurrence_count": state_counts[
            "normalization_admitted"
        ],
        "normalization_quarantined_occurrence_count": state_counts[
            "normalization_quarantined"
        ],
        "invalid_normalized_field_occurrence_count": invalid_field_occurrences,
        "value_kind_counts": _ordered(counters["value_kinds"]),
        "namespace_occurrence_counts": _ordered(counters["namespaces"]),
        "form_occurrence_counts": _ordered(counters["forms"]),
        "filed_year_occurrence_counts": _ordered(counters["filed_years"]),
    }
    if any(getattr(manifest, key) != value for key, value in observed.items()):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts aggregate counts differ"
        )
    expected_content = _fingerprint(
        tuple(
            (artifact.relative_path, artifact.logical_fingerprint)
            for artifact in manifest.artifacts
        )
    )
    if manifest.content_fingerprint != expected_content:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts content fingerprint differs"
        )
    return SecCompanyfactsNormalizedSourceResult(package_path=package, manifest=manifest)


def _normalize_worker(
    argument: tuple[
        str,
        tuple[str, ...],
        str,
        int,
        date,
        date,
        dict[str, _Clock],
    ]
) -> _WorkerResult:
    archive_name, names, partial_root, worker_index, range_start, range_end, clocks = argument
    worker_path = Path(partial_root) / f"worker={worker_index:02d}"
    os.mkdir(worker_path, mode=0o700)
    entities: list[dict[str, object]] = []
    concepts: list[dict[str, object]] = []
    occurrence_buffers: dict[int, list[dict[str, object]]] = {}
    occurrence_writers: dict[int, pq.ParquetWriter] = {}
    occurrence_digests: dict[int, _Digest] = {}
    occurrence_counts: Counter[int] = Counter()
    counters: dict[str, Counter[str]] = {
        name: Counter()
        for name in ("value_kinds", "namespaces", "forms", "filed_years")
    }
    states: Counter[str] = Counter()
    populated = empty_object = empty_facts = quarantined = 0
    invalid_field_occurrences = 0
    with zipfile.ZipFile(archive_name) as archive:
        for name in names:
            try:
                payload = json.loads(
                    archive.read(name), parse_float=Decimal, parse_int=int
                )
            except Exception as exc:
                raise SecCompanyfactsNormalizedSourceError(
                    "normalized Company Facts member cannot be read"
                ) from exc
            if payload == {}:
                empty_object += 1
                continue
            reason = _member_reason(name, payload)
            if reason is not None:
                quarantined += 1
                continue
            assert isinstance(payload, dict)
            if payload["facts"] == {}:
                empty_facts += 1
                continue
            if _structure_reason(payload) is not None:
                quarantined += 1
                continue
            entity_name = payload.get("entityName")
            if not isinstance(entity_name, str) or not entity_name.strip():
                quarantined += 1
                continue
            populated += 1
            match = _CIK_MEMBER.fullmatch(name)
            assert match is not None
            cik = match.group("cik")
            entities.append(
                {
                    "contract_version": CONTRACT_VERSION,
                    "companyfacts_cik": cik,
                    "source_member_name": name,
                    "entity_name": entity_name.strip(),
                }
            )
            facts = payload["facts"]
            for namespace in sorted(facts):
                namespace_concepts = facts[namespace]
                for concept_name in sorted(namespace_concepts):
                    concept = namespace_concepts[concept_name]
                    concept_key = _fingerprint((cik, namespace, concept_name))
                    concepts.append(
                        {
                            "contract_version": CONTRACT_VERSION,
                            "concept_key": concept_key,
                            "companyfacts_cik": cik,
                            "source_member_name": name,
                            "namespace": namespace,
                            "concept_name": concept_name,
                            "label": _optional_text(concept.get("label")),
                            "description": _optional_text(concept.get("description")),
                        }
                    )
                    for unit in sorted(concept["units"]):
                        values = concept["units"][unit]
                        for ordinal, fact in enumerate(values):
                            if not isinstance(fact, dict):
                                raise SecCompanyfactsNormalizedSourceError(
                                    "normalized Company Facts fact item is invalid"
                                )
                            filed = _optional_date(fact.get("filed"))
                            if filed is None or not range_start <= filed <= range_end:
                                continue
                            row = _normalize_occurrence(
                                name=name,
                                cik=cik,
                                namespace=namespace,
                                concept_name=concept_name,
                                concept_key=concept_key,
                                unit=unit,
                                ordinal=ordinal,
                                fact=fact,
                                filed=filed,
                                clocks=clocks,
                            )
                            year = filed.year
                            occurrence_buffers.setdefault(year, []).append(row)
                            occurrence_counts[year] += 1
                            digest = occurrence_digests.setdefault(
                                year, hashlib.sha256()
                            )
                            digest.update(_json_bytes(row))
                            digest.update(b"\n")
                            counters["value_kinds"][row["value_kind"]] += 1
                            counters["namespaces"][namespace] += 1
                            counters["forms"][row["form"]] += 1
                            counters["filed_years"][str(year)] += 1
                            states[
                                "clock_admitted"
                                if row["filing_clock_admission_status"] == "admitted"
                                else "clock_quarantined"
                            ] += 1
                            states[
                                "normalization_admitted"
                                if row["normalization_status"] == "admitted"
                                else "normalization_quarantined"
                            ] += 1
                            if any(
                                reason != "missing_filing_clock"
                                for reason in row["normalization_reason_codes"]
                            ):
                                invalid_field_occurrences += 1
                            if len(occurrence_buffers[year]) >= FACT_BUFFER_ROWS:
                                _flush_occurrences(
                                    worker_path=worker_path,
                                    year=year,
                                    buffer=occurrence_buffers[year],
                                    writers=occurrence_writers,
                                )
    for year in sorted(occurrence_buffers):
        if occurrence_buffers[year]:
            _flush_occurrences(
                worker_path=worker_path,
                year=year,
                buffer=occurrence_buffers[year],
                writers=occurrence_writers,
            )
    for writer in occurrence_writers.values():
        writer.close()
    artifacts = [
        _write_catalog_artifact(
            worker_path=worker_path,
            worker_index=worker_index,
            kind="entity",
            rows=entities,
            schema=ENTITY_ARROW_SCHEMA,
            file_name=ENTITY_FILE,
        ),
        _write_catalog_artifact(
            worker_path=worker_path,
            worker_index=worker_index,
            kind="concept",
            rows=concepts,
            schema=CONCEPT_ARROW_SCHEMA,
            file_name=CONCEPT_FILE,
        ),
    ]
    for year in sorted(occurrence_counts):
        path = worker_path / OCCURRENCE_FILE_TEMPLATE.format(year=year)
        path.chmod(0o400)
        _fsync_file(path)
        digest = occurrence_digests[year]
        artifacts.append(
            NormalizedArtifactV1(
                artifact_kind="occurrence",
                worker_index=worker_index,
                filed_year=year,
                relative_path=f"worker={worker_index:02d}/{path.name}",
                row_count=occurrence_counts[year],
                byte_size=path.stat().st_size,
                physical_sha256=_sha256_file(path),
                logical_fingerprint=digest.hexdigest(),
                schema_fingerprint=_schema_fingerprint(OCCURRENCE_ARROW_SCHEMA),
            )
        )
    _fsync_directory(worker_path)
    return _WorkerResult(
        worker_index=worker_index,
        member_count=len(names),
        member_name_fingerprint=_fingerprint(names),
        populated_count=populated,
        empty_object_count=empty_object,
        empty_facts_count=empty_facts,
        quarantined_member_count=quarantined,
        entity_count=len(entities),
        concept_count=len(concepts),
        occurrence_count=sum(occurrence_counts.values()),
        clock_admitted_count=states["clock_admitted"],
        clock_quarantined_count=states["clock_quarantined"],
        normalization_admitted_count=states["normalization_admitted"],
        normalization_quarantined_count=states["normalization_quarantined"],
        invalid_normalized_field_count=invalid_field_occurrences,
        value_kinds=counters["value_kinds"],
        namespaces=counters["namespaces"],
        forms=counters["forms"],
        filed_years=counters["filed_years"],
        artifacts=tuple(sorted(artifacts, key=lambda item: item.relative_path)),
    )


def _normalize_occurrence(
    *,
    name: str,
    cik: str,
    namespace: str,
    concept_name: str,
    concept_key: str,
    unit: str,
    ordinal: int,
    fact: dict[str, object],
    filed: date,
    clocks: dict[str, _Clock],
) -> dict[str, object]:
    reasons: set[str] = set()
    accession_value = fact.get("accn")
    if not isinstance(accession_value, str) or _ACCESSION.fullmatch(accession_value) is None:
        raise SecCompanyfactsNormalizedSourceError(
            "in-range normalized Company Facts accession is invalid"
        )
    clock = clocks.get(accession_value)
    if clock is None:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts accession is absent from clock ledger"
        )
    form = _optional_text(fact.get("form"))
    if form is None:
        reasons.add("form_invalid_or_missing")
        form = ""
    start_raw, start_date = _date_fields(fact.get("start"), "start", reasons)
    end_raw, end_date = _date_fields(
        fact.get("end"), "end", reasons, required=True
    )
    value_kind, value_text = _numeric_value(fact.get("val"), reasons)
    fiscal_year_raw, fiscal_year = _fiscal_year(fact.get("fy"), reasons)
    fiscal_period = _optional_text(fact.get("fp"))
    frame = _optional_text(fact.get("frame"))
    normalization_reasons = set(reasons)
    if clock.admission_status != "admitted":
        normalization_reasons.add("missing_filing_clock")
    occurrence_id = _fingerprint(
        (name, namespace, concept_name, unit, ordinal)
    )
    return {
        "contract_version": CONTRACT_VERSION,
        "source_occurrence_id": occurrence_id,
        "raw_fact_fingerprint": _fingerprint(fact),
        "companyfacts_cik": cik,
        "source_member_name": name,
        "concept_key": concept_key,
        "namespace": namespace,
        "concept_name": concept_name,
        "unit": unit,
        "unit_occurrence_ordinal": ordinal,
        "start_raw": start_raw,
        "start_date": start_date,
        "end_raw": end_raw,
        "end_date": end_date,
        "value_kind": value_kind,
        "value_text": value_text,
        "accession_number": accession_value,
        "fiscal_year_raw": fiscal_year_raw,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "form": form,
        "filed_date": filed,
        "frame": frame,
        "filing_clock_admission_status": clock.admission_status,
        "source_available_at_utc": clock.source_available_at,
        "signal_eligible_session": clock.signal_eligible_session,
        "clock_reason_codes": list(clock.reason_codes),
        "normalization_status": (
            "admitted" if not normalization_reasons else "quarantined"
        ),
        "normalization_reason_codes": sorted(normalization_reasons),
        "instrument_resolution_status": "unresolved",
        "instrument_id": None,
    }


def _flush_occurrences(
    *,
    worker_path: Path,
    year: int,
    buffer: list[dict[str, object]],
    writers: dict[int, pq.ParquetWriter],
) -> None:
    table = pa.Table.from_pylist(buffer, schema=OCCURRENCE_ARROW_SCHEMA)
    writer = writers.get(year)
    if writer is None:
        path = worker_path / OCCURRENCE_FILE_TEMPLATE.format(year=year)
        writer = pq.ParquetWriter(
            path,
            OCCURRENCE_ARROW_SCHEMA,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        writers[year] = writer
    writer.write_table(table)
    buffer.clear()


def _write_catalog_artifact(
    *,
    worker_path: Path,
    worker_index: int,
    kind: Literal["entity", "concept"],
    rows: list[dict[str, object]],
    schema: pa.Schema,
    file_name: str,
) -> NormalizedArtifactV1:
    if not rows:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts worker catalog is empty"
        )
    path = worker_path / file_name
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    path.chmod(0o400)
    _fsync_file(path)
    return NormalizedArtifactV1(
        artifact_kind=kind,
        worker_index=worker_index,
        relative_path=f"worker={worker_index:02d}/{file_name}",
        row_count=table.num_rows,
        byte_size=path.stat().st_size,
        physical_sha256=_sha256_file(path),
        logical_fingerprint=_rows_fingerprint(rows),
        schema_fingerprint=_schema_fingerprint(schema),
    )


def _read_filing_clocks(
    package_path: Path,
    manifest: SecFilingClockLedgerManifestV1,
) -> dict[str, _Clock]:
    table = pq.ParquetFile(package_path / FILING_CLOCK_PARQUET_FILE).read()
    if table.num_rows != manifest.record_count:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts clock row count differs"
        )
    result: dict[str, _Clock] = {}
    for row in table.to_pylist():
        accession = row["accession_number"]
        if accession in result:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts clock key is duplicated"
            )
        result[accession] = _Clock(
            admission_status=row["admission_status"],
            source_available_at=row["selected_source_available_at_utc"],
            signal_eligible_session=row["signal_eligible_session"],
            reason_codes=tuple(row["reason_codes"]),
        )
    return result


def _validate_source_census_binding(
    source: SecCompanyfactsSourceManifestV1,
    census: SecCompanyfactsPayloadCensusV1,
) -> None:
    if (
        census.source_snapshot_date != source.remote.last_modified.date()
        or census.source_logical_fingerprint != source.logical_fingerprint
        or census.source_archive_sha256 != source.archive_sha256
        or census.source_member_name_fingerprint != source.member_name_fingerprint
        or census.source_member_count != source.member_count
    ):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts source/census binding differs"
        )


def _validate_worker_results(
    *,
    results: tuple[_WorkerResult, ...],
    partitions: tuple[tuple[str, ...], ...],
    census: SecCompanyfactsPayloadCensusV1,
) -> None:
    if tuple(item.worker_index for item in results) != tuple(range(len(results))):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts worker order differs"
        )
    for index, result in enumerate(results):
        if (
            result.member_count != len(partitions[index])
            or result.member_name_fingerprint != _fingerprint(partitions[index])
        ):
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts worker member binding differs"
            )
    if (
        sum(item.populated_count for item in results) != census.populated_member_count
        or sum(item.empty_object_count for item in results)
        != census.empty_object_member_count
        or sum(item.empty_facts_count for item in results)
        != census.empty_facts_member_count
        or sum(item.quarantined_member_count for item in results)
        != census.quarantined_member_count
        or sum(item.entity_count for item in results) != census.populated_member_count
        or sum(item.concept_count for item in results)
        != sum(item.concept_count for item in census.namespace_counts)
        or sum(item.occurrence_count for item in results)
        != census.fact_filed_in_range_count
    ):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts census reproduction differs"
        )
    forms = sum((item.forms for item in results), Counter())
    if _ordered(forms) != census.in_range_form_counts:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts form census differs"
        )


def _build_manifest(
    *,
    source: SecCompanyfactsSourceManifestV1,
    census: SecCompanyfactsPayloadCensusV1,
    source_manifest_sha256: str,
    census_sha256: str,
    filing_clock_package_path: Path,
    clock_manifest: SecFilingClockLedgerManifestV1,
    results: tuple[_WorkerResult, ...],
    artifacts: tuple[NormalizedArtifactV1, ...],
    implementation_revision: str,
    built_at: datetime,
    range_start: date,
    range_end: date,
    worker_count: int,
) -> SecCompanyfactsNormalizedSourceManifestV1:
    counters = {
        name: sum((getattr(item, name) for item in results), Counter())
        for name in ("value_kinds", "namespaces", "forms", "filed_years")
    }
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": "sec_edgar",
        "implementation_revision": implementation_revision,
        "built_at": built_at,
        "range_start": range_start,
        "range_end": range_end,
        "companyfacts_snapshot_date": source.remote.last_modified.date(),
        "companyfacts_source_fingerprint": source.logical_fingerprint,
        "companyfacts_source_manifest_sha256": source_manifest_sha256,
        "companyfacts_payload_census_fingerprint": census.logical_fingerprint,
        "companyfacts_payload_census_sha256": census_sha256,
        "filing_clock_manifest_sha256": _sha256_file(
            filing_clock_package_path / FILING_CLOCK_MANIFEST_FILE
        ),
        "filing_clock_manifest_fingerprint": clock_manifest.logical_fingerprint,
        "filing_clock_content_fingerprint": clock_manifest.content_fingerprint,
        "worker_count": worker_count,
        "worker_partitions": tuple(
            WorkerMemberPartitionV1(
                worker_index=item.worker_index,
                member_count=item.member_count,
                member_name_fingerprint=item.member_name_fingerprint,
            )
            for item in results
        ),
        "artifacts": artifacts,
        "entity_count": sum(item.entity_count for item in results),
        "concept_count": sum(item.concept_count for item in results),
        "occurrence_count": sum(item.occurrence_count for item in results),
        "clock_admitted_occurrence_count": sum(
            item.clock_admitted_count for item in results
        ),
        "clock_quarantined_occurrence_count": sum(
            item.clock_quarantined_count for item in results
        ),
        "normalization_admitted_occurrence_count": sum(
            item.normalization_admitted_count for item in results
        ),
        "normalization_quarantined_occurrence_count": sum(
            item.normalization_quarantined_count for item in results
        ),
        "invalid_normalized_field_occurrence_count": sum(
            item.invalid_normalized_field_count for item in results
        ),
        "value_kind_counts": _ordered(counters["value_kinds"]),
        "namespace_occurrence_counts": _ordered(counters["namespaces"]),
        "form_occurrence_counts": _ordered(counters["forms"]),
        "filed_year_occurrence_counts": _ordered(counters["filed_years"]),
        "entity_schema_fingerprint": _schema_fingerprint(ENTITY_ARROW_SCHEMA),
        "concept_schema_fingerprint": _schema_fingerprint(CONCEPT_ARROW_SCHEMA),
        "occurrence_schema_fingerprint": _schema_fingerprint(
            OCCURRENCE_ARROW_SCHEMA
        ),
        "content_fingerprint": _fingerprint(
            tuple(
                (artifact.relative_path, artifact.logical_fingerprint)
                for artifact in artifacts
            )
        ),
        "stable_instrument_resolution_count": 0,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return SecCompanyfactsNormalizedSourceManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _validate_normalized_row(
    row: dict[str, object],
    artifact: NormalizedArtifactV1,
    counters: dict[str, Counter[str]],
    states: Counter[str],
) -> tuple[object, ...]:
    if row["contract_version"] != CONTRACT_VERSION:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts row version differs"
        )
    if artifact.artifact_kind == "entity":
        match = _CIK_MEMBER.fullmatch(row["source_member_name"])
        if match is None or row["companyfacts_cik"] != match.group("cik") or not row[
            "entity_name"
        ]:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts entity row differs"
            )
        return (row["source_member_name"],)
    if artifact.artifact_kind == "concept":
        match = _CIK_MEMBER.fullmatch(row["source_member_name"])
        if match is None or row["companyfacts_cik"] != match.group("cik"):
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts concept CIK differs"
            )
        expected = _fingerprint(
            (row["companyfacts_cik"], row["namespace"], row["concept_name"])
        )
        if row["concept_key"] != expected:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts concept key differs"
            )
        return (
            row["source_member_name"],
            row["namespace"],
            row["concept_name"],
        )
    if row["filed_date"].year != artifact.filed_year:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts filed-year partition differs"
        )
    match = _CIK_MEMBER.fullmatch(row["source_member_name"])
    if match is None or row["companyfacts_cik"] != match.group("cik"):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts occurrence CIK differs"
        )
    expected_occurrence = _fingerprint(
        (
            row["source_member_name"],
            row["namespace"],
            row["concept_name"],
            row["unit"],
            row["unit_occurrence_ordinal"],
        )
    )
    if row["source_occurrence_id"] != expected_occurrence:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts occurrence key differs"
        )
    if row["concept_key"] != _fingerprint(
        (row["companyfacts_cik"], row["namespace"], row["concept_name"])
    ):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts occurrence concept differs"
        )
    for key in ("clock_reason_codes", "normalization_reason_codes"):
        if row[key] != sorted(set(row[key])):
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts reason order differs"
            )
    if row["instrument_resolution_status"] != "unresolved" or row["instrument_id"] is not None:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts instrument boundary differs"
        )
    if row["filing_clock_admission_status"] == "admitted":
        if row["source_available_at_utc"] is None or row["signal_eligible_session"] is None:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts admitted clock is incomplete"
            )
        if "missing_filing_clock" in row["normalization_reason_codes"]:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts admitted clock is quarantined"
            )
        states["clock_admitted"] += 1
    elif row["filing_clock_admission_status"] == "quarantined":
        if row["source_available_at_utc"] is not None or row["signal_eligible_session"] is not None:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts quarantine invents a clock"
            )
        if "missing_filing_clock" not in row["normalization_reason_codes"]:
            raise SecCompanyfactsNormalizedSourceError(
                "normalized Company Facts missing clock is not quarantined"
            )
        states["clock_quarantined"] += 1
    else:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts clock state differs"
        )
    has_reasons = bool(row["normalization_reason_codes"])
    expected_status = "quarantined" if has_reasons else "admitted"
    if row["normalization_status"] != expected_status:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts quality state differs"
        )
    states[f"normalization_{expected_status}"] += 1
    counters["value_kinds"][row["value_kind"]] += 1
    counters["namespaces"][row["namespace"]] += 1
    counters["forms"][row["form"]] += 1
    counters["filed_years"][str(row["filed_date"].year)] += 1
    return (
        row["source_member_name"],
        row["namespace"],
        row["concept_name"],
        row["unit"],
        row["unit_occurrence_ordinal"],
    )


def _member_reason(name: str, payload: object) -> str | None:
    if not isinstance(payload, dict):
        return "root_not_object"
    match = _CIK_MEMBER.fullmatch(name)
    cik = payload.get("cik")
    if match is None or str(cik).zfill(10) != match.group("cik"):
        return "cik_filename_mismatch"
    if not isinstance(payload.get("facts"), dict):
        return "facts_root_invalid"
    return None


def _structure_reason(payload: dict[str, object]) -> str | None:
    facts = payload["facts"]
    assert isinstance(facts, dict)
    for namespace, concepts in facts.items():
        if not isinstance(namespace, str) or not namespace or not isinstance(concepts, dict):
            return "malformed_namespace"
        for concept_name, concept in concepts.items():
            if not isinstance(concept_name, str) or not concept_name:
                return "malformed_concept_name"
            if not isinstance(concept, dict) or not isinstance(concept.get("units"), dict):
                return "malformed_concept"
            for unit, values in concept["units"].items():
                if not isinstance(unit, str) or not unit or not isinstance(values, list):
                    return "malformed_unit"
    return None


def _date_fields(
    value: object,
    field: str,
    reasons: set[str],
    *,
    required: bool = False,
) -> tuple[str | None, date | None]:
    if value is None:
        if required:
            reasons.add(f"{field}_date_invalid")
        return None, None
    raw = value if isinstance(value, str) else _json_text(value)
    parsed = _optional_date(value)
    if parsed is None:
        reasons.add(f"{field}_date_invalid")
    return raw, parsed


def _numeric_value(
    value: object, reasons: set[str]
) -> tuple[str, str | None]:
    if isinstance(value, bool):
        reasons.add("value_not_numeric")
        return "invalid", None
    if isinstance(value, int):
        return "integer", str(value)
    if isinstance(value, Decimal) and value.is_finite():
        return "decimal", format(value, "f")
    reasons.add("value_not_numeric")
    return "invalid", None


def _fiscal_year(
    value: object, reasons: set[str]
) -> tuple[str | None, int | None]:
    if value is None:
        return None, None
    raw = str(value) if isinstance(value, (int, str)) else _json_text(value)
    if isinstance(value, int) and not isinstance(value, bool) and -(2**31) <= value < 2**31:
        return raw, value
    reasons.add("fiscal_year_invalid")
    return raw, None


def _optional_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _schema_for_kind(kind: str) -> pa.Schema:
    if kind == "entity":
        return ENTITY_ARROW_SCHEMA
    if kind == "concept":
        return CONCEPT_ARROW_SCHEMA
    return OCCURRENCE_ARROW_SCHEMA


def _rows_fingerprint(rows: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_json_bytes(row))
        digest.update(b"\n")
    return digest.hexdigest()


def _schema_fingerprint(schema: pa.Schema) -> str:
    return hashlib.sha256(schema.serialize().to_pybytes()).hexdigest()


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


def _census_path(root: Path, snapshot: date, start: date, end: date) -> Path:
    return root / (
        f"census=snapshot-{snapshot.isoformat()}--range-"
        f"{start.isoformat()}--{end.isoformat()}.json"
    )


def _validate_output_target(path: Path) -> tuple[Path, Path]:
    target = path.absolute()
    parent = _validate_owner_directory(target.parent)
    if target.parent != parent or re.fullmatch(r"build=[A-Za-z0-9._-]+", target.name) is None:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts output target is invalid"
        )
    partial = parent / f".{target.name}.partial"
    if os.path.lexists(target) or os.path.lexists(partial):
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts output target already exists"
        )
    return target, partial


def _validate_completed_package(path: Path) -> Path:
    package = path.absolute()
    if package.is_symlink() or not package.is_dir() or package.resolve(strict=True) != package:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts package is unsafe"
        )
    _require_mode(package, 0o700)
    return package


def _validate_owner_directory(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts parent is unsafe"
        )
    _require_mode(root, 0o700)
    return root


def _require_mode(path: Path, mode: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts ownership or mode differs"
        )


def _write_exclusive_json(path: Path, value: object) -> None:
    raw = _json_bytes(value) + b"\n"
    if len(raw) > MAXIMUM_MANIFEST_BYTES:
        raise SecCompanyfactsNormalizedSourceError(
            "normalized Company Facts manifest exceeds byte ceiling"
        )
    descriptor = os.open(
        path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o400
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    path.chmod(0o400)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_text(value: object) -> str:
    return _json_bytes(value).decode("utf-8")


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
