"""Typed SEC transaction-completion evidence for first-strategy cases."""

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
from tip_api.services.strong_leader_pullback_sec_case_adjudication import (
    SecCoverDocumentIdentityDecisionV1,
    StrongLeaderPullbackSecCaseAdjudicationResult,
    read_strong_leader_pullback_sec_case_adjudication,
)
from tip_api.services.strong_leader_pullback_sec_document_plan import (
    StrongLeaderPullbackSecDocumentPlanResult,
    read_strong_leader_pullback_sec_document_plan,
)
from tip_api.services.strong_leader_pullback_sec_document_source import (
    DOCUMENT_FILE,
    StrongLeaderPullbackSecDocumentSourceResult,
    read_strong_leader_pullback_sec_document_source,
)
from tip_api.services.strong_leader_pullback_sec_transaction_candidates import (
    SecTransactionDocumentCandidateV1,
    StrongLeaderPullbackSecTransactionCandidatesResult,
    read_strong_leader_pullback_sec_transaction_candidates,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-transaction-event-adjudication/1.0"
REPORT_FILE = "transaction-events.json"
EXPECTED_DOCUMENT_COUNT = 61
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 2048
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_ITEM_HEADING_RE = re.compile(r"^item\s+([0-9]+\.[0-9]{2})\.?", re.IGNORECASE)
_NOTE_HEADING_RE = re.compile(
    r"^(?:introductory|explanatory) note\.?$|^introduction\.?$", re.IGNORECASE
)
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December"
)
_DATE_TOKEN = rf"(?:{_MONTH_NAME})\s+[0-9]{{1,2}}\s*,\s*20[0-9]{{2}}"
_LEADING_DATE_RE = re.compile(
    rf"\b(?:On|Effective on)\s+({_DATE_TOKEN})\b", re.IGNORECASE
)
_NAMED_CLOSING_DATE_RE = re.compile(
    rf"({_DATE_TOKEN})\s*\([^)]{{0,140}}\bClosing Date\b[^)]*\)", re.IGNORECASE
)
_CLOSING_OF_TRANSACTION_RE = re.compile(
    rf"\bclosing\s+on\s+({_DATE_TOKEN})\s*\([^)]*\)\s+of\s+"
    r"(?:the\s+)?(?:merger|transactions?)\b",
    re.IGNORECASE,
)
_TERMINAL_TRANSACTION_RE = re.compile(
    r"\b(?:"
    r"merged\s+(?:with\s+and\s+)?into|"
    r"was\s+merged\s+(?:with\s+and\s+)?into|"
    r"completed\s+(?:its\s+|the\s+|a\s+)?(?:previously\s+announced\s+)?"
    r"(?:acquisition|merger)|"
    r"(?:mergers?|acquisition|transactions?)\s+(?:was|were)\s+"
    r"(?:completed|consummated)|"
    r"(?:mergers?|transactions?)[^.]{0,240}\bwere\s+consummated|"
    r"consummated\s+(?:the\s+)?(?:merger|transactions?\s+contemplated\s+by)|"
    r"completed\s+the\s+transactions?\s+contemplated\s+by\s+[^.]{0,180}"
    r"(?:merger\s+agreement|agreement\s+and\s+plan\s+of\s+merger)"
    r")\b",
    re.IGNORECASE,
)
_TENDER_TO_MERGER_RE = re.compile(
    rf"\bOn\s+({_DATE_TOKEN})\b[^.]{{0,1000}}\baccepted\s+for\s+"
    r"(?:purchase\s+and\s+)?payment\b[^.]*"
    r"(?:\.\s*[^.]*){0,2}\beffected\s+the\s+Merger\b",
    re.IGNORECASE,
)
_SEMANTIC_BOUNDARY_RE = re.compile(
    r"(?<=[.!?])\s+(?=(?:On|Pursuant|Item|ITEM|Effective|The|This|In|As|"
    r"Following|Immediately|Capitalized|At|After|Accordingly)\b)"
)

ResolutionState = Literal["matched", "ambiguous", "unsupported"]
ScopeProfile = Literal[
    "explicit_intro_and_item_2_01",
    "implicit_pre_item_completion_and_item_2_01",
]
DecisionRule = Literal[
    "named_closing_date_in_introduction",
    "closing_of_merger_date_in_introduction",
    "dated_transaction_completion_statement",
    "tender_acceptance_followed_by_effected_merger",
]
ReportDateRelation = Literal["before_report_date", "same_as_report_date", "after_report_date"]


class StrongLeaderPullbackSecTransactionEventAdjudicationError(RuntimeError):
    """Raised when typed transaction-event evidence cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecTransactionCompletionEvidenceV1(_FrozenModel):
    event_date: date
    decision_rule: DecisionRule
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=1)
    evidence_text: str = Field(min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS)
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str) -> str:
        if value != _normalized_text(value):
            raise ValueError("transaction completion evidence is not normalized")
        return value

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "SecTransactionCompletionEvidenceV1":
        if (
            self.normalized_end <= self.normalized_start
            or self.evidence_sha256
            != _sha256_bytes(self.evidence_text.encode("utf-8"))
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("transaction completion evidence differs")
        return self


class SecTransactionEventDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    report_date: date
    scope_profile: ScopeProfile
    scope_character_count: int = Field(ge=1)
    scope_sha256: str = Field(pattern=_SHA256_PATTERN)
    resolution_state: ResolutionState
    completion_evidence: tuple[SecTransactionCompletionEvidenceV1, ...]
    selected_event_date: date | None = None
    selected_decision_rule: DecisionRule | None = None
    report_date_relation: ReportDateRelation | None = None
    issuer_event_type: Literal["merger_or_acquisition_completion"] | None = None
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if not values or values != tuple(sorted(set(values))):
            raise ValueError("transaction event decision reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "SecTransactionEventDecisionV1":
        dates = {item.event_date for item in self.completion_evidence}
        matched = self.resolution_state == "matched"
        expected_relation = (
            _report_date_relation(self.selected_event_date, self.report_date)
            if self.selected_event_date is not None
            else None
        )
        if (
            (matched and len(dates) != 1)
            or (not matched and self.selected_event_date is not None)
            or (not matched and self.selected_decision_rule is not None)
            or (not matched and self.issuer_event_type is not None)
            or (matched and self.selected_event_date not in dates)
            or (
                matched
                and self.selected_decision_rule
                not in {item.decision_rule for item in self.completion_evidence}
            )
            or self.report_date_relation != expected_relation
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("transaction event decision differs")
        return self


class StrongLeaderPullbackSecTransactionEventAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-transaction-event-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["typed_transaction_event_evidence_adjudicated"] = (
        "typed_transaction_event_evidence_adjudicated"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cover_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cover_adjudication_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_document_count: Literal[61] = EXPECTED_DOCUMENT_COUNT
    matched_event_count: int = Field(ge=0, le=61)
    ambiguous_event_count: int = Field(ge=0, le=61)
    unsupported_event_count: int = Field(ge=0, le=61)
    resolution_state_counts: tuple[tuple[str, int], ...]
    decision_rule_counts: tuple[tuple[str, int], ...]
    scope_profile_counts: tuple[tuple[str, int], ...]
    report_date_relation_counts: tuple[tuple[str, int], ...]
    report_date_difference_count: int = Field(ge=0, le=61)
    earliest_event_date: date | None = None
    latest_event_date: date | None = None
    decisions: tuple[SecTransactionEventDecisionV1, ...]
    issuer_transaction_completion_evidence_count: int = Field(ge=0, le=61)
    termination_reason_adjudication_count: Literal[0] = 0
    consideration_adjudication_count: Literal[0] = 0
    party_relation_adjudication_count: Literal[0] = 0
    first_or_last_tradable_date_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecTransactionEventAdjudicationV1":
        resolutions = Counter(item.resolution_state for item in self.decisions)
        rules = Counter(
            item.selected_decision_rule
            for item in self.decisions
            if item.selected_decision_rule is not None
        )
        profiles = Counter(item.scope_profile for item in self.decisions)
        relations = Counter(
            item.report_date_relation
            for item in self.decisions
            if item.report_date_relation is not None
        )
        event_dates = tuple(
            item.selected_event_date
            for item in self.decisions
            if item.selected_event_date is not None
        )
        if (
            len(self.decisions) != EXPECTED_DOCUMENT_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or self.matched_event_count != resolutions["matched"]
            or self.ambiguous_event_count != resolutions["ambiguous"]
            or self.unsupported_event_count != resolutions["unsupported"]
            or self.resolution_state_counts != _ordered(resolutions)
            or self.decision_rule_counts != _ordered(rules)
            or self.scope_profile_counts != _ordered(profiles)
            or self.report_date_relation_counts != _ordered(relations)
            or self.report_date_difference_count
            != sum(item != "same_as_report_date" for item in relations.elements())
            or self.earliest_event_date != (min(event_dates) if event_dates else None)
            or self.latest_event_date != (max(event_dates) if event_dates else None)
            or self.issuer_transaction_completion_evidence_count
            != self.matched_event_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("transaction event adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecTransactionEventAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackSecTransactionEventAdjudicationV1
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
        normalized = _normalized_text(data)
        if normalized:
            self.nodes.append(normalized)


def build_strong_leader_pullback_sec_transaction_event_adjudication(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    transaction_root: Path,
    transaction_custody_root: Path,
    cover_adjudication_root: Path,
    cover_adjudication_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecTransactionEventAdjudicationResult:
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
        transaction = read_strong_leader_pullback_sec_transaction_candidates(
            output_root=transaction_root,
            output_custody_root=transaction_custody_root,
        )
        cover = read_strong_leader_pullback_sec_case_adjudication(
            output_root=cover_adjudication_root,
            output_custody_root=cover_adjudication_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            transaction=transaction,
            cover=cover,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_transaction_event_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecTransactionEventAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecTransactionEventAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event report bytes are not canonical"
        )
    return StrongLeaderPullbackSecTransactionEventAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    source: StrongLeaderPullbackSecDocumentSourceResult,
    transaction: StrongLeaderPullbackSecTransactionCandidatesResult,
    cover: StrongLeaderPullbackSecCaseAdjudicationResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecTransactionEventAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event revision is invalid"
        )
    if source.manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event source manifest is unavailable"
        )
    if (
        transaction.report.plan_sha256 != plan.plan_sha256
        or transaction.report.source_manifest_sha256 != source.manifest_sha256
        or cover.report.plan_sha256 != plan.plan_sha256
        or cover.report.source_manifest_sha256 != source.manifest_sha256
        or cover.report.transaction_report_sha256 != transaction.report_sha256
    ):
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event input bindings differ"
        )
    candidates = {
        item.request_sequence: item for item in transaction.report.candidates
    }
    cover_documents = tuple(
        item
        for item in cover.report.cover_documents
        if item.transaction_structure_state == "8k_item_2_01_candidate_scope"
        and item.resolution_state == "matched_in_source_lifecycle_window"
    )
    if len(cover_documents) != EXPECTED_DOCUMENT_COUNT:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event cover population differs"
        )
    decisions = tuple(
        _document_decision(
            candidate=candidates[item.request_sequence],
            identity_decision=item,
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in cover_documents
    )
    resolutions = Counter(item.resolution_state for item in decisions)
    rules = Counter(
        item.selected_decision_rule
        for item in decisions
        if item.selected_decision_rule is not None
    )
    profiles = Counter(item.scope_profile for item in decisions)
    relations = Counter(
        item.report_date_relation
        for item in decisions
        if item.report_date_relation is not None
    )
    event_dates = tuple(
        item.selected_event_date
        for item in decisions
        if item.selected_event_date is not None
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _fingerprint(
            {
                "rule_priority": [
                    "named_closing_date_in_introduction",
                    "closing_of_merger_date_in_introduction",
                    "dated_transaction_completion_statement",
                    "tender_acceptance_followed_by_effected_merger",
                ],
                "scope": "introduction_plus_item_2_01_excluding_intervening_items",
                "cover_report_date": "corroboration_only",
                "offer_expiration_date": "not_transaction_completion",
                "unique_highest_priority_date_required": True,
            }
        ),
        "plan_sha256": plan.plan_sha256,
        "source_manifest_sha256": source.manifest_sha256,
        "transaction_report_sha256": transaction.report_sha256,
        "transaction_logical_fingerprint": transaction.report.logical_fingerprint,
        "cover_adjudication_report_sha256": cover.report_sha256,
        "cover_adjudication_logical_fingerprint": cover.report.logical_fingerprint,
        "matched_event_count": resolutions["matched"],
        "ambiguous_event_count": resolutions["ambiguous"],
        "unsupported_event_count": resolutions["unsupported"],
        "resolution_state_counts": _ordered(resolutions),
        "decision_rule_counts": _ordered(rules),
        "scope_profile_counts": _ordered(profiles),
        "report_date_relation_counts": _ordered(relations),
        "report_date_difference_count": sum(
            key != "same_as_report_date" for key in relations.elements()
        ),
        "earliest_event_date": min(event_dates) if event_dates else None,
        "latest_event_date": max(event_dates) if event_dates else None,
        "decisions": decisions,
        "issuer_transaction_completion_evidence_count": resolutions["matched"],
    }
    provisional = StrongLeaderPullbackSecTransactionEventAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecTransactionEventAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_decision(
    *,
    candidate: SecTransactionDocumentCandidateV1,
    identity_decision: SecCoverDocumentIdentityDecisionV1,
    path: Path,
) -> SecTransactionEventDecisionV1:
    raw = path.read_bytes()
    if _sha256_bytes(raw) != candidate.document_sha256:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event source document identity differs"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event source document is not UTF-8"
        ) from exc
    parser = _DocumentParser()
    parser.feed(text)
    parser.close()
    normalized = _normalized_text(" ".join(parser.raw_parts))
    if (
        _sha256_bytes(normalized.encode("utf-8")) != candidate.normalized_text_sha256
        or len(normalized) != candidate.normalized_text_character_count
    ):
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event normalized source differs"
        )
    intro, item_two, scope_profile = _transaction_scope(tuple(parser.nodes))
    scope = _normalized_text(f"{intro} {item_two}")
    evidence = _completion_evidence(scope=scope, introduction=intro)
    dates = {item.event_date for item in evidence}
    if len(dates) == 1:
        state: ResolutionState = "matched"
        selected_date = next(iter(dates))
        selected_rule = evidence[0].decision_rule
        relation = _report_date_relation(selected_date, identity_decision.report_date)
        event_type = "merger_or_acquisition_completion"
        reasons = (
            "explicit_issuer_transaction_completion_statement",
            "highest_priority_rule_has_one_unique_date",
            "report_date_used_for_comparison_only",
        )
    elif dates:
        state = "ambiguous"
        selected_date = None
        selected_rule = None
        relation = None
        event_type = None
        reasons = (
            "highest_priority_rule_has_multiple_dates",
            "no_completion_date_selected",
        )
    else:
        state = "unsupported"
        selected_date = None
        selected_rule = None
        relation = None
        event_type = None
        reasons = (
            "no_registered_completion_statement_with_date",
            "no_completion_date_selected",
        )
    values = {
        "request_sequence": candidate.request_sequence,
        "instrument_id": candidate.instrument_id,
        "accession_number": candidate.accession_number,
        "filing_date": candidate.filing_date,
        "acceptance_datetime": candidate.acceptance_datetime,
        "document_sha256": candidate.document_sha256,
        "identity_decision_fingerprint": identity_decision.logical_fingerprint,
        "report_date": identity_decision.report_date,
        "scope_profile": scope_profile,
        "scope_character_count": len(scope),
        "scope_sha256": _sha256_bytes(scope.encode("utf-8")),
        "resolution_state": state,
        "completion_evidence": evidence,
        "selected_event_date": selected_date,
        "selected_decision_rule": selected_rule,
        "report_date_relation": relation,
        "issuer_event_type": event_type,
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = SecTransactionEventDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecTransactionEventDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _transaction_scope(nodes: tuple[str, ...]) -> tuple[str, str, ScopeProfile]:
    headings = tuple(
        (index, match.group(1))
        for index, node in enumerate(nodes)
        if (match := _ITEM_HEADING_RE.match(node)) is not None
    )
    item_two = tuple(index for index, code in headings if code == "2.01")
    if len(item_two) != 1:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event Item 2.01 structure differs"
        )
    item_start = item_two[0]
    item_end = next(
        (index for index, _ in headings if index > item_start), len(nodes)
    )
    note_starts = tuple(
        index
        for index, node in enumerate(nodes[:item_start])
        if _NOTE_HEADING_RE.fullmatch(node)
    )
    if note_starts:
        intro_start = note_starts[-1]
        intro_end = next(
            (index for index, _ in headings if index > intro_start), item_start
        )
        introduction = _normalized_text(" ".join(nodes[intro_start:intro_end]))
        profile: ScopeProfile = "explicit_intro_and_item_2_01"
    else:
        first_item = headings[0][0]
        implicit = tuple(
            node
            for node in nodes[:first_item]
            if _NAMED_CLOSING_DATE_RE.search(node)
            and _TERMINAL_TRANSACTION_RE.search(node)
        )
        introduction = _normalized_text(" ".join(implicit))
        profile = "implicit_pre_item_completion_and_item_2_01"
    item_text = _normalized_text(" ".join(nodes[item_start:item_end]))
    if not introduction or not item_text:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event bounded scope is unavailable"
        )
    return introduction, item_text, profile


def _completion_evidence(
    *, scope: str, introduction: str
) -> tuple[SecTransactionCompletionEvidenceV1, ...]:
    candidates = _pattern_evidence(
        scope=scope,
        scan_text=introduction,
        scan_offset=0,
        pattern=_NAMED_CLOSING_DATE_RE,
        rule="named_closing_date_in_introduction",
    )
    if not candidates:
        candidates = _pattern_evidence(
            scope=scope,
            scan_text=introduction,
            scan_offset=0,
            pattern=_CLOSING_OF_TRANSACTION_RE,
            rule="closing_of_merger_date_in_introduction",
        )
    if not candidates:
        candidates = _completion_statement_evidence(scope)
    if not candidates:
        candidates = _pattern_evidence(
            scope=scope,
            scan_text=introduction,
            scan_offset=0,
            pattern=_TENDER_TO_MERGER_RE,
            rule="tender_acceptance_followed_by_effected_merger",
        )
    deduplicated: dict[tuple[date, DecisionRule], SecTransactionCompletionEvidenceV1] = {}
    for item in candidates:
        deduplicated.setdefault((item.event_date, item.decision_rule), item)
    return tuple(
        sorted(
            deduplicated.values(),
            key=lambda item: (item.event_date, item.normalized_start),
        )
    )


def _completion_statement_evidence(
    scope: str,
) -> tuple[SecTransactionCompletionEvidenceV1, ...]:
    values = []
    for sentence_start, sentence_end in _semantic_sentence_spans(scope):
        sentence = scope[sentence_start:sentence_end]
        for terminal in _TERMINAL_TRANSACTION_RE.finditer(sentence):
            leading = tuple(_LEADING_DATE_RE.finditer(sentence[: terminal.start()]))
            if not leading:
                continue
            selected = leading[-1]
            values.append(
                _evidence(
                    scope=scope,
                    event_date=_parse_date_token(selected.group(1)),
                    rule="dated_transaction_completion_statement",
                    evidence_start=sentence_start + selected.start(),
                    evidence_end=sentence_start + terminal.end(),
                )
            )
    return tuple(values)


def _pattern_evidence(
    *,
    scope: str,
    scan_text: str,
    scan_offset: int,
    pattern: re.Pattern[str],
    rule: DecisionRule,
) -> tuple[SecTransactionCompletionEvidenceV1, ...]:
    return tuple(
        _evidence(
            scope=scope,
            event_date=_parse_date_token(match.group(1)),
            rule=rule,
            evidence_start=scan_offset + match.start(),
            evidence_end=scan_offset + match.end(),
        )
        for match in pattern.finditer(scan_text)
    )


def _evidence(
    *,
    scope: str,
    event_date: date,
    rule: DecisionRule,
    evidence_start: int,
    evidence_end: int,
) -> SecTransactionCompletionEvidenceV1:
    context_start = max(0, evidence_start - 240)
    context_end = min(len(scope), max(evidence_end + 1200, evidence_start + 600))
    if context_end - context_start > MAXIMUM_EVIDENCE_TEXT_CHARS:
        context_end = context_start + MAXIMUM_EVIDENCE_TEXT_CHARS
    raw_evidence = scope[context_start:context_end]
    leading_space_count = len(raw_evidence) - len(raw_evidence.lstrip())
    trailing_space_count = len(raw_evidence) - len(raw_evidence.rstrip())
    context_start += leading_space_count
    context_end -= trailing_space_count
    evidence_text = scope[context_start:context_end]
    values = {
        "event_date": event_date,
        "decision_rule": rule,
        "normalized_start": context_start,
        "normalized_end": context_end,
        "evidence_text": evidence_text,
        "evidence_sha256": _sha256_bytes(evidence_text.encode("utf-8")),
    }
    provisional = SecTransactionCompletionEvidenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecTransactionCompletionEvidenceV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _semantic_sentence_spans(text: str) -> tuple[tuple[int, int], ...]:
    starts = [0]
    starts.extend(match.end() for match in _SEMANTIC_BOUNDARY_RE.finditer(text))
    ends = starts[1:] + [len(text)]
    return tuple(zip(starts, ends, strict=True))


def _parse_date_token(value: str) -> date:
    normalized = re.sub(r"\s+,", ",", value.title())
    try:
        return datetime.strptime(normalized, "%B %d, %Y").date()
    except ValueError as exc:
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event date token is unsupported"
        ) from exc


def _report_date_relation(event_date: date, report_date: date) -> ReportDateRelation:
    if event_date < report_date:
        return "before_report_date"
    if event_date > report_date:
        return "after_report_date"
    return "same_as_report_date"


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecTransactionEventAdjudicationV1,
) -> StrongLeaderPullbackSecTransactionEventAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_transaction_event_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
                "existing transaction event report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event staging target exists"
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
    reread = read_strong_leader_pullback_sec_transaction_event_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecTransactionEventAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event paths must be absolute"
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
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event custody or target is unsafe"
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
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "transaction event file metadata differs"
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


def _ordered(counter: Counter[object]) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted((str(key), count) for key, count in counter.items() if count > 0)
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


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
        raise StrongLeaderPullbackSecTransactionEventAdjudicationError(
            "network access is prohibited during transaction event adjudication"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
