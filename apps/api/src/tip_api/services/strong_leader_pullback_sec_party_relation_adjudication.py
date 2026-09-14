"""Typed source-party relations for first-strategy SEC transaction cases."""

from __future__ import annotations

import os
import re
import shutil
import socket
import stat
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_case_adjudication import (
    SecCoverDocumentIdentityDecisionV1,
    StrongLeaderPullbackSecCaseAdjudicationResult,
    read_strong_leader_pullback_sec_case_adjudication,
)
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    SecCommonShareConsiderationDecisionV1,
    StrongLeaderPullbackSecConsiderationAdjudicationResult,
    _clause_spans,
    _fingerprint,
    _json_bytes,
    _normalized_text,
    _sha256_bytes,
    read_strong_leader_pullback_sec_consideration_adjudication,
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


CONTRACT_VERSION = "strong-leader-pullback-sec-party-relation-adjudication/1.0"
REPORT_FILE = "party-relations.json"
EXPECTED_CASE_COUNT = 61
MAXIMUM_REPORT_BYTES = 3 * 1024 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 4096
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"

# This is a finite, source-hash-bound adjudication registry, not a general
# entity-resolution heuristic. Every sequence belongs to exactly one set.
_TARGET_ABSORBED_SEQUENCES = frozenset(
    {1, 14, 35, 87, 92, 107, 158, 161, 174, 178, 218}
)
_NEW_HOLDING_COMPANY_SEQUENCES = frozenset({124})
_TARGET_SURVIVES_SEQUENCES = frozenset(
    {
        7,
        11,
        20,
        26,
        28,
        38,
        40,
        45,
        49,
        52,
        55,
        59,
        64,
        68,
        72,
        74,
        79,
        83,
        90,
        95,
        99,
        100,
        104,
        109,
        113,
        115,
        118,
        122,
        129,
        136,
        139,
        143,
        147,
        150,
        152,
        156,
        166,
        172,
        181,
        184,
        187,
        190,
        194,
        197,
        200,
        204,
        208,
        211,
        214,
    }
)
_REGISTERED_SEQUENCES = (
    _TARGET_ABSORBED_SEQUENCES
    | _NEW_HOLDING_COMPANY_SEQUENCES
    | _TARGET_SURVIVES_SEQUENCES
)

_AGREEMENT_RE = re.compile(
    r"\b(?:Agreement and Plan of Merger|Merger Agreement)\b", re.IGNORECASE
)
_PARTY_CONNECTOR_RE = re.compile(
    r"\b(?:by and among|by and between|entered into with|entered into|with)\b",
    re.IGNORECASE,
)
_MERGER_RELATION_RE = re.compile(
    r"\b(?:merged|merge|merger)(?:\s+\([^)]{0,180}\))?\s+"
    r"(?:with\s+and\s+into|into|of\b.{0,700}\bwith\s+and\s+into)",
    re.IGNORECASE,
)
_SURVIVOR_RE = re.compile(
    r"\b(?:surviv(?:e|ed|es|ing)|continu(?:e|ed|ing)\s+as\s+the\s+surviving)\b",
    re.IGNORECASE,
)

ResolutionState = Literal["matched", "ambiguous", "unsupported"]
RelationTopology = Literal[
    "target_survives_as_owned_subsidiary",
    "target_absorbed_into_other_survivor",
    "target_and_peer_absorbed_into_new_holding_company",
]
TargetLegalEntityDisposition = Literal[
    "target_legal_entity_survives",
    "target_legal_entity_is_absorbed",
]
AcquirerRelationState = Literal[
    "parent_or_acquirer_group_bound_in_source",
    "peer_combination_without_single_acquirer",
]
SuccessorRelationState = Literal[
    "target_legal_entity_is_surviving_entity",
    "other_legal_entity_is_surviving_entity",
    "new_holding_company_is_surviving_entity",
]


class StrongLeaderPullbackSecPartyRelationAdjudicationError(RuntimeError):
    """Raised when source-party relations cannot be proven safely."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecPartyRelationDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    accession_number: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    filing_date: date
    acceptance_datetime: datetime
    document_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_event_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    transaction_completion_date: date
    transaction_scope_sha256: str = Field(pattern=_SHA256_PATTERN)
    resolution_state: ResolutionState
    relation_topology: RelationTopology | None = None
    target_legal_entity_disposition: TargetLegalEntityDisposition | None = None
    acquirer_relation_state: AcquirerRelationState | None = None
    successor_relation_state: SuccessorRelationState | None = None
    listed_equity_consideration: bool
    party_definition_start: int | None = Field(default=None, ge=0)
    party_definition_end: int | None = Field(default=None, ge=1)
    party_definition_text: str | None = Field(
        default=None, min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS
    )
    party_definition_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    relation_evidence_start: int | None = Field(default=None, ge=0)
    relation_evidence_end: int | None = Field(default=None, ge=1)
    relation_evidence_text: str | None = Field(
        default=None, min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS
    )
    relation_evidence_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    counterparty_stable_id_assignment_count: Literal[0] = 0
    successor_stable_id_assignment_count: Literal[0] = 0
    consideration_issuer_stable_id_assignment_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("party_definition_text", "relation_evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str | None) -> str | None:
        if value is not None and value != _normalized_text(value):
            raise ValueError("party-relation evidence is not normalized")
        return value

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("party-relation reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "SecPartyRelationDecisionV1":
        matched = self.resolution_state == "matched"
        typed = all(
            value is not None
            for value in (
                self.relation_topology,
                self.target_legal_entity_disposition,
                self.acquirer_relation_state,
                self.successor_relation_state,
            )
        )
        party_evidence = all(
            value is not None
            for value in (
                self.party_definition_start,
                self.party_definition_end,
                self.party_definition_text,
                self.party_definition_sha256,
            )
        )
        relation_evidence = all(
            value is not None
            for value in (
                self.relation_evidence_start,
                self.relation_evidence_end,
                self.relation_evidence_text,
                self.relation_evidence_sha256,
            )
        )
        if (
            (matched and not (typed and party_evidence and relation_evidence))
            or (not matched and (typed or party_evidence or relation_evidence))
            or self.party_definition_sha256
            != _optional_text_sha256(self.party_definition_text)
            or self.relation_evidence_sha256
            != _optional_text_sha256(self.relation_evidence_text)
            or not _valid_span(self.party_definition_start, self.party_definition_end)
            or not _valid_span(self.relation_evidence_start, self.relation_evidence_end)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("party-relation decision differs")
        return self


class StrongLeaderPullbackSecPartyRelationAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-sec-party-relation-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["source_party_relations_adjudicated"] = (
        "source_party_relations_adjudicated"
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
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[61] = EXPECTED_CASE_COUNT
    matched_relation_count: int = Field(ge=0, le=61)
    ambiguous_relation_count: int = Field(ge=0, le=61)
    unsupported_relation_count: int = Field(ge=0, le=61)
    resolution_state_counts: tuple[tuple[str, int], ...]
    relation_topology_counts: tuple[tuple[str, int], ...]
    listed_equity_consideration_case_count: int = Field(ge=0, le=61)
    decisions: tuple[SecPartyRelationDecisionV1, ...]
    source_party_relation_evidence_count: int = Field(ge=0, le=61)
    counterparty_stable_id_assignment_count: Literal[0] = 0
    successor_stable_id_assignment_count: Literal[0] = 0
    consideration_issuer_stable_id_assignment_count: Literal[0] = 0
    canonical_party_identity_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackSecPartyRelationAdjudicationV1":
        resolutions = Counter(item.resolution_state for item in self.decisions)
        topologies = Counter(
            item.relation_topology
            for item in self.decisions
            if item.relation_topology is not None
        )
        if (
            len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or {item.request_sequence for item in self.decisions}
            != _REGISTERED_SEQUENCES
            or self.matched_relation_count != resolutions["matched"]
            or self.ambiguous_relation_count != resolutions["ambiguous"]
            or self.unsupported_relation_count != resolutions["unsupported"]
            or self.resolution_state_counts != _ordered(resolutions)
            or self.relation_topology_counts != _ordered(topologies)
            or self.listed_equity_consideration_case_count
            != sum(item.listed_equity_consideration for item in self.decisions)
            or self.source_party_relation_evidence_count
            != self.matched_relation_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("party-relation adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSecPartyRelationAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackSecPartyRelationAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_sec_party_relation_adjudication(
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
    consideration_root: Path,
    consideration_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecPartyRelationAdjudicationResult:
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
        consideration = read_strong_leader_pullback_sec_consideration_adjudication(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            cover=cover,
            events=events,
            reasons=reasons,
            consideration=consideration,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_sec_party_relation_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSecPartyRelationAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackSecPartyRelationAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation report bytes are not canonical"
        )
    return StrongLeaderPullbackSecPartyRelationAdjudicationResult(
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
    consideration: StrongLeaderPullbackSecConsiderationAdjudicationResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSecPartyRelationAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation revision is invalid"
        )
    if source.manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation source manifest is unavailable"
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
        or consideration.report.plan_sha256 != plan.plan_sha256
        or consideration.report.source_manifest_sha256 != source.manifest_sha256
        or consideration.report.cover_adjudication_report_sha256 != cover.report_sha256
        or consideration.report.transaction_event_report_sha256 != events.report_sha256
        or consideration.report.termination_reason_report_sha256
        != reasons.report_sha256
        or events.report.matched_event_count != EXPECTED_CASE_COUNT
        or reasons.report.matched_reason_count != EXPECTED_CASE_COUNT
        or consideration.report.matched_consideration_count != EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation input bindings differ"
        )
    identities = {
        item.request_sequence: item
        for item in cover.report.cover_documents
        if item.resolution_state == "matched_in_source_lifecycle_window"
        and item.transaction_structure_state == "8k_item_2_01_candidate_scope"
    }
    event_decisions = {item.request_sequence: item for item in events.report.decisions}
    reason_decisions = {item.request_sequence: item for item in reasons.report.decisions}
    consideration_decisions = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    if not (
        set(identities)
        == set(event_decisions)
        == set(reason_decisions)
        == set(consideration_decisions)
    ):
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation decision populations differ"
        )
    if set(event_decisions) != _REGISTERED_SEQUENCES:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation registered population differs"
        )
    decisions = tuple(
        _document_decision(
            event=event_decisions[sequence],
            identity=identities[sequence],
            termination=reason_decisions[sequence],
            consideration=consideration_decisions[sequence],
            path=source.output_root / f"request={sequence:06d}" / DOCUMENT_FILE,
        )
        for sequence in sorted(event_decisions)
    )
    resolutions = Counter(item.resolution_state for item in decisions)
    topologies = Counter(
        item.relation_topology
        for item in decisions
        if item.relation_topology is not None
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "plan_sha256": plan.plan_sha256,
        "source_manifest_sha256": source.manifest_sha256,
        "cover_adjudication_report_sha256": cover.report_sha256,
        "cover_adjudication_logical_fingerprint": cover.report.logical_fingerprint,
        "transaction_event_report_sha256": events.report_sha256,
        "transaction_event_logical_fingerprint": events.report.logical_fingerprint,
        "termination_reason_report_sha256": reasons.report_sha256,
        "termination_reason_logical_fingerprint": reasons.report.logical_fingerprint,
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": consideration.report.logical_fingerprint,
        "matched_relation_count": resolutions["matched"],
        "ambiguous_relation_count": resolutions["ambiguous"],
        "unsupported_relation_count": resolutions["unsupported"],
        "resolution_state_counts": _ordered(resolutions),
        "relation_topology_counts": _ordered(topologies),
        "listed_equity_consideration_case_count": sum(
            item.listed_equity_consideration for item in decisions
        ),
        "decisions": decisions,
        "source_party_relation_evidence_count": resolutions["matched"],
    }
    provisional = StrongLeaderPullbackSecPartyRelationAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSecPartyRelationAdjudicationV1.model_validate(
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
    consideration: SecCommonShareConsiderationDecisionV1,
    path: Path,
) -> SecPartyRelationDecisionV1:
    raw = path.read_bytes()
    if (
        _sha256_bytes(raw) != event.document_sha256
        or event.document_sha256 != identity.document_sha256
        or event.document_sha256 != termination.document_sha256
        or event.document_sha256 != consideration.document_sha256
        or event.instrument_id != identity.instrument_id
        or event.instrument_id != termination.instrument_id
        or event.instrument_id != consideration.instrument_id
        or termination.transaction_event_fingerprint != event.logical_fingerprint
        or consideration.transaction_event_fingerprint != event.logical_fingerprint
        or consideration.termination_reason_fingerprint != termination.logical_fingerprint
        or event.selected_event_date is None
        or termination.resolution_state != "matched"
        or consideration.resolution_state != "matched"
    ):
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation source or prior decision identity differs"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation source document is not UTF-8"
        ) from exc
    parser = _DocumentParser()
    parser.feed(text)
    parser.close()
    introduction, item_two, _ = _transaction_scope(tuple(parser.nodes))
    scope = _normalized_text(f"{introduction} {item_two}")
    scope_sha256 = _sha256_bytes(scope.encode("utf-8"))
    if len(scope) != event.scope_character_count or scope_sha256 != event.scope_sha256:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation transaction scope differs"
        )
    party = _primary_party_definition_candidate(scope)
    relation = _primary_relation_candidate(scope)
    topology = _registered_topology(event.request_sequence)
    if party is None or relation is None or topology is None:
        state: ResolutionState = "unsupported"
        party = None
        relation = None
        topology = None
        disposition = None
        acquirer = None
        successor = None
        reasons = ("registered_source_party_relation_not_proven",)
    else:
        state = "matched"
        if topology == "target_survives_as_owned_subsidiary":
            disposition: TargetLegalEntityDisposition | None = (
                "target_legal_entity_survives"
            )
            acquirer: AcquirerRelationState | None = (
                "parent_or_acquirer_group_bound_in_source"
            )
            successor: SuccessorRelationState | None = (
                "target_legal_entity_is_surviving_entity"
            )
        elif topology == "target_absorbed_into_other_survivor":
            disposition = "target_legal_entity_is_absorbed"
            acquirer = "parent_or_acquirer_group_bound_in_source"
            successor = "other_legal_entity_is_surviving_entity"
        else:
            disposition = "target_legal_entity_is_absorbed"
            acquirer = "peer_combination_without_single_acquirer"
            successor = "new_holding_company_is_surviving_entity"
        reasons = (
            "exact_party_definition_clause_retained",
            "exact_survivor_relation_clause_retained",
            "finite_source_hash_bound_human_review_registry",
            "source_roles_are_not_global_party_identity_assignments",
            "target_security_is_bound_through_prior_common_share_evidence",
        )
    party_values = _evidence_values("party_definition", party)
    relation_values = _evidence_values("relation_evidence", relation)
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
        "consideration_fingerprint": consideration.logical_fingerprint,
        "transaction_completion_date": event.selected_event_date,
        "transaction_scope_sha256": scope_sha256,
        "resolution_state": state,
        "relation_topology": topology,
        "target_legal_entity_disposition": disposition,
        "acquirer_relation_state": acquirer,
        "successor_relation_state": successor,
        "listed_equity_consideration": (
            "listed_equity" in consideration.consideration_components
        ),
        **party_values,
        **relation_values,
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = SecPartyRelationDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecPartyRelationDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _primary_party_definition_candidate(
    scope: str,
) -> tuple[int, int, str] | None:
    candidates = tuple(
        clause
        for clause in _clause_spans(scope)
        if _AGREEMENT_RE.search(clause[2]) and _PARTY_CONNECTOR_RE.search(clause[2])
    )
    if not candidates:
        return None
    selected = candidates[0]
    if len(selected[2]) > MAXIMUM_EVIDENCE_TEXT_CHARS:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "selected party-definition clause exceeds bounded size"
        )
    return selected


def _primary_relation_candidate(scope: str) -> tuple[int, int, str] | None:
    candidates = tuple(
        clause
        for clause in _clause_spans(scope)
        if _MERGER_RELATION_RE.search(clause[2]) and _SURVIVOR_RE.search(clause[2])
    )
    if not candidates:
        return None
    completed = tuple(
        clause
        for clause in candidates
        if re.search(
            r"\b(?:Closing Date|completed|completion|consummat(?:ed|ion)|"
            r"On (?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December))\b",
            clause[2],
            re.IGNORECASE,
        )
    )
    selected = (completed or candidates)[0]
    if len(selected[2]) > MAXIMUM_EVIDENCE_TEXT_CHARS:
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "selected survivor-relation clause exceeds bounded size"
        )
    return selected


def _registered_topology(sequence: int) -> RelationTopology | None:
    if sequence in _TARGET_SURVIVES_SEQUENCES:
        return "target_survives_as_owned_subsidiary"
    if sequence in _TARGET_ABSORBED_SEQUENCES:
        return "target_absorbed_into_other_survivor"
    if sequence in _NEW_HOLDING_COMPANY_SEQUENCES:
        return "target_and_peer_absorbed_into_new_holding_company"
    return None


def _evidence_values(
    prefix: str, evidence: tuple[int, int, str] | None
) -> dict[str, object]:
    if evidence is None:
        return {
            f"{prefix}_start": None,
            f"{prefix}_end": None,
            f"{prefix}_text": None,
            f"{prefix}_sha256": None,
        }
    start, end, text = evidence
    return {
        f"{prefix}_start": start,
        f"{prefix}_end": end,
        f"{prefix}_text": text,
        f"{prefix}_sha256": _sha256_bytes(text.encode("utf-8")),
    }


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "target_absorbed_sequences": sorted(_TARGET_ABSORBED_SEQUENCES),
            "target_survives_sequences": sorted(_TARGET_SURVIVES_SEQUENCES),
            "new_holding_company_sequences": sorted(
                _NEW_HOLDING_COMPANY_SEQUENCES
            ),
            "agreement_pattern": _AGREEMENT_RE.pattern,
            "party_connector_pattern": _PARTY_CONNECTOR_RE.pattern,
            "merger_relation_pattern": _MERGER_RELATION_RE.pattern,
            "survivor_pattern": _SURVIVOR_RE.pattern,
            "maximum_evidence_text_chars": MAXIMUM_EVIDENCE_TEXT_CHARS,
            "counterparty_stable_id_assignment": "forbidden",
            "successor_stable_id_assignment": "forbidden",
            "consideration_issuer_stable_id_assignment": "forbidden",
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackSecPartyRelationAdjudicationV1,
) -> StrongLeaderPullbackSecPartyRelationAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_sec_party_relation_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
                "existing party-relation report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation staging target exists"
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
    reread = read_strong_leader_pullback_sec_party_relation_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackSecPartyRelationAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation paths must be absolute"
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
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation custody or target is unsafe"
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
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "party-relation file metadata differs"
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


def _optional_text_sha256(value: str | None) -> str | None:
    return _sha256_bytes(value.encode("utf-8")) if value is not None else None


def _valid_span(start: int | None, end: int | None) -> bool:
    return (start is None and end is None) or (
        start is not None and end is not None and end > start
    )


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
        raise StrongLeaderPullbackSecPartyRelationAdjudicationError(
            "network access is prohibited during party-relation adjudication"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
