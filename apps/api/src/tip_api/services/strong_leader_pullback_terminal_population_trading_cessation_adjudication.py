"""Trading-cessation evidence for the corrected terminal-population case."""

from __future__ import annotations

import bisect
import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import strong_leader_pullback_sec_transaction_event_adjudication as event
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_core_adjudication as core_reader,
)
from tip_api.services import strong_leader_pullback_trading_cessation_adjudication as cessation


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-population-trading-cessation-adjudication/1.0"
)
REPORT_FILE = "trading-cessation.json"
MAXIMUM_REPORT_BYTES = 256 * 1024
MAXIMUM_EVIDENCE_TEXT_CHARS = 2048
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"
_REALIZED_STOP_RE = re.compile(
    r"\btrading\s+of\b[^.]{0,500}\b(?:halted|suspended|ceased)\b"
    r"[^.]{0,500}(?:\.|$)",
    re.IGNORECASE,
)
_CESSATION_DATE_RE = re.compile(
    rf"\b(?:opening\s+of\s+trading|market\s+open(?:ing)?)\s+on\s+"
    rf"({event._DATE_TOKEN})\b",
    re.IGNORECASE,
)

ResolutionState = Literal["matched", "conflicting", "unsupported"]


class StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
    RuntimeError
):
    """Raised when corrected-population cessation evidence is unsafe."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalPopulationTradingCessationDecisionV1(_FrozenModel):
    instrument_id: UUID
    resolution_state: ResolutionState
    timing_profile: Literal["before_open"] | None = None
    transaction_completion_date: date
    source_stated_trading_stop_boundary_date: date | None = None
    expected_last_eod_session: date | None = None
    observed_last_eod_session: date | None = None
    next_exchange_session: date | None = None
    cessation_evidence_start: int | None = Field(default=None, ge=0)
    cessation_evidence_end: int | None = Field(default=None, ge=1)
    cessation_evidence_text: str | None = Field(
        default=None, min_length=1, max_length=MAXIMUM_EVIDENCE_TEXT_CHARS
    )
    cessation_evidence_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    eod_presence_evidence: tuple[cessation.EodPresenceEvidenceV1, ...]
    first_tradable_date: None = None
    legal_delisting_effective_date: None = None
    canonical_lifecycle_fact_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("cessation_evidence_text")
    @classmethod
    def evidence_is_normalized(cls, value: str | None) -> str | None:
        if value is not None and value != cessation._normalized_text(value):
            raise ValueError("terminal-population cessation evidence differs")
        return value

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if not values or values != tuple(sorted(set(values))):
            raise ValueError("terminal-population cessation reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(
        self,
    ) -> "TerminalPopulationTradingCessationDecisionV1":
        supported = self.resolution_state in {"matched", "conflicting"}
        dates = (
            self.source_stated_trading_stop_boundary_date,
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
            (supported and not all(value is not None for value in (*dates, *evidence)))
            or (
                not supported
                and (
                    self.timing_profile is not None
                    or any(value is not None for value in (*dates, *evidence))
                    or self.eod_presence_evidence
                )
            )
            or self.cessation_evidence_sha256
            != cessation._optional_text_sha256(self.cessation_evidence_text)
            or not cessation._valid_span(
                self.cessation_evidence_start, self.cessation_evidence_end
            )
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population cessation decision differs")
        if self.resolution_state == "matched" and (
            self.observed_last_eod_session != self.expected_last_eod_session
            or not cessation._bar_presence(
                self.eod_presence_evidence, self.expected_last_eod_session
            )
            or cessation._bar_presence(
                self.eod_presence_evidence, self.next_exchange_session
            )
        ):
            raise ValueError("matched terminal-population cessation differs")
        return self


class StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1(
    _FrozenModel
):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-trading-cessation-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["trading_cessation_evidence_adjudicated"] = (
        "trading_cessation_evidence_adjudicated"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    core_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    core_adjudication_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_case_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_case_count: Literal[1] = 1
    matched_cessation_count: int = Field(ge=0, le=1)
    conflicting_cessation_count: int = Field(ge=0, le=1)
    unsupported_cessation_count: int = Field(ge=0, le=1)
    selected_eod_session_count: int = Field(ge=0, le=3)
    selected_eod_session_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    decision: TerminalPopulationTradingCessationDecisionV1
    last_eod_observation_evidence_count: int = Field(ge=0, le=1)
    first_tradable_date_count: Literal[0] = 0
    legal_delisting_effective_date_count: Literal[0] = 0
    normalized_payoff_term_count: Literal[0] = 0
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
    ) -> "StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1":
        states = {
            "matched": self.matched_cessation_count,
            "conflicting": self.conflicting_cessation_count,
            "unsupported": self.unsupported_cessation_count,
        }
        if (
            sum(states.values()) != 1
            or states[self.decision.resolution_state] != 1
            or self.last_eod_observation_evidence_count
            != int(self.decision.resolution_state in {"matched", "conflicting"})
            or self.selected_eod_session_count
            != len(self.decision.eod_presence_evidence)
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population cessation report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_trading_cessation_adjudication(
    *,
    core_adjudication_root: Path,
    core_adjudication_custody_root: Path,
    eod_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationResult:
    """Compare one source-stated stop boundary to stable-ID EOD presence."""

    with base._network_prohibited():
        core = core_reader.read_strong_leader_pullback_terminal_population_sec_core_adjudication(
            output_root=core_adjudication_root,
            output_custody_root=core_adjudication_custody_root,
        )
        report = _build_report(
            core=core,
            eod_repository=CanonicalEodReadRepository(eod_root),
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_trading_cessation_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation report bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, core: object, eod_repository: object,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation revision is invalid"
        )
    core_report = core.report
    if (
        core_report.lifecycle_case_count != 1
        or core_report.cover_identity.resolution_state
        != "matched_in_source_lifecycle_window"
        or core_report.transaction_event.resolution_state != "matched"
        or core_report.termination_reason.resolution_state != "matched"
        or core_report.transaction_event.instrument_id
        != core_report.termination_reason.instrument_id
        or core_report.transaction_event.selected_event_date is None
    ):
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation core binding differs"
        )
    decision, selected_integrity = _decision(
        instrument_id=core_report.transaction_event.instrument_id,
        transaction_completion_date=core_report.transaction_event.selected_event_date,
        item_3_01_text=core_report.termination_reason.item_3_01_text,
        eod_repository=eod_repository,
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "core_adjudication_report_sha256": core.report_sha256,
        "core_adjudication_logical_fingerprint": core_report.logical_fingerprint,
        "source_case_fingerprint": core_report.source_case_fingerprint,
        "matched_cessation_count": int(decision.resolution_state == "matched"),
        "conflicting_cessation_count": int(
            decision.resolution_state == "conflicting"
        ),
        "unsupported_cessation_count": int(
            decision.resolution_state == "unsupported"
        ),
        "selected_eod_session_count": len(selected_integrity),
        "selected_eod_session_fingerprint": base._fingerprint(selected_integrity),
        "decision": decision,
        "last_eod_observation_evidence_count": int(
            decision.resolution_state in {"matched", "conflicting"}
        ),
    }
    provisional = StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _decision(
    *, instrument_id: UUID, transaction_completion_date: date,
    item_3_01_text: str, eod_repository: object,
) -> tuple[TerminalPopulationTradingCessationDecisionV1, tuple[dict[str, object], ...]]:
    candidate = _realized_before_open_candidate(item_3_01_text)
    if candidate is None:
        values = {
            "instrument_id": instrument_id,
            "resolution_state": "unsupported",
            "transaction_completion_date": transaction_completion_date,
            "eod_presence_evidence": (),
            "decision_reasons": ("source_does_not_prove_exact_trading_stop_time",),
        }
        selected_integrity: tuple[dict[str, object], ...] = ()
    else:
        start, end, text, boundary_date = candidate
        if boundary_date != transaction_completion_date:
            raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
                "terminal-population stop and completion dates differ"
            )
        session_index = eod_repository.list_session_index()
        if not session_index or session_index != tuple(sorted(set(session_index))):
            raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
                "terminal-population cessation EOD index differs"
            )
        boundary_index = bisect.bisect_left(session_index, boundary_date)
        if (
            boundary_index < 2
            or boundary_index >= len(session_index)
            or session_index[boundary_index] != boundary_date
        ):
            raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
                "terminal-population cessation sessions are unavailable"
            )
        expected = session_index[boundary_index - 1]
        next_session = session_index[boundary_index]
        sessions = (
            session_index[boundary_index - 2],
            expected,
            next_session,
        )
        reads = eod_repository.read_instrument_presence_sessions(
            sessions, frozenset({instrument_id})
        )
        if tuple(item.integrity.session_date for item in reads) != sessions:
            raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
                "terminal-population cessation EOD population differs"
            )
        eod_evidence = tuple(
            _presence_evidence(read=item, instrument_id=instrument_id) for item in reads
        )
        observed = max(
            (
                item.session_date
                for item in eod_evidence
                if item.session_date <= expected and item.target_bar_present
            ),
            default=None,
        )
        matched = (
            observed == expected
            and cessation._bar_presence(eod_evidence, expected)
            and not cessation._bar_presence(eod_evidence, next_session)
        )
        values = {
            "instrument_id": instrument_id,
            "resolution_state": "matched" if matched else "conflicting",
            "timing_profile": "before_open",
            "transaction_completion_date": transaction_completion_date,
            "source_stated_trading_stop_boundary_date": boundary_date,
            "expected_last_eod_session": expected,
            "observed_last_eod_session": observed,
            "next_exchange_session": next_session,
            "cessation_evidence_start": start,
            "cessation_evidence_end": end,
            "cessation_evidence_text": text,
            "cessation_evidence_sha256": base._sha256_bytes(text.encode("utf-8")),
            "eod_presence_evidence": eod_evidence,
            "decision_reasons": tuple(
                sorted(
                    {
                        "realized_before_open_trading_halt_statement_retained",
                        "stable_id_expected_and_next_eod_presence_checked",
                        "last_eod_observation_is_not_legal_delisting_effectiveness",
                        *(() if matched else ("sec_boundary_and_eod_presence_conflict",)),
                    }
                )
            ),
        }
        selected_integrity = tuple(
            {
                "session_date": item.integrity.session_date.isoformat(),
                "record_count": item.integrity.record_count,
                "content_fingerprint": item.integrity.content_fingerprint,
                "parquet_sha256": item.integrity.parquet_sha256,
                "identity_snapshot_date": (
                    item.integrity.identity_snapshot_date.isoformat()
                ),
                "identity_snapshot_fingerprint": (
                    item.integrity.identity_snapshot_fingerprint
                ),
            }
            for item in reads
        )
    provisional = TerminalPopulationTradingCessationDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    decision = TerminalPopulationTradingCessationDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )
    return decision, selected_integrity


def _realized_before_open_candidate(
    text: str,
) -> tuple[int, int, str, date] | None:
    normalized = cessation._normalized_text(text)
    candidates = tuple(
        (match.start(), match.end(), match.group(0))
        for match in _REALIZED_STOP_RE.finditer(normalized)
        if cessation._BEFORE_OPEN_RE.search(match.group(0))
    )
    if len(candidates) != 1:
        return None
    start, end, evidence_text = candidates[0]
    matches = tuple(_CESSATION_DATE_RE.finditer(evidence_text))
    if len(matches) != 1 or len(evidence_text) > MAXIMUM_EVIDENCE_TEXT_CHARS:
        return None
    return start, end, evidence_text, event._parse_date_token(matches[0].group(1))


def _presence_evidence(
    *, read: object, instrument_id: UUID
) -> cessation.EodPresenceEvidenceV1:
    values = {
        "session_date": read.integrity.session_date,
        "record_count": read.integrity.record_count,
        "content_fingerprint": read.integrity.content_fingerprint,
        "parquet_sha256": read.integrity.parquet_sha256,
        "identity_snapshot_date": read.integrity.identity_snapshot_date,
        "identity_snapshot_fingerprint": (
            read.integrity.identity_snapshot_fingerprint
        ),
        "target_bar_present": instrument_id in read.instrument_ids,
    }
    provisional = cessation.EodPresenceEvidenceV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return cessation.EodPresenceEvidenceV1.model_validate(
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
            "source_rule": "one_realized_before_open_stop_sentence_one_date",
            "realized_stop_pattern": _REALIZED_STOP_RE.pattern,
            "before_open_pattern": cessation._BEFORE_OPEN_RE.pattern,
            "date_pattern": _CESSATION_DATE_RE.pattern,
            "selected_eod_sessions": "prior_expected_next",
            "identity_key": "stable_instrument_id",
            "first_tradable_date": "unresolved",
            "legal_delisting_effective_date": "unresolved",
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationV1,
) -> StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_trading_cessation_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
                "existing terminal-population cessation report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
                "terminal-population cessation report exceeds byte ceiling"
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
    reread = read_strong_leader_pullback_terminal_population_trading_cessation_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation paths must be absolute"
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
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation target is unsafe"
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
        raise StrongLeaderPullbackTerminalPopulationTradingCessationAdjudicationError(
            "terminal-population cessation output is unsafe"
        )
    return target
