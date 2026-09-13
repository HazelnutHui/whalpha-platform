"""Field-level Form 15 candidates for the first strategy lifecycle sample."""

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


CONTRACT_VERSION = "strong-leader-pullback-sec-form15-candidates/1.0"
REPORT_FILE = "candidates.json"
EXPECTED_DOCUMENT_COUNT = 66
EXPECTED_INSTRUMENT_COUNT = 62
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^extraction=[A-Za-z0-9._-]+$"
_COMMISSION_FILE_RE = re.compile(
    r"(?<![0-9A-Za-z-])(?:000|001|0|1|333)-[0-9]{3,6}(?![0-9A-Za-z-])"
)
_COMMISSION_PREFIX_RE = re.compile(r"(?:000|001|00|0|1|333)$")
_SECURITY_CLASS_LABEL_RE = re.compile(
    r"^\(titles? of (?:each )?class(?:es)? of securities covered by this form\)$",
    re.IGNORECASE,
)
_SIGNATURE_LABEL_RE = re.compile(r"^dated?\s*:", re.IGNORECASE)
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December"
)
_SIGNATURE_DATE_RE = re.compile(
    rf"\b(?:{_MONTH_NAME})\s+[0-9]{{1,2}}\s*,\s*20[0-9]{{2}}\b",
    re.IGNORECASE,
)
_RULE_RE = re.compile(
    r"(?:rule\s+)?(12g-4\(a\)\([12]\)|12h-3\(b\)\(1\)\((?:ii|i)\)|"
    r"15d-6|15d-22\(b\))",
    re.IGNORECASE,
)
_SELECTED_MARKS = frozenset({"☒", "☑", "x", "X", "[x]", "[X]"})
_RULE_CANONICAL = {
    "12g-4(a)(1)": "17 CFR 240.12g-4(a)(1)",
    "12g-4(a)(2)": "17 CFR 240.12g-4(a)(2)",
    "12h-3(b)(1)(i)": "17 CFR 240.12h-3(b)(1)(i)",
    "12h-3(b)(1)(ii)": "17 CFR 240.12h-3(b)(1)(ii)",
    "15d-6": "17 CFR 240.15d-6",
    "15d-22(b)": "17 CFR 240.15d-22(b)",
}
_PARTIAL_FIELDS = tuple(
    sorted(
        {
            "source_availability_time_and_revision_history",
            "stable_security_and_listing_identifiers",
            "suspension_and_delisting_status_effective_dates",
        }
    )
)

CandidateState = Literal[
    "single_candidate", "multiple_candidates", "unsupported_template"
]
RuleState = Literal["selected_controls_extracted", "unsupported_template"]
ClassState = Literal["text_fragments_extracted", "unsupported_template"]
DateRelationship = Literal[
    "before_filing_date", "same_as_filing_date", "after_filing_date", "unresolved"
]


class StrongLeaderPullbackSecForm15CandidatesError(RuntimeError):
    """Raised when the bounded Form 15 extraction cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecForm15CandidateV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    issuer_cik_locator: str = Field(pattern=r"^[0-9]{10}$")
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: Literal["15-12G", "15-15D"]
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    commission_file_number_candidates: tuple[str, ...]
    commission_file_number_state: CandidateState
    security_class_text_fragments: tuple[str, ...]
    security_class_state: ClassState
    certification_date_candidates: tuple[date, ...]
    certification_date_state: CandidateState
    certification_date_filing_relationship: DateRelationship
    selected_rule_provisions: tuple[str, ...]
    selected_rule_state: RuleState
    document_role: Literal[
        "registration_termination_or_reporting_suspension_notice"
    ] = "registration_termination_or_reporting_suspension_notice"
    partial_field_candidates: tuple[str, ...] = _PARTIAL_FIELDS
    unresolved_complete_fields: tuple[str, ...] = LIFECYCLE_REQUIRED_FIELDS
    last_tradable_date: None = None
    delisting_effective_date: None = None
    termination_reason: None = None
    predecessor_successor_or_acquirer: None = None
    cash_or_stock_consideration: None = None
    otc_or_liquidation_continuation: None = None
    structured_source_candidate_only: Literal[True] = True
    listed_security_identity_authorized: Literal[False] = False
    complete_lifecycle_field_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "commission_file_number_candidates",
        "certification_date_candidates",
        "selected_rule_provisions",
        "partial_field_candidates",
        "unresolved_complete_fields",
        mode="before",
    )
    @classmethod
    def sorted_tuples_are_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("Form 15 candidate values are not ordered and unique")
        return values

    @field_validator("security_class_text_fragments", mode="before")
    @classmethod
    def text_fragments_preserve_order(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if len(values) != len(set(values)):
            raise ValueError("Form 15 class fragments are not unique")
        return values

    @field_validator("security_class_text_fragments")
    @classmethod
    def text_fragments_are_normalized(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or item != " ".join(item.split()) for item in value):
            raise ValueError("Form 15 class fragments are not normalized")
        return value

    @model_validator(mode="after")
    def candidate_reconciles(self) -> "SecForm15CandidateV1":
        file_state = _candidate_state(len(self.commission_file_number_candidates))
        date_state = _candidate_state(len(self.certification_date_candidates))
        class_state: ClassState = (
            "text_fragments_extracted"
            if self.security_class_text_fragments
            else "unsupported_template"
        )
        rule_state: RuleState = (
            "selected_controls_extracted"
            if self.selected_rule_provisions
            else "unsupported_template"
        )
        relationship = _date_relationship(
            self.certification_date_candidates, self.filing_date
        )
        if (
            self.commission_file_number_state != file_state
            or self.certification_date_state != date_state
            or self.security_class_state != class_state
            or self.selected_rule_state != rule_state
            or self.certification_date_filing_relationship != relationship
            or any(
                value not in _RULE_CANONICAL.values()
                for value in self.selected_rule_provisions
            )
            or self.partial_field_candidates != _PARTIAL_FIELDS
            or self.unresolved_complete_fields != LIFECYCLE_REQUIRED_FIELDS
        ):
            raise ValueError("Form 15 candidate evidence differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("Form 15 candidate fingerprint differs")
        return self


class StrongLeaderPullbackSecForm15CandidatesV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-form15-candidates/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "field_level_candidates_complete_lifecycle_facts_unresolved"
    ] = "field_level_candidates_complete_lifecycle_facts_unresolved"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    content_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    content_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    form15_document_count: Literal[66] = EXPECTED_DOCUMENT_COUNT
    instrument_count: Literal[62] = EXPECTED_INSTRUMENT_COUNT
    duplicate_instrument_count: Literal[3] = 3
    maximum_instrument_document_count: Literal[3] = 3
    form_counts: tuple[tuple[str, int], ...]
    commission_file_number_state_counts: tuple[tuple[str, int], ...]
    security_class_state_counts: tuple[tuple[str, int], ...]
    certification_date_state_counts: tuple[tuple[str, int], ...]
    certification_date_filing_relationship_counts: tuple[tuple[str, int], ...]
    selected_rule_state_counts: tuple[tuple[str, int], ...]
    selected_rule_counts: tuple[tuple[str, int], ...]
    partial_field_candidate_document_counts: tuple[tuple[str, int], ...]
    complete_field_support_counts: tuple[tuple[str, int], ...]
    candidates: tuple[SecForm15CandidateV1, ...]
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecForm15CandidatesV1":
        ids = Counter(item.instrument_id for item in self.candidates)
        rules = Counter(
            rule for item in self.candidates for rule in item.selected_rule_provisions
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
            or sum(count > 1 for count in ids.values()) != 3
            or max(ids.values()) != 3
            or self.form_counts != _ordered(Counter(item.form for item in self.candidates))
            or self.commission_file_number_state_counts
            != _ordered(Counter(item.commission_file_number_state for item in self.candidates))
            or self.security_class_state_counts
            != _ordered(Counter(item.security_class_state for item in self.candidates))
            or self.certification_date_state_counts
            != _ordered(Counter(item.certification_date_state for item in self.candidates))
            or self.certification_date_filing_relationship_counts
            != _ordered(
                Counter(
                    item.certification_date_filing_relationship
                    for item in self.candidates
                )
            )
            or self.selected_rule_state_counts
            != _ordered(Counter(item.selected_rule_state for item in self.candidates))
            or self.selected_rule_counts != _ordered(rules)
            or self.partial_field_candidate_document_counts != partial_counts
            or self.complete_field_support_counts
            != tuple((field, 0) for field in LIFECYCLE_REQUIRED_FIELDS)
        ):
            raise ValueError("Form 15 candidate report aggregates differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("Form 15 candidate report fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecForm15CandidatesResult:
    output_root: Path
    report: StrongLeaderPullbackSecForm15CandidatesV1
    report_sha256: str
    status: Literal["published", "already_present"]


class _DocumentNodeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
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
        if not self._skip_depth:
            normalized = " ".join(unicodedata.normalize("NFKC", data).split())
            if normalized:
                self.nodes.append(normalized)


def build_strong_leader_pullback_sec_form15_candidates(
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
) -> StrongLeaderPullbackSecForm15CandidatesResult:
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


def read_strong_leader_pullback_sec_form15_candidates(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecForm15CandidatesResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecForm15CandidatesV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate report bytes are not canonical"
        )
    return StrongLeaderPullbackSecForm15CandidatesResult(
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
) -> StrongLeaderPullbackSecForm15CandidatesV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate revision is invalid"
        )
    manifest = source.manifest
    if manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 source manifest is unavailable"
        )
    if (
        census.report.source_manifest_sha256 != source.manifest_sha256
        or census.report.source_logical_fingerprint != manifest.logical_fingerprint
        or census.report.plan_sha256 != plan.plan_sha256
        or census.report.plan_logical_fingerprint != plan.plan.logical_fingerprint
        or census.report.parsed_document_count != 219
    ):
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 content-census binding differs"
        )
    items = tuple(item for item in plan.plan.items if item.form.startswith("15-"))
    if (
        len(items) != EXPECTED_DOCUMENT_COUNT
        or Counter(item.form for item in items) != Counter({"15-12G": 63, "15-15D": 3})
    ):
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 plan population differs"
        )
    candidates = tuple(
        _extract_candidate(
            item=item,
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in items
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
        "commission_file_number_state_counts": _ordered(
            Counter(item.commission_file_number_state for item in candidates)
        ),
        "security_class_state_counts": _ordered(
            Counter(item.security_class_state for item in candidates)
        ),
        "certification_date_state_counts": _ordered(
            Counter(item.certification_date_state for item in candidates)
        ),
        "certification_date_filing_relationship_counts": _ordered(
            Counter(item.certification_date_filing_relationship for item in candidates)
        ),
        "selected_rule_state_counts": _ordered(
            Counter(item.selected_rule_state for item in candidates)
        ),
        "selected_rule_counts": _ordered(
            Counter(
                rule
                for item in candidates
                for rule in item.selected_rule_provisions
            )
        ),
        "partial_field_candidate_document_counts": tuple(
            (field, EXPECTED_DOCUMENT_COUNT if field in _PARTIAL_FIELDS else 0)
            for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "complete_field_support_counts": tuple(
            (field, 0) for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "candidates": candidates,
    }
    provisional = StrongLeaderPullbackSecForm15CandidatesV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecForm15CandidatesV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _extract_candidate(
    *, item: SecPrimaryDocumentPlanItemV1, path: Path
) -> SecForm15CandidateV1:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 source is not UTF-8"
        ) from exc
    parser = _DocumentNodeParser()
    parser.feed(text)
    parser.close()
    nodes = tuple(parser.nodes)
    commission_files = _commission_file_numbers(nodes)
    class_fragments = _security_class_fragments(nodes)
    certification_dates = _certification_dates(nodes)
    selected_rules = _selected_rules(nodes)
    values = {
        "request_sequence": item.request_sequence,
        "instrument_id": item.instrument_id,
        "issuer_cik_locator": item.cik,
        "accession_number": item.accession_number,
        "form": item.form,
        "filing_date": item.filing_date,
        "acceptance_datetime": item.acceptance_datetime,
        "document_sha256": _sha256_bytes(raw),
        "commission_file_number_candidates": commission_files,
        "commission_file_number_state": _candidate_state(len(commission_files)),
        "security_class_text_fragments": class_fragments,
        "security_class_state": (
            "text_fragments_extracted" if class_fragments else "unsupported_template"
        ),
        "certification_date_candidates": certification_dates,
        "certification_date_state": _candidate_state(len(certification_dates)),
        "certification_date_filing_relationship": _date_relationship(
            certification_dates, item.filing_date
        ),
        "selected_rule_provisions": selected_rules,
        "selected_rule_state": (
            "selected_controls_extracted" if selected_rules else "unsupported_template"
        ),
    }
    provisional = SecForm15CandidateV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecForm15CandidateV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _commission_file_numbers(nodes: tuple[str, ...]) -> tuple[str, ...]:
    values: set[str] = set()
    for index, node in enumerate(nodes):
        if "commission file" not in node.lower():
            continue
        same_node = _COMMISSION_FILE_RE.findall(node)
        if same_node:
            values.update(same_node)
            continue
        trailing_prefix = _COMMISSION_PREFIX_RE.search(node)
        if trailing_prefix and index + 1 < len(nodes):
            values.update(
                _COMMISSION_FILE_RE.findall(trailing_prefix.group() + nodes[index + 1])
            )
            continue
        if index + 1 >= len(nodes):
            continue
        next_node = nodes[index + 1]
        next_values = _COMMISSION_FILE_RE.findall(next_node)
        if next_values:
            values.update(next_values)
        elif (
            _COMMISSION_PREFIX_RE.fullmatch(next_node)
            and index + 2 < len(nodes)
        ):
            values.update(
                _COMMISSION_FILE_RE.findall(next_node + nodes[index + 2])
            )
    return tuple(sorted(values))


def _security_class_fragments(nodes: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    for index, node in enumerate(nodes):
        if _SECURITY_CLASS_LABEL_RE.fullmatch(node) is None:
            continue
        boundary = None
        for previous in range(index - 1, max(-1, index - 30), -1):
            if "principal executive offices)" in nodes[previous].lower():
                boundary = previous + 1
                break
        if boundary is not None:
            values.extend(nodes[boundary:index])
    return tuple(dict.fromkeys(values))


def _certification_dates(nodes: tuple[str, ...]) -> tuple[date, ...]:
    values: set[date] = set()
    for index, node in enumerate(nodes):
        if _SIGNATURE_LABEL_RE.match(node) is None:
            continue
        bounded = " ".join(nodes[index : index + 3])
        for value in _SIGNATURE_DATE_RE.findall(bounded):
            normalized = re.sub(r"\s+,", ",", value.title())
            values.add(datetime.strptime(normalized, "%B %d, %Y").date())
    return tuple(sorted(values))


def _selected_rules(nodes: tuple[str, ...]) -> tuple[str, ...]:
    values: set[str] = set()
    for index, node in enumerate(nodes):
        match = _RULE_RE.search(node)
        if match is None:
            continue
        same_node_mark = node[match.end() :].strip()
        next_node_mark = nodes[index + 1].strip() if index + 1 < len(nodes) else ""
        if same_node_mark not in _SELECTED_MARKS and next_node_mark not in _SELECTED_MARKS:
            continue
        canonical = _RULE_CANONICAL.get(match.group(1).lower())
        if canonical is None:
            raise StrongLeaderPullbackSecForm15CandidatesError(
                "Form 15 selected-rule registry differs"
            )
        values.add(canonical)
    return tuple(sorted(values))


def _candidate_state(count: int) -> CandidateState:
    if count == 0:
        return "unsupported_template"
    if count == 1:
        return "single_candidate"
    return "multiple_candidates"


def _date_relationship(values: tuple[date, ...], filing_date: date) -> DateRelationship:
    if len(values) != 1:
        return "unresolved"
    if values[0] < filing_date:
        return "before_filing_date"
    if values[0] > filing_date:
        return "after_filing_date"
    return "same_as_filing_date"


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecForm15CandidatesV1,
) -> StrongLeaderPullbackSecForm15CandidatesResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_form15_candidates(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecForm15CandidatesError(
                "existing Form 15 candidate report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate staging target exists"
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
    reread = read_strong_leader_pullback_sec_form15_candidates(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecForm15CandidatesResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate paths must be absolute"
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
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate custody or target is unsafe"
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
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "Form 15 candidate file metadata differs"
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fingerprint(value: object) -> str:
    return _sha256_bytes(_json_bytes(value).rstrip(b"\n"))


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackSecForm15CandidatesError(
            "network access is prohibited during Form 15 extraction"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
