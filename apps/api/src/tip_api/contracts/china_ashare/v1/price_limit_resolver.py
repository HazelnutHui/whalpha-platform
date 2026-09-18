"""Outcome-blind, effective-dated A-share price-limit resolution contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    FrozenContract,
)


PRICE_LIMIT_RESOLVER_PLAN_VERSION = "china-ashare-price-limit-resolver-plan/1.0"
PRICE_LIMIT_RESOLUTION_VERSION = "china-ashare-price-limit-resolution/1.0"
PRICE_LIMIT_PARTITION_AGGREGATE_VERSION = (
    "china-ashare-price-limit-partition-aggregate/1.0"
)


class ChinaAsharePriceLimitResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    QUARANTINED = "quarantined"


class ChinaAshareListingStage(StrEnum):
    MATURE_LISTING = "mature_listing"
    ORIGINAL_IPO = "original_ipo"
    RELISTING_OR_RESUMPTION = "relisting_or_resumption"
    TERMINAL_BOUNDARY = "terminal_boundary"
    UNKNOWN = "unknown"


class ChinaAsharePriceLimitResolverPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal[
        "china-ashare-price-limit-resolver-plan/1.0"
    ] = PRICE_LIMIT_RESOLVER_PLAN_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    market_mechanics_package_fingerprint: str
    trading_rule_set_fingerprint: str
    trading_rule_ids: tuple[str, ...] = Field(min_length=1)
    official_source_urls: tuple[str, ...] = Field(min_length=1)
    warning_subtype_fail_closed: Literal[True] = True
    ipo_stage_fail_closed: Literal[True] = True
    relisting_fail_closed: Literal[True] = True
    terminal_boundary_fail_closed: Literal[True] = True
    outcome_read_count: Literal[0] = 0
    as_operated_claim_authorized: Literal[False] = False
    historical_coverage_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "market_mechanics_package_fingerprint",
        "trading_rule_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("trading_rule_ids", "official_source_urls", mode="before")
    @classmethod
    def values_are_ordered(cls, value: Any, info: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip() for item in value)
        if not normalized or normalized != tuple(sorted(set(normalized))):
            raise ValueError(f"{info.field_name} must be unique and ordered")
        return normalized

    @model_validator(mode="after")
    def fingerprint_reconciles(self) -> "ChinaAsharePriceLimitResolverPlanV1":
        if price_limit_resolver_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("price-limit resolver plan fingerprint differs")
        return self


class ChinaAsharePriceLimitResolutionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    resolution_version: Literal[
        "china-ashare-price-limit-resolution/1.0"
    ] = PRICE_LIMIT_RESOLUTION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    session_date: date
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    risk_warning_status: ChinaAshareRiskWarningStatus
    listing_date: date
    listing_stage: ChinaAshareListingStage
    listing_session_ordinal: int | None = Field(default=None, ge=1)
    original_listing_evidence_complete: bool
    risk_warning_evidence_complete: bool
    relisting_absence_evidence_complete: bool
    terminal_boundary_absence_evidence_complete: bool
    status: ChinaAsharePriceLimitResolutionStatus
    price_limit_regime: ChinaAsharePriceLimitRegime
    daily_price_limit_ratio: Decimal | None = None
    selected_rule_id: str | None = None
    reason_codes: tuple[str, ...] = Field(min_length=1)
    resolver_plan_fingerprint: str
    input_partition_manifest_fingerprint: str | None = None
    outcome_read_count: Literal[0] = 0
    as_operated: Literal[False] = False
    research_eligible: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "resolver_plan_fingerprint",
        "input_partition_manifest_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_ordered(cls, value: Any) -> tuple[str, ...]:
        normalized = tuple(str(item).strip().lower() for item in value)
        if not normalized or normalized != tuple(sorted(set(normalized))):
            raise ValueError("price-limit resolution reasons differ")
        return normalized

    @model_validator(mode="after")
    def resolution_is_fail_closed(self) -> "ChinaAsharePriceLimitResolutionV1":
        resolved = self.status is ChinaAsharePriceLimitResolutionStatus.RESOLVED
        if resolved != (self.price_limit_regime is not ChinaAsharePriceLimitRegime.UNKNOWN):
            raise ValueError("price-limit resolution status differs from regime")
        if resolved and (self.selected_rule_id is None):
            raise ValueError("resolved price limit requires selected rule")
        if not resolved and any(
            value is not None
            for value in (self.selected_rule_id, self.daily_price_limit_ratio)
        ):
            raise ValueError("quarantined price limit cannot select rule or ratio")
        if self.price_limit_regime is ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT:
            if self.daily_price_limit_ratio is not None:
                raise ValueError("no-limit resolution cannot carry a ratio")
        elif resolved and self.daily_price_limit_ratio is None:
            raise ValueError("bounded resolution requires a ratio")
        if price_limit_resolution_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("price-limit resolution fingerprint differs")
        return self


class ChinaAsharePriceLimitPartitionAggregateV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    aggregate_version: Literal[
        "china-ashare-price-limit-partition-aggregate/1.0"
    ] = PRICE_LIMIT_PARTITION_AGGREGATE_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    resolver_plan_fingerprint: str
    partition_index: int = Field(ge=0)
    input_partition_manifest_fingerprint: str
    state_count: int = Field(ge=1)
    resolved_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    no_daily_limit_count: int = Field(ge=0)
    percent_5_count: int = Field(ge=0)
    percent_10_count: int = Field(ge=0)
    percent_20_count: int = Field(ge=0)
    warning_evidence_gap_count: int = Field(ge=0)
    lifecycle_evidence_gap_count: int = Field(ge=0)
    rule_gap_count: int = Field(ge=0)
    resolution_set_fingerprint: str
    outcome_read_count: Literal[0] = 0
    as_operated_claim_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "resolver_plan_fingerprint",
        "input_partition_manifest_fingerprint",
        "resolution_set_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def aggregate_reconciles(self) -> "ChinaAsharePriceLimitPartitionAggregateV1":
        if self.resolved_count + self.quarantined_count != self.state_count:
            raise ValueError("price-limit partition dispositions differ")
        if sum(
            (
                self.no_daily_limit_count,
                self.percent_5_count,
                self.percent_10_count,
                self.percent_20_count,
            )
        ) != self.resolved_count:
            raise ValueError("price-limit partition regimes differ")
        if price_limit_partition_aggregate_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("price-limit partition aggregate fingerprint differs")
        return self


def build_price_limit_resolver_plan(**values: Any) -> ChinaAsharePriceLimitResolverPlanV1:
    return _build(
        ChinaAsharePriceLimitResolverPlanV1,
        price_limit_resolver_plan_fingerprint,
        values,
    )


def build_price_limit_resolution(**values: Any) -> ChinaAsharePriceLimitResolutionV1:
    return _build(ChinaAsharePriceLimitResolutionV1, price_limit_resolution_fingerprint, values)


def build_price_limit_partition_aggregate(
    **values: Any,
) -> ChinaAsharePriceLimitPartitionAggregateV1:
    return _build(
        ChinaAsharePriceLimitPartitionAggregateV1,
        price_limit_partition_aggregate_fingerprint,
        values,
    )


def price_limit_resolver_plan_fingerprint(value: ChinaAsharePriceLimitResolverPlanV1) -> str:
    return _contract_fingerprint(value)


def price_limit_resolution_fingerprint(value: ChinaAsharePriceLimitResolutionV1) -> str:
    return _contract_fingerprint(value)


def price_limit_partition_aggregate_fingerprint(
    value: ChinaAsharePriceLimitPartitionAggregateV1,
) -> str:
    return _contract_fingerprint(value)


def price_limit_resolution_set_fingerprint(
    values: tuple[ChinaAsharePriceLimitResolutionV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in values])


def trading_rule_set_fingerprint(values: tuple[Any, ...]) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in values])


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
