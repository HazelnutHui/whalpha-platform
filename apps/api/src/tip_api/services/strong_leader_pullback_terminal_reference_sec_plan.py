"""Freeze five official SEC documents needed for terminal-reference bounds."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    read_sec_submissions_source_package,
)
from tip_api.services.strong_leader_pullback_sec_document_plan import (
    _document_url,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-reference-sec-plan/1.0"
REPORT_FILE = "terminal-reference-sec-plan.json"
EXPECTED_REQUEST_COUNT = 5
MAXIMUM_REQUESTS_PER_SECOND = 2
MAXIMUM_RETRIES_PER_REQUEST = 2
MAXIMUM_DOCUMENT_BYTES = 64 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_OUTPUT_NAME_PATTERN = r"^plan=[A-Za-z0-9._-]+$"
MAXIMUM_REPORT_BYTES = 128 * 1024


class TerminalReferenceSecPlanError(RuntimeError):
    """Raised when the bounded official SEC plan cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalReferenceSecPlanItemV1(_FrozenModel):
    request_sequence: int = Field(ge=1, le=EXPECTED_REQUEST_COUNT)
    instrument_id: UUID
    ticker_locator: str = Field(pattern=r"^[A-Z][A-Z0-9.]{0,14}$")
    source_cik: str = Field(pattern=r"^[0-9]{10}$")
    source_party_role: Literal[
        "target_filer", "acquirer_filer", "surviving_parent_filer"
    ]
    accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    form: str = Field(min_length=1)
    filing_date: date
    acceptance_datetime: datetime
    submissions_primary_document: str = Field(min_length=1)
    requested_document: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    missing_source_role: Literal[
        "foreign_continuation_terms",
        "final_cvr_cap",
        "listed_consideration_terms",
        "unlisted_unit_acquisition_value",
    ]
    planned_reference_policy: Literal[
        "forced_last_us_close",
        "zero_to_cash_plus_cvr_cap",
        "zero_to_listed_consideration_max",
        "zero_to_unlisted_consideration_value",
    ]
    request_method: Literal["GET"] = "GET"
    accept_encoding: Literal["identity"] = "identity"
    maximum_response_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    source_content_retrieved: Literal[False] = False
    source_field_adjudicated: Literal[False] = False
    terminal_reference_authorized: Literal[False] = False
    outcome_read: Literal[False] = False

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @property
    def cik(self) -> str:
        """Expose the source filer CIK to the shared custody transport."""

        return self.source_cik

    @model_validator(mode="after")
    def item_reconciles(self) -> "TerminalReferenceSecPlanItemV1":
        expected = _document_url(
            cik=self.source_cik,
            accession=self.accession_number,
            primary_document=self.requested_document,
        )
        if self.request_url != expected:
            raise ValueError("terminal-reference SEC request URL differs")
        return self


class StrongLeaderPullbackTerminalReferenceSecPlanV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-reference-sec-plan/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["planned_not_executed"] = "planned_not_executed"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    planned_at: datetime
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_completed_at: datetime
    selection_rule: Literal[
        "five_gate_changing_official_documents_v1"
    ] = "five_gate_changing_official_documents_v1"
    planned_request_count: Literal[5] = EXPECTED_REQUEST_COUNT
    unique_url_count: Literal[5] = EXPECTED_REQUEST_COUNT
    allowed_hosts: tuple[Literal["www.sec.gov"], ...] = ("www.sec.gov",)
    maximum_requests_per_second: Literal[2] = MAXIMUM_REQUESTS_PER_SECOND
    maximum_retries_per_request: Literal[2] = MAXIMUM_RETRIES_PER_REQUEST
    maximum_document_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    items: tuple[TerminalReferenceSecPlanItemV1, ...] = Field(min_length=5)
    external_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
    document_write_count: Literal[0] = 0
    source_field_adjudication_count: Literal[0] = 0
    outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("planned_at", "submissions_completed_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def plan_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalReferenceSecPlanV1":
        sequences = tuple(item.request_sequence for item in self.items)
        tickers = tuple(item.ticker_locator for item in self.items)
        urls = tuple(item.request_url for item in self.items)
        registered = tuple(
            (
                str(item.instrument_id),
                item.ticker_locator,
                item.source_cik,
                item.accession_number,
                item.requested_document,
                item.missing_source_role,
                item.planned_reference_policy,
            )
            for item in self.items
        )
        expected = tuple(
            (
                item["instrument_id"],
                item["ticker_locator"],
                item["source_cik"],
                item["accession_number"],
                item["requested_document"],
                item["missing_source_role"],
                item["planned_reference_policy"],
            )
            for item in _REQUESTS
        )
        if (
            self.planned_at < self.submissions_completed_at
            or len(self.items) != self.planned_request_count
            or sequences != tuple(range(1, EXPECTED_REQUEST_COUNT + 1))
            or tickers != tuple(sorted(set(tickers)))
            or len(set(urls)) != self.unique_url_count
            or registered != expected
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-reference SEC plan differs")
        return self


_REQUESTS = (
    {
        "instrument_id": "15366b01-e0b4-518a-84b9-4017bac9464c",
        "ticker_locator": "LNW",
        "source_cik": "0000750004",
        "source_party_role": "target_filer",
        "accession_number": "0000950157-25-000856",
        "form": "8-K",
        "filing_date": "2025-10-14",
        "acceptance_datetime": "2025-10-14T11:03:58Z",
        "submissions_primary_document": "form8-k.htm",
        "requested_document": "ex99-1.htm",
        "missing_source_role": "foreign_continuation_terms",
        "planned_reference_policy": "forced_last_us_close",
    },
    {
        "instrument_id": "34deeee9-8d40-52d5-ba8a-eacb9b4004a5",
        "ticker_locator": "MTSR",
        "source_cik": "0002040807",
        "source_party_role": "target_filer",
        "accession_number": "0001193125-25-273435",
        "form": "DEFA14A",
        "filing_date": "2025-11-10",
        "acceptance_datetime": "2025-11-10T09:23:34Z",
        "submissions_primary_document": "d94128ddefa14a.htm",
        "requested_document": "d94128ddefa14a.htm",
        "missing_source_role": "final_cvr_cap",
        "planned_reference_policy": "zero_to_cash_plus_cvr_cap",
    },
    {
        "instrument_id": "2537e45b-62a8-5a96-9b7b-f30ba708645c",
        "ticker_locator": "REVG",
        "source_cik": "0000097216",
        "source_party_role": "acquirer_filer",
        "accession_number": "0001140361-26-003269",
        "form": "8-K",
        "filing_date": "2026-02-02",
        "acceptance_datetime": "2026-02-02T22:17:29Z",
        "submissions_primary_document": "ef20064508_8k.htm",
        "requested_document": "ef20064508_ex99-1.htm",
        "missing_source_role": "listed_consideration_terms",
        "planned_reference_policy": "zero_to_listed_consideration_max",
    },
    {
        "instrument_id": "2fe2a99c-8799-5188-ad89-5e471afddf3c",
        "ticker_locator": "SAND",
        "source_cik": "0001434614",
        "source_party_role": "target_filer",
        "accession_number": "0001279569-25-001118",
        "form": "6-K",
        "filing_date": "2025-10-15",
        "acceptance_datetime": "2025-10-15T16:16:24Z",
        "submissions_primary_document": "sandstormform6k.htm",
        "requested_document": "ex991.htm",
        "missing_source_role": "listed_consideration_terms",
        "planned_reference_policy": "zero_to_listed_consideration_max",
    },
    {
        "instrument_id": "714c4ae2-2938-5196-a02f-198c6b5b8415",
        "ticker_locator": "SKX",
        "source_cik": "0002066659",
        "source_party_role": "surviving_parent_filer",
        "accession_number": "0001193125-26-126281",
        "form": "10-K",
        "filing_date": "2026-03-26",
        "acceptance_datetime": "2026-03-26T16:15:34Z",
        "submissions_primary_document": "ck0002066659-20251231.htm",
        "requested_document": "ck0002066659-20251231.htm",
        "missing_source_role": "unlisted_unit_acquisition_value",
        "planned_reference_policy": "zero_to_unlisted_consideration_value",
    },
)


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalReferenceSecPlanResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalReferenceSecPlanV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_reference_sec_plan(
    *,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    implementation_revision: str,
    planned_at: datetime,
) -> StrongLeaderPullbackTerminalReferenceSecPlanV1:
    """Build a zero-network plan from the retained official submissions index."""

    source = read_sec_submissions_source_package(
        package_path=submissions_package_path,
        approved_custody_root=submissions_custody_root,
    )
    archive = submissions_package_path / ARCHIVE_FILE
    items: list[TerminalReferenceSecPlanItemV1] = []
    try:
        with zipfile.ZipFile(archive) as handle:
            for sequence, registered in enumerate(_REQUESTS, start=1):
                _validate_submission_metadata(
                    zip_handle=handle, registered=registered
                )
                url = _document_url(
                    cik=str(registered["source_cik"]),
                    accession=str(registered["accession_number"]),
                    primary_document=str(registered["requested_document"]),
                )
                items.append(
                    TerminalReferenceSecPlanItemV1.model_validate(
                        {**registered, "request_sequence": sequence, "request_url": url}
                    )
                )
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC submissions read failed"
        ) from exc
    values = {
        "implementation_revision": implementation_revision,
        "planned_at": normalize_utc_datetime(planned_at),
        "submissions_source_fingerprint": source.logical_fingerprint,
        "submissions_archive_sha256": source.archive_sha256,
        "submissions_completed_at": source.completed_at,
        "items": tuple(items),
    }
    provisional = StrongLeaderPullbackTerminalReferenceSecPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalReferenceSecPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def publish_strong_leader_pullback_terminal_reference_sec_plan(
    *,
    submissions_package_path: Path,
    submissions_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    planned_at: datetime,
) -> StrongLeaderPullbackTerminalReferenceSecPlanResult:
    """Publish the zero-request plan atomically into owner-only custody."""

    report = build_strong_leader_pullback_terminal_reference_sec_plan(
        submissions_package_path=submissions_package_path,
        submissions_custody_root=submissions_custody_root,
        implementation_revision=implementation_revision,
        planned_at=planned_at,
    )
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_reference_sec_plan(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise TerminalReferenceSecPlanError(
                "existing terminal-reference SEC plan differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = _json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise TerminalReferenceSecPlanError(
                "terminal-reference SEC plan exceeds byte ceiling"
            )
        _write_exclusive(partial / REPORT_FILE, raw)
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if (
            partial.exists()
            and not partial.is_symlink()
            and partial.parent == target.parent
        ):
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_terminal_reference_sec_plan(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    if reread.report != report:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan reread differs"
        )
    return StrongLeaderPullbackTerminalReferenceSecPlanResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def read_strong_leader_pullback_terminal_reference_sec_plan(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalReferenceSecPlanResult:
    """Reread the immutable five-document plan without network access."""

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalReferenceSecPlanV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan bytes differ"
        )
    return StrongLeaderPullbackTerminalReferenceSecPlanResult(
        output_root=root,
        report=report,
        report_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def _validate_submission_metadata(
    *, zip_handle: zipfile.ZipFile, registered: dict[str, str]
) -> None:
    member = f"CIK{registered['source_cik']}.json"
    try:
        payload = json.loads(zip_handle.read(member))
        recent = payload["filings"]["recent"]
        accessions = recent["accessionNumber"]
        matches = [
            index
            for index, value in enumerate(accessions)
            if value == registered["accession_number"]
        ]
    except (KeyError, TypeError) as exc:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC submissions structure differs"
        ) from exc
    if len(matches) != 1:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC accession metadata differs"
        )
    index = matches[0]
    expected = {
        "form": registered["form"],
        "filingDate": registered["filing_date"],
        "acceptanceDateTime": registered["acceptance_datetime"].replace("Z", ".000Z"),
        "primaryDocument": registered["submissions_primary_document"],
    }
    try:
        differs = any(recent[key][index] != value for key, value in expected.items())
    except (KeyError, IndexError, TypeError) as exc:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC filing columns differ"
        ) from exc
    if differs:
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC filing metadata differs"
        )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan paths must be absolute"
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
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan target is unsafe"
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
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan output is unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan file is unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise TerminalReferenceSecPlanError(
            "terminal-reference SEC plan file metadata differs"
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        + b"\n"
    )
