"""Trading-cessation and last-EOD evidence for first-strategy lifecycle cases."""

from __future__ import annotations

import bisect
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
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    _clause_spans,
    _fingerprint,
    _json_bytes,
    _normalized_text,
    _sha256_bytes,
)
from tip_api.services.strong_leader_pullback_sec_form25_candidates import (
    StrongLeaderPullbackSecForm25CandidatesResult,
    read_strong_leader_pullback_sec_form25_candidates,
)
from tip_api.services.strong_leader_pullback_sec_party_relation_adjudication import (
    SecPartyRelationDecisionV1,
    StrongLeaderPullbackSecPartyRelationAdjudicationResult,
    read_strong_leader_pullback_sec_party_relation_adjudication,
)
from tip_api.services.strong_leader_pullback_sec_termination_reason_adjudication import (
    SecTerminationReasonDecisionV1,
    StrongLeaderPullbackSecTerminationReasonAdjudicationResult,
    read_strong_leader_pullback_sec_termination_reason_adjudication,
)
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    LifecycleSourceAcceptanceCaseV1,
    StrongLeaderPullbackSourceAcceptanceSampleResult,
    read_strong_leader_pullback_source_acceptance_sample,
)


CONTRACT_VERSION = "strong-leader-pullback-trading-cessation-adjudication/1.0"
REPORT_FILE = "trading-cessation.json"
EXPECTED_CASE_COUNT = 61
MAXIMUM_REPORT_BYTES = 3 * 1024 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 4096
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"

# Finite, source-hash-bound human review. An unregistered case fails closed.
_BEFORE_OPEN_SEQUENCES = frozenset(
    {
        7,
        11,
        14,
        20,
        26,
        28,
        35,
        38,
        40,
        49,
        52,
        55,
        59,
        64,
        72,
        74,
        79,
        87,
        92,
        95,
        99,
        100,
        107,
        113,
        115,
        118,
        122,
        143,
        147,
        150,
        152,
        156,
        158,
        174,
        178,
        181,
        184,
        190,
        194,
        197,
        200,
        204,
        211,
        214,
        218,
    }
)
_AFTER_CLOSE_SEQUENCES = frozenset({1, 45, 68, 83, 90, 104, 139, 208})
_UNRESOLVED_TIMING_SEQUENCES = frozenset(
    {109, 124, 129, 136, 161, 166, 172, 187}
)
_REGISTERED_SEQUENCES = (
    _BEFORE_OPEN_SEQUENCES
    | _AFTER_CLOSE_SEQUENCES
    | _UNRESOLVED_TIMING_SEQUENCES
)
_STOP_DATE_OVERRIDES = {
    40: date(2025, 11, 28),
    68: date(2026, 4, 22),
    74: date(2025, 7, 25),
    83: date(2026, 5, 13),
    104: date(2025, 7, 24),
    139: date(2026, 7, 14),
    152: date(2026, 8, 5),
    174: date(2026, 2, 2),
    190: date(2026, 3, 20),
    197: date(2025, 9, 2),
    208: date(2026, 7, 14),
}
_ACTION_RE = re.compile(r"\b(?:suspend|halt|cease|ceased)\w*\b", re.IGNORECASE)
_BEFORE_OPEN_RE = re.compile(
    r"\b(?:prior to|before)\s+(?:the\s+)?(?:market\s+)?(?:open|opening)\b|"
    r"\bprior to\s+Nasdaq[’']s\s+opening\b|"
    r"\bbefore\s+the\s+market\s+opens\b|"
    r"\bas of\s+(?:the\s+)?open(?:ing)?\s+of\s+trading\b",
    re.IGNORECASE,
)
_AFTER_CLOSE_RE = re.compile(
    r"\b(?:after-hours|after hours|after market close|close of business|"
    r"following\s+(?:the\s+)?closing\s+of\s+(?:the\s+)?(?:market|trading)|"
    r"8:00\s+p\.m\.(?=$|[\s,;]))",
    re.IGNORECASE,
)

ResolutionState = Literal["matched", "conflicting", "unsupported"]
TimingProfile = Literal["before_open", "after_close", "unresolved"]


class StrongLeaderPullbackTradingCessationAdjudicationError(RuntimeError):
    """Raised when cessation evidence cannot be reconciled safely."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EodPresenceEvidenceV1(_FrozenModel):
    session_date: date
    record_count: int = Field(ge=1)
    content_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    parquet_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_snapshot_date: date
    identity_snapshot_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    target_bar_present: bool
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "EodPresenceEvidenceV1":
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("EOD presence evidence differs")
        return self


class TradingCessationDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    instrument_id: UUID
    transaction_completion_date: date
    provider_delist_date_candidate: date
    termination_reason_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    party_relation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    timing_profile: TimingProfile
    resolution_state: ResolutionState
    sec_stated_trading_stop_boundary_date: date | None = None
    expected_last_eod_session: date | None = None
    observed_last_eod_session: date | None = None
    next_exchange_session: date | None = None
    form25_common_equity_notice_count: int = Field(ge=0, le=2)
    cessation_evidence_start: int | None = Field(default=None, ge=0)
    cessation_evidence_end: int | None = Field(default=None, ge=1)
    cessation_evidence_text: str | None = Field(
        default=None, min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS
    )
    cessation_evidence_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    eod_presence_evidence: tuple[EodPresenceEvidenceV1, ...]
    first_tradable_date: None = None
    legal_delisting_effective_date: None = None
    canonical_lifecycle_fact_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("cessation_evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str | None) -> str | None:
        if value is not None and value != _normalized_text(value):
            raise ValueError("cessation evidence is not normalized")
        return value

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("cessation reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "TradingCessationDecisionV1":
        supported = self.resolution_state in {"matched", "conflicting"}
        dates = (
            self.sec_stated_trading_stop_boundary_date,
            self.expected_last_eod_session,
            self.observed_last_eod_session,
            self.next_exchange_session,
        )
        evidence = (
            self.cessation_evidence_start,
            self.cessation_evidence_end,
            self.cessation_evidence_text,
            self.cessation_evidence_sha256,
        )
        if (
            (supported and (not all(value is not None for value in dates) or not all(value is not None for value in evidence)))
            or (not supported and (any(value is not None for value in dates) or any(value is not None for value in evidence) or self.eod_presence_evidence))
            or self.cessation_evidence_sha256
            != _optional_text_sha256(self.cessation_evidence_text)
            or not _valid_span(
                self.cessation_evidence_start, self.cessation_evidence_end
            )
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("cessation decision differs")
        if self.resolution_state == "matched":
            if (
                self.observed_last_eod_session != self.expected_last_eod_session
                or not _bar_presence(
                    self.eod_presence_evidence, self.expected_last_eod_session
                )
                or _bar_presence(
                    self.eod_presence_evidence, self.next_exchange_session
                )
            ):
                raise ValueError("matched cessation evidence differs")
        if (
            self.resolution_state == "conflicting"
            and self.observed_last_eod_session == self.expected_last_eod_session
            and not _bar_presence(
                self.eod_presence_evidence, self.next_exchange_session
            )
        ):
            raise ValueError("conflicting cessation evidence differs")
        return self


class StrongLeaderPullbackTradingCessationAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-trading-cessation-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["trading_cessation_evidence_adjudicated"] = (
        "trading_cessation_evidence_adjudicated"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_sample_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_sample_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    form25_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    form25_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    termination_reason_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    party_relation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    party_relation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[61] = EXPECTED_CASE_COUNT
    matched_cessation_count: int = Field(ge=0, le=61)
    conflicting_cessation_count: int = Field(ge=0, le=61)
    unsupported_cessation_count: int = Field(ge=0, le=61)
    resolution_state_counts: tuple[tuple[str, int], ...]
    timing_profile_counts: tuple[tuple[str, int], ...]
    selected_eod_session_count: int = Field(ge=1)
    selected_eod_session_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    decisions: tuple[TradingCessationDecisionV1, ...]
    last_eod_observation_evidence_count: int = Field(ge=0, le=61)
    first_tradable_date_count: Literal[0] = 0
    complete_first_and_last_tradable_field_count: Literal[0] = 0
    legal_delisting_effective_date_count: Literal[0] = 0
    complete_suspension_and_delisting_field_count: Literal[0] = 0
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
    def report_reconciles(self) -> "StrongLeaderPullbackTradingCessationAdjudicationV1":
        resolutions = Counter(item.resolution_state for item in self.decisions)
        profiles = Counter(item.timing_profile for item in self.decisions)
        if (
            len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(item.request_sequence for item in self.decisions))
            or {item.request_sequence for item in self.decisions}
            != _REGISTERED_SEQUENCES
            or self.matched_cessation_count != resolutions["matched"]
            or self.conflicting_cessation_count != resolutions["conflicting"]
            or self.unsupported_cessation_count != resolutions["unsupported"]
            or self.resolution_state_counts != _ordered(resolutions)
            or self.timing_profile_counts != _ordered(profiles)
            or self.last_eod_observation_evidence_count
            != self.matched_cessation_count + self.conflicting_cessation_count
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("cessation adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTradingCessationAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackTradingCessationAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _EodContext:
    sessions: tuple[date, ...]
    evidence_by_session: dict[date, EodPresenceEvidenceV1]


def build_strong_leader_pullback_trading_cessation_adjudication(
    *,
    source_sample_root: Path,
    source_sample_custody_root: Path,
    form25_root: Path,
    form25_custody_root: Path,
    termination_reason_root: Path,
    termination_reason_custody_root: Path,
    party_relation_root: Path,
    party_relation_custody_root: Path,
    eod_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTradingCessationAdjudicationResult:
    with _network_prohibited():
        sample = read_strong_leader_pullback_source_acceptance_sample(
            output_root=source_sample_root,
            output_custody_root=source_sample_custody_root,
        )
        form25 = read_strong_leader_pullback_sec_form25_candidates(
            output_root=form25_root,
            output_custody_root=form25_custody_root,
        )
        reasons = read_strong_leader_pullback_sec_termination_reason_adjudication(
            output_root=termination_reason_root,
            output_custody_root=termination_reason_custody_root,
        )
        parties = read_strong_leader_pullback_sec_party_relation_adjudication(
            output_root=party_relation_root,
            output_custody_root=party_relation_custody_root,
        )
        report = _build_report(
            sample=sample,
            form25=form25,
            reasons=reasons,
            parties=parties,
            eod_repository=CanonicalEodReadRepository(eod_root),
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_trading_cessation_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTradingCessationAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTradingCessationAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation report bytes are not canonical"
        )
    return StrongLeaderPullbackTradingCessationAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    sample: StrongLeaderPullbackSourceAcceptanceSampleResult,
    form25: StrongLeaderPullbackSecForm25CandidatesResult,
    reasons: StrongLeaderPullbackSecTerminationReasonAdjudicationResult,
    parties: StrongLeaderPullbackSecPartyRelationAdjudicationResult,
    eod_repository: CanonicalEodReadRepository,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTradingCessationAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation revision is invalid"
        )
    if (
        parties.report.termination_reason_report_sha256 != reasons.report_sha256
        or parties.report.termination_reason_logical_fingerprint
        != reasons.report.logical_fingerprint
        or parties.report.matched_relation_count != EXPECTED_CASE_COUNT
        or reasons.report.matched_reason_count != EXPECTED_CASE_COUNT
        or sample.report.lifecycle_case_count != 64
        or form25.report.form25_document_count != 64
    ):
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation input bindings differ"
        )
    samples = {str(item.instrument_id): item for item in sample.report.lifecycle_cases}
    reason_decisions = {item.request_sequence: item for item in reasons.report.decisions}
    party_decisions = {item.request_sequence: item for item in parties.report.decisions}
    if set(reason_decisions) != _REGISTERED_SEQUENCES or set(party_decisions) != set(
        reason_decisions
    ):
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation registered population differs"
        )
    common_form25_counts: Counter[str] = Counter()
    for item in form25.report.candidates:
        if any(
            "common" in value.lower() and "right" not in value.lower()
            for value in item.security_class_descriptions
        ):
            common_form25_counts[str(item.instrument_id)] += 1
    session_index = eod_repository.list_session_index()
    eod_contexts, selected_integrity = _read_eod_contexts(
        repository=eod_repository,
        session_index=session_index,
        parties=party_decisions,
    )
    decisions = tuple(
        _document_decision(
            reason=reason_decisions[sequence],
            party=party_decisions[sequence],
            sample=samples[str(party_decisions[sequence].instrument_id)],
            form25_common_equity_notice_count=common_form25_counts[
                str(party_decisions[sequence].instrument_id)
            ],
            context=eod_contexts.get(sequence),
        )
        for sequence in sorted(party_decisions)
    )
    resolutions = Counter(item.resolution_state for item in decisions)
    profiles = Counter(item.timing_profile for item in decisions)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "source_sample_report_sha256": sample.report_sha256,
        "source_sample_logical_fingerprint": sample.report.logical_fingerprint,
        "form25_report_sha256": form25.report_sha256,
        "form25_logical_fingerprint": form25.report.logical_fingerprint,
        "termination_reason_report_sha256": reasons.report_sha256,
        "termination_reason_logical_fingerprint": reasons.report.logical_fingerprint,
        "party_relation_report_sha256": parties.report_sha256,
        "party_relation_logical_fingerprint": parties.report.logical_fingerprint,
        "matched_cessation_count": resolutions["matched"],
        "conflicting_cessation_count": resolutions["conflicting"],
        "unsupported_cessation_count": resolutions["unsupported"],
        "resolution_state_counts": _ordered(resolutions),
        "timing_profile_counts": _ordered(profiles),
        "selected_eod_session_count": len(selected_integrity),
        "selected_eod_session_fingerprint": _fingerprint(selected_integrity),
        "decisions": decisions,
        "last_eod_observation_evidence_count": (
            resolutions["matched"] + resolutions["conflicting"]
        ),
    }
    provisional = StrongLeaderPullbackTradingCessationAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTradingCessationAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _read_eod_contexts(
    *,
    repository: CanonicalEodReadRepository,
    session_index: tuple[date, ...],
    parties: dict[int, SecPartyRelationDecisionV1],
) -> tuple[dict[int, _EodContext], tuple[dict[str, object], ...]]:
    if not session_index or session_index != tuple(sorted(set(session_index))):
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation EOD session index differs"
        )
    session_sets: dict[int, tuple[date, ...]] = {}
    needed = set()
    for sequence, party in parties.items():
        timing = _registered_timing(sequence)
        if timing == "unresolved":
            continue
        stop = _STOP_DATE_OVERRIDES.get(sequence, party.transaction_completion_date)
        stop_index = bisect.bisect_left(session_index, stop)
        if timing == "before_open":
            if stop_index == 0:
                raise StrongLeaderPullbackTradingCessationAdjudicationError(
                    "cessation previous session is unavailable"
                )
            expected_index = stop_index - 1
        else:
            if stop_index >= len(session_index) or session_index[stop_index] != stop:
                raise StrongLeaderPullbackTradingCessationAdjudicationError(
                    "after-close stop date is not an exchange session"
                )
            expected_index = stop_index
        indexes = tuple(
            value
            for value in (expected_index - 1, expected_index, expected_index + 1)
            if 0 <= value < len(session_index)
        )
        dates = tuple(session_index[value] for value in indexes)
        session_sets[sequence] = dates
        needed.update(dates)
    reads = repository.read_history_sessions(tuple(sorted(needed)))
    by_date = {item.integrity.session_date: item for item in reads}
    if set(by_date) != needed:
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation EOD read population differs"
        )
    contexts = {}
    for sequence, dates in session_sets.items():
        instrument_id = parties[sequence].instrument_id
        evidence = []
        for session in dates:
            read = by_date[session]
            present = any(item.instrument_id == instrument_id for item in read.bars)
            values = {
                "session_date": session,
                "record_count": read.integrity.record_count,
                "content_fingerprint": read.integrity.content_fingerprint,
                "parquet_sha256": read.integrity.parquet_sha256,
                "identity_snapshot_date": read.integrity.identity_snapshot_date,
                "identity_snapshot_fingerprint": (
                    read.integrity.identity_snapshot_fingerprint
                ),
                "target_bar_present": present,
            }
            provisional = EodPresenceEvidenceV1.model_construct(
                **values, logical_fingerprint="0" * 64
            )
            evidence.append(
                EodPresenceEvidenceV1.model_validate(
                    {
                        **values,
                        "logical_fingerprint": _fingerprint(
                            provisional.model_dump(
                                mode="json", exclude={"logical_fingerprint"}
                            )
                        ),
                    }
                )
            )
        contexts[sequence] = _EodContext(
            sessions=dates, evidence_by_session={item.session_date: item for item in evidence}
        )
    selected_integrity = tuple(
        {
            "session_date": item.integrity.session_date.isoformat(),
            "record_count": item.integrity.record_count,
            "content_fingerprint": item.integrity.content_fingerprint,
            "parquet_sha256": item.integrity.parquet_sha256,
            "identity_snapshot_date": item.integrity.identity_snapshot_date.isoformat(),
            "identity_snapshot_fingerprint": (
                item.integrity.identity_snapshot_fingerprint
            ),
        }
        for item in sorted(reads, key=lambda value: value.integrity.session_date)
    )
    return contexts, selected_integrity


def _document_decision(
    *,
    reason: SecTerminationReasonDecisionV1,
    party: SecPartyRelationDecisionV1,
    sample: LifecycleSourceAcceptanceCaseV1,
    form25_common_equity_notice_count: int,
    context: _EodContext | None,
) -> TradingCessationDecisionV1:
    if (
        reason.instrument_id != party.instrument_id
        or reason.logical_fingerprint != party.termination_reason_fingerprint
        or reason.transaction_completion_date != party.transaction_completion_date
        or reason.resolution_state != "matched"
        or party.resolution_state != "matched"
        or sample.instrument_id != party.instrument_id
    ):
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation source decision identity differs"
        )
    timing = _registered_timing(reason.request_sequence)
    if timing == "unresolved":
        values = {
            "request_sequence": reason.request_sequence,
            "instrument_id": reason.instrument_id,
            "transaction_completion_date": reason.transaction_completion_date,
            "provider_delist_date_candidate": sample.provider_delist_date_candidate,
            "termination_reason_fingerprint": reason.logical_fingerprint,
            "party_relation_fingerprint": party.logical_fingerprint,
            "timing_profile": timing,
            "resolution_state": "unsupported",
            "form25_common_equity_notice_count": form25_common_equity_notice_count,
            "eod_presence_evidence": (),
            "decision_reasons": ("source_does_not_prove_trading_stop_time",),
        }
    else:
        if context is None:
            raise StrongLeaderPullbackTradingCessationAdjudicationError(
                "cessation EOD context is unavailable"
            )
        stop = _STOP_DATE_OVERRIDES.get(
            reason.request_sequence, reason.transaction_completion_date
        )
        if timing == "before_open":
            expected = max(session for session in context.sessions if session < stop)
        else:
            expected = stop
        next_session = min(session for session in context.sessions if session > expected)
        observed = max(
            (
                session
                for session, evidence in context.evidence_by_session.items()
                if session <= expected and evidence.target_bar_present
            ),
            default=None,
        )
        clause = _primary_cessation_candidate(reason.item_3_01_text, timing)
        if clause is None or observed is None:
            raise StrongLeaderPullbackTradingCessationAdjudicationError(
                "registered cessation evidence is unavailable for "
                f"request sequence {reason.request_sequence}"
            )
        matched = (
            observed == expected
            and context.evidence_by_session[expected].target_bar_present
            and not context.evidence_by_session[next_session].target_bar_present
        )
        state: ResolutionState = "matched" if matched else "conflicting"
        start, end, text = clause
        values = {
            "request_sequence": reason.request_sequence,
            "instrument_id": reason.instrument_id,
            "transaction_completion_date": reason.transaction_completion_date,
            "provider_delist_date_candidate": sample.provider_delist_date_candidate,
            "termination_reason_fingerprint": reason.logical_fingerprint,
            "party_relation_fingerprint": party.logical_fingerprint,
            "timing_profile": timing,
            "resolution_state": state,
            "sec_stated_trading_stop_boundary_date": stop,
            "expected_last_eod_session": expected,
            "observed_last_eod_session": observed,
            "next_exchange_session": next_session,
            "form25_common_equity_notice_count": form25_common_equity_notice_count,
            "cessation_evidence_start": start,
            "cessation_evidence_end": end,
            "cessation_evidence_text": text,
            "cessation_evidence_sha256": _sha256_bytes(text.encode("utf-8")),
            "eod_presence_evidence": tuple(
                context.evidence_by_session[session] for session in context.sessions
            ),
            "decision_reasons": tuple(
                sorted(
                    {
                        "exact_sec_trading_stop_boundary_retained",
                        "formal_eod_presence_and_next_session_absence_checked",
                        "last_eod_observation_is_not_first_tradable_or_legal_delisting_date",
                        *(
                            ()
                            if matched
                            else ("sec_stop_boundary_and_eod_presence_conflict",)
                        ),
                    }
                )
            ),
        }
    provisional = TradingCessationDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TradingCessationDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _primary_cessation_candidate(
    text: str, timing: Literal["before_open", "after_close"]
) -> tuple[int, int, str] | None:
    normalized = _normalized_text(text)
    timing_pattern = _BEFORE_OPEN_RE if timing == "before_open" else _AFTER_CLOSE_RE
    candidates = tuple(
        clause
        for clause in _clause_spans(normalized)
        if _ACTION_RE.search(clause[2]) and timing_pattern.search(clause[2])
    )
    if not candidates:
        return None
    selected = candidates[0]
    if len(selected[2]) > MAXIMUM_EVIDENCE_TEXT_CHARS:
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "selected cessation clause exceeds bounded size"
        )
    return selected


def _registered_timing(sequence: int) -> TimingProfile:
    if sequence in _BEFORE_OPEN_SEQUENCES:
        return "before_open"
    if sequence in _AFTER_CLOSE_SEQUENCES:
        return "after_close"
    if sequence in _UNRESOLVED_TIMING_SEQUENCES:
        return "unresolved"
    raise StrongLeaderPullbackTradingCessationAdjudicationError(
        "unregistered cessation case"
    )


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "before_open_sequences": sorted(_BEFORE_OPEN_SEQUENCES),
            "after_close_sequences": sorted(_AFTER_CLOSE_SEQUENCES),
            "unresolved_timing_sequences": sorted(_UNRESOLVED_TIMING_SEQUENCES),
            "stop_date_overrides": {
                str(key): value.isoformat()
                for key, value in sorted(_STOP_DATE_OVERRIDES.items())
            },
            "action_pattern": _ACTION_RE.pattern,
            "before_open_pattern": _BEFORE_OPEN_RE.pattern,
            "after_close_pattern": _AFTER_CLOSE_RE.pattern,
            "maximum_evidence_text_chars": MAXIMUM_EVIDENCE_TEXT_CHARS,
            "first_tradable_date": "unresolved",
            "legal_delisting_effective_date": "unresolved",
        }
    )


def _bar_presence(
    evidence: tuple[EodPresenceEvidenceV1, ...], session: date | None
) -> bool:
    if session is None:
        return False
    return any(item.session_date == session and item.target_bar_present for item in evidence)


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackTradingCessationAdjudicationV1,
) -> StrongLeaderPullbackTradingCessationAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTradingCessationAdjudicationError(
                "existing cessation report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation staging target exists"
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
    reread = read_strong_leader_pullback_trading_cessation_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTradingCessationAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation paths must be absolute"
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
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation custody or target is unsafe"
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
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "cessation file metadata differs"
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
    original_getaddrinfo = socket.getaddrinfo

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackTradingCessationAdjudicationError(
            "network access is prohibited during cessation adjudication"
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
