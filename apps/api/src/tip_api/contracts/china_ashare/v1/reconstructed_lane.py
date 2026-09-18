"""Conservative next-session reconstructed lane for A-share diagnostics."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
    FrozenContract,
)


RECONSTRUCTED_LANE_PLAN_VERSION = "china-ashare-reconstructed-lane-plan/1.0"
RECONSTRUCTED_UNIVERSE_DECISION_VERSION = (
    "china-ashare-reconstructed-universe-decision/1.0"
)
RECONSTRUCTED_PARTITION_AGGREGATE_VERSION = (
    "china-ashare-reconstructed-partition-aggregate/1.0"
)


class ChinaAshareReconstructedDisposition(StrEnum):
    CANDIDATE_INCLUDED = "candidate_included"
    CANDIDATE_EXCLUDED = "candidate_excluded"
    QUARANTINED = "quarantined"


class ChinaAshareReconstructedLanePlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-reconstructed-lane-plan/1.0"
    ] = RECONSTRUCTED_LANE_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    diagnostic_plan_fingerprint: str
    diagnostic_package_fingerprint: str
    gap_checklist_fingerprint: str
    normalized_run_fingerprint: str
    normalized_partition_manifest_fingerprints: tuple[str, ...] = Field(min_length=1)
    target_sessions: tuple[date, ...] = Field(min_length=2)
    target_session_set_fingerprint: str
    locally_deterministic_steps: tuple[str, ...] = Field(min_length=1)
    free_official_evidence_required: tuple[str, ...] = Field(min_length=1)
    isolate_or_exclude_rules: tuple[str, ...] = Field(min_length=1)
    knowledge_clock_policy: Literal["next_observed_session_date_only"] = (
        "next_observed_session_date_only"
    )
    source_clock_fabrication_authorized: Literal[False] = False
    as_operated_claim_authorized: Literal[False] = False
    corporate_action_candidate_windows_fail_closed: Literal[True] = True
    unknown_price_limit_fail_closed: Literal[True] = True
    terminal_boundary_candidates_fail_closed: Literal[True] = True
    future_return_read_count: Literal[0] = 0
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    factor_discovery_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "diagnostic_plan_fingerprint",
        "diagnostic_package_fingerprint",
        "gap_checklist_fingerprint",
        "normalized_run_fingerprint",
        "target_session_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("normalized_partition_manifest_fingerprints", mode="before")
    @classmethod
    def partition_hashes_are_ordered(cls, value: Any) -> tuple[str, ...]:
        return tuple(_sha(item, "partition_manifest_fingerprint") for item in value)

    @field_validator(
        "locally_deterministic_steps",
        "free_official_evidence_required",
        "isolate_or_exclude_rules",
        mode="before",
    )
    @classmethod
    def policy_codes_are_sorted(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if normalized != tuple(sorted(set(normalized))):
            raise ValueError("reconstructed lane policy codes differ")
        return normalized

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAshareReconstructedLanePlanV1":
        if self.target_sessions != tuple(sorted(set(self.target_sessions))):
            raise ValueError("reconstructed target sessions differ")
        if _fingerprint(self.target_sessions) != self.target_session_set_fingerprint:
            raise ValueError("reconstructed target session fingerprint differs")
        if reconstructed_lane_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("reconstructed lane plan fingerprint differs")
        return self


class ChinaAshareReconstructedUniverseDecisionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    decision_version: Literal[
        "china-ashare-reconstructed-universe-decision/1.0"
    ] = RECONSTRUCTED_UNIVERSE_DECISION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    evidence_session_date: date
    knowledge_session_date: date | None
    trading_status: ChinaAshareTradingStatus
    risk_warning_status: ChinaAshareRiskWarningStatus
    price_limit_regime: ChinaAsharePriceLimitRegime
    factor_change_candidate_window: bool
    terminal_boundary_candidate: bool
    disposition: ChinaAshareReconstructedDisposition
    reason_codes: tuple[str, ...] = Field(min_length=1)
    source_available_at: None = None
    knowledge_clock_basis: Literal["next_observed_session_date_only"] = (
        "next_observed_session_date_only"
    )
    as_operated: Literal[False] = False
    research_eligible: Literal[False] = False
    input_partition_manifest_fingerprint: str
    logical_fingerprint: str

    @field_validator("input_partition_manifest_fingerprint", "logical_fingerprint")
    @classmethod
    def decision_hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_sorted(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if normalized != tuple(sorted(set(normalized))) or not normalized:
            raise ValueError("reconstructed decision reasons differ")
        return normalized

    @model_validator(mode="after")
    def decision_is_fail_closed(self) -> "ChinaAshareReconstructedUniverseDecisionV1":
        if (
            self.knowledge_session_date is not None
            and self.knowledge_session_date <= self.evidence_session_date
        ):
            raise ValueError("reconstructed knowledge session is not later")
        if self.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN and (
            self.disposition is not ChinaAshareReconstructedDisposition.QUARANTINED
        ):
            raise ValueError("unknown price limit must remain quarantined")
        if (
            self.factor_change_candidate_window
            or self.terminal_boundary_candidate
            or self.knowledge_session_date is None
        ) and self.disposition is not ChinaAshareReconstructedDisposition.QUARANTINED:
            raise ValueError("reconstructed evidence gap must remain quarantined")
        if reconstructed_universe_decision_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("reconstructed Universe decision fingerprint differs")
        return self


class ChinaAshareReconstructedPartitionAggregateV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    aggregate_version: Literal[
        "china-ashare-reconstructed-partition-aggregate/1.0"
    ] = RECONSTRUCTED_PARTITION_AGGREGATE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    partition_index: int = Field(ge=0)
    normalized_partition_manifest_fingerprint: str
    decision_count: int = Field(ge=1)
    next_session_mapped_count: int = Field(ge=0)
    no_next_session_count: int = Field(ge=0)
    candidate_included_count: int = Field(ge=0)
    candidate_excluded_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    unknown_price_limit_count: int = Field(ge=0)
    risk_warning_exclusion_candidate_count: int = Field(ge=0)
    factor_change_candidate_window_count: int = Field(ge=0)
    terminal_boundary_candidate_count: int = Field(ge=0)
    decision_set_fingerprint: str
    future_return_read_count: Literal[0] = 0
    as_operated_claim_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "normalized_partition_manifest_fingerprint",
        "decision_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def aggregate_hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def aggregate_reconciles(self) -> "ChinaAshareReconstructedPartitionAggregateV1":
        if self.next_session_mapped_count + self.no_next_session_count != (
            self.decision_count
        ):
            raise ValueError("reconstructed knowledge counts differ")
        if sum(
            (
                self.candidate_included_count,
                self.candidate_excluded_count,
                self.quarantined_count,
            )
        ) != self.decision_count:
            raise ValueError("reconstructed dispositions differ")
        if reconstructed_partition_aggregate_fingerprint(self) != (
            self.logical_fingerprint
        ):
            raise ValueError("reconstructed partition aggregate fingerprint differs")
        return self


def build_reconstructed_lane_plan(**values: Any) -> ChinaAshareReconstructedLanePlanV1:
    return _build(
        ChinaAshareReconstructedLanePlanV1,
        reconstructed_lane_plan_fingerprint,
        values,
    )


def build_reconstructed_universe_decision(
    **values: Any,
) -> ChinaAshareReconstructedUniverseDecisionV1:
    return _build(
        ChinaAshareReconstructedUniverseDecisionV1,
        reconstructed_universe_decision_fingerprint,
        values,
    )


def build_reconstructed_partition_aggregate(
    **values: Any,
) -> ChinaAshareReconstructedPartitionAggregateV1:
    return _build(
        ChinaAshareReconstructedPartitionAggregateV1,
        reconstructed_partition_aggregate_fingerprint,
        values,
    )


def reconstructed_lane_plan_fingerprint(
    value: ChinaAshareReconstructedLanePlanV1,
) -> str:
    return _contract_fingerprint(value)


def reconstructed_universe_decision_fingerprint(
    value: ChinaAshareReconstructedUniverseDecisionV1,
) -> str:
    return _contract_fingerprint(value)


def reconstructed_partition_aggregate_fingerprint(
    value: ChinaAshareReconstructedPartitionAggregateV1,
) -> str:
    return _contract_fingerprint(value)


def reconstructed_decision_set_fingerprint(
    values: tuple[ChinaAshareReconstructedUniverseDecisionV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in values])


def target_session_set_fingerprint(values: tuple[date, ...]) -> str:
    return _fingerprint(values)


def _build(model, fingerprint, values):
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "logical_fingerprint": fingerprint(provisional),
        }
    )


def _contract_fingerprint(value: FrozenContract) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: object, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized
