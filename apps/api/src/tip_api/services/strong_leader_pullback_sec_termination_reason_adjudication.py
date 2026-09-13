"""SEC listing-termination reason evidence for first-strategy cases."""

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
from tip_api.services.strong_leader_pullback_sec_transaction_event_adjudication import (
    SecTransactionEventDecisionV1,
    StrongLeaderPullbackSecTransactionEventAdjudicationResult,
    read_strong_leader_pullback_sec_transaction_event_adjudication,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-termination-reason-adjudication/1.0"
REPORT_FILE = "termination-reasons.json"
EXPECTED_CASE_COUNT = 61
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
MAXIMUM_SECTION_CHARS = 4096
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_ITEM_PREFIXES = (
    "entry into",
    "termination of",
    "completion of",
    "notice of",
    "material modification",
    "changes in",
    "departure of",
    "amendments to",
    "other events",
    "financial statements",
    "results of",
    "regulation fd",
    "submission of",
    "creation of",
    "change in",
    "mine safety",
)
_ITEM_HEADING_RE = re.compile(r"^(?:item\s+)?([0-9]+\.[0-9]{2})(.*)$", re.IGNORECASE)
_TRANSACTION_RE = re.compile(r"\b(?:mergers?|acquisition|transactions?)\b", re.IGNORECASE)
_COMPLETION_LINK_RE = re.compile(
    r"\b(?:consummat\w*|complet\w*|closing|as a result|in connection)\b",
    re.IGNORECASE,
)
_LISTING_ACTION_PATTERNS = (
    (
        "trading_halt",
        re.compile(r"\bhalt(?:ed|ing)?\s+(?:of\s+)?trading\b|\btrading\s+halt", re.IGNORECASE),
    ),
    (
        "trading_suspension",
        re.compile(
            r"\bsuspend(?:ed|ing|sion)?\s+(?:of\s+)?trading\b|"
            r"\btrading\s+(?:be\s+)?suspended\b",
            re.IGNORECASE,
        ),
    ),
    (
        "trading_ceased",
        re.compile(r"\b(?:stock|shares?)\s+ceased\s+trading\b", re.IGNORECASE),
    ),
    (
        "listing_withdrawal",
        re.compile(r"\bwithdraw[^.]{0,160}\bfrom listing\b", re.IGNORECASE),
    ),
    (
        "delisting",
        re.compile(r"\bdelist(?:ed|ing)?\b|\bremoval from listing\b", re.IGNORECASE),
    ),
    (
        "no_longer_listed",
        re.compile(r"\bno longer (?:be )?listed\b", re.IGNORECASE),
    ),
    (
        "form_25_request",
        re.compile(r"\bForm 25\b", re.IGNORECASE),
    ),
)

ResolutionState = Literal["matched", "ambiguous", "unsupported"]
ListingAction = Literal[
    "trading_halt",
    "trading_suspension",
    "trading_ceased",
    "listing_withdrawal",
    "delisting",
    "no_longer_listed",
    "form_25_request",
]


class StrongLeaderPullbackSecTerminationReasonAdjudicationError(RuntimeError):
    """Raised when SEC termination-reason evidence cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecTerminationReasonDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_event_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_completion_date: date
    item_3_01_title: str = Field(min_length=1, max_length=256)
    item_3_01_character_count: int = Field(ge=1, le=MAXIMUM_SECTION_CHARS)
    item_3_01_sha256: str = Field(pattern=_SHA256_PATTERN)
    item_3_01_text: str = Field(min_length=1, max_length=MAXIMUM_SECTION_CHARS)
    resolution_state: ResolutionState
    listing_actions: tuple[ListingAction, ...]
    termination_reason: Literal["merger_or_acquisition"] | None = None
    decision_rule: Literal["bounded_item_3_01_transaction_listing_link_v1"]
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("item_3_01_title", "item_3_01_text")
    @classmethod
    def text_is_normalized(cls, value: str) -> str:
        if value != _normalized_text(value):
            raise ValueError("termination reason text is not normalized")
        return value

    @field_validator("listing_actions", "decision_reasons", mode="before")
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("termination reason values differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "SecTerminationReasonDecisionV1":
        matched = self.resolution_state == "matched"
        if (
            self.item_3_01_character_count != len(self.item_3_01_text)
            or self.item_3_01_sha256
            != _sha256_bytes(self.item_3_01_text.encode("utf-8"))
            or (matched and self.termination_reason != "merger_or_acquisition")
            or (matched and not self.listing_actions)
            or (not matched and self.termination_reason is not None)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("termination reason decision differs")
        return self


class StrongLeaderPullbackSecTerminationReasonAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-termination-reason-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["listing_termination_reason_adjudicated"] = (
        "listing_termination_reason_adjudicated"
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
    lifecycle_case_count: Literal[61] = EXPECTED_CASE_COUNT
    matched_reason_count: int = Field(ge=0, le=61)
    ambiguous_reason_count: int = Field(ge=0, le=61)
    unsupported_reason_count: int = Field(ge=0, le=61)
    resolution_state_counts: tuple[tuple[str, int], ...]
    listing_action_counts: tuple[tuple[str, int], ...]
    decisions: tuple[SecTerminationReasonDecisionV1, ...]
    termination_reason_evidence_count: int = Field(ge=0, le=61)
    effective_delisting_date_count: Literal[0] = 0
    first_or_last_tradable_date_count: Literal[0] = 0
    consideration_adjudication_count: Literal[0] = 0
    party_relation_adjudication_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecTerminationReasonAdjudicationV1":
        resolutions = Counter(item.resolution_state for item in self.decisions)
        actions = Counter(
            action for item in self.decisions for action in item.listing_actions
        )
        if (
            len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or self.matched_reason_count != resolutions["matched"]
            or self.ambiguous_reason_count != resolutions["ambiguous"]
            or self.unsupported_reason_count != resolutions["unsupported"]
            or self.resolution_state_counts != _ordered(resolutions)
            or self.listing_action_counts != _ordered(actions)
            or self.termination_reason_evidence_count != self.matched_reason_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("termination reason adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecTerminationReasonAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackSecTerminationReasonAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


class _DocumentParser(HTMLParser):
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
        if self._skip_depth:
            return
        normalized = _normalized_text(data)
        if normalized:
            self.nodes.append(normalized)


def build_strong_leader_pullback_sec_termination_reason_adjudication(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    cover_adjudication_root: Path,
    cover_adjudication_custody_root: Path,
    transaction_event_root: Path,
    transaction_event_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecTerminationReasonAdjudicationResult:
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
        report = _build_report(
            plan=plan,
            source=source,
            cover=cover,
            events=events,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_termination_reason_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecTerminationReasonAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecTerminationReasonAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason report bytes are not canonical"
        )
    return StrongLeaderPullbackSecTerminationReasonAdjudicationResult(
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
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecTerminationReasonAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason revision is invalid"
        )
    if source.manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason source manifest is unavailable"
        )
    if (
        cover.report.plan_sha256 != plan.plan_sha256
        or cover.report.source_manifest_sha256 != source.manifest_sha256
        or events.report.plan_sha256 != plan.plan_sha256
        or events.report.source_manifest_sha256 != source.manifest_sha256
        or events.report.cover_adjudication_report_sha256 != cover.report_sha256
        or events.report.matched_event_count != EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason input bindings differ"
        )
    covers = {
        item.request_sequence: item
        for item in cover.report.cover_documents
        if item.resolution_state == "matched_in_source_lifecycle_window"
        and item.transaction_structure_state == "8k_item_2_01_candidate_scope"
    }
    decisions = tuple(
        _document_decision(
            event=item,
            identity=covers[item.request_sequence],
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in events.report.decisions
    )
    resolutions = Counter(item.resolution_state for item in decisions)
    actions = Counter(
        action for item in decisions for action in item.listing_actions
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _fingerprint(
            {
                "registered_rule": "bounded_item_3_01_transaction_listing_link_v1",
                "required_section": "unique_item_3_01",
                "required_markers": [
                    "transaction_or_acquisition",
                    "completion_or_causal_link",
                    "listing_or_trading_action",
                ],
                "effective_date": "not_adjudicated",
                "last_tradable_date": "not_adjudicated",
            }
        ),
        "plan_sha256": plan.plan_sha256,
        "source_manifest_sha256": source.manifest_sha256,
        "cover_adjudication_report_sha256": cover.report_sha256,
        "cover_adjudication_logical_fingerprint": cover.report.logical_fingerprint,
        "transaction_event_report_sha256": events.report_sha256,
        "transaction_event_logical_fingerprint": events.report.logical_fingerprint,
        "matched_reason_count": resolutions["matched"],
        "ambiguous_reason_count": resolutions["ambiguous"],
        "unsupported_reason_count": resolutions["unsupported"],
        "resolution_state_counts": _ordered(resolutions),
        "listing_action_counts": _ordered(actions),
        "decisions": decisions,
        "termination_reason_evidence_count": resolutions["matched"],
    }
    provisional = StrongLeaderPullbackSecTerminationReasonAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecTerminationReasonAdjudicationV1.model_validate(
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
    path: Path,
) -> SecTerminationReasonDecisionV1:
    raw = path.read_bytes()
    if (
        _sha256_bytes(raw) != event.document_sha256
        or event.document_sha256 != identity.document_sha256
        or event.instrument_id != identity.instrument_id
        or event.selected_event_date is None
    ):
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason source or event identity differs"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason source document is not UTF-8"
        ) from exc
    parser = _DocumentParser()
    parser.feed(text)
    parser.close()
    sections = _item_sections(tuple(parser.nodes), "3.01")
    if len(sections) == 1:
        title, section = sections[0]
        actions = _listing_actions(section)
        matched = (
            "notice of delisting" in title.lower()
            and _TRANSACTION_RE.search(section) is not None
            and _COMPLETION_LINK_RE.search(section) is not None
            and bool(actions)
        )
        state: ResolutionState = "matched" if matched else "unsupported"
        reason = "merger_or_acquisition" if matched else None
        reasons = (
            (
                "bounded_item_3_01_links_transaction_to_listing_action",
                "common_equity_document_identity_previously_matched",
                "effective_and_last_tradable_dates_not_inferred",
            )
            if matched
            else ("item_3_01_lacks_registered_causal_markers",)
        )
    elif sections:
        state = "ambiguous"
        title = "multiple_item_3_01_sections"
        section = " ".join(value for _, value in sections)
        actions = _listing_actions(section)
        reason = None
        reasons = ("multiple_item_3_01_sections",)
    else:
        state = "unsupported"
        title = "item_3_01_unavailable"
        section = "item_3_01_unavailable"
        actions = ()
        reason = None
        reasons = ("item_3_01_unavailable",)
    if len(section) > MAXIMUM_SECTION_CHARS:
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason Item 3.01 exceeds bounded size"
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
        "transaction_completion_date": event.selected_event_date,
        "item_3_01_title": title,
        "item_3_01_character_count": len(section),
        "item_3_01_sha256": _sha256_bytes(section.encode("utf-8")),
        "item_3_01_text": section,
        "resolution_state": state,
        "listing_actions": actions,
        "termination_reason": reason,
        "decision_rule": "bounded_item_3_01_transaction_listing_link_v1",
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = SecTerminationReasonDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecTerminationReasonDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _item_sections(
    nodes: tuple[str, ...], code: str
) -> tuple[tuple[str, str], ...]:
    headings = _section_headings(nodes)
    matches = []
    for position, (start, heading_code, title) in enumerate(headings):
        if heading_code != code:
            continue
        end = headings[position + 1][0] if position + 1 < len(headings) else len(nodes)
        effective_title = title
        if not effective_title and start + 1 < end:
            effective_title = nodes[start + 1]
        section = _normalized_text(" ".join(nodes[start:end]))
        matches.append((_normalized_text(effective_title), section))
    return tuple(matches)


def _section_headings(nodes: tuple[str, ...]) -> tuple[tuple[int, str, str], ...]:
    values = []
    for index, node in enumerate(nodes):
        match = _ITEM_HEADING_RE.match(node)
        if match is None:
            continue
        raw_tail = match.group(2).lstrip()
        if raw_tail.startswith(","):
            continue
        title = raw_tail.lstrip(". ")
        if not title or title.lower().startswith(_ITEM_PREFIXES):
            values.append((index, match.group(1), title))
    return tuple(values)


def _listing_actions(text: str) -> tuple[ListingAction, ...]:
    return tuple(
        sorted(
            action
            for action, pattern in _LISTING_ACTION_PATTERNS
            if pattern.search(text) is not None
        )
    )  # type: ignore[return-value]


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecTerminationReasonAdjudicationV1,
) -> StrongLeaderPullbackSecTerminationReasonAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_termination_reason_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
                "existing termination reason report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason staging target exists"
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
    reread = read_strong_leader_pullback_sec_termination_reason_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecTerminationReasonAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason paths must be absolute"
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
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason custody or target is unsafe"
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
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "termination reason file metadata differs"
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
        raise StrongLeaderPullbackSecTerminationReasonAdjudicationError(
            "network access is prohibited during termination reason adjudication"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
