"""Language-neutral, bounded consumer contract for opportunity candidates."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .opportunity_candidate import (
    CandidateComponentV1,
    CandidateConfidenceV1,
    CandidateDataQualityStatus,
    CandidateOpportunityStage,
    CandidateRiskMode,
    CandidateStateGateResultV1,
    CandidateStateTransitionStatus,
)
from .candidate_entry_geometry import CandidateEntryGeometryV1
from tip_api.parameters.market_regime.candidate_entry_consumer_v1_0_0 import (
    ENTRY_LANE_CONSUMER_CONTRACT_VERSION,
    ENTRY_LANE_CONSUMER_PARAMETER_SET_ID,
    ENTRY_LANE_ORDER,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CandidatePublicationEvidenceV1(FrozenModel):
    evidence_kind: Literal["supporting", "counterevidence"]
    evidence_id: Literal["positive_component", "weak_component", "missing_component"]
    component_id: str
    observed_value: str | None


class CandidateRiskDispositionV1(FrozenModel):
    risk_mode: CandidateRiskMode
    eligible: bool
    risk_adjusted_rank: int | None = Field(default=None, ge=1)
    rejection_reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def disposition_reconciles(self) -> "CandidateRiskDispositionV1":
        if self.eligible != (self.risk_adjusted_rank is not None):
            raise ValueError("candidate risk eligibility and rank differ")
        if self.eligible == bool(self.rejection_reason_codes):
            raise ValueError("candidate risk rejection reasons differ from eligibility")
        return self


class CandidatePublicationStateV1(FrozenModel):
    final_stage: CandidateOpportunityStage | None
    transition_status: CandidateStateTransitionStatus
    transition_rule_id: str
    pending_target_stage: CandidateOpportunityStage | None
    stage_confirmation_count: int = Field(ge=0)
    required_confirmation_sessions: int = Field(ge=0)
    breakout_triggered: bool | None
    stale_state: bool
    manual_review_required: bool
    gate_results: tuple[CandidateStateGateResultV1, ...]
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class OpportunityCandidatePublicationItemV1(FrozenModel):
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    base_score: str | None
    adjusted_score: str | None
    configured_weight_available: str
    missingness_penalty: str
    confidence: CandidateConfidenceV1
    latest_price: str
    median_dollar_volume_20: str | None
    annualized_volatility_10: str | None
    maximum_absolute_open_gap_5: str | None
    current_volume_ratio: str | None
    primary_driver_instrument_id: UUID | None
    primary_driver_ticker: str | None
    driver_correlation_20: str | None
    relationship_kind: Literal["price_derived_exposure_proxy"] | None
    data_quality_status: CandidateDataQualityStatus
    components: tuple[CandidateComponentV1, ...]
    evidence: tuple[CandidatePublicationEvidenceV1, ...]
    invalidation_condition_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    state: CandidatePublicationStateV1
    risk_dispositions: tuple[CandidateRiskDispositionV1, ...]
    score_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def item_reconciles(self) -> "OpportunityCandidatePublicationItemV1":
        if tuple(row.risk_mode for row in self.risk_dispositions) != tuple(CandidateRiskMode):
            raise ValueError("candidate risk dispositions must use fixed mode order")
        if (
            self.state.final_stage is not CandidateOpportunityStage.INVALIDATED
            and not any(row.eligible for row in self.risk_dispositions)
            and getattr(self, "entry_geometry", None) is None
        ):
            raise ValueError("published active candidate must be eligible in at least one risk mode")
        return self


class CandidateRiskModePublicationV1(FrozenModel):
    risk_mode: CandidateRiskMode
    eligible_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    display_cap: int = Field(gt=0)
    displayed_instrument_ids: tuple[UUID, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def display_reconciles(self) -> "CandidateRiskModePublicationV1":
        if len(self.displayed_instrument_ids) != min(self.eligible_count, self.display_cap):
            raise ValueError("candidate risk display count differs from its fixed cap")
        if len(self.displayed_instrument_ids) != len(set(self.displayed_instrument_ids)):
            raise ValueError("candidate risk display IDs must be unique")
        return self


class OpportunityCandidateUniversePublicationV1(FrozenModel):
    universe_id: str
    universe_member_count: int = Field(gt=0)
    membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    bar_covered_member_count: int = Field(ge=0)
    missing_member_count: int = Field(ge=0)
    quality_counts: dict[CandidateDataQualityStatus, int]
    stage_counts: dict[str, int]
    risk_modes: tuple[CandidateRiskModePublicationV1, ...]
    candidates: tuple[OpportunityCandidatePublicationItemV1, ...]
    candidate_batch_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def universe_reconciles(self) -> "OpportunityCandidateUniversePublicationV1":
        if self.bar_covered_member_count + self.missing_member_count != self.universe_member_count:
            raise ValueError("published candidate coverage does not reconcile")
        if sum(self.quality_counts.values()) != self.bar_covered_member_count:
            raise ValueError("published candidate quality counts do not reconcile")
        if sum(self.stage_counts.values()) != self.universe_member_count:
            raise ValueError("published candidate stage counts do not reconcile")
        if tuple(row.risk_mode for row in self.risk_modes) != tuple(CandidateRiskMode):
            raise ValueError("published risk results must use fixed mode order")
        ids = tuple(str(row.instrument_id) for row in self.candidates)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("published candidate cards must be unique and stable-ID ordered")
        available = {row.instrument_id for row in self.candidates}
        if any(
            instrument_id not in available
            for result in self.risk_modes
            for instrument_id in result.displayed_instrument_ids
        ):
            raise ValueError("risk-mode display references an unpublished candidate")
        return self


class OpportunityCandidatePublicationSourceV1(FrozenModel):
    candidate_audit_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_audit_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_state_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    risk_results_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    oracle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    oracle_mismatch_count: Literal[0] = 0
    shared_raw_fact_match: Literal[True] = True
    input_permutation_match: Literal[True] = True
    append_full_replay_match: Literal[True] = True
    restart_replay_match: Literal[True] = True
    future_prefix_stable: Literal[True] = True
    candidate_contract_version: Literal["opportunity-candidate/1.1"]
    candidate_calculation_version: Literal["market-regime-opportunity-candidate-v1.1.1"]
    candidate_parameter_set_id: Literal["mrom-candidate-v1-fixed-baseline-3"]
    candidate_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_state_contract_version: Literal["opportunity-candidate-state/1.0"]
    candidate_state_calculation_version: Literal[
        "market-regime-opportunity-candidate-state-v1.0.0"
    ]
    candidate_state_parameter_set_id: Literal["mrom-candidate-state-v1-fixed-baseline-1"]
    candidate_state_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    activation_pointer_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eod_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    eod_business_key_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    history_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_candidate_batch_fingerprints: tuple[str, str]
    current_risk_result_fingerprints: tuple[str, str, str, str, str, str]

    @model_validator(mode="after")
    def current_fingerprints_are_digests(self) -> "OpportunityCandidatePublicationSourceV1":
        values = (
            *self.current_candidate_batch_fingerprints,
            *self.current_risk_result_fingerprints,
        )
        if any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in values):
            raise ValueError("Candidate current source fingerprints must be SHA-256 digests")
        return self


class OpportunityCandidatePublicationV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["opportunity-candidate-publication/1.0"] = (
        "opportunity-candidate-publication/1.0"
    )
    as_of_session: date
    default_universe_id: str
    universe_order: tuple[str, str]
    risk_mode_order: tuple[CandidateRiskMode, CandidateRiskMode, CandidateRiskMode] = tuple(
        CandidateRiskMode
    )
    source: OpportunityCandidatePublicationSourceV1
    universes: tuple[
        OpportunityCandidateUniversePublicationV1,
        OpportunityCandidateUniversePublicationV1,
    ]
    language_neutral: Literal[True] = True
    research_priority_only: Literal[True] = True
    underlying_stock_result_not_option_return: Literal[True] = True
    price_volume_not_fund_flow: Literal[True] = True
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def publication_reconciles(self) -> "OpportunityCandidatePublicationV1":
        if tuple(row.universe_id for row in self.universes) != self.universe_order:
            raise ValueError("candidate publication Universe order differs")
        if self.default_universe_id != self.universe_order[0]:
            raise ValueError("candidate publication default Universe must be first")
        raw = json.dumps(
            self.model_dump(mode="json", exclude={"logical_fingerprint"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != self.logical_fingerprint:
            raise ValueError("candidate publication logical fingerprint mismatch")
        return self


class CandidateEntryLane(StrEnum):
    REVIEW_NOW = "review_now"
    WATCH_TRIGGER = "watch_trigger"
    WAIT_RESET = "wait_reset"
    OTHER_RESEARCH = "other_research"


class CandidateEntryLanePublicationV1(FrozenModel):
    lane: CandidateEntryLane
    qualifying_count: int = Field(ge=0)
    display_cap: int = Field(gt=0)
    displayed_instrument_ids: tuple[UUID, ...]

    @model_validator(mode="after")
    def lane_reconciles(self) -> "CandidateEntryLanePublicationV1":
        if len(self.displayed_instrument_ids) > min(self.qualifying_count, self.display_cap):
            raise ValueError("entry-lane display exceeds its qualifying population or cap")
        if len(self.displayed_instrument_ids) != len(set(self.displayed_instrument_ids)):
            raise ValueError("entry-lane display IDs must be unique")
        return self


class CandidateRiskModeEntryPublicationV1(FrozenModel):
    risk_mode: CandidateRiskMode
    hard_risk_gate_qualified_count: int = Field(ge=0)
    lanes: tuple[
        CandidateEntryLanePublicationV1,
        CandidateEntryLanePublicationV1,
        CandidateEntryLanePublicationV1,
        CandidateEntryLanePublicationV1,
    ]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def lane_order_reconciles(self) -> "CandidateRiskModeEntryPublicationV1":
        if tuple(row.lane.value for row in self.lanes) != ENTRY_LANE_ORDER:
            raise ValueError("entry lanes must use the fixed decision order")
        if sum(row.qualifying_count for row in self.lanes) != self.hard_risk_gate_qualified_count:
            raise ValueError("entry-lane qualifying counts do not reconcile")
        raw = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if hashlib.sha256(
            json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest() != self.logical_fingerprint:
            raise ValueError("entry-lane logical fingerprint mismatch")
        return self


class OpportunityCandidatePublicationItemV1_1(OpportunityCandidatePublicationItemV1):
    entry_geometry: CandidateEntryGeometryV1

    @model_validator(mode="after")
    def entry_geometry_reconciles(self) -> "OpportunityCandidatePublicationItemV1_1":
        if (
            self.entry_geometry.instrument_id != self.instrument_id
            or self.entry_geometry.ticker != self.ticker
            or self.entry_geometry.security_type != self.security_type
            or self.entry_geometry.source_candidate_fingerprint != self.score_logical_fingerprint
            or self.entry_geometry.candidate_stage != self.state.final_stage
            or self.entry_geometry.candidate_base_score != self.base_score
        ):
            raise ValueError("published Candidate and entry geometry differ")
        return self


class OpportunityCandidateUniversePublicationV1_1(OpportunityCandidateUniversePublicationV1):
    entry_risk_modes: tuple[
        CandidateRiskModeEntryPublicationV1,
        CandidateRiskModeEntryPublicationV1,
        CandidateRiskModeEntryPublicationV1,
    ]
    candidates: tuple[OpportunityCandidatePublicationItemV1_1, ...]

    @model_validator(mode="after")
    def entry_universe_reconciles(self) -> "OpportunityCandidateUniversePublicationV1_1":
        if tuple(row.risk_mode for row in self.entry_risk_modes) != tuple(CandidateRiskMode):
            raise ValueError("entry risk modes must use fixed mode order")
        published = {row.instrument_id for row in self.candidates}
        if any(
            instrument_id not in published
            for result in self.entry_risk_modes
            for lane in result.lanes
            for instrument_id in lane.displayed_instrument_ids
        ):
            raise ValueError("entry lane references an unpublished Candidate card")
        if any(row.entry_geometry.universe_id != self.universe_id for row in self.candidates):
            raise ValueError("entry geometry Universe differs from Candidate publication")
        return self


class OpportunityCandidatePublicationSourceV1_1(OpportunityCandidatePublicationSourceV1):
    entry_geometry_audit_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_geometry_audit_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_geometry_contract_version: Literal["candidate-entry-geometry/1.0"]
    entry_geometry_calculation_version: Literal["candidate-entry-geometry-v1.0.0"]
    entry_geometry_parameter_set_id: Literal["candidate-entry-geometry-v1-fixed-baseline-1"]
    entry_geometry_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_geometry_oracle_mismatch_count: Literal[0] = 0
    entry_geometry_input_permutation_match: Literal[True] = True
    entry_geometry_batch_fingerprints: tuple[str, str]
    entry_lane_consumer_contract_version: Literal[ENTRY_LANE_CONSUMER_CONTRACT_VERSION]
    entry_lane_consumer_parameter_set_id: Literal[ENTRY_LANE_CONSUMER_PARAMETER_SET_ID]
    entry_lane_consumer_parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def entry_fingerprints_are_digests(self) -> "OpportunityCandidatePublicationSourceV1_1":
        if any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in self.entry_geometry_batch_fingerprints):
            raise ValueError("entry-geometry batch fingerprints must be SHA-256 digests")
        return self


class OpportunityCandidatePublicationV1_1(OpportunityCandidatePublicationV1):
    contract_version: Literal["opportunity-candidate-publication/1.1"] = (
        "opportunity-candidate-publication/1.1"
    )
    source: OpportunityCandidatePublicationSourceV1_1
    universes: tuple[
        OpportunityCandidateUniversePublicationV1_1,
        OpportunityCandidateUniversePublicationV1_1,
    ]
    leadership_rank_preserved: Literal[True] = True
    entry_location_separate_from_leadership: Literal[True] = True
    reference_support_not_stop_price: Literal[True] = True

    @model_validator(mode="after")
    def entry_publication_reconciles(self) -> "OpportunityCandidatePublicationV1_1":
        if any(
            row.entry_geometry.as_of_session != self.as_of_session
            for universe in self.universes
            for row in universe.candidates
        ):
            raise ValueError("entry geometry as-of session differs from Candidate publication")
        raw = json.dumps(
            self.model_dump(mode="json", exclude={"logical_fingerprint"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != self.logical_fingerprint:
            raise ValueError("Candidate 1.1 publication logical fingerprint mismatch")
        return self
