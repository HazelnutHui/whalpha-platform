"""Census cutoff-aware SEC issuer facts through one conservative security class."""

from __future__ import annotations

import bisect
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
from typing import Literal

import pyarrow.compute as pc
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_normalized_source import (
    NormalizedArtifactV1,
    SecCompanyfactsNormalizedSourceManifestV1,
)
from tip_api.providers.sec.fundamental_query_readiness_census import (
    CENSUS_FILE as QUERY_READINESS_CENSUS_FILE,
    _SelectedRow,
    _classify_row,
    _iter_target_rows,
    _read_bound_normalized_manifest,
    read_sec_fundamental_query_readiness_census,
)
from tip_api.providers.sec.fundamental_query_registry import (
    SecFundamentalQueryRegistryV1,
    SecFundamentalQueryV1,
    build_first_sec_fundamental_query_registry,
)
from tip_api.providers.sec.point_in_time_fundamental_selection import _select_core
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.sec_filer_security_link_decision import (
    CONTRACT_VERSION as LINK_CONTRACT_VERSION,
    LINK_ARROW_SCHEMA,
    MANIFEST_FILE as LINK_MANIFEST_FILE,
    MAXIMUM_MANIFEST_BYTES as LINK_MAXIMUM_MANIFEST_BYTES,
    PARQUET_FILE as LINK_PARQUET_FILE,
    SecFilerSecurityLinkManifestV1,
    read_sec_filer_security_link_package,
)


CONTRACT_VERSION = "sec-fundamental-projection-readiness-census/1.0"
CENSUS_FILE = "census.json"
MAXIMUM_PROCESSES = 8
MAXIMUM_CENSUS_BYTES = 16 * 1024 * 1024
_SHA256 = r"^[0-9a-f]{64}$"
_REVISION = r"^[0-9a-f]{40}$"
_TIERS = (
    "as_operated_next_open",
    "reconstructed_latest_vintage_development_only",
)
_LINK_DISPOSITIONS = (
    "common_link_not_admitted",
    "common_multi_security_cik",
    "common_single_as_operated_next_open",
    "common_single_reconstructed_latest_vintage",
    "link_source_custody_missing",
    "not_common_stock",
)
_SELECTION_STATUSES = ("not_available", "quarantined", "selected")
_AGE_BUCKETS = ("0_120", "121_240", "241_450", "451_730", "731_plus")
_LINK_COLUMNS = (
    "contract_version",
    "as_of_date",
    "instrument_id",
    "instrument_type",
    "sec_cik",
    "decision_status",
    "point_in_time_eligibility",
    "source_observed_at",
    "issuer_projection_authorized",
)


class SecFundamentalProjectionReadinessError(RuntimeError):
    """Raised when SEC projection readiness cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecProjectionQueryCountsV1(_FrozenModel):
    query_id: str = Field(pattern=r"^[a-z0-9_]+_v1$")
    selection_status_counts: tuple[tuple[str, int], ...]

    @model_validator(mode="after")
    def counts_reconcile(self) -> "SecProjectionQueryCountsV1":
        if tuple(name for name, _ in self.selection_status_counts) != _SELECTION_STATUSES:
            raise ValueError("projection query selection order differs")
        if any(value < 0 for _, value in self.selection_status_counts):
            raise ValueError("projection query selection count is negative")
        return self


class SecProjectionSessionSummaryV1(_FrozenModel):
    signal_session: date
    evaluated_session: date
    cutoff_at: datetime
    evidence_tier: Literal[
        "as_operated_next_open",
        "reconstructed_latest_vintage_development_only",
    ]
    projection_class_row_count: int = Field(ge=0)
    query_counts: tuple[SecProjectionQueryCountsV1, ...]

    @field_validator("cutoff_at")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def summary_reconciles(self) -> "SecProjectionSessionSummaryV1":
        registry = build_first_sec_fundamental_query_registry()
        if tuple(item.query_id for item in self.query_counts) != registry.query_order:
            raise ValueError("projection session query order differs")
        if any(
            sum(value for _, value in item.selection_status_counts)
            != self.projection_class_row_count
            for item in self.query_counts
        ):
            raise ValueError("projection session query denominator differs")
        return self


class SecProjectionQueryTierResultV1(_FrozenModel):
    query_id: str = Field(pattern=r"^[a-z0-9_]+_v1$")
    evidence_tier: Literal[
        "as_operated_next_open",
        "reconstructed_latest_vintage_development_only",
    ]
    projection_class_row_count: int = Field(ge=0)
    selection_status_counts: tuple[tuple[str, int], ...]
    nonselection_reason_counts: tuple[tuple[str, int], ...]
    selected_distinct_instrument_count: int = Field(ge=0)
    selected_session_count: int = Field(ge=0)
    selected_age_calendar_day_counts: tuple[tuple[str, int], ...]

    @model_validator(mode="after")
    def result_reconciles(self) -> "SecProjectionQueryTierResultV1":
        if tuple(name for name, _ in self.selection_status_counts) != _SELECTION_STATUSES:
            raise ValueError("projection result selection order differs")
        if tuple(name for name, _ in self.selected_age_calendar_day_counts) != _AGE_BUCKETS:
            raise ValueError("projection result age order differs")
        if (
            self.nonselection_reason_counts
            != tuple(sorted(self.nonselection_reason_counts))
            or any(value < 1 for _, value in self.nonselection_reason_counts)
        ):
            raise ValueError("projection result reason counts differ")
        if (
            sum(value for _, value in self.selection_status_counts)
            != self.projection_class_row_count
        ):
            raise ValueError("projection result denominator differs")
        selected = dict(self.selection_status_counts)["selected"]
        nonselected = self.projection_class_row_count - selected
        if sum(value for _, value in self.nonselection_reason_counts) != nonselected:
            raise ValueError("projection result reason denominator differs")
        if sum(value for _, value in self.selected_age_calendar_day_counts) != selected:
            raise ValueError("projection result age denominator differs")
        if self.selected_distinct_instrument_count > selected:
            raise ValueError("projection result distinct instruments differ")
        if (selected == 0) != (self.selected_session_count == 0):
            raise ValueError("projection result selected sessions differ")
        return self


class SecFundamentalProjectionReadinessCensusV1(_FrozenModel):
    contract_version: Literal[
        "sec-fundamental-projection-readiness-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    implementation_revision: str = Field(pattern=_REVISION)
    evaluated_at: datetime
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str = Field(min_length=1)
    projection_class: Literal["single_common_security_per_cik_v1"] = (
        "single_common_security_per_cik_v1"
    )
    registry_logical_fingerprint: str = Field(pattern=_SHA256)
    query_readiness_census_sha256: str = Field(pattern=_SHA256)
    query_readiness_logical_fingerprint: str = Field(pattern=_SHA256)
    normalized_logical_fingerprint: str = Field(pattern=_SHA256)
    normalized_content_fingerprint: str = Field(pattern=_SHA256)
    link_manifest_sha256: str = Field(pattern=_SHA256)
    link_logical_fingerprint: str = Field(pattern=_SHA256)
    link_content_fingerprint: str = Field(pattern=_SHA256)
    range_start: date
    range_end: date
    session_count: int = Field(ge=1)
    link_row_count: int = Field(ge=1)
    scanned_link_row_count: int = Field(ge=1)
    link_disposition_counts: tuple[tuple[str, int], ...]
    query_selection_evaluation_count: int = Field(ge=0)
    query_tier_results: tuple[SecProjectionQueryTierResultV1, ...]
    session_summaries: tuple[SecProjectionSessionSummaryV1, ...]
    full_link_row_scan: Literal[True] = True
    issuer_values_retained: Literal[False] = False
    security_fact_rows_retained: Literal[False] = False
    daily_cartesian_panel_created: Literal[False] = False
    feature_materialization_authorized: Literal[False] = False
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
    def census_reconciles(self) -> "SecFundamentalProjectionReadinessCensusV1":
        registry = build_first_sec_fundamental_query_registry()
        if (
            self.range_end < self.range_start
            or self.scanned_link_row_count != self.link_row_count
            or tuple(name for name, _ in self.link_disposition_counts)
            != _LINK_DISPOSITIONS
            or sum(value for _, value in self.link_disposition_counts)
            != self.link_row_count
            or self.registry_logical_fingerprint != registry.logical_fingerprint
        ):
            raise ValueError("projection census denominator or binding differs")
        expected_pairs = tuple(
            (query_id, tier) for query_id in registry.query_order for tier in _TIERS
        )
        if tuple(
            (item.query_id, item.evidence_tier) for item in self.query_tier_results
        ) != expected_pairs:
            raise ValueError("projection census query-tier order differs")
        observed_session_pairs = tuple(
            (summary.signal_session, summary.evidence_tier)
            for summary in self.session_summaries
        )
        if observed_session_pairs != tuple(
            sorted(observed_session_pairs, key=_session_tier_key)
        ):
            raise ValueError("projection census session summary order differs")
        if len(self.session_summaries) != self.session_count * len(_TIERS):
            raise ValueError("projection census session summary count differs")
        session_dates = tuple(
            item.signal_session
            for item in self.session_summaries
            if item.evidence_tier == _TIERS[0]
        )
        if (
            session_dates != tuple(sorted(set(session_dates)))
            or not session_dates
            or session_dates[0] != self.range_start
            or session_dates[-1] != self.range_end
        ):
            raise ValueError("projection census session range differs")
        expected_session_pairs = tuple(
            (session, tier) for session in session_dates for tier in _TIERS
        )
        if observed_session_pairs != expected_session_pairs:
            raise ValueError("projection census session-tier membership differs")
        result_by_pair = {
            (item.query_id, item.evidence_tier): item
            for item in self.query_tier_results
        }
        for query_id, tier in expected_pairs:
            summaries = tuple(
                item for item in self.session_summaries if item.evidence_tier == tier
            )
            aggregate = Counter()
            for summary in summaries:
                query_counts = next(
                    item for item in summary.query_counts if item.query_id == query_id
                )
                aggregate.update(dict(query_counts.selection_status_counts))
            result = result_by_pair[(query_id, tier)]
            if (
                _ordered(aggregate, _SELECTION_STATUSES)
                != result.selection_status_counts
                or sum(item.projection_class_row_count for item in summaries)
                != result.projection_class_row_count
                or sum(
                    1
                    for summary in summaries
                    if dict(
                        next(
                            item
                            for item in summary.query_counts
                            if item.query_id == query_id
                        ).selection_status_counts
                    )["selected"]
                    > 0
                )
                != result.selected_session_count
            ):
                raise ValueError("projection census session aggregation differs")
        disposition_by_tier = {
            _TIERS[0]: "common_single_as_operated_next_open",
            _TIERS[1]: "common_single_reconstructed_latest_vintage",
        }
        for tier, disposition in disposition_by_tier.items():
            expected_count = dict(self.link_disposition_counts)[disposition]
            if any(
                item.projection_class_row_count != expected_count
                for item in self.query_tier_results
                if item.evidence_tier == tier
            ):
                raise ValueError("projection census tier denominator differs")
        projected_rows = sum(
            dict(self.link_disposition_counts)[name]
            for name in (
                "common_single_as_operated_next_open",
                "common_single_reconstructed_latest_vintage",
            )
        )
        if self.query_selection_evaluation_count != projected_rows * len(
            registry.query_order
        ):
            raise ValueError("projection census evaluation denominator differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("projection census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecFundamentalProjectionReadinessResult:
    package_path: Path
    census: SecFundamentalProjectionReadinessCensusV1


@dataclass(frozen=True, slots=True)
class _TimelinePoint:
    eligible_session: date
    status: Literal["selected", "not_available", "quarantined"]
    reason: str | None
    period_end: date | None


@dataclass(frozen=True, slots=True)
class _Timeline:
    sessions: tuple[date, ...]
    points: tuple[_TimelinePoint, ...]


@dataclass(frozen=True, slots=True)
class _TimelineWorkerResult:
    worker_index: int
    scanned_occurrence_count: int
    timelines: dict[tuple[str, str], _Timeline]


@dataclass(slots=True)
class _TierAccumulator:
    statuses: Counter[str] = field(default_factory=Counter)
    reasons: Counter[str] = field(default_factory=Counter)
    ages: Counter[str] = field(default_factory=Counter)
    instruments: set[str] = field(default_factory=set)
    selected_sessions: set[date] = field(default_factory=set)


def build_sec_fundamental_projection_readiness_census(
    *,
    normalized_package_path: Path,
    query_readiness_package_path: Path,
    semantic_census_package_path: Path,
    semantic_link_package_path: Path,
    link_package_path: Path,
    data_root: Path,
    output_package_path: Path,
    process_count: int,
    implementation_revision: str,
    evaluated_at: datetime | None = None,
) -> SecFundamentalProjectionReadinessResult:
    """Build one immutable aggregate projection-readiness census."""

    if re.fullmatch(_REVISION, implementation_revision) is None:
        raise SecFundamentalProjectionReadinessError(
            "projection census implementation revision is invalid"
        )
    if process_count < 1 or process_count > MAXIMUM_PROCESSES:
        raise SecFundamentalProjectionReadinessError(
            "projection census process count is invalid"
        )
    readiness = read_sec_fundamental_query_readiness_census(
        package_path=query_readiness_package_path,
        normalized_package_path=normalized_package_path,
        semantic_census_package_path=semantic_census_package_path,
        semantic_link_package_path=semantic_link_package_path,
        data_root=data_root,
    ).census
    source, _ = _read_bound_normalized_manifest(normalized_package_path)
    link, link_manifest_sha256 = _read_bound_link_manifest(link_package_path)
    registry = build_first_sec_fundamental_query_registry()
    target, partial = _validate_output_target(output_package_path)
    os.mkdir(partial, mode=0o700)
    try:
        timeline_results = _build_timeline_index(
            normalized_package_path=normalized_package_path,
            source=source,
            registry=registry,
            process_count=process_count,
        )
        timelines: dict[tuple[str, str], _Timeline] = {}
        for result in timeline_results:
            overlap = set(timelines).intersection(result.timelines)
            if overlap:
                raise SecFundamentalProjectionReadinessError(
                    "projection timeline CIK crosses source workers"
                )
            timelines.update(result.timelines)
        if sum(item.scanned_occurrence_count for item in timeline_results) != (
            source.occurrence_count
        ):
            raise SecFundamentalProjectionReadinessError(
                "projection timeline source denominator differs"
            )
        census = _scan_link_projection(
            link_package_path=link_package_path,
            link=link,
            link_manifest_sha256=link_manifest_sha256,
            timelines=timelines,
            registry=registry,
            readiness_census_sha256=_sha256_file(
                query_readiness_package_path / QUERY_READINESS_CENSUS_FILE
            ),
            readiness_logical_fingerprint=readiness.logical_fingerprint,
            source=source,
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
    return read_sec_fundamental_projection_readiness_census(
        package_path=target,
        normalized_package_path=normalized_package_path,
        query_readiness_package_path=query_readiness_package_path,
        semantic_census_package_path=semantic_census_package_path,
        semantic_link_package_path=semantic_link_package_path,
        link_package_path=link_package_path,
        data_root=data_root,
        formal_read_workers=process_count,
    )


def read_sec_fundamental_projection_readiness_census(
    *,
    package_path: Path,
    normalized_package_path: Path,
    query_readiness_package_path: Path,
    semantic_census_package_path: Path,
    semantic_link_package_path: Path,
    link_package_path: Path,
    data_root: Path,
    formal_read_workers: int = 1,
) -> SecFundamentalProjectionReadinessResult:
    """Formally reread the report and both transitive input families."""

    package = _validate_completed_package(package_path)
    if {item.name for item in package.iterdir()} != {CENSUS_FILE}:
        raise SecFundamentalProjectionReadinessError(
            "projection census package members differ"
        )
    census_path = package / CENSUS_FILE
    _require_regular_mode(census_path, 0o400)
    if census_path.stat().st_size > MAXIMUM_CENSUS_BYTES:
        raise SecFundamentalProjectionReadinessError(
            "projection census exceeds byte ceiling"
        )
    try:
        census = SecFundamentalProjectionReadinessCensusV1.model_validate_json(
            census_path.read_bytes()
        )
    except Exception as exc:
        raise SecFundamentalProjectionReadinessError(
            "projection census report is invalid"
        ) from exc
    readiness = read_sec_fundamental_query_readiness_census(
        package_path=query_readiness_package_path,
        normalized_package_path=normalized_package_path,
        semantic_census_package_path=semantic_census_package_path,
        semantic_link_package_path=semantic_link_package_path,
        data_root=data_root,
    ).census
    link = read_sec_filer_security_link_package(
        package_path=link_package_path,
        data_root=data_root,
        formal_read_workers=formal_read_workers,
    ).manifest
    calendar = ExchangeCalendar()
    signal_sessions = calendar.sessions_in_range(census.range_start, census.range_end)
    expected_clock = {
        session: (
            calendar.next_session(session),
            calendar.session_open(calendar.next_session(session)),
        )
        for session in signal_sessions
    }
    if (
        census.registry_logical_fingerprint
        != build_first_sec_fundamental_query_registry().logical_fingerprint
        or census.query_readiness_census_sha256
        != _sha256_file(query_readiness_package_path / QUERY_READINESS_CENSUS_FILE)
        or census.query_readiness_logical_fingerprint != readiness.logical_fingerprint
        or census.normalized_logical_fingerprint
        != readiness.normalized_logical_fingerprint
        or census.normalized_content_fingerprint
        != readiness.normalized_content_fingerprint
        or census.link_manifest_sha256
        != _sha256_file(link_package_path / LINK_MANIFEST_FILE)
        or census.link_logical_fingerprint != link.logical_fingerprint
        or census.link_content_fingerprint != link.content_fingerprint
        or census.range_start != link.range_start
        or census.range_end != link.range_end
        or census.session_count != link.session_count
        or census.link_row_count != link.row_count
        or census.calendar_version != calendar.calendar_version
        or tuple(
            item.signal_session
            for item in census.session_summaries
            if item.evidence_tier == _TIERS[0]
        )
        != signal_sessions
        or any(
            (item.evaluated_session, item.cutoff_at)
            != expected_clock[item.signal_session]
            for item in census.session_summaries
        )
    ):
        raise SecFundamentalProjectionReadinessError(
            "projection census input binding differs"
        )
    return SecFundamentalProjectionReadinessResult(package_path=package, census=census)


def _build_timeline_index(
    *,
    normalized_package_path: Path,
    source: SecCompanyfactsNormalizedSourceManifestV1,
    registry: SecFundamentalQueryRegistryV1,
    process_count: int,
) -> tuple[_TimelineWorkerResult, ...]:
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
        results = tuple(_timeline_worker(item) for item in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=process_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            results = tuple(executor.map(_timeline_worker, arguments))
    results = tuple(sorted(results, key=lambda item: item.worker_index))
    if tuple(item.worker_index for item in results) != tuple(range(source.worker_count)):
        raise SecFundamentalProjectionReadinessError(
            "projection timeline worker order differs"
        )
    return results


def _timeline_worker(
    argument: tuple[
        str,
        int,
        tuple[NormalizedArtifactV1, ...],
        SecFundamentalQueryRegistryV1,
    ],
) -> _TimelineWorkerResult:
    package_raw, worker_index, artifacts, registry = argument
    by_concept = {
        (query.namespace, query.concept_name): query for query in registry.queries
    }
    query_by_id = {query.query_id: query for query in registry.queries}
    streams = tuple(
        _iter_target_rows(
            Path(package_raw) / artifact.relative_path,
            artifact,
            frozenset(by_concept),
        )
        for artifact in sorted(artifacts, key=lambda item: item.filed_year or 0)
    )
    if not streams:
        raise SecFundamentalProjectionReadinessError(
            "projection timeline worker has no occurrence artifacts"
        )
    calendar = ExchangeCalendar()
    cutoff_by_session: dict[date, datetime] = {}
    timelines: dict[tuple[str, str], _Timeline] = {}
    current_cik: str | None = None
    rows_by_query: dict[str, list[_SelectedRow]] = defaultdict(list)
    for _, row in heapq.merge(*streams, key=lambda item: item[0]):
        if current_cik is not None and row.companyfacts_cik != current_cik:
            _flush_timeline_filer(
                current_cik,
                rows_by_query,
                timelines,
                query_by_id,
                calendar,
                cutoff_by_session,
            )
            rows_by_query = defaultdict(list)
        current_cik = row.companyfacts_cik
        query = by_concept[(row.namespace, row.concept_name)]
        if _classify_row(row, query) == "query_eligible":
            rows_by_query[query.query_id].append(row)
    if current_cik is not None:
        _flush_timeline_filer(
            current_cik,
            rows_by_query,
            timelines,
            query_by_id,
            calendar,
            cutoff_by_session,
        )
    return _TimelineWorkerResult(
        worker_index=worker_index,
        scanned_occurrence_count=sum(item.row_count for item in artifacts),
        timelines=timelines,
    )


def _flush_timeline_filer(
    cik: str,
    rows_by_query: dict[str, list[_SelectedRow]],
    timelines: dict[tuple[str, str], _Timeline],
    query_by_id: dict[str, SecFundamentalQueryV1],
    calendar: ExchangeCalendar,
    cutoff_by_session: dict[date, datetime],
) -> None:
    for query_id, raw_rows in rows_by_query.items():
        rows = tuple(raw_rows)
        if any(
            row.companyfacts_cik != cik or row.signal_eligible_session is None
            for row in rows
        ):
            raise SecFundamentalProjectionReadinessError(
                "projection timeline filer rows differ"
            )
        event_sessions = tuple(
            sorted(
                {
                    row.signal_eligible_session
                    for row in rows
                    if row.signal_eligible_session is not None
                }
            )
        )
        points: list[_TimelinePoint] = []
        prior: tuple[str, str | None, date | None] | None = None
        for event_session in event_sessions:
            cutoff = cutoff_by_session.get(event_session)
            if cutoff is None:
                cutoff = calendar.session_open(event_session)
                cutoff_by_session[event_session] = cutoff
            core = _select_core(
                rows=rows,
                query=query_by_id[query_id],
                evaluated_session=event_session,
                cutoff_at=cutoff,
                rows_are_query_eligible=True,
            )
            reason = core.reasons[0] if core.reasons else None
            state = (core.status, reason, core.end_date)
            if state != prior:
                points.append(
                    _TimelinePoint(
                        eligible_session=event_session,
                        status=core.status,
                        reason=reason,
                        period_end=core.end_date,
                    )
                )
                prior = state
        if not points:
            raise SecFundamentalProjectionReadinessError(
                "projection timeline has no selection states"
            )
        key = (cik, query_id)
        if key in timelines:
            raise SecFundamentalProjectionReadinessError(
                "projection timeline key is duplicated"
            )
        timelines[key] = _Timeline(
            sessions=tuple(item.eligible_session for item in points),
            points=tuple(points),
        )


def _scan_link_projection(
    *,
    link_package_path: Path,
    link: SecFilerSecurityLinkManifestV1,
    link_manifest_sha256: str,
    timelines: dict[tuple[str, str], _Timeline],
    registry: SecFundamentalQueryRegistryV1,
    readiness_census_sha256: str,
    readiness_logical_fingerprint: str,
    source: SecCompanyfactsNormalizedSourceManifestV1,
    implementation_revision: str,
    evaluated_at: datetime,
) -> SecFundamentalProjectionReadinessCensusV1:
    calendar = ExchangeCalendar()
    if link.calendar_version != calendar.calendar_version:
        raise SecFundamentalProjectionReadinessError(
            "projection link calendar version differs"
        )
    dispositions: Counter[str] = Counter()
    accumulators = {
        (query_id, tier): _TierAccumulator()
        for query_id in registry.query_order
        for tier in _TIERS
    }
    summaries: list[SecProjectionSessionSummaryV1] = []
    scanned = 0
    for evidence in link.sessions:
        next_session = calendar.next_session(evidence.as_of_date)
        cutoff = calendar.session_open(next_session)
        tier = _session_evidence_tier(evidence, cutoff)
        path = link_package_path / evidence.relative_path
        _require_regular_mode(path, 0o400)
        if (
            path.stat().st_size != evidence.byte_size
            or _sha256_file(path) != evidence.physical_sha256
        ):
            raise SecFundamentalProjectionReadinessError(
                "projection link artifact identity differs"
            )
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != LINK_ARROW_SCHEMA:
            raise SecFundamentalProjectionReadinessError(
                "projection link artifact schema differs"
            )
        table = parquet.read(columns=list(_LINK_COLUMNS))
        if table.num_rows != evidence.row_count:
            raise SecFundamentalProjectionReadinessError(
                "projection link row denominator differs"
            )
        scanned += table.num_rows
        if not pc.all(pc.equal(table["contract_version"], LINK_CONTRACT_VERSION)).as_py():
            raise SecFundamentalProjectionReadinessError(
                "projection link contract differs"
            )
        if not pc.all(pc.equal(table["as_of_date"], evidence.as_of_date)).as_py():
            raise SecFundamentalProjectionReadinessError(
                "projection link session differs"
            )
        if not pc.all(
            pc.equal(
                table["point_in_time_eligibility"],
                evidence.point_in_time_eligibility,
            )
        ).as_py():
            raise SecFundamentalProjectionReadinessError(
                "projection link knowledge class differs"
            )
        observed_times_match = (
            pc.all(pc.is_null(table["source_observed_at"])).as_py()
            if evidence.source_observed_at is None
            else pc.all(
                pc.equal(table["source_observed_at"], evidence.source_observed_at)
            ).as_py()
        )
        if not observed_times_match:
            raise SecFundamentalProjectionReadinessError(
                "projection link source clock differs"
            )
        if pc.any(table["issuer_projection_authorized"]).as_py():
            raise SecFundamentalProjectionReadinessError(
                "projection source unexpectedly grants issuer projection"
            )
        rows = table.to_pydict()
        common_cik_counts = Counter(
            cik
            for instrument_type, status, cik in zip(
                rows["instrument_type"],
                rows["decision_status"],
                rows["sec_cik"],
                strict=True,
            )
            if instrument_type == "common_stock"
            and status == "admitted_unique_cik"
            and cik is not None
        )
        session_counts = {
            evidence_tier: {
                query_id: Counter() for query_id in registry.query_order
            }
            for evidence_tier in _TIERS
        }
        session_class_counts: Counter[str] = Counter()
        for index in range(table.num_rows):
            instrument_type = rows["instrument_type"][index]
            status = rows["decision_status"][index]
            cik = rows["sec_cik"][index]
            instrument_id = rows["instrument_id"][index]
            if tier is None:
                dispositions["link_source_custody_missing"] += 1
                continue
            if instrument_type != "common_stock":
                dispositions["not_common_stock"] += 1
                continue
            if status != "admitted_unique_cik" or cik is None:
                dispositions["common_link_not_admitted"] += 1
                continue
            if common_cik_counts[cik] != 1:
                dispositions["common_multi_security_cik"] += 1
                continue
            disposition = (
                "common_single_as_operated_next_open"
                if tier == _TIERS[0]
                else "common_single_reconstructed_latest_vintage"
            )
            dispositions[disposition] += 1
            session_class_counts[tier] += 1
            for query_id in registry.query_order:
                point = _lookup_timeline(
                    timelines.get((cik, query_id)),
                    next_session,
                )
                session_counts[tier][query_id][point.status] += 1
                accumulator = accumulators[(query_id, tier)]
                accumulator.statuses[point.status] += 1
                if point.status == "selected":
                    if point.period_end is None:
                        raise SecFundamentalProjectionReadinessError(
                            "selected projection timeline lacks period end"
                        )
                    accumulator.ages[_age_bucket((next_session - point.period_end).days)] += 1
                    accumulator.instruments.add(instrument_id)
                    accumulator.selected_sessions.add(evidence.as_of_date)
                elif point.reason is None:
                    raise SecFundamentalProjectionReadinessError(
                        "unselected projection timeline lacks reason"
                    )
                else:
                    accumulator.reasons[point.reason] += 1
        for evidence_tier in _TIERS:
            projection_count = session_class_counts[evidence_tier]
            summaries.append(
                SecProjectionSessionSummaryV1(
                    signal_session=evidence.as_of_date,
                    evaluated_session=next_session,
                    cutoff_at=cutoff,
                    evidence_tier=evidence_tier,
                    projection_class_row_count=projection_count,
                    query_counts=tuple(
                        SecProjectionQueryCountsV1(
                            query_id=query_id,
                            selection_status_counts=_ordered(
                                session_counts[evidence_tier][query_id],
                                _SELECTION_STATUSES,
                            ),
                        )
                        for query_id in registry.query_order
                    ),
                )
            )
    query_results = tuple(
        SecProjectionQueryTierResultV1(
            query_id=query_id,
            evidence_tier=tier,
            projection_class_row_count=sum(
                accumulator.statuses.values()
            ),
            selection_status_counts=_ordered(
                accumulator.statuses,
                _SELECTION_STATUSES,
            ),
            nonselection_reason_counts=tuple(sorted(accumulator.reasons.items())),
            selected_distinct_instrument_count=len(accumulator.instruments),
            selected_session_count=len(accumulator.selected_sessions),
            selected_age_calendar_day_counts=_ordered(
                accumulator.ages,
                _AGE_BUCKETS,
            ),
        )
        for query_id in registry.query_order
        for tier in _TIERS
        for accumulator in (accumulators[(query_id, tier)],)
    )
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "implementation_revision": implementation_revision,
        "evaluated_at": evaluated_at,
        "calendar_id": "XNYS",
        "calendar_version": calendar.calendar_version,
        "projection_class": "single_common_security_per_cik_v1",
        "registry_logical_fingerprint": registry.logical_fingerprint,
        "query_readiness_census_sha256": readiness_census_sha256,
        "query_readiness_logical_fingerprint": readiness_logical_fingerprint,
        "normalized_logical_fingerprint": source.logical_fingerprint,
        "normalized_content_fingerprint": source.content_fingerprint,
        "link_manifest_sha256": link_manifest_sha256,
        "link_logical_fingerprint": link.logical_fingerprint,
        "link_content_fingerprint": link.content_fingerprint,
        "range_start": link.range_start,
        "range_end": link.range_end,
        "session_count": link.session_count,
        "link_row_count": link.row_count,
        "scanned_link_row_count": scanned,
        "link_disposition_counts": _ordered(dispositions, _LINK_DISPOSITIONS),
        "query_selection_evaluation_count": sum(
            item.projection_class_row_count for item in query_results
        ),
        "query_tier_results": query_results,
        "session_summaries": tuple(summaries),
        "full_link_row_scan": True,
        "issuer_values_retained": False,
        "security_fact_rows_retained": False,
        "daily_cartesian_panel_created": False,
        "feature_materialization_authorized": False,
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
    return SecFundamentalProjectionReadinessCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _lookup_timeline(timeline: _Timeline | None, session: date) -> _TimelinePoint:
    if timeline is None:
        return _TimelinePoint(
            eligible_session=session,
            status="not_available",
            reason="issuer_query_absent",
            period_end=None,
        )
    index = bisect.bisect_right(timeline.sessions, session) - 1
    if index < 0:
        return _TimelinePoint(
            eligible_session=session,
            status="not_available",
            reason="issuer_query_not_yet_available",
            period_end=None,
        )
    return timeline.points[index]


def _session_evidence_tier(evidence, cutoff: datetime) -> str | None:
    if evidence.point_in_time_eligibility == "source_custody_missing":
        return None
    if (
        evidence.point_in_time_eligibility == "eligible_at_source_observed_at"
        and evidence.source_observed_at is not None
        and evidence.source_observed_at <= cutoff
    ):
        return _TIERS[0]
    return _TIERS[1]


def _age_bucket(days: int) -> str:
    if days < 0:
        raise SecFundamentalProjectionReadinessError(
            "projection selected period follows evaluated session"
        )
    if days <= 120:
        return "0_120"
    if days <= 240:
        return "121_240"
    if days <= 450:
        return "241_450"
    if days <= 730:
        return "451_730"
    return "731_plus"


def _read_bound_link_manifest(
    package_path: Path,
) -> tuple[SecFilerSecurityLinkManifestV1, str]:
    package = _validate_completed_package(package_path)
    manifest_path = package / LINK_MANIFEST_FILE
    _require_regular_mode(manifest_path, 0o400)
    if manifest_path.stat().st_size > LINK_MAXIMUM_MANIFEST_BYTES:
        raise SecFundamentalProjectionReadinessError(
            "projection link manifest exceeds byte ceiling"
        )
    raw = manifest_path.read_bytes()
    try:
        manifest = SecFilerSecurityLinkManifestV1.model_validate_json(raw)
    except Exception as exc:
        raise SecFundamentalProjectionReadinessError(
            "projection link manifest is invalid"
        ) from exc
    expected = {
        LINK_MANIFEST_FILE,
        *(f"as_of_date={item.as_of_date.isoformat()}" for item in manifest.sessions),
    }
    if {item.name for item in package.iterdir()} != expected:
        raise SecFundamentalProjectionReadinessError(
            "projection link package members differ"
        )
    return manifest, hashlib.sha256(raw).hexdigest()


def _session_tier_key(value: tuple[date, str]) -> tuple[date, int]:
    return value[0], _TIERS.index(value[1])


def _ordered(
    counter: Counter[str],
    names: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple((name, counter[name]) for name in names)


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
        raise SecFundamentalProjectionReadinessError(
            "projection output target is unsafe"
        )
    partial = parent / f".{target.name}.partial"
    if os.path.lexists(target) or os.path.lexists(partial):
        raise SecFundamentalProjectionReadinessError(
            "projection output target already exists"
        )
    return target, partial


def _validate_completed_package(path: Path) -> Path:
    package = path.absolute()
    if package.is_symlink() or not package.is_dir() or package.resolve(strict=True) != package:
        raise SecFundamentalProjectionReadinessError(
            "projection package is unsafe"
        )
    _require_mode(package, 0o700)
    return package


def _require_regular_mode(path: Path, mode: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise SecFundamentalProjectionReadinessError(
            "projection file is unsafe"
        )
    _require_mode(path, mode)


def _require_mode(path: Path, mode: int) -> None:
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != mode:
        raise SecFundamentalProjectionReadinessError(
            "projection ownership or mode differs"
        )


def _write_exclusive_json(path: Path, value: object) -> None:
    raw = _json_bytes(value) + b"\n"
    if len(raw) > MAXIMUM_CENSUS_BYTES:
        raise SecFundamentalProjectionReadinessError(
            "projection census exceeds byte ceiling"
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
