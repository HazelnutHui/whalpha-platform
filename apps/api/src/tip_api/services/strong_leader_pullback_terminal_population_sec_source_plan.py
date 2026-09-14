"""Freeze SEC source requests for terminal cases added by EOD correction."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.providers.sec.submissions_payload_census import (
    read_sealed_sec_submissions_payload_census,
)
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    read_sec_submissions_source_package,
)
from tip_api.services import strong_leader_pullback_sec_document_plan as document_plan
from tip_api.services import strong_leader_pullback_sec_lifecycle_pilot as lifecycle_pilot
from tip_api.services import strong_leader_pullback_terminal_gap_census_v2 as gap_source
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    read_historical_inactive_lifecycle_resolution_shadow,
)
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    _fingerprint,
    _json_bytes,
    _sha256_bytes,
)
from tip_api.services.strong_leader_pullback_listed_consideration_terminal_evidence import (
    _network_prohibited,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-population-sec-source-plan/1.0"
)
REPORT_FILE = "terminal-population-sec-source-plan.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
EXPECTED_NEW_CASE_COUNT = 1
MAXIMUM_REQUESTS_PER_SECOND = 2
MAXIMUM_RETRIES_PER_REQUEST = 2
MAXIMUM_DOCUMENT_BYTES = 64 * 1024 * 1024

_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_OUTPUT_NAME_PATTERN = r"^plan=[A-Za-z0-9._-]+$"

BoundaryRelation = Literal[
    "on_last_eod_observation",
    "after_last_eod_before_provider_delist_candidate",
    "on_provider_delist_candidate",
    "after_provider_delist_candidate",
]


class StrongLeaderPullbackTerminalPopulationSecSourcePlanError(RuntimeError):
    """Raised when the corrected-population SEC plan cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LifecycleShadowBindingV1(_FrozenModel):
    anchor_date: date
    contract_version: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)


class TerminalPopulationSecSourceCaseV1(_FrozenModel):
    instrument_id: UUID
    provider_ticker_locators: tuple[str, ...] = Field(min_length=1)
    cik: str = Field(pattern=r"^[0-9]{10}$")
    primary_exchange: str = Field(min_length=1)
    selected_identity_type: str = Field(min_length=1)
    selected_identity_value: str = Field(min_length=1)
    source_anchor_dates: tuple[date, ...] = Field(min_length=1)
    source_observation_fingerprints: tuple[str, ...] = Field(min_length=1)
    canonical_identity_last_observed_date: date
    strategy_window_last_eod_observed_date: date
    provider_delist_date_candidate: date
    corrected_horizon_5_crossing_path_count: int = Field(ge=1)
    planned_request_count: int = Field(ge=1)
    ticker_grants_identity_authority: Literal[False] = False
    terminal_fact_authorized: Literal[False] = False

    @field_validator(
        "provider_ticker_locators",
        "source_anchor_dates",
        "source_observation_fingerprints",
        mode="before",
    )
    @classmethod
    def values_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("terminal-population source-plan values differ")
        return values

    @model_validator(mode="after")
    def case_reconciles(self) -> "TerminalPopulationSecSourceCaseV1":
        if (
            self.strategy_window_last_eod_observed_date
            > self.canonical_identity_last_observed_date
            or self.canonical_identity_last_observed_date
            > self.provider_delist_date_candidate
        ):
            raise ValueError("terminal-population source-plan dates are reversed")
        return self


class TerminalPopulationSecSourceItemV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    form: str = Field(min_length=1)
    filing_date: date
    acceptance_datetime: datetime
    primary_document: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    source_member_name: str = Field(min_length=1)
    locator_categories: tuple[str, ...] = Field(min_length=1)
    structured_items: tuple[str, ...]
    relation_to_eod_boundary: BoundaryRelation
    request_method: Literal["GET"] = "GET"
    accept_encoding: Literal["identity"] = "identity"
    maximum_response_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    credential_material_retained: Literal[False] = False
    document_content_retrieved: Literal[False] = False
    listed_security_fact_authority: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("locator_categories", "structured_items", mode="before")
    @classmethod
    def values_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("terminal-population source-plan item values differ")
        return values

    @model_validator(mode="after")
    def item_reconciles(self) -> "TerminalPopulationSecSourceItemV1":
        if self.request_url != document_plan._document_url(
            cik=self.cik,
            accession=self.accession_number,
            primary_document=self.primary_document,
        ):
            raise ValueError("terminal-population source-plan URL differs")
        return self


class StrongLeaderPullbackTerminalPopulationSecSourcePlanV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-sec-source-plan/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["new_population_sec_source_plan_frozen"] = (
        "new_population_sec_source_plan_frozen"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    planned_at: datetime
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    terminal_gap_v2_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    terminal_gap_v2_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_shadow_bindings: tuple[LifecycleShadowBindingV1, ...] = Field(
        min_length=1
    )
    submissions_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_payload_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_payload_census_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_snapshot_date: date
    range_start: date
    range_end: date
    source_available_at: datetime
    selection_rule: Literal[
        "new_v2_cases_direct_or_structured_lifecycle_filings_on_or_after_last_eod_v1"
    ] = (
        "new_v2_cases_direct_or_structured_lifecycle_filings_on_or_after_last_eod_v1"
    )
    newly_in_scope_case_count: Literal[1] = EXPECTED_NEW_CASE_COUNT
    planned_request_count: int = Field(ge=1)
    unique_accession_count: int = Field(ge=1)
    unique_url_count: int = Field(ge=1)
    allowed_hosts: tuple[Literal["www.sec.gov"], ...] = ("www.sec.gov",)
    maximum_requests_per_second: Literal[2] = MAXIMUM_REQUESTS_PER_SECOND
    maximum_retries_per_request: Literal[2] = MAXIMUM_RETRIES_PER_REQUEST
    maximum_document_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    form_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]
    relation_counts: tuple[tuple[str, int], ...]
    cases: tuple[TerminalPopulationSecSourceCaseV1, ...]
    items: tuple[TerminalPopulationSecSourceItemV1, ...]
    external_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
    document_write_count: Literal[0] = 0
    listed_security_identity_assignment_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("planned_at", "source_available_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def plan_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalPopulationSecSourcePlanV1":
        sequences = tuple(item.request_sequence for item in self.items)
        accessions = tuple(item.accession_number for item in self.items)
        urls = tuple(item.request_url for item in self.items)
        ids = tuple(item.instrument_id for item in self.cases)
        item_counts = Counter(item.instrument_id for item in self.items)
        forms = Counter(item.form for item in self.items)
        categories = Counter(
            value for item in self.items for value in item.locator_categories
        )
        relations = Counter(item.relation_to_eod_boundary for item in self.items)
        if (
            self.planned_at < self.source_available_at
            or self.range_end < self.range_start
            or len(self.cases) != self.newly_in_scope_case_count
            or ids != tuple(sorted(set(ids), key=str))
            or len(self.items) != self.planned_request_count
            or sequences != tuple(range(1, self.planned_request_count + 1))
            or len(set(accessions)) != self.unique_accession_count
            or len(set(urls)) != self.unique_url_count
            or any(
                item_counts[item.instrument_id] != item.planned_request_count
                for item in self.cases
            )
            or set(item_counts) != set(ids)
            or self.form_counts != _ordered(forms)
            or self.category_counts != _ordered(categories)
            or self.relation_counts != _ordered(relations)
            or tuple(item.anchor_date for item in self.lifecycle_shadow_bindings)
            != tuple(sorted({item.anchor_date for item in self.lifecycle_shadow_bindings}))
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population SEC source plan differs")
        case_by_id = {item.instrument_id: item for item in self.cases}
        if any(
            item.cik != case_by_id[item.instrument_id].cik
            or item.filing_date
            < case_by_id[item.instrument_id].strategy_window_last_eod_observed_date
            or item.relation_to_eod_boundary
            != _boundary_relation(
                filing_date=item.filing_date,
                last_eod=(
                    case_by_id[item.instrument_id]
                    .strategy_window_last_eod_observed_date
                ),
                delist_candidate=(
                    case_by_id[item.instrument_id].provider_delist_date_candidate
                ),
            )
            for item in self.items
        ):
            raise ValueError("terminal-population SEC source item lineage differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationSecSourcePlanResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationSecSourcePlanV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_sec_source_plan(
    *,
    terminal_gap_v2_root: Path,
    terminal_gap_v2_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    lifecycle_anchor_dates: tuple[date, ...],
    submissions_package_path: Path,
    submissions_custody_root: Path,
    submissions_census_root: Path,
    source_snapshot_date: date,
    range_start: date,
    range_end: date,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    planned_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecSourcePlanResult:
    """Build one immutable, zero-request source plan for new V2 cases."""

    with _network_prohibited():
        planned_at = normalize_utc_datetime(planned_at)
        if planned_at > datetime.now(UTC):
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population SEC source-plan time is in the future"
            )
        if (
            not lifecycle_anchor_dates
            or lifecycle_anchor_dates != tuple(sorted(set(lifecycle_anchor_dates)))
        ):
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population lifecycle anchors differ"
            )
        gap = gap_source.read_strong_leader_pullback_terminal_gap_census_v2(
            output_root=terminal_gap_v2_root,
            output_custody_root=terminal_gap_v2_custody_root,
        )
        lifecycle = tuple(
            read_historical_inactive_lifecycle_resolution_shadow(
                root=lifecycle_shadow_root,
                anchor_date=anchor,
                approved_custody_root=lifecycle_shadow_custody_root,
            )
            for anchor in lifecycle_anchor_dates
        )
        source = read_sec_submissions_source_package(
            package_path=submissions_package_path,
            approved_custody_root=submissions_custody_root,
        )
        census = read_sealed_sec_submissions_payload_census(
            output_root=submissions_census_root,
            source_snapshot_date=source_snapshot_date,
            range_start=range_start,
            range_end=range_end,
        )
        lifecycle_pilot.validate_sec_lifecycle_submissions_binding(
            submissions_package_path=submissions_package_path,
            source=source,
            census=census,
            source_snapshot_date=source_snapshot_date,
            range_start=range_start,
            range_end=range_end,
        )
        report = _compose_report(
            gap=gap,
            lifecycle=lifecycle,
            source=source,
            census=census,
            submissions_package_path=submissions_package_path,
            submissions_census_root=submissions_census_root,
            implementation_revision=implementation_revision,
            planned_at=planned_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_sec_source_plan(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationSecSourcePlanResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationSecSourcePlanV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source plan is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")) + b"\n":
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationSecSourcePlanResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _compose_report(
    *, gap: object, lifecycle: tuple[object, ...], source: object, census: object,
    submissions_package_path: Path, submissions_census_root: Path,
    implementation_revision: str, planned_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecSourcePlanV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan revision is invalid"
        )
    gap_cases = tuple(
        item
        for item in gap.report.decisions
        if item.gap_state == "newly_in_scope_primary_source_unadjudicated"
    )
    if (
        len(gap_cases) != EXPECTED_NEW_CASE_COUNT
        or len(gap_cases) != gap.report.new_primary_source_case_count
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population new-case count differs"
        )
    recovered = _recover_cases(gap_cases=gap_cases, lifecycle=lifecycle)
    archive_path = submissions_package_path / ARCHIVE_FILE
    _require_regular_file(archive_path, 0o400, source.archive_bytes)
    projected: list[tuple[object, object]] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = tuple(sorted(item.filename for item in archive.infolist()))
        if (
            len(names) != source.member_count
            or _fingerprint(names) != source.member_name_fingerprint
        ):
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population SEC archive inventory differs"
            )
        for gap_case, locator in recovered:
            try:
                projected_case = lifecycle_pilot.build_sec_lifecycle_case_from_archive(
                    archive=archive,
                    archive_names=frozenset(names),
                    case=_ProjectionCase(
                        instrument_id=gap_case.instrument_id,
                        cik_locators=(locator["cik"],),
                        canonical_last_observed_date=(
                            gap_case.strategy_window_last_eod_observed_date
                        ),
                        provider_delist_date_candidate=locator[
                            "provider_delist_date"
                        ],
                    ),
                    range_start=census.range_start,
                    range_end=census.range_end,
                )
            except lifecycle_pilot.StrongLeaderPullbackSecLifecyclePilotError as exc:
                raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                    "terminal-population SEC filing projection failed"
                ) from exc
            selected = tuple(
                item
                for item in projected_case.candidate_filings
                if item.relation_to_last_observation != "before_last_observation"
            )
            if not selected:
                raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                    "terminal-population case lacks transition source candidates"
                )
            projected.extend((gap_case, (locator, item)) for item in selected)
    projected.sort(
        key=lambda value: (
            str(value[0].instrument_id),
            value[1][1].filing_date,
            value[1][1].acceptance_datetime,
            value[1][1].accession_number,
        )
    )
    if len({item[1][1].accession_number for item in projected}) != len(projected):
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC accessions are duplicated"
        )
    items = tuple(
        TerminalPopulationSecSourceItemV1(
            request_sequence=index,
            instrument_id=gap_case.instrument_id,
            cik=locator["cik"],
            accession_number=filing.accession_number,
            form=filing.form,
            filing_date=filing.filing_date,
            acceptance_datetime=filing.acceptance_datetime,
            primary_document=filing.primary_document,
            request_url=document_plan._document_url(
                cik=locator["cik"],
                accession=filing.accession_number,
                primary_document=filing.primary_document,
            ),
            source_member_name=filing.source_member_name,
            locator_categories=filing.locator_categories,
            structured_items=filing.items,
            relation_to_eod_boundary=_boundary_relation(
                filing_date=filing.filing_date,
                last_eod=gap_case.strategy_window_last_eod_observed_date,
                delist_candidate=locator["provider_delist_date"],
            ),
        )
        for index, (gap_case, (locator, filing)) in enumerate(projected, start=1)
    )
    item_counts = Counter(item.instrument_id for item in items)
    cases = tuple(
        TerminalPopulationSecSourceCaseV1(
            instrument_id=gap_case.instrument_id,
            provider_ticker_locators=locator["tickers"],
            cik=locator["cik"],
            primary_exchange=locator["primary_exchange"],
            selected_identity_type=locator["selected_identity_type"],
            selected_identity_value=locator["selected_identity_value"],
            source_anchor_dates=locator["source_anchor_dates"],
            source_observation_fingerprints=locator[
                "source_observation_fingerprints"
            ],
            canonical_identity_last_observed_date=(
                gap_case.canonical_identity_last_observed_date
            ),
            strategy_window_last_eod_observed_date=(
                gap_case.strategy_window_last_eod_observed_date
            ),
            provider_delist_date_candidate=locator["provider_delist_date"],
            corrected_horizon_5_crossing_path_count=(
                gap_case.horizon_5_crossing_path_count
            ),
            planned_request_count=item_counts[gap_case.instrument_id],
        )
        for gap_case, locator in recovered
    )
    shadow_bindings = tuple(
        LifecycleShadowBindingV1(
            anchor_date=item.manifest.anchor_date,
            contract_version=item.manifest.contract_version,
            manifest_sha256=item.manifest_sha256,
            logical_fingerprint=item.manifest.logical_fingerprint,
        )
        for item in lifecycle
    )
    forms = Counter(item.form for item in items)
    categories = Counter(value for item in items for value in item.locator_categories)
    relations = Counter(item.relation_to_eod_boundary for item in items)
    census_path = submissions_census_root / _census_file_name(
        census.submissions_snapshot_date, census.range_start, census.range_end
    )
    values = {
        "implementation_revision": implementation_revision,
        "planned_at": normalize_utc_datetime(planned_at),
        "terminal_gap_v2_report_sha256": gap.report_sha256,
        "terminal_gap_v2_logical_fingerprint": gap.report.logical_fingerprint,
        "lifecycle_shadow_bindings": shadow_bindings,
        "submissions_manifest_sha256": _sha256_file(
            submissions_package_path / "package.json"
        ),
        "submissions_source_fingerprint": source.logical_fingerprint,
        "submissions_archive_sha256": source.archive_sha256,
        "submissions_payload_census_sha256": _sha256_file(census_path),
        "submissions_payload_census_fingerprint": census.logical_fingerprint,
        "submissions_snapshot_date": census.submissions_snapshot_date,
        "range_start": census.range_start,
        "range_end": census.range_end,
        "source_available_at": source.completed_at,
        "planned_request_count": len(items),
        "unique_accession_count": len({item.accession_number for item in items}),
        "unique_url_count": len({item.request_url for item in items}),
        "form_counts": _ordered(forms),
        "category_counts": _ordered(categories),
        "relation_counts": _ordered(relations),
        "cases": cases,
        "items": items,
    }
    provisional = StrongLeaderPullbackTerminalPopulationSecSourcePlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationSecSourcePlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class _ProjectionCase:
    instrument_id: UUID
    cik_locators: tuple[str, ...]
    canonical_last_observed_date: date
    provider_delist_date_candidate: date


def _recover_cases(
    *, gap_cases: tuple[object, ...], lifecycle: tuple[object, ...]
) -> tuple[tuple[object, dict[str, object]], ...]:
    requested_ids = {item.instrument_id for item in gap_cases}
    rows: dict[UUID, list[tuple[object, object]]] = {
        instrument_id: [] for instrument_id in requested_ids
    }
    for result in lifecycle:
        source_by_fingerprint = {
            item.source_observation_fingerprint: item
            for item in result.source_observations
        }
        if len(source_by_fingerprint) != len(result.source_observations):
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population lifecycle observations are duplicated"
            )
        for decision in result.decisions:
            if (
                decision.disposition
                is not InactiveLifecycleDisposition.REVIEW_CANDIDATE
                or decision.canonical_instrument_id not in requested_ids
            ):
                continue
            gap_case = next(
                item
                for item in gap_cases
                if item.instrument_id == decision.canonical_instrument_id
            )
            if (
                decision.canonical_last_observed_date
                != gap_case.canonical_identity_last_observed_date
            ):
                continue
            source = source_by_fingerprint.get(decision.source_observation_fingerprint)
            if source is None:
                raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                    "terminal-population lifecycle occurrence is unavailable"
                )
            rows[gap_case.instrument_id].append((decision, source))
    recovered = []
    for gap_case in sorted(gap_cases, key=lambda item: str(item.instrument_id)):
        evidence = rows[gap_case.instrument_id]
        if not evidence:
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population case lacks stable-ID source evidence"
            )
        ciks = _values(item[1].cik for item in evidence)
        exchanges = _values(item[1].primary_exchange for item in evidence)
        identity_types = _values(item[0].selected_identity_type.value for item in evidence)
        identity_values = _values(item[0].selected_identity_value for item in evidence)
        delist_dates = tuple(sorted({item[0].effective_date_candidate for item in evidence}))
        if (
            len(ciks) != 1
            or len(exchanges) != 1
            or len(identity_types) != 1
            or len(identity_values) != 1
            or len(delist_dates) != 1
            or delist_dates[0] is None
        ):
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population source locators are ambiguous"
            )
        recovered.append(
            (
                gap_case,
                {
                    "cik": str(ciks[0]).zfill(10),
                    "primary_exchange": exchanges[0],
                    "selected_identity_type": identity_types[0],
                    "selected_identity_value": identity_values[0],
                    "provider_delist_date": delist_dates[0],
                    "tickers": _values(item[1].ticker for item in evidence),
                    "source_anchor_dates": tuple(
                        sorted({item[0].anchor_date for item in evidence})
                    ),
                    "source_observation_fingerprints": _values(
                        item[0].source_observation_fingerprint for item in evidence
                    ),
                },
            )
        )
    return tuple(recovered)


def _values(values: object) -> tuple[str, ...]:
    normalized = tuple(
        sorted(
            {
                str(value).strip()
                for value in values  # type: ignore[union-attr]
                if value is not None and str(value).strip()
            }
        )
    )
    return normalized


def _boundary_relation(
    *, filing_date: date, last_eod: date, delist_candidate: date
) -> BoundaryRelation:
    if filing_date < last_eod:
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population filing precedes EOD boundary"
        )
    if filing_date == last_eod:
        return "on_last_eod_observation"
    if filing_date < delist_candidate:
        return "after_last_eod_before_provider_delist_candidate"
    if filing_date == delist_candidate:
        return "on_provider_delist_candidate"
    return "after_provider_delist_candidate"


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationSecSourcePlanV1,
) -> StrongLeaderPullbackTerminalPopulationSecSourcePlanResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_sec_source_plan(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "existing terminal-population SEC source plan differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = _json_bytes(report.model_dump(mode="json")) + b"\n"
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
                "terminal-population SEC source plan exceeds byte ceiling"
            )
        _write_exclusive(partial / REPORT_FILE, raw)
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_terminal_population_sec_source_plan(
        output_root=target, output_custody_root=output_custody_root
    )
    if reread.report != report:
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan reread differs"
        )
    return StrongLeaderPullbackTerminalPopulationSecSourcePlanResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_OUTPUT_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan target is unsafe"
        )
    return path


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or target.resolve(strict=True) != target
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan output is unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan file is unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTerminalPopulationSecSourcePlanError(
            "terminal-population SEC source-plan file metadata differs"
        )


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _census_file_name(snapshot: date, start: date, end: date) -> str:
    return (
        f"census=snapshot-{snapshot.isoformat()}--range-"
        f"{start.isoformat()}--{end.isoformat()}.json"
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
