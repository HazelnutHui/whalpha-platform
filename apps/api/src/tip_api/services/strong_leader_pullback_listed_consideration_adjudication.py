"""Adjudicate listed merger consideration identities from frozen 424B3 files."""

from __future__ import annotations

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
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_listed_consideration_source import (
    DOCUMENT_FILE,
    ListedConsiderationDocumentArtifactV1,
    StrongLeaderPullbackListedConsiderationSourceResult,
    _read_artifact_directory,
    read_strong_leader_pullback_listed_consideration_source,
)
from tip_api.services.strong_leader_pullback_listed_consideration_source_plan import (
    EXPECTED_CASE_COUNT,
    ListedConsiderationSourcePlanDecisionV1,
    StrongLeaderPullbackListedConsiderationSourcePlanResult,
    _fingerprint,
    _json_bytes,
    _sha256_bytes,
    read_strong_leader_pullback_listed_consideration_source_plan,
)
from tip_api.services.strong_leader_pullback_sec_document_content_census import (
    _decode,
    _DocumentTextParser,
)
from tip_api.services.strong_leader_pullback_terminal_payoff_terms import (
    StrongLeaderPullbackTerminalPayoffTermsResult,
    TerminalPayoffTermsDecisionV1,
    read_strong_leader_pullback_terminal_payoff_terms,
)


CONTRACT_VERSION = "strong-leader-pullback-listed-consideration-adjudication/1.0"
REPORT_FILE = "listed-consideration-adjudication.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 2600
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"

ResolutionState = Literal[
    "matched",
    "final_exchange_ratio_absent_from_registration_source",
    "transaction_registration_scope_absent",
    "required_evidence_not_matched",
]
EvidencePurpose = Literal[
    "direct_registered_exchange_clause",
    "variable_exchange_formula_clause",
    "non_transaction_offering_scope",
]


@dataclass(frozen=True, slots=True)
class _CaseSpec:
    expected_ratio: str
    target_security_terms: tuple[str, ...]
    consideration_security_terms: tuple[str, ...]
    expected_source_state: Literal["direct", "formula_only", "wrong_scope"]
    formula_terms: tuple[str, ...] = ()
    wrong_scope_terms: tuple[str, ...] = ()


_CASE_SPECS = {
    1: _CaseSpec(
        "1.818500",
        ("PotlatchDeltic common stock",),
        ("Rayonier common shares",),
        "direct",
    ),
    14: _CaseSpec(
        "11.000000",
        ("Mr. Cooper common stock",),
        ("Rocket Class A common stock",),
        "direct",
    ),
    35: _CaseSpec(
        "1.152300",
        ("NV5 Common Stock",),
        ("Acuren Common Stock",),
        "direct",
    ),
    40: _CaseSpec(
        "0.344000",
        ("IPG common stock",),
        ("Omnicom common stock",),
        "direct",
    ),
    95: _CaseSpec(
        "1.436000",
        ("Anywhere common stock",),
        ("Compass Class A common stock",),
        "direct",
    ),
    107: _CaseSpec(
        "0.140000",
        ("NSA common shares",),
        ("Public Storage common shares",),
        "direct",
    ),
    158: _CaseSpec(
        "0.488300",
        ("SkyWater common stock",),
        ("IonQ common stock",),
        "formula_only",
        ("$20.00", "IonQ Trading Price", "quotient"),
    ),
    174: _CaseSpec(
        "1.866300",
        ("Comerica common stock",),
        ("Fifth Third common stock",),
        "wrong_scope",
        wrong_scope_terms=(
            "Fifth Third Bancorp is offering",
            "Senior Notes due 2032",
            "Senior Notes due 2037",
        ),
    ),
    178: _CaseSpec(
        "1.950000",
        ("Veritex common stock",),
        ("Huntington common stock",),
        "direct",
    ),
    184: _CaseSpec(
        "0.195500",
        ("Spirit Common Stock",),
        ("Boeing Common Stock",),
        "formula_only",
        ("$37.25", "Boeing Stock Price", "quotient"),
    ),
    197: _CaseSpec(
        "0.915000",
        ("Pacific Premier common stock",),
        ("Columbia common stock",),
        "direct",
    ),
    218: _CaseSpec(
        "2.793000",
        ("AvalonBay common stock",),
        ("Equity Residential common shares",),
        "direct",
    ),
}


class StrongLeaderPullbackListedConsiderationAdjudicationError(RuntimeError):
    """Raised when listed-consideration content cannot be adjudicated."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ListedConsiderationEvidenceSpanV1(_FrozenModel):
    purpose: EvidencePurpose
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS)
    text_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def span_reconciles(self) -> "ListedConsiderationEvidenceSpanV1":
        if (
            self.normalized_end <= self.normalized_start
            or self.normalized_end - self.normalized_start != len(self.text)
            or self.text_sha256 != _sha256_bytes(self.text.encode("utf-8"))
        ):
            raise ValueError("listed-consideration evidence span differs")
        return self


class ListedConsiderationIdentityDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    target_instrument_id: UUID
    proposed_consideration_instrument_id: UUID
    proposed_cik: str = Field(pattern=r"^[0-9]{10}$")
    plan_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_artifact_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_document_sha256: str = Field(pattern=_SHA256_PATTERN)
    normalized_text_character_count: int = Field(ge=1)
    normalized_text_sha256: str = Field(pattern=_SHA256_PATTERN)
    expected_exchange_ratio: str = Field(pattern=r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$")
    exact_ratio_occurrence_count: int = Field(ge=0)
    resolution_state: ResolutionState
    sec_filer_cik_to_canonical_common_security_match: bool
    transaction_match: bool
    target_common_security_match: bool
    consideration_security_class_match: bool
    registered_exchange_ratio_match: bool
    evidence: ListedConsiderationEvidenceSpanV1 | None
    assigned_consideration_instrument_id: UUID | None
    consideration_security_identity_assignment_count: int = Field(ge=0, le=1)
    terminal_value_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    source_name_or_ticker_grants_identity: Literal[False] = False
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("listed-consideration decision reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "ListedConsiderationIdentityDecisionV1":
        matched = self.resolution_state == "matched"
        if (
            matched
            != (
                self.transaction_match
                and self.sec_filer_cik_to_canonical_common_security_match
                and self.target_common_security_match
                and self.consideration_security_class_match
                and self.registered_exchange_ratio_match
            )
            or matched != (self.assigned_consideration_instrument_id is not None)
            or matched != (self.consideration_security_identity_assignment_count == 1)
            or (
                self.assigned_consideration_instrument_id is not None
                and self.assigned_consideration_instrument_id
                != self.proposed_consideration_instrument_id
            )
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-consideration identity decision differs")
        return self


class StrongLeaderPullbackListedConsiderationAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "listed_consideration_identity_partially_adjudicated"
    ] = "listed_consideration_identity_partially_adjudicated"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_artifact_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    case_count: Literal[12] = EXPECTED_CASE_COUNT
    matched_identity_count: int = Field(ge=0, le=EXPECTED_CASE_COUNT)
    final_ratio_absent_count: int = Field(ge=0, le=EXPECTED_CASE_COUNT)
    transaction_scope_absent_count: int = Field(ge=0, le=EXPECTED_CASE_COUNT)
    required_evidence_not_matched_count: int = Field(ge=0, le=EXPECTED_CASE_COUNT)
    resolution_state_counts: tuple[tuple[str, int], ...]
    decisions: tuple[ListedConsiderationIdentityDecisionV1, ...]
    consideration_security_identity_assignment_count: int = Field(
        ge=0, le=EXPECTED_CASE_COUNT
    )
    terminal_value_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackListedConsiderationAdjudicationV1":
        states = Counter(item.resolution_state for item in self.decisions)
        if (
            len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(_CASE_SPECS))
            or self.matched_identity_count != states["matched"]
            or self.final_ratio_absent_count
            != states["final_exchange_ratio_absent_from_registration_source"]
            or self.transaction_scope_absent_count
            != states["transaction_registration_scope_absent"]
            or self.required_evidence_not_matched_count
            != states["required_evidence_not_matched"]
            or self.resolution_state_counts != _ordered(states)
            or self.consideration_security_identity_assignment_count
            != sum(
                item.consideration_security_identity_assignment_count
                for item in self.decisions
            )
            or self.consideration_security_identity_assignment_count
            != self.matched_identity_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed-consideration adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackListedConsiderationAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_listed_consideration_adjudication(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationAdjudicationResult:
    with _network_prohibited():
        plan = read_strong_leader_pullback_listed_consideration_source_plan(
            output_root=plan_root, output_custody_root=plan_custody_root
        )
        source = read_strong_leader_pullback_listed_consideration_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=source_root,
            output_custody_root=source_custody_root,
        )
        payoff = read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            payoff=payoff,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_listed_consideration_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackListedConsiderationAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackListedConsiderationAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication bytes are not canonical"
        )
    return StrongLeaderPullbackListedConsiderationAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    plan: StrongLeaderPullbackListedConsiderationSourcePlanResult,
    source: StrongLeaderPullbackListedConsiderationSourceResult,
    payoff: StrongLeaderPullbackTerminalPayoffTermsResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication revision is invalid"
        )
    manifest = source.manifest
    if manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration source manifest is unavailable"
        )
    if (
        plan.report.payoff_terms_report_sha256 != payoff.report_sha256
        or plan.report.payoff_terms_logical_fingerprint
        != payoff.report.logical_fingerprint
        or manifest.plan_report_sha256 != plan.report_sha256
        or manifest.plan_logical_fingerprint != plan.report.logical_fingerprint
    ):
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication input binding differs"
        )
    payoff_map = {
        item.request_sequence: item
        for item in payoff.report.decisions
        if item.terminal_candidate_state
        == "listed_security_identity_and_market_value_required"
    }
    if set(payoff_map) != set(_CASE_SPECS):
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication population differs"
        )
    decisions = tuple(
        _adjudicate_decision(
            plan=item,
            payoff=payoff_map[item.request_sequence],
            artifact=_read_artifact_directory(
                source.output_root / f"request={item.request_sequence:06d}", item
            ),
            document_path=source.output_root
            / f"request={item.request_sequence:06d}"
            / DOCUMENT_FILE,
        )
        for item in plan.report.decisions
    )
    states = Counter(item.resolution_state for item in decisions)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "plan_report_sha256": plan.report_sha256,
        "plan_logical_fingerprint": plan.report.logical_fingerprint,
        "source_manifest_sha256": source.manifest_sha256,
        "source_logical_fingerprint": manifest.logical_fingerprint,
        "source_artifact_binding_fingerprint": (
            manifest.artifact_binding_fingerprint
        ),
        "payoff_terms_report_sha256": payoff.report_sha256,
        "payoff_terms_logical_fingerprint": payoff.report.logical_fingerprint,
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "matched_identity_count": states["matched"],
        "final_ratio_absent_count": states[
            "final_exchange_ratio_absent_from_registration_source"
        ],
        "transaction_scope_absent_count": states[
            "transaction_registration_scope_absent"
        ],
        "required_evidence_not_matched_count": states[
            "required_evidence_not_matched"
        ],
        "resolution_state_counts": _ordered(states),
        "decisions": decisions,
        "consideration_security_identity_assignment_count": sum(
            item.consideration_security_identity_assignment_count
            for item in decisions
        ),
    }
    provisional = StrongLeaderPullbackListedConsiderationAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackListedConsiderationAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _adjudicate_decision(
    *,
    plan: ListedConsiderationSourcePlanDecisionV1,
    payoff: TerminalPayoffTermsDecisionV1,
    artifact: ListedConsiderationDocumentArtifactV1,
    document_path: Path,
) -> ListedConsiderationIdentityDecisionV1:
    spec = _CASE_SPECS[plan.request_sequence]
    expected_ratio = _payoff_ratio(payoff)
    if (
        expected_ratio != spec.expected_ratio
        or payoff.instrument_id != plan.target_instrument_id
        or artifact.plan_decision_fingerprint != plan.logical_fingerprint
        or artifact.target_instrument_id != plan.target_instrument_id
        or artifact.proposed_consideration_instrument_id
        != plan.proposed_consideration_instrument_id
        or artifact.proposed_cik != plan.proposed_cik
        or plan.canonical_cik != plan.proposed_cik
        or not plan.canonical_source_instrument_id.startswith("share_class_figi:")
    ):
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration decision binding differs"
        )
    raw = document_path.read_bytes()
    if _sha256_bytes(raw) != artifact.physical_sha256:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration source document differs"
        )
    normalized = _normalized_document(raw)
    exact_matches = tuple(_ratio_pattern(expected_ratio).finditer(normalized))
    evidence: ListedConsiderationEvidenceSpanV1 | None
    transaction_match = False
    target_match = False
    class_match = False
    ratio_match = False
    if spec.expected_source_state == "direct":
        selected = _direct_evidence(normalized, spec, exact_matches)
        if selected is None:
            state: ResolutionState = "required_evidence_not_matched"
            evidence = None
            reasons = (
                "all_four_source_elements_required",
                "candidate_stable_id_remains_unassigned",
                "direct_registered_exchange_clause_not_matched",
            )
        else:
            state = "matched"
            evidence = _evidence_span(
                normalized, *selected, "direct_registered_exchange_clause"
            )
            transaction_match = target_match = class_match = ratio_match = True
            reasons = (
                "candidate_identity_bound_to_plan_and_source_artifact",
                "registered_clause_matches_same_transaction_target_class_and_ratio",
                "ticker_and_name_used_only_as_source_locators",
            )
    elif spec.expected_source_state == "formula_only":
        selected = _formula_evidence(normalized, spec)
        if selected is None or exact_matches:
            state = "required_evidence_not_matched"
            evidence = None
            reasons = (
                "candidate_stable_id_remains_unassigned",
                "formula_source_profile_differs",
            )
        else:
            state = "final_exchange_ratio_absent_from_registration_source"
            evidence = _evidence_span(
                normalized, *selected, "variable_exchange_formula_clause"
            )
            transaction_match = target_match = class_match = True
            reasons = (
                "candidate_stable_id_remains_unassigned",
                "registration_document_contains_variable_ratio_formula",
                "terminal_document_ratio_not_independently_present",
            )
    else:
        selected = _wrong_scope_evidence(normalized, spec)
        if selected is None or exact_matches:
            state = "required_evidence_not_matched"
            evidence = None
            reasons = (
                "candidate_stable_id_remains_unassigned",
                "non_transaction_source_profile_differs",
            )
        else:
            state = "transaction_registration_scope_absent"
            evidence = _evidence_span(
                normalized, *selected, "non_transaction_offering_scope"
            )
            reasons = (
                "candidate_stable_id_remains_unassigned",
                "selected_424b3_is_a_senior_notes_offering",
                "transaction_class_and_exchange_ratio_are_not_proven",
            )
    matched = state == "matched"
    values = {
        "request_sequence": plan.request_sequence,
        "target_instrument_id": plan.target_instrument_id,
        "proposed_consideration_instrument_id": (
            plan.proposed_consideration_instrument_id
        ),
        "proposed_cik": plan.proposed_cik,
        "plan_decision_fingerprint": plan.logical_fingerprint,
        "source_artifact_fingerprint": artifact.logical_fingerprint,
        "source_document_sha256": artifact.physical_sha256,
        "normalized_text_character_count": len(normalized),
        "normalized_text_sha256": _sha256_bytes(normalized.encode("utf-8")),
        "expected_exchange_ratio": expected_ratio,
        "exact_ratio_occurrence_count": len(exact_matches),
        "resolution_state": state,
        "sec_filer_cik_to_canonical_common_security_match": True,
        "transaction_match": transaction_match,
        "target_common_security_match": target_match,
        "consideration_security_class_match": class_match,
        "registered_exchange_ratio_match": ratio_match,
        "evidence": evidence,
        "assigned_consideration_instrument_id": (
            plan.proposed_consideration_instrument_id if matched else None
        ),
        "consideration_security_identity_assignment_count": int(matched),
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = ListedConsiderationIdentityDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ListedConsiderationIdentityDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _payoff_ratio(decision: TerminalPayoffTermsDecisionV1) -> str:
    values = tuple(
        item.normalized_value
        for item in decision.terms
        if item.term_kind == "listed_equity_shares_per_target_share"
    )
    if len(values) != 1:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration payoff ratio differs"
        )
    return values[0]


def _normalized_document(raw: bytes) -> str:
    decoded, _ = _decode(raw)
    parser = _DocumentTextParser()
    try:
        parser.feed(decoded)
        parser.close()
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration document markup cannot be parsed"
        ) from exc
    normalized = " ".join(
        unicodedata.normalize("NFKC", " ".join(parser.parts)).split()
    )
    if not normalized:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration normalized text is empty"
        )
    return normalized


def _ratio_pattern(value: str) -> re.Pattern[str]:
    integer, fraction = value.split(".", 1)
    significant = fraction.rstrip("0")
    if significant:
        decimal = rf"{re.escape(integer)}\.{re.escape(significant)}0*"
    else:
        decimal = rf"{re.escape(integer)}(?:\.0+)?"
    return re.compile(rf"(?<![0-9.]){decimal}(?![0-9.])")


def _direct_evidence(
    text: str, spec: _CaseSpec, matches: tuple[re.Match[str], ...]
) -> tuple[int, int] | None:
    for match in matches:
        start, end = _window(text, match.start(), match.end())
        candidate = text[start:end]
        if (
            _contains_all(candidate, spec.target_security_terms)
            and _contains_all(candidate, spec.consideration_security_terms)
            and re.search(r"\bmerger\b", candidate, re.IGNORECASE)
            and re.search(
                r"\b(?:receive|converted|exchange for)\b",
                candidate,
                re.IGNORECASE,
            )
        ):
            return start, end
    return None


def _formula_evidence(text: str, spec: _CaseSpec) -> tuple[int, int] | None:
    for match in re.finditer(r"\bexchange ratio\b", text, re.IGNORECASE):
        start, end = _window(text, match.start(), match.end())
        candidate = text[start:end]
        if (
            _contains_all(candidate, spec.target_security_terms)
            and _contains_all(candidate, spec.consideration_security_terms)
            and _contains_all(candidate, spec.formula_terms)
            and re.search(r"\bmerger", candidate, re.IGNORECASE)
        ):
            return start, end
    return None


def _wrong_scope_evidence(text: str, spec: _CaseSpec) -> tuple[int, int] | None:
    search_end = min(len(text), MAXIMUM_EVIDENCE_TEXT_CHARS)
    candidate = text[:search_end]
    if _contains_all(candidate, spec.wrong_scope_terms):
        return 0, search_end
    return None


def _window(text: str, start: int, end: int) -> tuple[int, int]:
    before = 900
    after = 1500
    window_start = max(0, start - before)
    window_end = min(len(text), end + after)
    if window_end - window_start > MAXIMUM_EVIDENCE_TEXT_CHARS:
        window_end = window_start + MAXIMUM_EVIDENCE_TEXT_CHARS
    return window_start, window_end


def _contains_all(text: str, values: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return all(value.casefold() in folded for value in values)


def _evidence_span(
    text: str, start: int, end: int, purpose: EvidencePurpose
) -> ListedConsiderationEvidenceSpanV1:
    value = text[start:end]
    return ListedConsiderationEvidenceSpanV1(
        purpose=purpose,
        normalized_start=start,
        normalized_end=end,
        text=value,
        text_sha256=_sha256_bytes(value.encode("utf-8")),
    )


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "case_specs": {
                str(key): {
                    "expected_ratio": value.expected_ratio,
                    "target_security_terms": value.target_security_terms,
                    "consideration_security_terms": (
                        value.consideration_security_terms
                    ),
                    "expected_source_state": value.expected_source_state,
                    "formula_terms": value.formula_terms,
                    "wrong_scope_terms": value.wrong_scope_terms,
                }
                for key, value in sorted(_CASE_SPECS.items())
            },
            "evidence_window_before": 900,
            "evidence_window_after": 1500,
            "identity_gate": (
                "same_transaction_and_target_common_security_and_"
                "consideration_class_and_exact_registered_ratio"
            ),
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackListedConsiderationAdjudicationV1,
) -> StrongLeaderPullbackListedConsiderationAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_listed_consideration_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackListedConsiderationAdjudicationError(
                "existing listed-consideration adjudication differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication staging target exists"
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
        if (
            partial.exists()
            and not partial.is_symlink()
            and partial.parent == target.parent
        ):
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_listed_consideration_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackListedConsiderationAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication paths must be absolute"
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
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication custody or target is unsafe"
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
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "listed-consideration adjudication file metadata differs"
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
    return tuple(sorted((key, count) for key, count in counter.items() if count))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackListedConsiderationAdjudicationError(
            "network access is prohibited during listed-consideration adjudication"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
