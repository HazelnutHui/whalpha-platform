"""Contracts for planning corroboration of inactive-lifecycle review candidates."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    inactive_lifecycle_fingerprint,
)
from tip_api.contracts.market_data.v1.historical_research import KnowledgeTimeStatus


WORK_ITEM_CONTRACT_VERSION = (
    "historical-inactive-lifecycle-corroboration-work-item/1.0"
)
PLAN_CONTRACT_VERSION = "historical-inactive-lifecycle-corroboration-plan/1.0"
PLAN_OPERATION = "plan_inactive_lifecycle_corroboration"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class LifecycleEvidenceRequirement(StrEnum):
    """Evidence that remains necessary before canonical lifecycle promotion."""

    EFFECTIVE_DATE_CORROBORATION = "effective_date_corroboration"
    LAST_TRADABLE_SESSION = "last_tradable_session"
    SOURCE_AVAILABILITY_SEMANTICS = "source_availability_semantics"
    SUCCESSOR_AND_CONSIDERATION_APPLICABILITY = (
        "successor_and_consideration_applicability"
    )
    TERMINAL_CLASSIFICATION = "terminal_classification"


REQUIRED_LIFECYCLE_EVIDENCE = tuple(sorted(LifecycleEvidenceRequirement, key=str))


class LifecycleCorroborationRoute(StrEnum):
    """Current source-selection route, not a selected source policy."""

    NASDAQ_DAILY_LIST_PILOT_REQUIRED = "nasdaq_daily_list_pilot_required"
    ALL_EXCHANGE_SOURCE_SELECTION_REQUIRED = (
        "all_exchange_source_selection_required"
    )


class LifecycleCorroborationStatus(StrEnum):
    """Why a work item cannot proceed to canonical resolution."""

    DOCUMENTED_SOURCE_PILOT_REQUIRED = "documented_source_pilot_required"
    SOURCE_SELECTION_REQUIRED = "source_selection_required"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalInactiveLifecycleCorroborationWorkItemV1(_FrozenModel):
    """One stable-ID review task derived from one shadow candidate."""

    schema_version: Literal[
        "historical-inactive-lifecycle-corroboration-work-item/1.0"
    ] = WORK_ITEM_CONTRACT_VERSION
    anchor_date: date
    source_observation_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    shadow_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_instrument_id: UUID
    primary_exchange: str
    effective_date_candidate: date
    canonical_first_observed_date: date
    canonical_last_observed_date: date
    source_first_observed_at: datetime
    provider_last_updated_field_present: bool
    provider_last_updated_semantics: Literal[
        "unverified_not_source_availability"
    ] = "unverified_not_source_availability"
    knowledge_time_status: Literal[KnowledgeTimeStatus.FIRST_OBSERVED_ONLY] = (
        KnowledgeTimeStatus.FIRST_OBSERVED_ONLY
    )
    source_available_at: None = None
    route: LifecycleCorroborationRoute
    status: LifecycleCorroborationStatus
    required_evidence: tuple[LifecycleEvidenceRequirement, ...] = (
        REQUIRED_LIFECYCLE_EVIDENCE
    )
    canonical_eod_terminal_crosscheck: Literal["required_not_executed"] = (
        "required_not_executed"
    )
    provider_exchange_route_is_locator_only: Literal[True] = True
    ticker_positive_resolution_allowed: Literal[False] = False
    canonical_promotion_allowed: Literal[False] = False
    signal_eligibility_allowed: Literal[False] = False

    @field_validator("primary_exchange", mode="before")
    @classmethod
    def normalize_exchange(cls, value: str) -> str:
        return normalize_required_string(
            value,
            field_name="primary_exchange",
            uppercase=True,
        )

    @field_validator("source_first_observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("required_evidence")
    @classmethod
    def evidence_is_complete(
        cls,
        value: tuple[LifecycleEvidenceRequirement, ...],
    ) -> tuple[LifecycleEvidenceRequirement, ...]:
        if value != REQUIRED_LIFECYCLE_EVIDENCE:
            raise ValueError("lifecycle corroboration evidence requirements differ")
        return value

    @model_validator(mode="after")
    def work_item_reconciles(
        self,
    ) -> "HistoricalInactiveLifecycleCorroborationWorkItemV1":
        if not (
            self.canonical_first_observed_date
            <= self.canonical_last_observed_date
            <= self.effective_date_candidate
            <= self.anchor_date
        ):
            raise ValueError("lifecycle corroboration dates are inconsistent")
        nasdaq_route = self.primary_exchange == "XNAS"
        if nasdaq_route != (
            self.route
            is LifecycleCorroborationRoute.NASDAQ_DAILY_LIST_PILOT_REQUIRED
        ):
            raise ValueError("lifecycle corroboration exchange route differs")
        expected_status = (
            LifecycleCorroborationStatus.DOCUMENTED_SOURCE_PILOT_REQUIRED
            if nasdaq_route
            else LifecycleCorroborationStatus.SOURCE_SELECTION_REQUIRED
        )
        if self.status is not expected_status:
            raise ValueError("lifecycle corroboration route status differs")
        return self


class HistoricalInactiveLifecycleCorroborationPlanV1(_FrozenModel):
    """Immutable no-authority plan for the complete shadow-candidate set."""

    contract_version: Literal[
        "historical-inactive-lifecycle-corroboration-plan/1.0"
    ] = PLAN_CONTRACT_VERSION
    operation: Literal["plan_inactive_lifecycle_corroboration"] = PLAN_OPERATION
    anchor_date: date
    planned_at: datetime
    implementation_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    shadow_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    shadow_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    shadow_source_record_count: int = Field(ge=1)
    shadow_review_candidate_count: int = Field(ge=1)
    shadow_quarantined_count: int = Field(ge=0)
    work_items: tuple[HistoricalInactiveLifecycleCorroborationWorkItemV1, ...] = (
        Field(min_length=1)
    )
    primary_exchange_counts: tuple[tuple[str, int], ...]
    route_counts: tuple[tuple[str, int], ...]
    status_counts: tuple[tuple[str, int], ...]
    required_evidence: tuple[LifecycleEvidenceRequirement, ...] = (
        REQUIRED_LIFECYCLE_EVIDENCE
    )
    unique_source_observation_count: int = Field(ge=1)
    unique_instrument_count: int = Field(ge=1)
    provider_last_updated_present_count: int = Field(ge=0)
    point_in_time_eligible_count: Literal[0] = 0
    ticker_locator_retained_count: Literal[0] = 0
    nasdaq_daily_list_sufficiency_claimed: Literal[False] = False
    all_exchange_source_selected: Literal[False] = False
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    acquisition_authorized: Literal[False] = False
    canonical_lifecycle_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_performance_authorized: Literal[False] = False
    operational_authority: Literal["none"] = "none"
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("planned_at")
    @classmethod
    def planned_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("primary_exchange_counts", "route_counts", "status_counts")
    @classmethod
    def counts_are_canonical(
        cls,
        value: tuple[tuple[str, int], ...],
        info: Any,
    ) -> tuple[tuple[str, int], ...]:
        if value != tuple(sorted(value)) or len(value) != len(dict(value)):
            raise ValueError(f"{info.field_name} must be sorted and unique")
        if any(not key or count < 0 for key, count in value):
            raise ValueError(f"{info.field_name} contains an invalid count")
        return value

    @field_validator("required_evidence")
    @classmethod
    def evidence_is_complete(
        cls,
        value: tuple[LifecycleEvidenceRequirement, ...],
    ) -> tuple[LifecycleEvidenceRequirement, ...]:
        if value != REQUIRED_LIFECYCLE_EVIDENCE:
            raise ValueError("plan evidence requirements differ")
        return value

    @model_validator(mode="after")
    def plan_reconciles(self) -> "HistoricalInactiveLifecycleCorroborationPlanV1":
        items = self.work_items
        count = len(items)
        if (
            count != self.shadow_review_candidate_count
            or self.shadow_source_record_count
            != self.shadow_review_candidate_count + self.shadow_quarantined_count
            or self.unique_source_observation_count != count
            or self.unique_instrument_count != count
        ):
            raise ValueError("lifecycle corroboration plan counts differ")
        source_keys = tuple(item.source_observation_fingerprint for item in items)
        decision_keys = tuple(item.shadow_decision_fingerprint for item in items)
        instrument_keys = tuple(str(item.canonical_instrument_id) for item in items)
        if any(len(set(keys)) != count for keys in (source_keys, decision_keys, instrument_keys)):
            raise ValueError("lifecycle corroboration work-item keys are not unique")
        if tuple(
            sorted(
                items,
                key=lambda item: (
                    item.primary_exchange,
                    item.effective_date_candidate,
                    str(item.canonical_instrument_id),
                ),
            )
        ) != items:
            raise ValueError("lifecycle corroboration work items are not canonical")
        if any(item.anchor_date != self.anchor_date for item in items):
            raise ValueError("lifecycle corroboration work-item anchor differs")
        expected_counts = {
            "primary_exchange_counts": _counts(
                item.primary_exchange for item in items
            ),
            "route_counts": _counts(item.route.value for item in items),
            "status_counts": _counts(item.status.value for item in items),
        }
        for name, expected in expected_counts.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} differs from work items")
        if self.provider_last_updated_present_count != sum(
            item.provider_last_updated_field_present for item in items
        ):
            raise ValueError("provider last-updated count differs")
        expected_fingerprint = inactive_lifecycle_fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected_fingerprint:
            raise ValueError("lifecycle corroboration plan fingerprint differs")
        return self


def _counts(values: Any) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(counts.items()))
