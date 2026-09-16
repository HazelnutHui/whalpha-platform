"""Frozen outcome-blind input qualification for Campaign Three interactions."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_campaign_three_hypotheses import (
    CampaignThreeHypothesisRole,
    quant_research_campaign_three_hypothesis_registry_v1,
)
from .quant_research_reusable_artifacts_v2 import (
    MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT,
    MARKET_STATE_QUALIFICATION_REPORT_SHA256,
)


QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_PROTOCOL_CONTRACT_VERSION = (
    "quant-research-campaign-input-qualification-protocol/1.0"
)
QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_PROTOCOL_VERSION = (
    "whalpha.quant-research.campaign-three-input-qualification/1.0.0"
)
QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_REPORT_CONTRACT_VERSION = (
    "quant-research-campaign-input-qualification-report/1.0"
)
V1_FACTOR_DIAGNOSTICS_FINGERPRINT = (
    "fb92e95acb146af66fb4d9e286c96852374a51884936f5d69536c4accacdab02"
)
V1_FACTOR_DIAGNOSTICS_SHA256 = (
    "3767c39e327e8e3959d184ae8a16d2c5be3e1425fda416093b6aeefc51485e5e"
)
V2_FACTOR_QUALIFICATION_FINGERPRINT = (
    "f49b17d74b9ec0960278405475ec962361c8169bd071030deda7fa36557aee90"
)
V2_FACTOR_QUALIFICATION_SHA256 = (
    "48b36f422e4a07e18de45e8b9a7bd8ea8d5469fc2961a84ab1037a554260999e"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CampaignThreeInputDecision(StrEnum):
    QUALIFIED_FOR_PROTOCOL_FREEZE = "qualified_for_protocol_freeze"
    REJECTED_INPUT_SUPPORT = "rejected_input_support"


class CampaignThreeInputQualificationStatus(StrEnum):
    READY_FOR_PROTOCOL_FREEZE = "ready_for_protocol_freeze"
    REJECTED_INPUT_SUPPORT = "rejected_input_support"


class CampaignThreeFactorVariationEvidence(StrEnum):
    V1_COMPLETE_SESSION_AND_PAIRWISE_ELIGIBILITY = (
        "v1_complete_session_and_pairwise_eligibility"
    )
    V2_EXACT_DEVELOPMENT_REPLAY = "v2_exact_development_replay"


class CampaignThreeInputQualificationProtocolV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_PROTOCOL_CONTRACT_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_PROTOCOL_CONTRACT_VERSION
    protocol_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_PROTOCOL_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_PROTOCOL_VERSION
    registered_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    source_hypothesis_registry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v1_factor_diagnostics_fingerprint: Literal[
        V1_FACTOR_DIAGNOSTICS_FINGERPRINT
    ] = V1_FACTOR_DIAGNOSTICS_FINGERPRINT
    source_v1_factor_diagnostics_sha256: Literal[V1_FACTOR_DIAGNOSTICS_SHA256] = (
        V1_FACTOR_DIAGNOSTICS_SHA256
    )
    source_v2_factor_qualification_fingerprint: Literal[
        V2_FACTOR_QUALIFICATION_FINGERPRINT
    ] = V2_FACTOR_QUALIFICATION_FINGERPRINT
    source_v2_factor_qualification_sha256: Literal[
        V2_FACTOR_QUALIFICATION_SHA256
    ] = V2_FACTOR_QUALIFICATION_SHA256
    source_market_state_qualification_fingerprint: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    ] = MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    source_market_state_qualification_sha256: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_SHA256
    ] = MARKET_STATE_QUALIFICATION_REPORT_SHA256
    development_first_session: Literal[date(2025, 7, 22)] = date(2025, 7, 22)
    development_last_session: Literal[date(2026, 1, 7)] = date(2026, 1, 7)
    development_session_count: Literal[106] = 106
    first_half_session_count: Literal[53] = 53
    second_half_session_count: Literal[53] = 53
    minimum_factor_eligible_session_count: Literal[80] = 80
    minimum_factor_half_eligible_session_count: Literal[40] = 40
    minimum_factor_instruments_per_session: Literal[100] = 100
    minimum_factor_distinct_values_per_session: Literal[2] = 2
    maximum_source_same_session_tie_excess_rate: Literal["0.2500000000"] = (
        "0.2500000000"
    )
    minimum_state_available_session_count: Literal[80] = 80
    minimum_state_half_available_session_count: Literal[40] = 40
    minimum_state_distinct_values: Literal[20] = 20
    minimum_state_half_distinct_values: Literal[10] = 10
    minimum_alpha_natural_zero_side_session_count: Literal[20] = 20
    minimum_alpha_natural_zero_side_half_session_count: Literal[8] = 8
    maximum_alpha_natural_zero_side_share: Literal["0.8500000000"] = (
        "0.8500000000"
    )
    maximum_alpha_same_side_run_sessions: Literal[35] = 35
    minimum_qualified_candidate_alpha_count: Literal[2] = 2
    minimum_qualified_risk_guard_count: Literal[1] = 1
    full_panel_hindsight_thresholds_authorized: Literal[False] = False
    contains_forward_outcomes: Literal[False] = False
    development_outcome_read_authorized: Literal[False] = False
    campaign_registration_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def protocol_reconciles(self) -> "CampaignThreeInputQualificationProtocolV1":
        registry = quant_research_campaign_three_hypothesis_registry_v1()
        if (
            self.source_hypothesis_registry_fingerprint
            != registry.logical_fingerprint
            or input_qualification_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three input qualification protocol differs")
        return self


class CampaignThreeInputQualificationDecisionV1(FrozenModel):
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    role: CampaignThreeHypothesisRole
    source_factor_catalog: Literal["v1", "v2"]
    source_factor_id: str
    state_metric_id: str
    factor_variation_evidence: CampaignThreeFactorVariationEvidence
    factor_eligible_session_count: int = Field(ge=0, le=106)
    factor_first_half_eligible_session_count: int = Field(ge=0, le=53)
    factor_second_half_eligible_session_count: int = Field(ge=0, le=53)
    factor_minimum_available_instruments: int = Field(ge=0)
    factor_minimum_distinct_values: int = Field(ge=0)
    source_same_session_tie_excess_rate: str
    state_available_session_count: int = Field(ge=0, le=106)
    state_first_half_available_session_count: int = Field(ge=0, le=53)
    state_second_half_available_session_count: int = Field(ge=0, le=53)
    state_distinct_value_count: int = Field(ge=0, le=106)
    state_first_half_distinct_value_count: int = Field(ge=0, le=53)
    state_second_half_distinct_value_count: int = Field(ge=0, le=53)
    state_positive_session_count: int = Field(ge=0, le=106)
    state_negative_session_count: int = Field(ge=0, le=106)
    state_zero_session_count: int = Field(ge=0, le=106)
    state_first_half_positive_session_count: int = Field(ge=0, le=53)
    state_first_half_negative_session_count: int = Field(ge=0, le=53)
    state_second_half_positive_session_count: int = Field(ge=0, le=53)
    state_second_half_negative_session_count: int = Field(ge=0, le=53)
    state_same_side_episode_count: int | None = Field(default=None, ge=1, le=106)
    state_longest_same_side_run: int | None = Field(default=None, ge=1, le=106)
    state_maximum_natural_zero_side_share: str | None = None
    decision: CampaignThreeInputDecision
    reason_codes: tuple[str, ...]
    contains_forward_outcomes: Literal[False] = False
    development_outcome_read_count: Literal[0] = 0
    formal_trial_registered: Literal[False] = False
    model_input_authorized: Literal[False] = False

    @model_validator(mode="after")
    def decision_reconciles(self) -> "CampaignThreeInputQualificationDecisionV1":
        protocol = quant_research_campaign_three_input_qualification_protocol_v1()
        registry = quant_research_campaign_three_hypothesis_registry_v1()
        source = next(
            (item for item in registry.proposals if item.hypothesis_id == self.hypothesis_id),
            None,
        )
        if (
            source is None
            or source.role is not self.role
            or source.source_factor_catalog != self.source_factor_catalog
            or source.source_factor_id != self.source_factor_id
            or source.state_metric_id != self.state_metric_id
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or self.factor_first_half_eligible_session_count
            + self.factor_second_half_eligible_session_count
            != self.factor_eligible_session_count
            or self.state_first_half_available_session_count
            + self.state_second_half_available_session_count
            != self.state_available_session_count
            or self.state_positive_session_count
            + self.state_negative_session_count
            + self.state_zero_session_count
            != self.state_available_session_count
        ):
            raise ValueError("Campaign Three input decision differs")
        _ratio(self.source_same_session_tie_excess_rate)
        if self.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION:
            if (
                self.state_same_side_episode_count is None
                or self.state_longest_same_side_run is None
                or self.state_maximum_natural_zero_side_share is None
            ):
                raise ValueError("Campaign Three Alpha state diagnostics are absent")
            _ratio(self.state_maximum_natural_zero_side_share)
        elif any(
            item is not None
            for item in (
                self.state_same_side_episode_count,
                self.state_longest_same_side_run,
                self.state_maximum_natural_zero_side_share,
            )
        ):
            raise ValueError("Campaign Three risk state carries Alpha diagnostics")
        qualified = not _input_rejection_reasons(self, protocol)
        if qualified != (
            self.decision is CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
        ) or self.reason_codes != _input_rejection_reasons(self, protocol):
            raise ValueError("Campaign Three input decision gate differs")
        return self


class CampaignThreeInputQualificationReportV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_REPORT_CONTRACT_VERSION
    ] = QUANT_RESEARCH_CAMPAIGN_THREE_INPUT_REPORT_CONTRACT_VERSION
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    created_at: datetime
    source_hypothesis_registry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v1_factor_diagnostics_fingerprint: Literal[
        V1_FACTOR_DIAGNOSTICS_FINGERPRINT
    ] = V1_FACTOR_DIAGNOSTICS_FINGERPRINT
    source_v1_factor_diagnostics_sha256: Literal[V1_FACTOR_DIAGNOSTICS_SHA256] = (
        V1_FACTOR_DIAGNOSTICS_SHA256
    )
    source_v2_factor_qualification_fingerprint: Literal[
        V2_FACTOR_QUALIFICATION_FINGERPRINT
    ] = V2_FACTOR_QUALIFICATION_FINGERPRINT
    source_v2_factor_qualification_sha256: Literal[
        V2_FACTOR_QUALIFICATION_SHA256
    ] = V2_FACTOR_QUALIFICATION_SHA256
    source_market_state_qualification_fingerprint: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    ] = MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    source_market_state_qualification_sha256: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_SHA256
    ] = MARKET_STATE_QUALIFICATION_REPORT_SHA256
    development_session_partition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    development_first_session: Literal[date(2025, 7, 22)] = date(2025, 7, 22)
    development_last_session: Literal[date(2026, 1, 7)] = date(2026, 1, 7)
    development_session_count: Literal[106] = 106
    decisions: tuple[CampaignThreeInputQualificationDecisionV1, ...] = Field(
        min_length=4, max_length=4
    )
    qualified_candidate_alpha_count: int = Field(ge=0, le=3)
    rejected_candidate_alpha_count: int = Field(ge=0, le=3)
    qualified_risk_guard_count: int = Field(ge=0, le=1)
    rejected_risk_guard_count: int = Field(ge=0, le=1)
    status: CampaignThreeInputQualificationStatus
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    development_outcome_read_count: Literal[0] = 0
    formal_trial_count_registered: Literal[0] = 0
    campaign_three_registered: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "CampaignThreeInputQualificationReportV1":
        protocol = quant_research_campaign_three_input_qualification_protocol_v1()
        registry = quant_research_campaign_three_hypothesis_registry_v1()
        accepted_ids = tuple(
            item.hypothesis_id
            for item in registry.proposals
            if item.prospective_trial_count == 1
        )
        qualified_alpha = sum(
            item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            and item.decision
            is CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
            for item in self.decisions
        )
        rejected_alpha = sum(
            item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            and item.decision is CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT
            for item in self.decisions
        )
        qualified_risk = sum(
            item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
            and item.decision
            is CampaignThreeInputDecision.QUALIFIED_FOR_PROTOCOL_FREEZE
            for item in self.decisions
        )
        rejected_risk = sum(
            item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
            and item.decision is CampaignThreeInputDecision.REJECTED_INPUT_SUPPORT
            for item in self.decisions
        )
        ready = (
            qualified_alpha >= protocol.minimum_qualified_candidate_alpha_count
            and qualified_risk >= protocol.minimum_qualified_risk_guard_count
        )
        expected_status = (
            CampaignThreeInputQualificationStatus.READY_FOR_PROTOCOL_FREEZE
            if ready
            else CampaignThreeInputQualificationStatus.REJECTED_INPUT_SUPPORT
        )
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.source_hypothesis_registry_fingerprint
            != registry.logical_fingerprint
            or tuple(item.hypothesis_id for item in self.decisions) != accepted_ids
            or (
                qualified_alpha,
                rejected_alpha,
                qualified_risk,
                rejected_risk,
            )
            != (
                self.qualified_candidate_alpha_count,
                self.rejected_candidate_alpha_count,
                self.qualified_risk_guard_count,
                self.rejected_risk_guard_count,
            )
            or self.status is not expected_status
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
            or input_qualification_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three input qualification report differs")
        return self


def input_qualification_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def quant_research_campaign_three_input_qualification_protocol_v1() -> (
    CampaignThreeInputQualificationProtocolV1
):
    payload = {
        "source_hypothesis_registry_fingerprint": (
            quant_research_campaign_three_hypothesis_registry_v1().logical_fingerprint
        )
    }
    provisional = CampaignThreeInputQualificationProtocolV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return CampaignThreeInputQualificationProtocolV1.model_validate(
        {
            **payload,
            "logical_fingerprint": input_qualification_fingerprint(provisional),
        }
    )


def _input_rejection_reasons(
    value: CampaignThreeInputQualificationDecisionV1,
    protocol: CampaignThreeInputQualificationProtocolV1,
) -> tuple[str, ...]:
    reasons = []
    if value.factor_eligible_session_count < protocol.minimum_factor_eligible_session_count:
        reasons.append("factor_eligible_sessions_below_floor")
    if min(
        value.factor_first_half_eligible_session_count,
        value.factor_second_half_eligible_session_count,
    ) < protocol.minimum_factor_half_eligible_session_count:
        reasons.append("factor_half_eligible_sessions_below_floor")
    if value.factor_minimum_available_instruments < protocol.minimum_factor_instruments_per_session:
        reasons.append("factor_cross_section_below_floor")
    if value.factor_minimum_distinct_values < protocol.minimum_factor_distinct_values_per_session:
        reasons.append("factor_variation_below_floor")
    if _ratio(value.source_same_session_tie_excess_rate) > Decimal(
        protocol.maximum_source_same_session_tie_excess_rate
    ):
        reasons.append("factor_tie_excess_above_ceiling")
    if value.state_available_session_count < protocol.minimum_state_available_session_count:
        reasons.append("state_available_sessions_below_floor")
    if min(
        value.state_first_half_available_session_count,
        value.state_second_half_available_session_count,
    ) < protocol.minimum_state_half_available_session_count:
        reasons.append("state_half_available_sessions_below_floor")
    if value.state_distinct_value_count < protocol.minimum_state_distinct_values:
        reasons.append("state_distinct_values_below_floor")
    if min(
        value.state_first_half_distinct_value_count,
        value.state_second_half_distinct_value_count,
    ) < protocol.minimum_state_half_distinct_values:
        reasons.append("state_half_distinct_values_below_floor")
    if value.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION:
        if min(
            value.state_positive_session_count,
            value.state_negative_session_count,
        ) < protocol.minimum_alpha_natural_zero_side_session_count:
            reasons.append("alpha_natural_zero_side_below_floor")
        if min(
            value.state_first_half_positive_session_count,
            value.state_first_half_negative_session_count,
            value.state_second_half_positive_session_count,
            value.state_second_half_negative_session_count,
        ) < protocol.minimum_alpha_natural_zero_side_half_session_count:
            reasons.append("alpha_half_natural_zero_side_below_floor")
        assert value.state_maximum_natural_zero_side_share is not None
        if _ratio(value.state_maximum_natural_zero_side_share) > Decimal(
            protocol.maximum_alpha_natural_zero_side_share
        ):
            reasons.append("alpha_state_side_concentration_above_ceiling")
        assert value.state_longest_same_side_run is not None
        if value.state_longest_same_side_run > protocol.maximum_alpha_same_side_run_sessions:
            reasons.append("alpha_state_run_concentration_above_ceiling")
    return tuple(sorted(reasons))


def _ratio(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Campaign Three ratio is invalid") from exc
    if (
        not parsed.is_finite()
        or not Decimal("0") <= parsed <= Decimal("1")
        or value != format(parsed.quantize(Decimal("0.0000000001")), "f")
    ):
        raise ValueError("Campaign Three ratio must be canonical in [0,1]")
    return parsed
