"""Network-free SEC Submissions payload and Company Facts accession census."""

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
from pathlib import Path
from typing import Iterable, Literal, Mapping, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.companyfacts_payload_census import (
    SecCompanyfactsPayloadCensusV1,
    extract_sec_companyfacts_in_range_accessions,
    read_sealed_sec_companyfacts_payload_census,
)
from tip_api.providers.sec.companyfacts_source import (
    SecCompanyfactsSourceManifestV1,
    read_sec_companyfacts_source_package,
)
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    SUBMISSIONS_PROFILE,
    SecSubmissionsSourceManifestV1,
    read_sec_submissions_source_package,
)


CONTRACT_VERSION = "sec-submissions-payload-census/1.1"
MAXIMUM_WORKERS = 16
MAXIMUM_OUTPUT_BYTES = 16 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")
_ACCEPTANCE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z\Z"
)
_ROOT_FIELDS = frozenset(
    {
        "addresses",
        "category",
        "cik",
        "description",
        "ein",
        "entityType",
        "exchanges",
        "filings",
        "fiscalYearEnd",
        "flags",
        "formerNames",
        "insiderTransactionForIssuerExists",
        "insiderTransactionForOwnerExists",
        "investorWebsite",
        "lei",
        "name",
        "ownerOrg",
        "phone",
        "sic",
        "sicDescription",
        "stateOfIncorporation",
        "stateOfIncorporationDescription",
        "tickers",
        "website",
    }
)
_FILING_COLUMNS = frozenset(
    {
        "acceptanceDateTime",
        "accessionNumber",
        "act",
        "core_type",
        "fileNumber",
        "filingDate",
        "filmNumber",
        "form",
        "isInlineXBRL",
        "isXBRL",
        "isXBRLNumeric",
        "items",
        "primaryDocDescription",
        "primaryDocument",
        "reportDate",
        "size",
    }
)
_REQUIRED_FILING_COLUMNS = frozenset(
    {"acceptanceDateTime", "accessionNumber", "filingDate", "form"}
)
_FILE_REFERENCE_FIELDS = frozenset(
    {"name", "filingCount", "filingFrom", "filingTo"}
)
_MappingValue = TypeVar("_MappingValue")


class SecSubmissionsPayloadCensusError(RuntimeError):
    """Raised when exact filing-time coverage cannot be measured safely."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuarantinedSubmissionMemberV1(_FrozenModel):
    member_name: str
    reason_code: str


class SecSubmissionsPayloadCensusV1(_FrozenModel):
    contract_version: Literal["sec-submissions-payload-census/1.1"] = (
        CONTRACT_VERSION
    )
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    range_start: date
    range_end: date
    evaluated_at: datetime
    submissions_snapshot_date: date
    submissions_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    companyfacts_snapshot_date: date
    companyfacts_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    companyfacts_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    companyfacts_payload_census_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_member_count: int = Field(ge=1)
    source_unique_cik_count: int = Field(ge=1)
    source_root_member_count: int = Field(ge=0)
    source_historical_shard_member_count: int = Field(ge=0)
    source_placeholder_member_count: int = Field(ge=0)
    payload_read_member_count: int = Field(ge=1)
    validated_root_member_count: int = Field(ge=0)
    validated_historical_shard_member_count: int = Field(ge=0)
    validated_placeholder_member_count: int = Field(ge=0)
    quarantined_member_count: int = Field(ge=0)
    quarantined_members: tuple[QuarantinedSubmissionMemberV1, ...]
    payload_validation_status: Literal[
        "complete", "complete_with_quarantined_members"
    ]
    filing_row_count: int = Field(ge=0)
    filing_date_before_range_count: int = Field(ge=0)
    filing_date_in_range_count: int = Field(ge=0)
    filing_date_after_range_count: int = Field(ge=0)
    filing_date_invalid_or_missing_count: int = Field(ge=0)
    earliest_valid_filing_date: date | None = None
    latest_valid_filing_date: date | None = None
    valid_accession_row_count: int = Field(ge=0)
    invalid_or_missing_accession_row_count: int = Field(ge=0)
    accession_member_cik_mismatch_row_count: int = Field(ge=0)
    valid_acceptance_datetime_row_count: int = Field(ge=0)
    missing_acceptance_datetime_row_count: int = Field(ge=0)
    invalid_acceptance_datetime_row_count: int = Field(ge=0)
    root_reference_row_count: int = Field(ge=0)
    invalid_root_reference_row_count: int = Field(ge=0)
    unique_root_reference_count: int = Field(ge=0)
    referenced_shard_present_count: int = Field(ge=0)
    missing_referenced_shard_count: int = Field(ge=0)
    unreferenced_actual_shard_count: int = Field(ge=0)
    root_current_ticker_exchange_aligned_count: int = Field(ge=0)
    root_current_ticker_exchange_empty_count: int = Field(ge=0)
    root_current_ticker_exchange_malformed_count: int = Field(ge=0)
    former_name_record_count: int = Field(ge=0)
    companyfacts_target_accession_count: int = Field(ge=0)
    target_accession_matched_count: int = Field(ge=0)
    target_accession_missing_count: int = Field(ge=0)
    target_duplicate_accession_count: int = Field(ge=0)
    target_with_valid_acceptance_count: int = Field(ge=0)
    target_without_valid_acceptance_count: int = Field(ge=0)
    target_conflicting_acceptance_count: int = Field(ge=0)
    target_filing_date_exact_match_count: int = Field(ge=0)
    target_filing_date_disagreement_count: int = Field(ge=0)
    target_filing_date_unavailable_count: int = Field(ge=0)
    target_missing_accession_samples: tuple[str, ...]
    target_missing_accession_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    target_acceptance_mapping_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    form_counts: tuple[tuple[str, int], ...]
    in_range_form_counts: tuple[tuple[str, int], ...]
    unexpected_root_field_counts: tuple[tuple[str, int], ...]
    unexpected_filing_column_counts: tuple[tuple[str, int], ...]
    unexpected_file_reference_field_counts: tuple[tuple[str, int], ...]
    worker_count: int = Field(ge=1, le=MAXIMUM_WORKERS)
    full_member_crc_and_json_read: Literal[True] = True
    acceptance_timezone_semantics_status: Literal[
        "sec_utc_timestamp_pending_market_session_mapping"
    ] = "sec_utc_timestamp_pending_market_session_mapping"
    acceptance_datetime_same_day_eligibility: Literal[False] = False
    stable_instrument_resolution_count: Literal[0] = 0
    normalized_filing_write_count: Literal[0] = 0
    normalized_fact_write_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def census_reconciles(self) -> "SecSubmissionsPayloadCensusV1":
        if self.range_end < self.range_start:
            raise ValueError("SEC Submissions census range is reversed")
        if self.payload_read_member_count != self.source_member_count:
            raise ValueError("SEC Submissions member read count differs")
        if (
            self.source_root_member_count
            + self.source_historical_shard_member_count
            + self.source_placeholder_member_count
            != self.source_member_count
        ):
            raise ValueError("SEC Submissions source member counts differ")
        if self.source_root_member_count != self.source_unique_cik_count:
            raise ValueError("SEC Submissions source CIK root counts differ")
        if (
            self.validated_root_member_count
            + self.validated_historical_shard_member_count
            + self.validated_placeholder_member_count
            + self.quarantined_member_count
            != self.source_member_count
        ):
            raise ValueError("SEC Submissions member state counts differ")
        if self.quarantined_member_count != len(self.quarantined_members):
            raise ValueError("SEC Submissions quarantine count differs")
        expected_status = (
            "complete_with_quarantined_members"
            if self.quarantined_members
            else "complete"
        )
        if self.payload_validation_status != expected_status:
            raise ValueError("SEC Submissions validation status differs")
        if (
            self.filing_date_before_range_count
            + self.filing_date_in_range_count
            + self.filing_date_after_range_count
            + self.filing_date_invalid_or_missing_count
            != self.filing_row_count
        ):
            raise ValueError("SEC Submissions filing-date counts differ")
        if (
            self.valid_accession_row_count
            + self.invalid_or_missing_accession_row_count
            != self.filing_row_count
        ):
            raise ValueError("SEC Submissions accession counts differ")
        if (
            self.valid_acceptance_datetime_row_count
            + self.missing_acceptance_datetime_row_count
            + self.invalid_acceptance_datetime_row_count
            != self.filing_row_count
        ):
            raise ValueError("SEC Submissions acceptance counts differ")
        if (
            self.referenced_shard_present_count
            + self.missing_referenced_shard_count
            != self.unique_root_reference_count
        ):
            raise ValueError("SEC Submissions reference counts differ")
        if (
            self.referenced_shard_present_count
            + self.unreferenced_actual_shard_count
            != self.source_historical_shard_member_count
        ):
            raise ValueError("SEC Submissions shard coverage differs")
        if (
            self.root_current_ticker_exchange_aligned_count
            + self.root_current_ticker_exchange_empty_count
            + self.root_current_ticker_exchange_malformed_count
            != self.validated_root_member_count
        ):
            raise ValueError("SEC Submissions current ticker counts differ")
        if (
            self.target_accession_matched_count
            + self.target_accession_missing_count
            != self.companyfacts_target_accession_count
        ):
            raise ValueError("SEC Submissions target coverage differs")
        if (
            self.target_with_valid_acceptance_count
            + self.target_without_valid_acceptance_count
            != self.target_accession_matched_count
        ):
            raise ValueError("SEC Submissions target acceptance differs")
        if (
            self.target_filing_date_exact_match_count
            + self.target_filing_date_disagreement_count
            + self.target_filing_date_unavailable_count
            != self.target_accession_matched_count
        ):
            raise ValueError("SEC Submissions target filed-date counts differ")
        for values in (
            self.form_counts,
            self.in_range_form_counts,
            self.unexpected_root_field_counts,
            self.unexpected_filing_column_counts,
            self.unexpected_file_reference_field_counts,
        ):
            if values != tuple(sorted(values)) or any(count < 1 for _, count in values):
                raise ValueError("SEC Submissions ordered counts differ")
        if self.target_missing_accession_samples != tuple(
            sorted(self.target_missing_accession_samples)
        ):
            raise ValueError("SEC Submissions missing samples differ")
        if tuple(
            (item.member_name, item.reason_code)
            for item in self.quarantined_members
        ) != tuple(
            sorted(
                (item.member_name, item.reason_code)
                for item in self.quarantined_members
            )
        ):
            raise ValueError("SEC Submissions quarantine order differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC Submissions census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class _Partial:
    member_count: int
    root_count: int
    shard_count: int
    placeholder_count: int
    quarantined: tuple[tuple[str, str], ...]
    filing_count: int
    filing_dates: Counter[str]
    earliest_filing: date | None
    latest_filing: date | None
    valid_accession_count: int
    invalid_accession_count: int
    accession_cik_mismatch_count: int
    acceptance_counts: Counter[str]
    reference_row_count: int
    invalid_reference_count: int
    references: frozenset[str]
    ticker_states: Counter[str]
    former_name_count: int
    forms: Counter[str]
    in_range_forms: Counter[str]
    unexpected_root: Counter[str]
    unexpected_columns: Counter[str]
    unexpected_reference: Counter[str]
    target_rows: Counter[str]
    target_acceptances: dict[str, tuple[str, ...]]
    target_filing_dates: dict[str, tuple[date, ...]]


def census_sec_submissions_payloads(
    *,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    companyfacts_package_path: Path,
    companyfacts_custody_root: Path,
    companyfacts_census_root: Path,
    range_start: date,
    range_end: date,
    worker_count: int,
    evaluated_at: datetime | None = None,
) -> SecSubmissionsPayloadCensusV1:
    """Validate all filing payloads and measure Company Facts accession clocks."""

    if range_end < range_start:
        raise SecSubmissionsPayloadCensusError("Submissions census range is reversed")
    if worker_count < 1 or worker_count > MAXIMUM_WORKERS:
        raise SecSubmissionsPayloadCensusError("Submissions worker count is invalid")
    submissions = read_sec_submissions_source_package(
        package_path=submissions_package_path,
        approved_custody_root=submissions_custody_root,
    )
    companyfacts = read_sec_companyfacts_source_package(
        package_path=companyfacts_package_path,
        approved_custody_root=companyfacts_custody_root,
    )
    companyfacts_census = read_sealed_sec_companyfacts_payload_census(
        output_root=companyfacts_census_root,
        source_snapshot_date=companyfacts.remote.last_modified.date(),
        range_start=range_start,
        range_end=range_end,
    )
    _validate_companyfacts_binding(companyfacts, companyfacts_census)
    targets = extract_sec_companyfacts_in_range_accessions(
        source_package_path=companyfacts_package_path,
        source_custody_root=companyfacts_custody_root,
        range_start=range_start,
        range_end=range_end,
        worker_count=worker_count,
    )
    if len(targets) != companyfacts_census.in_range_unique_accession_count:
        raise SecSubmissionsPayloadCensusError(
            "Company Facts target accession count differs"
        )

    archive_path = submissions_package_path / ARCHIVE_FILE
    with zipfile.ZipFile(archive_path) as archive:
        names = tuple(sorted(item.filename for item in archive.infolist()))
    if (
        len(names) != submissions.member_count
        or _fingerprint(names) != submissions.member_name_fingerprint
    ):
        raise SecSubmissionsPayloadCensusError("Submissions member binding differs")
    actual_shards = frozenset(
        name
        for name in names
        if (match := SUBMISSIONS_PROFILE.member_pattern.fullmatch(name)) is not None
        and match.groupdict().get("shard") is not None
    )
    actual_roots = frozenset(
        name
        for name in names
        if (match := SUBMISSIONS_PROFILE.member_pattern.fullmatch(name)) is not None
        and match.groupdict().get("shard") is None
    )
    actual_placeholders = frozenset(
        name for name in names if name in SUBMISSIONS_PROFILE.allowed_non_cik_members
    )
    partitions = tuple(
        names[index::worker_count]
        for index in range(worker_count)
        if names[index::worker_count]
    )
    arguments = tuple(
        (str(archive_path), partition, range_start, range_end, targets)
        for partition in partitions
    )
    if worker_count == 1:
        partials = tuple(_census_batch(argument) for argument in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            partials = tuple(executor.map(_census_batch, arguments))
    return _combine(
        partials=partials,
        submissions=submissions,
        companyfacts=companyfacts,
        companyfacts_census=companyfacts_census,
        targets=targets,
        actual_roots=actual_roots,
        actual_shards=actual_shards,
        actual_placeholders=actual_placeholders,
        submissions_manifest_sha256=_sha256_file(
            submissions_package_path / "package.json"
        ),
        companyfacts_manifest_sha256=_sha256_file(
            companyfacts_package_path / "package.json"
        ),
        range_start=range_start,
        range_end=range_end,
        worker_count=worker_count,
        evaluated_at=normalize_utc_datetime(evaluated_at or datetime.now(UTC)),
    )


def seal_sec_submissions_payload_census(
    *, output_root: Path, census: SecSubmissionsPayloadCensusV1
) -> Path:
    root = _validate_output_root(output_root)
    target = root / _file_name(
        census.submissions_snapshot_date, census.range_start, census.range_end
    )
    raw = _json_bytes(census.model_dump(mode="json")) + b"\n"
    if len(raw) > MAXIMUM_OUTPUT_BYTES:
        raise SecSubmissionsPayloadCensusError("Submissions census exceeds byte ceiling")
    descriptor = os.open(
        target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o400
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    target.chmod(0o400)
    _fsync_directory(root)
    return target


def read_sealed_sec_submissions_payload_census(
    *,
    output_root: Path,
    source_snapshot_date: date,
    range_start: date,
    range_end: date,
) -> SecSubmissionsPayloadCensusV1:
    root = _validate_output_root(output_root)
    target = root / _file_name(source_snapshot_date, range_start, range_end)
    if target.is_symlink() or not target.is_file():
        raise SecSubmissionsPayloadCensusError("sealed Submissions census is unavailable")
    metadata = target.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise SecSubmissionsPayloadCensusError("sealed Submissions census mode differs")
    if metadata.st_size < 1 or metadata.st_size > MAXIMUM_OUTPUT_BYTES:
        raise SecSubmissionsPayloadCensusError("sealed Submissions census size differs")
    try:
        result = SecSubmissionsPayloadCensusV1.model_validate_json(target.read_bytes())
    except Exception as exc:
        raise SecSubmissionsPayloadCensusError("sealed Submissions census is invalid") from exc
    if (
        result.submissions_snapshot_date != source_snapshot_date
        or result.range_start != range_start
        or result.range_end != range_end
    ):
        raise SecSubmissionsPayloadCensusError("sealed Submissions census scope differs")
    return result


def _census_batch(
    argument: tuple[
        str,
        tuple[str, ...],
        date,
        date,
        dict[str, tuple[date, ...]],
    ]
) -> _Partial:
    archive_name, names, range_start, range_end, targets = argument
    root_count = shard_count = placeholder_count = filing_count = 0
    valid_accessions = invalid_accessions = accession_cik_mismatch = 0
    reference_rows = invalid_references = former_names = 0
    earliest_filing: date | None = None
    latest_filing: date | None = None
    quarantined: list[tuple[str, str]] = []
    references: set[str] = set()
    target_acceptances: dict[str, set[str]] = {}
    target_filing_dates: dict[str, set[date]] = {}
    counters: dict[str, Counter[str]] = {
        name: Counter()
        for name in (
            "filing_dates",
            "acceptance",
            "ticker_states",
            "forms",
            "in_range_forms",
            "unexpected_root",
            "unexpected_columns",
            "unexpected_reference",
            "target_rows",
        )
    }
    with zipfile.ZipFile(archive_name) as archive:
        for name in names:
            try:
                with archive.open(name) as handle:
                    raw = handle.read()
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise SecSubmissionsPayloadCensusError(
                    "Submissions member CRC/read failed"
                ) from exc
            if name == "placeholder.txt":
                if _printable_placeholder(raw):
                    placeholder_count += 1
                else:
                    quarantined.append((name, "invalid_placeholder"))
                continue
            match = SUBMISSIONS_PROFILE.member_pattern.fullmatch(name)
            if match is None:
                quarantined.append((name, "unexpected_member_name"))
                continue
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                quarantined.append((name, "invalid_json"))
                continue
            cik = match.group("cik")
            is_shard = match.groupdict().get("shard") is not None
            if is_shard:
                if not isinstance(payload, dict):
                    quarantined.append((name, "shard_root_invalid"))
                    continue
                columns = payload
            else:
                reason = _root_reason(payload, cik)
                if reason is not None:
                    quarantined.append((name, reason))
                    continue
                assert isinstance(payload, dict)
                filings = payload["filings"]
                columns = filings["recent"]
                files = filings["files"]
            reason = _columns_reason(columns)
            if reason is not None:
                quarantined.append((name, reason))
                continue
            if is_shard:
                shard_count += 1
            else:
                root_count += 1
                counters["unexpected_root"].update(set(payload) - _ROOT_FIELDS)
                state = _ticker_exchange_state(payload)
                counters["ticker_states"][state] += 1
                if isinstance(payload.get("formerNames"), list):
                    former_names += len(payload["formerNames"])
                for reference in files:
                    reference_rows += 1
                    reference_name = _reference_name(reference, cik)
                    if reference_name is None:
                        invalid_references += 1
                        continue
                    assert isinstance(reference, dict)
                    counters["unexpected_reference"].update(
                        set(reference) - _FILE_REFERENCE_FIELDS
                    )
                    references.add(reference_name)
            if not columns:
                continue
            counters["unexpected_columns"].update(set(columns) - _FILING_COLUMNS)
            row_count = len(columns["accessionNumber"])
            filing_count += row_count
            for index in range(row_count):
                accession = _text(columns["accessionNumber"][index])
                if accession is None or _ACCESSION.fullmatch(accession) is None:
                    invalid_accessions += 1
                    accession = None
                else:
                    valid_accessions += 1
                    if accession[:10] != cik:
                        accession_cik_mismatch += 1
                filed = _date_value(columns["filingDate"][index])
                if filed is None:
                    counters["filing_dates"]["invalid"] += 1
                else:
                    earliest_filing = min(earliest_filing, filed) if earliest_filing else filed
                    latest_filing = max(latest_filing, filed) if latest_filing else filed
                    if filed < range_start:
                        counters["filing_dates"]["before"] += 1
                    elif filed > range_end:
                        counters["filing_dates"]["after"] += 1
                    else:
                        counters["filing_dates"]["in_range"] += 1
                acceptance_state, acceptance = _acceptance_value(
                    columns["acceptanceDateTime"][index]
                )
                counters["acceptance"][acceptance_state] += 1
                form = _text(columns["form"][index])
                if form is not None:
                    counters["forms"][form] += 1
                    if filed is not None and range_start <= filed <= range_end:
                        counters["in_range_forms"][form] += 1
                if accession is not None and accession in targets:
                    counters["target_rows"][accession] += 1
                    if filed is not None:
                        target_filing_dates.setdefault(accession, set()).add(filed)
                    if acceptance is not None:
                        target_acceptances.setdefault(accession, set()).add(acceptance)
    return _Partial(
        member_count=len(names),
        root_count=root_count,
        shard_count=shard_count,
        placeholder_count=placeholder_count,
        quarantined=tuple(quarantined),
        filing_count=filing_count,
        filing_dates=counters["filing_dates"],
        earliest_filing=earliest_filing,
        latest_filing=latest_filing,
        valid_accession_count=valid_accessions,
        invalid_accession_count=invalid_accessions,
        accession_cik_mismatch_count=accession_cik_mismatch,
        acceptance_counts=counters["acceptance"],
        reference_row_count=reference_rows,
        invalid_reference_count=invalid_references,
        references=frozenset(references),
        ticker_states=counters["ticker_states"],
        former_name_count=former_names,
        forms=counters["forms"],
        in_range_forms=counters["in_range_forms"],
        unexpected_root=counters["unexpected_root"],
        unexpected_columns=counters["unexpected_columns"],
        unexpected_reference=counters["unexpected_reference"],
        target_rows=counters["target_rows"],
        target_acceptances={
            key: tuple(sorted(values)) for key, values in target_acceptances.items()
        },
        target_filing_dates={
            key: tuple(sorted(values)) for key, values in target_filing_dates.items()
        },
    )


def _combine(
    *,
    partials: tuple[_Partial, ...],
    submissions: SecSubmissionsSourceManifestV1,
    companyfacts: SecCompanyfactsSourceManifestV1,
    companyfacts_census: SecCompanyfactsPayloadCensusV1,
    targets: dict[str, tuple[date, ...]],
    actual_roots: frozenset[str],
    actual_shards: frozenset[str],
    actual_placeholders: frozenset[str],
    submissions_manifest_sha256: str,
    companyfacts_manifest_sha256: str,
    range_start: date,
    range_end: date,
    worker_count: int,
    evaluated_at: datetime,
) -> SecSubmissionsPayloadCensusV1:
    counters = {
        name: sum((getattr(partial, name) for partial in partials), Counter())
        for name in (
            "filing_dates",
            "acceptance_counts",
            "ticker_states",
            "forms",
            "in_range_forms",
            "unexpected_root",
            "unexpected_columns",
            "unexpected_reference",
            "target_rows",
        )
    }
    references = set().union(*(partial.references for partial in partials))
    target_acceptances = _merge_set_mappings(
        partial.target_acceptances for partial in partials
    )
    target_filing_dates = _merge_set_mappings(
        partial.target_filing_dates for partial in partials
    )
    matched = set(counters["target_rows"])
    missing = sorted(set(targets) - matched)
    quarantined = tuple(
        QuarantinedSubmissionMemberV1(member_name=name, reason_code=reason)
        for name, reason in sorted(
            item for partial in partials for item in partial.quarantined
        )
    )
    present_references = references & actual_shards
    valid_acceptance_targets = {
        accession for accession in matched if target_acceptances.get(accession)
    }
    filing_exact = {
        accession
        for accession in matched
        if accession in target_filing_dates
        and tuple(target_filing_dates[accession]) == targets[accession]
    }
    filing_unavailable = {
        accession for accession in matched if accession not in target_filing_dates
    }
    earliest = tuple(
        item.earliest_filing for item in partials if item.earliest_filing is not None
    )
    latest = tuple(
        item.latest_filing for item in partials if item.latest_filing is not None
    )
    acceptance_mapping = tuple(
        (accession, tuple(target_acceptances.get(accession, ())))
        for accession in sorted(matched)
    )
    values = {
        "contract_version": CONTRACT_VERSION,
        "provider_id": "sec_edgar",
        "range_start": range_start,
        "range_end": range_end,
        "evaluated_at": evaluated_at,
        "submissions_snapshot_date": submissions.remote.last_modified.date(),
        "submissions_manifest_sha256": submissions_manifest_sha256,
        "submissions_source_fingerprint": submissions.logical_fingerprint,
        "submissions_archive_sha256": submissions.archive_sha256,
        "companyfacts_snapshot_date": companyfacts.remote.last_modified.date(),
        "companyfacts_manifest_sha256": companyfacts_manifest_sha256,
        "companyfacts_source_fingerprint": companyfacts.logical_fingerprint,
        "companyfacts_payload_census_fingerprint": companyfacts_census.logical_fingerprint,
        "source_member_count": submissions.member_count,
        "source_unique_cik_count": submissions.unique_cik_count,
        "source_root_member_count": len(actual_roots),
        "source_historical_shard_member_count": len(actual_shards),
        "source_placeholder_member_count": len(actual_placeholders),
        "payload_read_member_count": sum(item.member_count for item in partials),
        "validated_root_member_count": sum(item.root_count for item in partials),
        "validated_historical_shard_member_count": sum(
            item.shard_count for item in partials
        ),
        "validated_placeholder_member_count": sum(
            item.placeholder_count for item in partials
        ),
        "quarantined_member_count": len(quarantined),
        "quarantined_members": quarantined,
        "payload_validation_status": (
            "complete_with_quarantined_members" if quarantined else "complete"
        ),
        "filing_row_count": sum(item.filing_count for item in partials),
        "filing_date_before_range_count": counters["filing_dates"]["before"],
        "filing_date_in_range_count": counters["filing_dates"]["in_range"],
        "filing_date_after_range_count": counters["filing_dates"]["after"],
        "filing_date_invalid_or_missing_count": counters["filing_dates"]["invalid"],
        "earliest_valid_filing_date": min(earliest) if earliest else None,
        "latest_valid_filing_date": max(latest) if latest else None,
        "valid_accession_row_count": sum(item.valid_accession_count for item in partials),
        "invalid_or_missing_accession_row_count": sum(
            item.invalid_accession_count for item in partials
        ),
        "accession_member_cik_mismatch_row_count": sum(
            item.accession_cik_mismatch_count for item in partials
        ),
        "valid_acceptance_datetime_row_count": counters["acceptance_counts"]["valid"],
        "missing_acceptance_datetime_row_count": counters["acceptance_counts"]["missing"],
        "invalid_acceptance_datetime_row_count": counters["acceptance_counts"]["invalid"],
        "root_reference_row_count": sum(item.reference_row_count for item in partials),
        "invalid_root_reference_row_count": sum(
            item.invalid_reference_count for item in partials
        ),
        "unique_root_reference_count": len(references),
        "referenced_shard_present_count": len(present_references),
        "missing_referenced_shard_count": len(references - actual_shards),
        "unreferenced_actual_shard_count": len(actual_shards - references),
        "root_current_ticker_exchange_aligned_count": counters["ticker_states"]["aligned"],
        "root_current_ticker_exchange_empty_count": counters["ticker_states"]["empty"],
        "root_current_ticker_exchange_malformed_count": counters["ticker_states"]["malformed"],
        "former_name_record_count": sum(item.former_name_count for item in partials),
        "companyfacts_target_accession_count": len(targets),
        "target_accession_matched_count": len(matched),
        "target_accession_missing_count": len(missing),
        "target_duplicate_accession_count": sum(
            count > 1 for count in counters["target_rows"].values()
        ),
        "target_with_valid_acceptance_count": len(valid_acceptance_targets),
        "target_without_valid_acceptance_count": len(matched - valid_acceptance_targets),
        "target_conflicting_acceptance_count": sum(
            len(values) > 1 for values in target_acceptances.values()
        ),
        "target_filing_date_exact_match_count": len(filing_exact),
        "target_filing_date_disagreement_count": len(
            matched - filing_exact - filing_unavailable
        ),
        "target_filing_date_unavailable_count": len(filing_unavailable),
        "target_missing_accession_samples": tuple(missing[:100]),
        "target_missing_accession_fingerprint": _fingerprint(tuple(missing)),
        "target_acceptance_mapping_fingerprint": _fingerprint(acceptance_mapping),
        "form_counts": _ordered(counters["forms"]),
        "in_range_form_counts": _ordered(counters["in_range_forms"]),
        "unexpected_root_field_counts": _ordered(counters["unexpected_root"]),
        "unexpected_filing_column_counts": _ordered(counters["unexpected_columns"]),
        "unexpected_file_reference_field_counts": _ordered(counters["unexpected_reference"]),
        "worker_count": worker_count,
        "full_member_crc_and_json_read": True,
        "acceptance_timezone_semantics_status": (
            "sec_utc_timestamp_pending_market_session_mapping"
        ),
        "acceptance_datetime_same_day_eligibility": False,
        "stable_instrument_resolution_count": 0,
        "normalized_filing_write_count": 0,
        "normalized_fact_write_count": 0,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return SecSubmissionsPayloadCensusV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _validate_companyfacts_binding(
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
        raise SecSubmissionsPayloadCensusError(
            "Company Facts source/census binding differs"
        )


def _root_reason(payload: object, expected_cik: str) -> str | None:
    if not isinstance(payload, dict):
        return "root_not_object"
    cik = payload.get("cik")
    if not isinstance(cik, (str, int)) or isinstance(cik, bool):
        return "root_cik_invalid"
    if not str(cik).isdigit() or str(cik).zfill(10) != expected_cik:
        return "root_cik_mismatch"
    filings = payload.get("filings")
    if not isinstance(filings, dict):
        return "filings_root_invalid"
    if not isinstance(filings.get("recent"), dict):
        return "recent_columns_invalid"
    if not isinstance(filings.get("files"), list):
        return "historical_files_invalid"
    return None


def _columns_reason(columns: object) -> str | None:
    if not isinstance(columns, dict):
        return "filing_columns_not_object"
    if not columns:
        return None
    if not _REQUIRED_FILING_COLUMNS.issubset(columns):
        return "required_filing_columns_missing"
    if any(not isinstance(value, list) for value in columns.values()):
        return "filing_column_not_array"
    if len({len(value) for value in columns.values()}) != 1:
        return "filing_columns_misaligned"
    return None


def _reference_name(reference: object, expected_cik: str) -> str | None:
    if not isinstance(reference, dict):
        return None
    name = reference.get("name")
    count = reference.get("filingCount")
    start = _date_value(reference.get("filingFrom"))
    end = _date_value(reference.get("filingTo"))
    if not isinstance(name, str):
        return None
    match = SUBMISSIONS_PROFILE.member_pattern.fullmatch(name)
    if (
        match is None
        or match.group("cik") != expected_cik
        or match.groupdict().get("shard") is None
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        or start is None
        or end is None
        or end < start
    ):
        return None
    return name


def _ticker_exchange_state(payload: dict[str, object]) -> str:
    tickers = payload.get("tickers")
    exchanges = payload.get("exchanges")
    if tickers in (None, []) and exchanges in (None, []):
        return "empty"
    if (
        isinstance(tickers, list)
        and isinstance(exchanges, list)
        and len(tickers) == len(exchanges)
        and len(tickers) > 0
        and all(isinstance(value, str) and value.strip() for value in tickers)
        and all(isinstance(value, str) for value in exchanges)
    ):
        return "aligned"
    return "malformed"


def _acceptance_value(value: object) -> tuple[str, str | None]:
    text = _text(value)
    if text is None:
        return ("missing", None) if value in (None, "") else ("invalid", None)
    if _ACCEPTANCE.fullmatch(text) is None:
        return "invalid", None
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return "invalid", None
    return "valid", text


def _date_value(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _printable_placeholder(value: bytes) -> bool:
    return bool(value) and len(value) <= 1024 and not any(
        byte == 0 or (byte < 32 and byte not in {9, 10, 13}) for byte in value
    )


def _merge_set_mappings(
    mappings: Iterable[Mapping[str, Iterable[_MappingValue]]],
) -> dict[str, tuple[_MappingValue, ...]]:
    merged: dict[str, set[_MappingValue]] = {}
    for mapping in mappings:
        for key, values in mapping.items():
            merged.setdefault(key, set()).update(values)
    return {key: tuple(sorted(values)) for key, values in merged.items()}


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count > 0))


def _file_name(snapshot: date, start: date, end: date) -> str:
    return (
        f"census=snapshot-{snapshot.isoformat()}--range-"
        f"{start.isoformat()}--{end.isoformat()}.json"
    )


def _validate_output_root(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise SecSubmissionsPayloadCensusError("Submissions census root is unsafe")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise SecSubmissionsPayloadCensusError("Submissions census root mode differs")
    return root


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
