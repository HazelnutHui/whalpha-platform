"""Bounded local SEC cash-quality source-readiness census."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_earnings_quality_query_registry import (
    SecCashQualitySourceQueryV1,
    quant_research_sec_cash_quality_query_registry_v1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import (
    SecCashQualityQueryCensusResultV1,
    SecCashQualitySourceReadinessCensusV1,
    SecCashQualitySourceReadinessPlanV1,
    SecCashQualitySourceReadinessVerificationV1,
    canonical_census_bytes,
    census_fingerprint,
)
from tip_api.providers.sec.companyfacts_normalized_source import (
    SecCompanyfactsNormalizedSourceResult,
    read_sec_companyfacts_normalized_source,
)
_COLUMNS = (
    "contract_version",
    "source_occurrence_id",
    "companyfacts_cik",
    "namespace",
    "concept_name",
    "unit",
    "start_date",
    "end_date",
    "value_kind",
    "value_text",
    "accession_number",
    "fiscal_year",
    "fiscal_period",
    "form",
    "filed_date",
    "filing_clock_admission_status",
    "source_available_at_utc",
    "signal_eligible_session",
    "normalization_status",
)
_PERIODS = frozenset(("FY", "Q1", "Q2", "Q3"))


class SecCashQualitySourceReadinessCensusError(RuntimeError):
    """Raised when the bounded local census cannot fail closed."""


@dataclass(frozen=True, slots=True)
class _SelectionState:
    status: Literal["selected", "not_available", "quarantined"]
    reasons: tuple[str, ...] = ()
    accession_number: str | None = None


@dataclass(frozen=True, slots=True)
class _OccurrenceRow:
    source_occurrence_id: str
    companyfacts_cik: str
    namespace: str
    concept_name: str
    unit: str
    start_date: date | None
    end_date: date | None
    value_kind: str
    value_text: str | None
    accession_number: str
    fiscal_year: int | None
    fiscal_period: str | None
    form: str
    filed_date: date
    filing_clock_admission_status: str
    source_available_at: datetime | None
    signal_eligible_session: date | None
    normalization_status: str
    query_candidate: bool


@dataclass(frozen=True, slots=True)
class SecCashQualityPreparedTargetEvidence:
    source: SecCompanyfactsNormalizedSourceResult
    by_worker: dict[str, list[_OccurrenceRow]]
    target_records: tuple[tuple[dict[str, object], str], ...]
    dispositions: dict[str, Counter[str]]
    target_occurrences: Counter[str]
    target_count: int
    earliest_available: datetime | None
    latest_available: datetime | None


def prepare_sec_cash_quality_target_evidence(
    *,
    normalized_package_path: Path,
    plan: SecCashQualitySourceReadinessPlanV1,
) -> SecCashQualityPreparedTargetEvidence:
    """Formally reread once and retain the bounded registered-concept evidence."""

    registry = quant_research_sec_cash_quality_query_registry_v1()
    query_by_concept = {query.concept_name: query for query in registry.queries}
    by_worker: dict[str, list[_OccurrenceRow]] = defaultdict(list)
    records: list[tuple[dict[str, object], str]] = []
    dispositions = {query.query_id: Counter() for query in registry.queries}
    target_occurrences: Counter[str] = Counter()
    earliest_available: datetime | None = None
    latest_available: datetime | None = None

    def retain(artifact, batch: pa.RecordBatch) -> None:
        nonlocal earliest_available, latest_available
        worker = f"worker={artifact.worker_index:02d}"
        for raw in batch.select(list(_COLUMNS)).to_pylist():
            query = query_by_concept[str(raw["concept_name"])]
            disposition = _classify_raw_occurrence(
                raw=raw,
                query=query,
                plan=plan,
            )
            row = _occurrence(
                raw,
                query_candidate=disposition == "query_candidate",
            )
            records.append((raw, disposition))
            target_occurrences[query.query_id] += 1
            dispositions[query.query_id][disposition] += 1
            if row.source_available_at is not None:
                earliest_available = (
                    row.source_available_at
                    if earliest_available is None
                    else min(earliest_available, row.source_available_at)
                )
                latest_available = (
                    row.source_available_at
                    if latest_available is None
                    else max(latest_available, row.source_available_at)
                )
            by_worker[worker].append(row)
            if len(records) > plan.budget.maximum_target_occurrence_count:
                raise SecCashQualitySourceReadinessCensusError(
                    "cash-quality census target budget exceeded"
                )
            if len(by_worker[worker]) > plan.budget.maximum_rows_retained_per_worker:
                raise SecCashQualitySourceReadinessCensusError(
                    "cash-quality census worker retention budget exceeded"
                )

    source = read_sec_companyfacts_normalized_source(
        package_path=normalized_package_path,
        occurrence_concept_filter=frozenset(query_by_concept),
        occurrence_batch_consumer=retain,
    )
    plan_artifacts = {item.relative_path: item for item in plan.occurrence_artifacts}
    manifest_artifacts = {
        item.relative_path: item
        for item in source.manifest.artifacts
        if item.artifact_kind == "occurrence"
    }
    if plan_artifacts != {
        key: type(plan_artifacts[key])(
            relative_path=value.relative_path,
            row_count=value.row_count,
            physical_sha256=value.physical_sha256,
            logical_fingerprint=value.logical_fingerprint,
        )
        for key, value in manifest_artifacts.items()
    }:
        raise SecCashQualitySourceReadinessCensusError(
            "cash-quality census artifact binding differs"
        )
    return SecCashQualityPreparedTargetEvidence(
        source=source,
        by_worker=dict(by_worker),
        target_records=tuple(records),
        dispositions=dispositions,
        target_occurrences=target_occurrences,
        target_count=len(records),
        earliest_available=earliest_available,
        latest_available=latest_available,
    )


def run_sec_cash_quality_source_readiness_census(
    *,
    normalized_package_path: Path,
    plan: SecCashQualitySourceReadinessPlanV1,
    traversal_order: Literal["forward", "reverse"] = "forward",
) -> SecCashQualitySourceReadinessCensusV1:
    """Stream one exact local package and retain aggregates, never values."""

    prepared = prepare_sec_cash_quality_target_evidence(
        normalized_package_path=normalized_package_path,
        plan=plan,
    )
    return _run_verified_sec_cash_quality_source_readiness_census(
        normalized_package_path=normalized_package_path,
        plan=plan,
        traversal_order=traversal_order,
        source=prepared.source,
        prepared=prepared,
    )


def _run_verified_sec_cash_quality_source_readiness_census(
    *,
    normalized_package_path: Path,
    plan: SecCashQualitySourceReadinessPlanV1,
    traversal_order: Literal["forward", "reverse"],
    source: SecCompanyfactsNormalizedSourceResult,
    prepared: SecCashQualityPreparedTargetEvidence,
) -> SecCashQualitySourceReadinessCensusV1:
    if source.package_path != normalized_package_path:
        raise SecCashQualitySourceReadinessCensusError(
            "cash-quality census verified package path differs"
        )
    manifest = source.manifest
    if (
        manifest.logical_fingerprint != plan.normalized_manifest_fingerprint
        or manifest.content_fingerprint != plan.normalized_content_fingerprint
        or manifest.filing_clock_manifest_fingerprint
        != plan.filing_clock_manifest_fingerprint
        or manifest.occurrence_schema_fingerprint
        != plan.occurrence_schema_fingerprint
        or manifest.occurrence_count != plan.source_occurrence_count
    ):
        raise SecCashQualitySourceReadinessCensusError(
            "cash-quality census source binding differs"
        )
    registry = quant_research_sec_cash_quality_query_registry_v1()
    by_worker = prepared.by_worker
    dispositions = prepared.dispositions
    target_occurrences = prepared.target_occurrences
    scanned_count = plan.source_occurrence_count
    target_count = prepared.target_count
    earliest_available = prepared.earliest_available
    latest_available = prepared.latest_available
    query_endpoint_status = {
        query.query_id: Counter() for query in registry.queries
    }
    query_endpoint_reasons = {
        query.query_id: Counter() for query in registry.queries
    }
    readiness_reasons = Counter()
    fiscal_periods = Counter()
    issuer_ids: set[str] = set()
    observed_endpoints = ready_endpoints = 0
    workers = sorted(by_worker, reverse=traversal_order == "reverse")
    for worker in workers:
        rows_by_cik: dict[str, list[_OccurrenceRow]] = defaultdict(list)
        for row in by_worker[worker]:
            rows_by_cik[row.companyfacts_cik].append(row)
        cik_order = sorted(rows_by_cik, reverse=traversal_order == "reverse")
        for cik in cik_order:
            rows = tuple(rows_by_cik[cik])
            endpoint_rows: dict[
                tuple[int, str, date],
                dict[str, list[_OccurrenceRow]],
            ] = defaultdict(lambda: defaultdict(list))
            q1_rows: dict[
                tuple[int, str], list[_OccurrenceRow]
            ] = defaultdict(list)
            for row in rows:
                if row.fiscal_year is None:
                    continue
                if row.fiscal_period == "Q1":
                    q1_rows[(row.fiscal_year, row.concept_name)].append(row)
                if row.fiscal_period in _PERIODS and row.end_date is not None:
                    endpoint_rows[
                        (row.fiscal_year, row.fiscal_period, row.end_date)
                    ][row.concept_name].append(row)
            endpoints = sorted(
                endpoint_rows,
                reverse=traversal_order == "reverse",
            )
            if endpoints:
                issuer_ids.add(cik)
            for fiscal_year, fiscal_period, period_end in endpoints:
                if fiscal_year is None or period_end is None:
                    raise SecCashQualitySourceReadinessCensusError(
                        "cash-quality census endpoint is incomplete"
                    )
                observed_endpoints += 1
                if observed_endpoints > plan.budget.maximum_observed_endpoint_count:
                    raise SecCashQualitySourceReadinessCensusError(
                        "cash-quality census endpoint budget exceeded"
                    )
                fiscal_periods[str(fiscal_period)] += 1
                origins = _origin_candidates(
                    endpoint_rows=endpoint_rows[
                        (fiscal_year, str(fiscal_period), period_end)
                    ],
                    q1_rows=q1_rows,
                    fiscal_year=fiscal_year,
                    fiscal_period=str(fiscal_period),
                    registry_queries=registry.queries,
                )
                if len(origins) != 1:
                    reason = (
                        "joint_fiscal_year_origin_missing"
                        if not origins
                        else "joint_fiscal_year_origin_ambiguous"
                    )
                    readiness_reasons[reason] += 1
                    for query in registry.queries:
                        status = (
                            "not_available" if not origins else "quarantined"
                        )
                        query_endpoint_status[query.query_id][status] += 1
                        query_endpoint_reasons[query.query_id][reason] += 1
                    continue
                origin = next(iter(origins))
                if period_end < origin:
                    reason = "fiscal_endpoint_precedes_origin"
                    readiness_reasons[reason] += 1
                    for query in registry.queries:
                        query_endpoint_status[query.query_id]["quarantined"] += 1
                        query_endpoint_reasons[query.query_id][reason] += 1
                    continue
                states = tuple(
                    _select_indexed_query(
                        query=query,
                        endpoint_rows=endpoint_rows[
                            (fiscal_year, str(fiscal_period), period_end)
                        ].get(query.concept_name, ()),
                        q1_rows=q1_rows.get(
                            (fiscal_year, query.concept_name), ()
                        ),
                        fiscal_year=fiscal_year,
                        fiscal_period=str(fiscal_period),
                        period_end=period_end,
                        fiscal_year_origin=origin,
                    )
                    for query in registry.queries
                )
                state_by_id = {
                    query.query_id: state
                    for query, state in zip(registry.queries, states, strict=True)
                }
                cash_flow = state_by_id[
                    "operating_cash_flow_fiscal_ytd_and_year_v1"
                ]
                net_income = state_by_id[
                    "net_income_loss_fiscal_ytd_and_year_v1"
                ]
                coherent = (
                    cash_flow.status == "selected"
                    and net_income.status == "selected"
                    and cash_flow.accession_number == net_income.accession_number
                )
                endpoint_reasons = {
                    f"{query.query_id}:{reason}"
                    for query, state in zip(
                        registry.queries, states, strict=True
                    )
                    for reason in state.reasons
                }
                if (
                    cash_flow.status == "selected"
                    and net_income.status == "selected"
                    and not coherent
                ):
                    endpoint_reasons.add("duration_pair_accession_incoherent")
                if all(state.status == "selected" for state in states) and coherent:
                    ready_endpoints += 1
                else:
                    readiness_reasons.update(endpoint_reasons)
                for query, state in zip(registry.queries, states, strict=True):
                    query_endpoint_status[query.query_id][state.status] += 1
                    query_endpoint_reasons[query.query_id].update(state.reasons)
    query_results = tuple(
        SecCashQualityQueryCensusResultV1(
            query_id=query.query_id,
            target_occurrence_count=target_occurrences[query.query_id],
            occurrence_disposition_counts=tuple(
                sorted(dispositions[query.query_id].items())
            ),
            selected_endpoint_count=query_endpoint_status[query.query_id][
                "selected"
            ],
            not_available_endpoint_count=query_endpoint_status[query.query_id][
                "not_available"
            ],
            quarantined_endpoint_count=query_endpoint_status[query.query_id][
                "quarantined"
            ],
            endpoint_reason_counts=tuple(
                sorted(query_endpoint_reasons[query.query_id].items())
            ),
        )
        for query in registry.queries
    )
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "normalized_manifest_fingerprint": manifest.logical_fingerprint,
        "query_registry_fingerprint": registry.logical_fingerprint,
        "source_range_start": plan.source_range_start,
        "source_range_end": plan.source_range_end,
        "knowledge_cutoff_at": plan.knowledge_cutoff_at,
        "evaluated_session": plan.evaluated_session,
        "scanned_occurrence_count": scanned_count,
        "target_occurrence_count": target_count,
        "observed_issuer_count": len(issuer_ids),
        "observed_endpoint_count": observed_endpoints,
        "ready_endpoint_count": ready_endpoints,
        "blocked_endpoint_count": observed_endpoints - ready_endpoints,
        "fiscal_period_endpoint_counts": tuple(sorted(fiscal_periods.items())),
        "readiness_reason_counts": tuple(sorted(readiness_reasons.items())),
        "query_results": query_results,
        "earliest_target_source_available_at": earliest_available,
        "latest_target_source_available_at": latest_available,
    }
    provisional = SecCashQualitySourceReadinessCensusV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualitySourceReadinessCensusV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def independently_verify_sec_cash_quality_source_readiness(
    *,
    normalized_package_path: Path,
    plan: SecCashQualitySourceReadinessPlanV1,
) -> tuple[
    SecCashQualitySourceReadinessCensusV1,
    SecCashQualitySourceReadinessVerificationV1,
]:
    """Run forward and reverse traversals and require canonical equality."""

    prepared = prepare_sec_cash_quality_target_evidence(
        normalized_package_path=normalized_package_path,
        plan=plan,
    )
    return independently_verify_prepared_sec_cash_quality_source_readiness(
        normalized_package_path=normalized_package_path,
        plan=plan,
        prepared=prepared,
    )


def independently_verify_prepared_sec_cash_quality_source_readiness(
    *,
    normalized_package_path: Path,
    plan: SecCashQualitySourceReadinessPlanV1,
    prepared: SecCashQualityPreparedTargetEvidence,
) -> tuple[
    SecCashQualitySourceReadinessCensusV1,
    SecCashQualitySourceReadinessVerificationV1,
]:
    """Verify both traversals without rereading the normalized source."""

    primary = _run_verified_sec_cash_quality_source_readiness_census(
        normalized_package_path=normalized_package_path,
        plan=plan,
        traversal_order="forward",
        source=prepared.source,
        prepared=prepared,
    )
    replay = _run_verified_sec_cash_quality_source_readiness_census(
        normalized_package_path=normalized_package_path,
        plan=plan,
        traversal_order="reverse",
        source=prepared.source,
        prepared=prepared,
    )
    primary_sha = hashlib.sha256(canonical_census_bytes(primary)).hexdigest()
    replay_sha = hashlib.sha256(canonical_census_bytes(replay)).hexdigest()
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "primary_result_fingerprint": primary.logical_fingerprint,
        "replay_result_fingerprint": replay.logical_fingerprint,
        "primary_canonical_sha256": primary_sha,
        "replay_canonical_sha256": replay_sha,
    }
    provisional = SecCashQualitySourceReadinessVerificationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    verification = SecCashQualitySourceReadinessVerificationV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
    return primary, verification


def _occurrence(
    raw: dict[str, object],
    *,
    query_candidate: bool,
) -> _OccurrenceRow:
    return _OccurrenceRow(
        source_occurrence_id=raw["source_occurrence_id"],
        companyfacts_cik=raw["companyfacts_cik"],
        namespace=raw["namespace"],
        concept_name=raw["concept_name"],
        unit=raw["unit"],
        start_date=raw["start_date"],
        end_date=raw["end_date"],
        value_kind=raw["value_kind"],
        value_text=raw["value_text"],
        accession_number=raw["accession_number"],
        fiscal_year=raw["fiscal_year"],
        fiscal_period=raw["fiscal_period"],
        form=raw["form"],
        filed_date=raw["filed_date"],
        filing_clock_admission_status=raw["filing_clock_admission_status"],
        source_available_at=raw["source_available_at_utc"],
        signal_eligible_session=raw["signal_eligible_session"],
        normalization_status=raw["normalization_status"],
        query_candidate=query_candidate,
    )


def _classify_raw_occurrence(
    *,
    raw: dict[str, object],
    query: SecCashQualitySourceQueryV1,
    plan: SecCashQualitySourceReadinessPlanV1,
) -> str:
    periods_by_form = {
        form: rule.fiscal_periods
        for rule in query.form_period_rules
        for form in rule.forms
    }
    if raw["namespace"] != query.namespace:
        return "namespace_not_allowed"
    if raw["unit"] != query.unit:
        return "unit_not_allowed"
    if raw["form"] not in periods_by_form:
        return "form_not_allowed"
    if raw["fiscal_period"] not in periods_by_form[str(raw["form"])]:
        return "fiscal_period_not_allowed"
    if raw["fiscal_year"] is None:
        return "fiscal_year_missing"
    if raw["end_date"] is None:
        return "period_end_missing"
    if (query.period_shape == "instant") != (raw["start_date"] is None):
        return "period_shape_mismatch"
    if raw["normalization_status"] != "admitted":
        return "normalization_not_admitted"
    if raw["filing_clock_admission_status"] != "admitted":
        return "filing_clock_not_admitted"
    if raw["source_available_at_utc"] is None:
        return "source_available_at_missing"
    if raw["source_available_at_utc"] > plan.knowledge_cutoff_at:
        return "source_available_after_cutoff"
    if raw["signal_eligible_session"] is None:
        return "signal_eligible_session_missing"
    if raw["signal_eligible_session"] > plan.evaluated_session:
        return "signal_eligible_after_evaluation"
    if raw["value_kind"] not in query.accepted_value_kinds or raw["value_text"] is None:
        return "value_not_accepted"
    return "query_candidate"


def _origin_candidates(
    *,
    endpoint_rows: dict[str, list[_OccurrenceRow]],
    q1_rows: dict[tuple[int, str], list[_OccurrenceRow]],
    fiscal_year: int,
    fiscal_period: str,
    registry_queries: tuple[SecCashQualitySourceQueryV1, ...],
) -> set[date]:
    duration_concepts = {
        query.concept_name
        for query in registry_queries
        if query.period_shape == "duration"
    }
    result: set[date] = set()
    candidates = (
        tuple(
            row
            for concept in duration_concepts
            for row in q1_rows.get((fiscal_year, concept), ())
        )
        if fiscal_period in ("Q2", "Q3")
        else tuple(
            row
            for concept in duration_concepts
            for row in endpoint_rows.get(concept, ())
        )
    )
    for row in candidates:
        if (
            row.concept_name not in duration_concepts
            or row.fiscal_year != fiscal_year
            or row.fiscal_period
            != ("Q1" if fiscal_period in ("Q2", "Q3") else fiscal_period)
            or row.start_date is None
        ):
            continue
        if row.query_candidate:
            result.add(row.start_date)
    return result


def _select_indexed_query(
    *,
    query: SecCashQualitySourceQueryV1,
    endpoint_rows: list[_OccurrenceRow] | tuple[_OccurrenceRow, ...],
    q1_rows: list[_OccurrenceRow] | tuple[_OccurrenceRow, ...],
    fiscal_year: int,
    fiscal_period: str,
    period_end: date,
    fiscal_year_origin: date,
) -> _SelectionState:
    if query.period_shape == "duration" and fiscal_period in ("Q2", "Q3"):
        starts = {
            row.start_date
            for row in q1_rows
            if row.query_candidate
        }
        starts.discard(None)
        if len(starts) > 1:
            return _SelectionState(
                status="quarantined",
                reasons=("fiscal_year_origin_ambiguous",),
            )
        if starts and starts != {fiscal_year_origin}:
            return _SelectionState(
                status="quarantined",
                reasons=("fiscal_year_origin_witness_mismatch",),
            )
        if not starts:
            return _SelectionState(
                status="not_available",
                reasons=("fiscal_year_origin_witness_missing",),
            )
    candidates = tuple(
        row
        for row in endpoint_rows
        if row.fiscal_year == fiscal_year
        and row.fiscal_period == fiscal_period
        and row.end_date == period_end
        and row.query_candidate
        and (
            query.period_shape == "instant"
            or row.start_date == fiscal_year_origin
        )
    )
    if not candidates:
        return _SelectionState(
            status="not_available",
            reasons=("no_query_eligible_occurrence_at_endpoint",),
        )
    by_accession: dict[str, list[_OccurrenceRow]] = defaultdict(list)
    for row in candidates:
        by_accession[row.accession_number].append(row)
    clean: list[tuple[datetime, str]] = []
    for accession, accession_rows in by_accession.items():
        states = {
            (
                row.value_kind,
                row.value_text,
                row.source_available_at,
                row.signal_eligible_session,
                row.form,
                row.filed_date,
                row.start_date,
                row.end_date,
            )
            for row in accession_rows
        }
        if len(states) != 1:
            return _SelectionState(
                status="quarantined",
                reasons=("within_accession_conflict",),
            )
        available = accession_rows[0].source_available_at
        if available is None:
            raise SecCashQualitySourceReadinessCensusError(
                "eligible cash-quality census occurrence lacks availability"
            )
        clean.append((available, accession))
    latest_time = max(item[0] for item in clean)
    latest = tuple(item for item in clean if item[0] == latest_time)
    if len(latest) != 1:
        return _SelectionState(
            status="quarantined",
            reasons=("latest_availability_multiple_accessions",),
        )
    return _SelectionState(status="selected", accession_number=latest[0][1])
