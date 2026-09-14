"""Outcome-blind census of the first strategy's remaining terminal gaps."""

from __future__ import annotations

import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_evidence_blocker_census as blocker_source
from tip_api.services import strong_leader_pullback_fixed_cash_terminal_evidence as cash_source
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_terminal_evidence as residual_source,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_terminal_evidence as listed_source,
)
from tip_api.services import strong_leader_pullback_source_acceptance_sample as sample_source
from tip_api.services import strong_leader_pullback_terminal_payoff_terms as payoff_source


CONTRACT_VERSION = "strong-leader-pullback-terminal-gap-census/1.0"
REPORT_FILE = "terminal-gap-census.json"
MAXIMUM_REPORT_BYTES = 512 * 1024

GapState = Literal[
    "nominal_fixed_cash_reference_documented",
    "gross_listed_consideration_reference_documented",
    "cessation_timing_not_matched",
    "contingent_value_realization_unresolved",
    "holder_election_or_proration_unresolved",
    "unlisted_unit_value_unresolved",
    "exception_case_primary_source_unadjudicated",
]
ReferenceKind = Literal[
    "nominal_fixed_cash",
    "gross_listed_consideration",
    "none",
]
NextRequiredGate = Literal[
    "lifecycle_fact_and_label_policy_required",
    "cessation_timing_adjudication_required",
    "cvr_realization_and_valuation_required",
    "holder_election_or_proration_distribution_required",
    "unlisted_unit_and_election_valuation_required",
    "exception_case_primary_source_adjudication_required",
]

_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"
_REFERENCE_STATES = {
    "nominal_fixed_cash_reference_documented",
    "gross_listed_consideration_reference_documented",
}
_PRIORITY_ORDER: tuple[GapState, ...] = (
    "cessation_timing_not_matched",
    "exception_case_primary_source_unadjudicated",
    "contingent_value_realization_unresolved",
    "holder_election_or_proration_unresolved",
    "unlisted_unit_value_unresolved",
)


class StrongLeaderPullbackTerminalGapCensusError(RuntimeError):
    """Raised when the bounded terminal-gap census cannot be reconciled."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalGapSourceBindingV1(_FrozenModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    contract_version: str = Field(min_length=1)
    report_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)


class TerminalGapDecisionV1(_FrozenModel):
    instrument_id: UUID
    request_sequence: int | None = Field(default=None, ge=1)
    provider_ticker_locators: tuple[str, ...]
    gap_state: GapState
    reference_kind: ReferenceKind
    reference_evidence_count: int = Field(ge=0, le=1)
    reference_source_available_at: datetime | None = None
    reference_quality_flags: tuple[str, ...]
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)
    next_required_gate: NextRequiredGate
    terminal_outcome_authorized: Literal[False] = False
    research_admission_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("reference_source_available_at")
    @classmethod
    def source_time_is_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value is not None else None

    @field_validator("provider_ticker_locators", "reference_quality_flags", mode="before")
    @classmethod
    def tuples_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("terminal-gap tuple differs")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "TerminalGapDecisionV1":
        documented = self.gap_state in _REFERENCE_STATES
        if self.gap_state == "nominal_fixed_cash_reference_documented":
            expected_kind: ReferenceKind = "nominal_fixed_cash"
        elif self.gap_state == "gross_listed_consideration_reference_documented":
            expected_kind = "gross_listed_consideration"
        else:
            expected_kind = "none"
        if (
            documented != (self.reference_evidence_count == 1)
            or self.reference_kind != expected_kind
            or documented != (self.reference_source_available_at is not None)
            or (
                self.gap_state
                == "gross_listed_consideration_reference_documented"
                and "adjustment_factors_unverified"
                not in self.reference_quality_flags
            )
            or (
                self.gap_state
                != "gross_listed_consideration_reference_documented"
                and self.reference_quality_flags
            )
            or not (
                self.horizon_1_crossing_path_count
                <= self.horizon_3_crossing_path_count
                <= self.horizon_5_crossing_path_count
            )
            or self.next_required_gate != _next_gate(self.gap_state)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-gap decision differs")
        return self


class TerminalGapImpactV1(_FrozenModel):
    gap_state: GapState
    instrument_count: int = Field(ge=1)
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)


class StrongLeaderPullbackTerminalGapCensusV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-gap-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["terminal_evidence_gaps_measured"] = (
        "terminal_evidence_gaps_measured"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_bindings: tuple[TerminalGapSourceBindingV1, ...]
    population_instrument_count: int = Field(ge=1)
    structured_case_count: int = Field(ge=0)
    exception_case_count: int = Field(ge=0)
    reference_documented_instrument_count: int = Field(ge=0)
    remaining_gap_instrument_count: int = Field(ge=0)
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)
    documented_horizon_1_crossing_path_count: int = Field(ge=0)
    documented_horizon_3_crossing_path_count: int = Field(ge=0)
    documented_horizon_5_crossing_path_count: int = Field(ge=0)
    remaining_horizon_1_crossing_path_count: int = Field(ge=0)
    remaining_horizon_3_crossing_path_count: int = Field(ge=0)
    remaining_horizon_5_crossing_path_count: int = Field(ge=0)
    state_impacts: tuple[TerminalGapImpactV1, ...]
    priority_order: tuple[GapState, ...]
    decisions: tuple[TerminalGapDecisionV1, ...]
    outcome_blind: Literal[True] = True
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
    def report_reconciles(self) -> "StrongLeaderPullbackTerminalGapCensusV1":
        decisions = self.decisions
        ids = tuple(item.instrument_id for item in decisions)
        bindings = tuple(item.name for item in self.source_bindings)
        impacts = tuple(item.gap_state for item in self.state_impacts)
        calculated_impacts = _impacts(decisions)
        documented = tuple(
            item for item in decisions if item.reference_evidence_count == 1
        )
        remaining = tuple(
            item for item in decisions if item.reference_evidence_count == 0
        )
        if (
            bindings != tuple(sorted(set(bindings)))
            or ids != tuple(sorted(set(ids), key=str))
            or impacts != tuple(sorted(set(impacts)))
            or self.state_impacts != calculated_impacts
            or self.priority_order != _PRIORITY_ORDER
            or len(decisions) != self.population_instrument_count
            or self.structured_case_count + self.exception_case_count
            != self.population_instrument_count
            or len(documented) != self.reference_documented_instrument_count
            or len(remaining) != self.remaining_gap_instrument_count
            or len(documented) + len(remaining) != self.population_instrument_count
            or self.horizon_1_crossing_path_count
            != sum(item.horizon_1_crossing_path_count for item in decisions)
            or self.horizon_3_crossing_path_count
            != sum(item.horizon_3_crossing_path_count for item in decisions)
            or self.horizon_5_crossing_path_count
            != sum(item.horizon_5_crossing_path_count for item in decisions)
            or self.documented_horizon_1_crossing_path_count
            != sum(item.horizon_1_crossing_path_count for item in documented)
            or self.documented_horizon_3_crossing_path_count
            != sum(item.horizon_3_crossing_path_count for item in documented)
            or self.documented_horizon_5_crossing_path_count
            != sum(item.horizon_5_crossing_path_count for item in documented)
            or self.remaining_horizon_1_crossing_path_count
            != sum(item.horizon_1_crossing_path_count for item in remaining)
            or self.remaining_horizon_3_crossing_path_count
            != sum(item.horizon_3_crossing_path_count for item in remaining)
            or self.remaining_horizon_5_crossing_path_count
            != sum(item.horizon_5_crossing_path_count for item in remaining)
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-gap census differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalGapCensusResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalGapCensusV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_gap_census(
    *,
    blocker_census_root: Path,
    blocker_census_custody_root: Path,
    source_sample_root: Path,
    source_sample_custody_root: Path,
    payoff_terms_root: Path,
    payoff_terms_custody_root: Path,
    fixed_cash_root: Path,
    fixed_cash_custody_root: Path,
    listed_terminal_root: Path,
    listed_terminal_custody_root: Path,
    residual_terminal_root: Path,
    residual_terminal_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusResult:
    """Measure remaining terminal gaps without opening strategy outcomes."""

    with listed_source._network_prohibited():
        blocker = blocker_source.read_strong_leader_pullback_evidence_blocker_census(
            output_root=blocker_census_root,
            output_custody_root=blocker_census_custody_root,
        )
        sample = sample_source.read_strong_leader_pullback_source_acceptance_sample(
            output_root=source_sample_root,
            output_custody_root=source_sample_custody_root,
        )
        payoff = payoff_source.read_strong_leader_pullback_terminal_payoff_terms(
            output_root=payoff_terms_root,
            output_custody_root=payoff_terms_custody_root,
        )
        cash = cash_source.read_strong_leader_pullback_fixed_cash_terminal_evidence(
            output_root=fixed_cash_root,
            output_custody_root=fixed_cash_custody_root,
        )
        listed = listed_source.read_strong_leader_pullback_listed_consideration_terminal_evidence(
            output_root=listed_terminal_root,
            output_custody_root=listed_terminal_custody_root,
        )
        residual_reader = (
            residual_source.read_strong_leader_pullback_listed_consideration_residual_terminal_evidence
        )
        residual = residual_reader(
            output_root=residual_terminal_root,
            output_custody_root=residual_terminal_custody_root,
        )
        report = _build_report(
            blocker=blocker,
            sample=sample,
            payoff=payoff,
            cash=cash,
            listed=listed,
            residual=residual,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_gap_census(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalGapCensusResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap census package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalGapCensusV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap census report is invalid"
        ) from exc
    if raw != listed_source._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap census bytes are not canonical"
        )
    return StrongLeaderPullbackTerminalGapCensusResult(
        output_root=root,
        report=report,
        report_sha256=listed_source._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, blocker: object, sample: object, payoff: object, cash: object,
    listed: object, residual: object, implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusV1:
    if not _valid_revision(implementation_revision):
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap census revision is invalid"
        )
    _validate_upstream(
        blocker=blocker,
        sample=sample,
        payoff=payoff,
        cash=cash,
        listed=listed,
        residual=residual,
    )
    evaluated_at = normalize_utc_datetime(evaluated_at)
    sample_by_id = {
        item.instrument_id: item for item in sample.report.lifecycle_cases
    }
    crossing_by_id = {
        item.instrument_id: item
        for item in blocker.lifecycle_records
        if item.horizon_5_crosses_last_observed_path_count > 0
    }
    payoff_by_id = {
        item.instrument_id: item for item in payoff.report.decisions
    }
    reference = _reference_evidence(cash=cash, listed=listed, residual=residual)
    decisions = tuple(
        _decision(
            sample_case=sample_by_id[instrument_id],
            crossing=crossing_by_id[instrument_id],
            payoff=payoff_by_id.get(instrument_id),
            reference=reference.get(instrument_id),
        )
        for instrument_id in sorted(sample_by_id, key=str)
    )
    documented = tuple(item for item in decisions if item.reference_evidence_count)
    remaining = tuple(item for item in decisions if not item.reference_evidence_count)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": evaluated_at,
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "source_bindings": _source_bindings(
            blocker=blocker,
            sample=sample,
            payoff=payoff,
            cash=cash,
            listed=listed,
            residual=residual,
        ),
        "population_instrument_count": len(decisions),
        "structured_case_count": len(payoff_by_id),
        "exception_case_count": len(decisions) - len(payoff_by_id),
        "reference_documented_instrument_count": len(documented),
        "remaining_gap_instrument_count": len(remaining),
        "horizon_1_crossing_path_count": sum(
            item.horizon_1_crossing_path_count for item in decisions
        ),
        "horizon_3_crossing_path_count": sum(
            item.horizon_3_crossing_path_count for item in decisions
        ),
        "horizon_5_crossing_path_count": sum(
            item.horizon_5_crossing_path_count for item in decisions
        ),
        "documented_horizon_1_crossing_path_count": sum(
            item.horizon_1_crossing_path_count for item in documented
        ),
        "documented_horizon_3_crossing_path_count": sum(
            item.horizon_3_crossing_path_count for item in documented
        ),
        "documented_horizon_5_crossing_path_count": sum(
            item.horizon_5_crossing_path_count for item in documented
        ),
        "remaining_horizon_1_crossing_path_count": sum(
            item.horizon_1_crossing_path_count for item in remaining
        ),
        "remaining_horizon_3_crossing_path_count": sum(
            item.horizon_3_crossing_path_count for item in remaining
        ),
        "remaining_horizon_5_crossing_path_count": sum(
            item.horizon_5_crossing_path_count for item in remaining
        ),
        "state_impacts": _impacts(decisions),
        "priority_order": _PRIORITY_ORDER,
        "decisions": decisions,
    }
    model = StrongLeaderPullbackTerminalGapCensusV1
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_upstream(
    *, blocker: object, sample: object, payoff: object, cash: object,
    listed: object, residual: object,
) -> None:
    blocker_binding = next(
        (
            item
            for item in sample.report.source_bindings
            if item.name == "strong_leader_pullback_evidence_blocker_census"
        ),
        None,
    )
    sample_by_id = {
        item.instrument_id: item for item in sample.report.lifecycle_cases
    }
    crossing_by_id = {
        item.instrument_id: item
        for item in blocker.lifecycle_records
        if item.horizon_5_crosses_last_observed_path_count > 0
    }
    payoff_ids = {item.instrument_id for item in payoff.report.decisions}
    if (
        blocker_binding is None
        or blocker_binding.manifest_sha256 != blocker.manifest_sha256
        or blocker_binding.logical_fingerprint
        != blocker.manifest.logical_fingerprint
        or set(sample_by_id) != set(crossing_by_id)
        or len(sample_by_id) != sample.report.lifecycle_case_count
        or not payoff_ids.issubset(sample_by_id)
        or cash.report.payoff_terms_report_sha256 != payoff.report_sha256
        or cash.report.payoff_terms_logical_fingerprint
        != payoff.report.logical_fingerprint
        or listed.report.payoff_terms_report_sha256 != payoff.report_sha256
        or listed.report.payoff_terms_logical_fingerprint
        != payoff.report.logical_fingerprint
        or residual.report.prior_terminal_evidence_report_sha256
        != listed.report_sha256
        or residual.report.prior_terminal_evidence_logical_fingerprint
        != listed.report.logical_fingerprint
        or residual.report.payoff_terms_report_sha256 != payoff.report_sha256
        or residual.report.payoff_terms_logical_fingerprint
        != payoff.report.logical_fingerprint
    ):
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap upstream bindings differ"
        )
    for instrument_id, sample_case in sample_by_id.items():
        crossing = crossing_by_id[instrument_id]
        if (
            sample_case.horizon_1_crossing_path_count
            != crossing.horizon_1_crosses_last_observed_path_count
            or sample_case.horizon_3_crossing_path_count
            != crossing.horizon_3_crosses_last_observed_path_count
            or sample_case.horizon_5_crossing_path_count
            != crossing.horizon_5_crosses_last_observed_path_count
        ):
            raise StrongLeaderPullbackTerminalGapCensusError(
                "terminal-gap path counts differ"
            )
    reference = _reference_evidence(cash=cash, listed=listed, residual=residual)
    if set(reference) - payoff_ids:
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal reference population differs"
        )


def _reference_evidence(
    *, cash: object, listed: object, residual: object
) -> dict[UUID, tuple[ReferenceKind, datetime, tuple[str, ...]]]:
    values: dict[UUID, tuple[ReferenceKind, datetime, tuple[str, ...]]] = {}
    for item in cash.report.decisions:
        if item.evidence_state != "nominal_fixed_cash_terminal_evidence":
            continue
        if item.instrument_id in values:
            raise StrongLeaderPullbackTerminalGapCensusError(
                "duplicate fixed-cash reference evidence"
            )
        values[item.instrument_id] = (
            "nominal_fixed_cash",
            item.source_available_at,
            (),
        )
    for report in (listed.report, residual.report):
        for item in report.decisions:
            if item.evidence_state != "gross_listed_consideration_reference_value":
                continue
            if item.target_instrument_id in values:
                raise StrongLeaderPullbackTerminalGapCensusError(
                    "duplicate listed reference evidence"
                )
            values[item.target_instrument_id] = (
                "gross_listed_consideration",
                item.source_available_at,
                item.price_quality_flags,
            )
    return values


def _decision(
    *, sample_case: object, crossing: object, payoff: object | None,
    reference: tuple[ReferenceKind, datetime, tuple[str, ...]] | None,
) -> TerminalGapDecisionV1:
    if reference is not None:
        reference_kind, source_available_at, flags = reference
        state: GapState = (
            "nominal_fixed_cash_reference_documented"
            if reference_kind == "nominal_fixed_cash"
            else "gross_listed_consideration_reference_documented"
        )
    elif payoff is not None:
        reference_kind = "none"
        source_available_at = None
        flags = ()
        state = payoff.terminal_candidate_state
    else:
        reference_kind = "none"
        source_available_at = None
        flags = ()
        state = "exception_case_primary_source_unadjudicated"
    values = {
        "instrument_id": sample_case.instrument_id,
        "request_sequence": payoff.request_sequence if payoff is not None else None,
        "provider_ticker_locators": sample_case.provider_ticker_locators,
        "gap_state": state,
        "reference_kind": reference_kind,
        "reference_evidence_count": int(reference is not None),
        "reference_source_available_at": source_available_at,
        "reference_quality_flags": flags,
        "horizon_1_crossing_path_count": (
            crossing.horizon_1_crosses_last_observed_path_count
        ),
        "horizon_3_crossing_path_count": (
            crossing.horizon_3_crosses_last_observed_path_count
        ),
        "horizon_5_crossing_path_count": (
            crossing.horizon_5_crosses_last_observed_path_count
        ),
        "next_required_gate": _next_gate(state),
    }
    provisional = TerminalGapDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalGapDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _source_bindings(
    *, blocker: object, sample: object, payoff: object, cash: object,
    listed: object, residual: object,
) -> tuple[TerminalGapSourceBindingV1, ...]:
    raw = (
        (
            "evidence_blocker_census",
            blocker.manifest.contract_version,
            blocker.manifest_sha256,
            blocker.manifest.logical_fingerprint,
        ),
        (
            "fixed_cash_terminal_evidence",
            cash.report.contract_version,
            cash.report_sha256,
            cash.report.logical_fingerprint,
        ),
        (
            "listed_consideration_terminal_evidence",
            listed.report.contract_version,
            listed.report_sha256,
            listed.report.logical_fingerprint,
        ),
        (
            "residual_listed_consideration_terminal_evidence",
            residual.report.contract_version,
            residual.report_sha256,
            residual.report.logical_fingerprint,
        ),
        (
            "source_acceptance_sample",
            sample.report.contract_version,
            sample.report_sha256,
            sample.report.logical_fingerprint,
        ),
        (
            "terminal_payoff_terms",
            payoff.report.contract_version,
            payoff.report_sha256,
            payoff.report.logical_fingerprint,
        ),
    )
    return tuple(
        TerminalGapSourceBindingV1(
            name=name,
            contract_version=contract,
            report_sha256=sha,
            logical_fingerprint=fingerprint,
        )
        for name, contract, sha, fingerprint in sorted(raw)
    )


def _impacts(
    decisions: tuple[TerminalGapDecisionV1, ...],
) -> tuple[TerminalGapImpactV1, ...]:
    grouped: dict[GapState, list[TerminalGapDecisionV1]] = {}
    for item in decisions:
        grouped.setdefault(item.gap_state, []).append(item)
    return tuple(
        TerminalGapImpactV1(
            gap_state=state,
            instrument_count=len(items),
            horizon_1_crossing_path_count=sum(
                item.horizon_1_crossing_path_count for item in items
            ),
            horizon_3_crossing_path_count=sum(
                item.horizon_3_crossing_path_count for item in items
            ),
            horizon_5_crossing_path_count=sum(
                item.horizon_5_crossing_path_count for item in items
            ),
        )
        for state, items in sorted(grouped.items())
    )


def _next_gate(state: GapState) -> NextRequiredGate:
    return {
        "nominal_fixed_cash_reference_documented": (
            "lifecycle_fact_and_label_policy_required"
        ),
        "gross_listed_consideration_reference_documented": (
            "lifecycle_fact_and_label_policy_required"
        ),
        "cessation_timing_not_matched": (
            "cessation_timing_adjudication_required"
        ),
        "contingent_value_realization_unresolved": (
            "cvr_realization_and_valuation_required"
        ),
        "holder_election_or_proration_unresolved": (
            "holder_election_or_proration_distribution_required"
        ),
        "unlisted_unit_value_unresolved": (
            "unlisted_unit_and_election_valuation_required"
        ),
        "exception_case_primary_source_unadjudicated": (
            "exception_case_primary_source_adjudication_required"
        ),
    }[state]


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "population": "all_horizon_5_lifecycle_crossing_instruments",
            "documented_reference_types": (
                "nominal_fixed_cash",
                "gross_listed_consideration",
            ),
            "unresolved_states": _PRIORITY_ORDER,
            "priority_basis": (
                "resolve_timing_and_exception_identity_before_complex_value"
            ),
            "reference_value_is_terminal_outcome": False,
            "outcome_blind": True,
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalGapCensusV1,
) -> StrongLeaderPullbackTerminalGapCensusResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_gap_census(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalGapCensusError(
                "existing terminal-gap census differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap census staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(
            partial / REPORT_FILE,
            listed_source._json_bytes(report.model_dump(mode="json")),
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink():
            shutil.rmtree(partial)
        raise
    reread = read_strong_leader_pullback_terminal_gap_census(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackTerminalGapCensusResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _fingerprint(value: object) -> str:
    return listed_source._fingerprint(value)


def _valid_revision(value: str) -> bool:
    return re.fullmatch(_REVISION_PATTERN, value) is not None


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap paths must be absolute"
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
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap custody or target is unsafe"
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
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTerminalGapCensusError(
            "terminal-gap file metadata differs"
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
