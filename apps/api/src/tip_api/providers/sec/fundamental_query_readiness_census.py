"""Measure exact source readiness for the first SEC fundamental queries."""

from __future__ import annotations

import hashlib
import heapq
import json
import multiprocessing
import os
import re
import shutil
import stat
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterator, Literal, NamedTuple

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_normalized_source import (
    CONTRACT_VERSION as NORMALIZED_CONTRACT_VERSION,
    MANIFEST_FILE as NORMALIZED_MANIFEST_FILE,
    OCCURRENCE_ARROW_SCHEMA,
    NormalizedArtifactV1,
    SecCompanyfactsNormalizedSourceManifestV1,
)
from tip_api.providers.sec.companyfacts_semantic_census import (
    CENSUS_FILE as SEMANTIC_CENSUS_FILE,
    SecCompanyfactsSemanticCensusV1,
    read_sec_companyfacts_semantic_census,
)
from tip_api.providers.sec.fundamental_query_registry import (
    CONTRACT_VERSION as REGISTRY_CONTRACT_VERSION,
    REGISTRY_ID,
    SecFundamentalQueryRegistryV1,
    SecFundamentalQueryV1,
    build_first_sec_fundamental_query_registry,
)


CONTRACT_VERSION = "sec-fundamental-query-readiness-census/1.0"
CENSUS_FILE = "census.json"
MAXIMUM_PROCESSES = 16
MAXIMUM_CENSUS_BYTES = 1024 * 1024
MAXIMUM_BOUND_MANIFEST_BYTES = 4 * 1024 * 1024
_SHA256 = r"^[0-9a-f]{64}$"
_REVISION = r"^[0-9a-f]{40}$"
_TARGET_COLUMNS = (
    "contract_version",
    "source_member_name",
    "companyfacts_cik",
    "namespace",
    "concept_name",
    "unit",
    "unit_occurrence_ordinal",
    "start_date",
    "end_date",
    "value_kind",
    "value_text",
    "accession_number",
    "fiscal_period",
    "form",
    "filing_clock_admission_status",
    "source_available_at_utc",
    "normalization_status",
)
_DISPOSITIONS = (
    "filing_clock_not_admitted",
    "fiscal_period_not_allowed",
    "form_not_allowed",
    "missing_end_date",
    "normalization_not_admitted",
    "period_shape_mismatch",
    "query_eligible",
    "source_available_at_missing",
    "unit_not_allowed",
    "value_not_accepted",
    "year_duration_out_of_range",
)


class SecFundamentalQueryReadinessError(RuntimeError):
    """Raised when query readiness cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecFundamentalQueryReadinessV1(_FrozenModel):
    query_id: str = Field(pattern=r"^[a-z0-9_]+_v1$")
    namespace: Literal["us-gaap"] = "us-gaap"
    concept_name: str = Field(min_length=1)
    concept_occurrence_count: int = Field(ge=1)
    concept_filer_count: int = Field(ge=1)
    disposition_counts: tuple[tuple[str, int], ...]
    eligible_occurrence_count: int = Field(ge=0)
    eligible_filer_count: int = Field(ge=0)
    semantic_period_key_count: int = Field(ge=0)
    clean_semantic_period_key_count: int = Field(ge=0)
    quarantined_semantic_period_key_count: int = Field(ge=0)
    exact_duplicate_group_count: int = Field(ge=0)
    exact_duplicate_redundant_occurrence_count: int = Field(ge=0)
    within_accession_conflict_group_count: int = Field(ge=0)
    same_availability_conflict_group_count: int = Field(ge=0)
    same_period_end_conflict_group_count: int = Field(ge=0)
    selectable_filer_count: int = Field(ge=0)
    readiness_state: Literal["ready_for_projection_census", "source_query_blocked"]

    @model_validator(mode="after")
    def counts_reconcile(self) -> "SecFundamentalQueryReadinessV1":
        if tuple(name for name, _ in self.disposition_counts) != _DISPOSITIONS:
            raise ValueError("fundamental query disposition order differs")
        if any(count < 0 for _, count in self.disposition_counts):
            raise ValueError("fundamental query disposition count is negative")
        if sum(count for _, count in self.disposition_counts) != self.concept_occurrence_count:
            raise ValueError("fundamental query disposition denominator differs")
        disposition = dict(self.disposition_counts)
        if disposition["query_eligible"] != self.eligible_occurrence_count:
            raise ValueError("fundamental query eligible occurrence count differs")
        if (
            self.clean_semantic_period_key_count
            + self.quarantined_semantic_period_key_count
            != self.semantic_period_key_count
        ):
            raise ValueError("fundamental query semantic period denominator differs")
        if not (
            self.selectable_filer_count
            <= self.eligible_filer_count
            <= self.concept_filer_count
        ):
            raise ValueError("fundamental query filer counts differ")
        expected_state = (
            "ready_for_projection_census"
            if self.selectable_filer_count > 0
            else "source_query_blocked"
        )
        if self.readiness_state != expected_state:
            raise ValueError("fundamental query readiness state differs")
        return self


class SecFundamentalQueryReadinessCensusV1(_FrozenModel):
    contract_version: Literal[
        "sec-fundamental-query-readiness-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    implementation_revision: str = Field(pattern=_REVISION)
    evaluated_at: datetime
    registry_contract_version: Literal[
        "sec-fundamental-query-registry/1.0"
    ] = REGISTRY_CONTRACT_VERSION
    registry_id: Literal["sec-issuer-fundamentals-first-set-v1"] = REGISTRY_ID
    registry_logical_fingerprint: str = Field(pattern=_SHA256)
    semantic_census_sha256: str = Field(pattern=_SHA256)
    semantic_census_logical_fingerprint: str = Field(pattern=_SHA256)
    normalized_manifest_sha256: str = Field(pattern=_SHA256)
    normalized_logical_fingerprint: str = Field(pattern=_SHA256)
    normalized_content_fingerprint: str = Field(pattern=_SHA256)
    range_start: date
    range_end: date
    source_snapshot_date: date
    source_worker_count: int = Field(ge=1, le=MAXIMUM_PROCESSES)
    process_count: int = Field(ge=1, le=MAXIMUM_PROCESSES)
    source_occurrence_count: int = Field(ge=1)
    scanned_occurrence_count: int = Field(ge=1)
    targeted_concept_occurrence_count: int = Field(ge=1)
    unregistered_concept_occurrence_count: int = Field(ge=0)
    query_results: tuple[SecFundamentalQueryReadinessV1, ...]
    full_source_occurrence_scan: Literal[True] = True
    query_values_published: Literal[False] = False
    daily_cartesian_panel_created: Literal[False] = False
    security_projection_executed: Literal[False] = False
    security_feature_materialization_authorized: Literal[False] = False
    strategy_outcome_access_count: Literal[0] = 0
    research_performance_authorized: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
    membership_write_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def census_reconciles(self) -> "SecFundamentalQueryReadinessCensusV1":
        if self.range_end < self.range_start:
            raise ValueError("fundamental query census range is reversed")
        if self.process_count > self.source_worker_count:
            raise ValueError("fundamental query process count exceeds source workers")
        if self.scanned_occurrence_count != self.source_occurrence_count:
            raise ValueError("fundamental query scan denominator differs")
        if (
            self.targeted_concept_occurrence_count
            + self.unregistered_concept_occurrence_count
            != self.source_occurrence_count
        ):
            raise ValueError("fundamental query target denominator differs")
        registry = build_first_sec_fundamental_query_registry()
        if self.registry_logical_fingerprint != registry.logical_fingerprint:
            raise ValueError("fundamental query registry binding differs")
        if tuple(item.query_id for item in self.query_results) != registry.query_order:
            raise ValueError("fundamental query result order differs")
        if sum(
            item.concept_occurrence_count for item in self.query_results
        ) != self.targeted_concept_occurrence_count:
            raise ValueError("fundamental query concept denominator differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("fundamental query census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecFundamentalQueryReadinessResult:
    package_path: Path
    census: SecFundamentalQueryReadinessCensusV1


class _SelectedRow(NamedTuple):
    source_member_name: str
    companyfacts_cik: str
    namespace: str
    concept_name: str
    unit: str
    ordinal: int
    start_date: date | None
    end_date: date | None
    value_kind: str
    value_text: str | None
    accession_number: str
    fiscal_period: str | None
    form: str
    clock_status: str
    source_available_at: datetime | None
    normalization_status: str


@dataclass(slots=True)
class _QueryAccumulator:
    concept_occurrences: int = 0
    dispositions: Counter[str] = field(default_factory=Counter)
    concept_filers: set[str] = field(default_factory=set)
    eligible_filers: set[str] = field(default_factory=set)
    selectable_filers: set[str] = field(default_factory=set)
    semantic_period_keys: int = 0
    clean_semantic_period_keys: int = 0
    quarantined_semantic_period_keys: int = 0
    exact_duplicate_groups: int = 0
    exact_duplicate_redundant_occurrences: int = 0
    within_accession_conflict_groups: int = 0
    same_availability_conflict_groups: int = 0
    same_period_end_conflict_groups: int = 0

    def merge(self, other: "_QueryAccumulator") -> None:
        for left, right, name in (
            (self.concept_filers, other.concept_filers, "concept"),
            (self.eligible_filers, other.eligible_filers, "eligible"),
            (self.selectable_filers, other.selectable_filers, "selectable"),
        ):
            if left.intersection(right):
                raise SecFundamentalQueryReadinessError(
                    f"fundamental query {name} filer crosses source workers"
                )
            left.update(right)
        self.concept_occurrences += other.concept_occurrences
        self.dispositions.update(other.dispositions)
        self.semantic_period_keys += other.semantic_period_keys
        self.clean_semantic_period_keys += other.clean_semantic_period_keys
        self.quarantined_semantic_period_keys += other.quarantined_semantic_period_keys
        self.exact_duplicate_groups += other.exact_duplicate_groups
        self.exact_duplicate_redundant_occurrences += (
            other.exact_duplicate_redundant_occurrences
        )
        self.within_accession_conflict_groups += (
            other.within_accession_conflict_groups
        )
        self.same_availability_conflict_groups += (
            other.same_availability_conflict_groups
        )
        self.same_period_end_conflict_groups += other.same_period_end_conflict_groups


@dataclass(frozen=True, slots=True)
class _WorkerResult:
    worker_index: int
    scanned_occurrence_count: int
    queries: dict[str, _QueryAccumulator]


def build_sec_fundamental_query_readiness_census(
    *,
    normalized_package_path: Path,
    semantic_census_package_path: Path,
    semantic_link_package_path: Path,
    data_root: Path,
    output_package_path: Path,
    process_count: int,
    implementation_revision: str,
    evaluated_at: datetime | None = None,
) -> SecFundamentalQueryReadinessResult:
    """Build one immutable query-specific source readiness census."""

    if re.fullmatch(_REVISION, implementation_revision) is None:
        raise SecFundamentalQueryReadinessError(
            "fundamental query implementation revision is invalid"
        )
    registry = build_first_sec_fundamental_query_registry()
    semantic = read_sec_companyfacts_semantic_census(
        package_path=semantic_census_package_path,
        normalized_package_path=normalized_package_path,
        link_package_path=semantic_link_package_path,
        data_root=data_root,
    ).census
    source, source_manifest_sha256 = _read_bound_normalized_manifest(
        normalized_package_path
    )
    if process_count < 1 or process_count > min(
        MAXIMUM_PROCESSES, source.worker_count
    ):
        raise SecFundamentalQueryReadinessError(
            "fundamental query process count is invalid"
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
                registry,
            )
            for worker_index in range(source.worker_count)
        )
        if process_count == 1:
            worker_results = tuple(_census_worker(argument) for argument in arguments)
        else:
            with ProcessPoolExecutor(
                max_workers=process_count,
                mp_context=multiprocessing.get_context("spawn"),
            ) as executor:
                worker_results = tuple(executor.map(_census_worker, arguments))
        census = _combine_results(
            results=tuple(sorted(worker_results, key=lambda item: item.worker_index)),
            registry=registry,
            semantic=semantic,
            semantic_census_sha256=_sha256_file(
                semantic_census_package_path / SEMANTIC_CENSUS_FILE
            ),
            source=source,
            source_manifest_sha256=source_manifest_sha256,
            process_count=process_count,
            implementation_revision=implementation_revision,
            evaluated_at=normalize_utc_datetime(evaluated_at or datetime.now(UTC)),
        )
        _write_exclusive_json(partial / CENSUS_FILE, census.model_dump(mode="json"))
        _fsync_directory(partial)
        os.rename(partial, target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.parent == target.parent and partial.name == f".{target.name}.partial":
            shutil.rmtree(partial, ignore_errors=True)
        raise
    return read_sec_fundamental_query_readiness_census(
        package_path=target,
        normalized_package_path=normalized_package_path,
        semantic_census_package_path=semantic_census_package_path,
        semantic_link_package_path=semantic_link_package_path,
        data_root=data_root,
    )


def read_sec_fundamental_query_readiness_census(
    *,
    package_path: Path,
    normalized_package_path: Path,
    semantic_census_package_path: Path,
    semantic_link_package_path: Path,
    data_root: Path,
) -> SecFundamentalQueryReadinessResult:
    """Formally reread one readiness census and all source bindings."""

    package = _validate_completed_package(package_path)
    if {item.name for item in package.iterdir()} != {CENSUS_FILE}:
        raise SecFundamentalQueryReadinessError(
            "fundamental query census package members differ"
        )
    census_path = package / CENSUS_FILE
    _require_regular_mode(census_path, 0o400)
    if census_path.stat().st_size > MAXIMUM_CENSUS_BYTES:
        raise SecFundamentalQueryReadinessError(
            "fundamental query census exceeds byte ceiling"
        )
    try:
        census = SecFundamentalQueryReadinessCensusV1.model_validate_json(
            census_path.read_bytes()
        )
    except Exception as exc:
        raise SecFundamentalQueryReadinessError(
            "fundamental query census report is invalid"
        ) from exc
    registry = build_first_sec_fundamental_query_registry()
    semantic = read_sec_companyfacts_semantic_census(
        package_path=semantic_census_package_path,
        normalized_package_path=normalized_package_path,
        link_package_path=semantic_link_package_path,
        data_root=data_root,
    ).census
    source, source_manifest_sha256 = _read_bound_normalized_manifest(
        normalized_package_path
    )
    if (
        census.registry_logical_fingerprint != registry.logical_fingerprint
        or census.semantic_census_sha256
        != _sha256_file(semantic_census_package_path / SEMANTIC_CENSUS_FILE)
        or census.semantic_census_logical_fingerprint != semantic.logical_fingerprint
        or census.normalized_manifest_sha256 != source_manifest_sha256
        or census.normalized_logical_fingerprint != source.logical_fingerprint
        or census.normalized_content_fingerprint != source.content_fingerprint
        or census.range_start != source.range_start
        or census.range_end != source.range_end
        or census.source_snapshot_date != source.companyfacts_snapshot_date
        or census.source_worker_count != source.worker_count
        or census.source_occurrence_count != source.occurrence_count
    ):
        raise SecFundamentalQueryReadinessError(
            "fundamental query census input binding differs"
        )
    return SecFundamentalQueryReadinessResult(package_path=package, census=census)


def _census_worker(
    argument: tuple[
        str,
        int,
        tuple[NormalizedArtifactV1, ...],
        SecFundamentalQueryRegistryV1,
    ]
) -> _WorkerResult:
    package_raw, worker_index, artifacts, registry = argument
    if not artifacts:
        raise SecFundamentalQueryReadinessError(
            "fundamental query worker has no occurrence artifacts"
        )
    by_concept = {
        (query.namespace, query.concept_name): query for query in registry.queries
    }
    streams = tuple(
        _iter_target_rows(
            Path(package_raw) / artifact.relative_path,
            artifact,
            frozenset(by_concept),
        )
        for artifact in sorted(artifacts, key=lambda item: item.filed_year or 0)
    )
    accumulators = {query.query_id: _QueryAccumulator() for query in registry.queries}
    current_cik: str | None = None
    eligible_by_query: dict[str, list[_SelectedRow]] = defaultdict(list)
    for _, row in heapq.merge(*streams, key=lambda item: item[0]):
        if current_cik is not None and row.companyfacts_cik != current_cik:
            _flush_filer(current_cik, eligible_by_query, accumulators)
            eligible_by_query = defaultdict(list)
        current_cik = row.companyfacts_cik
        query = by_concept[(row.namespace, row.concept_name)]
        accumulator = accumulators[query.query_id]
        accumulator.concept_occurrences += 1
        accumulator.concept_filers.add(row.companyfacts_cik)
        disposition = _classify_row(row, query)
        accumulator.dispositions[disposition] += 1
        if disposition == "query_eligible":
            accumulator.eligible_filers.add(row.companyfacts_cik)
            eligible_by_query[query.query_id].append(row)
    if current_cik is not None:
        _flush_filer(current_cik, eligible_by_query, accumulators)
    return _WorkerResult(
        worker_index=worker_index,
        scanned_occurrence_count=sum(item.row_count for item in artifacts),
        queries=accumulators,
    )


def _iter_target_rows(
    path: Path,
    artifact: NormalizedArtifactV1,
    targets: frozenset[tuple[str, str]],
) -> Iterator[tuple[tuple[str, str, str, str, int], _SelectedRow]]:
    parquet = pq.ParquetFile(path)
    if parquet.schema_arrow != OCCURRENCE_ARROW_SCHEMA:
        raise SecFundamentalQueryReadinessError(
            "fundamental query source schema differs"
        )
    row_count = 0
    target_names = pa.array(sorted({concept for _, concept in targets}))
    for batch in parquet.iter_batches(batch_size=65_536, columns=list(_TARGET_COLUMNS)):
        row_count += batch.num_rows
        if not pc.all(
            pc.equal(
                batch.column(batch.schema.get_field_index("contract_version")),
                NORMALIZED_CONTRACT_VERSION,
            )
        ).as_py():
            raise SecFundamentalQueryReadinessError(
                "fundamental query source contract differs"
            )
        mask = pc.and_(
            pc.equal(
                batch.column(batch.schema.get_field_index("namespace")),
                "us-gaap",
            ),
            pc.is_in(
                batch.column(batch.schema.get_field_index("concept_name")),
                value_set=target_names,
            ),
        )
        selected = batch.filter(mask).to_pydict()
        for index in range(len(selected["companyfacts_cik"])):
            row = _SelectedRow(
                source_member_name=selected["source_member_name"][index],
                companyfacts_cik=selected["companyfacts_cik"][index],
                namespace=selected["namespace"][index],
                concept_name=selected["concept_name"][index],
                unit=selected["unit"][index],
                ordinal=selected["unit_occurrence_ordinal"][index],
                start_date=selected["start_date"][index],
                end_date=selected["end_date"][index],
                value_kind=selected["value_kind"][index],
                value_text=selected["value_text"][index],
                accession_number=selected["accession_number"][index],
                fiscal_period=selected["fiscal_period"][index],
                form=selected["form"][index],
                clock_status=selected["filing_clock_admission_status"][index],
                source_available_at=selected["source_available_at_utc"][index],
                normalization_status=selected["normalization_status"][index],
            )
            if (row.namespace, row.concept_name) not in targets:
                raise SecFundamentalQueryReadinessError(
                    "fundamental query target filter differs"
                )
            key = (
                row.source_member_name,
                row.namespace,
                row.concept_name,
                row.unit,
                row.ordinal,
            )
            yield key, row
    if row_count != artifact.row_count:
        raise SecFundamentalQueryReadinessError(
            "fundamental query source artifact row count differs"
        )


def _classify_row(row: _SelectedRow, query: SecFundamentalQueryV1) -> str:
    if row.unit != query.unit:
        return "unit_not_allowed"
    periods_by_form = {
        form: rule.fiscal_periods
        for rule in query.form_period_rules
        for form in rule.forms
    }
    if row.form not in periods_by_form:
        return "form_not_allowed"
    if row.fiscal_period not in periods_by_form[row.form]:
        return "fiscal_period_not_allowed"
    if row.end_date is None:
        return "missing_end_date"
    if query.period_shape == "instant":
        if row.start_date is not None:
            return "period_shape_mismatch"
    elif row.start_date is None:
        return "period_shape_mismatch"
    else:
        duration_days = (row.end_date - row.start_date).days
        if (
            query.minimum_duration_days is None
            or query.maximum_duration_days is None
            or not query.minimum_duration_days
            <= duration_days
            <= query.maximum_duration_days
        ):
            return "year_duration_out_of_range"
    if row.normalization_status != "admitted":
        return "normalization_not_admitted"
    if row.clock_status != "admitted":
        return "filing_clock_not_admitted"
    if row.source_available_at is None:
        return "source_available_at_missing"
    if row.value_kind not in query.accepted_value_kinds or row.value_text is None:
        return "value_not_accepted"
    return "query_eligible"


def _flush_filer(
    cik: str,
    eligible_by_query: dict[str, list[_SelectedRow]],
    accumulators: dict[str, _QueryAccumulator],
) -> None:
    for query_id, rows in eligible_by_query.items():
        if any(row.companyfacts_cik != cik for row in rows):
            raise SecFundamentalQueryReadinessError(
                "fundamental query filer buffer differs"
            )
        accumulator = accumulators[query_id]
        periods: dict[tuple[date | None, date], list[_SelectedRow]] = defaultdict(list)
        for row in rows:
            if row.end_date is None or row.source_available_at is None:
                raise SecFundamentalQueryReadinessError(
                    "fundamental query eligible row is incomplete"
                )
            periods[(row.start_date, row.end_date)].append(row)
        period_states: list[tuple[tuple[date | None, date], bool]] = []
        for period_key, period_rows in periods.items():
            accumulator.semantic_period_keys += 1
            by_accession: dict[str, list[_SelectedRow]] = defaultdict(list)
            for row in period_rows:
                by_accession[row.accession_number].append(row)
            clean_states: list[tuple[datetime, tuple[str, str | None]]] = []
            period_conflict = False
            for accession_rows in by_accession.values():
                values = {
                    (row.value_kind, row.value_text) for row in accession_rows
                }
                times = {row.source_available_at for row in accession_rows}
                if len(values) != 1 or len(times) != 1 or None in times:
                    accumulator.within_accession_conflict_groups += 1
                    period_conflict = True
                    continue
                if len(accession_rows) > 1:
                    accumulator.exact_duplicate_groups += 1
                    accumulator.exact_duplicate_redundant_occurrences += (
                        len(accession_rows) - 1
                    )
                available_at = next(iter(times))
                if available_at is None:
                    raise SecFundamentalQueryReadinessError(
                        "fundamental query clean accession lacks source time"
                    )
                clean_states.append((available_at, next(iter(values))))
            by_time: dict[datetime, set[tuple[str, str | None]]] = defaultdict(set)
            for available_at, value in clean_states:
                by_time[available_at].add(value)
            same_time_conflicts = sum(len(values) > 1 for values in by_time.values())
            accumulator.same_availability_conflict_groups += same_time_conflicts
            period_conflict = period_conflict or same_time_conflicts > 0
            period_states.append((period_key, period_conflict))
        clean_by_end: dict[date, list[tuple[date | None, date]]] = defaultdict(list)
        for period_key, period_conflict in period_states:
            if not period_conflict:
                clean_by_end[period_key[1]].append(period_key)
        ambiguous_periods: set[tuple[date | None, date]] = set()
        for period_keys in clean_by_end.values():
            if len(period_keys) > 1:
                accumulator.same_period_end_conflict_groups += 1
                ambiguous_periods.update(period_keys)
        filer_selectable = False
        for period_key, period_conflict in period_states:
            if period_conflict or period_key in ambiguous_periods:
                accumulator.quarantined_semantic_period_keys += 1
            else:
                accumulator.clean_semantic_period_keys += 1
                filer_selectable = True
        if filer_selectable:
            accumulator.selectable_filers.add(cik)


def _combine_results(
    *,
    results: tuple[_WorkerResult, ...],
    registry: SecFundamentalQueryRegistryV1,
    semantic: SecCompanyfactsSemanticCensusV1,
    semantic_census_sha256: str,
    source: SecCompanyfactsNormalizedSourceManifestV1,
    source_manifest_sha256: str,
    process_count: int,
    implementation_revision: str,
    evaluated_at: datetime,
) -> SecFundamentalQueryReadinessCensusV1:
    if tuple(item.worker_index for item in results) != tuple(range(source.worker_count)):
        raise SecFundamentalQueryReadinessError(
            "fundamental query worker result order differs"
        )
    combined = {query.query_id: _QueryAccumulator() for query in registry.queries}
    for result in results:
        if set(result.queries) != set(combined):
            raise SecFundamentalQueryReadinessError(
                "fundamental query worker registry differs"
            )
        for query_id, accumulator in result.queries.items():
            combined[query_id].merge(accumulator)
    query_by_id = {query.query_id: query for query in registry.queries}
    query_results = tuple(
        _build_query_result(query_by_id[query_id], combined[query_id])
        for query_id in registry.query_order
    )
    scanned = sum(item.scanned_occurrence_count for item in results)
    targeted = sum(item.concept_occurrence_count for item in query_results)
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": "sec_edgar",
        "implementation_revision": implementation_revision,
        "evaluated_at": evaluated_at,
        "registry_contract_version": registry.contract_version,
        "registry_id": registry.registry_id,
        "registry_logical_fingerprint": registry.logical_fingerprint,
        "semantic_census_sha256": semantic_census_sha256,
        "semantic_census_logical_fingerprint": semantic.logical_fingerprint,
        "normalized_manifest_sha256": source_manifest_sha256,
        "normalized_logical_fingerprint": source.logical_fingerprint,
        "normalized_content_fingerprint": source.content_fingerprint,
        "range_start": source.range_start,
        "range_end": source.range_end,
        "source_snapshot_date": source.companyfacts_snapshot_date,
        "source_worker_count": source.worker_count,
        "process_count": process_count,
        "source_occurrence_count": source.occurrence_count,
        "scanned_occurrence_count": scanned,
        "targeted_concept_occurrence_count": targeted,
        "unregistered_concept_occurrence_count": source.occurrence_count - targeted,
        "query_results": query_results,
        "full_source_occurrence_scan": True,
        "query_values_published": False,
        "daily_cartesian_panel_created": False,
        "security_projection_executed": False,
        "security_feature_materialization_authorized": False,
        "strategy_outcome_access_count": 0,
        "research_performance_authorized": False,
        "canonical_data_write_count": 0,
        "membership_write_count": 0,
        "candidate_write_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
        "external_request_count": 0,
    }
    return SecFundamentalQueryReadinessCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _build_query_result(
    query: SecFundamentalQueryV1,
    accumulator: _QueryAccumulator,
) -> SecFundamentalQueryReadinessV1:
    disposition_counts = tuple(
        (name, accumulator.dispositions[name]) for name in _DISPOSITIONS
    )
    selectable = len(accumulator.selectable_filers)
    return SecFundamentalQueryReadinessV1(
        query_id=query.query_id,
        namespace=query.namespace,
        concept_name=query.concept_name,
        concept_occurrence_count=accumulator.concept_occurrences,
        concept_filer_count=len(accumulator.concept_filers),
        disposition_counts=disposition_counts,
        eligible_occurrence_count=accumulator.dispositions["query_eligible"],
        eligible_filer_count=len(accumulator.eligible_filers),
        semantic_period_key_count=accumulator.semantic_period_keys,
        clean_semantic_period_key_count=accumulator.clean_semantic_period_keys,
        quarantined_semantic_period_key_count=(
            accumulator.quarantined_semantic_period_keys
        ),
        exact_duplicate_group_count=accumulator.exact_duplicate_groups,
        exact_duplicate_redundant_occurrence_count=(
            accumulator.exact_duplicate_redundant_occurrences
        ),
        within_accession_conflict_group_count=(
            accumulator.within_accession_conflict_groups
        ),
        same_availability_conflict_group_count=(
            accumulator.same_availability_conflict_groups
        ),
        same_period_end_conflict_group_count=(
            accumulator.same_period_end_conflict_groups
        ),
        selectable_filer_count=selectable,
        readiness_state=(
            "ready_for_projection_census" if selectable else "source_query_blocked"
        ),
    )


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
        raise SecFundamentalQueryReadinessError(
            "fundamental query output target is unsafe"
        )
    partial = parent / f".{target.name}.partial"
    if os.path.lexists(target) or os.path.lexists(partial):
        raise SecFundamentalQueryReadinessError(
            "fundamental query output target already exists"
        )
    return target, partial


def _read_bound_normalized_manifest(
    package_path: Path,
) -> tuple[SecCompanyfactsNormalizedSourceManifestV1, str]:
    """Read the manifest after the semantic census has formally verified its source."""

    package = package_path.absolute()
    if (
        package.is_symlink()
        or not package.is_dir()
        or package.resolve(strict=True) != package
    ):
        raise SecFundamentalQueryReadinessError(
            "fundamental query normalized package is unsafe"
        )
    _require_mode(package, 0o700)
    manifest_path = package / NORMALIZED_MANIFEST_FILE
    _require_regular_mode(manifest_path, 0o400)
    if manifest_path.stat().st_size > MAXIMUM_BOUND_MANIFEST_BYTES:
        raise SecFundamentalQueryReadinessError(
            "fundamental query normalized manifest exceeds byte ceiling"
        )
    raw = manifest_path.read_bytes()
    try:
        manifest = SecCompanyfactsNormalizedSourceManifestV1.model_validate_json(raw)
    except Exception as exc:
        raise SecFundamentalQueryReadinessError(
            "fundamental query normalized manifest is invalid"
        ) from exc
    return manifest, hashlib.sha256(raw).hexdigest()


def _validate_completed_package(path: Path) -> Path:
    package = path.absolute()
    if package.is_symlink() or not package.is_dir() or package.resolve(strict=True) != package:
        raise SecFundamentalQueryReadinessError(
            "fundamental query census package is unsafe"
        )
    _require_mode(package, 0o700)
    return package


def _require_regular_mode(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise SecFundamentalQueryReadinessError(
            "fundamental query census file is unsafe"
        )
    _require_mode(path, mode)


def _require_mode(path: Path, mode: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise SecFundamentalQueryReadinessError(
            "fundamental query census ownership or mode differs"
        )


def _write_exclusive_json(path: Path, value: object) -> None:
    raw = _json_bytes(value) + b"\n"
    if len(raw) > MAXIMUM_CENSUS_BYTES:
        raise SecFundamentalQueryReadinessError(
            "fundamental query census exceeds byte ceiling"
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
