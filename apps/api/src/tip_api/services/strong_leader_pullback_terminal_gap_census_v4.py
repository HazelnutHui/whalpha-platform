"""Local-evidence extension of the first-strategy terminal-gap census."""

from __future__ import annotations

import os
import re
import shutil
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import (
    strong_leader_pullback_sec_termination_reason_adjudication as reason_reader,
)
from tip_api.services import strong_leader_pullback_terminal_gap_census_v3 as prior_reader
from tip_api.services import strong_leader_pullback_terminal_payoff_terms as payoff_reader
from tip_api.services import strong_leader_pullback_trading_cessation_adjudication as cessation_reader
from tip_api.services.market_calendar import ExchangeCalendar


CONTRACT_VERSION = "strong-leader-pullback-terminal-gap-census/4.0"
REPORT_FILE = "terminal-gap-census-v4.json"
MAXIMUM_REPORT_BYTES = 1024 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 2048
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"
_VALUE_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{16}$"


@dataclass(frozen=True, slots=True)
class _CaseSpec:
    sequence: int
    ticker: str
    reference_session: date
    reference_kind: Literal["fixed_cash", "default_cash"]
    timing_pattern: str | None = None
    cash_term: str | None = None
    alternative_code: str | None = None


_CASE_SPECS = (
    _CaseSpec(
        109,
        "RNAM",
        date(2026, 2, 27),
        "fixed_cash",
        r"maintain the halt on trading.{0,180}effective at 8:00 p\.m\. Eastern time on February 26, 2026.{0,180}through the day on February 27, 2026",
        cash_term="guaranteed_cash",
    ),
    _CaseSpec(
        136,
        "TERN",
        date(2026, 5, 5),
        "fixed_cash",
        r"trading of the Shares is expected to be suspended effective prior to the open of trading on May 5, 2026",
        cash_term="guaranteed_cash",
    ),
    _CaseSpec(
        161,
        "PLYM",
        date(2026, 1, 28),
        "fixed_cash",
        r"Company Common Stock is expected to be suspended from trading.{0,120}prior to the opening of trading on January 28, 2026",
        cash_term="guaranteed_cash",
    ),
    _CaseSpec(
        194,
        "FL",
        date(2025, 9, 8),
        "default_cash",
        cash_term="cash_election_cash",
        alternative_code="cash_election",
    ),
)
_EXPECTED_SEQUENCES = frozenset(item.sequence for item in _CASE_SPECS)
_PRIOR_GAP_STATES = {
    109: "cessation_timing_not_matched",
    136: "cessation_timing_not_matched",
    161: "cessation_timing_not_matched",
    194: "holder_election_or_proration_unresolved",
}


class StrongLeaderPullbackTerminalGapCensusV4Error(RuntimeError):
    """Raised when the V4 extension cannot prove its bounded claims."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalGapLocalReferenceV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    ticker_locator: str = Field(min_length=1)
    instrument_id: UUID
    prior_gap_state: Literal[
        "cessation_timing_not_matched",
        "holder_election_or_proration_unresolved",
    ]
    resolution_basis: Literal[
        "source_stated_after_close_halt_and_fixed_cash",
        "source_stated_before_open_stop_and_fixed_cash",
        "source_stated_no_election_fixed_cash",
    ]
    terminal_reference_session: date
    target_bar_absent_on_reference_session: Literal[True] = True
    source_timing_evidence_text: str | None = Field(
        default=None, min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS
    )
    source_timing_evidence_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    payoff_term_fingerprints: tuple[str, ...] = Field(min_length=1)
    default_policy_code: str | None = None
    cash_amount_usd: str = Field(pattern=_VALUE_PATTERN)
    gross_reference_value_usd: str = Field(pattern=_VALUE_PATTERN)
    eod_session_content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    eod_session_parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_available_before_strategy_outcome_use: Literal[True] = True
    reference_is_execution_price: Literal[False] = False
    reference_is_realized_holder_election: Literal[False] = False
    reference_is_terminal_outcome: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_timing_evidence_text")
    @classmethod
    def timing_text_is_normalized(cls, value: str | None) -> str | None:
        if value is not None and value != cessation_reader._normalized_text(value):
            raise ValueError("V4 timing evidence is not normalized")
        return value

    @field_validator("payoff_term_fingerprints", mode="before")
    @classmethod
    def fingerprints_are_ordered(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("V4 payoff fingerprints differ")
        return values

    @model_validator(mode="after")
    def reference_reconciles(self) -> "TerminalGapLocalReferenceV1":
        if (
            self.source_timing_evidence_sha256
            != cessation_reader._optional_text_sha256(
                self.source_timing_evidence_text
            )
            or Decimal(self.gross_reference_value_usd)
            != Decimal(self.cash_amount_usd)
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("V4 terminal reference differs")
        return self


class StrongLeaderPullbackTerminalGapCensusV4(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-gap-census/4.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["local_terminal_evidence_extended"] = (
        "local_terminal_evidence_extended"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    prior_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    population_instrument_count: Literal[65] = 65
    extension_reference_count: Literal[4] = 4
    reference_documented_instrument_count: Literal[47] = 47
    remaining_gap_instrument_count: Literal[18] = 18
    documented_horizon_1_crossing_path_count: int = Field(ge=0)
    documented_horizon_3_crossing_path_count: int = Field(ge=0)
    documented_horizon_5_crossing_path_count: int = Field(ge=0)
    remaining_horizon_1_crossing_path_count: int = Field(ge=0)
    remaining_horizon_3_crossing_path_count: int = Field(ge=0)
    remaining_horizon_5_crossing_path_count: int = Field(ge=0)
    remaining_state_impacts: tuple[tuple[str, int, int, int, int], ...]
    references: tuple[TerminalGapLocalReferenceV1, ...] = Field(min_length=4, max_length=4)
    unresolved_successor_identity_count: Literal[1] = 1
    unresolved_cvr_or_complex_value_count: Literal[8] = 8
    unresolved_primary_source_case_count: Literal[3] = 3
    unresolved_cessation_or_eod_conflict_count: Literal[5] = 5
    unresolved_election_or_proration_count: Literal[1] = 1
    prior_v3_preserved: Literal[True] = True
    outcome_blind: Literal[True] = True
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackTerminalGapCensusV4":
        if (
            tuple(item.request_sequence for item in self.references)
            != tuple(sorted(_EXPECTED_SEQUENCES))
            or self.documented_horizon_1_crossing_path_count
            + self.remaining_horizon_1_crossing_path_count
            != 65
            or self.documented_horizon_3_crossing_path_count
            + self.remaining_horizon_3_crossing_path_count
            != 194
            or self.documented_horizon_5_crossing_path_count
            + self.remaining_horizon_5_crossing_path_count
            != 302
            or sum(item[1] for item in self.remaining_state_impacts) != 18
            or sum(item[2] for item in self.remaining_state_impacts)
            != self.remaining_horizon_1_crossing_path_count
            or sum(item[3] for item in self.remaining_state_impacts)
            != self.remaining_horizon_3_crossing_path_count
            or sum(item[4] for item in self.remaining_state_impacts)
            != self.remaining_horizon_5_crossing_path_count
            or self.unresolved_successor_identity_count
            + self.unresolved_cvr_or_complex_value_count
            + self.unresolved_primary_source_case_count
            + self.unresolved_cessation_or_eod_conflict_count
            + self.unresolved_election_or_proration_count
            != self.remaining_gap_instrument_count
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("V4 terminal gap census differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalGapCensusV4Result:
    output_root: Path
    report: StrongLeaderPullbackTerminalGapCensusV4
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_gap_census_v4(
    *,
    prior_census_root: Path,
    prior_census_custody_root: Path,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    termination_reason_root: Path,
    termination_reason_custody_root: Path,
    canonical_eod_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusV4Result:
    """Extend V3 with four exact, locally provable daily references."""

    with cessation_reader._network_prohibited():
        prior = prior_reader.read_strong_leader_pullback_terminal_gap_census_v3(
            output_root=prior_census_root,
            output_custody_root=prior_census_custody_root,
        )
        payoff = payoff_reader.read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        cessation = cessation_reader.read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        reasons = reason_reader.read_strong_leader_pullback_sec_termination_reason_adjudication(
            output_root=termination_reason_root,
            output_custody_root=termination_reason_custody_root,
        )
        report = _build_report(
            prior=prior,
            payoff=payoff,
            cessation=cessation,
            reasons=reasons,
            repository=CanonicalEodReadRepository(canonical_eod_root),
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_gap_census_v4(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalGapCensusV4Result:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalGapCensusV4.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap report bytes differ"
        )
    return StrongLeaderPullbackTerminalGapCensusV4Result(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, prior: Any, payoff: Any, cessation: Any, reasons: Any,
    repository: CanonicalEodReadRepository,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusV4:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap revision is invalid"
        )
    prior_report = prior.report
    if (
        prior_report.population_instrument_count != 65
        or prior_report.reference_documented_instrument_count != 43
        or prior_report.remaining_gap_instrument_count != 22
        or payoff.report.lifecycle_case_count != 61
        or cessation.report.lifecycle_case_count != 61
        or reasons.report.matched_reason_count != 61
    ):
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 upstream population differs"
        )
    prior_decisions = {
        item.request_sequence: item
        for item in prior_report.decisions
        if item.request_sequence is not None
    }
    payoff_decisions = {item.request_sequence: item for item in payoff.report.decisions}
    cessation_decisions = {
        item.request_sequence: item for item in cessation.report.decisions
    }
    reason_decisions = {item.request_sequence: item for item in reasons.report.decisions}
    sessions = tuple(sorted({item.reference_session for item in _CASE_SPECS}))
    history = repository.read_history_sessions(sessions)
    if tuple(item.integrity.session_date for item in history) != sessions:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 reference-session evidence differs"
        )
    by_session = {item.integrity.session_date: item for item in history}
    references = tuple(
        _build_reference(
            spec=spec,
            prior_decision=prior_decisions[spec.sequence],
            payoff_decision=payoff_decisions[spec.sequence],
            cessation_decision=cessation_decisions[spec.sequence],
            reason_decision=reason_decisions[spec.sequence],
            session_read=by_session[spec.reference_session],
            repository=repository,
        )
        for spec in sorted(_CASE_SPECS, key=lambda item: item.sequence)
    )
    selected = set(_EXPECTED_SEQUENCES)
    newly_h1 = sum(prior_decisions[item].horizon_1_crossing_path_count for item in selected)
    newly_h3 = sum(prior_decisions[item].horizon_3_crossing_path_count for item in selected)
    newly_h5 = sum(prior_decisions[item].horizon_5_crossing_path_count for item in selected)
    remaining = tuple(
        item
        for item in prior_report.decisions
        if item.gap_state not in {
            "gross_listed_consideration_reference_documented",
            "nominal_fixed_cash_reference_documented",
        }
        and item.request_sequence not in selected
    )
    impacts: Counter[str] = Counter()
    h1: Counter[str] = Counter()
    h3: Counter[str] = Counter()
    h5: Counter[str] = Counter()
    for item in remaining:
        state = item.gap_state
        if item.request_sequence == 124:
            state = "listed_successor_identity_unresolved"
        impacts[state] += 1
        h1[state] += item.horizon_1_crossing_path_count
        h3[state] += item.horizon_3_crossing_path_count
        h5[state] += item.horizon_5_crossing_path_count
    remaining_impacts = tuple(
        (state, impacts[state], h1[state], h3[state], h5[state])
        for state in sorted(impacts)
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "prior_census_report_sha256": prior.report_sha256,
        "prior_census_logical_fingerprint": prior_report.logical_fingerprint,
        "payoff_terms_report_sha256": payoff.report_sha256,
        "payoff_terms_logical_fingerprint": payoff.report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation.report.logical_fingerprint,
        "termination_reason_report_sha256": reasons.report_sha256,
        "termination_reason_logical_fingerprint": reasons.report.logical_fingerprint,
        "documented_horizon_1_crossing_path_count": (
            prior_report.documented_horizon_1_crossing_path_count + newly_h1
        ),
        "documented_horizon_3_crossing_path_count": (
            prior_report.documented_horizon_3_crossing_path_count + newly_h3
        ),
        "documented_horizon_5_crossing_path_count": (
            prior_report.documented_horizon_5_crossing_path_count + newly_h5
        ),
        "remaining_horizon_1_crossing_path_count": (
            prior_report.remaining_horizon_1_crossing_path_count - newly_h1
        ),
        "remaining_horizon_3_crossing_path_count": (
            prior_report.remaining_horizon_3_crossing_path_count - newly_h3
        ),
        "remaining_horizon_5_crossing_path_count": (
            prior_report.remaining_horizon_5_crossing_path_count - newly_h5
        ),
        "remaining_state_impacts": remaining_impacts,
        "references": references,
    }
    provisional = StrongLeaderPullbackTerminalGapCensusV4.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalGapCensusV4.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _build_reference(
    *, spec: _CaseSpec, prior_decision: Any, payoff_decision: Any,
    cessation_decision: Any, reason_decision: Any, session_read: Any,
    repository: CanonicalEodReadRepository,
) -> TerminalGapLocalReferenceV1:
    if (
        prior_decision.gap_state != _PRIOR_GAP_STATES[spec.sequence]
        or payoff_decision.instrument_id != prior_decision.instrument_id
        or cessation_decision.instrument_id != prior_decision.instrument_id
        or reason_decision.instrument_id != prior_decision.instrument_id
        or spec.ticker not in prior_decision.provider_ticker_locators
        or repository.read_instrument_presence_sessions(
            (spec.reference_session,), frozenset({prior_decision.instrument_id})
        )[0].instrument_ids
    ):
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            f"V4 case {spec.sequence} identity or target absence differs"
        )
    calendar = ExchangeCalendar()
    if calendar.next_session(prior_decision.strategy_window_last_eod_observed_date) != spec.reference_session:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            f"V4 case {spec.sequence} reference boundary differs"
        )
    terms = {item.term_key: item for item in payoff_decision.terms}
    selected_terms = [terms[spec.cash_term]] if spec.cash_term is not None else []
    cash = Decimal(selected_terms[0].normalized_value) if selected_terms else Decimal(0)
    timing_text = None
    resolution_basis = "source_stated_no_election_fixed_cash"
    default_policy = None
    if spec.timing_pattern is not None:
        timing_text = _extract_timing_evidence(
            reason_decision.item_3_01_text, spec.timing_pattern
        )
        if spec.sequence == 109:
            resolution_basis = "source_stated_after_close_halt_and_fixed_cash"
        else:
            resolution_basis = "source_stated_before_open_stop_and_fixed_cash"
    elif spec.alternative_code is not None:
        alternatives = {
            item.alternative_code: item for item in payoff_decision.alternatives
        }
        alternative = alternatives[spec.alternative_code]
        if not alternative.default_if_no_valid_election:
            raise StrongLeaderPullbackTerminalGapCensusV4Error(
                f"V4 case {spec.sequence} default election differs"
            )
        default_policy = f"no_valid_election_{spec.alternative_code}"
        if alternative.subject_to_proration:
            raise StrongLeaderPullbackTerminalGapCensusV4Error(
                f"V4 case {spec.sequence} default election is prorated"
            )
    integrity = session_read.integrity
    values = {
        "request_sequence": spec.sequence,
        "ticker_locator": spec.ticker,
        "instrument_id": prior_decision.instrument_id,
        "prior_gap_state": prior_decision.gap_state,
        "resolution_basis": resolution_basis,
        "terminal_reference_session": spec.reference_session,
        "source_timing_evidence_text": timing_text,
        "source_timing_evidence_sha256": cessation_reader._optional_text_sha256(
            timing_text
        ),
        "payoff_term_fingerprints": tuple(
            sorted(item.logical_fingerprint for item in selected_terms)
        ),
        "default_policy_code": default_policy,
        "cash_amount_usd": _fixed(cash, 16),
        "gross_reference_value_usd": _fixed(cash, 16),
        "eod_session_content_fingerprint": integrity.content_fingerprint,
        "eod_session_parquet_sha256": integrity.parquet_sha256,
        "identity_snapshot_fingerprint": integrity.identity_snapshot_fingerprint,
    }
    provisional = TerminalGapLocalReferenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalGapLocalReferenceV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _extract_timing_evidence(text: str, pattern: str) -> str:
    normalized = cessation_reader._normalized_text(text)
    matches = tuple(re.finditer(pattern, normalized, re.I))
    if len(matches) != 1:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 exact timing evidence differs"
        )
    match = matches[0]
    start = max(0, match.start() - 180)
    end = min(len(normalized), match.end() + 180)
    result = normalized[start:end]
    if len(result) > MAXIMUM_EVIDENCE_TEXT_CHARS:
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 timing evidence exceeds limit"
        )
    return result


def _fixed(value: Decimal, places: int) -> str:
    return format(value, f".{places}f")


def _ruleset_fingerprint() -> str:
    return base._fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "cases": [
                {
                    "sequence": item.sequence,
                    "ticker": item.ticker,
                    "reference_session": item.reference_session.isoformat(),
                    "reference_kind": item.reference_kind,
                    "timing_pattern": item.timing_pattern,
                    "cash_term": item.cash_term,
                    "alternative_code": item.alternative_code,
                }
                for item in _CASE_SPECS
            ],
            "identity_rule": "prior_stable_id_plus_source_timing_plus_eod_absence",
            "reference_rule": "source_stated_fixed_or_default_cash",
            "terminal_outcome": False,
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalGapCensusV4,
) -> StrongLeaderPullbackTerminalGapCensusV4Result:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_gap_census_v4(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalGapCensusV4Error(
                "existing V4 terminal-gap report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalGapCensusV4Error(
                "V4 terminal-gap report exceeds limit"
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
    reread = read_strong_leader_pullback_terminal_gap_census_v4(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalGapCensusV4Result(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap paths must be absolute"
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
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap target is unsafe"
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
        raise StrongLeaderPullbackTerminalGapCensusV4Error(
            "V4 terminal-gap output is unsafe"
        )
    return target
