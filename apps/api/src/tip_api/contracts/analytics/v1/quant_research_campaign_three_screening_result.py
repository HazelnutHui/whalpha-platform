"""Typed Development-only results for Campaign Three interaction screening."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_campaign_three_hypotheses import (
    MARKET_STATE_ARTIFACT_CONTENT_SHA256,
    MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT,
    CampaignThreeHypothesisRole,
)
from .quant_research_campaign_three_input_qualification import (
    V1_FACTOR_DIAGNOSTICS_FINGERPRINT,
    V1_FACTOR_DIAGNOSTICS_SHA256,
    V2_FACTOR_QUALIFICATION_FINGERPRINT,
    V2_FACTOR_QUALIFICATION_SHA256,
)
from .quant_research_campaign_three_screening import (
    CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT,
    CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256,
    quant_research_campaign_three_screening_protocol_v1,
)
from .quant_research_discovery_trial_ledger_v4 import (
    quant_research_discovery_trial_ledger_v4,
)
from .quant_research_factor_screening_result import (
    QuantResearchFactorScreeningDecisionStatus,
    QuantResearchFactorScreeningEndpoint,
    QuantResearchFactorScreeningLabelState,
    QuantResearchFactorScreeningReportStatus,
)
from .quant_research_reusable_artifacts_v2 import (
    MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT,
    MARKET_STATE_QUALIFICATION_REPORT_SHA256,
)


CAMPAIGN_THREE_SCREENING_REPORT_CONTRACT_VERSION = (
    "quant-research-campaign-three-screening-report/1.0"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CampaignThreeCostDiagnosticStatus(StrEnum):
    DECLARED_NON_GATING_NO_STRATEGY_EXPRESSION = (
        "declared_non_gating_no_strategy_expression"
    )


class CampaignThreeSessionEvidenceV1(FrozenModel):
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    role: CampaignThreeHypothesisRole
    horizon_sessions: Literal[1, 3, 5]
    endpoint: QuantResearchFactorScreeningEndpoint
    signal_session: date
    instrument_count: int = Field(ge=100)
    state_value: str
    session_rank_ic: str

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "CampaignThreeSessionEvidenceV1":
        _finite_decimal(self.state_value)
        rank_ic = _finite_decimal(self.session_rank_ic)
        if rank_ic < Decimal("-1") or rank_ic > Decimal("1"):
            raise ValueError("Campaign Three session rank IC is outside [-1,1]")
        return self


class CampaignThreeInteractionSummaryV1(FrozenModel):
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    role: CampaignThreeHypothesisRole
    horizon_sessions: Literal[1, 3, 5]
    endpoint: QuantResearchFactorScreeningEndpoint
    eligible_session_count: int = Field(ge=0, le=106)
    first_half_session_count: int = Field(ge=0, le=53)
    second_half_session_count: int = Field(ge=0, le=53)
    evidence_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    regression_alpha: str | None = None
    interaction_beta: str | None = None
    primary_block_lower_90pct: str | None = None
    primary_block_one_sided_p_value: str | None = None
    sensitivity_block_lower_90pct: str | None = None
    sensitivity_block_one_sided_p_value: str | None = None
    first_half_beta: str | None = None
    second_half_beta: str | None = None
    favorable_state_session_count: int | None = Field(default=None, ge=0, le=106)
    favorable_state_mean_rank_ic: str | None = None
    cost_scenarios_bps_per_side: tuple[
        Literal[0], Literal[10], Literal[25], Literal[50]
    ] = (0, 10, 25, 50)
    cost_diagnostic_status: CampaignThreeCostDiagnosticStatus = (
        CampaignThreeCostDiagnosticStatus.DECLARED_NON_GATING_NO_STRATEGY_EXPRESSION
    )
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def summary_reconciles(self) -> "CampaignThreeInteractionSummaryV1":
        if (
            self.first_half_session_count + self.second_half_session_count
            != self.eligible_session_count
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("Campaign Three interaction summary counts differ")
        numeric = (
            self.regression_alpha,
            self.interaction_beta,
            self.primary_block_lower_90pct,
            self.primary_block_one_sided_p_value,
            self.sensitivity_block_lower_90pct,
            self.sensitivity_block_one_sided_p_value,
            self.first_half_beta,
            self.second_half_beta,
        )
        regression_unavailable = "regression_unavailable" in self.reason_codes
        numeric_present = tuple(item is not None for item in numeric)
        if regression_unavailable:
            if any(numeric_present):
                raise ValueError(
                    "Campaign Three unavailable regression carries statistics"
                )
        elif self.eligible_session_count >= 2:
            if not all(numeric_present):
                raise ValueError("Campaign Three interaction statistics are absent")
            for item in numeric:
                assert item is not None
                _finite_decimal(item)
            for probability in (
                self.primary_block_one_sided_p_value,
                self.sensitivity_block_one_sided_p_value,
            ):
                assert probability is not None
                value = _finite_decimal(probability)
                if value < 0 or value > 1:
                    raise ValueError("Campaign Three probability is outside [0,1]")
        elif any(numeric_present):
            raise ValueError("Campaign Three empty summary carries statistics")
        if self.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION:
            if self.favorable_state_session_count is None:
                raise ValueError("Campaign Three Alpha favorable-state count is absent")
            if self.favorable_state_mean_rank_ic is not None:
                _finite_decimal(self.favorable_state_mean_rank_ic)
            if (
                not regression_unavailable
                and self.favorable_state_session_count > 0
                and self.favorable_state_mean_rank_ic is None
            ):
                raise ValueError("Campaign Three Alpha favorable-state mean is absent")
        elif (
            self.favorable_state_session_count is not None
            or self.favorable_state_mean_rank_ic is not None
        ):
            raise ValueError("Campaign Three risk summary carries Alpha state gate")
        return self


class CampaignThreeScreeningDecisionV1(FrozenModel):
    trial_id: str = Field(
        pattern=r"^whalpha\.discovery-trial\.campaign-three\.[a-z0-9-]+\.h3$"
    )
    hypothesis_id: str = Field(
        pattern=r"^whalpha\.hypothesis\.campaign-three\.[a-z0-9-]+$"
    )
    role: CampaignThreeHypothesisRole
    related_hypothesis_family: str
    primary_endpoint_count: Literal[1, 2]
    raw_family_p_value: str | None = None
    holm_adjusted_p_value: str | None = None
    worst_case_primary_beta: str | None = None
    worst_case_registered_lower_bound: str | None = None
    status: QuantResearchFactorScreeningDecisionStatus
    passed_all_frozen_gates: bool
    selected_for_model_candidate_set: bool
    failed_gate_codes: tuple[str, ...]

    @model_validator(mode="after")
    def decision_reconciles(self) -> "CampaignThreeScreeningDecisionV1":
        if self.failed_gate_codes != tuple(sorted(set(self.failed_gate_codes))):
            raise ValueError("Campaign Three failed gates are not canonical")
        numeric = (
            self.raw_family_p_value,
            self.holm_adjusted_p_value,
            self.worst_case_primary_beta,
            self.worst_case_registered_lower_bound,
        )
        for item in numeric:
            if item is not None:
                _finite_decimal(item)
        for probability in (self.raw_family_p_value, self.holm_adjusted_p_value):
            if probability is not None:
                parsed = _finite_decimal(probability)
                if parsed < 0 or parsed > 1:
                    raise ValueError("Campaign Three decision probability is outside [0,1]")
        expected_endpoint_count = (
            2
            if self.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
            else 1
        )
        if self.primary_endpoint_count != expected_endpoint_count:
            raise ValueError("Campaign Three primary endpoint count differs")
        if self.passed_all_frozen_gates == bool(self.failed_gate_codes):
            raise ValueError("Campaign Three decision gate state differs")
        if self.selected_for_model_candidate_set and (
            not self.passed_all_frozen_gates
            or self.status
            is not QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE
        ):
            raise ValueError("Campaign Three selected decision differs")
        if (
            not self.selected_for_model_candidate_set
            and self.status
            is QuantResearchFactorScreeningDecisionStatus.SELECTED_MODEL_CANDIDATE
        ):
            raise ValueError("Campaign Three unselected decision uses selected status")
        if self.passed_all_frozen_gates and not self.selected_for_model_candidate_set:
            if (
                self.status
                is not QuantResearchFactorScreeningDecisionStatus.QUALIFIED_NOT_SELECTED_CAP
            ):
                raise ValueError("Campaign Three qualified decision status differs")
        elif not self.passed_all_frozen_gates and self.status not in {
            QuantResearchFactorScreeningDecisionStatus.REJECTED_SCREEN,
            QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA,
        }:
            raise ValueError("Campaign Three failed decision status differs")
        if self.raw_family_p_value is None or self.holm_adjusted_p_value is None:
            raise ValueError("Campaign Three family probabilities are absent")
        return self


class CampaignThreeScreeningReportV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[CAMPAIGN_THREE_SCREENING_REPORT_CONTRACT_VERSION] = (
        CAMPAIGN_THREE_SCREENING_REPORT_CONTRACT_VERSION
    )
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    registered_ledger_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    access_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    access_grant_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    evaluator_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    source_input_qualification_fingerprint: Literal[
        CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
    ] = CAMPAIGN_THREE_INPUT_QUALIFICATION_FINGERPRINT
    source_input_qualification_sha256: Literal[
        CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
    ] = CAMPAIGN_THREE_INPUT_QUALIFICATION_SHA256
    source_v1_diagnostics_fingerprint: Literal[
        V1_FACTOR_DIAGNOSTICS_FINGERPRINT
    ] = V1_FACTOR_DIAGNOSTICS_FINGERPRINT
    source_v1_diagnostics_sha256: Literal[V1_FACTOR_DIAGNOSTICS_SHA256] = (
        V1_FACTOR_DIAGNOSTICS_SHA256
    )
    source_v2_qualification_fingerprint: Literal[
        V2_FACTOR_QUALIFICATION_FINGERPRINT
    ] = V2_FACTOR_QUALIFICATION_FINGERPRINT
    source_v2_qualification_sha256: Literal[V2_FACTOR_QUALIFICATION_SHA256] = (
        V2_FACTOR_QUALIFICATION_SHA256
    )
    source_market_state_fingerprint: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    ] = MARKET_STATE_QUALIFICATION_REPORT_FINGERPRINT
    source_market_state_sha256: Literal[
        MARKET_STATE_QUALIFICATION_REPORT_SHA256
    ] = MARKET_STATE_QUALIFICATION_REPORT_SHA256
    source_market_state_artifact_identity_fingerprint: Literal[
        MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT
    ] = MARKET_STATE_ARTIFACT_IDENTITY_FINGERPRINT
    source_market_state_artifact_content_sha256: Literal[
        MARKET_STATE_ARTIFACT_CONTENT_SHA256
    ] = MARKET_STATE_ARTIFACT_CONTENT_SHA256
    source_v1_observation_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v2_observation_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_label_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v1_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v1_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v2_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_v2_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_label_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_label_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_terminal_reference_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_evidence_collection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_signal_session: date = date(2025, 7, 22)
    last_signal_session: date = date(2026, 1, 7)
    signal_session_count: Literal[106] = 106
    aligned_observation_count: Literal[167860] = 167860
    label_count: Literal[503580] = 503580
    label_state_counts: dict[str, int]
    session_evidence: tuple[CampaignThreeSessionEvidenceV1, ...] = Field(min_length=1)
    summaries: tuple[CampaignThreeInteractionSummaryV1, ...] = Field(
        min_length=15, max_length=15
    )
    decisions: tuple[CampaignThreeScreeningDecisionV1, ...] = Field(
        min_length=3, max_length=3
    )
    selected_candidate_alpha_ids: tuple[str, ...] = Field(max_length=1)
    selected_risk_guard_ids: tuple[str, ...] = Field(max_length=1)
    status: QuantResearchFactorScreeningReportStatus
    reason_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    formal_execution_count: Literal[1] = 1
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    strategy_expression_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    broker_or_trading_authorized: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "CampaignThreeScreeningReportV1":
        protocol = quant_research_campaign_three_screening_protocol_v1()
        ledger = quant_research_discovery_trial_ledger_v4()
        expected_summaries = tuple(
            (hypothesis.hypothesis_id, horizon, endpoint)
            for hypothesis in protocol.formal_hypotheses
            for horizon in (1, 3, 5)
            for endpoint in (
                (
                    QuantResearchFactorScreeningEndpoint.LOWER,
                    QuantResearchFactorScreeningEndpoint.UPPER,
                )
                if hypothesis.role
                is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                else (QuantResearchFactorScreeningEndpoint.COMPLETE_PATH,)
            )
        )
        hypotheses = {
            item.hypothesis_id: item for item in protocol.formal_hypotheses
        }
        evidence_keys = tuple(
            (
                item.hypothesis_id,
                item.horizon_sessions,
                item.endpoint,
                item.signal_session,
            )
            for item in self.session_evidence
        )
        expected_evidence_keys = tuple(sorted(
            evidence_keys,
            key=lambda item: (
                tuple(hypotheses).index(item[0]),
                (1, 3, 5).index(item[1]),
                ("lower", "upper", "complete_path").index(item[2].value),
                item[3],
            ),
        ))
        selected_alpha = tuple(
            item.hypothesis_id
            for item in self.decisions
            if item.selected_for_model_candidate_set
            and item.role is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
        )
        selected_risk = tuple(
            item.hypothesis_id
            for item in self.decisions
            if item.selected_for_model_candidate_set
            and item.role is CampaignThreeHypothesisRole.RISK_GUARD_INTERACTION
        )
        expected_status = (
            QuantResearchFactorScreeningReportStatus.READY_FOR_MODEL_PROTOCOL_REVIEW
            if selected_alpha
            else (
                QuantResearchFactorScreeningReportStatus.INCONCLUSIVE_DATA
                if any(
                    item.role
                    is CampaignThreeHypothesisRole.CANDIDATE_ALPHA_INTERACTION
                    and item.status
                    is QuantResearchFactorScreeningDecisionStatus.INCONCLUSIVE_DATA
                    for item in self.decisions
                )
                else QuantResearchFactorScreeningReportStatus.CLOSED_NO_CANDIDATE_ALPHA
            )
        )
        expected_label_states = {
            item.value for item in QuantResearchFactorScreeningLabelState
        }
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.registered_ledger_fingerprint != ledger.logical_fingerprint
            or self.first_signal_session != date(2025, 7, 22)
            or self.last_signal_session != date(2026, 1, 7)
            or self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or self.created_at.utcoffset().total_seconds() != 0
            or tuple(
                (item.hypothesis_id, item.horizon_sessions, item.endpoint)
                for item in self.summaries
            )
            != expected_summaries
            or tuple(item.hypothesis_id for item in self.decisions)
            != tuple(item.hypothesis_id for item in protocol.formal_hypotheses)
            or any(
                item.role is not hypotheses[item.hypothesis_id].role
                for item in self.decisions
            )
            or evidence_keys != expected_evidence_keys
            or len(set(evidence_keys)) != len(evidence_keys)
            or any(
                item.role is not hypotheses[item.hypothesis_id].role
                for item in self.session_evidence
            )
            or self.session_evidence_collection_fingerprint
            != _collection_fingerprint(self.session_evidence)
            or any(
                item.evidence_collection_fingerprint
                != _collection_fingerprint(
                    tuple(
                        evidence
                        for evidence in self.session_evidence
                        if evidence.hypothesis_id == item.hypothesis_id
                        and evidence.horizon_sessions == item.horizon_sessions
                        and evidence.endpoint is item.endpoint
                    )
                )
                for item in self.summaries
            )
            or self.selected_candidate_alpha_ids != selected_alpha
            or self.selected_risk_guard_ids != selected_risk
            or (selected_risk and not selected_alpha)
            or self.status is not expected_status
            or set(self.label_state_counts) != expected_label_states
            or any(value < 0 for value in self.label_state_counts.values())
            or sum(self.label_state_counts.values()) != self.label_count
            or tuple(sorted(set(self.selected_candidate_alpha_ids)))
            != self.selected_candidate_alpha_ids
            or tuple(sorted(set(self.selected_risk_guard_ids)))
            != self.selected_risk_guard_ids
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
            or self.limitation_codes != tuple(sorted(set(self.limitation_codes)))
            or screening_result_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("Campaign Three screening report differs")
        return self


def screening_result_fingerprint(value: BaseModel | Mapping[str, object]) -> str:
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


def build_campaign_three_screening_report_v1(**payload: object) -> CampaignThreeScreeningReportV1:
    provisional = CampaignThreeScreeningReportV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return CampaignThreeScreeningReportV1.model_validate(
        {
            **payload,
            "logical_fingerprint": screening_result_fingerprint(provisional),
        }
    )


def _finite_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Campaign Three decimal is invalid") from exc
    if not parsed.is_finite():
        raise ValueError("Campaign Three decimal is not finite")
    return parsed


def _collection_fingerprint(values: tuple[BaseModel, ...]) -> str:
    return hashlib.sha256(
        json.dumps(
            [item.model_dump(mode="json") for item in values],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
