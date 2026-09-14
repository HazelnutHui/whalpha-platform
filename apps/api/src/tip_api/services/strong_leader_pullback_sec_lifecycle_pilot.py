"""Bounded SEC lifecycle-document locator pilot for the first strategy."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import zipfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.submissions_payload_census import (
    SecSubmissionsPayloadCensusV1,
    read_sealed_sec_submissions_payload_census,
)
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    SecSubmissionsSourceManifestV1,
    read_sec_submissions_source_package,
)
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    LIFECYCLE_REQUIRED_FIELDS,
    StrongLeaderPullbackSourceAcceptanceSampleResult,
    read_strong_leader_pullback_source_acceptance_sample,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-lifecycle-pilot/1.0"
REPORT_FILE = "pilot.json"
EXPECTED_CASE_COUNT = 64
MAXIMUM_REPORT_BYTES = 8 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_MEMBER_PATTERN = re.compile(
    r"CIK(?P<cik>[0-9]{10})(?:-submissions-(?P<shard>[0-9]{3}))?\.json\Z"
)
_BUILD_NAME_PATTERN = r"^build=[A-Za-z0-9._-]+$"

_DIRECT_LIFECYCLE_FORMS = frozenset(
    {
        "15",
        "15-12B",
        "15-12G",
        "15-15D",
        "15F",
        "15F-12B",
        "15F-12G",
        "15F-15D",
        "25",
        "25-NSE",
        "425",
        "DEFA14A",
        "DEFM14A",
        "F-4",
        "F-4/A",
        "PREM14A",
        "S-4",
        "S-4/A",
        "SC 14D9",
        "SC 14D9/A",
        "SC TO-T",
        "SC TO-T/A",
    }
)
_STRUCTURED_8K_ITEMS = frozenset({"1.03", "2.01", "3.01", "5.01", "8.01"})


class StrongLeaderPullbackSecLifecyclePilotError(RuntimeError):
    """Raised when the bounded SEC lifecycle pilot cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RequiredFieldAssessmentV1(_FrozenModel):
    field_name: str
    result_state: Literal["unsupported"] = "unsupported"
    reason_code: Literal["sec_submissions_metadata_is_not_security_lifecycle_fact"] = (
        "sec_submissions_metadata_is_not_security_lifecycle_fact"
    )


class SecLifecycleCandidateFilingV1(_FrozenModel):
    accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    cik: str = Field(pattern=r"^[0-9]{10}$")
    form: str
    filing_date: date
    acceptance_datetime: datetime
    primary_document: str
    primary_document_description: str
    items: tuple[str, ...]
    locator_categories: tuple[
        Literal[
            "direct_lifecycle_form",
            "post_last_observation_foreign_report",
            "structured_8k_lifecycle_item",
        ],
        ...,
    ]
    relation_to_last_observation: Literal[
        "before_last_observation",
        "on_last_observation",
        "after_last_before_provider_delist_candidate",
        "on_provider_delist_candidate",
        "after_provider_delist_candidate",
    ]
    source_member_name: str
    document_content_retrieved: Literal[False] = False
    listed_security_fact_authority: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False

    @field_validator(
        "form",
        "primary_document",
        "primary_document_description",
        "source_member_name",
    )
    @classmethod
    def text_is_normalized(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("SEC lifecycle filing text is invalid")
        return value

    @field_validator("items", "locator_categories", mode="before")
    @classmethod
    def tuple_is_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("SEC lifecycle filing values are not ordered and unique")
        return values

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class SecLifecycleCasePilotV1(_FrozenModel):
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    canonical_last_observed_date: date
    provider_delist_date_candidate: date
    root_member_name: str
    historical_shard_member_count: int = Field(ge=0)
    filing_row_count: int = Field(ge=0)
    in_range_filing_row_count: int = Field(ge=0)
    candidate_filing_count: int = Field(ge=1)
    on_or_after_last_observation_candidate_count: int = Field(ge=1)
    required_field_assessments: tuple[RequiredFieldAssessmentV1, ...]
    candidate_filings: tuple[SecLifecycleCandidateFilingV1, ...]
    sec_cik_is_issuer_locator_only: Literal[True] = True
    listed_security_identity_authorized: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False

    @model_validator(mode="after")
    def case_reconciles(self) -> "SecLifecycleCasePilotV1":
        if self.canonical_last_observed_date > self.provider_delist_date_candidate:
            raise ValueError("SEC lifecycle case dates are reversed")
        if self.in_range_filing_row_count > self.filing_row_count:
            raise ValueError("SEC lifecycle in-range count exceeds source rows")
        if self.candidate_filing_count != len(self.candidate_filings):
            raise ValueError("SEC lifecycle candidate count differs")
        observed_on_or_after = sum(
            item.relation_to_last_observation != "before_last_observation"
            for item in self.candidate_filings
        )
        if self.on_or_after_last_observation_candidate_count != observed_on_or_after:
            raise ValueError("SEC lifecycle transition candidate count differs")
        fields = tuple(item.field_name for item in self.required_field_assessments)
        if fields != LIFECYCLE_REQUIRED_FIELDS:
            raise ValueError("SEC lifecycle required-field assessments differ")
        keys = tuple(
            (item.filing_date, item.acceptance_datetime, item.accession_number)
            for item in self.candidate_filings
        )
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise ValueError("SEC lifecycle candidate filings are duplicated or unordered")
        return self


class StrongLeaderPullbackSecLifecyclePilotV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-lifecycle-pilot/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "metadata_locator_complete_terminal_evidence_incomplete"
    ] = "metadata_locator_complete_terminal_evidence_incomplete"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    source_tier: Literal["official_latest_vintage_metadata"] = (
        "official_latest_vintage_metadata"
    )
    outcome_blind: Literal[True] = True
    sample_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    sample_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_payload_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_payload_census_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_snapshot_date: date
    range_start: date
    range_end: date
    lifecycle_case_count: Literal[64] = EXPECTED_CASE_COUNT
    cik_count: Literal[64] = EXPECTED_CASE_COUNT
    root_member_count: Literal[64] = EXPECTED_CASE_COUNT
    historical_shard_member_count: int = Field(ge=0)
    filing_row_count: int = Field(ge=0)
    in_range_filing_row_count: int = Field(ge=0)
    candidate_filing_count: int = Field(ge=64)
    on_or_after_last_observation_candidate_count: int = Field(ge=64)
    cases_with_candidate_count: Literal[64] = EXPECTED_CASE_COUNT
    cases_with_on_or_after_last_candidate_count: Literal[64] = EXPECTED_CASE_COUNT
    candidate_form_counts: tuple[tuple[str, int], ...]
    candidate_category_counts: tuple[tuple[str, int], ...]
    candidate_relation_counts: tuple[tuple[str, int], ...]
    required_field_result_counts: tuple[tuple[str, int], ...]
    cases: tuple[SecLifecycleCasePilotV1, ...]
    document_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
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

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackSecLifecyclePilotV1":
        if self.range_end < self.range_start:
            raise ValueError("SEC lifecycle pilot range is reversed")
        ids = tuple(item.instrument_id for item in self.cases)
        ciks = tuple(item.cik for item in self.cases)
        if (
            len(self.cases) != self.lifecycle_case_count
            or ids != tuple(sorted(ids, key=str))
            or len(set(ids)) != self.lifecycle_case_count
            or len(set(ciks)) != self.cik_count
        ):
            raise ValueError("SEC lifecycle pilot population differs")
        if (
            sum(item.historical_shard_member_count for item in self.cases)
            != self.historical_shard_member_count
            or sum(item.filing_row_count for item in self.cases)
            != self.filing_row_count
            or sum(item.in_range_filing_row_count for item in self.cases)
            != self.in_range_filing_row_count
            or sum(item.candidate_filing_count for item in self.cases)
            != self.candidate_filing_count
            or sum(
                item.on_or_after_last_observation_candidate_count
                for item in self.cases
            )
            != self.on_or_after_last_observation_candidate_count
        ):
            raise ValueError("SEC lifecycle pilot aggregate counts differ")
        if any(
            values != tuple(sorted(values)) or any(count <= 0 for _, count in values)
            for values in (
                self.candidate_form_counts,
                self.candidate_category_counts,
                self.candidate_relation_counts,
                self.required_field_result_counts,
            )
        ):
            raise ValueError("SEC lifecycle pilot aggregate values are invalid")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC lifecycle pilot fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecLifecyclePilotResult:
    output_root: Path
    report: StrongLeaderPullbackSecLifecyclePilotV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_sec_lifecycle_pilot(
    *,
    sample_root: Path,
    sample_custody_root: Path,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    submissions_census_root: Path,
    source_snapshot_date: date,
    range_start: date,
    range_end: date,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecLifecyclePilotResult:
    """Build one outcome-blind SEC metadata locator pilot without network."""

    with _network_prohibited():
        sample = read_strong_leader_pullback_source_acceptance_sample(
            output_root=sample_root,
            output_custody_root=sample_custody_root,
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
        validate_sec_lifecycle_submissions_binding(
            submissions_package_path=submissions_package_path,
            source=source,
            census=census,
            source_snapshot_date=source_snapshot_date,
            range_start=range_start,
            range_end=range_end,
        )
        report = _compose_report(
            sample=sample,
            source=source,
            census=census,
            submissions_package_path=submissions_package_path,
            submissions_census_root=submissions_census_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_lifecycle_pilot(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecLifecyclePilotResult:
    """Formally reread one completed SEC lifecycle pilot."""

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecLifecyclePilotV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot report bytes are not canonical"
        )
    return StrongLeaderPullbackSecLifecyclePilotResult(
        output_root=root,
        report=report,
        report_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def validate_sec_lifecycle_submissions_binding(
    *,
    submissions_package_path: Path,
    source: SecSubmissionsSourceManifestV1,
    census: SecSubmissionsPayloadCensusV1,
    source_snapshot_date: date,
    range_start: date,
    range_end: date,
) -> None:
    manifest_path = submissions_package_path / "package.json"
    if (
        source.remote.last_modified.date() != source_snapshot_date
        or census.submissions_snapshot_date != source_snapshot_date
        or census.range_start != range_start
        or census.range_end != range_end
        or census.submissions_manifest_sha256 != _sha256_file(manifest_path)
        or census.submissions_source_fingerprint != source.logical_fingerprint
        or census.submissions_archive_sha256 != source.archive_sha256
        or census.payload_read_member_count != source.member_count
        or census.quarantined_member_count != 0
        or census.payload_validation_status != "complete"
    ):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC Submissions source/census binding differs"
        )


def _compose_report(
    *,
    sample: StrongLeaderPullbackSourceAcceptanceSampleResult,
    source: SecSubmissionsSourceManifestV1,
    census: SecSubmissionsPayloadCensusV1,
    submissions_package_path: Path,
    submissions_census_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecLifecyclePilotV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle implementation revision is invalid"
        )
    cases = sample.report.lifecycle_cases
    if (
        len(cases) != EXPECTED_CASE_COUNT
        or any(len(item.cik_locators) != 1 for item in cases)
        or len({item.cik_locators[0] for item in cases}) != EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle sample CIK population differs"
        )
    archive_path = submissions_package_path / ARCHIVE_FILE
    _require_regular_file(archive_path, 0o400, source.archive_bytes)
    with zipfile.ZipFile(archive_path) as archive:
        names = tuple(sorted(item.filename for item in archive.infolist()))
        if (
            len(names) != source.member_count
            or _fingerprint(names) != source.member_name_fingerprint
        ):
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "SEC lifecycle source archive inventory differs"
            )
        name_set = frozenset(names)
        results = tuple(
            sorted(
                (
                    build_sec_lifecycle_case_from_archive(
                        archive=archive,
                        archive_names=name_set,
                        case=item,
                        range_start=census.range_start,
                        range_end=census.range_end,
                    )
                    for item in cases
                ),
                key=lambda item: str(item.instrument_id),
            )
        )
    forms: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    for case in results:
        for filing in case.candidate_filings:
            forms[filing.form] += 1
            categories.update(filing.locator_categories)
            relations[filing.relation_to_last_observation] += 1
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "sample_report_sha256": sample.report_sha256,
        "sample_logical_fingerprint": sample.report.logical_fingerprint,
        "submissions_manifest_sha256": _sha256_file(
            submissions_package_path / "package.json"
        ),
        "submissions_source_fingerprint": source.logical_fingerprint,
        "submissions_archive_sha256": source.archive_sha256,
        "submissions_payload_census_sha256": _sha256_file(
            submissions_census_root
            / _census_file_name(
                census.submissions_snapshot_date,
                census.range_start,
                census.range_end,
            )
        ),
        "submissions_payload_census_fingerprint": census.logical_fingerprint,
        "submissions_snapshot_date": census.submissions_snapshot_date,
        "range_start": census.range_start,
        "range_end": census.range_end,
        "historical_shard_member_count": sum(
            item.historical_shard_member_count for item in results
        ),
        "filing_row_count": sum(item.filing_row_count for item in results),
        "in_range_filing_row_count": sum(
            item.in_range_filing_row_count for item in results
        ),
        "candidate_filing_count": sum(
            item.candidate_filing_count for item in results
        ),
        "on_or_after_last_observation_candidate_count": sum(
            item.on_or_after_last_observation_candidate_count for item in results
        ),
        "candidate_form_counts": _ordered(forms),
        "candidate_category_counts": _ordered(categories),
        "candidate_relation_counts": _ordered(relations),
        "required_field_result_counts": (
            ("unsupported", EXPECTED_CASE_COUNT * len(LIFECYCLE_REQUIRED_FIELDS)),
        ),
        "cases": results,
    }
    provisional = StrongLeaderPullbackSecLifecyclePilotV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecLifecyclePilotV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def build_sec_lifecycle_case_from_archive(
    *, archive: zipfile.ZipFile, archive_names: frozenset[str], case: object,
    range_start: date, range_end: date,
) -> SecLifecycleCasePilotV1:
    cik = _normalized_cik(case.cik_locators[0])
    root_name = f"CIK{cik}.json"
    if root_name not in archive_names:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle CIK root member is unavailable"
        )
    root = _json_member(archive, root_name)
    if not isinstance(root, dict) or str(root.get("cik", "")).zfill(10) != cik:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle CIK root member differs"
        )
    filings = root.get("filings")
    if not isinstance(filings, dict):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle filings root is invalid"
        )
    recent = filings.get("recent")
    references = filings.get("files")
    if not isinstance(recent, dict) or not isinstance(references, list):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle filing members are invalid"
        )
    members: list[tuple[str, dict[str, object]]] = [(root_name, recent)]
    referenced_names: list[str] = []
    for reference in references:
        if not isinstance(reference, dict) or not isinstance(reference.get("name"), str):
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "SEC lifecycle historical reference is invalid"
            )
        name = reference["name"]
        match = _MEMBER_PATTERN.fullmatch(name)
        if (
            match is None
            or match.group("cik") != cik
            or match.group("shard") is None
            or name not in archive_names
        ):
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "SEC lifecycle historical reference differs"
            )
        referenced_names.append(name)
        shard = _json_member(archive, name)
        if not isinstance(shard, dict):
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "SEC lifecycle historical shard is invalid"
            )
        members.append((name, shard))
    if referenced_names != sorted(set(referenced_names)):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle historical references are duplicated or unordered"
        )
    filing_rows = 0
    in_range_rows = 0
    candidates: list[SecLifecycleCandidateFilingV1] = []
    seen_accessions: set[str] = set()
    for member_name, columns in members:
        rows = _filing_rows(columns, member_name=member_name)
        filing_rows += len(rows)
        for row in rows:
            accession = row["accession_number"]
            if accession in seen_accessions:
                raise StrongLeaderPullbackSecLifecyclePilotError(
                    "SEC lifecycle accession is duplicated across members"
                )
            seen_accessions.add(accession)
            filing_date = row["filing_date"]
            if not (range_start <= filing_date <= range_end):
                continue
            in_range_rows += 1
            categories = _locator_categories(
                form=row["form"],
                items=row["items"],
                filing_date=filing_date,
                last_observed=case.canonical_last_observed_date,
            )
            if not categories:
                continue
            primary_document = row["primary_document"]
            if not isinstance(primary_document, str):
                raise StrongLeaderPullbackSecLifecyclePilotError(
                    "SEC lifecycle candidate lacks a primary document locator"
                )
            if (
                PurePosixPath(primary_document).is_absolute()
                or "\\" in primary_document
                or PurePosixPath(primary_document).as_posix() != primary_document
                or any(
                    part in {".", ".."}
                    for part in PurePosixPath(primary_document).parts
                )
            ):
                raise StrongLeaderPullbackSecLifecyclePilotError(
                    "SEC lifecycle primary document locator is invalid"
                )
            candidates.append(
                SecLifecycleCandidateFilingV1(
                    accession_number=accession,
                    cik=cik,
                    form=row["form"],
                    filing_date=filing_date,
                    acceptance_datetime=row["acceptance_datetime"],
                    primary_document=primary_document,
                    primary_document_description=row["primary_document_description"],
                    items=row["items"],
                    locator_categories=categories,
                    relation_to_last_observation=_date_relation(
                        filing_date=filing_date,
                        last_observed=case.canonical_last_observed_date,
                        delist_candidate=case.provider_delist_date_candidate,
                    ),
                    source_member_name=member_name,
                )
            )
    ordered_candidates = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.filing_date,
                item.acceptance_datetime,
                item.accession_number,
            ),
        )
    )
    on_or_after = sum(
        item.relation_to_last_observation != "before_last_observation"
        for item in ordered_candidates
    )
    if not ordered_candidates or not on_or_after:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle case lacks a transition-period filing candidate"
        )
    assessments = tuple(
        RequiredFieldAssessmentV1(field_name=field)
        for field in LIFECYCLE_REQUIRED_FIELDS
    )
    return SecLifecycleCasePilotV1(
        instrument_id=case.instrument_id,
        cik=cik,
        canonical_last_observed_date=case.canonical_last_observed_date,
        provider_delist_date_candidate=case.provider_delist_date_candidate,
        root_member_name=root_name,
        historical_shard_member_count=len(referenced_names),
        filing_row_count=filing_rows,
        in_range_filing_row_count=in_range_rows,
        candidate_filing_count=len(ordered_candidates),
        on_or_after_last_observation_candidate_count=on_or_after,
        required_field_assessments=assessments,
        candidate_filings=ordered_candidates,
    )


def _filing_rows(
    columns: dict[str, object], *, member_name: str
) -> tuple[dict[str, object], ...]:
    required = {
        "acceptanceDateTime",
        "accessionNumber",
        "filingDate",
        "form",
        "items",
        "primaryDocDescription",
        "primaryDocument",
    }
    if not required.issubset(columns) or any(
        not isinstance(columns[name], list) for name in required
    ):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle filing columns are incomplete"
        )
    lengths = {len(columns[name]) for name in required}  # type: ignore[arg-type]
    if len(lengths) != 1:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle filing columns are misaligned"
        )
    rows = []
    for index in range(lengths.pop()):
        accession = _required_text(columns["accessionNumber"][index])  # type: ignore[index]
        if re.fullmatch(_ACCESSION_PATTERN, accession) is None:
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "SEC lifecycle accession is invalid"
            )
        try:
            filed = date.fromisoformat(
                _required_text(columns["filingDate"][index])  # type: ignore[index]
            )
            accepted = datetime.strptime(
                _required_text(columns["acceptanceDateTime"][index]),  # type: ignore[index]
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ).replace(tzinfo=UTC)
            accepted = normalize_utc_datetime(accepted)
        except ValueError as exc:
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "SEC lifecycle filing clock is invalid"
            ) from exc
        document = _optional_text(columns["primaryDocument"][index])  # type: ignore[index]
        raw_items = _optional_text(columns["items"][index])  # type: ignore[index]
        rows.append(
            {
                "accession_number": accession,
                "form": _required_text(columns["form"][index]),  # type: ignore[index]
                "filing_date": filed,
                "acceptance_datetime": accepted,
                "primary_document": document,
                "primary_document_description": (
                    _optional_text(columns["primaryDocDescription"][index])  # type: ignore[index]
                    or "description_unavailable"
                ),
                "items": tuple(
                    sorted(
                        {
                            item.strip()
                            for item in (raw_items or "").split(",")
                            if item.strip()
                        }
                    )
                ),
                "source_member_name": member_name,
            }
        )
    return tuple(rows)


def _locator_categories(
    *, form: str, items: tuple[str, ...], filing_date: date, last_observed: date
) -> tuple[str, ...]:
    categories = set()
    if form in _DIRECT_LIFECYCLE_FORMS:
        categories.add("direct_lifecycle_form")
    if form in {"8-K", "8-K/A"} and set(items) & _STRUCTURED_8K_ITEMS:
        categories.add("structured_8k_lifecycle_item")
    if form == "6-K" and filing_date >= last_observed:
        categories.add("post_last_observation_foreign_report")
    return tuple(sorted(categories))


def _date_relation(
    *, filing_date: date, last_observed: date, delist_candidate: date
) -> str:
    if filing_date < last_observed:
        return "before_last_observation"
    if filing_date == last_observed:
        return "on_last_observation"
    if filing_date < delist_candidate:
        return "after_last_before_provider_delist_candidate"
    if filing_date == delist_candidate:
        return "on_provider_delist_candidate"
    return "after_provider_delist_candidate"


def _normalized_cik(value: object) -> str:
    text = str(value).strip()
    if not text.isdigit() or len(text) > 10:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle CIK locator is invalid"
        )
    return text.zfill(10)


def _json_member(archive: zipfile.ZipFile, name: str) -> object:
    try:
        raw = archive.read(name)
        return json.loads(raw)
    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle source member cannot be read"
        ) from exc


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle filing text is unavailable"
        )
    return value.strip()


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackSecLifecyclePilotV1,
) -> StrongLeaderPullbackSecLifecyclePilotResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_lifecycle_pilot(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecLifecyclePilotError(
                "existing SEC lifecycle pilot differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(partial / REPORT_FILE, _json_bytes(report.model_dump(mode="json")))
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_sec_lifecycle_pilot(
        output_root=target, output_custody_root=output_custody_root
    )
    if reread.report != report:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot formal reread differs"
        )
    return StrongLeaderPullbackSecLifecyclePilotResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_BUILD_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot custody or target is unsafe"
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
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot input is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "SEC lifecycle pilot file metadata differs"
        )


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _census_file_name(snapshot: date, start: date, end: date) -> str:
    return (
        f"census=snapshot-{snapshot.isoformat()}--range-"
        f"{start.isoformat()}--{end.isoformat()}.json"
    )


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


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
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value).rstrip(b"\n")).hexdigest()


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def blocked(*_args: object, **_kwargs: object) -> object:
        raise StrongLeaderPullbackSecLifecyclePilotError(
            "network access is prohibited for SEC lifecycle pilot construction"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
