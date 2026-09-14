"""Election and payoff-source policy for the corrected terminal case."""

from __future__ import annotations

import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import strong_leader_pullback_sec_party_relation_adjudication as party
from tip_api.services import strong_leader_pullback_sec_transaction_event_adjudication as event
from tip_api.services import strong_leader_pullback_terminal_payoff_terms as payoff
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_core_adjudication as core_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source as source_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_trading_cessation_adjudication as cessation_reader,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-population-payoff-policy/1.0"
REPORT_FILE = "payoff-policy.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
MAXIMUM_POLICY_EVIDENCE_CHARS = 2048
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_DEFAULT_ELECTION_RE = re.compile(
    r"\bShares of Steelcase common stock\b[^.]{0,700}"
    r"\bdid not make an election\b[^.]{0,700}"
    r"\bmixed election consideration\.",
    re.IGNORECASE,
)
_REFERENCE_PRICE_RE = re.compile(
    r"\bThe [“\"]Parent Common Stock Reference Price[”\"][^.]{0,1000}"
    r"\$41\.1991\b[^.]{0,1000}\.",
    re.IGNORECASE,
)
_PRORATION_RE = re.compile(r"\bprorat(?:e|ed|ion|ing)\b", re.IGNORECASE)


class StrongLeaderPullbackTerminalPopulationPayoffPolicyError(RuntimeError):
    """Raised when the corrected terminal payoff policy cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalPopulationPolicyEvidenceV1(_FrozenModel):
    normalized_start: int = Field(ge=0)
    normalized_end: int = Field(ge=1)
    evidence_text: str = Field(min_length=1, max_length=MAXIMUM_POLICY_EVIDENCE_CHARS)
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str) -> str:
        if value != payoff._normalized_text(value):
            raise ValueError("terminal-population policy evidence differs")
        return value

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "TerminalPopulationPolicyEvidenceV1":
        if (
            self.normalized_end <= self.normalized_start
            or self.evidence_sha256
            != base._sha256_bytes(self.evidence_text.encode("utf-8"))
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population policy evidence differs")
        return self


class TerminalPopulationPayoffAlternativeV1(_FrozenModel):
    alternative_code: Literal["cash_election", "mixed_election", "stock_election"]
    term_keys: tuple[str, ...] = Field(min_length=1)
    default_if_no_valid_election: bool
    automatic_adjustment_applies: Literal[True] = True
    automatic_adjustment_details_resolved: Literal[False] = False
    proration_state: Literal["not_stated_in_retained_completion_scope"] = (
        "not_stated_in_retained_completion_scope"
    )
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("term_keys", mode="before")
    @classmethod
    def keys_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("terminal-population alternative terms differ")
        return values

    @model_validator(mode="after")
    def alternative_reconciles(self) -> "TerminalPopulationPayoffAlternativeV1":
        if self.logical_fingerprint != base._fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("terminal-population payoff alternative differs")
        return self


class StrongLeaderPullbackTerminalPopulationPayoffPolicyV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-payoff-policy/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["election_payoff_policy_adjudicated_not_valued"] = (
        "election_payoff_policy_adjudicated_not_valued"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    core_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    core_adjudication_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[1] = 1
    party_relation: party.SecPartyRelationDecisionV1
    source_party_relation_evidence_count: Literal[1] = 1
    consideration_structure: Literal["holder_election_cash_or_stock"] = (
        "holder_election_cash_or_stock"
    )
    listed_equity_issuer_locator: Literal["HNI"] = "HNI"
    normalized_terms: tuple[payoff.NormalizedPayoffTermV1, ...]
    source_numeric_payoff_term_count: Literal[5] = 5
    alternatives: tuple[TerminalPopulationPayoffAlternativeV1, ...]
    default_no_valid_election_alternative: Literal["mixed_election"] = (
        "mixed_election"
    )
    default_election_evidence: TerminalPopulationPolicyEvidenceV1
    source_calculation_reference_price_literal: Literal["$41.1991"] = "$41.1991"
    source_calculation_reference_price_normalized: Literal["41.1991"] = "41.1991"
    calculation_reference_price_evidence: TerminalPopulationPolicyEvidenceV1
    calculation_reference_price_is_terminal_market_value: Literal[False] = False
    actual_holder_election_known: Literal[False] = False
    automatic_adjustment_details_resolved: Literal[False] = False
    proration_state: Literal["not_stated_in_retained_completion_scope"] = (
        "not_stated_in_retained_completion_scope"
    )
    research_reference_policy: Literal[
        "default_no_valid_election_mixed_with_alternative_sensitivity"
    ] = "default_no_valid_election_mixed_with_alternative_sensitivity"
    consideration_issuer_stable_id_assignment_count: Literal[0] = 0
    normalized_payoff_term_count: Literal[5] = 5
    terminal_reference_value_count: Literal[0] = 0
    lifecycle_fact_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalPopulationPayoffPolicyV1":
        term_keys = tuple(item.term_key for item in self.normalized_terms)
        alternative_codes = tuple(item.alternative_code for item in self.alternatives)
        referenced = {
            key for alternative in self.alternatives for key in alternative.term_keys
        }
        defaults = tuple(
            item.alternative_code
            for item in self.alternatives
            if item.default_if_no_valid_election
        )
        if (
            self.party_relation.resolution_state != "matched"
            or self.party_relation.relation_topology
            != "target_absorbed_into_other_survivor"
            or not self.party_relation.listed_equity_consideration
            or term_keys != tuple(sorted(set(term_keys)))
            or len(term_keys) != 5
            or referenced != set(term_keys)
            or alternative_codes
            != ("cash_election", "mixed_election", "stock_election")
            or defaults != ("mixed_election",)
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population payoff policy differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationPayoffPolicyResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationPayoffPolicyV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_payoff_policy(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    core_adjudication_root: Path,
    core_adjudication_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationPayoffPolicyResult:
    """Adjudicate one election policy without valuation or outcomes."""

    with base._network_prohibited():
        plan = plan_reader.read_strong_leader_pullback_terminal_population_sec_source_plan(
            output_root=plan_root, output_custody_root=plan_custody_root
        )
        source = source_reader.read_strong_leader_pullback_terminal_population_sec_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=source_root,
            output_custody_root=source_custody_root,
        )
        core = core_reader.read_strong_leader_pullback_terminal_population_sec_core_adjudication(
            output_root=core_adjudication_root,
            output_custody_root=core_adjudication_custody_root,
        )
        cessation_result = cessation_reader.read_strong_leader_pullback_terminal_population_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            core=core,
            cessation=cessation_result,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_payoff_policy(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationPayoffPolicyResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationPayoffPolicyV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationPayoffPolicyResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, plan: object, source: object, core: object, cessation: object,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationPayoffPolicyV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy revision is invalid"
        )
    core_report = core.report
    cessation_report = cessation.report
    if (
        len(plan.report.cases) != 1
        or core_report.plan_sha256 != plan.report_sha256
        or core_report.source_manifest_sha256 != source.manifest_sha256
        or core_report.source_logical_fingerprint
        != source.manifest.logical_fingerprint
        or cessation_report.core_adjudication_report_sha256 != core.report_sha256
        or cessation_report.core_adjudication_logical_fingerprint
        != core_report.logical_fingerprint
        or cessation_report.decision.resolution_state != "matched"
        or core_report.common_share_consideration.resolution_state != "matched"
        or core_report.common_share_consideration.consideration_structure
        != "holder_election_cash_or_stock"
    ):
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy bindings differ"
        )
    consideration = core_report.common_share_consideration
    source_path = (
        source.output_root
        / f"request={consideration.request_sequence:06d}"
        / source_reader.DOCUMENT_FILE
    )
    scope = _transaction_scope(source_path, core_report.transaction_event)
    relation = _party_relation(core_report=core_report, source_path=source_path)
    terms = _normalized_terms(consideration.evidence_text)
    alternatives = _alternatives()
    default_evidence = _policy_evidence(scope, _DEFAULT_ELECTION_RE)
    reference_evidence = _policy_evidence(scope, _REFERENCE_PRICE_RE)
    if _PRORATION_RE.search(scope):
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population retained scope contains unadjudicated proration"
        )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "plan_sha256": plan.report_sha256,
        "source_manifest_sha256": source.manifest_sha256,
        "source_logical_fingerprint": source.manifest.logical_fingerprint,
        "core_adjudication_report_sha256": core.report_sha256,
        "core_adjudication_logical_fingerprint": core_report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation_report.logical_fingerprint,
        "party_relation": relation,
        "normalized_terms": terms,
        "alternatives": alternatives,
        "default_election_evidence": default_evidence,
        "calculation_reference_price_evidence": reference_evidence,
    }
    provisional = StrongLeaderPullbackTerminalPopulationPayoffPolicyV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationPayoffPolicyV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _transaction_scope(path: Path, transaction: object) -> str:
    raw = path.read_bytes()
    if base._sha256_bytes(raw) != transaction.document_sha256:
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy source differs"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy source is not UTF-8"
        ) from exc
    parser = event._DocumentParser()
    parser.feed(text)
    parser.close()
    introduction, item_two, _ = event._transaction_scope(tuple(parser.nodes))
    scope = payoff._normalized_text(f"{introduction} {item_two}")
    if (
        len(scope) != transaction.scope_character_count
        or base._sha256_bytes(scope.encode("utf-8")) != transaction.scope_sha256
    ):
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy scope differs"
        )
    return scope


def _party_relation(*, core_report: object, source_path: Path) -> object:
    event_decision = core_report.transaction_event
    identity = core_report.cover_identity
    termination = core_report.termination_reason
    consideration = core_report.common_share_consideration
    raw = source_path.read_bytes()
    parser = event._DocumentParser()
    parser.feed(raw.decode("utf-8"))
    parser.close()
    introduction, item_two, _ = event._transaction_scope(tuple(parser.nodes))
    scope = payoff._normalized_text(f"{introduction} {item_two}")
    party_evidence = party._primary_party_definition_candidate(scope)
    relation_candidates = tuple(
        item
        for item in party._clause_spans(scope)
        if "separate existence of Steelcase ceased" in item[2]
        and "Merger Sub LLC continued as the surviving entity" in item[2]
    )
    relation_evidence = (
        relation_candidates[0] if len(relation_candidates) == 1 else None
    )
    if (
        party_evidence is None
        or relation_evidence is None
        or "acquisition by HNI Corporation" not in party_evidence[2]
        or "of Steelcase Inc." not in party_evidence[2]
        or "separate existence of Steelcase ceased" not in relation_evidence[2]
        or "Merger Sub LLC continued as the surviving entity"
        not in relation_evidence[2]
        or "wholly owned subsidiary of HNI" not in relation_evidence[2]
    ):
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population party relation is unsupported"
        )
    values = {
        "request_sequence": event_decision.request_sequence,
        "instrument_id": event_decision.instrument_id,
        "accession_number": event_decision.accession_number,
        "filing_date": event_decision.filing_date,
        "acceptance_datetime": event_decision.acceptance_datetime,
        "document_sha256": event_decision.document_sha256,
        "identity_decision_fingerprint": identity.logical_fingerprint,
        "transaction_event_fingerprint": event_decision.logical_fingerprint,
        "termination_reason_fingerprint": termination.logical_fingerprint,
        "consideration_fingerprint": consideration.logical_fingerprint,
        "transaction_completion_date": event_decision.selected_event_date,
        "transaction_scope_sha256": event_decision.scope_sha256,
        "resolution_state": "matched",
        "relation_topology": "target_absorbed_into_other_survivor",
        "target_legal_entity_disposition": "target_legal_entity_is_absorbed",
        "acquirer_relation_state": "parent_or_acquirer_group_bound_in_source",
        "successor_relation_state": "other_legal_entity_is_surviving_entity",
        "listed_equity_consideration": True,
        **party._evidence_values("party_definition", party_evidence),
        **party._evidence_values("relation_evidence", relation_evidence),
        "decision_reasons": tuple(
            sorted(
                {
                    "corrected_case_source_relation_independently_reviewed",
                    "exact_party_definition_clause_retained",
                    "exact_survivor_relation_clause_retained",
                    "source_roles_are_not_global_party_identity_assignments",
                    "target_security_is_bound_through_prior_common_share_evidence",
                }
            )
        ),
    }
    provisional = party.SecPartyRelationDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return party.SecPartyRelationDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _normalized_terms(text: str) -> tuple[payoff.NormalizedPayoffTermV1, ...]:
    specs = (
        payoff._TermSpec(
            "cash_election_cash", "cash_usd_per_target_share", "$16.19", "16.19"
        ),
        payoff._TermSpec(
            "cash_election_stock_ratio",
            "listed_equity_shares_per_target_share",
            "0.0009",
            "0.000900",
        ),
        payoff._TermSpec(
            "mixed_election_cash", "cash_usd_per_target_share", "$7.20", "7.20"
        ),
        payoff._TermSpec(
            "mixed_election_stock_ratio",
            "listed_equity_shares_per_target_share",
            "0.2192",
            "0.219200",
        ),
        payoff._TermSpec(
            "stock_election_stock_ratio",
            "listed_equity_shares_per_target_share",
            "0.3940",
            "0.394000",
        ),
    )
    return tuple(
        sorted(
            (payoff._normalized_term(text, spec) for spec in specs),
            key=lambda item: item.term_key,
        )
    )


def _alternatives() -> tuple[TerminalPopulationPayoffAlternativeV1, ...]:
    specs = {
        "cash_election": (
            ("cash_election_cash", "cash_election_stock_ratio"),
            False,
        ),
        "mixed_election": (
            ("mixed_election_cash", "mixed_election_stock_ratio"),
            True,
        ),
        "stock_election": (("stock_election_stock_ratio",), False),
    }
    values = []
    for code, (term_keys, default) in sorted(specs.items()):
        item_values = {
            "alternative_code": code,
            "term_keys": tuple(sorted(term_keys)),
            "default_if_no_valid_election": default,
        }
        provisional = TerminalPopulationPayoffAlternativeV1.model_construct(
            **item_values, logical_fingerprint="0" * 64
        )
        values.append(
            TerminalPopulationPayoffAlternativeV1.model_validate(
                {
                    **item_values,
                    "logical_fingerprint": base._fingerprint(
                        provisional.model_dump(
                            mode="json", exclude={"logical_fingerprint"}
                        )
                    ),
                }
            )
        )
    return tuple(values)


def _policy_evidence(scope: str, pattern: re.Pattern[str]) -> TerminalPopulationPolicyEvidenceV1:
    matches = tuple(pattern.finditer(scope))
    if len(matches) != 1:
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population policy evidence is not unique"
        )
    match = matches[0]
    evidence_text = match.group(0)
    values = {
        "normalized_start": match.start(),
        "normalized_end": match.end(),
        "evidence_text": evidence_text,
        "evidence_sha256": base._sha256_bytes(evidence_text.encode("utf-8")),
    }
    provisional = TerminalPopulationPolicyEvidenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalPopulationPolicyEvidenceV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _ruleset_fingerprint() -> str:
    return base._fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "party_relation": "independent_target_absorbed_hni_acquirer_group",
            "term_precision": {"cash": "0.01", "listed_equity_ratio": "0.000001"},
            "alternative_codes": ["cash_election", "mixed_election", "stock_election"],
            "default_election_pattern": _DEFAULT_ELECTION_RE.pattern,
            "reference_price_pattern": _REFERENCE_PRICE_RE.pattern,
            "proration_pattern": _PRORATION_RE.pattern,
            "research_reference_policy": (
                "default_no_valid_election_mixed_with_alternative_sensitivity"
            ),
            "actual_holder_election": "unknown",
            "listed_consideration_identity": "unassigned",
            "terminal_value": "not_calculated",
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationPayoffPolicyV1,
) -> StrongLeaderPullbackTerminalPopulationPayoffPolicyResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_payoff_policy(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
                "existing terminal-population payoff-policy report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
                "terminal-population payoff-policy report exceeds byte ceiling"
            )
        source_base._write_exclusive(partial / REPORT_FILE, raw)
        source_base._fsync_directory(partial)
        partial.replace(target)
        source_base._fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            source_base._fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_terminal_population_payoff_policy(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPopulationPayoffPolicyResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy paths must be absolute"
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
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy target is unsafe"
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
        raise StrongLeaderPullbackTerminalPopulationPayoffPolicyError(
            "terminal-population payoff-policy output is unsafe"
        )
    return target
