"""Immutable conservative SEC accession filing-clock ledger."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import stat
import zipfile
from bisect import bisect_right
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Literal

import pyarrow as pa
import pyarrow.parquet as pq
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
from tip_api.providers.sec.submissions_payload_census import (
    SecSubmissionsPayloadCensusV1,
    read_sealed_sec_submissions_payload_census,
)
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    SUBMISSIONS_PROFILE,
    SecSubmissionsSourceManifestV1,
    read_sec_submissions_source_package,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


CONTRACT_VERSION = "sec-filing-clock-ledger/1.0"
PARQUET_FILE = "filing-clocks.parquet"
MANIFEST_FILE = "manifest.json"
AVAILABILITY_METHODOLOGY = (
    "first_xnys_open_strictly_after_conservative_acceptance_v1"
)
MAXIMUM_WORKERS = 16
MAXIMUM_MANIFEST_BYTES = 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}\Z")
_ACCEPTANCE_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z\Z"
)


FILING_CLOCK_ARROW_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("accession_number", pa.string(), nullable=False),
        pa.field("companyfacts_filed_dates", pa.list_(pa.date32()), nullable=False),
        pa.field("submissions_filed_dates", pa.list_(pa.date32()), nullable=False),
        pa.field(
            "acceptance_datetimes_utc",
            pa.list_(pa.timestamp("ms", tz="UTC")),
            nullable=False,
        ),
        pa.field(
            "selected_source_available_at_utc",
            pa.timestamp("ms", tz="UTC"),
            nullable=True,
        ),
        pa.field("signal_eligible_session", pa.date32(), nullable=True),
        pa.field("submission_member_names", pa.list_(pa.string()), nullable=False),
        pa.field("submission_member_ciks", pa.list_(pa.string()), nullable=False),
        pa.field("forms", pa.list_(pa.string()), nullable=False),
        pa.field("submission_row_count", pa.int32(), nullable=False),
        pa.field("admission_status", pa.string(), nullable=False),
        pa.field("availability_resolution", pa.string(), nullable=False),
        pa.field("reason_codes", pa.list_(pa.string()), nullable=False),
        pa.field("instrument_resolution_status", pa.string(), nullable=False),
    ]
)


class SecFilingClockLedgerError(RuntimeError):
    """Raised when the filing-clock package cannot be built or read safely."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecFilingClockLedgerManifestV1(_FrozenModel):
    contract_version: Literal["sec-filing-clock-ledger/1.0"] = CONTRACT_VERSION
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
    submissions_snapshot_date: date
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_payload_census_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_payload_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: str = Field(min_length=1)
    availability_methodology: Literal[
        "first_xnys_open_strictly_after_conservative_acceptance_v1"
    ] = AVAILABILITY_METHODOLOGY
    worker_count: int = Field(ge=1, le=MAXIMUM_WORKERS)
    record_count: int = Field(ge=1)
    admitted_accession_count: int = Field(ge=0)
    quarantined_accession_count: int = Field(ge=0)
    missing_submission_accession_count: int = Field(ge=0)
    exact_acceptance_accession_count: int = Field(ge=0)
    conflicting_acceptance_accession_count: int = Field(ge=0)
    repeated_submission_accession_count: int = Field(ge=0)
    filing_date_exact_match_count: int = Field(ge=0)
    filing_date_disagreement_count: int = Field(ge=0)
    filing_date_unavailable_count: int = Field(ge=0)
    selected_midnight_acceptance_count: int = Field(ge=0)
    form_missing_accession_count: int = Field(ge=0)
    earliest_signal_eligible_session: date | None = None
    latest_signal_eligible_session: date | None = None
    parquet_file: Literal["filing-clocks.parquet"] = PARQUET_FILE
    parquet_bytes: int = Field(ge=1)
    parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    stable_instrument_resolution_count: Literal[0] = 0
    normalized_companyfacts_occurrence_count: Literal[0] = 0
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
    def manifest_reconciles(self) -> "SecFilingClockLedgerManifestV1":
        if self.range_end < self.range_start:
            raise ValueError("filing-clock range is reversed")
        if (
            self.admitted_accession_count + self.quarantined_accession_count
            != self.record_count
        ):
            raise ValueError("filing-clock admission counts differ")
        if self.missing_submission_accession_count != self.quarantined_accession_count:
            raise ValueError("filing-clock quarantine counts differ")
        if (
            self.exact_acceptance_accession_count
            + self.conflicting_acceptance_accession_count
            != self.admitted_accession_count
        ):
            raise ValueError("filing-clock acceptance counts differ")
        if (
            self.filing_date_exact_match_count
            + self.filing_date_disagreement_count
            + self.filing_date_unavailable_count
            != self.admitted_accession_count
        ):
            raise ValueError("filing-clock filed-date counts differ")
        has_sessions = self.admitted_accession_count > 0
        if has_sessions != (self.earliest_signal_eligible_session is not None):
            raise ValueError("filing-clock earliest session presence differs")
        if has_sessions != (self.latest_signal_eligible_session is not None):
            raise ValueError("filing-clock latest session presence differs")
        if (
            has_sessions
            and self.latest_signal_eligible_session
            < self.earliest_signal_eligible_session
        ):
            raise ValueError("filing-clock session range is reversed")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("filing-clock manifest fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class SecFilingClockPackageResult:
    package_path: Path
    manifest: SecFilingClockLedgerManifestV1


@dataclass(frozen=True, slots=True)
class _TargetEvidence:
    row_count: int
    member_names: tuple[str, ...]
    member_ciks: tuple[str, ...]
    filing_dates: tuple[date, ...]
    acceptances: tuple[datetime, ...]
    forms: tuple[str, ...]


@dataclass(slots=True)
class _MutableTargetEvidence:
    row_count: int
    member_names: set[str]
    member_ciks: set[str]
    filing_dates: set[date]
    acceptances: set[datetime]
    forms: set[str]


class _SessionMapper:
    def __init__(
        self,
        *,
        calendar: MarketSessionCalendar,
        boundaries: tuple[datetime, ...],
    ) -> None:
        if not boundaries:
            self.opens: tuple[datetime, ...] = ()
            self.sessions: tuple[date, ...] = ()
            return
        start = min(value.date() for value in boundaries) - timedelta(days=14)
        end = max(value.date() for value in boundaries) + timedelta(days=31)
        sessions = calendar.sessions_in_range(start, end)
        self.sessions = sessions
        self.opens = tuple(calendar.session_open(session) for session in sessions)

    def eligible_session(self, boundary: datetime) -> date:
        normalized = normalize_utc_datetime(boundary)
        if normalized.time() == time(0, 0):
            normalized = datetime.combine(
                normalized.date() + timedelta(days=1), time.min, UTC
            )
        index = bisect_right(self.opens, normalized)
        if index >= len(self.sessions):
            raise SecFilingClockLedgerError(
                "filing-clock calendar does not extend beyond acceptance"
            )
        return self.sessions[index]


def build_sec_filing_clock_package(
    *,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    submissions_census_root: Path,
    companyfacts_package_path: Path,
    companyfacts_custody_root: Path,
    companyfacts_census_root: Path,
    output_package_path: Path,
    range_start: date,
    range_end: date,
    worker_count: int,
    implementation_revision: str,
    built_at: datetime | None = None,
    session_calendar: MarketSessionCalendar | None = None,
) -> SecFilingClockPackageResult:
    """Build one atomic source-normalized filing-clock package."""

    if range_end < range_start:
        raise SecFilingClockLedgerError("filing-clock range is reversed")
    if worker_count < 1 or worker_count > MAXIMUM_WORKERS:
        raise SecFilingClockLedgerError("filing-clock worker count is invalid")
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise SecFilingClockLedgerError("filing-clock revision is invalid")
    target, partial = _validate_output_target(output_package_path)
    companyfacts = read_sec_companyfacts_source_package(
        package_path=companyfacts_package_path,
        approved_custody_root=companyfacts_custody_root,
    )
    submissions = read_sec_submissions_source_package(
        package_path=submissions_package_path,
        approved_custody_root=submissions_custody_root,
    )
    companyfacts_census = read_sealed_sec_companyfacts_payload_census(
        output_root=companyfacts_census_root,
        source_snapshot_date=companyfacts.remote.last_modified.date(),
        range_start=range_start,
        range_end=range_end,
    )
    submissions_census = read_sealed_sec_submissions_payload_census(
        output_root=submissions_census_root,
        source_snapshot_date=submissions.remote.last_modified.date(),
        range_start=range_start,
        range_end=range_end,
    )
    _validate_source_bindings(
        companyfacts=companyfacts,
        companyfacts_census=companyfacts_census,
        submissions=submissions,
        submissions_census=submissions_census,
    )
    targets = extract_sec_companyfacts_in_range_accessions(
        source_package_path=companyfacts_package_path,
        source_custody_root=companyfacts_custody_root,
        range_start=range_start,
        range_end=range_end,
        worker_count=worker_count,
    )
    if len(targets) != companyfacts_census.in_range_unique_accession_count:
        raise SecFilingClockLedgerError("filing-clock target count differs")
    evidence = _extract_target_evidence(
        source_package_path=submissions_package_path,
        source_manifest=submissions,
        targets=frozenset(targets),
        worker_count=worker_count,
    )
    _validate_census_reproduction(targets, evidence, submissions_census)
    calendar = session_calendar or ExchangeCalendar()
    rows = _build_rows(targets=targets, evidence=evidence, calendar=calendar)
    table = pa.Table.from_pylist(rows, schema=FILING_CLOCK_ARROW_SCHEMA)
    content_fingerprint = _table_fingerprint(table)

    os.mkdir(partial, mode=0o700)
    parquet_path = partial / PARQUET_FILE
    pq.write_table(
        table,
        parquet_path,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    parquet_path.chmod(0o400)
    _fsync_file(parquet_path)
    manifest = _build_manifest(
        rows=rows,
        table=table,
        companyfacts=companyfacts,
        companyfacts_census=companyfacts_census,
        companyfacts_source_manifest_sha256=_sha256_file(
            companyfacts_package_path / "package.json"
        ),
        companyfacts_census_sha256=_sha256_file(
            _census_path(
                companyfacts_census_root,
                companyfacts.remote.last_modified.date(),
                range_start,
                range_end,
            )
        ),
        submissions=submissions,
        submissions_census=submissions_census,
        submissions_source_manifest_sha256=_sha256_file(
            submissions_package_path / "package.json"
        ),
        submissions_census_sha256=_sha256_file(
            _census_path(
                submissions_census_root,
                submissions.remote.last_modified.date(),
                range_start,
                range_end,
            )
        ),
        implementation_revision=implementation_revision,
        built_at=normalize_utc_datetime(built_at or datetime.now(UTC)),
        range_start=range_start,
        range_end=range_end,
        worker_count=worker_count,
        calendar=calendar,
        parquet_path=parquet_path,
        content_fingerprint=content_fingerprint,
    )
    _write_exclusive_json(partial / MANIFEST_FILE, manifest.model_dump(mode="json"))
    _fsync_directory(partial)
    os.rename(partial, target)
    _fsync_directory(target.parent)
    return read_sec_filing_clock_package(
        package_path=target, session_calendar=calendar
    )


def read_sec_filing_clock_package(
    *,
    package_path: Path,
    session_calendar: MarketSessionCalendar | None = None,
) -> SecFilingClockPackageResult:
    """Formally reread all package bytes and row-level clock invariants."""

    package = _validate_completed_package(package_path)
    manifest_path = package / MANIFEST_FILE
    parquet_path = package / PARQUET_FILE
    if set(item.name for item in package.iterdir()) != {MANIFEST_FILE, PARQUET_FILE}:
        raise SecFilingClockLedgerError("filing-clock package members differ")
    for path in (manifest_path, parquet_path):
        if path.is_symlink() or not path.is_file():
            raise SecFilingClockLedgerError("filing-clock artifact is unavailable")
        metadata = path.stat()
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o400:
            raise SecFilingClockLedgerError("filing-clock artifact mode differs")
    if manifest_path.stat().st_size > MAXIMUM_MANIFEST_BYTES:
        raise SecFilingClockLedgerError("filing-clock manifest exceeds byte ceiling")
    try:
        manifest = SecFilingClockLedgerManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
    except Exception as exc:
        raise SecFilingClockLedgerError("filing-clock manifest is invalid") from exc
    if (
        parquet_path.stat().st_size != manifest.parquet_bytes
        or _sha256_file(parquet_path) != manifest.parquet_sha256
    ):
        raise SecFilingClockLedgerError("filing-clock Parquet identity differs")
    try:
        table = pq.ParquetFile(parquet_path).read()
    except Exception as exc:
        raise SecFilingClockLedgerError("filing-clock Parquet cannot be read") from exc
    if table.schema != FILING_CLOCK_ARROW_SCHEMA:
        raise SecFilingClockLedgerError("filing-clock Arrow schema differs")
    calendar = session_calendar or ExchangeCalendar()
    if calendar.calendar_id != manifest.calendar_id:
        raise SecFilingClockLedgerError("filing-clock calendar identity differs")
    if calendar.calendar_version != manifest.calendar_version:
        raise SecFilingClockLedgerError("filing-clock calendar version differs")
    _validate_table(table=table, manifest=manifest, calendar=calendar)
    return SecFilingClockPackageResult(package_path=package, manifest=manifest)


def _extract_target_evidence(
    *,
    source_package_path: Path,
    source_manifest: SecSubmissionsSourceManifestV1,
    targets: frozenset[str],
    worker_count: int,
) -> dict[str, _TargetEvidence]:
    archive_path = source_package_path / ARCHIVE_FILE
    with zipfile.ZipFile(archive_path) as archive:
        names = tuple(sorted(item.filename for item in archive.infolist()))
    if (
        len(names) != source_manifest.member_count
        or _fingerprint(names) != source_manifest.member_name_fingerprint
    ):
        raise SecFilingClockLedgerError("filing-clock source member binding differs")
    partitions = tuple(
        names[index::worker_count]
        for index in range(worker_count)
        if names[index::worker_count]
    )
    arguments = tuple((str(archive_path), part, targets) for part in partitions)
    if worker_count == 1:
        partials = tuple(_extract_target_batch(argument) for argument in arguments)
    else:
        with ProcessPoolExecutor(
            max_workers=worker_count,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            partials = tuple(executor.map(_extract_target_batch, arguments))
    merged: dict[str, _MutableTargetEvidence] = {}
    for partial in partials:
        for accession, item in partial.items():
            value = merged.setdefault(
                accession,
                _MutableTargetEvidence(0, set(), set(), set(), set(), set()),
            )
            value.row_count += item.row_count
            value.member_names.update(item.member_names)
            value.member_ciks.update(item.member_ciks)
            value.filing_dates.update(item.filing_dates)
            value.acceptances.update(item.acceptances)
            value.forms.update(item.forms)
    return {
        accession: _TargetEvidence(
            row_count=value.row_count,
            member_names=tuple(sorted(value.member_names)),
            member_ciks=tuple(sorted(value.member_ciks)),
            filing_dates=tuple(sorted(value.filing_dates)),
            acceptances=tuple(sorted(value.acceptances)),
            forms=tuple(sorted(value.forms)),
        )
        for accession, value in sorted(merged.items())
    }


def _extract_target_batch(
    argument: tuple[str, tuple[str, ...], frozenset[str]],
) -> dict[str, _TargetEvidence]:
    archive_name, names, targets = argument
    values: dict[str, _MutableTargetEvidence] = {}
    with zipfile.ZipFile(archive_name) as archive:
        for name in names:
            if name in SUBMISSIONS_PROFILE.allowed_non_cik_members:
                continue
            match = SUBMISSIONS_PROFILE.member_pattern.fullmatch(name)
            if match is None:
                raise SecFilingClockLedgerError(
                    "filing-clock source member name differs"
                )
            try:
                payload = json.loads(archive.read(name))
            except Exception as exc:
                raise SecFilingClockLedgerError(
                    "filing-clock source member cannot be read"
                ) from exc
            if match.groupdict().get("shard") is None:
                if not isinstance(payload, dict):
                    raise SecFilingClockLedgerError(
                        "filing-clock root payload is invalid"
                    )
                filings = payload.get("filings")
                if not isinstance(filings, dict):
                    raise SecFilingClockLedgerError(
                        "filing-clock root filings are invalid"
                    )
                columns = filings.get("recent")
            else:
                columns = payload
            _validate_columns(columns)
            assert isinstance(columns, dict)
            if not columns:
                continue
            member_cik = match.group("cik")
            for index, raw_accession in enumerate(columns["accessionNumber"]):
                if raw_accession not in targets:
                    continue
                if (
                    not isinstance(raw_accession, str)
                    or _ACCESSION_PATTERN.fullmatch(raw_accession) is None
                ):
                    raise SecFilingClockLedgerError(
                        "filing-clock target accession is invalid"
                    )
                filed = _parse_date(columns["filingDate"][index])
                accepted = _parse_acceptance(columns["acceptanceDateTime"][index])
                form_value = columns["form"][index]
                form = form_value.strip() if isinstance(form_value, str) else ""
                item = values.setdefault(
                    raw_accession,
                    _MutableTargetEvidence(0, set(), set(), set(), set(), set()),
                )
                item.row_count += 1
                item.member_names.add(name)
                item.member_ciks.add(member_cik)
                item.filing_dates.add(filed)
                item.acceptances.add(accepted)
                if form:
                    item.forms.add(form)
    return {
        accession: _TargetEvidence(
            row_count=value.row_count,
            member_names=tuple(sorted(value.member_names)),
            member_ciks=tuple(sorted(value.member_ciks)),
            filing_dates=tuple(sorted(value.filing_dates)),
            acceptances=tuple(sorted(value.acceptances)),
            forms=tuple(sorted(value.forms)),
        )
        for accession, value in values.items()
    }


def _validate_columns(columns: object) -> None:
    if not isinstance(columns, dict):
        raise SecFilingClockLedgerError("filing-clock columns are invalid")
    if not columns:
        return
    required = {"accessionNumber", "filingDate", "acceptanceDateTime", "form"}
    if not required.issubset(columns):
        raise SecFilingClockLedgerError("filing-clock columns are incomplete")
    if any(not isinstance(value, list) for value in columns.values()):
        raise SecFilingClockLedgerError("filing-clock column is not an array")
    if len({len(value) for value in columns.values()}) != 1:
        raise SecFilingClockLedgerError("filing-clock columns are misaligned")


def _validate_source_bindings(
    *,
    companyfacts: SecCompanyfactsSourceManifestV1,
    companyfacts_census: SecCompanyfactsPayloadCensusV1,
    submissions: SecSubmissionsSourceManifestV1,
    submissions_census: SecSubmissionsPayloadCensusV1,
) -> None:
    if (
        companyfacts_census.source_snapshot_date
        != companyfacts.remote.last_modified.date()
        or companyfacts_census.source_logical_fingerprint
        != companyfacts.logical_fingerprint
        or companyfacts_census.source_archive_sha256 != companyfacts.archive_sha256
    ):
        raise SecFilingClockLedgerError("Company Facts source binding differs")
    if (
        submissions_census.submissions_snapshot_date
        != submissions.remote.last_modified.date()
        or submissions_census.submissions_source_fingerprint
        != submissions.logical_fingerprint
        or submissions_census.submissions_archive_sha256
        != submissions.archive_sha256
        or submissions_census.companyfacts_source_fingerprint
        != companyfacts.logical_fingerprint
        or submissions_census.companyfacts_payload_census_fingerprint
        != companyfacts_census.logical_fingerprint
    ):
        raise SecFilingClockLedgerError("Submissions source binding differs")


def _validate_census_reproduction(
    targets: dict[str, tuple[date, ...]],
    evidence: dict[str, _TargetEvidence],
    census: SecSubmissionsPayloadCensusV1,
) -> None:
    matched = set(evidence)
    missing = set(targets) - matched
    exact_dates = {
        accession
        for accession, item in evidence.items()
        if item.filing_dates == targets[accession]
    }
    unavailable_dates = {
        accession for accession, item in evidence.items() if not item.filing_dates
    }
    observed = {
        "companyfacts_target_accession_count": len(targets),
        "target_accession_matched_count": len(matched),
        "target_accession_missing_count": len(missing),
        "target_duplicate_accession_count": sum(
            item.row_count > 1 for item in evidence.values()
        ),
        "target_with_valid_acceptance_count": sum(
            bool(item.acceptances) for item in evidence.values()
        ),
        "target_without_valid_acceptance_count": sum(
            not item.acceptances for item in evidence.values()
        ),
        "target_conflicting_acceptance_count": sum(
            len(item.acceptances) > 1 for item in evidence.values()
        ),
        "target_filing_date_exact_match_count": len(exact_dates),
        "target_filing_date_disagreement_count": len(
            matched - exact_dates - unavailable_dates
        ),
        "target_filing_date_unavailable_count": len(unavailable_dates),
    }
    if any(getattr(census, key) != value for key, value in observed.items()):
        raise SecFilingClockLedgerError(
            "filing-clock evidence does not reproduce source census"
        )


def _build_rows(
    *,
    targets: dict[str, tuple[date, ...]],
    evidence: dict[str, _TargetEvidence],
    calendar: MarketSessionCalendar,
) -> list[dict[str, object]]:
    boundaries = tuple(
        max(item.acceptances) for item in evidence.values() if item.acceptances
    )
    mapper = _SessionMapper(calendar=calendar, boundaries=boundaries)
    rows: list[dict[str, object]] = []
    for accession, companyfacts_dates in sorted(targets.items()):
        item = evidence.get(accession)
        if item is None:
            rows.append(
                {
                    "contract_version": CONTRACT_VERSION,
                    "accession_number": accession,
                    "companyfacts_filed_dates": list(companyfacts_dates),
                    "submissions_filed_dates": [],
                    "acceptance_datetimes_utc": [],
                    "selected_source_available_at_utc": None,
                    "signal_eligible_session": None,
                    "submission_member_names": [],
                    "submission_member_ciks": [],
                    "forms": [],
                    "submission_row_count": 0,
                    "admission_status": "quarantined",
                    "availability_resolution": "missing_submission_accession",
                    "reason_codes": ["missing_submission_accession"],
                    "instrument_resolution_status": "unresolved",
                }
            )
            continue
        if not item.acceptances:
            raise SecFilingClockLedgerError(
                "matched filing-clock accession lacks acceptance"
            )
        selected = max(item.acceptances)
        exact_date = item.filing_dates == companyfacts_dates
        reasons = {
            (
                "acceptance_conflict_conservative_latest"
                if len(item.acceptances) > 1
                else "acceptance_exact"
            ),
            "filing_date_exact" if exact_date else "filing_date_disagreement",
        }
        if item.row_count > 1:
            reasons.add("submission_accession_repeated")
        if selected.time() == time(0, 0):
            reasons.add("acceptance_midnight_time_quality_warning")
        if not item.forms:
            reasons.add("form_missing")
        rows.append(
            {
                "contract_version": CONTRACT_VERSION,
                "accession_number": accession,
                "companyfacts_filed_dates": list(companyfacts_dates),
                "submissions_filed_dates": list(item.filing_dates),
                "acceptance_datetimes_utc": list(item.acceptances),
                "selected_source_available_at_utc": selected,
                "signal_eligible_session": mapper.eligible_session(selected),
                "submission_member_names": list(item.member_names),
                "submission_member_ciks": list(item.member_ciks),
                "forms": list(item.forms),
                "submission_row_count": item.row_count,
                "admission_status": "admitted",
                "availability_resolution": (
                    "conservative_latest_conflict"
                    if len(item.acceptances) > 1
                    else "exact"
                ),
                "reason_codes": sorted(reasons),
                "instrument_resolution_status": "unresolved",
            }
        )
    return rows


def _build_manifest(
    *,
    rows: list[dict[str, object]],
    table: pa.Table,
    companyfacts: SecCompanyfactsSourceManifestV1,
    companyfacts_census: SecCompanyfactsPayloadCensusV1,
    companyfacts_source_manifest_sha256: str,
    companyfacts_census_sha256: str,
    submissions: SecSubmissionsSourceManifestV1,
    submissions_census: SecSubmissionsPayloadCensusV1,
    submissions_source_manifest_sha256: str,
    submissions_census_sha256: str,
    implementation_revision: str,
    built_at: datetime,
    range_start: date,
    range_end: date,
    worker_count: int,
    calendar: MarketSessionCalendar,
    parquet_path: Path,
    content_fingerprint: str,
) -> SecFilingClockLedgerManifestV1:
    sessions = [
        row["signal_eligible_session"]
        for row in rows
        if row["signal_eligible_session"] is not None
    ]
    admitted = [row for row in rows if row["admission_status"] == "admitted"]
    values = {
        "contract_version": CONTRACT_VERSION,
        "completion_status": "completed",
        "provider_id": "sec_edgar",
        "implementation_revision": implementation_revision,
        "built_at": built_at,
        "range_start": range_start,
        "range_end": range_end,
        "companyfacts_snapshot_date": companyfacts.remote.last_modified.date(),
        "companyfacts_source_fingerprint": companyfacts.logical_fingerprint,
        "companyfacts_source_manifest_sha256": companyfacts_source_manifest_sha256,
        "companyfacts_payload_census_fingerprint": companyfacts_census.logical_fingerprint,
        "companyfacts_payload_census_sha256": companyfacts_census_sha256,
        "submissions_snapshot_date": submissions.remote.last_modified.date(),
        "submissions_source_fingerprint": submissions.logical_fingerprint,
        "submissions_source_manifest_sha256": submissions_source_manifest_sha256,
        "submissions_payload_census_fingerprint": submissions_census.logical_fingerprint,
        "submissions_payload_census_sha256": submissions_census_sha256,
        "calendar_id": calendar.calendar_id,
        "calendar_version": calendar.calendar_version,
        "availability_methodology": AVAILABILITY_METHODOLOGY,
        "worker_count": worker_count,
        "record_count": table.num_rows,
        "admitted_accession_count": len(admitted),
        "quarantined_accession_count": sum(
            row["admission_status"] == "quarantined" for row in rows
        ),
        "missing_submission_accession_count": sum(
            row["availability_resolution"] == "missing_submission_accession"
            for row in rows
        ),
        "exact_acceptance_accession_count": sum(
            row["availability_resolution"] == "exact" for row in rows
        ),
        "conflicting_acceptance_accession_count": sum(
            row["availability_resolution"] == "conservative_latest_conflict"
            for row in rows
        ),
        "repeated_submission_accession_count": sum(
            row["submission_row_count"] > 1 for row in rows
        ),
        "filing_date_exact_match_count": sum(
            "filing_date_exact" in row["reason_codes"] for row in admitted
        ),
        "filing_date_disagreement_count": sum(
            "filing_date_disagreement" in row["reason_codes"] for row in admitted
        ),
        "filing_date_unavailable_count": sum(
            not row["submissions_filed_dates"] for row in admitted
        ),
        "selected_midnight_acceptance_count": sum(
            "acceptance_midnight_time_quality_warning" in row["reason_codes"]
            for row in admitted
        ),
        "form_missing_accession_count": sum(
            "form_missing" in row["reason_codes"] for row in admitted
        ),
        "earliest_signal_eligible_session": min(sessions) if sessions else None,
        "latest_signal_eligible_session": max(sessions) if sessions else None,
        "parquet_file": PARQUET_FILE,
        "parquet_bytes": parquet_path.stat().st_size,
        "parquet_sha256": _sha256_file(parquet_path),
        "content_fingerprint": content_fingerprint,
        "stable_instrument_resolution_count": 0,
        "normalized_companyfacts_occurrence_count": 0,
        "canonical_data_write_count": 0,
        "analytics_execution_count": 0,
        "publication_count": 0,
        "deployment_count": 0,
        "scheduler_change_count": 0,
    }
    return SecFilingClockLedgerManifestV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _validate_table(
    *,
    table: pa.Table,
    manifest: SecFilingClockLedgerManifestV1,
    calendar: MarketSessionCalendar,
) -> None:
    if table.num_rows != manifest.record_count:
        raise SecFilingClockLedgerError("filing-clock row count differs")
    rows = table.to_pylist()
    accessions = tuple(row["accession_number"] for row in rows)
    if accessions != tuple(sorted(accessions)) or len(set(accessions)) != len(
        accessions
    ):
        raise SecFilingClockLedgerError("filing-clock business keys differ")
    selected_boundaries = tuple(
        row["selected_source_available_at_utc"]
        for row in rows
        if row["selected_source_available_at_utc"] is not None
    )
    mapper = _SessionMapper(calendar=calendar, boundaries=selected_boundaries)
    for row in rows:
        if row["contract_version"] != CONTRACT_VERSION:
            raise SecFilingClockLedgerError("filing-clock row version differs")
        if _ACCESSION_PATTERN.fullmatch(row["accession_number"]) is None:
            raise SecFilingClockLedgerError("filing-clock accession differs")
        for key in (
            "companyfacts_filed_dates",
            "submissions_filed_dates",
            "acceptance_datetimes_utc",
            "submission_member_names",
            "submission_member_ciks",
            "forms",
            "reason_codes",
        ):
            values = row[key]
            if values != sorted(set(values)):
                raise SecFilingClockLedgerError(
                    "filing-clock ordered evidence differs"
                )
        if row["instrument_resolution_status"] != "unresolved":
            raise SecFilingClockLedgerError(
                "filing-clock instrument resolution differs"
            )
        if row["admission_status"] == "quarantined":
            if any(
                (
                    row["submission_row_count"],
                    row["submissions_filed_dates"],
                    row["acceptance_datetimes_utc"],
                    row["submission_member_names"],
                    row["submission_member_ciks"],
                    row["forms"],
                    row["selected_source_available_at_utc"],
                    row["signal_eligible_session"],
                )
            ):
                raise SecFilingClockLedgerError(
                    "filing-clock quarantine contains invented evidence"
                )
            if row["reason_codes"] != ["missing_submission_accession"]:
                raise SecFilingClockLedgerError(
                    "filing-clock quarantine reason differs"
                )
            if row["availability_resolution"] != "missing_submission_accession":
                raise SecFilingClockLedgerError(
                    "filing-clock quarantine resolution differs"
                )
            continue
        if row["admission_status"] != "admitted":
            raise SecFilingClockLedgerError("filing-clock admission state differs")
        if (
            row["submission_row_count"] < 1
            or not row["submissions_filed_dates"]
            or not row["companyfacts_filed_dates"]
            or not row["submission_member_names"]
            or not row["submission_member_ciks"]
        ):
            raise SecFilingClockLedgerError(
                "filing-clock admitted evidence is incomplete"
            )
        if any(
            re.fullmatch(r"[0-9]{10}", value) is None
            for value in row["submission_member_ciks"]
        ):
            raise SecFilingClockLedgerError("filing-clock member CIK differs")
        acceptances = row["acceptance_datetimes_utc"]
        selected = row["selected_source_available_at_utc"]
        if not acceptances or selected != max(acceptances):
            raise SecFilingClockLedgerError(
                "filing-clock conservative acceptance differs"
            )
        expected_resolution = (
            "conservative_latest_conflict" if len(acceptances) > 1 else "exact"
        )
        if row["availability_resolution"] != expected_resolution:
            raise SecFilingClockLedgerError(
                "filing-clock acceptance resolution differs"
            )
        if row["signal_eligible_session"] != mapper.eligible_session(selected):
            raise SecFilingClockLedgerError(
                "filing-clock eligible session differs"
            )
        expected_reasons = {
            (
                "acceptance_conflict_conservative_latest"
                if len(acceptances) > 1
                else "acceptance_exact"
            ),
            (
                "filing_date_exact"
                if row["submissions_filed_dates"]
                == row["companyfacts_filed_dates"]
                else "filing_date_disagreement"
            ),
        }
        if row["submission_row_count"] > 1:
            expected_reasons.add("submission_accession_repeated")
        if selected.time() == time(0, 0):
            expected_reasons.add("acceptance_midnight_time_quality_warning")
        if not row["forms"]:
            expected_reasons.add("form_missing")
        if row["reason_codes"] != sorted(expected_reasons):
            raise SecFilingClockLedgerError("filing-clock reason codes differ")
    if _table_fingerprint(table) != manifest.content_fingerprint:
        raise SecFilingClockLedgerError("filing-clock content fingerprint differs")
    expected = _manifest_counts_from_rows(rows)
    if any(getattr(manifest, key) != value for key, value in expected.items()):
        raise SecFilingClockLedgerError("filing-clock manifest counts differ")


def _manifest_counts_from_rows(rows: list[dict[str, object]]) -> dict[str, int | date | None]:
    admitted = [row for row in rows if row["admission_status"] == "admitted"]
    sessions = [row["signal_eligible_session"] for row in admitted]
    return {
        "admitted_accession_count": len(admitted),
        "quarantined_accession_count": len(rows) - len(admitted),
        "missing_submission_accession_count": sum(
            row["availability_resolution"] == "missing_submission_accession"
            for row in rows
        ),
        "exact_acceptance_accession_count": sum(
            row["availability_resolution"] == "exact" for row in admitted
        ),
        "conflicting_acceptance_accession_count": sum(
            row["availability_resolution"] == "conservative_latest_conflict"
            for row in admitted
        ),
        "repeated_submission_accession_count": sum(
            row["submission_row_count"] > 1 for row in rows
        ),
        "filing_date_exact_match_count": sum(
            "filing_date_exact" in row["reason_codes"] for row in admitted
        ),
        "filing_date_disagreement_count": sum(
            "filing_date_disagreement" in row["reason_codes"] for row in admitted
        ),
        "filing_date_unavailable_count": sum(
            not row["submissions_filed_dates"] for row in admitted
        ),
        "selected_midnight_acceptance_count": sum(
            "acceptance_midnight_time_quality_warning" in row["reason_codes"]
            for row in admitted
        ),
        "form_missing_accession_count": sum(
            "form_missing" in row["reason_codes"] for row in admitted
        ),
        "earliest_signal_eligible_session": min(sessions) if sessions else None,
        "latest_signal_eligible_session": max(sessions) if sessions else None,
    }


def _parse_date(value: object) -> date:
    if not isinstance(value, str):
        raise SecFilingClockLedgerError("filing-clock filing date is invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SecFilingClockLedgerError(
            "filing-clock filing date is invalid"
        ) from exc


def _parse_acceptance(value: object) -> datetime:
    if not isinstance(value, str) or _ACCEPTANCE_PATTERN.fullmatch(value) is None:
        raise SecFilingClockLedgerError("filing-clock acceptance is invalid")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=UTC
        )
    except ValueError as exc:
        raise SecFilingClockLedgerError("filing-clock acceptance is invalid") from exc


def _census_path(root: Path, snapshot: date, start: date, end: date) -> Path:
    return root / (
        f"census=snapshot-{snapshot.isoformat()}--range-"
        f"{start.isoformat()}--{end.isoformat()}.json"
    )


def _validate_output_target(path: Path) -> tuple[Path, Path]:
    target = path.absolute()
    parent = _validate_owner_directory(target.parent)
    if target.parent != parent or not re.fullmatch(r"build=[A-Za-z0-9._-]+", target.name):
        raise SecFilingClockLedgerError("filing-clock output target is invalid")
    partial = parent / f".{target.name}.partial"
    if os.path.lexists(target) or os.path.lexists(partial):
        raise SecFilingClockLedgerError("filing-clock output target already exists")
    return target, partial


def _validate_completed_package(path: Path) -> Path:
    package = path.absolute()
    if (
        package.is_symlink()
        or not package.is_dir()
        or package.resolve(strict=True) != package
    ):
        raise SecFilingClockLedgerError("filing-clock package is unsafe")
    metadata = package.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise SecFilingClockLedgerError("filing-clock package mode differs")
    return package


def _validate_owner_directory(path: Path) -> Path:
    root = path.absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise SecFilingClockLedgerError("filing-clock parent is unsafe")
    metadata = root.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise SecFilingClockLedgerError("filing-clock parent mode differs")
    return root


def _write_exclusive_json(path: Path, value: object) -> None:
    raw = _json_bytes(value) + b"\n"
    if len(raw) > MAXIMUM_MANIFEST_BYTES:
        raise SecFilingClockLedgerError("filing-clock manifest exceeds byte ceiling")
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


def _table_fingerprint(table: pa.Table) -> str:
    digest = hashlib.sha256()
    for row in table.to_pylist():
        digest.update(_json_bytes(row))
        digest.update(b"\n")
    return digest.hexdigest()


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


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()
