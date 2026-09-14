"""Reference terminal values for strictly matched listed merger consideration."""

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
from tip_api.contracts.market_data.v1 import EodPriceBarV1, EodSessionIntegrityV1
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.strong_leader_pullback_listed_consideration_adjudication import (
    ListedConsiderationIdentityDecisionV1,
    StrongLeaderPullbackListedConsiderationAdjudicationResult,
    _fingerprint,
    _json_bytes,
    _sha256_bytes,
    read_strong_leader_pullback_listed_consideration_adjudication,
)
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    SecCommonShareConsiderationDecisionV1,
    StrongLeaderPullbackSecConsiderationAdjudicationResult,
    read_strong_leader_pullback_sec_consideration_adjudication,
)
from tip_api.services.strong_leader_pullback_terminal_payoff_terms import (
    NormalizedPayoffTermV1,
    StrongLeaderPullbackTerminalPayoffTermsResult,
    TerminalPayoffTermsDecisionV1,
    read_strong_leader_pullback_terminal_payoff_terms,
)
from tip_api.services.strong_leader_pullback_trading_cessation_adjudication import (
    StrongLeaderPullbackTradingCessationAdjudicationResult,
    TimingProfile,
    TradingCessationDecisionV1,
    read_strong_leader_pullback_trading_cessation_adjudication,
)


CONTRACT_VERSION = "strong-leader-pullback-listed-consideration-terminal-evidence/1.0"
REPORT_FILE = "listed-consideration-terminal-evidence.json"
EXPECTED_CASE_COUNT = 12
EXPECTED_EVIDENCE_COUNT = 9
MAXIMUM_REPORT_BYTES = 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_RATIO_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$"
_CASH_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$"
_PRICE_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{10}$"
_VALUE_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{16}$"

EvidenceState = Literal[
    "gross_listed_consideration_reference_value",
    "excluded_by_identity_adjudication",
]


class StrongLeaderPullbackListedConsiderationTerminalEvidenceError(RuntimeError):
    """Raised when listed-consideration terminal evidence cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ListedConsiderationTerminalEvidenceDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    target_instrument_id: UUID
    identity_adjudication_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_resolution_state: str
    evidence_state: EvidenceState
    source_available_at: datetime
    transaction_completion_date: date
    timing_profile: TimingProfile
    observed_last_target_eod_session: date | None = None
    first_absent_target_exchange_session: date | None = None
    consideration_instrument_id: UUID | None = None
    listed_equity_ratio: str | None = Field(default=None, pattern=_RATIO_PATTERN)
    ratio_term_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    guaranteed_cash_amount_usd: str | None = Field(
        default=None, pattern=_CASH_PATTERN
    )
    cash_term_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    consideration_eod_close_usd: str | None = Field(
        default=None, pattern=_PRICE_PATTERN
    )
    listed_equity_component_value_usd: str | None = Field(
        default=None, pattern=_VALUE_PATTERN
    )
    gross_reference_terminal_value_usd: str | None = Field(
        default=None, pattern=_VALUE_PATTERN
    )
    valuation_session_record_count: int | None = Field(default=None, ge=1)
    valuation_session_content_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    valuation_session_parquet_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    valuation_identity_snapshot_date: date | None = None
    valuation_identity_snapshot_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    canonical_partition_created_at: datetime | None = None
    price_source: str | None = None
    price_revision: int | None = Field(default=None, ge=1)
    price_quality_status: str | None = None
    price_quality_flags: tuple[str, ...]
    price_currency: str | None = None
    terminal_value_basis: Literal[
        "gross_cash_plus_ratio_times_first_absent_session_close"
    ] | None = None
    terminal_reference_value_count: int = Field(ge=0, le=1)
    canonical_terminal_outcome_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("source_available_at", "canonical_partition_created_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value is not None else None

    @field_validator("decision_reasons", "price_quality_flags", mode="before")
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("listed terminal evidence tuple differs")
        return values

    @model_validator(mode="after")
    def decision_reconciles(
        self,
    ) -> "ListedConsiderationTerminalEvidenceDecisionV1":
        evidenced = self.evidence_state == "gross_listed_consideration_reference_value"
        evidence_fields = (
            self.observed_last_target_eod_session,
            self.first_absent_target_exchange_session,
            self.consideration_instrument_id,
            self.listed_equity_ratio,
            self.ratio_term_fingerprint,
            self.guaranteed_cash_amount_usd,
            self.consideration_eod_close_usd,
            self.listed_equity_component_value_usd,
            self.gross_reference_terminal_value_usd,
            self.valuation_session_record_count,
            self.valuation_session_content_fingerprint,
            self.valuation_session_parquet_sha256,
            self.valuation_identity_snapshot_date,
            self.valuation_identity_snapshot_fingerprint,
            self.canonical_partition_created_at,
            self.price_source,
            self.price_revision,
            self.price_quality_status,
            self.price_currency,
            self.terminal_value_basis,
        )
        if (
            (evidenced and not all(value is not None for value in evidence_fields))
            or (not evidenced and any(value is not None for value in evidence_fields))
            or evidenced != (self.terminal_reference_value_count == 1)
            or (not evidenced and self.price_quality_flags)
            or (not evidenced and self.cash_term_fingerprint is not None)
            or (evidenced and not self._formula_reconciles())
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed terminal evidence decision differs")
        return self

    def _formula_reconciles(self) -> bool:
        if self.prior_identity_resolution_state != "matched":
            return False
        try:
            ratio = Decimal(self.listed_equity_ratio or "")
            cash = Decimal(self.guaranteed_cash_amount_usd or "")
            close = Decimal(self.consideration_eod_close_usd or "")
            component = Decimal(self.listed_equity_component_value_usd or "")
            total = Decimal(self.gross_reference_terminal_value_usd or "")
        except (InvalidOperation, ValueError):
            return False
        return (
            self.first_absent_target_exchange_session is not None
            and self.observed_last_target_eod_session is not None
            and self.first_absent_target_exchange_session
            > self.observed_last_target_eod_session
            and component == ratio * close
            and total == cash + component
            and self.price_currency == "USD"
            and self.price_quality_status == "valid"
        )


class StrongLeaderPullbackListedConsiderationTerminalEvidenceV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-terminal-evidence/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "listed_consideration_reference_values_partially_documented"
    ] = "listed_consideration_reference_values_partially_documented"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    identity_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_adjudication_logical_fingerprint: str = Field(
        pattern=_SHA256_PATTERN
    )
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    case_count: Literal[12] = EXPECTED_CASE_COUNT
    source_candidate_count: Literal[9] = EXPECTED_EVIDENCE_COUNT
    terminal_reference_value_count: Literal[9] = EXPECTED_EVIDENCE_COUNT
    excluded_case_count: Literal[3] = EXPECTED_CASE_COUNT - EXPECTED_EVIDENCE_COUNT
    valuation_session_count: int = Field(ge=1, le=EXPECTED_EVIDENCE_COUNT)
    decision_state_counts: tuple[tuple[str, int], ...]
    price_quality_status_counts: tuple[tuple[str, int], ...]
    price_quality_flag_counts: tuple[tuple[str, int], ...]
    decisions: tuple[ListedConsiderationTerminalEvidenceDecisionV1, ...]
    canonical_terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
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
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackListedConsiderationTerminalEvidenceV1":
        evidenced = tuple(
            item
            for item in self.decisions
            if item.evidence_state
            == "gross_listed_consideration_reference_value"
        )
        states = Counter(item.evidence_state for item in self.decisions)
        quality = Counter(item.price_quality_status for item in evidenced)
        flags = Counter(flag for item in evidenced for flag in item.price_quality_flags)
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or len(evidenced) != EXPECTED_EVIDENCE_COUNT
            or self.valuation_session_count
            != len(
                {
                    item.first_absent_target_exchange_session
                    for item in evidenced
                }
            )
            or self.decision_state_counts != _ordered(states)
            or self.price_quality_status_counts != _ordered(quality)
            or self.price_quality_flag_counts != _ordered(flags)
            or sum(item.terminal_reference_value_count for item in self.decisions)
            != EXPECTED_EVIDENCE_COUNT
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("listed terminal evidence report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationTerminalEvidenceResult:
    output_root: Path
    report: StrongLeaderPullbackListedConsiderationTerminalEvidenceV1
    report_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _ValuationSessionEvidence:
    integrity: EodSessionIntegrityV1
    records: tuple[EodPriceBarV1, ...]
    available_at: datetime


def build_strong_leader_pullback_listed_consideration_terminal_evidence(
    *,
    identity_adjudication_root: Path,
    identity_adjudication_custody_root: Path,
    consideration_root: Path,
    consideration_custody_root: Path,
    cessation_root: Path,
    cessation_custody_root: Path,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    canonical_eod_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationTerminalEvidenceResult:
    with _network_prohibited():
        identities = read_strong_leader_pullback_listed_consideration_adjudication(
            output_root=identity_adjudication_root,
            output_custody_root=identity_adjudication_custody_root,
        )
        consideration = read_strong_leader_pullback_sec_consideration_adjudication(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        cessation = read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        payoff = read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        report = _build_report(
            identities=identities,
            consideration=consideration,
            cessation=cessation,
            payoff=payoff,
            canonical_eod_root=canonical_eod_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_listed_consideration_terminal_evidence(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackListedConsiderationTerminalEvidenceResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        model = StrongLeaderPullbackListedConsiderationTerminalEvidenceV1
        report = model.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence bytes are not canonical"
        )
    return StrongLeaderPullbackListedConsiderationTerminalEvidenceResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    identities: StrongLeaderPullbackListedConsiderationAdjudicationResult,
    consideration: StrongLeaderPullbackSecConsiderationAdjudicationResult,
    cessation: StrongLeaderPullbackTradingCessationAdjudicationResult,
    payoff: StrongLeaderPullbackTerminalPayoffTermsResult,
    canonical_eod_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationTerminalEvidenceV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence revision is invalid"
        )
    if (
        identities.report.payoff_terms_report_sha256 != payoff.report_sha256
        or identities.report.payoff_terms_logical_fingerprint
        != payoff.report.logical_fingerprint
        or payoff.report.consideration_report_sha256 != consideration.report_sha256
        or payoff.report.consideration_logical_fingerprint
        != consideration.report.logical_fingerprint
        or payoff.report.cessation_report_sha256 != cessation.report_sha256
        or payoff.report.cessation_logical_fingerprint
        != cessation.report.logical_fingerprint
        or identities.report.matched_identity_count != EXPECTED_EVIDENCE_COUNT
    ):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence input bindings differ"
        )
    identity_map = {item.request_sequence: item for item in identities.report.decisions}
    consideration_map = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    cessation_map = {item.request_sequence: item for item in cessation.report.decisions}
    payoff_map = {item.request_sequence: item for item in payoff.report.decisions}
    if not (
        set(identity_map).issubset(consideration_map)
        and set(identity_map).issubset(cessation_map)
        and set(identity_map).issubset(payoff_map)
        and len(identity_map) == EXPECTED_CASE_COUNT
    ):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence population differs"
        )
    requested_session_values = {
        cessation_map[sequence].next_exchange_session
        for sequence, item in identity_map.items()
        if item.resolution_state == "matched"
    }
    if None in requested_session_values:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal valuation session is unavailable"
        )
    requested_sessions = tuple(
        sorted(
            session
            for session in requested_session_values
            if session is not None
        )
    )
    repository = CanonicalEodReadRepository(canonical_eod_root)
    history = repository.read_history_sessions(requested_sessions)
    if any(item.available_at is None for item in history):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal valuation custody time is unavailable"
        )
    session_map = {
        item.integrity.session_date: _ValuationSessionEvidence(
            integrity=item.integrity,
            records=repository.read_canonical_records(item.integrity.session_date),
            available_at=item.available_at,  # type: ignore[arg-type]
        )
        for item in history
    }
    if any(
        len(item.records) != item.integrity.record_count
        or item.integrity.duplicate_instrument_session_count != 0
        or item.integrity.multiple_latest_revision_count != 0
        or item.integrity.future_identity_reference_count != 0
        for item in session_map.values()
    ):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal valuation session integrity differs"
        )
    decisions = tuple(
        _document_decision(
            identity=identity_map[sequence],
            consideration=consideration_map[sequence],
            cessation=cessation_map[sequence],
            payoff=payoff_map[sequence],
            valuation_session=(
                session_map.get(cessation_map[sequence].next_exchange_session)
                if identity_map[sequence].resolution_state == "matched"
                else None
            ),
        )
        for sequence in sorted(identity_map)
    )
    evidenced = tuple(
        item
        for item in decisions
        if item.evidence_state == "gross_listed_consideration_reference_value"
    )
    states = Counter(item.evidence_state for item in decisions)
    quality = Counter(item.price_quality_status for item in evidenced)
    flags = Counter(flag for item in evidenced for flag in item.price_quality_flags)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "identity_adjudication_report_sha256": identities.report_sha256,
        "identity_adjudication_logical_fingerprint": (
            identities.report.logical_fingerprint
        ),
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": consideration.report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation.report.logical_fingerprint,
        "payoff_terms_report_sha256": payoff.report_sha256,
        "payoff_terms_logical_fingerprint": payoff.report.logical_fingerprint,
        "valuation_session_count": len(requested_sessions),
        "decision_state_counts": _ordered(states),
        "price_quality_status_counts": _ordered(quality),
        "price_quality_flag_counts": _ordered(flags),
        "decisions": decisions,
    }
    provisional = (
        StrongLeaderPullbackListedConsiderationTerminalEvidenceV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
    )
    return StrongLeaderPullbackListedConsiderationTerminalEvidenceV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_decision(
    *,
    identity: ListedConsiderationIdentityDecisionV1,
    consideration: SecCommonShareConsiderationDecisionV1,
    cessation: TradingCessationDecisionV1,
    payoff: TerminalPayoffTermsDecisionV1,
    valuation_session: _ValuationSessionEvidence | None,
) -> ListedConsiderationTerminalEvidenceDecisionV1:
    if (
        identity.request_sequence != consideration.request_sequence
        or identity.request_sequence != cessation.request_sequence
        or identity.request_sequence != payoff.request_sequence
        or identity.target_instrument_id != consideration.instrument_id
        or identity.target_instrument_id != cessation.instrument_id
        or identity.target_instrument_id != payoff.instrument_id
        or payoff.consideration_fingerprint != consideration.logical_fingerprint
        or payoff.cessation_fingerprint != cessation.logical_fingerprint
        or consideration.transaction_completion_date
        != cessation.transaction_completion_date
    ):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal source decision differs"
        )
    matched = identity.resolution_state == "matched"
    reasons = {
        "canonical_partition_creation_is_custody_time_not_signal_knowledge",
        "reference_value_is_not_execution_price_or_strategy_return",
        "source_acceptance_is_label_evidence_not_signal_feature",
    }
    values: dict[str, object] = {
        "request_sequence": identity.request_sequence,
        "target_instrument_id": identity.target_instrument_id,
        "identity_adjudication_fingerprint": identity.logical_fingerprint,
        "consideration_fingerprint": consideration.logical_fingerprint,
        "cessation_fingerprint": cessation.logical_fingerprint,
        "payoff_terms_fingerprint": payoff.logical_fingerprint,
        "prior_identity_resolution_state": identity.resolution_state,
        "source_available_at": consideration.acceptance_datetime,
        "transaction_completion_date": consideration.transaction_completion_date,
        "timing_profile": cessation.timing_profile,
        "price_quality_flags": (),
        "terminal_reference_value_count": 0,
    }
    if matched:
        if (
            valuation_session is None
            or identity.assigned_consideration_instrument_id is None
            or cessation.resolution_state != "matched"
            or not _safe_daily_terminal_boundary(cessation)
            or payoff.alternatives
            or payoff.consideration_structure
            not in {"stock_only", "fixed_cash_and_stock"}
        ):
            raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
                "listed terminal evidence candidate differs"
            )
        ratio_term = _single_term(payoff, "listed_equity_shares_per_target_share")
        cash_terms = tuple(
            item
            for item in payoff.terms
            if item.term_kind == "cash_usd_per_target_share"
        )
        if len(cash_terms) > 1:
            raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
                "listed terminal cash component differs"
            )
        matches = tuple(
            bar
            for bar in valuation_session.records
            if bar.instrument_id == identity.assigned_consideration_instrument_id
        )
        if len(matches) != 1:
            raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
                "listed terminal consideration bar differs"
            )
        bar = matches[0]
        quality = bar.quality_status.value
        if (
            bar.currency != "USD"
            or quality != "valid"
            or not bar.is_latest_revision
            or bar.revision < 1
            or bar.session_date != cessation.next_exchange_session
            or bar.close <= 0
        ):
            raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
                "listed terminal price evidence is ineligible"
            )
        ratio = _decimal(ratio_term.normalized_value)
        cash = _decimal(cash_terms[0].normalized_value) if cash_terms else Decimal(0)
        close = bar.close
        component = ratio * close
        total = cash + component
        values.update(
            {
                "evidence_state": "gross_listed_consideration_reference_value",
                "observed_last_target_eod_session": (
                    cessation.observed_last_eod_session
                ),
                "first_absent_target_exchange_session": (
                    cessation.next_exchange_session
                ),
                "consideration_instrument_id": (
                    identity.assigned_consideration_instrument_id
                ),
                "listed_equity_ratio": _fixed(ratio, 6),
                "ratio_term_fingerprint": ratio_term.logical_fingerprint,
                "guaranteed_cash_amount_usd": _fixed(cash, 2),
                "cash_term_fingerprint": (
                    cash_terms[0].logical_fingerprint if cash_terms else None
                ),
                "consideration_eod_close_usd": _fixed(close, 10),
                "listed_equity_component_value_usd": _fixed(component, 16),
                "gross_reference_terminal_value_usd": _fixed(total, 16),
                "valuation_session_record_count": (
                    valuation_session.integrity.record_count
                ),
                "valuation_session_content_fingerprint": (
                    valuation_session.integrity.content_fingerprint
                ),
                "valuation_session_parquet_sha256": (
                    valuation_session.integrity.parquet_sha256
                ),
                "valuation_identity_snapshot_date": (
                    valuation_session.integrity.identity_snapshot_date
                ),
                "valuation_identity_snapshot_fingerprint": (
                    valuation_session.integrity.identity_snapshot_fingerprint
                ),
                "canonical_partition_created_at": valuation_session.available_at,
                "price_source": bar.source,
                "price_revision": bar.revision,
                "price_quality_status": quality,
                "price_quality_flags": tuple(sorted(bar.quality_flags)),
                "price_currency": bar.currency,
                "terminal_value_basis": (
                    "gross_cash_plus_ratio_times_first_absent_session_close"
                ),
                "terminal_reference_value_count": 1,
            }
        )
        reasons.update(
            {
                "consideration_security_identity_passed_four_element_gate",
                "first_absent_target_session_close_is_daily_reference_boundary",
                "unadjusted_close_and_unverified_adjustment_flag_retained",
            }
        )
    else:
        if valuation_session is not None:
            raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
                "excluded listed terminal decision received a price session"
            )
        values["evidence_state"] = "excluded_by_identity_adjudication"
        reasons.add(identity.resolution_state)
    values["decision_reasons"] = tuple(sorted(reasons))
    provisional = ListedConsiderationTerminalEvidenceDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ListedConsiderationTerminalEvidenceDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _single_term(
    payoff: TerminalPayoffTermsDecisionV1, kind: str
) -> NormalizedPayoffTermV1:
    matches = tuple(item for item in payoff.terms if item.term_kind == kind)
    if len(matches) != 1:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal payoff term differs"
        )
    return matches[0]


def _safe_daily_terminal_boundary(decision: TradingCessationDecisionV1) -> bool:
    stop = decision.sec_stated_trading_stop_boundary_date
    expected = decision.expected_last_eod_session
    observed = decision.observed_last_eod_session
    first_absent = decision.next_exchange_session
    if (
        decision.resolution_state != "matched"
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


def _decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal decimal is invalid"
        ) from exc
    if not result.is_finite() or result < 0:
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal decimal is invalid"
        )
    return result


def _fixed(value: Decimal, places: int) -> str:
    quantum = Decimal(1).scaleb(-places)
    if value != value.quantize(quantum):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal decimal scale differs"
        )
    return format(value.quantize(quantum), "f")


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "population": "all_12_listed_consideration_identity_decisions",
            "admission": "four_element_identity_resolution_matched_only",
            "valuation_session": "first_absent_target_exchange_session",
            "price": "canonical_unadjusted_consideration_security_eod_close",
            "formula": "cash_plus_ratio_times_close",
            "decimal_scales": {"cash": 2, "ratio": 6, "close": 10, "value": 16},
            "adjustment_flag": "retained_not_silently_corrected",
            "execution_price": "not_claimed",
            "strategy_outcome_label": "not_created",
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackListedConsiderationTerminalEvidenceV1,
) -> StrongLeaderPullbackListedConsiderationTerminalEvidenceResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_listed_consideration_terminal_evidence(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
                "existing listed terminal evidence differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence staging target exists"
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
    reread = read_strong_leader_pullback_listed_consideration_terminal_evidence(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackListedConsiderationTerminalEvidenceResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence paths must be absolute"
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
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence custody or target is unsafe"
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
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "listed terminal evidence file metadata differs"
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
        sorted((str(key), count) for key, count in counter.items() if count)
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
        raise StrongLeaderPullbackListedConsiderationTerminalEvidenceError(
            "network access is prohibited during listed terminal evidence"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = (  # type: ignore[assignment]
            original_create_connection
        )
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
