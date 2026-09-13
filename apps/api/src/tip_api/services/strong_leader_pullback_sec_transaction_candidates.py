"""Form-aware transaction candidates for the first strategy lifecycle sample."""

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
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_document_content_census import (
    SecDocumentContentCensusRecordV1,
    StrongLeaderPullbackSecDocumentContentCensusResult,
    read_strong_leader_pullback_sec_document_content_census,
)
from tip_api.services.strong_leader_pullback_sec_document_plan import (
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


CONTRACT_VERSION = "strong-leader-pullback-sec-transaction-candidates/1.0"
REPORT_FILE = "candidates.json"
EXPECTED_DOCUMENT_COUNT = 89
EXPECTED_INSTRUMENT_COUNT = 63
MAXIMUM_REPORT_BYTES = 4 * 1024 * 1024
MAXIMUM_CONTEXTS_PER_FIELD = 3
CONTEXT_CHARS_BEFORE = 140
CONTEXT_CHARS_AFTER = 280
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^extraction=[A-Za-z0-9._-]+$"
_ITEM_HEADING_RE = re.compile(r"^item\s+([0-9]+\.[0-9]{2})\.?", re.IGNORECASE)
_NOTE_HEADING_RE = re.compile(
    r"^(?:introductory|explanatory) note\.?$", re.IGNORECASE
)
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December"
)
_DATE_RE = re.compile(
    rf"\b(?:{_MONTH_NAME})\s+[0-9]{{1,2}}\s*,\s*20[0-9]{{2}}\b",
    re.IGNORECASE,
)
_FIELD_PATTERNS = (
    (
        "cash_and_stock_consideration",
        re.compile(
            r"\b(?:converted into the right to receive|merger consideration|"
            r"exchange ratio|cash consideration|per share|purchase price)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "predecessor_successor_and_acquirer",
        re.compile(
            r"\b(?:surviving (?:corporation|company|entity)|merged with and into|"
            r"became a wholly owned subsidiary|acquired by|successor by merger)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "suspension_and_delisting_status",
        re.compile(
            r"\b(?:last trading day|ceased trading|suspend(?:ed|sion) of trading|"
            r"delist(?:ed|ing)|removal from listing)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tender_acceptance_or_expiration",
        re.compile(
            r"\b(?:accepted for payment|(?:tender )?offer expired|"
            r"expiration of the offer|purchased pursuant to the offer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "transaction_completion_or_closing",
        re.compile(
            r"\b(?:consummat(?:ed|ion)|completed (?:its |the |a )?"
            r"(?:acquisition|merger|transaction)|(?:merger|transaction) "
            r"(?:closed|was completed)|closing date)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "transaction_effective_time",
        re.compile(r"\beffective time\b", re.IGNORECASE),
    ),
)
TRANSACTION_FIELD_NAMES = tuple(field for field, _ in _FIELD_PATTERNS)
_TRANSACTION_SCOPE_FIELDS = frozenset(
    {
        "cash_and_stock_consideration",
        "predecessor_successor_and_acquirer",
        "transaction_completion_or_closing",
        "transaction_effective_time",
    }
)
_BASE_PARTIAL_FIELDS = frozenset(
    {
        "source_availability_time_and_revision_history",
        "stable_security_and_listing_identifiers",
    }
)
_MARKER_TO_PARTIAL_FIELD = {
    "cash_and_stock_consideration": "cash_and_stock_consideration",
    "predecessor_successor_and_acquirer": "predecessor_successor_and_acquirer",
    "suspension_and_delisting_status": (
        "suspension_and_delisting_status_effective_dates"
    ),
    "transaction_completion_or_closing": "termination_reason",
}

StructureState = Literal[
    "8k_item_2_01_candidate_scope",
    "8k_without_item_2_01_scope",
    "tender_amendment_primary_document",
    "foreign_report_referenced_exhibit_only",
    "proxy_material_no_registered_completion_scope",
]
ScopeProfile = Literal[
    "explanatory_through_item_2_01",
    "item_2_01_only",
    "full_primary_document",
]


class StrongLeaderPullbackSecTransactionCandidatesError(RuntimeError):
    """Raised when transaction candidate extraction cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecTransactionCandidateContextV1(_FrozenModel):
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=1)
    context_text: str = Field(min_length=1, max_length=1024)
    context_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def context_reconciles(self) -> "SecTransactionCandidateContextV1":
        if (
            self.normalized_end <= self.normalized_start
            or self.context_sha256 != _sha256_bytes(self.context_text.encode("utf-8"))
        ):
            raise ValueError("transaction candidate context differs")
        return self


class SecTransactionFieldCandidateV1(_FrozenModel):
    field_name: str
    scan_profile: Literal["transaction_scope", "full_primary_document"]
    occurrence_count: int = Field(ge=0)
    retained_contexts: tuple[SecTransactionCandidateContextV1, ...]
    contexts_truncated: bool
    date_token_candidates: tuple[str, ...]
    primary_document_state: Literal[
        "candidate_present", "absent_from_primary_document"
    ]
    fact_disposition: Literal[
        "unresolved_source_candidate_only"
    ] = "unresolved_source_candidate_only"

    @field_validator("date_token_candidates", mode="before")
    @classmethod
    def dates_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("transaction candidate dates differ")
        return values

    @model_validator(mode="after")
    def marker_reconciles(self) -> "SecTransactionFieldCandidateV1":
        expected_state = (
            "candidate_present"
            if self.occurrence_count
            else "absent_from_primary_document"
        )
        expected_dates = _date_tokens(
            " ".join(item.context_text for item in self.retained_contexts)
        )
        if (
            self.field_name not in TRANSACTION_FIELD_NAMES
            or len(self.retained_contexts)
            != min(self.occurrence_count, MAXIMUM_CONTEXTS_PER_FIELD)
            or self.contexts_truncated
            != (self.occurrence_count > MAXIMUM_CONTEXTS_PER_FIELD)
            or self.primary_document_state != expected_state
            or self.date_token_candidates != expected_dates
        ):
            raise ValueError("transaction candidate field differs")
        return self


class SecTransactionDocumentCandidateV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    issuer_cik_locator: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: Literal["8-K", "SC TO-T/A", "SC 14D9/A", "DEFA14A", "6-K"]
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    normalized_text_character_count: int = Field(ge=1)
    normalized_text_sha256: str = Field(pattern=_SHA256_PATTERN)
    structure_state: StructureState
    scope_profile: ScopeProfile
    scope_start_node: int = Field(ge=0)
    scope_end_node: int = Field(ge=1)
    scope_character_count: int = Field(ge=1)
    scope_sha256: str = Field(pattern=_SHA256_PATTERN)
    referenced_completion_exhibit: bool
    field_candidates: tuple[SecTransactionFieldCandidateV1, ...]
    partial_field_candidates: tuple[str, ...]
    unresolved_complete_fields: tuple[str, ...] = LIFECYCLE_REQUIRED_FIELDS
    listed_security_identity_authorized: Literal[False] = False
    transaction_completion_fact_count: Literal[0] = 0
    lifecycle_fact_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "partial_field_candidates", "unresolved_complete_fields", mode="before"
    )
    @classmethod
    def values_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("transaction candidate values differ")
        return values

    @model_validator(mode="after")
    def candidate_reconciles(self) -> "SecTransactionDocumentCandidateV1":
        expected_reference = self.structure_state == (
            "foreign_report_referenced_exhibit_only"
        )
        if (
            self.scope_end_node <= self.scope_start_node
            or tuple(item.field_name for item in self.field_candidates)
            != TRANSACTION_FIELD_NAMES
            or self.referenced_completion_exhibit != expected_reference
            or self.partial_field_candidates != _partial_fields(self.field_candidates)
            or self.unresolved_complete_fields != LIFECYCLE_REQUIRED_FIELDS
            or any(
                marker.scan_profile
                != (
                    "transaction_scope"
                    if self.structure_state == "8k_item_2_01_candidate_scope"
                    and marker.field_name in _TRANSACTION_SCOPE_FIELDS
                    else "full_primary_document"
                )
                for marker in self.field_candidates
            )
        ):
            raise ValueError("transaction document candidate differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("transaction candidate fingerprint differs")
        return self


class StrongLeaderPullbackSecTransactionCandidatesV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-transaction-candidates/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "form_aware_candidates_complete_transaction_facts_unresolved"
    ] = "form_aware_candidates_complete_transaction_facts_unresolved"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    content_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    content_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_document_count: Literal[89] = EXPECTED_DOCUMENT_COUNT
    instrument_count: Literal[63] = EXPECTED_INSTRUMENT_COUNT
    duplicate_instrument_count: Literal[14] = 14
    maximum_instrument_document_count: Literal[3] = 3
    form_counts: tuple[tuple[str, int], ...]
    structure_state_counts: tuple[tuple[str, int], ...]
    field_candidate_document_counts: tuple[tuple[str, int], ...]
    field_candidate_occurrence_counts: tuple[tuple[str, int], ...]
    document_with_field_candidate_count: int = Field(ge=0, le=89)
    referenced_completion_exhibit_count: int = Field(ge=0, le=89)
    partial_field_candidate_document_counts: tuple[tuple[str, int], ...]
    complete_field_support_counts: tuple[tuple[str, int], ...]
    candidates: tuple[SecTransactionDocumentCandidateV1, ...]
    full_document_text_retained: Literal[False] = False
    candidate_context_is_fact: Literal[False] = False
    listed_security_identity_assignment_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecTransactionCandidatesV1":
        ids = Counter(item.instrument_id for item in self.candidates)
        documents = Counter()
        occurrences = Counter()
        for item in self.candidates:
            documents.update(
                marker.field_name
                for marker in item.field_candidates
                if marker.occurrence_count
            )
            occurrences.update(
                {
                    marker.field_name: marker.occurrence_count
                    for marker in item.field_candidates
                    if marker.occurrence_count
                }
            )
        with_candidate = sum(
            any(marker.occurrence_count for marker in item.field_candidates)
            for item in self.candidates
        )
        partial_counts = tuple(
            (
                field,
                sum(field in item.partial_field_candidates for item in self.candidates),
            )
            for field in LIFECYCLE_REQUIRED_FIELDS
        )
        if (
            len(self.candidates) != EXPECTED_DOCUMENT_COUNT
            or tuple(item.request_sequence for item in self.candidates)
            != tuple(sorted(item.request_sequence for item in self.candidates))
            or len(ids) != EXPECTED_INSTRUMENT_COUNT
            or sum(count > 1 for count in ids.values()) != 14
            or max(ids.values()) != 3
            or self.form_counts != _ordered(Counter(item.form for item in self.candidates))
            or self.structure_state_counts
            != _ordered(Counter(item.structure_state for item in self.candidates))
            or self.field_candidate_document_counts != _all_field_counts(documents)
            or self.field_candidate_occurrence_counts != _all_field_counts(occurrences)
            or self.document_with_field_candidate_count != with_candidate
            or self.referenced_completion_exhibit_count
            != sum(item.referenced_completion_exhibit for item in self.candidates)
            or self.partial_field_candidate_document_counts != partial_counts
            or self.complete_field_support_counts
            != tuple((field, 0) for field in LIFECYCLE_REQUIRED_FIELDS)
        ):
            raise ValueError("transaction candidate report aggregates differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("transaction candidate report fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecTransactionCandidatesResult:
    output_root: Path
    report: StrongLeaderPullbackSecTransactionCandidatesV1
    report_sha256: str
    status: Literal["published", "already_present"]


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.raw_parts: list[str] = []
        self.nodes: list[str] = []
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
        if self._skip_depth:
            return
        self.raw_parts.append(data)
        normalized = " ".join(unicodedata.normalize("NFKC", data).split())
        if normalized:
            self.nodes.append(normalized)


def build_strong_leader_pullback_sec_transaction_candidates(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    content_census_root: Path,
    content_census_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecTransactionCandidatesResult:
    with _network_prohibited():
        plan = read_strong_leader_pullback_sec_document_plan(
            output_root=plan_root, output_custody_root=plan_custody_root
        )
        source = read_strong_leader_pullback_sec_document_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=source_root,
            output_custody_root=source_custody_root,
        )
        census = read_strong_leader_pullback_sec_document_content_census(
            output_root=content_census_root,
            output_custody_root=content_census_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            census=census,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_transaction_candidates(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecTransactionCandidatesResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecTransactionCandidatesV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate report bytes are not canonical"
        )
    return StrongLeaderPullbackSecTransactionCandidatesResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    source: StrongLeaderPullbackSecDocumentSourceResult,
    census: StrongLeaderPullbackSecDocumentContentCensusResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecTransactionCandidatesV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate revision is invalid"
        )
    manifest = source.manifest
    if manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction source manifest is unavailable"
        )
    if (
        census.report.source_manifest_sha256 != source.manifest_sha256
        or census.report.source_logical_fingerprint != manifest.logical_fingerprint
        or census.report.plan_sha256 != plan.plan_sha256
        or census.report.plan_logical_fingerprint != plan.plan.logical_fingerprint
        or census.report.parsed_document_count != 219
    ):
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction content-census binding differs"
        )
    permitted_forms = {"8-K", "SC TO-T/A", "SC 14D9/A", "DEFA14A", "6-K"}
    items = tuple(item for item in plan.plan.items if item.form in permitted_forms)
    expected_forms = Counter(
        {"8-K": 62, "SC TO-T/A": 12, "SC 14D9/A": 12, "DEFA14A": 2, "6-K": 1}
    )
    if len(items) != EXPECTED_DOCUMENT_COUNT or Counter(
        item.form for item in items
    ) != expected_forms:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction plan population differs"
        )
    census_by_sequence = {
        item.request_sequence: item for item in census.report.records
    }
    candidates = tuple(
        _extract_candidate(
            item=item,
            census_record=census_by_sequence[item.request_sequence],
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in items
    )
    documents = Counter()
    occurrences = Counter()
    for item in candidates:
        documents.update(
            marker.field_name
            for marker in item.field_candidates
            if marker.occurrence_count
        )
        occurrences.update(
            {
                marker.field_name: marker.occurrence_count
                for marker in item.field_candidates
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
        "content_census_sha256": census.report_sha256,
        "content_census_logical_fingerprint": census.report.logical_fingerprint,
        "form_counts": _ordered(Counter(item.form for item in candidates)),
        "structure_state_counts": _ordered(
            Counter(item.structure_state for item in candidates)
        ),
        "field_candidate_document_counts": _all_field_counts(documents),
        "field_candidate_occurrence_counts": _all_field_counts(occurrences),
        "document_with_field_candidate_count": sum(
            any(marker.occurrence_count for marker in item.field_candidates)
            for item in candidates
        ),
        "referenced_completion_exhibit_count": sum(
            item.referenced_completion_exhibit for item in candidates
        ),
        "partial_field_candidate_document_counts": tuple(
            (
                field,
                sum(field in item.partial_field_candidates for item in candidates),
            )
            for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "complete_field_support_counts": tuple(
            (field, 0) for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "candidates": candidates,
    }
    provisional = StrongLeaderPullbackSecTransactionCandidatesV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecTransactionCandidatesV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _extract_candidate(
    *,
    item: SecPrimaryDocumentPlanItemV1,
    census_record: SecDocumentContentCensusRecordV1,
    path: Path,
) -> SecTransactionDocumentCandidateV1:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction source is not UTF-8"
        ) from exc
    parser = _DocumentParser()
    parser.feed(text)
    parser.close()
    nodes = tuple(parser.nodes)
    normalized = " ".join(
        unicodedata.normalize("NFKC", " ".join(parser.raw_parts)).split()
    )
    document_sha256 = _sha256_bytes(raw)
    normalized_sha256 = _sha256_bytes(normalized.encode("utf-8"))
    if (
        not normalized
        or census_record.request_sequence != item.request_sequence
        or census_record.document_sha256 != document_sha256
        or census_record.normalized_text_sha256 != normalized_sha256
        or census_record.normalized_text_character_count != len(normalized)
    ):
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction source/content-census record differs"
        )
    structure, profile, start, end, referenced = _structure_and_scope(item.form, nodes)
    scope = " ".join(nodes[start:end])
    field_candidates = tuple(
        _field_candidate(
            field=field,
            pattern=pattern,
            scan_text=(
                scope
                if structure == "8k_item_2_01_candidate_scope"
                and field in _TRANSACTION_SCOPE_FIELDS
                else normalized
            ),
            scan_profile=(
                "transaction_scope"
                if structure == "8k_item_2_01_candidate_scope"
                and field in _TRANSACTION_SCOPE_FIELDS
                else "full_primary_document"
            ),
        )
        for field, pattern in _FIELD_PATTERNS
    )
    values = {
        "request_sequence": item.request_sequence,
        "instrument_id": item.instrument_id,
        "issuer_cik_locator": item.cik,
        "accession_number": item.accession_number,
        "form": item.form,
        "filing_date": item.filing_date,
        "acceptance_datetime": item.acceptance_datetime,
        "document_sha256": document_sha256,
        "normalized_text_character_count": len(normalized),
        "normalized_text_sha256": normalized_sha256,
        "structure_state": structure,
        "scope_profile": profile,
        "scope_start_node": start,
        "scope_end_node": end,
        "scope_character_count": len(scope),
        "scope_sha256": _sha256_bytes(scope.encode("utf-8")),
        "referenced_completion_exhibit": referenced,
        "field_candidates": field_candidates,
        "partial_field_candidates": _partial_fields(field_candidates),
    }
    provisional = SecTransactionDocumentCandidateV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecTransactionDocumentCandidateV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _structure_and_scope(
    form: str, nodes: tuple[str, ...]
) -> tuple[StructureState, ScopeProfile, int, int, bool]:
    if form == "8-K":
        headings = tuple(
            (index, match.group(1))
            for index, node in enumerate(nodes)
            if (match := _ITEM_HEADING_RE.match(node)) is not None
        )
        item_two = tuple(index for index, code in headings if code == "2.01")
        if not item_two:
            return (
                "8k_without_item_2_01_scope",
                "full_primary_document",
                0,
                len(nodes),
                False,
            )
        if len(item_two) != 1:
            raise StrongLeaderPullbackSecTransactionCandidatesError(
                "8-K Item 2.01 structure is ambiguous"
            )
        item_start = item_two[0]
        note_starts = tuple(
            index
            for index, node in enumerate(nodes[:item_start])
            if _NOTE_HEADING_RE.fullmatch(node)
        )
        start = note_starts[-1] if note_starts else item_start
        end = next(
            (index for index, _ in headings if index > item_start), len(nodes)
        )
        profile: ScopeProfile = (
            "explanatory_through_item_2_01" if note_starts else "item_2_01_only"
        )
        return "8k_item_2_01_candidate_scope", profile, start, end, False
    if form in {"SC TO-T/A", "SC 14D9/A"}:
        return (
            "tender_amendment_primary_document",
            "full_primary_document",
            0,
            len(nodes),
            False,
        )
    if form == "6-K":
        referenced = any("closes arrangement" in node.lower() for node in nodes)
        if not referenced:
            raise StrongLeaderPullbackSecTransactionCandidatesError(
                "6-K completion-exhibit reference is unavailable"
            )
        return (
            "foreign_report_referenced_exhibit_only",
            "full_primary_document",
            0,
            len(nodes),
            True,
        )
    if form == "DEFA14A":
        return (
            "proxy_material_no_registered_completion_scope",
            "full_primary_document",
            0,
            len(nodes),
            False,
        )
    raise StrongLeaderPullbackSecTransactionCandidatesError(
        "transaction form is unsupported"
    )


def _field_candidate(
    *,
    field: str,
    pattern: re.Pattern[str],
    scan_text: str,
    scan_profile: Literal["transaction_scope", "full_primary_document"],
) -> SecTransactionFieldCandidateV1:
    matches = tuple(pattern.finditer(scan_text))
    contexts = tuple(
        _context(scan_text, match.start(), match.end())
        for match in matches[:MAXIMUM_CONTEXTS_PER_FIELD]
    )
    return SecTransactionFieldCandidateV1(
        field_name=field,
        scan_profile=scan_profile,
        occurrence_count=len(matches),
        retained_contexts=contexts,
        contexts_truncated=len(matches) > MAXIMUM_CONTEXTS_PER_FIELD,
        date_token_candidates=_date_tokens(
            " ".join(item.context_text for item in contexts)
        ),
        primary_document_state=(
            "candidate_present" if matches else "absent_from_primary_document"
        ),
    )


def _context(
    text: str, start: int, end: int
) -> SecTransactionCandidateContextV1:
    context_start = max(0, start - CONTEXT_CHARS_BEFORE)
    context_end = min(len(text), end + CONTEXT_CHARS_AFTER)
    value = text[context_start:context_end]
    return SecTransactionCandidateContextV1(
        normalized_start=context_start,
        normalized_end=context_end,
        context_text=value,
        context_sha256=_sha256_bytes(value.encode("utf-8")),
    )


def _date_tokens(text: str) -> tuple[str, ...]:
    values = set()
    for match in _DATE_RE.finditer(text):
        normalized = re.sub(r"\s+,", ",", match.group().title())
        values.add(datetime.strptime(normalized, "%B %d, %Y").date().isoformat())
    return tuple(sorted(values))


def _partial_fields(
    markers: tuple[SecTransactionFieldCandidateV1, ...]
) -> tuple[str, ...]:
    values = set(_BASE_PARTIAL_FIELDS)
    for marker in markers:
        lifecycle_field = _MARKER_TO_PARTIAL_FIELD.get(marker.field_name)
        if marker.occurrence_count and lifecycle_field is not None:
            values.add(lifecycle_field)
    return tuple(sorted(values))


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecTransactionCandidatesV1,
) -> StrongLeaderPullbackSecTransactionCandidatesResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_transaction_candidates(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecTransactionCandidatesError(
                "existing transaction candidate report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate staging target exists"
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
    reread = read_strong_leader_pullback_sec_transaction_candidates(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecTransactionCandidatesResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate paths must be absolute"
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
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate custody or target is unsafe"
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
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "transaction candidate file metadata differs"
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
    return tuple((field, counter[field]) for field in TRANSACTION_FIELD_NAMES)


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
        raise StrongLeaderPullbackSecTransactionCandidatesError(
            "network access is prohibited during transaction extraction"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
