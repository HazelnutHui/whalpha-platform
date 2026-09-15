"""Aggregate outcome-blind terminal-reference bounds for research admission."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.services.strong_leader_pullback_research_admission_v2 import (
    TerminalReferenceEvidenceV1,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-reference-bounds/1.0"
EXPECTED_RESIDUAL_CASE_COUNT = 18
EXPECTED_RESIDUAL_PATH_COUNT = 88
PRIOR_EXACT_REFERENCE_PATH_COUNT = 214
EXPECTED_TERMINAL_PATH_COUNT = 302
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_MONEY_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{10}$"


class TerminalReferenceBoundState(StrEnum):
    EXACT_REFERENCE_READY = "exact_reference_ready"
    FINITE_INTERVAL_READY = "finite_interval_ready"
    SOURCE_EVIDENCE_PENDING = "source_evidence_pending"


class TerminalReferencePolicy(StrEnum):
    FORCED_LAST_US_CLOSE = "forced_last_us_close"
    ZERO_TO_FIXED_CASH = "zero_to_fixed_cash"
    ZERO_TO_CASH_PLUS_CVR_CAP = "zero_to_cash_plus_cvr_cap"
    ZERO_TO_LISTED_CONSIDERATION_MAX = "zero_to_listed_consideration_max"
    ZERO_TO_UNLISTED_CONSIDERATION_VALUE = (
        "zero_to_unlisted_consideration_value"
    )


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalReferenceEvidenceLocatorV1(_FrozenModel):
    evidence_role: Literal[
        "canonical_successor_close",
        "canonical_target_close",
        "retained_payoff_terms",
        "retained_sec_document",
    ]
    evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)


class TerminalReferenceBoundCaseV1(_FrozenModel):
    instrument_id: UUID
    ticker_locator: str = Field(pattern=r"^[A-Z][A-Z0-9.]{0,14}$")
    prior_gap_state: str = Field(min_length=1)
    crossing_path_count: int = Field(ge=1, le=5)
    bound_state: TerminalReferenceBoundState
    policy: TerminalReferencePolicy | None = None
    lower_reference_value_usd: str | None = Field(
        default=None, pattern=_MONEY_PATTERN
    )
    upper_reference_value_usd: str | None = Field(
        default=None, pattern=_MONEY_PATTERN
    )
    evidence: tuple[TerminalReferenceEvidenceLocatorV1, ...] = ()
    missing_source_roles: tuple[
        Literal[
            "foreign_continuation_terms",
            "final_cvr_cap",
            "listed_consideration_terms",
            "unlisted_unit_acquisition_value",
        ],
        ...,
    ] = ()
    point_imputation_used: Literal[False] = False
    forward_outcome_read: Literal[False] = False
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0

    @field_validator("evidence", mode="before")
    @classmethod
    def evidence_is_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        keys = tuple(
            (item["evidence_role"], item["evidence_fingerprint"])
            if isinstance(item, dict)
            else (item.evidence_role, item.evidence_fingerprint)
            for item in values
        )
        if keys != tuple(sorted(set(keys))):
            raise ValueError("terminal reference evidence must be unique and sorted")
        return values

    @field_validator("missing_source_roles", mode="before")
    @classmethod
    def missing_roles_are_ordered_unique(
        cls, value: object
    ) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("missing source roles must be unique and sorted")
        return values

    @model_validator(mode="after")
    def bound_reconciles(self) -> "TerminalReferenceBoundCaseV1":
        pending = (
            self.bound_state
            is TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING
        )
        values_present = (
            self.lower_reference_value_usd is not None
            and self.upper_reference_value_usd is not None
        )
        if pending:
            if (
                self.policy is not None
                or values_present
                or not self.missing_source_roles
            ):
                raise ValueError("pending terminal reference is not fail closed")
            return self
        if (
            self.policy is None
            or not values_present
            or not self.evidence
            or self.missing_source_roles
        ):
            raise ValueError("ready terminal reference lacks bound evidence")
        lower = Decimal(self.lower_reference_value_usd)
        upper = Decimal(self.upper_reference_value_usd)
        exact = self.bound_state is TerminalReferenceBoundState.EXACT_REFERENCE_READY
        if lower > upper or exact != (lower == upper):
            raise ValueError("terminal reference bounds do not match state")
        if exact != (self.policy is TerminalReferencePolicy.FORCED_LAST_US_CLOSE):
            raise ValueError("exact terminal reference policy differs")
        if not exact and lower != Decimal("0"):
            raise ValueError("interval lower reference value must be zero")
        return self


class StrongLeaderPullbackTerminalReferenceBoundsV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-reference-bounds/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "complete", "source_evidence_pending"
    ]
    terminal_population_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_exact_reference_path_count: Literal[214] = (
        PRIOR_EXACT_REFERENCE_PATH_COUNT
    )
    residual_case_count: Literal[18] = EXPECTED_RESIDUAL_CASE_COUNT
    residual_path_count: Literal[88] = EXPECTED_RESIDUAL_PATH_COUNT
    supplemental_exact_reference_path_count: int = Field(ge=0, le=88)
    finite_interval_reference_path_count: int = Field(ge=0, le=88)
    unbounded_reference_path_count: int = Field(ge=0, le=88)
    total_exact_reference_path_count: int = Field(ge=214, le=302)
    total_terminal_path_count: Literal[302] = EXPECTED_TERMINAL_PATH_COUNT
    cases: tuple[TerminalReferenceBoundCaseV1, ...] = Field(min_length=18)
    interval_rules_frozen_before_outcomes: Literal[True] = True
    complete_case_headline_allowed: Literal[False] = False
    point_imputation_allowed: Literal[False] = False
    adversarial_interval_evaluation_required: Literal[True] = True
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalReferenceBoundsV1":
        case_keys = tuple(
            (item.ticker_locator, str(item.instrument_id)) for item in self.cases
        )
        if case_keys != tuple(sorted(set(case_keys))):
            raise ValueError("terminal reference cases must be unique and sorted")
        exact = sum(
            item.crossing_path_count
            for item in self.cases
            if item.bound_state
            is TerminalReferenceBoundState.EXACT_REFERENCE_READY
        )
        interval = sum(
            item.crossing_path_count
            for item in self.cases
            if item.bound_state
            is TerminalReferenceBoundState.FINITE_INTERVAL_READY
        )
        unbounded = sum(
            item.crossing_path_count
            for item in self.cases
            if item.bound_state
            is TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING
        )
        if (
            len(self.cases) != EXPECTED_RESIDUAL_CASE_COUNT
            or sum(item.crossing_path_count for item in self.cases)
            != EXPECTED_RESIDUAL_PATH_COUNT
            or (exact, interval, unbounded)
            != (
                self.supplemental_exact_reference_path_count,
                self.finite_interval_reference_path_count,
                self.unbounded_reference_path_count,
            )
            or self.total_exact_reference_path_count
            != PRIOR_EXACT_REFERENCE_PATH_COUNT + exact
            or self.completion_status
            != ("complete" if unbounded == 0 else "source_evidence_pending")
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal reference bounds report differs")
        return self

    def to_admission_evidence(self) -> TerminalReferenceEvidenceV1:
        return TerminalReferenceEvidenceV1(
            terminal_population_fingerprint=self.logical_fingerprint,
            crossing_path_count=self.total_terminal_path_count,
            exact_terminal_reference_path_count=(
                self.total_exact_reference_path_count
            ),
            interval_terminal_reference_path_count=(
                self.finite_interval_reference_path_count
            ),
            unbounded_terminal_reference_path_count=(
                self.unbounded_reference_path_count
            ),
            interval_rules_frozen_before_outcomes=True,
        )


def build_strong_leader_pullback_terminal_reference_bounds(
    *,
    terminal_population_fingerprint: str,
    cases: tuple[TerminalReferenceBoundCaseV1, ...],
) -> StrongLeaderPullbackTerminalReferenceBoundsV1:
    """Aggregate reviewed references without reading outcomes or providers."""

    exact = sum(
        item.crossing_path_count
        for item in cases
        if item.bound_state
        is TerminalReferenceBoundState.EXACT_REFERENCE_READY
    )
    interval = sum(
        item.crossing_path_count
        for item in cases
        if item.bound_state
        is TerminalReferenceBoundState.FINITE_INTERVAL_READY
    )
    unbounded = sum(
        item.crossing_path_count
        for item in cases
        if item.bound_state
        is TerminalReferenceBoundState.SOURCE_EVIDENCE_PENDING
    )
    values = {
        "completion_status": (
            "complete" if unbounded == 0 else "source_evidence_pending"
        ),
        "terminal_population_fingerprint": terminal_population_fingerprint,
        "supplemental_exact_reference_path_count": exact,
        "finite_interval_reference_path_count": interval,
        "unbounded_reference_path_count": unbounded,
        "total_exact_reference_path_count": (
            PRIOR_EXACT_REFERENCE_PATH_COUNT + exact
        ),
        "cases": cases,
    }
    provisional = StrongLeaderPullbackTerminalReferenceBoundsV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return StrongLeaderPullbackTerminalReferenceBoundsV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
