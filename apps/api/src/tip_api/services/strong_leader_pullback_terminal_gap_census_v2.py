"""EOD-boundary terminal-gap census for the first registered strategy."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services import strong_leader_pullback_fixed_cash_terminal_evidence as cash_source
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_terminal_evidence as residual_source,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_terminal_evidence as listed_source,
)
from tip_api.services import strong_leader_pullback_source_acceptance_sample as sample_source
from tip_api.services import strong_leader_pullback_terminal_boundary_census as boundary_source
from tip_api.services import strong_leader_pullback_terminal_gap_census as prior_source
from tip_api.services import strong_leader_pullback_terminal_payoff_terms as payoff_source
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    read_historical_inactive_lifecycle_resolution_shadow,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-gap-census/2.0"
REPORT_FILE = "terminal-gap-census-v2.json"
MAXIMUM_REPORT_BYTES = 768 * 1024

_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"
_REFERENCE_STATES = {
    "nominal_fixed_cash_reference_documented",
    "gross_listed_consideration_reference_documented",
}

GapState = Literal[
    "nominal_fixed_cash_reference_documented",
    "gross_listed_consideration_reference_documented",
    "cessation_timing_not_matched",
    "contingent_value_realization_unresolved",
    "holder_election_or_proration_unresolved",
    "unlisted_unit_value_unresolved",
    "exception_case_primary_source_unadjudicated",
    "newly_in_scope_primary_source_unadjudicated",
]
PopulationOrigin = Literal["legacy_identity_boundary_sample", "corrected_eod_boundary"]
ReferenceKind = Literal["nominal_fixed_cash", "gross_listed_consideration", "none"]
NextRequiredGate = Literal[
    "lifecycle_fact_and_label_policy_required",
    "cessation_timing_adjudication_required",
    "cvr_realization_and_valuation_required",
    "holder_election_or_proration_distribution_required",
    "unlisted_unit_and_election_valuation_required",
    "exception_case_primary_source_adjudication_required",
    "corrected_population_primary_source_adjudication_required",
]

_PRIORITY_ORDER: tuple[GapState, ...] = (
    "newly_in_scope_primary_source_unadjudicated",
    "cessation_timing_not_matched",
    "exception_case_primary_source_unadjudicated",
    "contingent_value_realization_unresolved",
    "holder_election_or_proration_unresolved",
    "unlisted_unit_value_unresolved",
)


class StrongLeaderPullbackTerminalGapCensusV2Error(RuntimeError):
    """Raised when the corrected terminal-gap census cannot be reconciled."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceBindingV2(_FrozenModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    contract_version: str = Field(min_length=1)
    physical_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    record_count: int = Field(ge=0)


class TerminalGapDecisionV2(_FrozenModel):
    instrument_id: UUID
    population_origin: PopulationOrigin
    request_sequence: int | None = Field(default=None, ge=1)
    provider_ticker_locators: tuple[str, ...] = Field(min_length=1)
    canonical_identity_last_observed_date: date
    strategy_window_last_eod_observed_date: date
    gap_state: GapState
    reference_kind: ReferenceKind
    reference_evidence_count: int = Field(ge=0, le=1)
    reference_source_available_at: datetime | None = None
    reference_quality_flags: tuple[str, ...]
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)
    next_required_gate: NextRequiredGate
    eod_observation_is_terminal_fact: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False
    research_admission_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("reference_source_available_at")
    @classmethod
    def source_time_is_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value is not None else None

    @field_validator("provider_ticker_locators", "reference_quality_flags", mode="before")
    @classmethod
    def values_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("terminal-gap V2 tuple differs")
        return values

    @model_validator(mode="after")
    def decision_reconciles(self) -> "TerminalGapDecisionV2":
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
                self.gap_state == "gross_listed_consideration_reference_documented"
                and "adjustment_factors_unverified" not in self.reference_quality_flags
            )
            or (
                self.gap_state != "gross_listed_consideration_reference_documented"
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
            raise ValueError("terminal-gap V2 decision differs")
        return self


class TerminalGapImpactV2(_FrozenModel):
    gap_state: GapState
    instrument_count: int = Field(ge=1)
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)


class StrongLeaderPullbackTerminalGapCensusV2(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-gap-census/2.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["corrected_terminal_evidence_gaps_measured"] = (
        "corrected_terminal_evidence_gaps_measured"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_bindings: tuple[SourceBindingV2, ...]
    population_instrument_count: int = Field(ge=1)
    legacy_population_instrument_count: int = Field(ge=1)
    newly_in_scope_instrument_count: int = Field(ge=0)
    structured_case_count: int = Field(ge=0)
    legacy_exception_case_count: int = Field(ge=0)
    new_primary_source_case_count: int = Field(ge=0)
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
    state_impacts: tuple[TerminalGapImpactV2, ...]
    priority_order: tuple[GapState, ...]
    decisions: tuple[TerminalGapDecisionV2, ...]
    prior_gap_counts_superseded: Literal[True] = True
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
    def report_reconciles(self) -> "StrongLeaderPullbackTerminalGapCensusV2":
        decisions = self.decisions
        ids = tuple(item.instrument_id for item in decisions)
        origins = Counter(item.population_origin for item in decisions)
        impacts = _impacts(decisions)
        documented = tuple(item for item in decisions if item.reference_evidence_count)
        remaining = tuple(item for item in decisions if not item.reference_evidence_count)
        if (
            tuple(item.name for item in self.source_bindings)
            != tuple(sorted({item.name for item in self.source_bindings}))
            or ids != tuple(sorted(set(ids), key=str))
            or len(decisions) != self.population_instrument_count
            or origins["legacy_identity_boundary_sample"]
            != self.legacy_population_instrument_count
            or origins["corrected_eod_boundary"] != self.newly_in_scope_instrument_count
            or self.legacy_population_instrument_count
            + self.newly_in_scope_instrument_count
            != self.population_instrument_count
            or self.structured_case_count
            + self.legacy_exception_case_count
            + self.new_primary_source_case_count
            != self.population_instrument_count
            or self.legacy_exception_case_count
            != sum(
                item.gap_state == "exception_case_primary_source_unadjudicated"
                for item in decisions
            )
            or self.new_primary_source_case_count
            != sum(
                item.gap_state == "newly_in_scope_primary_source_unadjudicated"
                for item in decisions
            )
            or len(documented) != self.reference_documented_instrument_count
            or len(remaining) != self.remaining_gap_instrument_count
            or self.state_impacts != impacts
            or self.priority_order != _PRIORITY_ORDER
            or any(
                getattr(self, f"{prefix}horizon_{horizon}_crossing_path_count")
                != sum(
                    item.horizon_1_crossing_path_count
                    if horizon == 1
                    else item.horizon_3_crossing_path_count
                    if horizon == 3
                    else item.horizon_5_crossing_path_count
                    for item in subset
                )
                for prefix, subset in (
                    ("", decisions),
                    ("documented_", documented),
                    ("remaining_", remaining),
                )
                for horizon in (1, 3, 5)
            )
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-gap V2 report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalGapCensusV2Result:
    output_root: Path
    report: StrongLeaderPullbackTerminalGapCensusV2
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_gap_census_v2(
    *,
    boundary_census_root: Path,
    boundary_census_custody_root: Path,
    prior_gap_census_root: Path,
    prior_gap_census_custody_root: Path,
    source_sample_root: Path,
    source_sample_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    lifecycle_anchor_dates: tuple[date, ...],
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
) -> StrongLeaderPullbackTerminalGapCensusV2Result:
    """Measure corrected gaps without opening outcomes or making network calls."""

    with listed_source._network_prohibited():
        if (
            not lifecycle_anchor_dates
            or lifecycle_anchor_dates
            != tuple(sorted(set(lifecycle_anchor_dates)))
        ):
            raise StrongLeaderPullbackTerminalGapCensusV2Error(
                "terminal-gap V2 lifecycle anchors differ"
            )
        boundary = boundary_source.read_strong_leader_pullback_terminal_boundary_census(
            output_root=boundary_census_root,
            output_custody_root=boundary_census_custody_root,
        )
        prior = prior_source.read_strong_leader_pullback_terminal_gap_census(
            output_root=prior_gap_census_root,
            output_custody_root=prior_gap_census_custody_root,
        )
        sample = sample_source.read_strong_leader_pullback_source_acceptance_sample(
            output_root=source_sample_root,
            output_custody_root=source_sample_custody_root,
        )
        lifecycle = tuple(
            read_historical_inactive_lifecycle_resolution_shadow(
                root=lifecycle_shadow_root,
                anchor_date=anchor,
                approved_custody_root=lifecycle_shadow_custody_root,
            )
            for anchor in lifecycle_anchor_dates
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
            residual_source
            .read_strong_leader_pullback_listed_consideration_residual_terminal_evidence
        )
        residual = residual_reader(
            output_root=residual_terminal_root,
            output_custody_root=residual_terminal_custody_root,
        )
        report = _build_report(
            boundary=boundary,
            prior=prior,
            sample=sample,
            lifecycle=lifecycle,
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


def read_strong_leader_pullback_terminal_gap_census_v2(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalGapCensusV2Result:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalGapCensusV2.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 report bytes are not canonical"
        )
    return StrongLeaderPullbackTerminalGapCensusV2Result(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, boundary: object, prior: object, sample: object, lifecycle: tuple[object, ...],
    payoff: object, cash: object, listed: object, residual: object,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusV2:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 revision is invalid"
        )
    _validate_prior_bindings(
        prior=prior,
        sample=sample,
        payoff=payoff,
        cash=cash,
        listed=listed,
        residual=residual,
    )
    boundary_by_id = {
        item.instrument_id: item
        for item in boundary.report.decisions
        if item.corrected_horizon_5_crossing_path_count > 0
    }
    legacy_boundary_by_id = {
        item.instrument_id: item
        for item in boundary.report.decisions
        if item.legacy_horizon_5_crossing_path_count > 0
    }
    sample_by_id = {item.instrument_id: item for item in sample.report.lifecycle_cases}
    prior_by_id = {item.instrument_id: item for item in prior.report.decisions}
    newly_in_scope_ids = set(boundary_by_id) - set(legacy_boundary_by_id)
    if (
        set(sample_by_id) != set(legacy_boundary_by_id)
        or set(prior_by_id) != set(sample_by_id)
        or set(legacy_boundary_by_id) - set(boundary_by_id)
        or len(boundary_by_id) != boundary.report.corrected_horizon_5_crossing_instrument_count
        or len(newly_in_scope_ids)
        != boundary.report.newly_horizon_5_in_scope_instrument_count
    ):
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 corrected population differs"
        )
    for instrument_id, boundary_item in legacy_boundary_by_id.items():
        sample_item = sample_by_id[instrument_id]
        prior_item = prior_by_id[instrument_id]
        legacy_counts = tuple(
            getattr(boundary_item, f"legacy_horizon_{horizon}_crossing_path_count")
            for horizon in (1, 3, 5)
        )
        if legacy_counts != (
            sample_item.horizon_1_crossing_path_count,
            sample_item.horizon_3_crossing_path_count,
            sample_item.horizon_5_crossing_path_count,
        ) or legacy_counts != (
            prior_item.horizon_1_crossing_path_count,
            prior_item.horizon_3_crossing_path_count,
            prior_item.horizon_5_crossing_path_count,
        ):
            raise StrongLeaderPullbackTerminalGapCensusV2Error(
                "terminal-gap V2 legacy path lineage differs"
            )
    cases = _corrected_cases(
        boundary_by_id=boundary_by_id,
        sample_by_id=sample_by_id,
        newly_in_scope_ids=newly_in_scope_ids,
        lifecycle=lifecycle,
    )
    payoff_by_id = {item.instrument_id: item for item in payoff.report.decisions}
    reference = prior_source._reference_evidence(
        cash=cash, listed=listed, residual=residual
    )
    if set(payoff_by_id) - set(cases) or set(reference) - set(payoff_by_id):
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 payoff population differs"
        )
    decisions = tuple(
        _decision(
            case=cases[instrument_id],
            boundary=boundary_by_id[instrument_id],
            payoff=payoff_by_id.get(instrument_id),
            reference=reference.get(instrument_id),
            newly_in_scope=instrument_id in newly_in_scope_ids,
        )
        for instrument_id in sorted(cases, key=str)
    )
    for instrument_id, prior_item in prior_by_id.items():
        current = next(item for item in decisions if item.instrument_id == instrument_id)
        if current.gap_state != prior_item.gap_state:
            raise StrongLeaderPullbackTerminalGapCensusV2Error(
                "terminal-gap V2 evidence state differs from prior report"
            )
    documented = tuple(item for item in decisions if item.reference_evidence_count)
    remaining = tuple(item for item in decisions if not item.reference_evidence_count)
    values: dict[str, object] = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "source_bindings": _source_bindings(
            boundary=boundary,
            prior=prior,
            sample=sample,
            lifecycle=lifecycle,
            payoff=payoff,
            cash=cash,
            listed=listed,
            residual=residual,
        ),
        "population_instrument_count": len(decisions),
        "legacy_population_instrument_count": len(prior_by_id),
        "newly_in_scope_instrument_count": len(newly_in_scope_ids),
        "structured_case_count": len(payoff_by_id),
        "legacy_exception_case_count": sum(
            item.gap_state == "exception_case_primary_source_unadjudicated"
            for item in decisions
        ),
        "new_primary_source_case_count": sum(
            item.gap_state == "newly_in_scope_primary_source_unadjudicated"
            for item in decisions
        ),
        "reference_documented_instrument_count": len(documented),
        "remaining_gap_instrument_count": len(remaining),
        "state_impacts": _impacts(decisions),
        "priority_order": _PRIORITY_ORDER,
        "decisions": decisions,
    }
    for prefix, subset in (
        ("", decisions),
        ("documented_", documented),
        ("remaining_", remaining),
    ):
        for horizon in (1, 3, 5):
            values[f"{prefix}horizon_{horizon}_crossing_path_count"] = sum(
                getattr(item, f"horizon_{horizon}_crossing_path_count")
                for item in subset
            )
    provisional = StrongLeaderPullbackTerminalGapCensusV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalGapCensusV2.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_prior_bindings(
    *, prior: object, sample: object, payoff: object, cash: object,
    listed: object, residual: object,
) -> None:
    observed = {
        item.name: (item.report_sha256, item.logical_fingerprint)
        for item in prior.report.source_bindings
    }
    expected = {
        "source_acceptance_sample": (
            sample.report_sha256,
            sample.report.logical_fingerprint,
        ),
        "terminal_payoff_terms": (
            payoff.report_sha256,
            payoff.report.logical_fingerprint,
        ),
        "fixed_cash_terminal_evidence": (
            cash.report_sha256,
            cash.report.logical_fingerprint,
        ),
        "listed_consideration_terminal_evidence": (
            listed.report_sha256,
            listed.report.logical_fingerprint,
        ),
        "residual_listed_consideration_terminal_evidence": (
            residual.report_sha256,
            residual.report.logical_fingerprint,
        ),
    }
    if any(observed.get(name) != value for name, value in expected.items()):
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 prior source bindings differ"
        )


def _corrected_cases(
    *, boundary_by_id: dict[UUID, object], sample_by_id: dict[UUID, object],
    newly_in_scope_ids: set[UUID], lifecycle: tuple[object, ...],
) -> dict[UUID, sample_source.LifecycleSourceAcceptanceCaseV1]:
    cases = {
        instrument_id: sample_source.LifecycleSourceAcceptanceCaseV1.model_validate(
            {
                **item.model_dump(mode="python"),
                "horizon_1_crossing_path_count": boundary_by_id[
                    instrument_id
                ].corrected_horizon_1_crossing_path_count,
                "horizon_3_crossing_path_count": boundary_by_id[
                    instrument_id
                ].corrected_horizon_3_crossing_path_count,
                "horizon_5_crossing_path_count": boundary_by_id[
                    instrument_id
                ].corrected_horizon_5_crossing_path_count,
            }
        )
        for instrument_id, item in sample_by_id.items()
    }
    evidence: dict[UUID, list[tuple[object, object]]] = {
        instrument_id: [] for instrument_id in newly_in_scope_ids
    }
    for result in lifecycle:
        source_by_fingerprint = {
            item.source_observation_fingerprint: item
            for item in result.source_observations
        }
        if len(source_by_fingerprint) != len(result.source_observations):
            raise StrongLeaderPullbackTerminalGapCensusV2Error(
                "terminal-gap V2 lifecycle source observations are duplicated"
            )
        for decision in result.decisions:
            if (
                decision.disposition is not InactiveLifecycleDisposition.REVIEW_CANDIDATE
                or decision.canonical_instrument_id not in newly_in_scope_ids
            ):
                continue
            boundary_item = boundary_by_id[decision.canonical_instrument_id]
            if (
                decision.canonical_first_observed_date
                != boundary_item.canonical_identity_first_observed_date
                or decision.canonical_last_observed_date
                != boundary_item.canonical_identity_last_observed_date
                or decision.effective_date_candidate
                != boundary_item.provider_delist_date_candidate
            ):
                continue
            source = source_by_fingerprint.get(decision.source_observation_fingerprint)
            if source is None:
                raise StrongLeaderPullbackTerminalGapCensusV2Error(
                    "terminal-gap V2 lifecycle decision lacks source occurrence"
                )
            evidence[decision.canonical_instrument_id].append((decision, source))
    for instrument_id in sorted(newly_in_scope_ids, key=str):
        rows = evidence[instrument_id]
        if not rows:
            raise StrongLeaderPullbackTerminalGapCensusV2Error(
                "terminal-gap V2 corrected case lacks source evidence"
            )
        boundary_item = boundary_by_id[instrument_id]
        values = sample_source._values
        cases[instrument_id] = sample_source.LifecycleSourceAcceptanceCaseV1(
            instrument_id=instrument_id,
            source_anchor_dates=tuple(sorted({item[0].anchor_date for item in rows})),
            source_observation_fingerprints=values(
                item[0].source_observation_fingerprint for item in rows
            ),
            source_occurrence_count=len(rows),
            selected_identity_types=values(
                item[0].selected_identity_type.value for item in rows
            ),
            selected_identity_values=values(
                item[0].selected_identity_value for item in rows
            ),
            provider_ticker_locators=values(item[1].ticker for item in rows),
            provider_name_locators=values(item[1].name for item in rows),
            cik_locators=values(item[1].cik for item in rows),
            primary_exchange_locators=values(
                item[1].primary_exchange for item in rows
            ),
            source_type_codes=values(item[1].type for item in rows),
            canonical_first_observed_date=(
                boundary_item.canonical_identity_first_observed_date
            ),
            canonical_last_observed_date=(
                boundary_item.canonical_identity_last_observed_date
            ),
            provider_delist_date_candidate=(
                boundary_item.provider_delist_date_candidate
            ),
            included_path_count=boundary_item.included_path_count,
            horizon_1_crossing_path_count=(
                boundary_item.corrected_horizon_1_crossing_path_count
            ),
            horizon_3_crossing_path_count=(
                boundary_item.corrected_horizon_3_crossing_path_count
            ),
            horizon_5_crossing_path_count=(
                boundary_item.corrected_horizon_5_crossing_path_count
            ),
        )
    if set(cases) != set(boundary_by_id):
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 corrected cases are incomplete"
        )
    return cases


def _decision(
    *, case: object, boundary: object, payoff: object | None,
    reference: tuple[object, datetime, tuple[str, ...]] | None,
    newly_in_scope: bool,
) -> TerminalGapDecisionV2:
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
    elif newly_in_scope:
        reference_kind = "none"
        source_available_at = None
        flags = ()
        state = "newly_in_scope_primary_source_unadjudicated"
    else:
        reference_kind = "none"
        source_available_at = None
        flags = ()
        state = "exception_case_primary_source_unadjudicated"
    values = {
        "instrument_id": case.instrument_id,
        "population_origin": (
            "corrected_eod_boundary"
            if newly_in_scope
            else "legacy_identity_boundary_sample"
        ),
        "request_sequence": payoff.request_sequence if payoff is not None else None,
        "provider_ticker_locators": case.provider_ticker_locators,
        "canonical_identity_last_observed_date": (
            boundary.canonical_identity_last_observed_date
        ),
        "strategy_window_last_eod_observed_date": (
            boundary.strategy_window_last_eod_observed_date
        ),
        "gap_state": state,
        "reference_kind": reference_kind,
        "reference_evidence_count": int(reference is not None),
        "reference_source_available_at": source_available_at,
        "reference_quality_flags": flags,
        "horizon_1_crossing_path_count": (
            boundary.corrected_horizon_1_crossing_path_count
        ),
        "horizon_3_crossing_path_count": (
            boundary.corrected_horizon_3_crossing_path_count
        ),
        "horizon_5_crossing_path_count": (
            boundary.corrected_horizon_5_crossing_path_count
        ),
        "next_required_gate": _next_gate(state),
    }
    provisional = TerminalGapDecisionV2.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalGapDecisionV2.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _source_bindings(
    *, boundary: object, prior: object, sample: object, lifecycle: tuple[object, ...],
    payoff: object, cash: object, listed: object, residual: object,
) -> tuple[SourceBindingV2, ...]:
    raw = [
        (
            "terminal_boundary_census",
            boundary.report.contract_version,
            boundary.report_sha256,
            boundary.report.logical_fingerprint,
            boundary.report.lifecycle_instrument_count,
        ),
        (
            "prior_terminal_gap_census",
            prior.report.contract_version,
            prior.report_sha256,
            prior.report.logical_fingerprint,
            prior.report.population_instrument_count,
        ),
        (
            "source_acceptance_sample",
            sample.report.contract_version,
            sample.report_sha256,
            sample.report.logical_fingerprint,
            sample.report.lifecycle_case_count,
        ),
        (
            "terminal_payoff_terms",
            payoff.report.contract_version,
            payoff.report_sha256,
            payoff.report.logical_fingerprint,
            len(payoff.report.decisions),
        ),
        (
            "fixed_cash_terminal_evidence",
            cash.report.contract_version,
            cash.report_sha256,
            cash.report.logical_fingerprint,
            len(cash.report.decisions),
        ),
        (
            "listed_consideration_terminal_evidence",
            listed.report.contract_version,
            listed.report_sha256,
            listed.report.logical_fingerprint,
            len(listed.report.decisions),
        ),
        (
            "residual_listed_consideration_terminal_evidence",
            residual.report.contract_version,
            residual.report_sha256,
            residual.report.logical_fingerprint,
            len(residual.report.decisions),
        ),
    ]
    raw.extend(
        (
            f"inactive_lifecycle_{item.manifest.anchor_date.isoformat().replace('-', '_')}",
            item.manifest.contract_version,
            item.manifest_sha256,
            item.manifest.logical_fingerprint,
            len(item.decisions),
        )
        for item in lifecycle
    )
    return tuple(
        SourceBindingV2(
            name=name,
            contract_version=contract,
            physical_sha256=sha,
            logical_fingerprint=fingerprint,
            record_count=count,
        )
        for name, contract, sha, fingerprint, count in sorted(raw)
    )


def _impacts(
    decisions: tuple[TerminalGapDecisionV2, ...],
) -> tuple[TerminalGapImpactV2, ...]:
    grouped: dict[GapState, list[TerminalGapDecisionV2]] = {}
    for item in decisions:
        grouped.setdefault(item.gap_state, []).append(item)
    return tuple(
        TerminalGapImpactV2(
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
        "cessation_timing_not_matched": "cessation_timing_adjudication_required",
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
        "newly_in_scope_primary_source_unadjudicated": (
            "corrected_population_primary_source_adjudication_required"
        ),
    }[state]


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "population": "all_corrected_horizon_5_eod_boundary_crossing_instruments",
            "legacy_population": "prior_identity_boundary_source_sample",
            "new_population": "formal_inactive_lifecycle_source_recovery",
            "path_counts": "terminal_boundary_census_corrected_eod_counts",
            "prior_evidence_states_preserved": True,
            "reference_value_is_terminal_outcome": False,
            "outcome_blind": True,
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalGapCensusV2,
) -> StrongLeaderPullbackTerminalGapCensusV2Result:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_gap_census_v2(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalGapCensusV2Error(
                "existing terminal-gap V2 census differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(partial / REPORT_FILE, _json_bytes(report.model_dump(mode="json")))
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink():
            shutil.rmtree(partial)
        raise
    reread = read_strong_leader_pullback_terminal_gap_census_v2(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalGapCensusV2Result(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _fingerprint(value: object) -> str:
    return _sha256_bytes(_json_bytes(value))


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 paths must be absolute"
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
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 custody or target is unsafe"
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
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTerminalGapCensusV2Error(
            "terminal-gap V2 file metadata differs"
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
