"""Normalized source terms for first-strategy terminal-payoff research."""

from __future__ import annotations

import os
import re
import shutil
import socket
import stat
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    ConsiderationStructure,
    SecCommonShareConsiderationDecisionV1,
    StrongLeaderPullbackSecConsiderationAdjudicationResult,
    _fingerprint,
    _json_bytes,
    _normalized_text,
    _sha256_bytes,
    read_strong_leader_pullback_sec_consideration_adjudication,
)
from tip_api.services.strong_leader_pullback_sec_party_relation_adjudication import (
    SecPartyRelationDecisionV1,
    StrongLeaderPullbackSecPartyRelationAdjudicationResult,
    read_strong_leader_pullback_sec_party_relation_adjudication,
)
from tip_api.services.strong_leader_pullback_trading_cessation_adjudication import (
    StrongLeaderPullbackTradingCessationAdjudicationResult,
    TradingCessationDecisionV1,
    read_strong_leader_pullback_trading_cessation_adjudication,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-payoff-terms/1.0"
REPORT_FILE = "terminal-payoff-terms.json"
EXPECTED_CASE_COUNT = 61
MAXIMUM_REPORT_BYTES = 3 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_DECIMAL_PATTERN = r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"

TermKind = Literal[
    "cash_usd_per_target_share",
    "listed_equity_shares_per_target_share",
    "cvr_units_per_target_share",
    "cvr_max_cash_usd_per_target_share",
    "unlisted_equity_units_per_target_share",
]
PayoffProfile = Literal[
    "fixed_cash_fully_specified",
    "listed_equity_market_value_required",
    "contingent_value_right_unvalued",
    "holder_election_unresolved",
    "unlisted_unit_and_election_unresolved",
]
TerminalCandidateState = Literal[
    "fixed_cash_and_timing_ready",
    "cessation_timing_not_matched",
    "listed_security_identity_and_market_value_required",
    "contingent_value_realization_unresolved",
    "holder_election_or_proration_unresolved",
    "unlisted_unit_value_unresolved",
]


@dataclass(frozen=True, slots=True)
class _TermSpec:
    key: str
    kind: TermKind
    source_literal: str
    normalized_value: str


@dataclass(frozen=True, slots=True)
class _AlternativeSpec:
    code: str
    term_keys: tuple[str, ...]
    default_if_no_valid_election: bool
    subject_to_proration: bool


@dataclass(frozen=True, slots=True)
class _CaseSpec:
    structure: ConsiderationStructure
    profile: PayoffProfile
    terms: tuple[_TermSpec, ...]
    alternatives: tuple[_AlternativeSpec, ...] = ()
    listed_equity_issuer_locator: str | None = None


def _cash(key: str, literal: str, value: str) -> _TermSpec:
    return _TermSpec(key, "cash_usd_per_target_share", literal, value)


def _ratio(key: str, literal: str, value: str) -> _TermSpec:
    return _TermSpec(
        key, "listed_equity_shares_per_target_share", literal, value
    )


_CASH_ONLY = {
    7: ("$221.50", "221.50"),
    11: ("$10.25", "10.25"),
    20: ("$15.50", "15.50"),
    26: ("$27.00", "27.00"),
    28: ("$105.00", "105.00"),
    38: ("$14.50", "14.50"),
    55: ("$24.50", "24.50"),
    59: ("$180.00", "180.00"),
    64: ("$17.00", "17.00"),
    68: ("$21.50", "21.50"),
    72: ("$28", "28.00"),
    74: ("$26.00", "26.00"),
    79: ("$9.15", "9.15"),
    90: ("$72.50", "72.50"),
    99: ("$65.00", "65.00"),
    109: ("$72.00", "72.00"),
    113: ("$25.00", "25.00"),
    115: ("$47.00", "47.00"),
    122: ("$24.00", "24.00"),
    129: ("$101", "101.00"),
    136: ("$53.00", "53.00"),
    139: ("$31.50", "31.50"),
    143: ("$58.00", "58.00"),
    147: ("$38.50", "38.50"),
    150: ("$59.00", "59.00"),
    152: ("$210", "210.00"),
    156: ("$20.50", "20.50"),
    161: ("$22.00", "22.00"),
    166: ("$53.00", "53.00"),
    181: ("$14.00", "14.00"),
    187: ("$210.00", "210.00"),
    190: ("$22.00", "22.00"),
    200: ("$31.00", "31.00"),
    204: ("$80.70", "80.70"),
    208: ("$124.00", "124.00"),
    211: ("$42.15", "42.15"),
    214: ("$83.50", "83.50"),
}

_FIXED_CASH_AND_STOCK = {
    1: ("$0.61", "0.61", "1.8185", "1.818500", "Rayonier"),
    35: ("$10.00", "10.00", "1.1523", "1.152300", "Acuren"),
    158: ("$15.00", "15.00", "0.4883", "0.488300", "IonQ"),
}

_STOCK_ONLY = {
    14: ("11.00", "11.000000", "Rocket"),
    40: ("0.344", "0.344000", "Omnicom"),
    95: ("1.436", "1.436000", "Compass"),
    107: ("0.1400", "0.140000", "Public Storage"),
    124: ("0.5237", "0.523700", "Newco"),
    174: ("1.8663", "1.866300", "Fifth Third"),
    178: ("1.95", "1.950000", "Huntington"),
    184: ("0.1955", "0.195500", "Boeing"),
    197: ("0.9150", "0.915000", "Columbia"),
    218: ("2.793", "2.793000", "Vivmark"),
}

_CVR = {
    45: ("$65.60", "65.60", None, None, "one contractual contingent value right"),
    49: ("$14.50", "14.50", "$6.00", "6.00", "one non-tradeable contingent value right"),
    52: ("$54.00", "54.00", "$6.00", "6.00", "one contractual contingent value right"),
    83: ("$41.00", "41.00", "$4.00", "4.00", "one contractual, non-transferable contingent value right"),
    104: ("$10.50", "10.50", "$3.00", "3.00", "one non-tradable contingent value right"),
    118: ("$76.00", "76.00", None, None, "one (1) CVR"),
    172: (None, None, None, None, "one (1) CVR per Share"),
}


def _case_specs() -> dict[int, _CaseSpec]:
    specs = {
        sequence: _CaseSpec(
            structure="cash_only",
            profile="fixed_cash_fully_specified",
            terms=(_cash("guaranteed_cash", literal, value),),
        )
        for sequence, (literal, value) in _CASH_ONLY.items()
    }
    specs.update(
        {
            sequence: _CaseSpec(
                structure="fixed_cash_and_stock",
                profile="listed_equity_market_value_required",
                terms=(
                    _cash("guaranteed_cash", cash_literal, cash_value),
                    _ratio("listed_equity_ratio", ratio_literal, ratio_value),
                ),
                listed_equity_issuer_locator=issuer,
            )
            for sequence, (
                cash_literal,
                cash_value,
                ratio_literal,
                ratio_value,
                issuer,
            ) in _FIXED_CASH_AND_STOCK.items()
        }
    )
    specs.update(
        {
            sequence: _CaseSpec(
                structure="stock_only",
                profile="listed_equity_market_value_required",
                terms=(_ratio("listed_equity_ratio", literal, value),),
                listed_equity_issuer_locator=issuer,
            )
            for sequence, (literal, value, issuer) in _STOCK_ONLY.items()
        }
    )
    for sequence, (cash_literal, cash_value, cap_literal, cap_value, unit_literal) in _CVR.items():
        terms = []
        if cash_literal is not None and cash_value is not None:
            terms.append(_cash("guaranteed_cash", cash_literal, cash_value))
        terms.append(
            _TermSpec(
                "cvr_units",
                "cvr_units_per_target_share",
                unit_literal,
                "1.000000",
            )
        )
        if cap_literal is not None and cap_value is not None:
            terms.append(
                _TermSpec(
                    "cvr_max_cash",
                    "cvr_max_cash_usd_per_target_share",
                    cap_literal,
                    cap_value,
                )
            )
        specs[sequence] = _CaseSpec(
            structure="cash_plus_contingent_value_right",
            profile="contingent_value_right_unvalued",
            terms=tuple(terms),
        )
    specs[87] = _CaseSpec(
        structure="holder_election_cash_or_stock",
        profile="holder_election_unresolved",
        terms=(
            _cash("cash_election_cash", "$505.00", "505.00"),
            _ratio("stock_election_ratio", "20.200", "20.200000"),
        ),
        alternatives=(
            _AlternativeSpec("cash_election", ("cash_election_cash",), False, True),
            _AlternativeSpec("stock_election", ("stock_election_ratio",), True, True),
        ),
        listed_equity_issuer_locator="QXO",
    )
    specs[92] = _CaseSpec(
        structure="holder_election_cash_or_stock",
        profile="holder_election_unresolved",
        terms=(
            _cash("cash_election_cash", "$63.89", "63.89"),
            _cash("mixed_election_cash", "$10.00", "10.00"),
            _ratio("mixed_election_ratio", "0.6840", "0.684000"),
            _ratio("stock_election_ratio", "0.8110", "0.811000"),
        ),
        alternatives=(
            _AlternativeSpec("cash_election", ("cash_election_cash",), False, True),
            _AlternativeSpec(
                "mixed_election",
                ("mixed_election_cash", "mixed_election_ratio"),
                True,
                True,
            ),
            _AlternativeSpec("stock_election", ("stock_election_ratio",), False, True),
        ),
        listed_equity_issuer_locator="CECO",
    )
    specs[100] = _CaseSpec(
        structure="holder_election_cash_or_cash_plus_unlisted_unit",
        profile="unlisted_unit_and_election_unresolved",
        terms=(
            _cash("cash_election_cash", "$63.00", "63.00"),
            _cash("mixed_election_cash", "$57.00", "57.00"),
            _TermSpec(
                "mixed_election_unlisted_units",
                "unlisted_equity_units_per_target_share",
                "one unlisted limited liability company unit",
                "1.000000",
            ),
        ),
        alternatives=(
            _AlternativeSpec("cash_election", ("cash_election_cash",), False, False),
            _AlternativeSpec(
                "mixed_election",
                ("mixed_election_cash", "mixed_election_unlisted_units"),
                False,
                True,
            ),
        ),
    )
    specs[194] = _CaseSpec(
        structure="holder_election_cash_or_stock",
        profile="holder_election_unresolved",
        terms=(
            _cash("cash_election_cash", "$24.00", "24.00"),
            _ratio("stock_election_ratio", "0.1168", "0.116800"),
        ),
        alternatives=(
            _AlternativeSpec("cash_election", ("cash_election_cash",), True, False),
            _AlternativeSpec("stock_election", ("stock_election_ratio",), False, False),
        ),
        listed_equity_issuer_locator="DICK’S Sporting Goods",
    )
    return specs


_CASE_SPECS = _case_specs()


class StrongLeaderPullbackTerminalPayoffTermsError(RuntimeError):
    """Raised when bounded terminal-payoff terms cannot be reconciled."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NormalizedPayoffTermV1(_FrozenModel):
    term_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    term_kind: TermKind
    source_literal: str = Field(min_length=1, max_length=128)
    normalized_value: str = Field(pattern=_DECIMAL_PATTERN)
    evidence_start: int = Field(ge=0)
    evidence_end: int = Field(ge=1)
    evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def term_reconciles(self) -> "NormalizedPayoffTermV1":
        if (
            self.evidence_end <= self.evidence_start
            or self.evidence_sha256
            != _sha256_bytes(self.source_literal.encode("utf-8"))
            or self.normalized_value
            != _canonical_decimal(self.term_kind, self.normalized_value)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("normalized payoff term differs")
        return self


class PayoffAlternativeV1(_FrozenModel):
    alternative_code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    term_keys: tuple[str, ...] = Field(min_length=1)
    default_if_no_valid_election: bool
    subject_to_proration: bool
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("term_keys", mode="before")
    @classmethod
    def keys_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("alternative term keys differ")
        return values

    @model_validator(mode="after")
    def alternative_reconciles(self) -> "PayoffAlternativeV1":
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("payoff alternative differs")
        return self


class TerminalPayoffTermsDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    consideration_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    party_relation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_structure: ConsiderationStructure
    cessation_resolution_state: Literal["matched", "conflicting", "unsupported"]
    payoff_profile: PayoffProfile
    terminal_candidate_state: TerminalCandidateState
    listed_equity_issuer_locator: str | None = Field(default=None, max_length=128)
    consideration_evidence_text: str = Field(min_length=1, max_length=4096)
    consideration_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    terms: tuple[NormalizedPayoffTermV1, ...] = Field(min_length=1)
    alternatives: tuple[PayoffAlternativeV1, ...]
    single_deterministic_cash_term_complete: bool
    fractional_share_cash_adjustment: bool
    terminal_outcome_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("consideration_evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str) -> str:
        if value != _normalized_text(value):
            raise ValueError("payoff-term evidence is not normalized")
        return value

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("payoff-term reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "TerminalPayoffTermsDecisionV1":
        term_keys = tuple(item.term_key for item in self.terms)
        alternatives = tuple(item.alternative_code for item in self.alternatives)
        referenced = {key for item in self.alternatives for key in item.term_keys}
        if (
            term_keys != tuple(sorted(set(term_keys)))
            or alternatives != tuple(sorted(set(alternatives)))
            or not referenced.issubset(set(term_keys))
            or self.consideration_evidence_sha256
            != _sha256_bytes(self.consideration_evidence_text.encode("utf-8"))
            or any(
                self.consideration_evidence_text[
                    item.evidence_start : item.evidence_end
                ]
                != item.source_literal
                for item in self.terms
            )
            or self.single_deterministic_cash_term_complete
            != (self.consideration_structure == "cash_only")
            or not _decision_matches_registry(self)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal payoff terms decision differs")
        return self


class StrongLeaderPullbackTerminalPayoffTermsV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-payoff-terms/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["terminal_payoff_source_terms_normalized"] = (
        "terminal_payoff_source_terms_normalized"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    party_relation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    party_relation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[61] = EXPECTED_CASE_COUNT
    source_numeric_term_count: int = Field(ge=1)
    fixed_cash_payoff_term_count: int = Field(ge=0, le=61)
    listed_equity_ratio_case_count: int = Field(ge=0, le=61)
    cvr_case_count: int = Field(ge=0, le=61)
    holder_election_case_count: int = Field(ge=0, le=61)
    unlisted_unit_case_count: int = Field(ge=0, le=61)
    fractional_share_cash_adjustment_count: int = Field(ge=0, le=61)
    fixed_cash_and_timing_ready_count: int = Field(ge=0, le=61)
    payoff_profile_counts: tuple[tuple[str, int], ...]
    terminal_candidate_state_counts: tuple[tuple[str, int], ...]
    decisions: tuple[TerminalPayoffTermsDecisionV1, ...]
    successor_stable_id_assignment_count: Literal[0] = 0
    consideration_issuer_stable_id_assignment_count: Literal[0] = 0
    canonical_lifecycle_fact_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackTerminalPayoffTermsV1":
        profiles = Counter(item.payoff_profile for item in self.decisions)
        states = Counter(item.terminal_candidate_state for item in self.decisions)
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(_CASE_SPECS))
            or self.source_numeric_term_count
            != sum(len(item.terms) for item in self.decisions)
            or self.fixed_cash_payoff_term_count
            != sum(item.single_deterministic_cash_term_complete for item in self.decisions)
            or self.listed_equity_ratio_case_count
            != sum(item.listed_equity_issuer_locator is not None for item in self.decisions)
            or self.cvr_case_count
            != profiles["contingent_value_right_unvalued"]
            or self.holder_election_case_count != sum(bool(item.alternatives) for item in self.decisions)
            or self.unlisted_unit_case_count
            != profiles["unlisted_unit_and_election_unresolved"]
            or self.fractional_share_cash_adjustment_count
            != sum(item.fractional_share_cash_adjustment for item in self.decisions)
            or self.fixed_cash_and_timing_ready_count
            != states["fixed_cash_and_timing_ready"]
            or self.payoff_profile_counts != _ordered(profiles)
            or self.terminal_candidate_state_counts != _ordered(states)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal payoff terms report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPayoffTermsResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPayoffTermsV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_payoff_terms(
    *,
    consideration_root: Path,
    consideration_custody_root: Path,
    party_relation_root: Path,
    party_relation_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPayoffTermsResult:
    with _network_prohibited():
        consideration = read_strong_leader_pullback_sec_consideration_adjudication(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        parties = read_strong_leader_pullback_sec_party_relation_adjudication(
            output_root=party_relation_root,
            output_custody_root=party_relation_custody_root,
        )
        cessation = read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        report = _build_report(
            consideration=consideration,
            parties=parties,
            cessation=cessation,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_payoff_terms(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPayoffTermsResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPayoffTermsV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms report bytes are not canonical"
        )
    return StrongLeaderPullbackTerminalPayoffTermsResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    consideration: StrongLeaderPullbackSecConsiderationAdjudicationResult,
    parties: StrongLeaderPullbackSecPartyRelationAdjudicationResult,
    cessation: StrongLeaderPullbackTradingCessationAdjudicationResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPayoffTermsV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms revision is invalid"
        )
    if (
        parties.report.consideration_report_sha256 != consideration.report_sha256
        or parties.report.consideration_logical_fingerprint
        != consideration.report.logical_fingerprint
        or cessation.report.party_relation_report_sha256 != parties.report_sha256
        or cessation.report.party_relation_logical_fingerprint
        != parties.report.logical_fingerprint
        or consideration.report.matched_consideration_count != EXPECTED_CASE_COUNT
        or parties.report.matched_relation_count != EXPECTED_CASE_COUNT
        or cessation.report.lifecycle_case_count != EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms input bindings differ"
        )
    considerations = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    party_decisions = {item.request_sequence: item for item in parties.report.decisions}
    cessation_decisions = {
        item.request_sequence: item for item in cessation.report.decisions
    }
    if not (
        set(considerations)
        == set(party_decisions)
        == set(cessation_decisions)
        == set(_CASE_SPECS)
    ):
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms population differs"
        )
    decisions = tuple(
        _document_decision(
            consideration=considerations[sequence],
            party=party_decisions[sequence],
            cessation=cessation_decisions[sequence],
        )
        for sequence in sorted(_CASE_SPECS)
    )
    profiles = Counter(item.payoff_profile for item in decisions)
    states = Counter(item.terminal_candidate_state for item in decisions)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": consideration.report.logical_fingerprint,
        "party_relation_report_sha256": parties.report_sha256,
        "party_relation_logical_fingerprint": parties.report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation.report.logical_fingerprint,
        "source_numeric_term_count": sum(len(item.terms) for item in decisions),
        "fixed_cash_payoff_term_count": sum(
            item.single_deterministic_cash_term_complete for item in decisions
        ),
        "listed_equity_ratio_case_count": sum(
            item.listed_equity_issuer_locator is not None for item in decisions
        ),
        "cvr_case_count": profiles["contingent_value_right_unvalued"],
        "holder_election_case_count": sum(bool(item.alternatives) for item in decisions),
        "unlisted_unit_case_count": profiles[
            "unlisted_unit_and_election_unresolved"
        ],
        "fractional_share_cash_adjustment_count": sum(
            item.fractional_share_cash_adjustment for item in decisions
        ),
        "fixed_cash_and_timing_ready_count": states[
            "fixed_cash_and_timing_ready"
        ],
        "payoff_profile_counts": _ordered(profiles),
        "terminal_candidate_state_counts": _ordered(states),
        "decisions": decisions,
    }
    provisional = StrongLeaderPullbackTerminalPayoffTermsV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPayoffTermsV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_decision(
    *,
    consideration: SecCommonShareConsiderationDecisionV1,
    party: SecPartyRelationDecisionV1,
    cessation: TradingCessationDecisionV1,
) -> TerminalPayoffTermsDecisionV1:
    if (
        consideration.instrument_id != party.instrument_id
        or consideration.instrument_id != cessation.instrument_id
        or party.consideration_fingerprint != consideration.logical_fingerprint
        or cessation.party_relation_fingerprint != party.logical_fingerprint
        or consideration.resolution_state != "matched"
        or party.resolution_state != "matched"
        or consideration.evidence_text is None
        or consideration.evidence_sha256 is None
    ):
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms source decision differs"
        )
    spec = _CASE_SPECS[consideration.request_sequence]
    if consideration.consideration_structure != spec.structure:
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms registered structure differs"
        )
    if party.listed_equity_consideration != (
        spec.listed_equity_issuer_locator is not None
    ):
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff listed-equity profile differs"
        )
    terms = tuple(
        sorted(
            (_normalized_term(consideration.evidence_text, item) for item in spec.terms),
            key=lambda item: item.term_key,
        )
    )
    alternatives = tuple(
        sorted(
            (_alternative(item) for item in spec.alternatives),
            key=lambda item: item.alternative_code,
        )
    )
    candidate_state = _candidate_state(
        profile=spec.profile,
        cessation_state=cessation.resolution_state,
    )
    reasons = {
        "numeric_terms_are_source_literal_bound",
        "terminal_outcome_not_calculated",
    }
    if spec.listed_equity_issuer_locator is not None:
        reasons.add("source_local_issuer_name_is_not_a_stable_identity")
    if spec.profile == "contingent_value_right_unvalued":
        keys = {item.key for item in spec.terms}
        if "guaranteed_cash" not in keys:
            reasons.add("guaranteed_cash_is_symbolic_in_selected_clause")
        if "cvr_max_cash" not in keys:
            reasons.add("cvr_maximum_not_stated_in_selected_clause")
    if consideration.fractional_share_cash_adjustment:
        reasons.add("fractional_share_cash_is_separate_from_primary_terms")
    if candidate_state == "fixed_cash_and_timing_ready":
        reasons.add("fixed_cash_term_and_cessation_timing_are_ready_for_later_outcome")
    else:
        reasons.add(candidate_state)
    values = {
        "request_sequence": consideration.request_sequence,
        "instrument_id": consideration.instrument_id,
        "consideration_fingerprint": consideration.logical_fingerprint,
        "party_relation_fingerprint": party.logical_fingerprint,
        "cessation_fingerprint": cessation.logical_fingerprint,
        "consideration_structure": consideration.consideration_structure,
        "cessation_resolution_state": cessation.resolution_state,
        "payoff_profile": spec.profile,
        "terminal_candidate_state": candidate_state,
        "listed_equity_issuer_locator": spec.listed_equity_issuer_locator,
        "consideration_evidence_text": consideration.evidence_text,
        "consideration_evidence_sha256": consideration.evidence_sha256,
        "terms": terms,
        "alternatives": alternatives,
        "single_deterministic_cash_term_complete": spec.structure == "cash_only",
        "fractional_share_cash_adjustment": (
            consideration.fractional_share_cash_adjustment
        ),
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = TerminalPayoffTermsDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalPayoffTermsDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _normalized_term(text: str, spec: _TermSpec) -> NormalizedPayoffTermV1:
    if text.count(spec.source_literal) != 1:
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            f"payoff source literal differs for {spec.key}"
        )
    start = text.index(spec.source_literal)
    values = {
        "term_key": spec.key,
        "term_kind": spec.kind,
        "source_literal": spec.source_literal,
        "normalized_value": _canonical_decimal(spec.kind, spec.normalized_value),
        "evidence_start": start,
        "evidence_end": start + len(spec.source_literal),
        "evidence_sha256": _sha256_bytes(spec.source_literal.encode("utf-8")),
    }
    provisional = NormalizedPayoffTermV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return NormalizedPayoffTermV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _alternative(spec: _AlternativeSpec) -> PayoffAlternativeV1:
    values = {
        "alternative_code": spec.code,
        "term_keys": tuple(sorted(spec.term_keys)),
        "default_if_no_valid_election": spec.default_if_no_valid_election,
        "subject_to_proration": spec.subject_to_proration,
    }
    provisional = PayoffAlternativeV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return PayoffAlternativeV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _candidate_state(
    *, profile: PayoffProfile, cessation_state: str
) -> TerminalCandidateState:
    if cessation_state != "matched":
        return "cessation_timing_not_matched"
    if profile == "fixed_cash_fully_specified":
        return "fixed_cash_and_timing_ready"
    if profile == "listed_equity_market_value_required":
        return "listed_security_identity_and_market_value_required"
    if profile == "contingent_value_right_unvalued":
        return "contingent_value_realization_unresolved"
    if profile == "holder_election_unresolved":
        return "holder_election_or_proration_unresolved"
    if profile == "unlisted_unit_and_election_unresolved":
        return "unlisted_unit_value_unresolved"
    raise StrongLeaderPullbackTerminalPayoffTermsError(
        "terminal payoff profile is unregistered"
    )


def _canonical_decimal(kind: TermKind, value: str) -> str:
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("payoff term is not decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("payoff term must be finite and positive")
    scale = Decimal("0.01") if "cash_usd" in kind else Decimal("0.000001")
    if number != number.quantize(scale):
        raise ValueError("payoff term exceeds registered precision")
    return format(number.quantize(scale), "f")


def _decision_matches_registry(decision: TerminalPayoffTermsDecisionV1) -> bool:
    spec = _CASE_SPECS.get(decision.request_sequence)
    if spec is None:
        return False
    expected_terms = tuple(
        sorted(
            (
                item.key,
                item.kind,
                item.source_literal,
                _canonical_decimal(item.kind, item.normalized_value),
            )
            for item in spec.terms
        )
    )
    observed_terms = tuple(
        (
            item.term_key,
            item.term_kind,
            item.source_literal,
            item.normalized_value,
        )
        for item in decision.terms
    )
    expected_alternatives = tuple(
        sorted(
            (
                item.code,
                tuple(sorted(item.term_keys)),
                item.default_if_no_valid_election,
                item.subject_to_proration,
            )
            for item in spec.alternatives
        )
    )
    observed_alternatives = tuple(
        (
            item.alternative_code,
            item.term_keys,
            item.default_if_no_valid_election,
            item.subject_to_proration,
        )
        for item in decision.alternatives
    )
    return (
        decision.consideration_structure == spec.structure
        and decision.payoff_profile == spec.profile
        and decision.listed_equity_issuer_locator == spec.listed_equity_issuer_locator
        and observed_terms == expected_terms
        and observed_alternatives == expected_alternatives
        and decision.terminal_candidate_state
        == _candidate_state(
            profile=spec.profile,
            cessation_state=decision.cessation_resolution_state,
        )
    )


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "cases": {
                str(sequence): {
                    "structure": spec.structure,
                    "profile": spec.profile,
                    "listed_equity_issuer_locator": spec.listed_equity_issuer_locator,
                    "terms": [
                        {
                            "key": item.key,
                            "kind": item.kind,
                            "source_literal": item.source_literal,
                            "normalized_value": item.normalized_value,
                        }
                        for item in spec.terms
                    ],
                    "alternatives": [
                        {
                            "code": item.code,
                            "term_keys": sorted(item.term_keys),
                            "default_if_no_valid_election": item.default_if_no_valid_election,
                            "subject_to_proration": item.subject_to_proration,
                        }
                        for item in spec.alternatives
                    ],
                }
                for sequence, spec in sorted(_CASE_SPECS.items())
            },
            "cash_scale": "0.01",
            "unit_and_ratio_scale": "0.000001",
            "terminal_outcome": "not_calculated",
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPayoffTermsV1,
) -> StrongLeaderPullbackTerminalPayoffTermsResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_payoff_terms(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPayoffTermsError(
                "existing terminal payoff terms report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms staging target exists"
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
    reread = read_strong_leader_pullback_terminal_payoff_terms(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPayoffTermsResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms paths must be absolute"
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
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms custody or target is unsafe"
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
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "terminal payoff terms file metadata differs"
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


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackTerminalPayoffTermsError(
            "network access is prohibited during terminal payoff term normalization"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
