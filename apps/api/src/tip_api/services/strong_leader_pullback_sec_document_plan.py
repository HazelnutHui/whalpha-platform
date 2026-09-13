"""Freeze the bounded SEC primary-document acquisition plan."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_lifecycle_pilot import (
    read_strong_leader_pullback_sec_lifecycle_pilot,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-document-plan/1.0"
PLAN_FILE = "plan.json"
EXPECTED_REQUEST_COUNT = 219
BATCH_SIZE = 10
EXPECTED_BATCH_COUNT = 22
MAXIMUM_REQUESTS_PER_SECOND = 2
MAXIMUM_RETRIES_PER_REQUEST = 2
MAXIMUM_DOCUMENT_BYTES = 64 * 1024 * 1024
MAXIMUM_PLAN_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_BUILD_NAME_PATTERN = r"^build=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackSecDocumentPlanError(RuntimeError):
    """Raised when the SEC primary-document plan cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecPrimaryDocumentPlanItemV1(_FrozenModel):
    request_sequence: int = Field(ge=1, le=EXPECTED_REQUEST_COUNT)
    batch_number: int = Field(ge=1, le=EXPECTED_BATCH_COUNT)
    batch_position: int = Field(ge=1, le=BATCH_SIZE)
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=_ACCESSION_PATTERN)
    form: str
    filing_date: date
    acceptance_datetime: datetime
    primary_document: str
    request_url: str
    locator_categories: tuple[str, ...]
    structured_items: tuple[str, ...]
    relation_to_last_observation: Literal[
        "on_last_observation",
        "after_last_before_provider_delist_candidate",
        "on_provider_delist_candidate",
        "after_provider_delist_candidate",
    ]
    request_method: Literal["GET"] = "GET"
    accept_encoding: Literal["identity"] = "identity"
    maximum_response_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    credential_material_retained: Literal[False] = False
    document_content_retrieved: Literal[False] = False
    listed_security_fact_authority: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False

    @field_validator("form", "primary_document", "request_url")
    @classmethod
    def text_is_normalized(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("SEC document plan text is invalid")
        return value

    @field_validator("locator_categories", "structured_items", mode="before")
    @classmethod
    def values_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("SEC document plan values are not ordered and unique")
        return values

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def item_reconciles(self) -> "SecPrimaryDocumentPlanItemV1":
        expected_batch = (self.request_sequence - 1) // BATCH_SIZE + 1
        expected_position = (self.request_sequence - 1) % BATCH_SIZE + 1
        if self.batch_number != expected_batch or self.batch_position != expected_position:
            raise ValueError("SEC document plan batch position differs")
        if self.request_url != _document_url(
            cik=self.cik,
            accession=self.accession_number,
            primary_document=self.primary_document,
        ):
            raise ValueError("SEC document plan URL differs")
        return self


class StrongLeaderPullbackSecDocumentPlanV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-document-plan/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["planned_not_executed"] = "planned_not_executed"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    planned_at: datetime
    provider_id: Literal["sec_edgar"] = "sec_edgar"
    source_pilot_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_pilot_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_pilot_evaluated_at: datetime
    selection_rule: Literal[
        "all_candidates_on_or_after_last_canonical_observation_v1"
    ] = "all_candidates_on_or_after_last_canonical_observation_v1"
    allowed_hosts: tuple[Literal["www.sec.gov"], ...] = ("www.sec.gov",)
    request_method: Literal["GET"] = "GET"
    accept_encoding: Literal["identity"] = "identity"
    batch_size: Literal[10] = BATCH_SIZE
    batch_count: Literal[22] = EXPECTED_BATCH_COUNT
    planned_request_count: Literal[219] = EXPECTED_REQUEST_COUNT
    unique_url_count: Literal[219] = EXPECTED_REQUEST_COUNT
    maximum_requests_per_second: Literal[2] = MAXIMUM_REQUESTS_PER_SECOND
    maximum_retries_per_request: Literal[2] = MAXIMUM_RETRIES_PER_REQUEST
    maximum_document_bytes: Literal[67108864] = MAXIMUM_DOCUMENT_BYTES
    form_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]
    relation_counts: tuple[tuple[str, int], ...]
    items: tuple[SecPrimaryDocumentPlanItemV1, ...]
    external_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
    document_write_count: Literal[0] = 0
    listed_security_identity_assignment_count: Literal[0] = 0
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

    @field_validator("planned_at", "source_pilot_evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def plan_reconciles(self) -> "StrongLeaderPullbackSecDocumentPlanV1":
        sequences = tuple(item.request_sequence for item in self.items)
        urls = tuple(item.request_url for item in self.items)
        if (
            len(self.items) != self.planned_request_count
            or sequences != tuple(range(1, self.planned_request_count + 1))
            or len(set(urls)) != self.unique_url_count
        ):
            raise ValueError("SEC document plan population differs")
        batch_counts = Counter(item.batch_number for item in self.items)
        expected_batches = {
            number: (
                BATCH_SIZE
                if number < EXPECTED_BATCH_COUNT
                else EXPECTED_REQUEST_COUNT - BATCH_SIZE * (EXPECTED_BATCH_COUNT - 1)
            )
            for number in range(1, EXPECTED_BATCH_COUNT + 1)
        }
        if dict(batch_counts) != expected_batches:
            raise ValueError("SEC document plan batch counts differ")
        forms = Counter(item.form for item in self.items)
        categories = Counter(
            category for item in self.items for category in item.locator_categories
        )
        relations = Counter(item.relation_to_last_observation for item in self.items)
        if (
            self.form_counts != _ordered(forms)
            or self.category_counts != _ordered(categories)
            or self.relation_counts != _ordered(relations)
        ):
            raise ValueError("SEC document plan aggregates differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC document plan fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecDocumentPlanResult:
    output_root: Path
    plan: StrongLeaderPullbackSecDocumentPlanV1
    plan_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_sec_document_plan(
    *,
    pilot_root: Path,
    pilot_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    planned_at: datetime,
) -> StrongLeaderPullbackSecDocumentPlanResult:
    """Build one immutable no-request plan from the completed SEC pilot."""

    with _network_prohibited():
        pilot = read_strong_leader_pullback_sec_lifecycle_pilot(
            output_root=pilot_root,
            output_custody_root=pilot_custody_root,
        )
        report = pilot.report
        if (
            report.completion_status
            != "metadata_locator_complete_terminal_evidence_incomplete"
            or report.document_request_count
            or report.terminal_outcome_count
            or report.research_admission_count
        ):
            raise StrongLeaderPullbackSecDocumentPlanError(
                "SEC lifecycle source pilot authority differs"
            )
        plan = _compose_plan(
            pilot=pilot,
            implementation_revision=implementation_revision,
            planned_at=planned_at,
        )
        return _write_plan(
            output_root=output_root,
            output_custody_root=output_custody_root,
            plan=plan,
        )


def read_strong_leader_pullback_sec_document_plan(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecDocumentPlanResult:
    """Formally reread one completed SEC document plan."""

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {PLAN_FILE}:
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan package members differ"
        )
    path = root / PLAN_FILE
    _require_regular_file(path, 0o400, MAXIMUM_PLAN_BYTES)
    raw = path.read_bytes()
    try:
        plan = StrongLeaderPullbackSecDocumentPlanV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan is invalid"
        ) from exc
    if raw != _json_bytes(plan.model_dump(mode="json")):
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan bytes are not canonical"
        )
    return StrongLeaderPullbackSecDocumentPlanResult(
        output_root=root,
        plan=plan,
        plan_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def _compose_plan(
    *, pilot: object, implementation_revision: str, planned_at: datetime
) -> StrongLeaderPullbackSecDocumentPlanV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan revision is invalid"
        )
    selected = tuple(
        sorted(
            (
                (case, filing)
                for case in pilot.report.cases
                for filing in case.candidate_filings
                if filing.relation_to_last_observation != "before_last_observation"
            ),
            key=lambda item: (
                str(item[0].instrument_id),
                item[1].filing_date,
                item[1].acceptance_datetime,
                item[1].accession_number,
            ),
        )
    )
    if len(selected) != EXPECTED_REQUEST_COUNT:
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document transition population differs"
        )
    items = tuple(
        SecPrimaryDocumentPlanItemV1(
            request_sequence=index,
            batch_number=(index - 1) // BATCH_SIZE + 1,
            batch_position=(index - 1) % BATCH_SIZE + 1,
            instrument_id=case.instrument_id,
            cik=case.cik,
            accession_number=filing.accession_number,
            form=filing.form,
            filing_date=filing.filing_date,
            acceptance_datetime=filing.acceptance_datetime,
            primary_document=filing.primary_document,
            request_url=_document_url(
                cik=case.cik,
                accession=filing.accession_number,
                primary_document=filing.primary_document,
            ),
            locator_categories=filing.locator_categories,
            structured_items=filing.items,
            relation_to_last_observation=filing.relation_to_last_observation,
        )
        for index, (case, filing) in enumerate(selected, start=1)
    )
    if len({item.accession_number for item in items}) != len(items):
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan accessions are duplicated"
        )
    forms = Counter(item.form for item in items)
    categories = Counter(
        category for item in items for category in item.locator_categories
    )
    relations = Counter(item.relation_to_last_observation for item in items)
    values = {
        "implementation_revision": implementation_revision,
        "planned_at": normalize_utc_datetime(planned_at),
        "source_pilot_sha256": pilot.report_sha256,
        "source_pilot_logical_fingerprint": pilot.report.logical_fingerprint,
        "source_pilot_evaluated_at": pilot.report.evaluated_at,
        "form_counts": _ordered(forms),
        "category_counts": _ordered(categories),
        "relation_counts": _ordered(relations),
        "items": items,
    }
    provisional = StrongLeaderPullbackSecDocumentPlanV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecDocumentPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_url(*, cik: str, accession: str, primary_document: str) -> str:
    if not re.fullmatch(r"[0-9]{10}", cik):
        raise ValueError("SEC document plan CIK is invalid")
    if re.fullmatch(_ACCESSION_PATTERN, accession) is None:
        raise ValueError("SEC document plan accession is invalid")
    path = PurePosixPath(primary_document)
    if (
        not primary_document
        or path.is_absolute()
        or "\\" in primary_document
        or path.as_posix() != primary_document
        or any(part in {".", ".."} for part in path.parts)
        or any(ord(char) < 32 or ord(char) == 127 for char in primary_document)
    ):
        raise ValueError("SEC document plan primary-document path is invalid")
    url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik)}/{accession.replace('-', '')}/{primary_document}"
    )
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.sec.gov"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("SEC document plan URL is invalid")
    return url


def _write_plan(
    *, output_root: Path, output_custody_root: Path,
    plan: StrongLeaderPullbackSecDocumentPlanV1,
) -> StrongLeaderPullbackSecDocumentPlanResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_document_plan(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.plan != plan:
            raise StrongLeaderPullbackSecDocumentPlanError(
                "existing SEC document plan differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(partial / PLAN_FILE, _json_bytes(plan.model_dump(mode="json")))
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_sec_document_plan(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    if reread.plan != plan:
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan formal reread differs"
        )
    return StrongLeaderPullbackSecDocumentPlanResult(
        output_root=target,
        plan=reread.plan,
        plan_sha256=reread.plan_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan paths must be absolute"
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
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan custody or target is unsafe"
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
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecDocumentPlanError(
            "SEC document plan file metadata differs"
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
        raise StrongLeaderPullbackSecDocumentPlanError(
            "network access is prohibited for SEC document planning"
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
