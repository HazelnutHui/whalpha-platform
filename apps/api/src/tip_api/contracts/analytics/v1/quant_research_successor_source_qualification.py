"""Outcome-blind source qualification for the frozen U.S. successor intake."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from functools import lru_cache
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_successor_hypotheses import (
    SuccessorHypothesisRole,
    quant_research_successor_hypothesis_registry_v1,
)


SUCCESSOR_SOURCE_QUALIFICATION_VERSION = (
    "whalpha.quant-research.successor-source-qualification/1.0.0"
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceQualificationDecision(StrEnum):
    BLOCKED_SOURCE_ABSENT = "blocked_source_absent"
    BLOCKED_FORMULA_IDENTITY_COVERAGE = "blocked_formula_identity_coverage"


class SuccessorSourceQualificationCardV1(FrozenModel):
    hypothesis_id: str
    hypothesis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: SuccessorHypothesisRole
    source_foundation_present: bool
    local_exact_feature_row_count: Literal[0] = 0
    local_eligible_session_count: Literal[0] = 0
    decision: SourceQualificationDecision
    stop_reason_codes: tuple[str, ...] = Field(min_length=1)
    acceptable_source_requirements: tuple[str, ...] = Field(min_length=1)
    forbidden_substitutes: tuple[str, ...] = Field(min_length=1)
    outcome_read_count: Literal[0] = 0
    validation_read_count: Literal[0] = 0
    holdout_read_count: Literal[0] = 0
    canonical_write_count: Literal[0] = 0
    formal_trial_count_registered: Literal[0] = 0


class SuccessorSourceQualificationReportV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[SUCCESSOR_SOURCE_QUALIFICATION_VERSION] = (
        SUCCESSOR_SOURCE_QUALIFICATION_VERSION
    )
    evaluated_date: date = date(2026, 9, 17)
    source_registry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["closed_source_blocked"] = "closed_source_blocked"
    cards: tuple[SuccessorSourceQualificationCardV1, ...] = Field(
        min_length=4, max_length=4
    )
    card_count: Literal[4] = 4
    qualified_candidate_alpha_count: Literal[0] = 0
    qualified_risk_guard_count: Literal[0] = 0
    blocked_candidate_alpha_count: Literal[3] = 3
    blocked_risk_guard_count: Literal[1] = 1
    formal_trial_count_registered: Literal[0] = 0
    minimum_alpha_inputs_required_to_continue: Literal[2] = 2
    intake_continuation_authorized: Literal[False] = False
    development_outcome_access_authorized: Literal[False] = False
    validation_access_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    model_construction_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    next_action: Literal[
        "acquire_or_authorize_new_point_in_time_sources_then_register_new_intake_version"
    ] = "acquire_or_authorize_new_point_in_time_sources_then_register_new_intake_version"
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "SuccessorSourceQualificationReportV1":
        registry = quant_research_successor_hypothesis_registry_v1()
        if (
            self.evaluated_date != date(2026, 9, 17)
            or self.source_registry_fingerprint != registry.logical_fingerprint
            or self.cards != _cards()
            or tuple(item.hypothesis_id for item in self.cards)
            != tuple(item.hypothesis_id for item in registry.cards)
            or sum(item.role is SuccessorHypothesisRole.CANDIDATE_ALPHA for item in self.cards) != 3
            or sum(item.role is SuccessorHypothesisRole.RISK_GUARD for item in self.cards) != 1
            or successor_source_qualification_fingerprint(self)
            != self.logical_fingerprint
        ):
            raise ValueError("successor source qualification report differs")
        return self


def successor_source_qualification_fingerprint(
    value: BaseModel | Mapping[str, object],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def quant_research_successor_source_qualification_v1() -> (
    SuccessorSourceQualificationReportV1
):
    registry = quant_research_successor_hypothesis_registry_v1()
    payload = {
        "source_registry_fingerprint": registry.logical_fingerprint,
        "cards": _cards(),
    }
    provisional = SuccessorSourceQualificationReportV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return SuccessorSourceQualificationReportV1.model_validate(
        {**payload, "logical_fingerprint": successor_source_qualification_fingerprint(provisional)}
    )


@lru_cache(maxsize=1)
def _cards() -> tuple[SuccessorSourceQualificationCardV1, ...]:
    registry = quant_research_successor_hypothesis_registry_v1()
    payload_by_id = {item["hypothesis_id"]: item for item in _CARD_PAYLOADS}
    return tuple(
        SuccessorSourceQualificationCardV1(
            hypothesis_id=card.hypothesis_id,
            hypothesis_fingerprint=card.logical_fingerprint,
            role=card.role,
            **{
                key: value
                for key, value in payload_by_id[card.hypothesis_id].items()
                if key != "hypothesis_id"
            },
        )
        for card in registry.cards
    )


_CARD_PAYLOADS = (
    {
        "hypothesis_id": "whalpha.hypothesis.successor-one.fy1-eps-revision-yield",
        "source_foundation_present": False,
        "decision": SourceQualificationDecision.BLOCKED_SOURCE_ABSENT,
        "stop_reason_codes": ("historical_consensus_vintage_absent", "publication_time_absent", "fiscal_period_currency_split_basis_absent"),
        "acceptable_source_requirements": ("licensed_point_in_time_fy1_consensus_vintages", "publication_timestamp_and_revision_lineage", "fiscal_period_currency_split_and_contributor_semantics"),
        "forbidden_substitutes": ("current_consensus_backfill", "actual_eps_or_price_momentum", "target_price_revision", "vintages_without_knowledge_time"),
    },
    {
        "hypothesis_id": "whalpha.hypothesis.successor-one.cash-earnings-quality",
        "source_foundation_present": True,
        "decision": SourceQualificationDecision.BLOCKED_FORMULA_IDENTITY_COVERAGE,
        "stop_reason_codes": ("ttm_formula_not_registered", "cfo_query_not_registered", "strict_identity_projection_insufficient", "point_in_time_nonfinancial_applicability_absent", "exact_feature_coverage_unmeasured"),
        "acceptable_source_requirements": ("sec_as_filed_companyfacts_and_submissions", "filing_acceptance_clock_and_amendment_lineage", "four_quarter_ttm_derivation_and_two_endpoint_assets", "stable_security_projection_and_applicability_policy"),
        "forbidden_substitutes": ("latest_restatement_backfill", "annual_values_as_ttm", "ebitda_or_free_cash_flow", "current_sector_classification", "ticker_or_cik_broadcast_to_share_classes"),
    },
    {
        "hypothesis_id": "whalpha.hypothesis.successor-one.short-interest-change",
        "source_foundation_present": False,
        "decision": SourceQualificationDecision.BLOCKED_SOURCE_ABSENT,
        "stop_reason_codes": ("published_short_interest_history_absent", "publication_and_correction_clock_absent", "point_in_time_security_level_shares_absent"),
        "acceptable_source_requirements": ("issue_level_short_interest_by_settlement_period", "publication_timestamp_and_correction_lineage", "point_in_time_security_level_shares_and_corporate_action_alignment"),
        "forbidden_substitutes": ("daily_short_volume", "trading_volume_or_liquidity", "borrow_fee_or_fails_to_deliver", "current_short_interest_or_shares_backfill"),
    },
    {
        "hypothesis_id": "whalpha.hypothesis.successor-one.scheduled-earnings-event-guard",
        "source_foundation_present": False,
        "decision": SourceQualificationDecision.BLOCKED_SOURCE_ABSENT,
        "stop_reason_codes": ("historical_event_calendar_absent", "announcement_and_revision_clock_absent", "release_timing_history_absent"),
        "acceptable_source_requirements": ("historical_point_in_time_event_calendar", "announcement_revision_cancellation_lineage", "before_open_during_market_after_close_timing"),
        "forbidden_substitutes": ("current_or_final_event_date_backfill", "sec_filing_acceptance_as_schedule", "fixed_day_projection", "price_gap_volume_or_news_proxy"),
    },
)
