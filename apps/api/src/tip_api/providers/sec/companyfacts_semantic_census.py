"""Stream a normalized SEC Company Facts package into a semantic census."""

from __future__ import annotations

import hashlib
import heapq
import json
import multiprocessing
import os
import re
import stat
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterator, Literal, NamedTuple

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_normalized_source import (
    CONCEPT_ARROW_SCHEMA,
    CONTRACT_VERSION as NORMALIZED_CONTRACT_VERSION,
    ENTITY_ARROW_SCHEMA,
    MANIFEST_FILE as NORMALIZED_MANIFEST_FILE,
    OCCURRENCE_ARROW_SCHEMA,
    NormalizedArtifactV1,
    SecCompanyfactsNormalizedSourceManifestV1,
)
from tip_api.services.sec_filer_security_link_decision import (
    PARQUET_FILE as LINK_PARQUET_FILE,
    read_sec_filer_security_link_package,
)


CONTRACT_VERSION = "sec-companyfacts-semantic-census/1.0"
CENSUS_FILE = "census.json"
MAXIMUM_PROCESSES = 16
MAXIMUM_CENSUS_BYTES = 16 * 1024 * 1024
TOP_STANDARD_CONCEPT_LIMIT = 250
CONFLICT_SAMPLE_LIMIT = 100
_SHA256 = r"^[0-9a-f]{64}$"
_REVISION = r"^[0-9a-f]{40}$"
_STANDARD_ACCOUNTING_NAMESPACES = frozenset({"ifrs-full", "us-gaap"})
_SEC_SPECIALIZED_NAMESPACES = frozenset(
    {"cef", "ecd", "ffd", "fnd", "invest", "oef", "rxp", "spac", "srt", "vip"}
)
_OCCURRENCE_COLUMNS = (
    "contract_version",
    "source_occurrence_id",
    "companyfacts_cik",
    "source_member_name",
    "concept_key",
    "namespace",
    "concept_name",
    "unit",
    "unit_occurrence_ordinal",
    "start_date",
    "end_date",
    "value_kind",
    "value_text",
    "accession_number",
    "form",
    "filed_date",
    "filing_clock_admission_status",
    "source_available_at_utc",
    "normalization_status",
)


class SecCompanyfactsSemanticCensusError(RuntimeError):
    """Raised when the semantic census cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StandardConceptCoverageV1(_FrozenModel):
    rank: int = Field(ge=1, le=TOP_STANDARD_CONCEPT_LIMIT)
    namespace: Literal["ifrs-full", "us-gaap"]
    concept_name: str = Field(min_length=1)
    occurrence_count: int = Field(ge=1)
    admitted_occurrence_count: int = Field(ge=0)
    distinct_filer_count: int = Field(ge=1)
    linked_common_stock_filer_count: int = Field(ge=0)
    instant_occurrence_count: int = Field(ge=0)
    duration_occurrence_count: int = Field(ge=0)
    other_period_occurrence_count: int = Field(ge=0)
    unit_counts: tuple[tuple[str, int], ...]
    form_counts: tuple[tuple[str, int], ...]

    @model_validator(mode="after")
    def coverage_reconciles(self) -> "StandardConceptCoverageV1":
        for counts in (self.unit_counts, self.form_counts):
            if counts != tuple(sorted(counts)) or any(value < 1 for _, value in counts):
                raise ValueError("semantic concept counts differ")
        if sum(value for _, value in self.unit_counts) != self.occurrence_count:
            raise ValueError("semantic concept unit denominator differs")
        if sum(value for _, value in self.form_counts) != self.occurrence_count:
            raise ValueError("semantic concept form denominator differs")
        if (
            self.instant_occurrence_count
            + self.duration_occurrence_count
            + self.other_period_occurrence_count
            != self.occurrence_count
        ):
            raise ValueError("semantic concept period denominator differs")
        if self.admitted_occurrence_count > self.occurrence_count:
            raise ValueError("semantic concept admitted count differs")
        if self.linked_common_stock_filer_count > self.distinct_filer_count:
            raise ValueError("semantic concept linked-filer count differs")
        return self


class SemanticConflictSampleV1(_FrozenModel):
    conflict_class: Literal[
        "within_accession_value_conflict",
        "same_availability_value_conflict",
    ]
    semantic_key_fingerprint: str = Field(pattern=_SHA256)
    companyfacts_cik: str = Field(pattern=r"^[0-9]{10}$")
    namespace: str = Field(min_length=1)
    concept_name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    source_available_at_utc: datetime | None = None
    accession_numbers: tuple[str, ...]
    distinct_value_fingerprints: tuple[str, ...]
    occurrence_count: int = Field(ge=2)

    @field_validator("source_available_at_utc")
    @classmethod
    def source_time_is_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def sample_reconciles(self) -> "SemanticConflictSampleV1":
        if self.accession_numbers != tuple(sorted(set(self.accession_numbers))):
            raise ValueError("semantic conflict accessions differ")
        if len(self.distinct_value_fingerprints) < 2 or self.distinct_value_fingerprints != tuple(
            sorted(set(self.distinct_value_fingerprints))
        ):
            raise ValueError("semantic conflict values differ")
        if self.conflict_class == "within_accession_value_conflict":
            if len(self.accession_numbers) != 1 or self.source_available_at_utc is not None:
                raise ValueError("within-accession conflict scope differs")
        elif self.source_available_at_utc is None or len(self.accession_numbers) < 2:
            raise ValueError("same-availability conflict scope differs")
        return self


class SecCompanyfactsSemanticCensusV1(_FrozenModel):
    contract_version: Literal[
        "sec-companyfacts-semantic-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    implementation_revision: str = Field(pattern=_REVISION)
    evaluated_at: datetime
    range_start: date
    range_end: date
    source_snapshot_date: date
    normalized_manifest_sha256: str = Field(pattern=_SHA256)
    normalized_logical_fingerprint: str = Field(pattern=_SHA256)
    normalized_content_fingerprint: str = Field(pattern=_SHA256)
    normalized_occurrence_schema_fingerprint: str = Field(pattern=_SHA256)
    normalized_artifact_count: int = Field(ge=1)
    source_worker_count: int = Field(ge=1, le=MAXIMUM_PROCESSES)
    process_count: int = Field(ge=1, le=MAXIMUM_PROCESSES)
    link_manifest_sha256: str = Field(pattern=_SHA256)
    link_logical_fingerprint: str = Field(pattern=_SHA256)
    link_population_session: date
    link_population_point_in_time_eligibility: str = Field(min_length=1)
    link_population_source_observed_at: datetime
    link_common_stock_instrument_count: int = Field(ge=1)
    link_admitted_common_stock_instrument_count: int = Field(ge=0)
    link_quarantined_common_stock_instrument_count: int = Field(ge=0)
    link_distinct_common_stock_cik_count: int = Field(ge=1)
    link_cik_with_source_facts_count: int = Field(ge=0)
    link_cik_without_source_facts_count: int = Field(ge=0)
    occurrence_count: int = Field(ge=1)
    distinct_filer_count: int = Field(ge=1)
    admitted_fact_filer_count: int = Field(ge=0)
    observed_concept_key_count: int = Field(ge=1)
    distinct_taxonomy_concept_count: int = Field(ge=1)
    semantic_key_count: int = Field(ge=1)
    accession_semantic_group_count: int = Field(ge=1)
    exact_duplicate_group_count: int = Field(ge=0)
    exact_duplicate_redundant_occurrence_count: int = Field(ge=0)
    within_accession_conflict_group_count: int = Field(ge=0)
    within_accession_conflict_occurrence_count: int = Field(ge=0)
    same_availability_conflict_group_count: int = Field(ge=0)
    revision_eligible_semantic_key_count: int = Field(ge=0)
    revision_quarantined_semantic_key_count: int = Field(ge=0)
    semantic_key_with_later_accession_count: int = Field(ge=0)
    later_accession_revision_count: int = Field(ge=0)
    later_revision_state_count: int = Field(ge=0)
    later_revision_value_change_count: int = Field(ge=0)
    namespace_occurrence_counts: tuple[tuple[str, int], ...]
    unit_occurrence_counts: tuple[tuple[str, int], ...]
    form_occurrence_counts: tuple[tuple[str, int], ...]
    filed_year_occurrence_counts: tuple[tuple[str, int], ...]
    value_kind_occurrence_counts: tuple[tuple[str, int], ...]
    period_shape_occurrence_counts: tuple[tuple[str, int], ...]
    filing_clock_status_counts: tuple[tuple[str, int], ...]
    normalization_status_counts: tuple[tuple[str, int], ...]
    taxonomy_class_occurrence_counts: tuple[tuple[str, int], ...]
    revision_quarantine_reason_counts: tuple[tuple[str, int], ...]
    top_standard_concepts: tuple[StandardConceptCoverageV1, ...]
    conflict_samples: tuple[SemanticConflictSampleV1, ...]
    full_occurrence_scan: Literal[True] = True
    daily_cartesian_panel_created: Literal[False] = False
    registered_feature_count: Literal[0] = 0
    issuer_projection_authorized: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
    membership_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    research_performance_authorized: Literal[False] = False
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("evaluated_at", "link_population_source_observed_at")
    @classmethod
    def datetimes_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def census_reconciles(self) -> "SecCompanyfactsSemanticCensusV1":
        if self.range_end < self.range_start:
            raise ValueError("semantic census range is reversed")
        if self.process_count > self.source_worker_count:
            raise ValueError("semantic census process count exceeds source workers")
        if (
            self.link_admitted_common_stock_instrument_count
            + self.link_quarantined_common_stock_instrument_count
            != self.link_common_stock_instrument_count
        ):
            raise ValueError("semantic census link instrument denominator differs")
        if (
            self.link_cik_with_source_facts_count
            + self.link_cik_without_source_facts_count
            != self.link_distinct_common_stock_cik_count
        ):
            raise ValueError("semantic census linked CIK denominator differs")
        if (
            self.revision_eligible_semantic_key_count
            + self.revision_quarantined_semantic_key_count
            != self.semantic_key_count
        ):
            raise ValueError("semantic census revision denominator differs")
        occurrence_counters = (
            self.namespace_occurrence_counts,
            self.unit_occurrence_counts,
            self.form_occurrence_counts,
            self.filed_year_occurrence_counts,
            self.value_kind_occurrence_counts,
            self.period_shape_occurrence_counts,
            self.filing_clock_status_counts,
            self.normalization_status_counts,
            self.taxonomy_class_occurrence_counts,
        )
        for counts in (*occurrence_counters, self.revision_quarantine_reason_counts):
            if counts != tuple(sorted(counts)) or any(value < 1 for _, value in counts):
                raise ValueError("semantic census ordered counts differ")
        if any(
            sum(value for _, value in counts) != self.occurrence_count
            for counts in occurrence_counters
        ):
            raise ValueError("semantic census occurrence denominator differs")
        expected_ranks = tuple(range(1, len(self.top_standard_concepts) + 1))
        if tuple(item.rank for item in self.top_standard_concepts) != expected_ranks:
            raise ValueError("semantic census concept ranks differ")
        if len(self.top_standard_concepts) > TOP_STANDARD_CONCEPT_LIMIT:
            raise ValueError("semantic census concept limit differs")
        if tuple(
            (
                -item.distinct_filer_count,
                -item.occurrence_count,
                item.namespace,
                item.concept_name,
            )
            for item in self.top_standard_concepts
        ) != tuple(
            sorted(
                (
                    -item.distinct_filer_count,
                    -item.occurrence_count,
                    item.namespace,
                    item.concept_name,
                )
                for item in self.top_standard_concepts
            )
        ):
            raise ValueError("semantic census concept order differs")
        samples = tuple(_sample_sort_key(item) for item in self.conflict_samples)
        if samples != tuple(sorted(samples)):
            raise ValueError("semantic census conflict samples are unordered")
        if any(
            sum(1 for item in self.conflict_samples if item.conflict_class == kind)
            > CONFLICT_SAMPLE_LIMIT
            for kind in (
                "within_accession_value_conflict",
                "same_availability_value_conflict",
            )
        ):
            raise ValueError("semantic census conflict sample limit differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("semantic census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecCompanyfactsSemanticCensusResult:
    package_path: Path
    census: SecCompanyfactsSemanticCensusV1


class _Row(NamedTuple):
    source_member_name: str
    companyfacts_cik: str
    concept_key: str
    namespace: str
    concept_name: str
    unit: str
    ordinal: int
    start_date: date | None
    end_date: date | None
    value_kind: str
    value_text: str | None
    accession_number: str
    form: str
    filed_date: date
    clock_status: str
    source_available_at: datetime | None
    normalization_status: str


@dataclass(slots=True)
class _AccessionState:
    occurrence_count: int = 0
    values: Counter[tuple[str, str | None]] = field(default_factory=Counter)
    source_times: set[datetime] = field(default_factory=set)
    invalid_for_revision: bool = False


@dataclass(slots=True)
class _ConceptAccumulator:
    occurrence_count: int = 0
    admitted_occurrence_count: int = 0
    distinct_filer_count: int = 0
    linked_filer_count: int = 0
    period_counts: Counter[str] = field(default_factory=Counter)
    unit_counts: Counter[str] = field(default_factory=Counter)
    form_counts: Counter[str] = field(default_factory=Counter)

    def merge(self, other: "_ConceptAccumulator") -> None:
        self.occurrence_count += other.occurrence_count
        self.admitted_occurrence_count += other.admitted_occurrence_count
        self.distinct_filer_count += other.distinct_filer_count
        self.linked_filer_count += other.linked_filer_count
        self.period_counts.update(other.period_counts)
        self.unit_counts.update(other.unit_counts)
        self.form_counts.update(other.form_counts)


@dataclass(frozen=True, slots=True)
class _WorkerResult:
    worker_index: int
    occurrence_count: int
    distinct_filer_count: int
    admitted_fact_filer_count: int
    observed_concept_key_count: int
    semantic_key_count: int
    accession_semantic_group_count: int
    exact_duplicate_group_count: int
    exact_duplicate_redundant_occurrence_count: int
    within_accession_conflict_group_count: int
    within_accession_conflict_occurrence_count: int
    same_availability_conflict_group_count: int
    revision_eligible_semantic_key_count: int
    revision_quarantined_semantic_key_count: int
    semantic_key_with_later_accession_count: int
    later_accession_revision_count: int
    later_revision_state_count: int
    later_revision_value_change_count: int
    linked_cik_with_facts_count: int
    counters: dict[str, Counter[str]]
    revision_quarantine_reasons: Counter[str]
    concepts: dict[tuple[str, str], _ConceptAccumulator]
    conflict_samples: tuple[SemanticConflictSampleV1, ...]


@dataclass(frozen=True, slots=True)
class _LinkPopulation:
    manifest_sha256: str
    logical_fingerprint: str
    session: date
    point_in_time_eligibility: str
    source_observed_at: datetime
    common_stock_instrument_count: int
    admitted_common_stock_instrument_count: int
    quarantined_common_stock_instrument_count: int
    ciks: frozenset[str]


def build_sec_companyfacts_semantic_census(
    *,
    normalized_package_path: Path,
    link_package_path: Path,
    data_root: Path,
    output_package_path: Path,
    process_count: int,
    implementation_revision: str,
    evaluated_at: datetime | None = None,
) -> SecCompanyfactsSemanticCensusResult:
    """Build one immutable, source-level semantic census."""

    if re.fullmatch(_REVISION, implementation_revision) is None:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census implementation revision is invalid"
        )
    source, source_manifest_sha256 = _inspect_normalized_source(
        normalized_package_path
    )
    if process_count < 1 or process_count > min(
        MAXIMUM_PROCESSES, source.worker_count
    ):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census process count is invalid"
        )
    link = _read_link_population(
        package_path=link_package_path,
        data_root=data_root,
    )
    target, partial = _validate_output_target(output_package_path)
    os.mkdir(partial, mode=0o700)
    try:
        arguments = tuple(
            (
                str(normalized_package_path.absolute()),
                worker_index,
                tuple(
                    artifact
                    for artifact in source.artifacts
                    if artifact.artifact_kind == "occurrence"
                    and artifact.worker_index == worker_index
                ),
                link.ciks,
            )
            for worker_index in range(source.worker_count)
        )
        if process_count == 1:
            results = tuple(_census_worker(argument) for argument in arguments)
        else:
            with ProcessPoolExecutor(
                max_workers=process_count,
                mp_context=multiprocessing.get_context("spawn"),
            ) as executor:
                results = tuple(executor.map(_census_worker, arguments))
        census = _combine_results(
            results=tuple(sorted(results, key=lambda item: item.worker_index)),
            source=source,
            source_manifest_sha256=source_manifest_sha256,
            link=link,
            process_count=process_count,
            implementation_revision=implementation_revision,
            evaluated_at=normalize_utc_datetime(evaluated_at or datetime.now(UTC)),
        )
        _write_exclusive_json(
            partial / CENSUS_FILE,
            census.model_dump(mode="json"),
        )
        _fsync_directory(partial)
        os.rename(partial, target)
        _fsync_directory(target.parent)
    except Exception:
        raise
    return read_sec_companyfacts_semantic_census(
        package_path=target,
        normalized_package_path=normalized_package_path,
        link_package_path=link_package_path,
        data_root=data_root,
    )


def read_sec_companyfacts_semantic_census(
    *,
    package_path: Path,
    normalized_package_path: Path,
    link_package_path: Path,
    data_root: Path,
) -> SecCompanyfactsSemanticCensusResult:
    """Formally read one census and verify its exact input bindings."""

    package = _validate_completed_package(package_path)
    if {item.name for item in package.iterdir()} != {CENSUS_FILE}:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census package members differ"
        )
    census_path = package / CENSUS_FILE
    _require_regular_mode(census_path, 0o400)
    if census_path.stat().st_size > MAXIMUM_CENSUS_BYTES:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census exceeds byte ceiling"
        )
    try:
        census = SecCompanyfactsSemanticCensusV1.model_validate_json(
            census_path.read_bytes()
        )
    except Exception as exc:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census report is invalid"
        ) from exc
    source, source_manifest_sha256 = _inspect_normalized_source(
        normalized_package_path
    )
    if (
        census.normalized_manifest_sha256 != source_manifest_sha256
        or census.normalized_logical_fingerprint != source.logical_fingerprint
        or census.normalized_content_fingerprint != source.content_fingerprint
        or census.normalized_occurrence_schema_fingerprint
        != source.occurrence_schema_fingerprint
        or census.normalized_artifact_count != len(source.artifacts)
        or census.occurrence_count != source.occurrence_count
        or census.range_start != source.range_start
        or census.range_end != source.range_end
        or census.source_snapshot_date != source.companyfacts_snapshot_date
        or census.source_worker_count != source.worker_count
    ):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census normalized-source binding differs"
        )
    link = _read_link_population(
        package_path=link_package_path,
        data_root=data_root,
    )
    if (
        census.link_manifest_sha256 != link.manifest_sha256
        or census.link_logical_fingerprint != link.logical_fingerprint
        or census.link_population_session != link.session
        or census.link_population_point_in_time_eligibility
        != link.point_in_time_eligibility
        or census.link_population_source_observed_at != link.source_observed_at
        or census.link_common_stock_instrument_count
        != link.common_stock_instrument_count
        or census.link_admitted_common_stock_instrument_count
        != link.admitted_common_stock_instrument_count
        or census.link_quarantined_common_stock_instrument_count
        != link.quarantined_common_stock_instrument_count
        or census.link_distinct_common_stock_cik_count != len(link.ciks)
    ):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census filer-link binding differs"
        )
    return SecCompanyfactsSemanticCensusResult(
        package_path=package,
        census=census,
    )


def _census_worker(
    argument: tuple[
        str,
        int,
        tuple[NormalizedArtifactV1, ...],
        frozenset[str],
    ]
) -> _WorkerResult:
    package_raw, worker_index, artifacts, linked_ciks = argument
    if not artifacts:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census worker has no occurrence artifacts"
        )
    streams = tuple(
        _iter_occurrence_rows(Path(package_raw) / artifact.relative_path, artifact)
        for artifact in sorted(artifacts, key=lambda item: item.filed_year or 0)
    )
    merged = heapq.merge(*streams, key=lambda item: item[0])
    counters = {
        name: Counter()
        for name in (
            "namespaces",
            "units",
            "forms",
            "filed_years",
            "value_kinds",
            "period_shapes",
            "clock_statuses",
            "normalization_statuses",
            "taxonomy_classes",
        )
    }
    concepts: dict[tuple[str, str], _ConceptAccumulator] = {}
    samples: list[SemanticConflictSampleV1] = []
    reason_counts: Counter[str] = Counter()
    occurrence_count = distinct_filers = admitted_filers = observed_concepts = 0
    semantic_count = accession_group_count = 0
    duplicate_groups = duplicate_redundant = 0
    accession_conflicts = accession_conflict_occurrences = 0
    same_time_conflicts = 0
    revision_eligible = revision_quarantined = 0
    keys_with_later = later_accessions = later_states = value_changes = 0
    linked_with_facts = 0
    current_unit: tuple[str, str, str, str] | None = None
    semantic_groups: dict[
        tuple[date | None, date | None],
        dict[str, _AccessionState],
    ] = {}
    last_merged_key: tuple[str, str, str, str, int] | None = None
    last_filer: str | None = None
    current_filer_has_admitted = False
    last_concept_identity: tuple[str, str, str] | None = None

    def finish_unit() -> None:
        nonlocal semantic_count, accession_group_count
        nonlocal duplicate_groups, duplicate_redundant
        nonlocal accession_conflicts, accession_conflict_occurrences
        nonlocal same_time_conflicts, revision_eligible, revision_quarantined
        nonlocal keys_with_later, later_accessions, later_states, value_changes
        if current_unit is None:
            return
        cik, namespace, concept_name, unit = current_unit
        for (start_date, end_date), accessions in semantic_groups.items():
            semantic_count += 1
            accession_group_count += len(accessions)
            reasons: set[str] = set()
            for accession, state in accessions.items():
                if state.occurrence_count > 1 and len(state.values) == 1:
                    duplicate_groups += 1
                    duplicate_redundant += state.occurrence_count - 1
                if len(state.values) > 1:
                    accession_conflicts += 1
                    accession_conflict_occurrences += state.occurrence_count
                    reasons.add("within_accession_value_conflict")
                    if sum(
                        item.conflict_class == "within_accession_value_conflict"
                        for item in samples
                    ) < CONFLICT_SAMPLE_LIMIT:
                        samples.append(
                            _conflict_sample(
                                conflict_class="within_accession_value_conflict",
                                cik=cik,
                                namespace=namespace,
                                concept_name=concept_name,
                                unit=unit,
                                start_date=start_date,
                                end_date=end_date,
                                source_available_at=None,
                                accession_numbers=(accession,),
                                values=tuple(state.values),
                                occurrence_count=state.occurrence_count,
                            )
                        )
                if state.invalid_for_revision:
                    reasons.add("normalization_or_clock_incomplete")
                if len(state.source_times) != 1:
                    reasons.add("accession_clock_ambiguity")
            time_values: dict[
                datetime,
                set[tuple[str, str | None]],
            ] = defaultdict(set)
            time_accessions: dict[datetime, list[str]] = defaultdict(list)
            if not reasons:
                for accession, state in accessions.items():
                    available = next(iter(state.source_times))
                    value = next(iter(state.values))
                    time_values[available].add(value)
                    time_accessions[available].append(accession)
                for available, values in time_values.items():
                    if len(values) > 1:
                        reasons.add("same_availability_value_conflict")
                        same_time_conflicts += 1
                        if sum(
                            item.conflict_class
                            == "same_availability_value_conflict"
                            for item in samples
                        ) < CONFLICT_SAMPLE_LIMIT:
                            samples.append(
                                _conflict_sample(
                                    conflict_class=(
                                        "same_availability_value_conflict"
                                    ),
                                    cik=cik,
                                    namespace=namespace,
                                    concept_name=concept_name,
                                    unit=unit,
                                    start_date=start_date,
                                    end_date=end_date,
                                    source_available_at=available,
                                    accession_numbers=tuple(
                                        sorted(time_accessions[available])
                                    ),
                                    values=tuple(values),
                                    occurrence_count=sum(
                                        accessions[item].occurrence_count
                                        for item in time_accessions[available]
                                    ),
                                )
                            )
            if reasons:
                revision_quarantined += 1
                reason_counts.update(reasons)
                continue
            revision_eligible += 1
            ordered_times = sorted(time_values)
            if len(ordered_times) > 1:
                keys_with_later += 1
                later_accessions += sum(
                    len(time_accessions[item]) for item in ordered_times[1:]
                )
                later_states += len(ordered_times) - 1
                ordered_values = [next(iter(time_values[item])) for item in ordered_times]
                value_changes += sum(
                    left != right
                    for left, right in zip(ordered_values, ordered_values[1:])
                )

    for merged_key, row in merged:
        if last_merged_key is not None and merged_key <= last_merged_key:
            raise SecCompanyfactsSemanticCensusError(
                "semantic census merged occurrence order differs"
            )
        last_merged_key = merged_key
        unit_key = (
            row.companyfacts_cik,
            row.namespace,
            row.concept_name,
            row.unit,
        )
        if current_unit != unit_key:
            finish_unit()
            current_unit = unit_key
            semantic_groups = {}
        if last_filer != row.companyfacts_cik:
            if last_filer is not None and current_filer_has_admitted:
                admitted_filers += 1
            last_filer = row.companyfacts_cik
            current_filer_has_admitted = False
            distinct_filers += 1
            if row.companyfacts_cik in linked_ciks:
                linked_with_facts += 1
        period_shape = _period_shape(row.start_date, row.end_date)
        taxonomy_class = _taxonomy_class(row.namespace)
        counters["namespaces"][row.namespace] += 1
        counters["units"][row.unit] += 1
        counters["forms"][row.form] += 1
        counters["filed_years"][str(row.filed_date.year)] += 1
        counters["value_kinds"][row.value_kind] += 1
        counters["period_shapes"][period_shape] += 1
        counters["clock_statuses"][row.clock_status] += 1
        counters["normalization_statuses"][row.normalization_status] += 1
        counters["taxonomy_classes"][taxonomy_class] += 1
        occurrence_count += 1
        admitted = row.normalization_status == "admitted"
        current_filer_has_admitted |= admitted
        concept_pair = (row.namespace, row.concept_name)
        concept = concepts.setdefault(concept_pair, _ConceptAccumulator())
        concept.occurrence_count += 1
        concept.admitted_occurrence_count += int(admitted)
        concept.period_counts[period_shape] += 1
        concept.unit_counts[row.unit] += 1
        concept.form_counts[row.form] += 1
        concept_identity = (
            row.companyfacts_cik,
            row.namespace,
            row.concept_name,
        )
        if concept_identity != last_concept_identity:
            observed_concepts += 1
            concept.distinct_filer_count += 1
            concept.linked_filer_count += int(row.companyfacts_cik in linked_ciks)
            last_concept_identity = concept_identity
        semantic = semantic_groups.setdefault(
            (row.start_date, row.end_date),
            {},
        )
        accession = semantic.setdefault(row.accession_number, _AccessionState())
        accession.occurrence_count += 1
        accession.values[(row.value_kind, row.value_text)] += 1
        if row.source_available_at is not None:
            accession.source_times.add(row.source_available_at)
        if (
            row.normalization_status != "admitted"
            or row.clock_status != "admitted"
            or row.source_available_at is None
        ):
            accession.invalid_for_revision = True
    finish_unit()
    if last_filer is not None and current_filer_has_admitted:
        admitted_filers += 1
    expected_rows = sum(item.row_count for item in artifacts)
    if occurrence_count != expected_rows:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census worker row denominator differs"
        )
    return _WorkerResult(
        worker_index=worker_index,
        occurrence_count=occurrence_count,
        distinct_filer_count=distinct_filers,
        admitted_fact_filer_count=admitted_filers,
        observed_concept_key_count=observed_concepts,
        semantic_key_count=semantic_count,
        accession_semantic_group_count=accession_group_count,
        exact_duplicate_group_count=duplicate_groups,
        exact_duplicate_redundant_occurrence_count=duplicate_redundant,
        within_accession_conflict_group_count=accession_conflicts,
        within_accession_conflict_occurrence_count=accession_conflict_occurrences,
        same_availability_conflict_group_count=same_time_conflicts,
        revision_eligible_semantic_key_count=revision_eligible,
        revision_quarantined_semantic_key_count=revision_quarantined,
        semantic_key_with_later_accession_count=keys_with_later,
        later_accession_revision_count=later_accessions,
        later_revision_state_count=later_states,
        later_revision_value_change_count=value_changes,
        linked_cik_with_facts_count=linked_with_facts,
        counters=counters,
        revision_quarantine_reasons=reason_counts,
        concepts=concepts,
        conflict_samples=tuple(samples),
    )


def _iter_occurrence_rows(
    path: Path,
    artifact: NormalizedArtifactV1,
) -> Iterator[tuple[tuple[str, str, str, str, int], _Row]]:
    parquet = pq.ParquetFile(path)
    row_count = 0
    last_key: tuple[str, str, str, str, int] | None = None
    for batch in parquet.iter_batches(
        batch_size=65_536,
        columns=list(_OCCURRENCE_COLUMNS),
    ):
        columns = batch.to_pydict()
        for index in range(batch.num_rows):
            if columns["contract_version"][index] != NORMALIZED_CONTRACT_VERSION:
                raise SecCompanyfactsSemanticCensusError(
                    "semantic census source contract differs"
                )
            source_member = columns["source_member_name"][index]
            cik = columns["companyfacts_cik"][index]
            namespace = columns["namespace"][index]
            concept_name = columns["concept_name"][index]
            unit = columns["unit"][index]
            ordinal = columns["unit_occurrence_ordinal"][index]
            key = (source_member, namespace, concept_name, unit, ordinal)
            if last_key is not None and key <= last_key:
                raise SecCompanyfactsSemanticCensusError(
                    "semantic census source occurrence order differs"
                )
            last_key = key
            if columns["source_occurrence_id"][index] != _fingerprint(key):
                raise SecCompanyfactsSemanticCensusError(
                    "semantic census source occurrence identity differs"
                )
            if columns["concept_key"][index] != _fingerprint(
                (cik, namespace, concept_name)
            ):
                raise SecCompanyfactsSemanticCensusError(
                    "semantic census source concept identity differs"
                )
            filed_date = columns["filed_date"][index]
            if filed_date.year != artifact.filed_year:
                raise SecCompanyfactsSemanticCensusError(
                    "semantic census filed-year partition differs"
                )
            row = _Row(
                source_member_name=source_member,
                companyfacts_cik=cik,
                concept_key=columns["concept_key"][index],
                namespace=namespace,
                concept_name=concept_name,
                unit=unit,
                ordinal=ordinal,
                start_date=columns["start_date"][index],
                end_date=columns["end_date"][index],
                value_kind=columns["value_kind"][index],
                value_text=columns["value_text"][index],
                accession_number=columns["accession_number"][index],
                form=columns["form"][index],
                filed_date=filed_date,
                clock_status=columns["filing_clock_admission_status"][index],
                source_available_at=columns["source_available_at_utc"][index],
                normalization_status=columns["normalization_status"][index],
            )
            row_count += 1
            yield key, row
    if row_count != artifact.row_count:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census source artifact row count differs"
        )


def _combine_results(
    *,
    results: tuple[_WorkerResult, ...],
    source: SecCompanyfactsNormalizedSourceManifestV1,
    source_manifest_sha256: str,
    link: _LinkPopulation,
    process_count: int,
    implementation_revision: str,
    evaluated_at: datetime,
) -> SecCompanyfactsSemanticCensusV1:
    if tuple(item.worker_index for item in results) != tuple(range(source.worker_count)):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census worker result order differs"
        )
    counters = {
        name: sum((item.counters[name] for item in results), Counter())
        for name in results[0].counters
    }
    if (
        _ordered(counters["namespaces"]) != source.namespace_occurrence_counts
        or _ordered(counters["forms"]) != source.form_occurrence_counts
        or _ordered(counters["filed_years"]) != source.filed_year_occurrence_counts
        or _ordered(counters["value_kinds"]) != source.value_kind_counts
        or sum(item.occurrence_count for item in results) != source.occurrence_count
    ):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census source aggregate binding differs"
        )
    combined_concepts: dict[tuple[str, str], _ConceptAccumulator] = {}
    for result in results:
        for key, partial in result.concepts.items():
            combined_concepts.setdefault(key, _ConceptAccumulator()).merge(partial)
    ordered_standard = sorted(
        (
            (key, value)
            for key, value in combined_concepts.items()
            if key[0] in _STANDARD_ACCOUNTING_NAMESPACES
        ),
        key=lambda item: (
            -item[1].distinct_filer_count,
            -item[1].occurrence_count,
            item[0][0],
            item[0][1],
        ),
    )[:TOP_STANDARD_CONCEPT_LIMIT]
    top_concepts = tuple(
        StandardConceptCoverageV1(
            rank=index,
            namespace=key[0],
            concept_name=key[1],
            occurrence_count=value.occurrence_count,
            admitted_occurrence_count=value.admitted_occurrence_count,
            distinct_filer_count=value.distinct_filer_count,
            linked_common_stock_filer_count=value.linked_filer_count,
            instant_occurrence_count=value.period_counts["instant"],
            duration_occurrence_count=value.period_counts["duration"],
            other_period_occurrence_count=(
                value.occurrence_count
                - value.period_counts["instant"]
                - value.period_counts["duration"]
            ),
            unit_counts=_ordered(value.unit_counts),
            form_counts=_ordered(value.form_counts),
        )
        for index, (key, value) in enumerate(ordered_standard, start=1)
    )
    samples_by_class: dict[str, list[SemanticConflictSampleV1]] = defaultdict(list)
    for sample in sorted(
        (sample for result in results for sample in result.conflict_samples),
        key=_sample_sort_key,
    ):
        if len(samples_by_class[sample.conflict_class]) < CONFLICT_SAMPLE_LIMIT:
            samples_by_class[sample.conflict_class].append(sample)
    samples = tuple(
        sorted(
            (item for values in samples_by_class.values() for item in values),
            key=_sample_sort_key,
        )
    )
    reason_counts = sum(
        (item.revision_quarantine_reasons for item in results),
        Counter(),
    )
    linked_with_facts = sum(item.linked_cik_with_facts_count for item in results)
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": "sec_edgar",
        "implementation_revision": implementation_revision,
        "evaluated_at": evaluated_at,
        "range_start": source.range_start,
        "range_end": source.range_end,
        "source_snapshot_date": source.companyfacts_snapshot_date,
        "normalized_manifest_sha256": source_manifest_sha256,
        "normalized_logical_fingerprint": source.logical_fingerprint,
        "normalized_content_fingerprint": source.content_fingerprint,
        "normalized_occurrence_schema_fingerprint": (
            source.occurrence_schema_fingerprint
        ),
        "normalized_artifact_count": len(source.artifacts),
        "source_worker_count": source.worker_count,
        "process_count": process_count,
        "link_manifest_sha256": link.manifest_sha256,
        "link_logical_fingerprint": link.logical_fingerprint,
        "link_population_session": link.session,
        "link_population_point_in_time_eligibility": (
            link.point_in_time_eligibility
        ),
        "link_population_source_observed_at": link.source_observed_at,
        "link_common_stock_instrument_count": link.common_stock_instrument_count,
        "link_admitted_common_stock_instrument_count": (
            link.admitted_common_stock_instrument_count
        ),
        "link_quarantined_common_stock_instrument_count": (
            link.quarantined_common_stock_instrument_count
        ),
        "link_distinct_common_stock_cik_count": len(link.ciks),
        "link_cik_with_source_facts_count": linked_with_facts,
        "link_cik_without_source_facts_count": len(link.ciks) - linked_with_facts,
        "occurrence_count": source.occurrence_count,
        "distinct_filer_count": sum(item.distinct_filer_count for item in results),
        "admitted_fact_filer_count": sum(
            item.admitted_fact_filer_count for item in results
        ),
        "observed_concept_key_count": sum(
            item.observed_concept_key_count for item in results
        ),
        "distinct_taxonomy_concept_count": len(combined_concepts),
        "semantic_key_count": sum(item.semantic_key_count for item in results),
        "accession_semantic_group_count": sum(
            item.accession_semantic_group_count for item in results
        ),
        "exact_duplicate_group_count": sum(
            item.exact_duplicate_group_count for item in results
        ),
        "exact_duplicate_redundant_occurrence_count": sum(
            item.exact_duplicate_redundant_occurrence_count for item in results
        ),
        "within_accession_conflict_group_count": sum(
            item.within_accession_conflict_group_count for item in results
        ),
        "within_accession_conflict_occurrence_count": sum(
            item.within_accession_conflict_occurrence_count for item in results
        ),
        "same_availability_conflict_group_count": sum(
            item.same_availability_conflict_group_count for item in results
        ),
        "revision_eligible_semantic_key_count": sum(
            item.revision_eligible_semantic_key_count for item in results
        ),
        "revision_quarantined_semantic_key_count": sum(
            item.revision_quarantined_semantic_key_count for item in results
        ),
        "semantic_key_with_later_accession_count": sum(
            item.semantic_key_with_later_accession_count for item in results
        ),
        "later_accession_revision_count": sum(
            item.later_accession_revision_count for item in results
        ),
        "later_revision_state_count": sum(
            item.later_revision_state_count for item in results
        ),
        "later_revision_value_change_count": sum(
            item.later_revision_value_change_count for item in results
        ),
        "namespace_occurrence_counts": _ordered(counters["namespaces"]),
        "unit_occurrence_counts": _ordered(counters["units"]),
        "form_occurrence_counts": _ordered(counters["forms"]),
        "filed_year_occurrence_counts": _ordered(counters["filed_years"]),
        "value_kind_occurrence_counts": _ordered(counters["value_kinds"]),
        "period_shape_occurrence_counts": _ordered(counters["period_shapes"]),
        "filing_clock_status_counts": _ordered(counters["clock_statuses"]),
        "normalization_status_counts": _ordered(
            counters["normalization_statuses"]
        ),
        "taxonomy_class_occurrence_counts": _ordered(
            counters["taxonomy_classes"]
        ),
        "revision_quarantine_reason_counts": _ordered(reason_counts),
        "top_standard_concepts": top_concepts,
        "conflict_samples": samples,
        "full_occurrence_scan": True,
        "daily_cartesian_panel_created": False,
        "registered_feature_count": 0,
        "issuer_projection_authorized": False,
        "canonical_data_write_count": 0,
        "membership_write_count": 0,
        "analytics_execution_count": 0,
        "candidate_write_count": 0,
        "research_performance_authorized": False,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return SecCompanyfactsSemanticCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _read_link_population(*, package_path: Path, data_root: Path) -> _LinkPopulation:
    result = read_sec_filer_security_link_package(
        package_path=package_path,
        data_root=data_root,
    )
    manifest = result.manifest
    if manifest.session_count != 1:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census requires one explicit link diagnostic session"
        )
    evidence = manifest.sessions[0]
    if evidence.source_observed_at is None:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census link diagnostic lacks source time"
        )
    path = package_path / f"as_of_date={evidence.as_of_date.isoformat()}" / LINK_PARQUET_FILE
    table = pq.ParquetFile(path).read(
        columns=["instrument_type", "decision_status", "sec_cik"]
    )
    common_count = admitted_count = 0
    ciks: set[str] = set()
    for row in table.to_pylist():
        if row["instrument_type"] != "common_stock":
            continue
        common_count += 1
        if row["decision_status"] == "admitted_unique_cik":
            if row["sec_cik"] is None:
                raise SecCompanyfactsSemanticCensusError(
                    "semantic census admitted common stock lacks CIK"
                )
            admitted_count += 1
            ciks.add(row["sec_cik"])
    if common_count == 0 or not ciks:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census link diagnostic population is empty"
        )
    return _LinkPopulation(
        manifest_sha256=_sha256_file(package_path / "manifest.json"),
        logical_fingerprint=manifest.logical_fingerprint,
        session=evidence.as_of_date,
        point_in_time_eligibility=evidence.point_in_time_eligibility,
        source_observed_at=evidence.source_observed_at,
        common_stock_instrument_count=common_count,
        admitted_common_stock_instrument_count=admitted_count,
        quarantined_common_stock_instrument_count=common_count - admitted_count,
        ciks=frozenset(ciks),
    )


def _inspect_normalized_source(
    package_path: Path,
) -> tuple[SecCompanyfactsNormalizedSourceManifestV1, str]:
    package = _validate_completed_package(package_path)
    manifest_path = package / NORMALIZED_MANIFEST_FILE
    _require_regular_mode(manifest_path, 0o400)
    if manifest_path.stat().st_size > 4 * 1024 * 1024:
        raise SecCompanyfactsSemanticCensusError(
            "normalized source manifest exceeds byte ceiling"
        )
    try:
        manifest = SecCompanyfactsNormalizedSourceManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise SecCompanyfactsSemanticCensusError(
            "normalized source manifest is invalid"
        ) from exc
    expected_workers = {f"worker={index:02d}" for index in range(manifest.worker_count)}
    if {item.name for item in package.iterdir()} != {
        NORMALIZED_MANIFEST_FILE,
        *expected_workers,
    }:
        raise SecCompanyfactsSemanticCensusError(
            "normalized source package members differ"
        )
    expected_by_worker: dict[int, set[str]] = {
        index: set() for index in range(manifest.worker_count)
    }
    for artifact in manifest.artifacts:
        expected_by_worker[artifact.worker_index].add(
            Path(artifact.relative_path).name
        )
    for index in range(manifest.worker_count):
        worker_path = package / f"worker={index:02d}"
        if worker_path.is_symlink() or not worker_path.is_dir():
            raise SecCompanyfactsSemanticCensusError(
                "normalized source worker is unavailable"
            )
        _require_mode(worker_path, 0o700)
        if {item.name for item in worker_path.iterdir()} != expected_by_worker[index]:
            raise SecCompanyfactsSemanticCensusError(
                "normalized source worker members differ"
            )
    for artifact in manifest.artifacts:
        path = package / artifact.relative_path
        _require_regular_mode(path, 0o400)
        if (
            path.stat().st_size != artifact.byte_size
            or _sha256_file(path) != artifact.physical_sha256
        ):
            raise SecCompanyfactsSemanticCensusError(
                "normalized source artifact identity differs"
            )
        expected_schema = (
            ENTITY_ARROW_SCHEMA
            if artifact.artifact_kind == "entity"
            else CONCEPT_ARROW_SCHEMA
            if artifact.artifact_kind == "concept"
            else OCCURRENCE_ARROW_SCHEMA
        )
        if (
            pq.ParquetFile(path).schema_arrow != expected_schema
            or artifact.schema_fingerprint != _schema_fingerprint(expected_schema)
        ):
            raise SecCompanyfactsSemanticCensusError(
                "normalized source artifact schema differs"
            )
    if manifest.content_fingerprint != _fingerprint(
        tuple(
            (artifact.relative_path, artifact.logical_fingerprint)
            for artifact in manifest.artifacts
        )
    ):
        raise SecCompanyfactsSemanticCensusError(
            "normalized source content binding differs"
        )
    return manifest, _sha256_file(manifest_path)


def _conflict_sample(
    *,
    conflict_class: Literal[
        "within_accession_value_conflict",
        "same_availability_value_conflict",
    ],
    cik: str,
    namespace: str,
    concept_name: str,
    unit: str,
    start_date: date | None,
    end_date: date | None,
    source_available_at: datetime | None,
    accession_numbers: tuple[str, ...],
    values: tuple[tuple[str, str | None], ...],
    occurrence_count: int,
) -> SemanticConflictSampleV1:
    semantic_key = (cik, namespace, concept_name, unit, start_date, end_date)
    return SemanticConflictSampleV1(
        conflict_class=conflict_class,
        semantic_key_fingerprint=_fingerprint(semantic_key),
        companyfacts_cik=cik,
        namespace=namespace,
        concept_name=concept_name,
        unit=unit,
        start_date=start_date,
        end_date=end_date,
        source_available_at_utc=source_available_at,
        accession_numbers=tuple(sorted(set(accession_numbers))),
        distinct_value_fingerprints=tuple(
            sorted({_fingerprint(value) for value in values})
        ),
        occurrence_count=occurrence_count,
    )


def _period_shape(start_date: date | None, end_date: date | None) -> str:
    if start_date is None and end_date is not None:
        return "instant"
    if start_date is not None and end_date is not None:
        return "duration"
    return "invalid_or_incomplete"


def _taxonomy_class(namespace: str) -> str:
    if namespace in _STANDARD_ACCOUNTING_NAMESPACES:
        return "standard_accounting"
    if namespace == "dei":
        return "document_entity"
    if namespace in _SEC_SPECIALIZED_NAMESPACES:
        return "sec_specialized"
    return "unregistered_namespace_review"


def _sample_sort_key(sample: SemanticConflictSampleV1) -> tuple[object, ...]:
    return (
        sample.conflict_class,
        sample.companyfacts_cik,
        sample.namespace,
        sample.concept_name,
        sample.unit,
        sample.start_date or date.min,
        sample.end_date or date.min,
        sample.source_available_at_utc or datetime.min.replace(tzinfo=UTC),
        sample.accession_numbers,
    )


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, value) for key, value in counter.items() if value > 0))


def _validate_output_target(path: Path) -> tuple[Path, Path]:
    target = path.absolute()
    parent = target.parent
    if (
        parent.is_symlink()
        or not parent.is_dir()
        or parent.resolve(strict=True) != parent
        or parent.stat().st_uid != os.getuid()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
        or re.fullmatch(r"build=[A-Za-z0-9._-]+", target.name) is None
    ):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census output target is unsafe"
        )
    partial = parent / f".{target.name}.partial"
    if os.path.lexists(target) or os.path.lexists(partial):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census output target already exists"
        )
    return target, partial


def _validate_completed_package(path: Path) -> Path:
    package = path.absolute()
    if (
        package.is_symlink()
        or not package.is_dir()
        or package.resolve(strict=True) != package
    ):
        raise SecCompanyfactsSemanticCensusError(
            "semantic census package is unsafe"
        )
    _require_mode(package, 0o700)
    return package


def _require_regular_mode(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise SecCompanyfactsSemanticCensusError("semantic census file is unsafe")
    _require_mode(path, mode)


def _require_mode(path: Path, mode: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census ownership or mode differs"
        )


def _write_exclusive_json(path: Path, value: object) -> None:
    raw = _json_bytes(value) + b"\n"
    if len(raw) > MAXIMUM_CENSUS_BYTES:
        raise SecCompanyfactsSemanticCensusError(
            "semantic census exceeds byte ceiling"
        )
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
        0o400,
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


def _schema_fingerprint(schema: pa.Schema) -> str:
    return hashlib.sha256(schema.serialize().to_pybytes()).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
