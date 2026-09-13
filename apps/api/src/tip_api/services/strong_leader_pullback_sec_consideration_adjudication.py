"""Typed common-share consideration evidence for first-strategy SEC cases."""

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
from tip_api.services.strong_leader_pullback_sec_termination_reason_adjudication import (
    SecTerminationReasonDecisionV1,
    StrongLeaderPullbackSecTerminationReasonAdjudicationResult,
    read_strong_leader_pullback_sec_termination_reason_adjudication,
)
from tip_api.services.strong_leader_pullback_sec_transaction_event_adjudication import (
    SecTransactionEventDecisionV1,
    StrongLeaderPullbackSecTransactionEventAdjudicationResult,
    _DocumentParser,
    _transaction_scope,
    read_strong_leader_pullback_sec_transaction_event_adjudication,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-consideration-adjudication/1.0"
REPORT_FILE = "consideration.json"
EXPECTED_CASE_COUNT = 61
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 4096
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_CLAUSE_BOUNDARY_RE = re.compile(
    r"(?<=[.!?])\s+(?=(?:On|Pursuant|Item|ITEM|Effective|The|This|In|As|"
    r"Following|Immediately|Capitalized|At|After|Subject|Except|Promptly|"
    r"Furthermore|Additionally|Holders|Treatment)\b)|\s+[•·]\s+"
)
_TENDER_OFFER_RE = re.compile(r"\btender offer\b", re.IGNORECASE)
_TENDER_SHARE_RE = re.compile(
    r"\b(?:all|any and all)\s+of\s+the\s+(?:issued\s+and\s+)?outstanding\s+"
    r"shares?\b",
    re.IGNORECASE,
)
_ORDINARY_SHARE_RE = re.compile(
    r"\beach(?:\s+of\s+the[^,;]{0,140})?\s+"
    r"(?:(?:issued|outstanding)\s+and\s+)?"
    r"(?:issued\s+|outstanding\s+)?(?:common\s+)?shares?\b",
    re.IGNORECASE,
)
_TRANSFER_RE = re.compile(
    r"\b(?:convert(?:ed|s|ing)?|exchangeable)\b[^.]{0,900}"
    r"\b(?:right to receive|in exchange for)\b",
    re.IGNORECASE,
)
_FRACTIONAL_CASH_RE = re.compile(
    r"\bcash(?:\s*\([^)]*\))?[^.;]{0,120}\bin lieu of\s+"
    r"(?:any |such )?fractional\s+(?:share|shares)\b",
    re.IGNORECASE,
)
_CASH_TERM_RE = re.compile(
    r"(?:\$[0-9][0-9,.]*(?:\s+per\s+(?:share|common share))?[^.;]{0,90}\bin cash\b|"
    r"\bcash\s+(?:in\s+(?:an|the)\s+amount|amount|consideration|election)|"
    r"\bamount\s+in\s+cash\b|\bin\s+cash\s+equal\s+to\s+\$|"
    r"\bclosing amount\b[^.;]{0,160}\bin cash\b)",
    re.IGNORECASE,
)
_LISTED_EQUITY_TERM_RE = re.compile(
    r"(?:\bexchange ratio\b|\bstock consideration\b|"
    r"\b(?:[0-9]+(?:\.[0-9]+)?|one)\s+(?!per\b)"
    r"(?:\([^)]{0,120}\)\s+)?"
    r"(?:fully paid and nonassessable\s+|newly issued\s+)?"
    r"(?:[A-Za-z0-9’'&.-]+\s+){0,3}(?:common\s+shares|shares\s+of)\b)",
    re.IGNORECASE,
)
_CVR_TERM_RE = re.compile(r"\bcontingent value right\b|\bCVR\b", re.IGNORECASE)
_ELECTION_RE = re.compile(
    r"\bat the election of the holder\b|\belection consideration\b|"
    r"\bcash election\b|\bstock election\b|\belection mechanics\b",
    re.IGNORECASE,
)
_UNLISTED_UNIT_RE = re.compile(
    r"\bunlisted\b[^.;]{0,120}\b(?:unit|units)\b|"
    r"\b(?:unit|units)\b[^.;]{0,120}\bunlisted\b",
    re.IGNORECASE,
)

ResolutionState = Literal["matched", "ambiguous", "unsupported"]
ConsiderationStructure = Literal[
    "cash_only",
    "stock_only",
    "fixed_cash_and_stock",
    "cash_plus_contingent_value_right",
    "holder_election_cash_or_stock",
    "holder_election_cash_or_cash_plus_unlisted_unit",
]
ConsiderationComponent = Literal[
    "cash",
    "contingent_value_right",
    "listed_equity",
    "unlisted_equity_unit",
]
DecisionRule = Literal[
    "tender_offer_common_share_terms_v1",
    "merger_conversion_common_share_terms_v1",
]


class StrongLeaderPullbackSecConsiderationAdjudicationError(RuntimeError):
    """Raised when common-share consideration evidence cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCommonShareConsiderationDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_event_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_completion_date: date
    transaction_scope_sha256: str = Field(pattern=_SHA256_PATTERN)
    resolution_state: ResolutionState
    decision_rule: DecisionRule | None = None
    consideration_structure: ConsiderationStructure | None = None
    consideration_components: tuple[ConsiderationComponent, ...]
    holder_election: bool
    fractional_share_cash_adjustment: bool
    evidence_start: int | None = Field(default=None, ge=0)
    evidence_end: int | None = Field(default=None, ge=1)
    evidence_text: str | None = Field(
        default=None, min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS
    )
    evidence_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str | None) -> str | None:
        if value is not None and value != _normalized_text(value):
            raise ValueError("consideration evidence is not normalized")
        return value

    @field_validator("consideration_components", "decision_reasons", mode="before")
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("consideration values differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "SecCommonShareConsiderationDecisionV1":
        matched = self.resolution_state == "matched"
        evidence_present = all(
            value is not None
            for value in (
                self.evidence_start,
                self.evidence_end,
                self.evidence_text,
                self.evidence_sha256,
            )
        )
        expected_hash = (
            _sha256_bytes(self.evidence_text.encode("utf-8"))
            if self.evidence_text is not None
            else None
        )
        if (
            (matched and not evidence_present)
            or (matched and self.decision_rule is None)
            or (matched and self.consideration_structure is None)
            or (matched and not self.consideration_components)
            or (not matched and evidence_present)
            or (not matched and self.decision_rule is not None)
            or (not matched and self.consideration_structure is not None)
            or (not matched and self.consideration_components)
            or self.evidence_sha256 != expected_hash
            or (
                evidence_present
                and self.evidence_end is not None
                and self.evidence_start is not None
                and self.evidence_end <= self.evidence_start
            )
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("consideration decision differs")
        return self


class StrongLeaderPullbackSecConsiderationAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-consideration-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["common_share_consideration_adjudicated"] = (
        "common_share_consideration_adjudicated"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    cover_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cover_adjudication_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_event_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_event_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[61] = EXPECTED_CASE_COUNT
    matched_consideration_count: int = Field(ge=0, le=61)
    ambiguous_consideration_count: int = Field(ge=0, le=61)
    unsupported_consideration_count: int = Field(ge=0, le=61)
    resolution_state_counts: tuple[tuple[str, int], ...]
    consideration_structure_counts: tuple[tuple[str, int], ...]
    consideration_component_counts: tuple[tuple[str, int], ...]
    holder_election_count: int = Field(ge=0, le=61)
    fractional_share_cash_adjustment_count: int = Field(ge=0, le=61)
    decisions: tuple[SecCommonShareConsiderationDecisionV1, ...]
    common_share_consideration_evidence_count: int = Field(ge=0, le=61)
    normalized_payoff_term_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecConsiderationAdjudicationV1":
        resolutions = Counter(item.resolution_state for item in self.decisions)
        structures = Counter(
            item.consideration_structure
            for item in self.decisions
            if item.consideration_structure is not None
        )
        components = Counter(
            component
            for item in self.decisions
            for component in item.consideration_components
        )
        if (
            len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or self.matched_consideration_count != resolutions["matched"]
            or self.ambiguous_consideration_count != resolutions["ambiguous"]
            or self.unsupported_consideration_count != resolutions["unsupported"]
            or self.resolution_state_counts != _ordered(resolutions)
            or self.consideration_structure_counts != _ordered(structures)
            or self.consideration_component_counts != _ordered(components)
            or self.holder_election_count
            != sum(item.holder_election for item in self.decisions)
            or self.fractional_share_cash_adjustment_count
            != sum(item.fractional_share_cash_adjustment for item in self.decisions)
            or self.common_share_consideration_evidence_count
            != self.matched_consideration_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("consideration adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecConsiderationAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackSecConsiderationAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_sec_consideration_adjudication(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    cover_adjudication_root: Path,
    cover_adjudication_custody_root: Path,
    transaction_event_root: Path,
    transaction_event_custody_root: Path,
    termination_reason_root: Path,
    termination_reason_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecConsiderationAdjudicationResult:
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
        cover = read_strong_leader_pullback_sec_case_adjudication(
            output_root=cover_adjudication_root,
            output_custody_root=cover_adjudication_custody_root,
        )
        events = read_strong_leader_pullback_sec_transaction_event_adjudication(
            output_root=transaction_event_root,
            output_custody_root=transaction_event_custody_root,
        )
        reasons = read_strong_leader_pullback_sec_termination_reason_adjudication(
            output_root=termination_reason_root,
            output_custody_root=termination_reason_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            cover=cover,
            events=events,
            reasons=reasons,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_consideration_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecConsiderationAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecConsiderationAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration report bytes are not canonical"
        )
    return StrongLeaderPullbackSecConsiderationAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    source: StrongLeaderPullbackSecDocumentSourceResult,
    cover: StrongLeaderPullbackSecCaseAdjudicationResult,
    events: StrongLeaderPullbackSecTransactionEventAdjudicationResult,
    reasons: StrongLeaderPullbackSecTerminationReasonAdjudicationResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecConsiderationAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration revision is invalid"
        )
    if source.manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration source manifest is unavailable"
        )
    if (
        cover.report.plan_sha256 != plan.plan_sha256
        or cover.report.source_manifest_sha256 != source.manifest_sha256
        or events.report.plan_sha256 != plan.plan_sha256
        or events.report.source_manifest_sha256 != source.manifest_sha256
        or events.report.cover_adjudication_report_sha256 != cover.report_sha256
        or reasons.report.plan_sha256 != plan.plan_sha256
        or reasons.report.source_manifest_sha256 != source.manifest_sha256
        or reasons.report.cover_adjudication_report_sha256 != cover.report_sha256
        or reasons.report.transaction_event_report_sha256 != events.report_sha256
        or events.report.matched_event_count != EXPECTED_CASE_COUNT
        or reasons.report.matched_reason_count != EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration input bindings differ"
        )
    covers = {
        item.request_sequence: item
        for item in cover.report.cover_documents
        if item.resolution_state == "matched_in_source_lifecycle_window"
        and item.transaction_structure_state == "8k_item_2_01_candidate_scope"
    }
    termination_decisions = {
        item.request_sequence: item for item in reasons.report.decisions
    }
    decisions = tuple(
        _document_decision(
            event=item,
            identity=covers[item.request_sequence],
            termination=termination_decisions[item.request_sequence],
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in events.report.decisions
    )
    resolutions = Counter(item.resolution_state for item in decisions)
    structures = Counter(
        item.consideration_structure
        for item in decisions
        if item.consideration_structure is not None
    )
    components = Counter(
        component for item in decisions for component in item.consideration_components
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _fingerprint(
            {
                "scope": "previously_bound_introduction_plus_item_2_01",
                "priority": [
                    "tender_offer_common_share_terms_v1",
                    "merger_conversion_common_share_terms_v1",
                ],
                "subject": "issued_or_outstanding_ordinary_common_shares",
                "excluded_subjects": [
                    "options",
                    "restricted_stock",
                    "restricted_stock_units",
                    "performance_awards",
                    "preferred_stock",
                    "debt",
                ],
                "fractional_share_cash": "adjustment_not_cash_component",
                "numeric_payoff_normalization": "not_adjudicated",
                "terminal_outcome": "not_adjudicated",
            }
        ),
        "plan_sha256": plan.plan_sha256,
        "source_manifest_sha256": source.manifest_sha256,
        "cover_adjudication_report_sha256": cover.report_sha256,
        "cover_adjudication_logical_fingerprint": cover.report.logical_fingerprint,
        "transaction_event_report_sha256": events.report_sha256,
        "transaction_event_logical_fingerprint": events.report.logical_fingerprint,
        "termination_reason_report_sha256": reasons.report_sha256,
        "termination_reason_logical_fingerprint": reasons.report.logical_fingerprint,
        "matched_consideration_count": resolutions["matched"],
        "ambiguous_consideration_count": resolutions["ambiguous"],
        "unsupported_consideration_count": resolutions["unsupported"],
        "resolution_state_counts": _ordered(resolutions),
        "consideration_structure_counts": _ordered(structures),
        "consideration_component_counts": _ordered(components),
        "holder_election_count": sum(item.holder_election for item in decisions),
        "fractional_share_cash_adjustment_count": sum(
            item.fractional_share_cash_adjustment for item in decisions
        ),
        "decisions": decisions,
        "common_share_consideration_evidence_count": resolutions["matched"],
    }
    provisional = StrongLeaderPullbackSecConsiderationAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecConsiderationAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_decision(
    *,
    event: SecTransactionEventDecisionV1,
    identity: SecCoverDocumentIdentityDecisionV1,
    termination: SecTerminationReasonDecisionV1,
    path: Path,
) -> SecCommonShareConsiderationDecisionV1:
    raw = path.read_bytes()
    if (
        _sha256_bytes(raw) != event.document_sha256
        or event.document_sha256 != identity.document_sha256
        or event.document_sha256 != termination.document_sha256
        or event.instrument_id != identity.instrument_id
        or event.instrument_id != termination.instrument_id
        or termination.transaction_event_fingerprint != event.logical_fingerprint
        or event.selected_event_date is None
        or termination.resolution_state != "matched"
    ):
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration source or prior decision identity differs"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration source document is not UTF-8"
        ) from exc
    parser = _DocumentParser()
    parser.feed(text)
    parser.close()
    introduction, item_two, _ = _transaction_scope(tuple(parser.nodes))
    scope = _normalized_text(f"{introduction} {item_two}")
    scope_sha256 = _sha256_bytes(scope.encode("utf-8"))
    if (
        len(scope) != event.scope_character_count
        or scope_sha256 != event.scope_sha256
    ):
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration transaction scope differs"
        )
    candidate = _primary_consideration_candidate(scope)
    if candidate is None:
        state: ResolutionState = "unsupported"
        rule = None
        structure = None
        components: tuple[ConsiderationComponent, ...] = ()
        election = False
        fractional = False
        evidence_start = None
        evidence_end = None
        evidence_text = None
        evidence_sha256 = None
        decision_reasons = (
            "no_registered_primary_common_share_consideration_clause",
        )
    else:
        evidence_start, evidence_end, evidence_text, rule = candidate
        classified = _classify_consideration(evidence_text)
        if classified is None:
            state = "unsupported"
            rule = None
            structure = None
            components = ()
            election = False
            fractional = False
            evidence_start = None
            evidence_end = None
            evidence_text = None
            evidence_sha256 = None
            decision_reasons = (
                "primary_clause_has_unregistered_consideration_structure",
            )
        else:
            structure, components, election, fractional = classified
            state = "matched"
            evidence_sha256 = _sha256_bytes(evidence_text.encode("utf-8"))
            decision_reasons = (
                "bounded_primary_common_share_clause",
                "cash_in_lieu_of_fractional_shares_is_not_main_cash_component",
                "numeric_payoff_terms_retained_in_evidence_not_normalized",
                "options_awards_preferred_stock_and_debt_excluded",
            )
    values = {
        "request_sequence": event.request_sequence,
        "instrument_id": event.instrument_id,
        "accession_number": event.accession_number,
        "filing_date": event.filing_date,
        "acceptance_datetime": event.acceptance_datetime,
        "document_sha256": event.document_sha256,
        "identity_decision_fingerprint": identity.logical_fingerprint,
        "transaction_event_fingerprint": event.logical_fingerprint,
        "termination_reason_fingerprint": termination.logical_fingerprint,
        "transaction_completion_date": event.selected_event_date,
        "transaction_scope_sha256": scope_sha256,
        "resolution_state": state,
        "decision_rule": rule,
        "consideration_structure": structure,
        "consideration_components": tuple(sorted(components)),
        "holder_election": election,
        "fractional_share_cash_adjustment": fractional,
        "evidence_start": evidence_start,
        "evidence_end": evidence_end,
        "evidence_text": evidence_text,
        "evidence_sha256": evidence_sha256,
        "decision_reasons": tuple(sorted(decision_reasons)),
    }
    provisional = SecCommonShareConsiderationDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCommonShareConsiderationDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _primary_consideration_candidate(
    scope: str,
) -> tuple[int, int, str, DecisionRule] | None:
    clauses = _clause_spans(scope)
    tender = tuple(
        (start, end, text, "tender_offer_common_share_terms_v1")
        for start, end, text in clauses
        if _TENDER_OFFER_RE.search(text)
        and _TENDER_SHARE_RE.search(text)
        and re.search(r"\b(?:purchase|acquire)\w*\b", text, re.IGNORECASE)
        and ("$" in text or "in exchange for" in text.lower())
    )
    if tender:
        selected = tender[0]
        if len(selected[2]) > MAXIMUM_EVIDENCE_TEXT_CHARS:
            raise StrongLeaderPullbackSecConsiderationAdjudicationError(
                "selected tender consideration clause exceeds bounded size"
            )
        return selected  # type: ignore[return-value]
    conversion = tuple(
        (start, end, text, "merger_conversion_common_share_terms_v1")
        for start, end, text in clauses
        if _ORDINARY_SHARE_RE.search(text) and _TRANSFER_RE.search(text)
    )
    if not conversion:
        return None
    selected = conversion[0]
    if len(selected[2]) > MAXIMUM_EVIDENCE_TEXT_CHARS:
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "selected merger consideration clause exceeds bounded size"
        )
    return selected  # type: ignore[return-value]


def _clause_spans(text: str) -> tuple[tuple[int, int, str], ...]:
    starts = [0]
    starts.extend(match.end() for match in _CLAUSE_BOUNDARY_RE.finditer(text))
    ends = [match.start() for match in _CLAUSE_BOUNDARY_RE.finditer(text)] + [len(text)]
    values = []
    for start, end in zip(starts, ends, strict=True):
        raw = text[start:end]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw) - len(raw.rstrip())
        start += leading
        end -= trailing
        if start < end:
            value = text[start:end]
            values.append((start, end, value))
    return tuple(values)


def _classify_consideration(
    evidence: str,
) -> tuple[
    ConsiderationStructure,
    tuple[ConsiderationComponent, ...],
    bool,
    bool,
] | None:
    fractional = _FRACTIONAL_CASH_RE.search(evidence) is not None
    economic = _FRACTIONAL_CASH_RE.sub("", evidence)
    election = _ELECTION_RE.search(economic) is not None
    has_cvr = _CVR_TERM_RE.search(economic) is not None
    has_unlisted_unit = _UNLISTED_UNIT_RE.search(economic) is not None
    has_listed_equity = _LISTED_EQUITY_TERM_RE.search(economic) is not None
    has_cash = _CASH_TERM_RE.search(economic) is not None
    components = []
    if has_cash:
        components.append("cash")
    if has_cvr:
        components.append("contingent_value_right")
    if has_listed_equity:
        components.append("listed_equity")
    if has_unlisted_unit:
        components.append("unlisted_equity_unit")
    if election and has_cash and has_unlisted_unit:
        structure: ConsiderationStructure = (
            "holder_election_cash_or_cash_plus_unlisted_unit"
        )
    elif election and has_cash and has_listed_equity:
        structure = "holder_election_cash_or_stock"
    elif has_cash and has_cvr and not has_listed_equity and not has_unlisted_unit:
        structure = "cash_plus_contingent_value_right"
    elif has_cash and has_listed_equity and not has_cvr and not has_unlisted_unit:
        structure = "fixed_cash_and_stock"
    elif has_listed_equity and not has_cash and not has_cvr and not has_unlisted_unit:
        structure = "stock_only"
    elif has_cash and not has_listed_equity and not has_cvr and not has_unlisted_unit:
        structure = "cash_only"
    else:
        return None
    return structure, tuple(components), election, fractional  # type: ignore[return-value]


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecConsiderationAdjudicationV1,
) -> StrongLeaderPullbackSecConsiderationAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_consideration_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecConsiderationAdjudicationError(
                "existing consideration report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration staging target exists"
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
    reread = read_strong_leader_pullback_sec_consideration_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecConsiderationAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration paths must be absolute"
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
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration custody or target is unsafe"
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
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "consideration file metadata differs"
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
        raise StrongLeaderPullbackSecConsiderationAdjudicationError(
            "network access is prohibited during consideration adjudication"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
