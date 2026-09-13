"""Deterministic content census for the frozen SEC lifecycle documents."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import unicodedata
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_document_plan import (
    EXPECTED_REQUEST_COUNT,
    SecPrimaryDocumentPlanItemV1,
    StrongLeaderPullbackSecDocumentPlanResult,
    read_strong_leader_pullback_sec_document_plan,
)
from tip_api.services.strong_leader_pullback_sec_document_source import (
    DOCUMENT_FILE,
    StrongLeaderPullbackSecDocumentSourceResult,
    read_strong_leader_pullback_sec_document_source,
)
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    LIFECYCLE_REQUIRED_FIELDS,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-document-content-census/1.0"
REPORT_FILE = "census.json"
MAXIMUM_REPORT_BYTES = 8 * 1024 * 1024
MAXIMUM_CONTEXTS_PER_FIELD = 3
CONTEXT_CHARS_BEFORE = 100
CONTEXT_CHARS_AFTER = 180
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_CENSUS_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"

_FIELD_PATTERNS = (
    (
        "bankruptcy_liquidation_or_otc_continuation",
        r"\b(?:bankrupt(?:cy)?|liquidat(?:e|ed|ion)|chapter 11|"
        r"over-the-counter|otc)\b",
    ),
    (
        "cash_and_stock_consideration",
        r"\b(?:cash consideration|stock consideration|per share|"
        r"exchange ratio)\b",
    ),
    (
        "first_and_last_tradable_dates",
        r"\b(?:last trading day|ceased trading|cease trading|"
        r"trading (?:has )?been suspended|suspension of trading)\b",
    ),
    (
        "predecessor_successor_and_acquirer",
        r"\b(?:predecessor|successor|acquirer|purchaser|parent company)\b",
    ),
    (
        "source_availability_time_and_revision_history",
        r"\b(?:amendment|amended|supplement)\b",
    ),
    (
        "stable_security_and_listing_identifiers",
        r"\b(?:trading symbol|ticker symbol|title of each class|"
        r"name of each exchange|commission file number|cusip)\b",
    ),
    (
        "suspension_and_delisting_status_effective_dates",
        r"\b(?:delist(?:ed|ing)?|suspend(?:ed|sion)?|removal from listing|"
        r"withdrawal of registration)\b",
    ),
    (
        "termination_reason",
        r"\b(?:merger|acquisition|bankrupt(?:cy)?|liquidat(?:e|ed|ion)|"
        r"dissolution|going private)\b",
    ),
)
if tuple(field for field, _ in _FIELD_PATTERNS) != LIFECYCLE_REQUIRED_FIELDS:
    raise RuntimeError("SEC content-census field registry differs")
_COMPILED_PATTERNS = tuple(
    (field, re.compile(pattern, re.IGNORECASE))
    for field, pattern in _FIELD_PATTERNS
)


class StrongLeaderPullbackSecDocumentContentCensusError(RuntimeError):
    """Raised when the SEC document content census cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecDocumentMarkerContextV1(_FrozenModel):
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=1)
    context_text: str = Field(min_length=1, max_length=512)
    context_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def context_reconciles(self) -> "SecDocumentMarkerContextV1":
        if (
            self.normalized_end <= self.normalized_start
            or self.context_sha256 != _sha256_bytes(self.context_text.encode("utf-8"))
        ):
            raise ValueError("SEC document marker context differs")
        return self


class SecDocumentFieldMarkerV1(_FrozenModel):
    field_name: str
    occurrence_count: int = Field(ge=0)
    retained_contexts: tuple[SecDocumentMarkerContextV1, ...]
    contexts_truncated: bool
    fact_disposition: Literal["unresolved_lexical_candidate_only"] = (
        "unresolved_lexical_candidate_only"
    )

    @model_validator(mode="after")
    def marker_reconciles(self) -> "SecDocumentFieldMarkerV1":
        if (
            len(self.retained_contexts)
            != min(self.occurrence_count, MAXIMUM_CONTEXTS_PER_FIELD)
            or self.contexts_truncated
            != (self.occurrence_count > MAXIMUM_CONTEXTS_PER_FIELD)
        ):
            raise ValueError("SEC document marker context count differs")
        return self


class SecDocumentContentCensusRecordV1(_FrozenModel):
    request_sequence: int = Field(ge=1, le=EXPECTED_REQUEST_COUNT)
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: str
    acceptance_datetime: datetime
    document_byte_count: int = Field(ge=1)
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    decoding: Literal["utf-8", "utf-8-sig", "windows-1252"]
    markup_profile: Literal["html", "sec-sgml-html", "xhtml-inline-xbrl"]
    normalized_text_character_count: int = Field(ge=1)
    normalized_text_sha256: str = Field(pattern=_SHA256_PATTERN)
    date_token_count: int = Field(ge=0)
    form_is_amendment: bool
    field_markers: tuple[SecDocumentFieldMarkerV1, ...]
    parsing_complete: Literal[True] = True
    listed_security_identity_authorized: Literal[False] = False
    lifecycle_fact_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def record_reconciles(self) -> "SecDocumentContentCensusRecordV1":
        if tuple(item.field_name for item in self.field_markers) != (
            LIFECYCLE_REQUIRED_FIELDS
        ):
            raise ValueError("SEC document content fields differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC document content record fingerprint differs")
        return self


class StrongLeaderPullbackSecDocumentContentCensusV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-document-content-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "content_parsed_field_candidates_unresolved"
    ] = "content_parsed_field_candidates_unresolved"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_artifact_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    marker_ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    document_count: Literal[219] = EXPECTED_REQUEST_COUNT
    parsed_document_count: Literal[219] = EXPECTED_REQUEST_COUNT
    form_counts: tuple[tuple[str, int], ...]
    decoding_counts: tuple[tuple[str, int], ...]
    markup_profile_counts: tuple[tuple[str, int], ...]
    field_marker_document_counts: tuple[tuple[str, int], ...]
    field_marker_occurrence_counts: tuple[tuple[str, int], ...]
    total_document_bytes: int = Field(ge=EXPECTED_REQUEST_COUNT)
    total_normalized_text_characters: int = Field(ge=EXPECTED_REQUEST_COUNT)
    records: tuple[SecDocumentContentCensusRecordV1, ...]
    full_document_text_retained: Literal[False] = False
    lexical_marker_is_fact: Literal[False] = False
    listed_security_identity_assignment_count: Literal[0] = 0
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
    def census_reconciles(self) -> "StrongLeaderPullbackSecDocumentContentCensusV1":
        if (
            tuple(item.request_sequence for item in self.records)
            != tuple(range(1, EXPECTED_REQUEST_COUNT + 1))
            or self.form_counts != _ordered(Counter(item.form for item in self.records))
            or self.decoding_counts
            != _ordered(Counter(item.decoding for item in self.records))
            or self.markup_profile_counts
            != _ordered(Counter(item.markup_profile for item in self.records))
            or self.total_document_bytes
            != sum(item.document_byte_count for item in self.records)
            or self.total_normalized_text_characters
            != sum(item.normalized_text_character_count for item in self.records)
        ):
            raise ValueError("SEC document content census aggregates differ")
        document_counts = Counter(
            marker.field_name
            for record in self.records
            for marker in record.field_markers
            if marker.occurrence_count
        )
        occurrence_counts = Counter()
        for record in self.records:
            occurrence_counts.update(
                {
                    marker.field_name: marker.occurrence_count
                    for marker in record.field_markers
                    if marker.occurrence_count
                }
            )
        if (
            self.field_marker_document_counts != _all_field_counts(document_counts)
            or self.field_marker_occurrence_counts
            != _all_field_counts(occurrence_counts)
        ):
            raise ValueError("SEC document content marker aggregates differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("SEC document content census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecDocumentContentCensusResult:
    output_root: Path
    report: StrongLeaderPullbackSecDocumentContentCensusV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_sec_document_content_census(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecDocumentContentCensusResult:
    """Parse all retained documents without assigning a lifecycle fact."""

    with _network_prohibited():
        plan = read_strong_leader_pullback_sec_document_plan(
            output_root=plan_root,
            output_custody_root=plan_custody_root,
        )
        source = read_strong_leader_pullback_sec_document_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=source_root,
            output_custody_root=source_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_document_content_census(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecDocumentContentCensusResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecDocumentContentCensusV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census bytes are not canonical"
        )
    return StrongLeaderPullbackSecDocumentContentCensusResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    source: StrongLeaderPullbackSecDocumentSourceResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecDocumentContentCensusV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census revision is invalid"
        )
    manifest = source.manifest
    if manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document source manifest is unavailable"
        )
    records = tuple(
        _parse_document(
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
            item=item,
        )
        for item in plan.plan.items
    )
    document_counts = Counter(
        marker.field_name
        for record in records
        for marker in record.field_markers
        if marker.occurrence_count
    )
    occurrence_counts = Counter()
    for record in records:
        occurrence_counts.update(
            {
                marker.field_name: marker.occurrence_count
                for marker in record.field_markers
                if marker.occurrence_count
            }
        )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "plan_sha256": plan.plan_sha256,
        "plan_logical_fingerprint": plan.plan.logical_fingerprint,
        "source_manifest_sha256": source.manifest_sha256,
        "source_logical_fingerprint": manifest.logical_fingerprint,
        "source_artifact_binding_fingerprint": (
            manifest.artifact_binding_fingerprint
        ),
        "marker_ruleset_fingerprint": _fingerprint(_FIELD_PATTERNS),
        "form_counts": _ordered(Counter(item.form for item in records)),
        "decoding_counts": _ordered(Counter(item.decoding for item in records)),
        "markup_profile_counts": _ordered(
            Counter(item.markup_profile for item in records)
        ),
        "field_marker_document_counts": _all_field_counts(document_counts),
        "field_marker_occurrence_counts": _all_field_counts(occurrence_counts),
        "total_document_bytes": sum(item.document_byte_count for item in records),
        "total_normalized_text_characters": sum(
            item.normalized_text_character_count for item in records
        ),
        "records": records,
    }
    provisional = StrongLeaderPullbackSecDocumentContentCensusV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecDocumentContentCensusV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _parse_document(
    *, path: Path, item: SecPrimaryDocumentPlanItemV1
) -> SecDocumentContentCensusRecordV1:
    raw = path.read_bytes()
    text, decoding = _decode(raw)
    profile = _markup_profile(text)
    parser = _DocumentTextParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document markup cannot be parsed"
        ) from exc
    normalized = " ".join(
        unicodedata.normalize("NFKC", " ".join(parser.parts)).split()
    )
    if not normalized:
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document normalized text is empty"
        )
    markers = tuple(
        _field_marker(field=field, pattern=pattern, normalized_text=normalized)
        for field, pattern in _COMPILED_PATTERNS
    )
    values = {
        "request_sequence": item.request_sequence,
        "instrument_id": item.instrument_id,
        "cik": item.cik,
        "accession_number": item.accession_number,
        "form": item.form,
        "acceptance_datetime": item.acceptance_datetime,
        "document_byte_count": len(raw),
        "document_sha256": _sha256_bytes(raw),
        "decoding": decoding,
        "markup_profile": profile,
        "normalized_text_character_count": len(normalized),
        "normalized_text_sha256": _sha256_bytes(normalized.encode("utf-8")),
        "date_token_count": len(_DATE_PATTERN.findall(normalized)),
        "form_is_amendment": item.form.endswith("/A"),
        "field_markers": markers,
    }
    provisional = SecDocumentContentCensusRecordV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecDocumentContentCensusRecordV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


_DATE_PATTERN = re.compile(
    r"\b(?:20[0-9]{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}/\d{1,2}/20[0-9]{2}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s+20[0-9]{2})\b",
    re.IGNORECASE,
)


def _field_marker(
    *, field: str, pattern: re.Pattern[str], normalized_text: str
) -> SecDocumentFieldMarkerV1:
    matches = tuple(pattern.finditer(normalized_text))
    contexts = tuple(
        _marker_context(normalized_text, match.start(), match.end())
        for match in matches[:MAXIMUM_CONTEXTS_PER_FIELD]
    )
    return SecDocumentFieldMarkerV1(
        field_name=field,
        occurrence_count=len(matches),
        retained_contexts=contexts,
        contexts_truncated=len(matches) > MAXIMUM_CONTEXTS_PER_FIELD,
    )


def _marker_context(text: str, start: int, end: int) -> SecDocumentMarkerContextV1:
    context_start = max(0, start - CONTEXT_CHARS_BEFORE)
    context_end = min(len(text), end + CONTEXT_CHARS_AFTER)
    context = text[context_start:context_end]
    return SecDocumentMarkerContextV1(
        normalized_start=context_start,
        normalized_end=context_end,
        context_text=context,
        context_sha256=_sha256_bytes(context.encode("utf-8")),
    )


class _DocumentTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag.lower() in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def _decode(raw: bytes) -> tuple[str, Literal["utf-8", "utf-8-sig", "windows-1252"]]:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("windows-1252"), "windows-1252"


def _markup_profile(
    text: str,
) -> Literal["html", "sec-sgml-html", "xhtml-inline-xbrl"]:
    prefix = text[:8192].lower()
    if "xmlns:ix=" in prefix or "inlinexbrl" in prefix:
        return "xhtml-inline-xbrl"
    if "<document>" in prefix:
        return "sec-sgml-html"
    return "html"


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecDocumentContentCensusV1,
) -> StrongLeaderPullbackSecDocumentContentCensusResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_document_content_census(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecDocumentContentCensusError(
                "existing SEC document content census differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(
            partial / REPORT_FILE,
            _json_bytes(report.model_dump(mode="json")),
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_sec_document_content_census(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackSecDocumentContentCensusResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_CENSUS_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census custody or target is unsafe"
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
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "SEC document content census file metadata differs"
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
        raise StrongLeaderPullbackSecDocumentContentCensusError(
            "network access is prohibited during SEC document content census"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
