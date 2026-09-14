"""Nominal fixed-cash terminal evidence for the first strategy."""

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
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    SecCommonShareConsiderationDecisionV1,
    StrongLeaderPullbackSecConsiderationAdjudicationResult,
    _fingerprint,
    _json_bytes,
    _sha256_bytes,
    read_strong_leader_pullback_sec_consideration_adjudication,
)
from tip_api.services.strong_leader_pullback_terminal_payoff_terms import (
    StrongLeaderPullbackTerminalPayoffTermsResult,
    TerminalCandidateState,
    TerminalPayoffTermsDecisionV1,
    read_strong_leader_pullback_terminal_payoff_terms,
)
from tip_api.services.strong_leader_pullback_trading_cessation_adjudication import (
    StrongLeaderPullbackTradingCessationAdjudicationResult,
    TimingProfile,
    TradingCessationDecisionV1,
    read_strong_leader_pullback_trading_cessation_adjudication,
)


CONTRACT_VERSION = "strong-leader-pullback-fixed-cash-terminal-evidence/1.0"
REPORT_FILE = "fixed-cash-terminal-evidence.json"
EXPECTED_CASE_COUNT = 61
EXPECTED_EVIDENCE_COUNT = 30
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_CASH_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$"

EvidenceState = Literal[
    "nominal_fixed_cash_terminal_evidence",
    "excluded_by_prior_terminal_candidate_state",
]


class StrongLeaderPullbackFixedCashTerminalEvidenceError(RuntimeError):
    """Raised when fixed-cash terminal evidence cannot be reconciled."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FixedCashTerminalEvidenceDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    consideration_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_terminal_candidate_state: TerminalCandidateState
    evidence_state: EvidenceState
    source_available_at: datetime
    transaction_completion_date: date
    cessation_resolution_state: Literal["matched", "conflicting", "unsupported"]
    timing_profile: TimingProfile
    sec_stated_trading_stop_boundary_date: date | None = None
    expected_last_eod_session: date | None = None
    observed_last_eod_session: date | None = None
    first_absent_exchange_session: date | None = None
    nominal_terminal_cash_amount_usd: str | None = Field(
        default=None, pattern=_CASH_PATTERN
    )
    amount_term_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    terminal_value_basis: Literal[
        "gross_nominal_cash_per_target_common_share"
    ] | None = None
    signal_feature_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    canonical_lifecycle_fact_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_available_at")
    @classmethod
    def source_available_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("fixed-cash terminal evidence reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "FixedCashTerminalEvidenceDecisionV1":
        evidenced = self.evidence_state == "nominal_fixed_cash_terminal_evidence"
        terminal_fields = (
            self.first_absent_exchange_session,
            self.nominal_terminal_cash_amount_usd,
            self.amount_term_fingerprint,
            self.terminal_value_basis,
        )
        if (
            (evidenced and not all(value is not None for value in terminal_fields))
            or (not evidenced and any(value is not None for value in terminal_fields))
            or (evidenced and self.prior_terminal_candidate_state != "fixed_cash_and_timing_ready")
            or (not evidenced and self.prior_terminal_candidate_state == "fixed_cash_and_timing_ready")
            or (
                self.nominal_terminal_cash_amount_usd is not None
                and self.nominal_terminal_cash_amount_usd
                != _canonical_cash(self.nominal_terminal_cash_amount_usd)
            )
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("fixed-cash terminal evidence decision differs")
        if evidenced and not _safe_daily_terminal_boundary(self):
            raise ValueError("fixed-cash daily terminal boundary differs")
        return self


class StrongLeaderPullbackFixedCashTerminalEvidenceV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-fixed-cash-terminal-evidence/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["fixed_cash_terminal_evidence_documented"] = (
        "fixed_cash_terminal_evidence_documented"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[61] = EXPECTED_CASE_COUNT
    source_candidate_count: Literal[30] = EXPECTED_EVIDENCE_COUNT
    terminal_cash_evidence_count: Literal[30] = EXPECTED_EVIDENCE_COUNT
    excluded_case_count: Literal[31] = EXPECTED_CASE_COUNT - EXPECTED_EVIDENCE_COUNT
    decision_state_counts: tuple[tuple[str, int], ...]
    evidenced_timing_profile_counts: tuple[tuple[str, int], ...]
    completion_equals_stop_boundary_count: int = Field(ge=0, le=30)
    completion_before_stop_boundary_count: int = Field(ge=0, le=30)
    completion_after_stop_boundary_count: int = Field(ge=0, le=30)
    decisions: tuple[FixedCashTerminalEvidenceDecisionV1, ...]
    canonical_lifecycle_fact_count: Literal[0] = 0
    canonical_terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    signal_feature_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    forward_return_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackFixedCashTerminalEvidenceV1":
        states = Counter(item.evidence_state for item in self.decisions)
        evidenced = tuple(
            item
            for item in self.decisions
            if item.evidence_state == "nominal_fixed_cash_terminal_evidence"
        )
        timing = Counter(item.timing_profile for item in evidenced)
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or len({item.request_sequence for item in self.decisions})
            != EXPECTED_CASE_COUNT
            or len(evidenced) != EXPECTED_EVIDENCE_COUNT
            or self.decision_state_counts != _ordered(states)
            or self.evidenced_timing_profile_counts != _ordered(timing)
            or self.completion_equals_stop_boundary_count
            != sum(
                item.transaction_completion_date
                == item.sec_stated_trading_stop_boundary_date
                for item in evidenced
            )
            or self.completion_before_stop_boundary_count
            != sum(
                item.transaction_completion_date
                < item.sec_stated_trading_stop_boundary_date  # type: ignore[operator]
                for item in evidenced
            )
            or self.completion_after_stop_boundary_count
            != sum(
                item.transaction_completion_date
                > item.sec_stated_trading_stop_boundary_date  # type: ignore[operator]
                for item in evidenced
            )
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("fixed-cash terminal evidence report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackFixedCashTerminalEvidenceResult:
    output_root: Path
    report: StrongLeaderPullbackFixedCashTerminalEvidenceV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_fixed_cash_terminal_evidence(
    *,
    consideration_root: Path,
    consideration_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackFixedCashTerminalEvidenceResult:
    with _network_prohibited():
        consideration = read_strong_leader_pullback_sec_consideration_adjudication(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        cessation = read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        payoff_terms = read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        report = _build_report(
            consideration=consideration,
            cessation=cessation,
            payoff_terms=payoff_terms,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_fixed_cash_terminal_evidence(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackFixedCashTerminalEvidenceResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackFixedCashTerminalEvidenceV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence report bytes are not canonical"
        )
    return StrongLeaderPullbackFixedCashTerminalEvidenceResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    consideration: StrongLeaderPullbackSecConsiderationAdjudicationResult,
    cessation: StrongLeaderPullbackTradingCessationAdjudicationResult,
    payoff_terms: StrongLeaderPullbackTerminalPayoffTermsResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackFixedCashTerminalEvidenceV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence revision is invalid"
        )
    if (
        payoff_terms.report.consideration_report_sha256 != consideration.report_sha256
        or payoff_terms.report.consideration_logical_fingerprint
        != consideration.report.logical_fingerprint
        or payoff_terms.report.cessation_report_sha256 != cessation.report_sha256
        or payoff_terms.report.cessation_logical_fingerprint
        != cessation.report.logical_fingerprint
        or payoff_terms.report.lifecycle_case_count != EXPECTED_CASE_COUNT
        or payoff_terms.report.fixed_cash_and_timing_ready_count
        != EXPECTED_EVIDENCE_COUNT
    ):
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence input bindings differ"
        )
    considerations = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    cessations = {item.request_sequence: item for item in cessation.report.decisions}
    terms = {item.request_sequence: item for item in payoff_terms.report.decisions}
    if not (
        len(considerations) == len(cessations) == len(terms) == EXPECTED_CASE_COUNT
        and set(considerations) == set(cessations) == set(terms)
    ):
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence population differs"
        )
    decisions = tuple(
        _document_decision(
            consideration=considerations[sequence],
            cessation=cessations[sequence],
            payoff_terms=terms[sequence],
        )
        for sequence in sorted(terms)
    )
    evidenced = tuple(
        item
        for item in decisions
        if item.evidence_state == "nominal_fixed_cash_terminal_evidence"
    )
    states = Counter(item.evidence_state for item in decisions)
    timing = Counter(item.timing_profile for item in evidenced)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": consideration.report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation.report.logical_fingerprint,
        "payoff_terms_report_sha256": payoff_terms.report_sha256,
        "payoff_terms_logical_fingerprint": payoff_terms.report.logical_fingerprint,
        "decision_state_counts": _ordered(states),
        "evidenced_timing_profile_counts": _ordered(timing),
        "completion_equals_stop_boundary_count": sum(
            item.transaction_completion_date
            == item.sec_stated_trading_stop_boundary_date
            for item in evidenced
        ),
        "completion_before_stop_boundary_count": sum(
            item.transaction_completion_date
            < item.sec_stated_trading_stop_boundary_date  # type: ignore[operator]
            for item in evidenced
        ),
        "completion_after_stop_boundary_count": sum(
            item.transaction_completion_date
            > item.sec_stated_trading_stop_boundary_date  # type: ignore[operator]
            for item in evidenced
        ),
        "decisions": decisions,
    }
    provisional = StrongLeaderPullbackFixedCashTerminalEvidenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackFixedCashTerminalEvidenceV1.model_validate(
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
    cessation: TradingCessationDecisionV1,
    payoff_terms: TerminalPayoffTermsDecisionV1,
) -> FixedCashTerminalEvidenceDecisionV1:
    if (
        consideration.instrument_id != cessation.instrument_id
        or consideration.instrument_id != payoff_terms.instrument_id
        or consideration.logical_fingerprint != payoff_terms.consideration_fingerprint
        or cessation.logical_fingerprint != payoff_terms.cessation_fingerprint
        or consideration.transaction_completion_date
        != cessation.transaction_completion_date
    ):
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal source decision differs"
        )
    ready = payoff_terms.terminal_candidate_state == "fixed_cash_and_timing_ready"
    cash_amount: str | None = None
    amount_term_fingerprint: str | None = None
    terminal_value_basis: str | None = None
    first_absent: date | None = None
    reasons = {
        "source_filing_acceptance_is_label_maturity_evidence_not_signal_knowledge",
        "strategy_return_not_calculated",
    }
    if ready:
        cash_terms = tuple(
            item
            for item in payoff_terms.terms
            if item.term_kind == "cash_usd_per_target_share"
        )
        if (
            not payoff_terms.single_deterministic_cash_term_complete
            or len(payoff_terms.terms) != 1
            or len(cash_terms) != 1
            or cash_terms[0].term_key != "guaranteed_cash"
            or payoff_terms.alternatives
            or cessation.resolution_state != "matched"
        ):
            raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
                "fixed-cash terminal candidate differs"
            )
        cash_amount = _canonical_cash(cash_terms[0].normalized_value)
        amount_term_fingerprint = cash_terms[0].logical_fingerprint
        terminal_value_basis = "gross_nominal_cash_per_target_common_share"
        first_absent = cessation.next_exchange_session
        reasons.update(
            {
                "fixed_cash_term_is_single_and_deterministic",
                "gross_nominal_cash_is_not_execution_or_net_settlement_proceeds",
                "terminal_cash_applies_only_after_last_observed_eod",
            }
        )
        state: EvidenceState = "nominal_fixed_cash_terminal_evidence"
    else:
        reasons.add(payoff_terms.terminal_candidate_state)
        state = "excluded_by_prior_terminal_candidate_state"
    values = {
        "request_sequence": consideration.request_sequence,
        "instrument_id": consideration.instrument_id,
        "consideration_fingerprint": consideration.logical_fingerprint,
        "cessation_fingerprint": cessation.logical_fingerprint,
        "payoff_terms_fingerprint": payoff_terms.logical_fingerprint,
        "prior_terminal_candidate_state": payoff_terms.terminal_candidate_state,
        "evidence_state": state,
        "source_available_at": consideration.acceptance_datetime,
        "transaction_completion_date": consideration.transaction_completion_date,
        "cessation_resolution_state": cessation.resolution_state,
        "timing_profile": cessation.timing_profile,
        "sec_stated_trading_stop_boundary_date": (
            cessation.sec_stated_trading_stop_boundary_date
        ),
        "expected_last_eod_session": cessation.expected_last_eod_session,
        "observed_last_eod_session": cessation.observed_last_eod_session,
        "first_absent_exchange_session": first_absent,
        "nominal_terminal_cash_amount_usd": cash_amount,
        "amount_term_fingerprint": amount_term_fingerprint,
        "terminal_value_basis": terminal_value_basis,
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = FixedCashTerminalEvidenceDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return FixedCashTerminalEvidenceDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _safe_daily_terminal_boundary(
    decision: FixedCashTerminalEvidenceDecisionV1,
) -> bool:
    stop = decision.sec_stated_trading_stop_boundary_date
    expected = decision.expected_last_eod_session
    observed = decision.observed_last_eod_session
    first_absent = decision.first_absent_exchange_session
    if (
        decision.cessation_resolution_state != "matched"
        or decision.timing_profile not in {"before_open", "after_close"}
        or stop is None
        or expected is None
        or observed is None
        or first_absent is None
        or observed != expected
        or first_absent <= observed
        or decision.transaction_completion_date > first_absent
    ):
        return False
    if decision.timing_profile == "before_open":
        return expected < stop and first_absent == stop
    return expected == stop


def _canonical_cash(value: str) -> str:
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("terminal cash is not decimal") from exc
    if not number.is_finite() or number <= 0 or number != number.quantize(
        Decimal("0.01")
    ):
        raise ValueError("terminal cash must be positive cents")
    return format(number.quantize(Decimal("0.01")), "f")


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "population": "all_61_upstream_terminal_term_decisions",
            "admission_state": "fixed_cash_and_timing_ready",
            "cash_term": "one_guaranteed_cash_term_only",
            "cash_scale": "0.01",
            "daily_effective_session": "first_exchange_session_after_last_observed_eod",
            "completion_rule": "on_or_before_first_absent_exchange_session",
            "signal_feature": "prohibited",
            "strategy_outcome_label": "not_calculated",
            "value_basis": "gross_nominal_cash_per_target_common_share",
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackFixedCashTerminalEvidenceV1,
) -> StrongLeaderPullbackFixedCashTerminalEvidenceResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_fixed_cash_terminal_evidence(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
                "existing fixed-cash terminal evidence report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence staging target exists"
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
    reread = read_strong_leader_pullback_fixed_cash_terminal_evidence(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackFixedCashTerminalEvidenceResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence paths must be absolute"
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
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence custody or target is unsafe"
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
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "fixed-cash terminal evidence file metadata differs"
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
        raise StrongLeaderPullbackFixedCashTerminalEvidenceError(
            "network access is prohibited during fixed-cash terminal evidence"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
