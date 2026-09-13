"""Cross-document SEC candidate coverage for the first lifecycle sample."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_form15_candidates import (
    StrongLeaderPullbackSecForm15CandidatesResult,
    read_strong_leader_pullback_sec_form15_candidates,
)
from tip_api.services.strong_leader_pullback_sec_form25_candidates import (
    StrongLeaderPullbackSecForm25CandidatesResult,
    read_strong_leader_pullback_sec_form25_candidates,
)
from tip_api.services.strong_leader_pullback_sec_transaction_candidates import (
    StrongLeaderPullbackSecTransactionCandidatesResult,
    read_strong_leader_pullback_sec_transaction_candidates,
)
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    LIFECYCLE_REQUIRED_FIELDS,
    LifecycleSourceAcceptanceCaseV1,
    StrongLeaderPullbackSourceAcceptanceSampleResult,
    read_strong_leader_pullback_source_acceptance_sample,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-case-coverage-census/1.0"
REPORT_FILE = "census.json"
EXPECTED_CASE_COUNT = 64
EXPECTED_DOCUMENT_COUNT = 219
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"
SOURCE_FAMILIES = ("form15", "form25", "transaction")

CaseEvidenceProfile = Literal[
    "structured_transaction_scope",
    "notice_only_no_transaction_document",
    "referenced_completion_exhibit_body_missing",
    "no_registered_transaction_completion_scope",
]


class StrongLeaderPullbackSecCaseCoverageCensusError(RuntimeError):
    """Raised when cross-document candidate coverage cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCaseFieldCoverageV1(_FrozenModel):
    field_name: str
    source_document_counts: tuple[tuple[str, int], ...]
    candidate_document_count: int = Field(ge=0)
    candidate_source_family_count: int = Field(ge=0, le=3)
    candidate_presence_state: Literal[
        "present_in_retained_primary_documents",
        "absent_from_retained_primary_documents",
    ]
    complete_result_state: Literal["unsupported"] = "unsupported"
    result_state_reason: Literal[
        "candidate_semantics_and_security_identity_unadjudicated"
    ] = "candidate_semantics_and_security_identity_unadjudicated"

    @model_validator(mode="after")
    def coverage_reconciles(self) -> "SecCaseFieldCoverageV1":
        if (
            self.field_name not in LIFECYCLE_REQUIRED_FIELDS
            or tuple(name for name, _ in self.source_document_counts)
            != SOURCE_FAMILIES
            or any(count < 0 for _, count in self.source_document_counts)
            or self.candidate_document_count
            != sum(count for _, count in self.source_document_counts)
            or self.candidate_source_family_count
            != sum(count > 0 for _, count in self.source_document_counts)
            or self.candidate_presence_state
            != (
                "present_in_retained_primary_documents"
                if self.candidate_document_count
                else "absent_from_retained_primary_documents"
            )
        ):
            raise ValueError("SEC case field coverage differs")
        return self


class SecLifecycleCaseCoverageV1(_FrozenModel):
    instrument_id: UUID
    source_case_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    provider_ticker_locators: tuple[str, ...]
    cik_locators: tuple[str, ...]
    canonical_last_observed_date: date
    provider_delist_date_candidate: date
    form15_document_count: int = Field(ge=0)
    form25_document_count: int = Field(ge=0)
    transaction_document_count: int = Field(ge=0)
    total_document_count: int = Field(ge=0)
    multiple_document_family_count: int = Field(ge=0, le=3)
    form15_multiple_file_number_document_count: int = Field(ge=0)
    transaction_structure_counts: tuple[tuple[str, int], ...]
    evidence_profile: CaseEvidenceProfile
    referenced_completion_exhibit_body_missing: bool
    field_coverage: tuple[SecCaseFieldCoverageV1, ...]
    adjudicated_field_count: Literal[0] = 0
    matched_field_count: Literal[0] = 0
    absent_field_count: Literal[0] = 0
    ambiguous_field_count: Literal[0] = 0
    conflicting_field_count: Literal[0] = 0
    irrelevant_field_count: Literal[0] = 0
    unsupported_field_count: Literal[8] = 8
    stable_security_identity_authorized: Literal[False] = False
    lifecycle_fact_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator(
        "provider_ticker_locators", "cik_locators", mode="before"
    )
    @classmethod
    def locator_values_are_ordered_unique(
        cls, value: object
    ) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if not values or values != tuple(sorted(set(values))):
            raise ValueError("SEC case locators differ")
        return values

    @field_validator("transaction_structure_counts", mode="before")
    @classmethod
    def counts_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(values)) or len(values) != len(
            {item[0] for item in values}  # type: ignore[index]
        ):
            raise ValueError("SEC case structure counts differ")
        return values

    @model_validator(mode="after")
    def case_reconciles(self) -> "SecLifecycleCaseCoverageV1":
        counts = (
            self.form15_document_count,
            self.form25_document_count,
            self.transaction_document_count,
        )
        expected_reference = self.evidence_profile == (
            "referenced_completion_exhibit_body_missing"
        )
        if (
            self.total_document_count != sum(counts)
            or self.multiple_document_family_count != sum(count > 1 for count in counts)
            or sum(count for _, count in self.transaction_structure_counts)
            != self.transaction_document_count
            or self.referenced_completion_exhibit_body_missing != expected_reference
            or tuple(item.field_name for item in self.field_coverage)
            != LIFECYCLE_REQUIRED_FIELDS
        ):
            raise ValueError("SEC lifecycle case coverage differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC lifecycle case fingerprint differs")
        return self


class StrongLeaderPullbackSecCaseCoverageCensusV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-case-coverage-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "candidate_coverage_complete_field_adjudication_not_started"
    ] = "candidate_coverage_complete_field_adjudication_not_started"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    source_sample_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_sample_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    form25_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    form25_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    form15_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    form15_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    content_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[64] = EXPECTED_CASE_COUNT
    candidate_document_count: Literal[219] = EXPECTED_DOCUMENT_COUNT
    form15_case_count: int = Field(ge=0, le=64)
    form25_case_count: int = Field(ge=0, le=64)
    transaction_case_count: int = Field(ge=0, le=64)
    evidence_profile_counts: tuple[tuple[str, int], ...]
    field_candidate_case_counts: tuple[tuple[str, int], ...]
    field_complete_result_counts: tuple[tuple[str, int], ...]
    referenced_completion_exhibit_body_missing_case_count: int = Field(
        ge=0, le=64
    )
    adjudicated_case_count: Literal[0] = 0
    adjudicated_field_count: Literal[0] = 0
    matched_field_count: Literal[0] = 0
    absent_field_count: Literal[0] = 0
    ambiguous_field_count: Literal[0] = 0
    conflicting_field_count: Literal[0] = 0
    irrelevant_field_count: Literal[0] = 0
    unsupported_field_count: Literal[512] = 512
    cases: tuple[SecLifecycleCaseCoverageV1, ...]
    stable_security_identity_assignment_count: Literal[0] = 0
    transaction_completion_fact_count: Literal[0] = 0
    lifecycle_fact_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecCaseCoverageCensusV1":
        candidate_cases = Counter()
        for item in self.cases:
            candidate_cases.update(
                field.field_name
                for field in item.field_coverage
                if field.candidate_document_count
            )
        if (
            len(self.cases) != EXPECTED_CASE_COUNT
            or tuple(str(item.instrument_id) for item in self.cases)
            != tuple(sorted(str(item.instrument_id) for item in self.cases))
            or self.form15_case_count != sum(item.form15_document_count > 0 for item in self.cases)
            or self.form25_case_count != sum(item.form25_document_count > 0 for item in self.cases)
            or self.transaction_case_count
            != sum(item.transaction_document_count > 0 for item in self.cases)
            or self.evidence_profile_counts
            != _ordered(Counter(item.evidence_profile for item in self.cases))
            or self.field_candidate_case_counts != _all_field_counts(candidate_cases)
            or self.field_complete_result_counts
            != tuple((field, EXPECTED_CASE_COUNT) for field in LIFECYCLE_REQUIRED_FIELDS)
            or self.referenced_completion_exhibit_body_missing_case_count
            != sum(item.referenced_completion_exhibit_body_missing for item in self.cases)
        ):
            raise ValueError("SEC case coverage census aggregates differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC case coverage census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecCaseCoverageCensusResult:
    output_root: Path
    report: StrongLeaderPullbackSecCaseCoverageCensusV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_sec_case_coverage_census(
    *,
    source_sample_root: Path,
    source_sample_custody_root: Path,
    form25_root: Path,
    form25_custody_root: Path,
    form15_root: Path,
    form15_custody_root: Path,
    transaction_root: Path,
    transaction_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecCaseCoverageCensusResult:
    with _network_prohibited():
        sample = read_strong_leader_pullback_source_acceptance_sample(
            output_root=source_sample_root,
            output_custody_root=source_sample_custody_root,
        )
        form25 = read_strong_leader_pullback_sec_form25_candidates(
            output_root=form25_root, output_custody_root=form25_custody_root
        )
        form15 = read_strong_leader_pullback_sec_form15_candidates(
            output_root=form15_root, output_custody_root=form15_custody_root
        )
        transaction = read_strong_leader_pullback_sec_transaction_candidates(
            output_root=transaction_root,
            output_custody_root=transaction_custody_root,
        )
        report = _build_report(
            sample=sample,
            form25=form25,
            form15=form15,
            transaction=transaction,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_case_coverage_census(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecCaseCoverageCensusResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecCaseCoverageCensusV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage report bytes are not canonical"
        )
    return StrongLeaderPullbackSecCaseCoverageCensusResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    sample: StrongLeaderPullbackSourceAcceptanceSampleResult,
    form25: StrongLeaderPullbackSecForm25CandidatesResult,
    form15: StrongLeaderPullbackSecForm15CandidatesResult,
    transaction: StrongLeaderPullbackSecTransactionCandidatesResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecCaseCoverageCensusV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage revision is invalid"
        )
    reports = (form25.report, form15.report, transaction.report)
    if (
        len({item.plan_sha256 for item in reports}) != 1
        or len({item.source_manifest_sha256 for item in reports}) != 1
        or len({item.content_census_sha256 for item in reports}) != 1
        or form25.report.form25_document_count
        + form15.report.form15_document_count
        + transaction.report.transaction_document_count
        != EXPECTED_DOCUMENT_COUNT
    ):
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC candidate package bindings differ"
        )
    sample_ids = {item.instrument_id for item in sample.report.lifecycle_cases}
    package_ids = {
        item.instrument_id
        for report in reports
        for item in report.candidates
    }
    if len(sample_ids) != EXPECTED_CASE_COUNT or package_ids != sample_ids:
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC candidate/sample population differs"
        )
    form25_by_id = _by_id(form25.report.candidates)
    form15_by_id = _by_id(form15.report.candidates)
    transaction_by_id = _by_id(transaction.report.candidates)
    cases = tuple(
        _case_coverage(
            source_case=source_case,
            form25=tuple(form25_by_id[source_case.instrument_id]),
            form15=tuple(form15_by_id[source_case.instrument_id]),
            transaction=tuple(transaction_by_id[source_case.instrument_id]),
        )
        for source_case in sorted(
            sample.report.lifecycle_cases, key=lambda item: str(item.instrument_id)
        )
    )
    candidate_cases = Counter()
    for item in cases:
        candidate_cases.update(
            field.field_name
            for field in item.field_coverage
            if field.candidate_document_count
        )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "source_sample_sha256": sample.report_sha256,
        "source_sample_logical_fingerprint": sample.report.logical_fingerprint,
        "form25_report_sha256": form25.report_sha256,
        "form25_logical_fingerprint": form25.report.logical_fingerprint,
        "form15_report_sha256": form15.report_sha256,
        "form15_logical_fingerprint": form15.report.logical_fingerprint,
        "transaction_report_sha256": transaction.report_sha256,
        "transaction_logical_fingerprint": transaction.report.logical_fingerprint,
        "plan_sha256": form25.report.plan_sha256,
        "source_manifest_sha256": form25.report.source_manifest_sha256,
        "content_census_sha256": form25.report.content_census_sha256,
        "form15_case_count": sum(item.form15_document_count > 0 for item in cases),
        "form25_case_count": sum(item.form25_document_count > 0 for item in cases),
        "transaction_case_count": sum(
            item.transaction_document_count > 0 for item in cases
        ),
        "evidence_profile_counts": _ordered(
            Counter(item.evidence_profile for item in cases)
        ),
        "field_candidate_case_counts": _all_field_counts(candidate_cases),
        "field_complete_result_counts": tuple(
            (field, EXPECTED_CASE_COUNT) for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "referenced_completion_exhibit_body_missing_case_count": sum(
            item.referenced_completion_exhibit_body_missing for item in cases
        ),
        "cases": cases,
    }
    provisional = StrongLeaderPullbackSecCaseCoverageCensusV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecCaseCoverageCensusV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _case_coverage(
    *,
    source_case: LifecycleSourceAcceptanceCaseV1,
    form25: tuple[object, ...],
    form15: tuple[object, ...],
    transaction: tuple[object, ...],
) -> SecLifecycleCaseCoverageV1:
    structures = Counter(item.structure_state for item in transaction)  # type: ignore[attr-defined]
    profile = _evidence_profile(structures, len(transaction))
    fields = tuple(
        _field_coverage(
            field=field, form25=form25, form15=form15, transaction=transaction
        )
        for field in LIFECYCLE_REQUIRED_FIELDS
    )
    values = {
        "instrument_id": source_case.instrument_id,
        "source_case_fingerprint": _fingerprint(source_case.model_dump(mode="json")),
        "provider_ticker_locators": source_case.provider_ticker_locators,
        "cik_locators": source_case.cik_locators,
        "canonical_last_observed_date": source_case.canonical_last_observed_date,
        "provider_delist_date_candidate": source_case.provider_delist_date_candidate,
        "form15_document_count": len(form15),
        "form25_document_count": len(form25),
        "transaction_document_count": len(transaction),
        "total_document_count": len(form15) + len(form25) + len(transaction),
        "multiple_document_family_count": sum(
            count > 1 for count in (len(form15), len(form25), len(transaction))
        ),
        "form15_multiple_file_number_document_count": sum(
            item.commission_file_number_state == "multiple_candidates"  # type: ignore[attr-defined]
            for item in form15
        ),
        "transaction_structure_counts": _ordered(structures),
        "evidence_profile": profile,
        "referenced_completion_exhibit_body_missing": profile
        == "referenced_completion_exhibit_body_missing",
        "field_coverage": fields,
    }
    provisional = SecLifecycleCaseCoverageV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecLifecycleCaseCoverageV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _field_coverage(
    *,
    field: str,
    form25: tuple[object, ...],
    form15: tuple[object, ...],
    transaction: tuple[object, ...],
) -> SecCaseFieldCoverageV1:
    counts = (
        ("form15", _partial_candidate_count(form15, field)),
        ("form25", _partial_candidate_count(form25, field)),
        ("transaction", _partial_candidate_count(transaction, field)),
    )
    total = sum(count for _, count in counts)
    return SecCaseFieldCoverageV1(
        field_name=field,
        source_document_counts=counts,
        candidate_document_count=total,
        candidate_source_family_count=sum(count > 0 for _, count in counts),
        candidate_presence_state=(
            "present_in_retained_primary_documents"
            if total
            else "absent_from_retained_primary_documents"
        ),
    )


def _partial_candidate_count(items: tuple[object, ...], field: str) -> int:
    return sum(
        field in getattr(item, "partial_field_candidates") for item in items
    )


def _evidence_profile(
    structures: Counter[str], transaction_count: int
) -> CaseEvidenceProfile:
    if structures["8k_item_2_01_candidate_scope"]:
        return "structured_transaction_scope"
    if structures["foreign_report_referenced_exhibit_only"]:
        return "referenced_completion_exhibit_body_missing"
    if transaction_count == 0:
        return "notice_only_no_transaction_document"
    return "no_registered_transaction_completion_scope"


def _by_id(items: tuple[object, ...]) -> defaultdict[UUID, list[object]]:
    values: defaultdict[UUID, list[object]] = defaultdict(list)
    for item in items:
        values[item.instrument_id].append(item)  # type: ignore[attr-defined]
    return values


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecCaseCoverageCensusV1,
) -> StrongLeaderPullbackSecCaseCoverageCensusResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_case_coverage_census(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecCaseCoverageCensusError(
                "existing SEC case coverage report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(
            partial / REPORT_FILE, _json_bytes(report.model_dump(mode="json"))
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_sec_case_coverage_census(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecCaseCoverageCensusResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage paths must be absolute"
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
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage custody or target is unsafe"
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
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "SEC case coverage file metadata differs"
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


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


def _all_field_counts(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple((field, counter[field]) for field in LIFECYCLE_REQUIRED_FIELDS)


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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fingerprint(value: object) -> str:
    return _sha256_bytes(_json_bytes(value).rstrip(b"\n"))


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackSecCaseCoverageCensusError(
            "network access is prohibited during SEC case coverage census"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
