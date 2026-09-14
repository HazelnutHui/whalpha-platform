"""Daily reference values for the three residual listed consideration cases."""

from __future__ import annotations

import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_adjudication as identities_source,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_terminal_evidence as base,
)
from tip_api.services import (
    strong_leader_pullback_sec_consideration_adjudication as consideration_source,
)
from tip_api.services import (
    strong_leader_pullback_terminal_payoff_terms as payoff_source,
)
from tip_api.services import (
    strong_leader_pullback_trading_cessation_adjudication as cessation_source,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-listed-consideration-residual-terminal-evidence/1.0"
)
REPORT_FILE = "listed-consideration-residual-terminal-evidence.json"
EXPECTED_CASE_COUNT = 3
EXPECTED_PRIOR_VALUE_COUNT = 9
EXPECTED_CUMULATIVE_VALUE_COUNT = 12
MAXIMUM_REPORT_BYTES = 512 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"


class StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
    RuntimeError
):
    """Raised when the residual terminal references cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1(
    _FrozenModel
):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-residual-terminal-evidence/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "listed_consideration_residual_reference_values_documented"
    ] = "listed_consideration_residual_reference_values_documented"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_terminal_evidence_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    prior_terminal_evidence_logical_fingerprint: str = Field(
        pattern=_SHA256_PATTERN
    )
    residual_identity_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    residual_identity_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    cessation_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    cessation_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_terms_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    residual_case_count: Literal[3] = EXPECTED_CASE_COUNT
    prior_terminal_reference_value_count: Literal[9] = EXPECTED_PRIOR_VALUE_COUNT
    residual_terminal_reference_value_count: Literal[3] = EXPECTED_CASE_COUNT
    cumulative_terminal_reference_value_count: Literal[12] = (
        EXPECTED_CUMULATIVE_VALUE_COUNT
    )
    valuation_session_count: int = Field(ge=1, le=EXPECTED_CASE_COUNT)
    decision_state_counts: tuple[tuple[str, int], ...]
    price_quality_status_counts: tuple[tuple[str, int], ...]
    price_quality_flag_counts: tuple[tuple[str, int], ...]
    decisions: tuple[base.ListedConsiderationTerminalEvidenceDecisionV1, ...]
    consideration_security_identity_assignment_count: Literal[0] = 0
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
    ) -> "StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1":
        states = Counter(item.evidence_state for item in self.decisions)
        quality = Counter(item.price_quality_status for item in self.decisions)
        flags = Counter(
            flag for item in self.decisions for flag in item.price_quality_flags
        )
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(identities_source.residual_plan._RESIDUAL_SPECS))
            or any(
                item.evidence_state
                != "gross_listed_consideration_reference_value"
                for item in self.decisions
            )
            or sum(
                item.terminal_reference_value_count for item in self.decisions
            )
            != EXPECTED_CASE_COUNT
            or self.valuation_session_count
            != len(
                {
                    item.first_absent_target_exchange_session
                    for item in self.decisions
                }
            )
            or self.decision_state_counts != base._ordered(states)
            or self.price_quality_status_counts != base._ordered(quality)
            or self.price_quality_flag_counts != base._ordered(flags)
            or self.cumulative_terminal_reference_value_count
            != self.prior_terminal_reference_value_count
            + self.residual_terminal_reference_value_count
            or self.logical_fingerprint
            != identities_source.residual_plan._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("residual terminal evidence report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceResult:
    output_root: Path
    report: StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1
    report_sha256: str
    status: Literal["published", "already_present"]


@dataclass(frozen=True, slots=True)
class _MatchedIdentityAdapter:
    request_sequence: int
    target_instrument_id: UUID
    assigned_consideration_instrument_id: UUID
    logical_fingerprint: str
    resolution_state: Literal["matched"] = "matched"


def build_strong_leader_pullback_listed_consideration_residual_terminal_evidence(
    *,
    prior_terminal_evidence_root: Path,
    prior_terminal_evidence_custody_root: Path,
    residual_identity_root: Path,
    residual_identity_custody_root: Path,
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
) -> StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceResult:
    with base._network_prohibited():
        prior_values = base.read_strong_leader_pullback_listed_consideration_terminal_evidence(
            output_root=prior_terminal_evidence_root,
            output_custody_root=prior_terminal_evidence_custody_root,
        )
        identity_reader = (
            identities_source.read_strong_leader_pullback_listed_consideration_residual_adjudication
        )
        identities = identity_reader(
            output_root=residual_identity_root,
            output_custody_root=residual_identity_custody_root,
        )
        consideration_reader = (
            consideration_source.read_strong_leader_pullback_sec_consideration_adjudication
        )
        consideration = consideration_reader(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        cessation = cessation_source.read_strong_leader_pullback_trading_cessation_adjudication(
            output_root=cessation_root,
            output_custody_root=cessation_custody_root,
        )
        payoff = payoff_source.read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        report = _build_report(
            prior_values=prior_values,
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


def read_strong_leader_pullback_listed_consideration_residual_terminal_evidence(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceResult:
    root = base._validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence members differ"
        )
    path = root / REPORT_FILE
    base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        model = StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1
        report = model.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence report is invalid"
        ) from exc
    canonical = identities_source.residual_plan._json_bytes(
        report.model_dump(mode="json")
    )
    if raw != canonical:
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence bytes are not canonical"
        )
    return StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceResult(
        output_root=root,
        report=report,
        report_sha256=identities_source.residual_plan._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    prior_values: base.StrongLeaderPullbackListedConsiderationTerminalEvidenceResult,
    identities: identities_source.StrongLeaderPullbackListedConsiderationResidualAdjudicationResult,
    consideration: consideration_source.StrongLeaderPullbackSecConsiderationAdjudicationResult,
    cessation: cessation_source.StrongLeaderPullbackTradingCessationAdjudicationResult,
    payoff: payoff_source.StrongLeaderPullbackTerminalPayoffTermsResult,
    canonical_eod_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence revision is invalid"
        )
    _validate_bindings(
        prior_values=prior_values,
        identities=identities,
        consideration=consideration,
        cessation=cessation,
        payoff=payoff,
    )
    identity_map = {
        item.request_sequence: item for item in identities.report.decisions
    }
    consideration_map = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    cessation_map = {
        item.request_sequence: item for item in cessation.report.decisions
    }
    payoff_map = {item.request_sequence: item for item in payoff.report.decisions}
    sequences = set(identities_source.residual_plan._RESIDUAL_SPECS)
    if not all(
        sequences.issubset(mapping)
        for mapping in (identity_map, consideration_map, cessation_map, payoff_map)
    ):
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence population differs"
        )
    requested_values = {
        cessation_map[sequence].next_exchange_session for sequence in sequences
    }
    if None in requested_values:
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal valuation session is unavailable"
        )
    requested_sessions = tuple(
        sorted(session for session in requested_values if session is not None)
    )
    repository = base.CanonicalEodReadRepository(canonical_eod_root)
    history = repository.read_history_sessions(requested_sessions)
    if any(item.available_at is None for item in history):
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal valuation custody time is unavailable"
        )
    session_map = {
        item.integrity.session_date: base._ValuationSessionEvidence(
            integrity=item.integrity,
            records=repository.read_canonical_records(item.integrity.session_date),
            available_at=item.available_at,  # type: ignore[arg-type]
        )
        for item in history
    }
    if (
        set(session_map) != set(requested_sessions)
        or any(
            len(item.records) != item.integrity.record_count
            or item.integrity.duplicate_instrument_session_count != 0
            or item.integrity.multiple_latest_revision_count != 0
            or item.integrity.future_identity_reference_count != 0
            for item in session_map.values()
        )
    ):
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal valuation session integrity differs"
        )
    decisions = tuple(
        _document_decision(
            identity=identity_map[sequence],
            consideration=consideration_map[sequence],
            cessation=cessation_map[sequence],
            payoff=payoff_map[sequence],
            valuation_session=session_map[cessation_map[sequence].next_exchange_session],
        )
        for sequence in sorted(sequences)
    )
    states = Counter(item.evidence_state for item in decisions)
    quality = Counter(item.price_quality_status for item in decisions)
    flags = Counter(flag for item in decisions for flag in item.price_quality_flags)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "prior_terminal_evidence_report_sha256": prior_values.report_sha256,
        "prior_terminal_evidence_logical_fingerprint": (
            prior_values.report.logical_fingerprint
        ),
        "residual_identity_report_sha256": identities.report_sha256,
        "residual_identity_logical_fingerprint": (
            identities.report.logical_fingerprint
        ),
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": consideration.report.logical_fingerprint,
        "cessation_report_sha256": cessation.report_sha256,
        "cessation_logical_fingerprint": cessation.report.logical_fingerprint,
        "payoff_terms_report_sha256": payoff.report_sha256,
        "payoff_terms_logical_fingerprint": payoff.report.logical_fingerprint,
        "valuation_session_count": len(requested_sessions),
        "decision_state_counts": base._ordered(states),
        "price_quality_status_counts": base._ordered(quality),
        "price_quality_flag_counts": base._ordered(flags),
        "decisions": decisions,
    }
    model = StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **values,
            "logical_fingerprint": identities_source.residual_plan._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_bindings(
    *,
    prior_values: base.StrongLeaderPullbackListedConsiderationTerminalEvidenceResult,
    identities: identities_source.StrongLeaderPullbackListedConsiderationResidualAdjudicationResult,
    consideration: consideration_source.StrongLeaderPullbackSecConsiderationAdjudicationResult,
    cessation: cessation_source.StrongLeaderPullbackTradingCessationAdjudicationResult,
    payoff: payoff_source.StrongLeaderPullbackTerminalPayoffTermsResult,
) -> None:
    if (
        prior_values.report.terminal_reference_value_count
        != EXPECTED_PRIOR_VALUE_COUNT
        or identities.report.prior_identity_report_sha256
        != prior_values.report.identity_adjudication_report_sha256
        or identities.report.consideration_report_sha256
        != consideration.report_sha256
        or identities.report.consideration_logical_fingerprint
        != consideration.report.logical_fingerprint
        or identities.report.residual_matched_identity_count != EXPECTED_CASE_COUNT
        or identities.report.cumulative_matched_identity_count
        != EXPECTED_CUMULATIVE_VALUE_COUNT
        or prior_values.report.consideration_report_sha256
        != consideration.report_sha256
        or prior_values.report.cessation_report_sha256 != cessation.report_sha256
        or prior_values.report.payoff_terms_report_sha256 != payoff.report_sha256
        or payoff.report.consideration_report_sha256 != consideration.report_sha256
        or payoff.report.consideration_logical_fingerprint
        != consideration.report.logical_fingerprint
        or payoff.report.cessation_report_sha256 != cessation.report_sha256
        or payoff.report.cessation_logical_fingerprint
        != cessation.report.logical_fingerprint
    ):
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence input bindings differ"
        )


def _document_decision(
    *,
    identity: identities_source.ListedConsiderationResidualIdentityDecisionV1,
    consideration: consideration_source.SecCommonShareConsiderationDecisionV1,
    cessation: cessation_source.TradingCessationDecisionV1,
    payoff: payoff_source.TerminalPayoffTermsDecisionV1,
    valuation_session: base._ValuationSessionEvidence,
) -> base.ListedConsiderationTerminalEvidenceDecisionV1:
    if (
        identity.assigned_consideration_instrument_id is None
        or not identity.composite_evidence_match
    ):
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual identity is not matched"
        )
    adapter = _MatchedIdentityAdapter(
        request_sequence=identity.request_sequence,
        target_instrument_id=identity.target_instrument_id,
        assigned_consideration_instrument_id=(
            identity.assigned_consideration_instrument_id
        ),
        logical_fingerprint=identity.logical_fingerprint,
    )
    try:
        decision = base._document_decision(
            identity=adapter,  # type: ignore[arg-type]
            consideration=consideration,
            cessation=cessation,
            payoff=payoff,
            valuation_session=valuation_session,
        )
    except base.StrongLeaderPullbackListedConsiderationTerminalEvidenceError as exc:
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal decision differs"
        ) from exc
    values = decision.model_dump(exclude={"logical_fingerprint"})
    reasons = set(decision.decision_reasons)
    reasons.discard("consideration_security_identity_passed_four_element_gate")
    reasons.update(
        {
            "consideration_security_identity_passed_residual_composite_gate",
            "identity_fingerprint_points_to_residual_composite_decision",
        }
    )
    values["decision_reasons"] = tuple(sorted(reasons))
    model = base.ListedConsiderationTerminalEvidenceDecisionV1
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **values,
            "logical_fingerprint": identities_source.residual_plan._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _ruleset_fingerprint() -> str:
    return identities_source.residual_plan._fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "population": "three_residual_composite_identity_matches",
            "prior_reference_value_count": EXPECTED_PRIOR_VALUE_COUNT,
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
    report: StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceV1,
) -> StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceResult:
    target = base._validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_listed_consideration_residual_terminal_evidence(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
                "existing residual terminal evidence differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceError(
            "residual terminal evidence staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        base._write_exclusive(
            partial / REPORT_FILE,
            identities_source.residual_plan._json_bytes(
                report.model_dump(mode="json")
            ),
        )
        base._fsync_directory(partial)
        partial.replace(target)
        base._fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink():
            shutil.rmtree(partial)
        raise
    reread = read_strong_leader_pullback_listed_consideration_residual_terminal_evidence(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackListedConsiderationResidualTerminalEvidenceResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )
