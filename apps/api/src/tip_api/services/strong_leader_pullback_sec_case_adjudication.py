"""Point-in-time SEC cover adjudication for first-strategy lifecycle cases."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import unicodedata
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.security_classification.v1 import (
    SecEvidenceResolutionStatus,
)
from tip_api.providers.sec.issuer_evidence import SecIdentityRecord, SecIdentityResolver
from tip_api.services.strong_leader_pullback_sec_case_coverage_census import (
    SecLifecycleCaseCoverageV1,
    StrongLeaderPullbackSecCaseCoverageCensusResult,
    read_strong_leader_pullback_sec_case_coverage_census,
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
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    LIFECYCLE_REQUIRED_FIELDS,
    LifecycleSourceAcceptanceCaseV1,
    StrongLeaderPullbackSourceAcceptanceSampleResult,
    read_strong_leader_pullback_source_acceptance_sample,
)


CONTRACT_VERSION = "strong-leader-pullback-sec-case-adjudication/1.0"
REPORT_FILE = "adjudication.json"
EXPECTED_CASE_COUNT = 64
EXPECTED_8K_DOCUMENT_COUNT = 62
EXPECTED_MATCHED_DOCUMENT_COUNT = 61
EXPECTED_MATCHED_CASE_COUNT = 61
EXPECTED_SECURITY_ROW_COUNT = 70
EXPECTED_INCOMPLETE_SECURITY_CONTEXT_COUNT = 1
EXPECTED_TOTAL_FIELD_COUNT = 512
EXPECTED_MATCHED_FIELD_COUNT = 61
EXPECTED_UNSUPPORTED_FIELD_COUNT = 451
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_REGISTERED_RULE = "point_in_time_inline_xbrl_cover_identity_v1"
_COVER_FACTS = frozenset(
    {
        "dei:DocumentPeriodEndDate",
        "dei:EntityCentralIndexKey",
        "dei:EntityRegistrantName",
        "dei:Security12bTitle",
        "dei:SecurityExchangeName",
        "dei:TradingSymbol",
    }
)
_SECURITY_FACTS = (
    "dei:Security12bTitle",
    "dei:TradingSymbol",
    "dei:SecurityExchangeName",
)
_COMMON_EQUITY_RE = re.compile(
    r"\b(?:class\s+[a-z]\s+)?common\s+(?:stock|shares?)\b",
    re.IGNORECASE,
)

AdjudicationState = Literal[
    "matched",
    "absent",
    "referenced_only",
    "unsupported",
    "ambiguous",
    "conflicting",
    "irrelevant",
]
CoverResolutionState = Literal[
    "matched_in_source_lifecycle_window",
    "outside_source_lifecycle_window",
    "unsupported_cover",
    "ambiguous_cover",
    "conflicting_cover",
]
SecurityFormScope = Literal["common_equity", "other_security"]


class StrongLeaderPullbackSecCaseAdjudicationError(RuntimeError):
    """Raised when the bounded SEC case adjudication cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecCoverSecurityRowV1(_FrozenModel):
    context_ref: str = Field(min_length=1, max_length=256)
    security_title: str = Field(min_length=1, max_length=500)
    trading_symbol: str = Field(min_length=1, max_length=64)
    exchange_name: str = Field(min_length=1, max_length=256)
    exchange_mic: Literal["XNAS", "XNYS"]
    security_form_scope: SecurityFormScope
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator(
        "context_ref", "security_title", "trading_symbol", "exchange_name"
    )
    @classmethod
    def text_is_normalized(cls, value: str) -> str:
        if value != " ".join(value.split()):
            raise ValueError("SEC cover security text is not normalized")
        return value

    @model_validator(mode="after")
    def row_reconciles(self) -> "SecCoverSecurityRowV1":
        if (
            self.exchange_mic != _exchange_mic(self.exchange_name)
            or self.security_form_scope != _security_form_scope(self.security_title)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("SEC cover security row differs")
        return self


class SecCoverIncompleteSecurityContextV1(_FrozenModel):
    context_ref: str = Field(min_length=1, max_length=256)
    security_titles: tuple[str, ...]
    trading_symbols: tuple[str, ...]
    exchange_names: tuple[str, ...]
    disposition: Literal["incomplete_non_target_cover_context"] = (
        "incomplete_non_target_cover_context"
    )
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator(
        "security_titles", "trading_symbols", "exchange_names", mode="before"
    )
    @classmethod
    def values_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("SEC incomplete cover values differ")
        return values

    @model_validator(mode="after")
    def context_reconciles(self) -> "SecCoverIncompleteSecurityContextV1":
        if (
            set(self.security_titles)
            and any(
                _security_form_scope(value) == "common_equity"
                for value in self.security_titles
            )
        ) or self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("SEC incomplete cover context differs")
        return self


class SecCoverDocumentIdentityDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_structure_state: str
    report_date: date
    issuer_cik: str = Field(pattern=r"^[0-9]{10}$")
    registrant_name_candidates: tuple[str, ...] = Field(min_length=1)
    security_rows: tuple[SecCoverSecurityRowV1, ...] = Field(min_length=1)
    incomplete_security_contexts: tuple[SecCoverIncompleteSecurityContextV1, ...]
    source_ticker: str = Field(min_length=1, max_length=64)
    source_exchange_mic: Literal["XNAS", "XNYS"]
    source_share_class_figi: str = Field(pattern=r"^BBG[0-9A-Z]{9}$")
    resolution_state: CoverResolutionState
    matched_row_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("registrant_name_candidates", "decision_reasons", mode="before")
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if not values or values != tuple(sorted(set(values))):
            raise ValueError("SEC cover decision values differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "SecCoverDocumentIdentityDecisionV1":
        matching = tuple(
            item
            for item in self.security_rows
            if item.trading_symbol.upper() == self.source_ticker.upper()
            and item.exchange_mic == self.source_exchange_mic
            and item.security_form_scope == "common_equity"
        )
        matched = self.resolution_state == "matched_in_source_lifecycle_window"
        if (
            (matched and len(matching) != 1)
            or (matched and self.matched_row_fingerprint != matching[0].logical_fingerprint)
            or (not matched and self.matched_row_fingerprint is not None)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("SEC cover identity decision differs")
        return self


class SecCaseFieldAdjudicationV1(_FrozenModel):
    field_name: str
    result_state: AdjudicationState
    decision_rule: str
    evidence_document_sequences: tuple[int, ...]
    evidence_fingerprints: tuple[str, ...]
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    matched_value_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )

    @field_validator(
        "evidence_document_sequences",
        "evidence_fingerprints",
        "decision_reasons",
        mode="before",
    )
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("SEC field adjudication values differ")
        return values

    @model_validator(mode="after")
    def result_reconciles(self) -> "SecCaseFieldAdjudicationV1":
        matched = self.result_state == "matched"
        if (
            self.field_name not in LIFECYCLE_REQUIRED_FIELDS
            or (matched and not self.evidence_document_sequences)
            or len(self.evidence_document_sequences) != len(self.evidence_fingerprints)
            or (matched and self.matched_value_fingerprint is None)
            or (not matched and self.matched_value_fingerprint is not None)
        ):
            raise ValueError("SEC field adjudication result differs")
        return self


class SecLifecycleCaseAdjudicationV1(_FrozenModel):
    instrument_id: UUID
    source_case_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    coverage_case_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    evidence_profile: str
    cover_document_sequences: tuple[int, ...]
    cover_resolution_counts: tuple[tuple[str, int], ...]
    field_results: tuple[SecCaseFieldAdjudicationV1, ...]
    adjudicated_field_count: int = Field(ge=0, le=8)
    matched_field_count: int = Field(ge=0, le=8)
    unsupported_field_count: int = Field(ge=0, le=8)
    lifecycle_fact_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("cover_document_sequences", mode="before")
    @classmethod
    def sequences_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("SEC case cover sequences differ")
        return values

    @model_validator(mode="after")
    def case_reconciles(self) -> "SecLifecycleCaseAdjudicationV1":
        states = Counter(item.result_state for item in self.field_results)
        if (
            tuple(item.field_name for item in self.field_results)
            != LIFECYCLE_REQUIRED_FIELDS
            or self.adjudicated_field_count != len(self.field_results) - states["unsupported"]
            or self.matched_field_count != states["matched"]
            or self.unsupported_field_count != states["unsupported"]
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("SEC lifecycle case adjudication differs")
        return self


class StrongLeaderPullbackSecCaseAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-case-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "cover_identity_adjudicated_remaining_fields_unsupported"
    ] = "cover_identity_adjudicated_remaining_fields_unsupported"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_sample_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_sample_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    transaction_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    coverage_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    coverage_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[64] = EXPECTED_CASE_COUNT
    cover_8k_document_count: Literal[62] = EXPECTED_8K_DOCUMENT_COUNT
    cover_security_row_count: Literal[70] = EXPECTED_SECURITY_ROW_COUNT
    incomplete_security_context_count: Literal[1] = (
        EXPECTED_INCOMPLETE_SECURITY_CONTEXT_COUNT
    )
    matched_cover_document_count: Literal[61] = EXPECTED_MATCHED_DOCUMENT_COUNT
    outside_lifecycle_window_document_count: Literal[1] = 1
    matched_identity_case_count: Literal[61] = EXPECTED_MATCHED_CASE_COUNT
    adjudicated_case_count: Literal[61] = EXPECTED_MATCHED_CASE_COUNT
    adjudicated_field_count: Literal[61] = EXPECTED_MATCHED_FIELD_COUNT
    matched_field_count: Literal[61] = EXPECTED_MATCHED_FIELD_COUNT
    absent_field_count: Literal[0] = 0
    referenced_only_field_count: Literal[0] = 0
    ambiguous_field_count: Literal[0] = 0
    conflicting_field_count: Literal[0] = 0
    irrelevant_field_count: Literal[0] = 0
    unsupported_field_count: Literal[451] = EXPECTED_UNSUPPORTED_FIELD_COUNT
    result_state_counts: tuple[tuple[str, int], ...]
    field_result_counts: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]
    cover_documents: tuple[SecCoverDocumentIdentityDecisionV1, ...]
    cases: tuple[SecLifecycleCaseAdjudicationV1, ...]
    stable_security_evidence_link_count: Literal[61] = EXPECTED_MATCHED_CASE_COUNT
    canonical_identity_write_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecCaseAdjudicationV1":
        states = Counter(
            field.result_state for item in self.cases for field in item.field_results
        )
        field_states = tuple(
            (
                field,
                _ordered(
                    Counter(
                        result.result_state
                        for item in self.cases
                        for result in item.field_results
                        if result.field_name == field
                    )
                ),
            )
            for field in LIFECYCLE_REQUIRED_FIELDS
        )
        if (
            len(self.cover_documents) != EXPECTED_8K_DOCUMENT_COUNT
            or len(self.cases) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.cover_documents)
            != tuple(sorted(item.request_sequence for item in self.cover_documents))
            or tuple(str(item.instrument_id) for item in self.cases)
            != tuple(sorted(str(item.instrument_id) for item in self.cases))
            or sum(len(item.security_rows) for item in self.cover_documents)
            != self.cover_security_row_count
            or sum(
                len(item.incomplete_security_contexts) for item in self.cover_documents
            )
            != self.incomplete_security_context_count
            or sum(
                item.resolution_state == "matched_in_source_lifecycle_window"
                for item in self.cover_documents
            )
            != self.matched_cover_document_count
            or sum(
                item.resolution_state == "outside_source_lifecycle_window"
                for item in self.cover_documents
            )
            != self.outside_lifecycle_window_document_count
            or self.result_state_counts != _ordered(states)
            or self.field_result_counts != field_states
            or sum(states.values()) != EXPECTED_TOTAL_FIELD_COUNT
            or states["matched"] != self.matched_field_count
            or states["unsupported"] != self.unsupported_field_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("SEC case adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecCaseAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackSecCaseAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


@dataclass(slots=True)
class _InlineFact:
    name: str
    context_ref: str
    parts: list[str]


class _InlineXbrlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active: list[_InlineFact] = []
        self.facts: list[tuple[str, str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "ix:nonnumeric":
            return
        values = {key.lower(): value for key, value in attrs}
        name = values.get("name")
        context_ref = values.get("contextref")
        if name in _COVER_FACTS and context_ref:
            self.active.append(_InlineFact(name, context_ref, []))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "ix:nonnumeric" or not self.active:
            return
        item = self.active.pop()
        text = _normalized_text("".join(item.parts))
        if text:
            self.facts.append((item.name, item.context_ref, text))

    def handle_data(self, data: str) -> None:
        for item in self.active:
            item.parts.append(data)


def build_strong_leader_pullback_sec_case_adjudication(
    *,
    source_sample_root: Path,
    source_sample_custody_root: Path,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    transaction_root: Path,
    transaction_custody_root: Path,
    coverage_root: Path,
    coverage_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecCaseAdjudicationResult:
    with _network_prohibited():
        sample = read_strong_leader_pullback_source_acceptance_sample(
            output_root=source_sample_root,
            output_custody_root=source_sample_custody_root,
        )
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
        coverage = read_strong_leader_pullback_sec_case_coverage_census(
            output_root=coverage_root,
            output_custody_root=coverage_custody_root,
        )
        report = _build_report(
            sample=sample,
            plan=plan,
            source=source,
            transaction=transaction,
            coverage=coverage,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_case_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecCaseAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecCaseAdjudicationV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication report bytes are not canonical"
        )
    return StrongLeaderPullbackSecCaseAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    sample: StrongLeaderPullbackSourceAcceptanceSampleResult,
    plan: StrongLeaderPullbackSecDocumentPlanResult,
    source: StrongLeaderPullbackSecDocumentSourceResult,
    transaction: StrongLeaderPullbackSecTransactionCandidatesResult,
    coverage: StrongLeaderPullbackSecCaseCoverageCensusResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecCaseAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication revision is invalid"
        )
    if source.manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC document source manifest is unavailable"
        )
    if (
        transaction.report.plan_sha256 != plan.plan_sha256
        or transaction.report.source_manifest_sha256 != source.manifest_sha256
        or coverage.report.source_sample_sha256 != sample.report_sha256
        or coverage.report.transaction_report_sha256 != transaction.report_sha256
        or coverage.report.lifecycle_case_count != EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC adjudication input bindings differ"
        )
    sample_by_id = {item.instrument_id: item for item in sample.report.lifecycle_cases}
    coverage_by_id = {item.instrument_id: item for item in coverage.report.cases}
    resolver = SecIdentityResolver(tuple(_identity_record(item) for item in sample_by_id.values()))
    candidates = tuple(
        item for item in transaction.report.candidates if item.form == "8-K"
    )
    if len(candidates) != EXPECTED_8K_DOCUMENT_COUNT:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC 8-K adjudication population differs"
        )
    documents = tuple(
        _document_decision(
            candidate=item,
            source_case=sample_by_id[item.instrument_id],
            resolver=resolver,
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in candidates
    )
    documents_by_id: defaultdict[UUID, list[SecCoverDocumentIdentityDecisionV1]] = (
        defaultdict(list)
    )
    for item in documents:
        documents_by_id[item.instrument_id].append(item)
    cases = tuple(
        _case_adjudication(
            source_case=source_case,
            coverage_case=coverage_by_id[source_case.instrument_id],
            cover_documents=tuple(documents_by_id[source_case.instrument_id]),
        )
        for source_case in sorted(
            sample.report.lifecycle_cases, key=lambda item: str(item.instrument_id)
        )
    )
    states = Counter(
        result.result_state for item in cases for result in item.field_results
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _fingerprint(
            {
                "registered_rule": _REGISTERED_RULE,
                "effective_window": "canonical_first_observed_through_provider_delist_inclusive",
                "identity_tuple": "cik_ticker_exchange_mic_common_equity",
                "ticker_only": "forbidden",
            }
        ),
        "source_sample_sha256": sample.report_sha256,
        "source_sample_logical_fingerprint": sample.report.logical_fingerprint,
        "plan_sha256": plan.plan_sha256,
        "source_manifest_sha256": source.manifest_sha256,
        "transaction_report_sha256": transaction.report_sha256,
        "transaction_logical_fingerprint": transaction.report.logical_fingerprint,
        "coverage_report_sha256": coverage.report_sha256,
        "coverage_logical_fingerprint": coverage.report.logical_fingerprint,
        "cover_security_row_count": sum(len(item.security_rows) for item in documents),
        "incomplete_security_context_count": sum(
            len(item.incomplete_security_contexts) for item in documents
        ),
        "matched_cover_document_count": sum(
            item.resolution_state == "matched_in_source_lifecycle_window"
            for item in documents
        ),
        "outside_lifecycle_window_document_count": sum(
            item.resolution_state == "outside_source_lifecycle_window"
            for item in documents
        ),
        "matched_identity_case_count": sum(item.matched_field_count for item in cases),
        "adjudicated_case_count": sum(item.adjudicated_field_count > 0 for item in cases),
        "adjudicated_field_count": sum(item.adjudicated_field_count for item in cases),
        "matched_field_count": states["matched"],
        "unsupported_field_count": states["unsupported"],
        "result_state_counts": _ordered(states),
        "field_result_counts": tuple(
            (
                field,
                _ordered(
                    Counter(
                        result.result_state
                        for item in cases
                        for result in item.field_results
                        if result.field_name == field
                    )
                ),
            )
            for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "cover_documents": documents,
        "cases": cases,
    }
    provisional = StrongLeaderPullbackSecCaseAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecCaseAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _identity_record(item: LifecycleSourceAcceptanceCaseV1) -> SecIdentityRecord:
    if (
        item.selected_identity_types != ("share_class_figi",)
        or len(item.selected_identity_values) != 1
        or len(item.provider_ticker_locators) != 1
        or len(item.cik_locators) != 1
        or len(item.primary_exchange_locators) != 1
        or item.primary_exchange_locators[0] not in {"XNAS", "XNYS"}
    ):
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "source sample identity tuple is unsupported"
        )
    return SecIdentityRecord(
        instrument_id=item.instrument_id,
        effective_from=item.canonical_first_observed_date,
        effective_to=item.provider_delist_date_candidate + timedelta(days=1),
        cik=item.cik_locators[0],
        ticker=item.provider_ticker_locators[0],
        exchange=item.primary_exchange_locators[0],
        share_class_figi=item.selected_identity_values[0],
    )


def _document_decision(
    *,
    candidate: SecTransactionDocumentCandidateV1,
    source_case: LifecycleSourceAcceptanceCaseV1,
    resolver: SecIdentityResolver,
    path: Path,
) -> SecCoverDocumentIdentityDecisionV1:
    raw = path.read_bytes()
    if _sha256_bytes(raw) != candidate.document_sha256:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover source document identity differs"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover source document is not UTF-8"
        ) from exc
    parser = _InlineXbrlParser()
    parser.feed(text)
    parser.close()
    facts = tuple(parser.facts)
    report_date = _single_report_date(facts)
    issuer_cik = _single_cik(facts)
    registrants = _fact_values(facts, "dei:EntityRegistrantName")
    rows, incomplete_contexts = _security_rows(facts)
    if issuer_cik not in source_case.cik_locators:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover issuer CIK differs from source case"
        )
    resolution = tuple(
        resolver.resolve(
            {
                "source_dataset": "inline_xbrl_cover",
                "cik": issuer_cik,
                "TradingSymbol": row.trading_symbol.upper(),
                "SecurityExchangeName": row.exchange_mic,
            },
            as_of_date=report_date,
        )
        for row in rows
    )
    matched_indexes = tuple(
        index
        for index, (row, decision) in enumerate(zip(rows, resolution, strict=True))
        if decision.status is SecEvidenceResolutionStatus.CANONICAL_MAPPED
        and decision.instrument_id == source_case.instrument_id
        and row.security_form_scope == "common_equity"
    )
    conflicting = any(
        decision.status
        in {SecEvidenceResolutionStatus.AMBIGUOUS, SecEvidenceResolutionStatus.COLLISION}
        or (
            decision.status is SecEvidenceResolutionStatus.CANONICAL_MAPPED
            and decision.instrument_id != source_case.instrument_id
        )
        for decision in resolution
    )
    if conflicting:
        state: CoverResolutionState = "conflicting_cover"
        reasons = ("cover_identity_evidence_conflicts",)
    elif len(matched_indexes) == 1:
        state = "matched_in_source_lifecycle_window"
        reasons = (
            "common_equity_cover_row",
            "point_in_time_cik_ticker_exchange_match",
            "ticker_only_join_forbidden",
        )
    elif report_date > source_case.provider_delist_date_candidate:
        state = "outside_source_lifecycle_window"
        reasons = (
            "cover_report_date_after_provider_delist_candidate",
            "ticker_reuse_outside_effective_window_rejected",
        )
    elif len(matched_indexes) > 1:
        state = "ambiguous_cover"
        reasons = ("multiple_matching_common_equity_cover_rows",)
    else:
        state = "unsupported_cover"
        reasons = ("no_point_in_time_common_equity_cover_match",)
    matched_fingerprint = (
        rows[matched_indexes[0]].logical_fingerprint
        if state == "matched_in_source_lifecycle_window"
        else None
    )
    values = {
        "request_sequence": candidate.request_sequence,
        "instrument_id": candidate.instrument_id,
        "accession_number": candidate.accession_number,
        "filing_date": candidate.filing_date,
        "acceptance_datetime": candidate.acceptance_datetime,
        "document_sha256": candidate.document_sha256,
        "transaction_structure_state": candidate.structure_state,
        "report_date": report_date,
        "issuer_cik": issuer_cik,
        "registrant_name_candidates": registrants,
        "security_rows": rows,
        "incomplete_security_contexts": incomplete_contexts,
        "source_ticker": source_case.provider_ticker_locators[0],
        "source_exchange_mic": source_case.primary_exchange_locators[0],
        "source_share_class_figi": source_case.selected_identity_values[0],
        "resolution_state": state,
        "matched_row_fingerprint": matched_fingerprint,
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = SecCoverDocumentIdentityDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCoverDocumentIdentityDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _case_adjudication(
    *,
    source_case: LifecycleSourceAcceptanceCaseV1,
    coverage_case: SecLifecycleCaseCoverageV1,
    cover_documents: tuple[SecCoverDocumentIdentityDecisionV1, ...],
) -> SecLifecycleCaseAdjudicationV1:
    structured_matches = tuple(
        item
        for item in cover_documents
        if item.transaction_structure_state == "8k_item_2_01_candidate_scope"
        and item.resolution_state == "matched_in_source_lifecycle_window"
    )
    adverse = tuple(
        item
        for item in cover_documents
        if item.resolution_state in {"ambiguous_cover", "conflicting_cover"}
    )
    identity_matched = len(structured_matches) == 1 and not adverse
    field_results = tuple(
        _field_result(
            field=field,
            instrument_id=source_case.instrument_id,
            identity_matched=identity_matched,
            structured_matches=structured_matches,
        )
        for field in LIFECYCLE_REQUIRED_FIELDS
    )
    states = Counter(item.result_state for item in field_results)
    values = {
        "instrument_id": source_case.instrument_id,
        "source_case_fingerprint": _fingerprint(source_case.model_dump(mode="json")),
        "coverage_case_fingerprint": coverage_case.logical_fingerprint,
        "evidence_profile": coverage_case.evidence_profile,
        "cover_document_sequences": tuple(
            sorted(item.request_sequence for item in cover_documents)
        ),
        "cover_resolution_counts": _ordered(
            Counter(item.resolution_state for item in cover_documents)
        ),
        "field_results": field_results,
        "adjudicated_field_count": len(field_results) - states["unsupported"],
        "matched_field_count": states["matched"],
        "unsupported_field_count": states["unsupported"],
    }
    provisional = SecLifecycleCaseAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecLifecycleCaseAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _field_result(
    *,
    field: str,
    instrument_id: UUID,
    identity_matched: bool,
    structured_matches: tuple[SecCoverDocumentIdentityDecisionV1, ...],
) -> SecCaseFieldAdjudicationV1:
    if field == "stable_security_and_listing_identifiers" and identity_matched:
        evidence = tuple(sorted(structured_matches, key=lambda item: item.request_sequence))
        return SecCaseFieldAdjudicationV1(
            field_name=field,
            result_state="matched",
            decision_rule=_REGISTERED_RULE,
            evidence_document_sequences=tuple(item.request_sequence for item in evidence),
            evidence_fingerprints=tuple(item.logical_fingerprint for item in evidence),
            decision_reasons=(
                "common_equity_cover_row",
                "point_in_time_cik_ticker_exchange_match",
                "stable_instrument_id_retained_as_join_key",
            ),
            matched_value_fingerprint=_fingerprint(
                {
                    "instrument_id": str(instrument_id),
                    "cover_decisions": [item.logical_fingerprint for item in evidence],
                }
            ),
        )
    reason = (
        "no_in_window_structured_8k_cover"
        if field == "stable_security_and_listing_identifiers"
        else "field_adjudication_rule_not_registered"
    )
    return SecCaseFieldAdjudicationV1(
        field_name=field,
        result_state="unsupported",
        decision_rule=(
            _REGISTERED_RULE
            if field == "stable_security_and_listing_identifiers"
            else "none"
        ),
        evidence_document_sequences=(),
        evidence_fingerprints=(),
        decision_reasons=(reason,),
    )


def _fact_values(
    facts: tuple[tuple[str, str, str], ...], name: str
) -> tuple[str, ...]:
    return tuple(sorted({text for fact_name, _, text in facts if fact_name == name}))


def _single_report_date(facts: tuple[tuple[str, str, str], ...]) -> date:
    values = _fact_values(facts, "dei:DocumentPeriodEndDate")
    if len(values) != 1:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover report date is not unique"
        )
    try:
        return datetime.strptime(values[0], "%B %d, %Y").date()
    except ValueError as exc:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover report date is unsupported"
        ) from exc


def _single_cik(facts: tuple[tuple[str, str, str], ...]) -> str:
    values = _fact_values(facts, "dei:EntityCentralIndexKey")
    if len(values) != 1 or not values[0].isdigit() or len(values[0]) > 10:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover issuer CIK is not unique"
        )
    return values[0].zfill(10)


def _security_rows(
    facts: tuple[tuple[str, str, str], ...]
) -> tuple[
    tuple[SecCoverSecurityRowV1, ...],
    tuple[SecCoverIncompleteSecurityContextV1, ...],
]:
    by_context: defaultdict[str, defaultdict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for name, context_ref, text in facts:
        if name in _SECURITY_FACTS:
            by_context[context_ref][name].add(text)
    rows: list[SecCoverSecurityRowV1] = []
    incomplete: list[SecCoverIncompleteSecurityContextV1] = []
    for context_ref, values in sorted(by_context.items()):
        if set(values) != set(_SECURITY_FACTS) or any(
            len(values[name]) != 1 for name in _SECURITY_FACTS
        ):
            titles = tuple(sorted(values["dei:Security12bTitle"]))
            if not titles or any(
                _security_form_scope(value) == "common_equity" for value in titles
            ):
                raise StrongLeaderPullbackSecCaseAdjudicationError(
                    "SEC target cover security triad is incomplete or ambiguous"
                )
            incomplete_values = {
                "context_ref": context_ref,
                "security_titles": titles,
                "trading_symbols": tuple(sorted(values["dei:TradingSymbol"])),
                "exchange_names": tuple(
                    sorted(values["dei:SecurityExchangeName"])
                ),
            }
            provisional_incomplete = SecCoverIncompleteSecurityContextV1.model_construct(
                **incomplete_values, logical_fingerprint="0" * 64
            )
            incomplete.append(
                SecCoverIncompleteSecurityContextV1.model_validate(
                    {
                        **incomplete_values,
                        "logical_fingerprint": _fingerprint(
                            provisional_incomplete.model_dump(
                                mode="json", exclude={"logical_fingerprint"}
                            )
                        ),
                    }
                )
            )
            continue
        title = next(iter(values["dei:Security12bTitle"]))
        ticker = next(iter(values["dei:TradingSymbol"]))
        exchange = next(iter(values["dei:SecurityExchangeName"]))
        row_values = {
            "context_ref": context_ref,
            "security_title": title,
            "trading_symbol": ticker,
            "exchange_name": exchange,
            "exchange_mic": _exchange_mic(exchange),
            "security_form_scope": _security_form_scope(title),
        }
        provisional = SecCoverSecurityRowV1.model_construct(
            **row_values, logical_fingerprint="0" * 64
        )
        rows.append(
            SecCoverSecurityRowV1.model_validate(
                {
                    **row_values,
                    "logical_fingerprint": _fingerprint(
                        provisional.model_dump(
                            mode="json", exclude={"logical_fingerprint"}
                        )
                    ),
                }
            )
        )
    if not rows:
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC cover has no security triad"
        )
    return tuple(rows), tuple(incomplete)


def _exchange_mic(value: str) -> Literal["XNAS", "XNYS"]:
    normalized = _normalized_text(value).lower()
    if "nasdaq" in normalized:
        return "XNAS"
    if normalized == "nyse" or "new york stock exchange" in normalized:
        return "XNYS"
    raise StrongLeaderPullbackSecCaseAdjudicationError(
        "SEC cover exchange mapping is unsupported"
    )


def _security_form_scope(value: str) -> SecurityFormScope:
    return "common_equity" if _COMMON_EQUITY_RE.search(value) else "other_security"


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecCaseAdjudicationV1,
) -> StrongLeaderPullbackSecCaseAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_case_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecCaseAdjudicationError(
                "existing SEC case adjudication report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication staging target exists"
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
    reread = read_strong_leader_pullback_sec_case_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecCaseAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication paths must be absolute"
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
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication custody or target is unsafe"
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
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "SEC case adjudication file metadata differs"
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
        raise StrongLeaderPullbackSecCaseAdjudicationError(
            "network access is prohibited during SEC case adjudication"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
